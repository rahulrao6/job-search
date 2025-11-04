"""Simple metrics tracking for API endpoints"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any
from threading import Lock


class MetricsTracker:
    """Simple in-memory metrics tracker"""
    
    def __init__(self):
        self._lock = Lock()
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._request_times: Dict[str, list] = defaultdict(list)
        self._started_at = datetime.utcnow()
        
        # Keep only last hour of request times
        self._cleanup_threshold = timedelta(hours=1)
    
    def record_request(self, endpoint: str, status_code: int, duration_ms: float):
        """Record a request"""
        with self._lock:
            self._request_counts[endpoint] += 1
            
            if status_code >= 400:
                self._error_counts[endpoint] += 1
            
            # Store request time (keep last hour)
            now = datetime.utcnow()
            self._request_times[endpoint].append({
                'timestamp': now,
                'duration_ms': duration_ms,
                'status_code': status_code
            })
            
            # Cleanup old entries
            cutoff = now - self._cleanup_threshold
            self._request_times[endpoint] = [
                entry for entry in self._request_times[endpoint]
                if entry['timestamp'] > cutoff
            ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self._lock:
            total_requests = sum(self._request_counts.values())
            total_errors = sum(self._error_counts.values())
            
            # Calculate average response times
            avg_times = {}
            slow_requests = {}
            
            for endpoint, times in self._request_times.items():
                if times:
                    avg_time = sum(t['duration_ms'] for t in times) / len(times)
                    avg_times[endpoint] = round(avg_time, 2)
                    
                    # Count slow requests (>5s)
                    slow_count = sum(1 for t in times if t['duration_ms'] > 5000)
                    if slow_count > 0:
                        slow_requests[endpoint] = slow_count
            
            return {
                'started_at': self._started_at.isoformat(),
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
                'requests_by_endpoint': dict(self._request_counts),
                'errors_by_endpoint': dict(self._error_counts),
                'avg_response_time_ms': avg_times,
                'slow_requests': slow_requests,
                'recent_requests': sum(len(times) for times in self._request_times.values())
            }
    
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self._request_counts.clear()
            self._error_counts.clear()
            self._request_times.clear()
            self._started_at = datetime.utcnow()


# Global metrics tracker
_metrics_tracker = MetricsTracker()


def get_metrics_tracker() -> MetricsTracker:
    """Get global metrics tracker instance"""
    return _metrics_tracker

