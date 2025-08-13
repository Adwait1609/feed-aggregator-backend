from typing import Optional
from loguru import logger
from models.article import Article

class ArticleProcessor:
    """Simple article processor without ML features"""
    
    async def process_new_article(self, article: Article) -> None:
        """Process a newly created article"""
        try:
            # For now, just log that we processed it
            # Later we'll add ML processing here
            logger.info(f"Processing article: {article.title[:50]}...")
            
            # Set a default relevance score for now
            article.relevance_score = 0.5
            
            # Mark as processed
            logger.debug(f"Article processed: {article.id}")
            
        except Exception as e:
            logger.error(f"Failed to process article {article.id}: {e}")
