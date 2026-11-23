# Phase 6 — Local Dashboard and Token Usage Analytics

## Scope

Phase 6 adds a local web dashboard at `GET /dashboard`, metadata-only opt-in SQLite persistence, `GET /v1/analytics/history`, and `GET /v1/analytics/summary`. The dashboard selects a local **request label**, not an actual IDE agent, and displays relevant features, original/optimized **estimated** tokens, estimated reduction, execution duration and delivery status.

Use custom_api to test a real locally returned candidate. Copilot, Codex and Claude remain unsupported over ordinary HTTP to avoid forging an MCP-delivered request; explicit MCP tools are still supported from Phase 5.

## Windows quick test

```powershell
git switch feature/phase-1-foundation
git pull origin feature/phase-1-foundation
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
$env:ATOF_ANALYTICS_ENABLED = "1"
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080/dashboard. Click **Use synthetic fixture → Analyze → Optimize** with `ATOF custom API`. Verify candidate reduction and feature statuses. Select Copilot and Optimize; expect `unsupported`, not fabricated savings. Refresh for stored metadata.

## Privacy and fidelity limitations

No user prompts, source, log lines, tool outputs or optimized context are saved in the SQLite metadata table. Persistence defaults OFF; set `ATOF_ANALYTICS_ENABLED=1` to enable. Default DB `~/.atof/analytics-v1.sqlite3`, customizable with `ATOF_ANALYTICS_DB`.

The API/dashboard are unauthenticated: use loopback only and never expose to the network. Token counts are a local heuristic, not provider billed usage. `estimated_tokens_removed` aggregates only actual smaller candidates, and is not verified model-token savings. Before/after context estimates are not a matched WITH/WITHOUT provider benchmark. Actual agent switching, IDE plugin integration, third-party Token Optimizer licensing/integration, and real provider receipts remain future work.
