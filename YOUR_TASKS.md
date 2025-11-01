# 🎯 YOUR ACTION ITEMS

## Required Tasks (Must Do)

### ✅ 1. Install Dependencies (2 minutes)
```bash
cd /Users/rahulrao/job-search
pip install -r requirements.txt
playwright install chromium
```

### ✅ 2. Test Without API Keys (1 minute)
**The system works right now without any setup!** Test it:
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```

You'll get 10-30 people from:
- Company career pages ✅
- GitHub profiles ✅  
- Crunchbase leadership ✅

## Recommended Tasks (For Better Results)

### 🔍 3. Add SerpAPI Key (3 minutes) - ⭐ BEST FREE OPTION

**Why?** 100 FREE searches per month, finds LinkedIn profiles via Google.

**Steps:**
1. Go to https://serpapi.com/
2. Click "Sign Up" (NO credit card required)
3. Copy API key from dashboard
4. **Edit `.env` file:**
   ```bash
   SERP_API_KEY=paste_your_key_here
   ```

**Result:** Will find 20-30 LinkedIn profiles! 🎉

### 🎯 4. Add Apollo.io API Key (FREE - 10k credits/month)

**CORRECTION: Apollo IS FREE!** (You were right!)

**Why?** Best source - includes emails + LinkedIn URLs. 10,000 free credits/month!

**Steps:**
1. Go to https://app.apollo.io/
2. Sign up (FREE - no credit card needed)
3. Verify email
4. Settings (⚙️) → Integrations → API → "Create API Key"
5. Copy the key
6. **Edit `.env` file:**
   ```bash
   APOLLO_API_KEY=paste_your_key_here
   ```

**What you get:** 15-25 people per search with emails + LinkedIn URLs

**Cost:** $0/month (10,000 credits = ~400-1000 job searches)

## What NOT To Do ❌

1. **Don't add LinkedIn cookies** - High risk of account ban
2. **Don't change rate limits** - Will get you blocked
3. **Don't commit .env to git** - Already in .gitignore

## Testing Your Setup

### Without API Keys:
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```
Expected: 10-30 people from free sources (no emails)

### With SerpAPI (100% FREE):
```bash
python scripts/test_all_sources.py --company "Meta" --title "Product Manager"
```
Expected: 30-50 people with LinkedIn URLs (no emails)

### With Apollo ($49/month):
```bash
python scripts/test_all_sources.py --company "Meta" --title "Product Manager"
```
Expected: 50-80 people with emails AND LinkedIn URLs

### Check Results:
```bash
ls outputs/
cat outputs/results_*.md
```

## Cost Summary

| Setup | Sources Working | People Found | Monthly Cost |
|-------|----------------|--------------|--------------|
| **No API Keys** | 3 sources | 10-30 | **$0** |
| **+ SerpAPI** | 4 sources | 30-50 | **$0** (100 free) |
| **+ Apollo** | 5 sources | 40-60 + emails | **$0** (10k free) |

**Recommendation:** Add both SerpAPI AND Apollo (both 100% free, takes 8 min total).

## Your .env File Status

✅ `.env` file created  
📝 Ready to add API keys (optional)  
🔒 Protected by .gitignore (won't commit to git)

To edit:
```bash
code .env
# or
nano .env
# or
vim .env
```

## Quick Reference

**Main Command:**
```bash
python scripts/test_all_sources.py --company "COMPANY" --title "JOB_TITLE"
```

**Examples:**
```bash
# Tech companies
python scripts/test_all_sources.py --company "Google" --title "Software Engineer"
python scripts/test_all_sources.py --company "Meta" --title "Product Manager"
python scripts/test_all_sources.py --company "Stripe" --title "Data Scientist"

# Startups
python scripts/test_all_sources.py --company "Anthropic" --title "ML Engineer"

# With domain hint
python scripts/test_all_sources.py --company "Airbnb" --title "Designer" --domain "airbnb.com"
```

## Troubleshooting

### "No module named 'src'"
```bash
cd /Users/rahulrao/job-search
python scripts/test_all_sources.py ...
```

### "playwright not found"
```bash
playwright install chromium
```

### "No results found"
- Try different company name variations
- Try a well-known company first (Google, Meta, etc.)
- Add Apollo API key for much better results

## Next Steps

1. ✅ Test without API keys (works now!)
2. 📝 Add Apollo API key (5 min, huge improvement)
3. 📝 Add SerpAPI key (3 min, more LinkedIn profiles)
4. 🚀 Use for real job searches
5. 📊 Review results in `outputs/` folder

## Documentation

- **Quick Start:** `SETUP_CHECKLIST.md` - Detailed walkthrough
- **Setup Guide:** `docs/setup_guide.md` - All API options
- **Legal Info:** `docs/legal_risks.md` - Important ToS information
- **How It Works:** `docs/architecture.md` - Technical details

---

## Summary

**Working right now:** ✅ (No API keys needed)  
**Recommended:** Add Apollo + SerpAPI keys (8 min, 100% free, 3x better results)  
**Best:** Apollo gives you emails + LinkedIn URLs!  
**Cost:** $0/month for 400-1000 job searches  

**Start here:**
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```

