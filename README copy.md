# ATOF Next Generation — Phase 1 (runnable starter)

A clean, original ATOF repository scaffold. The native code optimizer is copied from **your previously supplied ATOF package**, not from the third-party Token Optimizer repository. No third-party Token Optimizer source is bundled.

## Included / excluded
- **Included:** FastAPI API, 48-feature catalog, deterministic prompt/evidence analyzer, selective per-request reporting, native Code Context optimization, conservative fidelity gate, capability restrictions, safe fallback, pytest suite.
- **Not yet included:** external Token Optimizer adapter, actual model calls, real Codex/Copilot/Claude interception, provider-token usage, sophisticated semantic verification, database, dashboard. These are later phases.
- Catalog `implemented=true` only for `coding.code_context`. Other IDs are *registered requirements*, not implemented features.

## Windows PowerShell quick start

Open PowerShell **in the folder containing `pyproject.toml`**:

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m atof.cli
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --reload --host 127.0.0.1 --port 8080
```

API docs: http://127.0.0.1:8080/docs
- `GET /health`
- `GET /v1/features` lists catalog and implementation flags
- `POST /v1/analyze` selects applicable features (no optimization)
- `POST /v1/optimize` performs eligible native optimization and returns **candidate payload** + accurate report

**Important:** `payload_returned_to_client` is not evidence the LLM consumed it. `provider_tokens_saved` remains null. Callers must explicitly use the returned `optimized_context` in their downstream LLM requests; live delivery proof is a later phase.

## Git instructions

Extract this ZIP into the root of your **already cloned** empty repository (where `.git/` resides). Copy the *contents* of this starter, not its enclosing folder. Review `git status` and `git diff` before committing. Never commit `.venv` or real enterprise code/logs.

```powershell
git checkout -b feature/phase-1-foundation
git add .
git commit -m "feat: phase 1 ATOF foundation and selective feature registry"
git push -u origin feature/phase-1-foundation
```

Avoid copying the third-party Token Optimizer source into your repository without checking the PolyForm Noncommercial license and intended usage rights.

## Acceptance criteria

1. `GET /v1/features` returns 48 unique IDs; 1 marked implemented.
2. Explain-code request with authorized source selects only applicable Code Context.
3. The native Code Context engine preserves direct Python dependencies and reduces estimated input tokens on example.
4. Copilot requests are clearly `unsupported` for automatic optimization in this Phase 1 implementation.
5. Report distinguishes estimate from provider usage and does not claim verified savings.
6. Failed/ineligible reductions safely leave original evidence unchanged.
7. Unit/API tests pass.

See `docs/PHASE1_DESIGN.md` for architecture and roadmap.
