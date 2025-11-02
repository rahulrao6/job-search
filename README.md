# Job Referral Connection Finder

Production-ready system for finding relevant people at target companies for job referrals, with a focus on FREE data sources and cost optimization.

## Overview

This tool helps job seekers find the right people to connect with at target companies:
- **Smart Categorization**: Identifies managers, recruiters, peers, and senior employees
- **Cost-Optimized**: Prioritizes free sources (Google CSE, GitHub API) before paid APIs
- **Quality Focused**: Validates results to remove false positives
- **Easy to Use**: Web interface for non-technical users

## Key Features

- **Waterfall Data Strategy**: Free sources first (Google CSE, GitHub) → Paid only if needed
- **Multi-Source Aggregation**: Combines 5+ data sources with deduplication
- **Person Validation**: Removes past employees, name matches, and spam profiles
- **OpenAI Enhancement**: Categorizes people based on seniority and relevance
- **Beautiful Web UI**: Mobile-friendly with loading animations
- **Cost Tracking**: Usually $0 per search using free APIs

## Quick Start

### Option 1: Deploy Web App (Recommended)

**Deploy to Render.com (FREE):**
1. Fork/clone this repo to GitHub
2. Go to [render.com](https://render.com) and sign up
3. Create new Web Service → Connect your repo
4. Use these settings:
   - Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 web_app:app`
5. Add environment variables (see [SETUP_FREE_APIS.md](SETUP_FREE_APIS.md))
6. Deploy! Share the URL with anyone

**Local Testing:**
```bash
pip install -r requirements.txt
python web_app.py
# Open http://localhost:8000
```

### Option 2: Direct API Integration

```python
from src.core.orchestrator import ConnectionFinder

# Initialize
finder = ConnectionFinder()

# Search for connections
results = finder.find_connections(
    company="Stripe",
    title="Software Engineer"
)

# Access results
print(f"Found {results['total_found']} people")
for category, people in results['by_category'].items():
    print(f"{category}: {len(people)} people")
```

## How It Works

### 1. Data Collection Strategy (Waterfall Approach)
```
Phase 1: FREE Sources (Cost: $0)
├── Google Custom Search Engine API (100/day free)
├── GitHub API (5000/hour with token)
└── Company Websites

Phase 2: PAID Sources (Only if < 20 results)
├── SerpAPI ($50/month)
└── Apollo.io (50 credits/month free)
```

### 2. Data Processing Pipeline
1. **Search** → Multiple sources in parallel
2. **Aggregate** → Deduplicate by LinkedIn URL/name
3. **Validate** → Remove false positives
4. **Enhance** → Use OpenAI for categorization
5. **Categorize** → Manager, Recruiter, Senior, Peer, Unknown

## Performance

- **Small companies**: 15-25 people (usually FREE)
- **Medium companies**: 30-50 people (often FREE)  
- **Large companies**: 50+ people
- **Response time**: 10-25 seconds (optimized for Render's 30s limit)
- **Cost**: $0 for most searches

### Recent Performance Optimizations
- Reduced API timeouts (10s → 5s)
- Limited results per source for speed
- Skip expensive operations when approaching time limit
- Disabled company website search by default

## Project Structure

```
src/
├── core/            # Main orchestration logic
│   ├── orchestrator.py    # ConnectionFinder class
│   ├── aggregator.py      # Deduplication logic
│   └── categorizer.py     # Person categorization
├── scrapers/        # Data source implementations
│   └── actually_working_free_sources.py
├── models/          # Data models (Person, etc.)
├── utils/           # Utilities (validation, caching)
└── apis/            # API clients (Apollo, Google)

web_app.py          # Flask web application
requirements.txt    # Python dependencies
render.yaml         # Render.com configuration
```

## Configuration

### Required API Keys (All FREE)

1. **Google Custom Search** - See [GOOGLE_CSE_QUICKSTART.md](GOOGLE_CSE_QUICKSTART.md)
   - 100 searches/day free
   - Best source for LinkedIn profiles

2. **GitHub Token** (Optional but recommended)
   - 5000 API calls/hour vs 60 without
   - Great for tech companies

3. **OpenAI API** - For enhanced categorization
   - Small usage, minimal cost

### Environment Variables
```bash
GOOGLE_API_KEY=your_key
GOOGLE_CSE_ID=your_cse_id  
GITHUB_TOKEN=your_token     # Optional
OPENAI_API_KEY=your_key
SERP_API_KEY=your_key       # Backup only
APOLLO_API_KEY=your_key     # Backup only
```

## Documentation

- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - **Complete guide for teams** (share this!)
- [SETUP_FREE_APIS.md](SETUP_FREE_APIS.md) - Set up free API keys
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deploy to production
- [TIMEOUT_FIX_SUMMARY.md](TIMEOUT_FIX_SUMMARY.md) - Recent 502 timeout fixes
- [RENDER_SETUP.md](RENDER_SETUP.md) - Deploy to Render.com
- [GOOGLE_CSE_QUICKSTART.md](GOOGLE_CSE_QUICKSTART.md) - Google Custom Search setup
- [QUICK_START.md](QUICK_START.md) - Quick start guide

## License

MIT - Feel free to use commercially!

