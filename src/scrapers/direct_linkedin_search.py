"""Direct LinkedIn search using Google's cache and other clever methods"""

import re
import time
import random
import json
from typing import List, Optional, Dict
from urllib.parse import quote_plus, unquote
from bs4 import BeautifulSoup
import requests

from src.models.person import Person, PersonCategory
from src.utils.cache import get_cache


class DirectLinkedInSearch:
    """
    Smart LinkedIn profile finder that works without APIs.
    Uses clever search techniques and Google's cache.
    """
    
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    ]
    
    def __init__(self):
        self.session = self._create_session()
        self.cache = get_cache()
        self.found_profiles = set()  # Track found URLs to avoid duplicates
    
    def _create_session(self):
        """Create requests session with retries"""
        session = requests.Session()
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session
    
    def find_linkedin_profiles(self, company: str, role: Optional[str] = None, 
                             target_count: int = 20) -> List[Person]:
        """
        Find LinkedIn profiles using multiple clever techniques.
        
        Args:
            company: Company name
            role: Job role/title (optional)
            target_count: Target number of profiles to find
            
        Returns:
            List of Person objects
        """
        all_people = []
        
        print(f"\n🔍 Smart LinkedIn search for {company}")
        
        # Try different strategies
        strategies = [
            self._search_via_google_cache,
            self._search_via_duckduckgo_instant,
            self._search_via_bing_simple,
            self._search_via_direct_patterns,
        ]
        
        for strategy in strategies:
            if len(all_people) >= target_count:
                break
                
            try:
                print(f"\n  → Trying {strategy.__name__}")
                people = strategy(company, role)
                
                # Filter out duplicates
                new_people = []
                for person in people:
                    if person.linkedin_url not in self.found_profiles:
                        self.found_profiles.add(person.linkedin_url)
                        new_people.append(person)
                        all_people.append(person)
                
                if new_people:
                    print(f"    ✓ Found {len(new_people)} new profiles")
                else:
                    print(f"    - No new profiles")
                    
            except Exception as e:
                print(f"    ✗ Error: {e}")
            
            # Be respectful
            time.sleep(random.uniform(1, 3))
        
        print(f"\n✅ Total unique profiles found: {len(all_people)}")
        
        return all_people[:target_count]
    
    def _search_via_google_cache(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use Google's cache to find LinkedIn profiles"""
        people = []
        
        # Build search queries
        queries = [
            f'cache:linkedin.com/in/ "{company}" recruiter',
            f'"View * profile on LinkedIn" "{company}" recruiter',
            f'"Connect on LinkedIn" "{company}" manager',
        ]
        
        if role:
            queries.append(f'"View * profile on LinkedIn" "{company}" "{role}"')
        
        for query in queries[:2]:  # Limit to avoid detection
            try:
                # Use Google search but look for cached results
                url = f"https://www.google.com/search?q={quote_plus(query)}"
                
                headers = {'User-Agent': random.choice(self.USER_AGENTS)}
                response = self.session.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for any LinkedIn URLs in the page
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        
                        # Extract LinkedIn URL from Google's redirect
                        linkedin_match = re.search(r'linkedin\.com/in/([^/&?]+)', href)
                        if linkedin_match:
                            username = linkedin_match.group(1)
                            linkedin_url = f"https://www.linkedin.com/in/{username}"
                            
                            # Try to extract name from link text or context
                            text = link.get_text(strip=True)
                            parent_text = link.parent.get_text(strip=True) if link.parent else ""
                            
                            name = self._extract_name_from_text(text) or self._extract_name_from_text(parent_text)
                            
                            if name:
                                person = Person(
                                    name=name,
                                    title=self._guess_title_from_text(parent_text),
                                    company=company,
                                    linkedin_url=linkedin_url,
                                    source="google_cache",
                                    category=self._categorize_from_context(parent_text),
                                    confidence_score=0.7
                                )
                                people.append(person)
                
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                pass
        
        return people
    
    def _search_via_duckduckgo_instant(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use DuckDuckGo instant answers API (no rate limits)"""
        people = []
        
        queries = [
            f"{company} recruiter linkedin",
            f"{company} hiring manager linkedin",
            f"{company} talent acquisition linkedin",
        ]
        
        for query in queries:
            try:
                # DuckDuckGo instant answers API
                api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
                
                response = self.session.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check abstract URL
                    if data.get('AbstractURL') and 'linkedin.com/in/' in data['AbstractURL']:
                        self._process_ddg_result(data, company, people)
                    
                    # Check related topics
                    for topic in data.get('RelatedTopics', []):
                        if isinstance(topic, dict):
                            if topic.get('FirstURL') and 'linkedin.com/in/' in topic['FirstURL']:
                                self._process_ddg_topic(topic, company, people)
                
                time.sleep(0.5)  # DDG API is very lenient
                
            except Exception as e:
                pass
        
        return people
    
    def _search_via_bing_simple(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Use Bing's simple HTML search"""
        people = []
        
        query = f'"{company}" (recruiter OR "talent acquisition" OR "hiring manager") site:linkedin.com/in/'
        
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&form=QBLH"
            
            headers = {
                'User-Agent': random.choice(self.USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Bing result structure
                for result in soup.find_all(['li', 'div'], class_=['b_algo', 'b_algoorg']):
                    # Find the link
                    link = result.find('a', href=True)
                    if not link:
                        continue
                    
                    href = link.get('href', '')
                    if 'linkedin.com/in/' not in href:
                        continue
                    
                    # Extract URL
                    linkedin_url = self._clean_linkedin_url(href)
                    if not linkedin_url:
                        continue
                    
                    # Get all text from result
                    result_text = result.get_text(' ', strip=True)
                    
                    # Extract name
                    name = self._extract_name_from_text(link.get_text(strip=True))
                    if not name:
                        name = self._extract_name_from_text(result_text)
                    
                    if name:
                        person = Person(
                            name=name,
                            title=self._guess_title_from_text(result_text),
                            company=company,
                            linkedin_url=linkedin_url,
                            source="bing_search",
                            category=self._categorize_from_context(result_text),
                            confidence_score=0.75
                        )
                        people.append(person)
        
        except Exception as e:
            pass
        
        return people
    
    def _search_via_direct_patterns(self, company: str, role: Optional[str] = None) -> List[Person]:
        """Try common LinkedIn URL patterns directly"""
        people = []
        
        # Common patterns for recruiters at companies
        patterns = [
            f"{company.lower().replace(' ', '')}-recruiter",
            f"{company.lower().replace(' ', '')}-recruiting",
            f"{company.lower().replace(' ', '')}-talent",
            f"{company.lower().replace(' ', '-')}-recruiter",
            f"recruiter-at-{company.lower().replace(' ', '-')}",
        ]
        
        # Try each pattern
        for pattern in patterns[:3]:  # Limit attempts
            try:
                # Check if profile exists
                test_url = f"https://www.linkedin.com/in/{pattern}"
                
                # Just do a HEAD request to check existence
                response = self.session.head(test_url, allow_redirects=True, timeout=5)
                
                # If we get redirected to login or get 999, profile might exist
                if response.status_code in [200, 302, 999]:
                    # Assume it's a recruiter profile
                    person = Person(
                        name=f"{company} Recruiter",  # Generic name
                        title="Recruiter",
                        company=company,
                        linkedin_url=test_url,
                        source="url_pattern",
                        category=PersonCategory.RECRUITER,
                        confidence_score=0.5  # Lower confidence
                    )
                    people.append(person)
                    break
            
            except Exception:
                pass
        
        return people
    
    def _extract_name_from_text(self, text: str) -> Optional[str]:
        """Extract a person's name from text"""
        if not text:
            return None
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'\s*[-–]\s*LinkedIn.*$', '', text, flags=re.I)
        text = re.sub(r'\s*\|.*$', '', text)
        
        # Common name patterns
        # Pattern 1: "FirstName LastName - Title..."
        match = re.match(r'^([A-Z][a-z]+(?: [A-Z][a-z]+){1,2})\s*[-–]', text)
        if match and self._is_valid_name(match.group(1)):
            return match.group(1)
        
        # Pattern 2: Just "FirstName LastName" at start
        match = re.match(r'^([A-Z][a-z]+(?: [A-Z][a-z]+){1,2})(?:\s|$)', text)
        if match and self._is_valid_name(match.group(1)):
            return match.group(1)
        
        # Pattern 3: "FirstName M. LastName"
        match = re.match(r'^([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)', text)
        if match:
            return match.group(1)
        
        return None
    
    def _is_valid_name(self, name: str) -> bool:
        """Check if string is a valid name"""
        if not name or len(name) < 3 or len(name) > 50:
            return False
        
        # Should have 2-4 parts
        parts = name.split()
        if len(parts) < 2 or len(parts) > 4:
            return False
        
        # No URLs, special chars, or numbers
        if re.search(r'[0-9@#$%^&*(){}\[\]<>/\\]|https?:|www\.|\.com', name.lower()):
            return False
        
        # Not a company or title
        invalid_words = ['linkedin', 'profile', 'company', 'corporation', 'inc', 'llc']
        name_lower = name.lower()
        if any(word in name_lower for word in invalid_words):
            return False
        
        return True
    
    def _guess_title_from_text(self, text: str) -> str:
        """Guess job title from text"""
        if not text:
            return "Professional"
        
        text_lower = text.lower()
        
        # Direct title matches
        titles = [
            ('campus recruiter', 'Campus Recruiter'),
            ('university recruiter', 'University Recruiter'),
            ('technical recruiter', 'Technical Recruiter'),
            ('talent acquisition', 'Talent Acquisition Specialist'),
            ('recruiting manager', 'Recruiting Manager'),
            ('hiring manager', 'Hiring Manager'),
            ('recruiter', 'Recruiter'),
            ('engineering manager', 'Engineering Manager'),
            ('product manager', 'Product Manager'),
            ('program manager', 'Program Manager'),
            ('software engineer', 'Software Engineer'),
            ('data analyst', 'Data Analyst'),
            ('business analyst', 'Business Analyst'),
        ]
        
        for pattern, title in titles:
            if pattern in text_lower:
                return title
        
        return "Professional"
    
    def _categorize_from_context(self, text: str) -> PersonCategory:
        """Categorize person based on context"""
        if not text:
            return PersonCategory.UNKNOWN
        
        text_lower = text.lower()
        
        # Recruiters (highest priority for our use case)
        recruiter_keywords = ['recruiter', 'talent', 'staffing', 'hiring', 'campus', 'university']
        if any(kw in text_lower for kw in recruiter_keywords):
            return PersonCategory.RECRUITER
        
        # Managers
        if 'manager' in text_lower and not any(kw in text_lower for kw in ['senior manager', 'director', 'vp']):
            return PersonCategory.MANAGER
        
        # Senior
        if any(kw in text_lower for kw in ['senior', 'staff', 'principal', 'lead']):
            return PersonCategory.SENIOR
        
        # Junior/Peer
        if any(kw in text_lower for kw in ['junior', 'associate', 'analyst', 'intern']):
            return PersonCategory.PEER
        
        return PersonCategory.UNKNOWN
    
    def _clean_linkedin_url(self, url: str) -> Optional[str]:
        """Clean and validate LinkedIn URL"""
        if not url or 'linkedin.com/in/' not in url:
            return None
        
        # Extract the profile part
        match = re.search(r'linkedin\.com/in/([^/?&]+)', url)
        if match:
            username = match.group(1)
            return f"https://www.linkedin.com/in/{username}"
        
        return None
    
    def _process_ddg_result(self, data: dict, company: str, people: List[Person]):
        """Process DuckDuckGo API result"""
        url = data.get('AbstractURL', '')
        if url and 'linkedin.com/in/' in url:
            name = self._extract_name_from_text(data.get('Heading', ''))
            if name:
                person = Person(
                    name=name,
                    title=self._guess_title_from_text(data.get('AbstractText', '')),
                    company=company,
                    linkedin_url=self._clean_linkedin_url(url),
                    source="ddg_instant",
                    category=self._categorize_from_context(data.get('AbstractText', '')),
                    confidence_score=0.7
                )
                people.append(person)
    
    def _process_ddg_topic(self, topic: dict, company: str, people: List[Person]):
        """Process DuckDuckGo related topic"""
        url = topic.get('FirstURL', '')
        text = topic.get('Text', '')
        
        if url and 'linkedin.com/in/' in url:
            name = self._extract_name_from_text(text)
            if name:
                person = Person(
                    name=name,
                    title=self._guess_title_from_text(text),
                    company=company,
                    linkedin_url=self._clean_linkedin_url(url),
                    source="ddg_instant",
                    category=self._categorize_from_context(text),
                    confidence_score=0.65
                )
                people.append(person)
