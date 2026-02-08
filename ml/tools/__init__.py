"""
Tools package initialization - now using ADK tool patterns
"""

from .adk_tools import ADK_TOOLS, get_tools_for_agent

# Backward compatibility (if anything still references old names)
AgentTools = ADK_TOOLS
ToolImplementations = None  # Legacy, no longer used

__all__ = ['ADK_TOOLS', 'get_tools_for_agent', 'AgentTools']
