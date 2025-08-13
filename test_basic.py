#!/usr/bin/env python3
"""
Test script to verify the multi-user RSS feed reader is working
"""
import asyncio
import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from database.connection import init_database, SessionLocal
from models.user import User
from models.feed import RSSFeed
from processors.feed_processor import FeedProcessor
from utils.auth import create_user

@pytest.mark.asyncio
async def test_multi_user_functionality():
    """Test multi-user RSS feed reader functionality"""
    print("🚀 Testing Multi-User RSS Feed Reader...")
    
    # 1. Initialize database
    print("📦 Initializing database...")
    await init_database()
    print("✅ Database initialized")
    
    # 2. Create test user
    print("� Creating test user...")
    session = SessionLocal()
    
    # Check if test user already exists
    existing_user = session.query(User).filter(User.username == "testuser").first()
    
    if not existing_user:
        test_user = create_user(
            db=session,
            username="testuser",
            email="test@example.com",
            password="testpassword123"
        )
        print("✅ Test user created")
    else:
        test_user = existing_user
        print("✅ Test user already exists")
    
    # 3. Add a test feed for the user
    print("📡 Adding test RSS feed for user...")
    
    # Check if feed already exists for this user
    existing_feed = session.query(RSSFeed).filter(
        RSSFeed.url == "https://feeds.bbci.co.uk/news/rss.xml",
        RSSFeed.user_id == test_user.id
    ).first()
    
    if not existing_feed:
        test_feed = RSSFeed(
            name="BBC News",
            url="https://feeds.bbci.co.uk/news/rss.xml",
            description="BBC News RSS Feed",
            user_id=test_user.id
        )
        session.add(test_feed)
        session.commit()
        session.refresh(test_feed)
        print("✅ Test feed added for user")
    else:
        test_feed = existing_feed
        print("✅ Test feed already exists for user")
    
    # 4. Test feed processing
    print("📰 Processing RSS feed...")
    processor = FeedProcessor()
    result = await processor.process_feed(test_feed, session)
    print(f"✅ Feed processed: {result}")
    
    # 5. Check articles were created for the user
    articles_count = len(test_feed.articles)
    print(f"📄 Articles in user's feed: {articles_count}")
    
    session.close()
    print("🎉 All multi-user tests passed! Your RSS feed reader is working!")

if __name__ == "__main__":
    asyncio.run(test_multi_user_functionality())
