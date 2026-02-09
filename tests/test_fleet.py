"""
Tests for Fleet Management (M3.5)
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from uapk.fleet_registry import FleetRegistry


class TestFleetRegistry:
    """Test M3.5: Fleet Governance"""

    @pytest.fixture
    def temp_registry(self):
        """Create temporary registry for testing"""
        temp_file = tempfile.mktemp(suffix='.json')
        yield temp_file
        Path(temp_file).unlink(missing_ok=True)

    def test_fleet_registry_initialization(self, temp_registry):
        """Test fleet registry can be initialized"""
        registry = FleetRegistry(temp_registry)
        assert registry is not None

    def test_register_instance(self, temp_registry):
        """Test registering an instance"""
        registry = FleetRegistry(temp_registry)

        registry.register_instance(
            instance_id="test-instance-1",
            manifest_hash="abc123",
            status="running"
        )

        instance = registry.get_instance("test-instance-1")
        assert instance is not None
        assert instance["instance_id"] == "test-instance-1"
        assert instance["manifest_hash"] == "abc123"
        assert instance["status"] == "running"

    def test_update_status(self, temp_registry):
        """Test updating instance status"""
        registry = FleetRegistry(temp_registry)

        registry.register_instance("test", "hash1", "stopped")
        registry.update_status("test", "running")

        instance = registry.get_instance("test")
        assert instance["status"] == "running"

    def test_list_instances(self, temp_registry):
        """Test listing instances"""
        registry = FleetRegistry(temp_registry)

        registry.register_instance("instance1", "hash1", "running")
        registry.register_instance("instance2", "hash2", "stopped")
        registry.register_instance("instance3", "hash3", "running")

        # List all
        all_instances = registry.list_instances()
        assert len(all_instances) == 3

        # List with filter
        running = registry.list_instances(status_filter="running")
        assert len(running) == 2

        stopped = registry.list_instances(status_filter="stopped")
        assert len(stopped) == 1

    def test_detect_drift(self, temp_registry):
        """Test drift detection"""
        registry = FleetRegistry(temp_registry)

        registry.register_instance("test", "original_hash", "running")

        # No drift
        drifted = registry.detect_drift("test", "original_hash")
        assert drifted is False

        # Drift detected
        drifted = registry.detect_drift("test", "different_hash")
        assert drifted is True

    def test_get_fleet_stats(self, temp_registry):
        """Test fleet statistics"""
        registry = FleetRegistry(temp_registry)

        registry.register_instance("i1", "h1", "running")
        registry.register_instance("i2", "h2", "stopped")
        registry.register_instance("i3", "h3", "running")
        registry.register_instance("i4", "h4", "error")

        stats = registry.get_fleet_stats()

        assert stats["total_instances"] == 4
        assert stats["by_status"]["running"] == 2
        assert stats["by_status"]["stopped"] == 1
        assert stats["by_status"]["error"] == 1

    def test_remove_instance(self, temp_registry):
        """Test removing instance from registry"""
        registry = FleetRegistry(temp_registry)

        registry.register_instance("test", "hash", "running")
        assert registry.get_instance("test") is not None

        registry.remove_instance("test")
        assert registry.get_instance("test") is None

    def test_registry_persists_to_disk(self, temp_registry):
        """Test registry saves to disk and reloads"""
        # Create registry and add instance
        registry1 = FleetRegistry(temp_registry)
        registry1.register_instance("persistent", "hash123", "running")

        # Create new registry instance (should load from disk)
        registry2 = FleetRegistry(temp_registry)
        instance = registry2.get_instance("persistent")

        assert instance is not None
        assert instance["manifest_hash"] == "hash123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
