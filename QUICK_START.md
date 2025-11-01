# ⚡ Quick Start - Web Interface

## For You (Testing & Building)

### Option 1: Test Locally (Quickest)
```bash
python web_app.py
```
Then open: http://localhost:8000

**Note**: Using port 8000 because macOS AirPlay uses port 5000

### Option 2: Deploy to Render.com (Browser-Only, Free)
See [RENDER_SETUP.md](RENDER_SETUP.md) for full instructions.

**Super Quick Version:**
1. Push code to GitHub
2. Go to render.com → Sign up (free, no CC)
3. New Web Service → Connect GitHub repo
4. Add environment variables (optional)
5. Click "Create Web Service"
6. Share the URL!

## For Your Friends (Using It)

Just send them the URL! They don't need to:
- Install anything
- Have API keys
- Know how to code
- Use the terminal

They just:
1. Visit the URL
2. Enter company name + job title
3. Get connections!

## What It Does

Finds people you can reach out to for referrals:
- **Recruiters** - Can directly refer you
- **Managers** - Make hiring decisions  
- **Seniors** - Have influence
- **Peers** - Provide insider info

All with LinkedIn URLs for easy outreach!

## API Keys (Optional)

The app works WITHOUT API keys using:
- Demo data (for testing)
- GitHub public profiles
- Free web scrapers

Add keys for better results:
- `OPENAI_API_KEY` - Enhances data quality
- `APOLLO_API_KEY` - Gets more LinkedIn profiles (10k free/month)
- `SERP_API_KEY` - Backup search (can skip this)

## After Testing

When the "real" app is built by your team:
- Keep the Render deployment for quick testing
- Or integrate the backend into your production app

This is a simple test interface - perfect for validating the backend works!

## Why Render Over Replit?

- ✅ **Free tier doesn't require payment** to publish/share
- ✅ **Auto-deploys** from GitHub (no manual work)
- ✅ **More reliable** for web apps
- ✅ **Professional platform** used by real companies

Replit is great for learning, but Render is better for sharing working apps!

