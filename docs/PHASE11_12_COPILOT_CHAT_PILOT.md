# Phase 11–12 Copilot Chat pilot (partial implementation)
This update contributes a native VS Code language model tool and optional custom agent, plus automatically applicable instructions on compatible versions. It does not intercept the original Copilot prompt or guarantee tool selection. The tool can reduce source evidence before a subsequent model turn, not before the first model call. Provider usage is unavailable. No live IDE acceptance is claimed.

## Run
1. Pull feature/phase-1-foundation. Start the local service using python scripts/start_atof.py --port 8081. Keep it running.
2. In ide/vscode run npm run check, npm test, and npx @vscode/vsce package --no-dependencies. Install the new 0.9.0 VSIX and reload VS Code. Use a current VS Code/Copilot version supporting contributed chat instructions and agents.
3. Open a trusted local single-folder Food Express workspace. Enable ATOF in the control center; enable the ATOF source tool in Copilot Agent mode's tools list and approve tool use under your organization policy. No separate Ask AI command required. If ordinary agent does not select it, select the bundled ATOF agent once.
4. Ask a targeted question about an existing file and function without attaching its entire source. Example: Explain only calculate_total in src/cart.py (adjust path). Observe tool invocation and dashboard transport vscode_chat_tool. If absent, check tool availability, policy, instructions and model choice. Explicit #atofContext is a diagnostic, not evidence of automatic selection.
5. Repeat in a new conversation with ATOF OFF. Normal tools should work; no ATOF transformation. Re-enable and repeat. Compare response correctness and local estimates; never label these provider savings.
6. Run python -m pytest tests/test_vscode_chat_integration.py and the full regression suite. The tool rejects remote/untrusted workspaces, multi-root workspaces, sensitive paths and large or non-source files; path checks are not a full secrets scan. Approve only authorized files. It reads saved disk content, not unsaved edits.
7. IntelliJ and complete Phase 11/12 release gates remain outstanding; do not claim production readiness.
