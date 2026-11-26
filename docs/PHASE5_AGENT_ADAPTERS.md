# Phase 5 — Universal agent adapter framework

One registered capability inventory drives the common engine, MCP tool dispatch, supported agent information and dashboard. Agent preferences never grant a transport capability.

~~~mermaid
flowchart TD
 A[Approved client or owned application] --> B[Registered adapter]
 B --> C[Shared local ON/OFF policy]
 C --> D[Dynamic optimizer selection and fidelity checks]
 D --> E[Candidate or original fallback]
 E --> F[Explicit MCP tool result]
 E --> G[Owned input preparation]
 G --> H[Approved caller submits to provider]
 F --> R[Single dashboard and metadata history]
 G --> R
 H --> R
~~~

| Adapter | Implemented boundary |
| --- | --- |
| mcp_copilot / mcp_codex / mcp_claude | Explicit configured local MCP tool; not native replacement |
| owned_local / openai_api / gemini_api | Prepare one owned structured single-turn input before caller submission |
| local_api | Existing explicit candidate API |
| IDE and browser paths | Inventory only, unverified; cannot invoke owned preparation |

No native browser or IDE interception, no Codex CLI, no credentials collected by ATOF, no arbitrary destination URL or forwarding route. Provider APIs are distinct from ChatGPT/Gemini subscriptions. Future integrations should register an explicit capability and use the same engine rather than rely on agent labels.

## SDK and local API
For an application that owns its downstream model request:
~~~python
from atof.adapters import AgentAdapter
from atof.models import OptimizeRequest

request = OptimizeRequest(task="Diagnose the error", error_output=authorized_log)
adapter = AgentAdapter("openai_api")  # or gemini_api, owned_local
prepared = adapter.prepare(request)
# Submit only prepared.prompt to your existing approved provider client.
# Alternatively, use dispatch instead of prepare to record one submission attempt:
# result = adapter.dispatch(request, approved_sender, authorized=True)
~~~
The approved sender accepts a single string and returns its response; credentials and the provider client's configuration remain with the application. Disable automatic client retries if the application requires one network attempt; ATOF itself invokes the callback once. OpenAI Responses and Gemini API clients can consume a prepared text input (see https://platform.openai.com/docs/api-reference/responses and https://ai.google.dev/gemini-api/docs). No external request is made by prepare. A returned sender response is not a verified usage receipt. Phase 1 controlled provider tests remain separate.

GET /v1/adapters lists capabilities. POST /v1/adapters/openai_api/prepare (also gemini_api and owned_local) accepts OptimizeRequest with X-ATOF-Adapter: 1 on loopback. The response includes exactly one prepared input, a candidate report and full assembled input estimates. Caller must preserve original input on integration failure; no automatic retry. Global OFF and per-request OFF return original task and evidence, with zero full-input reduction. Unsupported adapters fail closed. Prompt text is returned only to caller, never stored in history.

## Verification
Run py -3.11 scripts/start_atof.py --verify --port 8081. Tests cover each explicit MCP adapter, each owned preparation path, shared OFF/ON, exact task, reduced evidence, no false native claims, sender failure/no retry, endpoint authorization and dashboard provenance. No live provider calls in tests. All 48 remain in scope; seven executable. Phase 6 is VS Code integration; Phase 7 JetBrains; Phase 8 Eclipse; Phase 9 browser where approved.
