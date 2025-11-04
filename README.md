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

**Deploy to Fly.io:**
1. Install [flyctl](https://fly.io/docs/getting-started/installing-flyctl/)
2. Run `flyctl launch` in the project directory (or `flyctl deploy` if app already exists)
3. Set environment variables:
   ```bash
   flyctl secrets set GOOGLE_API_KEY=your_key GOOGLE_CSE_ID=your_cse_id
   flyctl secrets set OPENAI_API_KEY=your_key
   flyctl secrets set SUPABASE_URL=your_url SUPABASE_KEY=your_key
   ```
4. Deploy: `flyctl deploy`
5. Your app will be live at `https://your-app-name.fly.dev`

**Benefits of Fly.io:**
- Auto-scaling based on traffic
- Global edge network for low latency
- Generous timeouts (120s+) for long-running searches
- Cost-effective pricing starting at ~$5/month
- Easy scaling as you grow

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

### 1. Data Collection Strategy (Quality-First Waterfall)
```
Phase 1: FREE Sources (Cost: $0)
├── Google Custom Search Engine API (LinkedIn profiles - HIGH QUALITY)
├── Bing API (LinkedIn profiles) - if configured
└── GitHub API (Usernames only - LOW QUALITY, for enrichment)

Phase 2: PAID Sources (Only if < 10 quality results)
├── SerpAPI (Best LinkedIn data)
└── Apollo.io (Verified professional data)

Note: GitHub results are included but heavily deprioritized
```

### 2. Data Processing Pipeline
1. **Search** → Multiple sources in parallel
2. **Aggregate** → Deduplicate by LinkedIn URL/name
3. **Validate** → Remove false positives
4. **Enhance** → Use OpenAI for categorization
5. **Categorize** → Manager, Recruiter, Senior, Peer, Unknown

## Performance

- **Small companies**: 10-20 quality people (LinkedIn profiles)
- **Medium companies**: 20-40 quality people  
- **Large companies**: 40+ quality people
- **Response time**: 10-25 seconds (optimized with caching and concurrency)
- **Cost**: $0 for most searches
- **Quality**: 100% LinkedIn profiles with job titles

### Recent Quality Improvements
- **GitHub deprioritized** - Included but sorted last (for future enrichment)
- **LinkedIn profiles first** - Full names, titles, direct links prioritized
- **Quality-based sorting** - LinkedIn (0.9) > GitHub (0.2) quality scores
- **Future-ready** - GitHub results ready for enrichment via Clay/APIs

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
fly.toml            # Fly.io deployment configuration
Dockerfile          # Docker image for deployment
```

## Configuration

### Required API Keys (All FREE)

1. **Google Custom Search** (REQUIRED) - See [GOOGLE_CSE_QUICKSTART.md](GOOGLE_CSE_QUICKSTART.md)
   - 100 searches/day free
   - Primary source for LinkedIn profiles
   - Returns professional data with titles

2. **OpenAI API** (REQUIRED) - For enhanced categorization
   - Small usage, minimal cost
   - Critical for categorizing people

3. **Bing API** (Optional) - Additional LinkedIn results
   - 1000/month free tier available

4. **GitHub Token** (Optional)
   - Returns usernames for future enrichment
   - Deprioritized in results (shown last)
   - Good for building enrichment pipelines

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
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deploy to Fly.io
- [GOOGLE_CSE_QUICKSTART.md](GOOGLE_CSE_QUICKSTART.md) - Google Custom Search setup
- [AUTH_SETUP.md](AUTH_SETUP.md) - Authentication setup
- [API_SETUP.md](API_SETUP.md) - API configuration
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting common issues

## License

MIT - Feel free to use commercially!

