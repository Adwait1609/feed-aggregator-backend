"""
Enhanced Feed Crawler with APScheduler support for per-user, per-feed crawl frequencies.

This system allows:
1. Multiple users to subscribe to the same feed
2. Each user to specify their own crawl frequency for each feed
3. Persistent job scheduling with APScheduler
4. Feed priority management
5. Optimized crawling (feeds are crawled only when needed)
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, distinct
from loguru import logger

from database.connection import get_db, get_database_url
from models.feed import RSSFeed
from models.user import User
from processors.feed_processor import FeedProcessor
from utils.feed_crawl_tracker import update_feed_crawl_time


@dataclass
class UserFeedCrawlInfo:
    """Information about a user's crawl preferences for a specific feed"""
    user_id: int
    feed_id: int
    feed_url: str
    feed_name: str
    crawl_frequency_minutes: int
    priority: int = 1  # 1 = high, 2 = medium, 3 = low
    last_crawled_at: Optional[datetime] = None
    next_crawl_at: Optional[datetime] = None


class EnhancedFeedCrawler:
    def __init__(self):
        """Initialize the enhanced feed crawler with APScheduler"""
        # Configure job store to persist jobs in database
        jobstores = {
            'default': SQLAlchemyJobStore(url=get_database_url(), tablename='scheduler_jobs')
        }
        
        executors = {
            'default': AsyncIOExecutor()
        }
        
        job_defaults = {
            'coalesce': True,  # Combine multiple pending instances of the same job
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        self.feed_processor = FeedProcessor()
        self.is_running = False
        self._active_crawl_sessions: Set[str] = set()  # Track active crawls to prevent duplicates
        
    async def start(self):
        """Start the enhanced crawler with persistent scheduling"""
        if self.is_running:
            logger.info("Enhanced crawler already running")
            return
            
        try:
            # Start the scheduler
            self.scheduler.start()
            
            # Schedule the feed discovery job (runs every 10 minutes)
            self.scheduler.add_job(
                discover_and_schedule_feeds,
                trigger=IntervalTrigger(minutes=10),
                id="feed_discovery",
                name="Feed Discovery and Scheduling",
                replace_existing=True
            )
            
            # Schedule health check (runs every hour)
            self.scheduler.add_job(
                health_check,
                trigger=IntervalTrigger(hours=1),
                id="health_check",
                name="System Health Check",
                replace_existing=True
            )
            
            # Initial discovery
            await self._discover_and_schedule_feeds()
            
            self.is_running = True
            logger.info("Enhanced feed crawler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start enhanced crawler: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the enhanced crawler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Enhanced crawler stopped")
    
    async def _discover_and_schedule_feeds(self):
        """Discover all user-feed combinations and schedule appropriate crawl jobs"""
        try:
            logger.info("Discovering feeds and scheduling crawl jobs...")
            
            session = next(get_db())
            
            # Get all user-feed combinations with their crawl preferences
            user_feeds = self._get_user_feed_combinations(session)
            
            # Group by unique feed URLs to optimize crawling
            feeds_by_url = self._group_feeds_by_url(user_feeds)
            
            # Schedule or update jobs for each unique feed URL
            for feed_url, user_feed_list in feeds_by_url.items():
                await self._schedule_feed_crawl_jobs(feed_url, user_feed_list)
            
            session.close()
            
            logger.info(f"Feed discovery completed. Managing {len(feeds_by_url)} unique feeds for {len(user_feeds)} user-feed combinations")
            
        except Exception as e:
            logger.error(f"Error in feed discovery: {str(e)}")
    
    def _get_user_feed_combinations(self, session: Session) -> List[UserFeedCrawlInfo]:
        """Get all active user-feed combinations with their crawl preferences"""
        # Query active feeds with their users
        feeds = session.query(RSSFeed).filter(
            RSSFeed.is_active == True
        ).join(User).filter(
            User.is_active == True
        ).all()
        
        user_feeds = []
        for feed in feeds:
            user_feed = UserFeedCrawlInfo(
                user_id=feed.user_id,
                feed_id=feed.id,
                feed_url=feed.url,
                feed_name=feed.name,
                crawl_frequency_minutes=feed.crawl_frequency_minutes,
                priority=getattr(feed, 'priority', 1),  # Default priority
                last_crawled_at=feed.last_crawled_at
            )
            
            # Calculate next crawl time
            if user_feed.last_crawled_at:
                user_feed.next_crawl_at = user_feed.last_crawled_at + timedelta(
                    minutes=user_feed.crawl_frequency_minutes
                )
            else:
                user_feed.next_crawl_at = datetime.now(timezone.utc)
            
            user_feeds.append(user_feed)
        
        return user_feeds
    
    def _group_feeds_by_url(self, user_feeds: List[UserFeedCrawlInfo]) -> Dict[str, List[UserFeedCrawlInfo]]:
        """Group user feeds by their URL to optimize crawling"""
        feeds_by_url = {}
        for user_feed in user_feeds:
            if user_feed.feed_url not in feeds_by_url:
                feeds_by_url[user_feed.feed_url] = []
            feeds_by_url[user_feed.feed_url].append(user_feed)
        return feeds_by_url
    
    async def _schedule_feed_crawl_jobs(self, feed_url: str, user_feeds: List[UserFeedCrawlInfo]):
        """Schedule crawl jobs for a feed URL based on user requirements"""
        # Determine the optimal crawl frequency (minimum of all user frequencies)
        min_frequency = min(uf.crawl_frequency_minutes for uf in user_feeds)
        
        # Determine priority (highest priority among all users)
        max_priority = min(uf.priority for uf in user_feeds)  # Lower number = higher priority
        
        # Create a unique job ID for this feed URL
        job_id = f"crawl_feed_{hash(feed_url) % 1000000}"
        
        # Check if job already exists
        existing_job = self.scheduler.get_job(job_id)
        
        if existing_job:
            # Update existing job if frequency changed
            current_interval = existing_job.trigger.interval.total_seconds() / 60
            if abs(current_interval - min_frequency) > 1:  # Allow 1 minute tolerance
                self.scheduler.reschedule_job(
                    job_id,
                    trigger=IntervalTrigger(minutes=min_frequency)
                )
                logger.info(f"Rescheduled feed {feed_url} from {current_interval}min to {min_frequency}min")
        else:
            # Create new job
            # Calculate when to start (earliest next_crawl_at among users)
            earliest_next_crawl = min(
                uf.next_crawl_at for uf in user_feeds 
                if uf.next_crawl_at
            )
            
            self.scheduler.add_job(
                crawl_feed_for_users,
                trigger=IntervalTrigger(minutes=min_frequency),
                args=[feed_url, [uf.user_id for uf in user_feeds]],
                id=job_id,
                name=f"Crawl Feed: {feed_url}",
                next_run_time=earliest_next_crawl,
                replace_existing=True
            )
            
            logger.info(f"Scheduled new crawl job for {feed_url} every {min_frequency}min (priority {max_priority})")
    
    async def _crawl_feed_for_users(self, feed_url: str, interested_user_ids: List[int]):
        """Crawl a feed and update articles for all interested users"""
        crawl_session_id = f"{feed_url}_{datetime.now().timestamp()}"
        
        # Prevent duplicate crawls of the same feed
        if crawl_session_id in self._active_crawl_sessions:
            logger.info(f"Skipping duplicate crawl for {feed_url}")
            return
        
        self._active_crawl_sessions.add(crawl_session_id)
        
        try:
            logger.info(f"Crawling feed {feed_url} for {len(interested_user_ids)} users")
            
            session = next(get_db())
            
            # Get all feed instances for this URL that belong to interested users
            feed_instances = session.query(RSSFeed).filter(
                and_(
                    RSSFeed.url == feed_url,
                    RSSFeed.user_id.in_(interested_user_ids),
                    RSSFeed.is_active == True
                )
            ).all()
            
            if not feed_instances:
                logger.warning(f"No active feed instances found for {feed_url}")
                session.close()
                return
            
            # Update last crawled time for all instances
            now = datetime.now(timezone.utc)
            for feed in feed_instances:
                feed.last_crawled_at = now
            session.commit()
            
            # Crawl the feed (we only need to crawl once since it's the same URL)
            representative_feed = feed_instances[0]  # Use first instance as representative
            result = await self.feed_processor.process_feed(representative_feed, session)
            
            # Update all feed instances based on the result
            total_new = 0
            total_updated = 0
            
            if result.get("status") == "success":
                # Success - reset error counts and update success time
                for feed in feed_instances:
                    feed.crawl_error_count = 0
                    feed.last_successful_crawl = now
                    
                    # Update CSV tracker
                    try:
                        update_feed_crawl_time(feed.id, now)
                    except Exception as csv_error:
                        logger.warning(f"Failed to update crawl tracker for feed {feed.name}: {str(csv_error)}")
                
                total_new = result.get("new_articles", 0)
                total_updated = result.get("updated_articles", 0)
                
                logger.info(f"Successfully crawled {feed_url}: {total_new} new, {total_updated} updated articles")
                
            else:
                # Error - increment error counts and potentially disable feeds
                for feed in feed_instances:
                    feed.crawl_error_count += 1
                    
                    if feed.crawl_error_count >= 5:
                        feed.is_active = False
                        logger.warning(f"Disabled feed {feed.name} (User: {feed.user_id}) after {feed.crawl_error_count} consecutive errors")
                
                logger.error(f"Failed to crawl {feed_url}: {result.get('error', 'Unknown error')}")
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error crawling feed {feed_url}: {str(e)}")
            
            # Update error counts for all instances
            try:
                session = next(get_db())
                feed_instances = session.query(RSSFeed).filter(
                    and_(
                        RSSFeed.url == feed_url,
                        RSSFeed.user_id.in_(interested_user_ids)
                    )
                ).all()
                
                for feed in feed_instances:
                    feed.crawl_error_count += 1
                    if feed.crawl_error_count >= 5:
                        feed.is_active = False
                
                session.commit()
                session.close()
                
            except Exception as db_error:
                logger.error(f"Failed to update error counts: {str(db_error)}")
        
        finally:
            self._active_crawl_sessions.discard(crawl_session_id)
    
    async def _health_check(self):
        """Perform system health check"""
        try:
            session = next(get_db())
            
            # Count feeds and users
            total_feeds = session.query(RSSFeed).count()
            active_feeds = session.query(RSSFeed).filter(RSSFeed.is_active == True).count()
            total_users = session.query(User).count()
            active_users = session.query(User).filter(User.is_active == True).count()
            
            # Count unique feed URLs
            unique_feed_urls = session.query(func.count(distinct(RSSFeed.url))).filter(
                RSSFeed.is_active == True
            ).scalar()
            
            # Count articles
            from models.article import Article
            total_articles = session.query(Article).count()
            
            # Recent crawling activity
            recent_crawls = session.query(RSSFeed).filter(
                RSSFeed.last_crawled_at >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).count()
            
            # Scheduler statistics
            scheduled_jobs = len(self.scheduler.get_jobs())
            running_jobs = len([job for job in self.scheduler.get_jobs() if job.next_run_time])
            
            session.close()
            
            logger.info(f"Enhanced Crawler Health Check:")
            logger.info(f"  Users: {active_users}/{total_users} active")
            logger.info(f"  Feeds: {active_feeds}/{total_feeds} active ({unique_feed_urls} unique URLs)")
            logger.info(f"  Articles: {total_articles} total")
            logger.info(f"  Recent crawls (24h): {recent_crawls}")
            logger.info(f"  Scheduled jobs: {running_jobs}/{scheduled_jobs}")
            logger.info(f"  Active crawl sessions: {len(self._active_crawl_sessions)}")
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
    
    async def force_crawl_feed(self, feed_url: str, user_ids: Optional[List[int]] = None):
        """Manually trigger a crawl for a specific feed"""
        try:
            if user_ids is None:
                # Get all users subscribed to this feed
                session = next(get_db())
                user_ids = [feed.user_id for feed in session.query(RSSFeed).filter(
                    and_(RSSFeed.url == feed_url, RSSFeed.is_active == True)
                ).all()]
                session.close()
            
            if user_ids:
                logger.info(f"Manually triggering crawl for {feed_url}")
                await self._crawl_feed_for_users(feed_url, user_ids)
            else:
                logger.warning(f"No active users found for feed {feed_url}")
                
        except Exception as e:
            logger.error(f"Failed to force crawl feed {feed_url}: {str(e)}")
    
    def get_scheduler_status(self) -> dict:
        """Get current scheduler status and job information"""
        jobs = self.scheduler.get_jobs()
        return {
            "is_running": self.is_running,
            "scheduler_running": self.scheduler.running,
            "total_jobs": len(jobs),
            "active_crawl_sessions": len(self._active_crawl_sessions),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                for job in jobs
            ]
        }


# Global instance
enhanced_crawler = EnhancedFeedCrawler()

# Standalone functions for APScheduler (to avoid serialization issues)
async def discover_and_schedule_feeds():
    """Standalone function for feed discovery and scheduling"""
    await enhanced_crawler._discover_and_schedule_feeds()

async def health_check():
    """Standalone function for health check"""
    await enhanced_crawler._health_check()

async def crawl_feed_for_users(feed_url: str, interested_user_ids: List[int]):
    """Standalone function for crawling feeds for users"""
    await enhanced_crawler._crawl_feed_for_users(feed_url, interested_user_ids)

async def start_enhanced_crawler():
    """Start the enhanced feed crawler"""
    await enhanced_crawler.start()

async def stop_enhanced_crawler():
    """Stop the enhanced feed crawler"""
    await enhanced_crawler.stop()

async def force_crawl_feed(feed_url: str, user_ids: Optional[List[int]] = None):
    """Force crawl a specific feed"""
    await enhanced_crawler.force_crawl_feed(feed_url, user_ids)

def get_crawler_status() -> dict:
    """Get current crawler status"""
    return enhanced_crawler.get_scheduler_status()
