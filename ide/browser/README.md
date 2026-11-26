# ATOF browser shortcut (Chrome / Edge)

Start the same ATOF service on port 8081. With organization approval, use chrome://extensions or edge://extensions > Developer mode > Load unpacked, selecting ide/browser. Pin the extension if desired. If extension installation is restricted, open http://127.0.0.1:8081/dashboard directly; do not bypass policy. No extension permissions or website access are requested. It provides shortcuts to the one Control Center and optional browser-owned AI client. No native chat interception.

The optional client is off by default. Only enable approved provider APIs as documented in docs/PHASE9_BROWSER_INTEGRATION.md. It is not a replacement for ChatGPT/Claude/Gemini/Copilot web subscriptions. No provider key in browser extension or web page. Full Chrome/Edge installation and paid API testing remain acceptance gates.

## Prebuilt packages (recommended for installation)

Use [the prebuilt package guide](../../docs/INSTALL_PREBUILT_PACKAGES.md) and the repository's ATOF installable packages workflow. Download the artifact only after its job succeeds. Local Gradle, Maven and VSCE are not necessary for installing the corresponding prebuilt plugin. The local engine still needs Python. The existing developer build commands are optional for contributors.
