"""DEPRECATED: Capability token API endpoints.

This module is deprecated. The HS256 token system it implements is not used by the Gateway.
Use /api/v1/orgs/{org_id}/capabilities/issue instead, which issues EdDSA tokens that the
Gateway PolicyEngine validates.

All endpoints return HTTP 410 Gone with migration instructions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, RequireOrgAdmin, RequireOrgOperator

router = APIRouter(prefix="/orgs/{org_id}/tokens", tags=["Capability Tokens (DEPRECATED)"])

DEPRECATION_MESSAGE = (
    "This endpoint is deprecated and no longer functional. "
    "The HS256 token system is not used by the Gateway PolicyEngine. "
    "Please use /api/v1/orgs/{org_id}/capabilities/issue instead to issue EdDSA capability tokens "
    "that are validated by the Gateway. "
    "See the capabilities API documentation for migration details."
)


@router.post("", status_code=status.HTTP_410_GONE)
async def create_capability_token(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
) -> dict:
    """DEPRECATED: Issue a new capability token.

    This endpoint is deprecated. Use /api/v1/orgs/{org_id}/capabilities/issue instead.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=DEPRECATION_MESSAGE,
    )


@router.get("", status_code=status.HTTP_410_GONE)
async def list_capability_tokens(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
    agent_id: str | None = Query(default=None),
    include_revoked: bool = Query(default=False),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """DEPRECATED: List capability tokens.

    This endpoint is deprecated. Use /api/v1/orgs/{org_id}/capabilities/issuers to list capability issuers.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=DEPRECATION_MESSAGE,
    )


@router.get("/{token_id}", status_code=status.HTTP_410_GONE)
async def get_capability_token(
    org_id: UUID,
    token_id: str,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
) -> dict:
    """DEPRECATED: Get a specific capability token.

    This endpoint is deprecated. Use /api/v1/orgs/{org_id}/capabilities/issuers to manage issuers.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=DEPRECATION_MESSAGE,
    )


@router.post("/{token_id}/revoke", status_code=status.HTTP_410_GONE)
async def revoke_capability_token(
    org_id: UUID,
    token_id: str,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> dict:
    """DEPRECATED: Revoke a capability token.

    This endpoint is deprecated. Use /api/v1/orgs/{org_id}/capabilities/issuers/{issuer_id}/revoke
    to revoke capability issuers.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=DEPRECATION_MESSAGE,
    )


@router.post("/revoke-all/{agent_id}", status_code=status.HTTP_410_GONE)
async def revoke_all_tokens_for_agent(
    org_id: UUID,
    agent_id: str,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> dict:
    """DEPRECATED: Revoke all tokens for an agent.

    This endpoint is deprecated. Use /api/v1/orgs/{org_id}/capabilities/issuers to manage issuers.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=DEPRECATION_MESSAGE,
    )
