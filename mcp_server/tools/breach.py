"""
Breach Check Tools

Tools for checking data breach exposure for emails and phones.
"""
import logging
from .registry import tool
from .helpers import call_backend, normalize_phone

logger = logging.getLogger(__name__)


@tool(
    name="check_breaches",
    description="""
**What it does:** Checks if a phone number or email has been exposed in known data breaches.
**Input:** Email address OR Phone number.
**Returns:** List of breaches (for email) or breach categories (for phone), including dates.
**Best for:** Security audits, checking if a user's data is compromised ("Have I Been Pwned" style checks).

Cost: 1 credit""",
    credits=1,
    parameters={
        "identifier": {
            "type": "string",
            "description": "Email address or phone number to check",
            "required": True
        },
        "identifier_type": {
            "type": "string",
            "description": "Type of identifier: 'email' or 'phone' (auto-detected if not specified)",
            "required": False
        }
    },
    category="security"
)
async def check_breaches(identifier: str, identifier_type: str = None) -> dict:
    """Check breach exposure for an email or phone."""
    identifier = identifier.strip()
    
    # Auto-detect identifier type if not specified
    if identifier_type is None:
        if "@" in identifier:
            identifier_type = "email"
        else:
            identifier_type = "phone"
    
    identifier_type = identifier_type.lower()
    
    try:
        if identifier_type == "email":
            # Use new public Email Breach API
            response = await call_backend(
                f"/api/breach/email/{identifier}?fetch_if_missing=true",
                method="GET"
            )
            
            breaches = response.get("breaches", [])
            
            # Format breach data
            formatted_breaches = []
            for breach in breaches:
                # Handle both HIBP/old format and new API format
                formatted_breaches.append({
                    "name": breach.get("Name") or breach.get("name", "Unknown"),
                    "title": breach.get("Title") or breach.get("title", ""),
                    "breach_date": breach.get("BreachDate") or breach.get("breach_date", ""),
                    "data_types": breach.get("DataClasses") or breach.get("data_types", []),
                    "is_verified": breach.get("IsVerified") if "IsVerified" in breach else breach.get("is_verified", False),
                    "is_sensitive": breach.get("IsSensitive") if "IsSensitive" in breach else breach.get("is_sensitive", False)
                })
            
            return {
                "success": True,
                "identifier": identifier,
                "identifier_type": "email",
                "total_breaches": len(formatted_breaches),
                "breaches": formatted_breaches,
                "source": "outris",  # Hide underlying data source
                "summary": f"Found {len(formatted_breaches)} data breaches for this email." if formatted_breaches else "No breaches found for this email."
            }
            
        else:
            # Use new public Phone Breach API
            phone = normalize_phone(identifier)
            response = await call_backend(
                f"/api/breach/phone/{phone}?fetch_if_missing=true",
                method="GET"
            )
            
            breaches = response.get("breaches", [])
            categories = response.get("breach_categories", [])
            
            return {
                "success": True,
                "identifier": phone,
                "identifier_type": "phone",
                "total_breaches": response.get("total_breaches", 0),
                "breach_categories": categories,
                "earliest_date": response.get("earliest_date"),
                "latest_date": response.get("latest_date"),
                "source": "outris",  # Hide underlying data source
                "summary": f"Found in {len(breaches)} data sources across categories: {', '.join(categories)}." if breaches else "No breach records found for this phone."
            }
    
    except Exception as e:
        logger.error(f"Breach check failed: {e}")
        return {
            "success": False,
            "identifier": identifier,
            "identifier_type": identifier_type,
            "error": str(e)
        }
