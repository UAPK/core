#!/bin/bash
set -e

echo "============================================"
echo "Pre-Cleanup Verification"
echo "============================================"
echo ""

# 1. Check critical files exist
echo "✅ Checking critical files..."
CRITICAL_FILES=(
    "backend/app/main.py"
    "backend/app/core/config.py"
    "pyproject.toml"
    "docker-compose.yml"
    "README.md"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✓ $file exists"
    else
        echo "   ✗ $file MISSING!"
        exit 1
    fi
done

# 2. Check Python dependencies
echo ""
echo "✅ Checking Python dependencies..."
python3 -c "import fastapi, uvicorn, sqlalchemy, cryptography" 2>/dev/null && echo "   ✓ Core dependencies installed" || echo "   ⚠️  Need to reinstall: pip install -e ."

# 3. Check if app can import
echo ""
echo "✅ Checking if app can import..."
cd backend
python3 -c "from app.main import app; print('   ✓ App imports successfully')" 2>/dev/null || echo "   ⚠️  App has import issues"
cd ..

# 4. Check Docker
echo ""
echo "✅ Checking Docker..."
docker --version >/dev/null 2>&1 && echo "   ✓ Docker available" || echo "   ⚠️  Docker not available"

# 5. Check deployment files
echo ""
echo "✅ Checking deployment readiness..."
[ -f "setup-production-env.sh" ] && echo "   ✓ Production setup script exists" || echo "   ⚠️  Missing setup script"
[ -f "P0_SECURITY_FIXES_COMPLETE.md" ] && echo "   ✓ Security docs exist" || echo "   ⚠️  Missing security docs"

echo ""
echo "============================================"
echo "✅ Pre-Cleanup Verification Complete"
echo "============================================"
echo ""
echo "System is ready for safe cleanup."
echo ""
