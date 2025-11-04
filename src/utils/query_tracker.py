"""
Query performance tracking utility.

Tracks query performance metrics to identify successful search patterns.
Can be enhanced later to persist to database for analytics.
"""

import time
import logging
from typing import Dict, List
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class QueryTracker:
    """
    Track query performance metrics.
    
    Tracks:
    - Query text
    - Results count
    - Execution time
    - Source name
    - Success/failure status
    """
    
    def __init__(self):
        self.queries: List[Dict] = []
        self._stats_by_pattern: Dict[str, Dict] = defaultdict(lambda: {
            'count': 0,
            'total_results': 0,
            'total_time_ms': 0,
            'successes': 0,
            'failures': 0
        })
    
    def track_query(
        self,
        query: str,
        results_count: int,
        execution_time_ms: float,
        source: str,
        success: bool = True
    ):
        """
        Track a query execution.
        
        Args:
            query: The search query text
            results_count: Number of results returned
            execution_time_ms: Execution time in milliseconds
            source: Source name (e.g., 'google_cse', 'bing_api')
            success: Whether query succeeded
        """
        entry = {
            'query': query,
            'results_count': results_count,
            'execution_time_ms': execution_time_ms,
            'source': source,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.queries.append(entry)
        
        # Update pattern stats (simple pattern: first 50 chars of query)
        pattern = query[:50] if len(query) > 50 else query
        stats = self._stats_by_pattern[pattern]
        stats['count'] += 1
        stats['total_results'] += results_count
        stats['total_time_ms'] += execution_time_ms
        if success:
            stats['successes'] += 1
        else:
            stats['failures'] += 1
        
        # Log query performance
        status = "✓" if success else "✗"
        log_msg = f"QUERY_PERF: {status} query={query[:60]}..., results={results_count}, time={execution_time_ms:.0f}ms, source={source}"
        print(f"  {log_msg}")
        logger.debug(log_msg)
    
    def get_stats(self) -> Dict:
        """
        Get query performance statistics.
        
        Returns:
            Dictionary with overall stats and pattern breakdowns
        """
        if not self.queries:
            return {
                'total_queries': 0,
                'total_results': 0,
                'avg_results_per_query': 0,
                'avg_time_ms': 0,
                'success_rate': 0,
                'top_patterns': []
            }
        
        total_queries = len(self.queries)
        total_results = sum(q['results_count'] for q in self.queries)
        total_time = sum(q['execution_time_ms'] for q in self.queries)
        successes = sum(1 for q in self.queries if q['success'])
        
        # Calculate pattern performance
        pattern_performance = []
        for pattern, stats in self._stats_by_pattern.items():
            pattern_performance.append({
                'pattern': pattern,
                'queries': stats['count'],
                'avg_results': stats['total_results'] / stats['count'] if stats['count'] > 0 else 0,
                'avg_time_ms': stats['total_time_ms'] / stats['count'] if stats['count'] > 0 else 0,
                'success_rate': stats['successes'] / stats['count'] if stats['count'] > 0 else 0
            })
        
        # Sort by average results (descending)
        pattern_performance.sort(key=lambda x: x['avg_results'], reverse=True)
        
        return {
            'total_queries': total_queries,
            'total_results': total_results,
            'avg_results_per_query': total_results / total_queries if total_queries > 0 else 0,
            'avg_time_ms': total_time / total_queries if total_queries > 0 else 0,
            'success_rate': successes / total_queries if total_queries > 0 else 0,
            'top_patterns': pattern_performance[:5]  # Top 5 patterns
        }
    
    def reset(self):
        """Reset all tracking data"""
        self.queries.clear()
        self._stats_by_pattern.clear()


# Global query tracker instance
_query_tracker = QueryTracker()


def get_query_tracker() -> QueryTracker:
    """Get the global query tracker instance"""
    return _query_tracker


def track_query(query: str, results_count: int, execution_time_ms: float, source: str, success: bool = True):
    """Convenience function to track a query"""
    _query_tracker.track_query(query, results_count, execution_time_ms, source, success)

