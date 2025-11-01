"""DuckDuckGo scraper implementation using base scraper"""

import re
import json
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .base_scraper import BaseSearchScraper


class DuckDuckGoScraper(BaseSearchScraper):
    """
    DuckDuckGo scraper - privacy-focused, no rate limits.
    
    Features:
    - No official rate limits
    - Privacy-focused (no tracking)
    - Good for high-volume searches
    - HTML interface more stable than API
    """
    
    def __init__(self):
        # DDG has no official rate limits but be respectful
        super().__init__(name="duckduckgo", rate_limit=0.5, cache_ttl=3600)
    
    def get_domain(self) -> str:
        """DuckDuckGo domain"""
        return "duckduckgo.com"
    
    def build_search_url(self, query: str, **kwargs) -> str:
        """Build DuckDuckGo search URL"""
        # Use HTML interface for stability
        params = {
            'q': query,
            's': kwargs.get('offset', '0'),  # Start offset
            'dc': kwargs.get('dc', ''),      # Country code
            'kl': 'us-en',                    # Region
            'kp': '-2',                       # Safe search off
        }
        
        # Remove empty params
        params = {k: v for k, v in params.items() if v}
        
        param_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"https://html.duckduckgo.com/html/?{param_str}"
    
    def parse_results(self, html: str, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo search results"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # DDG HTML results structure
        result_items = soup.find_all('div', {'class': ['result', 'results_links_deep']})
        
        for item in result_items[:30]:
            result = self._parse_single_result(item)
            if result:
                results.append(result)
        
        # Alternative structure
        if not results:
            # Sometimes results are in a table
            result_rows = soup.find_all('tr')
            for row in result_rows[:30]:
                if row.find('a', {'class': 'result__a'}):
                    result = self._parse_table_result(row)
                    if result:
                        results.append(result)
        
        return results
    
    def _parse_single_result(self, result_div) -> Optional[Dict[str, Any]]:
        """Parse a single DDG result"""
        try:
            # Find link
            link = result_div.find('a', {'class': ['result__a', 'result-link']})
            if not link:
                return None
            
            url = link.get('href', '')
            title = link.get_text(strip=True)
            
            # Find snippet
            snippet = ""
            snippet_elem = result_div.find('a', {'class': 'result__snippet'})
            if not snippet_elem:
                snippet_elem = result_div.find('div', {'class': 'result__snippet'})
            
            if snippet_elem:
                snippet = snippet_elem.get_text(strip=True)
            
            return {
                'url': url,
                'title': title,
                'snippet': snippet,
                'source': 'duckduckgo',
            }
            
        except Exception as e:
            return None
    
    def _parse_table_result(self, result_row) -> Optional[Dict[str, Any]]:
        """Parse result from table structure"""
        try:
            link = result_row.find('a', {'class': 'result__a'})
            if not link:
                return None
            
            url = link.get('href', '')
            title = link.get_text(strip=True)
            
            # Find snippet in next td
            snippet_td = result_row.find('td', {'class': 'result__snippet'})
            snippet = snippet_td.get_text(strip=True) if snippet_td else ""
            
            return {
                'url': url,
                'title': title,
                'snippet': snippet,
                'source': 'duckduckgo',
            }
            
        except Exception as e:
            return None
    
    def is_blocked(self, response: requests.Response) -> bool:
        """Check if DuckDuckGo is blocking us (rare)"""
        if response.status_code in [429, 403]:
            return True
        
        # DDG rarely blocks but check for maintenance
        text_lower = response.text.lower()
        blocked_indicators = [
            'please wait while we check',
            'maintenance',
            'temporarily unavailable',
        ]
        
        return any(indicator in text_lower for indicator in blocked_indicators)
    
    def search_with_instant_answers(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Try to get DDG's instant answers (structured data).
        This can sometimes return direct LinkedIn profiles.
        """
        try:
            # DDG's API endpoint for instant answers
            api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
            
            response = self._make_request(api_url)
            if response:
                data = response.json()
                
                # Check for relevant instant answer types
                if data.get('AbstractURL') and 'linkedin.com' in data['AbstractURL']:
                    return {
                        'type': 'instant_answer',
                        'url': data['AbstractURL'],
                        'title': data.get('Heading', ''),
                        'abstract': data.get('AbstractText', ''),
                    }
                
                # Check RelatedTopics
                for topic in data.get('RelatedTopics', []):
                    if isinstance(topic, dict) and topic.get('FirstURL'):
                        if 'linkedin.com' in topic['FirstURL']:
                            return {
                                'type': 'related_topic',
                                'url': topic['FirstURL'],
                                'text': topic.get('Text', ''),
                            }
        
        except Exception as e:
            pass
        
        return None
