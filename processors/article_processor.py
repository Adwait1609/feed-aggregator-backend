from typing import Optional, Dict
from loguru import logger
from sqlalchemy.orm import Session
import hashlib

from models.article import SharedArticle

class ArticleProcessor:
    """Enhanced article processor with duplicate detection"""
    
    async def process_new_shared_article(self, article: SharedArticle) -> None:
        """Process a newly created article in the normalized schema"""
        try:
            logger.info(f"Processing article: {article.title[:50]}...")
            
            # Generate content hash for duplicate detection if not already set
            if not article.content_hash:
                content_hash = self._generate_content_hash(article)
                article.content_hash = content_hash
            
            # Set a default relevance score for now
            # Later we'll add ML processing here
            
            # Extract keywords and category (placeholder for ML)
            # This could be extended with NLP processing in the future
            
            # Mark as processed
            logger.debug(f"Article processed: {article.id}")
            
        except Exception as e:
            logger.error(f"Failed to process article {article.id}: {e}")
    
    def check_for_duplicates(self, session: Session, article_data: Dict, feed_id: int) -> Optional[SharedArticle]:
        """
        Check for duplicate articles in the normalized schema:
        1. Exact URL match within the same feed
        2. Content hash match (for feeds that change URLs)
        """
        url = article_data.get("url", "").strip()
        
        # 1. Exact URL match within the same feed (fastest check)
        if url:
            existing = session.query(SharedArticle).filter(
                SharedArticle.url == url,
                SharedArticle.feed_id == feed_id
            ).first()
            if existing:
                logger.debug(f"Found duplicate by URL: {url}")
                return existing
        
        # 2. Content hash check (for feeds that change URLs but keep content)
        content_hash = self._generate_content_hash_from_data(article_data)
        if content_hash:
            existing = session.query(SharedArticle).filter(
                SharedArticle.content_hash == content_hash,
                SharedArticle.feed_id == feed_id
            ).first()
            if existing:
                logger.debug(f"Found duplicate by content hash")
                return existing
        
        return None  # No duplicate found
    
    def _generate_content_hash(self, article: SharedArticle) -> str:
        """Generate hash from article content for duplicate detection"""
        content = f"{article.title}{article.description or ''}{article.content or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _generate_content_hash_from_data(self, article_data: Dict) -> str:
        """Generate hash from article data dict"""
        content = f"{article_data.get('title', '')}{article_data.get('description', '')}{article_data.get('content', '')}"
        return hashlib.md5(content.encode()).hexdigest()
