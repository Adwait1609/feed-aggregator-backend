from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, case, literal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from database.connection import get_db
from models.feed import SharedFeed, FeedSubscription
from models.article import SharedArticle
from models.user import User
from processors.feed_processor import NormalizedFeedProcessor
from utils.dependencies import get_current_active_user

router = APIRouter()

class FeedCreate(BaseModel):
    name: str
    url: str
    description: str = ""
    crawl_frequency_minutes: int = 60  # Default: every hour

class FeedUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    crawl_frequency_minutes: Optional[int] = None
    is_active: Optional[bool] = None

class FeedResponse(BaseModel):
    id: int
    name: str
    url: str
    description: str
    is_active: bool
    crawl_frequency_minutes: int
    last_crawled_at: Optional[datetime] = None
    article_count: Optional[int] = None
    newest_article_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[FeedResponse])
async def get_user_feeds(
    current_user: User = Depends(get_current_active_user),
    include_stats: bool = Query(False, description="Include article statistics"),
    session: Session = Depends(get_db)
):
    """Get all RSS feeds for current user with optimized queries"""
    
    # Use a CTE (Common Table Expression) equivalent in SQLAlchemy for better query organization
    if include_stats:
        # With article stats - using subqueries for better performance
        results = (
            session.query(
                FeedSubscription,
                SharedFeed,
                # Count of articles (as a scalar subquery)
                session.query(func.count(SharedArticle.id))
                .filter(SharedArticle.feed_id == SharedFeed.id)
                .label('article_count'),
                # Latest article date (as a scalar subquery)
                session.query(func.max(SharedArticle.published_at))
                .filter(SharedArticle.feed_id == SharedFeed.id)
                .label('newest_article_date')
            )
            .join(
                SharedFeed,
                FeedSubscription.feed_id == SharedFeed.id
            )
            .filter(
                FeedSubscription.user_id == current_user.id
            )
            .order_by(FeedSubscription.priority)
            .all()
        )
        
        # Convert to response format
        feeds = []
        for subscription, feed, article_count, newest_date in results:
            feeds.append({
                "id": subscription.id,
                "name": subscription.display_name or feed.default_name,
                "url": feed.url,
                "description": subscription.description or feed.default_description or "",
                "is_active": subscription.is_active,
                "crawl_frequency_minutes": subscription.crawl_frequency_minutes,
                "priority": subscription.priority,
                "last_crawled_at": feed.last_crawled_at,
                "article_count": article_count,
                "newest_article_date": newest_date
            })
    else:
        # Without article stats - simple efficient join
        results = (
            session.query(
                FeedSubscription,
                SharedFeed
            )
            .join(
                SharedFeed,
                FeedSubscription.feed_id == SharedFeed.id
            )
            .filter(
                FeedSubscription.user_id == current_user.id
            )
            .order_by(FeedSubscription.priority)
            .all()
        )
        
        # Convert to response format
        feeds = []
        for subscription, feed in results:
            feeds.append({
                "id": subscription.id,
                "name": subscription.display_name or feed.default_name,
                "url": feed.url,
                "description": subscription.description or feed.default_description or "",
                "is_active": subscription.is_active,
                "crawl_frequency_minutes": subscription.crawl_frequency_minutes,
                "priority": subscription.priority,
                "last_crawled_at": feed.last_crawled_at
            })
    
    return feeds

