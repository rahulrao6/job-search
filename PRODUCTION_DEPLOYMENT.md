# Production Deployment Guide

## Quick Deploy to Render.com

### 1. Update Commands in Render.com UI

**Build Command:**
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 web_app:app
```

### 2. Required Environment Variables

Add these in Render.com dashboard:
- `GOOGLE_API_KEY` - Your Google API key
- `GOOGLE_CSE_ID` - Your CSE ID (e.g., 57a851efab97f4477)
- `GITHUB_TOKEN` - Optional but recommended for higher limits
- `OPENAI_API_KEY` - For enhanced categorization
- `SERP_API_KEY` - Backup for paid searches
- `APOLLO_API_KEY` - Backup for paid searches

### 3. System Architecture

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

### 4. Expected Performance

- **Small companies**: 15-30 people
- **Medium companies**: 30-50 people  
- **Large companies**: 50-100+ people
- **Cost**: $0 for most searches (free APIs)
- **Response time**: 10-20 seconds

### 5. Monitoring

Check Render.com logs for:
- "🚀 Elite free sources loaded" - System initialized
- "📊 Free sources found: X people" - Phase 1 results
- "✅ Sufficient results from free sources!" - No paid APIs used
- Any "⚠️" warnings for configuration issues

### 6. Troubleshooting

**502 Bad Gateway:**
- Ensure gunicorn is in requirements.txt ✅
- Check build logs for pip install errors
- Verify Python version compatibility

**No results:**
- Check GOOGLE_API_KEY and GOOGLE_CSE_ID are set
- Verify Google Custom Search Engine is configured for linkedin.com
- Check daily API limits (100 for Google CSE)

**Few results:**
- Add GITHUB_TOKEN for better GitHub API limits
- Consider enabling paid APIs for backup

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Test with gunicorn
gunicorn --bind 0.0.0.0:8000 web_app:app

# Open http://localhost:8000
```

## Key Files

- `web_app.py` - Flask application with loading UI
- `src/core/orchestrator.py` - Main search orchestrator with waterfall logic
- `src/scrapers/actually_working_free_sources.py` - Free API integrations
- `src/utils/person_validator.py` - False positive removal

## Recent Changes

1. Fixed gunicorn installation in render.yaml
2. Added runtime.txt for Python version
3. Optimized search queries for better results
4. Implemented waterfall approach (free first, then paid)
5. Added loading animation with progress indicators
6. Enhanced person validation to reduce false positives
7. Improved GitHub search flexibility

## Cost Analysis

- Google CSE: 100 searches/day FREE
- GitHub API: 60/hour (no auth), 5000/hour (with token) FREE
- SerpAPI: $50/month for 5000 searches (backup only)
- Apollo: 50 credits/month FREE (backup only)

**Typical cost per search: $0** (using free sources)
