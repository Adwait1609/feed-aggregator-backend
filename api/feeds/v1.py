from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from database.connection import get_db
from models.feed import RSSFeed
from models.article import Article
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

@router.delete("/{feed_id}", status_code=204)
async def delete_feed(
    feed_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Delete user's feed and all associated articles and feedback"""
    try:
        feed = session.query(RSSFeed).filter(
            RSSFeed.id == feed_id,
            RSSFeed.user_id == current_user.id
        ).first()
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        # Count items before deletion for logging
        article_count = session.query(Article).filter(Article.feed_id == feed_id).count()
        
        # Count user feedback that will be deleted
        from models.user_feedback import UserFeedback
        feedback_count = session.query(UserFeedback).join(Article).filter(Article.feed_id == feed_id).count()
        
        logger.info(f"Deleting feed '{feed.name}' (ID: {feed_id}) with {article_count} articles and {feedback_count} feedback records for user {current_user.username}")
        
        # EXPLICIT DELETION ORDER to handle existing data:
        # 1. First delete user feedback for articles in this feed
        feedback_to_delete = session.query(UserFeedback).join(Article).filter(Article.feed_id == feed_id).all()
        for feedback in feedback_to_delete:
            session.delete(feedback)
        
        # 2. Then delete articles in this feed
        articles_to_delete = session.query(Article).filter(Article.feed_id == feed_id).all()
        for article in articles_to_delete:
            session.delete(article)
        
        # 3. Finally delete the feed
        session.delete(feed)
        session.commit()
        
        logger.info(f"Successfully deleted feed '{feed.name}', {article_count} articles, and {feedback_count} feedback records")
        return  # No content for 204
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to delete feed {feed_id}: {str(e)}")
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
