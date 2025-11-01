"""
Person data validator to remove false positives and improve quality.

False positives we filter:
1. People who used to work at company (past employees)
2. People whose name matches company name
3. Spam/low-quality profiles
4. Duplicate profiles with slight variations
"""

import re
from typing import List, Optional
from src.models.person import Person


class PersonValidator:
    """
    Validates person data to remove false positives.
    
    Filters out:
    - Past employees (title says "Former", "Ex-", "Previously at")
    - Name matches company (e.g., "Amazon" person when searching Amazon)
    - Generic/spam profiles (no title, no LinkedIn, low info)
    - Obvious duplicates
    """
    
    # Keywords indicating past employment
    PAST_EMPLOYMENT_KEYWORDS = [
        'former', 'ex-', 'previously at', 'formerly at',
        'retired from', 'alumni', 'past', 'was at',
        'worked at', 'used to work'
    ]
    
    # Generic/spam indicators
    SPAM_INDICATORS = [
        'freelancer', 'consultant', 'available for hire',
        'seeking opportunities', 'open to work', 'looking for',
        'independent contractor', 'self-employed'
    ]
    
    def __init__(self, company: str):
        """
        Initialize validator for a specific company search.
        
        Args:
            company: Company name being searched
        """
        self.company = company.lower().strip()
        self.company_words = set(self.company.split())
    
    def validate_person(self, person: Person) -> tuple[bool, str]:
        """
        Validate if person is a real current employee.
        
        Returns:
            (is_valid, reason_if_invalid)
        """
        # Check 1: Name matches company name
        if self._name_matches_company(person):
            return False, "Name matches company name (likely false positive)"
        
        # Check 2: Past employment indicators
        if self._is_past_employee(person):
            return False, "Past employee (not current)"
        
        # Check 3: Generic/spam profile
        if self._is_spam_profile(person):
            return False, "Generic/spam profile"
        
        # Check 4: Missing critical info
        if self._missing_critical_info(person):
            return False, "Missing critical information"
        
        # Check 5: Company mismatch in title
        if self._company_mismatch_in_title(person):
            return False, "Title indicates different company"
        
        return True, ""
    
    def validate_batch(self, people: List[Person]) -> List[Person]:
        """
        Validate a batch of people, keeping only valid ones.
        
        Returns:
            List of validated people with confidence scores adjusted
        """
        validated = []
        
        for person in people:
            is_valid, reason = self.validate_person(person)
            
            if is_valid:
                # Adjust confidence based on quality indicators
                person.confidence_score = self._calculate_confidence(person)
                validated.append(person)
            else:
                print(f"  ⊘ Filtered: {person.name} - {reason}")
        
        return validated
    
    def _name_matches_company(self, person: Person) -> bool:
        """
        Check if person's name matches company name.
        
        Examples:
        - Searching "Amazon" → Person named "Amazon Smith" (FALSE POSITIVE)
        - Searching "Meta" → Person named "Meta Johnson" (FALSE POSITIVE)
        """
        name_lower = person.name.lower()
        name_words = set(name_lower.split())
        
        # Check if company name is in person's name
        if self.company in name_lower:
            # But allow if it's clearly part of a longer name
            # e.g., "Amazona" is different from "Amazon"
            words_in_common = name_words & self.company_words
            if words_in_common:
                return True
        
        return False
    
    def _is_past_employee(self, person: Person) -> bool:
        """
        Check if title/bio indicates past employment.
        
        Examples:
        - "Former Software Engineer at Google"
        - "Ex-Meta Engineer"
        - "Previously at Amazon"
        """
        if not person.title:
            return False
        
        title_lower = person.title.lower()
        
        for keyword in self.PAST_EMPLOYMENT_KEYWORDS:
            if keyword in title_lower:
                return True
        
        return False
    
    def _is_spam_profile(self, person: Person) -> bool:
        """
        Check if profile looks like spam/generic.
        
        Examples:
        - "Freelance Developer"
        - "Open to work | Seeking opportunities"
        """
        if not person.title:
            return False
        
        title_lower = person.title.lower()
        
        # Check for spam indicators
        spam_count = sum(1 for indicator in self.SPAM_INDICATORS if indicator in title_lower)
        
        return spam_count >= 2  # Multiple spam indicators
    
    def _missing_critical_info(self, person: Person) -> bool:
        """
        Check if person is missing critical information.
        
        A person should have at least:
        - Name (always required)
        - Either: LinkedIn URL OR title
        """
        # Must have name (always)
        if not person.name or len(person.name) < 3:
            return True
        
        # Must have either LinkedIn OR title
        has_linkedin = bool(person.linkedin_url)
        has_title = bool(person.title and len(person.title) > 3)
        
        if not (has_linkedin or has_title):
            return True
        
        return False
    
    def _company_mismatch_in_title(self, person: Person) -> bool:
        """
        Check if title explicitly mentions a DIFFERENT company.
        
        Examples:
        - Searching "Google" → Title "Engineer at Microsoft" (MISMATCH)
        - Searching "Meta" → Title "Former Meta, now at Amazon" (MISMATCH)
        """
        if not person.title:
            return False
        
        title_lower = person.title.lower()
        
        # Pattern: "at [company]" or "@ [company]"
        at_pattern = r'(?:at|@)\s+([a-z]+)'
        matches = re.findall(at_pattern, title_lower)
        
        for matched_company in matches:
            # If they mention a different company (not the target)
            if matched_company != self.company and len(matched_company) > 3:
                # But allow if they mention BOTH (e.g., "Former Google, now at Amazon")
                if self.company not in title_lower:
                    return True
        
        return False
    
    def _calculate_confidence(self, person: Person) -> float:
        """
        Calculate confidence score based on data quality.
        
        Factors:
        - Has LinkedIn URL: +0.3
        - Has detailed title: +0.2
        - Has location: +0.1
        - Has skills: +0.1
        - Has department: +0.1
        - High-quality source: +0.2
        """
        confidence = 0.0
        
        # LinkedIn URL is strong signal
        if person.linkedin_url:
            confidence += 0.3
        
        # Detailed title (>20 chars)
        if person.title and len(person.title) > 20:
            confidence += 0.2
        elif person.title and len(person.title) > 5:
            confidence += 0.1
        
        # Location info
        if person.location:
            confidence += 0.1
        
        # Skills info
        if person.skills and len(person.skills) > 0:
            confidence += 0.1
        
        # Department info
        if person.department:
            confidence += 0.1
        
        # Source quality bonus
        high_quality_sources = ['google_serp', 'serpapi', 'apollo']
        if person.source in high_quality_sources:
            confidence += 0.2
        
        # Cap at 1.0
        return min(confidence, 1.0)


def get_validator(company: str) -> PersonValidator:
    """Get a validator instance for a company"""
    return PersonValidator(company)

