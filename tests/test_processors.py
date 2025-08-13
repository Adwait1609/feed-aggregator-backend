import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from processors.article_processor import ArticleProcessor
from processors.feed_processor import FeedProcessor
from models.article import Article
from models.feed import RSSFeed
from models.user import User
from datetime import datetime, timezone
import hashlib

class TestArticleProcessor:
    """Test ArticleProcessor functionality"""
    
    @pytest.fixture
    def processor(self):
        return ArticleProcessor()
    
    @pytest.fixture
    def sample_article(self, test_db):
        """Create a sample article for testing"""
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=user.id)
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        article = Article(
            title="Test Article",
            url="https://example.com/article/1",
            description="Test description",
            content="Test content",
            published_at=datetime.now(timezone.utc),
            feed_id=feed.id
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        
        return article
    
    @pytest.mark.asyncio
    async def test_process_new_article(self, processor, sample_article):
        """Test processing a new article"""
        # Article should not have content_hash initially
        assert sample_article.content_hash is None
        
        # Process the article
        await processor.process_new_article(sample_article)
        
        # Should now have content_hash
        assert sample_article.content_hash is not None
        assert len(sample_article.content_hash) == 32  # MD5 hash length
    
    def test_generate_content_hash(self, processor):
        """Test content hash generation"""
        article = Article(
            title="Test Title",
            description="Test Description",
            content="Test Content",
            url="https://example.com/test",
            published_at=datetime.now(timezone.utc),
            feed_id=1
        )
        
        hash_value = processor._generate_content_hash(article)
        
        # Should be MD5 hash
        assert len(hash_value) == 32
        assert hash_value == hashlib.md5("Test TitleTest DescriptionTest Content".encode()).hexdigest()
    
    def test_generate_content_hash_from_data(self, processor):
        """Test content hash generation from data dict"""
        article_data = {
            "title": "Test Title",
            "description": "Test Description",
            "content": "Test Content"
        }
        
        hash_value = processor._generate_content_hash_from_data(article_data)
        
        # Should match expected hash
        expected = hashlib.md5("Test TitleTest DescriptionTest Content".encode()).hexdigest()
        assert hash_value == expected
    
    def test_check_for_duplicates_by_url(self, processor, test_db):
        """Test duplicate detection by URL"""
        # Create user and feed
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=user.id)
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create existing article
        existing_article = Article(
            title="Existing Article",
            url="https://example.com/article/1",
            published_at=datetime.now(timezone.utc),
            feed_id=feed.id
        )
        test_db.add(existing_article)
        test_db.commit()
        
        # Test duplicate detection
        article_data = {
            "title": "New Article",
            "url": "https://example.com/article/1",  # Same URL
            "description": "Different description"
        }
        
        duplicate = processor.check_for_duplicates(test_db, article_data, feed.id)
        assert duplicate is not None
        assert duplicate.id == existing_article.id
    
    def test_check_for_duplicates_by_content_hash(self, processor, test_db):
        """Test duplicate detection by content hash"""
        # Create user and feed
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=user.id)
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Create existing article with content hash
        content_hash = hashlib.md5("TitleDescriptionContent".encode()).hexdigest()
        existing_article = Article(
            title="Existing Article",
            url="https://example.com/article/old",
            content_hash=content_hash,
            published_at=datetime.now(timezone.utc),
            feed_id=feed.id
        )
        test_db.add(existing_article)
        test_db.commit()
        
        # Test duplicate detection with different URL but same content
        article_data = {
            "title": "Title",
            "description": "Description",
            "content": "Content",
            "url": "https://example.com/article/new"  # Different URL
        }
        
        duplicate = processor.check_for_duplicates(test_db, article_data, feed.id)
        assert duplicate is not None
        assert duplicate.id == existing_article.id
    
    def test_no_duplicates_found(self, processor, test_db):
        """Test when no duplicates are found"""
        # Create user and feed
        user = User(username="testuser", email="test@example.com", hashed_password="hash")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        feed = RSSFeed(name="Test Feed", url="https://example.com/feed.xml", user_id=user.id)
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        
        # Test with completely new article data
        article_data = {
            "title": "Unique Article",
            "url": "https://example.com/article/unique",
            "description": "Unique description",
            "content": "Unique content"
        }
        
        duplicate = processor.check_for_duplicates(test_db, article_data, feed.id)
        assert duplicate is None

