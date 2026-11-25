"""Transport capabilities are explicit, not claims of provider consumption."""
AGENTS = ('custom_api', 'codex', 'copilot', 'claude')


def can_return_candidate(agent: str, transport: str, mode: str) -> bool:
    return mode == 'return_payload' and (
        (agent == 'custom_api' and transport == 'http_api') or
        (agent in AGENTS[1:] and transport == 'mcp_explicit')
    )
