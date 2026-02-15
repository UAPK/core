"""
Tests for Web3 NFT Minting (Phase 3)
"""
import json
import os
import tempfile
from pathlib import Path
import pytest

from uapk.nft.mint_pipeline import create_nft_metadata, mint_nft, verify_nft
from uapk.nft.minter import mint_business_nft


def create_test_instance(tmpdir: str, instance_id: str) -> Path:
    """Helper to create a test instance directory"""
    instance_dir = Path(tmpdir) / 'instances' / instance_id
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Create manifest
    manifest = {
        "@context": "https://uapk.ai/context/v0.1",
        "@id": f"urn:uapk:{instance_id}:v1",
        "uapkVersion": "0.1",
        "name": "Test Business",
        "description": "Test business instance",
        "executionMode": "dry_run",
        "cryptoHeader": {
            "hashAlg": "sha256",
            "manifestHash": "sha256:abcd1234",
            "planHash": "",
            "merkleRoot": "",
            "signature": "test-sig",
            "signedBy": "test-key",
            "signedAt": None
        }
    }

    with open(instance_dir / 'manifest.jsonld', 'w') as f:
        json.dump(manifest, f)

    # Create plan lock
    plan = {
        "planHash": "sha256:plan1234",
        "resolvedAt": "2024-01-01T00:00:00Z"
    }

    with open(instance_dir / 'plan.lock.json', 'w') as f:
        json.dump(plan, f)

    # Create package info
    package = {
        "packageHash": "sha256:pkg1234",
        "createdAt": "2024-01-01T00:00:00Z"
    }

    with open(instance_dir / 'package.json', 'w') as f:
        json.dump(package, f)

    return instance_dir


def test_create_nft_metadata():
    """Test NFT metadata generation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'test-001'
        instance_dir = create_test_instance(tmpdir, instance_id)

        metadata = create_nft_metadata(instance_dir)

        # Check structure
        assert 'name' in metadata
        assert 'description' in metadata
        assert 'attributes' in metadata
        assert 'properties' in metadata

        # Check required properties
        props = metadata['properties']
        assert props['manifestHash'] == 'sha256:abcd1234'
        assert props['planHash'] == 'sha256:plan1234'
        assert props['packageHash'] == 'sha256:pkg1234'
        assert props['instanceId'] == instance_id
        assert props['compilerVersion'] == '0.1.0'
        assert 'createdAt' in props

        # Check attributes
        attrs = {attr['trait_type']: attr['value'] for attr in metadata['attributes']}
        assert attrs['Instance ID'] == instance_id
        assert attrs['Manifest Hash'] == 'sha256:abcd1234'
        assert attrs['Plan Hash'] == 'sha256:plan1234'
        assert attrs['Package Hash'] == 'sha256:pkg1234'
        assert attrs['Execution Mode'] == 'dry_run'
        assert attrs['UAPK Version'] == '0.1'


def test_create_nft_metadata_missing_manifest():
    """Test metadata generation with missing manifest"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_dir = Path(tmpdir) / 'instances' / 'missing'
        instance_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            create_nft_metadata(instance_dir)


def test_create_nft_metadata_without_plan():
    """Test metadata generation without plan lock"""
    with tempfile.TemporaryDirectory() as tmpdir:
        instance_id = 'test-no-plan'
        instance_dir = Path(tmpdir) / 'instances' / instance_id
        instance_dir.mkdir(parents=True)

        manifest = {
            "@context": "https://uapk.ai/context/v0.1",
            "@id": f"urn:uapk:{instance_id}:v1",
            "name": "Test",
            "executionMode": "dry_run",
            "cryptoHeader": {"manifestHash": "sha256:test"}
        }

        with open(instance_dir / 'manifest.jsonld', 'w') as f:
            json.dump(manifest, f)

        metadata = create_nft_metadata(instance_dir)

        # Should have default/empty values
        assert metadata['properties']['planHash'] is None
        assert metadata['properties']['packageHash'] is None


def test_mint_business_nft_simulation():
    """Test NFT minting in simulation mode"""
    receipt = mint_business_nft(
        metadata_uri='cas://abcd1234',
        manifest_hash='sha256:manifest',
        plan_hash='sha256:plan',
        merkle_root='sha256:merkle',
        rpc_url='http://127.0.0.1:9999',  # Invalid to force simulation
        chain_id=31337
    )

    assert 'contract' in receipt
    assert 'tokenId' in receipt
    assert receipt['chainId'] == 31337
    assert receipt['metadataURI'] == 'cas://abcd1234'
    assert receipt['manifestHash'] == 'sha256:manifest'
    assert receipt['status'] == 'simulated'


