"""
Agent Memory System
Provides context storage and retrieval for agents.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Memory system for agents to store and retrieve context.
    
    Features:
    - Short-term memory (in-memory cache)
    - Long-term memory (persistent storage)
    - Context retrieval with TTL
    - Similarity-based lookup
    """
    
    def __init__(self, memory_dir: str = None):
        """
        Initialize agent memory.
        
        Args:
            memory_dir: Directory for persistent memory storage
        """
        if memory_dir is None:
            project_root = Path(__file__).parent.parent
            memory_dir = project_root / 'data' / 'agent_memory'
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Short-term memory (in-memory)
        self._short_term: Dict[str, Dict[str, Any]] = {}
        
        # Memory settings
        self.short_term_ttl_hours = 6
        self.long_term_ttl_days = 30
        
        logger.info(f"Agent memory initialized at {self.memory_dir}")
    
    def store(
        self,
        key: str,
        data: Dict[str, Any],
        agent_type: str,
        persistent: bool = False
    ) -> bool:
        """
        Store data in memory.
        
        Args:
            key: Memory key (e.g., coin symbol)
            data: Data to store
            agent_type: Agent type storing the data
            persistent: Whether to persist to disk
            
        Returns:
            True if stored successfully
        """
        try:
            memory_entry = {
                'data': data,
                'agent_type': agent_type,
                'timestamp': datetime.now().isoformat(),
                'key': key
            }
            
            # Store in short-term memory
            memory_key = f"{agent_type}:{key}"
            self._short_term[memory_key] = memory_entry
            
            # Optionally persist
            if persistent:
                self._persist_memory(memory_key, memory_entry)
            
            logger.debug(f"Stored memory: {memory_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory for {key}: {e}")
            return False
    
    def retrieve(
        self,
        key: str,
        agent_type: str,
        check_persistent: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from memory.
        
        Args:
            key: Memory key
            agent_type: Agent type
            check_persistent: Whether to check persistent storage
            
        Returns:
            Retrieved data or None
        """
        try:
            memory_key = f"{agent_type}:{key}"
            
            # Check short-term memory first
            if memory_key in self._short_term:
                entry = self._short_term[memory_key]
                
                # Check if expired
                timestamp = datetime.fromisoformat(entry['timestamp'])
                if datetime.now() - timestamp < timedelta(hours=self.short_term_ttl_hours):
                    logger.debug(f"Retrieved from short-term memory: {memory_key}")
                    return entry['data']
                else:
                    # Expired, remove
                    del self._short_term[memory_key]
            
            # Check persistent storage
            if check_persistent:
                data = self._load_persistent_memory(memory_key)
                if data:
                    # Reload into short-term memory
                    self._short_term[memory_key] = data
                    logger.debug(f"Retrieved from persistent memory: {memory_key}")
                    return data['data']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory for {key}: {e}")
            return None
    
    def _persist_memory(self, memory_key: str, entry: Dict[str, Any]):
        """Persist memory entry to disk"""
        try:
            # Create safe filename
            filename = hashlib.md5(memory_key.encode()).hexdigest() + '.json'
            filepath = self.memory_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(entry, f, indent=2)
            
            logger.debug(f"Persisted memory to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to persist memory {memory_key}: {e}")
    
    def _load_persistent_memory(self, memory_key: str) -> Optional[Dict[str, Any]]:
        """Load memory entry from disk"""
        try:
            filename = hashlib.md5(memory_key.encode()).hexdigest() + '.json'
            filepath = self.memory_dir / filename
            
            if not filepath.exists():
                return None
            
            # Check if file is expired
            file_age = datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)
            if file_age > timedelta(days=self.long_term_ttl_days):
                # Expired, delete
                filepath.unlink()
                return None
            
            with open(filepath, 'r') as f:
                entry = json.load(f)
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to load persistent memory {memory_key}: {e}")
            return None
    
    def clear(self, agent_type: Optional[str] = None):
        """
        Clear memory.
        
        Args:
            agent_type: If specified, only clear for this agent type
        """
        try:
            if agent_type:
                # Clear specific agent's memory
                keys_to_remove = [
                    k for k in self._short_term.keys()
                    if k.startswith(f"{agent_type}:")
                ]
                for key in keys_to_remove:
                    del self._short_term[key]
                
                logger.info(f"Cleared memory for {agent_type}")
            else:
                # Clear all memory
                self._short_term.clear()
                logger.info("Cleared all memory")
                
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        try:
            persistent_files = list(self.memory_dir.glob('*.json'))
            total_size = sum(f.stat().st_size for f in persistent_files)
            
            return {
                'short_term_entries': len(self._short_term),
                'persistent_entries': len(persistent_files),
                'total_size_kb': round(total_size / 1024, 2),
                'memory_dir': str(self.memory_dir)
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}


# Global memory instance
_memory_instance: Optional[AgentMemory] = None


def get_memory() -> AgentMemory:
    """Get or create memory singleton"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = AgentMemory()
    return _memory_instance


if __name__ == "__main__":
    # Test memory system
    print("Agent Memory Test")
    print("-" * 50)
    
    memory = get_memory()
    print(f"Initialized: {memory.memory_dir}")
    
    # Store some test data
    test_data = {
        'score': 0.85,
        'confidence': 0.9,
        'analysis': 'Test analysis'
    }
    
    memory.store('BTC', test_data, 'test_agent', persistent=True)
    print("\nStored test data for BTC")
    
    # Retrieve it
    retrieved = memory.retrieve('BTC', 'test_agent')
    print(f"Retrieved: {retrieved}")
    
    # Stats
    stats = memory.get_stats()
    print(f"\nMemory Stats: {json.dumps(stats, indent=2)}")
