import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from loguru import logger

from database.connection import get_db
from models.feed import RSSFeed
from processors.feed_processor import FeedProcessor

class FeedCrawlerJob:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.feed_processor = FeedProcessor()
        
    async def start_background_jobs(self):
        """Start basic background jobs"""
        # Feed crawling job - every 30 minutes
        self.scheduler.add_job(
            self.crawl_all_feeds,
            trigger=IntervalTrigger(minutes=30),
            id="feed_crawler",
            name="RSS Feed Crawler"
        )
        
        self.scheduler.start()
        logger.info("Background jobs started (basic version)")
    
    async def crawl_all_feeds(self):
        """Crawl all active RSS feeds"""
        try:
            logger.info("Starting RSS feed crawling job")
            
            session = next(get_db())
            active_feeds = session.query(RSSFeed).filter(RSSFeed.is_active == True).all()
            
            results = []
            for feed in active_feeds:
                result = await self.feed_processor.process_feed(feed, session)
                results.append(result)
            
            session.close()
            
            # Log summary
            total_new = sum(r.get("new_articles", 0) for r in results)
            total_updated = sum(r.get("updated_articles", 0) for r in results)
            
            logger.info(f"Feed crawling completed: {total_new} new, {total_updated} updated articles")
            
        except Exception as e:
            logger.error(f"Feed crawling job failed: {str(e)}")

# Global job instance
job_instance = FeedCrawlerJob()

# Simplified - basic background jobs only
async def start_background_jobs():
    """Start basic background jobs - ML features will be added later"""
    logger.info("Background jobs disabled for now - focusing on basic functionality")
    pass
