from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import BaseModel

class SharedFeed(BaseModel):
    """Stores unique feed URLs, shared across all users"""
    __tablename__ = "shared_feeds"
    
    url = Column(String(1000), unique=True, nullable=False, index=True)
    default_name = Column(String(255), nullable=False)
    default_description = Column(String(1000))
    last_crawled_at = Column(DateTime, nullable=True)
    last_successful_crawl = Column(DateTime, nullable=True)
    crawl_error_count = Column(Integer, default=0)
    
    # Relationships
    articles = relationship("SharedArticle", back_populates="feed", cascade="all, delete-orphan")
    subscriptions = relationship("FeedSubscription", back_populates="feed", cascade="all, delete-orphan")
    
    def __str__(self):
        return f"SharedFeed({self.default_name})"


class FeedSubscription(BaseModel):
    """Many-to-many relationship between users and feeds"""
    __tablename__ = "feed_subscriptions"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feed_id = Column(Integer, ForeignKey("shared_feeds.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # User-specific feed preferences
    display_name = Column(String(255), nullable=True)  # User can rename feeds
    description = Column(String(1000), nullable=True)  # User-specific description
    crawl_frequency_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="feed_subscriptions")
    feed = relationship("SharedFeed", back_populates="subscriptions")
    
    # Ensure each user can only subscribe once to a feed
    __table_args__ = (
        UniqueConstraint('user_id', 'feed_id', name='unique_user_feed_subscription'),
    )
    
    def __str__(self):
        feed_name = self.display_name or (self.feed.default_name if self.feed else "Unknown")
        return f"FeedSubscription({feed_name} - User: {self.user_id})"
