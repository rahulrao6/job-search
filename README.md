# Connection Finder PoC

A proof-of-concept system for finding relevant people at target companies for job referrals.

## Overview

This tool helps job seekers identify high-value connections at companies by:
- Finding managers, recruiters, peers, and senior employees
- Aggregating data from multiple free and paid sources
- Providing categorized lists of people to reach out to

## Features

- **Multiple data sources**: Apollo.io, GitHub, company websites, Google SERP, LinkedIn (with protection)
- **Anti-detection measures**: Rate limiting, proxy rotation, browser fingerprinting
- **Graceful degradation**: Works even if some sources fail
- **Cost tracking**: Monitor API usage and costs
- **Caching**: Avoid redundant requests

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. **Configure environment**:
```bash
cp config/.env.example config/.env
# Edit config/.env with your API keys
```

3. **Run a test search**:
```bash
python scripts/test_all_sources.py --company "Meta" --title "Software Engineer"
```

## Project Structure

```
src/
├── models/          # Data models
├── utils/           # Shared utilities (rate limiting, caching, etc.)
├── apis/            # API client implementations
├── sources/         # Web scraping implementations
└── core/            # Core orchestration logic

tests/               # Test suites
scripts/             # CLI tools
config/              # Configuration files
docs/                # Documentation
outputs/             # Results and reports
```

## Data Sources

### Tier 1 (Most Reliable)
- Apollo.io API (50 free credits/month)
- Company career pages
- GitHub organization search
- Crunchbase free tier

### Tier 2 (Search Intermediaries)
- Google SERP scraping
- Bing Search API

### Tier 3 (Direct Scraping)
- LinkedIn public profiles
- LinkedIn company pages

## Configuration

See `docs/setup_guide.md` for detailed setup instructions.

## Legal & ToS

See `docs/legal_risks.md` for important information about terms of service and scraping ethics.

## License

MIT

