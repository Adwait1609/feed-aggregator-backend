from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.orm import relationship
from models.base import BaseModel

class RSSFeed(BaseModel):
    __tablename__ = "rss_feeds"
    
    name = Column(String(200), nullable=False)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    # Crawling metadata
    last_crawled_at = Column(DateTime)
    crawl_frequency_minutes = Column(Integer, default=60)  # Every hour
    
    # Relationships
    articles = relationship("Article", back_populates="feed")
    
    def __str__(self):
        return f"RSSFeed({self.name})"
