"""Browser-based scraper using Playwright for when simple requests fail"""

import re
import time
import random
from typing import List, Optional
from urllib.parse import quote_plus

from src.models.person import Person, PersonCategory
from src.utils.stealth_browser import StealthBrowser
from src.utils.cache import get_cache


class PlaywrightScraper:
    """Use real browser automation when other methods fail"""
    
    def __init__(self):
        self.browser = None
        self.cache = get_cache()
    
    def search_linkedin_profiles(self, company: str, role: str = None) -> List[Person]:
        """Search using browser automation"""
        all_people = []
        
        try:
            # Initialize browser
            self.browser = StealthBrowser()
            
            # Try different search engines
            engines = [
                self._search_duckduckgo_browser,
                self._search_bing_browser,
            ]
            
            for engine in engines:
                try:
                    people = engine(company, role)
                    if people:
                        all_people.extend(people)
                        print(f"✓ {engine.__name__} found {len(people)} profiles via browser")
                except Exception as e:
                    print(f"⚠️ {engine.__name__} browser error: {e}")
                
                # Random delay between engines
                time.sleep(random.uniform(3, 6))
            
        finally:
            if self.browser:
                self.browser.close()
        
        # Deduplicate
        unique_people = self._deduplicate(all_people)
        
        return unique_people
    
    def _search_duckduckgo_browser(self, company: str, role: str = None) -> List[Person]:
        """Search DuckDuckGo using browser"""
        people = []
        
        queries = [
            f'"{company}" recruiter linkedin',
            f'"{company}" "talent acquisition" linkedin',
            f'"{company}" manager linkedin profile',
        ]
        
        for query in queries[:2]:
            try:
                # Navigate to DuckDuckGo
                page = self.browser.new_page()
                page.goto('https://duckduckgo.com', wait_until='domcontentloaded')
                
                # Wait for search box
                search_box = page.wait_for_selector('input[name="q"]', timeout=5000)
                
                # Type query
                search_box.type(query, delay=random.randint(50, 150))
                
                # Submit search
                search_box.press('Enter')
                
                # Wait for results
                page.wait_for_selector('.results', timeout=10000)
                
                # Extract results
                results = page.query_selector_all('.result')
                
                for result in results[:15]:
                    try:
                        # Get link
                        link = result.query_selector('a.result__a')
                        if not link:
                            continue
                        
                        url = link.get_attribute('href')
                        if not url or 'linkedin.com/in/' not in url:
                            continue
                        
                        # Get text
                        text = result.inner_text()
                        
                        # Extract person
                        person = self._extract_person(text, url, company)
                        if person:
                            people.append(person)
                    
                    except Exception:
                        continue
                
                page.close()
                
                # Random delay
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"⚠️ DDG browser error on query '{query}': {e}")
        
        return people
    
    def _search_bing_browser(self, company: str, role: str = None) -> List[Person]:
        """Search Bing using browser"""
        people = []
        
        query = f'"{company}" recruiter OR manager site:linkedin.com/in/'
        
        try:
            # Navigate to Bing
            page = self.browser.new_page()
            page.goto('https://www.bing.com', wait_until='domcontentloaded')
            
            # Find search box
            search_box = page.wait_for_selector('input[name="q"]', timeout=5000)
            
            # Type and search
            search_box.type(query, delay=random.randint(50, 150))
            search_box.press('Enter')
            
            # Wait for results
            page.wait_for_selector('.b_algo', timeout=10000)
            
            # Extract results
            results = page.query_selector_all('.b_algo')
            
            for result in results[:15]:
                try:
                    # Get link
                    link = result.query_selector('h2 a')
                    if not link:
                        continue
                    
                    url = link.get_attribute('href')
                    if not url or 'linkedin.com/in/' not in url:
                        continue
                    
                    # Get text
                    text = result.inner_text()
                    
                    # Extract person
                    person = self._extract_person(text, url, company)
                    if person:
                        people.append(person)
                
                except Exception:
                    continue
            
            page.close()
            
        except Exception as e:
            print(f"⚠️ Bing browser error: {e}")
        
        return people
    
    def _extract_person(self, text: str, url: str, company: str) -> Optional[Person]:
        """Extract person from search result text"""
        try:
            # Extract name
            name = self._extract_name(text)
            if not name:
                return None
            
            # Extract title
            title = self._guess_title(text)
            
            # Categorize
            category = self._categorize_from_text(text)
            
            return Person(
                name=name,
                title=title or "Professional",
                company=company,
                linkedin_url=url,
                source="browser_search",
                category=category,
                confidence_score=0.8
            )
            
        except Exception:
            return None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract name from text"""
        # Remove LinkedIn suffix
        text = re.sub(r'\s*[-–|]\s*LinkedIn.*$', '', text, flags=re.I)
        
        # Look for name pattern at start
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            
            # Check if it looks like a name
            if self._is_valid_name(first_line):
                return first_line
            
            # Try splitting by separators
            for sep in [' - ', ' – ', ' — ', ' | ']:
                if sep in first_line:
                    parts = first_line.split(sep)
                    if parts and self._is_valid_name(parts[0].strip()):
                        return parts[0].strip()
        
        return None
    
    def _is_valid_name(self, name: str) -> bool:
        """Check if string is valid name"""
        if not name or len(name) < 3 or len(name) > 50:
            return False
        
        parts = name.split()
        if len(parts) < 2 or len(parts) > 4:
            return False
        
        # Should start with capital letter
        if not name[0].isupper():
            return False
        
        # No URLs, emails, or special chars
        if re.search(r'[@#$%^&*()\[\]{}\\/<>]|https?:|\.com|\.org', name):
            return False
        
        return True
    
    def _guess_title(self, text: str) -> Optional[str]:
        """Guess title from text"""
        text_lower = text.lower()
        
        # Title keywords
        titles = {
            'recruiter': 'Recruiter',
            'talent acquisition': 'Talent Acquisition',
            'campus recruiter': 'Campus Recruiter',
            'hiring manager': 'Hiring Manager',
            'engineering manager': 'Engineering Manager',
            'product manager': 'Product Manager',
            'software engineer': 'Software Engineer',
            'analyst': 'Analyst',
        }
        
        for keyword, title in titles.items():
            if keyword in text_lower:
                return title
        
        return None
    
    def _categorize_from_text(self, text: str) -> PersonCategory:
        """Categorize based on text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['recruiter', 'talent', 'campus']):
            return PersonCategory.RECRUITER
        elif 'manager' in text_lower:
            return PersonCategory.MANAGER
        elif any(word in text_lower for word in ['senior', 'staff', 'principal']):
            return PersonCategory.SENIOR
        elif any(word in text_lower for word in ['junior', 'intern', 'analyst']):
            return PersonCategory.PEER
        
        return PersonCategory.UNKNOWN
    
    def _deduplicate(self, people: List[Person]) -> List[Person]:
        """Remove duplicates"""
        seen = set()
        unique = []
        
        for person in people:
            key = (person.name.lower(), person.linkedin_url)
            if key not in seen:
                seen.add(key)
                unique.append(person)
        
        return unique
