#!/usr/bin/env python3
"""
CSV Export Manager for RSS Feed Reader
Manages CSV exports of feeds and articles for each user
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from utils.csv_exporter import FeedCSVExporter
from database.connection import get_db
from models.user import User
from models.feed import RSSFeed


def show_help():
    """Show help information"""
    print("""
CSV Export Manager for RSS Feed Reader

Usage:
    python csv_manager.py <command> [options]

Commands:
    export-all              Export all feeds and articles to CSV
    export-user <user_id>   Export feeds for specific user
    export-feed <feed_id>   Export specific feed
    summary                 Show export summary
    list-files              List all CSV files
    clean                   Remove all CSV files
    help                    Show this help

Examples:
    python csv_manager.py export-all
    python csv_manager.py export-user 1
    python csv_manager.py export-feed 2
    python csv_manager.py summary
""")


def export_all():
    """Export all feeds and articles"""
    print("Exporting all feeds and articles to CSV...")
    
    exporter = FeedCSVExporter()
    result = exporter.export_all_feeds_and_articles()
    
    print(f"✅ Export completed!")
    print(f"📁 Export directory: {result['export_directory']}")
    print(f"📊 Feed status files: {len(result['feed_files'])}")
    print(f"📄 Article files: {len(result['article_files'])}")
    print("\nExported files:")
    
    for file in result['feed_files']:
        print(f"  📊 {Path(file).name}")
    
    for file in result['article_files']:
        print(f"  📄 {Path(file).name}")


def export_user(user_id):
    """Export feeds for specific user"""
    try:
        user_id = int(user_id)
    except ValueError:
        print("❌ User ID must be a number")
        return
    
    session = next(get_db())
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        print(f"❌ User {user_id} not found")
        session.close()
        return
    
    print(f"Exporting feeds for user: {user.username} (ID: {user_id})")
    
    exporter = FeedCSVExporter()
    
    # Export feed status
    feed_files = exporter.export_feed_status(session, user_id)
    
    # Export articles
    article_files = exporter.export_feed_articles(session, user_id=user_id)
    
    session.close()
    
    print(f"✅ Export completed for user {user.username}!")
    print(f"📊 Feed files: {len(feed_files)}")
    print(f"📄 Article files: {len(article_files)}")


def export_feed(feed_id):
    """Export specific feed"""
    try:
        feed_id = int(feed_id)
    except ValueError:
        print("❌ Feed ID must be a number")
        return
    
    session = next(get_db())
    feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
    
    if not feed:
        print(f"❌ Feed {feed_id} not found")
        session.close()
        return
    
    print(f"Exporting feed: {feed.name} (ID: {feed_id})")
    
    exporter = FeedCSVExporter()
    
    # Export feed status
    feed_files = exporter.export_feed_status(session, feed.user_id)
    
    # Export articles for this feed
    article_files = exporter.export_feed_articles(session, feed_id=feed_id)
    
    session.close()
    
    print(f"✅ Export completed for feed {feed.name}!")
    print(f"📊 Feed file: {len(feed_files)} file(s)")
    print(f"📄 Article file: {len(article_files)} file(s)")


def show_summary():
    """Show export summary"""
    exporter = FeedCSVExporter()
    summary = exporter.get_export_summary()
    
    if 'error' in summary:
        print(f"❌ {summary['error']}")
        return
    
    print("📈 CSV Export Summary")
    print("=" * 50)
    print(f"📁 Export directory: {summary['export_directory']}")
    print(f"📊 Total files: {summary['total_files']}")
    print(f"📊 Feed status files: {summary['feed_status_files']}")
    print(f"📄 Article files: {summary['article_files']}")
    
    if summary['last_export']:
        print(f"🕒 Last export: {summary['last_export']}")
    
    if summary['files']:
        print(f"\n📋 Files:")
        for file in sorted(summary['files']):
            if file.endswith('_articles.csv'):
                print(f"  📄 {file}")
            else:
                print(f"  📊 {file}")


def list_files():
    """List all CSV files with details"""
    exporter = FeedCSVExporter()
    export_dir = exporter.export_directory
    
    if not export_dir.exists():
        print("❌ Export directory does not exist")
        return
    
    csv_files = list(export_dir.glob('*.csv'))
    
    if not csv_files:
        print("📁 No CSV files found")
        return
    
    print(f"📋 CSV Files in {export_dir}")
    print("=" * 80)
    
    for file in sorted(csv_files):
        stat = file.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Format file size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        
        file_type = "📄 Articles" if file.name.endswith('_articles.csv') else "📊 Feed Status"
        
        print(f"{file_type} | {file.name}")
        print(f"         Size: {size_str} | Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        print()


def clean_files():
    """Remove all CSV files"""
    exporter = FeedCSVExporter()
    export_dir = exporter.export_directory
    
    if not export_dir.exists():
        print("❌ Export directory does not exist")
        return
    
    csv_files = list(export_dir.glob('*.csv'))
    
    if not csv_files:
        print("📁 No CSV files to clean")
        return
    
    print(f"🗑️  Found {len(csv_files)} CSV files to remove")
    
    confirm = input("Are you sure you want to delete all CSV files? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Operation cancelled")
        return
    
    removed_count = 0
    for file in csv_files:
        try:
            file.unlink()
            removed_count += 1
        except Exception as e:
            print(f"❌ Failed to remove {file.name}: {e}")
    
    print(f"✅ Removed {removed_count} CSV files")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "export-all":
            export_all()
        elif command == "export-user":
            if len(sys.argv) < 3:
                print("❌ Usage: python csv_manager.py export-user <user_id>")
                return
            export_user(sys.argv[2])
        elif command == "export-feed":
            if len(sys.argv) < 3:
                print("❌ Usage: python csv_manager.py export-feed <feed_id>")
                return
            export_feed(sys.argv[2])
        elif command == "summary":
            show_summary()
        elif command == "list-files":
            list_files()
        elif command == "clean":
            clean_files()
        elif command == "help":
            show_help()
        else:
            print(f"❌ Unknown command: {command}")
            show_help()
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
