# Phase 8 — Eclipse integration

One service and one dashboard. Eclipse 2025-12 (4.38) baseline, JDK 21, Maven 3.9.9+, Tycho 5.0.4. Native SWT workbench view with metadata-only polling and disposal. No dependency on private Copilot APIs. p2 feature/repository packaging, not VSIX.

~~~mermaid
flowchart TD
 A[Eclipse ATOF view] --> B[Shared local control API]
 C[Explicit Ask AI plus selected text] --> D[Eclipse owned adapter]
 D --> E[Global ON/OFF and dynamic engine]
 E --> F[One prepared input]
 F --> G[Approved OpenAI or Gemini API]
 G --> H[Answer in Eclipse]
 E --> I[Shared dashboard: preparation estimates]
 J[Optional approved native Copilot MCP] --> E
~~~

Supported native Eclipse extensions: https://help.eclipse.org/latest/topic/org.eclipse.platform.doc.isv/reference/extension-points/org_eclipse_ui_views.html. Tycho p2 packaging: https://tycho.eclipseprojects.io/doc/latest/PackagingTypes.html. GitHub Copilot MCP support includes Eclipse: https://docs.github.com/en/copilot/concepts/customizations/mcp. This does not establish native request replacement.

The same Python engine, control settings and analytics are reused. The plain Java transport and protocol are derived from JetBrains phase 7, with a parity test to prevent drift until a shared Java library is extracted. No separate optimizer. The view polls only controls, stops polling when disposed, and runs blocking requests in background Eclipse Jobs. Request action reads current selected text only and asks consent before preparation/submission. Provider endpoint fixed, approved credential and model required, no arbitrary URLs, no retry or silent fallback. Global OFF preserves original task/evidence. ATOF reports preparation only, not provider consumption. Native AI assistant subscriptions cannot be accessed by this plugin.

Existing explicit MCP server may be configured via the installed Copilot client's official UI where approved. No automatic changes to MCP or security settings. Configure the same installed Python environment, agent copilot; optional metadata analytics uses ATOF_ANALYTICS_ENABLED=1. Tool results are candidates and not proof of pre-model replacement.

Build: mvn clean verify in ide/eclipse, then install the p2 local repository directory per README. Validate target platform resolution, SWT view lifecycle, policy synchronization, explicit request, response quality and matched OFF/ON on a real approved Eclipse instance. Python tests cover the adapter, policy, original preservation, native denial, provenance, protocol parity and XML. No live model requests in tests. Full plugin build, p2 install and provider usage validation are acceptance gates.

Phase 9 browser integration where technically supported; Phase 10 complete all 48 feature implementations; Phase 11 cross-platform validation; Phase 12 installer.
