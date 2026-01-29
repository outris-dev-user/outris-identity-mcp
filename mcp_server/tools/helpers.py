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
    Smart masking for sensitive data that PRESERVES LENGTH.
    
    Strategies:
    - Email (>7 chars local): sa***ab***i@gmail.com (First 2, Middle 2, Last 1 kept)
    - Phone (>=10 digits): 91***5***7890 (First 2, Middle 1, Last 4 kept)
    - General (>8 chars): Sau...thi (First 3, Last 3 kept)
    - General (short): J**n (First 1, Last 1 kept)
    """
    if not value:
        return value
        
    value = str(value).strip()
    length = len(value)
    
    # Helper to mask string while keeping specific indices
    def apply_mask(text: str, keep_indices: set) -> str:
        return "".join([c if i in keep_indices else "*" for i, c in enumerate(text)])

    # Email Masking
    if "@" in value and "." in value:
        try:
            local, domain = value.split("@", 1)
            local_len = len(local)
            
            if local_len > 7:
                # Keep First 2, Middle 2, Last 1
                mid = local_len // 2
                indices = {0, 1, mid-1, mid, local_len-1}
                masked_local = apply_mask(local, indices)
            elif local_len > 2:
                # Keep First 1, Last 1
                indices = {0, local_len-1}
                masked_local = apply_mask(local, indices)
            else:
                # Keep First 1
                masked_local = local[0] + "*" * (local_len - 1)
                
            return f"{masked_local}@{domain}"
        except:
            pass # Fallback
            
    # Phone Masking (numeric check)
    if value.replace("+", "").isdigit() and length >= 10:
        # Keep First 2, Middle 1, Last 4
        mid = length // 2
        indices = {0, 1, mid}
        # Add last 4 indices
        for i in range(length - 4, length):
            indices.add(i)
            
        return apply_mask(value, indices)
        
    # General String (Names/Addresses)
    if length > 8:
        # Keep First 3, Last 3
        indices = {0, 1, 2, length-3, length-2, length-1}
        return apply_mask(value, indices)
    elif length > 2:
        # Keep First 1, Last 1
        indices = {0, length-1}
        return apply_mask(value, indices)
    else:
        # Keep First 1
        return value[0] + "*" * (length - 1)


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
