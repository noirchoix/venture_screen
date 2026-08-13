# Venture Screening Intelligence

Evidence-grounded startup diligence, accelerator-readiness screening, competitive redundancy analysis, current opportunity matching, and evidence-producing validation workflows.

This project consolidates the useful technical assets from `startup_command`, `startup_catalog`, `workflow_build`, `multi_agent`, and selected `mcp_scout` concepts into one production-shaped system. The old agent catalogs are retained in `apps/api/data/legacy_agents_*.json` as donor resources; they are not exposed as pretend independent experts.

## Product thesis

The system answers different questions separately:

1. **Is the startup sufficiently evidenced to judge?**
2. **Is the underlying company/problem/market strong?**
3. **Does it fit a specific accelerator/program adapter?**
4. **How competitively redundant is the thesis against the indexed corpus?**
5. **Do current public problem calls suggest a more defensible adjacent direction?**
6. **What evidence should the founder produce next before rescreening?**

It intentionally does **not** output an accelerator acceptance probability. Public accelerator data does not provide a defensible, calibrated accepted/rejected application dataset with private decision reasoning.

## Current program adapters

The initial registry is versioned as of **2026-08-13**:

- Y Combinator — Fall 2026
- Techstars — General Pool / Program Fit 2026
- Antler Residency — 2026
- 500 Global Accelerator — Eurasia Batch 11

Each adapter stores source URL, capture date, hard/warning eligibility rules, public-selection guidance, criterion weights, and readiness thresholds. Rules are data, not hidden conditionals.

Authoritative source snapshots:

- YC application: `https://apply.ycombinator.com/`
- YC Fall 2026 RFS: `https://www.ycombinator.com/rfs?year=2026`
- Techstars application/interview guidance: `https://www.techstars.com/blog/founder-advice/inside-a-techstars-accelerator-the-application-and-interview-process`
- Antler application/residency: `https://www.antler.co/apply`
- 500 Global Eurasia accelerator: `https://500.co/founders/eurasia/accelerator`

## Architecture

```text
Structured startup submission ─┐
PDF/DOCX/text evidence ─────────┼──> Evidence ledger
Repository ZIP ─────────────────┘        │
                                         ├──> Founder / Team reviewer
Versioned Program Registry ──────────────┤──> Market skeptic
                                         ├──> Customer / traction reviewer
Company Catalog ─> Hybrid Retrieval ─────┤──> Competition reviewer
                                         ├──> Application reviewer
Current Opportunity Registry ────────────┘
                                                │
                                                v
                                       deterministic dimensions
                                                │
                       ┌────────────────────────┼──────────────────────┐
                       v                        v                      v
                Program readiness       Contradictions        Opportunity fit
                       │                        │                      │
                       └────────────────────────┼──────────────────────┘
                                                v
                                         Screening verdict
                                                │
                                                v
                                  Evidence-producing workflows
                                                │
                                                v
                                             rescreen
```

### Deterministic reviewer dimensions

- Founder / Team
- Problem Strength
- Market Attractiveness
- Evidence / Traction
- Differentiation / Competitive Density
- Technical Execution
- Application Quality

Every dimension returns a score, confidence, rationale, evidence IDs, and explicit gaps. Program readiness is a weighted view of these independent dimensions plus program-specific eligibility gates.


## Upload-first startup extraction

Pitch decks/business plans can now be used as the starting point rather than only as attachments. `/api/v1/evidence/prefill` proposes a structured startup patch from uploaded evidence using conservative deterministic extraction:

- explicit section headings map problem, solution, customer, market, business model, pricing, traction, differentiation and moat;
- explicit MRR/users/customers/pilots/growth/funding metrics are parsed with field-level provenance;
- stage and geography cues are proposed only when stated in the document;
- every proposed field includes the source document, excerpt, extraction method and confidence;
- missing required fields remain missing and require founder review.

The web UI shows these proposals and applies them to the startup form only when the user selects **Apply to startup form**.

## Competitive retrieval

