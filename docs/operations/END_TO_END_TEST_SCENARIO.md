# 🎭 Complete End-to-End Test Scenario

**Simulate a real customer from discovery to invoice payment**

---

## 📋 Test Scenario: "Acme Law Firm"

**Customer Profile:**
- **Company:** Acme Law Partners LLP
- **Contact:** Jennifer Smith, Senior Partner
- **Email:** jennifer.smith@acmelaw.example.com (use your real email for testing)
- **Use Case:** "Settlement negotiation agent for IP litigation cases"
- **Budget:** $20,000
- **Timeline:** Immediate
- **Location:** Germany (for VAT testing)
- **VAT ID:** DE123456789

---

## 🎬 STEP-BY-STEP TEST

### **PHASE 1: Customer Submits Inquiry** (2 minutes)

**As the customer (Jennifer):**

1. **Visit website:**
   ```
   https://uapk.github.io/core/
   ```

2. **Scroll to bottom** to see contact form

3. **Fill out form:**
   - Name: `Jennifer Smith`
   - Email: `YOUR-REAL-EMAIL@example.com` ← Use your actual email
   - Company: `Acme Law Partners LLP`
   - Role: `Partner (Law Firm)`
   - Use case: `We need agent governance for our IP settlement workflow. Currently handling 50+ cases/month and want to deploy automated negotiation agents but compliance requires audit trails and human approval for settlements over $10K.`
   - Timeline: `Immediate (this month)`
   - Budget: `$15K-$25K (Pilot)`

4. **Click:** "Get Expert Review"

5. **Verify:**
   - ✅ Success message appears
   - ✅ Form clears
   - ✅ No errors

**Expected:** "Thank you! We'll contact you within 24 hours..."

---

### **PHASE 2: You Process the Lead** (3 minutes)

**As yourself (business owner):**

1. **Open admin dashboard:**
   ```
   http://34.171.83.82:8000/admin
   ```

2. **Click "Leads" tab**

3. **Verify new lead appears:**
   - Name: Jennifer Smith
   - Company: Acme Law Partners LLP
   - Status: NEW (yellow badge)
   - Budget: $15K-$25K
   - Timeline: Immediate

4. **Review the use case** (should show full text)

5. **Click "Contact" button**
   - Status changes to: CONTACTED (gray badge)
   - contacted_at timestamp set

6. **(Simulate discovery call happens)**

7. **Click "Qualify" button**
   - Status changes to: QUALIFIED (green badge)
   - Lead is now qualified for conversion

**Expected:** Lead visible with all data, workflow buttons working

---

### **PHASE 3: Convert to Client** (1 minute)

**In admin dashboard:**

1. **Still in Leads tab**

2. **Find Jennifer's lead** (status: QUALIFIED)

3. **Click "→ Client" button**

4. **Confirm dialog:** Click OK

5. **Verify success:**
   - ✅ Alert: "Success! Lead converted to client..."
   - ✅ Lead status changes to: WON (green badge)
   - ✅ converted_at timestamp set

6. **Click "Clients" tab**

7. **Verify new client appears:**
   - Name: Acme Law Partners LLP
   - Slug: acme-law-partners-llp
   - Contact: Jennifer Smith
   - Email: YOUR-EMAIL
   - Total Invoices: 0
   - Total Revenue: €0.00

**Expected:** Lead successfully converted to client organization

---

### **PHASE 4: Generate Invoice** (3 minutes)

**In Clients tab:**

1. **Find "Acme Law Partners LLP"**

2. **Click "Create Invoice" button** next to the client

3. **Modal opens** - Invoice form pre-filled with client

4. **Fill out invoice:**
   - Client: `Acme Law Partners LLP` (already selected)
   - Description: `UAPK Gateway - Agent Governance Pilot Implementation`
   - Quantity: `1`
   - Unit Price: `20000` (€20,000)
   - Customer Country: `DE` (Germany)
   - Payment Due: `30` days

5. **Click "Create Invoice"**

6. **Verify:**
   - ✅ Success alert
   - ✅ Modal closes
   - ✅ Redirected or updated view

7. **Click "Invoices" tab**

