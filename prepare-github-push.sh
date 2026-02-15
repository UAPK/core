#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║     Preparing UAPK Gateway for GitHub Push            ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 1. Update .gitignore to exclude runtime data
echo "1️⃣  Updating .gitignore for runtime data..."
if ! grep -q "^runtime/" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Runtime data (not for git)" >> .gitignore
    echo "runtime/" >> .gitignore
    echo "*.db" >> .gitignore
    echo "audit.jsonl" >> .gitignore
    echo ".env.production" >> .gitignore
    echo "*.pem" >> .gitignore
    echo "   ✅ Updated .gitignore"
else
    echo "   ✓ .gitignore already configured"
fi

# 2. Stage important new files
echo ""
echo "2️⃣  Staging important files..."

# Security documentation
git add CLEANUP_COMPLETE.md 2>/dev/null || true
git add P0_SECURITY_FIXES_COMPLETE.md 2>/dev/null || true
git add P0_FIXES_SUMMARY.md 2>/dev/null || true
git add setup-production-env.sh 2>/dev/null || true

# Deployment files
git add deploy/systemd/*.service 2>/dev/null || true
git add docker-compose*.yml 2>/dev/null || true
git add scripts/*.sh 2>/dev/null || true

# Documentation
git add docs/_audit/*.md 2>/dev/null || true
git add docs/deployment/*.md 2>/dev/null || true

# Tests
git add tests/test_*.py 2>/dev/null || true

# Templates
git add templates/*.jsonld 2>/dev/null || true
git add manifests/plan.lock.json 2>/dev/null || true

# Modified files
git add .env.example README.md 2>/dev/null || true
git add deploy/systemd/uapk-gateway.service 2>/dev/null || true
git add uapk/cli.py uapk/nft/minter.py 2>/dev/null || true

# Contracts (if they exist)
git add contracts/ 2>/dev/null || true

# Remove deleted files
git rm P0_BLOCKERS_FIX_GUIDE.md P0_FIXES_COMPLETE.md P0_FIXES_DEPLOYMENT.md 2>/dev/null || true

echo "   ✅ Files staged"

# 3. Show what will be committed
echo ""
echo "3️⃣  Changes to be committed:"
git status --short | grep "^[AMD]" | head -30

# 4. Summary
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     Ready to Commit                                    ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📦 What will be committed:"
echo "   • Security fixes documentation (P0_SECURITY_FIXES_COMPLETE.md)"
echo "   • Cleanup report (CLEANUP_COMPLETE.md)"
echo "   • Production setup script (setup-production-env.sh)"
echo "   • Deployment configurations"
echo "   • Updated documentation"
echo "   • Tests and templates"
echo ""
echo "🚫 What will NOT be committed:"
echo "   • runtime/ directory (databases, keys, logs)"
echo "   • .env.production (secrets)"
echo "   • *.pem files (private keys)"
echo ""
echo "🔄 Commit with:"
echo '   git commit -m "Security hardening: P0 fixes complete, cleanup done, production-ready"'
echo ""
echo "📤 Push to GitHub:"
echo "   git push origin main"
echo ""