class TestFeedProcessor:
    """Test FeedProcessor functionality"""
    
    @pytest.fixture
    def processor(self):
        return FeedProcessor()
    
    def test_parse_date_with_valid_tuple(self, processor):
        """Test date parsing with valid time tuple"""
        # Mock time tuple (year, month, day, hour, min, sec, weekday, yearday, dst)
        time_tuple = (2023, 12, 25, 10, 30, 45, 0, 359, 0)
        
        result = processor._parse_date(time_tuple)
        
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo is not None
    
    def test_parse_date_with_none(self, processor):
        """Test date parsing with None input"""
        result = processor._parse_date(None)
        
        # Should return current time
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
    
    def test_extract_content_from_entry(self, processor):
        """Test content extraction from RSS entry"""
        # Mock RSS entry with content
        entry = MagicMock()
        entry.content = [MagicMock(value="<p>Full content here</p>")]
        entry.summary = "Summary content"
        
        content = processor._extract_content(entry)
        assert content == "<p>Full content here</p>"
        
        # Test fallback to summary
        entry.content = None
        entry.summary_detail = MagicMock(value="Summary detail content")
        
        content = processor._extract_content(entry)
        assert content == "Summary detail content"
        
        # Test fallback to summary
        entry.summary_detail = None
        
        content = processor._extract_content(entry)
        assert content == "Summary content"
    
    def test_should_update_article(self, processor):
        """Test article update logic"""
        existing_article = Article(
            title="Old Title",
            description="Old Description",
            content="Old Content",
            url="https://example.com/article",
            published_at=datetime.now(timezone.utc),
            feed_id=1
        )
        
        # Test update with different title
        new_data = {
            "title": "New Title",
            "description": "Old Description",
            "content": "Old Content"
        }
        assert processor._should_update_article(existing_article, new_data) is True
        
        # Test update with different description
        new_data = {
            "title": "Old Title",
            "description": "New Description",
            "content": "Old Content"
        }
        assert processor._should_update_article(existing_article, new_data) is True
        
        # Test update with longer content
        new_data = {
            "title": "Old Title",
            "description": "Old Description",
            "content": "Much longer content than the original"
        }
        assert processor._should_update_article(existing_article, new_data) is True
        
        # Test no update needed
        new_data = {
            "title": "Old Title",
            "description": "Old Description",
            "content": "Old Content"
        }
        assert processor._should_update_article(existing_article, new_data) is False
    
    def test_extract_article_data(self, processor):
        """Test extracting article data from RSS entry"""
        # Create mock RSS feed
        feed = RSSFeed(id=1, name="Test Feed", url="https://example.com/feed.xml", user_id=1)
        
        # Create mock RSS entry
        entry = MagicMock()
        entry.get.side_effect = lambda key, default='': {
            'title': 'Test Article Title',
            'link': 'https://example.com/article/1',
            'summary': 'Test article summary',
            'author': 'Test Author'
        }.get(key, default)
        
        # Mock date parsing
        entry.published_parsed = (2023, 12, 25, 10, 30, 45, 0, 359, 0)
        entry.updated_parsed = None
        
        # Mock content extraction
        entry.content = [MagicMock(value="Full article content")]
        
        article_data = processor._extract_article_data(entry, feed)
        
        assert article_data["title"] == "Test Article Title"
        assert article_data["url"] == "https://example.com/article/1"
        assert article_data["description"] == "Test article summary"
        assert article_data["author"] == "Test Author"
        assert article_data["feed_id"] == 1
        assert article_data["content"] == "Full article content"
        assert isinstance(article_data["published_at"], datetime)
    
    @pytest.mark.asyncio
    async def test_process_feed_success(self, processor):
        """Test successful feed processing"""
        # Create mock feed
        feed = RSSFeed(
            id=1,
            name="Test Feed",
            url="https://example.com/feed.xml",
            user_id=1
        )
        
        # Mock session
        mock_session = MagicMock()
        
        # Mock feedparser
        with patch('processors.feed_processor.feedparser') as mock_feedparser:
            mock_parsed = MagicMock()
            mock_parsed.bozo = False
            mock_parsed.entries = [
                MagicMock(get=lambda k, d='': {'title': 'Article 1', 'link': 'https://example.com/1'}.get(k, d))
            ]
            mock_feedparser.parse.return_value = mock_parsed
            
            # Mock _process_entry
            with patch.object(processor, '_process_entry', new_callable=AsyncMock) as mock_process:
                mock_process.return_value = "new"
                
                result = await processor.process_feed(feed, mock_session)
                
                assert result["status"] == "success"
                assert result["feed_name"] == "Test Feed"
                assert result["new_articles"] == 1
                assert result["updated_articles"] == 0
                
                # Verify feed was updated
                assert feed.last_crawled_at is not None
                mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_feed_with_errors(self, processor):
        """Test feed processing with errors"""
        feed = RSSFeed(name="Test Feed", url="https://invalid-url", user_id=1)
        mock_session = MagicMock()
        
        # Mock feedparser to raise exception
        with patch('processors.feed_processor.feedparser') as mock_feedparser:
            mock_feedparser.parse.side_effect = Exception("Network error")
            
            result = await processor.process_feed(feed, mock_session)
            
            assert result["status"] == "error"
            assert "Network error" in result["error"]
