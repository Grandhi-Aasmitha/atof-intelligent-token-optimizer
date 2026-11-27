# JetBrains ATOF Control Center

Target: IntelliJ Platform 2025.2 (252.*), Java 21. Only platform module dependency; PyCharm, WebStorm and Rider 2025.2 are intended targets, subject to Plugin Verifier and real product tests. Existing plugin ID retained for upgrade.

Start the shared ATOF service on port 8081. Build with Maven and an approved local IntelliJ IDEA 2025.2 installation (JDK 21). This is a custom Maven SDK build, not JetBrains Gradle tooling:
~~~powershell
cd ide/intellij
mvn "-Didea.home=C:\Program Files\JetBrains\IntelliJ IDEA 2025.2" clean verify
~~~
Install the ZIP from target/*-plugin.zip in Settings > Plugins > gear > Install Plugin from Disk. Restart as requested. Open View > Tool Windows > ATOF. ON/OFF uses the shared setting. Open Control Center opens the single web dashboard. JVM property atof.apiUrl may override the local origin; default is http://127.0.0.1:8081. No new dashboard.

ATOF: Ask AI with ATOF is optional, requires an approved provider API credential in the IDE environment (OPENAI_API_KEY or GEMINI_API_KEY), approved model and per-request consent. It does not use or read subscriptions, native AI chat, credential stores, or other editor files. Select authorized text optionally. ATOF optimizes before the plugin-owned provider call. A preparation failure aborts; no raw fallback or retry. No API keys stored by ATOF. Provider usage and actual token savings are not verified. Native Copilot/Codex/Claude/AI Assistant integration remains pending; use explicitly approved MCP client setup where supported. No CLI or organization policy bypass.

See docs/PHASE7_JETBRAINS_INTEGRATION.md.

## Prebuilt packages (recommended for installation)

Use [the prebuilt package guide](../../docs/INSTALL_PREBUILT_PACKAGES.md) and the repository's ATOF installable packages workflow. Download the artifact only after its job succeeds. Local Gradle, Maven and VSCE are not necessary for installing the corresponding prebuilt plugin. The local engine still needs Python. The existing developer build commands are optional for contributors.
