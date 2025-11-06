"""
ML Service - Simplified wrapper for local ML functionality
Currently not used in main application - kept for future Azure integration
"""

import logging
from typing import Dict, Optional

class MLService:
    """Simplified ML service - not currently used in main application"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("MLService initialized - currently not integrated with main app")
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "status": "available",
            "message": "MLService ready for future Azure integration",
            "integrated": False
        }

# Note: This service is not currently used in the main application.
# The main ML functionality is handled directly by the ML classes in the ml/ directory.
