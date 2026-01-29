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
    """
    Smart masking for sensitive data.
    
    Strategies:
    - Email (>7 chars): sa***ab***i@gmail.com (First 2, Middle 2, Last 1)
    - Email (short): j***n@gmail.com
    - Phone: 91***5***7890 (First 2, Middle 1, Last 4)
    - Regular String: Sau...thi (First 3...Last 3)
    """
    if not value:
        return value
        
    value = str(value).strip()
    
    # Email Masking
    if "@" in value and "." in value:
        try:
            local, domain = value.split("@", 1)
            if len(local) > 7:
                # Long email: Show First 2, Middle 2, Last 1
                mid = len(local) // 2
                masked_local = f"{local[:2]}***{local[mid-1:mid+1]}***{local[-1]}"
            elif len(local) > 2:
                # Short email: Keep first and last
                masked_local = f"{local[0]}***{local[-1]}"
            else:
                masked_local = local[0] + "***" 
            return f"{masked_local}@{domain}"
        except:
            pass # Fallback
            
    # Phone Masking (numeric check)
    if value.replace("+", "").isdigit() and len(value) >= 10:
        # Show First 2...Middle 1...Last 4
        # e.g., 919876543210 -> 91***5***3210
        mid = len(value) // 2
        return f"{value[:2]}***{value[mid]}***{value[-4:]}"
        
    # Short strings
    if len(value) <= 4:
        return value[0] + "*" * (len(value)-1)
        
    # General String (Names/Addresses)
    if len(value) > 8:
        # Keep first 3 and last 3
        return f"{value[:3]}...{value[-3:]}"
    else:
        # Keep first 1 and last 1
        return f"{value[0]}***{value[-1]}"


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
