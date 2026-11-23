# ATOF Next Generation — Phase 3

Dynamic, capability-aware selection and multi-feature execution for caller-supplied source, Git diffs, test logs and error output.

## What works

- 48 registered feature IDs, with five native engines currently executable.
- One request can run multiple non-conflicting optimizers across separate evidence types.
- Mutual exclusion: Code Context vs Repository Retrieval (shared `files` evidence).
- Deterministic priority, per-request `max_optimizers`, safe `feature_override`.
- Independent stage failures retain original evidence; no raw exception details leaked in the report.
- A composed context with original/optimized estimates, per-feature statuses and stage results.
- No fabricated model delivery or provider-token savings.

## Local development

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --reload --port 8080
```

Open http://127.0.0.1:8080/docs and run `POST /v1/optimize`.

See `docs/PHASE3_DESIGN.md` for orchestration semantics, limitations and testing.

**Not included yet:** licensed GitHub Token Optimizer integration, direct Codex/Copilot/Claude interception, provider-level delivery receipts, measured provider savings.
