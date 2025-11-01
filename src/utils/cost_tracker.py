"""Cost tracking utilities"""

from collections import defaultdict
from typing import Dict
from datetime import datetime


class CostTracker:
    """Track API costs across sources"""
    
    def __init__(self):
        self._costs: Dict[str, float] = defaultdict(float)
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._started_at = datetime.utcnow()
    
    def record_request(self, source: str, cost: float = 0.0):
        """Record a request and its cost"""
        self._costs[source] += cost
        self._request_counts[source] += 1
    
    def get_total_cost(self) -> float:
        """Get total cost across all sources"""
        return sum(self._costs.values())
    
    def get_source_cost(self, source: str) -> float:
        """Get cost for a specific source"""
        return self._costs[source]
    
    def get_stats(self) -> dict:
        """Get comprehensive cost statistics"""
        return {
            "total_cost": self.get_total_cost(),
            "by_source": {
                source: {
                    "cost": self._costs[source],
                    "requests": self._request_counts[source],
                }
                for source in self._costs.keys()
            },
            "total_requests": sum(self._request_counts.values()),
            "started_at": self._started_at.isoformat(),
        }
    
    def reset(self):
        """Reset all tracking"""
        self._costs.clear()
        self._request_counts.clear()
        self._started_at = datetime.utcnow()


# Global cost tracker instance
_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance"""
    return _cost_tracker

