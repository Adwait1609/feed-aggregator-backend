import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from database.connection import get_db
from models.feed import RSSFeed
from models.user import User
from loguru import logger


class FeedCrawlTracker:
    """Simple CSV tracker for feed crawl times"""
    
    def __init__(self, csv_file: str = "feed_crawl_times.csv"):
        self.csv_file = Path(csv_file)
        self.headers = [
            'feed_id',
            'feed_name', 
            'feed_url',
            'user_id',
            'username',
            'last_crawled_at',
            'crawl_frequency_minutes',
            'is_active',
            'updated_at'
        ]
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()
            logger.info(f"Created crawl tracker CSV: {self.csv_file}")
    
    def _read_existing_data(self) -> Dict[int, Dict]:
        """Read existing data from CSV"""
        existing_data = {}
        
        if self.csv_file.exists():
            try:
                with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['feed_id']:
                            existing_data[int(row['feed_id'])] = row
            except Exception as e:
                logger.warning(f"Error reading existing CSV data: {e}")
        
        return existing_data
    
    def update_all_feeds(self):
        """Update CSV with all current feeds from database"""
        try:
            session = next(get_db())
            feeds = session.query(RSSFeed).join(User).all()
            
            # Read existing data
            existing_data = self._read_existing_data()
            
            # Prepare updated data
            updated_data = []
            current_time = datetime.now(timezone.utc).isoformat()
            
            for feed in feeds:
                feed_data = {
                    'feed_id': feed.id,
                    'feed_name': feed.name,
                    'feed_url': feed.url,
                    'user_id': feed.user_id,
                    'username': feed.user.username,
                    'last_crawled_at': feed.last_crawled_at.isoformat() if feed.last_crawled_at else 'Never',
                    'crawl_frequency_minutes': feed.crawl_frequency_minutes,
                    'is_active': feed.is_active,
                    'updated_at': current_time
                }
                updated_data.append(feed_data)
            
            # Write updated data back to CSV
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()
                writer.writerows(updated_data)
            
            session.close()
            logger.info(f"Updated crawl times for {len(updated_data)} feeds in {self.csv_file}")
            
        except Exception as e:
            logger.error(f"Error updating feed crawl times: {e}")
    
    def update_feed_crawl_time(self, feed_id: int, crawl_time: datetime = None):
        """Update crawl time for a specific feed"""
        if crawl_time is None:
            crawl_time = datetime.now(timezone.utc)
        
        try:
            session = next(get_db())
            feed = session.query(RSSFeed).join(User).filter(RSSFeed.id == feed_id).first()
            
            if not feed:
                logger.warning(f"Feed {feed_id} not found")
                session.close()
                return
            
            # Read existing data
            existing_data = self._read_existing_data()
            
            # Update or add this feed's data
            feed_data = {
                'feed_id': feed.id,
                'feed_name': feed.name,
                'feed_url': feed.url,
                'user_id': feed.user_id,
                'username': feed.user.username,
                'last_crawled_at': crawl_time.isoformat(),
                'crawl_frequency_minutes': feed.crawl_frequency_minutes,
                'is_active': feed.is_active,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Update existing data
            existing_data[feed.id] = feed_data
            
            # Write all data back
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()
                for feed_record in existing_data.values():
                    writer.writerow(feed_record)
            
            session.close()
            logger.info(f"Updated crawl time for feed {feed.name} ({feed.url}) to {crawl_time.isoformat()}")
            
        except Exception as e:
            logger.error(f"Error updating crawl time for feed {feed_id}: {e}")
    
    def get_crawl_status(self) -> List[Dict]:
        """Get current crawl status of all feeds"""
        existing_data = self._read_existing_data()
        return list(existing_data.values())
    
    def show_crawl_status(self):
        """Print crawl status in a readable format"""
        data = self.get_crawl_status()
        
        if not data:
            print("No feed data found")
            return
        
        print("=" * 100)
        print("FEED CRAWL STATUS")
        print("=" * 100)
        print(f"{'Feed Name':<20} {'URL':<40} {'Last Crawled':<25} {'Active':<8} {'User'}")
        print("-" * 100)
        
        for feed in data:
            last_crawled = feed['last_crawled_at']
            if last_crawled != 'Never' and 'T' in last_crawled:
                # Format datetime for display
                try:
                    dt = datetime.fromisoformat(last_crawled.replace('Z', '+00:00'))
                    last_crawled = dt.strftime('%Y-%m-%d %H:%M UTC')
                except:
                    pass
            
            print(f"{feed['feed_name']:<20} {feed['feed_url']:<40} {last_crawled:<25} {feed['is_active']:<8} {feed['username']}")


# Global tracker instance
_tracker = None

def get_tracker() -> FeedCrawlTracker:
    """Get global tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = FeedCrawlTracker()
    return _tracker


def update_feed_crawl_time(feed_id: int, crawl_time: datetime = None):
    """Convenience function to update feed crawl time"""
    tracker = get_tracker()
    tracker.update_feed_crawl_time(feed_id, crawl_time)


def update_all_feeds():
    """Convenience function to update all feeds"""
    tracker = get_tracker()
    tracker.update_all_feeds()


def show_crawl_status():
    """Convenience function to show crawl status"""
    tracker = get_tracker()
    tracker.show_crawl_status()


if __name__ == "__main__":
    # Initialize and update all feeds
    tracker = FeedCrawlTracker()
    tracker.update_all_feeds()
    tracker.show_crawl_status()
