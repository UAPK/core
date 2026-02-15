#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║          🚀 UAPK GATEWAY - PRODUCTION DEPLOYMENT            ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "This will deploy your UAPK Gateway to PRODUCTION."
echo ""
echo "⚠️  IMPORTANT: This is a REAL production deployment."
echo "    Make sure you have:"
echo "    • A PostgreSQL database ready"
echo "    • Domain names configured"
echo "    • SSL certificates (or will use HTTP for now)"
echo ""
read -p "Continue with production deployment? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " STEP 1: Generate Production Keys"
echo "════════════════════════════════════════════════════════════════"
echo ""

if [ -f ".env.production" ]; then
    echo "⚠️  .env.production already exists!"
    read -p "Overwrite existing configuration? (yes/no): " overwrite
    if [ "$overwrite" != "yes" ]; then
        echo "Using existing .env.production"
    else
        ./setup-production-env.sh
    fi
else
    ./setup-production-env.sh
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " STEP 2: Configure Your Settings"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  IMPORTANT: You must update .env.production with:"
echo "    1. DATABASE_URL"
echo "    2. CORS_ORIGINS"
echo "    3. GATEWAY_ALLOWED_WEBHOOK_DOMAINS"
echo ""

# Show current configuration
echo "Current configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -E "^(DATABASE_URL|CORS_ORIGINS|GATEWAY_ALLOWED_WEBHOOK_DOMAINS)=" .env.production | sed 's/=.*/=[CONFIGURED]/' || true
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Open editor to configure now? (yes/no): " edit
if [ "$edit" = "yes" ]; then
    ${EDITOR:-nano} .env.production
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " STEP 3: Pre-Deployment Checks"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Please install Docker first."
    exit 1
fi
echo "✅ Docker installed: $(docker --version)"

# Check Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose not found! Please install Docker Compose first."
    exit 1
fi
echo "✅ Docker Compose installed"

# Check if secrets are set
if grep -q "changeme" .env.production 2>/dev/null; then
    echo "⚠️  WARNING: Default values detected in .env.production"
    echo "   Please update DATABASE_URL and other settings!"
    read -p "Continue anyway? (yes/no): " continue_anyway
    if [ "$continue_anyway" != "yes" ]; then
        exit 1
    fi
fi

# Check if ports are available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use!"
    echo "   Current process:"
    lsof -Pi :8000 -sTCP:LISTEN
    read -p "Stop existing service and continue? (yes/no): " stop_service
    if [ "$stop_service" = "yes" ]; then
        docker compose down 2>/dev/null || true
    else
        exit 1
    fi
fi
echo "✅ Port 8000 available"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " STEP 4: Deploy Services"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Pull latest images
echo "📥 Pulling Docker images..."
docker compose --env-file .env.production pull

# Start services
echo ""
echo "🚀 Starting services..."
docker compose --env-file .env.production up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check if backend is up
if ! docker compose ps | grep -q "backend.*running"; then
    echo "❌ Backend failed to start!"
    echo ""
    echo "Checking logs:"
    docker compose logs backend --tail 50
    exit 1
fi
echo "✅ Backend started"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " STEP 5: Database Migration"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "🗄️  Running database migrations..."
docker compose exec backend alembic upgrade head

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " STEP 6: Verification"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test health endpoint
echo "🏥 Testing health endpoints..."
sleep 2

HEALTH_RESPONSE=$(curl -s http://localhost:8000/healthz 2>/dev/null || echo "failed")
if [[ "$HEALTH_RESPONSE" == *"ok"* ]]; then
    echo "✅ Health check passed: $HEALTH_RESPONSE"
else
    echo "❌ Health check failed!"
    echo "   Response: $HEALTH_RESPONSE"
    echo ""
    echo "Checking logs:"
    docker compose logs backend --tail 30
    exit 1
fi

READY_RESPONSE=$(curl -s http://localhost:8000/readyz 2>/dev/null || echo "failed")
if [[ "$READY_RESPONSE" == *"ready"* ]]; then
    echo "✅ Ready check passed: $READY_RESPONSE"
else
    echo "⚠️  Ready check returned: $READY_RESPONSE"
fi

# Test API docs
API_DOCS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null)
if [ "$API_DOCS" = "200" ]; then
    echo "✅ API documentation accessible"
else
    echo "⚠️  API docs returned: $API_DOCS"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " STEP 7: Create Admin User"
echo "════════════════════════════════════════════════════════════════"
echo ""

read -p "Create admin user now? (yes/no): " create_admin
if [ "$create_admin" = "yes" ]; then
    echo ""
    echo "Admin user creation (you can do this via API later too):"
    echo "Use the API endpoint: POST /api/v1/auth/register"
    echo "Or run: docker compose exec backend python -m app.scripts.create_admin"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║          ✅ DEPLOYMENT COMPLETE!                            ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 Your UAPK Gateway is LIVE in production!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 🌐 Access Points"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   API Base URL:      http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check:      http://localhost:8000/healthz"
echo "   Metrics:           http://localhost:8000/metrics"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 🔧 Management Commands"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   View logs:     docker compose logs -f backend"
echo "   Stop:          docker compose down"
echo "   Restart:       docker compose restart"
echo "   Shell access:  docker compose exec backend bash"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 📊 Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   1. Create admin user (POST /api/v1/auth/register)"
echo "   2. Create organization (POST /api/v1/orgs)"
echo "   3. Generate API key for agents"
echo "   4. Upload your first UAPK manifest"
echo "   5. Test with agent requests"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 🚀 Ready to Make Money!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Your UAPK Gateway is production-ready and accepting requests!"
echo ""
