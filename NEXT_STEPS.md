# What To Do Next

## Option 1: Test What's Working (10 minutes)

### Add SerpAPI Key
```bash
# 1. Go to https://serpapi.com/
# 2. Sign up (free, no credit card)
# 3. Copy API key
# 4. Add to .env:
echo "SERP_API_KEY=your_key_here" >> .env
```

### Test with Multiple Companies
```bash
# Tech companies (GitHub works great)
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer" --no-cache
python scripts/test_all_sources.py --company "Shopify" --title "Backend Engineer" --no-cache
python scripts/test_all_sources.py --company "Databricks" --title "Data Engineer" --no-cache

# Check results
cat outputs/results_*.md
```

### Evaluate Results
- How many people per company?
- Which sources work best?
- Do you need emails? (If yes → need paid service)
- Is categorization correct?

## Option 2: Improve Free Scrapers (2-4 hours)

If you want to stay 100% free, improve these:

### 1. Company Pages Scraper
**Problem**: Not finding anyone
**Fix**: Handle more website structures
**Effort**: 2 hours
**Payoff**: Could find 5-15 people per company

### 2. Twitter/Nitter Scraper
**Problem**: Nitter instances timing out
**Fix**: Better instance rotation, fallbacks
**Effort**: 1 hour
**Payoff**: 5-10 people per company

### 3. Wellfound Scraper
**Problem**: Not finding companies
**Fix**: Better slug guessing, company search
**Effort**: 1 hour
**Payoff**: Good for startups

## Option 3: Pay for Better Data (Recommended for Production)

### Apollo.io Basic - $49/month
- Unlimited API access
- Emails included
- LinkedIn URLs
- 2000 requests/day
- **Best option if you're serious**

### Hunter.io - $39/month
- Email finding only
- Use with free scrapers for LinkedIn
- 500 emails/month
- Good middle ground

### Decision Matrix

| Need | Free Option | Paid Option | Recommendation |
|------|-------------|-------------|----------------|
| LinkedIn URLs | SerpAPI (100/mo) | Apollo ($49) | Free is fine |
| Emails | ❌ Not reliable | Apollo ($49) | Need paid |
| Managers | Hit/miss | Apollo ($49) | Need paid |
| Recruiters | Hard to find | Apollo ($49) | Need paid |
| Tech roles | ✅ GitHub | Not needed | Free works |

## Option 4: Focus on Integration (Your DB → Engine)

Since you said data comes from your DB anyway:

### Create Integration Layer
```python
# your_integration.py

from src.core.orchestrator import ConnectionFinder
from src.extractors.job_parser import JobParser
from src.extractors.resume_parser import ResumeParser

def find_connections_for_job(job_id: str):
    """
    Your main integration function.
    
    Called from your service when user requests connections.
    """
    # 1. Get data from your DB
    job = db.get_job(job_id)
    candidate = db.get_candidate(job.candidate_id)
    
    # 2. Parse if needed (or assume your DB has clean data)
    job_parser = JobParser()
    job_info = job_parser.parse(
        job_url=job.url,
        job_text=job.description
    )
    
    resume_parser = ResumeParser()
    candidate_profile = resume_parser.parse(candidate.resume_text)
    
    # 3. Find connections
    finder = ConnectionFinder()
    results = finder.find_connections(
        company=job_info["company"],
        title=job_info["job_title"],
        company_domain=job_info.get("company_domain"),
    )
    
    # 4. Store in your DB
    for category, people in results["by_category"].items():
        for person in people:
            db.store_connection(
                job_id=job_id,
                candidate_id=candidate.id,
                person_name=person["name"],
                person_title=person["title"],
                person_linkedin=person["linkedin_url"],
                person_email=person["email"],
                category=category,
                confidence=person["confidence"],
                source=person["source"],
            )
    
    return results
```

### Test Integration
```python
# test_integration.py

# Mock your DB data
mock_job = {
    "id": "job123",
    "url": "https://linkedin.com/jobs/view/123",
    "description": "Software Engineer at Meta...",
    "company": "Meta",
    "title": "Software Engineer",
}

mock_candidate = {
    "id": "cand456",
    "resume_text": "Stanford graduate, ex-Google engineer...",
    "schools": ["Stanford"],
    "past_companies": ["Google"],
}

# Run
results = find_connections_for_job("job123")
print(f"Found {results['total_found']} connections")
```

## My Recommendation

**For PoC (Next 1-2 weeks)**:
1. ✅ Add SerpAPI key (3 minutes)
2. ✅ Test with 10 different companies
3. ✅ Validate engine works end-to-end
4. ✅ Show to users, get feedback

**If Users Like It**:
1. 💰 Pay for Apollo ($49/mo) → get emails
2. 🔧 Improve categorization based on feedback
3. 🔧 Add alumni boost scoring
4. 🚀 Scale up

**If You Want to Stay Free**:
1. 🔧 Spend 4-8 hours improving scrapers
2. ⚠️ Accept that you won't get emails
3. ⚠️ Accept that some categories will be sparse
4. ✅ But it will work for PoC

## What I'd Do (If I Were You)

```bash
# Day 1: Validate (30 min)
1. Add SerpAPI key
2. Test with 5 companies
3. Check if results are useful

# Day 2-3: If promising (4 hours)
1. Improve company pages scraper
2. Add alumni boost
3. Test with 20 companies

# Week 2: If users want it (1 day)
1. Subscribe to Apollo ($49/mo)
2. Integration with your DB
3. Deploy to production

# Month 2: Optimize (ongoing)
1. Track which sources work best
2. Improve ranking based on user feedback
3. Add more sources as needed
```

## Questions to Answer

Before you continue, decide:

1. **Do you need emails?**
   - Yes → Need Apollo ($49/mo) or Hunter ($39/mo)
   - No → Free sources are fine

2. **How many job searches per month?**
   - <100 → Free tier is fine
   - 100-1000 → Need SerpAPI paid ($50/mo)
   - >1000 → Need all paid tiers

3. **What's more valuable: time or money?**
   - Time → Pay $49/mo for Apollo, save 10+ hours
   - Money → Spend 10 hours improving free scrapers

4. **Is this a PoC or production?**
   - PoC → Use free, validate concept
   - Production → Pay for reliability

## Ready to Move Forward?

Run this to see current state:
```bash
python scripts/test_engine_comprehensive.py  # Validate engine
python scripts/test_all_sources.py --company "YourTargetCo" --title "Role" --no-cache
cat STATUS.md  # Read detailed status
```

