from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from enum import Enum
from models.base import BaseModel

class FeedbackType(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"

class SharedUserFeedback(BaseModel):
    """User feedback on articles (likes, bookmarks, etc.)"""
    __tablename__ = "shared_user_feedback"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("shared_articles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Feedback types
    is_liked = Column(Boolean, default=False)
    is_bookmarked = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    feedback_type = Column(SQLEnum(FeedbackType), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="shared_feedback")
    article = relationship("SharedArticle", back_populates="user_feedback")
    
    # Ensure feedback is unique per user-article
    __table_args__ = (
        UniqueConstraint('user_id', 'article_id', name='unique_user_article_feedback'),
    )
    
    def __str__(self):
        article_title = self.article.title[:50] if self.article else "Unknown"
        return f"SharedUserFeedback({self.user_id}, {article_title}, {self.feedback_type})"
