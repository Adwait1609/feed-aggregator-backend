import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger
from datetime import datetime, timezone, timedelta
from typing import List

from database.connection import get_db, get_database_url
from models.feed import SharedFeed, FeedSubscription
from processors.feed_processor import NormalizedFeedProcessor
from models.article import SharedArticle

# Global scheduler instance
scheduler = None

async def crawl_feeds_job():
    """Independent function to crawl feeds - can be serialized by APScheduler"""
    try:
        # Create processor instance for this job
        processor = NormalizedFeedProcessor()
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get feeds that need crawling
            feeds_to_crawl = get_feeds_due_for_crawl(db)
            
            if not feeds_to_crawl:
                logger.info("No feeds due for crawling")
                return {"feeds_crawled": 0}
            
            logger.info(f"Starting crawl for {len(feeds_to_crawl)} feeds")
            
            total_new_articles = 0
            total_updated_articles = 0
            successful_crawls = 0
            
            for feed in feeds_to_crawl:
                try:
                    result = await crawl_single_feed(feed, db, processor)
                    if result:
                        total_new_articles += result.get('new_articles', 0)
                        total_updated_articles += result.get('updated_articles', 0)
                        successful_crawls += 1
                except Exception as e:
                    logger.error(f"Failed to crawl feed {feed.default_name}: {e}")
                    # Update error count
                    feed.crawl_error_count += 1
                    feed.last_crawled_at = datetime.now(timezone.utc)
                    db.commit()
            
            logger.info(f"Crawl cycle completed: {successful_crawls}/{len(feeds_to_crawl)} feeds successful, "
                       f"{total_new_articles} new articles, {total_updated_articles} updated")
            
            return {
                "feeds_crawled": successful_crawls,
                "total_new_articles": total_new_articles,
                "total_updated_articles": total_updated_articles
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Crawl cycle failed: {e}")
        return {"error": str(e)}

def get_feeds_due_for_crawl(session: Session) -> List[SharedFeed]:
    """Get all shared feeds that are due for crawling"""
    try:
        # Get the minimum crawl frequency from all active subscriptions per feed
        # This ensures we crawl each feed at the frequency requested by the most frequent subscriber
        subquery = (
            session.query(
                FeedSubscription.feed_id,
                func.min(FeedSubscription.crawl_frequency_minutes).label('min_frequency')
            )
            .filter(FeedSubscription.is_active == True)
            .group_by(FeedSubscription.feed_id)
            .subquery()
        )
        
        # Get shared feeds that have active subscriptions and are due for crawling
        feeds_with_frequency = (
            session.query(SharedFeed, subquery.c.min_frequency)
            .join(subquery, SharedFeed.id == subquery.c.feed_id)
            .all()
        )
        
        feeds_due = []
        for feed, min_frequency in feeds_with_frequency:
            if is_feed_due(feed, min_frequency):
                feeds_due.append(feed)
        
        return feeds_due
        
    except Exception as e:
        logger.error(f"Error getting feeds due for crawl: {e}")
        return []

def is_feed_due(feed: SharedFeed, frequency_minutes: int) -> bool:
    """Check if a feed is due for crawling based on frequency"""
    if not feed.last_crawled_at:
        return True  # Never crawled before
    
    # Ensure we're comparing timezone-aware datetimes
    last_crawled = feed.last_crawled_at
    if last_crawled.tzinfo is None:
        last_crawled = last_crawled.replace(tzinfo=timezone.utc)
    
    time_since_last_crawl = datetime.now(timezone.utc) - last_crawled
    crawl_interval = timedelta(minutes=frequency_minutes)
    
    return time_since_last_crawl >= crawl_interval

async def crawl_single_feed(feed: SharedFeed, session: Session, processor: NormalizedFeedProcessor) -> dict:
    """Crawl a single shared feed"""
    try:
        logger.info(f"Crawling feed: {feed.default_name} ({feed.url})")
        
        # Process the feed
        result = await processor.process_shared_feed(feed, session)
        
        if result and result.get('status') == 'success':
            # Update last crawled time and reset error count
            feed.last_crawled_at = datetime.now(timezone.utc)
            feed.last_successful_crawl = datetime.now(timezone.utc)
            feed.crawl_error_count = 0
            session.commit()
            
            logger.info(f"Successfully crawled {feed.default_name}: "
                       f"{result.get('new_articles', 0)} new, "
                       f"{result.get('updated_articles', 0)} updated")
            
            return result
        else:
            # Update error count and last crawled time
            feed.crawl_error_count += 1
            feed.last_crawled_at = datetime.now(timezone.utc)
            session.commit()
            
            logger.warning(f"Failed to crawl {feed.default_name}")
            return {"error": "Crawl failed"}
            
    except Exception as e:
        logger.error(f"Error crawling feed {feed.default_name}: {e}")
        
        # Update error count
        feed.crawl_error_count += 1
        feed.last_crawled_at = datetime.now(timezone.utc)
        session.commit()
        
        return {"error": str(e)}

async def start_background_jobs():
    """Start the background feed crawler"""
    global scheduler
    
    if scheduler and scheduler.running:
        logger.info("Scheduler already running")
        return
    
    try:
        # Configure scheduler with persistent job store
        jobstore = SQLAlchemyJobStore(url=get_database_url())
        
        scheduler = AsyncIOScheduler(
            jobstores={'default': jobstore},
            job_defaults={
                'coalesce': True,      # Skip missed runs if scheduler was down
                'max_instances': 1,    # Only one instance of each job
                'misfire_grace_time': 300  # Allow 5 minutes delay
            }
        )
        
        # Add the crawl job - runs every 10 minutes
        scheduler.add_job(
            func=crawl_feeds_job,
            trigger='interval',
            minutes=10,
            id='feed_crawl_cycle',
            name='RSS Feed Crawl Cycle',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Feed crawler scheduler started successfully")
        
        # Run initial crawl
        await crawl_feeds_job()
        
    except Exception as e:
        logger.error(f"Failed to start crawler: {e}")
        raise

async def stop_background_jobs():
    """Stop the background feed crawler"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Feed crawler scheduler stopped")

async def run_crawl_cycle():
    """Run a single crawl cycle manually - useful for API endpoints"""
    try:
        return await crawl_feeds_job()
    except Exception as e:
        logger.error(f"Manual crawl job failed: {e}")
        return {"error": str(e)}
