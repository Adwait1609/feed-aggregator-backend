from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, exists
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from models.article import SharedArticle
from models.feed import SharedFeed, FeedSubscription
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
    subscription_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    session: Session = Depends(get_db)
):
    """Get articles from user's subscribed feeds with advanced filtering"""
    try:
        # Use a subquery to get all user's subscribed feed IDs for better performance
        subscribed_feeds = (
            session.query(FeedSubscription.feed_id)
            .filter(
                FeedSubscription.user_id == current_user.id,
                FeedSubscription.is_active == True
            )
        )
        
        if subscription_id:
            subscribed_feeds = subscribed_feeds.filter(FeedSubscription.id == subscription_id)
        
        # Base query with optimized joins using subquery
        query = (
            session.query(
                SharedArticle,
                FeedSubscription.display_name,
                SharedFeed.default_name
            )
            .join(
                SharedFeed, 
                SharedArticle.feed_id == SharedFeed.id
            )
            .join(
                FeedSubscription, 
                (FeedSubscription.feed_id == SharedFeed.id) & 
                (FeedSubscription.user_id == current_user.id)
            )
            .filter(SharedArticle.feed_id.in_(subscribed_feeds))
        )
        
        # Add dynamic filtering based on parameters
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (SharedArticle.title.ilike(search_pattern)) | 
                (SharedArticle.description.ilike(search_pattern))
            )
            
        if from_date:
            query = query.filter(SharedArticle.published_at >= from_date)
            
        if to_date:
            query = query.filter(SharedArticle.published_at <= to_date)
            
        # Get total count for pagination metadata (using a more efficient count query)
        total_count = query.with_entities(SharedArticle.id).distinct().count()
        
        if total_count == 0:
            return []
            
        # Apply ordering, offset and limit with index hints
        results = (
            query
            .order_by(SharedArticle.published_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Create response objects
        response = []
        for article, subscription_name, feed_default_name in results:
            feed_name = subscription_name or feed_default_name
            
            response.append({
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "description": article.description,
                "content": article.content,
                "author": article.author,
                "published_at": article.published_at,
                "feed_name": feed_name,
                "feed_id": article.feed_id
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get articles: {str(e)}")

@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article_detail(
    article_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Get details of a specific article"""
    try:
        # Use EXISTS subquery for efficient permission check
        user_has_access = (
            session.query(
                session.query(FeedSubscription)
                .join(SharedFeed, FeedSubscription.feed_id == SharedFeed.id)
                .join(SharedArticle, SharedArticle.feed_id == SharedFeed.id)
                .filter(
                    SharedArticle.id == article_id,
                    FeedSubscription.user_id == current_user.id,
                    FeedSubscription.is_active == True
                )
                .exists()
            )
            .scalar()
        )
        
        if not user_has_access:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Efficient query for article with feed data
        result = (
            session.query(
                SharedArticle,
                # Use a CASE expression for the feed name
                session.query(
                    func.coalesce(FeedSubscription.display_name, SharedFeed.default_name)
                )
                .filter(
                    FeedSubscription.feed_id == SharedArticle.feed_id,
                    FeedSubscription.user_id == current_user.id
                )
                .as_scalar()
                .label('feed_name')
            )
            .filter(SharedArticle.id == article_id)
            .first()
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Article not found")
        
        article, feed_name = result
        
        return {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "description": article.description,
            "content": article.content,
            "author": article.author,
            "published_at": article.published_at,
            "feed_name": feed_name,
            "feed_id": article.feed_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get article: {str(e)}")

@router.get("/subscription/{subscription_id}", response_model=List[ArticleResponse])
async def get_articles_by_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db)
):
    """Get articles from a specific feed subscription"""
    try:
        # Single query with joins to get articles with feed and subscription data
        results = (
            session.query(
                SharedArticle,
                FeedSubscription.display_name,
                SharedFeed.default_name
            )
            .join(
                SharedFeed, 
                SharedArticle.feed_id == SharedFeed.id
            )
            .join(
                FeedSubscription, 
                FeedSubscription.feed_id == SharedFeed.id
            )
            .filter(
                FeedSubscription.id == subscription_id,
                FeedSubscription.user_id == current_user.id
            )
            .order_by(SharedArticle.published_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        if not results:
            # Check if subscription exists but has no articles
            subscription = session.query(FeedSubscription).filter(
                FeedSubscription.id == subscription_id,
                FeedSubscription.user_id == current_user.id
            ).first()
            
            if not subscription:
                raise HTTPException(status_code=404, detail="Feed subscription not found")
            return []
        
        # Create response objects
        response = []
        for article, subscription_name, feed_default_name in results:
            feed_name = subscription_name or feed_default_name
            
            response.append({
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "description": article.description,
                "content": article.content,
                "author": article.author,
                "published_at": article.published_at,
                "feed_name": feed_name,
                "feed_id": article.feed_id
            })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get articles: {str(e)}")
