import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from loguru import logger

from database.connection import get_db
from models.feed import RSSFeed
from processors.feed_processor import FeedProcessor
from processors.ml.ranking_engine import PersonalizationEngine

class FeedCrawlerJob:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.feed_processor = FeedProcessor()
        self.personalization_engine = PersonalizationEngine()
        
    async def start_background_jobs(self):
        """Start all background jobs"""
        # Feed crawling job - every 30 minutes
        self.scheduler.add_job(
            self.crawl_all_feeds,
            trigger=IntervalTrigger(minutes=30),
            id="feed_crawler",
            name="RSS Feed Crawler"
        )
        
        # ML model training job - every 6 hours
        self.scheduler.add_job(
            self.train_personalization_model,
            trigger=IntervalTrigger(hours=6),
            id="ml_trainer",
            name="ML Model Trainer"
        )
        
        # Article relevance update - every hour
        self.scheduler.add_job(
            self.update_article_relevance,
            trigger=IntervalTrigger(hours=1),
            id="relevance_updater", 
            name="Article Relevance Updater"
        )
        
        self.scheduler.start()
        logger.info("Background jobs started")
    
    async def crawl_all_feeds(self):
        """Crawl all active RSS feeds"""
        try:
            logger.info("Starting RSS feed crawling job")
            
            session = next(get_db())
            active_feeds = session.query(RSSFeed).filter(RSSFeed.is_active == True).all()
            
            results = []
            for feed in active_feeds:
                result = await self.feed_processor.process_feed(feed, session)
                results.append(result)
            
            session.close()
            
            # Log summary
            total_new = sum(r.get("new_articles", 0) for r in results)
            total_updated = sum(r.get("updated_articles", 0) for r in results)
            
            logger.info(f"Feed crawling completed: {total_new} new, {total_updated} updated articles")
            
        except Exception as e:
            logger.error(f"Feed crawling job failed: {str(e)}")
    
    async def train_personalization_model(self):
        """Train personalization model with latest feedback"""
        try:
            logger.info("Starting ML model training job")
            
            session = next(get_db())
            training_data = await self.personalization_engine.get_training_data(session)
            session.close()
            
            if len(training_data) >= 10:
                result = await self.personalization_engine.train_model(training_data)
                logger.info(f"Model training result: {result}")
            else:
                logger.info(f"Insufficient training data: {len(training_data)} samples")
                
        except Exception as e:
            logger.error(f"ML training job failed: {str(e)}")
    
    async def update_article_relevance(self):
        """Update relevance scores for articles"""
        try:
            logger.info("Starting article relevance update job")
            
            # This would call the API endpoint or implement similar logic
            # For now, we'll implement it directly here
            
            session = next(get_db())
            
            # Load model
            self.personalization_engine.load_model()
            
            # Get articles needing score updates
            from models.article import Article
            articles = session.query(Article).filter(
                Article.relevance_score == 0.0
            ).limit(500).all()
            
            if articles:
                scores = self.personalization_engine.predict_relevance(articles)
                
                for article, score in zip(articles, scores):
                    article.relevance_score = score
                
                session.commit()
                logger.info(f"Updated relevance scores for {len(articles)} articles")
            
            session.close()
            
        except Exception as e:
            logger.error(f"Relevance update job failed: {str(e)}")

# Global job instance
job_instance = FeedCrawlerJob()

async def start_background_jobs():
    """Function to start background jobs - called from main.py"""
    await job_instance.start_background_jobs()
