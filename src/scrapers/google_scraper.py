"""Elite Google scraper implementation using base scraper"""

import re
import random
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .base_scraper import BaseSearchScraper


class GoogleScraper(BaseSearchScraper):
    """
    Production-ready Google scraper with advanced anti-detection.
    
    Features:
    - Multiple Google domains for rotation
    - Advanced query generation
    - Smart result parsing
    - Anti-CAPTCHA measures
    """
    
    # Google domains for geographic distribution
    DOMAINS = [
        'google.com',
        'google.co.uk',
        'google.ca',
        'google.com.au',
        'google.co.nz',
        'google.ie',
        'google.co.za',
    ]
    
    def __init__(self):
        # Google needs very conservative rate limiting
        super().__init__(name="google", rate_limit=0.1, cache_ttl=7200)  # 1 req/10s, 2hr cache
        self.domain_index = 0
    
    def get_domain(self) -> str:
        """Rotate through Google domains"""
        domain = self.DOMAINS[self.domain_index % len(self.DOMAINS)]
        self.domain_index += 1
        return domain
    
    def build_search_url(self, query: str, **kwargs) -> str:
        """Build Google search URL with natural-looking parameters"""
        params = {
            'q': query,
            'num': kwargs.get('num', 20),
            'hl': 'en',
            'gl': kwargs.get('gl', 'us'),
            'lr': 'lang_en',
            'safe': 'off',
            'filter': '0',  # Don't filter similar results
        }
        
        # Add some randomization
        if random.random() > 0.5:
            params['gbv'] = '1'  # Basic HTML version sometimes
        
        param_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"https://www.{self.get_domain()}/search?{param_str}"
    
    def parse_results(self, html: str, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Parse Google search results"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all result divs
        result_divs = soup.find_all('div', {'class': 'g'})
        
        for div in result_divs[:30]:  # Limit to 30 results
            result = self._parse_single_result(div)
            if result:
                results.append(result)
        
        # If no results with 'g' class, try alternative selectors
        if not results:
            # Try data-hveid attribute (Google's result identifier)
            result_divs = soup.find_all('div', {'data-hveid': True})
            for div in result_divs[:30]:
                if div.find('a', href=True) and div.find(['h3', 'div']):
                    result = self._parse_single_result(div)
                    if result:
                        results.append(result)
        
        return results
    
    def _parse_single_result(self, result_div) -> Optional[Dict[str, Any]]:
        """Parse a single Google result"""
        try:
            # Find link
            link_elem = result_div.find('a', href=True)
            if not link_elem:
                return None
            
            url = link_elem.get('href', '')
            
            # Skip Google's internal links
            if url.startswith('/search?') or 'google.com' in url:
                return None
            
            # Find title
            title_elem = result_div.find(['h3', 'div'], class_=re.compile(r'.*'))
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Find snippet
            snippet = ""
            snippet_elem = result_div.find('div', {'data-sncf': '1'})
            if not snippet_elem:
                # Try alternative selectors
                snippet_elem = result_div.find('div', class_=re.compile(r'VwiC3b|yXK7lf|lEBKkf'))
                if not snippet_elem:
                    snippet_elem = result_div.find('span', class_=re.compile(r'.*'))
            
            if snippet_elem:
                snippet = snippet_elem.get_text(strip=True)
            
            return {
                'url': url,
                'title': title,
                'snippet': snippet,
                'source': 'google',
            }
            
        except Exception as e:
            return None
    
    def is_blocked(self, response: requests.Response) -> bool:
        """Check if Google is blocking us"""
        if response.status_code == 429:
            return True
        
        text_lower = response.text.lower()
        
        # Check for CAPTCHA or unusual traffic messages
        blocked_indicators = [
            'unusual traffic',
            'captcha',
            'recaptcha',
            'sorry, we have detected unusual traffic',
            'please show you\'re not a robot',
            'suspicious activity',
        ]
        
        return any(indicator in text_lower for indicator in blocked_indicators)
    
    def generate_linkedin_queries(self, company: str, role: str, 
                                 department: Optional[str] = None) -> List[str]:
        """Generate LinkedIn-focused search queries"""
        queries = []
        
        # Basic LinkedIn searches
        queries.extend([
            f'site:linkedin.com/in/ "{company}" recruiter',
            f'site:linkedin.com/in/ "{company}" "talent acquisition"',
            f'site:linkedin.com/in/ "{company}" "campus recruiter"',
            f'site:linkedin.com/in/ "{company}" "university relations"',
            f'site:linkedin.com/in/ "{company}" "early career"',
        ])
        
        # Role-specific searches
        if role:
            base_role = re.sub(r'\b(junior|senior|staff|principal|lead)\b', '', role, flags=re.I).strip()
            queries.extend([
                f'site:linkedin.com/in/ "{company}" "{base_role}" manager',
                f'site:linkedin.com/in/ "{company}" "{base_role}" team lead',
                f'site:linkedin.com/in/ "{company}" hiring manager "{base_role}"',
            ])
        
        # Department-specific if provided
        if department:
            queries.extend([
                f'site:linkedin.com/in/ "{company}" "{department}" manager',
                f'site:linkedin.com/in/ "{company}" "{department}" lead',
            ])
        
        # Recent graduate searches
        current_year = 2024
        for year in range(current_year - 4, current_year + 1):
            queries.append(f'site:linkedin.com/in/ "{company}" "class of {year}"')
        
        # Advanced patterns
        queries.extend([
            f'intitle:"{company}" "linkedin.com/in/" recruiter',
            f'"{company}" site:linkedin.com/in/ "we\'re hiring"',
            f'"{company}" site:linkedin.com/in/ "join our team"',
        ])
        
        return queries
