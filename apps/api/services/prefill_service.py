from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from schemas.models import PrefillField, StartupPrefillResponse


@dataclass(frozen=True)
class Section:
    title: str
    body: str
    document_id: str
    filename: str


class StartupPrefillService:
    """Conservative deterministic extraction from startup plans/pitch text.

    This service does not invent absent fields. It looks for explicit section headings,
    recognized metric phrases, and a small set of stage/location cues. Every proposed
    value is returned with the excerpt and method that produced it for founder review.
    """

    SECTION_ALIASES = {
        'problem': {'problem', 'problem statement', 'challenge', 'pain point', 'pain points'},
        'solution': {'solution', 'our solution', 'product', 'product overview', 'proposed solution'},
        'customer': {'target customer', 'target customers', 'customer', 'customers', 'target audience', 'ideal customer profile', 'icp'},
        'industry': {'industry', 'sector', 'category'},
        'business_model': {'business model', 'revenue model', 'monetization', 'how we make money'},
        'pricing': {'pricing', 'pricing model', 'price'},
        'market_evidence': {'market', 'market opportunity', 'market size', 'target market', 'tam sam som'},
        'differentiation': {'competition', 'competitive landscape', 'competitive advantage', 'differentiation', 'why us'},
        'unfair_advantage': {'unfair advantage', 'moat', 'defensibility', 'defensible advantage'},
        'traction': {'traction', 'progress', 'milestones', 'validation', 'key metrics', 'metrics'},
        'summary': {'executive summary', 'summary', 'overview', 'company overview'},
        'team': {'team', 'founders', 'founding team'},
    }

    METRICS: list[tuple[str, re.Pattern[str], str]] = [
        ('revenue_monthly_usd', re.compile(r'(?i)\b(?:mrr|monthly recurring revenue|monthly revenue)\b[^\n$0-9]{0,45}(?:USD\s*)?\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*([kKmM]?)'), 'USD/month'),
        ('active_users', re.compile(r'(?i)\b([0-9][0-9,]*)\s+(?:monthly\s+|weekly\s+)?active\s+users?\b'), 'users'),
        ('paying_customers', re.compile(r'(?i)\b([0-9][0-9,]*)\s+(?:paying\s+customers?|paid\s+customers?|customers?\s+paying)\b'), 'customers'),
        ('pilots', re.compile(r'(?i)\b([0-9][0-9,]*)\s+(?:paid\s+)?pilots?\b'), 'pilots'),
        ('monthly_growth_percent', re.compile(r'(?i)\b(?:mom|month[- ]over[- ]month|monthly)\s+(?:growth\s*)?(?:of\s*)?([0-9]+(?:\.\d+)?)\s*%'), 'percent'),
        ('funding_raised_usd', re.compile(r'(?i)\b(?:raised|funding raised|capital raised)\b[^\n$0-9]{0,35}(?:USD\s*)?\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*([kKmM]?)'), 'USD'),
        ('months_building', re.compile(r'(?i)\b(?:building|working on (?:this|the company)|development)\b[^\n0-9]{0,35}([0-9]+(?:\.\d+)?)\s+months?\b'), 'months'),
    ]

    GEO_TERMS = [
        'Nigeria', 'Lagos', 'United States', 'USA', 'United Kingdom', 'UK', 'Canada', 'Europe', 'Africa',
        'Ghana', 'Kenya', 'South Africa', 'India', 'Singapore', 'UAE', 'Global', 'Worldwide'
    ]

    def extract(self, documents: list[dict[str, Any]]) -> StartupPrefillResponse:
        fields: list[PrefillField] = []
        warnings: list[str] = []
        sections: list[Section] = []
        for doc in documents:
            text = str(doc.get('text_content') or '')[:160_000]
            if not text.strip():
                warnings.append(f"{doc.get('filename','document')}: no machine-readable text was available for prefill.")
                continue
            sections.extend(self._sections(text, str(doc['id']), str(doc.get('filename') or doc['id'])))
            fields.extend(self._title_and_summary(text, str(doc['id']), str(doc.get('filename') or doc['id'])))
            fields.extend(self._metrics(text, str(doc['id']), str(doc.get('filename') or doc['id'])))
            fields.extend(self._stage(text, str(doc['id']), str(doc.get('filename') or doc['id'])))
            fields.extend(self._geography(text, str(doc['id']), str(doc.get('filename') or doc['id'])))

        for target, aliases in self.SECTION_ALIASES.items():
            if target in {'summary', 'team'}:
                continue
            candidates = [s for s in sections if self._norm_heading(s.title) in aliases]
            if not candidates:
                continue
            best = max(candidates, key=lambda s: min(len(s.body), 3500))
            body = self._clean(best.body, 3200)
            if body:
                fields.append(PrefillField(
                    field=target, value=body, confidence='high', source_document_id=best.document_id,
                    source_filename=best.filename, evidence_excerpt=body[:420], method=f'section:{best.title}'
                ))

        # Prefer explicit high-confidence fields and de-duplicate per target.
        rank = {'high': 3, 'medium': 2, 'low': 1}
        best_by_field: dict[str, PrefillField] = {}
        for field in fields:
            current = best_by_field.get(field.field)
            if current is None or rank[field.confidence] > rank[current.confidence] or (
                rank[field.confidence] == rank[current.confidence] and len(str(field.value)) > len(str(current.value))
            ):
                best_by_field[field.field] = field

        startup_patch = {k: v.value for k, v in best_by_field.items()}
        required = ['name', 'one_liner', 'problem', 'solution', 'customer']
        missing = [x for x in required if not str(startup_patch.get(x, '')).strip()]
        if missing:
            warnings.append('Required fields not safely extractable: ' + ', '.join(missing) + '. Founder review/input is required before screening.')
        ordered = sorted(best_by_field.values(), key=lambda x: (required.index(x.field) if x.field in required else 99, x.field))
        return StartupPrefillResponse(startup_patch=startup_patch, fields=ordered, missing_required_fields=missing, warnings=warnings)

    def _sections(self, text: str, document_id: str, filename: str) -> list[Section]:
        lines = text.replace('\r', '').split('\n')
        headings: list[tuple[int, str]] = []
        aliases = {a for values in self.SECTION_ALIASES.values() for a in values}
        for i, raw in enumerate(lines):
            stripped = raw.strip().strip('#').strip().rstrip(':').strip()
            norm = self._norm_heading(stripped)
            if norm in aliases:
                headings.append((i, stripped))
        result: list[Section] = []
        for pos, (index, title) in enumerate(headings):
            end = headings[pos + 1][0] if pos + 1 < len(headings) else min(len(lines), index + 45)
            body = '\n'.join(lines[index + 1:end]).strip()
            if body:
                result.append(Section(title=title, body=body, document_id=document_id, filename=filename))
        return result

    def _title_and_summary(self, text: str, document_id: str, filename: str) -> list[PrefillField]:
        out: list[PrefillField] = []
        lines = [self._clean(x.strip().strip('#').strip(), 300) for x in text.replace('\r', '').split('\n') if x.strip()]
        generic = {a for values in self.SECTION_ALIASES.values() for a in values} | {'pitch deck', 'business plan', 'startup plan', 'confidential'}
        for line in lines[:12]:
            norm = self._norm_heading(line)
            if 2 <= len(line) <= 100 and norm not in generic and not re.search(r'[@/]|https?://|\b20\d{2}\b', line):
                if len(line.split()) <= 10:
                    out.append(PrefillField(field='name', value=line, confidence='medium', source_document_id=document_id, source_filename=filename, evidence_excerpt=line, method='document-title-candidate'))
                    break
        # One-liner only when a summary/overview section provides a complete sentence.
        secs = self._sections(text, document_id, filename)
        summaries = [s for s in secs if self._norm_heading(s.title) in self.SECTION_ALIASES['summary']]
        if summaries:
            sentence = re.split(r'(?<=[.!?])\s+', self._clean(summaries[0].body, 1200))[0].strip()
            if 20 <= len(sentence) <= 500:
                out.append(PrefillField(field='one_liner', value=sentence, confidence='medium', source_document_id=document_id, source_filename=filename, evidence_excerpt=sentence, method=f'summary-first-sentence:{summaries[0].title}'))
        return out

    def _metrics(self, text: str, document_id: str, filename: str) -> list[PrefillField]:
        out: list[PrefillField] = []
        for field, pattern, unit in self.METRICS:
            match = pattern.search(text)
            if not match:
                continue
            raw_num = match.group(1).replace(',', '')
            value = float(raw_num)
            suffix = match.group(2).lower() if match.lastindex and match.lastindex >= 2 and match.group(2) else ''
            if suffix == 'k': value *= 1000
            elif suffix == 'm': value *= 1_000_000
            if field in {'active_users', 'paying_customers', 'pilots'}:
                value = int(value)
            excerpt = self._context(text, match.start(), match.end())
            out.append(PrefillField(field=field, value=value, confidence='high', source_document_id=document_id, source_filename=filename, evidence_excerpt=excerpt, method=f'explicit-metric:{unit}'))
        return out

    def _stage(self, text: str, document_id: str, filename: str) -> list[PrefillField]:
        lower = text.lower()
        choices = [
            ('growth', [r'\bgrowth stage\b', r'\bscaling\b']),
            ('early_revenue', [r'\bearly[- ]revenue\b', r'\brevenue generating\b']),
            ('pre_revenue', [r'\bpre[- ]revenue\b']),
            ('prototype', [r'\bprototype\b', r'\bmvp\b', r'minimum viable product']),
            ('idea', [r'\bidea stage\b', r'\bpre[- ]product\b']),
        ]
        for stage, patterns in choices:
            for pattern in patterns:
                match = re.search(pattern, lower)
                if match:
                    return [PrefillField(field='stage', value=stage, confidence='medium', source_document_id=document_id, source_filename=filename, evidence_excerpt=self._context(text, match.start(), match.end()), method='explicit-stage-cue')]
        return []

    def _geography(self, text: str, document_id: str, filename: str) -> list[PrefillField]:
        found=[]
        for term in self.GEO_TERMS:
            if re.search(rf'(?i)(?<!\w){re.escape(term)}(?!\w)', text):
                canonical = {'USA':'United States','UK':'United Kingdom','Worldwide':'Global'}.get(term, term)
                if canonical not in found: found.append(canonical)
        if not found:
            return []
        return [PrefillField(field='geography', value=found[:8], confidence='medium', source_document_id=document_id, source_filename=filename, evidence_excerpt=', '.join(found[:8]), method='named-geography-cue')]

    @staticmethod
    def _norm_heading(value: str) -> str:
        return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', value.lower())).strip()

    @staticmethod
    def _clean(value: str, limit: int) -> str:
        value = re.sub(r'[ \t]+', ' ', value)
        value = re.sub(r'\n{3,}', '\n\n', value).strip()
        return value[:limit]

    @staticmethod
    def _context(text: str, start: int, end: int, radius: int = 100) -> str:
        return re.sub(r'\s+', ' ', text[max(0, start-radius):min(len(text), end+radius)]).strip()[:360]
