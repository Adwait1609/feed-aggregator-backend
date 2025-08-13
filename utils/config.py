from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./news_aggregator.db"
    
    # ChromaDB
    chroma_persist_directory: str = "./chroma_db"
    
    # ML Models
    model_directory: str = "./models"
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    
    # API
    api_title: str = "News Aggregator API"
    api_version: str = "1.0.0"
    
    # Logging
    log_level: str = "INFO"
    
    # Background jobs
    feed_crawl_interval_minutes: int = 30
    ml_training_interval_hours: int = 6
    
    class Config:
        env_file = ".env"

settings = Settings()
