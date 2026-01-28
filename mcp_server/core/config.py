"""
MCP Server Configuration
"""
import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    
    # Backend API
    backend_url: str = Field(default="https://api.outris.com", description="Main Backend URL")
    backend_api_key: str = ""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    # Environment
    environment: str = "production"
    
    # URLs
    dashboard_url: str = "https://portal.outris.com"
    api_base_url: str = Field(default="https://rail.outris.com", validation_alias="BACKEND_API_URL")
    
    # JWT Authentication (shared with main backend)
    jwt_secret_key: str = ""
    
    # Stripe (optional)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    
    # Razorpay (optional - for India payments)
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    
    # MCP Settings
    mcp_version: str = "1.0"
    server_name: str = "outris-mcp-server"
    
    # Feature Flags
    enable_kyc_tools: bool = False  # Disabled by default in public repo
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
