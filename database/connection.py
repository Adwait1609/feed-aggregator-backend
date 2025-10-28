from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator
from loguru import logger

from utils.config import settings

# Create engine
engine = create_engine(
    settings.database_url
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import all models to ensure they're registered
from models.base import Base
from models.article import SharedArticle
from models.feed import SharedFeed, FeedSubscription
from models.user_feedback import SharedUserFeedback

async def init_database():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def get_database_url() -> str:
    """Get the database URL for external tools like APScheduler"""
    return settings.database_url

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_scheduler_table():
    """Create the APScheduler jobs table if it doesn't exist"""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Create the scheduler_jobs table for APScheduler
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS scheduler_jobs (
                    id VARCHAR(191) NOT NULL PRIMARY KEY,
                    next_run_time DOUBLE PRECISION,
                    job_state BYTEA NOT NULL
                )
            """))
            
            # Create index for better performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_scheduler_jobs_next_run_time 
                ON scheduler_jobs(next_run_time)
            """))
            
            conn.commit()
            logger.info("APScheduler jobs table created successfully")
    except Exception as e:
        logger.warning(f"Failed to create scheduler table (may already exist): {e}")
