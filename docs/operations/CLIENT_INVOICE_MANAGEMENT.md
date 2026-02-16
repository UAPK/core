# Client & Invoice Management System

**Complete guide to managing clients and invoices in the UAPK Gateway**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Client Management](#client-management)
4. [Invoice Management](#invoice-management)
5. [Database Schema](#database-schema)
6. [API Reference](#api-reference)
7. [Common Operations](#common-operations)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The UAPK Gateway includes a complete client and invoice management system with:

- **Client Management**: Track customers as organizations with business details
- **Invoice Generation**: Create professional invoices with VAT calculation
- **Payment Tracking**: Monitor invoice status and payment history
- **Financial Reporting**: View revenue, outstanding balances, and statistics
- **Double-Entry Bookkeeping**: Automatic ledger entries for accounting

### Key Features

✅ **EU VAT Compliant** - Automatic VAT calculation with reverse charge support
✅ **Multi-Currency** - Support for different currencies per client
✅ **RESTful API** - Complete programmatic access
✅ **Audit Trail** - Immutable ledger entries for all financial transactions
✅ **Payment Terms** - Configurable payment due dates per client

---

## Quick Start

### Access the API Documentation

Visit: **http://34.171.83.82:8000/docs**

Interactive API documentation with:
- Try-it-now interface
- Request/response examples
- Schema documentation

### Create Your First Client

```bash
curl -X POST 'http://34.171.83.82:8000/api/v1/clients' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Acme Corporation",
    "slug": "acme-corp",
    "billing_email": "billing@acme.com",
    "contact_name": "John Doe",
    "contact_email": "john@acme.com",
    "company_address": "123 Business St, Munich, Germany",
    "vat_id": "DE123456789",
    "country_code": "DE",
    "currency": "EUR",
    "payment_terms_days": 30
  }'
```

### Create Your First Invoice

```bash
curl -X POST 'http://34.171.83.82:8000/api/v1/invoices' \
  -H 'Content-Type: application/json' \
  -d '{
    "organization_id": "<CLIENT_ID>",
    "items": [
      {
        "description": "UAPK Gateway - Professional Plan",
        "quantity": 1,
        "unit_price": 199.00
      }
    ],
    "customer_country": "DE",
    "due_days": 30
  }'
```

---

## Client Management

### Client Data Model

Each client is stored as an `Organization` with extended business fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique client identifier |
| `name` | String | Company/client name |
| `slug` | String | URL-friendly identifier (unique) |
| `billing_email` | Email | Billing contact email |
| `contact_name` | String | Primary contact person |
| `contact_email` | Email | Contact person email |
| `company_address` | String | Full company address |
| `vat_id` | String | EU VAT ID (e.g., DE123456789) |
| `country_code` | String | ISO 3166-1 alpha-2 (e.g., DE, FR) |
| `currency` | String | ISO 4217 currency code (e.g., EUR, USD) |
| `payment_terms_days` | Integer | Default payment terms (days) |
| `created_at` | DateTime | Client creation timestamp |

### Client API Endpoints

#### List All Clients
```http
GET /api/v1/clients?page=1&page_size=20
```

**Response includes:**
- Total invoices
- Total revenue
- Outstanding balance
- Active subscription status

#### Get Client Details
```http
GET /api/v1/clients/{client_id}
```

Returns full client information plus financial statistics.

#### Create New Client
```http
POST /api/v1/clients
Content-Type: application/json

{
  "name": "Client Name",
  "slug": "client-slug",
  "billing_email": "billing@client.com",
  "vat_id": "EU12345",
  "country_code": "DE"
}
```

#### Update Client
```http
PATCH /api/v1/clients/{client_id}
Content-Type: application/json

{
  "billing_email": "new-billing@client.com",
  "payment_terms_days": 45
}
```

#### Delete Client
```http
DELETE /api/v1/clients/{client_id}
```

⚠️ **Warning**: Deletes client and all related invoices, subscriptions, etc.

---

## Invoice Management

### Invoice Workflow

```
1. DRAFT    → Invoice created, can be edited
2. SENT     → Invoice sent to client, awaiting payment
3. PAID     → Payment received
4. OVERDUE  → Past due date, payment not received
5. VOID     → Cancelled/voided invoice
```

### Invoice Data Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique invoice identifier |
| `invoice_number` | String | Human-readable number (INV-YYYY-NNNN) |
| `organization_id` | UUID | Client (organization) ID |
| `status` | Enum | draft, sent, paid, overdue, void |
| `currency` | String | Invoice currency |
| `subtotal` | Float | Total before VAT |
| `vat_rate` | Float | VAT rate applied (e.g., 0.19 for 19%) |
| `vat_amount` | Float | Calculated VAT amount |
| `total` | Float | Final amount (subtotal + VAT) |
| `customer_vat_id` | String | Client's VAT ID |
| `customer_country` | String | Client's country |
| `reverse_charge` | Boolean | EU reverse charge applied |
| `issued_at` | DateTime | Invoice issue date |
| `due_at` | DateTime | Payment due date |
| `paid_at` | DateTime | Payment received date |
| `items` | Array | Invoice line items |

### Invoice Line Items

Each invoice contains one or more line items:

```json
{
  "description": "Product/service description",
  "quantity": 1,
  "unit_price": 199.00,
  "amount": 199.00
}
```

### VAT Calculation Rules

The system automatically calculates VAT based on:

**German Domestic (DE → DE)**
- VAT Rate: 19%
- Reverse Charge: No
- Example: €100 → €19 VAT → €119 total

**EU Reverse Charge (DE → EU with VAT ID)**
- VAT Rate: 0%
- Reverse Charge: Yes
- Example: €100 → €0 VAT → €100 total
- Note: "Reverse charge" notation on invoice

**International**
- VAT Rate: 0%
- Reverse Charge: No
- Example: €100 → €0 VAT → €100 total

### Invoice API Endpoints

#### Create Invoice
```http
POST /api/v1/invoices
Content-Type: application/json

{
  "organization_id": "uuid",
  "items": [
    {
      "description": "Service description",
      "quantity": 1,
      "unit_price": 199.00
    }
  ],
  "customer_country": "DE",
  "customer_vat_id": "DE123456789",
  "due_days": 30
}
```

#### List Invoices
```http
GET /api/v1/invoices?page=1&page_size=20
GET /api/v1/invoices?organization_id={client_id}
GET /api/v1/invoices?status=paid
```

#### Get Invoice Details
```http
GET /api/v1/invoices/{invoice_id}
```

#### Mark Invoice as Paid
```http
POST /api/v1/invoices/{invoice_id}/mark-paid
```

Sets status to "paid" and records `paid_at` timestamp.

#### Update Invoice Status
```http
PATCH /api/v1/invoices/{invoice_id}/status
Content-Type: application/json

{
  "status": "sent"
}
```

#### Get Invoice Summary
```http
GET /api/v1/invoices/summary
GET /api/v1/invoices/summary?organization_id={client_id}
```

Returns financial statistics:
- Total invoices count
- Total revenue
- Outstanding balance
- Total paid
- Total overdue

---

## Database Schema

### Tables Created

#### `plans`
Subscription plan definitions
- Pricing tiers
- Feature limits
- Currency

#### `subscriptions`
Client subscriptions to plans
- Active period
- Status tracking
- Linked to organization

#### `invoices`
Financial invoices
- Invoice metadata
- VAT calculation results
- Payment tracking

#### `invoice_items`
Invoice line items
- Description
- Quantity × Unit Price
- Linked to invoice

#### `ledger_entries`
Double-entry bookkeeping
- Account code (chart of accounts)
- Debit/Credit amounts
- Linked to invoice

### Database Relationships

```
organizations (clients)
    ├─→ subscriptions
    └─→ invoices
            ├─→ invoice_items
            └─→ ledger_entries
```

### Chart of Accounts

| Code | Account | Type |
|------|---------|------|
| 1000 | Accounts Receivable | Asset (Debit) |
| 2000 | VAT Payable | Liability (Credit) |
| 4000 | Revenue - Services | Revenue (Credit) |

---

## API Reference

### Base URL
- **Local**: `http://localhost:8000/api/v1`
- **Production**: `http://34.171.83.82:8000/api/v1`

### Authentication
Currently no authentication required. Add API key or JWT authentication before production use.

### Response Format
All responses are JSON with consistent structure:

**Success (200/201)**:
```json
{
  "id": "uuid",
  "field": "value",
  ...
}
```

**List Response**:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**Error (4xx/5xx)**:
```json
{
  "detail": "Error message"
}
```

---

## Common Operations

### Monthly Billing Cycle

1. **Generate invoices for all active subscriptions**:
```bash
# For each subscription, create invoice
curl -X POST http://localhost:8000/api/v1/invoices \
  -H 'Content-Type: application/json' \
  -d '{...}'
```

2. **Mark invoices as sent**:
```bash
curl -X PATCH http://localhost:8000/api/v1/invoices/{id}/status \
  -d '{"status":"sent"}'
```

3. **Check for overdue invoices** (run daily):
```sql
-- Find invoices past due date
SELECT * FROM invoices
WHERE status = 'sent'
  AND due_at < NOW();
```

### Financial Reporting

**Monthly Revenue**:
```bash
curl http://localhost:8000/api/v1/invoices/summary
```

**Client-Specific Report**:
```bash
curl "http://localhost:8000/api/v1/invoices/summary?organization_id={client_id}"
```

**Outstanding Invoices**:
```bash
curl "http://localhost:8000/api/v1/invoices?status=sent"
```

### Direct Database Access

If you need to query the database directly:

```bash
PGPASSWORD=uapk_production_2026 psql -U uapk -h localhost -d uapk
```

**Useful queries**:

```sql
-- List all clients with revenue
SELECT
  o.name,
  COUNT(i.id) as invoice_count,
  SUM(i.total) as total_revenue
FROM organizations o
LEFT JOIN invoices i ON i.organization_id = o.id
GROUP BY o.id, o.name
ORDER BY total_revenue DESC;

-- Recent invoices
SELECT
  i.invoice_number,
  o.name as client,
  i.total,
  i.status,
  i.issued_at
FROM invoices i
JOIN organizations o ON o.id = i.organization_id
ORDER BY i.issued_at DESC
LIMIT 10;

-- Overdue invoices
SELECT
  i.invoice_number,
  o.name as client,
  i.total,
  i.due_at,
  NOW() - i.due_at as days_overdue
FROM invoices i
JOIN organizations o ON o.id = i.organization_id
WHERE i.status = 'sent'
  AND i.due_at < NOW()
ORDER BY i.due_at;
```

---

## Troubleshooting

### Service Not Running

**Check status**:
```bash
sudo systemctl status uapk-gateway
```

**Restart service**:
```bash
sudo systemctl restart uapk-gateway
```

**View logs**:
```bash
sudo journalctl -u uapk-gateway -f
```

### API Returns 404

Ensure service is running and accessible:
```bash
curl http://localhost:8000/healthz
```

### Database Connection Issues

Check PostgreSQL is running:
```bash
sudo systemctl status postgresql
```

Test database connection:
```bash
PGPASSWORD=uapk_production_2026 psql -U uapk -h localhost -d uapk -c "SELECT 1;"
```

### Invoice VAT Calculation Wrong

Verify client's country code and VAT ID are correct:
```bash
curl http://localhost:8000/api/v1/clients/{client_id}
```

VAT logic:
- DE domestic: 19% VAT
- EU with valid VAT ID: 0% (reverse charge)
- Other: 0%

---

## Next Steps

### Recommended Enhancements

1. **Add Authentication**
   - Implement API key or JWT authentication
   - See: `/api/v1/auth` endpoints

2. **Build Admin Dashboard**
   - Create web UI for client/invoice management
   - Use the existing APIs
   - Frameworks: React, Vue, or simple HTML/JS

3. **Automate Billing**
   - Cron job for monthly invoice generation
   - Email notifications
   - Payment reminders for overdue invoices

4. **Payment Integration**
   - Stripe integration for online payments
   - Payment webhook handling
   - Auto-update invoice status on payment

5. **Export Functionality**
   - PDF invoice generation
   - CSV export for accounting
   - DATEV format for German accounting

---

## Support

**Documentation**: `/docs/` directory
**API Docs**: http://34.171.83.82:8000/docs
**Health Check**: http://34.171.83.82:8000/healthz

**Database Credentials**:
- Host: localhost
- Port: 5432
- Database: uapk
- User: uapk
- Password: uapk_production_2026

**Service Management**:
```bash
# Start/stop/restart
sudo systemctl start uapk-gateway
sudo systemctl stop uapk-gateway
sudo systemctl restart uapk-gateway

# View status
sudo systemctl status uapk-gateway

# View logs
sudo journalctl -u uapk-gateway -n 100
```

---

**Last Updated**: 2026-02-16
**UAPK Gateway Version**: 0.1.0
