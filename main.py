from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger
import time
from starlette.middleware.base import BaseHTTPMiddleware

from database.connection import init_database, create_scheduler_table
from api.auth import v1 as auth_v1
from api.articles import v1 as articles_v1
from api.feeds import v1 as feeds_v1
from api.user_feedback import v1 as feedback_v1
from api.crawler import v1 as crawler_v1
from jobs.feed_crawler import start_background_jobs, stop_background_jobs
from utils.config import settings

# Middleware for performance monitoring
class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add timing header to responses
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 0.5:  # Log requests that take more than 500ms
            logger.warning(f"Slow request: {request.method} {request.url.path} - {process_time:.4f}s")
        
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Normalized Multi-User RSS Feed Reader...")
    await init_database()
    create_scheduler_table()  # Create APScheduler table
    await start_background_jobs()  # Start normalized feed crawling
    logger.info("Application started successfully with normalized schema")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await stop_background_jobs()

app = FastAPI(
    title="Multi-User RSS Feed Reader",
    description="A production-grade Multi-User RSS Feed Reader API with Normalized Schema",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",  # More secure path for docs
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React frontend
        "http://127.0.0.1:3000", 
        "http://localhost:8501",    # Streamlit frontend
        "http://127.0.0.1:8501"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add performance monitoring middleware
app.add_middleware(PerformanceMiddleware)

# Register API routers
app.include_router(auth_v1.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(articles_v1.router, prefix="/api/v1/articles", tags=["articles"])
app.include_router(feeds_v1.router, prefix="/api/v1/feeds", tags=["feeds"])
app.include_router(feedback_v1.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(crawler_v1.router, prefix="/api/v1/crawler", tags=["crawler"])

@app.get("/")
async def root():
    return {
        "message": "Multi-User RSS Feed Reader API", 
        "version": "2.0.0",
        "status": "running",
        "features": ["authentication", "normalized_schema", "shared_feeds", "per_user_subscriptions"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy", 
        "service": "Normalized RSS Feed Reader",
        "uptime": time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0
    }

if __name__ == "__main__":
    app.state.start_time = time.time()  # Track app start time
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=getattr(settings, "workers", 1),  # Use multiple workers for production
        proxy_headers=True,  # Trust proxy headers for proper IP handling
        forwarded_allow_ips="*"  # Allow all forwarded IPs
    )
