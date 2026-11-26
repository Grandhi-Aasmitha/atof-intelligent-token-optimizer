# ATOF for Eclipse

Requires Eclipse 2025-12 (4.38) baseline and JDK 21. Build with approved Maven 3.9.9+ and Tycho 5.0.4, using the pinned Eclipse release p2 repository. No build or install automatically changes native assistant configuration.

Start the shared service from the repository root:
~~~powershell
py -3.11 scripts/start_atof.py --port 8081
~~~
Build from another terminal:
~~~powershell
cd ide/eclipse
mvn clean verify
~~~
The expected p2 installation site is dev.atof.eclipse.repository/target/repository. In Eclipse: Help > Install New Software > Add > Local, select that directory, choose ATOF Control Center, approve installation and restart. Builds and unsigned plugin installation must follow organization policy. Do not disable security checks. If dependencies are needed, use the approved Eclipse 2025-12 repository. Build and runtime verification are required before distribution.

Open Window > Show View > Other > ATOF > ATOF Control Center. ON/OFF changes the same settings as VS Code and IntelliJ. Open Control Center opens the existing dashboard. Optional JVM property -Datof.apiUrl=http://127.0.0.1:8081 (local only). The view does not start the backend.

Optional Ask AI buttons use approved OPENAI_API_KEY or GEMINI_API_KEY in Eclipse's environment, a model ID and explicit consent. Only the task and current editor selection are prepared locally. No automatic file reads or chat interception. No key stored or transmitted to ATOF. A preparation failure aborts before provider submission; no automatic retry. Cancelling after submission may not stop provider charges. Ordinary Copilot/Eclipse chat remains unchanged; approved explicit MCP tools are available via the existing stdio server where the installed client permits. Do not duplicate a configured server or bypass policy.

See docs/PHASE8_ECLIPSE_INTEGRATION.md.

## Prebuilt packages (recommended for installation)

Use [the prebuilt package guide](../../docs/INSTALL_PREBUILT_PACKAGES.md) and the repository's ATOF installable packages workflow. Download the artifact only after its job succeeds. Local Gradle, Maven and VSCE are not necessary for installing the corresponding prebuilt plugin. The local engine still needs Python. The existing developer build commands are optional for contributors.
