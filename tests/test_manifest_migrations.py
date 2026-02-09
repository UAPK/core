"""
Tests for Manifest Version Migrations (M2.2)
"""
import pytest
from uapk.migrations import get_available_migrations, find_migration_path, apply_migration
from uapk.migrations.v0_1_to_v1_0 import migrate, get_migration_info


class TestVersionMigrations:
    """Test M2.2: Versioning and Migration Framework"""

    def test_get_available_migrations(self):
        """Test that available migrations are discovered"""
        migrations = get_available_migrations()

        assert isinstance(migrations, dict)
        # Should have at least v0.1 → v1.0
        assert "0.1" in migrations
        assert "1.0" in migrations["0.1"]

    def test_find_direct_migration_path(self):
        """Test finding direct migration path"""
        path = find_migration_path("0.1", "1.0")

        assert len(path) == 1
        assert "v0_1_to_v1_0" in path[0]

    def test_find_missing_migration_path(self):
        """Test error when migration path doesn't exist"""
        with pytest.raises(ValueError, match="No migration path"):
            find_migration_path("9.9", "10.0")

    def test_migration_v0_1_to_v1_0(self):
        """Test v0.1 → v1.0 migration"""
        extended = {
            "@id": "urn:uapk:test:v1",
            "uapkVersion": "0.1",
            "name": "TestAgent",
            "corporateModules": {
                "policyGuardrails": {
                    "toolPermissions": {
                        "TestAgent": ["read_data"]
                    },
                    "liveActionGates": ["send_email"],
                    "rateLimits": {"actionsPerMinute": 10}
                }
            }
        }

        canonical = migrate(extended)

        # Check structure
        assert canonical["version"] == "1.0"
        assert "agent" in canonical
        assert "capabilities" in canonical
        assert "policy" in canonical

        # Check agent
        assert canonical["agent"]["name"] == "TestAgent"

        # Check capabilities
        assert "testagent:read_data" in canonical["capabilities"]["requested"]
        assert "send_email" in canonical["capabilities"]["requested"]

        # Check extensions preserve original
        assert "extensions" in canonical
        assert "opspilotos" in canonical["extensions"]
        assert canonical["extensions"]["opspilotos"]["@id"] == "urn:uapk:test:v1"

    def test_migration_rejects_wrong_source_version(self):
        """Test migration rejects wrong source version"""
        wrong_version = {
            "uapkVersion": "2.0",
            "name": "Test"
        }

        with pytest.raises(ValueError, match="Expected v0.1"):
            migrate(wrong_version)

    def test_get_migration_info(self):
        """Test migration metadata"""
        info = get_migration_info()

        assert info["from_version"] == "0.1"
        assert info["to_version"] == "1.0"
        assert "breaking_changes" in info
        assert len(info["breaking_changes"]) > 0
        assert info["reversible"] is True

    def test_apply_migration_v0_1_to_v1_0(self):
        """Test apply_migration helper function"""
        extended = {
            "@id": "urn:uapk:apply-test:v1",
            "uapkVersion": "0.1",
            "name": "ApplyTest",
            "corporateModules": {
                "policyGuardrails": {
                    "toolPermissions": {},
                    "liveActionGates": []
                }
            }
        }

        canonical = apply_migration(extended, "0.1", "1.0")

        assert canonical["version"] == "1.0"
        assert canonical["agent"]["name"] == "ApplyTest"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
