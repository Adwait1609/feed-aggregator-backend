from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import BaseModel

class RSSFeed(BaseModel):
    __tablename__ = "rss_feeds"
    
    name = Column(String(200), nullable=False)
    url = Column(String(1000), nullable=False, index=True)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    # User ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Crawling metadata
    last_crawled_at = Column(DateTime)
    crawl_frequency_minutes = Column(Integer, default=60)  # Every hour
    last_successful_crawl = Column(DateTime)
    crawl_error_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="feeds")
    articles = relationship("Article", back_populates="feed")
    
    def __str__(self):
        return f"RSSFeed({self.name} - User: {self.user_id})"
