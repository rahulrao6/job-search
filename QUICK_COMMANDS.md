# Quick Command Reference

## Setup (One Time)

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with:
# SUPABASE_URL=...
# SUPABASE_KEY=...
# GOOGLE_API_KEY=...
# GOOGLE_CSE_ID=...
# OPENAI_API_KEY=...
```

## Run Server

```bash
# Development
python web_app.py

# Production
gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120 web_app:app
```

## Test Commands (Replace YOUR_TOKEN with actual JWT)

### 1. Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### 2. Search (Main Endpoint)
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company": "Stripe", "job_title": "Software Engineer"}'
```

### 3. Get Quota
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/quota
```

### 4. Get Profile
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/profile
```

### 5. Save Profile
```bash
curl -X POST http://localhost:8000/api/v1/profile/save \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"profile": {"skills": ["Python"], "past_companies": ["Google"]}}'
```

## Get JWT Token

From your Supabase Auth (frontend) or:
```bash
curl -X POST 'https://YOUR_PROJECT.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

