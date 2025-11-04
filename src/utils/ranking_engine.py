"""
Advanced ranking engine for connection quality scoring.

Implements multi-factor scoring to ensure the best connections
appear at the top, especially for early career job seekers.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.models.person import Person, PersonCategory
from src.models.job_context import JobContext, CandidateProfile


class MatchType(Enum):
    """Types of matches between candidate and connection"""
    ALUMNI = "alumni"
    PAST_COMPANY = "past_company"
    SKILL_MATCH = "skill_match"
    DEPARTMENT = "department"
    LOCATION = "location"
    SENIORITY = "seniority"


@dataclass
class ScoringWeights:
    """Configurable weights for different scoring factors"""
    # Employment verification
    current_employee_weight: float = 0.3
    
    # Role relevance
    role_relevance_weight: float = 0.25
    
    # Profile matching
    profile_match_weight: float = 0.2
    
    # Data quality
    data_quality_weight: float = 0.15
    
    # Source quality
    source_quality_weight: float = 0.1
    
    def validate(self):
        """Ensure weights sum to 1.0"""
        total = (
            self.current_employee_weight + 
            self.role_relevance_weight + 
            self.profile_match_weight + 
            self.data_quality_weight + 
            self.source_quality_weight
        )
        assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"


class RankingEngine:
    """
    Advanced ranking engine for connection scoring.
    
    Prioritizes:
    1. Current employees at target company
    2. Relevant roles (recruiter > manager > peer)
    3. Profile matches (alumni, skills, etc.)
    4. Data quality (LinkedIn URL, recent data)
    """
    
    # Category relevance scores for different job seeker types
    CATEGORY_RELEVANCE = {
        # Early career (intern, new grad)
        "early_career": {
            PersonCategory.RECRUITER: 1.0,     # Recruiters most helpful
            PersonCategory.MANAGER: 0.85,      # Managers can hire
            PersonCategory.SENIOR: 0.8,        # Seniors can mentor/refer
            PersonCategory.PEER: 0.7,          # Peers understand the role
            PersonCategory.UNKNOWN: 0.2,       # Avoid unknowns
        },
        # Mid career
        "mid_career": {
            PersonCategory.MANAGER: 0.95,      # Managers are key
            PersonCategory.RECRUITER: 0.9,     # Still important
            PersonCategory.SENIOR: 0.85,       # Potential future colleagues
            PersonCategory.PEER: 0.75,         # Current colleagues
            PersonCategory.UNKNOWN: 0.3,
        },
        # Senior/Staff
        "senior_career": {
            PersonCategory.MANAGER: 1.0,       # Directors/VPs crucial
            PersonCategory.SENIOR: 0.9,        # Fellow seniors
            PersonCategory.RECRUITER: 0.8,     # Less critical at this level
            PersonCategory.PEER: 0.7,          # Peers at level
            PersonCategory.UNKNOWN: 0.4,
        }
    }
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        self.weights.validate()
    
    def rank_people(
        self, 
        people: List[Person],
        job_context: Optional[JobContext] = None,
        candidate_profile: Optional[CandidateProfile] = None,
        source_quality_map: Optional[Dict[str, float]] = None
    ) -> List[Tuple[Person, float, Dict[str, float]]]:
        """
        Rank people by relevance with detailed scoring.
        
        Returns:
            List of (Person, total_score, score_breakdown) tuples
        """
        if not people:
            return []
        
        # Determine career stage
        career_stage = self._determine_career_stage(job_context, candidate_profile)
        
        # Score each person
        scored_people = []
        for person in people:
            score, breakdown = self._calculate_score(
                person, 
                career_stage,
                job_context, 
                candidate_profile,
                source_quality_map
            )
            scored_people.append((person, score, breakdown))
        
        # Sort by score (highest first)
        scored_people.sort(key=lambda x: x[1], reverse=True)
        
        return scored_people
    
    def _determine_career_stage(
        self, 
        job_context: Optional[JobContext],
        candidate_profile: Optional[CandidateProfile]
    ) -> str:
        """Determine career stage from context"""
        # Check job title
        if job_context:
            title_lower = (job_context.job_title or "").lower()
            
            # Early career indicators
            early_indicators = ["intern", "new grad", "junior", "entry", "associate"]
            if any(ind in title_lower for ind in early_indicators):
                return "early_career"
            
            # Senior indicators
            senior_indicators = ["senior", "staff", "principal", "lead", "director"]
            if any(ind in title_lower for ind in senior_indicators):
                return "senior_career"
        
        # Check years of experience
        if candidate_profile and hasattr(candidate_profile, 'years_experience'):
            years = getattr(candidate_profile, 'years_experience', 0)
            if years < 3:
                return "early_career"
            elif years > 8:
                return "senior_career"
        
        # Default to mid-career
        return "mid_career"
    
    def _calculate_score(
        self,
        person: Person,
        career_stage: str,
        job_context: Optional[JobContext],
        candidate_profile: Optional[CandidateProfile],
        source_quality_map: Optional[Dict[str, float]]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate comprehensive score for a person"""
        breakdown = {}
        
        # 1. Employment Verification Score (0-1)
        employment_score = self._calculate_employment_score(person)
        breakdown['employment'] = employment_score
        
        # 2. Role Relevance Score (0-1)
        role_score = self._calculate_role_relevance(person, career_stage)
        breakdown['role_relevance'] = role_score
        
        # 3. Profile Match Score (0-1)
        profile_score, match_types = self._calculate_profile_match(
            person, job_context, candidate_profile
        )
        breakdown['profile_match'] = profile_score
        breakdown['match_types'] = match_types
        
        # 4. Data Quality Score (0-1)
        quality_score = self._calculate_data_quality(person)
        breakdown['data_quality'] = quality_score
        
        # 5. Source Quality Score (0-1)
        source_score = 0.5  # Default
        if source_quality_map and person.source in source_quality_map:
            source_score = source_quality_map[person.source]
        breakdown['source_quality'] = source_score
        
        # Calculate weighted total
        total_score = (
            employment_score * self.weights.current_employee_weight +
            role_score * self.weights.role_relevance_weight +
            profile_score * self.weights.profile_match_weight +
            quality_score * self.weights.data_quality_weight +
            source_score * self.weights.source_quality_weight
        )
        
        return total_score, breakdown
    
    def _calculate_employment_score(self, person: Person) -> float:
        """Score based on employment verification confidence"""
        # Use the confidence score which includes employment verification
        base_score = person.confidence_score or 0.5
        
        # Boost if we have strong signals
        if person.linkedin_url and person.company:
            base_score = min(1.0, base_score + 0.1)
        
        return base_score
    
    def _calculate_role_relevance(self, person: Person, career_stage: str) -> float:
        """Score based on role category relevance"""
        relevance_map = self.CATEGORY_RELEVANCE.get(career_stage, self.CATEGORY_RELEVANCE["mid_career"])
        return relevance_map.get(person.category, 0.5)
    
    def _calculate_profile_match(
        self,
        person: Person,
        job_context: Optional[JobContext],
        candidate_profile: Optional[CandidateProfile]
    ) -> Tuple[float, List[str]]:
        """Calculate profile matching score"""
        score = 0.0
        matches = []
        
        if not candidate_profile:
            return 0.5, []  # Neutral score if no profile
        
        # Alumni match (highest weight for early career)
        if candidate_profile.schools and person.title:
            # Simple heuristic: check if school name appears in person's data
            person_text = f"{person.title} {person.company}".lower()
            for school in candidate_profile.schools:
                if school.lower() in person_text:
                    score += 0.3
                    matches.append(MatchType.ALUMNI.value)
                    break
        
        # Past company match
        if candidate_profile.past_companies:
            for company in candidate_profile.past_companies:
                if company.lower() in (person.title or "").lower():
                    score += 0.2
                    matches.append(MatchType.PAST_COMPANY.value)
                    break
        
        # Skills match
        if candidate_profile.skills and person.skills:
            overlap = set(s.lower() for s in candidate_profile.skills) & \
                     set(s.lower() for s in person.skills)
            if overlap:
                score += min(0.2, len(overlap) * 0.05)
                matches.append(MatchType.SKILL_MATCH.value)
        
        # Department match
        if job_context and job_context.department and person.department:
            if job_context.department.lower() in person.department.lower():
                score += 0.15
                matches.append(MatchType.DEPARTMENT.value)
        
        # Location match
        if job_context and job_context.location and person.location:
            job_loc = job_context.location.lower()
            person_loc = person.location.lower()
            if job_loc in person_loc or person_loc in job_loc:
                score += 0.1
                matches.append(MatchType.LOCATION.value)
        
        return min(1.0, score), matches
    
    def _calculate_data_quality(self, person: Person) -> float:
        """Score based on data completeness and quality"""
        score = 0.0
        
        # Has LinkedIn URL (most important)
        if person.linkedin_url:
            score += 0.4
        
        # Has title
        if person.title and person.title != "Unknown":
            score += 0.2
        
        # Has location
        if person.location:
            score += 0.1
        
        # Has department
        if person.department:
            score += 0.1
        
        # Not in unknown category
        if person.category != PersonCategory.UNKNOWN:
            score += 0.2
        
        return score
    
    def explain_ranking(
        self,
        person: Person,
        score: float,
        breakdown: Dict[str, float]
    ) -> str:
        """Generate human-readable explanation of ranking"""
        explanations = []
        
        # Employment status
        emp_score = breakdown.get('employment', 0)
        if emp_score >= 0.8:
            explanations.append("✓ Verified current employee")
        elif emp_score >= 0.5:
            explanations.append("◐ Likely current employee")
        else:
            explanations.append("✗ Employment uncertain")
        
        # Role relevance
        if person.category == PersonCategory.RECRUITER:
            explanations.append("★ Recruiter - can directly help with applications")
        elif person.category == PersonCategory.MANAGER:
            explanations.append("★ Hiring manager - decision maker")
        elif person.category == PersonCategory.SENIOR:
            explanations.append("◆ Senior professional - valuable referral")
        
        # Profile matches
        matches = breakdown.get('match_types', [])
        if MatchType.ALUMNI.value in matches:
            explanations.append("🎓 Alumni connection")
        if MatchType.PAST_COMPANY.value in matches:
            explanations.append("🏢 Worked at same company")
        if MatchType.SKILL_MATCH.value in matches:
            explanations.append("💡 Matching skills")
        
        # Data quality
        if person.linkedin_url:
            explanations.append("🔗 LinkedIn profile available")
        
        return " | ".join(explanations)
