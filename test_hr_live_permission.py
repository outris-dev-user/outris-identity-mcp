
import asyncio
import json
from unittest.mock import patch
from mcp_server.core.database import Database
from mcp_server.core.auth import get_account_by_id
from mcp_server.tools.registry import execute_tool
import mcp_server.tools.investigation # required for registration

async def test_hr_permission():
    print("Verifying hr@outris.com Live Permission...")
    print("========================================")

    await Database.connect()
    
    # 1. Fetch the actual account from DB
    # hr@outris.com has ID 1 based on previous runs
    account = await get_account_by_id(1)
    
    if not account:
        print("Error: Could not find account ID 1 (hr@outris.com)")
        return
        
    print(f"Account: {account.user_email}")
    print(f"allow_raw_records flag in Account object: {account.allow_raw_records}")

    # 2. Execute tool with internal mocking of the backend call (to avoid 401)
    # But using the REAL account context
    
    test_phone = "919876543210"
    mock_backend_data = {
        "emails": ["hr.private@outris.com", "backup@gmail.com"],
        "count": 2
    }

    print("\nExecuting get_email with live account context...")
    with patch("mcp_server.tools.investigation.call_backend") as mock_call:
        mock_call.return_value = mock_backend_data
        
        result, latency = await execute_tool("get_email", {"phone": test_phone}, account_id=1)
        
        print(f"Tool Output (Emails): {json.dumps(result['emails'], indent=2)}")
        print(f"Masked Flag in output: {result.get('masked')}")
        
        is_masked = any("*" in e for e in result['emails'])
        if not is_masked and account.allow_raw_records:
            print("\nVERDICT: SUCCESS. Data is UNMASKED because the DB flag is TRUE.")
        elif is_masked and not account.allow_raw_records:
            print("\nVERDICT: SUCCESS. Data is MASKED because the DB flag is FALSE.")
        else:
            print("\nVERDICT: DISCREPANCY DETECTED.")

    await Database.disconnect()

if __name__ == "__main__":
    asyncio.run(test_hr_permission())
