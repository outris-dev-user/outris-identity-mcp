"""
Database connection management for MCP Server.
Uses asyncpg for async PostgreSQL operations.
"""
import asyncpg
import logging
from typing import Optional
from contextlib import asynccontextmanager

from .config import get_settings

logger = logging.getLogger(__name__)


class Database:
    """Async PostgreSQL connection pool manager."""
    
    pool: Optional[asyncpg.Pool] = None
    
    @classmethod
    async def connect(cls) -> None:
        """Initialize the connection pool."""
        if cls.pool is not None:
            return
        
        settings = get_settings()
        
        try:
            cls.pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=30,
                statement_cache_size=0,  # Disable for Neon compatibility
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """Close the connection pool."""
        if cls.pool is not None:
            await cls.pool.close()
            cls.pool = None
            logger.info("Database connection pool closed")
    
    @classmethod
    async def execute(cls, query: str, *args) -> str:
        """Execute a query and return status."""
        async with cls.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    @classmethod
    async def fetch(cls, query: str, *args) -> list:
        """Fetch multiple rows."""
        async with cls.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    @classmethod
    async def fetchrow(cls, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row."""
        async with cls.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    @classmethod
    async def fetchval(cls, query: str, *args):
        """Fetch a single value."""
        async with cls.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    @classmethod
    @asynccontextmanager
    async def transaction(cls):
        """Context manager for transactions."""
        async with cls.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Convenience functions
async def get_db() -> Database:
    """Get database instance (for FastAPI dependency injection)."""
    if Database.pool is None:
        await Database.connect()
    return Database
