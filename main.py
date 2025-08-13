from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

from database.connection import init_database
from api.articles import v1 as articles_v1
from api.feeds import v1 as feeds_v1
from api.user_feedback import v1 as feedback_v1
from utils.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Simple RSS Feed Reader...")
    await init_database()
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(
    title="Simple RSS Feed Reader",
    description="A Simple RSS Feed Reader API",
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
app.include_router(articles_v1.router, prefix="/api/articles", tags=["articles"])
app.include_router(feeds_v1.router, prefix="/api/feeds", tags=["feeds"])
app.include_router(feedback_v1.router, prefix="/api/feedback", tags=["feedback"])

@app.get("/")
async def root():
    return {
        "message": "Simple RSS Feed Reader API", 
        "version": "1.0.0",
        "status": "running"
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