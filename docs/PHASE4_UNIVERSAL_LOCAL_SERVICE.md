# Phase 4 — Universal local ATOF service and Control Center

This follows the approved twelve-phase IDE-independent plan. The existing loopback FastAPI service is the common service for future IDE adapters. One dashboard includes the Control Center, report, feature catalog and history. No manual input form or second dashboard.

~~~mermaid
flowchart TD
 U[Control Center ON/OFF and preferences] --> C[Shared per-user SQLite settings]
 H[Local HTTP or IDE request] --> P[Read policy per request]
 M[Existing local MCP process] --> P
 C --> P
 P -->|ON and supported evidence| E[Shared engine and dynamic detection]
 P -->|OFF or settings error| F[No optimized candidate; caller retains original]
 E --> R[Accepted candidate and applied-only report]
 F --> R
 R --> D[Existing metadata history and dashboard]
~~~

## Contract
GET /v1/control and PUT /v1/control expose strict local settings: enabled, preferred_ide, preferred_agent. PUT requires X-ATOF-Control: 1 and a loopback Host; browser Origin must match. No CORS or remote binding. Preferences are NOT live client selection, installation, detection or verification. Auto means no preferred environment. Future adapters implement actual discovery. The same installed Python package uses ~/.atof/control-v1.sqlite3 by default, independent of analytics; ATOF_CONTROL_DB can override it consistently across processes. Default ON preserves existing behavior; no interception or capture is enabled by that alone. A corrupt/unavailable store disables normal optimization. HTTP/explicit IDE and MCP calls read settings before planning; per-request OFF still wins. Already-running requests use their initial snapshot. An OFF response returns no optimized candidate, not an empty replacement; the caller must retain its original evidence. Explicit controlled validation, synthetic and developer-test endpoints are isolated and may exercise ON/OFF without changing the user's policy. Reports mark the policy used. Old/unupdated MCP processes do not honor this switch until restarted with the new package.

## Startup
Pull the existing feature branch and run:
~~~powershell
py -3.11 scripts/start_atof.py --port 8081
~~~
Open http://127.0.0.1:8081/dashboard. Select preferred IDE/agent or leave Automatic; toggle ON/OFF. The report reflects actual recorded agent requests, not preferences. Use --verify for regression tests; the pytest run uses isolated settings/analytics. Automated checks are not provider token savings.

## Acceptance
Tests cover persistence across processes, HTTP and MCP OFF/ON, request-level OFF, read-only detection, forged source labels, invalid/cross-origin writes, corrupt settings and diagnostics isolation. The service is still local development infrastructure, not a packaged OS background service. Native IDE hooks, centralized routing of every MCP call, Eclipse and browser integrations, verified connections and remaining optimizer implementations are later phases. No automatic interception or full provider savings claim. Full 48-feature scope retained.
