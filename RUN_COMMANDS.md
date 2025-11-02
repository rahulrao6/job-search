# Commands to Run and Test the API

## Initial Setup

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the root directory:

```bash
# Supabase (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Existing API Keys
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id
OPENAI_API_KEY=your_openai_key
GITHUB_TOKEN=your_github_token  # Optional

# Frontend (for CORS)
FRONTEND_URL=*  # or your frontend URL

# Server
PORT=8000  # Optional, defaults to 8000
```

## Running the Server

### Development Mode (Flask)

```bash
# Activate virtual environment first
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run Flask development server
python web_app.py
```

Server will start at: `http://localhost:8000`

### Production Mode (Gunicorn)

```bash
# Activate virtual environment
source venv/bin/activate

# Run with Gunicorn (recommended for production)
gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120 web_app:app
```

### With Environment Variables

```bash
# Set PORT from environment
export PORT=8000
python web_app.py

# Or inline:
PORT=8000 python web_app.py
```

## Testing with cURL

### Prerequisites

Before testing, you need:
1. A user account in Supabase Auth
2. A JWT token from that user

**Get JWT Token:**
- Option 1: From your frontend after login
- Option 2: Use Supabase Auth API to sign in:

```bash
curl -X POST 'https://YOUR_PROJECT.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

The response will contain `access_token` - use that as `<YOUR_TOKEN>` below.

### 1. Health Check (No Auth Required)

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "sources": {...},
  "database": {...}
}
```

### 2. Search for Connections (Requires Auth)

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Stripe",
    "job_title": "Software Engineer",
    "profile": {
      "skills": ["Python", "Go"],
      "past_companies": ["Google"],
      "schools": ["Stanford University"]
    }
  }'
```

**With more options:**
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Meta",
    "job_title": "Backend Engineer",
    "department": "Engineering",
    "location": "Menlo Park, CA",
    "profile": {
      "skills": ["Python", "JavaScript", "React"],
      "past_companies": ["Google", "Microsoft"],
      "schools": ["MIT", "Stanford University"],
      "current_title": "Senior Software Engineer",
      "years_experience": 5
    },
    "filters": {
      "categories": ["recruiter", "manager"],
      "min_confidence": 0.7,
      "max_results": 50
    }
  }'
```

### 3. Get User Quota

```bash
curl http://localhost:8000/api/v1/quota \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Expected response:
```json
{
  "success": true,
  "data": {
    "tier": "free",
    "searches_per_month": 10,
    "searches_used_this_month": 3,
    "searches_remaining": 7,
    "rate_limit_per_minute": 5
  }
}
```

### 4. Get User Profile

```bash
curl http://localhost:8000/api/v1/profile \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Save User Profile

```bash
curl -X POST http://localhost:8000/api/v1/profile/save \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": {
      "skills": ["Python", "Go", "Kubernetes"],
      "past_companies": ["Google", "Meta"],
      "schools": ["Stanford University"],
      "current_title": "Senior Software Engineer",
      "years_experience": 5,
      "full_name": "John Doe",
      "linkedin_url": "https://linkedin.com/in/johndoe"
    }
  }'
```

### 6. Get Connection Details

```bash
# First, run a search to get a connection_id from results
# Then use that ID:
curl http://localhost:8000/api/v1/connections/CONNECTION_ID_HERE \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 7. Test HTML Routes (Backward Compatibility)

```bash
# Home page
curl http://localhost:8000/

# Search form submission (form data)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "company=Stripe&role=Software+Engineer"
```

## Testing Script

Create a test script `test_api.sh`:

```bash
#!/bin/bash

# Set your token here
TOKEN="YOUR_JWT_TOKEN_HERE"
BASE_URL="http://localhost:8000"

echo "Testing Health Endpoint..."
curl -s "$BASE_URL/api/v1/health" | jq .

echo -e "\n\nTesting Search Endpoint..."
curl -s -X POST "$BASE_URL/api/v1/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Stripe",
    "job_title": "Software Engineer"
  }' | jq .

echo -e "\n\nTesting Quota Endpoint..."
curl -s "$BASE_URL/api/v1/quota" \
  -H "Authorization: Bearer $TOKEN" | jq .

echo -e "\n\nTesting Profile Endpoint..."
curl -s "$BASE_URL/api/v1/profile" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Make it executable:
```bash
chmod +x test_api.sh
./test_api.sh
```

## Production Deployment

### Render.com

```bash
# Build command:
pip install --upgrade pip && pip install -r requirements.txt

# Start command:
gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 web_app:app
```

### Docker

```bash
# Build
docker build -t job-search-api .

# Run
docker run -p 8000:8000 --env-file .env job-search-api
```

## Common Issues

### "Module not found"
```bash
pip install -r requirements.txt
```

### "SUPABASE_URL not set"
Make sure `.env` file exists with all required variables.

### "Auth token invalid"
- Token may have expired (tokens expire after ~1 hour)
- Get a fresh token from Supabase Auth
- Make sure you're using the `access_token`, not `refresh_token`

### "Rate limit exceeded"
- Wait 60 seconds
- Check your subscription tier in database
- Upgrade tier if needed

### "Quota exceeded"
- Check `searches_used_this_month` in `profiles` table
- Reset monthly usage or upgrade tier

## Database Setup

Before running, make sure to:

1. **Run migrations** in Supabase SQL Editor:
   ```sql
   -- Copy contents of src/db/migrations.sql
   -- Paste and run in Supabase SQL Editor
   ```

2. **Create a test user** in Supabase Auth:
   - Go to Supabase Dashboard → Authentication
   - Create user manually or use signup endpoint

3. **Verify profile exists**:
   ```sql
   SELECT * FROM profiles WHERE id = 'user-uuid';
   ```

## Quick Test Checklist

- [ ] Dependencies installed
- [ ] `.env` file configured
- [ ] Database migrations run
- [ ] Test user created in Supabase Auth
- [ ] JWT token obtained
- [ ] Health endpoint works
- [ ] Search endpoint works with token
- [ ] Quota endpoint works

## Useful Commands

```bash
# Check if server is running
curl http://localhost:8000/api/v1/health

# Check Python version
python --version

# List installed packages
pip list

# Update a package
pip install --upgrade package-name

# View server logs
# If running with gunicorn, logs go to stdout/stderr
# If running with Flask, logs appear in terminal
```

