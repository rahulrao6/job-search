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
    
    def __init__(self, company: str, company_domain: str = None):
        """
        Initialize validator for a specific company search.
        
        Args:
            company: Company name being searched
            company_domain: Optional company domain for better verification
        """
        self.company = company.lower().strip()
        self.company_words = set(self.company.split())
        self.company_domain = company_domain.lower().strip() if company_domain else None
    
    def validate_person(self, person: Person) -> tuple[bool, float, str, dict]:
        """
        Validate if person is a real current employee with confidence scoring.
        
        Returns:
            (is_valid, confidence_score, reason_if_invalid, validation_details)
        """
        confidence = 1.0  # Start with full confidence
        validation_details = {
            'checks_passed': [],
            'checks_failed': [],
            'warnings': [],
            'confidence_breakdown': {}
        }
        
        # Check 1: Name matches company name (-0.9 confidence, likely reject)
        if self._name_matches_company(person):
            confidence *= 0.1
            validation_details['checks_failed'].append('name_matches_company')
            validation_details['confidence_breakdown']['name_check'] = 0.1
            if confidence < 0.2:
                return False, confidence, "Name matches company name (likely false positive)", validation_details
        else:
            validation_details['checks_passed'].append('name_check')
            validation_details['confidence_breakdown']['name_check'] = 1.0
        
        # Check 2: Past employment indicators with enhanced verification
        # Get text snippet if available (from LinkedIn search results)
        text_snippet = getattr(person, '_text_snippet', None) or person.title
        is_past, confidence_boost = self._is_past_employee(person, text_snippet)
        
        if is_past:
            confidence *= 0.2
            validation_details['checks_failed'].append('past_employee')
            validation_details['confidence_breakdown']['employment_status'] = 0.2
            if confidence < 0.2:
                return False, confidence, "Past employee (not current)", validation_details
        else:
            # Apply confidence boost from verification
            if confidence_boost > 0:
                confidence = min(1.0, confidence + confidence_boost)
            validation_details['checks_passed'].append('current_employee')
            validation_details['confidence_breakdown']['employment_status'] = min(1.0, 0.8 + confidence_boost)
        
        # Check 3: Generic/spam profile (-0.5 confidence)
        if self._is_spam_profile(person):
            confidence *= 0.5
            validation_details['warnings'].append('possible_spam_profile')
            validation_details['confidence_breakdown']['profile_quality'] = 0.5
        else:
            validation_details['checks_passed'].append('profile_quality')
            validation_details['confidence_breakdown']['profile_quality'] = 1.0
        
        # Check 4: Missing critical info (-0.3 confidence per missing field)
        missing_info_penalty = self._calculate_missing_info_penalty(person)
        if missing_info_penalty > 0:
            confidence *= (1.0 - missing_info_penalty)
            validation_details['warnings'].append(f'missing_info_penalty_{missing_info_penalty:.2f}')
            validation_details['confidence_breakdown']['info_completeness'] = 1.0 - missing_info_penalty
        else:
            validation_details['checks_passed'].append('info_complete')
            validation_details['confidence_breakdown']['info_completeness'] = 1.0
        
        # Check 5: Company mismatch in title (-0.7 confidence)
        if self._company_mismatch_in_title(person):
            confidence *= 0.3
            validation_details['checks_failed'].append('company_mismatch')
            validation_details['confidence_breakdown']['company_match'] = 0.3
            if confidence < 0.2:
                return False, confidence, "Title indicates different company", validation_details
        else:
            validation_details['checks_passed'].append('company_match')
            validation_details['confidence_breakdown']['company_match'] = 1.0
        
        # Check 6: Company context (+0.2 confidence if strong signals)
        company_context_score = self._evaluate_company_context(person)
        if company_context_score < 0.3:
            confidence *= 0.5
            validation_details['warnings'].append('weak_company_context')
            validation_details['confidence_breakdown']['company_context'] = 0.5
        else:
            confidence *= (0.8 + 0.2 * company_context_score)  # Boost for strong context
            validation_details['checks_passed'].append('strong_company_context')
            validation_details['confidence_breakdown']['company_context'] = company_context_score
        
        # Final decision based on confidence
        if confidence < 0.3:
            return False, confidence, "Low confidence match", validation_details
        
        return True, confidence, "", validation_details
    
    def validate_batch(self, people: List[Person]) -> List[Person]:
        """
        Validate a batch of people, keeping only valid ones.
        
        Returns:
            List of validated people with confidence scores adjusted
        """
        validated = []
        validation_results = []
        
        for person in people:
            is_valid, confidence, reason, details = self.validate_person(person)
            
            if is_valid:
                # Update person's confidence score with validation confidence
                person.confidence_score = confidence
                validated.append(person)
                validation_results.append((person, confidence, details))
            elif confidence < 0.2:  # Only log very low confidence rejections
                print(f"  ⊘ Filtered: {person.name} - {reason} (confidence={confidence:.2f})")
        
        # Remove duplicates, keeping highest confidence version
        seen_names = {}
        for person in validated:
            if person.name not in seen_names or person.confidence_score > seen_names[person.name].confidence_score:
                seen_names[person.name] = person
        
        # Return unique validated people sorted by confidence
        unique_validated = list(seen_names.values())
        return sorted(unique_validated, key=lambda p: p.confidence_score, reverse=True)
    
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
    
    def _is_past_employee(self, person: Person, text_snippet: Optional[str] = None) -> tuple[bool, float]:
        """
        Check if title/bio indicates past employment with confidence scoring.
        
        Enhanced detection:
        - Date pattern parsing for LinkedIn formats
        - Recency signal detection with scoring
        - Position order checking
        
        Returns:
            (is_past_employee: bool, confidence_boost: float)
            - is_past_employee: True if likely past employee
            - confidence_boost: Negative score if past, positive if current
        
        Examples:
        - "Former Software Engineer at Google" → (True, -0.8)
        - "Software Engineer at Google - Present" → (False, 0.3)
        - "Jan 2023 - Present" with company → (False, 0.2)
        """
        if not person.title:
            return False, 0.0
        
        title_lower = person.title.lower()
        text_to_check = (text_snippet or person.title).lower()
        
        # Negative score accumulator
        negative_score = 0.0
        positive_score = 0.0
        
        # Check for negative keywords with weighted scoring
        negative_keywords = {
            'formerly': 2.0,
            'ex-': 2.0,
            'was at': 1.0,
            'worked at': 1.0,
            'alumni': 1.0,
            'former': 2.0,
            'previously': 1.5,
            'past': 1.0,
            'retired from': 2.0,
        }
        
        for keyword, weight in negative_keywords.items():
            if keyword in text_to_check:
                # Check proximity to company name
                keyword_pos = text_to_check.find(keyword)
                company_pos = text_to_check.find(self.company)
                if company_pos != -1 and abs(keyword_pos - company_pos) < 50:
                    negative_score += weight
        
        # Date pattern parsing for LinkedIn date formats
        date_patterns = [
            r'(\w+\s+\d{4})\s*[-–]\s*(Present|Current)',  # "Jan 2023 - Present"
            r'(\d{4})\s*[-–]\s*(Present|Current)',        # "2023 - Present"
            r'(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4})',      # "Jan 2023 - Dec 2024"
        ]
        
        has_present_date = False
        for pattern in date_patterns:
            match = re.search(pattern, text_to_check, re.IGNORECASE)
            if match:
                end_date = match.group(2) if len(match.groups()) >= 2 else None
                if end_date and end_date.lower() in ['present', 'current']:
                    has_present_date = True
                    positive_score += 0.3
                    break
        
        # Positive signals for current employment
        positive_signals = {
            f'at {self.company}': 0.3,
            f'{self.company} · full-time': 0.3,
            'present': 0.2,
            'current': 0.2,
            'ongoing': 0.15,
        }
        
        for signal, weight in positive_signals.items():
            if signal in text_to_check:
                positive_score += weight
                break  # Only count strongest signal
        
        # Position order check - LinkedIn shows current job first
        # If company appears in first 100 chars, it's likely current position
        if text_snippet:
            first_100_chars = text_snippet[:100].lower()
            if self.company.lower() in first_100_chars:
                positive_score += 0.3
        
        # Determine if past employee
        is_past = negative_score > 1.5 or (negative_score > 0.5 and not has_present_date and positive_score < 0.2)
        
        # Calculate confidence boost (negative if past, positive if current)
        confidence_boost = positive_score - (negative_score * 0.3)
        
        return is_past, confidence_boost
    
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
        - Searching "Root" → Title "Engineer at Roots AI" (MISMATCH - different company)
        """
        if not person.title:
            return False
        
        title_lower = person.title.lower()
        company_lower = self.company.lower()
        company_words = company_lower.split()
        
        # Check if company OR domain is mentioned (domain is strong signal)
        company_mentioned = (
            company_lower in title_lower or
            any(word in title_lower for word in company_words if len(word) > 3)
        )
        
        # Check domain if available
        if self.company_domain and self.company_domain in title_lower:
            company_mentioned = True
        
        # If title is generic without company context, filter out
        generic_title_patterns = [
            r'^(software|senior|principal|staff|lead)\s+(engineer|developer|programmer|swe)',
            r'^(product|engineering|technical)\s+(manager|director)',
            r'^(data|machine\s+learning|ml|ai)\s+(engineer|scientist)',
            r'^(ai|ml|applied)\s+(engineer|researcher)',
        ]
        
        is_generic = any(re.match(pattern, title_lower) for pattern in generic_title_patterns)
        
        if is_generic and not company_mentioned:
            return True  # Filter out - generic title without company context
        
        # Check for false positive companies (e.g., Root vs Roots AI)
        false_positive_companies = {
            'root': ['root insurance', 'roots ai', 'square root', 'grassroots', 'root cause'],
            'meta': ['metadata', 'metallic', 'metamask', 'metaphor'],
            'apple': ['apple tree', 'pineapple', 'apple valley'],
            'amazon': ['amazon rainforest', 'amazonia'],
        }
        
        if company_lower in false_positive_companies:
            for false_positive in false_positive_companies[company_lower]:
                if false_positive in title_lower:
                    return True  # Wrong company!
        
        # Pattern: "at [company]" or "@ [company]"
        at_pattern = r'(?:at|@)\s+([a-z][a-z0-9]+(?:\s+[a-z][a-z0-9]+)*)'
        matches = re.findall(at_pattern, title_lower)
        
        for matched_company in matches:
            matched_lower = matched_company.lower()
            # If they mention a different company (not the target)
            if matched_lower != company_lower:
                # Check if matched company is clearly different
                company_variations = {company_lower}
                if company_words:
                    company_variations.add(company_words[0])
                
                # Add domain variations
                if self.company_domain:
                    domain_base = self.company_domain.split('.')[0]
                    company_variations.add(domain_base)
                
                if matched_lower not in company_variations and len(matched_company) > 3:
                    # But allow if they mention BOTH companies
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
    
    def _calculate_missing_info_penalty(self, person: Person) -> float:
        """
        Calculate penalty for missing information.
        
        Returns:
            Penalty score 0.0-1.0 (higher = more penalty)
        """
        penalty = 0.0
        missing_fields = []
        
        # Critical fields
        if not person.name or person.name.strip() == "":
            penalty += 0.3
            missing_fields.append('name')
        
        if not person.title or person.title.strip() == "":
            penalty += 0.2
            missing_fields.append('title')
            
        if not person.linkedin_url:
            penalty += 0.1
            missing_fields.append('linkedin_url')
            
        # Nice-to-have fields
        if not person.location:
            penalty += 0.05
            missing_fields.append('location')
            
        if not person.skills or len(person.skills) == 0:
            penalty += 0.05
            missing_fields.append('skills')
        
        return min(penalty, 0.7)  # Cap at 70% penalty
    
    def _evaluate_company_context(self, person: Person) -> float:
        """
        Evaluate how strongly the company context appears in person data.
        
        Returns:
            Score 0.0-1.0 (higher = stronger company signals)
        """
        score = 0.0
        
        # Build text to analyze
        text_parts = []
        if person.title:
            text_parts.append(person.title.lower())
        if person.department:
            text_parts.append(person.department.lower())
        if person.location:
            text_parts.append(person.location.lower())
            
        combined_text = ' '.join(text_parts)
        
        # Check for company name
        if self.company in combined_text:
            score += 0.4
            
        # Check for company domain
        if self.company_domain and self.company_domain in combined_text:
            score += 0.3
            
        # Check for @ symbol pattern (e.g., "@ Company")
        if f"@ {self.company}" in combined_text or f"@{self.company}" in combined_text:
            score += 0.2
            
        # Check for "at Company" pattern
        if f"at {self.company}" in combined_text:
            score += 0.1
            
        # Bonus for current/present tense indicators
        current_indicators = ['currently', 'present', 'current role', 'works at', 'working at']
        if any(indicator in combined_text for indicator in current_indicators):
            score *= 1.2
        
        return min(score, 1.0)  # Cap at 1.0


def get_validator(company: str, company_domain: str = None) -> PersonValidator:
    """Get a validator instance for a company"""
    return PersonValidator(company, company_domain)

