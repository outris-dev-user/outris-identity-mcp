"""
OAuh 2.0 Identity Provider Routes
=================================
Implements OAuth 2.0 endpoints for third-party integration (Claude.ai).

Endpoints:
- GET /.well-known/oauth-authorization-server: Discovery metadata
- POST /api/oauth/authorize: Generate authorization code (Internal use by Dashboard)
- POST /api/oauth/token: Exchange code for access token (Public use by Claude)

Flow:
1. Claude sends user to Dashboard /oauth/authorize -> Authentication & Consent
2. Dashboard calls Backend POST /api/oauth/authorize -> Returns code
3. Dashboard redirects user back to Claude with code
4. Claude calls Backend POST /api/oauth/token with code -> Returns JWT Access Token
"""
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request, Form
from pydantic import BaseModel
from fastapi.responses import JSONResponse

from ..core.database import Database
from ..core.config import get_settings
from .user_routes import get_current_user, generate_mcp_key, get_mcp_account_by_email, create_jwt_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["OAuth 2.0"])

# ============================================================================
# Models
# ============================================================================

class OAuthAuthorizeRequest(BaseModel):
    """Request to generate authorization code (from Dashboard)."""
    client_id: str
    response_type: str
    redirect_uri: str
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    state: Optional[str] = None
    scope: Optional[str] = None

class OAuthAuthorizeResponse(BaseModel):
    """Response with authorization code."""
    code: str
    state: Optional[str]
    redirect_uri: str

class OAuthTokenResponse(BaseModel):
    """OAuth 2.0 Token Response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None

# ============================================================================
# Discovery Endpoint
# ============================================================================

@router.get("/.well-known/oauth-authorization-server")
async def oauth_discovery():
    """
    OAuth 2.0 Discovery Endpoint for Claude.ai.
    """
    settings = get_settings()
    # Base URL for the dashboard (where authorization happens)
    # Assumes dashboard is hosted at portal.outris.com or configured via env
    # For now we use the backend API base for token and specific known dashboard URL
    
    # We need to know the Dashboard URL to tell Claude where to send the user
    # This should be configured. Defaults to https://portal.outris.com
    dashboard_url = "https://portal.outris.com" 
    
    api_base_url = "https://rail.outris.com" # Or derive from request
    
    return {
        "issuer": api_base_url,
        "authorization_endpoint": f"{dashboard_url}/oauth/authorize",
        "token_endpoint": f"{api_base_url}/api/oauth/token",
        "token_endpoint_auth_methods_supported": ["client_secret_post", "none"], # 'none' for PKCE public clients
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["mcp"],
    }

# ============================================================================
# Authorize Endpoint (Internal - called by Dashboard)
# ============================================================================

@router.post("/api/oauth/authorize", response_model=OAuthAuthorizeResponse)
async def authorize_user(
    request: OAuthAuthorizeRequest,
    req: Request
):
    """
    Generate authorization code.
    Authenticated endpoint - requires User JWT.
    """
    # 1. Verify User
    auth_header = req.headers.get("Authorization", "")
    user = await get_current_user(auth_header)
    
    # 2. Validate Request
    if request.response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")
    
    # In a real implementation, we would validate client_id against a registered clients table.
    # For now, we allow the known Claude ID or 'claude'
    # valid_clients = ["claude", "https://claude.ai"]
    # if request.client_id not in valid_clients:
    #     logger.warning(f"Unknown client_id: {request.client_id}")
    
    # 3. Generate Code
    code = secrets.token_urlsafe(32)
    # Expires in 10 minutes
    expires_at = datetime.now() + timedelta(minutes=10)
    
    # 4. Store Code
    # Table: mcp.oauth_codes
    try:
        await Database.execute(
            """
            INSERT INTO mcp.oauth_codes (
                code, user_email, user_id, client_id, redirect_uri, 
                code_challenge, code_challenge_method, 
                expires_at, used, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE, NOW())
            """,
            code,
            user["email"],
            user.get("user_id"),
            request.client_id,
            request.redirect_uri,
            request.code_challenge,
            request.code_challenge_method,
            expires_at
        )
    except Exception as e:
        logger.error(f"Failed to store oauth code: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return OAuthAuthorizeResponse(
        code=code,
        state=request.state,
        redirect_uri=request.redirect_uri
    )

# ============================================================================
# Token Endpoint (Public - called by Claude)
# ============================================================================

@router.post("/api/oauth/token", response_model=OAuthTokenResponse)
async def exchange_token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    code_verifier: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None)
):
    """
    Exchange authorization code for access token.
    """
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Unsupported grant_type")
    
    # 1. Find Code
    row = await Database.fetchrow(
        """
        SELECT code, user_email, user_id, redirect_uri, code_challenge, code_challenge_method, expires_at, used
        FROM mcp.oauth_codes
        WHERE code = $1
        """,
        code
    )
    
    if not row:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    # 2. Check Validity
    if row["used"]:
        raise HTTPException(status_code=400, detail="Code already used")
        
    if datetime.now() > row["expires_at"]:
        raise HTTPException(status_code=400, detail="Code expired")
        
    if row["redirect_uri"] != redirect_uri:
        raise HTTPException(status_code=400, detail="Redirect URI mismatch")
        
    # 3. Verify PKCE (if challenge exists)
    if row["code_challenge"]:
        if not code_verifier:
             raise HTTPException(status_code=400, detail="Missing code_verifier")
        
        # S256
        if row["code_challenge_method"] == "S256":
            import base64
            # SHA256(code_verifier) -> Base64URL
            digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
            calculated = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
            
            if calculated != row["code_challenge"]:
                 raise HTTPException(status_code=400, detail="PKCE verification failed")
        else:
            # plain
             if code_verifier != row["code_challenge"]:
                 raise HTTPException(status_code=400, detail="PKCE verification failed")

    # 4. Mark Used
    await Database.execute("UPDATE mcp.oauth_codes SET used = TRUE WHERE code = $1", code)
    
    # 5. Issue Token
    # We reissue a standard User JWT. 
    # In future, we might want a specific OAuth token scope, but for now, 
    # re-using the User JWT allows seamless integration with existing tools.
    
    # We need a display name for the token. Fetch from user accounts or use email parts.
    display_name = row["user_email"].split("@")[0] # Callback to user service if needed
    
    # We need the JWT secret. Import from existing auth module or config.
    # Note: user_routes has create_jwt_token logic? No, it only validates. 
    # We need to replicate creation or import it.
    
    settings = get_settings()
    if not settings.jwt_secret_key:
         raise HTTPException(status_code=500, detail="Server config error")

    # generate generic token
    payload = {
        "sub": row["user_email"],
        "email": row["user_email"],
        "role": "user", # Default to user
        "displayName": display_name,
        "exp": datetime.utcnow() + timedelta(days=30), # Long lived for MCP?
        "aud": "mcp-server",
        "iss": "outris-oauth"
    }
    
    import jwt # Helper import
    access_token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    
    return OAuthTokenResponse(
        access_token=access_token,
        expires_in=30 * 24 * 60 * 60, # 30 days
        scope="mcp"
    )
