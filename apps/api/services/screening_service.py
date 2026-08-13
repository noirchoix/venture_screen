from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from repositories.store import VentureStore
from schemas.models import (
    CompetitorMatch, Contradiction, EligibilityCheck, ProgramAssessment, ReviewDimension,
    ScreeningResponse, StartupSubmission,
)
from services.competitor_service import CompetitorService
from services.evidence_service import EvidenceService
from services.program_registry import ProgramRegistry
from services.reviewers import ReviewerEngine
from services.workflow_service import WorkflowService


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScreeningService:
    QUALITY_WEIGHTS = {
        'founder_team': .17,
        'problem': .15,
        'market': .15,
        'traction': .18,
        'differentiation': .15,
        'technical_execution': .12,
        'application_quality': .08,
    }

    def __init__(self, store: VentureStore):
        self.store = store
        self.registry = ProgramRegistry()
        self.competitors = CompetitorService(store, self.registry)
        self.evidence = EvidenceService()
        self.reviewers = ReviewerEngine()
        self.workflows = WorkflowService()

    def screen(self, startup: StartupSubmission, competitor_limit: int = 8, opportunity_limit: int = 4) -> ScreeningResponse:
        documents = self.store.get_documents(startup.evidence_document_ids)
        ledger = self.evidence.build(startup, documents)
        competitors = self.competitors.find(startup, competitor_limit)
        opportunities = self.competitors.opportunities(startup, opportunity_limit)
        reviewer_reports, dimensions = self.reviewers.evaluate(startup, ledger, competitors)
        confidence = self.evidence.confidence(ledger)
        assessments = self._program_assessments(startup, dimensions, confidence)
        contradictions = self._contradictions(startup, ledger)
        workflows = self.workflows.generate(dimensions)
        overall = self._weighted(dimensions, self.QUALITY_WEIGHTS)
        verdict, rationale = self._verdict(overall, confidence, dimensions, assessments, competitors, opportunities)
        screening_id = 'scr_' + uuid.uuid4().hex[:14]
        response = ScreeningResponse(
            screening_id=screening_id,
            created_at=utcnow(),
            startup_name=startup.name,
            verdict=verdict,
            verdict_rationale=rationale,
            overall_quality_score=round(overall, 1),
            evidence_confidence=confidence,  # type: ignore[arg-type]
            reviewers=reviewer_reports,
            dimensions=dimensions,
            program_assessments=assessments,
            competitors=competitors,
            opportunities=opportunities,
            contradictions=contradictions,
            evidence_ledger=ledger,
            validation_workflows=workflows,
            limitations=[
                'Program readiness is based on public criteria and guidance, not private accelerator deliberations.',
                'The system does not estimate acceptance probability because a calibrated accepted/rejected application dataset is not available.',
                'Competitor retrieval is only as complete as the indexed company catalog; the bundled catalog is a smoke-test seed, not comprehensive market coverage.',
                'Program rules are versioned snapshots and should be refreshed when official program requirements change.',
            ],
            metadata={
                'program_registry_version': max((p['version'] for p in self.registry.programs()), default='unknown'),
                'programs_screened': len(assessments),
                'company_catalog_size': self.store.company_count(),
                'documents_used': len(documents),
                'deterministic_scoring': True,
            },
        )
        self.store.save_screening(screening_id, startup.name, startup.model_dump(mode='json'), response.model_dump(mode='json'))
        return response

    def _program_assessments(self, startup: StartupSubmission, dimensions: list[ReviewDimension], confidence: str) -> list[ProgramAssessment]:
        selected = set(startup.target_program_ids)
        programs = [p for p in self.registry.programs() if not selected or p['id'] in selected]
        dim = {d.id: d for d in dimensions}
        results=[]
        for program in programs:
            checks=[self._eval_rule(rule,startup) for rule in program.get('eligibility_rules',[])]
            hard_fail=any((not c.passed) and c.severity == 'hard' for c in checks)
            score=sum(float(weight)*dim[key].score for key,weight in program['weights'].items() if key in dim)
            thresholds=program.get('readiness_thresholds') or {'strong':75,'moderate':60}
            if hard_fail:
                readiness='ineligible'
            elif score >= thresholds['strong']:
                readiness='strong'
            elif score >= thresholds['moderate']:
                readiness='moderate'
            else:
                readiness='weak'
            notes=list(program.get('notes') or [])
            if program.get('status') == 'deadline_passed':
                notes.insert(0,'The published deadline for this specific cohort has passed; this score describes profile fit, not current application availability.')
            if program.get('status') == 'program_specific':
                notes.insert(0,'Specific Techstars programs can impose additional vertical or geographic constraints; select a concrete program before submission.')
            results.append(ProgramAssessment(
                program_id=program['id'], program_name=program['name'], version=program['version'], source_url=program['source_url'], captured_at=program['captured_at'],
                eligibility=checks, eligible=not hard_fail, applicability_notes=notes,
                weighted_score=round(score,1), readiness=readiness,
                criterion_scores={key:dim[key].score for key in program['weights'] if key in dim},
                evidence_confidence=confidence,  # type: ignore[arg-type]
            ))
        return results

    def _eval_rule(self, rule: dict[str, Any], s: StartupSubmission) -> EligibilityCheck:
        kind=rule['type']; passed=True; evidence=[]
        if kind == 'exists':
            value=getattr(s,rule['field'])
            passed=bool(value)
            if value: evidence.append(str(value))
        elif kind == 'geography_any':
            allowed={str(x).lower() for x in rule.get('values',[])}
            supplied={str(x).lower() for x in s.geography}
            passed=bool(allowed & supplied)
            evidence.append(', '.join(s.geography) or 'No geography supplied')
        elif kind == 'stage_in':
            passed=s.stage in rule.get('values',[]); evidence.append(s.stage)
        elif kind == 'stage_not':
            passed=s.stage != rule.get('value'); evidence.append(s.stage)
        elif kind == 'number_gt':
            value=float(getattr(s,rule['field']))
            passed=value > float(rule.get('value',0)); evidence.append(str(value))
        elif kind == 'founder_count_min':
            count=len(s.founders); passed=count >= int(rule.get('value',1)); evidence.append(str(count))
        return EligibilityCheck(rule_id=rule['id'],passed=passed,severity=rule.get('severity','warning'),message=rule['message'],evidence=evidence)

    def _weighted(self, dimensions: list[ReviewDimension], weights: dict[str,float]) -> float:
        lookup={d.id:d.score for d in dimensions}
        denom=sum(w for k,w in weights.items() if k in lookup) or 1
        return sum(lookup[k]*w for k,w in weights.items() if k in lookup)/denom

    def _verdict(self, overall: float, confidence: str, dims: list[ReviewDimension], assessments: list[ProgramAssessment], competitors: list[CompetitorMatch], opportunities: list[Any]) -> tuple[str,str]:
        d={x.id:x.score for x in dims}
        top_similarity=competitors[0].overall_similarity if competitors else 0
        actionable=[a for a in assessments if a.eligible and a.readiness in {'strong','moderate'}]
        strong=[a for a in assessments if a.eligible and a.readiness == 'strong']
        top_opp=opportunities[0] if opportunities else None
        if confidence == 'low' and d.get('application_quality',0) < 45:
            return 'INSUFFICIENT_EVIDENCE','The submission does not contain enough specific, inspectable evidence to support a reliable venture or accelerator-readiness judgment.'
        if top_similarity >= .80 and d.get('differentiation',0) < 50:
            return 'HIGH_COMPETITIVE_REDUNDANCY',f'The closest indexed competitor has {top_similarity:.0%} modeled overlap while differentiation evidence is weak. Validate a switching trigger or reposition before investing heavily in development.'
        if d.get('market',0) < 38 and d.get('problem',0) < 50:
            return 'LOW_VENTURE_SCALE_POTENTIAL','The current problem/market case is too weakly evidenced to justify accelerator-focused execution. Validate the problem and economic market before optimizing the application.'
        if top_opp and top_opp.similarity >= .35 and d.get('differentiation',0) < 58 and overall >= 48:
            return 'REPOSITION',f'The current thesis has material gaps, but the existing problem/assets align with “{top_opp.title}”. A constrained pivot/repositioning experiment is more defensible than continuing unchanged.'
        if strong and overall >= 70 and confidence in {'medium','high'}:
            names=', '.join(a.program_name for a in strong[:2])
            return 'APPLY_NOW',f'The company clears the internal quality threshold and is strongly aligned with {names}. Address remaining criterion gaps, but the evidence supports applying rather than delaying for generic polish.'
        if actionable:
            names=', '.join(a.program_name for a in actionable[:2])
            return 'APPLY_AFTER_EVIDENCE',f'The company has plausible fit with {names}, but one or more material evidence gaps should be closed with the generated validation workflows before submission.'
        if overall >= 72:
            return 'STRONG_COMPANY_LOW_PROGRAM_FIT','The underlying company scores strongly, but none of the selected program adapters currently show strong actionable fit. Target a different program or cohort rather than distort the company to match a rubric.'
        return 'VALIDATE_FIRST','The idea is not rejected outright, but the evidence is not strong enough to justify accelerator-application optimization yet. Run the highest-priority validation workflows and rescreen.'

    def _contradictions(self, s: StartupSubmission, ledger: list[Any]) -> list[Contradiction]:
        items: list[Contradiction]=[]
        def add(severity: str, a: str, b: str, explanation: str):
            items.append(Contradiction(severity=severity,claim_a=a,claim_b=b,explanation=explanation,evidence_ids=[]))
        if s.stage == 'idea' and (s.revenue_monthly_usd > 0 or s.active_users > 0 or s.paying_customers > 0):
            add('material','Stage is “idea”.','Traction metrics are non-zero.','The structured stage label conflicts with reported operating traction; correct the stage or explain whether metrics refer to prior testing rather than the current product.')
        if s.stage in {'early_revenue','growth'} and s.revenue_monthly_usd <= 0 and 'revenue' not in s.traction.lower():
            add('warning',f'Stage is “{s.stage}”.','No monthly revenue is reported.','A revenue-stage label should be reconciled with the reported revenue metric or revenue narrative.')
        if s.revenue_monthly_usd > 0 and re.search(r'\b(no|zero)\s+(revenue|mrr|sales)\b',s.traction,re.I):
            add('material',f'Monthly revenue is ${s.revenue_monthly_usd:,.0f}.',s.traction[:240],'The traction narrative explicitly states no/zero revenue while the structured revenue field is non-zero.')
        if s.paying_customers > s.active_users and s.active_users > 0:
            add('warning',f'{s.paying_customers} paying customers.',f'{s.active_users} active users.','Paying customers exceed active users; verify the definitions or reporting period.')
        return items
