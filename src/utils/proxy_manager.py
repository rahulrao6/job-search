"""Proxy rotation manager"""

import os
import random
from typing import List, Optional


class ProxyManager:
    """
    Manage and rotate proxies.
    
    Supports:
    - Single proxy
    - Proxy list rotation
    - Free proxy lists (with testing)
    """
    
    def __init__(self, proxy_list: Optional[str] = None):
        """
        Initialize proxy manager.
        
        Args:
            proxy_list: Comma-separated list of proxies or single proxy
                       Format: http://user:pass@host:port or http://host:port
        """
        self.proxies: List[str] = []
        self.current_index = 0
        
        # Load from parameter or environment
        proxy_str = proxy_list or os.getenv("PROXY_LIST", "")
        
        if proxy_str:
            # Split by comma if multiple proxies
            self.proxies = [p.strip() for p in proxy_str.split(",") if p.strip()]
    
    def is_configured(self) -> bool:
        """Check if any proxies are configured"""
        return len(self.proxies) > 0
    
    def get_proxy(self, rotate: bool = True) -> Optional[str]:
        """
        Get a proxy.
        
        Args:
            rotate: If True, rotate to next proxy. If False, return current.
        
        Returns:
            Proxy URL or None if no proxies configured
        """
        if not self.proxies:
            return None
        
        if rotate:
            # Rotate to next proxy
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy
        else:
            # Return current without rotating
            return self.proxies[self.current_index]
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random proxy"""
        if not self.proxies:
            return None
        
        return random.choice(self.proxies)
    
    def add_proxy(self, proxy: str):
        """Add a proxy to the list"""
        if proxy and proxy not in self.proxies:
            self.proxies.append(proxy)
    
    def remove_proxy(self, proxy: str):
        """Remove a proxy from the list (e.g., if it's not working)"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
    
    def get_proxy_dict(self, rotate: bool = True) -> Optional[dict]:
        """
        Get proxy in requests-compatible dict format.
        
        Returns:
            {"http": "...", "https": "..."} or None
        """
        proxy = self.get_proxy(rotate=rotate)
        
        if proxy:
            return {
                "http": proxy,
                "https": proxy,
            }
        
        return None
    
    def get_stats(self) -> dict:
        """Get proxy statistics"""
        return {
            "total_proxies": len(self.proxies),
            "current_index": self.current_index,
            "proxies": self.proxies if len(self.proxies) <= 10 else f"{len(self.proxies)} proxies (hidden)",
        }


# Global proxy manager instance
_proxy_manager = ProxyManager()


def get_proxy_manager() -> ProxyManager:
    """Get the global proxy manager instance"""
    return _proxy_manager

