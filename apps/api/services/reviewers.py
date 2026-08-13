from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

from schemas.models import CompetitorMatch, EvidenceItem, ReviewDimension, ReviewerReport, StartupSubmission


NUMERIC_RE = re.compile(r'(?:\$|USD\s*)?\d[\d,.]*(?:\s*(?:%|users?|customers?|hours?|days?|months?|years?|k|m|million|billion))?', re.I)
PAIN_WORDS = {'manual','slow','expensive','cost','delay','risk','error','waste','fraud','downtime','inefficient','pain','compliance','rejection'}
MARKET_WORDS = {'tam','sam','som','market size','bottom-up','spend','budget','buyers','segment','market'}
MOAT_WORDS = {'proprietary','exclusive','network','workflow','data','distribution','switching','patent','integration','domain','regulatory','community'}


def clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def bounded_text_score(text: str, min_chars: int, full_chars: int) -> float:
    n = len((text or '').strip())
    if n <= min_chars:
        return max(0.0, n / max(1, min_chars) * 25)
    return min(100.0, 25 + 75 * (n - min_chars) / max(1, full_chars - min_chars))


def numeric_density(text: str) -> float:
    if not text:
        return 0.0
    return min(1.0, len(NUMERIC_RE.findall(text)) / 4)


def keyword_density(text: str, words: set[str]) -> float:
    lower = (text or '').lower()
    count = sum(word in lower for word in words)
    return min(1.0, count / max(1, min(4, len(words))))


def conf_for_evidence(ids: list[str], ledger: list[EvidenceItem]) -> str:
    lookup = {e.id: e for e in ledger}
    selected = [lookup[x] for x in ids if x in lookup]
    if not selected:
        return 'low'
    high = sum(x.confidence == 'high' for x in selected)
    if high >= 2 or (high == 1 and len(selected) >= 3):
        return 'high'
    if len(selected) >= 2 or high == 1:
        return 'medium'
    return 'low'


