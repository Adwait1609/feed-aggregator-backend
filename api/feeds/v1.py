from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from models.feed import RSSFeed
from models.user import User
from processors.feed_processor import FeedProcessor
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
    last_successful_crawl: Optional[datetime] = None
    crawl_error_count: int
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[FeedResponse])
async def get_user_feeds(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Get all RSS feeds for current user"""
    feeds = session.query(RSSFeed).filter(RSSFeed.user_id == current_user.id).all()
    return feeds

@router.post("/", response_model=FeedResponse)
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
        
        # Check if user already has this feed URL
        existing = session.query(RSSFeed).filter(
            RSSFeed.url == feed_data.url,
            RSSFeed.user_id == current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="You already have this feed URL")
        
        # Create new feed for current user
        feed = RSSFeed(
            name=feed_data.name,
            url=feed_data.url,
            description=feed_data.description,
            crawl_frequency_minutes=feed_data.crawl_frequency_minutes,
            user_id=current_user.id
        )
        
        session.add(feed)
        session.commit()
        session.refresh(feed)
        
        return feed
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create feed: {str(e)}")

@router.put("/{feed_id}", response_model=FeedResponse)
async def update_feed(
    feed_id: int,
    feed_update: FeedUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Update user's feed settings"""
    try:
        feed = session.query(RSSFeed).filter(
            RSSFeed.id == feed_id,
            RSSFeed.user_id == current_user.id
        ).first()
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        # Update fields
        if feed_update.name is not None:
            feed.name = feed_update.name
        if feed_update.description is not None:
            feed.description = feed_update.description
        if feed_update.is_active is not None:
            feed.is_active = feed_update.is_active
        if feed_update.crawl_frequency_minutes is not None:
            if not (15 <= feed_update.crawl_frequency_minutes <= 1440):
                raise HTTPException(
                    status_code=400, 
                    detail="Crawl frequency must be between 15 minutes and 24 hours"
                )
            feed.crawl_frequency_minutes = feed_update.crawl_frequency_minutes
        
        session.commit()
        session.refresh(feed)
        
        return feed
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update feed: {str(e)}")

@router.delete("/{feed_id}")
async def delete_feed(
    feed_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Delete user's feed"""
    try:
        feed = session.query(RSSFeed).filter(
            RSSFeed.id == feed_id,
            RSSFeed.user_id == current_user.id
        ).first()
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        session.delete(feed)
        session.commit()
        
        return {"message": "Feed deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete feed: {str(e)}")

@router.post("/{feed_id}/crawl")
async def crawl_feed(
    feed_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Manually trigger crawling for a specific user's feed"""
    try:
        feed = session.query(RSSFeed).filter(
            RSSFeed.id == feed_id,
            RSSFeed.user_id == current_user.id
        ).first()
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        processor = FeedProcessor()
        result = await processor.process_feed(feed, session)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to crawl feed: {str(e)}")
