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
    personalized: bool = Query(True),
    session: Session = Depends(get_db)
):
    """Get personalized article feed - main endpoint like your topic search"""
    try:
        # Base query
        query = session.query(Article).join(RSSFeed)
        
        # Apply filters
        query = query.filter(RSSFeed.is_active == True)
        
        if personalized:
            # Sort by relevance score (personalized ranking)
            query = query.order_by(Article.relevance_score.desc())
        else:
            # Sort by published date
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
    """Get articles similar to given article - semantic clustering"""
    try:
        # Get the target article
        target_article = session.query(Article).filter(Article.id == article_id).first()
        if not target_article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        if not target_article.cluster_id:
            return []  # No cluster assigned yet
        
        # Find articles in same cluster
        similar_articles = session.query(Article).filter(
            Article.cluster_id == target_article.cluster_id,
            Article.id != article_id
        ).order_by(Article.relevance_score.desc()).limit(limit).all()
        
        return [ArticleResponse.from_orm(article) for article in similar_articles]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch similar articles: {str(e)}")

@router.post("/update-relevance")
async def update_article_relevance(
    session: Session = Depends(get_db)
):
    """Update relevance scores for all articles - background ML processing"""
    try:
        # Initialize personalization engine
        engine = PersonalizationEngine()
        engine.load_model()
        
        # Get articles without relevance scores
        articles = session.query(Article).filter(
            Article.relevance_score == 0.0
        ).limit(1000).all()
        
        if not articles:
            return {"message": "No articles to update"}
        
        # Predict relevance scores
        scores = engine.predict_relevance(articles)
        
        # Update articles
        for article, score in zip(articles, scores):
            article.relevance_score = score
        
        session.commit()
        
        return {
            "message": f"Updated relevance scores for {len(articles)} articles",
            "updated_count": len(articles)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update relevance: {str(e)}")
