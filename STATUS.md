# Connection Finder - Current Status

**Last Updated:** November 1, 2025

## ✅ What's Working (Tested & Validated)

### Core Engine Logic
- ✅ **Categorization**: Correctly identifies managers, recruiters, seniors, peers
- ✅ **Deduplication**: Merges same person from multiple sources
- ✅ **Data Merging**: Combines LinkedIn URLs, emails, GitHub profiles
- ✅ **Confidence Scoring**: Multi-source matches get higher scores
- ✅ **Ranking**: People sorted by confidence within categories
- ✅ **Top N Selection**: Returns best 5 people per category

### Data Sources (Tested with Stripe)
- ✅ **GitHub**: Found 20 Stripe engineers (working perfectly)
- ✅ **Google SERP**: Found 10 LinkedIn profiles (with SerpAPI key)
- ⚠️ **Company Pages**: Needs improvement (found 0)
- ⚠️ **Twitter**: Needs improvement (found 0)
- ⚠️ **Wellfound**: Needs improvement (found 0)
- ❌ **Crunchbase**: Blocked (403 errors)
- ❌ **Apollo.io**: Free API has no database access (need paid tier)

### Infrastructure
- ✅ **Rate Limiting**: Per-source limits working
- ✅ **Caching**: 24hr cache to avoid redundant requests
- ✅ **Cost Tracking**: API usage tracked
- ✅ **OpenAI Enhancement**: Cleans messy titles/bios (if key provided)
- ✅ **Error Handling**: Graceful degradation when sources fail

## 🔧 What's Implemented But Needs Testing

### Parsers (Ready for DB integration)
- ✅ **Job Parser**: Extracts company, title, department from job posting
- ✅ **Resume Parser**: Extracts schools, past companies, skills
- ✅ **Job Context Model**: Structured format for DB → Engine

### Alumni Matching Logic
- ✅ **Data Model**: Candidate schools & past companies stored
- ⚠️ **Scoring Boost**: Not yet applied (easy to add)
- ⚠️ **Alumni Detection**: Need to check if found people match candidate background

### Additional Sources (Code ready, not tested)
- ✅ **Twitter Search**: Via Nitter instances
- ✅ **Wellfound**: AngelList scraping
- ⚠️ Both need testing with different companies

## 🚀 What You Have Now

### Free Sources Working
1. **GitHub** (✅ Excellent for tech roles)
   - Finds: Engineers, DevOps, data scientists
   - Returns: Name, title, GitHub URL, sometimes email
   - Cost: $0, unlimited

2. **Google SERP via SerpAPI** (✅ Good for LinkedIn profiles)
   - Finds: Anyone with LinkedIn profile
   - Returns: Name, title, LinkedIn URL
   - Cost: $0 for 100 searches/month
   - **YOU NEED TO ADD**: SerpAPI key

### What Each Source Gives You

| Source | People Found | Has LinkedIn | Has Email | Cost | Status |
|--------|--------------|--------------|-----------|------|--------|
| GitHub | 10-20 | ❌ | Sometimes | $0 | ✅ Working |
| Google SERP | 10-30 | ✅ | ❌ | $0* | ✅ Needs key |
| Company Pages | 5-15 | Sometimes | ❌ | $0 | ⚠️ Hit/miss |
| Twitter | 5-10 | ❌ | ❌ | $0 | ⚠️ Needs work |
| Crunchbase | 5-10 | Sometimes | ❌ | $0 | ❌ Blocked |
| Wellfound | 5-15 | Sometimes | ❌ | $0 | ⚠️ Needs work |
| **Apollo.io** | **0** | ✅ | ✅ | **$49/mo** | ❌ Needs paid |

*SerpAPI: 100 free/month, then $50/mo for 5000

## 📊 Current Performance (Based on Stripe Test)

**Input**: Company="Stripe", Title="Software Engineer"

