# Phase 7 — JetBrains integration

The existing plugin is upgraded in place, retaining its ID. Uses IntelliJ Platform APIs only, 2025.2 baseline with 252.* compatibility range. Other JetBrains products require verifier and runtime tests. No product-specific Java PSI dependency.

~~~mermaid
flowchart TD
 A[JetBrains tool window] --> B[Shared local control API]
 C[Explicit Ask AI action plus selected text] --> D[JetBrains owned preparation adapter]
 D --> E[Shared ON/OFF and dynamic optimizer]
 E --> F[One prepared input]
 F --> G[Approved provider API after consent]
 G --> H[Answer shown in IDE]
 E --> I[Existing web dashboard]
~~~

One local service, status and controls in the IDE; single reporting dashboard. Tool window polling is metadata-only and stops on disposal. HTTP uses loopback origin and no redirect. Selected text is the only optional evidence. Conservative detection routes error/test/diff or generic context. No file scanning. The explicit local candidate action sends nothing to a provider.

Plugin-owned single-turn AI request uses fixed OpenAI Responses or Gemini generateContent endpoint, approved model ID and environment key, with explicit consent. No credential enters the local API, no provider calls by the Python service, no user-supplied provider URL, no automatic retry or silent raw fallback. Java request preparation checks task identity, expected adapter, fidelity, policy and monotonic full-input estimates. Cancellation can stop before submission; a request already submitted may incur charges. Responses are held in memory and displayed. Prepared input history is metadata only, not proof of provider consumption. No native AI assistant interception.

Build with approved Gradle and JDK 21: gradle test buildPlugin in ide/intellij. Install ZIP from build/distributions. Plugin Verifier must be run against the intended JetBrains builds before distribution. Official platform docs: https://plugins.jetbrains.com/docs/intellij/plugin-compatibility.html and https://plugins.jetbrains.com/docs/intellij/tool-windows.html. Provider API docs: https://developers.openai.com/api/reference/resources/responses and https://ai.google.dev/api/generate-content.

Tests: JUnit protocol tests for classification, origin allowlist, original fallback, prepared input validation, one provider input and fixed endpoint. Python endpoint tests for ON/OFF, native denial and accurate dashboard status. Run py -3.11 scripts/start_atof.py --verify --port 8081 for regression. Test real IDE with synthetic text first and compare matched OFF/ON using an authorized model; verify response quality and consumption separately. Native Copilot/Codex/Claude/AI Assistant remains unverified. Phase 8 Eclipse, Phase 9 Web, Phase 10 remaining optimizers, Phase 11 validation, Phase 12 installer.
