"""Google SERP scraping for LinkedIn profiles"""

import os
import re
from typing import List, Optional
from urllib.parse import quote_plus, urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter
from src.utils.cost_tracker import get_cost_tracker


class GoogleSearchScraper:
    """
    Search Google for LinkedIn profiles without hitting LinkedIn directly.
    
    Uses SerpAPI if available (recommended), falls back to direct scraping.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERP_API_KEY")
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.cost_tracker = get_cost_tracker()
        
        # Configure rate limiting
        self.rate_limiter.configure("google_serp", requests_per_second=0.5)
    
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search for people via Google SERP.
        
        Args:
            company: Company name
            title: Job title
        
        Returns:
            List of Person objects
        """
        if self.api_key:
            return self._search_with_api(company, title)
        else:
            print("⚠️  No SERP API key - using direct scraping (may be unreliable)")
            return self._search_direct(company, title)
    
    def _search_with_api(self, company: str, title: str) -> List[Person]:
        """Search using SerpAPI (recommended)"""
        self.rate_limiter.wait_if_needed("google_serp")
        
        # Build search query
        query = f'site:linkedin.com/in/ "{company}" "{title}" -intitle:jobs'
        
        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self.api_key,
                    "num": 20,
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Track cost (free tier)
            self.cost_tracker.record_request("google_serp", cost=0.0)
            
            # Parse results
            people = []
            for result in data.get("organic_results", []):
                person = self._parse_serp_result(result, company, title)
                if person:
                    people.append(person)
            
            print(f"✓ Google SERP found {len(people)} people")
            return people
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"⚠️  SerpAPI authentication failed")
            else:
                print(f"⚠️  SerpAPI error: {e}")
            return []
        except Exception as e:
            print(f"⚠️  SerpAPI unexpected error: {e}")
            return []
    
    def _search_direct(self, company: str, title: str) -> List[Person]:
        """Direct Google scraping (fallback, less reliable)"""
        self.rate_limiter.wait_if_needed("google_serp")
        
        query = f'site:linkedin.com/in/ "{company}" "{title}" -intitle:jobs'
        url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
        
        try:
            response = self.http_client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search results
            people = []
            results = soup.find_all('div', class_='g')
            
            for result in results[:20]:
                person = self._parse_google_result(result, company, title)
                if person:
                    people.append(person)
            
            if people:
                print(f"✓ Google scraping found {len(people)} people")
            else:
                print(f"⚠️  Google scraping found no results (may be blocked)")
            
            return people
            
        except Exception as e:
            print(f"⚠️  Google scraping error: {e}")
            return []
    
    def _parse_serp_result(self, result: dict, company: str, title: str) -> Optional[Person]:
        """Parse SerpAPI result into Person"""
        try:
            link = result.get("link", "")
            
            # Verify it's a LinkedIn profile
            if "linkedin.com/in/" not in link:
                return None
            
            # Extract name from title
            result_title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            # Parse name from title (usually "Name - Title - Company")
            name = self._extract_name_from_title(result_title)
            if not name:
                return None
            
            # Parse actual title from title or snippet
            person_title = self._extract_title_from_text(result_title, snippet)
            
            return Person(
                name=name,
                title=person_title or title,
                company=company,
                linkedin_url=link,
                source="google_serp",
                evidence_url=link,
            )
            
        except Exception as e:
            return None
    
    def _parse_google_result(self, result_elem, company: str, title: str) -> Optional[Person]:
        """Parse direct Google result into Person"""
        try:
            # Find link
            link_elem = result_elem.find('a', href=True)
            if not link_elem:
                return None
            
            link = link_elem['href']
            
            # Verify it's a LinkedIn profile
            if "linkedin.com/in/" not in link:
                return None
            
            # Find title (h3)
            title_elem = result_elem.find('h3')
            if not title_elem:
                return None
            
            result_title = title_elem.get_text(strip=True)
            
            # Find snippet
            snippet_elem = result_elem.find('div', class_=re.compile(r'VwiC3b'))
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Parse name and title
            name = self._extract_name_from_title(result_title)
            if not name:
                return None
            
            person_title = self._extract_title_from_text(result_title, snippet)
            
            return Person(
                name=name,
                title=person_title or title,
                company=company,
                linkedin_url=link,
                source="google_serp",
                evidence_url=link,
            )
            
        except Exception as e:
            return None
    
    def _extract_name_from_title(self, title: str) -> Optional[str]:
        """Extract person name from page title"""
        # LinkedIn titles usually: "Name - Title - Company | LinkedIn"
        # or "Name | Professional Profile | LinkedIn"
        
        # Remove "| LinkedIn" suffix
        title = re.sub(r'\s*\|\s*LinkedIn.*$', '', title)
        
        # Split by dash or pipe
        parts = re.split(r'\s*[-|]\s*', title)
        
        if parts:
            # First part is usually the name
            name = parts[0].strip()
            
            # Validate it looks like a name
            if len(name) > 2 and len(name) < 100:
                # Check it has at least first and last name
                if ' ' in name:
                    return name
        
        return None
    
    def _extract_title_from_text(self, title: str, snippet: str) -> Optional[str]:
        """Extract job title from title or snippet"""
        # From title: "Name - Title - Company"
        parts = re.split(r'\s*[-|]\s*', title)
        
        if len(parts) >= 2:
            # Second part is often the title
            potential_title = parts[1].strip()
            
            # Skip if it's just "LinkedIn" or similar
            if potential_title and not any(x in potential_title.lower() for x in ['linkedin', 'profile', 'professional']):
                return potential_title
        
        # Try to extract from snippet
        # Pattern: "Name is a Title at Company"
        match = re.search(r'is (?:a|an|the) ([^.]+) at', snippet, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None

