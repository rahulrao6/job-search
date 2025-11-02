# 🚀 Job Referral Connection Finder - Integration Guide

## Executive Summary

This service helps users find the right people to connect with at target companies for job referrals. It aggregates data from multiple sources, validates results, and categorizes people by seniority - all while keeping costs near $0 through smart use of free APIs.

**Key Benefits:**
- ✅ 20-100+ relevant contacts per search
- ✅ Smart categorization (Manager, Recruiter, Peer, etc.)
- ✅ Cost: Usually $0 (free API usage)
- ✅ Response time: 10-25 seconds (optimized for 30s timeout)
- ✅ 95%+ accuracy after validation

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web UI/API    │────▶│  Orchestrator   │────▶│ Data Sources    │
│  (Flask/REST)   │     │  (Waterfall)    │     │ (Free → Paid)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Processing    │
                        │ • Deduplication │
                        │ • Validation    │
                        │ • Enhancement   │
                        └─────────────────┘
```

### Data Flow

1. **Input**: Company name + Job title
2. **Search Phase**: 
   - Free sources first (Google CSE, GitHub API)
   - Paid sources only if < 20 results
3. **Processing**:
   - Aggregate & deduplicate
   - Validate (remove false positives)
   - Enhance with OpenAI
   - Categorize by seniority
4. **Output**: Categorized list of people with metadata

## Integration Options

### Option 1: Deploy as Standalone Service

**Best for:** Teams wanting a ready-to-use solution

```bash
# Deploy to Render.com (FREE)
1. Fork repo to your GitHub
2. Connect to Render.com
3. Add API keys as environment variables
4. Deploy with one click
```

**Access Methods:**
- Web UI: `https://your-app.onrender.com`
- REST API: `POST https://your-app.onrender.com/api/search`

### Option 2: Integrate Core Library

**Best for:** Teams with existing Python applications

```python
# Install (add to requirements.txt)
git+https://github.com/yourusername/job-search.git

# Use in your code
from src.core.orchestrator import ConnectionFinder

finder = ConnectionFinder()
results = finder.find_connections(
    company="Stripe",
    title="Software Engineer"
)
```

### Option 3: REST API Integration

**Best for:** Non-Python applications

```javascript
// JavaScript Example
const response = await fetch('https://your-app.onrender.com/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        company: 'Stripe',
        title: 'Software Engineer'
    })
});

const data = await response.json();
console.log(`Found ${data.total_found} people`);
```

## API Reference

### Web Endpoints

#### `GET /` - Web Interface
Returns the search form UI

#### `POST /search` - Web Search
Form submission endpoint for web UI

#### `POST /api/search` - REST API

**Request:**
```json
{
    "company": "Stripe",
    "title": "Software Engineer",
    "use_cache": true  // Optional, default: true
}
```

**Response:**
```json
{
    "company": "Stripe",
    "title": "Software Engineer", 
    "total_found": 45,
    "by_category": {
        "manager": [
            {
                "name": "John Doe",
                "title": "Engineering Manager",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "source": "google_cse",
                "confidence": 0.95
            }
        ],
        "recruiter": [...],
        "senior": [...],
        "peer": [...],
        "unknown": [...]
    },
    "category_counts": {
        "manager": 5,
        "recruiter": 2,
        "senior": 8,
        "peer": 28,
        "unknown": 2
    },
    "source_stats": {
        "google_cse": 25,
        "github": 20
    },
    "cost_stats": {
        "total_cost": 0.00,
        "by_source": {
            "google_cse": 0.00,
            "github": 0.00
        }
    }
}
```

### Python API

```python
from src.core.orchestrator import ConnectionFinder

# Initialize
finder = ConnectionFinder()

# Basic search
results = finder.find_connections(
    company="Stripe",
    title="Software Engineer"
)

# Advanced search
results = finder.find_connections(
    company="Stripe",
    title="Software Engineer",
    company_domain="stripe.com",  # Optional: helps with company pages
    use_cache=False,              # Force fresh search
    debug=True                    # Show detailed logs
)

# Access results
people = results['by_category']['manager']
for person in people:
    print(f"{person['name']} - {person['title']}")
    print(f"LinkedIn: {person['linkedin_url']}")
    print(f"Confidence: {person['confidence']}")
```

## Configuration

### Required API Keys

1. **Google Custom Search Engine** (FREE - 100/day)
   ```bash
   GOOGLE_API_KEY=AIza...
   GOOGLE_CSE_ID=017643...
   ```
   Setup: [GOOGLE_CSE_QUICKSTART.md](GOOGLE_CSE_QUICKSTART.md)

2. **GitHub Token** (FREE - 5000/hour) 
   ```bash
   GITHUB_TOKEN=ghp_...
   ```
   Create at: https://github.com/settings/tokens

3. **OpenAI API** (For categorization)
   ```bash
   OPENAI_API_KEY=sk-...
   ```

### Optional API Keys (Backup Sources)

```bash
SERP_API_KEY=...      # SerpAPI (paid backup)
APOLLO_API_KEY=...    # Apollo.io (paid backup)
```

### Configuration File

Create `config/config.yaml`:
```yaml
sources:
  elite_free:
    enabled: true
  google_serp:
    enabled: false  # Enable if you have API key
  apollo:
    enabled: false  # Enable if you have API key

rate_limits:
  google_cse: 100  # per day
  github: 5000     # per hour with token

cache:
  ttl: 3600  # 1 hour
```

## Data Sources & Quality

### Source Hierarchy

1. **Google Custom Search Engine** (Quality: 0.85)
   - Returns LinkedIn profiles directly
   - 100 searches/day FREE
   - High quality results

