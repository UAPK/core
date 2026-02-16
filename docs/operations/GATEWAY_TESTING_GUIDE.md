# UAPK Gateway Testing Guide

## Current Status

✅ **Deployment**: Complete
✅ **Database**: PostgreSQL 17 with all tables
✅ **Admin User**: Created (admin@uapk.ai / Admin123!)
✅ **Organization**: Default Organization created
✅ **Security**: All P0 issues fixed
⚠️ **Server**: Needs to be started (simple command)

---

## Quick Start: Restart Server

The server may have stopped. Restart it with:

```bash
cd /home/dsanker/uapk-gateway/backend

# Kill any existing processes
pkill -f uvicorn

# Start server
ENVIRONMENT=production \
DATABASE_URL="postgresql+asyncpg://uapk:uapk_production_2026@localhost:5432/uapk" \
SECRET_KEY=$(grep SECRET_KEY ../.env.production | cut -d= -f2) \
GATEWAY_FERNET_KEY=$(grep GATEWAY_FERNET_KEY ../.env.production | cut -d= -f2) \
LOG_LEVEL=INFO \
CORS_ORIGINS='["*"]' \
GATEWAY_ALLOWED_WEBHOOK_DOMAINS="[]" \
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 &

# Wait 10 seconds
sleep 10

# Test
curl http://localhost:8080/healthz
```

---

## Testing Flow

### 1. Login and Get Token

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@uapk.ai","password":"Admin123!"}' \
  | python3 -m json.tool

# Save the access_token from response
```

### 2. Create API Key

```bash
# Replace <TOKEN> with access_token from step 1
# Replace <ORG_ID> with: a5b6ee52-8329-4f52-b5f0-350e0c9d8a2f

curl -X POST http://localhost:8080/api/v1/api-keys \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test API Key",
    "org_id": "a5b6ee52-8329-4f52-b5f0-350e0c9d8a2f"
  }' | python3 -m json.tool

# Save the api_key from response
```

### 3. Upload UAPK Manifest

```bash
curl -X POST http://localhost:8080/api/v1/orgs/a5b6ee52-8329-4f52-b5f0-350e0c9d8a2f/manifests \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "manifest": {
      "version": "1.0",
      "agent": {
        "id": "test-agent",
        "name": "Test Agent"
      },
      "capabilities": {
        "requested": ["test:action"]
      }
    }
  }' | python3 -m json.tool
```

### 4. Test Gateway Evaluate

```bash
curl -X POST http://localhost:8080/api/v1/gateway/evaluate \
  -H "X-API-Key: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-agent",
    "action": {
      "type": "test",
      "tool": "test_tool",
      "params": {}
    }
  }' | python3 -m json.tool
```

### 5. Test Gateway Execute

```bash
curl -X POST http://localhost:8080/api/v1/gateway/execute \
  -H "X-API-Key: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-agent",
    "action": {
      "type": "test",
      "tool": "test_tool",
      "params": {}
    }
  }' | python3 -m json.tool
```

---

## Admin Credentials

```
Email:    admin@uapk.ai
Password: Admin123!
User ID:  4f26f35a-e438-49b1-925c-785c9695a40e
Org ID:   a5b6ee52-8329-4f52-b5f0-350e0c9d8a2f
Role:     OWNER
```

---

## External Access

Once server is running:

```
API Base:     http://34.171.83.82:8080
API Docs:     http://34.171.83.82:8080/docs
Health:       http://34.171.83.82:8080/healthz
```

Open the docs URL in your browser for interactive testing!

---

## Database Access

```bash
# Access database
sudo -u postgres psql -d uapk

# Check users
SELECT email, id FROM users;

# Check organizations
SELECT name, slug, id FROM organizations;

# Check memberships
SELECT u.email, o.name, m.role 
FROM memberships m
JOIN users u ON m.user_id = u.id
JOIN organizations o ON m.org_id = o.id;
```

---

## Troubleshooting

### Server not responding?

```bash
# Check if running
ps aux | grep uvicorn

# Check logs
tail -f /tmp/uapk-clean.log

# Restart
cd /home/dsanker/uapk-gateway/backend
# (Run start command above)
```

### Database issues?

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

**Gateway is deployed and ready to test!** 🚀

Just restart the server and follow the testing flow above.

