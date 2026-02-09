"""
RBAC (Role-Based Access Control) Decorators (M1.4)
Enforces role-based permissions on API endpoints.
"""
from functools import wraps
from fastapi import HTTPException, Depends
from typing import List
from uapk.db.models import User


def require_role(*allowed_roles: str):
    """
    Decorator to enforce role-based access control on endpoints.

    Usage:
        @router.post("/admin/action")
        @require_role("Owner", "Admin")
        async def admin_action(current_user: User = Depends(get_current_user)):
            ...

    Args:
        *allowed_roles: One or more role names that are allowed to access this endpoint

    Raises:
        HTTPException 403 if user role not in allowed_roles
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract current_user from kwargs (injected by get_current_user dependency)
            current_user: User = kwargs.get('current_user')

            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            # Get user role (from user object or JWT)
            user_role = getattr(current_user, 'role', None)

            if not user_role:
                # Fallback: check if role is in JWT token
                # (In M1.4, we add role to JWT payload)
                user_role = getattr(current_user, '_role_from_token', None)

            if not user_role:
                raise HTTPException(
                    status_code=403,
                    detail="User role not determined"
                )

            # Check if user role is allowed
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions: requires one of {allowed_roles}, user has '{user_role}'"
                )

            # Role check passed, proceed
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous endpoints
            current_user: User = kwargs.get('current_user')

            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            user_role = getattr(current_user, 'role', None) or getattr(current_user, '_role_from_token', None)

            if not user_role:
                raise HTTPException(
                    status_code=403,
                    detail="User role not determined"
                )

            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions: requires one of {allowed_roles}, user has '{user_role}'"
                )

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
