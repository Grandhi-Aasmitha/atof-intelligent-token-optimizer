# JetBrains ATOF Control Center

Target: IntelliJ Platform 2025.2 (252.*), Java 21. Only platform module dependency; PyCharm, WebStorm and Rider 2025.2 are intended targets, subject to Plugin Verifier and real product tests. Existing plugin ID retained for upgrade.

Start the shared ATOF service on port 8081. Build with an approved Gradle installation compatible with the IntelliJ Platform Gradle Plugin:
~~~powershell
cd ide/intellij
gradle test buildPlugin
~~~
Install the ZIP from build/distributions in Settings > Plugins > gear > Install Plugin from Disk. Restart as requested. Open View > Tool Windows > ATOF. ON/OFF uses the shared setting. Open Control Center opens the single web dashboard. JVM property atof.apiUrl may override the local origin; default is http://127.0.0.1:8081. No new dashboard.

ATOF: Ask AI with ATOF is optional, requires an approved provider API credential in the IDE environment (OPENAI_API_KEY or GEMINI_API_KEY), approved model and per-request consent. It does not use or read subscriptions, native AI chat, credential stores, or other editor files. Select authorized text optionally. ATOF optimizes before the plugin-owned provider call. A preparation failure aborts; no raw fallback or retry. No API keys stored by ATOF. Provider usage and actual token savings are not verified. Native Copilot/Codex/Claude/AI Assistant integration remains pending; use explicitly approved MCP client setup where supported. No CLI or organization policy bypass.

See docs/PHASE7_JETBRAINS_INTEGRATION.md.
