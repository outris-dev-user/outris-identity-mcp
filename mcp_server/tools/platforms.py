"""
Platform Registration Check Tools

Tools for checking if a phone is registered on various platforms.
"""
import logging
from .registry import tool
from .helpers import call_backend, normalize_phone

logger = logging.getLogger(__name__)


@tool(
    name="check_online_platforms",
    description="""
**What it does:** Checks if a phone number is registered on major global platforms (Amazon, Instagram, Snapchat).
**Input:** Phone number (with or without country code).
**Returns:** Registration status (true/false) for each specific platform.
**Best for:** Digital footprint analysis, verifying if a number is "real" and active on social/shopping apps.
    
Cost: 1 credit""",
    credits=1,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number (with or without country code)",
            "required": True
        }
    },
    category="platforms"
)
async def check_online_platforms(phone: str, platforms: list[str] = None) -> dict:
    """Check platform registrations for a phone number via unified triage endpoint."""
    phone = normalize_phone(phone)
    
    try:
        # Call the unified platform triage endpoint
        response = await call_backend(
            "/api/platforms/check",
            method="POST",
            json_data={"phone": phone, "skip_cache": False}
        )
        
        registered_count = response.get("registered_count", 0)
        platforms_checked = response.get("platforms_checked", 0)

        return {
            "success": True,
            "phone": response.get("phone", phone),
            "country": response.get("country", "UNKNOWN"),
            "source": "outris",  # Hide underlying provider
            "platforms_checked": platforms_checked,
            "registered_count": registered_count,
            "registered_platforms": response.get("registered_platforms", []),
            "not_registered": response.get("not_registered", []),
            "from_cache": response.get("from_cache", False),
            "errors": response.get("errors"),
            "summary": f"Found {registered_count} platform registrations out of {platforms_checked} checked"
        }
    
    except Exception as e:
        logger.error(f"Platform check failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }
