from __future__ import annotations

from pathlib import Path

from repositories.store import VentureStore
from schemas.models import FounderProfile, StartupSubmission
from services.screening_service import ScreeningService


def startup(**overrides):
    data = dict(
        name='ContractGuard',
        one_liner='Detect API changes and automatically prepare tested migrations for affected customer repositories.',
        problem='API vendors ship breaking changes that cause customer downtime, expensive emergency fixes, and integration risk.',
        solution='Normalize old and new API contracts, locate affected client calls, generate a migration, and validate it with repository tests.',
        customer='API providers and engineering teams maintaining production integrations',
        industry='developer tools API infrastructure',
        geography=['Nigeria','Global'],
        stage='prototype',
        business_model='B2B SaaS priced per connected repository and API provider',
        pricing='$299/month pilot tier with enterprise plans',
        market_evidence='Initial buyers are API vendors and engineering teams already paying for observability, CI, dependency management, and developer tooling.',
        differentiation='Provider-aware contract diff plus repository blast-radius analysis and evidence-backed migration validation.',
        unfair_advantage='Cross-API contract graph, migration traces, and accumulated change-to-fix data improve routing and patch quality over time.',
        traction='3 design partners are testing repository scans; one paid pilot is under negotiation.',
        active_users=9,
        pilots=3,
        monthly_growth_percent=12,
        months_building=4,
        founders=[FounderProfile(name='A',role='Founder/Engineer',bio='Builds developer tooling and API systems.',technical=True,domain_years=4,prior_builds=5,notable_outcomes=['Deployed production APIs'])],
        technical_assets=['OpenAPI parser','repository analyzer','contract diff engine','test runner'],
        repository_signals=['FastAPI service','SvelteKit client','automated tests'],
        application_answers={'Why now?':'Agentic coding tools now make repository-aware automated maintenance practical.'},
    )
    data.update(overrides)
    return StartupSubmission(**data)


def test_screening_produces_evidence_not_acceptance_probability(tmp_path: Path):
    service=ScreeningService(VentureStore(tmp_path/'vsi.db'))
    result=service.screen(startup())
    assert 0 <= result.overall_quality_score <= 100
    assert result.program_assessments
    assert all('acceptance probability' in a.caveat for a in result.program_assessments)
    assert result.evidence_ledger
    assert result.validation_workflows
    assert result.metadata['deterministic_scoring'] is True


def test_500_eurasia_hard_geography_rule(tmp_path: Path):
    service=ScreeningService(VentureStore(tmp_path/'vsi.db'))
    s=startup(target_program_ids=['500_eurasia_b11_2026'], geography=['Nigeria'], stage='early_revenue', revenue_monthly_usd=3000)
    result=service.screen(s)
    assessment=result.program_assessments[0]
    assert assessment.eligible is False
    assert assessment.readiness == 'ineligible'
    assert any(c.rule_id == 'eurasia_geography' and not c.passed for c in assessment.eligibility)


def test_yc_rfs_self_maintaining_api_is_retrieved(tmp_path: Path):
    service=ScreeningService(VentureStore(tmp_path/'vsi.db'))
    result=service.screen(startup(), opportunity_limit=5)
    ids={o.opportunity_id for o in result.opportunities}
    assert 'yc_rfs_self_maintaining_api_f2026' in ids


def test_contradictory_stage_is_flagged(tmp_path: Path):
    service=ScreeningService(VentureStore(tmp_path/'vsi.db'))
    result=service.screen(startup(stage='idea', revenue_monthly_usd=2000))
    assert any(x.severity == 'material' for x in result.contradictions)


def test_company_import_changes_catalog(tmp_path: Path):
    store=VentureStore(tmp_path/'vsi.db')
    service=ScreeningService(store)
    before=store.company_count()
    service.competitors.import_companies([{
        'id':'custom','name':'Custom Competitor','one_liner':'API maintenance agent','problem':'breaking API changes','customer':'developers','product':'migration agent','business_model':'SaaS','industry':'developer tools','geography':['Global'],'url':'','source':'test','source_url':''
    }])
    assert store.company_count() == before + 1
