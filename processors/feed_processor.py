import feedparser
from datetime import datetime, timezone
import hashlib
from typing import Dict
from loguru import logger
from sqlalchemy.orm import Session

from models.article import SharedArticle
from models.feed import SharedFeed
from processors.article_processor import ArticleProcessor

class NormalizedFeedProcessor:
    """Simple, efficient RSS feed processor"""
    
    def __init__(self):
        self.article_processor = ArticleProcessor()
        self.user_agent = "RSS-Feed-Aggregator/1.0"
    
    async def process_shared_feed(self, feed: SharedFeed, session: Session) -> Dict:
        """Process a single RSS feed"""
        try:
            logger.info(f"Processing feed: {feed.default_name}")
            
            # Parse RSS feed
            parsed_feed = feedparser.parse(feed.url, agent=self.user_agent)
            
            if parsed_feed.bozo:
                logger.warning(f"Feed has parsing issues: {parsed_feed.bozo_exception}")
                # Continue processing anyway - many feeds have minor issues
            
            if not parsed_feed.entries:
                logger.warning(f"No entries found in feed: {feed.default_name}")
                return {"status": "success", "new_articles": 0, "updated_articles": 0}
            
            new_articles = 0
            updated_articles = 0
            
            # Process each entry
            for entry in parsed_feed.entries:
                result = await self._process_entry(entry, feed, session)
                if result == "new":
                    new_articles += 1
                elif result == "updated":
                    updated_articles += 1
            
            # Commit all changes
            session.commit()
            
            logger.info(f"Feed {feed.default_name}: {new_articles} new, {updated_articles} updated")
            
            return {
                "status": "success",
                "new_articles": new_articles,
                "updated_articles": updated_articles,
                "feed_name": feed.default_name
            }
            
        except Exception as e:
            logger.error(f"Error processing feed {feed.default_name}: {e}")
            session.rollback()
            return {
                "status": "error",
                "error": str(e),
                "feed_name": feed.default_name
            }
            
    
    async def _process_entry(self, entry, feed: SharedFeed, session: Session) -> str:
        """Process individual RSS entry"""
        try:
            # Extract article data
            article_data = self._extract_article_data(entry, feed)
            
            # Check if article already exists
            existing = session.query(SharedArticle).filter(
                SharedArticle.feed_id == feed.id,
                SharedArticle.url == article_data["url"]
            ).first()
            
            if existing:
                # Update if content changed
                if existing.content_hash != article_data["content_hash"]:
                    # Update existing article
                    for key, value in article_data.items():
                        setattr(existing, key, value)
                    
                    # Process updated content
                    await self.article_processor.process_new_shared_article(existing)
                    return "updated"
                return "exists"
            else:
                # Create new article
                article = SharedArticle(**article_data)
                session.add(article)
                session.flush()  # Get ID without committing
                
                # Process new article content
                await self.article_processor.process_new_shared_article(article)
                return "new"
                
        except Exception as e:
            logger.error(f"Error processing entry: {e}")
            return "error"
    
    def _extract_article_data(self, entry, feed: SharedFeed) -> Dict:
        """Extract article data from RSS entry"""
        # Get published date
        published_at = self._parse_date(entry.get('published_parsed') or entry.get('updated_parsed'))
        
        # Extract content
        content = self._extract_content(entry)
        
        # Generate content hash for duplicate detection
        content_hash = self._generate_content_hash(entry.get('title', ''), content)
        
        return {
            "feed_id": feed.id,
            "title": entry.get('title', '').strip()[:500],  # Limit title length
            "url": entry.get('link', '').strip(),
            "description": entry.get('summary', '').strip(),
            "content": content,
            "author": entry.get('author', '').strip()[:200],  # Limit author length
            "published_at": published_at,
            "content_hash": content_hash,
        }
    
    def _parse_date(self, date_tuple) -> datetime:
        """Parse RSS date to datetime"""
        if date_tuple:
            try:
                return datetime(*date_tuple[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass
        return datetime.now(timezone.utc)
    
    def _extract_content(self, entry) -> str:
        """Extract content from RSS entry"""
        content = ""
        
        # Try different content fields
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value
        elif hasattr(entry, 'summary_detail') and entry.summary_detail:
            content = entry.summary_detail.value
        elif hasattr(entry, 'summary'):
            content = entry.summary
        
        return content.strip()
    
    def _generate_content_hash(self, title: str, content: str) -> str:
        """Generate hash for duplicate detection"""
        hash_content = f"{title}{content}"
        return hashlib.md5(hash_content.encode('utf-8')).hexdigest()