8. **Verify new invoice:**
   - Invoice #: INV-2026-0002 (or next number)
   - Client: Acme Law Partners LLP
   - Amount: €23,800.00 (€20,000 + 19% VAT = €3,800)
   - Status: DRAFT (gray badge)
   - VAT breakdown visible

9. **Check VAT calculation:**
   - Subtotal: €20,000.00
   - VAT Rate: 19% (German domestic)
   - VAT Amount: €3,800.00
   - Total: €23,800.00

**Expected:** Invoice generated with correct VAT calculation

---

### **PHASE 5: Send Invoice to Client** (Manual for now)

**In Invoices tab:**

1. **Click on INV-2026-0002** to view details

2. **Copy invoice details** (for email to client)

3. **(In real life, you would):**
   - Email invoice to jennifer.smith@acmelaw.example.com
   - Include payment instructions
   - Attach PDF (future feature)

4. **In dashboard, update status:**
   - (Future feature: Update status to "SENT")
   - For now, note that you sent it

**Expected:** Invoice ready to send to customer

---

### **PHASE 6: Customer Pays** (1 minute)

**Simulate payment received:**

1. **In Invoices tab**

2. **Find INV-2026-0002**

3. **Click "Mark Paid" button**

4. **Verify:**
   - ✅ Status changes to: PAID (green badge)
   - ✅ paid_at timestamp set
   - ✅ Invoice total: €23,800.00

5. **Click "Dashboard" tab**

