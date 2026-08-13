const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');

export type Program = { id:string; name:string; version:string; captured_at:string; source_url:string; status:string; notes:string[] };
export type ExtractedDocument = { document_id:string; filename:string; media_type:string; chars:number; sha256:string; text_preview:string; warnings:string[] };
export type Prefill = { startup_patch:Partial<Startup>; fields:{field:string;value:unknown;confidence:string;source_document_id:string;source_filename:string;evidence_excerpt:string;method:string}[]; missing_required_fields:string[]; warnings:string[]; requires_human_review:boolean };
export type Founder = { name:string; role:string; bio:string; technical:boolean; domain_years:number; prior_builds:number; prior_startups:number; notable_outcomes:string[] };
export type Startup = {
  name:string; one_liner:string; problem:string; solution:string; customer:string; industry:string; geography:string[];
  stage:'idea'|'prototype'|'pre_revenue'|'early_revenue'|'growth'|'later'; business_model:string; pricing:string; market_evidence:string;
  differentiation:string; unfair_advantage:string; traction:string; revenue_monthly_usd:number; active_users:number; paying_customers:number;
  pilots:number; monthly_growth_percent:number; months_building:number; funding_raised_usd:number; product_url:string; founders:Founder[];
  technical_assets:string[]; repository_signals:string[]; application_answers:Record<string,string>; evidence_document_ids:string[]; target_program_ids:string[];
};
export type Dimension = { id:string; label:string; score:number; confidence:string; rationale:string; evidence_ids:string[]; gaps:string[] };
export type ProgramAssessment = { program_id:string; program_name:string; eligible:boolean; readiness:string; weighted_score:number; evidence_confidence:string; criterion_scores:Record<string,number>; eligibility:{rule_id:string;passed:boolean;severity:string;message:string;evidence:string[]}[]; applicability_notes:string[]; caveat:string };
export type Competitor = { company_id:string; name:string; url:string; source:string; overall_similarity:number; problem_overlap:number; customer_overlap:number; product_overlap:number; business_model_overlap:number; geography_overlap:number; explanation:string };
export type Opportunity = { opportunity_id:string; title:string; source:string; source_url:string; similarity:number; capability_fit:number; rationale:string; transferable_assets:string[] };
export type Workflow = { workflow_id:string; finding:string; objective:string; priority:string; steps:{id:string;title:string;instruction:string;gate:string;evidence_output:string;owner:string}[]; success_criteria:string[]; rescore_dimensions:string[] };
export type Screening = { screening_id:string; created_at:string; startup_name:string; verdict:string; verdict_rationale:string; overall_quality_score:number; evidence_confidence:string; dimensions:Dimension[]; program_assessments:ProgramAssessment[]; competitors:Competitor[]; opportunities:Opportunity[]; contradictions:{severity:string;claim_a:string;claim_b:string;explanation:string}[]; validation_workflows:Workflow[]; limitations:string[]; metadata:Record<string,unknown> };

async function json<T>(path:string, init?:RequestInit):Promise<T>{
  const res = await fetch(`${API_BASE}${path}`, init);
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if(!res.ok) throw new Error(body?.detail ?? body?.message ?? `HTTP ${res.status}`);
  return body as T;
}

export const api = {
  programs: () => json<Program[]>('/programs'),
  upload: async (file:File) => {
    const form=new FormData(); form.append('file',file);
    return json<ExtractedDocument>('/evidence/upload',{method:'POST',body:form});
  },
  prefill: (documentIds:string[]) => json<Prefill>('/evidence/prefill',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({document_ids:documentIds})}),
  screen: (startup:Startup) => json<Screening>('/screenings',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({startup,competitor_limit:8,opportunity_limit:5})})
};
