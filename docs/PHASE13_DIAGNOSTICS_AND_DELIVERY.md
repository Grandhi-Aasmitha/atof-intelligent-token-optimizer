# Phase 13 incremental integration repair

Scope: request diagnostics, client-reported owned Copilot response receipts, and source tool regression coverage. Existing native chat boundaries remain unchanged. The 48-feature catalog is not evidence of 48 working optimizers.

## Run on Windows

From the existing development branch, stop the previous ATOF service normally, pull, and reinstall.

```powershell
git switch feature/phase-1-foundation
git pull --ff-only origin feature/phase-1-foundation
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
$env:ATOF_ANALYTICS_ENABLED = "1"
& .\.venv\Scripts\python.exe scripts/start_atof.py --port 8081
```

In another terminal:
```powershell
cd ide/vscode
npm run check
npm test
npx @vscode/vsce package --no-dependencies
```
Install the new VSIX and reload VS Code. Check the dashboard on port 8081.

For ordinary Copilot Agent mode, enable the approved ATOF source tool. Use a targeted task on a trusted, authorized file containing the named function plus many unrelated definitions. If the tool is invoked, inspect its history and feature evaluation. A compact file may not have a safe reduction. Tool selection and model consumption remain unverified. The source endpoint accepts exactly one file, not arbitrary error logs. Use the owned request path or explicit MCP for logs.

For the owned Copilot path, run ATOF: Ask AI with ATOF and explicitly approve the model request with authorized selected evidence. On a completed response the extension records an advisory receipt correlated with the preparation request. This is not a provider receipt, native interception or verified token savings. No model retry is added.

Older records cannot recover missing diagnostic data. Reproduce them. A global OFF result is expected to retain the original evidence.

## Remaining release gates

- Exact cause of the old 211-token request requires its local history.
- Native chat integration and provider usage across agents need real supported client testing; no universal interception is claimed.
- Twelve structured candidates, seven controls and seven text engines are distinct from 22 runtime-required catalog items.
- IntelliJ Maven-only build and actual IDE plugin acceptance are outstanding. No new Gradle dependency introduced.
- CI and local live provider testing must be reviewed before declaring a release ready.
