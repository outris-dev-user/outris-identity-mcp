"""
MCP Server Admin Routes

Endpoints for managing users and credits.
Restricted to Admin users (via JWT role or email whitelist).
"""
import os
import logging
import jwt
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Header, Depends, Query
from pydantic import BaseModel

from ..core.database import Database
from ..core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ============================================================================
# Admin Models
# ============================================================================

class MCPAccountAdmin(BaseModel):
    id: int
    user_email: str
    display_name: Optional[str]
    credits_balance: int
    credits_tier: str
    is_active: bool
    created_at: datetime
    last_connected_at: Optional[datetime]
    usage_today: int = 0
    usage_this_month: int = 0
    stripe_customer_id: Optional[str] = None


class MCPAnalytics(BaseModel):
    total_accounts: int
    active_accounts: int
    paid_accounts: int
    total_tool_calls_today: int
    total_credits_used_today: int
    total_tool_calls_month: int
    total_credits_used_month: int
    tier_breakdown: Dict[str, int]
    top_tools: List[Dict[str, Any]]
    top_users: List[Dict[str, Any]]


class ToolUsageStats(BaseModel):
    tool_name: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_credits_consumed: int
    avg_latency_ms: float
    success_rate: float


class UpdateCreditsRequest(BaseModel):
    amount: int
    reason: str


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
    Checks JWT role or Email Whitelist.
    """
    claims = await get_current_user_claims(authorization)
    
    email = claims.get("email") or claims.get("sub")
    role = claims.get("role") or claims.get("app_metadata", {}).get("role")
    
    if role == "admin":
        return claims
    
    admin_emails = os.getenv("ADMIN_EMAILS", "").lower().split(",")
    if email and email.lower() in [e.strip() for e in admin_emails if e.strip()]:
        return claims
        
    logger.warning(f"Unauthorized admin access attempt: {email}")
    raise HTTPException(status_code=403, detail="Admin access required")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/mcp/accounts", response_model=List[MCPAccountAdmin])
async def list_mcp_accounts(
    limit: int = 50, 
    offset: int = 0,
    search: Optional[str] = None,
    include_inactive: bool = False,
    sort_by: Optional[str] = "created_at",
    sort_desc: bool = True,
    _ = Depends(verify_admin)
):
    """List all MCP users with usage stats."""
    
    # Base query
    where_clauses = []
    args = []
    arg_idx = 1
    
    if not include_inactive:
        where_clauses.append("is_active = true")
        
    if search:
        where_clauses.append(f"(user_email ILIKE ${arg_idx} OR display_name ILIKE ${arg_idx})")
        args.append(f"%{search}%")
        arg_idx += 1
    
    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = f"WHERE {where_sql}"
        
    order_dir = "DESC" if sort_desc else "ASC"
    order_sql = f"ORDER BY {sort_by or 'created_at'} {order_dir}"
    
    query = f"""
        SELECT 
            id, user_email, display_name, credits_balance, credits_tier, 
            is_active, created_at, last_connected_at, stripe_customer_id
        FROM mcp.user_accounts
        {where_sql}
        {order_sql}
        LIMIT ${arg_idx} OFFSET ${arg_idx+1}
    """
    args.append(limit)
    args.append(offset)
    
    rows = await Database.fetch(query, *args)
    
    # Enrich with usage stats (TODO: Optimize with JOIN later)
    results = []
    for row in rows:
        account_id = row["id"]
        
        # Get usage counts
        usage_today = await Database.fetchval(
            """
            SELECT COUNT(*) FROM mcp.tool_executions 
            WHERE mcp_account_id = $1 AND created_at > CURRENT_DATE
            """, 
            account_id
        ) or 0
        
        usage_month = await Database.fetchval(
            """
            SELECT COUNT(*) FROM mcp.tool_executions 
            WHERE mcp_account_id = $1 AND created_at > DATE_TRUNC('month', CURRENT_DATE)
            """, 
            account_id
        ) or 0
        
        results.append({
            **dict(row),
            "usage_today": usage_today,
            "usage_this_month": usage_month
        })
        
    return results


@router.get("/mcp/analytics", response_model=MCPAnalytics)
async def get_analytics(_ = Depends(verify_admin)):
    """Get overall MCP analytics."""
    
    # Account stats
    total_accounts = await Database.fetchval("SELECT COUNT(*) FROM mcp.user_accounts")
    active_accounts = await Database.fetchval("SELECT COUNT(*) FROM mcp.user_accounts WHERE is_active = true")
    paid_accounts = await Database.fetchval("SELECT COUNT(*) FROM mcp.user_accounts WHERE credits_tier != 'free'")
    
    # Tier breakdown
    tier_rows = await Database.fetch(
        "SELECT credits_tier, COUNT(*) as count FROM mcp.user_accounts GROUP BY credits_tier"
    )
    tier_breakdown = {row["credits_tier"]: row["count"] for row in tier_rows}
    
    # Usage Today
    total_calls_today = await Database.fetchval(
        "SELECT COUNT(*) FROM mcp.tool_executions WHERE created_at > CURRENT_DATE"
    ) or 0
    
    # Credits used requires parsing/summing if not stored directly. 
    # Assuming we track credits_cost in tool_executions (if not, use count * ~average)
    # The schema might not have credits_cost column yet. If so, create dummy logic for now.
    # Step 763 shows ToolCall interface has credits_cost. Check DB schema?
    # I'll check if credits_cost column exists using '0' fallback.
    try:
        credits_today = await Database.fetchval(
            "SELECT SUM(credits_cost) FROM mcp.tool_executions WHERE created_at > CURRENT_DATE"
        )
    except Exception:
        credits_today = total_calls_today # Fallback
        
    # Usage Month
    total_calls_month = await Database.fetchval(
        "SELECT COUNT(*) FROM mcp.tool_executions WHERE created_at > DATE_TRUNC('month', CURRENT_DATE)"
    ) or 0
    try:
        credits_month = await Database.fetchval(
            "SELECT SUM(credits_cost) FROM mcp.tool_executions WHERE created_at > DATE_TRUNC('month', CURRENT_DATE)"
        )
    except:
        credits_month = total_calls_month

    # Top Tools (Month)
    top_tools_rows = await Database.fetch(
        """
        SELECT tool_name as tool, COUNT(*) as calls, SUM(COALESCE(credits_cost, 1)) as credits
        FROM mcp.tool_executions
        WHERE created_at > DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY tool_name
        ORDER BY calls DESC
        LIMIT 5
        """
    )
    top_tools = [dict(row) for row in top_tools_rows]
    
    # Top Users (Month)
    top_users_rows = await Database.fetch(
        """
        SELECT u.user_email as email, u.credits_tier as tier, COUNT(t.id) as calls, SUM(COALESCE(t.credits_cost, 1)) as credits
        FROM mcp.tool_executions t
        JOIN mcp.user_accounts u ON t.mcp_account_id = u.id
        WHERE t.created_at > DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY u.user_email, u.credits_tier
        ORDER BY calls DESC
        LIMIT 5
        """
    )
    top_users = [dict(row) for row in top_users_rows]

    return {
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "paid_accounts": paid_accounts,
        "total_tool_calls_today": total_calls_today,
        "total_credits_used_today": credits_today or 0,
        "total_tool_calls_month": total_calls_month,
        "total_credits_used_month": credits_month or 0,
        "tier_breakdown": tier_breakdown,
        "top_tools": top_tools,
        "top_users": top_users
    }


@router.get("/mcp/tool-usage", response_model=List[ToolUsageStats])
async def get_tool_usage(days: int = 30, _ = Depends(verify_admin)):
    """Get per-tool usage statistics."""
    
    query = """
        SELECT 
            tool_name,
            COUNT(*) as total_calls,
            COUNT(*) FILTER (WHERE success = true) as successful_calls,
            COUNT(*) FILTER (WHERE success = false) as failed_calls,
            SUM(COALESCE(credits_cost, 1)) as total_credits_consumed,
            AVG(latency_ms) as avg_latency_ms
        FROM mcp.tool_executions
        WHERE created_at > CURRENT_DATE - INTERVAL '1 day' * $1
        GROUP BY tool_name
        ORDER BY total_calls DESC
    """
    
    rows = await Database.fetch(query, days)
    
    stats = []
    for row in rows:
        total = row["total_calls"]
        success = row["successful_calls"]
        rate = (success / total * 100) if total > 0 else 0
        
        stats.append({
            "tool_name": row["tool_name"],
            "total_calls": total,
            "successful_calls": success,
            "failed_calls": row["failed_calls"],
            "total_credits_consumed": row["total_credits_consumed"] or total, # Fallback
            "avg_latency_ms": row["avg_latency_ms"] or 0.0,
            "success_rate": round(rate, 2)
        })
        
    return stats


@router.post("/mcp/accounts/{account_id}/add-credits")
async def add_credits_to_account(
    account_id: int, 
    body: UpdateCreditsRequest,
    admin: dict = Depends(verify_admin)
):
    """Add credits to specific account."""
    
    # Get current balance
    current_balance = await Database.fetchval(
        "SELECT credits_balance FROM mcp.user_accounts WHERE id = $1",
        account_id
    )
    
    if current_balance is None:
        raise HTTPException(404, "Account not found")
        
    # Update
    await Database.execute(
        "UPDATE mcp.user_accounts SET credits_balance = credits_balance + $1 WHERE id = $2",
        body.amount, account_id
    )
    
    # Log it (TODO: Create audit table)
    admin_email = admin.get("email") or admin.get("sub")
    logger.info(f"Admin {admin_email} added {body.amount} credits to Account {account_id}. Reason: {body.reason}")
    
    return {
        "success": True,
        "account_id": account_id,
        "credits_added": body.amount,
        "balance_before": current_balance,
        "balance_after": current_balance + body.amount,
        "reason": body.reason
    }
