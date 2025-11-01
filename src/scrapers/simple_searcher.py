"""Simple, working search scrapers that actually return results"""

import re
import time
import json
import random
from typing import List, Dict, Optional
from urllib.parse import quote, quote_plus, urlencode
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models.person import Person, PersonCategory
from src.utils.cache import get_cache


class WorkingSearcher:
    """Simple searcher that actually works by using better strategies"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    ]
    
    def __init__(self):
        self.session = self._create_session()
        self.cache = get_cache()
    
    def _create_session(self):
        """Create a session with retry logic"""
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.3)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def search_linkedin_profiles(self, company: str, role: str = None) -> List[Person]:
        """Search for LinkedIn profiles using multiple strategies"""
        all_people = []
        
        # Try different search strategies
        strategies = [
            self._search_duckduckgo_lite,
            self._search_startpage,
            self._search_brave,
        ]
        
        for strategy in strategies:
            try:
                people = strategy(company, role)
                if people:
                    all_people.extend(people)
                    print(f"✓ {strategy.__name__} found {len(people)} profiles")
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"⚠️ {strategy.__name__} failed: {e}")
        
        # Deduplicate
        unique_people = self._deduplicate(all_people)
        
        return unique_people
    
    def _search_duckduckgo_lite(self, company: str, role: str = None) -> List[Person]:
        """Use DuckDuckGo Lite (no JS required)"""
        people = []
        
        # Build queries without site: operator
        queries = [
            f'"{company}" recruiter linkedin',
            f'"{company}" "talent acquisition" linkedin',
            f'"{company}" "campus recruiter" linkedin',
            f'"{company}" manager linkedin profile',
        ]
        
        if role:
            queries.append(f'"{company}" "{role}" linkedin')
        
        for query in queries[:3]:  # Limit queries
            try:
                # DuckDuckGo Lite URL
                url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
                
                headers = {
                    'User-Agent': random.choice(self.USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                response = self.session.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # DuckDuckGo Lite has simple structure
                    results = soup.find_all('a', {'class': 'result-link'})
                    
                    for link in results[:10]:
                        person = self._extract_person_from_link(link, company)
                        if person:
                            people.append(person)
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                print(f"⚠️ DDG Lite error: {e}")
        
        return people
    
    def _search_startpage(self, company: str, role: str = None) -> List[Person]:
        """Use StartPage (privacy-focused, less blocking)"""
        people = []
        
        queries = [
            f'"{company}" recruiter site:linkedin.com',
            f'"{company}" "hiring manager" linkedin',
        ]
        
        for query in queries[:2]:
            try:
                url = "https://www.startpage.com/do/search"
                params = {
                    'q': query,
                    'cat': 'web',
                    'language': 'english'
                }
                
                headers = {
                    'User-Agent': random.choice(self.USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.startpage.com/',
                }
                
                response = self.session.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find result containers
                    results = soup.find_all('div', {'class': 'result'})
                    if not results:
                        results = soup.find_all('div', {'class': 'w-gl__result'})
                    
                    for result in results[:10]:
                        # Extract URL and title
                        link_elem = result.find('a', {'class': ['result-link', 'w-gl__result-url']})
                        if link_elem and 'linkedin.com' in str(link_elem.get('href', '')):
                            person = self._extract_person_from_result(result, company)
                            if person:
                                people.append(person)
                
                time.sleep(random.uniform(2, 3))
                
            except Exception as e:
                print(f"⚠️ StartPage error: {e}")
        
        return people
    
    def _search_brave(self, company: str, role: str = None) -> List[Person]:
        """Use Brave Search (has good LinkedIn results)"""
        people = []
        
        query = f'"{company}" recruiter OR manager site:linkedin.com/in/'
        
        try:
            url = "https://search.brave.com/search"
            params = {
                'q': query,
                'source': 'web'
            }
            
            headers = {
                'User-Agent': random.choice(self.USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Brave results structure
                results = soup.find_all('div', {'class': 'snippet'})
                
                for result in results[:15]:
                    link = result.find('a')
                    if link and 'linkedin.com/in/' in str(link.get('href', '')):
                        person = self._extract_person_from_brave_result(result, company)
                        if person:
                            people.append(person)
            
        except Exception as e:
            print(f"⚠️ Brave error: {e}")
        
        return people
    
    def _extract_person_from_link(self, link_elem, company: str) -> Optional[Person]:
        """Extract person from a simple link element"""
        try:
            url = link_elem.get('href', '')
            text = link_elem.get_text(strip=True)
            
            if 'linkedin.com/in/' not in url:
                return None
            
            # Extract name from link text (usually "Name - Title - Company | LinkedIn")
            name = self._extract_name(text)
            if not name:
                return None
            
            # Guess title from text
            title = self._guess_title(text)
            
            # Categorize
            category = self._categorize_from_text(text)
            
            return Person(
                name=name,
                title=title or "Professional",
                company=company,
                linkedin_url=url,
                source="search",
                category=category,
                confidence_score=0.7
            )
            
        except Exception:
            return None
    
    def _extract_person_from_result(self, result_div, company: str) -> Optional[Person]:
        """Extract person from a result div"""
        try:
            # Find link
            link = result_div.find('a', href=True)
            if not link or 'linkedin.com/in/' not in link.get('href', ''):
                return None
            
            url = link.get('href', '')
            
            # Find title/description
            title_elem = result_div.find(['h3', 'h4', 'a'])
            title_text = title_elem.get_text(strip=True) if title_elem else ""
            
            # Find snippet
            snippet = result_div.get_text(strip=True)
            
            # Extract name
            name = self._extract_name(title_text or snippet)
            if not name:
                return None
            
            # Extract job title
            job_title = self._guess_title(snippet)
            
            # Categorize
            category = self._categorize_from_text(snippet)
            
            return Person(
                name=name,
                title=job_title or "Professional",
                company=company,
                linkedin_url=url,
                source="search",
                category=category,
                confidence_score=0.75
            )
            
        except Exception:
            return None
    
    def _extract_person_from_brave_result(self, result_div, company: str) -> Optional[Person]:
        """Extract person from Brave search result"""
        try:
            # Find the link
            link = result_div.find('a', href=True)
            if not link:
                return None
            
            url = link.get('href', '')
            if 'linkedin.com/in/' not in url:
                return None
            
            # Get all text
            full_text = result_div.get_text(strip=True)
            
            # Extract name
            name = self._extract_name(full_text)
            if not name:
                return None
            
            # Extract title
            title = self._guess_title(full_text)
            
            # Categorize
            category = self._categorize_from_text(full_text)
            
            return Person(
                name=name,
                title=title or "Professional",
                company=company,
                linkedin_url=url,
                source="brave_search",
                category=category,
                confidence_score=0.7
            )
            
        except Exception:
            return None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract a name from text"""
        # Clean common suffixes
        text = re.sub(r'\s*[-–|]\s*LinkedIn.*$', '', text, flags=re.I)
        text = re.sub(r'\s*\|.*$', '', text)
        
        # Common patterns
        patterns = [
            r'^([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # First Last
            r'^([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)',  # First M. Last
            r'^([A-Z][a-z]+ [A-Z][a-z]+-[A-Z][a-z]+)',  # First Last-Last
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                name = match.group(1)
                if self._is_valid_name(name):
                    return name
        
        # Try splitting by common separators
        for sep in [' - ', ' – ', ' — ', ' | ']:
            if sep in text:
                parts = text.split(sep)
                potential_name = parts[0].strip()
                if self._is_valid_name(potential_name):
                    return potential_name
        
        return None
    
    def _is_valid_name(self, name: str) -> bool:
        """Check if string is a valid name"""
        if not name or len(name) < 3 or len(name) > 50:
            return False
        
        # Should have 2-4 parts
        parts = name.split()
        if len(parts) < 2 or len(parts) > 4:
            return False
        
        # No numbers or special chars
        if re.search(r'[\d@#$%^&*()]', name):
            return False
        
        # No common non-name words
        non_names = ['linkedin', 'profile', 'professional', 'view', 'sign', 'join']
        name_lower = name.lower()
        if any(word in name_lower for word in non_names):
            return False
        
        return True
    
    def _guess_title(self, text: str) -> Optional[str]:
        """Guess job title from text"""
        text_lower = text.lower()
        
        # Direct title patterns
        title_patterns = [
            (r'recruiter', 'Recruiter'),
            (r'talent acquisition', 'Talent Acquisition Specialist'),
            (r'campus recruiter', 'Campus Recruiter'),
            (r'university recruiter', 'University Recruiter'),
            (r'hiring manager', 'Hiring Manager'),
            (r'engineering manager', 'Engineering Manager'),
            (r'product manager', 'Product Manager'),
            (r'software engineer', 'Software Engineer'),
            (r'business analyst', 'Business Analyst'),
            (r'data analyst', 'Data Analyst'),
            (r'manager', 'Manager'),
        ]
        
        for pattern, title in title_patterns:
            if pattern in text_lower:
                return title
        
        return None
    
    def _categorize_from_text(self, text: str) -> PersonCategory:
        """Categorize person based on text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['recruiter', 'talent acquisition', 'campus recruit']):
            return PersonCategory.RECRUITER
        elif any(word in text_lower for word in ['manager', 'lead', 'head of']):
            return PersonCategory.MANAGER
        elif any(word in text_lower for word in ['senior', 'staff', 'principal']):
            return PersonCategory.SENIOR
        elif any(word in text_lower for word in ['intern', 'junior', 'associate', 'analyst']):
            return PersonCategory.PEER
        
        return PersonCategory.UNKNOWN
    
    def _deduplicate(self, people: List[Person]) -> List[Person]:
        """Remove duplicate people"""
        seen_names = set()
        seen_urls = set()
        unique = []
        
        for person in people:
            name_key = person.name.lower()
            url_key = person.linkedin_url
            
            if name_key not in seen_names and url_key not in seen_urls:
                seen_names.add(name_key)
                seen_urls.add(url_key)
                unique.append(person)
        
        return unique
