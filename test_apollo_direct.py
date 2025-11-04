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

# Try both authentication methods
auth_methods = [
    ("X-Api-Key", api_key),
    ("Authorization", f"Bearer {api_key}"),
]

try:
    for auth_header, auth_value in auth_methods:
        print(f"\n{'='*60}")
        print(f"Testing with {auth_header} header...")
        print('='*60)
        
        try:
            # Test 1: Simple company search (no title filter) - try multiple companies
            test_companies = ["Meta", "Google", "Microsoft", "Apple"]
            for test_company in test_companies:
                print(f"\nTest 1: Search for company='{test_company}' (no title filter)")
                response = requests.post(
                    "https://api.apollo.io/api/v1/mixed_people/search",
                    json={
                        "q_organization_name": test_company,
                        "page": 1,
                        "per_page": 10,
                    },
                    headers={
                        auth_header: auth_value,
                        "Content-Type": "application/json"
                    },
                    timeout=30
                )
            
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    contacts = data.get("contacts", [])
                    pagination = data.get("pagination", {})
                    total_entries = pagination.get("total_entries", 0)
                    
                    print(f"✓ Found {len(contacts)} contacts (total available: {total_entries})")
                    
                    # Show full response structure for debugging
                    if not contacts:
                        print(f"   ⚠️  No contacts for {test_company}")
                        if total_entries == 0:
                            print(f"   Apollo database may not have data for '{test_company}'")
                        continue  # Try next company
                    
                    # Success! Found contacts
                    print(f"\n✓ SUCCESS! Found contacts for '{test_company}'")
                    print(f"\nFirst 3 results:")
                    for i, contact in enumerate(contacts[:3], 1):
                        print(f"\n{i}. {contact.get('name', 'N/A')}")
                        print(f"   Title: {contact.get('title', 'N/A')}")
                        print(f"   Email: {contact.get('email', 'N/A')}")
                        print(f"   LinkedIn: {contact.get('linkedin_url', 'N/A')}")
                    # Success! Exit both loops
                    raise StopIteration("Found contacts successfully")
                else:
                    print(f"   ❌ Status {response.status_code}: {response.text[:200]}")
                    if response.status_code == 401:
                        print("\n⚠️  Authentication failed - check your API key")
                        break  # Stop trying this auth method
                    elif response.status_code == 429:
                        print("\n⚠️  Rate limit exceeded")
                        break  # Stop trying this auth method
                    continue  # Try next company
        except StopIteration:
            # Successfully found contacts, exit outer loop
            break
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()
except StopIteration:
    pass  # Successfully found contacts
except Exception as e:
    print(f"❌ Outer exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

