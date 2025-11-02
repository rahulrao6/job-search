"""Categorize people into target buckets"""

import re
from typing import List, Optional
from src.models.person import Person, PersonCategory
from src.db.models import UserProfile, JobRecord


class PersonCategorizer:
    """
    Categorize people into:
    - Manager: Would be your manager or higher
    - Recruiter: HR/Talent/Recruiting
    - Senior: One level above target role
    - Peer: Same level as target role
    """
    
    # Keywords for each category
    MANAGER_KEYWORDS = [
        "manager", "director", "head of", "vp", "vice president",
        "chief", "ceo", "cto", "cfo", "coo", "president",
        "lead", "leadership", "principal"
    ]
    
    RECRUITER_KEYWORDS = [
        "recruiter", "talent", "recruiting", "hiring", 
        "hr", "human resources", "people operations",
        "people partner", "talent acquisition"
    ]
    
    SENIOR_KEYWORDS = [
        "senior", "staff", "principal", "architect",
        "distinguished", "fellow"
    ]
    
    def __init__(self, target_title: str):
        """
        Initialize with target job title.
        
        Args:
            target_title: The job title the user is targeting
        """
        self.target_title = target_title.lower()
        
        # Extract seniority from target title
        self.target_is_senior = any(kw in self.target_title for kw in self.SENIOR_KEYWORDS)
    
    def categorize(self, person: Person) -> Person:
        """
        Categorize a person based on their title.
        
        Returns:
            Person with category field updated
        """
        if not person.title:
            person.category = PersonCategory.UNKNOWN
            return person
        
        title_lower = person.title.lower()
        
        # Check for recruiter
        if any(kw in title_lower for kw in self.RECRUITER_KEYWORDS):
            person.category = PersonCategory.RECRUITER
            return person
        
        # Check for manager/leadership
        if any(kw in title_lower for kw in self.MANAGER_KEYWORDS):
            person.category = PersonCategory.MANAGER
            return person
        
        # Check for senior (if target is not already senior)
        if not self.target_is_senior and any(kw in title_lower for kw in self.SENIOR_KEYWORDS):
            person.category = PersonCategory.SENIOR
            return person
        
        # Check if it's similar to target title (peer)
        if self._is_similar_title(title_lower, self.target_title):
            person.category = PersonCategory.PEER
            return person
        
        # Default to unknown
        person.category = PersonCategory.UNKNOWN
        return person
    
    def categorize_batch(self, people: List[Person]) -> List[Person]:
        """Categorize a list of people"""
        return [self.categorize(person) for person in people]
    
    def _is_similar_title(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar (same role, different seniority)"""
        # Remove seniority keywords
        for kw in self.SENIOR_KEYWORDS + ["junior", "jr", "sr", "i", "ii", "iii", "iv"]:
            title1 = re.sub(rf'\b{kw}\b', '', title1, flags=re.IGNORECASE)
            title2 = re.sub(rf'\b{kw}\b', '', title2, flags=re.IGNORECASE)
        
        # Clean whitespace
        title1 = ' '.join(title1.split())
        title2 = ' '.join(title2.split())
        
        # Check if core titles match
        return title1 == title2 or title1 in title2 or title2 in title1
    
    def categorize_with_profile_context(
        self,
        person: Person,
        profile: Optional[UserProfile] = None,
        job: Optional[JobRecord] = None
    ) -> Person:
        """
        Categorize a person with profile and job context.
        Boosts confidence for alumni/ex-company matches.
        
        Args:
            person: Person to categorize
            profile: User profile (optional)
            job: Job record (optional)
            
        Returns:
            Person with category and potentially boosted confidence
        """
        # First, do standard categorization
        person = self.categorize(person)
        
        # Boost confidence if there are profile matches
        if profile:
            # Check for alumni match (if we had school data in person)
            # Note: This is a placeholder - in production, extract school from LinkedIn
            if profile.schools:
                # If person's metadata indicates same school, boost confidence
                # For now, we'll boost if they work at a company user used to work at
                pass
            
            # Check for ex-company match (person works at company user used to work at)
            if profile.past_companies and person.company:
                person_company_lower = person.company.lower()
                for past_company in profile.past_companies:
                    past_company_lower = past_company.lower()
                    if past_company_lower in person_company_lower or person_company_lower in past_company_lower:
                        # Boost confidence for ex-company connections
                        person.confidence_score = min(1.0, (person.confidence_score or 0.5) + 0.15)
                        break
        
        return person
    
    def get_category_counts(self, people: List[Person]) -> dict:
        """Get counts of people in each category"""
        counts = {
            PersonCategory.MANAGER: 0,
            PersonCategory.RECRUITER: 0,
            PersonCategory.SENIOR: 0,
            PersonCategory.PEER: 0,
            PersonCategory.UNKNOWN: 0,
        }
        
        for person in people:
            counts[person.category] = counts.get(person.category, 0) + 1
        
        return counts

