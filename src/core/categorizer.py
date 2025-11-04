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
        "lead", "leadership", "principal",
        # AI/ML management roles
        "head of ai", "head of ml", "head of data", "head of engineering",
        "ai lead", "ml lead", "research lead", "engineering lead",
        "director of engineering", "director of ai", "director of ml",
        # Department heads
        "head of product", "head of design", "head of infrastructure",
        "engineering manager", "product lead", "tech lead manager"
    ]
    
    RECRUITER_KEYWORDS = [
        "recruiter", "talent", "recruiting", "hiring", 
        "hr", "human resources", "people operations",
        "people partner", "talent acquisition", "sourcerer",
        # Tech recruiting
        "technical recruiter", "engineering recruiter", "ai recruiter",
        "ml recruiter", "campus recruiter", "university recruiter",
        "talent specialist", "recruiting coordinator"
    ]
    
    SENIOR_KEYWORDS = [
        "senior", "staff", "principal", "architect",
        "distinguished", "fellow", "expert", "specialist",
        # AI/ML seniority markers
        "lead", "staff ai", "staff ml", "senior ai", "senior ml",
        "principal ai", "principal ml", "research scientist", "applied scientist",
        "staff engineer", "senior staff", "tech lead", "team lead",
        # Level indicators
        "iii", "iv", "v", "vi", "l5", "l6", "l7", "e5", "e6"
    ]
    
    # Expanded: Keywords for specific tech roles
    PEER_ROLE_KEYWORDS = [
        # AI/ML roles
        "ai engineer", "ml engineer", "machine learning engineer",
        "applied ai", "applied ml", "research engineer",
        "ai/ml engineer", "mlops engineer", "ai researcher",
        "deep learning engineer", "computer vision engineer",
        "nlp engineer", "data scientist", "ml scientist",
        
        # Software/Engineering roles
        "software engineer", "software developer", "swe",
        "backend engineer", "frontend engineer", "full stack",
        "fullstack engineer", "platform engineer", "systems engineer",
        "infrastructure engineer", "devops engineer", "sre",
        "site reliability engineer", "cloud engineer", "security engineer",
        
        # Mobile/Web
        "ios engineer", "android engineer", "mobile engineer",
        "web developer", "ui engineer", "ux engineer",
        
        # Data roles
        "data engineer", "data analyst", "analytics engineer",
        "business intelligence", "bi engineer", "data architect",
        
        # Product/Design
        "product manager", "pm", "product owner", "tpm",
        "technical program manager", "product designer", "ux designer",
        "ui designer", "interaction designer",
        
        # Specialized
        "blockchain engineer", "crypto engineer", "game developer",
        "embedded engineer", "firmware engineer", "hardware engineer",
        "robotics engineer", "ar/vr engineer", "graphics engineer",
        
        # Early career
        "intern", "engineering intern", "software intern",
        "new grad", "associate engineer", "junior engineer",
        "entry level", "apprentice"
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
        
        # Check for recruiter (highest priority)
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
        
        # Check for exact role matches (NEW - improves peer detection)
        if any(kw in title_lower for kw in self.PEER_ROLE_KEYWORDS):
            # Verify it's not senior/manager role
            if not any(kw in title_lower for kw in self.MANAGER_KEYWORDS + self.SENIOR_KEYWORDS):
                person.category = PersonCategory.PEER
                return person
        
        # Check if it's similar to target title (peer)
        if self._is_similar_title(title_lower, self.target_title):
            person.category = PersonCategory.PEER
            return person
        
        # Try fuzzy matching for edge cases
        if self._fuzzy_match_role(title_lower, self.target_title):
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
    
    def _fuzzy_match_role(self, title: str, target: str) -> bool:
        """
        Fuzzy match for roles that don't exactly match keywords.
        Helps catch variations like "AI Eng" vs "AI Engineer"
        """
        # Remove common words and clean
        stop_words = {'the', 'a', 'an', 'and', 'or', 'at', 'in', 'of', 'for', 'with'}
        
        title_words = set(title.lower().split()) - stop_words
        target_words = set(target.lower().split()) - stop_words
        
        # Check word overlap
        if not title_words or not target_words:
            return False
            
        overlap = title_words & target_words
        
        # If 50%+ overlap, consider it a match
        overlap_ratio = len(overlap) / min(len(title_words), len(target_words))
        if overlap_ratio >= 0.5:
            return True
        
        # Check for tech role variations and abbreviations
        tech_variations = {
            # AI/ML variations
            'ai': ['artificial intelligence', 'a.i.', 'ml', 'machine learning'],
            'ml': ['machine learning', 'ai', 'artificial intelligence'],
            'mlops': ['ml ops', 'ml operations', 'machine learning operations'],
            'nlp': ['natural language processing', 'language processing'],
            'cv': ['computer vision', 'vision'],
            
            # Engineering variations
            'eng': ['engineer', 'engineering', 'engr'],
            'dev': ['developer', 'development'],
            'swe': ['software engineer', 'software developer', 'software eng'],
            'sde': ['software development engineer', 'software dev engineer'],
            'fe': ['frontend', 'front end', 'front-end'],
            'be': ['backend', 'back end', 'back-end'],
            'fs': ['fullstack', 'full stack', 'full-stack'],
            'devops': ['dev ops', 'development operations'],
            'sre': ['site reliability', 'site reliability engineer'],
            
            # Product/Management
            'pm': ['product manager', 'product management'],
            'tpm': ['technical program manager', 'tech program manager'],
            'em': ['engineering manager', 'eng manager'],
            
            # Data roles
            'ds': ['data scientist', 'data science'],
            'de': ['data engineer', 'data engineering'],
            'da': ['data analyst', 'data analysis'],
            'bi': ['business intelligence', 'business intel'],
            
            # Other common abbreviations
            'sr': ['senior'],
            'jr': ['junior'],
            'assoc': ['associate'],
            'mgr': ['manager'],
            'dir': ['director'],
            'vp': ['vice president'],
            'infra': ['infrastructure'],
            'sec': ['security'],
            'arch': ['architect', 'architecture']
        }
        
        # Check if any variations match
        for word in title_words:
            if word in tech_variations:
                variations = tech_variations[word]
                for var in variations:
                    if any(v in target_words for v in var.split()):
                        return True
        
        return False
    
    def is_early_career_role(self, title: str) -> bool:
        """
        Detect if a title is for early career (intern, new grad, junior).
        Important for matching appropriate connections.
        """
        title_lower = title.lower()
        
        early_career_indicators = [
            'intern', 'internship', 'co-op', 'coop',
            'new grad', 'new graduate', 'recent grad',
            'entry level', 'entry-level', 'associate',
            'junior', 'jr', 'apprentice', 'trainee',
            'early career', 'campus', 'university',
            # Level indicators
            'level 1', 'l1', 'e1', 'e2'
        ]
        
        return any(indicator in title_lower for indicator in early_career_indicators)
    
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

