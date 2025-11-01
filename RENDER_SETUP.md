# 🚀 Deploy to Render.com (FREE)

## Why Render?
- **Completely FREE tier** (no credit card needed)
- Auto-deploys from GitHub
- Simple setup (2 minutes)
- More reliable than Replit for free tier
- Professional deployment platform

## Step-by-Step Deployment

### 1. Push Your Code to GitHub
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Sign Up for Render
- Go to [render.com](https://render.com)
- Sign up with GitHub (free account)
- **No credit card required for free tier**

### 3. Create New Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub account (if not already)
3. Select your `job-search` repository
4. Render auto-detects it's Python!

### 4. Configure the Service
**On the setup page:**
- **Name**: `job-referral-finder` (or whatever you want)
- **Region**: Choose closest to you (e.g., Oregon for US West)
- **Branch**: `main`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python web_app.py`
- **Plan**: **FREE** ⚡ (select this!)

### 5. Add Environment Variables
Click **"Advanced"** → **"Add Environment Variable"**

Add these (only the ones you have):
- `OPENAI_API_KEY` = your-openai-key
- `APOLLO_API_KEY` = your-apollo-key (optional)
- `SERP_API_KEY` = your-serp-key (optional)

**Note**: The app works without API keys using demo data and GitHub profiles!

### 6. Deploy!
- Click **"Create Web Service"**
- Wait 2-3 minutes for build
- You'll get a URL like: `https://job-referral-finder.onrender.com`

### 7. Share with Friends
Copy your Render URL and send to friends - they can use it immediately!

## Important Notes

### Free Tier Limitations
- **Spins down after 15 min of inactivity**
- Takes ~30 seconds to wake up when someone visits (first request is slow)
- Perfect for testing and sharing with friends!
- Want it always-on? Upgrade to paid tier ($7/month)

### Auto-Deploy
Every time you push to GitHub, Render **automatically deploys** your changes!
- No need to manually redeploy
- Check "Logs" tab to see deployment progress

### Viewing Logs
- Click on your service in Render dashboard
- Click "Logs" tab
- See real-time logs (useful for debugging)

## Troubleshooting

### Build Fails?
**Check:**
- `requirements.txt` exists and has Flask
- `web_app.py` exists in root directory
- Build command is correct: `pip install -r requirements.txt`

**View logs** in Render dashboard to see exact error.

### App Won't Start?
**Check:**
1. Start command is `python web_app.py`
2. `web_app.py` doesn't have syntax errors
3. Environment variables are set correctly (if using API keys)

**View logs** for the actual error message.

### App is Slow on First Load?
**This is normal!** Free tier spins down after 15 min idle.
- First request wakes it up (~30 seconds)
- Subsequent requests are fast
- If you need always-on, upgrade to $7/month

### Getting "Application Error"?
1. Check logs in Render dashboard
2. Make sure port is read from environment: `PORT = int(os.environ.get('PORT', 8000))`
3. Check that Flask app uses that port
4. Ensure `0.0.0.0` is used for host (not `localhost`)

## Cost Breakdown

### Free Tier (Perfect for Testing)
- **Cost**: $0/month
- **Limits**: 
  - 750 hours/month (25 days of runtime)
  - Spins down after 15 min idle
  - 512 MB RAM
  - Shared CPU
- **Perfect for**: Testing, sharing with friends, low-traffic apps

### Paid Tier (If Needed)
- **Cost**: $7/month
- **Benefits**:
  - Always-on (no spin down)
  - More RAM (512 MB - 16 GB options)
  - Faster CPU
  - Custom domains
- **When to upgrade**: Lots of users, need always-on

## Next Steps

Once deployed:
1. ✅ Test the URL yourself
2. ✅ Share with friends
3. ✅ Monitor logs for any errors
4. ✅ Every git push auto-deploys!

## Render vs Replit

| Feature | Render | Replit |
|---------|--------|--------|
| Free Tier | Yes, no CC needed | Limited, needs payment to publish |
| Auto-Deploy | ✅ Yes | ❌ No |
| Custom Domain | ✅ Yes (paid) | ✅ Yes (paid) |
| Always-On | ⚡ $7/month | 💰 Expensive |
| Professional | ✅ Yes | ❌ Education-focused |

**Winner**: Render for production/sharing apps! 🏆

