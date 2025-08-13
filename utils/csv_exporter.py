import csv
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from pathlib import Path

from database.connection import get_db
from models.feed import RSSFeed
from models.article import Article
from models.user import User
from sqlalchemy.orm import Session
from loguru import logger


class FeedCSVExporter:
    """Handle CSV export and updates for feeds"""
    
    def __init__(self, export_directory: str = "feed_exports"):
        self.export_directory = Path(export_directory)
        self.export_directory.mkdir(exist_ok=True)
        
    def get_user_feed_filename(self, user_id: int, feed_id: int, feed_name: str) -> str:
        """Generate CSV filename for a user's feed"""
        # Sanitize feed name for filename
        safe_name = "".join(c for c in feed_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        return f"user_{user_id}_feed_{feed_id}_{safe_name}.csv"
    
    def create_feed_csv_headers(self) -> List[str]:
        """Define CSV headers for feed export"""
        return [
            'feed_id',
            'feed_name', 
            'feed_url',
            'user_id',
            'username',
            'is_active',
            'crawl_frequency_minutes',
            'last_crawled_at',
            'last_successful_crawl',
            'crawl_error_count',
            'created_at',
            'updated_at',
            'total_articles',
            'export_timestamp'
        ]
    
    def create_article_csv_headers(self) -> List[str]:
        """Define CSV headers for articles export"""
        return [
            'article_id',
            'title',
            'url',
            'published_at',
            'content_hash',
            'feed_id',
            'feed_name',
            'user_id',
            'created_at',
            'export_timestamp'
        ]
    
    def export_feed_status(self, session: Session, user_id: int = None) -> List[str]:
        """Export feed status to CSV files"""
        exported_files = []
        
        try:
            # Get feeds for specific user or all users
            query = session.query(RSSFeed).join(User)
            if user_id:
                query = query.filter(RSSFeed.user_id == user_id)
            
            feeds = query.all()
            
            for feed in feeds:
                # Count articles for this feed
                article_count = session.query(Article).filter(Article.feed_id == feed.id).count()
                
                # Prepare feed data
                feed_data = {
                    'feed_id': feed.id,
                    'feed_name': feed.name,
                    'feed_url': feed.url,
                    'user_id': feed.user_id,
                    'username': feed.user.username,
                    'is_active': feed.is_active,
                    'crawl_frequency_minutes': feed.crawl_frequency_minutes,
                    'last_crawled_at': feed.last_crawled_at.isoformat() if feed.last_crawled_at else None,
                    'last_successful_crawl': feed.last_successful_crawl.isoformat() if feed.last_successful_crawl else None,
                    'crawl_error_count': feed.crawl_error_count,
                    'created_at': feed.created_at.isoformat() if hasattr(feed, 'created_at') and feed.created_at else None,
                    'updated_at': feed.updated_at.isoformat() if hasattr(feed, 'updated_at') and feed.updated_at else None,
                    'total_articles': article_count,
                    'export_timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Create CSV file for this feed
                filename = self.get_user_feed_filename(feed.user_id, feed.id, feed.name)
                filepath = self.export_directory / filename
                
                # Write or update CSV file
                file_exists = filepath.exists()
                
                with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.create_feed_csv_headers())
                    
                    # Write header if new file
                    if not file_exists:
                        writer.writeheader()
                    
                    # Write feed data
                    writer.writerow(feed_data)
                
                exported_files.append(str(filepath))
                logger.info(f"Exported feed status to {filepath}")
            
            return exported_files
            
        except Exception as e:
            logger.error(f"Error exporting feed status: {str(e)}")
            raise
    
    def export_feed_articles(self, session: Session, feed_id: int = None, user_id: int = None) -> List[str]:
        """Export articles to CSV files"""
        exported_files = []
        
        try:
            # Get articles for specific feed/user or all
            query = session.query(Article).join(RSSFeed).join(User)
            
            if feed_id:
                query = query.filter(Article.feed_id == feed_id)
            elif user_id:
                query = query.filter(RSSFeed.user_id == user_id)
            
            articles = query.order_by(Article.published_at.desc()).all()
            
            # Group articles by feed
            feeds_articles = {}
            for article in articles:
                if article.feed_id not in feeds_articles:
                    feeds_articles[article.feed_id] = []
                feeds_articles[article.feed_id].append(article)
            
            # Export each feed's articles
            for feed_id, feed_articles in feeds_articles.items():
                if not feed_articles:
                    continue
                    
                feed = feed_articles[0].feed
                
                # Create filename for articles
                filename = f"user_{feed.user_id}_feed_{feed.id}_{feed.name.replace(' ', '_')}_articles.csv"
                filepath = self.export_directory / filename
                
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.create_article_csv_headers())
                    writer.writeheader()
                    
                    for article in feed_articles:
                        article_data = {
                            'article_id': article.id,
                            'title': article.title,
                            'url': article.url,
                            'published_at': article.published_at.isoformat() if article.published_at else None,
                            'content_hash': article.content_hash,
                            'feed_id': article.feed_id,
                            'feed_name': article.feed.name,
                            'user_id': article.feed.user_id,
                            'created_at': article.created_at.isoformat() if hasattr(article, 'created_at') and article.created_at else None,
                            'export_timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        writer.writerow(article_data)
                
                exported_files.append(str(filepath))
                logger.info(f"Exported {len(feed_articles)} articles to {filepath}")
            
            return exported_files
            
        except Exception as e:
            logger.error(f"Error exporting articles: {str(e)}")
            raise
    
    def update_feed_crawl_time(self, feed_id: int, crawl_time: datetime = None):
        """Update last crawled time in CSV for a specific feed"""
        if crawl_time is None:
            crawl_time = datetime.now(timezone.utc)
        
        try:
            session = next(get_db())
            feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
            
            if not feed:
                logger.error(f"Feed {feed_id} not found")
                return
            
            # Export updated status
            self.export_feed_status(session, feed.user_id)
            
            session.close()
            logger.info(f"Updated crawl time for feed {feed.name} (ID: {feed_id})")
            
        except Exception as e:
            logger.error(f"Error updating feed crawl time: {str(e)}")
    
    def export_all_feeds_and_articles(self):
        """Export all feeds and their articles to CSV files"""
        try:
            session = next(get_db())
            
            logger.info("Starting full CSV export...")
            
            # Export feed status
            feed_files = self.export_feed_status(session)
            logger.info(f"Exported {len(feed_files)} feed status files")
            
            # Export articles
            article_files = self.export_feed_articles(session)
            logger.info(f"Exported {len(article_files)} article files")
            
            session.close()
            
            return {
                'feed_files': feed_files,
                'article_files': article_files,
                'export_directory': str(self.export_directory)
            }
            
        except Exception as e:
            logger.error(f"Error in full export: {str(e)}")
            raise
    
    def get_export_summary(self) -> Dict[str, Any]:
        """Get summary of exported files"""
        if not self.export_directory.exists():
            return {'error': 'Export directory does not exist'}
        
        files = list(self.export_directory.glob('*.csv'))
        
        summary = {
            'export_directory': str(self.export_directory),
            'total_files': len(files),
            'feed_status_files': len([f for f in files if not f.name.endswith('_articles.csv')]),
            'article_files': len([f for f in files if f.name.endswith('_articles.csv')]),
            'files': [f.name for f in files],
            'last_export': max([f.stat().st_mtime for f in files]) if files else None
        }
        
        if summary['last_export']:
            summary['last_export'] = datetime.fromtimestamp(summary['last_export']).isoformat()
        
        return summary


# Utility functions for easy use
def export_feeds_to_csv(user_id: int = None) -> Dict[str, Any]:
    """Export feeds to CSV (convenience function)"""
    exporter = FeedCSVExporter()
    return exporter.export_all_feeds_and_articles()


def update_feed_csv_on_crawl(feed_id: int):
    """Update CSV when a feed is crawled (convenience function)"""
    exporter = FeedCSVExporter()
    exporter.update_feed_crawl_time(feed_id)


if __name__ == "__main__":
    # Example usage
    exporter = FeedCSVExporter()
    result = exporter.export_all_feeds_and_articles()
    print(f"Export completed: {result}")
