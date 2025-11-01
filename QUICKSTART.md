# Quick Start - What You Need To Do

## 🚀 3-Step Setup (10 minutes total)

### Step 1: Install Dependencies (2 minutes)
```bash
pip install -r requirements.txt
playwright install chromium
```

### Step 2: Get Free API Keys (8 minutes)

**Apollo.io** (⭐ Most Important - 5 min):
1. Go to https://app.apollo.io/
2. Sign up (free)
3. Settings → API → Generate key
4. Copy to notepad

**SerpAPI** (Optional but recommended - 3 min):
1. Go to https://serpapi.com/
2. Sign up (free 100 searches/month)
3. Copy API key from dashboard

### Step 3: Configure (1 minute)
```bash
# Create .env file (skip the .example one, it's blocked)
cat > .env << EOF
APOLLO_API_KEY=paste_your_apollo_key_here
SERP_API_KEY=paste_your_serp_key_here
EOF
```

## ✅ That's It!

Test it works:
```bash
python scripts/test_all_sources.py --company "Meta" --title "Software Engineer"
```

## 💰 What You'll Pay

- **Apollo.io**: $0/month (50 free searches)
- **SerpAPI**: $0/month (100 free searches)  
- **Total**: **$0/month** for PoC

## 📊 What You'll Get

For each job search:
- 5-50 relevant people at the target company
- Categories: Managers, Recruiters, Peers, Senior employees
- LinkedIn URLs (when available)
- Emails (when available via Apollo)
- Evidence URLs showing where we found them

## ⚠️ What NOT to Do

**Don't** add LinkedIn cookies - high risk of account ban
**Don't** change rate limits - will get you blocked
**Don't** use for high-volume commercial use (without legal review)

## 🎯 Next Steps After Setup

1. Run test search
2. Review results in `outputs/` folder
3. Adjust `config/sources.yaml` if needed
4. Start searching for real jobs

## 📚 More Info

- **Detailed setup**: See `docs/setup_guide.md`
- **Legal info**: See `docs/legal_risks.md`
- **Full README**: See `README.md`

## 🆘 Troubleshooting

**"No results found"**:
- Check API keys are correct in `.env`
- Try different company name format

**"Rate limit exceeded"**:
- You've used all free credits
- Wait until next month or upgrade account

**Still stuck?**:
- Enable debug: `DEBUG=true` in `.env`
- Check `outputs/debug.log`

