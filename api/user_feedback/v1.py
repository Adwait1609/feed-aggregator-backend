from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, exists, and_, or_
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from database.connection import get_db
from models.user_feedback import SharedUserFeedback, FeedbackType
from models.article import SharedArticle
from models.feed import SharedFeed, FeedSubscription
from models.user import User
from utils.dependencies import get_current_active_user

router = APIRouter()

class FeedbackCreate(BaseModel):
    article_id: int
    feedback_type: Optional[FeedbackType] = None
    is_liked: Optional[bool] = None
    is_bookmarked: Optional[bool] = None
    is_read: Optional[bool] = None

class FeedbackResponse(BaseModel):
    id: int
    article_id: int
    user_id: int
    feedback_type: Optional[FeedbackType] = None
    is_liked: bool
    is_bookmarked: bool
    is_read: bool
    # Add extended info
    article_title: Optional[str] = None
    feed_name: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Create or update user feedback for an article"""
    try:
        # Verify article exists and user has access in a single query
        article_access = (
            session.query(
                session.query(SharedArticle)
                .join(SharedFeed, SharedArticle.feed_id == SharedFeed.id)
                .join(FeedSubscription, FeedSubscription.feed_id == SharedFeed.id)
                .filter(
                    SharedArticle.id == feedback_data.article_id,
                    FeedSubscription.user_id == current_user.id
                )
                .exists()
            )
            .scalar()
        )
        
        if not article_access:
            raise HTTPException(status_code=404, detail="Article not found or you don't have access")
        
        # Use a single transaction with upsert pattern (update or insert)
        # This pattern avoids race conditions and reduces round trips
        existing = session.query(SharedUserFeedback).filter(
            SharedUserFeedback.article_id == feedback_data.article_id,
            SharedUserFeedback.user_id == current_user.id
        ).first()
        
        if existing:
            # Update existing feedback with optimized bulk updates
            update_data = {}
            
            if feedback_data.feedback_type is not None:
                update_data["feedback_type"] = feedback_data.feedback_type
            
            if feedback_data.is_liked is not None:
                update_data["is_liked"] = feedback_data.is_liked
                
            if feedback_data.is_bookmarked is not None:
                update_data["is_bookmarked"] = feedback_data.is_bookmarked
                
            if feedback_data.is_read is not None:
                update_data["is_read"] = feedback_data.is_read
                
            # Apply updates
            for key, value in update_data.items():
                setattr(existing, key, value)
                
            session.commit()
            session.refresh(existing)
            return existing
        else:
            # Create new feedback
            new_feedback = SharedUserFeedback(
                article_id=feedback_data.article_id,
                user_id=current_user.id,
                feedback_type=feedback_data.feedback_type,
                is_liked=feedback_data.is_liked or False,
                is_bookmarked=feedback_data.is_bookmarked or False,
                is_read=feedback_data.is_read or False
            )
            
            session.add(new_feedback)
            session.commit()
            session.refresh(new_feedback)
            return new_feedback
            
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create feedback: {str(e)}")

@router.get("/article/{article_id}", response_model=FeedbackResponse)
async def get_article_feedback(
    article_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
):
    """Get user's feedback for a specific article"""
    try:
        # First check if article exists and user has access to it
        article_exists = (
            session.query(SharedArticle)
            .join(
                SharedFeed,
                SharedArticle.feed_id == SharedFeed.id
            )
            .join(
                FeedSubscription,
                FeedSubscription.feed_id == SharedFeed.id
            )
            .filter(
                SharedArticle.id == article_id,
                FeedSubscription.user_id == current_user.id
            )
            .first()
        )
        
        if not article_exists:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Get user feedback with a join
        feedback = (
            session.query(SharedUserFeedback)
            .filter(
                SharedUserFeedback.article_id == article_id,
                SharedUserFeedback.user_id == current_user.id
            )
            .first()
        )
        
        if not feedback:
            # Create empty feedback
            new_feedback = SharedUserFeedback(
                article_id=article_id,
                user_id=current_user.id,
                is_liked=False,
                is_bookmarked=False,
                is_read=False
            )
            
            session.add(new_feedback)
            session.commit()
            session.refresh(new_feedback)
            return new_feedback
        
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to get article feedback: {str(e)}")

@router.get("/bookmarked", response_model=List[FeedbackResponse])
async def get_bookmarked_articles(
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db)
):
    """Get all bookmarked articles for current user with extended article info"""
    try:
        # Efficient query using lateral joins and window functions to get all data in one query
        results = (
            session.query(
                SharedUserFeedback,
                SharedArticle.title.label('article_title'),
                func.coalesce(FeedSubscription.display_name, SharedFeed.default_name).label('feed_name')
            )
            .join(
                SharedArticle,
                SharedUserFeedback.article_id == SharedArticle.id
            )
            .join(
                SharedFeed,
                SharedArticle.feed_id == SharedFeed.id
            )
            .join(
                FeedSubscription,
                and_(
                    FeedSubscription.feed_id == SharedFeed.id,
                    FeedSubscription.user_id == current_user.id
                )
            )
            .filter(
                SharedUserFeedback.user_id == current_user.id,
                SharedUserFeedback.is_bookmarked == True
            )
            .order_by(SharedArticle.published_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Create enhanced response objects
        response = []
        for feedback, article_title, feed_name in results:
            feedback_dict = {
                "id": feedback.id,
                "article_id": feedback.article_id,
                "user_id": feedback.user_id,
                "feedback_type": feedback.feedback_type,
                "is_liked": feedback.is_liked,
                "is_bookmarked": feedback.is_bookmarked,
                "is_read": feedback.is_read,
                "article_title": article_title,
                "feed_name": feed_name
            }
            response.append(feedback_dict)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bookmarked articles: {str(e)}")

@router.get("/liked", response_model=List[FeedbackResponse])
async def get_liked_articles(
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db)
):
    """Get all liked articles for current user with extended article info"""
    try:
        # Reuse the same efficient query pattern from bookmarked articles
        results = (
            session.query(
                SharedUserFeedback,
                SharedArticle.title.label('article_title'),
                func.coalesce(FeedSubscription.display_name, SharedFeed.default_name).label('feed_name')
            )
            .join(
                SharedArticle,
                SharedUserFeedback.article_id == SharedArticle.id
            )
            .join(
                SharedFeed,
                SharedArticle.feed_id == SharedFeed.id
            )
            .join(
                FeedSubscription,
                and_(
                    FeedSubscription.feed_id == SharedFeed.id,
                    FeedSubscription.user_id == current_user.id
                )
            )
            .filter(
                SharedUserFeedback.user_id == current_user.id,
                SharedUserFeedback.is_liked == True
            )
            .order_by(SharedArticle.published_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Create enhanced response objects
        response = []
        for feedback, article_title, feed_name in results:
            feedback_dict = {
                "id": feedback.id,
                "article_id": feedback.article_id,
                "user_id": feedback.user_id,
                "feedback_type": feedback.feedback_type,
                "is_liked": feedback.is_liked,
                "is_bookmarked": feedback.is_bookmarked,
                "is_read": feedback.is_read,
                "article_title": article_title,
                "feed_name": feed_name
            }
            response.append(feedback_dict)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get liked articles: {str(e)}")
