"""
ACTUALLY Working Free Sources (2024)
Based on real testing - these methods work TODAY

Strategy: Don't scrape search engines directly (they block)
Use: APIs with free tiers + GitHub + company websites
"""

import os
import requests
import time
from typing import List, Optional
from bs4 import BeautifulSoup

from src.models.person import Person


class ActuallyWorkingFreeSources:
    """
    Sources that ACTUALLY work as of 2024:
    
    1. Google Custom Search Engine API (100 free/day)
    2. Bing Web Search API (1000 free/month)
    3. GitHub API (60/hour unauthenticated, 5000/hour authenticated)
    4. Company websites (team pages, about pages)
    5. PeopleDataLabs Company Dataset (free dataset, not API)
    
    What DOESN'T work:
    - Direct DuckDuckGo/Bing/Yahoo HTML scraping (blocked)
    - LinkedIn direct scraping (ToS violation + blocked)
    - Most "free" search engines (block bots)
    """
    
    def __init__(self):
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.bing_api_key = os.getenv('BING_SEARCH_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')  # Optional but increases limits
        
    def search_all(self, company: str, title: str = None, max_results: int = 50) -> List[Person]:
        """
        Search all working sources.
        """
        all_people = []
        seen_urls = set()
        
        print(f"\n🔍 Searching: {company} {title or ''}")
        
        # Priority 1: Google Custom Search (if configured)
        if self.google_cse_id and self.google_api_key:
            print("  → Google Custom Search...")
            try:
                people = self._search_google_cse(company, title)
                new = self._add_unique(people, seen_urls, all_people)
                print(f"    ✓ Found {new} profiles")
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
        else:
            print("  ⊘ Google CSE not configured (set GOOGLE_CSE_ID + GOOGLE_API_KEY)")
        
        # Priority 2: Bing Search API (if configured)
        if self.bing_api_key:
            print("  → Bing Web Search API...")
            try:
                people = self._search_bing_api(company, title)
                new = self._add_unique(people, seen_urls, all_people)
                print(f"    ✓ Found {new} profiles")
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
        else:
            print("  ⊘ Bing API not configured (set BING_SEARCH_KEY)")
        
        # Priority 3: GitHub (always works, no API key required)
        print("  → GitHub API...")
        try:
            people = self._search_github(company)
            new = self._add_unique(people, seen_urls, all_people)
            print(f"    ✓ Found {new} profiles")
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:50]}")
        
        # Priority 4: Company website
        print("  → Company website...")
        try:
            people = self._search_company_website(company)
            new = self._add_unique(people, seen_urls, all_people)
            if new > 0:
                print(f"    ✓ Found {new} people")
            else:
                print(f"    - No team page found")
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:50]}")
        
        print(f"\n✅ Total: {len(all_people)} connections")
        return all_people[:max_results]
    
    def _add_unique(self, people: List[Person], seen_urls: set, all_people: List[Person]) -> int:
        """Add unique people to results"""
        count = 0
        for person in people:
            key = person.linkedin_url or person.name
            if key and key not in seen_urls:
                seen_urls.add(key)
                all_people.append(person)
                count += 1
        return count
    
    def _search_google_cse(self, company: str, title: str = None) -> List[Person]:
        """
        Google Custom Search Engine API.
        
        Setup:
        1. Create CSE: https://programmablesearchengine.google.com/
        2. Configure to search "linkedin.com/in/*"
        3. Get API key from Google Cloud Console
        4. 100 searches/day free
        """
        people = []
        
        query = f'"{company}"'
        if title:
            query += f' "{title}"'
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.google_api_key,
            'cx': self.google_cse_id,
            'q': query,
            'num': 10,  # Max per request
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for item in data.get('items', []):
                url = item.get('link', '')
                title_text = item.get('title', '')
                snippet = item.get('snippet', '')
                
                if 'linkedin.com/in/' in url:
                    # Extract name from title (format: "Name - Job Title - LinkedIn")
                    name = title_text.split(' - ')[0].strip()
                    
                    # Try to extract title from snippet or title
                    job_title = None
                    if ' - ' in title_text:
                        parts = title_text.split(' - ')
                        if len(parts) >= 2:
                            job_title = parts[1].strip()
                    
                    if len(name) > 2:
                        person = Person(
                            name=name,
                            title=job_title,
                            company=company,
                            linkedin_url=url,
                            source='google_cse',
                            confidence_score=0.9  # High quality from Google
                        )
                        people.append(person)
        
        return people
    
    def _search_bing_api(self, company: str, title: str = None) -> List[Person]:
        """
        Bing Web Search API.
        
        Setup:
        1. Create Azure account
        2. Create Bing Search resource
        3. Get API key
        4. 1000 searches/month free
        """
        people = []
        
        query = f'site:linkedin.com/in/ "{company}"'
        if title:
            query += f' "{title}"'
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_api_key,
        }
        params = {
            'q': query,
            'count': 50,
            'mkt': 'en-US',
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for result in data.get('webPages', {}).get('value', []):
                url = result.get('url', '')
                title_text = result.get('name', '')
                
                if 'linkedin.com/in/' in url:
                    name = title_text.split(' - ')[0].strip()
                    
                    job_title = None
                    if ' - ' in title_text:
                        parts = title_text.split(' - ')
                        if len(parts) >= 2:
                            job_title = parts[1].strip()
                    
                    if len(name) > 2:
                        person = Person(
                            name=name,
                            title=job_title,
                            company=company,
                            linkedin_url=url,
                            source='bing_api',
                            confidence_score=0.85
                        )
                        people.append(person)
        
        return people
    
    def _search_github(self, company: str) -> List[Person]:
        """
        GitHub API - SIMPLIFIED for reliability.
        
        Only uses search API (no individual user lookups to save rate limits).
        Returns basic info quickly.
        
        Limits:
        - 60 requests/hour without auth (10 searches = 1000 users)
        - 5000 requests/hour with GITHUB_TOKEN
        """
        people = []
        
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        # Search users by company in bio (single API call)
        url = "https://api.github.com/search/users"
        params = {
            'q': f'"{company}" in:bio type:user',
            'per_page': 100  # Max allowed
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total_count = data.get('total_count', 0)
                items = data.get('items', [])
                
                print(f"    Found {total_count} GitHub users (returning {len(items)})")
                
                # Use data directly from search (no extra API calls)
                for user in items:
                    login = user.get('login', '')
                    avatar = user.get('avatar_url', '')
                    profile_url = user.get('html_url', '')
                    
                    # Use login as name (can enhance later with individual API calls if needed)
                    name = login.replace('-', ' ').replace('_', ' ').title()
                    
                    person = Person(
                        name=name,
                        company=company,
                        source='github',
                        confidence_score=0.5,  # Lower since we don't verify bio
                        github_url=profile_url,
                        evidence_url=profile_url,
                    )
                    people.append(person)
                    
            elif response.status_code == 403:
                print("    ⚠ Rate limited (add GITHUB_TOKEN to .env)")
            else:
                print(f"    ⚠ GitHub API error: {response.status_code}")
                
        except Exception as e:
            print(f"    ⚠ Exception: {str(e)[:50]}")
        
        # Also try organization members (quick check, no extra lookups)
        try:
            org_name = company.lower().replace(' ', '').replace(',', '').replace('.', '')
            org_url = f"https://api.github.com/orgs/{org_name}/members"
            
            response = requests.get(org_url, headers=headers, params={'per_page': 100}, timeout=10)
            
            if response.status_code == 200:
                members = response.json()
                print(f"    Found {len(members)} org members")
                
                for member in members:
                    login = member.get('login', '')
                    name = login.replace('-', ' ').replace('_', ' ').title()
                    profile_url = member.get('html_url', '')
                    
                    person = Person(
                        name=name,
                        company=company,
                        source='github',
                        confidence_score=0.7,  # Higher - confirmed org member
                        github_url=profile_url,
                        evidence_url=profile_url,
                    )
                    people.append(person)
                    
        except Exception:
            pass  # Org might not exist, that's OK
        
        return people
    
    def _search_company_website(self, company: str) -> List[Person]:
        """
        Search company website for team/about pages.
        """
        people = []
        
        # Guess domain
        domain = self._guess_domain(company)
        if not domain:
            return []
        
        # Try common team page patterns
        patterns = [
            f"https://{domain}/team",
            f"https://{domain}/about/team",
            f"https://{domain}/about-us",
            f"https://{domain}/leadership",
            f"https://{domain}/people",
            f"https://{domain}/company/team",
        ]
        
        for url in patterns:
            try:
                response = requests.get(url, timeout=5, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for team member sections
                    # Common patterns: name + title + LinkedIn link
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        
                        if 'linkedin.com/in/' in href:
                            # Found a LinkedIn link
                            # Try to find name nearby
                            parent = link.find_parent(['div', 'section', 'article'])
                            if parent:
                                text = parent.get_text(strip=True)
                                # Name is usually near the link
                                words = text.split()
                                if len(words) >= 2:
                                    # Assume first 2-3 words are the name
                                    name = ' '.join(words[:3])
                                    
                                    person = Person(
                                        name=name,
                                        company=company,
                                        linkedin_url=href,
                                        source='company_website',
                                        confidence_score=0.8
                                    )
                                    people.append(person)
                    
                    if people:
                        break  # Found a page with results
                        
            except Exception:
                continue
        
        return people
    
    def _guess_domain(self, company: str) -> Optional[str]:
        """Guess company domain"""
        # Common mappings
        mappings = {
            'google': 'google.com',
            'meta': 'meta.com',
            'facebook': 'meta.com',
            'stripe': 'stripe.com',
            'cursor': 'cursor.so',
            'openai': 'openai.com',
            'anthropic': 'anthropic.com',
        }
        
        company_lower = company.lower()
        if company_lower in mappings:
            return mappings[company_lower]
        
        # Try .com
        clean = company_lower.replace(' ', '').replace(',', '').replace('.', '')
        return f"{clean}.com"


def test_working_sources():
    """Test with real companies"""
    searcher = ActuallyWorkingFreeSources()
    
    print("\n" + "="*60)
    print("🧪 TESTING ACTUALLY WORKING FREE SOURCES")
    print("="*60)
    
    # Check configuration
    print("\n📋 Configuration:")
    print(f"  Google CSE: {'✓ Configured' if searcher.google_cse_id else '✗ Not configured'}")
    print(f"  Bing API: {'✓ Configured' if searcher.bing_api_key else '✗ Not configured'}")
    print(f"  GitHub Token: {'✓ Configured' if searcher.github_token else '⚠ Using 60/hour limit'}")
    
    # Test
    people = searcher.search_all("Google", "Software Engineer", max_results=30)
    
    if people:
        print("\n📊 Sample Results:")
        for i, person in enumerate(people[:5], 1):
            print(f"\n{i}. {person.name}")
            if person.title:
                print(f"   Title: {person.title[:60]}...")
            if person.linkedin_url:
                print(f"   LinkedIn: {person.linkedin_url[:70]}...")
            print(f"   Source: {person.source}")
            print(f"   Confidence: {person.confidence_score}")
    else:
        print("\n⚠ No results - configure API keys for better results")
        print("\nSetup instructions:")
        print("  1. Google CSE: https://programmablesearchengine.google.com/")
        print("  2. Bing API: https://portal.azure.com/ (search for Bing Search)")
        print("  3. GitHub Token: https://github.com/settings/tokens (optional)")


if __name__ == "__main__":
    test_working_sources()
