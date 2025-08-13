import feedparser
import asyncio
from datetime import datetime, timezone
from typing import List, Dict
from urllib.parse import urljoin
from loguru import logger
from sqlalchemy.orm import Session

from models.article import Article
from models.feed import RSSFeed
from database.connection import get_db
from processors.article_processor import ArticleProcessor

class FeedProcessor:
    def __init__(self):
        self.article_processor = ArticleProcessor()
    
    async def process_feed(self, feed: RSSFeed, session: Session) -> Dict:
        """Process single RSS feed"""
        try:
            logger.info(f"Processing feed: {feed.name}")
            
            # Parse RSS feed
            parsed_feed = feedparser.parse(feed.url)
            
            if parsed_feed.bozo:
                logger.warning(f"Feed parsing issues for {feed.name}: {parsed_feed.bozo_exception}")
            
            new_articles = 0
            updated_articles = 0
            
            for entry in parsed_feed.entries:
                result = await self._process_entry(entry, feed, session)
                if result == "new":
                    new_articles += 1
                elif result == "updated":
                    updated_articles += 1
            
            # Update feed metadata
            feed.last_crawled_at = datetime.now(timezone.utc)
            session.commit()
            
            logger.info(f"Feed {feed.name}: {new_articles} new, {updated_articles} updated articles")
            
            return {
                "feed_name": feed.name,
                "new_articles": new_articles,
                "updated_articles": updated_articles,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing feed {feed.name}: {str(e)}")
            return {"feed_name": feed.name, "status": "error", "error": str(e)}
    
    async def _process_entry(self, entry, feed: RSSFeed, session: Session) -> str:
        """Process individual article entry"""
        try:
            # Extract article data
            article_data = self._extract_article_data(entry, feed)
            
            # Check if article already exists
            existing_article = session.query(Article).filter(
                Article.url == article_data["url"]
            ).first()
            
            if existing_article:
                # Update existing article if needed
                if self._should_update_article(existing_article, article_data):
                    for key, value in article_data.items():
                        setattr(existing_article, key, value)
                    return "updated"
                return "exists"
            else:
                # Create new article
                article = Article(**article_data)
                session.add(article)
                session.flush()  # Get the ID
                
                # Process article content
                await self.article_processor.process_new_article(article)
                
                return "new"
                
        except Exception as e:
            logger.error(f"Error processing entry: {str(e)}")
            return "error"
    
    def _extract_article_data(self, entry, feed: RSSFeed) -> Dict:
        """Extract article data from RSS entry"""
        # Handle different date formats
        published_at = self._parse_date(entry.get('published_parsed') or entry.get('updated_parsed'))
        
        return {
            "title": entry.get('title', '').strip(),
            "url": entry.get('link', '').strip(),
            "description": entry.get('summary', '').strip(),
            "author": entry.get('author', '').strip(),
            "published_at": published_at,
            "feed_id": feed.id,
            "content": self._extract_content(entry),
        }
    
    def _parse_date(self, date_tuple) -> datetime:
        """Parse RSS date to datetime"""
        if date_tuple:
            return datetime(*date_tuple[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc)
    
    def _extract_content(self, entry) -> str:
        """Extract full content from entry"""
        # Try different content fields
        content = ""
        
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value
        elif hasattr(entry, 'summary_detail') and entry.summary_detail:
            content = entry.summary_detail.value
        elif hasattr(entry, 'summary'):
            content = entry.summary
        
        return content.strip()
    
    def _should_update_article(self, existing: Article, new_data: Dict) -> bool:
        """Check if article should be updated"""
        # Update if title, description, or content changed significantly
        return (
            existing.title != new_data["title"] or
            existing.description != new_data["description"] or
            len(new_data.get("content", "")) > len(existing.content or "")
        )
