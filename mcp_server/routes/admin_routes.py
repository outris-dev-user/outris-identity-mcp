"""
MCP Server Admin Routes

Endpoints for managing users and credits.
Restricted to Admin users (via JWT role or email whitelist).
"""
import os
import logging
import jwt
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Body, Depends
from pydantic import BaseModel, EmailStr

from ..core.database import Database
from ..core.config import get_settings
from ..core.auth import hash_mcp_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ============================================================================
# Admin Models
# ============================================================================

class MCPAccountAdminView(BaseModel):
    id: int
    user_email: str
    display_name: Optional[str]
    credits_balance: int
    credits_tier: str
    is_active: bool
    created_at: datetime
    last_connected_at: Optional[datetime]
    mcp_key_preview: Optional[str] = None # Last 4 chars only or masked


class UpdateCreditsRequest(BaseModel):
    user_email: str
    credits: int # Amount to add (can be negative)
    reason: Optional[str] = "Manual adjustment"


class UserStatusRequest(BaseModel):
    user_email: str
    is_active: bool


# ============================================================================
# Admin Authorization
# ============================================================================

async def get_current_user_claims(authorization: str) -> dict:
    """Validate JWT and return claims."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    token = authorization[7:]
    settings = get_settings()
    jwt_secret = settings.jwt_secret_key
    
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="Authentication not configured")
    
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_admin(authorization: str = Header(...)):
    """
    Verify user is an admin.
    Checks:
    1. JWT 'role' claim == 'admin'
    2. OR Email is in ADMIN_EMAILS env var
    """
    claims = await get_current_user_claims(authorization)
    
    email = claims.get("email") or claims.get("sub")
    role = claims.get("role") or claims.get("app_metadata", {}).get("role")
    
    # Check 1: Role
    if role == "admin":
        return claims
    
    # Check 2: Email Whitelist
    admin_emails = os.getenv("ADMIN_EMAILS", "").lower().split(",")
    if email and email.lower() in [e.strip() for e in admin_emails if e.strip()]:
        return claims
        
    logger.warning(f"Unauthorized admin access attempt: {email}")
    raise HTTPException(status_code=403, detail="Admin access required")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/users", response_model=List[MCPAccountAdminView])
async def list_users(
    limit: int = 50, 
    offset: int = 0,
    search: Optional[str] = None,
    _ = Depends(verify_admin)
):
    """List all MCP users (Admin only)."""
    
    query = """
        SELECT 
            id, user_email, display_name, credits_balance, credits_tier, 
            is_active, created_at, last_connected_at
        FROM mcp.user_accounts
    """
    
    args = []
    if search:
        query += " WHERE user_email ILIKE $1 OR display_name ILIKE $1"
        args.append(f"%{search}%")
        
    query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
    
    if not search:
        rows = await Database.fetch(query)
    else:
        # If search used, handle positional arg
        # Complex logic skipped for brevity, implementing simple search
        # Re-using query builder properly
        full_query = """
            SELECT 
                id, user_email, display_name, credits_balance, credits_tier, 
                is_active, created_at, last_connected_at
            FROM mcp.user_accounts
            WHERE user_email ILIKE $1 OR display_name ILIKE $1
            ORDER BY created_at DESC LIMIT $2 OFFSET $3
        """
        rows = await Database.fetch(full_query, f"%{search}%", limit, offset)
        
    # If no search
    if not search:
        # Need to fix the Limit/Offset execution for simple case
        full_query = """
            SELECT 
                id, user_email, display_name, credits_balance, credits_tier, 
                is_active, created_at, last_connected_at
            FROM mcp.user_accounts
            ORDER BY created_at DESC LIMIT $1 OFFSET $2
        """
        rows = await Database.fetch(full_query, limit, offset)

    return [dict(row) for row in rows]


@router.post("/credits/add")
async def add_credits(
    body: UpdateCreditsRequest,
    admin: dict = Depends(verify_admin)
):
    """Add (or remove) credits manually."""
    
    # Check user exists
    user = await Database.fetchrow(
        "SELECT id, credits_balance FROM mcp.user_accounts WHERE user_email = $1",
        body.user_email
    )
    
    if not user:
        raise HTTPException(404, "User not found")
        
    # Update credits
    await Database.execute(
        """
        UPDATE mcp.user_accounts 
        SET credits_balance = credits_balance + $1
        WHERE user_email = $2
        """,
        body.credits, body.user_email
    )
    
    # Log transaction (audit trail)
    admin_email = admin.get("email") or admin.get("sub")
    logger.info(f"Admin {admin_email} added {body.credits} credits to {body.user_email}. Reason: {body.reason}")
    
    return {"success": True, "message": f"Added {body.credits} credits to {body.user_email}"}


@router.post("/users/status")
async def set_user_status(
    body: UserStatusRequest,
    admin: dict = Depends(verify_admin)
):
    """Activate or deactivate a user."""
    
    result = await Database.execute(
        "UPDATE mcp.user_accounts SET is_active = $1 WHERE user_email = $2",
        body.is_active, body.user_email
    )
    
    if result == "UPDATE 0":
        raise HTTPException(404, "User not found")
        
    status = "activated" if body.is_active else "deactivated"
    admin_email = admin.get("email") or admin.get("sub")
    logger.info(f"Admin {admin_email} {status} user {body.user_email}")
    
    return {"success": True, "status": status}
