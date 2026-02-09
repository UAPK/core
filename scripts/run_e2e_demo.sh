#!/bin/bash
set -e

echo "========================================="
echo "OpsPilotOS End-to-End Demo"
echo "========================================="
echo ""

API_BASE="http://localhost:8000"
EMAIL="admin@opspilotos.local"
PASSWORD="changeme123"

# Helper function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local headers=$4

    if [ -n "$data" ]; then
        curl -s -X $method "$API_BASE$endpoint" \
            -H "Content-Type: application/json" \
            $headers \
            -d "$data"
    else
        curl -s -X $method "$API_BASE$endpoint" \
            $headers
    fi
}

# Step 1: Login
echo "[Step 1/10] Logging in as admin..."
LOGIN_RESPONSE=$(api_call POST "/auth/login" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(echo $LOGIN_RESPONSE | python -c "import json,sys; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$TOKEN" ]; then
    echo "✗ Login failed. Is the API running? (python -m uapk.cli run manifests/opspilotos.uapk.jsonld)"
    exit 1
fi

echo "✓ Logged in successfully"
AUTH_HEADER="-H \"Authorization: Bearer $TOKEN\""

# Step 2: Create organization (already exists from bootstrap, get ID)
echo "[Step 2/10] Getting organization..."
ORG_ID=1  # From bootstrap
echo "✓ Using org ID: $ORG_ID"

# Step 3: Create project
echo "[Step 3/10] Creating project..."
PROJECT_RESPONSE=$(eval api_call POST "/projects" "'{\"name\":\"Cloud Migration Project\",\"description\":\"Enterprise cloud migration\",\"org_id\":$ORG_ID}'" "$AUTH_HEADER")
PROJECT_ID=$(echo $PROJECT_RESPONSE | python -c "import json,sys; obj=json.load(sys.stdin); print(obj.get('id', 0) if isinstance(obj, dict) else 0)")
echo "✓ Created project ID: $PROJECT_ID"

# Step 4: Upload KB documents
echo "[Step 4/10] Uploading knowledge base documents..."
for KB_FILE in fixtures/kb/*.md; do
    FILENAME=$(basename "$KB_FILE")
    echo "  Uploading $FILENAME..."
    curl -s -X POST "$API_BASE/projects/$PROJECT_ID/kb/upload" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$KB_FILE" > /dev/null
done
echo "✓ Uploaded KB documents"

# Step 5: Create deliverable request
echo "[Step 5/10] Creating deliverable request..."
DELIVERABLE_RESPONSE=$(eval api_call POST "/deliverables" "'{\"project_id\":$PROJECT_ID,\"title\":\"Cloud Architecture Assessment\",\"description\":\"Comprehensive cloud architecture assessment and recommendations\",\"request_details\":{}}'" "$AUTH_HEADER")
DELIVERABLE_ID=$(echo $DELIVERABLE_RESPONSE | python -c "import json,sys; obj=json.load(sys.stdin); print(obj.get('id', 0) if isinstance(obj, dict) else 0)")
echo "✓ Created deliverable ID: $DELIVERABLE_ID"

# Wait for fulfillment (background task)
echo "[Step 6/10] Waiting for fulfillment agent to generate deliverable..."
sleep 3

# Check deliverable status
DELIVERABLE_STATUS=$(eval api_call GET "/deliverables/$DELIVERABLE_ID" "" "$AUTH_HEADER")
echo "✓ Deliverable status: $(echo $DELIVERABLE_STATUS | python -c 'import json,sys; print(json.load(sys.stdin).get("status", "unknown"))')"

# Step 7: Generate invoice
echo "[Step 7/10] Generating invoice..."
INVOICE_RESPONSE=$(eval api_call POST "/billing/invoices/generate" "'{\"org_id\":$ORG_ID,\"customer_country\":\"DE\",\"customer_vat_id\":\"DE123456789\",\"is_business\":true,\"items\":[{\"description\":\"Cloud Architecture Assessment\",\"quantity\":1,\"unit_price\":500.0}]}'" "$AUTH_HEADER")
INVOICE_ID=$(echo $INVOICE_RESPONSE | python -c "import json,sys; obj=json.load(sys.stdin); print(obj.get('invoice_id', 0) if isinstance(obj, dict) else 0)")
echo "✓ Generated invoice ID: $INVOICE_ID"
echo "  Invoice details:"
echo "$INVOICE_RESPONSE" | python -c "import json,sys; obj=json.load(sys.stdin); print(f\"    Total: {obj.get('total', 0)} EUR\"); print(f\"    VAT: {obj.get('vat_amount', 0)} EUR\"); print(f\"    Reverse Charge: {obj.get('reverse_charge', False)}\")"

# Step 8: Generate VAT report
echo "[Step 8/10] Generating VAT report..."
VAT_REPORT=$(eval api_call GET "/billing/reports/vat?org_id=$ORG_ID&period_start=2024-01-01&period_end=2024-12-31" "" "$AUTH_HEADER")
echo "✓ VAT report generated"
echo "$VAT_REPORT" | python -c "import json,sys; obj=json.load(sys.stdin); summary=obj.get('summary',{}); print(f\"    Total Sales: {summary.get('totalSales', 0)} EUR\"); print(f\"    Total VAT: {summary.get('totalVATCollected', 0)} EUR\")"

# Step 9: Export ledger
echo "[Step 9/10] Exporting ledger..."
LEDGER_EXPORT=$(eval api_call GET "/billing/exports/ledger?org_id=$ORG_ID" "" "$AUTH_HEADER")
echo "✓ Ledger exported"
echo "$LEDGER_EXPORT" | python -c "import json,sys; obj=json.load(sys.stdin); print(f\"    Path: {obj.get('path', 'N/A')}\")"

# Step 10: Attempt NFT mint (will go to HITL in dry_run)
echo "[Step 10/10] Attempting NFT mint..."
NFT_RESPONSE=$(eval api_call POST "/nft/mint" "'{\"force\":false}'" "$AUTH_HEADER" 2>&1 || true)

if echo "$NFT_RESPONSE" | grep -q "requires approval"; then
    echo "⚠️  NFT minting requires approval (execution mode: dry_run)"
    echo "    To mint NFT, either:"
    echo "    1. Approve via HITL endpoint, or"
    echo "    2. Use: python -m uapk.cli mint --force manifests/opspilotos.uapk.jsonld"
else
    echo "✓ NFT mint completed (or attempted)"
fi

echo ""
echo "========================================="
echo "✓ End-to-End Demo Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "  - Project created with KB documents"
echo "  - Deliverable generated by FulfillmentAgent"
echo "  - Invoice created with VAT calculation (EU B2B reverse charge)"
echo "  - VAT report generated"
echo "  - Ledger exported to CSV"
echo "  - NFT mint attempted (requires approval in dry_run mode)"
echo ""
echo "Artifacts created:"
echo "  - Deliverable PDF: artifacts/deliverables/$DELIVERABLE_ID.pdf"
echo "  - Ledger export: artifacts/exports/ledger_org_$ORG_ID.csv"
echo "  - Audit log: runtime/audit.jsonl"
echo ""
echo "Next steps:"
echo "  - Review artifacts in artifacts/ directory"
echo "  - Check audit log: cat runtime/audit.jsonl | jq"
echo "  - Verify hash chain: python -c 'from uapk.audit import get_audit_log; print(get_audit_log().verify_chain())'"
echo "  - Compute merkle root: python -c 'from uapk.audit import get_audit_log; print(get_audit_log().compute_merkle_root())'"
echo ""
