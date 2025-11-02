# 🆓 Setup Free APIs - 5 Minutes to 100x Better Results

## Why This Matters

Without APIs: 10-30 results (GitHub only)
**With APIs: 50-150 results** ← HUGE difference

Setup time: 5-10 minutes total
Cost: **$0/month**

## Quick Setup

### 1. Google Custom Search Engine (5 min) - HIGHEST IMPACT

**What it does**: Returns LinkedIn profiles directly from Google's index
**Results**: 10-30 high-quality LinkedIn profiles per search
**Limit**: 100 searches/day FREE

#### Setup Steps:

```bash
# 1. Create Custom Search Engine
#    Go to: https://programmablesearchengine.google.com/
#    Click "Add" button
#    Name: "LinkedIn Profile Search"
#    What to search: "Sites to search" → Add "linkedin.com/in/*"
#    Click "Create"
#    Copy your "Search engine ID" (looks like: 017643025432574196288:xxxxxxx)

# 2. Get API Key
#    Go to: https://console.cloud.google.com/
#    If new: Create a project
#    Go to "APIs & Services" → "Credentials"
#    Click "Create Credentials" → "API Key"
#    Copy the API key
#    Click "Enable APIs and Services"
#    Search for "Custom Search API"
#    Click "Enable"

# 3. Add to your .env file
echo "GOOGLE_CSE_ID=paste_your_search_engine_id" >> .env
echo "GOOGLE_API_KEY=paste_your_api_key" >> .env
```

**Test it:**
```bash
python -c "
import os
os.environ['GOOGLE_CSE_ID'] = 'your_id'
os.environ['GOOGLE_API_KEY'] = 'your_key'

import requests
url = 'https://www.googleapis.com/customsearch/v1'
params = {
    'key': os.environ['GOOGLE_API_KEY'],
    'cx': os.environ['GOOGLE_CSE_ID'],
    'q': 'Software Engineer',
}
r = requests.get(url, params=params)
print('✅ Working!' if r.status_code == 200 else f'❌ Error: {r.status_code}')
"
```

### 2. Bing Web Search API - DEPRECATED ⚠️

**Update**: Microsoft has deprecated the free tier of Bing Search API.

**Alternative**: Google Custom Search Engine (above) provides similar functionality and is still free.

If you need more searches beyond Google CSE's 100/day:
- Upgrade Google CSE to paid tier ($5 per 1000 searches)
- Use SerpAPI ($50/month for 5000 searches)
- Use multiple Google accounts for multiple CSEs (not recommended)

### 3. GitHub Token (2 min) - OPTIONAL

**What it does**: Increases GitHub API limit from 60/hour to 5000/hour
**Results**: Same results, just faster/more requests
**Limit**: 5000 requests/hour FREE

#### Setup Steps:

```bash
# 1. Generate Token
#    Go to: https://github.com/settings/tokens
#    Click "Generate new token (classic)"
#    Note: "Job Search Tool"
#    Expiration: No expiration (or 1 year)
#    Scopes: NONE needed (public data only)
#    Click "Generate token"
#    Copy the token (starts with ghp_)

# 2. Add to .env
echo "GITHUB_TOKEN=paste_your_token" >> .env
```

## Expected Results

### Scenario 1: No APIs Configured
- GitHub (no token): ~10-20 results
- Company websites: ~0-10 results
- **Total: 10-30 connections**

### Scenario 2: GitHub Token Only
- GitHub (with token): ~20-50 results
- Company websites: ~0-10 results
- **Total: 20-60 connections**

### Scenario 3: All APIs Configured ✅
- Google CSE: ~10-30 LinkedIn profiles
- Bing API: ~20-50 LinkedIn profiles
- GitHub: ~20-50 results
- Company websites: ~5-15 results
- **Total: 55-145 connections** 🎯

## Troubleshooting

### Google CSE

**"API key not valid"**
- Make sure you enabled "Custom Search API" in Google Cloud Console
- Make sure the API key is correct (no spaces, full key)

**"Invalid CX parameter"**
- Make sure you're using the full search engine ID (looks like: 017643025432574196288:pqowieqo)
- Not the search engine name

**"Daily limit exceeded"**
- Free tier is 100 queries/day
- Resets at midnight PT
- Can upgrade to paid tier if needed ($5 per 1000 queries)

### Bing API

**"Access denied"**
- Make sure you selected the F0 (FREE) tier
- Make sure the resource deployment completed
- Try regenerating the key

**"Out of call volume quota"**
- Free tier is 1000 queries/month
- Resets monthly
- Can upgrade to paid tier if needed

### GitHub Token

**"Bad credentials"**
- Token must start with `ghp_`
- Make sure you copied the entire token
- Tokens expire - regenerate if needed

**Still getting rate limited**
- 5000 requests/hour even with token
- Wait for reset (check `X-RateLimit-Reset` header)

## Cost Analysis

### Free Tier Limits:
- Google CSE: 100/day = 3000/month
- Bing API: 1000/month
- GitHub: 5000/hour = unlimited practically
- **Total: ~4000 searches/month FREE**

### If You Need More:
- Google CSE: $5 per 1000 queries
- Bing API: Paid tiers start at $7/month
- GitHub: Always free

For 99% of users, free tier is plenty.
