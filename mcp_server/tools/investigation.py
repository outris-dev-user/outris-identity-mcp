"""
Investigation Tools

Phone-to-identity resolution tools.
"""
import logging
from .registry import tool
from .helpers import call_backend, normalize_phone, mask_sensitive
from ..core.context import current_account

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
    account = current_account.get()
    should_mask = not (account and account.allow_raw_records)
    
    try:
        response = await call_backend(
            f"/api/investigate/enhanced/phone/{phone}/complete",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        summary = response.get("summary", {})
        basic = response.get("basic_data", {})
        enhanced = response.get("enhanced_data", {})
        
        emails = basic.get("emails", [])
        if should_mask:
            emails = [mask_sensitive(e) for e in emails]
            
        alt_phones = basic.get("alternate_phones", [])
        if should_mask:
            alt_phones = [mask_sensitive(p) for p in alt_phones]

        # NEW: Mask names and addresses as well if requested
        names = basic.get("names", [])
        if should_mask:
            names = [mask_sensitive(n) for n in names]

        addresses = basic.get("addresses", [])
        if should_mask:
            masked_addresses = []
            for addr in addresses:
                if isinstance(addr, str):
                    masked_addresses.append(mask_sensitive(addr))
                elif isinstance(addr, dict):
                    if "full_address" in addr:
                        addr["full_address"] = mask_sensitive(addr["full_address"])
                    masked_addresses.append(addr)
            addresses = masked_addresses

        breach_categories = enhanced.get("breach_categories", [])
        # Mask breach sources often means hiding specific source names
        # Assuming breach_categories format is list of strings or dicts
        # If it's pure source names, we mask them or replace with 'Hidden Source'
        # For now, simplistic masking logic
        
        return {
            "success": True,
            "phone": phone,
            
            # Basic identity data
            "names": names,
            "emails": emails,
            "addresses": addresses,
            "alternate_phones": alt_phones,
            
            # Enhanced data
            "documents": enhanced.get("documents", []),
            "metadata": enhanced.get("metadata", {}),
            "breach_categories": breach_categories,
            
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
            "generated_at": response.get("generated_at"),
            "masked": should_mask
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
        
        names = response.get("names", [])
        if should_mask:
            names = [mask_sensitive(n) for n in names]
            
        return {
            "success": True,
            "phone": phone,
            "names": names,
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
    account = current_account.get()
    should_mask = not (account and account.allow_raw_records)
    
    try:
        response = await call_backend(
            f"/api/investigate/phone/{phone}/emails",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        emails = response.get("emails", [])
        if should_mask:
            emails = [mask_sensitive(e) for e in emails]
        
        return {
            "success": True,
            "phone": phone,
            "emails": emails,
            "count": response.get("count", 0),
            "masked": should_mask
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
    account = current_account.get()
    should_mask = not (account and account.allow_raw_records)
    
    try:
        response = await call_backend(
            f"/api/investigate/phone/{phone}/addresses",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        addresses = response.get("addresses", [])
        # Mask address fields while keeping structure
        if should_mask:
            masked_addresses = []
            for addr in addresses:
                # Assuming addr is a dict or string. Mask sensitive parts.
                if isinstance(addr, str):
                    masked_addresses.append(mask_sensitive(addr))
                elif isinstance(addr, dict):
                    # Mask everything except maybe country/state?
                    # For safety, mask full address string if present
                    if "full_address" in addr:
                        addr["full_address"] = mask_sensitive(addr["full_address"])
                    # If just fields, maybe tricky. Let's rely on masking string representation
                    masked_addresses.append(addr)
            addresses = masked_addresses

        return {
            "success": True,
            "phone": phone,
            "addresses": addresses,
            "count": response.get("count", 0),
            "masked": should_mask
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
    account = current_account.get()
    should_mask = not (account and account.allow_raw_records)
    
    try:
        response = await call_backend(
            f"/api/investigate/phone/{phone}/alternate-phones",
            method="GET",
            params={"fetch_if_missing": "true"}
        )
        
        alt_phones = response.get("alternate_phones", [])
        if should_mask:
            alt_phones = [mask_sensitive(p) for p in alt_phones]
        
        return {
            "success": True,
            "phone": phone,
            "alternate_phones": alt_phones,
            "count": response.get("count", 0),
            "masked": should_mask
        }
    
    except Exception as e:
        logger.error(f"Get alternate phones failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }
