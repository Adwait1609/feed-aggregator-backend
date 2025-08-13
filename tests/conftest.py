import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
import tempfile
import os
import asyncio

from database.connection import get_db
from models.base import Base
from main import app

# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database for each test"""
    # Use in-memory SQLite database for tests
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()

@pytest.fixture
async def client():
    """Async FastAPI test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }

@pytest.fixture
def sample_feed_data():
    """Sample RSS feed data for testing"""
    return {
        "name": "Test Feed",
        "url": "https://example.com/feed.xml",
        "description": "A test RSS feed",
        "crawl_frequency_minutes": 60
    }

@pytest.fixture
def sample_article_data():
    """Sample article data for testing"""
    from datetime import datetime, timezone
    return {
        "title": "Test Article",
        "url": "https://example.com/article/1",
        "description": "Test article description",
        "content": "Test article content",
        "author": "Test Author",
        "published_at": datetime.now(timezone.utc)
    }
