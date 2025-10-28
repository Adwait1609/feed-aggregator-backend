import pytest
from models.user import User
from models.feed import SharedFeed, FeedSubscription
from models.article import SharedArticle
from models.user_feedback import SharedUserFeedback
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
    
    def test_user_str_representation(self, test_db):
        """Test user string representation"""
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        assert str(user) == "User(testuser)"

class TestSharedFeedModel:
    """Test SharedFeed model functionality"""
    
    def test_shared_feed_creation(self, test_db):
        """Test creating a shared feed"""
        feed = SharedFeed(
            name="Test Feed",
            url="https://example.com/feed.xml",
            description="Test feed description"
        )
        
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        assert feed.id is not None
        assert feed.name == "Test Feed"
        assert feed.url == "https://example.com/feed.xml"
        assert feed.description == "Test feed description"
        assert feed.is_active is True
        assert feed.last_crawled is None
        assert feed.crawl_error_count == 0
    
    def test_shared_feed_str_representation(self, test_db):
        """Test shared feed string representation"""
        feed = SharedFeed(name="Test Feed", url="https://example.com/feed.xml")
        assert str(feed) == "SharedFeed(Test Feed)"

class TestFeedSubscriptionModel:
    """Test FeedSubscription model functionality"""
    
    def test_feed_subscription_creation(self, test_db):
        """Test creating a feed subscription"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create shared feed
        feed = SharedFeed(name="Test Feed", url="https://example.com/feed.xml")
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create subscription
        subscription = FeedSubscription(
            user_id=user.id,
            shared_feed_id=feed.id,
            crawl_frequency_minutes=60,
            is_active=True
        )
        
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)
        
        assert subscription.id is not None
        assert subscription.user_id == user.id
        assert subscription.shared_feed_id == feed.id
        assert subscription.crawl_frequency_minutes == 60
        assert subscription.is_active is True
        assert subscription.subscribed_at is not None
    
    def test_feed_subscription_relationships(self, test_db):
        """Test feed subscription relationships"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create shared feed
        feed = SharedFeed(name="Test Feed", url="https://example.com/feed.xml")
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create subscription
        subscription = FeedSubscription(
            user_id=user.id,
            shared_feed_id=feed.id,
            crawl_frequency_minutes=60
        )
        test_db.add(subscription)
        test_db.commit()
        test_db.refresh(subscription)
        
        # Test relationships
        assert subscription.user.username == "testuser"
        assert subscription.shared_feed.name == "Test Feed"
        assert len(user.feed_subscriptions) == 1
        assert len(feed.subscriptions) == 1

class TestSharedArticleModel:
    """Test SharedArticle model functionality"""
    
    def test_shared_article_creation(self, test_db):
        """Test creating a shared article"""
        # Create shared feed
        feed = SharedFeed(name="Test Feed", url="https://example.com/feed.xml")
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create article
        article = SharedArticle(
            title="Test Article",
            url="https://example.com/article/1",
            description="Test article description",
            content="Test article content",
            author="Test Author",
            published_at=datetime.now(timezone.utc),
            shared_feed_id=feed.id,
            content_hash="abcdef123456"
        )
        
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        assert article.id is not None
        assert article.title == "Test Article"
        assert article.url == "https://example.com/article/1"
        assert article.shared_feed_id == feed.id
        assert article.content_hash == "abcdef123456"
    
    def test_shared_article_feed_relationship(self, test_db):
        """Test article-feed relationship"""
        # Create shared feed
        feed = SharedFeed(name="Test Feed", url="https://example.com/feed.xml")
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create article
        article = SharedArticle(
            title="Test Article",
            url="https://example.com/article/1",
            published_at=datetime.now(timezone.utc),
            shared_feed_id=feed.id
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        # Test relationship
        assert article.shared_feed.name == "Test Feed"
        assert len(feed.articles) == 1
        assert feed.articles[0].title == "Test Article"
    
    def test_shared_article_clean_content_property(self, test_db):
        """Test article clean_content property"""
        article = SharedArticle(
            title="Test Title",
            url="https://example.com/article/1",
            description="Test Description",
            content="Test Content",
            published_at=datetime.now(timezone.utc),
            shared_feed_id=1
        )
        
        expected = "Test Title Test Description Test Content"
        assert article.clean_content == expected
        
        # Test with missing content
        article.content = None
        expected = "Test Title Test Description "
        assert article.clean_content == expected

class TestSharedUserFeedbackModel:
    """Test SharedUserFeedback model functionality"""
    
    def test_shared_user_feedback_creation(self, test_db):
        """Test creating shared user feedback"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create shared feed
        feed = SharedFeed(name="Test Feed", url="https://example.com/feed.xml")
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create shared article
        article = SharedArticle(
            title="Test Article",
            url="https://example.com/article/1",
            published_at=datetime.now(timezone.utc),
            shared_feed_id=feed.id
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        # Create feedback
        feedback = SharedUserFeedback(
            user_id=user.id,
            shared_article_id=article.id,
            feedback_type="like",
            feedback_text="Great article!"
        )
        
        test_db.add(feedback)
        test_db.commit()
        test_db.refresh(feedback)
        
        assert feedback.id is not None
        assert feedback.user_id == user.id
        assert feedback.shared_article_id == article.id
        assert feedback.feedback_type == "like"
        assert feedback.feedback_text == "Great article!"
        assert feedback.created_at is not None
    
    def test_shared_user_feedback_relationships(self, test_db):
        """Test shared user feedback relationships"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create shared feed and article
        feed = SharedFeed(name="Test Feed", url="https://example.com/feed.xml")
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        article = SharedArticle(
            title="Test Article",
            url="https://example.com/article/1",
            published_at=datetime.now(timezone.utc),
            shared_feed_id=feed.id
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        # Create feedback
        feedback = SharedUserFeedback(
            user_id=user.id,
            shared_article_id=article.id,
            feedback_type="like"
        )
        test_db.add(feedback)
        test_db.commit()
        test_db.refresh(feedback)
        
        # Test relationships
        assert feedback.user.username == "testuser"
        assert feedback.shared_article.title == "Test Article"
        assert len(user.shared_feedback) == 1
        assert len(article.user_feedback) == 1
