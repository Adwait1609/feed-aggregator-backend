# Normalized RSS Feed Aggregator

A production-grade RSS feed aggregator built with FastAPI, PostgreSQL, and SQLAlchemy. This system uses a normalized database schema to efficiently handle many users subscribing to the same feeds without duplication.

## Database Normalization Explained

This project uses a normalized database schema to eliminate redundancy and improve scalability. Here's how normalization helps:

### Before Normalization (Common Problems)

In a non-normalized RSS feed reader:
- Each user has their own copy of each feed
- Articles are duplicated for each user
- If 100 users subscribe to the same feed with 1000 articles, the database stores 100,000 articles
- Crawling the same feed URL happens multiple times (once per user)
- Any updates to article content must be done separately for each user's copy

### After Normalization (Our Solution)

In our normalized schema:
- Feeds are stored once, regardless of how many users subscribe
- Articles are stored once per feed
- If 100 users subscribe to the same feed with 1000 articles, the database stores only 1000 articles
- Each feed URL is crawled only once
- Users maintain their own subscription settings while sharing the underlying feed data

## Entity-Relationship Diagram

```
┌────────────┐       ┌──────────────────┐       ┌─────────────┐
│            │       │                  │       │             │
│    User    │◄──────┤ FeedSubscription │───────►  SharedFeed │
│            │       │                  │       │             │
└────────────┘       └──────────────────┘       └──────┬──────┘
      ▲                                                 │
      │                                                 │
      │                                                 │
      │                                                 ▼
      │                                          ┌─────────────┐
      │                                          │             │
      └─────────────┐                           │SharedArticle │
                    │                           │             │
                    │                           └──────┬──────┘
                    │                                  │
                    ▼                                  │
           ┌──────────────────┐                        │
           │                  │                        │
           │SharedUserFeedback│◄───────────────────────┘
           │                  │
           └──────────────────┘
```

### Entity Descriptions:

1. **User**
   - Represents a user of the system
   - Each user can subscribe to multiple feeds
   - Fields: id, username, email, hashed_password, is_active, last_login, etc.

2. **SharedFeed**
   - Represents a unique RSS feed URL in the system
   - Stored once regardless of how many users subscribe
   - Fields: id, url, default_name, default_description, last_crawled_at, etc.

3. **FeedSubscription**
   - Represents a user's subscription to a feed
   - Many-to-many relationship between users and feeds
   - Stores user-specific preferences like display name, crawl frequency, priority
   - Fields: id, user_id, feed_id, display_name, description, crawl_frequency_minutes, priority, is_active, etc.

4. **SharedArticle**
   - Represents an article from a feed
   - Linked to the feed, not to individual users
   - Fields: id, feed_id, title, url, description, content, published_at, etc.

5. **SharedUserFeedback**
   - Represents a user's interaction with an article (likes, bookmarks, etc.)
   - Links users to articles they've interacted with
   - Fields: id, user_id, article_id, is_liked, is_bookmarked, is_read, feedback_type, etc.

## Normalization Benefits

1. **Reduced Storage Requirements**
   - Articles are stored once, not once per user
   - Significantly reduces database size for popular feeds

2. **Efficient Crawling**
   - Each feed URL is crawled only once, regardless of subscription count
   - Crawler prioritizes based on the highest priority subscription

3. **Consistent Content**
   - All users see the same article content for the same feed
   - Updates to articles benefit all subscribed users

4. **Personalized Experience**
   - Despite shared data, users maintain personal settings:
     - Custom feed names
     - Individual crawl frequencies
     - Personal priority levels
     - Individual read/unread status

5. **Scalability**
   - System can handle millions of users with minimal additional storage
   - Crawling workload doesn't increase linearly with user count

## API Endpoints

- `/api/v1/auth/*` - User authentication (login, register, etc.)
- `/api/v1/feeds/*` - Feed subscription management
- `/api/v1/articles/*` - Article retrieval and filtering
- `/api/v1/feedback/*` - User feedback on articles
- `/api/v1/crawler/*` - Crawler management and control

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up database: `python scripts/reset_database.py`
4. Start the server: `python main.py`

## Architecture

- Backend: FastAPI
- Database: PostgreSQL with SQLAlchemy ORM
- Scheduling: APScheduler with SQLAlchemy job store
- Frontend: Streamlit
