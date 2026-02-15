"""
Tests for Platform Paths Module (Phase 1)
"""
import os
import tempfile
from pathlib import Path
import pytest

from uapk.platform.paths import PlatformPaths, get_platform_paths


def test_platform_paths_defaults():
    """Test default path configuration"""
    paths = PlatformPaths()

    assert paths.code_dir == Path('/opt/uapk')
    assert paths.data_dir == Path('/var/lib/uapk')
    assert paths.log_dir == Path('/var/log/uapk')


def test_platform_paths_from_env():
    """Test path configuration from environment variables"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_CODE_DIR'] = f'{tmpdir}/code'
        os.environ['UAPK_DATA_DIR'] = f'{tmpdir}/data'
        os.environ['UAPK_LOG_DIR'] = f'{tmpdir}/logs'

        paths = PlatformPaths()

        assert paths.code_dir == Path(f'{tmpdir}/code')
        assert paths.data_dir == Path(f'{tmpdir}/data')
        assert paths.log_dir == Path(f'{tmpdir}/logs')

        # Cleanup
        del os.environ['UAPK_CODE_DIR']
        del os.environ['UAPK_DATA_DIR']
        del os.environ['UAPK_LOG_DIR']


def test_derived_paths():
    """Test derived path properties"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        paths = PlatformPaths()

        assert paths.instances_dir() == Path(tmpdir) / 'instances'
        assert paths.cas_dir() == Path(tmpdir) / 'cas'
        assert paths.db_dir() == Path(tmpdir) / 'db'
        assert paths.runtime_dir() == Path(tmpdir) / 'runtime'
        assert paths.chain_data_dir() == Path(tmpdir) / 'chain'

        del os.environ['UAPK_DATA_DIR']


def test_instance_specific_paths():
    """Test instance-specific path methods"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        paths = PlatformPaths()
        instance_id = 'test-instance-001'

        assert paths.instance_dir(instance_id) == Path(tmpdir) / 'instances' / instance_id
        assert paths.instance_manifest_path(instance_id) == Path(tmpdir) / 'instances' / instance_id / 'manifest.jsonld'
        assert paths.instance_plan_lock_path(instance_id) == Path(tmpdir) / 'instances' / instance_id / 'plan.lock.json'
        assert paths.instance_package_path(instance_id) == Path(tmpdir) / 'instances' / instance_id / 'package.zip'
        assert paths.instance_nft_receipt_path(instance_id) == Path(tmpdir) / 'instances' / instance_id / 'nft_mint_receipt.json'

        del os.environ['UAPK_DATA_DIR']


def test_log_paths():
    """Test log file paths"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_LOG_DIR'] = tmpdir

        paths = PlatformPaths()

        assert paths.chain_log_path() == Path(tmpdir) / 'chain.log'
        assert paths.compiler_log_path() == Path(tmpdir) / 'compiler.log'
        assert paths.gateway_log_path() == Path(tmpdir) / 'gateway.log'

        del os.environ['UAPK_LOG_DIR']


def test_ensure_directories():
    """Test directory creation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir
        os.environ['UAPK_LOG_DIR'] = f'{tmpdir}/logs'

        paths = PlatformPaths()
        paths.ensure_directories()

        # Check all directories were created
        assert paths.data_dir.exists()
        assert paths.instances_dir().exists()
        assert paths.cas_dir().exists()
        assert paths.db_dir().exists()
        assert paths.runtime_dir().exists()
        assert paths.chain_data_dir().exists()
        assert paths.log_dir.exists()

        del os.environ['UAPK_DATA_DIR']
        del os.environ['UAPK_LOG_DIR']


def test_check_writable():
    """Test writability checking"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir
        os.environ['UAPK_LOG_DIR'] = f'{tmpdir}/logs'

        paths = PlatformPaths()
        results = paths.check_writable()

        # All paths should be writable in tmpdir
        for name, result in results.items():
            assert result['writable'], f"{name} should be writable"
            assert result['exists'], f"{name} should exist after check"

        del os.environ['UAPK_DATA_DIR']
        del os.environ['UAPK_LOG_DIR']


def test_get_platform_paths_singleton():
    """Test global platform paths instance"""
    paths1 = get_platform_paths()
    paths2 = get_platform_paths()

    # Should return same instance
    assert paths1 is paths2


def test_fleet_db_path():
    """Test fleet database path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        paths = PlatformPaths()

        assert paths.fleet_db_path() == Path(tmpdir) / 'db' / 'fleet.db'

        del os.environ['UAPK_DATA_DIR']


def test_nft_contract_path():
    """Test NFT contract deployment info path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['UAPK_DATA_DIR'] = tmpdir

        paths = PlatformPaths()

        assert paths.nft_contract_path() == Path(tmpdir) / 'runtime' / 'nft_contract.json'

        del os.environ['UAPK_DATA_DIR']
