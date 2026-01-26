"""
Investigation Tools

Phone-to-identity resolution tools.
"""
import logging
from .registry import tool
from .helpers import call_backend, normalize_phone

logger = logging.getLogger(__name__)


@tool(
    name="get_identity_profile",
    description="""
**What it does:** Comprehensive identity report. Fetches names, emails, addresses, metadata, and risk scores in one go.
**Input:** Phone number.
**Returns:** Complete JSON profile containing all linked entities.
**Best for:** Deep investigations where you need the "full picture" immediately.

Cost: 3 credits""",
    credits=3,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number",
            "required": True
        }
    },
    category="investigation"
)
async def get_identity_profile(phone: str) -> dict:
    """Get complete identity profile."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            f"/api/investigate/enhanced/phone/{phone}/complete",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        summary = response.get("summary", {})
        basic = response.get("basic_data", {})
        enhanced = response.get("enhanced_data", {})
        
        return {
            "success": True,
            "phone": phone,
            
            # Basic identity data
            "names": basic.get("names", []),
            "emails": basic.get("emails", []),
            "addresses": basic.get("addresses", []),
            "alternate_phones": basic.get("alternate_phones", []),
            
            # Enhanced data
            "documents": enhanced.get("documents", []),
            "metadata": enhanced.get("metadata", {}),
            "breach_categories": enhanced.get("breach_categories", []),
            
            # Summary
            "summary": {
                "names_count": summary.get("names_count", 0),
                "emails_count": summary.get("emails_count", 0),
                "addresses_count": summary.get("addresses_count", 0),
                "alternate_phones_count": summary.get("alternate_phones_count", 0),
                "documents_count": summary.get("documents_count", 0),
                "person_ids_count": summary.get("person_ids_count", 0)
            },
            
            "person_ids": response.get("person_ids", []),
            "generated_at": response.get("generated_at")
        }
    
    except Exception as e:
        logger.error(f"Identity profile failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }


@tool(
    name="get_name",
    description="""
**What it does:** identifying the owner name of a phone number.
**Input:** Phone number (with or without country code).
**Returns:** List of full names linked to this phone with confidence scores.
**Best for:** KYC verification, caller ID, finding out "who called me".

Cost: 2 credits""",
    credits=2,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number",
            "required": True
        }
    },
    category="investigation"
)
async def get_name(phone: str) -> dict:
    """Get names for a phone number."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            f"/api/investigate/phone/{phone}/names",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        return {
            "success": True,
            "phone": phone,
            "names": response.get("names", []),
            "count": response.get("count", 0)
        }
    
    except Exception as e:
        logger.error(f"Get names failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }


@tool(
    name="get_email",
    description="""
**What it does:** Finds email addresses linked to a phone number.
**Input:** Phone number.
**Returns:** List of email addresses with confidence scores.
**Best for:** Digital footprint analysis, finding contact details, or cross-referencing identities.

Cost: 2 credits""",
    credits=2,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number",
            "required": True
        }
    },
    category="investigation"
)
async def get_email(phone: str) -> dict:
    """Get emails for a phone number."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            f"/api/investigate/phone/{phone}/emails",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        return {
            "success": True,
            "phone": phone,
            "emails": response.get("emails", []),
            "count": response.get("count", 0)
        }
    
    except Exception as e:
        logger.error(f"Get emails failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }


@tool(
    name="get_address",
    description="""
**What it does:** Finds physical addresses associated with a phone number.
**Input:** Phone number.
**Returns:** List of addresses with metadata (e.g., "shipping", "billing", "home") and dates.
**Best for:** Fraud investigation, delivery verification, and location analysis.

Cost: 2 credits""",
    credits=2,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number",
            "required": True
        }
    },
    category="investigation"
)
async def get_address(phone: str) -> dict:
    """Get addresses for a phone number."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            f"/api/investigate/phone/{phone}/addresses",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        return {
            "success": True,
            "phone": phone,
            "addresses": response.get("addresses", []),
            "count": response.get("count", 0)
        }
    
    except Exception as e:
        logger.error(f"Get addresses failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }


@tool(
    name="get_alternate_phones",
    description="""Get other phone numbers belonging to the same person.

Returns: List of alternate phone numbers linked through shared identities
(same name, email, or address).

Use when: User wants to find all phones associated with a person.

Example queries:
- "What other phones does this person have?"
- "Find alternate numbers for 9876543210"
- "Are there other phones linked to this one?"

Cost: 2 credits""",
    credits=2,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number",
            "required": True
        }
    },
    category="investigation"
)
async def get_alternate_phones(phone: str) -> dict:
    """Get alternate phone numbers."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            f"/api/investigate/phone/{phone}/alternate-phones",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        return {
            "success": True,
            "phone": phone,
            "alternate_phones": response.get("alternate_phones", []),
            "count": response.get("count", 0)
        }
    
    except Exception as e:
        logger.error(f"Get alternate phones failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }
