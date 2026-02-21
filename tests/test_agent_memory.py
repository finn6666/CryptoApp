"""
Unit tests for Agent Memory.
"""

import os
import pytest
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from ml.agent_memory import AgentMemory


class TestAgentMemory:
    """Tests for the AgentMemory class."""

    @pytest.fixture
    def memory(self, tmp_data_dir):
        return AgentMemory(memory_dir=str(tmp_data_dir / "agent_memory"))

    def test_store_and_retrieve(self, memory):
        memory.store("test_key", {"foo": "bar"}, agent_type="research")
        result = memory.retrieve("test_key", agent_type="research")
        assert result is not None
        assert result["foo"] == "bar"

    def test_retrieve_nonexistent(self, memory):
        result = memory.retrieve("nonexistent", agent_type="research")
        assert result is None

    def test_persistent_store(self, memory):
        memory.store("persist_key", {"data": 42}, agent_type="risk", persistent=True)
        # Clear in-memory cache
        memory.clear()
        # Should still retrieve from disk
        result = memory.retrieve("persist_key", agent_type="risk")
        assert result is not None
        assert result["data"] == 42

    def test_clear_all(self, memory):
        memory.store("k1", {"a": 1}, agent_type="research")
        memory.store("k2", {"b": 2}, agent_type="technical")
        memory.clear()
        assert memory.retrieve("k1", agent_type="research") is None
        assert memory.retrieve("k2", agent_type="technical") is None

    def test_get_stats(self, memory):
        memory.store("k1", {"a": 1}, agent_type="research")
        stats = memory.get_stats()
        assert "short_term_entries" in stats
