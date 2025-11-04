# Production Deployment Guide - Fly.io

## Quick Deploy to Fly.io

### 1. Initial Setup

**Prerequisites:**
- Install [flyctl](https://fly.io/docs/getting-started/installing-flyctl/)
- Have a Fly.io account (sign up at [fly.io](https://fly.io))

**Initial Deployment:**
```bash
# Launch app (first time)
flyctl launch

# Or if app already exists, just deploy
flyctl deploy
```

### 2. Required Environment Variables

Set secrets in Fly.io:
```bash
# Required
flyctl secrets set GOOGLE_API_KEY=your_key
flyctl secrets set GOOGLE_CSE_ID=your_cse_id
flyctl secrets set OPENAI_API_KEY=your_key
flyctl secrets set SUPABASE_URL=your_url
flyctl secrets set SUPABASE_KEY=your_key

# Optional but recommended
flyctl secrets set GITHUB_TOKEN=your_token
flyctl secrets set SERP_API_KEY=your_key
flyctl secrets set APOLLO_API_KEY=your_key
```

**View secrets:**
```bash
flyctl secrets list
```

### 3. Gunicorn Configuration

The app uses optimized Gunicorn settings for I/O-bound workloads:
- **Workers**: 4 (auto-scales based on CPU)
- **Threads**: 8 per worker (optimal for concurrent API calls)
- **Worker Class**: `gthread` (better for Flask with I/O-bound operations)
- **Timeout**: 120 seconds (Fly.io supports longer timeouts)
- **Max Requests**: 1000 per worker (with jitter for graceful restarts)

Configured in `Dockerfile` CMD.

### 4. System Architecture

#### Waterfall Approach (Cost Optimization)
1. **Phase 1: Free Sources** (Cost: $0)
   - Google CSE API (100 searches/day free)
   - GitHub API (5000 requests/hour with token)
   - Company websites

2. **Phase 2: Paid Sources** (Only if < 20 results)
   - SerpAPI
   - Apollo.io

#### Data Quality Features
- Person validation (removes false positives)
- Multi-source matching (higher confidence)
- OpenAI enhancement for categorization
- Source quality scoring
- Request queue management (max 10 concurrent searches)

### 5. Expected Performance

- **Small companies**: 15-30 people
- **Medium companies**: 30-50 people  
- **Large companies**: 50-100+ people
- **Cost**: $0 for most searches (free APIs)
- **Response time**: 10-25 seconds (with caching)
- **Concurrent capacity**: 10+ simultaneous searches per instance

### 6. Scaling Configuration

**Auto-scaling:**
Fly.io automatically scales based on traffic. Configure in `fly.toml`:
```toml
[http_service]
  min_machines_running = 1
  auto_start_machines = true
  auto_stop_machines = false
```

**Manual scaling:**
```bash
# Scale to 2 instances
flyctl scale count 2

# Scale memory/CPU
flyctl scale vm shared-cpu-2x --memory 1024
```

### 7. Monitoring

**View logs:**
```bash
flyctl logs
```

**Check app status:**
```bash
flyctl status
flyctl metrics
```

**Look for in logs:**
- "🚀 Elite free sources loaded" - System initialized
- "📊 Free sources found: X people" - Phase 1 results
- "✅ Sufficient results from free sources!" - No paid APIs used
- Any "⚠️" warnings for configuration issues

### 8. Troubleshooting

**Application won't start:**
- Check logs: `flyctl logs`
- Verify environment variables: `flyctl secrets list`
- Ensure Dockerfile builds successfully locally

**Timeout errors:**
- Fly.io allows 120+ second timeouts (much longer than Render's 30s)
- Check if APIs are responding slowly
- Reduce search scope (more specific job titles)
- Ensure you're not hitting rate limits

**No results:**
- Check GOOGLE_API_KEY and GOOGLE_CSE_ID are set
- Verify Google Custom Search Engine is configured for linkedin.com
- Check daily API limits (100 for Google CSE)

**429 Rate Limit errors:**
- Server is handling maximum concurrent searches (10)
- Wait a moment and retry
- Consider scaling to multiple instances

**Few results:**
- Add GITHUB_TOKEN for better GitHub API limits
- Consider enabling paid APIs for backup

**Database connection issues:**
- Verify SUPABASE_URL and SUPABASE_KEY are set correctly
- Check Supabase dashboard for connection limits

### 9. Cost Optimization

**Current setup:**
- Fly.io: ~$5-15/month (512MB RAM, shared CPU)
- Google CSE: FREE (100 searches/day)
- GitHub API: FREE (5000/hour with token)
- OpenAI: Minimal cost (small usage per search)

**As you scale:**
- Fly.io scales automatically - pay for what you use
- Consider Redis caching for search results (reduce API calls)
- Monitor API usage to avoid unexpected costs

**Typical cost per search: $0** (using free sources)

### 10. Health Checks

The app includes health check endpoint:
- URL: `/api/v1/health`
- Checks database connection and API configuration
- Used by Fly.io for automatic health monitoring

### 11. Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Test with production Gunicorn settings
gunicorn --bind 0.0.0.0:8080 \
  --workers 4 \
  --threads 8 \
  --worker-class gthread \
  --timeout 120 \
  web_app:app

# Open http://localhost:8080
```

### 12. Key Files

- `web_app.py` - Flask application with loading UI
- `src/core/orchestrator.py` - Main search orchestrator with waterfall logic
- `src/scrapers/actually_working_free_sources.py` - Free API integrations
- `src/utils/person_validator.py` - False positive removal
- `fly.toml` - Fly.io configuration
- `Dockerfile` - Production Docker image

### 13. Recent Optimizations

1. **Concurrency Improvements**
   - Request queue management (max 10 concurrent searches)
   - Optimized Gunicorn configuration (4 workers, 8 threads)
   - Connection pooling for database

2. **Performance Enhancements**
   - Extended cache TTL (7 days for search results)
   - Better timeout handling (120s vs 30s)
   - Improved error handling

3. **Production Hardening**
   - Removed unused code and dependencies
   - Cleaned up imports
   - Optimized Docker image size

4. **Cost Optimization**
   - Waterfall approach (free sources first)
   - Caching to reduce API calls
   - Smart source selection

## Migration from Render

If migrating from Render:
1. Set up Fly.io account and install flyctl
2. Run `flyctl launch` to create app
3. Set all environment variables as secrets
4. Deploy: `flyctl deploy`
5. Update DNS/domain if needed
6. Monitor logs and metrics

**Benefits over Render:**
- Longer timeouts (120s+ vs 30s)
- Better auto-scaling
- Global edge network
- More cost-effective at scale
