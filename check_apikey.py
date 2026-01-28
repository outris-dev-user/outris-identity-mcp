import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check_key():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return

    try:
        conn = await asyncpg.connect(db_url)
        row = await conn.fetchrow("""
            SELECT id, allow_raw_records 
            FROM public.api_keys 
            WHERE client_email = 'hr@outris.com' AND is_active = TRUE
        """)
        if row:
            print(f"User has API Key: Yes (Allow Raw: {row['allow_raw_records']})")
        else:
            print("User has API Key: No")
        await conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(check_key())
