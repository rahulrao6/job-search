# API Testing Guide

Quick reference for testing all API endpoints easily.

## Quick Start

```bash
# Run all tests
python test_api.py

# Run specific tests
python test_api.py --test 8,9

# Test only resume endpoints
python test_api.py --resume-only

# Test only job endpoints
python test_api.py --job-only

# Skip rate limit tests
python test_api.py --skip-rate-limit

# Use custom token
python test_api.py --token YOUR_JWT_TOKEN
```

## Test List

| # | Test Name | Endpoint | Description |
|---|-----------|----------|-------------|
| 1 | Health Check | `GET /api/v1/health` | Server health check |
| 2 | Get Quota | `GET /api/v1/quota` | User quota information |
| 3 | Get Profile | `GET /api/v1/profile` | Get user profile |
| 4 | Save Profile | `POST /api/v1/profile/save` | Save user profile |
| 5 | Search Simple | `POST /api/v1/search` | Simple search query |
| 6 | Search With Profile | `POST /api/v1/search` | Search with profile context |
| 7 | Search With Job Context | `POST /api/v1/search` | Search with job context |
| 8 | Resume Upload (File) | `POST /api/v1/resume/upload` | Upload PDF resume |
| 8b | Resume Upload (URL) | `POST /api/v1/resume/upload` | Upload from storage URL |
| 9 | Job Parsing | `POST /api/v1/job/parse` | Parse job from URL |
| 10 | Search Auto-Resume | `POST /api/v1/search` | Search auto-loads resume |
| 11 | Search Auto-Job | `POST /api/v1/search` | Search auto-scrapes job |
| 12 | Invalid Token | `GET /api/v1/quota` | Error handling test |
| 13 | Missing Token | `GET /api/v1/quota` | Error handling test |
| 14 | Invalid Request | `POST /api/v1/search` | Error handling test |

## Common Test Scenarios

### Test Resume Functionality
```bash
python test_api.py --resume-only
```
Tests:
- Resume upload (PDF file)
- Resume upload (from URL)

### Test Job Parsing
```bash
python test_api.py --job-only
```
Tests:
- Job URL parsing

### Test New Features
```bash
python test_api.py --test 8,9,10,11
```
Tests:
- Resume upload
- Job parsing
- Auto-load resume in search
- Auto-scrape job in search

### Quick Validation (Skip Long Tests)
```bash
python test_api.py --test 1,2,3,4,8,9 --skip-rate-limit
```
Fast validation of core endpoints.

## Environment Setup

### Required
- Server running at `http://localhost:8000` (or set `API_BASE_URL`)
- Valid JWT token (set via `--token` or edit `TOKEN` variable)

### Optional
- `DISABLE_RATE_LIMIT=true` - Disable rate limiting for testing
- Test PDF file (optional - script creates dummy PDF if not provided)

## Getting Your Token

1. **From React Frontend**
   - Login to your app
   - Check browser DevTools → Application → Local Storage → `supabase.auth.token`

2. **From Supabase Dashboard**
   - Go to Authentication → Users
   - Find your user and generate token

3. **From API Response**
   - After login, check the JWT in the response

## Examples

### Test Resume Upload with Real File
```bash
# Edit test_api.py and modify test_file_upload call to use:
file_path="/path/to/your/resume.pdf"
```

### Test Job Parsing with Real URL
```bash
# Edit test_api.py test 9 to use real job URL:
job_url = "https://www.linkedin.com/jobs/view/YOUR_JOB_ID"
```

### Test Specific Feature
```bash
# Test only resume upload
python test_api.py --test 8

# Test only job parsing
python test_api.py --test 9

# Test auto-features
python test_api.py --test 10,11
```

## Troubleshooting

### "Cannot connect to server"
- Make sure server is running: `python web_app.py`
- Check `BASE_URL` is correct

### "Invalid token" errors
- Token may have expired
- Get fresh token using `--token` flag

### "Rate limit exceeded"
- Use `--skip-rate-limit` flag (if enabled in server)
- Or set `DISABLE_RATE_LIMIT=true` before running server
- Wait for rate limit to reset (60 seconds)

### "Timeout" errors
- Server may be slow
- Check server logs for errors
- Some tests (like job scraping) can take 30+ seconds

## Output Explanation

- ✓ Green checkmark = Test passed
- ✗ Red X = Test failed  
- ℹ Yellow info = Informational message
- ⚠ Yellow warning = Warning (test may still pass)

## Tips

1. **Start with health check**: Always test #1 first to ensure server is running
2. **Use specific tests**: Run `--test 8,9` for quick resume/job testing
3. **Check response details**: Failed tests show response JSON for debugging
4. **Monitor server logs**: Keep server terminal open to see backend errors
5. **Test incrementally**: Fix one failing test before moving to next

