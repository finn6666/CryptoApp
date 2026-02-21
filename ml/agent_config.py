"""
Agent Configuration
Centralized settings for the multi-agent crypto analysis system.
"""

import os
from typing import Dict, Any
from enum import Enum


class AgentType(Enum):
    """Types of agents in the system"""
    GEMINI_RESEARCH = "gemini_research"
    GEMINI_TECHNICAL = "gemini_technical"
    GEMINI_RISK = "gemini_risk"
    ORCHESTRATOR = "orchestrator"


class ModelConfig:
    """LLM Model configurations"""
    
    # Google Gemini Config
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    GEMINI_MODEL = "gemini-2.5-flash"  # Fast and cost-effective
    GEMINI_PRO_MODEL = "gemini-2.5-pro"  # For complex tasks
    
    # Temperature settings
    TEMPERATURE_CREATIVE = 0.7  # For research and exploration
    TEMPERATURE_ANALYTICAL = 0.3  # For technical analysis
    TEMPERATURE_CONSERVATIVE = 0.1  # For risk assessment


class AgentConfig:
    """Individual agent configurations"""
    
    AGENTS = {
        AgentType.GEMINI_RESEARCH: {
            "name": "Research Analyst",
            "description": "Fundamentals, team, tech, partnerships, roadmap analysis",
            "model": ModelConfig.GEMINI_MODEL,
            "temperature": ModelConfig.TEMPERATURE_ANALYTICAL,
            "max_tokens": 3000,
            "timeout": 45,
            "cache_ttl": 7200,  # 2 hours
            "priority": 2,
        },
        AgentType.GEMINI_TECHNICAL: {
            "name": "Technical Analyst",
            "description": "Charts, patterns, support/resistance, volume analysis",
            "model": ModelConfig.GEMINI_MODEL,
            "temperature": ModelConfig.TEMPERATURE_ANALYTICAL,
            "max_tokens": 2000,
            "timeout": 30,
            "cache_ttl": 1800,  # 30 minutes
            "priority": 2,
        },
        AgentType.GEMINI_RISK: {
            "name": "Position Manager",
            "description": "Position sizing, entry/exit optimization, reward ratios, correlations",
            "model": ModelConfig.GEMINI_MODEL,
            "temperature": ModelConfig.TEMPERATURE_CONSERVATIVE,
            "max_tokens": 2500,
            "timeout": 40,
            "cache_ttl": 3600,  # 1 hour
            "priority": 2,
        },
    }


class OrchestratorConfig:
    """Orchestrator settings"""
    
    # Consensus settings
    MIN_AGENTS_FOR_CONSENSUS = 2
    CONSENSUS_THRESHOLD = 0.6  # 60% agreement needed
    
    # Routing strategy
    USE_PARALLEL_EXECUTION = True
    MAX_PARALLEL_AGENTS = 3
    
    # Caching
    ENABLE_RESPONSE_CACHE = True
    CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'agent_cache')
    
    # Conflict resolution
    CONFLICT_RESOLUTION_STRATEGY = "weighted_voting"  # or "expert_override"
    AGENT_WEIGHTS = {
        AgentType.GEMINI_RESEARCH: 0.40,
        AgentType.GEMINI_TECHNICAL: 0.40,
        AgentType.GEMINI_RISK: 0.20,
    }
    
    # Timeouts
    ORCHESTRATOR_TIMEOUT = 120  # 2 minutes total
    AGENT_RETRY_ATTEMPTS = 2
    
    # Cost optimization
    USE_CACHING = True
    CACHE_HIT_BONUS = 0.6  # 60% cost reduction on cache hits


class SystemConfig:
    """System-wide settings"""
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'agents.log')
    
    # Performance
    ENABLE_METRICS = True
    METRICS_RETENTION_DAYS = 30
    
    # Feature flags
    ENABLE_AGENT_MEMORY = True
    ENABLE_AUTONOMOUS_MONITORING = False  # Phase 5 feature
    ENABLE_USER_FEEDBACK = False  # Phase 5 feature
    
    # Budget limits (USD per month)
    MONTHLY_BUDGET_LIMIT = 5.00
    COST_ALERT_THRESHOLD = 0.8  # Alert at 80% of budget


def get_agent_config(agent_type: AgentType) -> Dict[str, Any]:
    """Get configuration for a specific agent"""
    return AgentConfig.AGENTS.get(agent_type, {})


def validate_api_keys() -> Dict[str, bool]:
    """Validate that required API keys are set"""
    return {
        "google": bool(ModelConfig.GOOGLE_API_KEY),
    }


if __name__ == "__main__":
    # Test configuration
    print("Agent Configuration Test")
    print("-" * 50)
    
    api_status = validate_api_keys()
    print(f"API Keys Status: {api_status}")
    
    for agent_type in [
        AgentType.GEMINI_RESEARCH,
        AgentType.GEMINI_TECHNICAL,
        AgentType.GEMINI_RISK
    ]:
        config = get_agent_config(agent_type)
        print(f"\n{agent_type.value}:")
        print(f"  Name: {config['name']}")
        print(f"  Model: {config['model']}")
        print(f"  Priority: {config['priority']}")
