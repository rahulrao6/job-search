# 🆓 Free Sources Strategy - Build What Works

## 🎯 Goal: Scale with FREE Sources

**Key Insight:** SerpAPI costs money. To scale, we need robust FREE sources.

## 📊 Current State

### Working:
- ✅ **GitHub** - Works, but minimal metadata
- ✅ **SerpAPI** - Works, but COSTS MONEY

### Broken (Need to Fix):
- ❌ **Free LinkedIn (RealWorkingScraper)** - Search engines not returning results
- ❌ **Company Pages** - Missing dependencies, needs better scraping
- ❌ **Twitter/X** - Nitter instances down, need alternative
- ❌ **Wellfound** - Not finding companies reliably
- ❌ **Crunchbase** - 403 Forbidden (anti-scraping)

## 🔧 Fix Strategy for Each Source

### 1. Free LinkedIn (RealWorkingScraper) - PRIORITY 1
**Problem:** Alternative search engines (Searx, Qwant, etc.) not returning results

**Solutions to Try:**
1. **Google Custom Search API** (100 free searches/day)
2. **Bing Search API** (1000 free searches/month)
3. **DuckDuckGo HTML scraping** (with proper user agent)
4. **LinkedIn company page patterns** (e.g., linkedin.com/company/google/people)
5. **LinkedIn Sales Navigator URLs** (public patterns)

**Implementation:**
```python
def search_linkedin_profiles_free(company, role):
    sources = [
        google_custom_search,  # 100/day free
        bing_search_api,       # 1000/month free
        duckduckgo_html,       # Unlimited with rate limiting
    ]
    
    for source in sources:
        results = source.search(f'site:linkedin.com/in "{company}" "{role}"')
        if results:
            return results
    
    return []
```

### 2. Company Pages - PRIORITY 2
**Problem:** Missing `get_company_info` dependency

**Solutions:**
1. **Fix the missing import** - Implement or remove dependency
2. **Enhance scraping patterns** - Better regex for names/titles
3. **Common page patterns:**
   - `/about/team`
   - `/team`
   - `/leadership`
   - `/careers` (hiring managers)
   - `/contact` (recruiters)

**Implementation:**
```python
def scrape_company_pages(company_domain):
    pages_to_check = [
        f"https://{domain}/team",
        f"https://{domain}/about/team",
        f"https://{domain}/leadership",
        f"https://{domain}/people",
        f"https://{domain}/careers",
    ]
    
    people = []
    for page in pages_to_check:
        html = fetch_with_retries(page)
        people.extend(extract_people_from_html(html))
    
    return deduplicate(people)
```

### 3. Twitter/X - PRIORITY 3
**Problem:** Nitter instances are down

**Solutions:**
1. **Twitter/X public API** (free tier exists)
2. **Alternative Nitter instances** (check updated list)
3. **Direct Twitter scraping** (with stealth)
4. **Twitter Advanced Search URLs** (public, no auth needed)

**Twitter Advanced Search Pattern:**
```
https://twitter.com/search?q=("Software Engineer" "Google")&f=user
```

### 4. Wellfound (AngelList) - PRIORITY 3
**Problem:** Not finding companies reliably

**Solutions:**
1. **Better company slug detection**
2. **Search API** (if available)
3. **Company page URL patterns**

### 5. Crunchbase - PRIORITY 4
**Problem:** 403 Forbidden

**Solutions:**
1. **Rotating user agents**
2. **Proxy rotation**
3. **Rate limiting** (very slow, respectful)
4. **Alternative:** Use their official API (paid, but has free tier)

### 6. NEW: Google Custom Search API
**Add this as a new free source!**

**Benefits:**
- 100 searches/day FREE
- Can search LinkedIn profiles
- Can search company pages
- Official Google API (reliable)

**Setup:**
```bash
# Get API key: https://developers.google.com/custom-search
GOOGLE_CUSTOM_SEARCH_KEY=xxx
GOOGLE_CUSTOM_SEARCH_CX=xxx  # Custom Search Engine ID
```