2. **GitHub API** (Quality: 0.7)
   - Great for tech companies
   - 5000 requests/hour with token
   - Returns GitHub profiles

3. **Company Websites** (Quality: 0.6)
   - Direct from source
   - Limited coverage

4. **SerpAPI** (Quality: 1.0) - Paid backup
   - Best quality LinkedIn data
   - Only used if free sources < 20 results

5. **Apollo.io** (Quality: 0.95) - Paid backup
   - Professional database
   - 50 free credits/month

### Validation Rules

The system automatically filters out:
- ❌ Past employees (keywords: "former", "ex-", "previously")
- ❌ Company name matches (e.g., "Stripe" as person name)
- ❌ Missing critical info (no name or LinkedIn URL)
- ❌ Different company mentions in title
- ❌ Spam profiles (multiple spam indicators)

## Performance & Scaling

### Expected Performance

| Company Size | Results | Free Sources | Cost | Time |
|-------------|---------|--------------|------|------|
| Small (<100 employees) | 15-30 | ✅ Sufficient | $0 | 10-20s |
| Medium (100-1000) | 30-60 | ✅ Sufficient | $0 | 15-25s |
| Large (1000+) | 60-100+ | ✅ Usually sufficient | $0 | 20-25s |

**Note**: All searches are optimized to complete within Render's 30-second timeout limit.

### Rate Limits

- Google CSE: 100 searches/day
- GitHub: 60/hour (no auth), 5000/hour (with token)
- OpenAI: Based on your tier
- No rate limits on internal processing

### Scaling Considerations

1. **Horizontal Scaling**: Deploy multiple instances
2. **Caching**: Results cached for 1 hour by default
3. **API Keys**: Can use multiple Google CSE engines
4. **Database**: Can add PostgreSQL for persistent cache

## Deployment Guide

### Quick Deploy to Render.com (Recommended)

1. **Fork the repository** to your GitHub

2. **Sign up** at [render.com](https://render.com) (FREE)

3. **Create Web Service**:
   - Connect GitHub repo
   - Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 web_app:app`

4. **Add Environment Variables**:
   - All API keys from Configuration section
   - Render will provide PORT automatically

5. **Deploy** - Takes ~2 minutes

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "web_app:app"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: job-search-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: job-search-api
  template:
    metadata:
      labels:
        app: job-search-api
    spec:
      containers:
      - name: api
        image: your-registry/job-search-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: google-api-key
        # ... other secrets
```

## Monitoring & Debugging

### Logs to Watch

```python
# Success indicators
"🚀 Elite free sources loaded"
"📊 Free sources found: 45 people"
"✅ Sufficient results from free sources!"

# Warning indicators  
"⚠️ Free sources not configured"
"⚠️ Rate limited"
"💳 Phase 2: Premium Sources"  # Using paid APIs
```

### Common Issues

1. **Timeout/502 after 30 seconds**
   - This is Render's 30-second HTTP limit (free tier)
   - Our system is optimized to complete within 25 seconds
   - If persistent: Check API response times, reduce search scope

2. **No results returned**
   - Check: Are API keys configured?
   - Check: Daily limits exceeded?
   - Solution: Add GitHub token for better limits

3. **Few results for small companies**
   - Expected for companies < 50 employees
   - Solution: Try broader job title

4. **502 Bad Gateway on Render (immediate)**
   - Check: Is gunicorn installed?
   - Check: Build logs for errors

## Security Considerations

1. **API Key Management**
   - Use environment variables
   - Never commit keys to repo
   - Rotate keys regularly

2. **Rate Limiting**
   - Built-in rate limiting per source
   - Prevents API abuse

3. **Input Validation**
   - Company and title sanitized
   - SQL injection protected

4. **CORS** (if enabling API access)
   ```python
   from flask_cors import CORS
   CORS(app, origins=['https://yourapp.com'])
   ```

## Cost Analysis

### Typical Usage Costs

| Searches/Day | Free APIs | Paid APIs | Total Cost |
|-------------|-----------|-----------|------------|
| < 100 | $0 | $0 | **$0/month** |
| 100-500 | $0 | ~$50 (SerpAPI) | **$50/month** |
| 500+ | $0 | Custom | **Variable** |

### Cost Optimization Tips

1. Always configure free sources first
2. Set `min_people_threshold` higher to avoid paid APIs
3. Use caching aggressively
4. Monitor usage with `cost_stats` in response

## Support & Troubleshooting

### Debug Mode

```python
# Enable detailed logging
results = finder.find_connections(
    company="Stripe",
    title="Software Engineer", 
    debug=True
)
```

### Health Check Endpoint

```python
@app.route('/health')
def health():
    return {
        'status': 'healthy',
        'sources_configured': {
            'google_cse': bool(os.getenv('GOOGLE_CSE_ID')),
            'github': bool(os.getenv('GITHUB_TOKEN')),
            'openai': bool(os.getenv('OPENAI_API_KEY'))
        }
    }
```

### Common Error Codes

- `400` - Invalid company/title
- `429` - Rate limit exceeded  
- `500` - Server error (check logs)
- `503` - External API unavailable

## License & Legal

- MIT License - Commercial use allowed
- Respects robots.txt and ToS
- No direct LinkedIn scraping
- Uses only public APIs and data

## Contact & Contribution

- GitHub Issues: Report bugs or request features
- Pull Requests: Welcome! See CONTRIBUTING.md
- Documentation: This guide + README.md

---

Built with ❤️ for job seekers. Good luck with your integration!