The service uses a bounded hybrid similarity model over:

- problem
- customer
- product / solution
- business model
- industry
- geography

Text similarity uses TF-IDF with word n-grams; geography and structured overlap use explicit set similarity. The bundled `companies_seed.json` is **only a smoke-test corpus**. Production use should import a broader, provenance-preserving company index through `/api/v1/companies/import`.

## Evidence ingestion

Supported uploads:

- PDF (machine-readable text; no OCR)
- DOCX
- TXT / Markdown / CSV / JSON / YAML
- repository ZIP

Repository ZIP extraction blocks path traversal, excludes dependency/build directories, bounds file size and total context, and never executes uploaded code.

## Current YC Fall 2026 opportunity registry

The bundled current-RFS snapshot includes:

- The Primer
- The Future of American Defense
- A Cloud for Small Software
- Multiplayer AI
- Compute at Sea
- AI-Powered Consumer Products for 1 Billion People
- AI for the Aging Population
- New Operating Systems for the Physical World
- The Best Time to Build in Crypto
- Data for the Real World
- Proving You're Human
- AI-Native Compliance Infrastructure
- Self-Maintaining APIs

These are used for **adjacent opportunity matching**, not as an assertion that YC only funds these ideas.

## Validation workflow engine

Weak dimensions generate concrete workflows rather than generic advice. Examples include:

- problem interviews with disconfirmation gates;
- bottom-up market sizing and willingness-to-pay validation;
- product activation / pilot / commercial-signal measurement;
- competitor and switching-trigger tests;
- technical proof-of-execution and automated verification;
- claim-to-evidence application rewrites.

Each workflow has an objective, priority, ordered steps, evidence outputs, success criteria, and the dimensions to rescore afterward.

## API

Key endpoints:

```text
GET  /api/v1/health
GET  /api/v1/programs
GET  /api/v1/opportunities
POST /api/v1/evidence/upload
POST /api/v1/evidence/prefill
POST /api/v1/screenings
GET  /api/v1/screenings/{screening_id}
POST /api/v1/companies/import
```

Interactive OpenAPI documentation is available at `/docs` when the API runs.

## Run locally

Python 3.11+ and Node 20+ are recommended.

```bash
# API
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Web, separate terminal
cd apps/web
npm ci
npm run dev -- --host 0.0.0.0
```

Or:

```bash
docker compose up --build
```

The frontend expects `VITE_API_BASE_URL=http://localhost:8000/api/v1` by default.

## Tests

```bash
make check
```

Current backend regression suite covers:

- evidence-grounded screening response construction;
- no acceptance-probability leakage;
- hard geographic/program eligibility rules;
- current opportunity retrieval;
- contradiction detection;
- company-catalog import;
- safe ZIP extraction / path traversal protection;
- upload-first business-plan prefill, explicit metric extraction, and no-invention behavior.

## Production boundaries

The repository is production-shaped but deliberately conservative:

- Store program rules as versioned snapshots and refresh them when official criteria change.
- Treat the bundled company catalog as demonstration data only.
- Put authentication, abuse controls, and encrypted storage in front of public deployments that accept confidential pitch decks or repositories.
- Do not store customer evidence indefinitely without an explicit retention policy.
- Keep LLMs optional. The current screening and scoring core is deterministic and does not require an API key.
- If an LLM is later used for narrative synthesis, it should receive evidence IDs and must not alter deterministic scores or eligibility gates.

## Donor map

| Old project | Reused / adapted capability |
| --- | --- |
| `startup_command` | specialist resources and startup/operator concepts |
| `startup_catalog` | cleaner capability taxonomy and resource metadata |
| `workflow_build` | typed workflow/gate concepts; converted into evidence-producing remediation workflows |
| `multi_agent` | claim/evidence, confidence, session/run ideas; converted from pseudo-agents into scoped reviewer outputs |
| `mcp_scout` | capability-registry concept; used as a basis for bounded research/tool architecture rather than a standalone product |

The application is intentionally **one system**, not a menu of nominal agents.
