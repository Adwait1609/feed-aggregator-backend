import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from loguru import logger
from datetime import datetime, timezone, timedelta

from database.connection import get_db
from models.feed import RSSFeed
from processors.feed_processor import FeedProcessor
from utils.feed_crawl_tracker import update_feed_crawl_time

class FeedCrawlerJob:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.feed_processor = FeedProcessor()
        self.is_running = False
        
    async def start_background_jobs(self):
        """Start background crawling jobs for all users' feeds"""
        if self.is_running:
            logger.info("Background jobs already running")
            return
            
        try:
            # Feed crawling job - runs every 15 minutes to check which feeds need updating
            self.scheduler.add_job(
                self.crawl_due_feeds,
                trigger=IntervalTrigger(minutes=15),  # Check every 15 minutes
                id="feed_crawler_check",
                name="RSS Feed Crawler Check",
                replace_existing=True
            )
            
            # Health check job - runs every hour
            self.scheduler.add_job(
                self.health_check,
                trigger=IntervalTrigger(hours=1),
                id="crawler_health_check",
                name="Crawler Health Check",
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("Background crawling jobs started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start background jobs: {str(e)}")
    
    async def stop_background_jobs(self):
        """Stop all background jobs"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Background jobs stopped")
    
    async def crawl_due_feeds(self):
        """Crawl all feeds that are due for updates (from all users)"""
        try:
            logger.info("Checking for feeds due for crawling...")
            
            session = next(get_db())
            
            # Get all active feeds from all users
            active_feeds = session.query(RSSFeed).filter(
                RSSFeed.is_active == True
            ).all()
            
            due_feeds = []
            for feed in active_feeds:
                if self._should_crawl_feed(feed):
                    due_feeds.append(feed)
            
            if not due_feeds:
                logger.info("No feeds due for crawling")
                session.close()
                return
            
            logger.info(f"Found {len(due_feeds)} feeds due for crawling")
            
            # Crawl feeds in batches to avoid overwhelming
            batch_size = 5
            total_new = 0
            total_updated = 0
            
            for i in range(0, len(due_feeds), batch_size):
                batch = due_feeds[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} feeds")
                
                # Process batch concurrently
                tasks = [
                    self.crawl_single_feed(feed, session) 
                    for feed in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Aggregate results
                for result in results:
                    if isinstance(result, dict) and result.get("status") == "success":
                        total_new += result.get("new_articles", 0)
                        total_updated += result.get("updated_articles", 0)
                
                # Small delay between batches
                if i + batch_size < len(due_feeds):
                    await asyncio.sleep(2)
            
            session.close()
            
            logger.info(f"Crawling completed: {total_new} new, {total_updated} updated articles from {len(due_feeds)} feeds")
            
        except Exception as e:
            logger.error(f"Error in crawl_due_feeds: {str(e)}")
    
    def _should_crawl_feed(self, feed: RSSFeed) -> bool:
        """Check if feed should be crawled now based on frequency"""
        if not feed.is_active:
            return False
            
        if not feed.last_crawled_at:
            return True  # Never crawled before
            
        # Make sure last_crawled_at is timezone-aware
        last_crawled = feed.last_crawled_at
        if last_crawled.tzinfo is None:
            last_crawled = last_crawled.replace(tzinfo=timezone.utc)
            
        next_crawl_time = last_crawled + timedelta(minutes=feed.crawl_frequency_minutes)
        return datetime.now(timezone.utc) >= next_crawl_time
    
    async def crawl_single_feed(self, feed: RSSFeed, session: Session) -> dict:
        """Crawl a single feed with error handling"""
        try:
            logger.info(f"Crawling feed: {feed.name} (User: {feed.user_id})")
            
            # Update last crawled time immediately to prevent duplicate crawling
            feed.last_crawled_at = datetime.now(timezone.utc)
            session.commit()
            
            # Process the feed
            result = await self.feed_processor.process_feed(feed, session)
            
            if result.get("status") == "success":
                # Reset error count on success
                feed.crawl_error_count = 0
                feed.last_successful_crawl = datetime.now(timezone.utc)
                
                # Update CSV tracker with latest crawl time
                try:
                    update_feed_crawl_time(feed.id, feed.last_crawled_at)
                except Exception as csv_error:
                    logger.warning(f"Failed to update crawl tracker for feed {feed.name}: {str(csv_error)}")
            else:
                # Increment error count on failure
                feed.crawl_error_count += 1
                
                # Disable feed if too many consecutive errors
                if feed.crawl_error_count >= 5:
                    feed.is_active = False
                    logger.warning(f"Disabled feed {feed.name} (User: {feed.user_id}) after {feed.crawl_error_count} consecutive errors")
            
            session.commit()
            return result
            
        except Exception as e:
            logger.error(f"Error crawling feed {feed.name} (User: {feed.user_id}): {str(e)}")
            
            # Update error count
            feed.crawl_error_count += 1
            if feed.crawl_error_count >= 5:
                feed.is_active = False
                logger.warning(f"Disabled feed {feed.name} (User: {feed.user_id}) after {feed.crawl_error_count} consecutive errors")
            
            session.commit()
            
            return {
                "feed_name": feed.name,
                "user_id": feed.user_id,
                "status": "error",
                "error": str(e)
            }
    
    async def health_check(self):
        """Perform health check on the crawling system"""
        try:
            session = next(get_db())
            
            # Count feeds by status
            total_feeds = session.query(RSSFeed).count()
            active_feeds = session.query(RSSFeed).filter(RSSFeed.is_active == True).count()
            inactive_feeds = total_feeds - active_feeds
            
            # Count articles
            from models.article import Article
            total_articles = session.query(Article).count()
            
            # Recent crawling activity
            recent_crawls = session.query(RSSFeed).filter(
                RSSFeed.last_crawled_at >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).count()
            
            # User statistics
            from models.user import User
            total_users = session.query(User).count()
            active_users = session.query(User).filter(User.is_active == True).count()
            
            session.close()
            
            logger.info(f"Crawler Health Check - Users: {active_users}/{total_users} active | "
                       f"Feeds: {active_feeds} active, {inactive_feeds} inactive | "
                       f"Articles: {total_articles} total | Recent crawls (24h): {recent_crawls}")
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")

# Global instance
crawler_job = FeedCrawlerJob()

async def start_background_jobs():
    """Start background crawling jobs"""
    await crawler_job.start_background_jobs()

async def stop_background_jobs():
    """Stop background crawling jobs"""
    await crawler_job.stop_background_jobs()
