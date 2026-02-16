#!/bin/bash
set -e

echo "========================================="
echo "UAPK Gateway - Production Environment Setup"
echo "========================================="
echo ""

# Check if .env.production already exists
if [ -f .env.production ]; then
    echo "⚠️  .env.production already exists!"
    read -p "Do you want to overwrite it? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 1
    fi
    mv .env.production .env.production.backup.$(date +%s)
    echo "✅ Backed up existing .env.production"
fi

echo "Generating secure keys and creating .env.production..."
echo ""

# Generate SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)
echo "✅ Generated SECRET_KEY"

# Generate GATEWAY_FERNET_KEY
FERNET_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
echo "✅ Generated GATEWAY_FERNET_KEY"

# Generate Ed25519 key
echo "Generating Ed25519 key pair..."
ssh-keygen -t ed25519 -f gateway_ed25519_temp -N '' -q
ED25519_KEY=$(cat gateway_ed25519_temp)
ED25519_PUB=$(cat gateway_ed25519_temp.pub)
rm gateway_ed25519_temp gateway_ed25519_temp.pub
echo "✅ Generated GATEWAY_ED25519_PRIVATE_KEY"

# Create .env.production
cat > .env.production << ENVEOF
# UAPK Gateway Production Environment
# Generated: $(date)
# WARNING: Keep this file secure! Contains sensitive keys.

# Environment
ENVIRONMENT=production

# Security Keys (REQUIRED)
SECRET_KEY=${SECRET_KEY}
GATEWAY_FERNET_KEY=${FERNET_KEY}
GATEWAY_ED25519_PRIVATE_KEY=${ED25519_KEY}

# Database (REQUIRED - UPDATE THIS)
DATABASE_URL=postgresql+asyncpg://uapk:changeme@localhost:5432/uapk

# CORS Origins (REQUIRED - UPDATE THIS)
CORS_ORIGINS=["https://yourdomain.com"]

# Webhook Domains Allowlist (REQUIRED - UPDATE THIS)
GATEWAY_ALLOWED_WEBHOOK_DOMAINS=["api.example.com"]

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Gateway Settings (Optional - defaults are good)
GATEWAY_DEFAULT_DAILY_BUDGET=1000
GATEWAY_APPROVAL_EXPIRY_HOURS=24
GATEWAY_CONNECTOR_TIMEOUT_SECONDS=30
GATEWAY_MAX_REQUEST_BYTES=1000000
GATEWAY_MAX_CONNECTOR_RESPONSE_BYTES=1000000
ENVEOF

echo ""
echo "========================================="
echo "✅ .env.production created successfully!"
echo "========================================="
echo ""
echo "📝 IMPORTANT: You must manually update these values:"
echo ""
echo "1. DATABASE_URL - Set your PostgreSQL connection string"
echo "2. CORS_ORIGINS - Add your frontend domain(s)"
echo "3. GATEWAY_ALLOWED_WEBHOOK_DOMAINS - Add allowed webhook domains"
echo ""
echo "Example:"
echo "  DATABASE_URL=postgresql+asyncpg://user:pass@db.example.com:5432/uapk"
echo "  CORS_ORIGINS=[\"https://app.example.com\",\"https://admin.example.com\"]"
echo "  GATEWAY_ALLOWED_WEBHOOK_DOMAINS=[\"api.stripe.com\",\"hooks.slack.com\"]"
echo ""
echo "========================================="
echo "Ed25519 Public Key (for reference):"
echo "========================================="
echo "${ED25519_PUB}"
echo ""
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo "1. Edit .env.production and update DATABASE_URL, CORS_ORIGINS, etc."
echo "2. Secure this file: chmod 600 .env.production"
echo "3. Deploy: docker compose --env-file .env.production up -d"
echo "4. Run migrations: docker compose exec backend alembic upgrade head"
echo "5. Test: curl http://localhost:8000/healthz"
echo ""
echo "⚠️  SECURITY: Keep .env.production SECRET. Never commit to git!"
echo ""
