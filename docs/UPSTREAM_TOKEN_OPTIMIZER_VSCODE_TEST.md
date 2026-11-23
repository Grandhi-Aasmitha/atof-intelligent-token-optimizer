# VS Code: real upstream Token Optimizer verification

**This executes original code from a separate \`alexgreensh/token-optimizer\` checkout. It does not copy that repository into ATOF or install agent hooks.**

## Steps (Windows PowerShell)

Open the existing ATOF repository in VS Code on branch \`feature/phase-1-foundation\`:

~~~powershell
git switch feature/phase-1-foundation
git pull origin feature/phase-1-foundation
git clone https://github.com/alexgreensh/token-optimizer.git ..\token-optimizer
~~~

Clone only once. The repos must be siblings. The upstream repository uses **PolyForm Noncommercial licensing**; review its LICENSE before commercial usage, redistribution or integration.

Choose **Terminal → Run Task → ATOF: Verify Upstream Token Optimizer**.

Or use:

~~~powershell
py -3.11 scripts\test_upstream_token_optimizer.py --upstream ..\token-optimizer --output-dir demo-results
~~~

The runner invokes upstream \`measure.py benchmark --json\`, which loads the **real** \`bash_compress.py\` compressor, then runs the upstream \`git_status_basic\` fixture for an actual before/after text example. It refuses validation-only \`no_compressor\` output.

Inspect:
- VS Code terminal: fixture pass/fail, category names, estimated tokens, actual original/compressed output.
- \`demo-results/token-optimizer-verification.html\`: feature categories and side-by-side output (open in browser).
- \`demo-results/token-optimizer-verification.json\`: machine-readable test results.

**Exit codes:** 0 = full success; 1 = genuine fixture or example failure (reports still written); 2 = missing upstream or invalid results.

A previously shared upstream archive yielded **86/87** passes and one \`grep_with_credential\` ratio failure; it preserved its sensitive marker and therefore did not meet a compression target. Your fresh Git clone may produce different results. Do not hide upstream failures.

### What this proves (and what it does not)

The test proves local source-code execution of the upstream compressor, category-level output reduction and required marker retention on benchmark fixtures. Estimates are a bytes/4 proxy, not model/provider token receipts. It does **not** prove VS Code Copilot is receiving optimized context automatically.

For real agent behavior, follow upstream's [Copilot compatibility notes](https://github.com/alexgreensh/token-optimizer/blob/main/docs/copilot.md) or [Codex integration](https://github.com/alexgreensh/token-optimizer/blob/main/docs/codex.md). Confirm installed hooks actually execute; do not install two overlapping ATOF/Token Optimizer hook systems without reviewing configuration. Actual token savings require matched provider usage and correctness measurements.

Run the ATOF regression suite separately with \`python -m pytest -q\`.
