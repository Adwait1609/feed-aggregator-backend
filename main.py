from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

from database.connection import init_database
from api.auth import v1 as auth_v1
from api.articles import v1 as articles_v1
from api.feeds import v1 as feeds_v1
from api.user_feedback import v1 as feedback_v1
from jobs.feed_crawler import start_background_jobs, stop_background_jobs
from utils.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Multi-User RSS Feed Reader...")
    await init_database()
    await start_background_jobs()  # Start automatic feed crawling
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await stop_background_jobs()

app = FastAPI(
    title="Multi-User RSS Feed Reader",
    description="A Multi-User RSS Feed Reader API with Authentication",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_v1.router, prefix="/api/auth", tags=["authentication"])
app.include_router(articles_v1.router, prefix="/api/articles", tags=["articles"])
app.include_router(feeds_v1.router, prefix="/api/feeds", tags=["feeds"])
app.include_router(feedback_v1.router, prefix="/api/feedback", tags=["feedback"])

@app.get("/")
async def root():
    return {
        "message": "Multi-User RSS Feed Reader API", 
        "version": "1.0.0",
        "status": "running",
        "features": ["authentication", "user_feeds", "scheduled_crawling"]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "RSS Feed Reader"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )