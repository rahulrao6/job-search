#!/bin/bash
# Setup script to create .env file

echo "🚀 Creating .env file for Connection Finder..."
echo ""

cat > .env << 'EOF'
# Connection Finder Configuration
# This file contains your API keys and settings
# The system works WITHOUT any API keys - just leave them blank!

# =============================================================================
# TIER 1 - RECOMMENDED (All have FREE tiers)
# =============================================================================

# Apollo.io API - Best source for people data with emails + LinkedIn URLs
# Sign up: https://app.apollo.io/ (FREE - 50 credits/month)
# Get key: Settings → Integrations → API
APOLLO_API_KEY=

# SerpAPI - For Google search results without hitting Google directly
# Sign up: https://serpapi.com/ (FREE - 100 searches/month)
# Get key: Dashboard → API Key
SERP_API_KEY=

# =============================================================================
# TIER 2 - OPTIONAL (Pay-as-you-go or Expensive)
# =============================================================================

# OpenAI API - For enhanced parsing and extraction (costs ~$0.01 per search)
# Get key: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Clay API - Expensive waterfall enrichment ($149+/month)
# Only add if you have a Clay account
CLAY_API_KEY=

# =============================================================================
# TIER 3 - ADVANCED (Risky - Use at your own risk)
# =============================================================================

# LinkedIn Cookies - ⚠️ VIOLATES LINKEDIN TOS - Account may be BANNED
# Only use if you accept the risk
# How to get: Login to LinkedIn → Dev Tools (F12) → Application → Cookies → Copy 'li_at' value
# Leave BLANK to skip LinkedIn scraping (recommended)
LINKEDIN_COOKIES=

# Proxy Configuration - For avoiding rate limits
# Format: http://user:pass@host:port or http://host:port
# Free option: https://www.webshare.io/ (1GB free)
PROXY_LIST=

# =============================================================================
# RATE LIMITING (Don't change unless you know what you're doing)
# =============================================================================

# Global rate limit (requests per minute across all sources)
MAX_REQUESTS_PER_MINUTE=30

# LinkedIn-specific limit (very conservative to avoid bans)
MAX_LINKEDIN_REQUESTS_PER_HOUR=50

# =============================================================================
# CACHING
# =============================================================================

# How long to cache results (in hours)
# Prevents re-scraping the same company/job combination
CACHE_TTL_HOURS=24

# =============================================================================
# DEBUGGING & TESTING
# =============================================================================

# Enable verbose logging (true/false)
DEBUG=false

# Dry run mode - test without making real requests (true/false)
DRY_RUN=false

# =============================================================================
# NOTES
# =============================================================================
# 
# WORKS WITHOUT ANY API KEYS:
# - Company career pages scraping ✅
# - GitHub profile search ✅
# - Crunchbase leadership scraping ✅
# - Google search (limited, may be blocked) ⚠️
#
# RECOMMENDED SETUP (FREE):
# 1. Add APOLLO_API_KEY (5 min setup, 50 free credits/month)
# 2. Add SERP_API_KEY (3 min setup, 100 free searches/month)
# 3. Leave everything else blank
#
# AVOID:
# - LinkedIn cookies (high risk of account ban)
# - Changing rate limits (will get you blocked)
#
# =============================================================================
EOF

echo "✅ .env file created successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env and add your API keys (optional)"
echo "2. Run: pip install -r requirements.txt"
echo "3. Run: playwright install chromium"
echo "4. Test: python scripts/test_all_sources.py --company 'Stripe' --title 'Software Engineer'"
echo ""
echo "See SETUP_CHECKLIST.md for detailed instructions."

