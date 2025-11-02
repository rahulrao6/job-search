# Simple User Authentication Setup

## Overview

Users sign up and log in through your frontend using Supabase Auth. No API keys needed! The backend validates their JWT tokens automatically.

## How It Works

1. **User signs up/logs in** via your frontend (Supabase Auth handles this)
2. **Frontend gets JWT token** from Supabase Auth
3. **Frontend sends requests** with token: `Authorization: Bearer <token>`
4. **Backend validates token** and tracks usage per user
5. **Rate limiting & quotas** are enforced per user automatically

## Database Changes

Run the migration in `src/db/migrations.sql` to add:
- `subscription_tier` column to `profiles` table (default: 'free')
- `searches_used_this_month` column to `profiles` table
- `search_history` table for analytics

## Subscription Tiers

- **Free**: 10 searches/month, 5/minute
- **Basic**: 50 searches/month, 10/minute  
- **Pro**: 200 searches/month, 20/minute
- **Enterprise**: Unlimited, 50/minute

## Frontend Integration

### 1. Sign Up (Frontend)
```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123'
})

// Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
})

// Get token
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token
```

### 2. Make API Requests (Frontend)
```javascript
const token = session?.access_token

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

const data = await response.json()
```

## Updating User Subscription

To upgrade a user's subscription tier:

```python
from uuid import UUID
from src.services.user_service import UserService

user_id = UUID("user-uuid")
UserService.update_subscription_tier(user_id, 'pro')
```

## Testing

### Test Health Endpoint (No Auth)
```bash
curl https://your-backend.com/api/v1/health
```

### Test Search Endpoint (Requires Auth)
1. Get token from Supabase Auth (frontend)
2. Use in request:

```bash
curl -X POST https://your-backend.com/api/v1/search \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Stripe",
    "job_title": "Software Engineer"
  }'
```

### Test Quota Endpoint
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-backend.com/api/v1/quota
```

## Error Responses

- `AUTH_REQUIRED` (401): No token provided
- `AUTH_INVALID` (401): Invalid/expired token
- `QUOTA_EXCEEDED` (429): Monthly limit reached
- `RATE_LIMIT_EXCEEDED` (429): Too many requests per minute

## Environment Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key  # Same as frontend
FRONTEND_URL=https://your-frontend.com
```

That's it! Users just sign up and use the app. No API keys, no complexity.

