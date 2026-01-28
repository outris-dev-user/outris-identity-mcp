import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check_credits():
    print("Checking credits for hr@outris.com...")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set")
        return

    try:
        conn = await asyncpg.connect(db_url)
        
        # Check Account
        row = await conn.fetchrow("SELECT * FROM mcp.user_accounts WHERE user_email = 'hr@outris.com'")
        if row:
            print(f"Account Found: {row['user_email']} (ID: {row['id']})")
            print(f"Balance: {row['credits_balance']}")
            print(f"Tier: {row['credits_tier']}")
            user_id = row['id']
        else:
            print("Account not found.")
            return

        # List all tables in mcp schema to find the logs table
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'mcp'")
        print("Tables in mcp schema:", [t['table_name'] for t in tables])
        
        
        
        
        
        
        # Check Recent Transactions
        try:
             txs = await conn.fetch("SELECT * FROM mcp.user_credit_transactions WHERE user_account_id = $1 ORDER BY created_at DESC LIMIT 5", user_id)
             print("\nRecent Credit Transactions:")
             for tx in txs:
                 print(f"- {tx['transaction_type']}: {tx['amount']} credits (Bal: {tx['balance_after']}) at {tx['created_at']}")
        except Exception as e:
            print(f"Error querying transactions: {e}")

        # Check Tool Calls
        try:
             calls = await conn.fetch("SELECT * FROM mcp.user_tool_calls WHERE user_account_id = $1 ORDER BY created_at DESC LIMIT 5", user_id)
             print("\nRecent Tool Calls:")
             for call in calls:
                 print(f"- Tool: {call['tool_name']} (Cost: {call['credits_cost']}) Output: {str(call.get('output_summary',''))[:100]}...")
        except Exception as e:
            print(f"Error querying tool calls: {e}")

        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_credits())
