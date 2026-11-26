"""Capability inventory derived from registered paths, not user preferences."""
from .engines.registry import EngineRegistry
from .adapter_policy import AGENTS, MCP_AGENTS, SPECS, can_return_candidate

def capabilities(agent: str) -> dict:
    if agent not in AGENTS:
        raise ValueError('Unsupported agent')
    via_mcp = agent in MCP_AGENTS
    transport = 'mcp_explicit' if via_mcp else 'http_api' if agent == 'custom_api' else 'owned_adapter'
    return {
        'agent': agent,
        'available_optimization_features': [x.feature_id for x in EngineRegistry().capabilities()],
        'integration': 'explicit_mcp_stdio_tool' if via_mcp else 'local_http_api' if agent == 'custom_api' else 'owned_api_preparation',
        'explicit_optimization_supported': can_return_candidate(agent, transport, 'return_payload'),
        'adapter_ids': [s.id for s in SPECS if s.agent == agent],
        'automatic_model_input_replacement_verified': False,
        'automatic_tool_result_substitution_verified': False,
        'model_consumption_verified': False,
        'provider_token_usage_available': False,
        'provider_token_savings_verified': False,
        'requires_caller_supplied_evidence': True,
        'notes': 'Explicit tool or owned API input only; model consumption and native connection are unverified.',
    }
