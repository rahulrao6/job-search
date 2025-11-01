# ✅ Testing Instructions

## Flask App is Running!

The web app is currently running at: **http://localhost:8000**

## Test It Now

1. **Open in Browser**: http://localhost:8000
2. **Enter Test Data**:
   - Company: `Google`
   - Job Title: `Software Engineer`
3. **Click "Find Connections"**
4. **Verify Results**:
   - Should see Recruiters (Sarah Chen, Mike Johnson, etc.)
   - Should see Managers (Emily Zhang, David Park, etc.)
   - Should see GitHub profiles
   - Each with LinkedIn URLs you can click

## What You Should See

### Demo Data (Always Works)
- 5 sample profiles from DemoScraper
- Recruiters, managers with fake but realistic LinkedIn URLs
- Perfect for testing the UI

### GitHub Data (If Company Has Public Org)
- Real GitHub profiles
- Engineers, developers from public repos
- Some may not have LinkedIn URLs (that's normal)

### API Data (If You Added Keys)
- Apollo results (if APOLLO_API_KEY in .env)
- SERP results (if SERP_API_KEY in .env)
- More comprehensive results

## Test Different Companies

Try these to see different results:
- **Google**: Gets demo data + GitHub profiles
- **Amazon**: Gets demo data (no public GitHub)
- **Microsoft**: Gets demo data + GitHub profiles
- **Apple**: Gets demo data + GitHub profiles
- **Stripe**: Gets demo data (smaller company)

## If It's Not Working

### Check the logs:
```bash
tail -f /tmp/flask_app.log
```

### Common Issues:
1. **Port 8000 in use**: Kill with `lsof -ti:8000 | xargs kill -9`
2. **Import errors**: Make sure you're in the right directory
3. **No results**: That's okay! Try a big tech company

## Stop the Server

When done testing:
```bash
# Find the process
ps aux | grep web_app.py

# Kill it
kill [process_id]
```

Or just close the terminal window.

## Next Steps: Deploy to Render.com

Once you've verified it works locally:

1. **Commit and push to GitHub**:
   ```bash
   git add .
   git commit -m "Add Flask web interface"
   git push origin main
   ```

2. **Go to Render.com**:
   - Sign up free at render.com (no credit card needed)
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your `job-search` repository
   - Configure:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `python web_app.py`
     - Plan: FREE
   - Add API keys in Environment Variables (optional)
   - Click "Create Web Service"

3. **Share the URL**:
   - Wait 2-3 minutes for build
   - Copy the Render URL (e.g., https://job-referral-finder.onrender.com)
   - Send to friends
   - They can use it immediately!

See [RENDER_SETUP.md](RENDER_SETUP.md) for detailed deployment instructions.

## Local Development

Want to keep testing locally as you build?

1. Keep the Flask app running
2. Make changes to `src/` files
3. Restart: `python web_app.py`
4. Refresh browser to see changes

The web interface makes it way easier to test than using the terminal!

## Why Render Instead of Replit?

- ✅ **Free tier actually lets you publish/share** (Replit requires payment)
- ✅ **Auto-deploys from GitHub** (every push updates your app)
- ✅ **More reliable** for production-like testing
- ✅ **Professional platform** (used by real companies)

