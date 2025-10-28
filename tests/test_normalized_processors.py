import pytest
from unittest.mock import patch, MagicMock
from processors.feed_processor import NormalizedFeedProcessor
from processors.article_processor import ArticleProcessor
from models.feed import SharedFeed
from models.article import SharedArticle

class TestNormalizedFeedProcessor:
    """Test NormalizedFeedProcessor functionality"""
    
    @pytest.fixture
    def processor(self):
        return NormalizedFeedProcessor()
    
    @pytest.fixture
    def sample_feed(self, test_db):
        """Create a sample shared feed for testing"""
        feed = SharedFeed(
            url="https://example.com/feed.xml",
            default_name="Test Feed",
            default_description="A test RSS feed"
        )
        test_db.add(feed)
        test_db.commit()
        test_db.refresh(feed)
        return feed
    
    @patch('feedparser.parse')
    async def test_process_shared_feed_success(self, mock_parse, processor, sample_feed, test_db):
        """Test successful feed processing"""
        # Mock feedparser response
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[
                MagicMock(
                    title="Test Article",
                    link="https://example.com/article1",
                    description="Test description",
                    published_parsed=None,
                    content=[],
                    author="Test Author"
                )
            ]
        )
        
        result = await processor.process_shared_feed(sample_feed, test_db)
        
        assert result["status"] == "success"
        assert result["new_articles"] >= 0
        assert result["updated_articles"] >= 0
        assert result["feed_name"] == "Test Feed"

class TestArticleProcessor:
    """Test ArticleProcessor functionality"""
    
    @pytest.fixture
    def processor(self):
        return ArticleProcessor()
    
    @pytest.fixture
    def sample_article(self, test_db):
        """Create a sample shared article for testing"""
        feed = SharedFeed(
            url="https://example.com/feed.xml",
            default_name="Test Feed"
        )
        test_db.add(feed)
        test_db.flush()
        
        article = SharedArticle(
            feed_id=feed.id,
            title="Test Article",
            url="https://example.com/article1",
            description="Test description",
            content="Test content"
        )
        test_db.add(article)
        test_db.commit()
        test_db.refresh(article)
        return article
    
    async def test_process_new_shared_article(self, processor, sample_article):
        """Test processing a new shared article"""
        # This should run without errors
        await processor.process_new_shared_article(sample_article)
        
        # Verify article has processed fields
        assert sample_article.content_hash is not None
        assert sample_article.word_count >= 0
