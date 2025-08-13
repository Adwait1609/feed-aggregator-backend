from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from models.article import Article
from models.feed import RSSFeed
from models.user import User
from utils.dependencies import get_current_active_user

router = APIRouter()

class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    description: Optional[str]
    content: Optional[str]
    author: Optional[str]
    published_at: datetime
    feed_name: str
    feed_id: int
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ArticleResponse])
async def get_user_articles(
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    feed_id: Optional[int] = Query(None),
    session: Session = Depends(get_db)
):
    """Get articles from user's RSS feeds"""
    try:
        # Base query - only articles from user's feeds
        query = session.query(Article).join(RSSFeed).filter(
            RSSFeed.user_id == current_user.id
        )
        
        # Filter by specific feed if specified (and user owns it)
        if feed_id:
            query = query.filter(Article.feed_id == feed_id)
        
        # Only active feeds
        query = query.filter(RSSFeed.is_active == True)
        
        # Sort by published date (newest first)
        query = query.order_by(Article.published_at.desc())
        
        # Pagination
        articles = query.offset(offset).limit(limit).all()
        
        # Format response
        response = []
        for article in articles:
            response.append(ArticleResponse(
                id=article.id,
                title=article.title,
                url=article.url,
                description=article.description,
                content=article.content,
                author=article.author,
                published_at=article.published_at,
                feed_name=article.feed.name,
                feed_id=article.feed_id
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch articles: {str(e)}")

@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Get single article by ID (user must own the feed)"""
    try:
        article = session.query(Article).join(RSSFeed).filter(
            Article.id == article_id,
            RSSFeed.user_id == current_user.id
        ).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return ArticleResponse(
            id=article.id,
            title=article.title,
            url=article.url,
            description=article.description,
            content=article.content,
            author=article.author,
            published_at=article.published_at,
            feed_name=article.feed.name,
            feed_id=article.feed_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch article: {str(e)}")
