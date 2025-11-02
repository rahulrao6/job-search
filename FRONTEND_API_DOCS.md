# Frontend API Integration Guide

Complete guide for integrating the Job Search API with your React frontend.

## Base URL

```
http://localhost:8000  # Development
https://your-domain.com  # Production
```

All endpoints are prefixed with `/api/v1`

## Authentication

All authenticated endpoints require a JWT token from Supabase Auth in the Authorization header:

```
Authorization: Bearer <your-supabase-jwt-token>
```

## Endpoints

### 1. Health Check

**Endpoint:** `GET /api/v1/health`

**Auth:** Not required

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "sources": {...},
  "database": {...}
}
```

---

### 2. Get User Quota

**Endpoint:** `GET /api/v1/quota`

**Auth:** Required

**Response:**
```json
{
  "success": true,
  "data": {
    "tier": "free",
    "searches_per_month": 10,
    "searches_used_this_month": 5,
    "searches_remaining": 5,
    "rate_limit_per_minute": 5
  }
}
```

---

### 3. Get User Profile

**Endpoint:** `GET /api/v1/profile`

**Auth:** Required

**Response:**
```json
{
  "success": true,
  "data": {
    "profile": {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "linkedin_url": "https://linkedin.com/in/johndoe",
      "resume_url": "https://...",
      "skills": ["Python", "JavaScript"],
      "past_companies": ["Google", "Meta"],
      "schools": ["Stanford University"],
      "current_title": "Software Engineer",
      "years_experience": 5
    }
  }
}
```

---

### 4. Save User Profile

**Endpoint:** `POST /api/v1/profile/save`

**Auth:** Required

**Request Body:**
```json
{
  "profile": {
    "skills": ["Python", "Go", "JavaScript"],
    "past_companies": ["Google", "Meta"],
    "schools": ["Stanford University"],
    "current_title": "Senior Software Engineer",
    "years_experience": 5,
    "full_name": "John Doe",
    "linkedin_url": "https://linkedin.com/in/johndoe"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "profile_id": "uuid",
    "message": "Profile saved successfully"
  }
}
```

---

### 5. Upload Resume (PDF)

**Endpoint:** `POST /api/v1/resume/upload`

**Auth:** Required

**Content-Type:** `multipart/form-data`

**Request Body:**
- `file`: PDF file (max 10MB)

**OR** send JSON:

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "resume_url": "https://your-project.supabase.co/storage/v1/object/public/resumes/uuid/filename.pdf"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "resume_url": "https://...",
    "parsed_data": {
      "skills": ["Python", "Go", "Kubernetes"],
      "past_companies": ["Google", "Microsoft"],
      "schools": ["Stanford University", "MIT"],
      "current_title": "Senior Software Engineer",
      "years_experience": null
    },
    "message": "Resume uploaded and parsed successfully"
  }
}
```

**React Example:**
```javascript
const uploadResume = async (file, token) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/api/v1/resume/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return await response.json();
};
```

---

### 6. Parse Job URL

**Endpoint:** `POST /api/v1/job/parse`

**Auth:** Required

**Request Body:**
```json
{
  "job_url": "https://www.linkedin.com/jobs/view/1234567890"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_url": "https://...",
    "company": "Google",
    "company_domain": "google.com",
    "job_title": "Software Engineer - Infrastructure",
    "department": "Infrastructure Engineering",
    "location": "Mountain View, CA",
    "required_skills": ["Go", "Python", "Distributed Systems"],
    "job_description": "Looking for experienced engineers...",
    "seniority": "senior"
  }
}
```

**React Example:**
```javascript
const parseJob = async (jobUrl, token) => {
  const response = await fetch('http://localhost:8000/api/v1/job/parse', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ job_url: jobUrl })
  });
  
  return await response.json();
};
```

---

### 7. Search for Connections

**Endpoint:** `POST /api/v1/search`

**Auth:** Required

