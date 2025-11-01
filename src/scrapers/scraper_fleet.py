"""Fleet management for multiple scrapers with intelligent orchestration"""

import re
import time
import random
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from .google_scraper import GoogleScraper
from .bing_scraper import BingScraper
from .duckduckgo_scraper import DuckDuckGoScraper
from .base_scraper import BaseSearchScraper


class ScraperFleet:
    """
    Manages a fleet of search scrapers with:
    - Intelligent load balancing
    - Failure detection and recovery
    - Result deduplication
    - Query optimization
    - Health monitoring
    """
    
    def __init__(self, scrapers: Optional[List[BaseSearchScraper]] = None):
        """
        Initialize scraper fleet.
        
        Args:
            scrapers: List of scraper instances, defaults to all available
        """
        if scrapers is None:
            scrapers = [
                DuckDuckGoScraper(),  # Most reliable, no limits
                BingScraper(),        # Good for volume
                GoogleScraper(),      # Best results but strict limits
            ]
        
        self.scrapers = {s.name: s for s in scrapers}
        
        # Health tracking
        self.health_scores = defaultdict(lambda: 1.0)  # 0-1 health score
        self.failure_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        self.last_success = defaultdict(float)
        
        # Result tracking
        self.seen_urls = set()
        self.result_quality = defaultdict(list)  # Track quality scores
    
    def search_linkedin_profiles(self, company: str, role: str, 
                                target_count: int = 50,
                                categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for LinkedIn profiles across all scrapers.
        
        Args:
            company: Target company name
            role: Job role/title
            target_count: Target number of unique profiles
            categories: Specific categories to search for (recruiter, manager, etc.)
            
        Returns:
            List of deduplicated LinkedIn profiles
        """
        if categories is None:
            categories = ['recruiter', 'manager', 'team_lead', 'alumni']
        
        # Generate comprehensive query set
        queries = self._generate_query_set(company, role, categories)
        
        # Distribute queries across scrapers
        results = self._execute_distributed_search(queries, target_count)
        
        # Post-process results
        profiles = self._extract_linkedin_profiles(results)
        
        # Deduplicate and rank
        unique_profiles = self._deduplicate_profiles(profiles)
        
        # Sort by relevance
        ranked_profiles = self._rank_profiles(unique_profiles, role, categories)
        
        return ranked_profiles[:target_count]
    
    def _generate_query_set(self, company: str, role: str, 
                           categories: List[str]) -> List[Dict[str, Any]]:
        """Generate optimized query set for different scrapers"""
        queries = []
        
        # Base role without seniority
        base_role = re.sub(r'\b(junior|senior|staff|principal|lead)\b', '', 
                          role, flags=re.I).strip()
        
        # Category-specific queries
        if 'recruiter' in categories:
            queries.extend([
                {'query': f'site:linkedin.com/in/ "{company}" recruiter', 'category': 'recruiter'},
                {'query': f'site:linkedin.com/in/ "{company}" "talent acquisition"', 'category': 'recruiter'},
                {'query': f'site:linkedin.com/in/ "{company}" "campus recruiter"', 'category': 'recruiter'},
                {'query': f'"{company}" "university recruiter" linkedin', 'category': 'recruiter'},
            ])
        
        if 'manager' in categories:
            queries.extend([
                {'query': f'site:linkedin.com/in/ "{company}" "{base_role}" manager', 'category': 'manager'},
                {'query': f'site:linkedin.com/in/ "{company}" "engineering manager"', 'category': 'manager'},
                {'query': f'"{company}" "hiring manager" linkedin', 'category': 'manager'},
            ])
        
        if 'team_lead' in categories:
            queries.extend([
                {'query': f'site:linkedin.com/in/ "{company}" "team lead"', 'category': 'team_lead'},
                {'query': f'site:linkedin.com/in/ "{company}" "tech lead"', 'category': 'team_lead'},
                {'query': f'"{company}" supervisor "{base_role}" linkedin', 'category': 'team_lead'},
            ])
        
        if 'alumni' in categories:
            current_year = 2024
            for year in range(current_year - 4, current_year + 1):
                queries.append({
                    'query': f'site:linkedin.com/in/ "{company}" "class of {year}"',
                    'category': 'alumni',
                })
            
            queries.extend([
                {'query': f'site:linkedin.com/in/ "{company}" "recent graduate"', 'category': 'alumni'},
                {'query': f'"{company}" "new grad" "started" linkedin', 'category': 'alumni'},
            ])
        
        # General queries
        queries.extend([
            {'query': f'site:linkedin.com/in/ "{company}" "{base_role}"', 'category': 'general'},
            {'query': f'"{company}" "{role}" linkedin profile', 'category': 'general'},
        ])
        
        return queries
    
    def _execute_distributed_search(self, queries: List[Dict[str, Any]], 
                                   target_count: int) -> List[Dict[str, Any]]:
        """Execute searches across fleet with load balancing"""
        all_results = []
        
        # Sort scrapers by health score
        sorted_scrapers = sorted(
            self.scrapers.items(),
            key=lambda x: self.health_scores[x[0]],
            reverse=True
        )
        
        # Distribute queries
        query_assignments = defaultdict(list)
        for i, query_data in enumerate(queries):
            # Assign to healthiest available scraper
            scraper_name = sorted_scrapers[i % len(sorted_scrapers)][0]
            query_assignments[scraper_name].append(query_data)
        
        # Execute in parallel with thread pool
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_scraper = {}
            
            for scraper_name, scraper_queries in query_assignments.items():
                scraper = self.scrapers[scraper_name]
                
                for query_data in scraper_queries:
                    future = executor.submit(
                        self._execute_single_search,
                        scraper,
                        query_data['query'],
                        query_data['category']
                    )
                    future_to_scraper[future] = (scraper_name, query_data)
            
            # Collect results as they complete
            for future in as_completed(future_to_scraper):
                scraper_name, query_data = future_to_scraper[future]
                
                try:
                    results = future.result(timeout=30)
                    if results:
                        all_results.extend(results)
                        self._update_health(scraper_name, success=True)
                        
                        # Stop if we have enough results
                        if len(all_results) >= target_count * 2:
                            break
                    else:
                        self._update_health(scraper_name, success=False)
                        
                except Exception as e:
                    print(f"⚠️ {scraper_name} failed on query: {e}")
                    self._update_health(scraper_name, success=False)
        
        return all_results
    
    def _execute_single_search(self, scraper: BaseSearchScraper, 
                              query: str, category: str) -> List[Dict[str, Any]]:
        """Execute a single search with a scraper"""
        try:
            results = scraper.search(query, max_results=20)
            
            # Add category to results
            for result in results:
                result['category'] = category
                result['scraper'] = scraper.name
            
            return results
            
        except Exception as e:
            print(f"⚠️ {scraper.name} error: {e}")
            return []
    
    def _extract_linkedin_profiles(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract LinkedIn profiles from search results"""
        profiles = []
        
        for result in results:
            url = result.get('url', '')
            
            # Only LinkedIn profiles
            if 'linkedin.com/in/' not in url:
                continue
            
            # Clean URL
            if '?' in url:
                url = url.split('?')[0]
            
            # Extract name from title
            title = result.get('title', '')
            name = self._extract_name_from_title(title)
            
            if name:
                profile = {
                    'name': name,
                    'url': url,
                    'title': result.get('snippet', ''),
                    'category': result.get('category', 'unknown'),
                    'source': result.get('scraper', 'unknown'),
                }
                profiles.append(profile)
        
        return profiles
    
    def _extract_name_from_title(self, title: str) -> Optional[str]:
        """Extract name from search result title"""
        # LinkedIn format: "Name - Title - Company | LinkedIn"
        title = re.sub(r'\s*\|\s*LinkedIn.*$', '', title)
        
        parts = re.split(r'\s*[-–—]\s*', title)
        if parts:
            name = parts[0].strip()
            # Validate
            if 2 <= len(name.split()) <= 5 and len(name) < 60:
                return name
        
        return None
    
    def _deduplicate_profiles(self, profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate profiles by URL and name"""
        seen_urls = set()
        seen_names = set()
        unique = []
        
        for profile in profiles:
            url = profile['url']
            name = profile['name'].lower()
            
            # Skip if seen
            if url in seen_urls or name in seen_names:
                continue
            
            seen_urls.add(url)
            seen_names.add(name)
            unique.append(profile)
        
        return unique
    
    def _rank_profiles(self, profiles: List[Dict[str, Any]], 
                      role: str, categories: List[str]) -> List[Dict[str, Any]]:
        """Rank profiles by relevance"""
        for profile in profiles:
            score = 0.5  # Base score
            
            # Category bonuses
            if profile['category'] == 'recruiter':
                score += 0.3  # Recruiters are high value
            elif profile['category'] == 'manager':
                score += 0.25
            elif profile['category'] == 'alumni':
                score += 0.2
            elif profile['category'] == 'team_lead':
                score += 0.15
            
            # Source quality bonus
            if profile['source'] == 'google':
                score += 0.1  # Google tends to have better ranking
            
            # Title relevance
            title = profile.get('title', '').lower()
            if any(cat in title for cat in ['recruiter', 'talent', 'hiring']):
                score += 0.2
            if 'manager' in title and 'senior' not in title:
                score += 0.15
            if any(year in title for year in ['2023', '2024', 'recent']):
                score += 0.1
            
            profile['relevance_score'] = score
        
        # Sort by relevance
        return sorted(profiles, key=lambda x: x['relevance_score'], reverse=True)
    
    def _update_health(self, scraper_name: str, success: bool):
        """Update scraper health metrics"""
        if success:
            self.success_counts[scraper_name] += 1
            self.last_success[scraper_name] = time.time()
            # Improve health score
            self.health_scores[scraper_name] = min(1.0, self.health_scores[scraper_name] + 0.1)
        else:
            self.failure_counts[scraper_name] += 1
            # Degrade health score
            self.health_scores[scraper_name] = max(0.0, self.health_scores[scraper_name] - 0.2)
    
    def get_fleet_status(self) -> Dict[str, Any]:
        """Get current fleet status"""
        status = {}
        
        for name, scraper in self.scrapers.items():
            status[name] = {
                'health_score': self.health_scores[name],
                'success_count': self.success_counts[name],
                'failure_count': self.failure_counts[name],
                'last_success': time.time() - self.last_success.get(name, 0),
                'rate_limit': scraper.rate_limiter.get_stats(name),
            }
        
        return status
