from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.config import BASE_DIR
from repositories.store import VentureStore
from schemas.models import CompetitorMatch, OpportunityMatch, StartupSubmission
from services.program_registry import ProgramRegistry


WORD_RE = re.compile(r'[a-z0-9][a-z0-9+.#/-]*', re.I)


def tokens(text: str) -> set[str]:
    return {x.lower() for x in WORD_RE.findall(text or '') if len(x) > 2}


def jaccard(a: str | list[str], b: str | list[str]) -> float:
    aa = tokens(' '.join(a) if isinstance(a, list) else a)
    bb = tokens(' '.join(b) if isinstance(b, list) else b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


class CompetitorService:
    def __init__(self, store: VentureStore, registry: ProgramRegistry):
        self.store = store
        self.registry = registry
        self._ensure_seed()

    def _ensure_seed(self) -> None:
        if self.store.company_count() > 0:
            return
        seed_path = BASE_DIR / 'data' / 'companies_seed.json'
        seed = json.loads(seed_path.read_text(encoding='utf-8'))
        self.store.upsert_companies(seed)

    def import_companies(self, companies: list[dict[str, Any]], replace_source: str | None = None) -> int:
        return self.store.upsert_companies(companies, replace_source)

    def find(self, startup: StartupSubmission, limit: int = 8) -> list[CompetitorMatch]:
        companies = self.store.list_companies()
        if not companies:
            return []
        fields = {
            'problem': (startup.problem, [c.get('problem','') for c in companies]),
            'customer': (startup.customer, [c.get('customer','') for c in companies]),
            'product': (' '.join([startup.one_liner, startup.solution]), [' '.join([c.get('one_liner',''), c.get('product','')]) for c in companies]),
            'business': (startup.business_model, [c.get('business_model','') for c in companies]),
            'industry': (startup.industry, [c.get('industry','') for c in companies]),
        }
        sims = {name: self._tfidf(query, corpus) for name, (query, corpus) in fields.items()}
        matches: list[CompetitorMatch] = []
        for i, c in enumerate(companies):
            problem = float(sims['problem'][i])
            customer = float(sims['customer'][i])
            product = float(sims['product'][i])
            business = float(sims['business'][i])
            industry = float(sims['industry'][i])
            geo = jaccard(startup.geography, c.get('geography') or [])
            overall = 0.28 * problem + 0.23 * customer + 0.23 * product + 0.10 * business + 0.11 * industry + 0.05 * geo
            strongest = sorted(
                [('problem', problem), ('customer', customer), ('product', product), ('business model', business), ('industry', industry)],
                key=lambda x: x[1], reverse=True,
            )[:2]
            explanation = f"Strongest overlap: {strongest[0][0]} {strongest[0][1]:.0%}, {strongest[1][0]} {strongest[1][1]:.0%}. Geography overlap {geo:.0%}."
            matches.append(CompetitorMatch(
                company_id=c['id'], name=c['name'], url=c.get('url',''), source=c.get('source',''),
                overall_similarity=round(max(0.0, min(1.0, overall)), 4),
                problem_overlap=round(problem, 4), customer_overlap=round(customer, 4),
                product_overlap=round(product, 4), business_model_overlap=round(business, 4),
                geography_overlap=round(geo, 4), explanation=explanation,
            ))
        matches.sort(key=lambda x: x.overall_similarity, reverse=True)
        return matches[:limit]

    def opportunities(self, startup: StartupSubmission, limit: int = 4) -> list[OpportunityMatch]:
        opportunities = self.registry.opportunities()
        query = ' '.join([
            startup.one_liner, startup.problem, startup.solution, startup.customer, startup.industry,
            startup.business_model, startup.differentiation, ' '.join(startup.technical_assets),
        ])
        corpus = [' '.join([o['title'], o['summary'], ' '.join(o.get('keywords') or [])]) for o in opportunities]
        sim = self._tfidf(query, corpus)
        asset_text = ' '.join(startup.technical_assets + startup.repository_signals + [startup.solution])
        results: list[OpportunityMatch] = []
        for i, opp in enumerate(opportunities):
            capability = jaccard(asset_text, opp.get('keywords') or [])
            # Avoid a zero capability score for conceptually similar opportunities when assets are not supplied.
            if not startup.technical_assets and not startup.repository_signals:
                capability = min(float(sim[i]) * 0.65, 0.55)
            transferable = self._transferable_assets(startup, opp)
            rationale = f"Idea similarity {float(sim[i]):.0%}; capability/asset overlap {capability:.0%}."
            if transferable:
                rationale += ' Transferable assets: ' + ', '.join(transferable[:4]) + '.'
            results.append(OpportunityMatch(
                opportunity_id=opp['id'], title=opp['title'], source=opp['source'], source_url=opp['source_url'],
                similarity=round(float(sim[i]), 4), capability_fit=round(float(capability), 4),
                rationale=rationale, transferable_assets=transferable,
            ))
        results.sort(key=lambda x: (0.72 * x.similarity + 0.28 * x.capability_fit), reverse=True)
        return results[:limit]

    def _transferable_assets(self, startup: StartupSubmission, opp: dict[str, Any]) -> list[str]:
        opp_tokens = tokens(' '.join(opp.get('keywords') or []) + ' ' + opp.get('summary',''))
        result = []
        for asset in startup.technical_assets + startup.repository_signals:
            if tokens(asset) & opp_tokens:
                result.append(asset)
        return result[:8]

    def _tfidf(self, query: str, corpus: list[str]) -> np.ndarray:
        if not query.strip() or not any(x.strip() for x in corpus):
            return np.zeros(len(corpus), dtype=float)
        texts = [query] + [x or '' for x in corpus]
        try:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words='english',
                ngram_range=(1, 2),
                sublinear_tf=True,
                max_features=12000,
            )
            matrix = vectorizer.fit_transform(texts)
            return cosine_similarity(matrix[0:1], matrix[1:]).ravel()
        except ValueError:
            return np.zeros(len(corpus), dtype=float)
