#!/usr/bin/env python3
"""Test different Apollo search strategies"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("APOLLO_API_KEY")
headers = {
    "X-Api-Key": api_key,
    "Content-Type": "application/json"
}

def test_search(description, params):
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Params: {params}")
    print('='*60)
    
    try:
        response = requests.post(
            "https://api.apollo.io/v1/contacts/search",
            json=params,
            headers=headers,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get("contacts", [])
            pagination = data.get("pagination", {})
            
            print(f"✓ Found {len(contacts)} contacts (total: {pagination.get('total_entries', 0)})")
            
            if contacts:
                for i, c in enumerate(contacts[:3], 1):
                    print(f"\n  {i}. {c.get('name', 'N/A')}")
                    print(f"     Title: {c.get('title', 'N/A')}")
                    print(f"     Company: {c.get('organization_name', 'N/A')}")
                    print(f"     Email: {c.get('email', 'N/A')}")
        else:
            print(f"❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

# Test 1: Exact company name match
test_search(
    "Test 1: Company name 'Meta'",
    {
        "q_organization_name": "Meta",
        "page": 1,
        "per_page": 5,
    }
)

# Test 2: Try "Meta Platforms"
test_search(
    "Test 2: Company name 'Meta Platforms'",
    {
        "q_organization_name": "Meta Platforms",
        "page": 1,
        "per_page": 5,
    }
)

# Test 3: With title filter
test_search(
    "Test 3: Meta + Software Engineer title",
    {
        "q_organization_name": "Meta",
        "person_titles": ["Software Engineer"],
        "page": 1,
        "per_page": 5,
    }
)

# Test 4: Just search by title (no company)
test_search(
    "Test 4: Just 'Software Engineer' title",
    {
        "person_titles": ["Software Engineer"],
        "page": 1,
        "per_page": 5,
    }
)

# Test 5: Try organization_ids approach
test_search(
    "Test 5: Search for 'google' to see if Apollo has any data",
    {
        "q_organization_name": "Google",
        "page": 1,
        "per_page": 5,
    }
)

# Test 6: Try with broader search
test_search(
    "Test 6: Search with keywords",
    {
        "q_keywords": "Software Engineer Meta",
        "page": 1,
        "per_page": 5,
    }
)

print("\n" + "="*60)
print("All tests complete!")
print("="*60)

