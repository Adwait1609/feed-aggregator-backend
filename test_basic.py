#!/usr/bin/env python3
"""
Test script to verify the RSS feed reader is working
"""
import asyncio
import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from database.connection import init_database, SessionLocal
from models.feed import RSSFeed
from processors.feed_processor import FeedProcessor

@pytest.mark.asyncio
async def test_basic_functionality():
    """Test basic RSS feed reader functionality"""
    print("🚀 Testing RSS Feed Reader...")
    
    # 1. Initialize database
    print("📦 Initializing database...")
    await init_database()
    print("✅ Database initialized")
    
    # 2. Add a test feed
    print("📡 Adding test RSS feed...")
    session = SessionLocal()
    
    # Check if feed already exists
    existing_feed = session.query(RSSFeed).filter(RSSFeed.url == "https://feeds.bbci.co.uk/news/rss.xml").first()
    
    if not existing_feed:
        test_feed = RSSFeed(
            name="BBC News",
            url="https://feeds.bbci.co.uk/news/rss.xml",
            description="BBC News RSS Feed"
        )
        session.add(test_feed)
        session.commit()
        session.refresh(test_feed)
        print("✅ Test feed added")
    else:
        test_feed = existing_feed
        print("✅ Test feed already exists")
    
    # 3. Test feed processing
    print("📰 Processing RSS feed...")
    processor = FeedProcessor()
    result = await processor.process_feed(test_feed, session)
    print(f"✅ Feed processed: {result}")
    
    session.close()
    print("🎉 All tests passed! Your RSS feed reader is working!")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
