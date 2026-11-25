"""Explicit tool results are available; transparent interception is not implied."""
from .engines.registry import EngineRegistry

from .adapter_policy import AGENTS, can_return_candidate

def capabilities(agent: str) -> dict:
    if agent not in AGENTS:
        raise ValueError('Unsupported agent')
    via_mcp = agent != 'custom_api'
    return {
        'agent': agent,
        'available_optimization_features': [x.feature_id for x in EngineRegistry().capabilities()],
        'integration': 'explicit_mcp_stdio_tool' if via_mcp else 'local_http_api',
        'explicit_optimization_supported': can_return_candidate(agent, 'mcp_explicit' if via_mcp else 'http_api', 'return_payload'),
        'automatic_model_input_replacement_verified': False,
        'automatic_tool_result_substitution_verified': False,
        'model_consumption_verified': False,
        'provider_token_usage_available': False,
        'provider_token_savings_verified': False,
        'requires_caller_supplied_evidence': True,
        'notes': 'Explicit MCP tool result is a candidate; model consumption is not verifiable from this server alone.' if via_mcp else 'API return does not prove downstream model consumption.',
    }