class ReviewerEngine:
    def evaluate(self, startup: StartupSubmission, ledger: list[EvidenceItem], competitors: list[CompetitorMatch]) -> tuple[list[ReviewerReport], list[ReviewDimension]]:
        dimensions = {
            'founder_team': self._founder(startup, ledger),
            'problem': self._problem(startup, ledger),
            'market': self._market(startup, ledger),
            'traction': self._traction(startup, ledger),
            'differentiation': self._differentiation(startup, ledger, competitors),
            'technical_execution': self._technical(startup, ledger),
            'application_quality': self._application(startup, ledger),
        }
        reports = [
            self._report('founder_reviewer', 'Founder / Team Reviewer', 'Assess founder capability, founder-market fit, complementarity, and demonstrated ability to execute.', [dimensions['founder_team'], dimensions['technical_execution']]),
            self._report('market_skeptic', 'Market Skeptic', 'Stress-test whether the problem is concrete, painful, specific, and attached to a venture-scale market.', [dimensions['problem'], dimensions['market']]),
            self._report('traction_reviewer', 'Customer / Traction Reviewer', 'Separate traction evidence from narrative and measure whether customer behavior supports the thesis.', [dimensions['traction']]),
            self._report('competition_reviewer', 'Competition & Redundancy Reviewer', 'Compare claimed differentiation against retrieved commercial overlap and moat evidence.', [dimensions['differentiation']]),
            self._report('application_reviewer', 'Application Quality Reviewer', 'Assess completeness, specificity, quantification, and whether claims are supported by evidence.', [dimensions['application_quality']]),
        ]
        return reports, list(dimensions.values())

    def _evidence_ids(self, ledger: list[EvidenceItem], *tags_or_fields: str) -> list[str]:
        wanted = set(tags_or_fields)
        ids = []
        for e in ledger:
            if e.field in wanted or wanted.intersection(e.tags):
                ids.append(e.id)
        return ids[:16]

    def _dimension(self, id: str, label: str, score: float, rationale: str, evidence_ids: list[str], ledger: list[EvidenceItem], gaps: list[str]) -> ReviewDimension:
        return ReviewDimension(
            id=id, label=label, score=clamp(score), confidence=conf_for_evidence(evidence_ids, ledger),
            rationale=rationale, evidence_ids=evidence_ids, gaps=gaps,
        )

    def _founder(self, s: StartupSubmission, ledger: list[EvidenceItem]) -> ReviewDimension:
        n = len(s.founders)
        if n == 0:
            return self._dimension('founder_team','Founder / Team',8,'No founder profile was supplied.',[],ledger,['Add founder roles, biographies, domain experience, prior builds, and evidence of execution.'])
        technical = sum(f.technical for f in s.founders)
        domain_years = sum(min(f.domain_years, 10) for f in s.founders)
        prior_builds = sum(min(f.prior_builds, 5) for f in s.founders)
        prior_startups = sum(min(f.prior_startups, 3) for f in s.founders)
        outcomes = sum(min(len(f.notable_outcomes), 3) for f in s.founders)
        roles = {f.role.lower().strip() for f in s.founders if f.role.strip()}
        score = 15 + min(n, 3) * 8 + min(technical, 2) * 8 + min(domain_years / 20, 1) * 20 + min(prior_builds / 6, 1) * 14 + min(prior_startups / 3, 1) * 8 + min(outcomes / 4, 1) * 8 + min(len(roles), 3) * 3
        gaps=[]
        if not technical: gaps.append('No technical founder or equivalent product-building evidence is identified.')
        if domain_years < 2: gaps.append('Founder-market/domain experience is weakly evidenced.')
        if prior_builds == 0 and not s.repository_signals: gaps.append('No demonstrated prior build or repository evidence was supplied.')
        ids=self._evidence_ids(ledger,'founder','technical','repository')
        rationale=f'{n} founder(s); {technical} technical; {domain_years:g} capped domain-years; {prior_builds} capped prior builds; {outcomes} notable outcomes.'
        return self._dimension('founder_team','Founder / Team',score,rationale,ids,ledger,gaps)

    def _problem(self, s: StartupSubmission, ledger: list[EvidenceItem]) -> ReviewDimension:
        specificity=bounded_text_score(s.problem,40,450)
        quantified=numeric_density(s.problem+' '+s.market_evidence)
        pain=keyword_density(s.problem,PAIN_WORDS)
        customer=bounded_text_score(s.customer,10,140)
        score=.42*specificity+20*quantified+18*pain+.20*customer
        gaps=[]
        if quantified < .25: gaps.append('Quantify the pain with cost, time, risk, frequency, or failure-rate evidence.')
        if customer < 55: gaps.append('Narrow the initial customer/ICP enough that a reviewer can identify the buyer and user.')
        if specificity < 55: gaps.append('Describe the current workflow and why existing alternatives fail.')
        ids=self._evidence_ids(ledger,'problem','customer','market')
        return self._dimension('problem','Problem Strength',score,f'Problem specificity {specificity:.0f}/100; quantified-pain signal {quantified:.0%}; pain-language signal {pain:.0%}; customer specificity {customer:.0f}/100.',ids,ledger,gaps)

    def _market(self, s: StartupSubmission, ledger: list[EvidenceItem]) -> ReviewDimension:
        evidence=bounded_text_score(s.market_evidence,25,650)
        quantified=numeric_density(s.market_evidence)
        market_logic=keyword_density(s.market_evidence,MARKET_WORDS)
        monetization=bounded_text_score(' '.join([s.business_model,s.pricing]),12,260)
        geo=min(100,25+18*len(s.geography)) if s.geography else 20
        score=.34*evidence+20*quantified+16*market_logic+.20*monetization+.10*geo
        gaps=[]
        if quantified < .25: gaps.append('Provide bottom-up market sizing or buyer-spend evidence instead of only a top-down TAM.')
        if monetization < 50: gaps.append('Clarify who pays, how much, and the economic unit of purchase.')
        if not s.market_evidence.strip(): gaps.append('No market evidence was supplied.')
        ids=self._evidence_ids(ledger,'market','business_model','pricing','geography')
        return self._dimension('market','Market Attractiveness',score,f'Market-evidence specificity {evidence:.0f}/100; quantitative signal {quantified:.0%}; monetization specificity {monetization:.0f}/100.',ids,ledger,gaps)

    def _traction(self, s: StartupSubmission, ledger: list[EvidenceItem]) -> ReviewDimension:
        revenue = min(35, 7 * math.log10(1 + s.revenue_monthly_usd)) if s.revenue_monthly_usd else 0
        customers = min(20, 6 * math.log10(1 + s.paying_customers)) if s.paying_customers else 0
        users = min(12, 3.5 * math.log10(1 + s.active_users)) if s.active_users else 0
        pilots = min(10, s.pilots * 3.5)
        growth = min(13, max(0, s.monthly_growth_percent) / 8)
        narrative = min(10, bounded_text_score(s.traction,20,300) / 10)
        score=revenue+customers+users+pilots+growth+narrative
        if s.stage == 'idea': score=min(score,45)
        gaps=[]
        if s.revenue_monthly_usd == 0 and s.paying_customers == 0: gaps.append('No paid validation is reported; obtain paid pilots, pre-orders, LOIs with commercial terms, or revenue.')
        if s.active_users == 0 and s.pilots == 0: gaps.append('No usage or pilot evidence is reported.')
        if s.monthly_growth_percent <= 0 and s.stage in {'early_revenue','growth'}: gaps.append('Growth-stage claims need a measured growth trajectory.')
        ids=self._evidence_ids(ledger,'traction','revenue_monthly_usd','active_users','paying_customers','pilots','monthly_growth_percent')
        rationale=f'Revenue contribution {revenue:.1f}/35; customers {customers:.1f}/20; users {users:.1f}/12; pilots {pilots:.1f}/10; growth {growth:.1f}/13; narrative {narrative:.1f}/10.'
        return self._dimension('traction','Evidence / Traction',score,rationale,ids,ledger,gaps)

    def _differentiation(self, s: StartupSubmission, ledger: list[EvidenceItem], competitors: list[CompetitorMatch]) -> ReviewDimension:
        narrative=bounded_text_score(' '.join([s.differentiation,s.unfair_advantage]),25,650)
        moat=keyword_density(s.unfair_advantage+' '+s.differentiation,MOAT_WORDS)
        max_sim=competitors[0].overall_similarity if competitors else 0
        redundancy_component=(1-max_sim)*38
        score=.44*narrative+18*moat+redundancy_component
        gaps=[]
        if narrative < 55: gaps.append('State the specific dimension on which the company is meaningfully different, not merely better/faster/AI-powered.')
        if max_sim >= .72: gaps.append(f'Top retrieved competitor overlap is {max_sim:.0%}; validate why customers would switch or choose this product.')
        if moat < .25: gaps.append('Moat evidence is weak; identify data, distribution, workflow ownership, switching costs, IP, regulation, or another defensible compounding advantage.')
        ids=self._evidence_ids(ledger,'competition','moat')
        rationale=f'Differentiation specificity {narrative:.0f}/100; moat signal {moat:.0%}; top competitor similarity {max_sim:.0%}.'
        return self._dimension('differentiation','Differentiation / Competitive Density',score,rationale,ids,ledger,gaps)

    def _technical(self, s: StartupSubmission, ledger: list[EvidenceItem]) -> ReviewDimension:
        stage_points={'idea':8,'prototype':28,'pre_revenue':38,'early_revenue':48,'growth':58,'later':62}[s.stage]
        technical_founder=18 if any(f.technical for f in s.founders) else 0
        assets=min(14,len(s.technical_assets)*4)
        repo=min(18,len(s.repository_signals)*4)
        building=min(8,s.months_building/2)
        score=stage_points+technical_founder+assets+repo+building
        gaps=[]
        if s.stage == 'idea': gaps.append('No functional product/prototype is represented in the submission.')
        if not s.technical_assets: gaps.append('List deployed systems, prototypes, datasets, integrations, or engineering assets relevant to execution.')
        if not s.repository_signals: gaps.append('Repository-level evidence was not supplied; technical claims are therefore less independently inspectable.')
        ids=self._evidence_ids(ledger,'technical','repository','stage','execution')
        return self._dimension('technical_execution','Technical Execution',score,f'Stage contribution {stage_points}; technical-founder contribution {technical_founder}; technical assets {len(s.technical_assets)}; repository signals {len(s.repository_signals)}.',ids,ledger,gaps)

    def _application(self, s: StartupSubmission, ledger: list[EvidenceItem]) -> ReviewDimension:
        fields=[s.one_liner,s.problem,s.solution,s.customer,s.business_model,s.market_evidence,s.differentiation,s.traction]
        complete=sum(bool(x.strip()) for x in fields)/len(fields)
        rich=sum(len(x.strip())>=80 for x in fields)/len(fields)
        quantified=sum(bool(NUMERIC_RE.search(x or '')) for x in fields)/len(fields)
        answers=s.application_answers
        answer_score=min(1,len([v for v in answers.values() if len(v.strip())>=30])/6) if answers else 0
        evidence_bonus=min(1,len(ledger)/18)
        score=35*complete+25*rich+15*quantified+15*answer_score+10*evidence_bonus
        gaps=[]
        if complete < .85: gaps.append('Core application fields are incomplete.')
        if rich < .5: gaps.append('Several answers are too terse to demonstrate specificity and evidence.')
        if quantified < .25: gaps.append('Application answers contain little quantified evidence.')
        if not answers: gaps.append('No program-specific application answers were supplied.')
        ids=self._evidence_ids(ledger,'application','positioning','problem','solution','market','traction')
        return self._dimension('application_quality','Application Quality',score,f'Core completeness {complete:.0%}; substantive-answer coverage {rich:.0%}; quantitative coverage {quantified:.0%}; evidence coverage {evidence_bonus:.0%}.',ids,ledger,gaps)

    def _report(self, reviewer_id: str, name: str, mandate: str, dims: list[ReviewDimension]) -> ReviewerReport:
        concerns=[]; positives=[]
        for d in dims:
            if d.score < 55:
                concerns.append(f'{d.label}: {d.score:.0f}/100. ' + (d.gaps[0] if d.gaps else d.rationale))
            if d.score >= 72:
                positives.append(f'{d.label}: {d.score:.0f}/100.')
        return ReviewerReport(reviewer_id=reviewer_id,name=name,mandate=mandate,dimensions=dims,concerns=concerns,positives=positives)