@router.post("/", response_model=FeedResponse, status_code=201)
async def create_feed(
    feed_data: FeedCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Add a new RSS feed for current user"""
    try:
        # Validate frequency (minimum 15 minutes, maximum 24 hours)
        if not (15 <= feed_data.crawl_frequency_minutes <= 1440):
            raise HTTPException(
                status_code=400, 
                detail="Crawl frequency must be between 15 minutes and 24 hours"
            )
        
        # Check if user already has a subscription to this feed
        existing_feed = session.query(SharedFeed).filter(
            SharedFeed.url == feed_data.url
        ).first()
        
        if existing_feed:
            # Check if user already has a subscription
            existing_subscription = session.query(FeedSubscription).filter(
                FeedSubscription.user_id == current_user.id,
                FeedSubscription.feed_id == existing_feed.id
            ).first()
            
            if existing_subscription:
                raise HTTPException(status_code=400, detail="You already have this feed URL")
            
            # Create new subscription to existing feed
            subscription = FeedSubscription(
                user_id=current_user.id,
                feed_id=existing_feed.id,
                display_name=feed_data.name,
                description=feed_data.description,
                crawl_frequency_minutes=feed_data.crawl_frequency_minutes,
                is_active=True
            )
            
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            
            return {
                "id": subscription.id,
                "name": subscription.display_name or existing_feed.default_name,
                "url": existing_feed.url,
                "description": subscription.description or existing_feed.default_description or "",
                "is_active": subscription.is_active,
                "crawl_frequency_minutes": subscription.crawl_frequency_minutes,
                "priority": subscription.priority,
                "last_crawled_at": existing_feed.last_crawled_at
            }
        else:
            # Create new shared feed
            shared_feed = SharedFeed(
                url=feed_data.url,
                default_name=feed_data.name,
                default_description=feed_data.description
            )
            
            session.add(shared_feed)
            session.flush()  # Get ID but don't commit yet
            
            # Create subscription
            subscription = FeedSubscription(
                user_id=current_user.id,
                feed_id=shared_feed.id,
                display_name=feed_data.name,
                description=feed_data.description,
                crawl_frequency_minutes=feed_data.crawl_frequency_minutes,
                is_active=True
            )
            
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            
            # Attempt to crawl the feed immediately (async)
            try:
                processor = NormalizedFeedProcessor()
                # This will run in the background - don't await
                processor.process_shared_feed(shared_feed, session)
            except Exception as e:
                logger.error(f"Failed to crawl new feed: {e}")
            
            return {
                "id": subscription.id,
                "name": subscription.display_name or shared_feed.default_name,
                "url": shared_feed.url,
                "description": subscription.description or shared_feed.default_description or "",
                "is_active": subscription.is_active,
                "crawl_frequency_minutes": subscription.crawl_frequency_minutes,
                "priority": subscription.priority,
                "last_crawled_at": shared_feed.last_crawled_at
            }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create feed: {str(e)}")

@router.put("/{subscription_id}", response_model=FeedResponse)
async def update_feed(
    subscription_id: int,
    feed_update: FeedUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Update user's feed subscription"""
    try:
        # Get subscription and verify ownership
        subscription = session.query(FeedSubscription).filter(
            FeedSubscription.id == subscription_id,
            FeedSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Feed subscription not found")
        
        # Update subscription fields
        if feed_update.name is not None:
            subscription.display_name = feed_update.name
        
        if feed_update.description is not None:
            subscription.description = feed_update.description
        
        if feed_update.is_active is not None:
            subscription.is_active = feed_update.is_active
        
        if feed_update.crawl_frequency_minutes is not None:
            # Validate frequency
            if not (15 <= feed_update.crawl_frequency_minutes <= 1440):
                raise HTTPException(
                    status_code=400, 
                    detail="Crawl frequency must be between 15 minutes and 24 hours"
                )
            subscription.crawl_frequency_minutes = feed_update.crawl_frequency_minutes
        
        if feed_update.priority is not None:
            if not (1 <= feed_update.priority <= 3):
                raise HTTPException(
                    status_code=400, 
                    detail="Priority must be between 1 (high) and 3 (low)"
                )
            subscription.priority = feed_update.priority
        
        session.commit()
        session.refresh(subscription)
        
        shared_feed = subscription.feed
        
        return {
            "id": subscription.id,
            "name": subscription.display_name or shared_feed.default_name,
            "url": shared_feed.url,
            "description": subscription.description or shared_feed.default_description or "",
            "is_active": subscription.is_active,
            "crawl_frequency_minutes": subscription.crawl_frequency_minutes,
            "priority": subscription.priority,
            "last_crawled_at": shared_feed.last_crawled_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update feed: {str(e)}")

@router.delete("/{subscription_id}")
async def delete_feed(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Delete user's feed subscription"""
    try:
        # Get subscription and verify ownership
        subscription = session.query(FeedSubscription).filter(
            FeedSubscription.id == subscription_id,
            FeedSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Feed subscription not found")
        
        # Delete subscription
        session.delete(subscription)
        session.commit()
        
        return {"detail": "Feed subscription deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete feed: {str(e)}")

@router.post("/{subscription_id}/crawl")
async def crawl_feed_manually(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Manually crawl a feed"""
    try:
        # Get subscription and verify ownership
        subscription = session.query(FeedSubscription).filter(
            FeedSubscription.id == subscription_id,
            FeedSubscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Feed subscription not found")
        
        shared_feed = subscription.feed
        
        # Crawl the feed
        processor = NormalizedFeedProcessor()
        result = await processor.process_shared_feed(shared_feed, session)
        
        if result.get("status") == "success":
            return {
                "detail": f"Feed crawled successfully. {result.get('new_articles', 0)} new articles, {result.get('updated_articles', 0)} updated."
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to crawl feed: {result.get('error', 'Unknown error')}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to crawl feed: {str(e)}")
