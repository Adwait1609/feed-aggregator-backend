from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import BaseModel

class SharedArticle(BaseModel):
    """Stores articles, linked to shared feeds (not duplicated per user)"""
    __tablename__ = "shared_articles"
    
    feed_id = Column(Integer, ForeignKey("shared_feeds.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    url = Column(String(1000), nullable=False, index=True)
    description = Column(Text)  # RSS summary/description
    content = Column(Text)  # Full content if available
    author = Column(String(200))
    published_at = Column(DateTime, nullable=False, index=True)
    
    # Content metadata
    content_hash = Column(String(32), index=True)  # For duplicate detection
    
    # Additional fields
    sentiment_score = Column(Integer, nullable=True)
    category = Column(String(100), nullable=True)
    keywords = Column(String, nullable=True)
    
    # Relationships
    feed = relationship("SharedFeed", back_populates="articles")
    user_feedback = relationship("SharedUserFeedback", back_populates="article", cascade="all, delete-orphan")
    
    # Ensure articles are unique per feed
    __table_args__ = (
        UniqueConstraint('feed_id', 'url', name='unique_article_per_feed'),
    )
    
    @property
    def clean_content(self) -> str:
        """Return cleaned content for processing"""
        return f"{self.title} {self.description or ''} {self.content or ''}"
