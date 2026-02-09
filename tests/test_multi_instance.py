"""
Tests for Multi-Instance Isolation (M3.2)
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from uapk.runtime import InstanceRuntime, set_current_runtime, get_current_runtime


class TestMultiInstanceIsolation:
    """Test M3.2: Multi-Tenant Instance Isolation"""

    @pytest.fixture
    def temp_runtime_dir(self):
        """Create temporary runtime directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_instance_runtime_initialization(self, temp_runtime_dir):
        """Test instance runtime creates namespaced directories"""
        runtime = InstanceRuntime("instance1", temp_runtime_dir)
        runtime.ensure_directories()

        # Check instance directory created
        assert runtime.instance_dir.exists()
        assert runtime.instance_dir.name == "instance1"

        # Check subdirectories created
        assert runtime.get_cas_dir().exists()
        assert runtime.get_artifacts_dir().exists()
        assert runtime.get_logs_dir().exists()
        assert runtime.get_keys_dir().exists()

    def test_instance_paths_are_namespaced(self, temp_runtime_dir):
        """Test that all paths are scoped to instance ID"""
        runtime = InstanceRuntime("test-instance", temp_runtime_dir)

        # All paths should include instance_id
        assert "test-instance" in str(runtime.get_audit_log_path())
        assert "test-instance" in str(runtime.get_plan_lock_path())
        assert "test-instance" in str(runtime.get_database_path())
        assert "test-instance" in str(runtime.get_artifacts_dir())

    def test_multiple_instances_isolated(self, temp_runtime_dir):
        """Test that multiple instances have separate directories"""
        runtime1 = InstanceRuntime("instance1", temp_runtime_dir)
        runtime2 = InstanceRuntime("instance2", temp_runtime_dir)

        runtime1.ensure_directories()
        runtime2.ensure_directories()

        # Both instances should exist
        assert runtime1.instance_dir.exists()
        assert runtime2.instance_dir.exists()

        # Paths should be different
        assert runtime1.get_audit_log_path() != runtime2.get_audit_log_path()
        assert runtime1.get_database_path() != runtime2.get_database_path()

    def test_get_database_url_sqlite(self, temp_runtime_dir):
        """Test SQLite database URL generation"""
        runtime = InstanceRuntime("test", temp_runtime_dir)
        url = runtime.get_database_url(use_postgresql=False)

        assert url.startswith("sqlite:///")
        assert "test" in url
        assert url.endswith("test.db")

    def test_get_database_url_postgresql(self, temp_runtime_dir):
        """Test PostgreSQL database URL generation with instance schema"""
        runtime = InstanceRuntime("test", temp_runtime_dir)
        url = runtime.get_database_url(use_postgresql=True)

        assert url.startswith("postgresql://")
        assert "search_path=test" in url

    def test_cleanup_preserves_audit_by_default(self, temp_runtime_dir):
        """Test cleanup preserves audit log by default"""
        runtime = InstanceRuntime("test", temp_runtime_dir)
        runtime.ensure_directories()

        # Create dummy files
        audit_path = runtime.get_audit_log_path()
        audit_path.write_text("test event")

        db_path = runtime.get_database_path()
        db_path.write_text("test db")

        # Cleanup with preserve_audit=True
        runtime.cleanup(preserve_audit=True)

        # Audit should exist
        assert audit_path.exists()

        # Database should be gone
        assert not db_path.exists()

    def test_cleanup_removes_all_with_flag(self, temp_runtime_dir):
        """Test cleanup removes everything when preserve_audit=False"""
        runtime = InstanceRuntime("test", temp_runtime_dir)
        runtime.ensure_directories()

        # Create dummy files
        audit_path = runtime.get_audit_log_path()
        audit_path.write_text("test event")

        # Cleanup with preserve_audit=False
        runtime.cleanup(preserve_audit=False)

        # Audit should be gone
        assert not audit_path.exists()

    def test_set_and_get_current_runtime(self, temp_runtime_dir):
        """Test global runtime context"""
        set_current_runtime("global-test", temp_runtime_dir)

        runtime = get_current_runtime()

        assert runtime.instance_id == "global-test"
        assert runtime.instance_dir.exists()

    def test_get_current_runtime_fails_if_not_set(self):
        """Test error when runtime not initialized"""
        # Reset global runtime
        import uapk.runtime
        uapk.runtime._current_runtime = None

        with pytest.raises(RuntimeError, match="No instance runtime initialized"):
            get_current_runtime()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
