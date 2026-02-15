"""
Tests for NFT Metadata Structure (Phase 3)
"""
import json
import os
import tempfile
from pathlib import Path
import pytest

from uapk.nft.mint_pipeline import create_nft_metadata
from uapk.cas import ContentAddressedStore


def create_full_instance(tmpdir: str, instance_id: str, with_audit: bool = False) -> Path:
    """Helper to create a complete test instance"""
    instance_dir = Path(tmpdir) / 'instances' / instance_id
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Create manifest with full crypto header
    manifest = {
        "@context": "https://uapk.ai/context/v0.1",
        "@id": f"urn:uapk:{instance_id}:v1",
        "uapkVersion": "0.1",
        "name": "Complete Test Business",
        "description": "Full test instance with all fields",
        "executionMode": "dry_run",
        "cryptoHeader": {
            "hashAlg": "sha256",
            "manifestHash": "sha256:complete_manifest_hash_12345678",
            "planHash": "sha256:complete_plan_hash_12345678",
            "merkleRoot": "sha256:complete_merkle_root_12345678",
            "signature": "complete-test-signature",
            "signedBy": "complete-test-key",
            "signedAt": "2024-01-01T00:00:00Z"
        },
        "corporateModules": {
            "governance": {
                "roles": ["Owner", "Admin"]
            }
        }
    }

    with open(instance_dir / 'manifest.jsonld', 'w') as f:
        json.dump(manifest, f)

    # Create plan lock with all fields
    plan = {
        "planHash": "sha256:complete_plan_hash_12345678",
        "resolvedAt": "2024-01-01T00:00:00Z",
        "steps": [
            {"action": "init", "module": "governance"},
            {"action": "start", "module": "agents"}
        ]
    }

    with open(instance_dir / 'plan.lock.json', 'w') as f:
        json.dump(plan, f)

    # Create package info
    package = {
        "packageHash": "sha256:complete_package_hash_12345678",
        "createdAt": "2024-01-01T00:00:00Z",
        "format": "zip",
        "size": 12345
    }

    with open(instance_dir / 'package.json', 'w') as f:
        json.dump(package, f)

    # Optionally create audit log
    if with_audit:
        audit_events = [
            {"timestamp": "2024-01-01T00:00:00Z", "event": "startup", "data": {}},
            {"timestamp": "2024-01-01T00:01:00Z", "event": "action", "data": {"type": "test"}}
        ]

        with open(instance_dir / 'audit.jsonl', 'w') as f:
            for event in audit_events:
                f.write(json.dumps(event) + '\n')

    return instance_dir


def test_metadata_has_all_required_fields():
    """Test that metadata contains all required fields per plan"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'metadata-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id, with_audit=True)

        metadata = create_nft_metadata(instance_dir)

        # Check top-level fields
        assert 'name' in metadata
        assert 'description' in metadata
        assert 'image' in metadata
        assert 'attributes' in metadata
        assert 'properties' in metadata

        # Check all required properties exist
        props = metadata['properties']
        required_props = [
            'manifestHash',
            'planHash',
            'packageHash',
            'auditMerkleRoot',
            'instanceId',
            'createdAt',
            'compilerVersion'
        ]

        for prop in required_props:
            assert prop in props, f"Missing required property: {prop}"

        # Check properties have non-empty values
        assert props['manifestHash'] == 'sha256:complete_manifest_hash_12345678'
        assert props['planHash'] == 'sha256:complete_plan_hash_12345678'
        assert props['packageHash'] == 'sha256:complete_package_hash_12345678'
        assert props['instanceId'] == instance_id
        assert props['compilerVersion'] == '0.1.0'
        assert props['createdAt']  # Should be ISO timestamp


def test_metadata_attributes_structure():
    """Test that attributes array is properly structured"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'attr-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        attrs = metadata['attributes']

        # Should be list of dicts
        assert isinstance(attrs, list)
        assert len(attrs) > 0

        # Each attribute should have trait_type and value
        for attr in attrs:
            assert 'trait_type' in attr
            assert 'value' in attr

        # Check specific attributes exist
        attr_dict = {attr['trait_type']: attr['value'] for attr in attrs}

        assert 'Instance ID' in attr_dict
        assert 'Manifest Hash' in attr_dict
        assert 'Plan Hash' in attr_dict
        assert 'Package Hash' in attr_dict
        assert 'Execution Mode' in attr_dict
        assert 'UAPK Version' in attr_dict
        assert 'Compiler Version' in attr_dict


