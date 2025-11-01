# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Connection Finder PoC** - a job search tool that finds relevant people at target companies for job referrals by aggregating data from multiple sources (Apollo.io API, GitHub, company websites, Google SERP, LinkedIn public profiles, etc.).

## Development Commands

### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Install browser for web scraping
playwright install chromium
```

### Main Development Command
```bash
# Primary CLI tool - test all data sources
python scripts/test_all_sources.py --company "Meta" --title "Software Engineer"

# With optional domain hint
python scripts/test_all_sources.py --company "Stripe" --title "Engineer" --domain "stripe.com"

# Disable caching for fresh results
python scripts/test_all_sources.py --company "Google" --title "PM" --no-cache
```

### Testing
```bash
# Run unit tests
pytest tests/

# Run specific test files
pytest tests/test_sources.py
pytest tests/test_core.py

# Run with verbose output
pytest -v tests/
```

### Code Quality
```bash
# Format code
black src/ scripts/ tests/

# Run black in check mode (don't modify files)
black --check src/ scripts/ tests/
```

## Architecture Overview

### Core Components

**Orchestrator Pattern**: `src/core/orchestrator.py` (`ConnectionFinder` class) coordinates the entire pipeline:
1. Loads source configurations from `config/sources.yaml`
2. Initializes all data source clients
3. Runs searches across multiple sources in parallel
4. Aggregates and deduplicates results
5. Categorizes people into Manager/Recruiter/Peer/Senior buckets

**Data Sources** (`src/sources/` and `src/apis/`):
- **Apollo.io API** (`apollo_client.py`) - Primary paid API with emails + LinkedIn URLs
- **Company Pages** (`company_pages.py`) - Scrapes career pages for team listings
- **GitHub** (`github_profiles.py`) - Finds developers via organization search
- **Google SERP** (`google_search.py`) - Uses SerpAPI to find LinkedIn profiles
- **Crunchbase** (`crunchbase_client.py`) - Finds executives and leadership
- **LinkedIn Public** (`linkedin_public.py`) - Direct scraping (rate limited)

**Core Processing** (`src/core/`):
- **Aggregator** (`aggregator.py`) - Deduplicates and merges person records
- **Categorizer** (`categorizer.py`) - Classifies people into referral categories using keyword matching

**Utilities** (`src/utils/`):
- **Rate Limiter** (`rate_limiter.py`) - Per-source rate limiting
- **Cache** (`cache.py`) - Disk-based caching with 24hr TTL
- **Cost Tracker** (`cost_tracker.py`) - Monitors API usage costs
- **HTTP Client** (`http_client.py`) - Shared HTTP session with retries
- **Stealth Browser** (`stealth_browser.py`) - Anti-detection for scraping

### Data Flow

1. User runs CLI with company + job title
2. `ConnectionFinder` loads enabled sources from config
3. Each source searches for people matching criteria
4. Results flow through `PeopleAggregator` for deduplication
5. `PersonCategorizer` assigns Manager/Recruiter/Peer/Senior categories
6. Final results exported as JSON + Markdown reports to `outputs/`

### Configuration System

**Source Configuration** (`config/sources.yaml`):
- Enable/disable sources
- Set rate limits per source
- Configure priority tiers
- Specify authentication requirements

**Environment Variables** (`.env` file):
- `APOLLO_API_KEY` - Apollo.io API key (10k free credits/month)
- `SERP_API_KEY` - SerpAPI key (100 free searches/month)
- `DEBUG` - Enable debug logging

### Person Data Model

All sources normalize to unified `Person` model (`src/models/person.py`):
- Core fields: name, title, company
- Contact info: linkedin_url, email, twitter_url, github_url
- Metadata: source, confidence, category
- Uses Pydantic for validation

### Anti-Detection & Ethics

- **Rate Limiting**: Configurable per-source limits in `sources.yaml`
- **Proxy Support**: `proxy_manager.py` for IP rotation (optional)
- **Browser Stealth**: `stealth_browser.py` with fingerprint protection
- **Graceful Degradation**: System works even if sources fail
- **Caching**: Avoids redundant requests (24hr cache TTL)

## File Locations

- **Results**: `outputs/results_[company]_[timestamp].json` and `.md`
- **Debug Logs**: `outputs/debug.log` (when `DEBUG=true`)
- **Configuration**: `config/sources.yaml` and `.env`
- **Documentation**: `docs/` directory with setup guides and legal info

## Development Notes

- **Add New Sources**: Implement `BaseSource` interface in `src/sources/` or `src/apis/`
- **Modify Categories**: Update keyword lists in `config/sources.yaml`
- **Change Rate Limits**: Adjust per-source limits in `config/sources.yaml`
- **Debug Issues**: Set `DEBUG=true` in `.env` and check `outputs/debug.log`

The system is designed for defensive job search automation - finding publicly available information about potential referrers while respecting rate limits and ToS constraints.