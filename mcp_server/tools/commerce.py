"""
Digital Commerce Analysis Tools

Tools for analyzing e-commerce and digital commerce activity.
"""
import logging
from .registry import tool
from .helpers import call_backend, normalize_phone

logger = logging.getLogger(__name__)


@tool(
    name="check_digital_commerce_activity",
    description="""
**What it does:** Checks if a phone number has been used for any digital commerce activity (ecommerce, travel, quick-commerce).
**Input:** Phone number (Indian numbers only, add ISD code infront).
**Returns:** Boolean flags for overall commerce types, activity timeline, and demographics if available.
**Best for:** Assessing if a phone number belongs to a real, active consumer vs. a throwaway number.

Cost: 1 credit""",
    credits=1,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number (with or without country code)",
            "required": True
        },
        "include_demographics": {
            "type": "boolean",
            "description": "Include age/gender estimation (default: true)",
            "required": False
        }
    },
    category="commerce"
)
async def check_digital_commerce_activity(phone: str, include_demographics: bool = True) -> dict:
    """Analyze digital commerce activity for a phone number."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            "/api/commerce/OS_digitalCommerce",
            method="POST",
            json_data={
                "phone": phone,
                "fetch_if_missing": True,
                "include_demographics": include_demographics,
                "include_breach_details": True
            }
        )
        
        # Build structured response
        result = {
            "success": True,
            "phone": phone,
            "has_commerce_activity": response.get("has_digitalcommerce", False),
            "commerce_types": {
                "ecommerce": response.get("has_ecommerce", False),
                "quick_commerce": response.get("has_quickcommerce", False),
                "travel_commerce": response.get("has_travelcommerce", False)
            },
            "timeline": {
                "first_seen": response.get("first_seen"),
                "last_seen": response.get("last_seen")
            },
            "activity_count": response.get("total_commerce_breaches", 0),
            "linked_identities": {
                "email_count": response.get("identity_email_count", 0),
                "name_count": response.get("identity_name_count", 0)
            }
        }
        
        # Add demographics if available
        if include_demographics and response.get("demographics"):
            result["demographics"] = {
                "age": response["demographics"].get("age"),
                "age_range": response["demographics"].get("age_range"),
                "gender": response["demographics"].get("gender"),
                "confidence": response["demographics"].get("confidence_score")
            }
        
        # Add platform summary
        breach_summary = response.get("breach_summary", [])
        platforms = []
        for breach in breach_summary:
            if breach.get("category"):
                platforms.append({
                    "category": breach["category"],
                    "types": breach.get("commerce_types", [])
                })
        result["platforms"] = platforms
        
        # Generate summary text
        if result["has_commerce_activity"]:
            types_active = [k for k, v in result["commerce_types"].items() if v]
            result["summary"] = (
                f"Active on {', '.join(types_active)}. "
                f"First activity: {result['timeline']['first_seen'] or 'unknown'}."
            )
        else:
            result["summary"] = "No digital commerce activity found for this phone number."
        
        return result
    
    except Exception as e:
        logger.error(f"Commerce check failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }
