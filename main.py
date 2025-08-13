from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

from database.connection import init_database
from api.articles import v1 as articles_v1
from api.feeds import v1 as feeds_v1
from api.user_feedback import v1 as feedback_v1
from api.clustering import v1 as clustering_v1
from jobs.feed_crawler import start_background_jobs
from utils.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting News Aggregator Backend...")
    await init_database()
    await start_background_jobs()
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(
    title="News Aggregator API",
    description="AI-Powered Personalized News Feed Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(articles_v1.router, prefix="/api/articles", tags=["articles"])
app.include_router(feeds_v1.router, prefix="/api/feeds", tags=["feeds"])
app.include_router(feedback_v1.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(clustering_v1.router, prefix="/api/clustering", tags=["clustering"])

@app.get("/")
async def root():
    return {"message": "News Aggregator API", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