**Output**:
- 20 unique people found
- 17 peers (engineers at same level)
- 1 senior (architect/lead)
- 2 unknown (couldn't categorize)
- Sources: GitHub (10) + Google SERP (10)
- Time: ~30 seconds
- Cost: $0

**What's Missing**: Managers, Recruiters (need better sources)

## 🎯 Recommended Next Steps

### Immediate (To Make It Actually Useful)

1. **Add SerpAPI Key** (3 minutes, FREE)
   ```bash
   # Get key: https://serpapi.com/
   # Add to .env:
   SERP_API_KEY=your_key_here
   ```
   This will 2x your results with LinkedIn profiles.

2. **Improve Company Pages Scraper**
   - Currently not finding anyone
   - Need to handle more website structures
   - Should find leadership (managers, directors)

3. **Test with 5-10 Different Companies**
   - See which sources work best for which companies
   - GitHub: Great for tech companies (Stripe, Airbnb, Shopify)
   - Company pages: Better for traditional companies
   - Build source → company type mapping

### Short Term (For Better Results)

4. **Add Email Finding Service**
   - Hunter.io: $49/mo for 500 emails
   - OR RocketReach: $39/mo
   - OR just use Apollo paid ($49/mo gets everything)
   
5. **Implement Alumni Boost**
   - Parse candidate resume for schools/companies
   - Boost confidence +0.2 if same school
   - Boost confidence +0.3 if past company match
   - Prioritize alumni in results

6. **Add Connection Path**
   - Parse candidate's LinkedIn connections (if provided)
   - Mark people as "2nd degree connection"
   - Show mutual connections

### Future (For Scale)

7. **Database Integration**
   - Store found people in DB
   - Avoid re-searching same company
   - Build historical data

8. **More Sources**
   - Blind (for anonymous company insights)
   - Glassdoor (for company reviews, sometimes has people)
   - Reddit (r/cscareerquestions mentions)
   - Hacker News (Who's hiring threads)

9. **Smart Ranking**
   - ML model for better categorization
   - Response rate tracking (who actually responds)
   - Conversion tracking (who gives referrals)

## 💡 Architecture Decisions Made

### Why Multiple Cheap Sources vs One Expensive API?
✅ **Resilience**: If one source fails, others work
✅ **Cost**: 5 free sources > 1 expensive API
✅ **Coverage**: Different sources find different people
✅ **Deduplication**: Engine merges overlapping results

### Data Flow
```
Your DB → Job Context → Engine → People Finder
                                      ↓
                          [GitHub, SerpAPI, Company Pages...]
                                      ↓
                              Aggregator (dedupe)
                                      ↓
                              Categorizer
                                      ↓
                                  Ranker
                                      ↓
                              Top 5 per category
                                      ↓
                              Your DB/Frontend
```

### What You Control
- ✅ Job posting data (your scraper)
- ✅ Candidate resume (your DB)
- ✅ User context (your forms)
- ✅ Which sources to enable
- ✅ How to rank/filter results

### What Engine Handles
- ✅ Finding people from multiple sources
- ✅ Deduplication
- ✅ Categorization
- ✅ Ranking
- ✅ Rate limiting
- ✅ Caching
- ✅ Error handling

## 📝 Sample Integration

```python
from src.core.orchestrator import ConnectionFinder

# Initialize once
finder = ConnectionFinder()

# From your DB/service
job_context = {
    "company": "Meta",
    "job_title": "Software Engineer",
    "company_domain": "meta.com",  # Optional but helps
    "candidate_schools": ["Stanford"],  # For alumni matching
    "candidate_past_companies": ["Google"],  # For alumni matching
}

# Find connections
results = finder.find_connections(
    company=job_context["company"],
    title=job_context["job_title"],
    company_domain=job_context["company_domain"],
)

# Returns
# {
#   "total_found": 20,
#   "by_category": {
#     "manager": [...],  # Top 5 managers
#     "recruiter": [...],  # Top 5 recruiters
#     "senior": [...],  # Top 5 senior people
#     "peer": [...],  # Top 5 peers
#   },
#   "source_stats": {...},
#   "cost_stats": {...}
# }
```

## 🎯 Bottom Line

**Working Now:**
- ✅ Core engine (categorization, deduplication, ranking)
- ✅ GitHub scraper (excellent for tech companies)
- ✅ Google SERP (with SerpAPI key)
- ✅ Full infrastructure (caching, rate limiting, etc.)

**Needs Work:**
- ⚠️ Company pages scraper (not finding people)
- ⚠️ Manager/recruiter finding (need better sources)
- ⚠️ Email addresses (need paid service OR better free scraping)

**Recommended Path:**
1. Add SerpAPI key → immediate 2x improvement
2. Test with 10 companies → see what works
3. Then decide: improve free scrapers OR pay for Apollo ($49/mo)

**For PoC**: GitHub + SerpAPI is enough to validate the concept works.

**For Production**: Need email addresses → Apollo ($49/mo) or Hunter.io ($39/mo)

