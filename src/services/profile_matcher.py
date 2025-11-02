"""Profile-based matching logic for connection relevance scoring"""

from typing import List, Optional
from src.models.person import Person
from src.models.job_context import CandidateProfile
from src.db.models import UserProfile, JobRecord


class ProfileMatcher:
    """Match connections based on user profile and job context"""
    
    # Match weights
    ALUMNI_MATCH_WEIGHT = 0.3
    EX_COMPANY_MATCH_WEIGHT = 0.25
    SKILLS_OVERLAP_WEIGHT = 0.2
    DEPARTMENT_MATCH_WEIGHT = 0.15
    LOCATION_MATCH_WEIGHT = 0.1
    
    @classmethod
    def calculate_relevance(
        cls,
        person: Person,
        profile: Optional[UserProfile] = None,
        job: Optional[JobRecord] = None,
        candidate_profile: Optional[CandidateProfile] = None
    ) -> tuple[float, List[str]]:
        """
        Calculate relevance score for a person based on profile and job context.
        
        Args:
            person: Person to score
            profile: User profile (optional)
            job: Job record (optional)
            
        Returns:
            (relevance_score, match_reasons) - Score 0.0-1.0, list of match reasons
        """
        score = person.confidence_score or 0.5  # Start with base confidence
        match_reasons = []
        
        if not profile and not candidate_profile and not job:
            return score, match_reasons
        
        # Extract profile data (support both UserProfile and CandidateProfile)
        if candidate_profile:
            profile_schools = candidate_profile.schools or []
            profile_past_companies = candidate_profile.past_companies or []
            profile_skills = candidate_profile.skills or []
        elif profile:
            profile_schools = profile.schools or []
            profile_past_companies = profile.past_companies or []
            profile_skills = profile.skills or []
        else:
            profile_schools = []
            profile_past_companies = []
            profile_skills = []
        
        # Extract job data
        if job:
            job_department = (job.department or '').lower()
            job_location = (job.location or '').lower()
            job_required_skills = job.required_skills or []
            job_nice_to_have = job.nice_to_have_skills or []
        else:
            job_department = ''
            job_location = ''
            job_required_skills = []
            job_nice_to_have = []
        
        # Check for alumni match
        if profile_schools:
            # Try to match school in person's metadata
            # Check if person's title, location, or other metadata mentions a school
            person_text = ' '.join([
                person.title or '',
                person.location or '',
                person.department or '',
                str(person.skills or [])
            ]).lower()
            
            for school in profile_schools:
                # Normalize school names (remove common words like "University of", "College")
                school_normalized = school.lower()
                school_words = [w for w in school_normalized.split() 
                              if w not in ['university', 'of', 'college', 'the', 'at', 'in']]
                school_keywords = ' '.join(school_words)
                
                # Check if school keywords appear in person's metadata
                if school_keywords and len(school_keywords) > 3:
                    if school_keywords in person_text or any(word in person_text for word in school_words if len(word) > 3):
                        score += cls.ALUMNI_MATCH_WEIGHT
                        match_reasons.append(f'alumni_match ({school})')
                        break
        
        # Check for ex-company match
        if profile_past_companies and person.company:
            person_company_lower = person.company.lower()
            for past_company in profile_past_companies:
                past_company_lower = past_company.lower()
                # Check if person works at a company user used to work at
                # (This could be a connection)
                if past_company_lower in person_company_lower or person_company_lower in past_company_lower:
                    score += cls.EX_COMPANY_MATCH_WEIGHT
                    match_reasons.append('ex_company_match')
                    break
        
        # Check for skills overlap with fuzzy matching and weighting
        if profile_skills or job_required_skills or job_nice_to_have:
            person_skills = [s.lower() for s in (person.skills or [])]
            
            # Build weighted skill sets
            # Required skills (from job) get highest weight
            required_skills_set = set([s.lower() for s in job_required_skills])
            # Nice-to-have skills get medium weight
            nice_to_have_set = set([s.lower() for s in job_nice_to_have])
            # Profile skills get base weight
            profile_skills_set = set([s.lower() for s in profile_skills])
            
            # Check for exact matches first
            exact_overlap_required = set(person_skills) & required_skills_set
            exact_overlap_nice = set(person_skills) & nice_to_have_set
            exact_overlap_profile = set(person_skills) & profile_skills_set
            
            # Fuzzy matching for skill variations
            skill_synonyms = {
                'js': ['javascript'],
                'jsx': ['react'],
                'ts': ['typescript'],
                'ml': ['machine learning'],
                'ai': ['artificial intelligence'],
                'py': ['python'],
                'go': ['golang'],
                'c++': ['cpp'],
                'k8s': ['kubernetes'],
            }
            
            fuzzy_overlap = 0
            for person_skill in person_skills:
                # Check synonyms
                for person_variant in [person_skill] + skill_synonyms.get(person_skill, []):
                    if person_variant in required_skills_set or person_variant in nice_to_have_set or person_variant in profile_skills_set:
                        fuzzy_overlap += 1
                        break
            
            # Calculate weighted score
            overlap_score = 0.0
            # Required skills matches are most valuable
            if exact_overlap_required:
                overlap_score += len(exact_overlap_required) * 0.08  # Higher weight for required
            # Nice-to-have matches
            if exact_overlap_nice:
                overlap_score += len(exact_overlap_nice) * 0.04  # Medium weight
            # Profile skill matches
            if exact_overlap_profile:
                overlap_score += len(exact_overlap_profile) * 0.03  # Lower weight
            
            # Add fuzzy match bonus (capped)
            fuzzy_bonus = min(0.05, fuzzy_overlap * 0.01)
            overlap_score += fuzzy_bonus
            
            # Cap at SKILLS_OVERLAP_WEIGHT
            overlap_score = min(cls.SKILLS_OVERLAP_WEIGHT, overlap_score)
            
            if overlap_score > 0:
                score += overlap_score
                total_matches = len(exact_overlap_required) + len(exact_overlap_nice) + len(exact_overlap_profile)
                match_reasons.append(f'skills_match ({total_matches} skills, {len(exact_overlap_required)} required)')
        
        # Check for department match
        if job_department and person.department:
            person_dept_lower = person.department.lower()
            if job_department in person_dept_lower or person_dept_lower in job_department:
                score += cls.DEPARTMENT_MATCH_WEIGHT
                match_reasons.append('department_match')
        
        # Check for location match
        if job_location and person.location:
            person_loc_lower = person.location.lower()
            if job_location in person_loc_lower or person_loc_lower in job_location:
                score += cls.LOCATION_MATCH_WEIGHT
                match_reasons.append('location_match')
        
        # Factor in source quality (boost high-quality sources)
        from src.core.orchestrator import ConnectionFinder
        source_quality = ConnectionFinder.SOURCE_QUALITY_SCORES.get(person.source, 0.5)
        # Boost score slightly based on source quality (0.05 max boost)
        score += (source_quality - 0.5) * 0.1
        
        # Cap at 1.0
        score = min(1.0, score)
        
        return score, match_reasons
    
    @classmethod
    def enhance_people_with_profile(
        cls,
        people: List[Person],
        profile: Optional[UserProfile] = None,
        job: Optional[JobRecord] = None
    ) -> List[Person]:
        """
        Enhance a list of people with relevance scores based on profile.
        
        Args:
            people: List of Person objects
            profile: User profile (optional)
            job: Job record (optional)
            
        Returns:
            List of Person objects with enhanced relevance scores
        """
        enhanced = []
        
        for person in people:
            relevance_score, match_reasons = cls.calculate_relevance(person, profile, job)
            
            # Store match reasons in person metadata if available
            # Since Person model doesn't have match_reasons, we'll return it separately
            # In the API response, we'll add match_reasons to the JSON
            
            enhanced.append(person)
        
        return enhanced

