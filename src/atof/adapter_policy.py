"""One allowlisted capability contract; an agent label never proves connection."""
from dataclasses import dataclass, asdict

MCP_AGENTS = ("copilot", "codex", "claude")
AGENTS = ("custom_api", "codex", "copilot", "claude", "chatgpt", "gemini")

@dataclass(frozen=True)
class AdapterSpec:
    id: str
    agent: str
    environment: str
    transport: str
    status: str
    scope: str

SPECS = (
    AdapterSpec("local_api", "custom_api", "Owned application", "http_api", "candidate_only", "Existing explicit candidate API"),
    AdapterSpec("vscode_copilot_model", "copilot", "VS Code Language Model API", "owned_adapter", "owned_preparation", "Extension-owned single-turn input; not native chat interception"),
    AdapterSpec("jetbrains_openai", "chatgpt", "JetBrains plugin-owned OpenAI API", "owned_adapter", "owned_preparation", "Explicit single-turn plugin request; not native AI Assistant"),
    AdapterSpec("jetbrains_gemini", "gemini", "JetBrains plugin-owned Gemini API", "owned_adapter", "owned_preparation", "Explicit single-turn plugin request; not native AI Assistant"),
    AdapterSpec("owned_local", "custom_api", "Owned application", "owned_adapter", "owned_preparation", "Prepare one downstream input"),
    *[AdapterSpec("mcp_"+a, a, "Compatible MCP client", "mcp_explicit", "explicit_tool_only",
                 "Explicit tool result; native replacement not verified") for a in MCP_AGENTS],
    AdapterSpec("openai_api", "chatgpt", "Owned OpenAI API application", "owned_adapter", "owned_preparation", "Caller owns provider submission; not ChatGPT Web"),
    AdapterSpec("gemini_api", "gemini", "Owned Gemini API application", "owned_adapter", "owned_preparation", "Caller owns provider submission; not Gemini Web"),
    *[AdapterSpec(i,a,e,"native","unverified","Requires approved runtime-specific delivery proof") for i,a,e in (
        ("vscode_copilot","copilot","VS Code"), ("vscode_codex","codex","VS Code"),
        ("vscode_claude","claude","VS Code"), ("intellij_copilot","copilot","IntelliJ IDEA"),
        ("intellij_ai","jetbrains_ai","IntelliJ IDEA"), ("eclipse_copilot","copilot","Eclipse"),
        ("chatgpt_web","chatgpt","Web"), ("gemini_web","gemini","Web"),
        ("claude_web","claude","Web"), ("copilot_web","copilot","Web"), ("other_agent","other","Other"))],
)
_BY_ID = {s.id:s for s in SPECS}

def get_adapter(adapter_id):
    return _BY_ID[adapter_id]

def can_return_candidate(agent: str, transport: str, mode: str) -> bool:
    return mode == "return_payload" and any(
        s.agent == agent and s.transport == transport and s.transport != "native" for s in SPECS)

def inventory():
    return [{**asdict(s), "live_agent_verified":False, "provider_savings_verified":False}
            for s in SPECS]
