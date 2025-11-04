"""
Smart query generation based on context for enhanced search accuracy.
"""

from typing import List, Optional, Dict, Tuple
from src.models.job_context import JobContext, CandidateProfile
from src.core.categorizer import PersonCategorizer
from src.utils.company_resolver import CompanyResolver


class QueryOptimizer:
    """
    Generate optimized search queries based on job context, career stage, and user profile.
    """
    
    # Query templates by platform
    PLATFORM_TEMPLATES = {
        'linkedin': {
            'base': 'site:linkedin.com/in/',
            'company_patterns': [
                '"{company}"',
                '{company}',
                '"{company}" currently',
                '"works at {company}"',
                '"@ {company}"'
            ]
        },
        'github': {
            'base': 'site:github.com/',
            'patterns': [
                '{company} {title}',
                '"{company}" {title}',
                'org:{company} {title}'
            ]
        },
        'general': {
            'patterns': [
                '"{company}" {title} LinkedIn',
                '"{company}" {title} profile',
                '"{company}" {title} team'
            ]
        }
    }
    
    # Career stage specific query modifiers
    CAREER_STAGE_MODIFIERS = {
        'early_career': {
            'keywords': ['intern', 'new grad', 'associate', 'junior', 'entry level'],
            'exclude': ['-senior', '-principal', '-staff', '-lead', '-manager'],
            'boost_alumni': True,
            'boost_campus': True
        },
        'mid_career': {
            'keywords': [],
            'exclude': [],
            'boost_alumni': False,
            'boost_campus': False
        },
        'senior_career': {
            'keywords': ['senior', 'staff', 'principal', 'lead'],
            'exclude': ['-intern', '-junior'],
            'boost_alumni': False,
            'boost_campus': False
        }
    }
    
    # Role-specific query enhancers
    ROLE_ENHANCERS = {
        'ai_ml': ['AI', 'ML', 'machine learning', 'deep learning', 'data science'],
        'software': ['software', 'engineer', 'developer', 'SWE'],
        'data': ['data', 'analytics', 'BI', 'ETL'],
        'product': ['product', 'PM', 'product manager'],
        'design': ['design', 'UX', 'UI', 'designer'],
        'devops': ['devops', 'SRE', 'infrastructure', 'platform']
    }
    
    def __init__(self):
        self.company_resolver = CompanyResolver()
        self.categorizer = None
    
    def generate_queries(
        self,
        company: str,
        title: Optional[str] = None,
        job_context: Optional[JobContext] = None,
        candidate_profile: Optional[CandidateProfile] = None,
        platform: str = 'linkedin'
    ) -> List[str]:
        """
        Generate optimized search queries based on all available context.
        
        Args:
            company: Company name
            title: Job title to search for
            job_context: Full job context with skills, location, etc.
            candidate_profile: User profile with schools, past companies
            platform: Target platform (linkedin, github, general)
            
        Returns:
            List of optimized query strings, ordered by relevance
        """
        queries = []
        
        # Detect career stage
        career_stage = self._detect_career_stage(title or (job_context.job_title if job_context else ''))
        stage_mods = self.CAREER_STAGE_MODIFIERS[career_stage]
        
        # Get company variations
        company_domain = None
        if job_context and job_context.company_domain:
            company_domain = job_context.company_domain
        else:
            company_domain = self.company_resolver.get_company_domain(company)
        
        # Get company patterns
        company_patterns = self.company_resolver.get_company_patterns(company, company_domain)
        
        # Build platform-specific queries
        if platform == 'linkedin':
            queries.extend(self._build_linkedin_queries(
                company, title, company_domain, company_patterns,
                job_context, candidate_profile, career_stage, stage_mods
            ))
        elif platform == 'github':
            queries.extend(self._build_github_queries(
                company, title, company_patterns, job_context
            ))
        else:
            queries.extend(self._build_general_queries(
                company, title, company_domain, job_context
            ))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries
    
    def _detect_career_stage(self, title: str) -> str:
        """Detect career stage from job title"""
        if not title:
            return 'mid_career'
            
        if not self.categorizer:
            self.categorizer = PersonCategorizer(title)
            
        if self.categorizer.is_early_career_role(title):
            return 'early_career'
        elif any(kw in title.lower() for kw in ['senior', 'staff', 'principal', 'lead']):
            return 'senior_career'
        return 'mid_career'
    
    def _build_linkedin_queries(
        self,
        company: str,
        title: Optional[str],
        company_domain: Optional[str],
        company_patterns: Dict[str, List[str]],
        job_context: Optional[JobContext],
        candidate_profile: Optional[CandidateProfile],
        career_stage: str,
        stage_mods: dict
    ) -> List[str]:
        """Build LinkedIn-specific queries"""
        queries = []
        base = self.PLATFORM_TEMPLATES['linkedin']['base']
        
        # Priority 1: Domain + Company + Title (most specific)
        if company_domain and title:
            queries.append(f'{base} "{company}" "{company_domain}" {title}')
            
            # Add career stage modifiers
            if career_stage == 'early_career' and stage_mods['keywords']:
                for keyword in stage_mods['keywords'][:2]:
                    queries.append(f'{base} "{company}" {title} {keyword}')
        
        # Priority 2: Company patterns + Title
        if title and company_patterns.get('linkedin'):
            for pattern in company_patterns['linkedin'][:3]:
                query = f'{base} {pattern} {title}'
                
                # Add exclusions for career stage
                if stage_mods['exclude']:
                    query += ' ' + ' '.join(stage_mods['exclude'])
                    
                queries.append(query)
        
        # Priority 3: Alumni queries (boosted for early career)
        if candidate_profile and candidate_profile.schools:
            boost = 2 if stage_mods['boost_alumni'] else 1
            for i in range(min(boost, len(candidate_profile.schools))):
                school = candidate_profile.schools[i]
                if title:
                    queries.append(f'{base} "{company}" {title} "{school}"')
                else:
                    queries.append(f'{base} "{company}" "{school}"')
        
        # Priority 4: Skills-based queries
        if job_context and job_context.candidate_skills and title:
            # Detect role type and add enhancers
            role_type = self._detect_role_type(title)
            if role_type and role_type in self.ROLE_ENHANCERS:
                enhancers = self.ROLE_ENHANCERS[role_type]
                skill_query = f'{base} "{company}" {title}'
                for enhancer in enhancers[:2]:
                    if enhancer.lower() not in title.lower():
                        skill_query += f' {enhancer}'
                queries.append(skill_query)
            
            # Add top required skills
            top_skills = job_context.candidate_skills[:2]
            if top_skills:
                queries.append(f'{base} "{company}" {title} {" ".join(top_skills)}')
        
        # Priority 5: Department/Team queries
        if job_context and job_context.department and title:
            queries.append(f'{base} "{company}" "{job_context.department}" {title}')
            
            # For early career, also try campus recruiting
            if career_stage == 'early_career':
                queries.append(f'{base} "{company}" campus recruiter')
                queries.append(f'{base} "{company}" university recruiting')
        
        # Priority 6: Location-based (if specified)
        if job_context and job_context.location and title:
            queries.append(f'{base} "{company}" {title} "{job_context.location}"')
        
        # Priority 7: Ex-employee queries (for referrals)
        if candidate_profile and candidate_profile.past_companies and title:
            for past_company in candidate_profile.past_companies[:1]:
                queries.append(f'{base} "{past_company}" to "{company}" {title}')
        
        return queries
    
    def _build_github_queries(
        self,
        company: str,
        title: Optional[str],
        company_patterns: Dict[str, List[str]],
        job_context: Optional[JobContext]
    ) -> List[str]:
        """Build GitHub-specific queries"""
        queries = []
        
        # GitHub org searches
        if title:
            queries.append(f'org:{company} {title}')
            queries.append(f'user:{company} {title}')
        
        # GitHub bio/location searches
        if job_context and job_context.location:
            queries.append(f'{company} location:"{job_context.location}" {title or ""}')
        
        # Skills in repos
        if job_context and job_context.candidate_skills:
            for skill in job_context.candidate_skills[:2]:
                queries.append(f'{company} language:{skill} {title or ""}')
        
        return queries
    
    def _build_general_queries(
        self,
        company: str,
        title: Optional[str],
        company_domain: Optional[str],
        job_context: Optional[JobContext]
    ) -> List[str]:
        """Build general web search queries"""
        queries = []
        
        if title:
            # Company website team pages
            if company_domain:
                queries.append(f'site:{company_domain} team {title}')
                queries.append(f'site:{company_domain} "our team" {title}')
                queries.append(f'site:{company_domain} about {title}')
            
            # General patterns
            queries.append(f'"{company}" {title} LinkedIn profile')
            queries.append(f'"{company}" {title} team member')
            queries.append(f'"{company}" {title} employee')
        
        return queries
    
    def _detect_role_type(self, title: str) -> Optional[str]:
        """Detect the general role type from title"""
        title_lower = title.lower()
        
        role_mappings = {
            'ai_ml': ['ai', 'ml', 'machine learning', 'data scien', 'deep learn'],
            'software': ['software', 'swe', 'developer', 'engineer'],
            'data': ['data engineer', 'data analyst', 'analytics', 'bi '],
            'product': ['product', 'pm', 'program manager'],
            'design': ['design', 'ux', 'ui', 'user experience'],
            'devops': ['devops', 'sre', 'platform', 'infrastructure', 'cloud']
        }
        
        for role_type, keywords in role_mappings.items():
            if any(kw in title_lower for kw in keywords):
                return role_type
                
        return None
    
    def rank_queries_by_expected_quality(
        self,
        queries: List[str],
        has_domain: bool,
        has_alumni: bool,
        career_stage: str
    ) -> List[Tuple[str, float]]:
        """
        Rank queries by expected result quality.
        
        Returns:
            List of (query, expected_quality_score) tuples
        """
        ranked = []
        
        for query in queries:
            score = 0.5  # Base score
            
            # Boost domain queries
            if has_domain and 'domain' in query:
                score += 0.3
                
            # Boost alumni queries for early career
            if has_alumni and career_stage == 'early_career':
                if any(term in query for term in ['university', 'college', 'school']):
                    score += 0.25
                    
            # Boost specific queries
            if '"' in query:  # Has exact matches
                score += 0.1
                
            # Boost queries with skills
            if any(term in query.lower() for term in ['python', 'java', 'react', 'ml', 'ai']):
                score += 0.15
                
            ranked.append((query, score))
        
        return sorted(ranked, key=lambda x: x[1], reverse=True)
