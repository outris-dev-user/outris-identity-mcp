"""
TraceFlow Tool

Comprehensive phone investigation combining multiple data sources.
"""
import logging
from .registry import tool
from .helpers import call_backend, normalize_phone

logger = logging.getLogger(__name__)


@tool(
    name="traceflow",
    description="""Comprehensive phone investigation combining multiple data sources.

This is the most powerful investigation tool - it aggregates data from:
- Names, emails, addresses linked to the phone
- Documents and metadata (IDs, devices, IPs)
- Social media profiles (India-specific platforms)
- Digital footprint analysis
- Breach category summary

Returns a complete profile with data richness score (0-100).

Use when: User wants a complete investigation, deep dive into a phone number,
or comprehensive background check. More expensive but saves multiple API calls.

Example queries:
- "Do a full investigation on 9876543210"
- "Run traceflow on this number"
- "Get me everything you can find about +91 98765 43210"
- "Comprehensive phone lookup"

Cost: 5 credits (recommended for thorough investigations)""",
    credits=5,
    parameters={
        "phone": {
            "type": "string",
            "description": "Phone number to investigate",
            "required": True
        }
    },
    category="investigation",
    enabled=False  # Disabled for initial launch - too expensive
)
async def traceflow(phone: str) -> dict:
    """Run comprehensive phone investigation."""
    phone = normalize_phone(phone)
    
    try:
        response = await call_backend(
            f"/api/traceflow/{phone}",
            method="GET"
        )
        
        # Extract and structure the response
        investigate = response.get("investigate", {})
        social = response.get("social", {})
        summary = response.get("summary", {})
        
        return {
            "success": True,
            "phone": response.get("phone", phone),
            "country": response.get("phone_country", "UNKNOWN"),
            "request_id": response.get("request_id"),
            
            # Basic identity data
            "names": investigate.get("basic_data", {}).get("names", []),
            "emails": investigate.get("basic_data", {}).get("emails", []),
            "addresses": investigate.get("basic_data", {}).get("addresses", []),
            "alternate_phones": investigate.get("basic_data", {}).get("alternate_phones", []),
            
            # Enhanced data
            "documents": investigate.get("enhanced_data", {}).get("documents", []),
            "metadata": investigate.get("enhanced_data", {}).get("metadata", {}),
            "breach_categories": investigate.get("enhanced_data", {}).get("breach_categories", []),
            
            # Social presence
            "social_profiles": {
                "global": social.get("global_profiles", []),
                "india": social.get("india_profiles", []),
                "total_count": social.get("total_profiles", 0)
            },
            
            # Summary statistics
            "summary": {
                "names_found": summary.get("names_found", 0),
                "emails_found": summary.get("emails_found", 0),
                "addresses_found": summary.get("addresses_found", 0),
                "alternate_phones_found": summary.get("alternate_phones_found", 0),
                "social_profiles_found": summary.get("social_profiles_found", 0),
                "data_richness_score": summary.get("data_richness_score", 0)
            },
            
            "data_sources": response.get("data_sources", []),
            "generated_at": response.get("generated_at")
        }
    
    except Exception as e:
        logger.error(f"TraceFlow failed: {e}")
        return {
            "success": False,
            "phone": phone,
            "error": str(e)
        }