6. **Verify stats updated:**
   - Total Revenue: Should include €23,800.00
   - Total Invoices: Increased by 1
   - Outstanding: Should NOT include this invoice (it's paid)

7. **Click "Clients" tab**

8. **Find Acme Law Partners**

9. **Verify client stats:**
   - Total Revenue: €23,800.00
   - Total Invoices: 1
   - Outstanding Balance: €0.00

**Expected:** Payment tracked, all statistics updated

---

### **PHASE 7: Financial Verification** (2 minutes)

**Verify accounting integrity:**

1. **Check invoice summary:**
   ```bash
   curl http://34.171.83.82:8000/api/v1/invoices/summary
   ```

   **Should show:**
   ```json
   {
     "total_invoices": 2,
     "total_revenue": 24036.81,  // €236.81 + €23,800
     "total_outstanding": 0.0,
     "total_paid": 24036.81,
     "total_overdue": 0.0
   }
   ```

2. **Check ledger entries (double-entry bookkeeping):**
   ```bash
   PGPASSWORD=uapk_production_2026 psql -U uapk -h localhost -d uapk \
     -c "SELECT account_code, description, debit, credit
         FROM ledger_entries
         WHERE invoice_id = (SELECT id FROM invoices WHERE invoice_number = 'INV-2026-0002');"
   ```

   **Should show:**
   ```
   account_code |        description        | debit    | credit
   -------------+---------------------------+----------+----------
   1000         | Invoice INV-2026-0002     | 23800.00 | 0.00
   4000         | Invoice... - Revenue      | 0.00     | 20000.00
   2000         | Invoice... - VAT          | 0.00     | 3800.00
   ```

3. **Verify balances:**
   - Debit total = Credit total (€23,800 both sides)
   - Accounts Receivable (1000): €23,800 debit
   - Revenue (4000): €20,000 credit
   - VAT Payable (2000): €3,800 credit

**Expected:** Perfect double-entry bookkeeping

---

## 🎯 SUCCESS CRITERIA

After completing this test, you should have:

### **In Database:**
- ✅ 1 new lead (Acme Law Partners, status: WON)
- ✅ 1 new client (Acme Law Partners LLP)
- ✅ 1 new invoice (INV-2026-0002, €23,800, PAID)
- ✅ 3 new ledger entries (double-entry)

### **In Dashboard:**
- ✅ Lead visible in Leads tab (status: WON)
- ✅ Client visible in Clients tab (€23,800 revenue)
- ✅ Invoice visible in Invoices tab (status: PAID)
- ✅ Stats updated on Dashboard tab

### **Verified:**
- ✅ Complete customer journey works
- ✅ Lead → Client conversion works
- ✅ Invoice generation works
- ✅ VAT calculation correct (19% for Germany)
- ✅ Payment tracking works
- ✅ Financial reporting accurate
- ✅ Accounting integrity maintained

---

## 🧪 BONUS TESTS

### **Test 2: EU Reverse Charge**

Create another invoice for Acme with:
- Customer Country: `FR` (France)
- VAT ID: `FR12345678900`

**Expected:**
- VAT Rate: 0%
- Reverse Charge: YES
- Total: €20,000 (no VAT added)
- Invoice note: "EU Reverse Charge applies"

### **Test 3: Multiple Line Items**

Create invoice with:
- Item 1: "UAPK Gateway Pilot" - €15,000
- Item 2: "Custom Connector Development" - €5,000
- Item 3: "Training Session (2 hours)" - €1,000

**Expected:**
- Subtotal: €21,000
- VAT (19%): €3,990
- Total: €24,990

### **Test 4: Lead Pipeline**

Create 3 more test leads with different statuses:
- Lead 1: Status NEW (just submitted)
- Lead 2: Status CONTACTED (you reached out)
- Lead 3: Status LOST (not qualified)

**Expected:**
- Pipeline stats show correct counts
- Conversion rate calculates properly
- Status badges display correctly

---

## 📊 VERIFICATION CHECKLIST

After completing the main test scenario:

- [ ] Lead submitted through website form
- [ ] Lead appears in admin dashboard
- [ ] Lead status workflow works (NEW → CONTACTED → QUALIFIED → WON)
- [ ] Lead converts to client successfully
- [ ] Client appears in Clients tab with correct info
- [ ] Invoice generates with correct VAT (19%)
- [ ] Invoice number is sequential (INV-2026-NNNN)
- [ ] Invoice marks as PAID successfully
- [ ] Dashboard statistics update correctly
- [ ] Client revenue shows €23,800
- [ ] Ledger entries balance (debits = credits)
- [ ] No errors in any step
- [ ] All transitions smooth and logical

---

## 🎯 QUICK TEST COMMAND

**Or run this automated test via API:**

```bash
# Step 1: Create lead
LEAD_ID=$(curl -s -X POST 'http://34.171.83.82:8000/api/v1/leads' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Jennifer Smith",
    "email": "jennifer@acmelaw.example",
    "company": "Acme Law Partners LLP",
    "role": "Partner",
    "use_case": "IP settlement agent for litigation",
    "timeline": "Immediate",
    "budget": "$20K",
    "interest_type": "pilot"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Lead created: $LEAD_ID"

# Step 2: Convert to client
CLIENT_ID=$(curl -s -X POST "http://34.171.83.82:8000/api/v1/leads/$LEAD_ID/convert" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['client_id'])")

echo "Client created: $CLIENT_ID"

# Step 3: Create invoice
INVOICE_ID=$(curl -s -X POST 'http://34.171.83.82:8000/api/v1/invoices' \
  -H 'Content-Type: application/json' \
  -d "{
    \"organization_id\": \"$CLIENT_ID\",
    \"items\": [{
      \"description\": \"UAPK Gateway Pilot Implementation\",
      \"quantity\": 1,
      \"unit_price\": 20000.00
    }],
    \"customer_country\": \"DE\",
    \"due_days\": 30
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Invoice created: $INVOICE_ID"

# Step 4: Mark as paid
curl -s -X POST "http://34.171.83.82:8000/api/v1/invoices/$INVOICE_ID/mark-paid" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Invoice {d[\"invoice_number\"]}: €{d[\"total\"]} - {d[\"status\"].upper()}')"

# Step 5: Check summary
curl -s http://34.171.83.82:8000/api/v1/invoices/summary \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'\nTotal Revenue: €{d[\"total_revenue\"]:.2f}'); print(f'Total Paid: €{d[\"total_paid\"]:.2f}')"

echo ""
echo "✅ End-to-end test complete!"
echo "Check dashboard: http://34.171.83.82:8000/admin"
```

---

## ✅ RECOMMENDED: Manual Test via UI

**This is better because it tests the full user experience.**

---

## 🎯 START THE TEST NOW

Would you like me to run the automated API test, or would you prefer to test manually through the website and dashboard?

**Option A:** Run automated test now (I'll execute the script above)
**Option B:** I'll guide you step-by-step through manual testing
**Option C:** Do it yourself using the guide above

Which would you prefer?