def test_metadata_stored_in_cas():
    """Test that metadata can be stored in CAS"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        from uapk.platform.paths import get_platform_paths
        paths = get_platform_paths()
        paths.ensure_directories()

        instance_id = 'cas-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        # Store in CAS
        cas = ContentAddressedStore(str(paths.cas_dir()))
        metadata_hash = cas.put_json(metadata)

        # Verify stored correctly
        assert metadata_hash.startswith('sha256:')

        # Retrieve and verify
        retrieved = cas.get_json(metadata_hash)
        assert retrieved == metadata

        # Verify URI format
        token_uri = f"cas://{metadata_hash}"
        assert token_uri.startswith('cas://sha256:')

        del os.environ['UAPK_DATA_DIR']


def test_metadata_with_missing_optional_fields():
    """Test metadata generation when optional fields are missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'minimal-test-001'
        instance_dir = Path(tmpdir) / 'instances' / instance_id
        instance_dir.mkdir(parents=True)

        # Minimal manifest
        manifest = {
            "@context": "https://uapk.ai/context/v0.1",
            "@id": f"urn:uapk:{instance_id}:v1",
            "name": "Minimal",
            "executionMode": "dry_run",
            "cryptoHeader": {
                "manifestHash": "sha256:minimal_hash"
            }
        }

        with open(instance_dir / 'manifest.jsonld', 'w') as f:
            json.dump(manifest, f)

        metadata = create_nft_metadata(instance_dir)

        # Should have properties with defaults/None
        props = metadata['properties']
        assert props['manifestHash'] == 'sha256:minimal_hash'
        assert props['planHash'] is None
        assert props['packageHash'] is None
        assert props['auditMerkleRoot'] is None
        assert props['instanceId'] == instance_id

        # Check attributes handle missing values
        attr_dict = {attr['trait_type']: attr['value'] for attr in metadata['attributes']}
        assert attr_dict['Plan Hash'] == 'not_resolved'
        assert attr_dict['Package Hash'] == 'not_packaged'
        assert attr_dict['Audit Merkle Root'] == 'no_audit'


def test_metadata_json_serializable():
    """Test that metadata is JSON serializable"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'json-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        # Should be serializable
        json_str = json.dumps(metadata)
        assert json_str

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed == metadata


def test_metadata_deterministic():
    """Test that metadata generation is deterministic"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'deterministic-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        # Generate metadata twice
        metadata1 = create_nft_metadata(instance_dir)
        metadata2 = create_nft_metadata(instance_dir)

        # Should be identical except for createdAt timestamp
        props1 = metadata1['properties'].copy()
        props2 = metadata2['properties'].copy()

        # Remove timestamps for comparison
        created1 = props1.pop('createdAt')
        created2 = props2.pop('createdAt')

        assert props1 == props2
        assert created1  # Should exist
        assert created2  # Should exist


def test_metadata_name_includes_instance_id():
    """Test that metadata name includes instance information"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'name-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        assert 'UAPK Business Instance' in metadata['name']
        assert 'Complete Test Business' in metadata['name']


def test_metadata_description_exists():
    """Test that metadata has a description"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'desc-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        assert metadata['description']
        assert 'Full test instance with all fields' in metadata['description']


def test_metadata_compiler_version():
    """Test that compiler version is tracked"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'version-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        assert metadata['properties']['compilerVersion'] == '0.1.0'

        # Should also be in attributes
        attr_dict = {attr['trait_type']: attr['value'] for attr in metadata['attributes']}
        assert attr_dict['Compiler Version'] == '0.1.0'


def test_metadata_execution_mode_captured():
    """Test that execution mode is captured in metadata"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'exec-mode-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        # Should be in attributes
        attr_dict = {attr['trait_type']: attr['value'] for attr in metadata['attributes']}
        assert attr_dict['Execution Mode'] == 'dry_run'


def test_metadata_uapk_version_captured():
    """Test that UAPK version is captured"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'uapk-version-test-001'
        instance_dir = create_full_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        # Should be in attributes
        attr_dict = {attr['trait_type']: attr['value'] for attr in metadata['attributes']}
        assert attr_dict['UAPK Version'] == '0.1'
