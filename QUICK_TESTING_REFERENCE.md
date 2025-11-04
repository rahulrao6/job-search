# 🚀 Quick Testing Reference

## Start Server
```bash
cd /Users/rahulrao/job-search
source venv/bin/activate
python web_app.py
```

## URLs

| Interface | URL | Auth Required |
|-----------|-----|---------------|
| **API Testing UI** 🧪 | http://localhost:8000/api-test | ✅ JWT Token |
| Simple Search | http://localhost:8000/ | ❌ No |
| Health Check | http://localhost:8000/api/v1/health | ❌ No |

## Quick Test Flow

1. **Open Testing UI:** http://localhost:8000/api-test
2. **Paste JWT Token** (get from Supabase)
3. **Click "Save Token"**
4. **Test endpoints** by clicking buttons

## Get JWT Token Fast

```bash
# Replace with your Supabase credentials
curl -X POST 'https://YOUR_PROJECT.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "your_password"}'
```

Copy the `access_token` from response.

## Test Endpoints via cURL

```bash
# Set your token
export TOKEN="your-jwt-token"

# Health (no auth)
curl http://localhost:8000/api/v1/health | jq .

# Quota
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/quota | jq .

# Search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company": "Stripe", "job_title": "Software Engineer"}' | jq .
```

## All API Endpoints

| Endpoint | Method | Auth | Try It |
|----------|--------|------|--------|
| `/api/v1/health` | GET | ❌ | Health section |
| `/api/v1/quota` | GET | ✅ | Quota button |
| `/api/v1/profile` | GET | ✅ | Get Profile |
| `/api/v1/profile/save` | POST | ✅ | Save form |
| `/api/v1/search` | POST | ✅ | Search form |
| `/api/v1/resume/upload` | POST | ✅ | Upload file |
| `/api/v1/job/parse` | POST | ✅ | Parse job |

## Response Format

✅ **Success:**
```json
{
  "success": true,
  "data": { ... }
}
```

❌ **Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "..."
  }
}
```

## Common Issues

| Problem | Solution |
|---------|----------|
| Token expired | Get new token (expires ~1hr) |
| Port in use | `lsof -ti:8000 \| xargs kill -9` |
| Server not starting | Check `.env` file exists |
| CORS errors | Set `FRONTEND_URL=*` in `.env` |

## What's Available

✅ **Old Interface** (/) - Simple search form (no auth)
✅ **New Interface** (/api-test) - Full API testing UI
✅ **REST APIs** (/api/v1/*) - For React frontend

## Next Steps

1. Test all endpoints via UI: http://localhost:8000/api-test
2. Connect your React frontend to `/api/v1/*` endpoints
3. Deploy both backend and frontend

---

**Need detailed help?** See `NEW_UI_TESTING_SUMMARY.md` or `API_UI_TESTING_GUIDE.md`

