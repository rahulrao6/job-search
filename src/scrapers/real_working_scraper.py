"""A scraper that ACTUALLY works by using alternative search engines and methods"""

import re
import json
import time
import random
from typing import List, Optional, Dict, Tuple
from urllib.parse import quote, quote_plus, unquote
import requests
from bs4 import BeautifulSoup

from src.models.person import Person, PersonCategory
from src.utils.cache import get_cache


class RealWorkingScraper:
    """
    A scraper that actually returns real LinkedIn profiles.
    Uses alternative search engines and clever techniques.
    """
    
    def __init__(self):
        self.session = self._create_session()
        self.cache = get_cache()
        
    def _create_session(self):
        """Create a session with proper headers"""
        session = requests.Session()
        return session
    
    def search_people(self, company: str, title: Optional[str] = None, 
                     max_results: int = 20, **kwargs) -> List[Person]:
        """Alias for compatibility with other scrapers"""
        return self.search_linkedin_profiles(company, title, max_results)
    
    def search_linkedin_profiles(self, company: str, role: Optional[str] = None, 
                               max_results: int = 20) -> List[Person]:
        """
        Search for real LinkedIn profiles.
        
        Args:
            company: Company name
            role: Job role (optional)
            max_results: Maximum number of results
            
        Returns:
            List of Person objects with real data
        """
        all_people = []
        seen_urls = set()
        
        print(f"\n🔍 Searching for real LinkedIn profiles at {company}")
        
        # Use multiple search methods
        search_methods = [
            self._search_using_searx,
            self._search_using_qwant,
            self._search_using_yahoo,
            self._search_using_ecosia,
            self._search_using_swisscows,
        ]
        
        for method in search_methods:
            if len(all_people) >= max_results:
                break
                
            try:
                print(f"  → Trying {method.__name__}...")
                people = method(company, role)
                
                # Filter duplicates
                new_count = 0
                for person in people:
                    if person.linkedin_url not in seen_urls:
                        seen_urls.add(person.linkedin_url)
                        all_people.append(person)
                        new_count += 1
                
                if new_count > 0:
                    print(f"    ✓ Found {new_count} new profiles")
                else:
                    print(f"    - No new profiles")
                    
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}...")
            
            # Random delay
            time.sleep(random.uniform(1, 3))
        
        print(f"\n✅ Total profiles found: {len(all_people)}")
        
        return all_people[:max_results]
    
    def _search_using_searx(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use Searx instances (privacy-focused metasearch)"""
        people = []
        
        # Public Searx instances
        searx_instances = [
            "https://searx.be",
            "https://search.privacyguides.net",
            "https://searx.tiekoetter.com",
        ]
        
        query = f'site:linkedin.com/in/ "{company}" recruiter OR manager OR talent'
        
        for instance in searx_instances[:1]:  # Try one instance
            try:
                url = f"{instance}/search"
                params = {
                    'q': query,
                    'format': 'json',
                    'categories': 'general',
                }
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json',
                }
                
                response = self.session.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for result in data.get('results', [])[:20]:
                        person = self._extract_person_from_searx_result(result, company)
                        if person:
                            people.append(person)
                    
                    if people:
                        break  # Got results, no need to try other instances
                        
            except Exception:
                continue
        
        return people
    
    def _search_using_qwant(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use Qwant search (French privacy-focused engine)"""
        people = []
        
        query = f'"{company}" recruiter OR manager linkedin.com/in/'
        
        try:
            # Qwant API endpoint
            url = "https://api.qwant.com/v3/search/web"
            
            params = {
                'q': query,
                'count': 20,
                'locale': 'en_US',
                'device': 'desktop',
                'safesearch': 1,
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract results
                results = data.get('data', {}).get('result', {}).get('items', {}).get('mainline', [])
                
                for section in results:
                    if section.get('type') == 'web':
                        for item in section.get('items', []):
                            person = self._extract_person_from_qwant_result(item, company)
                            if person:
                                people.append(person)
        
        except Exception:
            pass
        
        return people
    
    def _search_using_yahoo(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use Yahoo search"""
        people = []
        
        query = f'site:linkedin.com/in/ "{company}" (recruiter OR "talent acquisition" OR manager)'
        
        try:
            url = "https://search.yahoo.com/search"
            
            params = {
                'p': query,
                'n': 20,
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Yahoo result structure
                for result in soup.find_all('div', class_='dd algo'):
                    # Get link
                    link = result.find('a', href=True)
                    if not link:
                        continue
                    
                    url = link.get('href', '')
                    if 'linkedin.com/in/' not in url:
                        continue
                    
                    # Get title and snippet
                    title = link.get_text(strip=True)
                    snippet_elem = result.find('span', class_='fc-falcon')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    person = self._extract_person_from_result(title, snippet, url, company, "yahoo")
                    if person:
                        people.append(person)
        
        except Exception:
            pass
        
        return people
    
    def _search_using_ecosia(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use Ecosia search (environmental search engine)"""
        people = []
        
        query = f'"{company}" linkedin recruiter OR manager'
        
        try:
            url = "https://www.ecosia.org/search"
            
            params = {
                'q': query,
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ecosia uses Bing results
                for result in soup.find_all(['div', 'li'], class_=['result', 'result-wrapper']):
                    # Get the link
                    link = result.find('a', class_='result-title')
                    if not link:
                        link = result.find('a', href=True)
                    
                    if not link:
                        continue
                    
                    url = link.get('href', '')
                    if 'linkedin.com/in/' not in url:
                        continue
                    
                    # Get text
                    title = link.get_text(strip=True)
                    snippet_elem = result.find(['p', 'div'], class_=['result-snippet', 'snippet'])
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    person = self._extract_person_from_result(title, snippet, url, company, "ecosia")
                    if person:
                        people.append(person)
        
        except Exception:
            pass
        
        return people
    
    def _search_using_swisscows(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use Swisscows (Swiss privacy search)"""
        people = []
        
        query = f'"{company}" linkedin recruiter'
        
        try:
            # Swisscows API
            url = "https://api.swisscows.com/web/search"
            
            params = {
                'query': query,
                'region': 'en-US',
                'itemsCount': 20,
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('items', []):
                    url = item.get('url', '')
                    if 'linkedin.com/in/' not in url:
                        continue
                    
                    title = item.get('title', '')
                    snippet = item.get('description', '')
                    
                    person = self._extract_person_from_result(title, snippet, url, company, "swisscows")
                    if person:
                        people.append(person)
        
        except Exception:
            pass
        
        return people
    
    def _extract_person_from_searx_result(self, result: dict, company: str) -> Optional[Person]:
        """Extract person from Searx result"""
        url = result.get('url', '')
        if 'linkedin.com/in/' not in url:
            return None
        
        title = result.get('title', '')
        content = result.get('content', '')
        
        return self._extract_person_from_result(title, content, url, company, "searx")
    
    def _extract_person_from_qwant_result(self, result: dict, company: str) -> Optional[Person]:
        """Extract person from Qwant result"""
        url = result.get('url', '')
        if 'linkedin.com/in/' not in url:
            return None
        
        title = result.get('title', '')
        desc = result.get('desc', '')
        
        return self._extract_person_from_result(title, desc, url, company, "qwant")
    
    def _extract_person_from_result(self, title: str, snippet: str, url: str, 
                                   company: str, source: str) -> Optional[Person]:
        """Extract person from search result"""
        # Clean LinkedIn URL
        linkedin_url = self._clean_url(url)
        if not linkedin_url:
            return None
        
        # Extract name
        name = self._extract_name(title)
        if not name:
            # Try from snippet
            name = self._extract_name(snippet)
        
        if not name:
            # Last resort - try to get from URL
            username = re.search(r'linkedin\.com/in/([^/?]+)', linkedin_url)
            if username:
                # Convert username to name (john-doe -> John Doe)
                name_parts = username.group(1).split('-')
                if len(name_parts) >= 2 and all(p.isalpha() for p in name_parts[:2]):
                    name = ' '.join(p.capitalize() for p in name_parts[:2])
        
        if not name:
            return None
        
        # Extract job title
        job_title = self._extract_title(title, snippet)
        
        # Categorize
        category = self._categorize_person(title + " " + snippet)
        
        # Calculate confidence
        confidence = 0.8
        if source in ['searx', 'qwant']:
            confidence = 0.85
        elif source in ['yahoo', 'ecosia']:
            confidence = 0.75
        
        return Person(
            name=name,
            title=job_title,
            company=company,
            linkedin_url=linkedin_url,
            source=f"search_{source}",
            category=category,
            confidence_score=confidence,
            evidence_url=linkedin_url
        )
    
    def _clean_url(self, url: str) -> Optional[str]:
        """Clean and validate LinkedIn URL"""
        if not url or 'linkedin.com/in/' not in url:
            return None
        
        # Extract profile ID
        match = re.search(r'linkedin\.com/in/([^/?&#]+)', url)
        if match:
            profile_id = match.group(1)
            return f"https://www.linkedin.com/in/{profile_id}"
        
        return None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract name from text"""
        if not text:
            return None
        
        # Clean text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common suffixes
        text = re.sub(r'\s*[-–|]\s*LinkedIn.*$', '', text, flags=re.I)
        text = re.sub(r'\s*on\s+LinkedIn.*$', '', text, flags=re.I)
        text = re.sub(r'\s*\|.*$', '', text)
        
        # Pattern 1: "FirstName LastName - Title"
        match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*[-–]', text)
        if match:
            name = match.group(1)
            if self._is_valid_name(name):
                return name
        
        # Pattern 2: Just name at beginning
        match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s|,|$)', text)
        if match:
            name = match.group(1)
            if self._is_valid_name(name):
                return name
        
        # Pattern 3: "View FirstName LastName's profile"
        match = re.search(r'(?:View|See)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\'s|\'s)', text)
        if match:
            name = match.group(1)
            if self._is_valid_name(name):
                return name
        
        return None
    
    def _is_valid_name(self, name: str) -> bool:
        """Check if name is valid"""
        if not name or len(name) < 3 or len(name) > 50:
            return False
        
        parts = name.split()
        if len(parts) < 2 or len(parts) > 4:
            return False
        
        # Check for invalid patterns
        invalid_words = ['linkedin', 'profile', 'view', 'see', 'http', 'www']
        name_lower = name.lower()
        if any(word in name_lower for word in invalid_words):
            return False
        
        return True
    
    def _extract_title(self, title: str, snippet: str) -> str:
        """Extract job title"""
        full_text = f"{title} {snippet}".lower()
        
        # Common titles
        title_patterns = [
            (r'campus recruiter', 'Campus Recruiter'),
            (r'university recruiter', 'University Recruiter'), 
            (r'technical recruiter', 'Technical Recruiter'),
            (r'senior recruiter', 'Senior Recruiter'),
            (r'talent acquisition', 'Talent Acquisition Specialist'),
            (r'recruiting manager', 'Recruiting Manager'),
            (r'hiring manager', 'Hiring Manager'),
            (r'head of talent', 'Head of Talent'),
            (r'recruiter', 'Recruiter'),
            (r'engineering manager', 'Engineering Manager'),
            (r'product manager', 'Product Manager'),
            (r'software engineer', 'Software Engineer'),
            (r'data scientist', 'Data Scientist'),
            (r'business analyst', 'Business Analyst'),
            (r'manager', 'Manager'),
        ]
        
        for pattern, title_str in title_patterns:
            if re.search(pattern, full_text):
                return title_str
        
        return "Professional"
    
    def _categorize_person(self, text: str) -> PersonCategory:
        """Categorize person based on text"""
        text_lower = text.lower()
        
        # Recruiters (highest priority)
        recruiter_keywords = [
            'recruiter', 'talent acquisition', 'talent partner',
            'campus recruit', 'university recruit', 'hiring',
            'staffing', 'talent scout'
        ]
        if any(kw in text_lower for kw in recruiter_keywords):
            return PersonCategory.RECRUITER
        
        # Managers
        if 'manager' in text_lower and not any(x in text_lower for x in ['senior manager', 'director', 'vp']):
            return PersonCategory.MANAGER
        
        # Senior
        if any(kw in text_lower for kw in ['senior', 'staff', 'principal', 'lead', 'architect']):
            return PersonCategory.SENIOR
        
        # Junior
        if any(kw in text_lower for kw in ['junior', 'associate', 'analyst', 'intern', 'entry']):
            return PersonCategory.PEER
        
        return PersonCategory.PEER
