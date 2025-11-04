#!/usr/bin/env python3
"""
Quick debug script for Google CSE issues.
Tests the API directly to see what's being returned.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_google_cse():
    """Test Google CSE API directly"""
    google_cse_id = os.getenv('GOOGLE_CSE_ID')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    
    print("=" * 60)
    print("Google CSE Debug Test")
    print("=" * 60)
    
    # Check configuration
    if not google_cse_id:
        print("❌ GOOGLE_CSE_ID is not set in .env")
        return
    if not google_api_key:
        print("❌ GOOGLE_API_KEY is not set in .env")
        return
    
    print(f"✓ GOOGLE_CSE_ID: {google_cse_id[:20]}...")
    print(f"✓ GOOGLE_API_KEY: {google_api_key[:20]}...")
    print()
    
    # Test with a simple query
    url = "https://www.googleapis.com/customsearch/v1"
    test_query = 'site:linkedin.com/in/ "Google" "Software Engineer"'
    
    params = {
        'key': google_api_key,
        'cx': google_cse_id,
        'q': test_query,
        'num': 10,
    }
    
    print(f"Testing query: {test_query}")
    print()
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        print(f"HTTP Status: {response.status_code}")
        print()
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.text[:500]}")
            return
        
        data = response.json()
        
        # Check for API errors
        if 'error' in data:
            error_info = data['error']
            print("❌ API Error Detected:")
            print(json.dumps(error_info, indent=2))
            
            error_message = error_info.get('message', '')
            if 'quota' in error_message.lower():
                print("\n💡 Quota exceeded - Google CSE has 100 searches/day limit")
            elif 'invalid' in error_message.lower():
                print("\n💡 Invalid credentials - check GOOGLE_API_KEY and GOOGLE_CSE_ID")
            return
        
        # Check search information
        search_info = data.get('searchInformation', {})
        total_results = search_info.get('totalResults', '0')
        search_time = search_info.get('searchTime', '0')
        
        print(f"✓ Search completed in {search_time}s")
        print(f"✓ Total results: {total_results}")
        print()
        
        # Check items
        items = data.get('items', [])
        print(f"Items returned: {len(items)}")
        print()
        
        if len(items) == 0:
            print("⚠️  No items returned!")
            print("\nPossible reasons:")
            print("  1. CSE is not configured to search linkedin.com")
            print("  2. Query returned no matches")
            print("  3. CSE indexing is incomplete")
            print("\nFull response:")
            print(json.dumps(data, indent=2)[:1000])
        else:
            print("✓ Found results!")
            print("\nFirst result:")
            if items:
                first = items[0]
                print(f"  Title: {first.get('title', 'N/A')}")
                print(f"  Link: {first.get('link', 'N/A')}")
                print(f"  Snippet: {first.get('snippet', 'N/A')[:100]}...")
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_google_cse()