## 🏗️ Implementation Plan

### Phase 1: Quick Wins (TODAY)
1. ✅ **Re-enable all free sources** (don't disable them)
2. ✅ **Keep quality sorting** (SerpAPI first, but others still run)
3. ✅ **Fix company_pages import** (remove or implement dependency)
4. ✅ **Add Google Custom Search API** (100 free/day)
5. ✅ **Add Bing Search API** (1000 free/month)

### Phase 2: Robust Free LinkedIn (NEXT)
1. Implement Google Custom Search for LinkedIn
2. Implement Bing Search API for LinkedIn
3. Add DuckDuckGo HTML scraping fallback
4. Test with 10+ companies
5. Ensure 20-50 profiles per search

### Phase 3: Enhanced Company Pages (SOON)
1. Fix missing dependencies
2. Add more page patterns
3. Better name/title extraction
4. Test with 20+ companies

### Phase 4: Twitter/X Integration (LATER)
1. Find working Nitter instances
2. Or implement Twitter public API
3. Extract bio + LinkedIn URL from profiles

## 🎯 Target: 100% Free Operations

**With all free sources working:**
- Google Custom Search: 100 searches/day
- Bing Search API: 1000 searches/month
- GitHub: Unlimited (respectful rate limiting)
- Company Pages: Unlimited (respectful)
- DuckDuckGo: Unlimited (with delays)
- Twitter: Depends on method

**Expected results per search:**
- 10-30 from Google Custom Search (LinkedIn profiles)
- 5-20 from Bing Search (LinkedIn profiles)
- 10-30 from GitHub
- 5-15 from Company Pages
- 5-10 from Twitter/X

**Total: 35-105 connections per search, 100% FREE!**

## 💰 Cost Comparison

### Current (SerpAPI):
- Cost: $0.005 per search
- 100 searches = $0.50
- 1000 searches = $5.00

### With Free Sources:
- Cost: $0.00 per search
- 100 searches = $0.00
- 1000 searches = $0.00
- **Savings: 100%**

### Hybrid (Best Quality):
- SerpAPI (primary): $0.005/search
- Free sources (backup): $0.00
- Total: Same cost but MORE results

## 🚀 Why This Matters

1. **Scalability:** Can handle unlimited users
2. **Cost:** $0 infrastructure cost
3. **Reliability:** Multiple sources = backup if one fails
4. **Quality:** More sources = more connections found
5. **Independence:** Not reliant on one paid API

## 📋 Next Steps

1. **DON'T disable free sources** - keep them enabled
2. **DO fix them one by one** - make them work well
3. **DO add new free APIs** - Google Custom Search, Bing
4. **DO improve scraping** - better patterns, anti-detection
5. **DO test thoroughly** - ensure high success rate

## 🎯 Success Metrics

For each free source:
- ✅ **Success rate:** >80% of searches return results
- ✅ **Results per search:** 10-30 connections
- ✅ **Quality:** LinkedIn URLs or enough metadata
- ✅ **Speed:** <10 seconds per source
- ✅ **Reliability:** Works consistently over 100+ searches

## 💡 Key Principle

**Quality sorting keeps SerpAPI results first, but free sources still contribute!**

Users with SERP_API_KEY:
- Get 30-50 from SerpAPI (sorted first)
- PLUS 30-50 from free sources (sorted after)
- Total: 60-100 connections

Users WITHOUT SERP_API_KEY:
- Get 0 from SerpAPI
- Get 30-50 from free sources only
- Total: 30-50 connections (still useful!)

## 🎉 Vision

**Build the best free connection finder on the internet.**

No other tool should be able to match our combination of:
- Quality (smart sorting, categorization)
- Quantity (multiple sources, 50-100 results)
- Cost ($0 for basic use, cheap for premium)
- Features (relevance matching in V2)

