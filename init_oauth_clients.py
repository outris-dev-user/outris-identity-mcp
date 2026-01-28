import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def init_db():
    print("Initializing OAuth Clients Database...")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set")
        return

    try:
        conn = await asyncpg.connect(db_url)
        
        # Create table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mcp.oauth_clients (
                client_id TEXT PRIMARY KEY,
                client_name TEXT,
                client_uri TEXT,
                redirect_uris TEXT, 
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        print("Created table: mcp.oauth_clients")
        
        await conn.close()
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())
