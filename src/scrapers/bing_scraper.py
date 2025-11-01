"""Bing scraper implementation using base scraper"""

import re
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .base_scraper import BaseSearchScraper


class BingScraper(BaseSearchScraper):
    """
    Bing scraper - generally more lenient than Google.
    
    Features:
    - Better for high-volume searches
    - Good LinkedIn profile discovery
    - Less aggressive anti-bot measures
    """
    
    def __init__(self):
        # Bing is more forgiving
        super().__init__(name="bing", rate_limit=0.3, cache_ttl=3600)  # 1 req/3s
    
    def get_domain(self) -> str:
        """Bing domain"""
        return "bing.com"
    
    def build_search_url(self, query: str, **kwargs) -> str:
        """Build Bing search URL"""
        params = {
            'q': query,
            'count': kwargs.get('count', 30),
            'offset': kwargs.get('offset', 0),
            'cc': kwargs.get('cc', 'US'),
            'setlang': 'en',
            'freshness': kwargs.get('freshness', ''),  # Day, Week, Month
        }
        
        # Remove empty params
        params = {k: v for k, v in params.items() if v}
        
        param_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"https://www.bing.com/search?{param_str}"
    
    def parse_results(self, html: str, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Parse Bing search results"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Bing result structure
        result_items = soup.find_all('li', {'class': 'b_algo'})
        
        for item in result_items[:30]:
            result = self._parse_single_result(item)
            if result:
                results.append(result)
        
        # Alternative: look for h2 tags with links
        if not results:
            h2_tags = soup.find_all('h2')
            for h2 in h2_tags[:30]:
                link = h2.find('a', href=True)
                if link:
                    result = {
                        'url': link.get('href', ''),
                        'title': link.get_text(strip=True),
                        'snippet': '',
                        'source': 'bing',
                    }
                    results.append(result)
        
        return results
    
    def _parse_single_result(self, result_item) -> Optional[Dict[str, Any]]:
        """Parse a single Bing result"""
        try:
            # Find link in h2
            h2 = result_item.find('h2')
            if not h2:
                return None
            
            link = h2.find('a', href=True)
            if not link:
                return None
            
            url = link.get('href', '')
            title = link.get_text(strip=True)
            
            # Find snippet
            snippet = ""
            caption = result_item.find('div', {'class': 'b_caption'})
            if caption:
                p_tag = caption.find('p')
                if p_tag:
                    snippet = p_tag.get_text(strip=True)
                else:
                    # Sometimes snippet is directly in caption
                    snippet = caption.get_text(strip=True)
            
            return {
                'url': url,
                'title': title,
                'snippet': snippet,
                'source': 'bing',
            }
            
        except Exception as e:
            return None
    
    def is_blocked(self, response: requests.Response) -> bool:
        """Check if Bing is blocking us"""
        if response.status_code in [429, 403]:
            return True
        
        text_lower = response.text.lower()
        
        # Bing block indicators
        blocked_indicators = [
            'unusual traffic',
            'automated queries',
            'please enter the characters',
            'we have detected that this',
        ]
        
        return any(indicator in text_lower for indicator in blocked_indicators)
    
    def generate_advanced_queries(self, company: str, role: str) -> List[str]:
        """Generate Bing-specific advanced queries"""
        queries = []
        
        # Bing supports some unique operators
        queries.extend([
            f'site:linkedin.com/in/ "{company}" recruiter',
            f'site:linkedin.com/in/ "{company}" "hiring manager"',
            f'site:linkedin.com/in/ "{company}" filetype:html',
            f'"{company}" instreamset:(url):"linkedin.com/in/"',  # Bing-specific
            f'"{company}" contains:"recruiter" site:linkedin.com',
        ])
        
        # Use Bing's prefer operator for freshness
        queries.extend([
            f'site:linkedin.com/in/ "{company}" prefer:recent',
            f'"{company}" "just started" site:linkedin.com',
            f'"{company}" "excited to announce" site:linkedin.com',
        ])
        
        return queries
