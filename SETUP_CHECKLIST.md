# Setup Checklist - Get Started in 5 Minutes

## ✅ Step-by-Step Setup

### 1. Install Python Dependencies (2 minutes)
```bash
cd /Users/rahulrao/job-search
pip install -r requirements.txt
```

### 2. Install Playwright Browser (1 minute)
```bash
playwright install chromium
```

### 3. Test Without API Keys (1 minute)
The system works without any API keys! Test it now:
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```

**Expected Output:**
```
✓ Company pages found X people
✓ GitHub found X people  
✓ Crunchbase found X people
⊘ apollo: not configured (missing API key)
⊘ google_serp: not configured (missing API key)
⊘ linkedin_public: disabled
```

### 4. Add API Keys for Better Results (Optional - 8 minutes)

#### Apollo.io (⭐ MOST IMPORTANT - 5 min)
1. Go to https://app.apollo.io/
2. Click "Sign Up" (use work email for best results)
3. Verify your email
4. Click Settings (gear icon) → Integrations → API
5. Click "Create API Key"
6. Copy the key
7. Open `.env` file and paste: `APOLLO_API_KEY=your_key_here`

#### SerpAPI (Recommended - 3 min)
1. Go to https://serpapi.com/
2. Click "Sign Up" (free account)
3. After login, go to Dashboard
4. Copy your API key
5. Open `.env` file and paste: `SERP_API_KEY=your_key_here`

### 5. Test With API Keys (1 minute)
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```

**Expected Output:**
```
✓ Apollo found 15 people
✓ Company pages found 8 people
✓ GitHub found 12 people
✓ Crunchbase found 5 people
✓ Google SERP found 20 people
⊘ linkedin_public: disabled (recommended)

📊 RESULTS SUMMARY
Total unique people found: 45

By category:
  👔 Manager: 8
  🎯 Recruiter: 3
  ⭐ Senior: 12
  👥 Peer: 18
```

## ✅ Verify Everything Works

Run the full test:
```bash
python scripts/test_all_sources.py --company "Meta" --title "Product Manager"
```

Check the output files:
```bash
ls -la outputs/
# You should see:
# - results_meta_TIMESTAMP.json
# - results_meta_TIMESTAMP.md
```

Read the markdown report:
```bash
cat outputs/results_*.md
```

## 🎯 What You Get

For each job search, you'll find:

### 👔 Managers (Top 5)
- People who would be your manager
- Directors, VPs, Heads of Department
- LinkedIn URLs + emails (if available)

### 🎯 Recruiters (Top 5)
- Technical recruiters
- Talent acquisition
- HR business partners

### ⭐ Senior Peers (Top 5)
- People one level above you
- Senior engineers, Staff engineers
- Good for technical insights

### 👥 Peers (Top 5)
- People at your level
- Can provide insider info
- May refer you directly

## 💰 Cost Breakdown

**Without API Keys:** $0/month
- Works but limited results (10-30 people)

**With Free API Keys:** $0/month  
- Apollo: 50 searches free
- SerpAPI: 100 searches free
- Total: **50 job searches/month for FREE**

**If You Exceed Free Tier:**
- Apollo: $49/month for unlimited
- SerpAPI: $50/month for 5000 searches
- Only pay if you need more

## 🚫 What NOT to Do

**Don't:**
- ❌ Add LinkedIn cookies (account ban risk)
- ❌ Change rate limits aggressively
- ❌ Use for high-volume commercial purposes without legal review
- ❌ Commit the .env file to git

**Do:**
- ✅ Use free sources (company pages, GitHub, Crunchbase)
- ✅ Add free API keys (Apollo, SerpAPI)
- ✅ Respect rate limits
- ✅ Cache results (automatic)

## 🔧 Troubleshooting

### "No module named 'src'"
```bash
# Make sure you're in the project directory
cd /Users/rahulrao/job-search
python scripts/test_all_sources.py --company "Meta" --title "Engineer"
```

### "Apollo authentication failed"
- Check API key is correct in `.env`
- Make sure there are no spaces around the `=`
- Verify email is confirmed on Apollo account

### "No results found"
- Try different company name: "Meta" vs "Meta Platforms" vs "Facebook"
- Some companies have limited public data
- Try a bigger/well-known company first

### "playwright not found"
```bash
playwright install chromium
```

## 📁 Project Structure

```
job-search/
├── .env                      ← Your API keys (edit this)
├── requirements.txt          ← Dependencies
├── README.md                 ← Overview
├── QUICKSTART.md            ← Quick reference
├── SETUP_CHECKLIST.md       ← This file
│
├── config/
│   └── sources.yaml         ← Enable/disable sources
│
├── scripts/
│   └── test_all_sources.py  ← Main CLI tool
│
├── src/
│   ├── models/              ← Data structures
│   ├── utils/               ← Rate limiting, caching
│   ├── apis/                ← API clients (Apollo, etc)
│   ├── sources/             ← Scrapers (GitHub, etc)
│   └── core/                ← Orchestration logic
│
├── outputs/                 ← Results go here
├── tests/                   ← Unit tests
├── examples/                ← Sample data
└── docs/                    ← Documentation
```

## 🚀 Next Steps

Once setup is complete:

1. **Test with your target company:**
   ```bash
   python scripts/test_all_sources.py --company "YourTargetCompany" --title "Your Target Role"
   ```

2. **Review the results:**
   ```bash
   cat outputs/results_*.md
   ```

3. **Reach out to connections:**
   - Start with recruiters (easiest)
   - Then managers (decision makers)
   - Then peers (insider info)

4. **Iterate:**
   - Try variations of company name
   - Try different role titles
   - Results cached for 24hrs

## 📖 More Documentation

- **Setup Guide:** `docs/setup_guide.md` - Detailed setup instructions
- **Legal Info:** `docs/legal_risks.md` - Important ToS information
- **Architecture:** `docs/architecture.md` - How it all works

## ✉️ Support

If something doesn't work:
1. Check this checklist again
2. Read `docs/setup_guide.md`
3. Enable debug mode: `DEBUG=true` in `.env`
4. Check `outputs/debug.log`

---

**You're all set! Run your first search now:**
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```

