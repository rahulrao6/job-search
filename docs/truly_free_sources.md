# Truly Free Data Sources (No Payment Required)

## Summary

These sources work 100% FREE with no credit card, no payment, no trials.

| Source | Free? | Results Quality | Setup Time | Best For |
|--------|-------|----------------|------------|----------|
| **SerpAPI** | ✅ 100 searches/month | ⭐⭐⭐⭐ High | 3 min | LinkedIn profiles via Google |
| **GitHub** | ✅ Unlimited | ⭐⭐⭐ Medium | 0 min | Technical roles |
| **Company Pages** | ✅ Unlimited | ⭐⭐⭐ Medium | 0 min | Leadership/teams |
| **Crunchbase** | ✅ Public data | ⭐⭐ Low | 0 min | Startup leadership |
| **Apollo.io API** | ❌ Requires $49-119/month | ⭐⭐⭐⭐⭐ Best | N/A | NOT FREE |

## 1. SerpAPI (⭐ BEST FREE OPTION)

### What You Get
- 100 Google searches per month FREE
- Finds LinkedIn profiles without hitting LinkedIn
- Returns name, title, LinkedIn URL from Google results
- No credit card required

### Setup (3 minutes)
```bash
# 1. Sign up
https://serpapi.com/

# 2. After signup, copy API key from dashboard
# 3. Add to .env:
SERP_API_KEY=your_key_here
```

### Example Output
```
✓ Google SERP found 20 people
- John Smith - Engineering Manager at Meta
  LinkedIn: https://linkedin.com/in/johnsmith
- Jane Doe - Technical Recruiter at Meta
  LinkedIn: https://linkedin.com/in/janedoe
```

### Pros
- ✅ Best free option
- ✅ Finds LinkedIn URLs
- ✅ No scraping risk (official API)
- ✅ 100 searches = ~50 job searches

### Cons
- ⚠️ Limited to 100 searches/month
- ⚠️ No emails (just LinkedIn URLs)

## 2. GitHub (Technical Roles)

### What You Get
- Unlimited searches (no API key needed)
- Find engineers by company
- GitHub profiles show:
  - Name
  - Bio (often includes title/role)
  - Company affiliation
  - Email (sometimes public)

### Setup
None! Works immediately.

### Example
Search: "Software Engineer at Meta"
Finds: Engineers with Meta in their GitHub profile

### Pros
- ✅ 100% free, unlimited
- ✅ No API key needed
- ✅ Good for technical roles
- ✅ Sometimes shows emails

### Cons
- ⚠️ Only works for technical roles
- ⚠️ Not everyone has GitHub
- ⚠️ Limited company data

## 3. Company Career Pages

### What You Get
- Team/About pages listing employees
- Job postings with hiring manager names
- Leadership directories
- Press releases with people names

### Setup
None! Works immediately.

### Example
Scrapes: company.com/team, company.com/about/leadership
Finds: Names, titles from public pages

### Pros
- ✅ 100% free, unlimited
- ✅ Fully legal (public data)
- ✅ Often has leadership
- ✅ No API needed

### Cons
- ⚠️ Not all companies have this
- ⚠️ Usually just leadership (not individual contributors)
- ⚠️ No contact info

## 4. Crunchbase Public Data

### What You Get
- Company leadership (CEO, CTO, etc.)
- Founders
- Board members
- Sometimes LinkedIn links

### Setup
None! Works immediately.

### Example
Searches: crunchbase.com/organization/meta
Finds: Leadership team

### Pros
- ✅ Free for public data
- ✅ Good for startups
- ✅ Leadership focus
- ✅ Often has LinkedIn

### Cons
- ⚠️ Only leadership/founders
- ⚠️ Not good for large companies
- ⚠️ Limited to public profiles

## Recommended Strategy for PoC

### Phase 1: Test with 100% Free Sources
```bash
# Edit .env and add ONLY:
SERP_API_KEY=your_serpapi_key_here

# Leave Apollo blank:
APOLLO_API_KEY=

# Test:
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```

**Expected Results:**
- 20-30 people with LinkedIn URLs
- Some with titles and names
- No emails (yet)

### Phase 2: Verify It Works
Run 5-10 test searches with different companies:
```bash
python scripts/test_all_sources.py --company "Airbnb" --title "Product Manager"
python scripts/test_all_sources.py --company "Notion" --title "Designer"
python scripts/test_all_sources.py --company "OpenAI" --title "ML Engineer"
```

Check results in `outputs/` folder.

### Phase 3: If It Works, Then Pay
Once you've validated the PoC works, consider paid options:

**Option A: Apollo.io** ($49/month)
- Best data quality
- Includes emails
- Unlimited API access
- Worth it if you're doing 50+ searches/month

**Option B: Proxycurl** ($0.01-0.05 per profile)
- Pay per use
- LinkedIn data API
- Good for lower volume

**Option C: RocketReach** ($39/month)
- Email finder
- LinkedIn enrichment
- Good middle ground

## Updated .env Configuration

```bash
# === 100% FREE SOURCES (Start Here) ===

# SerpAPI - 100 free searches/month (BEST FREE OPTION)
# Sign up: https://serpapi.com/
SERP_API_KEY=

# GitHub - Unlimited, no key needed (automatically works)
# Company Pages - Unlimited, no key needed (automatically works)
# Crunchbase - Unlimited public data (automatically works)

# === PAID SOURCES (Test free sources first) ===

# Apollo.io - Requires $49-119/month (NOT FREE)
# Leave blank for now
APOLLO_API_KEY=

# OpenAI - Optional, ~$0.01 per search
OPENAI_API_KEY=
```

## Cost Comparison

### FREE Setup (Recommended for PoC)
- SerpAPI: $0/month (100 searches)
- GitHub: $0/month (unlimited)
- Company Pages: $0/month (unlimited)
- Crunchbase: $0/month (public data)
- **Total: $0/month, ~50 job searches**

### Paid Setup (If PoC successful)
- Apollo.io: $49/month (unlimited emails)
- SerpAPI: $50/month (5000 searches)
- OpenAI: ~$5/month (500 searches)
- **Total: ~$100/month, unlimited searches**

## Action Plan

1. **Today:** Add SerpAPI key only (3 minutes, free)
2. **Test:** Run 5-10 searches with free sources
3. **Validate:** Check if results are good enough
4. **Decide:** If good, keep free. If need emails, then pay for Apollo.

## Bottom Line

**Start with SerpAPI + free sources** = $0/month, 40-60 people per search

Only pay for Apollo ($49/month) once you've proven the free version works and you need emails.

