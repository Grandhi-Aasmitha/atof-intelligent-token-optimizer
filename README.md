# ATOF Next Generation — Phase 5 (Multi-Agent MCP)

**Purpose:** One extensible ATOF optimization platform with explicit MCP tools callable from GitHub Copilot, Codex, and Claude Code. The existing Phase 1–4 API and native optimization engines are preserved.

## Current features

- 48 registered feature IDs; 5 native coding engines currently executable.
- Dynamic applicable-feature analysis, conflict-aware composition, fidelity checks, and honest estimated reductions.
- **3 MCP tools:** `atof_capabilities`, `atof_analyze`, `atof_optimize`.
- Local stdio MCP server with agent startup profiles: `copilot`, `codex`, `claude`.
- VS Code MCP config generator and local smoke-test command.
- No automatic repository reads, agent interception, or provider savings claims.

## Quick start (Windows PowerShell)

Run from repository root with `pyproject.toml`:

```powershell
git switch feature/phase-1-foundation
git pull origin feature/phase-1-foundation
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m atof.mcp_smoke --agent all
```

Optional HTTP API:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --host 127.0.0.1 --port 8080
```

Swagger: http://127.0.0.1:8080/docs. Agent profiles: `GET /v1/agents/capabilities`.

## Connect your coding agent

**See [docs/PHASE5_DESIGN.md](docs/PHASE5_DESIGN.md)** for installation and testing with VS Code Copilot, Codex and Claude Code. In particular, use `python -m atof.mcp_setup` to register Copilot in an approved VS Code workspace.

## Status and limitations

`mcp_tool_result_returned` means the MCP server returned an optimization candidate **as a tool result**, not that an LLM consumed it. Provider-token savings remain unverified. The third-party `alexgreensh/token-optimizer` code is **not bundled**; its license and integration interface need separate review. Automatic agent context replacement is not implemented.
