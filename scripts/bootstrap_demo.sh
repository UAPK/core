#!/bin/bash
set -e

echo "========================================="
echo "OpsPilotOS Bootstrap Script"
echo "========================================="

# Install Python dependencies
echo "[1/4] Installing Python dependencies..."
pip install -r requirements.opspilotos.txt

# Verify manifest
echo "[2/4] Verifying UAPK manifest..."
python -m uapk.cli verify manifests/opspilotos.uapk.jsonld

# Initialize database
echo "[3/4] Initializing database..."
python -c "from uapk.db import init_db; init_db()"

# Create demo user and org
echo "[4/4] Creating demo admin user..."
python -c "
from uapk.db import create_session
from uapk.db.models import User, Organization, Membership, Plan
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
session = create_session()

# Create admin user
user = User(
    email='admin@opspilotos.local',
    hashed_password=pwd_context.hash('changeme123'),
    full_name='Demo Admin'
)
session.add(user)
session.flush()

# Create demo organization
org = Organization(
    name='Demo Organization',
    owner_id=user.id
)
session.add(org)
session.flush()

# Create membership
membership = Membership(
    user_id=user.id,
    org_id=org.id,
    role='Owner'
)
session.add(membership)

# Create default plans
plans = [
    Plan(name='starter', price_monthly=49, currency='EUR', seats=5, deliverables=100, price_per_deliverable=0.5),
    Plan(name='professional', price_monthly=199, currency='EUR', seats=20, deliverables=500, price_per_deliverable=0.4),
    Plan(name='enterprise', price_monthly=999, currency='EUR', seats=-1, deliverables=-1, price_per_deliverable=0.3),
]
for plan in plans:
    session.add(plan)

session.commit()

print(f'✓ Created admin user: admin@opspilotos.local / changeme123')
print(f'✓ Created organization: {org.name} (ID: {org.id})')
print(f'✓ Created {len(plans)} subscription plans')
"

echo ""
echo "========================================="
echo "✓ Bootstrap complete!"
echo "========================================="
echo ""
echo "Credentials:"
echo "  Email: admin@opspilotos.local"
echo "  Password: changeme123"
echo ""
echo "Next steps:"
echo "  1. Run the application:"
echo "     python -m uapk.cli run manifests/opspilotos.uapk.jsonld"
echo ""
echo "  2. Or run the E2E demo:"
echo "     ./scripts/run_e2e_demo.sh"
echo ""
