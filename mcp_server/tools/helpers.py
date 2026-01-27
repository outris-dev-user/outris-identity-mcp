"""
Helper utilities for tool implementations.
"""
import httpx
import logging
from typing import Optional, Any

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Shared HTTP client
_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            follow_redirects=True
        )
    return _client


async def close_http_client() -> None:
    """Close shared HTTP client."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def call_backend(
    endpoint: str,
    method: str = "GET",
    params: dict = None,
    json_data: dict = None,
    api_key: str = None
) -> dict:
    """
    Call the backend API (number-lookup).
    
    Args:
        endpoint: API endpoint (e.g., "/api/kyc/pan/details")
        method: HTTP method
        params: Query parameters
        json_data: JSON body for POST requests
        api_key: API key (uses configured backend key if not provided)
    
    Returns:
        Response JSON as dict
    """
    settings = get_settings()
    client = await get_http_client()
    
    url = f"{settings.backend_url}{endpoint}"
    headers = {
        "X-API-Key": api_key or settings.backend_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    logger.debug(f"Calling backend: {method} {url}")
    
    try:
        if method.upper() == "GET":
            response = await client.get(url, params=params, headers=headers)
        elif method.upper() == "POST":
            response = await client.post(url, params=params, json=json_data, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Backend call failed: {e}")
        raise


def normalize_phone(phone: str) -> str:
    """Normalize a phone number to standard format."""
    # Remove common prefixes and formatting
    phone = phone.strip()
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Remove + prefix
    if phone.startswith("+"):
        phone = phone[1:]
    
    # Add 91 prefix for 10-digit Indian numbers
    if len(phone) == 10 and phone[0] in "6789":
        phone = "91" + phone
    
    return phone


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive data, showing only last N characters."""
    if not value or len(value) <= visible_chars:
        return value
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def summarize_response(response: dict, max_items: int = 5) -> dict:
    """Create a summary of a response for logging (truncate lists)."""
    summary = {}
    for key, value in response.items():
        if isinstance(value, list):
            summary[key] = f"[{len(value)} items]" if len(value) > max_items else value
        elif isinstance(value, dict):
            summary[key] = summarize_response(value, max_items)
        else:
            summary[key] = value
    return summary
