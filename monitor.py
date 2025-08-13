#!/usr/bin/env python3
"""
Feed monitoring tool for the RSS Feed Reader
Shows feed status, crawl schedule, and recent articles
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from database.connection import get_db
from models.feed import RSSFeed
from models.article import Article
from models.user import User
from utils.feed_crawl_tracker import update_feed_crawl_time


def format_time_diff(dt):
    """Format time difference in human-readable format"""
    if dt.total_seconds() < 0:
        return f"{abs(int(dt.total_seconds() // 60))} minutes ago"
    else:
        return f"in {int(dt.total_seconds() // 60)} minutes"


def show_feed_status():
    """Show current status of all feeds"""
    session = next(get_db())
    
    print("=" * 80)
    print("RSS FEED READER - FEED STATUS")
    print("=" * 80)
    print(f"Current time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Get all feeds with user info
    feeds = session.query(RSSFeed).join(User).all()
    
    if not feeds:
        print("No feeds found!")
        return
    
    for feed in feeds:
        print(f"📰 {feed.name} (User: {feed.user.username})")
        print(f"   URL: {feed.url}")
        print(f"   Status: {'✅ Active' if feed.is_active else '❌ Inactive'}")
        print(f"   Crawl frequency: {feed.crawl_frequency_minutes} minutes")
        
        if feed.last_crawled_at:
            # Make timezone-aware for comparison
            last_crawled = feed.last_crawled_at
            if last_crawled.tzinfo is None:
                last_crawled = last_crawled.replace(tzinfo=timezone.utc)
                
            time_since_crawl = datetime.now(timezone.utc) - last_crawled
            next_crawl_time = last_crawled + timedelta(minutes=feed.crawl_frequency_minutes)
            time_until_next = next_crawl_time - datetime.now(timezone.utc)
            
            print(f"   Last crawled: {format_time_diff(-time_since_crawl)}")
            print(f"   Next crawl: {format_time_diff(time_until_next)}")
            
            # Show if due for crawling
            if time_until_next.total_seconds() <= 0:
                print("   🔔 DUE FOR CRAWLING NOW!")
        else:
            print("   Last crawled: Never")
            print("   🔔 DUE FOR CRAWLING NOW!")
        
        if feed.crawl_error_count > 0:
            print(f"   ⚠️  Error count: {feed.crawl_error_count}")
        
        # Show article count
        article_count = session.query(Article).filter(Article.feed_id == feed.id).count()
        print(f"   📄 Articles: {article_count}")
        
        print()
    
    session.close()


def show_recent_articles(limit=10):
    """Show recent articles across all feeds"""
    session = next(get_db())
    
    print("=" * 80)
    print(f"RECENT ARTICLES (Last {limit})")
    print("=" * 80)
    
    articles = session.query(Article).join(RSSFeed).order_by(Article.published_at.desc()).limit(limit).all()
    
    if not articles:
        print("No articles found!")
        return
    
    for i, article in enumerate(articles, 1):
        print(f"{i:2d}. {article.title[:60]}...")
        print(f"     📰 {article.feed.name} | 📅 {article.published_at}")
        print(f"     🔗 {article.url}")
        print()
    
    session.close()


def force_crawl_feed(feed_name_or_id):
    """Force crawl a specific feed"""
    from jobs.feed_crawler import FeedCrawlerJob
    
    async def do_crawl():
        session = next(get_db())
        
        # Find feed by name or ID
        try:
            feed_id = int(feed_name_or_id)
            feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        except ValueError:
            feed = session.query(RSSFeed).filter(RSSFeed.name.ilike(f"%{feed_name_or_id}%")).first()
        
        if not feed:
            print(f"Feed '{feed_name_or_id}' not found!")
            return
        
        print(f"Force crawling feed: {feed.name}")
        
        crawler = FeedCrawlerJob()
        result = await crawler.crawl_single_feed(feed, session)
        
        print(f"Crawl result: {result}")
        
        # Update CSV tracker
        try:
            update_feed_crawl_time(feed.id)
            print("✅ CSV tracker updated")
        except Exception as e:
            print(f"⚠️ Failed to update CSV tracker: {e}")
        
        session.close()
    
    asyncio.run(do_crawl())


def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            show_feed_status()
        elif command == "articles":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            show_recent_articles(limit)
        elif command == "crawl":
            if len(sys.argv) < 3:
                print("Usage: python monitor.py crawl <feed_name_or_id>")
                return
            force_crawl_feed(sys.argv[2])
        else:
            print("Unknown command!")
            print("Usage:")
            print("  python monitor.py status           - Show feed status")
            print("  python monitor.py articles [N]     - Show N recent articles")
            print("  python monitor.py crawl <feed>     - Force crawl a feed")
    else:
        show_feed_status()


if __name__ == "__main__":
    main()
