# Build Status — Venture Screening Intelligence

Checkpoint date: 2026-08-13

## Verified in this build environment

- Python bytecode compilation: passed.
- Backend regression suite: **8 passed**.
- FastAPI smoke path: health -> evidence upload -> deterministic startup prefill: passed.
- No accelerator acceptance-probability output exists in the response model.
- Program hard-rule, opportunity retrieval, contradiction, catalog import, safe ZIP, and no-invention prefill regression tests are present.

## Frontend verification boundary

The SvelteKit source, typed API client, and CI workflow are included. `npm ci` / `svelte-check` / production build could not be executed in the artifact container because outbound network access is disabled and one required npm tarball is absent from the local cache. The GitHub Actions workflow performs `npm ci && npm run check && npm run build` in an online runner.

This limitation is about local dependency availability, not a claimed passing frontend build.
