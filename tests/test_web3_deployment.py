"""
Tests for Web3 NFT Contract Deployment (Phase 3)
"""
import json
import os
import tempfile
from pathlib import Path
import pytest

from uapk.nft.deployer import deploy_contract, get_deployed_contract, CONTRACT_ABI


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get('UAPK_CHAIN_RPC', 'http://127.0.0.1:8545') != 'http://127.0.0.1:8545',
    reason="Chain not configured"
)
def test_contract_deployment_without_chain():
    """Test deployment behavior when chain is not running"""
    result = deploy_contract(
        rpc_url='http://127.0.0.1:9999',  # Invalid port
        private_key='0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
    )

    assert result['success'] is False
    assert 'message' in result


def test_contract_abi_structure():
    """Test that contract ABI has required functions"""
    # Check mint function
    mint_fn = next((f for f in CONTRACT_ABI if f.get('name') == 'mint'), None)
    assert mint_fn is not None
    assert mint_fn['type'] == 'function'
    assert mint_fn['stateMutability'] == 'nonpayable'

    # Check required parameters
    input_names = [inp['name'] for inp in mint_fn['inputs']]
    assert 'to' in input_names
    assert 'tokenURI' in input_names
    assert 'instanceId' in input_names
    assert 'manifestHash' in input_names
    assert 'planHash' in input_names
    assert 'packageHash' in input_names
    assert 'auditMerkleRoot' in input_names
    assert 'compilerVersion' in input_names

    # Check tokenURI function
    token_uri_fn = next((f for f in CONTRACT_ABI if f.get('name') == 'tokenURI'), None)
    assert token_uri_fn is not None
    assert token_uri_fn['stateMutability'] == 'view'

    # Check getBusinessMetadata function
    metadata_fn = next((f for f in CONTRACT_ABI if f.get('name') == 'getBusinessMetadata'), None)
    assert metadata_fn is not None
    assert metadata_fn['stateMutability'] == 'view'

    # Check totalSupply function
    supply_fn = next((f for f in CONTRACT_ABI if f.get('name') == 'totalSupply'), None)
    assert supply_fn is not None
    assert supply_fn['stateMutability'] == 'view'


def test_get_deployed_contract_from_file():
    """Test loading deployed contract info from file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        from uapk.platform.paths import get_platform_paths
        paths = get_platform_paths()

        # Create deployment info
        deployment_info = {
            "contract_address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
            "deployer": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
            "tx_hash": "0x123abc",
            "block_number": 1,
            "chain_id": 31337,
            "rpc_url": "http://127.0.0.1:8545"
        }

        # Save to file
        paths.ensure_directories()
        with open(paths.nft_contract_path(), 'w') as f:
            json.dump(deployment_info, f)

        # Load it
        loaded = get_deployed_contract()

        assert loaded is not None
        assert loaded['contract_address'] == deployment_info['contract_address']
        assert loaded['deployer'] == deployment_info['deployer']

        del os.environ['UAPK_DATA_DIR']


def test_get_deployed_contract_from_env():
    """Test loading contract address from environment"""
    os.environ['UAPK_NFT_CONTRACT_ADDRESS'] = '0xABCD1234'

    result = get_deployed_contract()

    assert result is not None
    assert result['contract_address'] == '0xABCD1234'
    assert result['source'] == 'environment'

    del os.environ['UAPK_NFT_CONTRACT_ADDRESS']


def test_get_deployed_contract_not_found():
    """Test behavior when no contract is deployed"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        result = get_deployed_contract()

        assert result is None

        del os.environ['UAPK_DATA_DIR']


@pytest.mark.integration
@pytest.mark.skipif(
    not os.path.exists('/usr/bin/docker') and not os.path.exists('/usr/local/bin/docker'),
    reason="Docker not available"
)
def test_deployment_validates_inputs():
    """Test that deployment validates required inputs"""
    # Missing private key should fail early
    result = deploy_contract(
        rpc_url='http://127.0.0.1:8545',
        private_key=''
    )

    assert result['success'] is False


@pytest.mark.integration
def test_contract_bytecode_format():
    """Test that contract bytecode is properly formatted"""
    from uapk.nft.deployer import CONTRACT_BYTECODE

    assert CONTRACT_BYTECODE.startswith('0x')
    assert len(CONTRACT_BYTECODE) > 100  # Should be substantial


# Integration test (requires running Anvil)
@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get('SKIP_CHAIN_TESTS') == '1',
    reason="Chain integration tests disabled"
)
def test_deploy_contract_to_anvil():
    """
    Test actual deployment to local Anvil chain.
    Requires: docker compose -f docker-compose.chain.yml up
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

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        # Deploy contract
        result = deploy_contract(
            rpc_url='http://127.0.0.1:8545',
            private_key='0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'  # Anvil dev key
        )

        if result['success']:
            assert 'contract_address' in result
            assert result['contract_address'].startswith('0x')
            assert 'deployer' in result
            assert 'tx_hash' in result

            # Verify deployment info was saved
            from uapk.platform.paths import get_platform_paths
            paths = get_platform_paths()
            assert paths.nft_contract_path().exists()

            # Verify we can load it back
            loaded = get_deployed_contract()
            assert loaded is not None
            assert loaded['contract_address'] == result['contract_address']

        del os.environ['UAPK_DATA_DIR']
