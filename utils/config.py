from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg2://postgres:password@localhost:5432/RSS"

    # API
    api_title: str = "Simple RSS Feed Reader"
    api_version: str = "1.0.0"
    api_host: str = "localhost"
    api_port: int = 8000
    
    # Logging
    log_level: str = "INFO"
    
    # Background jobs
    feed_crawl_interval_minutes: int = 30
    
    class Config:
        env_file = ".env"
        protected_namespaces = ('settings_',)  # Fix pydantic warning
        extra = "ignore"  # Ignore extra fields from environment

settings = Settings()
