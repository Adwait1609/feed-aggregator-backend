import pytest
from models.user import User
from models.feed import RSSFeed
from models.article import Article
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

class TestRSSFeedModel:
    """Test RSSFeed model functionality"""
    
    def test_feed_creation(self, test_db):
        """Test creating an RSS feed"""
        # Create user first
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create feed
        feed = RSSFeed(
            name="Test Feed",
            url="https://example.com/feed.xml",
            description="Test feed description",
            user_id=user.id,
            crawl_frequency_minutes=60
        )
        
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        assert feed.id is not None
        assert feed.name == "Test Feed"
        assert feed.url == "https://example.com/feed.xml"
        assert feed.user_id == user.id
        assert feed.is_active is True
        assert feed.crawl_frequency_minutes == 60
        assert feed.crawl_error_count == 0
    
    def test_feed_user_relationship(self, test_db):
        """Test feed-user relationship"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create feed
        feed = RSSFeed(
            name="Test Feed",
            url="https://example.com/feed.xml",
            user_id=user.id
        )
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Test relationship
        assert feed.user.username == "testuser"
        assert len(user.feeds) == 1
        assert user.feeds[0].name == "Test Feed"
    
    def test_feed_str_representation(self, test_db):
        """Test feed string representation"""
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=1)
        assert str(feed) == "RSSFeed(Test Feed - User: 1)"

class TestArticleModel:
    """Test Article model functionality"""
    
    def test_article_creation(self, test_db):
        """Test creating an article"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create feed
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=user.id)
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create article
        article = Article(
            title="Test Article",
            url="https://example.com/article/1",
            description="Test article description",
            content="Test article content",
            author="Test Author",
            published_at=datetime.now(timezone.utc),
            feed_id=feed.id,
            content_hash="abcdef123456"
        )
        
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        assert article.id is not None
        assert article.title == "Test Article"
        assert article.url == "https://example.com/article/1"
        assert article.feed_id == feed.id
        assert article.content_hash == "abcdef123456"
    
    def test_article_feed_relationship(self, test_db):
        """Test article-feed relationship"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create feed
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=user.id)
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create article
        article = Article(
            title="Test Article",
            url="https://example.com/article/1",
            published_at=datetime.now(timezone.utc),
            feed_id=feed.id
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        # Test relationship
        assert article.feed.name == "Test Feed"
        assert len(feed.articles) == 1
        assert feed.articles[0].title == "Test Article"
    
    def test_article_user_id_property(self, test_db):
        """Test article user_id property through feed"""
        # Create user
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create feed
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=user.id)
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create article
        article = Article(
            title="Test Article",
            url="https://example.com/article/1",
            published_at=datetime.now(timezone.utc),
            feed_id=feed.id
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        # Test user_id property
        assert article.user_id == user.id
    
    def test_article_clean_content_property(self, test_db):
        """Test article clean_content property"""
        article = Article(
            title="Test Title",
            url="https://example.com/article/1",
            description="Test Description",
            content="Test Content",
            published_at=datetime.now(timezone.utc),
            feed_id=1
        )
        
        expected = "Test Title Test Description Test Content"
        assert article.clean_content == expected
        
        # Test with missing content
        article.content = None
        expected = "Test Title Test Description "
        assert article.clean_content == expected
