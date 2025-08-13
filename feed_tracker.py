#!/usr/bin/env python3
"""
Simple Feed Crawl Time Tracker
Tracks last crawled time for each feed URL in a simple CSV file
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from utils.feed_crawl_tracker import FeedCrawlTracker, show_crawl_status, update_all_feeds


def show_help():
    """Show help information"""
    print("""
Feed Crawl Time Tracker

Usage:
    python feed_tracker.py <command>

Commands:
    update      Update CSV with all current feeds
    status      Show current crawl status
    show        Show CSV file content
    help        Show this help

The CSV file 'feed_crawl_times.csv' contains:
- feed_id, feed_name, feed_url
- user_id, username  
- last_crawled_at (updated automatically when feeds are crawled)
- crawl_frequency_minutes, is_active
- updated_at

Examples:
    python feed_tracker.py update
    python feed_tracker.py status
""")


def update_feeds():
    """Update CSV with all current feeds"""
    print("Updating feed crawl times CSV...")
    update_all_feeds()
    print("✅ Feed crawl times updated!")


def show_status():
    """Show current crawl status"""
    show_crawl_status()


def show_csv():
    """Show CSV file content"""
    csv_file = Path("feed_crawl_times.csv")
    
    if not csv_file.exists():
        print("❌ CSV file 'feed_crawl_times.csv' not found")
        print("Run: python feed_tracker.py update")
        return
    
    print(f"📄 Contents of {csv_file}")
    print("=" * 80)
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "update":
            update_feeds()
        elif command == "status":
            show_status()
        elif command == "show":
            show_csv()
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
