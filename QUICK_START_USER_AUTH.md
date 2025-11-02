# Quick Start: Simple User Authentication

## What Changed

✅ **No API keys needed!** Users just sign up and log in through your frontend.

✅ **Automatic usage tracking** per user with rate limiting and quotas.

✅ **Simple integration** - Frontend sends JWT token, backend validates it.

## Setup Steps

### 1. Run Database Migration

Run `src/db/migrations.sql` in your Supabase SQL editor. This adds:
- `subscription_tier` to `profiles` table (default: 'free')
- `searches_used_this_month` to `profiles` table
- `search_history` table for analytics

### 2. Frontend Integration

Your React frontend should already be using Supabase Auth. Just send the token:

```javascript
// Get token from Supabase session
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token

// Make API request
const response = await fetch('https://your-backend.com/api/v1/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    company: 'Stripe',
    job_title: 'Software Engineer',
    profile: {
      skills: ['Python', 'Go'],
      past_companies: ['Google'],
      schools: ['Stanford']
    }
  })
})
```

### 3. Testing

**Test with a real user:**
1. Sign up/login in your frontend
2. Get the JWT token from Supabase session
3. Use it in API requests

**Or test with curl:**
```bash
# Get token from frontend first, then:
curl -X POST https://your-backend.com/api/v1/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company": "Stripe", "job_title": "Engineer"}'
```

## Rate Limits (Per User)

- **Free**: 10 searches/month, 5/minute
- **Basic**: 50 searches/month, 10/minute
- **Pro**: 200 searches/month, 20/minute
- **Enterprise**: Unlimited, 50/minute

## Upgrading User Tiers

```python
from uuid import UUID
from src.services.user_service import UserService

user_id = UUID("user-uuid")
UserService.update_subscription_tier(user_id, 'pro')
```

## How It Works

1. User signs up → Supabase Auth creates user
2. User logs in → Gets JWT token
3. Frontend sends token → `Authorization: Bearer <token>`
4. Backend validates token → Gets `user_id`
5. Backend checks rate limits & quota → Per user_id
6. Request processed → Usage incremented automatically

That's it! No API keys, no complexity. Users just use your app.

