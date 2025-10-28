"""
Normalized Feed Crawler Management API

Provides endpoints for managing the feed crawler system.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from jobs.feed_crawler import run_crawl_cycle
from database.connection import get_db
from utils.dependencies import get_current_user
from models.user import User
from models.feed import SharedFeed, FeedSubscription
from processors.feed_processor import NormalizedFeedProcessor

router = APIRouter()

class CrawlerStatusResponse(BaseModel):
    is_running: bool
    total_shared_feeds: int
    total_subscriptions: int
    active_subscriptions: int

class ForceCrawlRequest(BaseModel):
    feed_url: Optional[str] = None
    shared_feed_id: Optional[int] = None

class CrawlResultResponse(BaseModel):
    success: bool
    message: str
    new_articles: int = 0
    updated_articles: int = 0

@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get crawler status and statistics"""
    
    # Count shared feeds
    total_shared_feeds = db.query(SharedFeed).count()
    
    # Count total and active subscriptions
    total_subscriptions = db.query(FeedSubscription).count()
    active_subscriptions = db.query(FeedSubscription).filter(
        FeedSubscription.is_active == True
    ).count()
    
    return CrawlerStatusResponse(
        is_running=True,  # Since the job is always scheduled
        total_shared_feeds=total_shared_feeds,
        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions
    )

@router.post("/force-crawl", response_model=CrawlResultResponse)
async def force_crawl_feed(
    request: ForceCrawlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force crawl a specific feed or all feeds"""
    
    try:
        processor = NormalizedFeedProcessor(db)
        
        if request.shared_feed_id:
            # Crawl specific shared feed
            shared_feed = db.query(SharedFeed).filter(
                SharedFeed.id == request.shared_feed_id
            ).first()
            
            if not shared_feed:
                raise HTTPException(status_code=404, detail="Shared feed not found")
            
            result = await processor.process_shared_feed(shared_feed, db)
            
            if result and result.get('status') == 'success':
                return CrawlResultResponse(
                    success=True,
                    message=f"Successfully crawled feed: {shared_feed.default_name}",
                    new_articles=result.get('new_articles', 0),
                    updated_articles=result.get('updated_articles', 0)
                )
            else:
                return CrawlResultResponse(
                    success=False,
                    message=f"Failed to crawl feed: {shared_feed.default_name}"
                )
        
        elif request.feed_url:
            # Find shared feed by URL
            shared_feed = db.query(SharedFeed).filter(
                SharedFeed.url == request.feed_url
            ).first()
            
            if not shared_feed:
                raise HTTPException(status_code=404, detail="Feed with this URL not found")
            
            result = await processor.process_shared_feed(shared_feed, db)
            
            if result and result.get('status') == 'success':
                return CrawlResultResponse(
                    success=True,
                    message=f"Successfully crawled feed: {shared_feed.default_name}",
                    new_articles=result.get('new_articles', 0),
                    updated_articles=result.get('updated_articles', 0)
                )
            else:
                return CrawlResultResponse(
                    success=False,
                    message=f"Failed to crawl feed: {shared_feed.default_name}"
                )
        
        else:
            # Crawl all active shared feeds
            result = await run_crawl_cycle()
            
            return CrawlResultResponse(
                success=True,
                message="Successfully crawled all active feeds",
                new_articles=result.get('total_new_articles', 0),
                updated_articles=result.get('total_updated_articles', 0)
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")

@router.get("/feeds", response_model=List[dict])
async def list_crawlable_feeds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all shared feeds that can be crawled"""
    
    # Get all shared feeds with subscription counts
    feeds = db.query(SharedFeed).all()
    
    result = []
    for feed in feeds:
        subscription_count = db.query(FeedSubscription).filter(
            FeedSubscription.shared_feed_id == feed.id,
            FeedSubscription.is_active == True
        ).count()
        
        result.append({
            "id": feed.id,
            "name": feed.name,
            "url": feed.url,
            "description": feed.description,
            "is_active": feed.is_active,
            "last_crawled": feed.last_crawled,
            "crawl_error_count": feed.crawl_error_count,
            "subscription_count": subscription_count
        })
    
    return result
