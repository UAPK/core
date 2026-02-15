# VM Transformator MVP Deployment Guide

This guide walks you through transforming your VM into a **UAPK Compiler/Transformator node** that can compile business templates, package instances, and mint NFTs on a local blockchain.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [7-Command Workflow](#7-command-workflow)
- [Systemd Services (Optional)](#systemd-services-optional)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)

## Overview

The VM Transformator MVP provides:

1. **Template Compilation** - Convert UAPK templates into business instances
2. **Deterministic Planning** - Generate reproducible execution plans
3. **CAS Packaging** - Create content-addressed packages
4. **Local Blockchain** - Run Anvil for NFT minting
5. **NFT Minting** - Mint business instance NFTs with metadata
6. **HITL Approval** - Human-in-the-loop workflow for sensitive actions
7. **Instance Execution** - Run compiled business instances

## Prerequisites

### Required

- **Linux VM** (Ubuntu 20.04+ or Debian 11+ recommended)
- **Python 3.12+**
- **Docker** and **Docker Compose** (for blockchain)
- **Git** (for cloning the repository)

### Recommended

- 4+ GB RAM
- 20+ GB disk space
- Root or sudo access (for optional systemd setup)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/uapk-gateway.git
cd uapk-gateway
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.opspilotos.txt

# Optional: Install web3 for real blockchain integration
pip install web3
```

### 3. Install Docker

If Docker is not already installed:

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

### 4. Verify Installation

```bash
# Check Python
python3 --version  # Should be 3.12+

# Check Docker
docker --version
docker compose version

# Check UAPK CLI
python3 -m uapk.cli --help
```

## Configuration

### 1. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Generate Required Secrets

```bash
# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output and set UAPK_JWT_SECRET_KEY in .env

# Generate Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output and set UAPK_FERNET_KEY in .env
```

### 3. Configure Platform Paths

Edit `.env` and set:

```bash
# Platform Paths
UAPK_CODE_DIR=/opt/uapk          # Or current directory
UAPK_DATA_DIR=/var/lib/uapk      # Or ./uapk_data
UAPK_LOG_DIR=/var/log/uapk       # Or ./logs

# Blockchain
UAPK_CHAIN_RPC=http://127.0.0.1:8545
UAPK_CHAIN_ID=31337
UAPK_CHAIN_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# Required Secrets
UAPK_JWT_SECRET_KEY=<your-jwt-secret>
UAPK_FERNET_KEY=<your-fernet-key>
```

**Note:** The default `UAPK_CHAIN_PRIVATE_KEY` is Anvil's dev key #0. **Never use this in production.**

### 4. Create Data Directories

```bash
# Create directories with proper permissions
sudo mkdir -p /var/lib/uapk/{instances,cas,db,runtime,chain}
sudo mkdir -p /var/log/uapk
sudo chown -R $USER:$USER /var/lib/uapk /var/log/uapk

# Or use local directories (no sudo required)
mkdir -p ./uapk_data/{instances,cas,db,runtime,chain}
mkdir -p ./logs
export UAPK_DATA_DIR=$(pwd)/uapk_data
export UAPK_LOG_DIR=$(pwd)/logs
```

### 5. Verify Configuration

```bash
python3 -m uapk.cli doctor
```

This should show:
- ✓ All directories writable
- ✓ Required environment variables set
- ⚠ Chain RPC unreachable (until you start it in next step)

## Quick Start

Run the complete E2E demo:

```bash
./scripts/e2e_vm_transformator_demo.sh
```

This will:
1. Compile a business instance from template
2. Generate deterministic plan
3. Create CAS-indexed package
4. Start local blockchain (Anvil)
5. Deploy NFT contract
6. Mint business instance NFT
7. Verify NFT metadata

## 7-Command Workflow

### 1. Compile Template

Convert a template into a business instance:

```bash
python3 -m uapk.cli compile templates/minimal_business.template.jsonld \
  --params templates/example_vars.yaml \
  --out /var/lib/uapk/instances/my-business-001
```

**Output:** Creates instance directory with `manifest.jsonld`

### 2. Generate Plan

Resolve deterministic execution plan:

```bash
python3 -m uapk.cli plan /var/lib/uapk/instances/my-business-001/manifest.jsonld \
  --lock /var/lib/uapk/instances/my-business-001/plan.lock.json
```

**Output:** Creates `plan.lock.json` with deterministic plan hash

### 3. Package Instance

Create content-addressed package:

```bash
python3 -m uapk.cli package /var/lib/uapk/instances/my-business-001 --format zip
```

**Output:** Creates `package.zip` and `package.json` with SHA-256 hash

### 4. Start Blockchain

Start local Anvil blockchain:

```bash
python3 -m uapk.cli chain up
```

**Output:** Starts Anvil on `http://127.0.0.1:8545`

To check status:

```bash
curl -X POST http://127.0.0.1:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

To stop:

```bash
python3 -m uapk.cli chain down
```

### 5. Deploy NFT Contract

Deploy BusinessInstanceNFT contract:

```bash
python3 -m uapk.cli nft deploy --network local
```

**Output:** Deploys contract and saves address to `/var/lib/uapk/runtime/nft_contract.json`

### 6. Mint NFT (with Approval)

#### Request mint:

```bash
python3 -m uapk.cli mint /var/lib/uapk/instances/my-business-001 \
  --network local \
  --require-approval
```

**Output:** Creates HITL approval request

#### List pending requests:

```bash
python3 -m uapk.cli hitl list --status pending
```

#### Approve request:

```bash
python3 -m uapk.cli hitl approve <request-id>
```

**Output:** Returns override token

#### Mint with override token:

```bash
python3 -m uapk.cli mint /var/lib/uapk/instances/my-business-001 \
  --network local \
  --override-token <token>
```

**Output:** Mints NFT and saves receipt to `nft_mint_receipt.json`

### 7. Verify NFT

Verify NFT metadata matches local instance:

```bash
python3 -m uapk.cli nft verify my-business-001
```

**Output:** Compares on-chain metadata with local instance state

### Bonus: Run Instance

Execute the compiled instance:

```bash
python3 -m uapk.cli run --instance my-business-001
```

Or by manifest path:

```bash
python3 -m uapk.cli run /var/lib/uapk/instances/my-business-001/manifest.jsonld
```

## Systemd Services (Optional)

For production deployment, install systemd services:

### 1. Install Service Files

```bash
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2. Create UAPK User (Optional)

```bash
sudo useradd -r -s /bin/false -d /opt/uapk uapk
sudo chown -R uapk:uapk /var/lib/uapk /var/log/uapk
```

### 3. Start Services

```bash
# Start blockchain
sudo systemctl start uapk-chain
sudo systemctl status uapk-chain

# Enable on boot
sudo systemctl enable uapk-chain

# Optionally start gateway
sudo systemctl start uapk-gateway
sudo systemctl enable uapk-gateway
```

### 4. View Logs

```bash
# Chain logs
sudo journalctl -u uapk-chain -f

# Or direct log files
tail -f /var/log/uapk/chain.log
```

## Troubleshooting

### Issue: "typer not installed"

**Solution:**
```bash
pip install -r requirements.opspilotos.txt
```

### Issue: "Cannot connect to chain"

**Cause:** Anvil not running

**Solution:**
```bash
# Start chain
python3 -m uapk.cli chain up

# Or with docker compose directly
docker compose -f docker-compose.chain.yml up -d

# Check if running
curl -X POST http://127.0.0.1:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Issue: "Permission denied" on directories

**Cause:** Insufficient permissions on `/var/lib/uapk` or `/var/log/uapk`

**Solution:**
```bash
# Option 1: Fix permissions
sudo chown -R $USER:$USER /var/lib/uapk /var/log/uapk

# Option 2: Use local directories
export UAPK_DATA_DIR=$(pwd)/uapk_data
export UAPK_LOG_DIR=$(pwd)/logs
mkdir -p $UAPK_DATA_DIR $UAPK_LOG_DIR
```

### Issue: "web3 module not installed"

**Cause:** Web3.py not installed (optional dependency)

**Solution:**
```bash
pip install web3
```

**Note:** Without web3, minting will use simulation mode

### Issue: "Contract deployment failed"

**Cause:** Chain not running or invalid private key

**Solution:**
1. Verify chain is running: `curl http://127.0.0.1:8545`
2. Check private key in `.env` matches Anvil dev key
3. Check chain logs: `docker compose -f docker-compose.chain.yml logs`

### Issue: Doctor shows "✗ UAPK_JWT_SECRET_KEY: MISSING"

**Cause:** Secrets not set in `.env`

**Solution:**
```bash
# Generate and set secrets
python3 -c "import secrets; print('UAPK_JWT_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
python3 -c "from cryptography.fernet import Fernet; print('UAPK_FERNET_KEY=' + Fernet.generate_key().decode())" >> .env
```

### Issue: Template compilation fails

**Cause:** Invalid template or vars file

**Solution:**
1. Verify template exists: `ls -l templates/minimal_business.template.jsonld`
2. Verify vars file: `cat templates/example_vars.yaml`
3. Check template syntax (must be valid JSON-LD)

## Architecture

### Directory Structure

```
/var/lib/uapk/
├── instances/           # Compiled business instances
│   └── my-business-001/
│       ├── manifest.jsonld
│       ├── plan.lock.json
│       ├── package.zip
│       ├── package.json
│       └── nft_mint_receipt.json
├── cas/                 # Content-addressed storage
├── db/                  # Fleet registry database
│   └── fleet.db
├── runtime/             # Runtime state
│   └── nft_contract.json
└── chain/              # Blockchain data

/var/log/uapk/
├── chain.log
├── compiler.log
└── gateway.log
```

### Data Flow

```
Template + Vars
    ↓
[1. Compile] → manifest.jsonld
    ↓
[2. Plan] → plan.lock.json
    ↓
[3. Package] → package.zip + CAS hash
    ↓
[4. Chain Up] → Anvil running
    ↓
[5. Deploy] → NFT contract
    ↓
[6. Mint] → NFT with metadata
    ↓
[7. Verify] → Validation
    ↓
[8. Run] → Execute instance
```

### NFT Metadata

NFTs include the following on-chain metadata:

- `manifestHash` - SHA-256 of manifest
- `planHash` - SHA-256 of plan
- `packageHash` - SHA-256 of package
- `auditMerkleRoot` - Merkle root of audit log
- `instanceId` - Unique instance identifier
- `createdAt` - ISO timestamp
- `compilerVersion` - UAPK compiler version

## Advanced Usage

### Custom Templates

Create your own business templates:

```bash
cp templates/minimal_business.template.jsonld templates/my-template.template.jsonld
# Edit template with your business logic
```

Template variables use Jinja2 syntax:
```json
{
  "name": "{{business_name}}",
  "executionMode": "{{execution_mode | default('dry_run')}}"
}
```

### Multiple Instances

Compile multiple instances from the same template:

```bash
for id in 001 002 003; do
  python3 -m uapk.cli compile templates/minimal_business.template.jsonld \
    --params templates/example_vars.yaml \
    --out /var/lib/uapk/instances/business-$id
done
```

### Fleet Management

List all registered instances:

```bash
python3 -m uapk.cli fleet list
```

Get instance details:

```bash
python3 -m uapk.cli fleet info my-business-001
```

### Remote Chains

To use a different chain (e.g., testnet):

```bash
export UAPK_CHAIN_RPC=https://rpc.testnet.example.com
export UAPK_CHAIN_ID=12345
export UAPK_CHAIN_PRIVATE_KEY=0x...your-key...

python3 -m uapk.cli nft deploy --network testnet
```

## Next Steps

1. **Explore Templates** - Review `templates/` directory
2. **Run Tests** - `pytest tests/`
3. **Read Docs** - See `docs/` for detailed documentation
4. **Join Community** - Report issues on GitHub

## Support

- **Documentation:** `docs/`
- **Issues:** https://github.com/yourusername/uapk-gateway/issues
- **CLI Help:** `python3 -m uapk.cli --help`
- **Command Help:** `python3 -m uapk.cli <command> --help`
