# API UI Testing Guide

## Overview

Your Flask server now has **three interfaces** for testing:

1. **Simple HTML Form** (`/`) - Quick demo interface
2. **API Testing UI** (`/api-test`) - NEW! Interactive browser-based API testing
3. **REST API Endpoints** (`/api/v1/*`) - For your React frontend

## Quick Start

### 1. Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the Flask server
python web_app.py
```

Server starts at: **http://localhost:8000**

### 2. Access the Testing Interfaces

| Interface | URL | Purpose |
|-----------|-----|---------|
| Simple Search | http://localhost:8000/ | Quick search without auth |
| **API Testing UI** | http://localhost:8000/api-test | Test all API endpoints |
| Health Check | http://localhost:8000/api/v1/health | Direct API health |

## Using the API Testing UI

### Step 1: Open the Testing Interface

Navigate to: **http://localhost:8000/api-test**

You'll see a beautiful interface with sections for each API endpoint.

### Step 2: Get Your JWT Token

**Option A: From Your React Frontend**
1. Login to your React app
2. Open browser DevTools (F12)
3. Go to Application → Local Storage
4. Find `supabase.auth.token`
5. Copy the `access_token` value

**Option B: Direct Login via API**
```bash
curl -X POST 'https://YOUR_PROJECT.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "your_password"
  }'
```

Copy the `access_token` from the response.

### Step 3: Save Your Token in the UI

1. Scroll to the **Authentication Setup** section
2. Paste your JWT token
3. Click **💾 Save Token**

The token is saved in your browser's localStorage and will be used for all authenticated requests.

### Step 4: Test the Endpoints

#### Test 1: Health Check (No Auth Required)
- Scroll to **Health Check** section
- Click **🏥 Check Health**
- See the status of database and API sources

#### Test 2: Get Quota
- Click **📊 Get Quota**
- See your remaining searches and rate limits

#### Test 3: Get Profile
- Click **👤 Get Profile**
- View your saved profile data (skills, companies, schools)

#### Test 4: Save Profile
- Fill in your information:
  - Full Name
  - Current Title
  - Skills (comma-separated)
  - Past Companies (comma-separated)
  - Schools (comma-separated)
- Click **💾 Save Profile**
- Profile is saved to Supabase

#### Test 5: Search for Connections
- Enter **Company Name** (e.g., "Stripe")
- Enter **Job Title** (e.g., "Software Engineer")
- Optionally add **Advanced Options** as JSON:
  ```json
  {
    "profile": {
      "skills": ["Python", "Go"],
      "past_companies": ["Google"]
    },
    "filters": {
      "categories": ["recruiter", "manager"],
      "min_confidence": 0.7
    }
  }
  ```
- Click **🔍 Search Connections**
- See results with connections found

#### Test 6: Parse Job URL
- Enter a job posting URL
- Click **🔗 Parse Job**
- Get extracted job details (company, title, skills, etc.)

#### Test 7: Upload Resume
- Click **Choose File** and select a PDF resume
- Click **📄 Upload Resume**
- See parsed resume data (skills, companies, schools)

## Available API Endpoints

### Authentication Required

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/quota` | Get user quota info |
| GET | `/api/v1/profile` | Get saved profile |
| POST | `/api/v1/profile/save` | Save profile data |
| POST | `/api/v1/search` | Search for connections |
| POST | `/api/v1/resume/upload` | Upload & parse resume |
| POST | `/api/v1/job/parse` | Parse job posting URL |
| GET | `/api/v1/connections/<id>` | Get connection details |

### No Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/` | Simple search form |
| POST | `/search` | Simple search (form) |

## Response Format

All API responses follow this format:

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data here
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

## Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| `AUTH_REQUIRED` | No token provided | Add JWT token |
| `AUTH_INVALID` | Token is invalid/expired | Get new token |
| `INVALID_REQUEST` | Missing required fields | Check request body |
| `QUOTA_EXCEEDED` | Monthly quota used up | Wait for reset or upgrade |
| `RATE_LIMIT` | Too many requests | Wait 60 seconds |

## Example: Full Testing Workflow

```bash
# 1. Start server
python web_app.py

# 2. Open browser
http://localhost:8000/api-test

# 3. Set token (paste your JWT)

# 4. Test Health
Click "Check Health" → Should see "healthy" status

# 5. Get Quota
Click "Get Quota" → See searches remaining

# 6. Save Profile
Fill in: Name, Skills, Companies, Schools
Click "Save Profile"

# 7. Search
Company: "Stripe"
Job Title: "Software Engineer"
Advanced: {"profile": {"skills": ["Python"]}}
Click "Search Connections"

# 8. View Results
See JSON response with connections found
```

## Testing with cURL (Alternative)

If you prefer command line:

```bash
# Set your token
TOKEN="your-jwt-token-here"

# Health Check
curl http://localhost:8000/api/v1/health

# Get Quota
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/quota

# Search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Stripe",
    "job_title": "Software Engineer",
    "profile": {
      "skills": ["Python", "Go"],
      "past_companies": ["Google"]
    }
  }'
```

## Connecting Your React Frontend

Your React frontend should call the `/api/v1/*` endpoints:

```javascript
// Example: Search for connections
const response = await fetch('http://localhost:8000/api/v1/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${userToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    company: 'Stripe',
    job_title: 'Software Engineer',
    profile: {
      skills: ['Python', 'Go'],
      past_companies: ['Google']
    }
  })
});

const data = await response.json();
if (data.success) {
  console.log('Found connections:', data.data.results);
} else {
  console.error('Error:', data.error);
}
```

## Features of the API Testing UI

✅ **Visual Interface** - No need for curl commands
✅ **Token Management** - Save and reuse JWT tokens
✅ **JSON Responses** - Formatted and color-coded
✅ **Error Handling** - Clear error messages
✅ **All Endpoints** - Test every API route
✅ **Advanced Options** - Support for complex queries
✅ **File Upload** - Test resume upload
✅ **Responsive** - Works on mobile too

## Troubleshooting

### "Please set your JWT token first!"
- You need to paste a valid JWT token in the Authentication Setup section
- Click "Save Token" after pasting

### Token Expired
- JWT tokens expire after ~1 hour
- Get a new token from Supabase
- Update in the UI and click "Save Token"

### "Connection refused"
- Make sure Flask server is running: `python web_app.py`
- Check server is on port 8000: `http://localhost:8000`

### CORS Errors (from React)
- Check `.env` has `FRONTEND_URL=*` or your React URL
- Restart Flask server after changing .env

### "Profile not found"
- User must exist in Supabase Auth
- Profile is auto-created on first login
- Check Supabase Dashboard → Profiles table

## Next Steps

1. **Test All Endpoints** - Use the UI to test each endpoint
2. **Connect React Frontend** - Update your React app to call these APIs
3. **Deploy** - Both Flask backend and React frontend
4. **Monitor** - Check quota usage and API health

## Need Help?

- Check `RUN_COMMANDS.md` for detailed curl examples
- See `src/api/routes.py` for endpoint implementations
- Review `test_api.py` for programmatic testing examples

---

**Happy Testing! 🎉**

The UI testing interface makes it easy to test all your API endpoints without writing any code. Just paste your token and click buttons!

