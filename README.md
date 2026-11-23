# ATOF Next Generation — Phase 2

Policy-driven, extensible token optimization for LLM applications and AI coding agents. Current work is on the existing `feature/phase-1-foundation` branch.

## Implemented

- 48 registered feature identifiers, **five** available native ATOF strategies.
- Code Context, Repository Retrieval, Code Diff, Test Log, and Error Context adapters behind one engine registry.
- Structured authorized evidence fields: `files`, `diff`, `test_output`, `error_output`.
- Deterministic feature selection and guarded `feature_override`.
- Conservative fallback and transparent per-request token estimates.
- `GET /v1/engines` for engine discovery, plus Phase 1 API endpoints.
- Phase 1 regression and Phase 2 contract tests (**19 passed locally**).

**Not yet integrated:** GitHub Token Optimizer source, provider calls and receipts, verified provider savings, multi-engine composition, or automatic Codex/Copilot/Claude interception.

## Windows Quick Start

Run from your cloned repository folder containing `pyproject.toml`:

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --reload --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080/docs and test `/v1/engines` and `/v1/optimize`.

See `docs/PHASE2_DESIGN.md` for contracts, sample requests, and limitations. No third-party Token Optimizer code is vendored. API payload returned does **not** prove model delivery or token savings.
