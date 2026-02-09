# Secrets Management (M1.5)

**Feature**: Environment-based secret loading (not hardcoded)
**Implemented**: Milestone 1.5
**Version**: 2.0.0

---

## Quick Reference

**Required Secrets**:
- `UAPK_JWT_SECRET_KEY` - JWT signing
- `UAPK_FERNET_KEY` - Database encryption

**Optional Secrets**:
- `UAPK_ED25519_PRIVATE_KEY` - Audit/override token signing
- `UAPK_SECRET_<NAME>` - Connector credentials

**Generate Secrets**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"  # JWT
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # Fernet
```

**Load from .env**:
```bash
cp .env.example .env
# Edit .env with your secrets
```

See full documentation in this file for production deployment, rotation, and best practices.
