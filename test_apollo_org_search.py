#!/usr/bin/env python3
"""
Test Apollo organization search, then use org IDs to find contacts.
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
print("Apollo Organization + Contact Search Test")
print("=" * 60)

if not api_key:
    print("❌ ERROR: No Apollo API key found")
    exit(1)

print(f"✓ Apollo API key found: {api_key[:10]}...{api_key[-10:]}\n")

headers = {
    "X-Api-Key": api_key,
    "Content-Type": "application/json"
}

# Step 1: Search for organizations
print("Step 1: Searching for organizations...")
print("-" * 60)

companies = ["Meta", "Google", "Microsoft"]

for company in companies:
    print(f"\nSearching for '{company}'...")
    
    try:
        # Search organizations
        org_response = requests.post(
            "https://api.apollo.io/v1/organizations/search",
            json={
                "q_name": company,
                "page": 1,
                "per_page": 5,
            },
            headers=headers,
            timeout=30
        )
        
        print(f"  Organization search status: {org_response.status_code}")
        
        if org_response.status_code == 200:
            org_data = org_response.json()
            organizations = org_data.get("organizations", [])
            print(f"  Found {len(organizations)} organizations")
            
            if organizations:
                org = organizations[0]
                org_id = org.get("id")
                org_name = org.get("name")
                print(f"  ✓ Using organization: {org_name} (ID: {org_id})")
                
                # Step 2: Search contacts using organization ID
                print(f"\n  Step 2: Searching contacts at {org_name}...")
                contacts_response = requests.post(
                    "https://api.apollo.io/v1/contacts/search",
                    json={
                        "organization_ids": [org_id],
                        "page": 1,
                        "per_page": 10,
                    },
                    headers=headers,
                    timeout=30
                )
                
                print(f"  Contact search status: {contacts_response.status_code}")
                
                if contacts_response.status_code == 200:
                    contacts_data = contacts_response.json()
                    contacts = contacts_data.get("contacts", [])
                    pagination = contacts_data.get("pagination", {})
                    total = pagination.get("total_entries", 0)
                    
                    print(f"  ✓ Found {len(contacts)} contacts (total: {total})")
                    
                    if contacts:
                        print(f"\n  First 3 contacts:")
                        for i, contact in enumerate(contacts[:3], 1):
                            print(f"    {i}. {contact.get('name', 'N/A')}")
                            print(f"       Title: {contact.get('title', 'N/A')}")
                            print(f"       Email: {contact.get('email', 'N/A')}")
                        break  # Success! Exit loop
                    else:
                        print(f"  ⚠️  No contacts found (total available: {total})")
                else:
                    print(f"  ❌ Contact search failed: {contacts_response.status_code}")
                    print(f"     Response: {contacts_response.text[:200]}")
            else:
                print(f"  ⚠️  No organizations found for '{company}'")
        else:
            print(f"  ❌ Organization search failed: {org_response.status_code}")
            print(f"     Response: {org_response.text[:200]}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)

