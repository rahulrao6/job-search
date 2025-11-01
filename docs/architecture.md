# Architecture Documentation

## System Overview

The Connection Finder is a modular system for discovering relevant people at target companies for job referrals. It aggregates data from multiple free and paid sources, deduplicates results, and categorizes people into target buckets.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Input                           │
│                  (Company + Job Title)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   ConnectionFinder                           │
│                   (Orchestrator)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Tier 1      │  │ Tier 2      │  │ Tier 3      │
│ Sources     │  │ Sources     │  │ Sources     │
│             │  │             │  │             │
│ • Apollo    │  │ • Google    │  │ • LinkedIn  │
│ • Company   │  │   SERP      │  │   Public    │
│ • GitHub    │  │ • Bing      │  │             │
│ • Crunchbase│  │             │  │             │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │ PeopleAggregator │
              │  (Deduplication) │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ PersonCategorizer│
              │  (Manager/Peer)  │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   Results +      │
              │  Report Output   │
              └──────────────────┘
```

## Component Breakdown

### 1. Data Models (`src/models/`)

#### Person
Core data structure representing a person:
- Identification: name, title, company
- Contact: linkedin_url, email, github_url
- Metadata: source, category, confidence_score
- Evidence: evidence_url (where found)

#### PersonCategory (Enum)
- MANAGER: Would be your manager or higher
- RECRUITER: HR/Talent/Recruiting roles
- SENIOR: One level above target role
- PEER: Same level as target role
- UNKNOWN: Cannot categorize

#### SourceConfig
Configuration for each data source:
- enabled, requires_auth
- rate_limit, max_requests_per_hour
- cost_per_request
- status (healthy/degraded/failing)

### 2. Data Sources

#### Tier 1: Reliable APIs & Public Sources
**Apollo.io API** (`src/apis/apollo_client.py`)
- Official API, 50 free credits/month
- Returns: name, title, LinkedIn URL, email
- Rate limit: 1 req/sec
- Cost: Free

**Company Career Pages** (`src/sources/company_pages.py`)
- Scrapes team/about/leadership pages
- Fully legal, rarely blocked
- Rate limit: 2 req/sec
- Cost: Free

**GitHub** (`src/sources/github_profiles.py`)
- Searches org members and user bios
- Good for technical roles
- Rate limit: 1 req/sec
- Cost: Free

**Crunchbase** (`src/sources/crunchbase_client.py`)
- Leadership and employee data
- Good for startups
- Rate limit: 0.5 req/sec
- Cost: Free (basic scraping)

#### Tier 2: Search Intermediaries
**Google SERP** (`src/sources/google_search.py`)
- Searches LinkedIn profiles via Google
- Uses SerpAPI (100 free/month) or direct scraping
- Rate limit: 0.5 req/sec
- Cost: Free (with API key)

#### Tier 3: Direct Scraping (Risky)
**LinkedIn Public** (`src/sources/linkedin_public.py`)
- ⚠️ Violates LinkedIn ToS
- Uses Playwright with stealth mode
- Rate limit: 0.2 req/sec (very conservative)
- Max: 50 req/hour
- Cost: Free but high risk

### 3. Utilities (`src/utils/`)

#### RateLimiter
- Per-source rate limiting
- Supports both per-second and per-hour limits
- Thread-safe
- Automatic wait if limit reached

#### Cache
- File-based caching using diskcache
- 24-hour TTL by default
- Key: source + query parameters
- Prevents redundant API calls

#### HttpClient
- Wrapper around requests
- User agent rotation
- Automatic retries (3x)
- Proxy support

#### CostTracker
- Tracks API costs per source
- Records request counts
- Reports total spend

#### StealthBrowser
- Playwright-based browser automation
- Anti-detection measures:
  - Random user agents
  - Fingerprint rotation
  - Random delays
  - Stealth scripts

#### ProxyManager
- Manages proxy rotation
- Supports single or multiple proxies
- Format: http://user:pass@host:port

### 4. Core Logic (`src/core/`)

#### PeopleAggregator
Deduplication and merging:
- Deduplicates by (name, company) tuple (case-insensitive)
- Merges data from multiple sources
- Increases confidence score for multi-source matches
- Tracks which sources found each person

#### PersonCategorizer
Categorizes people based on title:
- Uses keyword matching
- Context-aware (considers target title)
- Heuristics:
  - Manager: "manager", "director", "vp", "head of"
  - Recruiter: "recruiter", "talent", "hr"
  - Senior: "senior", "staff", "principal"
  - Peer: Similar title without seniority keywords

#### ConnectionFinder (Orchestrator)
Main coordinator:
1. Loads source configuration
2. Initializes all enabled sources
3. Runs searches in sequence
4. Aggregates and deduplicates
5. Categorizes people
6. Groups by category and sorts by confidence
7. Returns top 5 per category
8. Generates reports

### 5. Configuration

#### config/sources.yaml
- Enable/disable sources
- Set rate limits per source
- Define cost per request
- Category keyword definitions

#### config/.env
- API keys (APOLLO_API_KEY, SERP_API_KEY, etc.)
- Optional: LinkedIn cookies (risky)
- Optional: Proxy configuration
- Rate limit overrides
- Debug flags

## Data Flow

1. **Input**: User provides company name and job title
2. **Cache Check**: Check if results already cached
3. **Source Execution**: Run each enabled source:
   - Rate limit check
   - API key validation
   - Execute search
   - Parse results into Person objects
4. **Aggregation**: Deduplicate across sources
5. **Categorization**: Assign category to each person
6. **Ranking**: Sort by confidence score within categories
7. **Top Selection**: Take top 5 per category
8. **Output**: Generate JSON and markdown reports

## Anti-Detection Measures

### Rate Limiting
- Conservative defaults to avoid bans
- Per-source and global limits
- Automatic backoff

### Stealth Browsing
- Playwright with stealth plugin
- Random user agents
- Fingerprint rotation
- Random delays (2-5 seconds)

### Caching
- 24-hour cache prevents re-scraping
- Reduces load on target sites
- Faster repeat queries

### Proxy Support
- Optional proxy rotation
- Distributes requests across IPs
- Recommended for high volume

## Scalability Considerations

### Current Limitations
- Sequential source execution (can parallelize)
- In-memory aggregation (works for <1000 people)
- File-based cache (fine for PoC)
- No persistent database

### Future Improvements
- Parallel source execution (asyncio)
- Database for people storage (PostgreSQL)
- Redis for caching
- Message queue for background jobs
- API service layer (FastAPI)
- Web UI (React)

## Security & Privacy

### API Keys
- Never commit .env file
- Use environment variables
- Rotate keys periodically

### Scraped Data
- Don't republish as-is
- Transform and add value
- Respect robots.txt
- Cache to minimize requests

### LinkedIn ToS
- LinkedIn scraping violates ToS
- Account ban risk
- Legal gray area
- Use official API for production

## Error Handling

### Source Failures
- Graceful degradation
- Continue with other sources
- Log errors but don't fail entire search

### Rate Limits
- Automatic retry with backoff
- Warn user when limits hit
- Suggest wait time

### Network Issues
- Automatic retries (3x)
- Timeout after 30 seconds
- Fallback to cached data if available

## Testing Strategy

### Unit Tests
- Test each source independently
- Mock HTTP responses
- Test categorization logic
- Test deduplication

### Integration Tests
- Test full pipeline
- Use sample company/job
- Verify output format

### Manual Testing
- Test with real API keys
- Verify results quality
- Check rate limiting works
- Validate anti-detection

## Performance Metrics

### Target Performance
- Search completion: < 2 minutes
- Sources queried: 4-6
- Results found: 20-100 people
- Top 5 per category: 20 people total
- API cost: < $0.05 per search

### Monitoring
- Track success rate per source
- Monitor API costs
- Log response times
- Alert on failures

## Deployment

### Local Development
```bash
pip install -r requirements.txt
playwright install chromium
cp config/.env.example .env
# Add API keys to .env
python scripts/test_all_sources.py --company "Meta" --title "Engineer"
```

### Production Considerations
- Use official APIs only (no scraping)
- Deploy as web service (FastAPI)
- Add authentication
- Rate limit per user
- Monitor costs and usage
- Legal review

