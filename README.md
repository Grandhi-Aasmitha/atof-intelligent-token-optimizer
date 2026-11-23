# ATOF Next Generation — Phase 4

One platform, 48 registered feature requirements and five executable native optimization strategies. Phase 4 introduces transparent **measurement, evidence fidelity checks and per-feature reporting** on top of the Phase 3 orchestrator.

### Windows quick start (existing branch)

```powershell
git switch feature/phase-1-foundation
git pull origin feature/phase-1-foundation
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --reload --host 127.0.0.1 --port 8080
```

Visit http://127.0.0.1:8080/docs. Use `POST /v1/optimize`, `POST /v1/analyze`, or `GET /v1/reporting/capabilities`.

**Phase 4 is still an API candidate-generation system, not a direct model proxy.** Real Codex/Copilot/Claude delivery, provider usage, and actual model-token savings are not yet verified. The third-party Token Optimizer package remains unintegrated until licensing and callable interface support are settled. Do not put confidential evidence into untrusted endpoints.

See `docs/PHASE4_DESIGN.md` for contracts, limitations and validation steps.