**Request Body (Minimal - API auto-loads resume and scrapes job):**
```json
{
  "company": "Google",
  "job_title": "Software Engineer",
  "job_url": "https://..."
}
```

**Request Body (Full control):**
```json
{
  "company": "Google",
  "job_title": "Software Engineer",
  "job_url": "https://...",
  "job_description": "Job description text...",
  "required_skills": ["Go", "Python"],
  "profile": {
    "skills": ["Python", "Go"],
    "past_companies": ["Meta"],
    "schools": ["Stanford"]
  },
  "filters": {
    "categories": ["recruiter", "manager"],
    "min_confidence": 0.7,
    "max_results": 20
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": {
      "company": "Google",
      "job_title": "Software Engineer"
    },
    "results": {
      "total_found": 30,
      "by_category": {
        "recruiter": [...],
        "manager": [...],
        "peer": [...]
      },
      "category_counts": {
        "recruiter": 5,
        "manager": 8,
        "peer": 17
      }
    },
    "insights": {
      "alumni_matches": 2,
      "ex_company_matches": 3,
      "skills_matches": 15
    },
    "quota": {
      "searches_remaining": 4,
      "searches_per_month": 10
    }
  }
}
```

**React Example:**
```javascript
const searchConnections = async (searchParams, token) => {
  const response = await fetch('http://localhost:8000/api/v1/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(searchParams)
  });
  
  return await response.json();
};
```

---

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Error Codes

- `AUTH_REQUIRED` (401) - Missing or invalid token
- `AUTH_INVALID` (401) - Invalid or expired token
- `INVALID_REQUEST` (400) - Invalid request parameters
- `RATE_LIMIT_EXCEEDED` (429) - Too many requests
- `QUOTA_EXCEEDED` (429) - Monthly quota exceeded
- `PARSING_ERROR` (500) - Error parsing resume or job
- `STORAGE_ERROR` (400) - Error with Supabase Storage
- `INTERNAL_SERVER_ERROR` (500) - Server error

---

## Recommended User Flow

### 1. Onboarding Flow

```javascript
// Step 1: User signs up (handled by Supabase Auth)
const user = await supabase.auth.signUp({ email, password });

// Step 2: Upload resume
const resumeData = await uploadResume(resumeFile, user.session.access_token);

// Step 3: User provides job URL
const jobData = await parseJob(jobUrl, user.session.access_token);

// Step 4: Search for connections
const results = await searchConnections({
  company: jobData.data.company,
  job_title: jobData.data.job_title,
  job_url: jobUrl
}, user.session.access_token);
```

### 2. Subsequent Searches

Once resume is uploaded, you can search with minimal data:

```javascript
const results = await searchConnections({
  company: "Google",
  job_title: "Software Engineer",
  job_url: "https://..."
}, token);
// API automatically uses saved resume data
```

---

## Rate Limiting

- Free tier: 5 requests per minute, 10 searches per month
- Basic tier: 10 requests per minute, 50 searches per month
- Pro tier: 20 requests per minute, 200 searches per month
- Enterprise: 50 requests per minute, unlimited searches

**Rate limit headers:**
- Check response for `429` status
- Error details include `reset_in_seconds`

---

## Best Practices

1. **Resume Upload**: Upload resume once during onboarding, then reuse saved data
2. **Job Parsing**: Parse job URL once, then reuse the parsed data
3. **Error Handling**: Always check `success` field in responses
4. **Token Management**: Store JWT token securely, refresh when expired
5. **Rate Limiting**: Implement client-side rate limiting to avoid 429 errors
6. **Loading States**: Show loading indicators for resume upload and job parsing (can take 5-15 seconds)

---

## Testing

Use the provided test script:

```bash
python test_api.py
```

Or test manually with curl:

```bash
# Upload resume
curl -X POST http://localhost:8000/api/v1/resume/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@resume.pdf"

# Parse job
curl -X POST http://localhost:8000/api/v1/job/parse \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_url": "https://..."}'

# Search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company": "Google", "job_title": "Engineer", "job_url": "https://..."}'
```

