#!/usr/bin/env python3
"""
Background Jobs Explanation for RSS Feed Reader
Shows how and when background jobs run
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))


def explain_background_jobs():
    """Explain how background jobs work"""
    print("🔄 RSS FEED READER - BACKGROUND JOBS EXPLANATION")
    print("=" * 80)
    
    print("❓ WHEN DO BACKGROUND JOBS RUN?")
    print("=" * 50)
    print("✅ Jobs run ONLY when the FastAPI server is running")
    print("❌ Jobs DO NOT run when the server is stopped")
    print("❌ Jobs DO NOT run independently/standalone")
    print()
    
    print("🏃 HOW TO START THE SERVER (and jobs):")
    print("=" * 50)
    print("1. Run: uv run python main.py")
    print("2. You'll see these startup messages:")
    print("   - 'Background crawling jobs started successfully'")
    print("   - Server starts on http://127.0.0.1:8000")
    print("3. Jobs will now run automatically in the background")
    print()
    
    print("⏰ JOB SCHEDULE:")
    print("=" * 50)
    print("1. RSS Feed Crawler Check - Every 15 minutes")
    print("   - Checks which feeds need crawling")
    print("   - Crawls feeds based on their individual frequency:")
    print("     • TechCrunch: Every 15 minutes")
    print("     • BBC News: Every 60 minutes")
    print("   - Updates CSV file automatically")
    print()
    print("2. Health Check - Every 1 hour")
    print("   - Monitors system health")
    print("   - Reports feed statistics")
    print()
    
    print("📋 WHAT HAPPENS DURING CRAWLING:")
    print("=" * 50)
    print("1. Job checks: Is feed due for crawling?")
    print("2. If yes: Downloads RSS feed")
    print("3. Processes new articles")
    print("4. Saves to database")
    print("5. Updates last_crawled_at time")
    print("6. Updates CSV tracker file")
    print("7. Logs activity")
    print()
    
    print("🔍 HOW TO MONITOR JOBS:")
    print("=" * 50)
    print("1. Check server logs while running:")
    print("   uv run python main.py")
    print("   Look for: 'Checking for feeds due for crawling...'")
    print()
    print("2. Check CSV tracker:")
    print("   uv run python feed_tracker.py status")
    print()
    print("3. Check database:")
    print("   uv run python db_inspector.py")
    print()
    print("4. Force crawl (for testing):")
    print("   uv run python monitor.py crawl TechCrunch")
    print()
    
    print("⚠️  IMPORTANT NOTES:")
    print("=" * 50)
    print("• Jobs are part of the FastAPI application lifecycle")
    print("• When you stop the server (Ctrl+C), jobs stop too")
    print("• For production: Use a process manager like systemd, supervisor, or PM2")
    print("• For development: Keep the server running to see jobs work")
    print("• Jobs use APScheduler (Advanced Python Scheduler)")
    print()
    
    print("🚀 PRODUCTION DEPLOYMENT:")
    print("=" * 50)
    print("For continuous operation, you would:")
    print("1. Use a process manager (systemd, supervisor, PM2)")
    print("2. Or deploy to cloud with auto-restart (Docker, Kubernetes)")
    print("3. Or use a hosting service (Railway, Heroku, DigitalOcean)")
    print()
    
    print("💡 TIPS:")
    print("=" * 50)
    print("• Test jobs by starting server and watching logs")
    print("• CSV file shows when feeds were last crawled")
    print("• Force crawl to test without waiting")
    print("• Check database to see if articles are being added")


if __name__ == "__main__":
    explain_background_jobs()
