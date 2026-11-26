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

Open the dashboard to view the latest agent-tool request, token estimates and features used. If no approved integration is verified, the page says so. No need to type prompts or select evidence on the dashboard. The catalog expands to all 48 features. History separates developer tests from agent-tool requests; choose a record and View to inspect it. Follow latest restores the default report.

For developer testing only, expand Advanced · Developer diagnostics. Run the automated pre-model OFF / ON check, verify features or import a benchmark there. The manual optimization form has been removed entirely; developers can still use the existing diagnostic API for custom tests. These are not proof of live agent optimization.

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

The dashboard identifies the recorded agent; it does not switch or connect an IDE. Agent-labelled HTTP requests remain observe-only. Actual MCP clients must supply authorized evidence.

## 6. Verification and troubleshooting

Run py -3.11 scripts/start_atof.py --verify --setup-only for local tests. A simple question or irreducible input should have no applied features.

If the MCP tool is missing, check workspace root, workspace trust, organizational MCP access, server output and the active session tool selector. Reload the IDE. Do not add duplicate servers or bypass restrictions. A successful local smoke test does not establish live connectivity.

If a virtual environment is missing, the launcher creates it. If the port is occupied use --port 8081. If history is empty check analytics is enabled for both MCP and dashboard, with the same profile/database. ATOF analytics is opt-in metadata only. Do not commit personal paths or credentials; use authorized evidence and keep the unauthenticated service on loopback.

Token counts are local estimates, not actual provider savings. Actual savings need full workflow usage receipts, repeated matched trials and quality checks. The external upstream compressor is separate pending license review. See [main README](README.md).

## Phase 1 delivery validation

Expand Phase 1 · integration readiness and delivery validation in the same dashboard and run the controlled OFF / ON test. Whole-prompt estimates include framing; native agent/model consumption is not verified. See [Phase 1 guide](docs/PHASE1_INTEGRATION_FOUNDATION.md) for optional approved provider testing and acceptance gates.

See [Phase 2 dashboard guide](docs/PHASE2_REPORT_FIRST_UX.md) for provenance, feature state and test instructions.

## Old dashboard still displayed?

The report-only dashboard shows revision **feature-readiness-v9** in its header.
Use PowerShell in the intended checkout, not its parent or a nested older clone:

~~~powershell
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git pull --ff-only origin feature/phase-1-foundation
py -3.11 scripts/start_atof.py --port 8081
~~~

Open http://127.0.0.1:8081/dashboard. Using a different port avoids the previous server on 8080. The launcher prints the project path, dashboard revision and verified API module path. It refuses an old source file or occupied port rather than terminating unknown processes. Check http://127.0.0.1:8081/health for dashboard_revision=feature-readiness-v9. If the revision is absent, the browser is not reaching the updated server. Stop your own old server with Ctrl+C when convenient. No reset, forced checkout or deletion is needed. If the remote is different, verify the correct repository before pulling.

## Phase 3 automatic feature detection

Use the same dashboard and startup. Under Advanced · Developer diagnostics choose Check automatic feature detection for unforced synthetic OFF/ON checks. No feature selection or evidence entry is required for this check. See [Phase 3 guide](docs/PHASE3_DYNAMIC_DETECTION.md).

## Phase 4 Control Center

Use the same dashboard. ON/OFF persists and applies to updated local HTTP and MCP requests. Preferred environment/agent are preferences, not live connections. Restart existing MCP processes after updating. The single dashboard is report-only; no manual prompt form. See [Phase 4 guide](docs/PHASE4_UNIVERSAL_LOCAL_SERVICE.md).

## Phase 5 agent adapter framework

The same Control Center and dashboard now report owned API preparation separately from tests and explicit MCP requests. OpenAI API and Gemini API adapters are for applications that own their model inputs, not browser subscriptions. No extra setup for dashboard monitoring. See [Phase 5 guide](docs/PHASE5_AGENT_ADAPTERS.md) for the SDK and API contract. Existing MCP clients should restart after updating.

## Phase 6 VS Code extension

Start the existing service on 8081. Build/install the VSIX from ide/vscode using the approved VSCE tool. The ATOF status bar opens the same dashboard; ATOF: Toggle Optimization controls the shared switch. ATOF: Ask AI with ATOF uses a separate approved model request, with optional selected editor text. Optional Copilot MCP registration is separate; do not duplicate existing configuration. See [Phase 6 guide](docs/PHASE6_VSCODE_INTEGRATION.md). No normal-chat interception is claimed.

## Phase 7 JetBrains plugin

Build/install the plugin from ide/intellij using approved Gradle and JDK 21. Open the ATOF tool window for the shared ON/OFF switch and dashboard shortcut. Optional Ask AI uses approved provider API credentials, not native subscriptions. See [Phase 7 guide](docs/PHASE7_JETBRAINS_INTEGRATION.md).

## Phase 8 Eclipse plugin

Start the same service on 8081. Build in ide/eclipse using approved Maven and JDK 21, install the p2 repository through Eclipse Help > Install New Software. See [Phase 8 guide](docs/PHASE8_ECLIPSE_INTEGRATION.md). For VS Code, the VSIX is generated separately by npm run package in ide/vscode; a missing VSIX means packaging has not completed. The single dashboard remains unchanged in purpose.

## Phase 9 browser extension

Load ide/browser as an unpacked extension only where approved, or open the existing dashboard directly. The optional browser AI client is disabled by default and requires approved API configuration and consent. See [Phase 9 guide](docs/PHASE9_BROWSER_INTEGRATION.md). No native website interception or additional reporting dashboard.

## Phase 10 feature readiness

The same dashboard separates text engines, structured candidate implementations, controls and runtime-required features. Under Advanced, Verify structured optimizers runs offline checks. See [Phase 10 contract](docs/PHASE10_FEATURE_IMPLEMENTATION.md); normal native clients do not automatically supply the new structured evidence. No verified provider savings claim.

## Prebuilt packages (recommended for installation)

Use [the prebuilt package guide](docs/INSTALL_PREBUILT_PACKAGES.md) and the repository's ATOF installable packages workflow. Download the artifact only after its job succeeds. Local Gradle, Maven and VSCE are not necessary for installing the corresponding prebuilt plugin. The local engine still needs Python. The existing developer build commands are optional for contributors.
