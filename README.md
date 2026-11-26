# ATOF Next Generation — Generic Platform Foundation

ATOF provides **explicit IDE text optimization** and **controlled A/B provider benchmarks** on top of the Phase 1–6 foundation.

Existing features: 48 registered requirements, seven native optimization strategies, a capability-aware planner, fidelity checks, local dashboard, and explicit MCP tools for Codex/Copilot/Claude.

## Quick start (Windows)

~~~powershell
py -3.11 scripts/start_atof.py
~~~

For approved Copilot setup use py -3.11 scripts/start_atof.py --copilot. The launcher creates the virtual environment, installs dependencies and starts the single dashboard. Open http://127.0.0.1:8080/dashboard. Use --verify for local validation or --setup-only to skip launch.

See [new user guide](README_ATOF_CONFIGURATION.md) for cloning, use and troubleshooting. The dashboard includes all catalog features, applied-only reports, request history, local OFF/ON comparison, diagnostics and benchmark import.

## Phase 7 — IDE source integrations

- VS Code source extension under ide/vscode: open as extension project, press F5 (Extension Development Host). Select text and use **ATOF: Optimize Selection**, choose evidence type, and explicitly approve sending to local ATOF.
- IntelliJ IDEA source plugin under ide/intellij: open as Gradle project with JDK 21 and compatible IntelliJ Platform, run Gradle runIde, select synthetic text, right-click **ATOF: Optimize Selection**. Gradle plugin build has not been verified here.
- Neither extension intercepts internal LLM requests or automatically changes editor files. It returns an explicit optimization candidate.

## Phase 8 — Provider-measured ON/OFF benchmarking

**Free offline test:**

~~~powershell
& .\.venv\Scripts\python.exe -m atof.benchmark_cli --provider synthetic --require-term "Synthetic reply"
~~~

Expected: two synthetic arms; reported context reduction, but provider_usage_measured=false and provider_savings_verified=false.

**Optional real OpenAI (two potentially billed calls):**

~~~powershell
$env:OPENAI_API_KEY = "<secure key outside Git>"
& .\.venv\Scripts\python.exe -m atof.benchmark_cli --provider openai --model YOUR_SUPPORTED_MODEL --accept-paid-calls --require-term RuntimeError
~~~

**Optional real Gemini:**

~~~powershell
$env:GEMINI_API_KEY = "<secure key outside Git>"
& .\.venv\Scripts\python.exe -m atof.benchmark_cli --provider gemini --model YOUR_SUPPORTED_MODEL --accept-paid-calls --require-term RuntimeError
~~~

Never commit credentials. Test with synthetic/non-sensitive data. Model provider receipts are not equivalent to causal savings proven through repeated matched AB/BA studies. Paste benchmark JSON into the dashboard's provider comparison pane.

## Limitations

- The development API is unauthenticated: bind only to 127.0.0.1.
- VS Code and IntelliJ **do not** transparently intercept Copilot, Claude, Codex, or JetBrains AI requests. Explicit MCP tools remain separate.
- No actual provider calls were made during offline tests.
- The third-party Token Optimizer implementation has **not** been integrated; its license and compatibility must be resolved first.
- The original/optimized sizes are local estimates except for live provider API responses where usage receipts are returned.

## Generic platform upgrade

The planner now discovers plugin metadata from the engine registry. Generic context and tool output support reversible repeated-line encoding. The existing task prompt is not rewritten. Seven modules are executable; the other feature IDs remain a roadmap, not active optimizers. New plugins require a fidelity validator and authorized evidence.

Run `python -m atof.verify_platform` or use **Run feature verification** in the dashboard. Each synthetic fixture runs OFF and ON, with no model calls. Enable analytics before launch to see both arms in history. See [Generic platform onboarding and verification](docs/GENERIC_PLATFORM.md).

## New user setup

Start with the [ATOF Configuration and User Guide](README_ATOF_CONFIGURATION.md) for installation, agent setup, daily usage and end-to-end validation.

## Cross-platform roadmap — Phase 1

See [integration foundation and acceptance gates](docs/PHASE1_INTEGRATION_FOUNDATION.md). Start with `py -3.11 scripts/start_atof.py --verify`. The unified dashboard includes an offline controlled pre-model delivery verification. Live IDE integration remains subject to runtime validation.

## Cross-platform roadmap — Phase 2

[Report-first dashboard and feature-state contract](docs/PHASE2_REPORT_FIRST_UX.md). One dashboard, tests under Advanced, separate provenance for historical and agent-tool records. Native live delivery remains unverified.

## Revised roadmap — Phase 3

[Dynamic feature detection](docs/PHASE3_DYNAMIC_DETECTION.md): registered plugin applicability and relevance, read-only detection API, unforced OFF/ON fixture checks. No new dashboard or manual form. All 48 remain in scope.

## Revised roadmap — Phase 4

[Universal local service and Control Center](docs/PHASE4_UNIVERSAL_LOCAL_SERVICE.md). Persistent shared ON/OFF, IDE/agent preferences and one report-only dashboard. Native integration verification remains pending.

## Revised roadmap — Phase 5

[Universal agent adapters](docs/PHASE5_AGENT_ADAPTERS.md). Shared MCP adapters and explicit owned-input preparation for OpenAI/Gemini/custom applications. No native interception or provider savings claim.

## Revised roadmap — Phase 6

[VS Code integration](docs/PHASE6_VSCODE_INTEGRATION.md): status bar, global policy toggle, optional owned model request and opt-in MCP definition. Native agent interception remains unverified.

## Revised roadmap — Phase 7

[JetBrains integration](docs/PHASE7_JETBRAINS_INTEGRATION.md): shared controls, one dashboard, opt-in plugin-owned API request. Native AI assistant interception remains unverified.

## Revised roadmap — Phase 8

[Eclipse integration](docs/PHASE8_ECLIPSE_INTEGRATION.md): native control view, shared policy and optional owned API preparation, Tycho p2 build. Native assistant interception remains unverified.
