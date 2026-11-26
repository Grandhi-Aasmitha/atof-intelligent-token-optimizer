# Phase 1 — Cross-agent integration feasibility

This is the new cross-platform roadmap Phase 1, not a replacement of the earlier Phase 1–8 optimization work.

## Scope and contract
All 48 catalog features remain in scope. Existing engines and explicit MCP/HTTP contracts remain intact. This phase adds a trusted in-process Receiver interface, a controlled adapter that owns final request assembly, exact-payload receipt checks, and a common metadata-only report. The request must be explicitly authorized and use the existing custom_api agent label. External callers cannot obtain a native-agent replacement capability by changing an agent string. No hooks, proxy interception, CLI installation or corporate policy changes.

The controlled adapter preserves the task exactly, composes authorized evidence, calls the generic engine before delivery, rejects nonreducing or partially rejected candidates, and passes only the accepted candidate or original fallback to the receiver. JSON framing is included in full-prompt estimates; context estimates remain separately comparable in the existing dashboard. A downstream failure is not retried automatically. No delivered reduction is claimed for an unconfirmed receipt. Each arm records once after delivery when analytics is enabled.

## One dashboard; one startup
~~~powershell
py -3.11 scripts/start_atof.py --verify
~~~
Open http://127.0.0.1:8080/dashboard and expand Phase 1 · integration readiness and delivery validation. Click Run pre-model OFF / ON verification. This runs a fixed synthetic example using the offline receiver, shows whole-prompt estimates, and records the two request IDs in the existing history. The result is not evidence of a live IDE or provider call.

Optional standalone offline check:
~~~powershell
& .\.venv\Scripts\python.exe -m atof.premodel
~~~

Optional controlled real provider trial, only with approved credentials and explicit acceptance of potentially billed requests:
~~~powershell
& .\.venv\Scripts\python.exe -m atof.premodel --provider openai --model YOUR_APPROVED_MODEL --accept-paid-calls
~~~
Credentials must be supplied securely via the existing OPENAI_API_KEY environment setting; Gemini uses GEMINI_API_KEY with --provider gemini. No Codex CLI or subscription credential extraction. Repeat with --order BA and evaluate quality and all usage receipts. Provider observations show the controlled call, not a native Copilot/ChatGPT session or causal verified savings. Analytics remains opt-in for standalone commands.

## Capability gates
| Integration | Current gate |
| --- | --- |
| Local controlled receiver | Automated synthetic payload verification |
| Approved provider API | Optional controlled real call and receipt review |
| IntelliJ Copilot / JetBrains AI | Approved runtime-specific capture and replacement proof pending |
| VS Code Copilot / Codex / Claude | Approved runtime-specific capture and replacement proof pending |
| Existing MCP | Explicit candidate only; no automatic replacement claim |
| ChatGPT Web / other agents | Supported remote adapter and evidence-delivery proof pending |

For each actual native runtime, record agent and IDE versions, approved integration point, actual downstream payload evidence, OFF/ON matched trials, preservation of task and necessary information, and provider usage when exposed. If only a candidate is returned or the model saw the raw evidence first, do not mark pre-model replacement verified. A simulated receiver is an integration harness, not a model.

## Acceptance gates
Unit: authorization, agent-label restriction, exact task preservation, no-reduction fallback, bad receipt, delivery error, AB/BA.
Integration: captured downstream payload differs only in evidence; required error remains, original noise is absent from optimized delivery; API history has exactly two arms, no raw evidence.
Optimization: full submitted prompt estimates decrease after framing, feature list comes from accepted transformations only.
Dashboard: same page, selected report and integration inventory, no new dashboard.
Regression: run all existing pytest tests and verify_platform and mcp_smoke.
Live: at least one approved genuine model/agent workflow with delivery proof and quality validation is required before declaring the live feasibility gate complete.

No new optimization feature is marked implemented by this phase. The full 48-feature roadmap is unchanged. Do not advance the live-integration gate based on synthetic results alone.
