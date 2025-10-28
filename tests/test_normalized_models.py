import pytest
from models.user import User
from models.feed import SharedFeed, FeedSubscription
from models.article import SharedArticle
from datetime import datetime, timezone

class TestUserModel:
    """Test User model functionality"""
    
    def test_user_creation(self, test_db):
        """Test creating a user"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashedpassword123",
            is_active=True
        )
        
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.created_at is not None

class TestNormalizedFeedModel:
    """Test normalized feed models functionality"""
    
    def test_shared_feed_creation(self, test_db):
        """Test creating a shared feed"""
        feed = SharedFeed(
            url="https://example.com/feed.xml",
            default_name="Test Feed",
            default_description="A test RSS feed"
        )
        
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        assert feed.id is not None
        assert feed.url == "https://example.com/feed.xml"
        assert feed.default_name == "Test Feed"
        assert feed.created_at is not None

    def test_feed_subscription_creation(self, test_db):
        """Test creating a feed subscription"""
        # Create user and shared feed first
        user = User(username="testuser", email="test@example.com", hashed_password="hashedpassword123")
        test_db.add(user)
        test_db.flush()
        
        shared_feed = SharedFeed(url="https://example.com/feed.xml", default_name="Test Feed")
        test_db.add(shared_feed)
        test_db.flush()
        
        # Create subscription
        subscription = FeedSubscription(
            user_id=user.id,
            feed_id=shared_feed.id,
            display_name="My Custom Feed Name",
            crawl_frequency_minutes=30,
            is_active=True
        )
        
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)
        
        assert subscription.id is not None
        assert subscription.user_id == user.id
        assert subscription.feed_id == shared_feed.id
        assert subscription.display_name == "My Custom Feed Name"
        assert subscription.crawl_frequency_minutes == 30
        assert subscription.is_active is True

    def test_feed_subscription_relationships(self, test_db):
        """Test feed subscription relationships"""
        # Create user and shared feed
        user = User(username="testuser", email="test@example.com", hashed_password="hashedpassword123")
        test_db.add(user)
        test_db.flush()
        
        shared_feed = SharedFeed(url="https://example.com/feed.xml", default_name="Test Feed")
        test_db.add(shared_feed)
        test_db.flush()
        
        subscription = FeedSubscription(
            user_id=user.id,
            feed_id=shared_feed.id,
            display_name="My Feed"
        )
        test_db.add(subscription)
        test_db.commit()
        
        # Test relationships
        assert subscription.user == user
        assert subscription.feed == shared_feed
        assert subscription in user.feed_subscriptions
        assert subscription in shared_feed.subscriptions

class TestNormalizedArticleModel:
    """Test normalized article model functionality"""
    
    def test_shared_article_creation(self, test_db):
        """Test creating a shared article"""
        # Create shared feed first
        shared_feed = SharedFeed(url="https://example.com/feed.xml", default_name="Test Feed")
        test_db.add(shared_feed)
        test_db.flush()
        
        article = SharedArticle(
            feed_id=shared_feed.id,
            title="Test Article",
            url="https://example.com/article1",
            description="A test article",
            content="This is test content",
            author="Test Author",
            published_at=datetime.now(timezone.utc)
        )
        
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        assert article.id is not None
        assert article.feed_id == shared_feed.id
        assert article.title == "Test Article"
        assert article.url == "https://example.com/article1"
        assert article.author == "Test Author"
        assert article.published_at is not None

    def test_article_feed_relationship(self, test_db):
        """Test article-feed relationship"""
        shared_feed = SharedFeed(url="https://example.com/feed.xml", default_name="Test Feed")
        test_db.add(shared_feed)
        test_db.flush()
        
        article = SharedArticle(
            feed_id=shared_feed.id,
            title="Test Article",
            url="https://example.com/article1"
        )
        test_db.add(article)
        test_db.commit()
        
        # Test relationship
        assert article.feed == shared_feed
        assert article in shared_feed.articles

class TestNormalizedSchema:
    """Test normalized schema constraints and relationships"""
    
    def test_unique_feed_url_constraint(self, test_db):
        """Test that feed URLs must be unique"""
        feed1 = SharedFeed(url="https://example.com/feed.xml", default_name="Feed 1")
        feed2 = SharedFeed(url="https://example.com/feed.xml", default_name="Feed 2")
        
        test_db.add(feed1)
        test_db.commit()
        
        test_db.add(feed2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()

    def test_unique_user_feed_subscription_constraint(self, test_db):
        """Test that users can only subscribe once to each feed"""
        user = User(username="testuser", email="test@example.com", hashed_password="hashedpassword123")
        test_db.add(user)
        test_db.flush()
        
        shared_feed = SharedFeed(url="https://example.com/feed.xml", default_name="Test Feed")
        test_db.add(shared_feed)
        test_db.flush()
        
        subscription1 = FeedSubscription(user_id=user.id, feed_id=shared_feed.id)
        subscription2 = FeedSubscription(user_id=user.id, feed_id=shared_feed.id)
        
        test_db.add(subscription1)
        test_db.commit()
        
        test_db.add(subscription2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()
