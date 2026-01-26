"""
WhatsApp Tools

WhatsApp registration status checking.
"""
import logging
from .registry import tool
from .helpers import call_backend, normalize_phone

logger = logging.getLogger(__name__)


@tool(
    name="check_whatsapp",
    description="""Check if a phone number is registered on WhatsApp platform.

Part of platform check suite - specifically for WhatsApp verification.
Use check_online_platforms for multi-platform checks (Instagram, Amazon, etc.)
Use this tool when you ONLY need WhatsApp status (faster, lower cost).

Returns: Registration status (registered/not_registered), last seen status,
about text (if public), and profile picture availability.

Use when: User asks specifically about WhatsApp presence, wants to know if
a number is on WhatsApp, or needs single-platform WhatsApp verification.

Example queries:
- "Is 9876543210 on WhatsApp?"
- "Check WhatsApp status for +91 98765 43210"
- "Does this number have WhatsApp?"
- "Verify WhatsApp registration"
- "Check if they use WhatsApp"

Cost: 1 credit (vs 2 credits for full platform check)""",
    credits=1,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number with country code",
            "required": True
        }
    },
    category="platforms"  # Changed from "social" to "platforms"
)
async def check_whatsapp(phone: str) -> dict:
    """Check WhatsApp registration status."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            f"/api/whatsapp/{phone}",
            method="GET"
        )
        
        # Normalize response format
        is_registered = response.get("whatsapp_status", False)
        if isinstance(is_registered, str):
            is_registered = is_registered.lower() in ("true", "yes", "registered", "1")
        
        return {
            "success": True,
            "phone": phone,
            "registered": is_registered,
            "status": "registered" if is_registered else "not_registered",
            "last_checked": response.get("last_checked"),
            "profile_picture": response.get("has_profile_picture"),
            "about": response.get("about")
        }
    
    except Exception as e:
        logger.error(f"WhatsApp check failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }
