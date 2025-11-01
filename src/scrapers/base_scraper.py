"""Base scraper class with best practices and reusable patterns"""

import re
import time
import random
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import quote_plus, urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.cache import get_cache
from src.utils.rate_limiter import get_rate_limiter
from src.utils.proxy_manager import get_proxy_manager


class BaseSearchScraper(ABC):
    """
    Abstract base scraper with production-ready features:
    - Smart rate limiting with exponential backoff
    - Proxy rotation support
    - User agent rotation
    - Caching with TTL
    - Anti-detection measures
    - Error handling and retry logic
    - Result parsing abstraction
    """
    
    # Default user agents - can be overridden
    USER_AGENTS = [
        # Chrome Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        # Chrome Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        # Firefox Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        # Firefox Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) Gecko/20100101 Firefox/121.0',
        # Safari
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        # Edge
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    ]
    
    # Common headers that make requests look more natural
    BASE_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    def __init__(self, name: str, rate_limit: float = 0.5, cache_ttl: int = 3600):
        """
        Initialize base scraper.
        
        Args:
            name: Scraper name for logging and rate limiting
            rate_limit: Requests per second (default 0.5 = 1 request per 2 seconds)
            cache_ttl: Cache time-to-live in seconds (default 1 hour)
        """
        self.name = name
        self.cache = get_cache()
        self.rate_limiter = get_rate_limiter()
        self.proxy_manager = get_proxy_manager()
        
        # Configure rate limiting
        self.rate_limiter.configure(name, requests_per_second=rate_limit)
        
        # Cache configuration
        self.cache_ttl = cache_ttl
        
        # Session management
        self._session = None
        self._session_requests = 0
        self._max_session_requests = 10  # Rotate session after N requests
        
        # Anti-detection
        self._last_request_time = 0
        self._request_count = 0
        self._backoff_until = 0
        
    @property
    def session(self) -> requests.Session:
        """Get or create session with retry logic"""
        if self._session is None or self._session_requests >= self._max_session_requests:
            if self._session:
                self._session.close()
            
            self._session = requests.Session()
            
            # Add retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            
            # Set proxy if available
            if self.proxy_manager.is_configured():
                proxy_dict = self.proxy_manager.get_proxy_dict()
                if proxy_dict:
                    self._session.proxies.update(proxy_dict)
            
            self._session_requests = 0
        
        return self._session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get randomized headers for request"""
        headers = self.BASE_HEADERS.copy()
        headers['User-Agent'] = random.choice(self.USER_AGENTS)
        
        # Add some randomization
        if random.random() > 0.5:
            headers['Referer'] = f'https://www.{self.get_domain()}/'
        
        return headers
    
    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with anti-detection measures"""
        # Check if we're in backoff period
        if time.time() < self._backoff_until:
            wait_time = self._backoff_until - time.time()
            print(f"⏳ {self.name}: In backoff period, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        
        # Rate limiting
        self.rate_limiter.wait_if_needed(self.name)
        
        # Add random delay
        delay = random.uniform(1.5, 4.0)
        time.sleep(delay)
        
        # Get headers if not provided
        if 'headers' not in kwargs:
            kwargs['headers'] = self._get_headers()
        
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
        
        try:
            response = self.session.get(url, **kwargs)
            self._session_requests += 1
            self._request_count += 1
            
            # Check for blocks
            if self.is_blocked(response):
                self._handle_block(response)
                return None
            
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ {self.name} request error: {e}")
            return None
    
    def _handle_block(self, response: requests.Response):
        """Handle detected blocks with exponential backoff"""
        print(f"🚫 {self.name}: Detected block (status {response.status_code})")
        
        # Exponential backoff
        backoff_base = 30  # Start with 30 seconds
        backoff_multiplier = min(2 ** (self._request_count // 10), 8)  # Max 8x
        backoff_time = backoff_base * backoff_multiplier + random.uniform(0, 30)
        
        self._backoff_until = time.time() + backoff_time
        print(f"⏰ {self.name}: Backing off for {backoff_time:.0f} seconds")
        
        # Reset session
        self._session = None
        
        # Rotate proxy if available
        if self.proxy_manager.is_configured():
            self.proxy_manager.get_proxy(rotate=True)
            print(f"🔄 {self.name}: Rotated to next proxy")
    
    def _get_cache_key(self, query: str, **kwargs) -> str:
        """Generate cache key from query and parameters"""
        # Create stable hash from query and kwargs
        key_data = {
            'query': query,
            'scraper': self.name,
            **kwargs
        }
        key_str = str(sorted(key_data.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def search(self, query: str, max_results: int = 30, **kwargs) -> List[Dict[str, Any]]:
        """
        Main search method with caching.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            **kwargs: Additional search parameters
            
        Returns:
            List of result dictionaries
        """
        # Check cache
        cache_key = self._get_cache_key(query, **kwargs)
        cached = self.cache.get(self.name, {'key': cache_key})
        if cached:
            print(f"💾 {self.name}: Using cached results for '{query}'")
            return cached[:max_results]
        
        # Build search URL
        search_url = self.build_search_url(query, **kwargs)
        
        # Make request
        response = self._make_request(search_url)
        if not response:
            return []
        
        # Parse results
        results = self.parse_results(response.text, query, **kwargs)
        
        # Cache results
        if results:
            self.cache.set(self.name, {'key': cache_key}, results)
            print(f"✅ {self.name}: Found {len(results)} results for '{query}'")
        else:
            print(f"⚠️ {self.name}: No results for '{query}'")
        
        return results[:max_results]
    
    @abstractmethod
    def get_domain(self) -> str:
        """Get the search engine domain"""
        pass
    
    @abstractmethod
    def build_search_url(self, query: str, **kwargs) -> str:
        """Build search URL from query"""
        pass
    
    @abstractmethod
    def parse_results(self, html: str, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Parse search results from HTML"""
        pass
    
    @abstractmethod
    def is_blocked(self, response: requests.Response) -> bool:
        """Check if response indicates we're blocked"""
        pass
    
    def extract_linkedin_url(self, url: str) -> Optional[str]:
        """Extract and clean LinkedIn URL"""
        if 'linkedin.com/in/' not in url:
            return None
        
        # Clean tracking parameters
        if '?' in url:
            url = url.split('?')[0]
        
        # Ensure it's a valid LinkedIn profile URL
        if not url.startswith('http'):
            url = 'https://' + url
        
        return url
    
    def extract_name_from_title(self, title: str) -> Optional[str]:
        """Extract name from page title (common LinkedIn format)"""
        # LinkedIn format: "Name - Title - Company | LinkedIn"
        title = re.sub(r'\s*\|\s*LinkedIn.*$', '', title)
        
        # Split by separators
        parts = re.split(r'\s*[-–—]\s*', title)
        
        if parts:
            name = parts[0].strip()
            # Basic validation
            if self.is_valid_name(name):
                return name
        
        return None
    
    def is_valid_name(self, name: str) -> bool:
        """Validate if string looks like a person's name"""
        if not name or len(name) < 3 or len(name) > 60:
            return False
        
        # Should have at least first and last name
        parts = name.split()
        if len(parts) < 2 or len(parts) > 5:
            return False
        
        # Check for common invalid patterns
        invalid_patterns = [
            r'\d{3,}',  # No long numbers
            r'@',       # No email addresses
            r'https?:', # No URLs
            r'[<>{}]',  # No HTML/code characters
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, name):
                return False
        
        return True
    
    def categorize_title(self, title: str) -> str:
        """Categorize job title into standard categories"""
        if not title:
            return "unknown"
        
        title_lower = title.lower()
        
        # Define category patterns
        categories = {
            'recruiter': ['recruiter', 'talent', 'staffing', 'campus recruit', 'university relations'],
            'manager': ['manager', 'lead', 'head of', 'director', 'supervisor'],
            'senior': ['senior', 'staff', 'principal', 'architect', 'expert'],
            'junior': ['junior', 'associate', 'analyst', 'coordinator', 'entry level', 'new grad'],
            'intern': ['intern', 'co-op', 'student'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        
        return "individual_contributor"
