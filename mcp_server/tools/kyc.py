"""
KYC Verification Tools

Tools for identity verification (PAN, Aadhaar, etc.)
"""
import logging
from .registry import tool
from .helpers import call_backend

logger = logging.getLogger(__name__)


@tool(
    name="verify_pan",
    description="""Verify a PAN (Permanent Account Number) and retrieve holder details.

Returns: Full name, date of birth, gender, PAN type (individual/company), 
Aadhaar linking status, and validity.

Use when: User asks to verify a PAN, check PAN validity, look up PAN details,
validate a PAN card, or get information about a PAN holder.

Example queries:
- "Verify PAN ABCDE1234F"
- "Who does PAN XYZAB5678C belong to?"
- "Check if this PAN is valid: PQRST9012A"

Cost: 1 credit""",
    credits=1,
    parameters={
        "pan": {
            "type": "string",
            "description": "10-character PAN number (e.g., ABCDE1234F)",
            "required": True
        }
    },
    category="kyc",
    enabled=False  # Disabled for initial launch
)
async def verify_pan(pan: str) -> dict:
    """Verify a PAN number and get holder details."""
    # Normalize PAN
    pan = pan.upper().strip()
    
    # Basic validation
    if len(pan) != 10:
        return {
            "success": False,
            "error": "Invalid PAN format. PAN must be exactly 10 characters."
        }
    
    # Call backend
    try:
        response = await call_backend(
            f"/kyc/pan/{pan}/details",
            method="GET",
            params={"consent": "true"}
        )
        
        return {
            "success": True,
            "pan": pan,
            "full_name": response.get("full_name"),
            "first_name": response.get("first_name"),
            "middle_name": response.get("middle_name"),
            "last_name": response.get("last_name"),
            "date_of_birth": response.get("date_of_birth"),
            "gender": response.get("gender"),
            "pan_type": response.get("pan_type", "Individual"),
            "aadhaar_linked": response.get("aadhaar_linked"),
            "valid": response.get("success", True)
        }
    
    except Exception as e:
        logger.error(f"PAN verification failed: {e}")
        return {
            "success": False,
            "pan": pan,
            "error": str(e)
        }


@tool(
    name="verify_pan_detailed",
    description="""Get comprehensive PAN verification with additional details.

Returns: Everything from verify_pan PLUS aadhaar_seeding_status,
last_updated date, name variations, and company details if corporate PAN.

Use when: Need detailed PAN verification, compliance checks, corporate PAN
analysis, or when you need more than basic verification.

Example queries:
- "Get full details for PAN ABCDE1234F"
- "Do a comprehensive PAN check on XYZAB5678C"
- "I need detailed PAN verification for compliance"

Cost: 2 credits""",
    credits=2,
    parameters={
        "pan": {
            "type": "string",
            "description": "10-character PAN number",
            "required": True
        }
    },
    category="kyc",
    enabled=False  # Disabled for initial launch
)
async def verify_pan_detailed(pan: str) -> dict:
    """Get comprehensive PAN verification with additional details."""
    pan = pan.upper().strip()
    
    if len(pan) != 10:
        return {
            "success": False,
            "error": "Invalid PAN format. PAN must be exactly 10 characters."
        }
    
    try:
        # Call backend with advanced provider
        response = await call_backend(
            f"/kyc/pan/{pan}/details",
            method="GET",
            params={"consent": "true", "provider": "v2"}  # Advanced provider
        )
        
        return {
            "success": True,
            "pan": pan,
            "full_name": response.get("full_name"),
            "first_name": response.get("first_name"),
            "middle_name": response.get("middle_name"),
            "last_name": response.get("last_name"),
            "date_of_birth": response.get("date_of_birth"),
            "gender": response.get("gender"),
            "pan_type": response.get("pan_type", "Individual"),
            "aadhaar_linked": response.get("aadhaar_linked"),
            "aadhaar_seeding_status": response.get("aadhaar_seeding_status"),
            "last_updated": response.get("last_updated"),
            "name_on_card": response.get("name_on_card"),
            "valid": response.get("success", True),
            # Company details (if corporate PAN)
            "company_name": response.get("company_name"),
            "company_status": response.get("company_status"),
            "registration_date": response.get("registration_date")
        }
    
    except Exception as e:
        logger.error(f"Detailed PAN verification failed: {e}")
        return {
            "success": False,
            "pan": pan,
            "error": str(e)
        }


