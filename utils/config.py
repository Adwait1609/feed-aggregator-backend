from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./news_aggregator.db"
    
    # API
    api_title: str = "Simple RSS Feed Reader"
    api_version: str = "1.0.0"
    
    # Logging
    log_level: str = "INFO"
    
    # Background jobs
    feed_crawl_interval_minutes: int = 30
    
    class Config:
        env_file = ".env"
        protected_namespaces = ('settings_',)  # Fix pydantic warning
        extra = "ignore"  # Ignore extra fields from environment

settings = Settings()
