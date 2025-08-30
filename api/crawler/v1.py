"""
Enhanced Feed Crawler Management API

Provides endpoints for managing the enhanced feed crawler system.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel

from jobs.enhanced_feed_crawler import enhanced_crawler, force_crawl_feed
from utils.dependencies import get_current_user
from models.user import User

router = APIRouter()

class CrawlerStatusResponse(BaseModel):
    is_running: bool
    scheduler_running: bool
    total_jobs: int
    active_crawl_sessions: int
    jobs: List[dict]

class ForceCrawlRequest(BaseModel):
    feed_url: str
    user_ids: Optional[List[int]] = None

@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status(current_user: User = Depends(get_current_user)):
    """Get the current status of the enhanced feed crawler"""
    try:
        status = enhanced_crawler.get_scheduler_status()
        return CrawlerStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get crawler status: {str(e)}")

@router.post("/force-crawl")
async def force_crawl_feed_endpoint(
    request: ForceCrawlRequest,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger a crawl for a specific feed"""
    try:
        await force_crawl_feed(request.feed_url, request.user_ids)
        return {
            "status": "success",
            "message": f"Crawl triggered for feed: {request.feed_url}",
            "feed_url": request.feed_url,
            "user_ids": request.user_ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to force crawl: {str(e)}")

@router.post("/refresh-schedule")
async def refresh_crawler_schedule(current_user: User = Depends(get_current_user)):
    """Refresh the crawler schedule (discover new feeds and update job schedules)"""
    try:
        await enhanced_crawler._discover_and_schedule_feeds()
        return {
            "status": "success",
            "message": "Crawler schedule refreshed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh schedule: {str(e)}")

@router.get("/health")
async def crawler_health_check(current_user: User = Depends(get_current_user)):
    """Get detailed health information about the crawler system"""
    try:
        await enhanced_crawler._health_check()
        return {
            "status": "success",
            "message": "Health check completed - see logs for details"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
