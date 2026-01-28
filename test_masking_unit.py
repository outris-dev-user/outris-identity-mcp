
import asyncio
import json
from unittest.mock import patch, MagicMock
from mcp_server.tools.investigation import get_email, get_identity_profile
from mcp_server.core.auth import MCPAccount
from mcp_server.core.context import current_account

async def test_masking_logic():
    print("Starting Masking Unit Tests...")
    print("==============================")

    # 1. Mock Backend Response
    mock_backend_data = {
        "emails": ["test.user@outris.com", "private@gmail.com"],
        "alternate_phones": ["+919876543210", "+911234567890"],
        "names": ["John Doe"]
    }
    
    # Complete profile mock
    mock_complete_profile = {
        "basic_data": {
            "emails": ["test.user@outris.com"],
            "names": ["John Doe"],
            "alternate_phones": ["+919876543210"]
        },
        "enhanced_data": {
            "breach_categories": ["Social Media", "Financial"]
        },
        "summary": {"emails_count": 1}
    }

    test_phone = "919876543210"

    # Scenario 1: User WITHOUT allow_raw_records (Masking Expected)
    print("\n[Scenario 1] User WITHOUT 'allow_raw_records' (Default)")
    account_no_raw = MCPAccount(
        id=1, 
        user_email="user@example.com", 
        display_name="User", 
        credits_balance=100, 
        credits_tier="free", 
        is_active=True,
        allow_raw_records=False
    )
    
    token = current_account.set(account_no_raw)
    try:
        with patch("mcp_server.tools.investigation.call_backend") as mock_call:
            mock_call.return_value = mock_backend_data
            
            # Test get_email
            result = await get_email(test_phone)
            print(f"get_email result: {json.dumps(result['emails'])}")
            
            # Verify masking (at least some asterisks)
            is_masked = all("*" in email for email in result["emails"])
            print(f"Is masked: {is_masked}")
            
            # Test get_identity_profile
            mock_call.return_value = mock_complete_profile
            result_profile = await get_identity_profile(test_phone)
            print(f"get_identity_profile emails: {json.dumps(result_profile['emails'])}")
            print(f"get_identity_profile masked flag: {result_profile['masked']}")

    finally:
        current_account.reset(token)

    # Scenario 2: User WITH allow_raw_records (Unmasked Expected)
    print("\n[Scenario 2] User WITH 'allow_raw_records'")
    account_raw = MCPAccount(
        id=2, 
        user_email="admin@outris.com", 
        display_name="Admin", 
        credits_balance=1000, 
        credits_tier="pro", 
        is_active=True,
        allow_raw_records=True
    )
    
    token = current_account.set(account_raw)
    try:
        with patch("mcp_server.tools.investigation.call_backend") as mock_call:
            mock_call.return_value = mock_backend_data
            
            # Test get_email
            result = await get_email(test_phone)
            print(f"get_email result: {json.dumps(result['emails'])}")
            
            # Verify NOT masked
            is_masked = any("*" in email for email in result["emails"])
            print(f"Is masked: {is_masked}")

    finally:
        current_account.reset(token)

    # Scenario 3: No Account context (Fail-safe, should mask)
    print("\n[Scenario 3] No Account Context (Fail-safe)")
    try:
        with patch("mcp_server.tools.investigation.call_backend") as mock_call:
            mock_call.return_value = mock_backend_data
            result = await get_email(test_phone)
            print(f"get_email result: {json.dumps(result['emails'])}")
            is_masked = all("*" in email for email in result["emails"])
            print(f"Is masked: {is_masked}")
    except Exception as e:
        print(f"Error in fail-safe: {e}")

if __name__ == "__main__":
    asyncio.run(test_masking_logic())
