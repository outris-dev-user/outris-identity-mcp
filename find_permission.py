import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def find_permission():
    print("Searching for permission columns...")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set")
        return

    try:
        conn = await asyncpg.connect(db_url)
        
        
        cols = await conn.fetch("""
            SELECT table_schema, table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name IN ('api_keys', 'users', 'user_permissions')
        """)
        
        print("\nAPI Key / User Columns:")
        for c in cols:
            print(f"{c['table_name']}.{c['column_name']}")

        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(find_permission())
