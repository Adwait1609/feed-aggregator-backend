from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum
from models.base import BaseModel

class FeedbackType(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"

class UserFeedback(BaseModel):
    __tablename__ = "user_feedback"
    
    # For now, we'll use a simple user system
    user_id = Column(String(50), nullable=False, index=True, default="default_user")
    
    # Article relationship
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    article = relationship("Article", back_populates="user_feedbacks")
    
    # Feedback
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    
    def __str__(self):
        return f"UserFeedback({self.user_id}, {self.article.title[:50]}, {self.feedback_type})"
