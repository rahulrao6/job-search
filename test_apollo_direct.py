#!/usr/bin/env python3
"""
Direct test of Apollo API to verify it's working.
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("APOLLO_API_KEY")

print("=" * 60)
print("Apollo API Direct Test")
print("=" * 60)

if not api_key:
    print("❌ ERROR: No Apollo API key found in .env")
    print(f"Looking for .env at: {env_path}")
    print(f".env exists: {env_path.exists()}")
    if env_path.exists():
        with open(env_path) as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if 'APOLLO' in line:
                    # Don't print the actual key, just show if it's there
                    has_value = '=' in line and line.split('=', 1)[1].strip()
                    print(f"Line {i}: APOLLO_API_KEY = {'<set>' if has_value else '<empty>'}")
    exit(1)

print(f"✓ Apollo API key found: {api_key[:10]}...{api_key[-10:]}")
print(f"\nTesting API with company='Meta', title='Software Engineer'...")

try:
    response = requests.post(
        "https://api.apollo.io/v1/contacts/search",
        json={
            "q_organization_name": "Meta",
            "person_titles": ["Software Engineer"],
            "page": 1,
            "per_page": 10,
        },
        headers={
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        },
        timeout=30
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        contacts = data.get("contacts", [])
        print(f"✓ SUCCESS! Found {len(contacts)} people")
        
        if contacts:
            print(f"\nFirst 3 results:")
            for i, contact in enumerate(contacts[:3], 1):
                print(f"\n{i}. {contact.get('name', 'N/A')}")
                print(f"   Title: {contact.get('title', 'N/A')}")
                print(f"   Email: {contact.get('email', 'N/A')}")
                print(f"   LinkedIn: {contact.get('linkedin_url', 'N/A')}")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 401:
            print("\n⚠️  Authentication failed - check your API key")
        elif response.status_code == 429:
            print("\n⚠️  Rate limit exceeded")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 60)

