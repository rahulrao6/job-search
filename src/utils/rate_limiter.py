"""Rate limiting utilities"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional


class RateLimiter:
    """Thread-safe rate limiter with per-source limits"""
    
    def __init__(self):
        self._locks: Dict[str, Lock] = defaultdict(Lock)
        self._last_request: Dict[str, float] = {}
        self._hourly_counts: Dict[str, list] = defaultdict(list)
        self._min_intervals: Dict[str, float] = {}
        self._hourly_limits: Dict[str, int] = {}
    
    def configure(self, source: str, requests_per_second: float, 
                  max_per_hour: Optional[int] = None):
        """Configure rate limits for a source"""
        self._min_intervals[source] = 1.0 / requests_per_second if requests_per_second > 0 else 0
        if max_per_hour:
            self._hourly_limits[source] = max_per_hour
    
    def wait_if_needed(self, source: str) -> float:
        """
        Wait if necessary to respect rate limits.
        Returns the time waited in seconds.
        """
        with self._locks[source]:
            now = time.time()
            wait_time = 0.0
            
            # Check per-second rate limit
            if source in self._min_intervals:
                min_interval = self._min_intervals[source]
                if source in self._last_request:
                    time_since_last = now - self._last_request[source]
                    if time_since_last < min_interval:
                        wait_time = min_interval - time_since_last
                        time.sleep(wait_time)
                        now = time.time()
            
            # Check hourly limit
            if source in self._hourly_limits:
                # Clean old entries (older than 1 hour)
                cutoff = now - 3600
                self._hourly_counts[source] = [
                    t for t in self._hourly_counts[source] if t > cutoff
                ]
                
                # Wait if at limit
                if len(self._hourly_counts[source]) >= self._hourly_limits[source]:
                    # Wait until oldest request expires
                    oldest = self._hourly_counts[source][0]
                    wait_until = oldest + 3600
                    if wait_until > now:
                        extra_wait = wait_until - now
                        time.sleep(extra_wait)
                        wait_time += extra_wait
                        now = time.time()
                        # Clean again after waiting
                        cutoff = now - 3600
                        self._hourly_counts[source] = [
                            t for t in self._hourly_counts[source] if t > cutoff
                        ]
            
            # Record this request
            self._last_request[source] = now
            self._hourly_counts[source].append(now)
            
            return wait_time
    
    def get_stats(self, source: str) -> dict:
        """Get current rate limit stats for a source"""
        now = time.time()
        cutoff = now - 3600
        
        recent_requests = [
            t for t in self._hourly_counts.get(source, []) if t > cutoff
        ]
        
        return {
            "source": source,
            "requests_last_hour": len(recent_requests),
            "hourly_limit": self._hourly_limits.get(source),
            "last_request": datetime.fromtimestamp(
                self._last_request[source]
            ).isoformat() if source in self._last_request else None,
        }


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter

