from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from models.base import BaseModel

class Article(BaseModel):
    __tablename__ = "articles"
    
    title = Column(String(500), nullable=False, index=True)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    description = Column(Text)
    content = Column(Text)
    author = Column(String(200))
    published_at = Column(DateTime, nullable=False, index=True)
    
    # RSS Feed relationship
    feed_id = Column(Integer, ForeignKey("rss_feeds.id"), nullable=False, index=True)
    feed = relationship("RSSFeed", back_populates="articles")
    
    # ML Features
    relevance_score = Column(Float, default=0.0)  # Personalization score
    cluster_id = Column(String(50), index=True)   # Article cluster
    embedding_generated = Column(Boolean, default=False)
    
    # User interaction
    user_feedbacks = relationship("UserFeedback", back_populates="article")
    
    @property
    def clean_content(self) -> str:
        """Return cleaned content for ML processing"""
        return f"{self.title} {self.description or ''} {self.content or ''}"
