# Setup Guide - Connection Finder PoC

## Quick Start (Minimal Setup)

The system works with **ZERO API keys** for basic functionality. However, adding API keys significantly improves results.

## Setup Tasks Checklist

### Required (5 minutes)
- [ ] Install Python 3.9+ 
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Install Playwright browsers: `playwright install chromium`
- [ ] Copy config: `cp config/.env.example .env`

### Optional API Keys (Recommended)

#### Tier 1 - Most Valuable (Free tiers available)

##### 1. Apollo.io API (⭐ HIGHLY RECOMMENDED)
- **Cost**: FREE (50 credits/month)
- **Value**: Best source for finding people with emails + LinkedIn URLs
- **Setup time**: 5 minutes
- **Steps**:
  1. Go to https://app.apollo.io/
  2. Sign up for free account (use work email)
  3. Verify email
  4. Go to Settings → Integrations → API
  5. Generate API key
  6. Add to `.env`: `APOLLO_API_KEY=your_key_here`

##### 2. SerpAPI (for Google/Bing searches)
- **Cost**: FREE (100 searches/month)
- **Value**: Find LinkedIn profiles via Google without hitting LinkedIn directly
- **Setup time**: 3 minutes
- **Steps**:
  1. Go to https://serpapi.com/
  2. Sign up for free account
  3. Copy API key from dashboard
  4. Add to `.env`: `SERP_API_KEY=your_key_here`

#### Tier 2 - Nice to Have

##### 3. OpenAI API (for enhanced parsing)
- **Cost**: Pay-as-you-go (~$0.01 per job search)
- **Value**: Better extraction from messy HTML/text
- **Setup**: Get key from https://platform.openai.com/api-keys
- **Add to `.env`**: `OPENAI_API_KEY=your_key_here`

##### 4. Clay API (expensive, only if budget allows)
- **Cost**: $149+/month
- **Value**: Waterfall enrichment when other sources fail
- **Setup**: https://clay.com/
- **Add to `.env`**: `CLAY_API_KEY=your_key_here`

#### Tier 3 - Advanced (for LinkedIn scraping)

##### 5. LinkedIn Session Cookies (optional, risky)
- **Cost**: FREE (use your own account)
- **Value**: Access more LinkedIn data
- **Risk**: ⚠️ Violates LinkedIn ToS, account may be banned
- **Setup**:
  1. Log into LinkedIn in browser
  2. Open Developer Tools (F12)
  3. Go to Application/Storage → Cookies
  4. Copy `li_at` cookie value
  5. Add to `.env`: `LINKEDIN_COOKIES=li_at=your_cookie_value`
- **Note**: Only use if you're comfortable with the risk

##### 6. Proxy Service (optional)
- **Cost**: FREE tier available (WebShare.io - 1GB free)
- **Value**: Avoid rate limits and blocks
- **Setup**:
  1. Sign up at https://www.webshare.io/
  2. Get proxy list from dashboard
  3. Add to `.env`: `PROXY_LIST=http://user:pass@proxy:port`

## Configuration

### Environment Variables (.env file)

```bash
# === TIER 1 - Recommended ===
APOLLO_API_KEY=                    # Apollo.io - 50 free credits/month
SERP_API_KEY=                      # SerpAPI - 100 free searches/month

# === TIER 2 - Optional ===
OPENAI_API_KEY=                    # OpenAI - pay per use
CLAY_API_KEY=                      # Clay - $149+/month

# === TIER 3 - Advanced (risky) ===
LINKEDIN_COOKIES=                  # Your LinkedIn cookies (risky)
PROXY_LIST=                        # Proxy server URL

# === Rate Limiting (don't change unless needed) ===
MAX_REQUESTS_PER_MINUTE=30
MAX_LINKEDIN_REQUESTS_PER_HOUR=50

# === Caching ===
CACHE_TTL_HOURS=24                 # How long to cache results

# === Debugging ===
DEBUG=false
DRY_RUN=false                      # Test mode without real requests
```

### Source Configuration (config/sources.yaml)

Each source can be enabled/disabled:

```yaml
sources:
  apollo:
    enabled: true                   # Turn on/off
    requires_auth: true             # Needs API key
    rate_limit: 1                   # Requests per second
    
  company_pages:
    enabled: true
    requires_auth: false            # No API key needed
    
  # ... etc
```

## What Works Without Any Setup

Even with zero API keys, these sources work:

1. ✅ **Company career pages** - Scrapes team/about pages
2. ✅ **GitHub** - Searches public profiles and org members
3. ✅ **Crunchbase** - Scrapes leadership data
4. ✅ **Google search** - Limited without API (will use direct scraping)

## Recommended Setup for Best Results

**Minimum (FREE)**:
- Apollo.io API key (5 min setup)
- SerpAPI key (3 min setup)
- Total time: 8 minutes
- Total cost: $0/month

**Optimal (STILL FREE)**:
- Everything above +
- OpenAI API key (~$0.01 per search)
- Total time: 12 minutes
- Total cost: ~$0.50/month for 50 searches

## Testing Your Setup

Run this to test all configured sources:

```bash
python scripts/test_all_sources.py --company "Meta" --title "Software Engineer"
```

You'll see which sources are working:
```
✓ Apollo found 15 people (API key configured)
✓ Company pages found 8 people
✓ GitHub found 12 people
✓ Google SERP found 20 people (API key configured)
⚠️  LinkedIn skipped (no cookies provided)
```

## Troubleshooting

### "Apollo authentication failed"
- Check API key is correct in `.env`
- Verify email is confirmed on Apollo account
- Check you haven't exceeded 50 credit limit

### "Rate limit exceeded"
- Wait 1 hour and try again
- Reduce `MAX_REQUESTS_PER_MINUTE` in `.env`
- Add proxy to distribute requests

### "No results found"
- Try different company name format (e.g., "Meta" vs "Meta Platforms")
- Check `outputs/` folder for debug logs
- Enable debug mode: `DEBUG=true` in `.env`

## Security Notes

1. **Never commit `.env` file** - It contains your API keys
2. **LinkedIn cookies are risky** - Use at your own risk, account may be banned
3. **Respect rate limits** - Don't change limits to avoid bans
4. **Cache is local** - Results stored in `.cache/` folder

## Next Steps

Once setup is complete:
1. Run test search to verify setup
2. Check `outputs/source_comparison.json` to see which sources work best
3. Adjust `config/sources.yaml` to disable sources you don't need
4. Start using the system for real job searches

## Support

If you encounter issues:
1. Check `outputs/debug.log` for error details
2. Try with `DRY_RUN=true` to test without making requests
3. Enable `DEBUG=true` for verbose output

