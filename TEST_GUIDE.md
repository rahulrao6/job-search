# Testing Guide

## Quick Start

### Option 1: Python Script (Recommended)

```bash
# Set your token
export API_TOKEN="your-jwt-token-here"

# Run tests
python test_api.py
```

Or edit the script and set TOKEN at the top.

### Option 2: Bash Script

```bash
# Make executable
chmod +x test_api.sh

# Run with token
./test_api.sh YOUR_JWT_TOKEN

# Or set environment variable
export API_TOKEN="your-token"
./test_api.sh
```

### Option 3: Manual cURL

See `RUN_COMMANDS.md` for individual curl commands.

## What Gets Tested

The test script (`test_api.py`) tests:

1. ✅ **Health Check** - Server connectivity
2. ✅ **Get Quota** - User's remaining searches
3. ✅ **Get Profile** - User profile data
4. ✅ **Save Profile** - Update user profile
5. ✅ **Search (Simple)** - Basic search
6. ✅ **Search (With Profile)** - Search with profile context
7. ✅ **Search (With Job Context)** - Search with job details
8. ✅ **Error Handling** - Invalid/missing tokens
9. ✅ **Error Handling** - Invalid requests

## Test Results

- ✅ Green = Pass
- ❌ Red = Fail
- ℹ️ Yellow = Info

The script shows:
- HTTP status codes
- Response bodies (truncated if long)
- Quota information
- Error messages

## Using Your Token

Your token is in `RUN_COMMANDS.md`. Use it like:

```bash
export API_TOKEN="eyJhbGciOiJIUzI1NiIsImtpZCI6IlE4ME45aGIzazJaUmNtZEEiLCJ0eXAiOiJKV1QifQ..."
python test_api.py
```

Or edit `test_api.py` and replace:
```python
TOKEN = os.getenv("API_TOKEN", "")
```

With:
```python
TOKEN = "your-token-here"
```

## Troubleshooting

### "Could not connect to server"
- Make sure server is running: `python web_app.py`
- Check BASE_URL in script (default: http://localhost:8000)

### "Invalid token"
- Token may have expired (usually 1 hour)
- Get fresh token from Supabase Auth
- Make sure you're using `access_token`, not `refresh_token`

### "401 Unauthorized"
- Token format: `Authorization: Bearer <token>`
- Make sure token is valid and not expired

### "Rate limit exceeded"
- Wait 60 seconds and try again
- Check your subscription tier

### "Quota exceeded"
- You've used all monthly searches
- Upgrade tier or wait for reset

## Customizing Tests

Edit `test_api.py` to:
- Add more test cases
- Change test data
- Modify expected status codes
- Test specific scenarios

## Continuous Testing

For CI/CD, use:

```bash
export API_TOKEN="$CI_TOKEN"
python test_api.py
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Tests failed!"
    exit 1
fi
```

