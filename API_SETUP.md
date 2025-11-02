# API Setup and Usage Guide

## Overview

This backend provides a REST API for finding job referral connections with profile-based matching and Supabase integration.

## Environment Variables

Add these to your `.env` file:

```bash
# Supabase (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Existing API Keys
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...
OPENAI_API_KEY=...
GITHUB_TOKEN=...

# Frontend (for CORS)
FRONTEND_URL=https://your-frontend.com  # or "*" for all origins

# API Key Secret (for generating keys)
API_KEY_SECRET=your-secret-here
```

## Database Setup

Run the SQL migration in `src/db/migrations.sql` in your Supabase SQL editor to create:
- `api_keys` table
- `search_history` table (optional)
- Indexes for performance

## Creating API Keys

To create an API key for a user:

```python
from uuid import UUID
from src.services.api_key_service import create_api_key_for_user

user_id = UUID("user-uuid-from-profiles-table")
full_key, key_record = create_api_key_for_user(user_id, tier='free')

# Show full_key to user ONCE - store it securely
# Store key_record in database
```

## API Endpoints

### Base URL
`https://your-domain.com/api/v1`

### Authentication
All endpoints (except `/health`) require an API key:

```bash
Authorization: Bearer <your-api-key>
```

Or use header:
```bash
X-API-Key: <your-api-key>
```

### Endpoints

#### POST /api/v1/search
Main search endpoint with profile context.

**Request:**
```json
{
  "company": "Stripe",
  "job_title": "Software Engineer",
  "profile": {
    "skills": ["Python", "Go"],
    "past_companies": ["Google"],
    "schools": ["Stanford University"]
  },
  "filters": {
    "categories": ["recruiter", "manager"],
    "min_confidence": 0.7
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "search_id": "...",
    "query": {...},
    "results": {
      "total_found": 45,
      "by_category": {...},
      "category_counts": {...}
    },
    "insights": {
      "alumni_matches": 5,
      "ex_company_matches": 2,
      "skills_matches": 15
    },
    "timing": {...},
    "cost": {...},
    "quota": {...}
  }
}
```

#### GET /api/v1/health
Health check (no auth required).

#### GET /api/v1/quota
Get remaining quota for API key.

#### GET /api/v1/connections/:id
Get details for a specific connection.

#### GET /api/v1/profile
Get saved user profile.

#### POST /api/v1/profile/save
Save user profile.

## Rate Limiting Tiers

- **Free**: 10 searches/month, 5/minute
- **Basic**: 50 searches/month, 10/minute
- **Pro**: 200 searches/month, 20/minute
- **Enterprise**: Unlimited, 50/minute

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

Common error codes:
- `API_KEY_MISSING` (401)
- `API_KEY_INVALID` (401)
- `QUOTA_EXCEEDED` (429)
- `RATE_LIMIT_EXCEEDED` (429)
- `INVALID_REQUEST` (400)
- `NOT_FOUND` (404)
- `INTERNAL_SERVER_ERROR` (500)

## Testing

Test the health endpoint:
```bash
curl https://your-domain.com/api/v1/health
```

Test search with API key:
```bash
curl -X POST https://your-domain.com/api/v1/search \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Stripe",
    "job_title": "Software Engineer"
  }'
```

