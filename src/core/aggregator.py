"""Aggregate and deduplicate people from multiple sources"""

from typing import List, Dict, Set
from collections import defaultdict
from src.models.person import Person


class PeopleAggregator:
    """
    Aggregate people from multiple sources and deduplicate.
    
    Deduplication strategy:
    - By name + company (case-insensitive)
    - Merge data from multiple sources
    - Track which sources found each person
    """
    
    def __init__(self):
        self.people_by_key: Dict[tuple, Person] = {}
        self.sources_by_key: Dict[tuple, Set[str]] = defaultdict(set)
    
    def add(self, person: Person):
        """Add a person to the aggregator"""
        key = self._make_key(person)
        
        if key in self.people_by_key:
            # Person already exists - merge data
            existing = self.people_by_key[key]
            merged = self._merge_people(existing, person)
            self.people_by_key[key] = merged
        else:
            # New person
            self.people_by_key[key] = person
        
        # Track source
        self.sources_by_key[key].add(person.source)
    
    def add_batch(self, people: List[Person]):
        """Add multiple people"""
        for person in people:
            self.add(person)
    
    def get_all(self) -> List[Person]:
        """Get all unique people"""
        return list(self.people_by_key.values())
    
    def get_stats(self) -> dict:
        """Get aggregation statistics"""
        source_counts = defaultdict(int)
        
        for key, sources in self.sources_by_key.items():
            for source in sources:
                source_counts[source] += 1
        
        # Find people found by multiple sources (high confidence)
        multi_source_count = sum(1 for sources in self.sources_by_key.values() if len(sources) > 1)
        
        return {
            "total_unique_people": len(self.people_by_key),
            "by_source": dict(source_counts),
            "multi_source_matches": multi_source_count,
        }
    
    def _make_key(self, person: Person) -> tuple:
        """Create deduplication key"""
        return (
            person.name.lower().strip(),
            person.company.lower().strip()
        )
    
    def _merge_people(self, existing: Person, new: Person) -> Person:
        """
        Merge data from two person records.
        
        Strategy:
        - Keep non-null values
        - Prefer more specific data
        - Update confidence if found by multiple sources
        """
        # Start with existing
        merged = existing.copy()
        
        # Merge fields (prefer non-null)
        if not merged.title and new.title:
            merged.title = new.title
        if not merged.linkedin_url and new.linkedin_url:
            merged.linkedin_url = new.linkedin_url
        if not merged.email and new.email:
            merged.email = new.email
        if not merged.twitter_url and new.twitter_url:
            merged.twitter_url = new.twitter_url
        if not merged.github_url and new.github_url:
            merged.github_url = new.github_url
        if not merged.department and new.department:
            merged.department = new.department
        if not merged.location and new.location:
            merged.location = new.location
        
        # Merge skills
        merged.skills = list(set(merged.skills + new.skills))
        
        # Increase confidence (found by multiple sources)
        merged.confidence_score = min(1.0, merged.confidence_score + 0.2)
        
        # Track all sources (in evidence_url if possible)
        if new.source not in merged.source:
            merged.source = f"{merged.source},{new.source}"
        
        return merged

