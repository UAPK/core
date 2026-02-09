"""
Tests for Upgrade/Rollback (M3.3)
"""
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from uapk.upgrade_engine import UpgradeManager, compute_manifest_diff


class TestUpgradeRollback:
    """Test M3.3: Upgrade/Migration/Rollback"""

    @pytest.fixture
    def temp_runtime(self):
        """Create temporary runtime for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def initialized_instance(self, temp_runtime):
        """Create an initialized instance with a manifest"""
        instance_id = "test-instance"
        instance_dir = temp_runtime / instance_id
        instance_dir.mkdir(parents=True)

        # Create initial manifest
        manifest = {
            "version": "1.0",
            "agent": {"id": "test", "name": "Test", "version": "1.0.0"},
            "capabilities": {"requested": ["action1"]}
        }

        with open(instance_dir / "manifest.jsonld", 'w') as f:
            json.dump(manifest, f)

        return instance_id, temp_runtime

    def test_compute_manifest_diff(self):
        """Test manifest diff computation"""
        old = {
            "version": "1.0",
            "agent": {"name": "OldName"},
            "old_field": "value"
        }

        new = {
            "version": "1.0",
            "agent": {"name": "NewName"},
            "new_field": "value"
        }

        diff = compute_manifest_diff(old, new)

        assert "added" in diff
        assert "removed" in diff
        assert "changed" in diff

        # Check specific changes
        assert any("new_field" in item for item in diff["added"])
        assert any("old_field" in item for item in diff["removed"])
        assert any("agent.name" in item for item in diff["changed"])

    def test_upgrade_manager_initialization(self, temp_runtime):
        """Test upgrade manager can be initialized"""
        manager = UpgradeManager("test", temp_runtime)

        assert manager.instance_id == "test"
        assert manager.instance_dir == temp_runtime / "test"

    def test_create_backup(self, initialized_instance):
        """Test backup creation"""
        instance_id, runtime_dir = initialized_instance
        manager = UpgradeManager(instance_id, runtime_dir)

        backup_path = manager.create_backup()

        assert backup_path.exists()
        assert (backup_path / "runtime").exists()
        assert (backup_path / "runtime" / "manifest.jsonld").exists()
        assert (backup_path / "backup_metadata.json").exists()

    def test_restore_backup(self, initialized_instance):
        """Test backup restoration"""
        instance_id, runtime_dir = initialized_instance
        manager = UpgradeManager(instance_id, runtime_dir)

        # Create backup
        backup_path = manager.create_backup()

        # Modify current instance
        manifest_path = runtime_dir / instance_id / "manifest.jsonld"
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        manifest["agent"]["name"] = "Modified"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

        # Restore from backup
        success = manager.restore_backup(backup_path.name)
        assert success is True

        # Check manifest was restored
        with open(manifest_path, 'r') as f:
            restored = json.load(f)
        assert restored["agent"]["name"] == "Test"  # Original value

    def test_upgrade_dry_run(self, initialized_instance):
        """Test upgrade in dry-run mode"""
        instance_id, runtime_dir = initialized_instance
        manager = UpgradeManager(instance_id, runtime_dir)

        # Create new manifest
        new_manifest = {
            "version": "1.0",
            "agent": {"id": "test", "name": "Test", "version": "2.0.0"},
            "capabilities": {"requested": ["action1", "action2"]}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(new_manifest, f)
            new_path = Path(f.name)

        # Dry run upgrade
        result = manager.upgrade(new_path, dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "diff" in result

        # Original manifest should be unchanged
        manifest_path = runtime_dir / instance_id / "manifest.jsonld"
        with open(manifest_path, 'r') as f:
            current = json.load(f)
        assert current["agent"]["version"] == "1.0.0"  # Not upgraded

        # Clean up
        new_path.unlink()

    def test_upgrade_applies_changes(self, initialized_instance):
        """Test upgrade actually applies changes"""
        instance_id, runtime_dir = initialized_instance
        manager = UpgradeManager(instance_id, runtime_dir)

        # Create new manifest
        new_manifest = {
            "version": "1.0",
            "agent": {"id": "test", "name": "Test", "version": "2.0.0"},
            "capabilities": {"requested": ["action1", "action2"]}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(new_manifest, f)
            new_path = Path(f.name)

        # Perform upgrade
        result = manager.upgrade(new_path, auto_backup=True, dry_run=False)

        assert result["success"] is True
        assert "backup_path" in result

        # Manifest should be updated
        manifest_path = runtime_dir / instance_id / "manifest.jsonld"
        with open(manifest_path, 'r') as f:
            upgraded = json.load(f)
        assert upgraded["agent"]["version"] == "2.0.0"
        assert len(upgraded["capabilities"]["requested"]) == 2

        # Clean up
        new_path.unlink()

    def test_rollback_restores_previous_version(self, initialized_instance):
        """Test rollback restores previous version"""
        instance_id, runtime_dir = initialized_instance
        manager = UpgradeManager(instance_id, runtime_dir)

        # Save original version
        manifest_path = runtime_dir / instance_id / "manifest.jsonld"
        with open(manifest_path, 'r') as f:
            original = json.load(f)

        # Create new manifest and upgrade
        new_manifest = {
            "version": "1.0",
            "agent": {"id": "test", "name": "Test", "version": "2.0.0"},
            "capabilities": {"requested": ["new_action"]}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(new_manifest, f)
            new_path = Path(f.name)

        manager.upgrade(new_path, auto_backup=True)

        # Rollback
        result = manager.rollback()

        assert result["success"] is True

        # Manifest should be restored to original
        with open(manifest_path, 'r') as f:
            restored = json.load(f)
        assert restored["agent"]["version"] == original["agent"]["version"]

        # Clean up
        new_path.unlink()

    def test_list_backups(self, initialized_instance):
        """Test listing available backups"""
        instance_id, runtime_dir = initialized_instance
        manager = UpgradeManager(instance_id, runtime_dir)

        # Create some backups
        backup1 = manager.create_backup()
        backup2 = manager.create_backup()

        # List backups
        backups = manager.list_backups()

        assert len(backups) >= 2
        assert all("instance_id" in b for b in backups)
        assert all("created_at" in b for b in backups)
        assert all("backup_name" in b for b in backups)

    def test_upgrade_without_backup_fails_safely(self, temp_runtime):
        """Test upgrade on non-existent instance fails gracefully"""
        manager = UpgradeManager("nonexistent", temp_runtime)

        new_manifest_path = Path("/tmp/fake.json")
        result = manager.upgrade(new_manifest_path, dry_run=False)

        assert result["success"] is False
        assert "not initialized" in result["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
