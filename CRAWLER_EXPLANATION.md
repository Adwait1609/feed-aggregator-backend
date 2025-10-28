# RSS Feed Crawler Architecture

## Simple, Efficient Design (No Priority System)

### Core Components

1. **FeedCrawler** - Main crawler class with APScheduler
2. **NormalizedFeedProcessor** - Processes individual RSS feeds
3. **ArticleProcessor** - Handles article content processing

### How It Works

#### 1. Scheduler Setup
```python
# Uses APScheduler with SQLAlchemy job store for persistence
scheduler = AsyncIOScheduler(
    jobstores={'default': SQLAlchemyJobStore(url=database_url)},
    job_defaults={
        'coalesce': True,      # Skip missed runs
        'max_instances': 1,    # One job instance only
        'misfire_grace_time': 300  # 5 minute grace period
    }
)
```

#### 2. Crawl Cycle (Every 10 Minutes)
1. Query database for feeds with active subscriptions
2. For each feed, find the MOST FREQUENT crawl requirement (lowest minutes)
3. Check if feed is due for crawling based on that frequency
4. Process feeds one by one (simple, reliable)
5. Update feed metadata and article counts

## How Crawler Respects Per-User Crawl Frequency

1. **User-Specified Frequencies**: Each user can set their own `crawl_frequency_minutes` when subscribing to a feed
2. **Most Frequent Wins**: For each feed, the crawler uses the MOST FREQUENT crawl requirement (lowest minutes)
   - If User A wants every 30 minutes and User B wants every 60 minutes
   - The crawler will crawl every 30 minutes to satisfy both users
3. **Due Check Logic**: Before crawling, checks `(now - last_crawled) >= most_frequent_requirement`

## Simplified Design Decisions

**No Priority System** - Removed for simplicity:
- Frequency already handles urgency (15 min = urgent, 60 min = normal)
- Simpler data model and API
- Less complexity for interviews and maintenance
- Clear business logic: "most frequent wins"

#### 3. Feed Processing
1. Parse RSS feed with feedparser
2. Check each entry against existing articles
3. Create new articles or update existing ones
4. Process article content (sentiment, keywords, etc.)
5. Commit changes to database

### Key Design Decisions

**Why Simple Over Complex?**
- **Reliability**: Sequential processing is more predictable
- **Debugging**: Easy to trace issues
- **Resource Usage**: Controlled memory and CPU usage
- **Thread Safety**: No complex concurrency issues

**Why 10-Minute Intervals?**
- Balance between responsiveness and resource usage
- Most RSS feeds don't update more frequently
- Allows time for thorough processing

**Why Single Job Instead of Per-Feed Jobs?**
- Easier to manage and monitor
- Better resource control
- Simpler error handling
- Avoids job explosion with many feeds

### Interview Talking Points

1. **Trade-offs**: Chose simplicity over maximum performance
2. **Scalability**: Can handle hundreds of feeds efficiently
3. **Error Handling**: Robust error tracking per feed
4. **Data Consistency**: Proper transaction management
5. **User Experience**: Immediate crawling when users add feeds

### Production Considerations

- **Monitoring**: Built-in logging and error tracking
- **Persistence**: Jobs survive application restarts
- **Error Recovery**: Graceful handling of feed failures
- **Resource Usage**: Controlled, predictable resource consumption

This design prioritizes **reliability and maintainability** over maximum throughput, making it perfect for a production RSS aggregator.
