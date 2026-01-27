"""
MCP Server Public Routes

Public endpoints for anonymous playground access.
Rate-limited to 3 tries per IP per day.
"""
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from ..core.database import Database
from ..tools.registry import get_tool, execute_tool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["Public"])

# Rate limiting configuration
DAILY_LIMIT = 3
ALLOWED_TOOLS = ["phone_to_name", "check_online_platforms", "digital_commerce"] # Matched with registry names

# In-memory rate limit store (for MVP - use Redis in production)
_rate_limit_store: Dict[str, Dict[str, Any]] = {}


class TryToolRequest(BaseModel):
    """Request model for anonymous tool trial."""
    tool: str
    inputs: Dict[str, Any]


class TryToolResponse(BaseModel):
    """Response model for anonymous tool trial."""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    remaining_tries: int
    demo_mode: bool = True


def _get_ip_hash(ip: str) -> str:
    """Hash IP for privacy."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _get_today_key() -> str:
    """Get date key for rate limiting."""
    return datetime.utcnow().strftime("%Y-%m-%d")


def _check_rate_limit(ip_hash: str) -> tuple[bool, int]:
    """
    Check if IP is rate limited.
    Returns (is_allowed, remaining_tries)
    """
    today = _get_today_key()
    
    # Cleanup old entries
    keys_to_delete = [k for k in _rate_limit_store if not k.endswith(today)]
    for k in keys_to_delete:
        del _rate_limit_store[k]
    
    key = f"{ip_hash}:{today}"
    usage = _rate_limit_store.get(key, {"count": 0})
    
    remaining = DAILY_LIMIT - usage["count"]
    return remaining > 0, max(0, remaining)


def _increment_usage(ip_hash: str) -> int:
    """Increment usage counter and return remaining tries."""
    today = _get_today_key()
    key = f"{ip_hash}:{today}"
    
    if key not in _rate_limit_store:
        _rate_limit_store[key] = {"count": 0}
    
    _rate_limit_store[key]["count"] += 1
    return max(0, DAILY_LIMIT - _rate_limit_store[key]["count"])


@router.get("/tools")
async def get_available_tools():
    """Get list of tools available in demo mode."""
    tools = []
    for tool_name in ALLOWED_TOOLS:
        tool_def = get_tool(tool_name)
        if tool_def:
            tools.append({
                "name": tool_name,
                "description": tool_def.description.split("\n")[0],
                "credits": tool_def.credits,
                "category": tool_def.category,
                "parameters": tool_def.parameters
            })
    
    return {
        "tools": tools,
        "daily_limit": DAILY_LIMIT,
        "demo_mode": True
    }


@router.post("/try-tool", response_model=TryToolResponse)
async def try_tool_anonymous(request: Request, body: TryToolRequest):
    """
    Anonymous playground endpoint with rate limiting.
    
    No auth required, but limited to 3 calls/day per IP.
    Only a subset of safe tools are allowed.
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    ip_hash = _get_ip_hash(client_ip)
    
    # Check rate limit
    is_allowed, remaining = _check_rate_limit(ip_hash)
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for IP hash: {ip_hash}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily limit reached. Sign up for 50 free credits!",
                "remaining_tries": 0,
                "demo_mode": True
            }
        )
    
    # Validate tool is allowed
    if body.tool not in ALLOWED_TOOLS:
        return TryToolResponse(
            success=False,
            error=f"Tool '{body.tool}' not available in demo mode. Available: {', '.join(ALLOWED_TOOLS)}",
            remaining_tries=remaining,
            demo_mode=True
        )
    
    # Get tool definition
    tool_def = get_tool(body.tool)
    if not tool_def:
        return TryToolResponse(
            success=False,
            error=f"Tool '{body.tool}' not found",
            remaining_tries=remaining,
            demo_mode=True
        )
    
    # Execute tool
    try:
        logger.info(f"Demo tool call: {body.tool} from IP hash {ip_hash}")
        result, execution_time = await execute_tool(body.tool, body.inputs)
        
        # Increment usage AFTER successful execution
        remaining = _increment_usage(ip_hash)
        
        return TryToolResponse(
            success=True,
            result=result,
            remaining_tries=remaining,
            demo_mode=True
        )
        
    except Exception as e:
        logger.error(f"Demo tool execution failed: {e}")
        return TryToolResponse(
            success=False,
            error=str(e),
            remaining_tries=remaining,
            demo_mode=True
        )


@router.get("/remaining-tries")
async def get_remaining_tries(request: Request):
    """Check remaining demo tries for current IP."""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    ip_hash = _get_ip_hash(client_ip)
    _, remaining = _check_rate_limit(ip_hash)
    
    return {
        "remaining_tries": remaining,
        "daily_limit": DAILY_LIMIT,
        "demo_mode": True
    }


# ============================================================================
# Demo Router for Platform Check (alternative prefix)
# ============================================================================

demo_router = APIRouter(prefix="/api/demo", tags=["Demo"])


@demo_router.get("/platform-check")
async def demo_platform_check(phone: str, request: Request):
    """
    Public demo endpoint for platform check - rate limited by IP.
    
    Used by landing page widget to showcase platform check capability.
    Returns simplified format suitable for demo display.
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    ip_hash = _get_ip_hash(client_ip)
    
    # Check rate limit
    is_allowed, remaining = _check_rate_limit(ip_hash)
    if not is_allowed:
        logger.warning(f"Demo platform check rate limit exceeded for IP hash: {ip_hash}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily limit reached. Sign up for 50 free credits!",
                "remaining_tries": 0
            }
        )
    
    # Validate phone format
    if not phone or len(phone) < 10:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid phone number format. Include country code (e.g., 919876543210)"}
        )
    
    try:
        logger.info(f"Demo platform check for phone: {phone[:4]}*** from IP hash {ip_hash}")
        
        # Execute the check_online_platforms tool
        result, execution_time = await execute_tool("check_online_platforms", {"phone": phone})
        
        # Increment usage AFTER successful execution
        remaining = _increment_usage(ip_hash)
        
        # Format response for demo display
        registered_platforms = result.get("registered_platforms", [])
        not_registered = result.get("not_registered", [])
        platforms_checked = result.get("platforms_checked", 0)
        
        # Build platforms dict in expected format
        platforms_dict = {}
        
        # Add registered platforms
        for platform in registered_platforms:
            platforms_dict[platform.lower()] = {
                "domain": platform.lower(),
                "exists": True,
                "status": "registered"
            }
        
        # Add not-registered platforms
        for platform in not_registered:
            platforms_dict[platform.lower()] = {
                "domain": platform.lower(),
                "exists": False,
                "status": "not_registered"
            }
        
        # If no platforms returned, return default set as unchecked
        if not platforms_dict:
            default_platforms = ["whatsapp", "instagram", "amazon", "twitter", 
                                "facebook", "telegram", "snapchat", "signal"]
            for platform in default_platforms:
                platforms_dict[platform] = {
                    "domain": platform,
                    "exists": False,
                    "status": "error"
                }
        
        return {
            "phone": result.get("phone", phone),
            "platforms_checked": platforms_checked or len(platforms_dict),
            "platforms": platforms_dict,
            "registered_platforms": registered_platforms,
            "remaining_tries": remaining,
            "execution_time": execution_time
        }
        
    except Exception as e:
        logger.error(f"Demo platform check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "remaining_tries": remaining}
        )
