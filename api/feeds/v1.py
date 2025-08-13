from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from models.feed import RSSFeed
from processors.feed_processor import FeedProcessor

router = APIRouter()

class FeedCreate(BaseModel):
    name: str
    url: str
    description: str = ""

class FeedResponse(BaseModel):
    id: int
    name: str
    url: str
    description: str
    is_active: bool
    last_crawled_at: datetime = None
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[FeedResponse])
async def get_feeds(session: Session = Depends(get_db)):
    """Get all RSS feeds"""
    feeds = session.query(RSSFeed).all()
    return feeds

@router.post("/", response_model=FeedResponse)
async def create_feed(feed_data: FeedCreate, session: Session = Depends(get_db)):
    """Add a new RSS feed"""
    try:
        # Check if feed already exists
        existing = session.query(RSSFeed).filter(RSSFeed.url == feed_data.url).first()
        if existing:
            raise HTTPException(status_code=400, detail="Feed URL already exists")
        
        # Create new feed
        feed = RSSFeed(
            name=feed_data.name,
            url=feed_data.url,
            description=feed_data.description
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

@router.post("/{feed_id}/crawl")
async def crawl_feed(feed_id: int, session: Session = Depends(get_db)):
    """Manually trigger crawling for a specific feed"""
    try:
        feed = session.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        processor = FeedProcessor()
        result = await processor.process_feed(feed, session)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to crawl feed: {str(e)}")
