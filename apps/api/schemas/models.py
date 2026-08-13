from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

Confidence = Literal['low', 'medium', 'high']
Verdict = Literal[
    'APPLY_NOW',
    'APPLY_AFTER_EVIDENCE',
    'STRONG_COMPANY_LOW_PROGRAM_FIT',
    'VALIDATE_FIRST',
    'REPOSITION',
    'HIGH_COMPETITIVE_REDUNDANCY',
    'LOW_VENTURE_SCALE_POTENTIAL',
    'INSUFFICIENT_EVIDENCE',
]


class HealthResponse(BaseModel):
    ok: bool
    app_name: str
    environment: str
    programs: int
    opportunities: int
    company_catalog: int
    screenings: int
    deterministic_core: bool = True


class FounderProfile(BaseModel):
    name: str = ''
    role: str = ''
    bio: str = ''
    technical: bool = False
    domain_years: float = Field(default=0, ge=0, le=80)
    prior_builds: int = Field(default=0, ge=0)
    prior_startups: int = Field(default=0, ge=0)
    notable_outcomes: list[str] = Field(default_factory=list)


class StartupSubmission(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    one_liner: str = Field(min_length=8, max_length=500)
    problem: str = Field(min_length=8, max_length=5000)
    solution: str = Field(min_length=8, max_length=5000)
    customer: str = Field(min_length=2, max_length=2000)
    industry: str = Field(default='', max_length=300)
    geography: list[str] = Field(default_factory=list)
    stage: Literal['idea', 'prototype', 'pre_revenue', 'early_revenue', 'growth', 'later'] = 'idea'
    business_model: str = Field(default='', max_length=2000)
    pricing: str = Field(default='', max_length=1200)
    market_evidence: str = Field(default='', max_length=5000)
    differentiation: str = Field(default='', max_length=5000)
    unfair_advantage: str = Field(default='', max_length=5000)
    traction: str = Field(default='', max_length=5000)
    revenue_monthly_usd: float = Field(default=0, ge=0)
    active_users: int = Field(default=0, ge=0)
    paying_customers: int = Field(default=0, ge=0)
    pilots: int = Field(default=0, ge=0)
    monthly_growth_percent: float = Field(default=0, ge=-100, le=10000)
    months_building: float = Field(default=0, ge=0, le=240)
    funding_raised_usd: float = Field(default=0, ge=0)
    product_url: str = ''
    founders: list[FounderProfile] = Field(default_factory=list)
    technical_assets: list[str] = Field(default_factory=list)
    repository_signals: list[str] = Field(default_factory=list)
    application_answers: dict[str, str] = Field(default_factory=dict)
    evidence_document_ids: list[str] = Field(default_factory=list)
    target_program_ids: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def normalize_programs(self) -> 'StartupSubmission':
        self.target_program_ids = list(dict.fromkeys(self.target_program_ids))
        return self


class EvidenceItem(BaseModel):
    id: str
    claim: str
    evidence: str
    source_type: Literal['structured_input', 'document', 'repository', 'catalog', 'program_source', 'derived']
    source: str
    confidence: Confidence
    field: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    tags: list[str] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    document_id: str
    filename: str
    media_type: str
    chars: int
    sha256: str
    text_preview: str
    warnings: list[str] = Field(default_factory=list)


class EligibilityCheck(BaseModel):
    rule_id: str
    passed: bool
    severity: Literal['hard', 'warning', 'info']
    message: str
    evidence: list[str] = Field(default_factory=list)


class ReviewDimension(BaseModel):
    id: str
    label: str
    score: float = Field(ge=0, le=100)
    confidence: Confidence
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ReviewerReport(BaseModel):
    reviewer_id: str
    name: str
    mandate: str
    dimensions: list[ReviewDimension]
    concerns: list[str] = Field(default_factory=list)
    positives: list[str] = Field(default_factory=list)


class CompetitorMatch(BaseModel):
    company_id: str
    name: str
    url: str = ''
    source: str = ''
    overall_similarity: float = Field(ge=0, le=1)
    problem_overlap: float = Field(ge=0, le=1)
    customer_overlap: float = Field(ge=0, le=1)
    product_overlap: float = Field(ge=0, le=1)
    business_model_overlap: float = Field(ge=0, le=1)
    geography_overlap: float = Field(ge=0, le=1)
    explanation: str


class OpportunityMatch(BaseModel):
    opportunity_id: str
    title: str
    source: str
    source_url: str
    similarity: float = Field(ge=0, le=1)
    capability_fit: float = Field(ge=0, le=1)
    rationale: str
    transferable_assets: list[str] = Field(default_factory=list)


class ProgramAssessment(BaseModel):
    program_id: str
    program_name: str
    version: str
    source_url: str
    captured_at: str
    eligibility: list[EligibilityCheck]
    eligible: bool
    applicability_notes: list[str] = Field(default_factory=list)
    weighted_score: float = Field(ge=0, le=100)
    readiness: Literal['strong', 'moderate', 'weak', 'ineligible']
    criterion_scores: dict[str, float]
    evidence_confidence: Confidence
    caveat: str = 'Readiness is a decision-support assessment, not an acceptance probability.'


class WorkflowStep(BaseModel):
    id: str
    title: str
    instruction: str
    gate: str
    evidence_output: str
    owner: str = 'founder'


class ValidationWorkflow(BaseModel):
    workflow_id: str
    finding: str
    objective: str
    priority: Literal['critical', 'high', 'medium']
    steps: list[WorkflowStep]
    success_criteria: list[str]
    rescore_dimensions: list[str]


class Contradiction(BaseModel):
    severity: Literal['warning', 'material']
    claim_a: str
    claim_b: str
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)


class ScreeningRequest(BaseModel):
    startup: StartupSubmission
    competitor_limit: int = Field(default=8, ge=1, le=25)
    opportunity_limit: int = Field(default=4, ge=1, le=12)


class ScreeningResponse(BaseModel):
    screening_id: str
    created_at: str
    startup_name: str
    verdict: Verdict
    verdict_rationale: str
    overall_quality_score: float = Field(ge=0, le=100)
    evidence_confidence: Confidence
    reviewers: list[ReviewerReport]
    dimensions: list[ReviewDimension]
    program_assessments: list[ProgramAssessment]
    competitors: list[CompetitorMatch]
    opportunities: list[OpportunityMatch]
    contradictions: list[Contradiction]
    evidence_ledger: list[EvidenceItem]
    validation_workflows: list[ValidationWorkflow]
    limitations: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanyRecord(BaseModel):
    id: str
    name: str
    one_liner: str = ''
    problem: str = ''
    customer: str = ''
    product: str = ''
    business_model: str = ''
    industry: str = ''
    geography: list[str] = Field(default_factory=list)
    url: str = ''
    source: str = 'user_import'
    source_url: str = ''


class CompanyImportRequest(BaseModel):
    companies: list[CompanyRecord] = Field(min_length=1, max_length=5000)
    replace_source: str | None = None


class CompanyImportResponse(BaseModel):
    inserted: int
    catalog_size: int


class PrefillField(BaseModel):
    field: str
    value: Any
    confidence: Confidence
    source_document_id: str
    source_filename: str
    evidence_excerpt: str
    method: str


class StartupPrefillRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1, max_length=20)


class StartupPrefillResponse(BaseModel):
    startup_patch: dict[str, Any]
    fields: list[PrefillField]
    missing_required_fields: list[str]
    warnings: list[str]
    requires_human_review: bool = True
