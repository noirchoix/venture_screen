from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from schemas.models import EvidenceItem, StartupSubmission


NUMBER_RE = re.compile(r'(?<!\w)(?:\$|USD\s*)?([0-9]+(?:\.[0-9]+)?)(?:\s*(%|k|m|million|billion|users?|customers?|pilots?|months?|years?))?', re.I)


class EvidenceService:
    def build(self, startup: StartupSubmission, documents: list[dict[str, Any]]) -> list[EvidenceItem]:
        ledger: list[EvidenceItem] = []

        def add(
            claim: str,
            evidence: str,
            source_type: str,
            source: str,
            confidence: str,
            field: str | None = None,
            numeric_value: float | None = None,
            unit: str | None = None,
            tags: list[str] | None = None,
        ) -> None:
            evidence = str(evidence).strip()
            if not evidence:
                return
            raw = json.dumps([claim, evidence, source_type, source, field], sort_keys=True)
            item_id = 'ev_' + hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]
            ledger.append(EvidenceItem(
                id=item_id,
                claim=claim,
                evidence=evidence[:12000],
                source_type=source_type,  # type: ignore[arg-type]
                source=source,
                confidence=confidence,  # type: ignore[arg-type]
                field=field,
                numeric_value=numeric_value,
                unit=unit,
                tags=tags or [],
            ))

        text_fields = {
            'one_liner': ('Startup value proposition supplied by founder', startup.one_liner, ['positioning']),
            'problem': ('Problem statement supplied by founder', startup.problem, ['problem']),
            'solution': ('Solution statement supplied by founder', startup.solution, ['solution', 'product']),
            'customer': ('Target customer supplied by founder', startup.customer, ['customer']),
            'industry': ('Industry classification supplied by founder', startup.industry, ['market']),
            'business_model': ('Business model supplied by founder', startup.business_model, ['business_model']),
            'pricing': ('Pricing information supplied by founder', startup.pricing, ['pricing']),
            'market_evidence': ('Market evidence supplied by founder', startup.market_evidence, ['market']),
            'differentiation': ('Differentiation claim supplied by founder', startup.differentiation, ['competition']),
            'unfair_advantage': ('Unfair-advantage claim supplied by founder', startup.unfair_advantage, ['competition', 'moat']),
            'traction': ('Traction narrative supplied by founder', startup.traction, ['traction']),
        }
        for field, (claim, value, tags) in text_fields.items():
            add(claim, value, 'structured_input', 'startup_submission', 'high', field, tags=tags)

        add('Startup stage supplied by founder', startup.stage, 'structured_input', 'startup_submission', 'high', 'stage', tags=['stage'])
        if startup.geography:
            add('Operating geography supplied by founder', ', '.join(startup.geography), 'structured_input', 'startup_submission', 'high', 'geography', tags=['geography'])

        numeric = [
            ('Monthly revenue', startup.revenue_monthly_usd, 'USD/month', 'revenue_monthly_usd', 'traction'),
            ('Active users', startup.active_users, 'users', 'active_users', 'traction'),
            ('Paying customers', startup.paying_customers, 'customers', 'paying_customers', 'traction'),
            ('Pilots', startup.pilots, 'pilots', 'pilots', 'traction'),
            ('Monthly growth', startup.monthly_growth_percent, 'percent', 'monthly_growth_percent', 'traction'),
            ('Months building', startup.months_building, 'months', 'months_building', 'execution'),
            ('Funding raised', startup.funding_raised_usd, 'USD', 'funding_raised_usd', 'funding'),
        ]
        for label, value, unit, field, tag in numeric:
            if value:
                add(f'{label} supplied by founder', f'{value:g} {unit}', 'structured_input', 'startup_submission', 'high', field, float(value), unit, [tag])

        for index, founder in enumerate(startup.founders, start=1):
            details = [founder.name, founder.role, founder.bio]
            if founder.technical:
                details.append('technical founder')
            if founder.domain_years:
                details.append(f'{founder.domain_years:g} domain years')
            if founder.prior_builds:
                details.append(f'{founder.prior_builds} prior builds')
            if founder.prior_startups:
                details.append(f'{founder.prior_startups} prior startups')
            details.extend(founder.notable_outcomes)
            add(f'Founder {index} profile supplied by founder', ' | '.join(x for x in details if x), 'structured_input', 'startup_submission', 'high', f'founders[{index - 1}]', tags=['founder'])

        if startup.technical_assets:
            add('Technical assets supplied by founder', '; '.join(startup.technical_assets), 'structured_input', 'startup_submission', 'high', 'technical_assets', tags=['technical'])
        if startup.repository_signals:
            add('Repository signals supplied or extracted', '; '.join(startup.repository_signals), 'repository', 'startup_submission', 'medium', 'repository_signals', tags=['technical', 'repository'])

        for key, answer in startup.application_answers.items():
            add(f'Application answer: {key}', answer, 'structured_input', 'startup_submission', 'high', f'application_answers.{key}', tags=['application'])

        for doc in documents:
            text = (doc.get('text_content') or '').strip()
            filename = doc.get('filename') or doc.get('id') or 'document'
            source_type = 'repository' if filename.lower().endswith('.zip') or '--- FILE:' in text else 'document'
            add(
                f'Uploaded evidence document: {filename}',
                text,
                source_type,
                filename,
                'medium',
                tags=['document', 'repository'] if source_type == 'repository' else ['document'],
            )
            metrics = self._extract_metrics(text)
            for metric in metrics[:20]:
                add(
                    f'Numeric evidence extracted from {filename}', metric['raw'], source_type, filename,
                    'medium', numeric_value=metric['value'], unit=metric['unit'], tags=['numeric', 'document'],
                )
        return ledger

    def _extract_metrics(self, text: str) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for match in NUMBER_RE.finditer(text[:80000]):
            raw = match.group(0).strip()
            value = float(match.group(1))
            unit = (match.group(2) or '').lower() or None
            if unit == 'k':
                value *= 1_000
            elif unit in {'m', 'million'}:
                value *= 1_000_000
            elif unit == 'billion':
                value *= 1_000_000_000
            found.append({'raw': raw, 'value': value, 'unit': unit})
        return found

    @staticmethod
    def confidence(ledger: list[EvidenceItem]) -> str:
        if not ledger:
            return 'low'
        high = sum(item.confidence == 'high' for item in ledger)
        direct = sum(item.source_type in {'structured_input', 'repository', 'document'} for item in ledger)
        if high >= 8 and direct >= 10:
            return 'high'
        if high >= 4 or direct >= 6:
            return 'medium'
        return 'low'
