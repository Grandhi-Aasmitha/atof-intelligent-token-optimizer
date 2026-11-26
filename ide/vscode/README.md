# ATOF Control Center for VS Code

Install the shared ATOF service once using the repository launcher on port 8081. This extension requires local trusted VS Code 1.105+ and approved access to Copilot models for its optional Ask AI command. No dependency on a provider subscription for basic local controls. Do not install in remote or untrusted workspaces.

- Status bar: click ATOF ON/OFF to open the single dashboard. The status reflects the local policy, not an authenticated AI connection.
- Command Palette: ATOF: Toggle Optimization changes the shared switch.
- Command Palette: ATOF: Ask AI with ATOF sends your task and optional selected text through local preparation first, then submits one user message via the approved VS Code Language Model API. It is a separate single-turn command, not interception of normal chat or automatic repository scanning. Response opens in an untitled editor.
- Optional: ATOF: Configure Optional Copilot MCP registers the user-approved ATOF virtual-environment Python executable using the official extension MCP provider API. Avoid duplicates with an existing workspace MCP entry; approve/start in VS Code. It exposes explicit tools only. Use existing approved configuration for Codex IDE and Claude; the extension does not modify their settings.

For build, use Node.js and an approved installed @vscode/vsce. In this directory run npm run check, npm test, npm run package. Install the generated VSIX using Extensions > Install from VSIX. No policy bypass or automatic dependency downloads. The backend remains a separate local process in this phase. See repository Phase 6 documentation for testing and boundaries.

## Prebuilt packages (recommended for installation)

Use [the prebuilt package guide](../../docs/INSTALL_PREBUILT_PACKAGES.md) and the repository's ATOF installable packages workflow. Download the artifact only after its job succeeds. Local Gradle, Maven and VSCE are not necessary for installing the corresponding prebuilt plugin. The local engine still needs Python. The existing developer build commands are optional for contributors.
