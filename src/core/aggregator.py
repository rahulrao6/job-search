"""Aggregate and deduplicate people from multiple sources"""

import re
from typing import List, Dict, Set
from collections import defaultdict
from src.models.person import Person


class PeopleAggregator:
    """
    Aggregate people from multiple sources and deduplicate.
    
    Deduplication strategy:
    - By name + normalized company (case-insensitive)
    - Handles company name variations (LLC, Inc, Corp, etc.)
    - Maps parent companies (Facebook → Meta, Alphabet → Google)
    - Merge data from multiple sources
    - Track which sources found each person
    """
    
    # Parent company mappings (child → parent)
    PARENT_COMPANY_MAPPINGS = {
        'facebook': 'meta',
        'facebook inc': 'meta',
        'facebook llc': 'meta',
        'alphabet': 'google',
        'alphabet inc': 'google',
        'alphabet llc': 'google',
    }
    
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
    
    def _normalize_company_name(self, company: str) -> str:
        """
        Normalize company name for better deduplication.
        
        Handles:
        - Common suffixes: LLC, Inc, Ltd, Corp, Corporation → removed
        - Parent company mappings: Facebook → Meta, Alphabet → Google
        - Case normalization
        
        Examples:
        - "Google LLC" → "google"
        - "Meta Platforms Inc" → "meta platforms"
        - "Facebook" → "meta" (parent mapping)
        - "Alphabet Inc" → "google" (parent mapping)
        """
        if not company:
            return ""
        
        # Convert to lowercase and strip
        normalized = company.lower().strip()
        
        # Remove common legal suffixes (with or without periods)
        suffixes = ['llc', 'inc', 'ltd', 'corp', 'corporation', 'company', 'co']
        for suffix in suffixes:
            # Match suffix at end of string (with optional period and whitespace)
            pattern = r'\s+' + re.escape(suffix) + r'\.?\s*$'
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Strip again after suffix removal
        normalized = normalized.strip()
        
        # Apply parent company mappings
        if normalized in self.PARENT_COMPANY_MAPPINGS:
            normalized = self.PARENT_COMPANY_MAPPINGS[normalized]
        
        return normalized
    
    def _make_key(self, person: Person) -> tuple:
        """Create deduplication key with normalized company name"""
        normalized_company = self._normalize_company_name(person.company)
        return (
            person.name.lower().strip(),
            normalized_company
        )
    
    def _merge_people(self, existing: Person, new: Person) -> Person:
        """
        Merge data from two person records.
        
        Strategy:
        - Keep non-null values
        - Prefer more specific data
        - Update confidence if found by multiple sources
        """
        # Start with existing - use Pydantic v2 model_copy() method
        # Fallback to copy() for backward compatibility with Pydantic v1
        if hasattr(existing, 'model_copy'):
            merged = existing.model_copy()
        elif hasattr(existing, 'copy'):
            merged = existing.copy()
        else:
            # Fallback: create new Person with existing data
            merged = Person(**existing.model_dump() if hasattr(existing, 'model_dump') else existing.dict())
        
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

