#!/bin/bash
# OPTION 2: Local Python Deployment

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     OPTION 2: Local Python Deployment                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

cd /home/dsanker/uapk-gateway

echo "📦 Step 1: Install Python dependencies..."
echo ""

# Install dependencies
pip3 install --user -e . || {
    echo "❌ Failed to install dependencies"
    exit 1
}

echo ""
echo "🔑 Step 2: Generate environment file..."
echo ""

# Generate keys using Python
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ED25519_KEY=$(python3 -c "from cryptography.hazmat.primitives.asymmetric import ed25519; from cryptography.hazmat.primitives import serialization; key = ed25519.Ed25519PrivateKey.generate(); print(key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()).decode())")

cat > .env.production << ENVEOF
# Production Environment
ENVIRONMENT=production

# Security Keys
SECRET_KEY=${SECRET_KEY}
GATEWAY_FERNET_KEY=${FERNET_KEY}
GATEWAY_ED25519_PRIVATE_KEY=${ED25519_KEY}

# Database (UPDATE THIS)
DATABASE_URL=postgresql+asyncpg://uapk:uapk@localhost:5432/uapk

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# CORS (UPDATE THIS)
CORS_ORIGINS=["http://localhost:3000"]

# Webhook Domains (UPDATE THIS)
GATEWAY_ALLOWED_WEBHOOK_DOMAINS=["api.example.com"]

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
ENVEOF

echo "✅ Generated .env.production"
echo ""
echo "⚠️  IMPORTANT: Edit .env.production and update:"
echo "   • DATABASE_URL"
echo "   • CORS_ORIGINS"
echo "   • GATEWAY_ALLOWED_WEBHOOK_DOMAINS"
echo ""
read -p "Open editor now? (yes/no): " edit
if [ "$edit" = "yes" ]; then
    ${EDITOR:-nano} .env.production
fi

echo ""
echo "🗄️  Step 3: Database setup..."
echo ""
echo "Make sure PostgreSQL is installed and running:"
echo "   sudo apt install postgresql postgresql-contrib"
echo "   sudo systemctl start postgresql"
echo ""
echo "Create database:"
echo '   sudo -u postgres psql -c "CREATE DATABASE uapk;"'
echo '   sudo -u postgres psql -c "CREATE USER uapk WITH PASSWORD '\''uapk'\'';"'
echo '   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE uapk TO uapk;"'
echo ""
read -p "Database ready? (yes/no): " db_ready

if [ "$db_ready" != "yes" ]; then
    echo "Please set up the database first, then run this script again."
    exit 1
fi

echo ""
echo "📝 Step 4: Run migrations..."
cd backend
export $(cat ../.env.production | xargs)
alembic upgrade head
cd ..

echo ""
echo "🚀 Step 5: Start the server..."
echo ""
echo "Starting UAPK Gateway..."
export $(cat .env.production | xargs)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 &
SERVER_PID=$!
cd ..

echo "Server started with PID: $SERVER_PID"
echo ""
sleep 5

echo "🏥 Step 6: Verify deployment..."
HEALTH=$(curl -s http://localhost:8000/healthz)
if [[ "$HEALTH" == *"ok"* ]]; then
    echo "✅ Server is running!"
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     ✅ DEPLOYMENT COMPLETE                                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Access your API at: http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
    echo ""
    echo "Server PID: $SERVER_PID"
    echo "Stop with: kill $SERVER_PID"
    echo ""
    echo "💡 For production, use a process manager like systemd or supervisor"
else
    echo "❌ Health check failed"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi
