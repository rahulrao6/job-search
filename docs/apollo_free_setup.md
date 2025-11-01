# Apollo.io Free API Setup Guide

## ✅ YES - Apollo Free API DOES Work!

You were right! Apollo.io **does** provide free API access with their free plan.

## What You Get (FREE)

- ✅ **API Key Creation:** Free
- ✅ **Rate Limits:** 50 calls/minute, 600 calls/day
- ✅ **Credits:** 10,000 email credits per month
- ✅ **Endpoints:** `/contacts/search`, `/accounts/search`, `/organizations/search`
- ✅ **Data:** Names, titles, LinkedIn URLs, emails, phone numbers

## How It Works

1. Sign up for free Apollo account
2. Create API key (no payment required)
3. Each search result uses 1 email credit
4. You get 10,000 credits/month = **10,000 contact results per month FREE**

## Setup Steps (5 minutes)

### 1. Sign Up
Go to: https://app.apollo.io/
- Click "Sign Up"
- Use work email for best results
- Verify email

### 2. Create API Key
- Login to Apollo
- Click Settings (⚙️ icon, bottom left)
- Go to "Integrations" section
- Find "API" section
- Click "Create API Key"
- Give it a name like "job-search-poc"
- Copy the API key

### 3. Add to .env
```bash
# Open .env file and add:
APOLLO_API_KEY=your_api_key_here
```

### 4. Test It
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Software Engineer"
```

Expected output:
```
✓ Apollo found 15-25 people (used 15 of 10k free credits)
```

## API Endpoints (Free Tier)

### 1. Contacts Search
```
POST /api/v1/contacts/search
```
Search for people by company, title, location, etc.

**Parameters:**
- `q_organization_name`: Company name
- `person_titles`: Array of job titles
- `person_locations`: Array of locations (optional)
- `page`: Page number (default: 1)
- `per_page`: Results per page (max: 100)

**Returns:**
- Name
- Title
- Company
- Email
- Phone
- LinkedIn URL
- Location

### 2. Accounts Search
```
POST /api/v1/accounts/search
```
Search for companies.

### 3. Organizations Search
```
POST /api/v1/organizations/search
```
Search for organizations.

## Rate Limits (Free Tier)

| Limit | Free Plan |
|-------|-----------|
| Calls per minute | 50 |
| Calls per day | 600 |
| Email credits/month | 10,000 |
| Mobile credits/month | 5 |

## Credit Usage

**What uses credits:**
- Getting email addresses: 1 credit per email
- Getting phone numbers: 1 mobile credit per phone

**What's free:**
- API calls (within rate limits)
- Basic profile data (name, title, company)
- LinkedIn URLs

**Strategy:**
- Each search returns ~10-25 people
- Each person uses 1 credit
- 10,000 credits = ~400-1000 job searches per month

## Cost Analysis

### Free Plan (Your PoC)
- **Cost:** $0/month
- **Credits:** 10,000 emails
- **API calls:** 600/day
- **Good for:** 400-1000 job searches/month
- **Limitation:** Rate limited to 600 calls/day

### If You Exceed Free Tier

**Basic Plan ($49/month):**
- Unlimited email credits
- 2,000 API calls/day
- 200 calls/minute

**Professional Plan ($79/month):**
- Everything in Basic
- More advanced filters
- Better support

## Recommendation

**For PoC (Testing):**
✅ Use FREE plan
- 10,000 credits is plenty for testing
- 600 API calls/day is enough
- No credit card needed

**For Production (If validated):**
💰 Upgrade to Basic ($49/month) only if:
- You're doing 1000+ searches per month
- You need faster rate limits
- You want unlimited credits

## Testing Your Setup

### Test 1: Basic Search
```bash
python scripts/test_all_sources.py --company "Meta" --title "Software Engineer"
```

### Test 2: Different Companies
```bash
python scripts/test_all_sources.py --company "Stripe" --title "Product Manager"
python scripts/test_all_sources.py --company "Airbnb" --title "Designer"
python scripts/test_all_sources.py --company "Notion" --title "Engineer"
```

### Test 3: Check Credits Used
After a few searches, log into Apollo dashboard and check:
- Settings → Usage
- See how many credits you've used
- You should have used ~50-100 credits (out of 10,000)

## Troubleshooting

### "API key invalid"
- Make sure you copied the entire key
- No extra spaces in .env file
- Format: `APOLLO_API_KEY=abc123...`

### "Rate limit exceeded"
- Free plan: 50 calls/min, 600/day
- Wait 1 minute and try again
- Or upgrade to paid plan

### "No credits remaining"
- You've used all 10,000 free credits
- Wait until next month (resets monthly)
- Or upgrade to paid plan for unlimited

### "No results found"
- Try different company name format
- Check company exists in Apollo database
- Try a larger/well-known company

## API Documentation

Official Apollo API docs:
https://docs.apollo.io/

Key sections:
- Authentication: https://docs.apollo.io/docs/authentication
- Contacts Search: https://docs.apollo.io/docs/contacts-search
- Rate Limits: https://docs.apollo.io/docs/rate-limiting

## What You Get vs Other Sources

| Source | Free? | Has Emails? | Has LinkedIn? | Results Quality |
|--------|-------|-------------|---------------|-----------------|
| **Apollo** | ✅ 10k/mo | ✅ Yes | ✅ Yes | ⭐⭐⭐⭐⭐ |
| SerpAPI | ✅ 100/mo | ❌ No | ✅ Yes | ⭐⭐⭐⭐ |
| GitHub | ✅ Unlimited | ⚠️ Sometimes | ❌ No | ⭐⭐⭐ |
| Company Pages | ✅ Unlimited | ❌ No | ⚠️ Sometimes | ⭐⭐⭐ |

**Verdict:** Apollo is the best free source if you have an API key!

## Your Next Steps

1. ✅ Sign up at https://app.apollo.io/
2. ✅ Create API key (Settings → Integrations → API)
3. ✅ Add to .env: `APOLLO_API_KEY=your_key`
4. ✅ Test: `python scripts/test_all_sources.py --company "Stripe" --title "Engineer"`
5. ✅ Check results in `outputs/` folder

You should get 15-25 people per search with emails + LinkedIn URLs! 🎉