@tool(
    name="mobile_to_pan",
    description="""Find PAN number associated with a mobile number.

Returns: PAN number and holder name if found in KYC databases.
Provide name parameters for better match accuracy.

Use when: User wants to find PAN from a phone number, reverse lookup
mobile to PAN, or verify PAN-mobile linkage.

Example queries:
- "Find PAN for mobile 9876543210"
- "What PAN is linked to this phone?"
- "Lookup PAN by mobile number"

Cost: 2 credits""",
    credits=2,
    parameters={
        "mobile": {
            "type": "string",
            "description": "10-digit mobile number",
            "required": True
        },
        "first_name": {
            "type": "string",
            "description": "First name (optional, improves accuracy)",
            "required": False
        },
        "last_name": {
            "type": "string",
            "description": "Last name (optional, improves accuracy)",
            "required": False
        }
    },
    category="kyc",
    enabled=False  # Disabled for initial launch
)
async def mobile_to_pan(mobile: str, first_name: str = None, last_name: str = None) -> dict:
    """Find PAN from mobile number."""
    mobile = mobile.strip()

    if len(mobile) != 10:
        return {
            "success": False,
            "error": "Invalid mobile format. Mobile must be exactly 10 digits."
        }

    try:
        params = {"mobile": mobile}
        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name

        response = await call_backend(
            f"/kyc/mobile/{mobile}/pan",
            method="GET",
            params=params
        )

        return {
            "success": True,
            "mobile": mobile,
            "pan": response.get("pan"),
            "full_name": response.get("full_name"),
            "match_confidence": response.get("match_confidence", "unknown"),
            "found": bool(response.get("pan"))
        }

    except Exception as e:
        logger.error(f"Mobile to PAN lookup failed: {e}")
        return {
            "success": False,
            "mobile": mobile,
            "error": str(e)
        }


@tool(
    name="mobile_to_kyc",
    description="""Get complete KYC details from a mobile number.

Returns: PAN, full name, date of birth, gender, Aadhaar linking status,
and other KYC data if available in databases.

Use when: User needs full KYC profile from mobile, comprehensive identity
verification, or detailed background check using phone number.

Example queries:
- "Get full KYC for mobile 9876543210"
- "What KYC data is linked to this phone?"
- "Do a KYC lookup by mobile number"

Cost: 3 credits""",
    credits=3,
    parameters={
        "mobile": {
            "type": "string",
            "description": "10-digit mobile number",
            "required": True
        },
        "first_name": {
            "type": "string",
            "description": "First name (optional, improves accuracy)",
            "required": False
        },
        "last_name": {
            "type": "string",
            "description": "Last name (optional, improves accuracy)",
            "required": False
        }
    },
    category="kyc",
    enabled=False  # Disabled for initial launch
)
async def mobile_to_kyc(mobile: str, first_name: str = None, last_name: str = None) -> dict:
    """Get full KYC from mobile number."""
    mobile = mobile.strip()

    if len(mobile) != 10:
        return {
            "success": False,
            "error": "Invalid mobile format. Mobile must be exactly 10 digits."
        }

    try:
        params = {"mobile": mobile}
        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name

        response = await call_backend(
            f"/kyc/mobile/{mobile}/kyc",
            method="GET",
            params=params
        )

        return {
            "success": True,
            "mobile": mobile,
            "pan": response.get("pan"),
            "full_name": response.get("full_name"),
            "first_name": response.get("first_name"),
            "middle_name": response.get("middle_name"),
            "last_name": response.get("last_name"),
            "date_of_birth": response.get("date_of_birth"),
            "gender": response.get("gender"),
            "aadhaar_linked": response.get("aadhaar_linked"),
            "aadhaar_last_4": response.get("aadhaar_last_4"),
            "match_confidence": response.get("match_confidence", "unknown"),
            "data_source": response.get("data_source"),
            "found": bool(response.get("pan"))
        }

    except Exception as e:
        logger.error(f"Mobile to KYC lookup failed: {e}")
        return {
            "success": False,
            "mobile": mobile,
            "error": str(e)
        }


# Future tools can be added here
# @tool(name="verify_aadhaar", ...)
