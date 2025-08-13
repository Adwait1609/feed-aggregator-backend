from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from models.article import Article
from models.feed import RSSFeed
from processors.ml.ranking_engine import PersonalizationEngine
from utils.config import settings

router = APIRouter()

class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    description: Optional[str]
    author: Optional[str]
    published_at: datetime
    relevance_score: float
    feed_name: str
    cluster_id: Optional[str]
    
    class Config:
        from_attributes = True

class ArticleFilters(BaseModel):
    feed_ids: Optional[List[int]] = None
    min_relevance_score: Optional[float] = None
    cluster_id: Optional[str] = None
    hours_back: Optional[int] = 24

@router.get("/", response_model=List[ArticleResponse])
async def get_articles(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db)
):
    """Get articles feed"""
    try:
        # Base query - just get recent articles for now
        query = session.query(Article).join(RSSFeed)
        
        # Apply filters
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
                author=article.author,
                published_at=article.published_at,
                relevance_score=article.relevance_score,
                feed_name=article.feed.name,
                cluster_id=article.cluster_id
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch articles: {str(e)}")

@router.get("/similar/{article_id}")
async def get_similar_articles(
    article_id: int,
    limit: int = Query(5, le=20),
    session: Session = Depends(get_db)
):
    """Get articles similar to given article - placeholder for now"""
    try:
        # For now, just return empty list
        # We'll implement clustering later
        return []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch similar articles: {str(e)}")

@router.get("/{article_id}")
async def get_article(article_id: int, session: Session = Depends(get_db)):
    """Get single article by ID"""
    try:
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return ArticleResponse(
            id=article.id,
            title=article.title,
            url=article.url,
            description=article.description,
            author=article.author,
            published_at=article.published_at,
            relevance_score=article.relevance_score,
            feed_name=article.feed.name,
            cluster_id=article.cluster_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch article: {str(e)}")
