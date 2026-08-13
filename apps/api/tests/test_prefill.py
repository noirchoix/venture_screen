from __future__ import annotations

from services.prefill_service import StartupPrefillService


def test_business_plan_prefill_extracts_sections_and_explicit_metrics():
    text = '''
ContractGuard
Executive Summary
ContractGuard detects breaking API changes and prepares tested migrations before customer integrations fail.

Problem
API providers change contracts and customer teams lose hours to emergency integration fixes and production downtime.

Solution
We compare old and new OpenAPI contracts, locate affected repository usages, and prepare a reviewable migration.

Target Customer
API providers and engineering teams with many production integrations.

Business Model
B2B SaaS sold per connected API and repository.

Pricing
Pilot pricing is $299 per month.

Market Opportunity
Initial buyers already spend on API observability, CI, and dependency-management tools.

Competitive Advantage
Provider-aware semantic diff plus customer-repository blast-radius analysis.

Unfair Advantage
Accumulated API-change-to-fix traces create proprietary migration data.

Traction
We have 3 pilots and 9 active users. MRR $1,250. MoM growth 12%.

Stage
MVP prototype is deployed.

We operate from Nigeria and sell globally.
'''
    doc={'id':'d1','filename':'plan.md','text_content':text}
    result=StartupPrefillService().extract([doc])
    assert result.startup_patch['name']=='ContractGuard'
    assert result.startup_patch['problem'].startswith('API providers change contracts')
    assert result.startup_patch['solution'].startswith('We compare old and new')
    assert result.startup_patch['pilots']==3
    assert result.startup_patch['active_users']==9
    assert result.startup_patch['revenue_monthly_usd']==1250
    assert result.startup_patch['monthly_growth_percent']==12
    assert result.startup_patch['stage']=='prototype'
    assert 'Nigeria' in result.startup_patch['geography']
    assert result.requires_human_review is True


def test_prefill_does_not_invent_missing_required_fields():
    result=StartupPrefillService().extract([{'id':'d1','filename':'notes.txt','text_content':'Traction\n2 pilots\n'}])
    assert result.startup_patch['pilots']==2
    assert 'problem' in result.missing_required_fields
    assert 'solution' in result.missing_required_fields
