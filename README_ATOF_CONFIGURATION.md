# ATOF — Simple setup and unified dashboard

## 1. Install once
Install approved Git, Python 3.11+ and VS Code. Open PowerShell in your projects directory, not inside an existing ATOF clone.

~~~powershell
git clone -b feature/phase-1-foundation https://github.com/Grandhi-Aasmitha/atof-intelligent-token-optimizer.git
cd atof-intelligent-token-optimizer
~~~

Existing users: check git remote -v and git status; pull the existing branch with git pull --ff-only origin feature/phase-1-foundation. Do not clone again.

## 2. Start with one command

~~~powershell
py -3.11 scripts/start_atof.py
~~~

This creates the virtual environment if missing, installs dependencies, enables local metadata analytics and starts the loopback dashboard. Open http://127.0.0.1:8080/dashboard. Keep the terminal running. Stop with Ctrl+C.

For approved Copilot setup and launch in one command:

~~~powershell
py -3.11 scripts/start_atof.py --copilot
~~~

This additionally configures .vscode/mcp.json, preserving other servers and refusing conflicting ATOF definitions. Start/approve the MCP server through VS Code; configuration does not guarantee live discovery. No global hooks or security settings are changed.

Optional flags: --verify runs regression tests, local feature verification and local MCP smoke; --setup-only installs/configures without starting the dashboard; --port 8081 changes the local port; --workspace C:/Projects/approved-project selects the Copilot workspace. VS Code Terminal > Run Task also offers Start unified dashboard and Setup Copilot and start dashboard.

## 3. Use one dashboard

- Load a synthetic example and click Run request. The catalog shows all 48 current requirements, highlighting only accepted applied features for the selected request. Implemented but unused features are inactive; unimplemented entries are clearly marked. Seven strategies are currently executable.
- Click Compare OFF / ON to run a matched local evidence comparison. No provider calls.
- View original/optimized estimates, estimated saved tokens, reduction percentage, agent, delivery, fidelity, processing time and applied-only feature report.
- Request history refreshes every five seconds; View selects a record, Follow latest resumes automatic selection. History contains metadata only, not raw evidence, and is limited to 200 records.
- Expand developer diagnostics to run all existing fixtures. This is separate from normal request reports.
- Expand benchmark imports to paste the synthetic benchmark JSON or choose the external upstream JSON report. No second dashboard is required. External metrics are separate and never activate ATOF features or inflate its totals.

## 4. Live Copilot test

After approved setup, use Ctrl+Shift+P > MCP: List Servers, start/restart atof-copilot if available, and open a tool-enabled Copilot Chat session. Verify atof_capabilities, atof_analyze, atof_optimize.

Ask in chat: Directly invoke atof_capabilities. Do not use terminal or simulated MCP calls. If unavailable, report ATOF MCP CONNECTION NOT ESTABLISHED.

For a synthetic log, run in PowerShell:

~~~powershell
((1..150 | ForEach-Object { "heartbeat ok" }) + "RuntimeError: database unavailable") | Set-Content .\atof-test.log
~~~

Attach it in chat and ask: Analyze this log using the registered atof_optimize tool with the actual log content as error_output. Do not set feature_override. Preserve the exact error and report request ID and applied features.

Check actual tool output for mcp_tool_result_returned, reduced context and coding.error_context if applied. Match request ID in the dashboard. The tool returns a candidate, not proof of model consumption.

## 5. Other agents

Use the same engine with each approved MCP client. For Codex IDE Chat or Claude configure the installed virtual-environment Python executable with args -m atof.mcp_server --agent codex (or claude), plus ATOF_ANALYTICS_ENABLED=1. For Copilot in IntelliJ use copilot in its supported MCP configuration. Restart the client and verify direct invocation. No Codex CLI is required. ChatGPT Web needs an approved authenticated remote MCP adapter, not implemented here. Custom apps can call the local REST API; see http://127.0.0.1:8080/docs.

Agent selection on the dashboard does not switch or connect an IDE. Agent-labelled HTTP requests remain observe-only. Actual MCP clients must supply authorized evidence.

## 6. Verification and troubleshooting

Run py -3.11 scripts/start_atof.py --verify --setup-only for local tests. A simple question or irreducible input should have no applied features.

If the MCP tool is missing, check workspace root, workspace trust, organizational MCP access, server output and the active session tool selector. Reload the IDE. Do not add duplicate servers or bypass restrictions. A successful local smoke test does not establish live connectivity.

If a virtual environment is missing, the launcher creates it. If the port is occupied use --port 8081. If history is empty check analytics is enabled for both MCP and dashboard, with the same profile/database. ATOF analytics is opt-in metadata only. Do not commit personal paths or credentials; use authorized evidence and keep the unauthenticated service on loopback.

Token counts are local estimates, not actual provider savings. Actual savings need full workflow usage receipts, repeated matched trials and quality checks. The external upstream compressor is separate pending license review. See [main README](README.md).

## Phase 1 delivery validation

Expand Phase 1 · integration readiness and delivery validation in the same dashboard and run the controlled OFF / ON test. Whole-prompt estimates include framing; native agent/model consumption is not verified. See [Phase 1 guide](docs/PHASE1_INTEGRATION_FOUNDATION.md) for optional approved provider testing and acceptance gates.
