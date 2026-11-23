# ATOF Next Generation — Phases 7 + 8

ATOF provides **explicit IDE text optimization** and **controlled A/B provider benchmarks** on top of the Phase 1–6 foundation.

Existing features: 48 registered requirements, five native optimization strategies, a capability-aware planner, fidelity checks, local dashboard, and explicit MCP tools for Codex/Copilot/Claude.

## Windows developer setup

Run from the existing checkout on the existing branch:

~~~powershell
git switch feature/phase-1-foundation
git pull origin feature/phase-1-foundation
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m atof.mcp_smoke --agent all
& .\.venv\Scripts\python.exe -m atof.benchmark_cli --provider synthetic
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --host 127.0.0.1 --port 8080
~~~

Dashboard: http://127.0.0.1:8080/dashboard
IDE optimization API: POST /v1/ide/optimize

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
