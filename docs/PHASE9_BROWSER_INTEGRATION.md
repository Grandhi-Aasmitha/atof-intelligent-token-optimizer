# Phase 9 — Browser integration

One local service and existing dashboard. Chrome/Edge MV3 permission-free extension provides shortcuts only, with no host permissions, page scripts, cookies, history or session access. Native ChatGPT, Claude, Copilot and Gemini websites are not intercepted. The optional browser-owned API client is a separate actual request interface, never a dashboard test form.

~~~mermaid
flowchart TD
 A[Chrome or Edge shortcut] --> B[Existing Control Center]
 A --> C[Optional local browser AI client]
 C --> D[Same-origin consent and approved provider gate]
 D --> E[Global policy and shared engine]
 E --> F[One prepared input]
 F --> G[Fixed approved API endpoint]
 G --> H[Response in browser]
 E --> B
~~~

## Run
Pull the existing branch; run py -3.11 scripts/start_atof.py --port 8081. Load unpacked ide/browser in an approved browser or just open /dashboard. The shortcut itself has no background service. /browser is the optional AI client.

## Optional API opt-in
Use only approved environment credentials and model IDs. Do not paste secrets into a browser or terminal transcript. In the same PowerShell process used to launch ATOF, set:
~~~powershell
$env:ATOF_BROWSER_API_ENABLED = "1"
$env:ATOF_BROWSER_OPENAI_MODEL = "<approved-model-id>"
# OPENAI_API_KEY must already be supplied via approved secret handling.
# For Gemini, use ATOF_BROWSER_GEMINI_MODEL and GEMINI_API_KEY.
py -3.11 scripts/start_atof.py --port 8081
~~~
The service does not offer external API submission by default. The provider, configured model, explicit request consent and exact local browser Origin are required. Request schema rejects arbitrary URLs, keys, model overrides and extra fields. The provider client is fixed to OpenAI Responses or Gemini generateContent, with bounded response size, no redirects and no application retry. No credential or raw prompt stored by ATOF. Provider retention terms still apply; OpenAI store=false is not a universal zero-retention promise. ATOF uses normal network configuration, not policy bypass. The existing /v1/adapters/{id}/prepare endpoint still only prepares input; new /v1/browser/ask explicitly submits if opted in. No remote bind or CORS exceptions. Disable by unsetting ATOF_BROWSER_API_ENABLED and restarting. A request in flight may incur charges.

## Acceptance
Tests cover opt-in gate, consent, same-origin protection, both provider mock paths, global OFF, fixed single input, failure/no retry, metadata-only reporting and permission-free manifest. Browser UI displays plain text only; no raw HTML injection or localStorage. Browser setup and provider tests on real approved environments remain pending. Existing seven executable optimizers and 48-feature scope unchanged. Native web chat integration is unverified, not implemented as transparent interception.

Official references: https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions, https://learn.microsoft.com/en-us/microsoft-edge/extensions/, https://developers.openai.com/api/reference/resources/responses/methods/create, https://ai.google.dev/api/generate-content.

Next: Phase 10 complete all 48 features, Phase 11 cross-platform verification, Phase 12 packaging.
