# ATOF Next Generation — Phase 6

Local multi-agent-aware token optimization analytics dashboard on top of the 48-feature catalog, five native engines, and explicit MCP integrations.

**Open:** http://127.0.0.1:8080/dashboard after starting the FastAPI server.

### Windows setup on the existing branch

```powershell
git switch feature/phase-1-foundation
git pull origin feature/phase-1-foundation
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
$env:ATOF_ANALYTICS_ENABLED = "1"
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --host 127.0.0.1 --port 8080
```

Use the dashboard's **Use synthetic fixture → Analyze → Optimize** flow. Metrics are **local estimates**, not provider-verified savings. Agent selection does not switch the active IDE model, or intercept Copilot/Claude/Codex requests. Their explicit MCP tools from Phase 5 are unaffected.

### Endpoints

- `GET /dashboard` — responsive web dashboard
- `GET /v1/analytics/summary` — aggregate candidate reductions and feature status
- `GET /v1/analytics/history` — metadata-only local history
- Existing `/v1/optimize`, `/v1/analyze`, `/v1/agents/capabilities`, `/health` and MCP tools remain

**Security:** Bind only to `127.0.0.1`; there is no API authentication. Persistence disabled by default and opt-in with `ATOF_ANALYTICS_ENABLED=1`. No raw prompt/log/source is stored in analytics. External Token Optimizer code is not bundled due to licensing/integration considerations.

See `docs/PHASE6_DESIGN.md` for test cases and remaining limitations.
