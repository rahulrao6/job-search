"""Caching utilities"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timedelta
from diskcache import Cache as DiskCache


class Cache:
    """Simple file-based cache with TTL"""
    
    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 168):  # 7 days default for search results
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        
        # Use diskcache for robust file-based caching
        self._cache = DiskCache(str(self.cache_dir))
    
    def _make_key(self, source: str, query: dict) -> str:
        """Generate cache key from source and query"""
        query_str = json.dumps(query, sort_keys=True)
        hash_val = hashlib.md5(query_str.encode()).hexdigest()
        return f"{source}:{hash_val}"
    
    def get(self, source: str, query: dict) -> Optional[Any]:
        """Get cached result if it exists and is not expired"""
        key = self._make_key(source, query)
        
        try:
            result = self._cache.get(key)
            if result is not None:
                # Check if expired
                cached_at = result.get("cached_at")
                if cached_at:
                    cached_time = datetime.fromisoformat(cached_at)
                    if datetime.utcnow() - cached_time > self.ttl:
                        self._cache.delete(key)
                        return None
                
                return result.get("data")
        except Exception as e:
            print(f"Cache read error: {e}")
            return None
        
        return None
    
    def set(self, source: str, query: dict, data: Any):
        """Cache a result"""
        key = self._make_key(source, query)
        
        try:
            self._cache.set(key, {
                "data": data,
                "cached_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def clear(self, source: Optional[str] = None):
        """Clear cache for a source or all sources"""
        if source:
            # Clear all keys starting with source prefix
            for key in list(self._cache.iterkeys()):
                if key.startswith(f"{source}:"):
                    self._cache.delete(key)
        else:
            self._cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "size_mb": self._cache.volume() / (1024 * 1024),
            "entries": len(self._cache),
        }


# Global cache instance
_cache = Cache()


def get_cache() -> Cache:
    """Get the global cache instance"""
    return _cache

