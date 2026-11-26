# ATOF Configuration and User Guide

## 1. What is ATOF?
ATOF evaluates authorized evidence, dynamically selects registered optimizers, validates candidates and reports only applied features. It does not automatically intercept every AI prompt.

## 2. Prerequisites
Approved Git, Python 3.11+, VS Code, repository access and an approved MCP-capable assistant. Use synthetic or authorized data. No API key or Codex CLI is required for local tests.

## 3. Install on Windows
Open PowerShell in your projects directory.
~~~powershell
git clone 
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
~~~
Open the cloned folder in VS Code. Existing users should check git remote -v and git status, confirm the correct origin and branch, and run git pull --ff-only origin feature/phase-1-foundation instead of cloning again.

## 4. Verify installation
~~~powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m atof.verify_platform
& .\.venv\Scripts\python.exe -m atof.mcp_smoke --agent all
~~~
Expect regression tests, seven optimizer fixtures and three local MCP configurations to pass. Local MCP smoke is not proof of live agent connectivity.

## 5. Start dashboard
~~~powershell
$env:ATOF_ANALYTICS_ENABLED = "1"
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --host 127.0.0.1 --port 8080
~~~
Keep this terminal running. Open http://127.0.0.1:8080/dashboard. Keep the unauthenticated API on loopback. In another terminal run Invoke-RestMethod http://127.0.0.1:8080/health. Use the developer diagnostics feature verification panel for offline tests.

## 6. Configure Copilot in VS Code
From another terminal at the ATOF root:
~~~powershell
& .\.venv\Scripts\python.exe -m atof.mcp_setup --agent copilot --write-vscode --workspace .
~~~
For another approved project replace the dot with its absolute workspace path. Review .vscode/mcp.json, preserve other servers and add analytics env to the ATOF entry. Replace the example path with your actual Python path:
~~~json
{
  "servers": {
    "atof-copilot": {
      "type": "stdio",
      "command": "C:/Projects/atof-intelligent-token-optimizer/.venv/Scripts/python.exe",
      "args": ["-m", "atof.mcp_server", "--agent", "copilot"],
      "env": {"ATOF_ANALYTICS_ENABLED": "1"}
    }
  }
}
~~~
Save. Ctrl+Shift+P > MCP: List Servers > select ATOF > start/restart if available. Approve only if permitted. Open a tool-enabled Copilot Chat session and check for atof_capabilities, atof_analyze and atof_optimize. The IDE launches the server; do not type its name into PowerShell. Enable analytics in both MCP and dashboard processes using the same user profile/database.

## 7. Verify live connection
Paste in Copilot Chat:
> Directly invoke atof_capabilities. Do not use terminal commands, scripts or simulated MCP calls. If unavailable, report ATOF MCP CONNECTION NOT ESTABLISHED.

Inspect the actual tool trace. A terminal smoke test is not a substitute.

## 8. First optimization
~~~powershell
((1..150 | ForEach-Object { "heartbeat ok" }) + "RuntimeError: database unavailable") | Set-Content .\atof-test.log
~~~
Attach the log in chat:
> Analyze the attached log. Directly invoke atof_optimize with the task and actual log content as error_output. Do not set feature_override. Use the returned candidate, preserve the exact error and report request ID, estimated before/after tokens and only applied features. Do not modify files or use a terminal fallback.

Expect coding.error_context if a safe reduction is accepted. Inspect optimized_context, report.executed_features, fidelity_status and mcp_tool_result_returned delivery. Refresh dashboard history and match request ID. Tool delivery is not proof of model consumption.

## 9. Daily usage
Ask the assistant to use ATOF on authorized evidence without forcing a feature. Supply files (path/content) for source or repository tasks, diff for changes, test_output for test logs, error_output for errors, context for general text and tool_output for command output. No applied features is valid when no safe reduction exists. Normal reports hide unused features; diagnostics are separate.

