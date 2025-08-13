#!/usr/bin/env python3
"""
Database Inspector for RSS Feed Reader
Check database status, tables, and data
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_db
from models.user import User
from models.feed import RSSFeed
from models.article import Article


def check_database_file():
    """Check if database file exists and show basic info"""
    db_file = 'news_aggregator.db'
    
    print("🔍 DATABASE FILE CHECK")
    print("=" * 50)
    
    if os.path.exists(db_file):
        size = os.path.getsize(db_file)
        modified = datetime.fromtimestamp(os.path.getmtime(db_file))
        
        print(f"✅ Database found: {db_file}")
        print(f"📁 File size: {size:,} bytes ({size/1024:.1f} KB)")
        print(f"📅 Last modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    else:
        print(f"❌ Database not found: {db_file}")
        print("💡 Run the app to create database: uv run python main.py")
        return False


def check_sqlite_tables():
    """Check tables using direct SQLite connection"""
    print("\n📊 SQLITE TABLES")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('news_aggregator.db')
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables:")
        
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                print(f"  📋 {table_name}: {count:,} records")
            except Exception as e:
                print(f"  ❌ {table_name}: Error counting - {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")


def check_orm_data():
    """Check data using SQLAlchemy ORM"""
    print("\n🗃️  ORM DATA CHECK")
    print("=" * 50)
    
    try:
        session = next(get_db())
        
        # Count users
        user_count = session.query(User).count()
        print(f"👥 Users: {user_count}")
        
        if user_count > 0:
            users = session.query(User).all()
            for user in users:
                print(f"  - {user.username} ({user.email}) [ID: {user.id}]")
        
        # Count feeds
        feed_count = session.query(RSSFeed).count()
        print(f"\n📰 RSS Feeds: {feed_count}")
        
        if feed_count > 0:
            feeds = session.query(RSSFeed).all()
            for feed in feeds:
                print(f"  - {feed.name}: {feed.url} [User: {feed.user_id}, Active: {feed.is_active}]")
        
        # Count articles
        article_count = session.query(Article).count()
        print(f"\n📄 Articles: {article_count:,}")
        
        if article_count > 0:
            # Show articles by feed
            feeds = session.query(RSSFeed).all()
            for feed in feeds:
                feed_articles = session.query(Article).filter(Article.feed_id == feed.id).count()
                if feed_articles > 0:
                    latest_article = session.query(Article).filter(Article.feed_id == feed.id).order_by(Article.published_at.desc()).first()
                    print(f"  - {feed.name}: {feed_articles:,} articles (latest: {latest_article.published_at if latest_article else 'N/A'})")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error accessing ORM data: {e}")


def show_recent_activity():
    """Show recent crawl activity"""
    print("\n🕒 RECENT ACTIVITY")
    print("=" * 50)
    
    try:
        session = next(get_db())
        
        # Recent articles
        recent_articles = session.query(Article).order_by(Article.published_at.desc()).limit(5).all()
        
        if recent_articles:
            print("📄 5 Most Recent Articles:")
            for i, article in enumerate(recent_articles, 1):
                print(f"  {i}. {article.title[:50]}...")
                print(f"     📰 {article.feed.name} | 📅 {article.published_at}")
        else:
            print("📄 No articles found")
        
        # Feed crawl status
        feeds = session.query(RSSFeed).all()
        if feeds:
            print(f"\n🔄 Feed Crawl Status:")
            for feed in feeds:
                last_crawled = feed.last_crawled_at.strftime('%Y-%m-%d %H:%M UTC') if feed.last_crawled_at else 'Never'
                print(f"  - {feed.name}: {last_crawled}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error getting recent activity: {e}")


def main():
    """Main function"""
    print("🗄️  RSS FEED READER - DATABASE INSPECTOR")
    print("=" * 80)
    
    # Check database file
    if not check_database_file():
        return
    
    # Check tables
    check_sqlite_tables()
    
    # Check ORM data
    check_orm_data()
    
    # Show recent activity
    show_recent_activity()
    
    print("\n" + "=" * 80)
    print("💡 TIPS:")
    print("  - To start the server: uv run python main.py")
    print("  - To check feed status: uv run python feed_tracker.py status")
    print("  - To force crawl: uv run python monitor.py crawl <feed_name>")
    print("  - Background jobs run only when the server is running!")


if __name__ == "__main__":
    main()