@pytest.mark.integration
def test_mint_nft_requires_approval():
    """Test that minting creates HITL request when approval required"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        instance_id = 'test-hitl'
        instance_dir = create_test_instance(tmpdir, instance_id)

        result = mint_nft(
            instance_dir=instance_dir,
            rpc_url='http://127.0.0.1:8545',
            private_key='0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
            contract_address='0x5FbDB2315678afecb367f032d93F642f64180aa3',
            require_approval=True,
            override_token=None
        )

        assert result['success'] is False
        assert result['requires_approval'] is True
        assert 'hitl_request_id' in result

        del os.environ['UAPK_DATA_DIR']


@pytest.mark.integration
def test_mint_nft_without_web3():
    """Test minting behavior when web3 is not available"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        instance_id = 'test-noweb3'
        instance_dir = create_test_instance(tmpdir, instance_id)

        # Try to mint without approval (will fail due to missing web3 connection)
        result = mint_nft(
            instance_dir=instance_dir,
            rpc_url='http://127.0.0.1:9999',  # Invalid
            private_key='0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
            contract_address='0x5FbDB2315678afecb367f032d93F642f64180aa3',
            require_approval=False,
            override_token='test-token'
        )

        assert result['success'] is False
        assert 'message' in result

        del os.environ['UAPK_DATA_DIR']


@pytest.mark.integration
def test_verify_nft_not_minted():
    """Test verification of instance without NFT"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        from uapk.fleet.db import get_fleet_db

        instance_id = 'test-not-minted'
        instance_dir = create_test_instance(tmpdir, instance_id)

        # Register instance without NFT
        fleet_db = get_fleet_db()
        fleet_db.register_instance(
            instance_id=instance_id,
            manifest_path=str(instance_dir / 'manifest.jsonld'),
            manifest_hash='sha256:test',
            plan_hash=None,
            package_hash=None
        )
        fleet_db.close()

        result = verify_nft(instance_id)

        assert result['success'] is False
        assert 'not been minted' in result['message']

        del os.environ['UAPK_DATA_DIR']


@pytest.mark.integration
def test_verify_nft_not_found():
    """Test verification of non-existent instance"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        result = verify_nft('non-existent-instance')

        assert result['success'] is False
        assert 'not found' in result['message']

        del os.environ['UAPK_DATA_DIR']


# Integration test (requires running Anvil + deployed contract)
@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get('SKIP_CHAIN_TESTS') == '1',
    reason="Chain integration tests disabled"
)
def test_full_mint_and_verify_flow():
    """
    Test complete mint + verify flow.
    Requires: docker compose -f docker-compose.chain.yml up
    And: uapk nft deploy --network local
    """
    try:
        import requests

        # Check if Anvil is running
        response = requests.post(
            'http://127.0.0.1:8545',
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=2
        )

        if response.status_code != 200:
            pytest.skip("Anvil not running")
    except:
        pytest.skip("Anvil not running")

    # Check if contract is deployed
    from uapk.nft.deployer import get_deployed_contract
    contract_info = get_deployed_contract()

    if not contract_info:
        pytest.skip("NFT contract not deployed")

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        from uapk.fleet.db import get_fleet_db

        instance_id = 'test-full-flow'
        instance_dir = create_test_instance(tmpdir, instance_id)

        # Register instance
        fleet_db = get_fleet_db()
        fleet_db.register_instance(
            instance_id=instance_id,
            manifest_path=str(instance_dir / 'manifest.jsonld'),
            manifest_hash='sha256:abcd1234',
            plan_hash='sha256:plan1234',
            package_hash='sha256:pkg1234'
        )
        fleet_db.close()

        # Mint NFT
        result = mint_nft(
            instance_dir=instance_dir,
            rpc_url='http://127.0.0.1:8545',
            private_key='0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
            contract_address=contract_info['contract_address'],
            require_approval=False,
            override_token='test-override'
        )

        if result['success']:
            assert 'token_id' in result
            assert 'tx_hash' in result

            # Verify NFT
            verify_result = verify_nft(instance_id)
            assert verify_result['success'] is True
            assert verify_result['verified'] is True

        del os.environ['UAPK_DATA_DIR']
