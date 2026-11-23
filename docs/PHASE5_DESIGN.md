# Phase 5 — Multi-Agent MCP Integration

## Components implemented

- One local MCP stdio server: `python -m atof.mcp_server --agent copilot|codex|claude`.
- Three discoverable tools: `atof_capabilities`, `atof_analyze`, `atof_optimize`.
- JSON-RPC initialize, ping, notifications, tools/list and tools/call.
- Dynamic feature selection and the five existing native engines; conservative stage fidelity checks and API return-only reporting.
- A separate internal `mcp_explicit` transport, so a caller setting `agent=copilot` in HTTP does **not** bypass the agent restrictions.
- Workspace-scoped additive VS Code configuration generator that preserves other MCP servers and refuses conflicting entries.

All input evidence must be explicitly supplied. Paths are labels: ATOF **does not read local source files automatically**. For real source optimization, the agent must retrieve authorized content with its own tools and pass that content in `files[].content`.

## Validate Phase 5 locally

From the existing repo root:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m atof.mcp_smoke --agent all
```

Expect 60 tests and three JSON lines in the smoke output, each with `tools_discovered: 3`, an executed `coding.error_context`, and `delivery: mcp_tool_result_returned`. This is a **local MCP protocol test**, not a test of actual Copilot/Codex/Claude model consumption.

## 1. VS Code GitHub Copilot

The command below adds `atof-copilot` to the selected test workspace's `.vscode/mcp.json` using the installed ATOF Python. Run from the ATOF repo root:

```powershell
$atofPython = (Resolve-Path ".\.venv\Scripts\python.exe").Path
& $atofPython -m atof.mcp_setup --agent copilot --python "$atofPython" --workspace "C:\Users\pekiran\Downloads\ATOF1Test" --write-vscode
```

Check that `ATOF1Test/.vscode/mcp.json` contains:

```json
{
  "servers": {
    "atof-copilot": {
      "type": "stdio",
      "command": "ABSOLUTE_PATH_TO_ATOF_PYTHON",
      "args": ["-m", "atof.mcp_server", "--agent", "copilot"]
    }
  }
}
```

The real config generator fills the absolute Python path automatically. Other pre-existing MCP servers are preserved. Do not commit a machine-specific MCP config blindly; MCP servers run code with your permissions.

1. Open `ATOF1Test` in VS Code.
2. From Command Palette run **MCP: List Servers**. Start `atof-copilot` or inspect its output if it fails.
3. In Copilot Chat select **Agent** mode, open the tool-selection list, enable the three `atof_*` tools and open a fresh chat.
4. Ask: **"Invoke the actual `atof_capabilities` MCP tool. Report which native optimizers are available. Do not invent a tool call."**
5. Next ask it to invoke `atof_optimize` with a synthetic multi-line error log (a hundred or more redundant lines) and `task="Analyze repeated backend failure"`. *Do not provide a filepath alone.* Inspect the tool-call panel for `atof_optimize`.
6. Success requires a real tool invocation and a returned context + report; token-saving claims must remain **unverified**.

## 2. Codex CLI

From the ATOF repo PowerShell terminal:

```powershell
$atofPython = (Resolve-Path ".\.venv\Scripts\python.exe").Path
codex mcp add atof -- "$atofPython" -m atof.mcp_server --agent codex
codex mcp list
```

Restart Codex and ask it to call `atof_capabilities` and then `atof_optimize` with synthetic evidence. The old Codex gateway is **not required** for this explicit MCP workflow. If your installed Codex version differs, consult `codex mcp add --help`.

## 3. Claude Code CLI

From the ATOF repo PowerShell terminal:

```powershell
$atofPython = (Resolve-Path ".\.venv\Scripts\python.exe").Path
claude mcp add --transport stdio atof -- "$atofPython" -m atof.mcp_server --agent claude
claude mcp list
```

Restart Claude Code; invoke `atof_capabilities` and `atof_optimize`, checking the actual tool result and not just the model's narrative.

## Checks and restrictions

- The Python stdio smoke test verifies actual process startup, protocol handshake, tool listing, tool invocation, and response formatting.
- MCP tool arguments cannot spoof agent identity; agent startup config determines the report label, but does not cryptographically authenticate the caller.
- Unsupported or missing evidence yields a safe skip. Input validation failures produce MCP tool errors.
- Ordinary HTTP requests continue to treat direct Codex/Copilot/Claude contexts as unsupported.
- No third-party Token Optimizer source code, actual provider calls, or billed token receipts are present.
- `mcp_tool_result_returned` is **not** provider-model consumption; estimated local token reduction is **not** verified savings.

## Acceptance criteria

- Unit and MCP process tests pass.
- Three tool names appear in VS Code/Codex/Claude MCP tool registry on the actual target machine.
- ATOF tool successfully executes on synthetic evidence, preserving failure anchors and returning an estimated before/after count.
- Report declares provider usage and savings unavailable.
- No confidential enterprise code/logs or secrets are used in smoke testing.
