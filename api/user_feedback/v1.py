from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from models.user_feedback import UserFeedback, FeedbackType
from models.article import Article

router = APIRouter()

class FeedbackCreate(BaseModel):
    article_id: int
    feedback_type: FeedbackType
    user_id: str = "default_user"

class FeedbackResponse(BaseModel):
    id: int
    article_id: int
    user_id: str
    feedback_type: FeedbackType
    
    class Config:
        from_attributes = True

@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    feedback_data: FeedbackCreate,
    session: Session = Depends(get_db)
):
    """Create user feedback for an article"""
    try:
        # Check if article exists
        article = session.query(Article).filter(Article.id == feedback_data.article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Check if feedback already exists
        existing = session.query(UserFeedback).filter(
            UserFeedback.article_id == feedback_data.article_id,
            UserFeedback.user_id == feedback_data.user_id
        ).first()
        
        if existing:
            # Update existing feedback
            existing.feedback_type = feedback_data.feedback_type
            session.commit()
            session.refresh(existing)
            return existing
        else:
            # Create new feedback
            feedback = UserFeedback(
                article_id=feedback_data.article_id,
                user_id=feedback_data.user_id,
                feedback_type=feedback_data.feedback_type
            )
            
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            
            return feedback
            
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create feedback: {str(e)}")
