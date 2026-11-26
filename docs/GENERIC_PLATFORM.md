# ATOF generic platform foundation

## Scope

Seven registered strategies execute: five existing coding modules, generic context and generic tool output. Forty-one other catalog entries are not implemented. Repeated-line encoding uses an explicit count marker followed by the original line; a bounded round-trip validator must recover the exact input before accepting the candidate. The task itself is never rewritten. The budget diagnostic estimates evidence size only and does not truncate evidence or guarantee provider limits.

## Developer onboarding (Windows / VS Code)

Use a company-approved Python 3.11+, Git, VS Code and Copilot Chat installation. Obtain permission to process the chosen evidence. No Codex CLI or external API key is needed for offline validation.

    git clone https://github.com/Grandhi-Aasmitha/atof-intelligent-token-optimizer.git
    cd atof-intelligent-token-optimizer
    git switch feature/phase-1-foundation
    py -3.11 -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
    & .\.venv\Scripts\python.exe -m pytest -q
    & .\.venv\Scripts\python.exe -m atof.verify_platform
    & .\.venv\Scripts\python.exe -m atof.mcp_smoke --agent all

For an existing clone, use git pull --ff-only instead of cloning again.

## Copilot Chat POC (explicit MCP, not transparent interception)

In an approved test workspace, use the installed ATOF Python interpreter:

    & .\.venv\Scripts\python.exe -m atof.mcp_setup --agent copilot --write-vscode --workspace .

Review .vscode/mcp.json and approve the server only if policy permits. Existing conflicting server definitions are not overwritten. Use VS Code MCP server controls to start the server and expose the ATOF tools in Copilot Chat. To enable local metadata collection, add an env object to the ATOF server entry with ATOF_ANALYTICS_ENABLED set to "1", then restart the server. No evidence or prompts are stored by ATOF analytics; IDE/provider policies still apply.

In Copilot Chat use a synthetic fixture and explicitly request the atof_optimize tool with task "Inspect synthetic output" and tool_output containing at least 30 identical lines "worker ready" followed by "ERROR: missing input". Use the actual repeated lines, not the description of the repetition. Inspect the tool-call trace for agent.tool_output and the repeat marker plus the error. Compare with optimization_enabled=false in a separate matched task. The tool result is not proof that the model avoided reading the original evidence. An MCP response also carries report overhead. No direct Copilot billing measurement is implemented.

## Dashboard

    $env:ATOF_ANALYTICS_ENABLED = "1"
    & .\.venv\Scripts\python.exe -m uvicorn atof.api:app --host 127.0.0.1 --port 8080

Open http://127.0.0.1:8080/dashboard. Click Run feature verification. Expect seven successful fixture rows; when analytics is enabled, 14 records are added (7 OFF, 7 ON). Repeat runs add new records. Use the evidence selector and Enable optimization checkbox to test other supplied evidence. Verify request IDs and counts through /v1/analytics/history and /v1/analytics/summary. The history is a bounded window, not lifetime totals. Provider usage remains unavailable.

## Extend the platform

Implement OptimizationEngine.optimize(request) -> EngineResult. Declare a PluginSpec with feature ID, evidence slot, priority, conflicts/dependencies and a validator callable(original, candidate) -> bool. Add the engine to the trusted registry and its catalog entry; add positive, negative, no-reduction and transport tests. A new evidence shape requires a request and composition schema change. No untrusted dynamic plugin loading. Do not claim automatic agent prompt replacement.

## Next milestones

- Establish real Copilot Chat tool invocation and measurable overhead; audit all existing coding fidelity checks.
- Add conservative prompt transformations and budget policies without rewriting instructions or discarding necessary context.
- Add context history/retrieval, caching and provider-aware controls only for clients exposing the required capabilities.
- Import the external benchmark report into a unified dashboard; keep upstream separate pending license review.
- Verify provider-measured savings under approved controlled matched trials. Do not confuse local estimates, explicit tool delivery, or model consumption.

The third-party compressor remains independent. This upgrade does not install hooks, switch the IDE assistant, or change company security settings.

## Applied-feature reporting

Normal HTTP optimization, explicit IDE optimization, MCP `atof_optimize`, console output and analytics history show only accepted, executed optimizers. An analyzed, skipped, rejected, unsupported or disabled feature is not presented as applied. Older stored history is filtered on read; no database deletion or migration is required. If no reducing candidate is accepted, the feature list is empty. Safety and delivery warnings remain separate from feature names.

For explicit diagnostics use `/v1/analyze`, `atof_analyze`, `python -m atof.cli --diagnostics --file examples/sample_request.json`, or the collapsed dashboard developer verification panel. These are planning/test views, not normal execution reports. The planner evaluates registered plugins against the supplied evidence and capabilities; the caller still supplies authorized evidence. No new optimization algorithms were added in this reporting change. Future registered modules require no report-specific changes. File-count eligibility is declared in plugin metadata (`minimum_items`).

## Unified dashboard

Use `py -3.11 scripts/start_atof.py` or `--copilot` for approved workspace configuration. The complete catalog is displayed separately from the applied-only execution report. Import external benchmark JSON into the same dashboard; external results do not contribute to ATOF history. See [user guide](../README_ATOF_CONFIGURATION.md).
