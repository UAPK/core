"""
Authentication endpoints
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from datetime import datetime, timedelta
import jwt
import bcrypt

from uapk.db import get_session
from uapk.db.models import User

# M1.5: Load secrets from environment
from uapk.core.secrets import get_jwt_secret_key

router = APIRouter()
security = HTTPBearer()

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# M1.5: Get secret key from environment (not hardcoded)
def _get_secret_key() -> str:
    """Get JWT secret key (with fallback for development)"""
    try:
        return get_jwt_secret_key()
    except ValueError:
        # Development fallback (will warn)
        print("⚠️  UAPK_JWT_SECRET_KEY not set, using insecure development key")
        print("⚠️  Set UAPK_JWT_SECRET_KEY env var for production")
        return "dev-secret-key-change-in-production"

SECRET_KEY = _get_secret_key()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(data: dict, user: User = None, session: Any = None) -> str:
    """
    Create JWT access token.
    M1.4: Now includes role claim from user's organization membership.

    Args:
        data: Token data (must include 'sub': user_id)
        user: User object (optional, for role lookup)
        session: Database session (optional, for role lookup)

    Returns:
        JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # M1.4: Add role claim if user provided
    if user and session:
        # Look up user's role from organization membership
        from sqlmodel import select
        from uapk.db.models import Membership

        statement = select(Membership).where(Membership.user_id == user.id)
        membership = session.exec(statement).first()

        if membership:
            to_encode['role'] = membership.role
        else:
            # No organization membership - default to Viewer
            to_encode['role'] = 'Viewer'
    elif 'role' not in to_encode:
        # Fallback: default role if not provided
        to_encode['role'] = 'Viewer'

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """
    Dependency to get current authenticated user.
    M1.4: Extracts role from JWT and attaches to user object.
    """
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # M1.4: Extract role from JWT
        role = payload.get("role", "Viewer")

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # M1.4: Attach role to user object (for RBAC decorators)
    user.role = role  # type: ignore

    return user


@router.post("/signup", response_model=TokenResponse)
def signup(request: SignupRequest, session: Session = Depends(get_session)):
    """Sign up new user"""
    # Check if user exists
    statement = select(User).where(User.email == request.email)
    existing = session.exec(statement).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Create token (M1.4: with role claim)
    token = create_access_token({"sub": user.id}, user=user, session=session)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, session: Session = Depends(get_session)):
    """Login user"""
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")

    # M1.4: Create token with role claim
    token = create_access_token({"sub": user.id}, user=user, session=session)
    return TokenResponse(access_token=token)


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "created_at": current_user.created_at
    }