## 10. Compare OFF and ON
With dashboard running:
~~~powershell
$body = @{
    task = "Identify the root cause"
    error_output = ((1..150 | ForEach-Object { "heartbeat ok" }) + "RuntimeError: database unavailable") -join [Environment]::NewLine
    agent = "custom_api"
    optimization_enabled = $false
}
$off = Invoke-RestMethod -Uri http://127.0.0.1:8080/v1/optimize -Method Post -ContentType application/json -Body ($body | ConvertTo-Json)
$body.optimization_enabled = $true
$on = Invoke-RestMethod -Uri http://127.0.0.1:8080/v1/optimize -Method Post -ContentType application/json -Body ($body | ConvertTo-Json)
$off.report | ConvertTo-Json -Depth 10
$on.report | ConvertTo-Json -Depth 10
$on.optimized_context
~~~
OFF should return no applied features or candidate. ON should reduce evidence and preserve the error. Null OFF after-count is not zero; use original estimate as baseline.

~~~powershell
& .\.venv\Scripts\python.exe -m atof.benchmark_cli --provider synthetic --require-term RuntimeError
~~~
Paste benchmark JSON into the dashboard comparison panel. Capture original/optimized estimates, reduction, features, fidelity, duration and delivery. Reduction percentage = (original - optimized) / original × 100. Synthetic estimates are not actual provider savings. For real comparisons repeat matched OFF/ON and ON/OFF trials, review quality and capture full workflow usage including tool overhead. IDE provider savings remain unverified.

## 11. Other clients
| Client | Setup |
| --- | --- |
| Copilot IntelliJ | If supported by installed plugin, configure the same stdio executable, args and env in its approved MCP settings. |
| Codex IDE Chat | Use approved IDE MCP settings or existing TOML; agent codex. No CLI needed. |
| Claude Code | Use its supported MCP settings with agent claude. |
| ChatGPT Web | Secure remote MCP integration requires additional development and approval. Local stdio cannot connect directly. |
| Custom applications | Local REST API /v1/optimize; see http://127.0.0.1:8080/docs. |

Example Codex TOML (merge and replace path):
~~~toml
[mcp_servers.atof]
command = "C:/Projects/atof-intelligent-token-optimizer/.venv/Scripts/python.exe"
args = ["-m", "atof.mcp_server", "--agent", "codex"]
[mcp_servers.atof.env]
ATOF_ANALYTICS_ENABLED = "1"
~~~
Repeat direct capability and log tests per client. Copilot reports do not currently distinguish IDEs.

## 12. Troubleshooting
| Problem | Action |
| --- | --- |
| Unexpected token -m | Use PowerShell & before executable. |
| atof-copilot not recognized | Server name is not a terminal command. |
| Module not found | Reinstall using the same Python as MCP. |
| Duplicate entry | Keep one ATOF entry and preserve other servers. |
| Local smoke passes but tools missing | Check workspace root, trust, MCP access policy, server logs, session tools and client version. Reload and retest. Follow approved client configuration UI; destinations vary. |
| Dashboard empty | Enable analytics in both processes, restart MCP, check shared database/profile and refresh. |
| Port busy | Stop your previous ATOF instance or choose another loopback port. |
| No features applied | Check evidence field and content; safe no-reduction is valid. |
| Provider savings unavailable | Expected without verified provider receipts. |

Do not bypass organizational restrictions, expose the unauthenticated API, commit secrets or personal absolute-path configuration, or send restricted data. Analytics stores local metadata rather than raw evidence; client/provider retention policies still apply.

## 13. Checklist
- [ ] Install and pass regression tests.
- [ ] Pass feature verification and local MCP smoke.
- [ ] Start dashboard and verify health.
- [ ] Invoke MCP tools directly in real client.
- [ ] Verify reduced evidence, fidelity and applied-only report.
- [ ] Match dashboard request ID.
- [ ] Compare OFF/ON and review quality.
- [ ] Repeat for each approved client.

Stop dashboard with Ctrl+C and stop/disable MCP in IDE. Remove only the ATOF entry to uninstall integration. See [main README](README.md) and [platform design](docs/GENERIC_PLATFORM.md). External token-optimizer is not required or integrated; license review remains pending.
