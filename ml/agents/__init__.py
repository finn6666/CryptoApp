"""
Agent package initialization

Using Official Google ADK (google-adk package) for multi-agent crypto analysis.
All custom agent code has been replaced with official ADK implementation.
"""

# Official Google ADK agents are in the 'official' subdirectory
# Import the main analysis function for convenience
try:
    from .official import analyze_crypto
    __all__ = ['analyze_crypto']
except ImportError:
    __all__ = []
