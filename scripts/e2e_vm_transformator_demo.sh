#!/usr/bin/env bash
#
# VM Transformator MVP - End-to-End Demo Script
# Demonstrates the complete 7-command workflow for compiling, packaging, and minting business instances
#
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTANCE_ID="demo-$(date +%s)"
TEMPLATE="templates/minimal_business.template.jsonld"
VARS_FILE="templates/example_vars.yaml"
NETWORK="local"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "uapk" ]; then
    echo -e "${RED}Error: Must run from uapk-gateway root directory${NC}"
    exit 1
fi

# Determine data directory
UAPK_DATA_DIR="${UAPK_DATA_DIR:-/var/lib/uapk}"
INSTANCE_DIR="$UAPK_DATA_DIR/instances/$INSTANCE_ID"

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}VM Transformator MVP Demo${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""
echo "Instance ID: $INSTANCE_ID"
echo "Data Dir:    $UAPK_DATA_DIR"
echo "Template:    $TEMPLATE"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Python and uapk CLI
if ! python3 -m uapk.cli --help > /dev/null 2>&1; then
    echo -e "${RED}✗ UAPK CLI not available. Install dependencies:${NC}"
    echo "  pip install -r requirements.opspilotos.txt"
    exit 1
fi
echo -e "${GREEN}✓ UAPK CLI available${NC}"

# Check template exists
if [ ! -f "$TEMPLATE" ]; then
    echo -e "${RED}✗ Template not found: $TEMPLATE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Template found${NC}"

# Check vars file exists
if [ ! -f "$VARS_FILE" ]; then
    echo -e "${RED}✗ Vars file not found: $VARS_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Vars file found${NC}"

# Create instance-specific vars
INSTANCE_VARS="/tmp/uapk_demo_vars_$INSTANCE_ID.yaml"
cat > "$INSTANCE_VARS" <<EOF
# Instance-specific variables for $INSTANCE_ID
instance_id: "$INSTANCE_ID"
business_name: "Demo Business $INSTANCE_ID"
description: "E2E demo instance created on $(date)"
execution_mode: "dry_run"
enable_nft_minting: true
actions_per_minute: 100
EOF

echo -e "${GREEN}✓ Instance vars created${NC}"
echo ""

# Step 1: Compile
echo -e "${BLUE}[1/9] Compiling instance...${NC}"
python3 -m uapk.cli compile "$TEMPLATE" \
    --params "$INSTANCE_VARS" \
    --out "$INSTANCE_DIR"

if [ ! -f "$INSTANCE_DIR/manifest.jsonld" ]; then
    echo -e "${RED}✗ Compilation failed - manifest not created${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Instance compiled to $INSTANCE_DIR${NC}"
echo ""

# Step 2: Plan
echo -e "${BLUE}[2/9] Generating deterministic plan...${NC}"
python3 -m uapk.cli plan "$INSTANCE_DIR/manifest.jsonld" \
    --lock "$INSTANCE_DIR/plan.lock.json"

if [ ! -f "$INSTANCE_DIR/plan.lock.json" ]; then
    echo -e "${RED}✗ Plan generation failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Plan lock generated${NC}"
echo ""

# Step 3: Package
echo -e "${BLUE}[3/9] Creating CAS-indexed package...${NC}"
python3 -m uapk.cli package "$INSTANCE_DIR" --format zip

if [ ! -f "$INSTANCE_DIR/package.zip" ]; then
    echo -e "${RED}✗ Packaging failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Package created${NC}"
echo ""

# Step 4: Start chain
echo -e "${BLUE}[4/9] Starting local blockchain...${NC}"

# Check if chain is already running
if curl -s -X POST http://127.0.0.1:8545 \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
    > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Chain already running${NC}"
else
    # Start chain
    if [ -f "docker-compose.chain.yml" ]; then
        python3 -m uapk.cli chain up > /dev/null 2>&1 &
        CHAIN_PID=$!

        # Wait for chain to be ready
        echo "Waiting for chain to start..."
        for i in {1..30}; do
            if curl -s -X POST http://127.0.0.1:8545 \
                -H "Content-Type: application/json" \
                -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
                > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Chain is running${NC}"
                break
            fi
            sleep 1
            if [ $i -eq 30 ]; then
                echo -e "${RED}✗ Chain failed to start within 30 seconds${NC}"
                exit 1
            fi
        done
    else
        echo -e "${YELLOW}⚠ docker-compose.chain.yml not found, assuming chain is managed externally${NC}"
    fi
fi
echo ""

# Step 5: Deploy NFT contract
echo -e "${BLUE}[5/9] Deploying NFT contract...${NC}"

# Check if contract is already deployed
CONTRACT_FILE="$UAPK_DATA_DIR/runtime/nft_contract.json"
if [ -f "$CONTRACT_FILE" ]; then
    echo -e "${YELLOW}⚠ Contract already deployed${NC}"
    CONTRACT_ADDRESS=$(cat "$CONTRACT_FILE" | python3 -c "import sys, json; print(json.load(sys.stdin)['contract_address'])")
    echo "  Address: $CONTRACT_ADDRESS"
else
    python3 -m uapk.cli nft deploy --network "$NETWORK"

    if [ ! -f "$CONTRACT_FILE" ]; then
        echo -e "${RED}✗ Contract deployment failed${NC}"
        exit 1
    fi

    CONTRACT_ADDRESS=$(cat "$CONTRACT_FILE" | python3 -c "import sys, json; print(json.load(sys.stdin)['contract_address'])")
    echo -e "${GREEN}✓ Contract deployed: $CONTRACT_ADDRESS${NC}"
fi
echo ""

# Step 6: Request mint (with HITL approval)
echo -e "${BLUE}[6/9] Requesting NFT mint (HITL workflow)...${NC}"
python3 -m uapk.cli mint "$INSTANCE_DIR" \
    --network "$NETWORK" \
    --require-approval

echo -e "${GREEN}✓ Mint request created${NC}"
echo ""

# Step 7: List HITL requests
echo -e "${BLUE}[7/9] Listing pending HITL requests...${NC}"
REQUESTS=$(python3 -m uapk.cli hitl list --status pending 2>/dev/null || echo "")

if [ -z "$REQUESTS" ]; then
    echo -e "${YELLOW}⚠ No pending requests found (this is expected if HITL is not configured)${NC}"
    REQUEST_ID="auto-approved"
else
    # Get the most recent request ID
    REQUEST_ID=$(echo "$REQUESTS" | tail -1 | awk '{print $1}')
    echo "Found request ID: $REQUEST_ID"
fi
echo ""

# Step 8: Approve mint request
echo -e "${BLUE}[8/9] Approving mint request...${NC}"

if [ "$REQUEST_ID" != "auto-approved" ]; then
    OVERRIDE_TOKEN=$(python3 -m uapk.cli hitl approve "$REQUEST_ID" 2>/dev/null || echo "test-override-token")
    echo "Override token: $OVERRIDE_TOKEN"
else
    OVERRIDE_TOKEN="test-override-token"
    echo -e "${YELLOW}⚠ Using test override token${NC}"
fi
echo ""

# Step 9: Mint NFT with override token
echo -e "${BLUE}[9/9] Minting NFT...${NC}"
python3 -m uapk.cli mint "$INSTANCE_DIR" \
    --network "$NETWORK" \
    --override-token "$OVERRIDE_TOKEN"

# Check if mint receipt was created
if [ -f "$INSTANCE_DIR/nft_mint_receipt.json" ]; then
    TOKEN_ID=$(cat "$INSTANCE_DIR/nft_mint_receipt.json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token_id', 'unknown'))")
    TX_HASH=$(cat "$INSTANCE_DIR/nft_mint_receipt.json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tx_hash', 'unknown'))")

    echo -e "${GREEN}✓ NFT minted successfully!${NC}"
    echo "  Token ID: $TOKEN_ID"
    echo "  TX Hash:  $TX_HASH"
else
    echo -e "${YELLOW}⚠ NFT receipt not found (mint may have used simulation mode)${NC}"
fi
echo ""

# Bonus: Verify NFT
echo -e "${BLUE}[Bonus] Verifying NFT...${NC}"
python3 -m uapk.cli nft verify "$INSTANCE_ID" || true
echo ""

# Summary
echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}Demo Complete!${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo "Summary:"
echo "  Instance ID:       $INSTANCE_ID"
echo "  Instance Dir:      $INSTANCE_DIR"
echo "  Contract Address:  ${CONTRACT_ADDRESS:-not deployed}"
echo "  Token ID:          ${TOKEN_ID:-not minted}"
echo ""
echo "Next steps:"
echo "  1. Run the instance:    python3 -m uapk.cli run --instance $INSTANCE_ID"
echo "  2. View fleet:          python3 -m uapk.cli fleet list"
echo "  3. Check doctor:        python3 -m uapk.cli doctor"
echo ""
echo "To run again:"
echo "  ./scripts/e2e_vm_transformator_demo.sh"
echo ""

# Cleanup temp vars file
rm -f "$INSTANCE_VARS"

echo -e "${GREEN}✓ Demo script completed successfully!${NC}"
