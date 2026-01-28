import asyncio
import logging
import os
from mcp_server.core.database import Database
from mcp_server.core.config import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

async def init_db():
    try:
        settings = get_settings()
        logger.info(f"Connecting to database: {settings.database_url.split('@')[1] if settings.database_url and '@' in settings.database_url else 'UNKNOWN'}")
        
        await Database.connect()
        
        query = """
        CREATE TABLE IF NOT EXISTS mcp.oauth_codes (
            code VARCHAR(64) PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            user_id INTEGER,
            client_id VARCHAR(64),
            redirect_uri TEXT,
            code_challenge TEXT,
            code_challenge_method VARCHAR(10),
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_oauth_codes_code ON mcp.oauth_codes(code);
        """
        
        await Database.execute(query)
        logger.info("Successfully created mcp.oauth_codes table")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        await Database.disconnect()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
