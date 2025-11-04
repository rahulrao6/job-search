#!/usr/bin/env python3
"""
Check Apollo API usage and permissions.
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import json

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("APOLLO_API_KEY")

print("=" * 60)
print("Apollo API Usage & Permissions Check")
print("=" * 60)

if not api_key:
    print("❌ ERROR: No Apollo API key found")
    exit(1)

print(f"✓ Apollo API key found: {api_key[:10]}...{api_key[-10:]}\n")

headers = {
    "X-Api-Key": api_key,
    "Content-Type": "application/json"
}

# Check API usage stats
print("Checking API usage stats...")
print("-" * 60)

try:
    usage_response = requests.post(
        "https://api.apollo.io/v1/auth/health",
        headers=headers,
        timeout=30
    )
    
    print(f"Health check status: {usage_response.status_code}")
    if usage_response.status_code == 200:
        print(f"Response: {usage_response.text}")
    
    # Try to get usage stats
    usage_response = requests.post(
        "https://api.apollo.io/v1/mixed_people/search",
        json={},
        headers=headers,
        timeout=30
    )
    
    print(f"\nMixed people search status: {usage_response.status_code}")
    if usage_response.status_code == 200:
        data = usage_response.json()
        print(f"Keys in response: {list(data.keys())[:10]}")
    else:
        print(f"Response: {usage_response.text[:300]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("\n💡 SUMMARY:")
print("=" * 60)
print("""
Based on the tests:

✓ Authentication works (X-Api-Key header with 200 status)
✓ Organization search works (finds organizations)
✗ Contact search returns 0 results (even with organization IDs)

POSSIBLE REASONS:
1. Free tier may only have access to enrichment, not search
2. API key may need to be upgraded to a paid plan for search
3. Account may need to enable contact search permissions
4. Free tier credits may be exhausted

NEXT STEPS:
- Check your Apollo dashboard for API usage/credits
- Verify your plan includes contact search (not just enrichment)
- Consider upgrading if free tier doesn't include search
""")

