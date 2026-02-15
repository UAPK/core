"""
Instance Packager (Phase 2)
Creates CAS-addressed bundles from compiled instances.
"""
import json
import hashlib
import zipfile
from pathlib import Path
from typing import Dict, Any, List

from uapk.cas import ContentAddressedStore
from uapk.platform.paths import get_platform_paths


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def package_instance(instance_dir: Path, format: str = 'zip') -> Dict[str, Any]:
    """
    Package instance into CAS-addressed bundle.

    Args:
        instance_dir: Path to instance directory
        format: Package format ('zip' for MVP)

    Returns:
        Package manifest with hashes and CAS URIs
    """
    if not instance_dir.exists():
        raise FileNotFoundError(f"Instance directory not found: {instance_dir}")

    paths = get_platform_paths()
    cas = ContentAddressedStore(str(paths.cas_dir()))

    # Collect files to package
    files_to_package = []
    file_hashes = {}

    # Required files
    manifest_path = instance_dir / 'manifest.jsonld'
    plan_lock_path = instance_dir / 'plan.lock.json'

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    if not plan_lock_path.exists():
        raise FileNotFoundError(f"Plan lock not found: {plan_lock_path}")

    files_to_package.append(('manifest.jsonld', manifest_path))
    files_to_package.append(('plan.lock.json', plan_lock_path))

    # Optional files
    optional_files = [
        'nft_mint_receipt.json',
        'audit.jsonl',
        'metadata.json'
    ]

    for filename in optional_files:
        file_path = instance_dir / filename
        if file_path.exists():
            files_to_package.append((filename, file_path))

    # Compute hashes and store in CAS
    for arcname, file_path in files_to_package:
        file_hash = compute_file_hash(file_path)
        file_hashes[arcname] = file_hash

        # Store in CAS
        with open(file_path, 'rb') as f:
            content = f.read()
        cas.put(content)

    # Create package manifest
    package_manifest = {
        "files": [
            {
                "name": arcname,
                "hash": file_hash,
                "uri": f"cas://{file_hash}"
            }
            for arcname, file_hash in file_hashes.items()
        ],
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    # Compute package hash (hash of all file hashes combined)
    combined_hashes = "".join(sorted(file_hashes.values()))
    package_hash = hashlib.sha256(combined_hashes.encode('utf-8')).hexdigest()

    package_manifest["packageHash"] = package_hash

    # Write package manifest
    package_json_path = instance_dir / 'package.json'
    with open(package_json_path, 'w') as f:
        json.dump(package_manifest, f, indent=2)

    # Store package manifest in CAS
    package_manifest_hash = cas.put_json(package_manifest)

    # Create ZIP bundle if requested
    if format == 'zip':
        package_zip_path = instance_dir / 'package.zip'

        with zipfile.ZipFile(package_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for arcname, file_path in files_to_package:
                zipf.write(file_path, arcname)
            zipf.writestr('package.json', json.dumps(package_manifest, indent=2))

    return {
        "packageHash": package_hash,
        "packageManifestHash": package_manifest_hash,
        "files": package_manifest["files"],
        "package_path": str(package_zip_path) if format == 'zip' else None
    }


# Import datetime
from datetime import datetime
