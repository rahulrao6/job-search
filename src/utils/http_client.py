"""HTTP client with retries and proxy support"""

import random
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    """HTTP client with automatic retries and user agent rotation"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self.proxy = proxy
        self.timeout = timeout
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry logic"""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        if self.proxy:
            session.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }
        
        return session
    
    def _get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get headers with random user agent"""
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None, 
            params: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Make a GET request"""
        merged_headers = self._get_headers(headers)
        
        response = self.session.get(
            url,
            headers=merged_headers,
            params=params,
            timeout=self.timeout,
            **kwargs
        )
        
        response.raise_for_status()
        return response
    
    def post(self, url: str, headers: Optional[Dict[str, str]] = None,
             data: Optional[Any] = None, json: Optional[Any] = None, **kwargs) -> requests.Response:
        """Make a POST request"""
        merged_headers = self._get_headers(headers)
        
        response = self.session.post(
            url,
            headers=merged_headers,
            data=data,
            json=json,
            timeout=self.timeout,
            **kwargs
        )
        
        response.raise_for_status()
        return response
    
    def close(self):
        """Close the session"""
        self.session.close()


def create_client(proxy: Optional[str] = None) -> HttpClient:
    """Factory function to create HTTP client"""
    return HttpClient(proxy=proxy)

