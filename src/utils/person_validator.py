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
        'worked at', 'used to work', 'alumnus of', 'formerly',
        'was', 'previous', 'past role', 'previous role',
        'alumni of', 'former employee', 'ex employee'
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
            return False, "Title indicates different company or missing company context"
        
        # Check 6: Verify company appears in title/snippet (additional safety check)
        if self._missing_company_context(person):
            return False, "Company not mentioned in title/snippet (likely wrong person)"
        
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
        
        Improved logic:
        - Only filter exact word matches (not substrings)
        - Check if matched word is actually a name component vs part of a longer word
        - Example: "Amazonia Smith" searching "Amazon" should pass
        - Example: "Amazon Johnson" searching "Amazon" should fail
        
        Examples:
        - Searching "Amazon" → Person named "Amazon Smith" (FALSE POSITIVE)
        - Searching "Meta" → Person named "Meta Johnson" (FALSE POSITIVE)
        - Searching "Amazon" → Person named "Amazonia Smith" (VALID - substring, not exact word)
        """
        name_lower = person.name.lower()
        name_words = name_lower.split()
        
        # Check for exact word matches (not substrings)
        # This catches "Amazon Smith" but not "Amazonia Smith"
        for name_word in name_words:
            # Exact word match (case-insensitive)
            if name_word == self.company:
                return True
            
            # Check if company is multi-word and matches as phrase
            if ' ' in self.company:
                company_words = self.company.split()
                # Check if consecutive words in name match company phrase
                for i in range(len(name_words) - len(company_words) + 1):
                    name_phrase = ' '.join(name_words[i:i+len(company_words)])
                    if name_phrase == self.company:
                        return True
        
        return False
    
    def _is_past_employee(self, person: Person) -> bool:
        """
        Check if title/bio indicates past employment.
        
        Enhanced detection:
        - Expanded keyword list
        - Pattern matching for phrases like "was at [company]" or "[company] alumnus"
        
        Examples:
        - "Former Software Engineer at Google"
        - "Ex-Meta Engineer"
        - "Previously at Amazon"
        - "Was at Stripe"
        - "Google Alumnus"
        """
        if not person.title:
            return False
        
        title_lower = person.title.lower()
        
        # Check for keywords
        for keyword in self.PAST_EMPLOYMENT_KEYWORDS:
            if keyword in title_lower:
                return True
        
        # Pattern matching for common past employment phrases
        past_patterns = [
            r'was\s+at\s+[a-z]+',  # "was at Google"
            r'[a-z]+\s+alumnus',   # "Google alumnus"
            r'alumnus\s+of\s+[a-z]+',  # "alumnus of Google"
            r'formerly\s+[a-z]+',  # "formerly Google"
            r'previous\s+[a-z]+\s+employee',  # "previous Google employee"
        ]
        
        for pattern in past_patterns:
            if re.search(pattern, title_lower):
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
        - Either: LinkedIn URL OR meaningful title
        
        GitHub-only profiles are not sufficient for professional outreach.
        """
        # Must have name (always)
        if not person.name or len(person.name) < 3:
            return True
        
        # Must have professional info OR be from GitHub (for future enrichment)
        has_linkedin = bool(person.linkedin_url)
        has_title = bool(person.title and len(person.title) > 3)
        is_github = person.source in ['github', 'github_legacy']
        
        # Allow GitHub profiles through (they'll be deprioritized by quality score)
        if is_github:
            return False  # Keep GitHub results for future enrichment
        
        # Non-GitHub sources must have LinkedIn or title
        if not (has_linkedin or has_title):
            return True
        
        return False
    
    def _company_mismatch_in_title(self, person: Person) -> bool:
        """
        Check if title explicitly mentions a DIFFERENT company.
        Also verify company is actually mentioned in title (reduces false positives).
        
        Examples:
        - Searching "Google" → Title "Engineer at Microsoft" (MISMATCH)
        - Searching "Meta" → Title "Former Meta, now at Amazon" (MISMATCH)
        - Searching "Stripe" → Title "Software Engineer" with no company mention (FILTER - likely wrong person)
        """
        if not person.title:
            # If no title, require company mention elsewhere (already checked in _missing_critical_info)
            return False
        
        title_lower = person.title.lower()
        company_lower = self.company.lower()
        company_words = company_lower.split()
        
        # Check if company is mentioned in title
        company_mentioned = (
            company_lower in title_lower or
            any(word in title_lower for word in company_words if len(word) > 3)
        )
        
        # If title is generic (like "Software Engineer" without company context), filter out
        # This catches cases where Google returned wrong person
        generic_title_patterns = [
            r'^(software|senior|principal|staff|lead)\s+(engineer|developer|programmer|swe)',
            r'^(product|engineering|technical)\s+(manager|director)',
            r'^(data|machine\s+learning|ml|ai)\s+(engineer|scientist)',
        ]
        
        is_generic = any(re.match(pattern, title_lower) for pattern in generic_title_patterns)
        
        # If title is generic AND company not mentioned, likely wrong person
        if is_generic and not company_mentioned:
            return True  # Filter out - generic title without company context
        
        # Pattern: "at [company]" or "@ [company]"
        at_pattern = r'(?:at|@)\s+([a-z][a-z0-9]+(?:\s+[a-z][a-z0-9]+)*)'
        matches = re.findall(at_pattern, title_lower)
        
        for matched_company in matches:
            matched_lower = matched_company.lower()
            # If they mention a different company (not the target)
            if matched_lower != company_lower:
                # Check if matched company is clearly different (not a variation)
                # e.g., "Google" vs "Alphabet" should be caught, but "google llc" should not
                company_variations = {company_lower, company_words[0] if company_words else company_lower}
                if matched_lower not in company_variations and len(matched_company) > 3:
                    # But allow if they mention BOTH (e.g., "Former Google, now at Amazon")
                    if not any(word in title_lower for word in company_words if len(word) > 3):
                        return True
        
        return False
    
    def _missing_company_context(self, person: Person) -> bool:
        """
        Check if person's title/snippet lacks company context.
        
        Filters out generic titles like "Software Engineer" where company isn't mentioned.
        This catches cases where Google search returned wrong person.
        
        Examples:
        - "Software Engineer" without company → FILTER (generic, no context)
        - "Software Engineer at Stripe" → PASS (company mentioned)
        - "Stripe Software Engineer" → PASS (company mentioned)
        """
        if not person.title:
            return False  # Already checked in _missing_critical_info
        
        title_lower = person.title.lower()
        company_lower = self.company.lower()
        company_words = company_lower.split()
        
        # Check if company is mentioned
        company_mentioned = (
            company_lower in title_lower or
            any(word in title_lower for word in company_words if len(word) > 3)
        )
        
        # If company is mentioned, we're good
        if company_mentioned:
            return False
        
        # If no company mentioned, check if title suggests employment context
        # Titles like "Engineer at X" or "X Engineer" suggest company context
        employment_patterns = [
            r'\bat\s+',  # "Engineer at Company"
            r'\b@\s+',   # "Engineer @ Company"
            r'\b\|\s*',  # "Engineer | Company"
        ]
        
        has_employment_context = any(re.search(pattern, title_lower) for pattern in employment_patterns)
        
        # If title has employment context pattern but no company, might be wrong person
        # But be lenient - allow through if it's a detailed title
        if has_employment_context and not company_mentioned:
            # Could be "Engineer at [different company]" - already caught by _company_mismatch_in_title
            return False  # Let other checks handle this
        
        # Filter very generic titles without company context (high false positive risk)
        very_generic = ['engineer', 'developer', 'programmer', 'manager', 'director']
        title_words = title_lower.split()
        
        # If title is just generic words without company, filter
        if len(title_words) <= 2 and any(gen in title_words for gen in very_generic):
            return True  # Too generic, likely wrong person
        
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

