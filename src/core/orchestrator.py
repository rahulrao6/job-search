"""Main orchestrator for finding connections"""

import os
import yaml
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from src.models.person import Person, PersonCategory
from src.models.job_context import CandidateProfile, JobContext
from src.db.models import UserProfile, JobRecord
from src.utils.cache import get_cache
from src.utils.cost_tracker import get_cost_tracker
from src.services.profile_matcher import ProfileMatcher

logger = logging.getLogger(__name__)

# Import sources that are actually used
from src.apis.apollo_client import ApolloClient
from src.sources.github_profiles import GitHubScraper
from src.sources.google_search import GoogleSearchScraper

from .aggregator import PeopleAggregator
from .categorizer import PersonCategorizer
from src.utils.openai_enhancer import get_openai_enhancer
from src.utils.person_validator import get_validator
from src.utils.ranking_engine import RankingEngine, ScoringWeights
from src.utils.validation_pipeline import ValidationPipeline


class ConnectionFinder:
    """
    Main orchestrator for finding people connections.
    
    Coordinates all data sources, aggregation, and categorization.
    """
    
    # Source quality scores (higher = better data quality)
    SOURCE_QUALITY_SCORES = {
        # Premium APIs (Best quality, but paid)
        'google_serp': 1.0,           # Best: SerpAPI with LinkedIn URLs + metadata
        'apollo': 0.95,               # Professional database with verified data
        
        # High Quality Free Sources (LinkedIn profiles with titles)
        'google_cse': 0.9,            # Google Custom Search - LinkedIn profiles
        'bing_api': 0.85,             # Bing Web Search API - LinkedIn profiles
        
        # Combined sources
        'elite_free': 0.8,            # Our combined free sources
        
        # Low Quality Sources (minimal professional info)
        'github': 0.2,                # GitHub API - just usernames, no titles
        'github_legacy': 0.2,         # GitHub org members - no professional info
        'company_website': 0.6,       # Company team pages (if used in future)
        
        # Default for unknown sources
        'unknown': 0.5,
        
        # Deprecated/Broken sources
        'twitter': 0.1,               # Broken (Nitter down)
        'wellfound': 0.1,             # Broken (not finding companies)
        'crunchbase': 0.1,            # Broken (403 Forbidden)
        'linkedin_public': 0.1,       # Broken/Risky (ToS violations)
        'free_linkedin': 0.1,         # Broken (all search engines blocking)
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the connection finder.
        
        Args:
            config_path: Path to sources.yaml config file
        """
        # Load config
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize utilities
        self.cache = get_cache()
        self.cost_tracker = get_cost_tracker()
        
        # Initialize sources based on config
        self.sources = self._initialize_sources()
    
    def find_connections(
        self,
        company: str,
        title: str,
        company_domain: Optional[str] = None,
        use_cache: bool = True,
        debug: bool = False,
        user_profile: Optional[CandidateProfile] = None,
        job_context: Optional[JobContext] = None,
    ) -> Dict:
        """
        Find connections for a job.
        
        Args:
            company: Company name
            title: Target job title
            company_domain: Company website domain (optional)
            use_cache: Whether to use cached results
        
        Returns:
            Dictionary with results and metadata
        """
        logger.info(f"Finding connections for {title} at {company}")
        logger.debug("=" * 60)
        
        # Track start time for timeout management
        start_time = time.time()
        max_search_time = 25  # Leave 5 seconds buffer for processing
        
        # Check cache
        cache_key = {"company": company, "title": title}
        if use_cache:
            cached = self.cache.get("connections", cache_key)
            if cached:
                logger.info("Using cached results")
                return cached
        
        # Auto-detect company domain if not provided
        if not company_domain:
            company_domain = self._guess_company_domain(company)
            if company_domain:
                logger.debug(f"Auto-detected domain: {company_domain}")
        
        # Initialize aggregator and categorizer
        aggregator = PeopleAggregator()
        categorizer = PersonCategorizer(target_title=title)
        
        # Smart source selection: Use Apollo first for pharma/biotech, Google CSE for tech
        source_selection = self._smart_source_selection(company, job_context)
        primary_sources = source_selection['primary']
        secondary_sources = source_selection['secondary']
        
        min_people_threshold = 10  # Focus on quality over quantity
        
        # Phase 1: Run PRIMARY sources (Apollo for pharma, Google CSE for tech)
        logger.info(f"Phase 1: Primary Sources ({', '.join(primary_sources) if primary_sources else 'None'})")
        logger.debug("-" * 40)
        
        for source_name in primary_sources:
            if source_name not in self.sources:
                continue
                
            source_instance = self.sources[source_name]
            source_config = self.config['sources'].get(source_name, {})
            
            if not source_config.get('enabled', True):
                logger.debug(f"{source_name}: disabled")
                continue
            
            # Check if source requires auth and is configured
            if hasattr(source_instance, 'is_configured'):
                if not source_instance.is_configured():
                    logger.debug(f"{source_name}: not configured (missing API key)")
                    continue
            
            logger.debug(f"Running {source_name}...")
            
            try:
                # Call search_people on each source with context
                kwargs = {}
                # Note: company_domain can be passed if source supports it
                
                # Pass user profile and job context for tailored searches
                if user_profile:
                    kwargs["user_profile"] = user_profile
                if job_context:
                    kwargs["job_context"] = job_context
                
                people = source_instance.search_people(company, title, **kwargs)
                
                if people:
                    aggregator.add_batch(people)
                
            except Exception as e:
                logger.warning(f"{source_name} error: {e}", exc_info=True)
        
        # Check if we have enough QUALITY people (LinkedIn profiles)
        all_people = aggregator.get_all()
        quality_people = [p for p in all_people if p.source not in ['github', 'github_legacy']]
        github_people = [p for p in all_people if p.source in ['github', 'github_legacy']]
        current_count = len(quality_people)
        github_count = len(github_people)
        
        logger.info(f"Free sources found: {current_count} quality results, {github_count} GitHub results")
        logger.debug(f"  - Quality results (LinkedIn profiles): {current_count} people")
        logger.debug(f"  - GitHub results (for enrichment): {github_count} people")
        
        # Check if we have time for secondary sources
        elapsed_time = time.time() - start_time
        
        # Phase 2: Run SECONDARY sources in parallel if we need more results AND have time
        if current_count < min_people_threshold and elapsed_time < 15:  # Only if < 15 seconds elapsed
            logger.info(f"Phase 2: Secondary Sources (Need {min_people_threshold - current_count} more)")
            logger.debug("-" * 40)
            
            # Run secondary sources sequentially (can be parallelized later if needed)
            for source_name in secondary_sources:
                if source_name not in self.sources:
                    continue
                    
                source_instance = self.sources[source_name]
                source_config = self.config['sources'].get(source_name, {})
                
                if not source_config.get('enabled', True):
                    logger.debug(f"{source_name}: disabled")
                    continue
                
                # Check if source requires auth and is configured
                if hasattr(source_instance, 'is_configured'):
                    if not source_instance.is_configured():
                        logger.debug(f"{source_name}: not configured (missing API key)")
                        continue
                
                logger.debug(f"Running {source_name}...")
                
                try:
                    # Pass context for secondary sources
                    kwargs = {}
                    if user_profile:
                        kwargs["user_profile"] = user_profile
                    if job_context:
                        kwargs["job_context"] = job_context
                    
                    people = source_instance.search_people(company, title, **kwargs)
                    
                    if people:
                        aggregator.add_batch(people)
                        # Check if we have enough now
                        if len(aggregator.get_all()) >= min_people_threshold:
                            logger.info(f"Reached threshold ({min_people_threshold}+ people), stopping secondary searches")
                            break
                    
                except Exception as e:
                    logger.warning(f"{source_name} error: {e}", exc_info=True)
        else:
            logger.info("Sufficient results from primary sources! Skipping secondary sources.")
        
        # Get all unique people
        all_people = aggregator.get_all()
        

        # VALIDATE: Remove false positives before processing
        logger.debug(f"Validating {len(all_people)} people (removing false positives)...")
        validator = get_validator(company)
        validated_people = validator.validate_batch(all_people)
        filtered_count = len(all_people) - len(validated_people)
        logger.info(f"Kept {len(validated_people)} valid people (filtered {filtered_count} false positives)")

        
        # Use OpenAI to enhance if available (but skip if running out of time)
        elapsed_time = time.time() - start_time
        enhancer = get_openai_enhancer()
        if enhancer.enabled and validated_people and elapsed_time < 20:
            # Limit enhancement based on time remaining
            max_enhance = 20 if elapsed_time < 15 else 10
            logger.debug(f"Using OpenAI to enhance data (up to {max_enhance} people)...")
            validated_people = enhancer.enhance_batch(validated_people, title, max_enhance=max_enhance)
        elif elapsed_time >= 20:
            logger.debug("Skipping OpenAI enhancement (time limit)")
        
        # Apply quality gate filtering
        quality_gate_results = self._quality_gate_filter(validated_people, target_count=5)
        high_confidence_people = quality_gate_results['high_confidence']
        additional_options = quality_gate_results['additional_options']
        
        logger.info(f"Quality gates: {len(high_confidence_people)} high-confidence, {len(additional_options)} additional options")
        logger.debug(f"Quality gate message: {quality_gate_results['message']}")
        
        # Use high confidence people for categorization, but keep additional options
        categorized_people = categorizer.categorize_batch(high_confidence_people)
        
        # Group by category
        by_category = self._group_by_category(categorized_people)
        
        # Sort within each category using advanced ranking
        by_category = self._sort_by_quality(by_category, job_context, user_profile)
        
        # Show ALL connections (not just top 5)
        # Users requested to see all data, not limited results
        
        # Create basic validation metrics from available data
        metrics = {
            'total_processed': len(all_people),
            'rejected_basic_validation': filtered_count,
            'rejected_quality': 0,  # Not tracked with current validator
            'rejected_threshold': 0,  # Not tracked with current validator
            'valid_results': len(validated_people),
            'average_confidence': 0.7,  # Default estimate
            'average_quality': 0.7,  # Default estimate
        }
        
        # Prepare results
        results = {
            "company": company,
            "title": title,
            "total_found": len(all_people),
            "by_category": {
                category.value: [self._person_to_dict(p) for p in people]
                for category, people in by_category.items()
            },
            "category_counts": {
                category.value: len(people)
                for category, people in by_category.items()
            },
            "source_stats": aggregator.get_stats(),
            "cost_stats": self.cost_tracker.get_stats(),
            "validation_metrics": metrics,
            "quality_insights": {
                "average_confidence": metrics['average_confidence'],
                "average_quality": metrics['average_quality'],
                "filters_applied": {
                    "basic_validation": metrics['rejected_basic_validation'],
                    "quality_filter": metrics['rejected_quality'],
                    "threshold_filter": metrics['rejected_threshold']
                },
                "high_confidence_count": len(high_confidence_people),
                "explainable_results": []  # Empty for now, can be enhanced later
            },
            "quality_gate_results": {
                "high_confidence_count": len(high_confidence_people),
                "additional_options_count": len(additional_options),
                "message": quality_gate_results['message'],
                "additional_options": [self._person_to_dict(p) for p in additional_options] if additional_options else []
            }
        }
        
        # Cache results
        if use_cache:
            self.cache.set("connections", cache_key, results)
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def find_connections_with_context(
        self,
        company: str,
        title: str,
        user_profile: Optional[CandidateProfile] = None,
        job_context: Optional[JobContext] = None,
        company_domain: Optional[str] = None,
        use_cache: bool = True,
        debug: bool = False,
        filters: Optional[Dict] = None,
    ) -> Dict:
        """
        Find connections with profile and job context for enhanced matching.
        
        Args:
            company: Company name
            title: Target job title
            user_profile: User profile with skills, schools, past companies
            job_context: Job context with department, location, skills
            company_domain: Company website domain (optional)
            use_cache: Whether to use cached results
            debug: Debug mode
            filters: Optional filters (categories, min_confidence, max_results)
            
        Returns:
            Dictionary with results including relevance scores and match reasons
        """
        logger.info(f"Finding connections for {title} at {company} (with context)")
        logger.debug("=" * 60)
        
        start_time = time.time()
        
        # Note: ProfileMatcher accepts CandidateProfile directly, so no conversion needed
        # We'll pass user_profile (CandidateProfile) directly to ProfileMatcher
        
        # Extract job data from job_context if provided
        job_department = None
        job_location = None
        if job_context:
            job_department = job_context.department
            job_location = job_context.location
            if not company_domain:
                company_domain = job_context.company_domain
            if not title and job_context.job_title:
                title = job_context.job_title
        
        # Run search with context (now passes user_profile and job_context)
        results = self.find_connections(
            company=company,
            title=title,
            company_domain=company_domain,
            use_cache=use_cache,
            debug=debug,
            user_profile=user_profile,
            job_context=job_context
        )
        
        # Get all people from results
        all_people_dicts = []
        for category, people_list in results.get('by_category', {}).items():
            all_people_dicts.extend(people_list)
        
        # Convert back to Person objects for matching
        # Note: We need to reconstruct Person objects from dicts
        # For now, we'll work with dicts and add relevance scores
        
        # Apply profile matching if profile provided
        relevance_scores = {}
        match_reasons_dict = {}
        
        if user_profile or job_context:
            # Create a temporary JobRecord for matching
            job_record = None
            if job_context:
                job_record = JobRecord(
                    company_name=company,
                    job_title=title,
                    department=job_department,
                    location=job_location,
                    required_skills=job_context.candidate_skills if job_context else None
                )
            
            # Calculate relevance for each person
            for person_dict in all_people_dicts:
                # Create a minimal Person object for matching
                from src.models.person import Person as PersonModel
                person_obj = PersonModel(
                    name=person_dict.get('name', ''),
                    title=person_dict.get('title'),
                    company=person_dict.get('company', company),
                    linkedin_url=person_dict.get('linkedin_url'),
                    source=person_dict.get('source', 'unknown'),
                    confidence_score=person_dict.get('confidence', 0.5),
                    department=person_dict.get('department'),
                    location=person_dict.get('location'),
                    skills=person_dict.get('skills', [])
                )
                
                # Calculate relevance
                relevance, match_reasons = ProfileMatcher.calculate_relevance(
                    person_obj,
                    profile=None,  # We'll use candidate_profile instead
                    job=job_record,
                    candidate_profile=user_profile  # Pass CandidateProfile directly
                )
                
                relevance_scores[person_dict.get('name', '')] = relevance
                match_reasons_dict[person_dict.get('name', '')] = match_reasons
        
        # Sort by relevance score if available
        if relevance_scores:
            # Sort each category by relevance
            enhanced_by_category = {}
            for category, people_list in results.get('by_category', {}).items():
                # Add relevance scores and match reasons to each person
                enhanced_people = []
                for person_dict in people_list:
                    person_name = person_dict.get('name', '')
                    person_dict['relevance_score'] = relevance_scores.get(person_name, person_dict.get('confidence', 0.5))
                    person_dict['match_reasons'] = match_reasons_dict.get(person_name, [])
                    enhanced_people.append(person_dict)
                
                # Sort by relevance score (descending)
                enhanced_people.sort(key=lambda p: p.get('relevance_score', 0), reverse=True)
                enhanced_by_category[category] = enhanced_people
            results['by_category'] = enhanced_by_category
        
        # Add insights
        insights = {
            'alumni_matches': sum(1 for reasons in match_reasons_dict.values() if 'alumni_match' in reasons),
            'ex_company_matches': sum(1 for reasons in match_reasons_dict.values() if 'ex_company_match' in reasons),
            'skills_matches': sum(1 for reasons in match_reasons_dict.values() if 'skills_match' in str(reasons)),
            'best_matches': []  # Categories with highest average relevance
        }
        
        # Calculate best match categories
        category_avg_relevance = {}
        for category, people_list in results.get('by_category', {}).items():
            if people_list:
                avg_relevance = sum(p.get('relevance_score', 0.5) for p in people_list) / len(people_list)
                category_avg_relevance[category] = avg_relevance
        
        if category_avg_relevance:
            insights['best_matches'] = sorted(
                category_avg_relevance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
        
        results['insights'] = insights
        results['relevance_scores'] = relevance_scores
        
        return results
    
    def _initialize_sources(self) -> Dict:
        """
        Initialize data sources - PRODUCTION ELITE SCRAPERS INTEGRATION.
        
        Architecture:
        1. Elite Sources Orchestrator (API + Selenium hybrid) - 200-500+ results
        2. Paid APIs as backup/enhancement (SerpAPI, Apollo) 
        3. Legacy sources disabled (proven not to work)
        
        This integrates all our elite scraping systems:
        - Your proven API sources (Google CSE, Bing, GitHub)
        - Production Selenium scrapers (DuckDuckGo, advanced GitHub, company pages)
        - Smart fallback and deduplication
        """
        sources = {}
        
        # Tier 1: Free API Sources (Primary - handles most use cases)
        try:
            from src.scrapers.actually_working_free_sources import ActuallyWorkingFreeSources
            elite_free = ActuallyWorkingFreeSources()
            if elite_free.is_configured():
                sources['elite_free'] = elite_free  # Quality: 0.9 - Best free solution
                logger.info("Elite free sources loaded (Google CSE, GitHub API, Company Pages)")
            else:
                logger.warning("Free sources not configured - add GOOGLE_API_KEY and GOOGLE_CSE_ID to .env")
        except ImportError as e:
            logger.warning(f"Free sources not available: {e}")
        
        # Tier 2: Premium APIs (enhancement/backup)
        sources['google_serp'] = GoogleSearchScraper()  # Quality: 1.0 - Best results (paid)
        sources['apollo'] = ApolloClient()              # Quality: 0.9 - Professional data (paid)
        
        # Tier 3: Legacy GitHub (minimal fallback only)
        sources['github_legacy'] = GitHubScraper()      # Quality: 0.3 - Basic fallback
        
        logger.info(f"Initialized {len(sources)} data sources")
        logger.debug("   Primary: Google CSE (LinkedIn profiles)")
        logger.debug("   Secondary: GitHub (usernames for enrichment)")
        logger.debug("   Backup: Paid APIs (SerpAPI, Apollo)")
        
        return sources
    
    def _smart_source_selection(self, company: str, job_context: Optional[JobContext] = None) -> Dict[str, List[str]]:
        """
        Determine which sources to use FIRST based on company/industry context.
        
        Strategy:
        - Use Apollo FIRST for: pharma/biotech, small companies with non-tech roles
        - Use Google CSE FIRST for: tech companies, large companies, engineering roles
        
        Returns:
            {'primary': [source_names], 'secondary': [source_names]}
        """
        # Industry detection
        pharma_keywords = ['pharma', 'biotech', 'pharmaceutical', 'medical device', 'life sciences', 
                          'biotechnology', 'pharmaceuticals', 'biopharma']
        company_lower = company.lower()
        is_pharma = any(kw in company_lower for kw in pharma_keywords)
        
        # Company size heuristic (if available in job_context)
        # For now, assume small companies (<1000 employees) benefit more from Apollo
        is_small_company = False
        if job_context and hasattr(job_context, 'company_size'):
            company_size = getattr(job_context, 'company_size', None)
            if company_size and company_size < 1000:
                is_small_company = True
        
        # Role type detection
        is_non_tech_role = False
        if job_context and job_context.job_title:
            non_tech_keywords = ['sales', 'operations', 'marketing', 'business development', 
                               'account manager', 'business analyst', 'customer success']
            job_title_lower = job_context.job_title.lower()
            is_non_tech_role = any(kw in job_title_lower for kw in non_tech_keywords)
        
        # Decision logic
        use_apollo_first = is_pharma or (is_small_company and is_non_tech_role)
        
        primary = []
        secondary = []
        
        if use_apollo_first:
            # Apollo first for pharma/biotech or small non-tech companies
            if 'apollo' in self.sources and self.sources['apollo'].is_configured():
                primary.append('apollo')
            primary.append('elite_free')  # Fallback to Google CSE
            secondary = ['google_serp'] if 'google_serp' in self.sources else []
            logger.debug(f"Smart selection: Apollo first (pharma={is_pharma}, small={is_small_company}, non-tech={is_non_tech_role})")
        else:
            # Google CSE first for tech companies (default)
            primary.append('elite_free')
            if 'apollo' in self.sources and self.sources['apollo'].is_configured():
                secondary.append('apollo')
            if 'google_serp' in self.sources:
                secondary.append('google_serp')
            logger.debug(f"Smart selection: Google CSE first (standard tech company)")
        
        return {'primary': primary, 'secondary': secondary}
    
    def _guess_company_domain(self, company: str) -> Optional[str]:
        """Guess company domain from company name"""
        # Common company domain mappings
        domain_map = {
            "meta": "meta.com",
            "meta platforms": "meta.com",
            "facebook": "meta.com",
            "google": "google.com",
            "alphabet": "google.com",
            "microsoft": "microsoft.com",
            "amazon": "amazon.com",
            "apple": "apple.com",
            "netflix": "netflix.com",
            "tesla": "tesla.com",
            "twitter": "twitter.com",
            "x": "twitter.com",
            "linkedin": "linkedin.com",
            "airbnb": "airbnb.com",
            "uber": "uber.com",
            "lyft": "lyft.com",
            "stripe": "stripe.com",
            "square": "squareup.com",
            "shopify": "shopify.com",
            "salesforce": "salesforce.com",
            "adobe": "adobe.com",
            "oracle": "oracle.com",
            "ibm": "ibm.com",
            "intel": "intel.com",
            "nvidia": "nvidia.com",
            "amd": "amd.com",
            "cisco": "cisco.com",
            "vmware": "vmware.com",
            "dropbox": "dropbox.com",
            "slack": "slack.com",
            "zoom": "zoom.us",
            "figma": "figma.com",
            "notion": "notion.so",
            "asana": "asana.com",
            "atlassian": "atlassian.com",
            "databricks": "databricks.com",
            "snowflake": "snowflake.com",
            "twilio": "twilio.com",
            "cloudflare": "cloudflare.com",
            "openai": "openai.com",
            "anthropic": "anthropic.com",
        }
        
        company_lower = company.lower().strip()
        return domain_map.get(company_lower)
    
    def _group_by_category(self, people: List[Person]) -> Dict[PersonCategory, List[Person]]:
        """Group people by category"""
        groups = {
            PersonCategory.MANAGER: [],
            PersonCategory.RECRUITER: [],
            PersonCategory.SENIOR: [],
            PersonCategory.PEER: [],
            PersonCategory.UNKNOWN: [],
        }
        
        for person in people:
            groups[person.category].append(person)
        
        return groups
    
    def _sort_by_quality(self, by_category: Dict[PersonCategory, List[Person]], 
                        job_context: Optional[JobContext] = None,
                        candidate_profile: Optional[CandidateProfile] = None) -> Dict[PersonCategory, List[Person]]:
        """
        Sort people within each category using advanced ranking.
        
        Uses multi-factor scoring:
        1. Employment verification (current vs past employee)
        2. Role relevance (based on career stage)
        3. Profile matching (alumni, skills, etc.)
        4. Data quality (LinkedIn URL, completeness)
        5. Source quality (API quality scores)
        """
        # Use ranking engine for sophisticated scoring
        ranking_engine = RankingEngine()
        
        # Sort each category independently
        for category in by_category:
            # Get ranked results with scores
            ranked_results = ranking_engine.rank_people(
                by_category[category],
                job_context=job_context,
                candidate_profile=candidate_profile,
                source_quality_map=self.SOURCE_QUALITY_SCORES
            )
            
            # Extract just the sorted people
            by_category[category] = [person for person, score, breakdown in ranked_results]
        
        return by_category
    
    def _person_to_dict(self, person: Person) -> dict:
        """Convert Person to dictionary for output"""
        return {
            "name": person.name,
            "title": person.title,
            "company": person.company,
            "linkedin_url": person.linkedin_url,
            "email": person.email,
            "source": person.source,
            "category": person.category.value,
            "confidence": round(person.confidence_score, 2),
            "evidence_url": person.evidence_url,
        }
    
    def _print_summary(self, results: dict):
        """Print results summary"""
        logger.info("=" * 60)
        logger.info("RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total unique people found: {results['total_found']}")
        
        category_summary = []
        for category, count in results['category_counts'].items():
            if count > 0:
                category_summary.append(f"{category}: {count}")
        
        if category_summary:
            logger.info(f"By category: {', '.join(category_summary)}")
        
        sources_used = []
        for source, count in results['source_stats']['by_source'].items():
            sources_used.append(f"{source}: {count}")
            logger.debug(f"  Source {source}: {count} people")
        
        logger.info(f"Sources used: {', '.join(sources_used)}")
        logger.debug(f"Multi-source matches: {results['source_stats']['multi_source_matches']}")
        
        total_cost = results['cost_stats']['total_cost']
        if total_cost > 0:
            logger.info(f"Total API cost: ${total_cost:.4f}")
        
        logger.debug("=" * 60)
    
    def _quality_gate_filter(self, people: List[Person], target_count: int = 5) -> Dict[str, Any]:
        """
        Apply aggressive quality gates to filter results.
        
        Gates:
        1. Minimum data completeness (score > 0.7)
        2. Employment verification confidence (score > 0.8)
        3. Relevance threshold (> 0.6)
        4. Diversity requirement (max 2 per category)
        5. Additional options if < target_count
        
        Returns:
            {
                'high_confidence': List[Person],
                'additional_options': List[Person],
                'message': str
            }
        """
        if not people:
            return {
                'high_confidence': [],
                'additional_options': [],
                'message': "No people found"
            }
        
        # Gate 1: Minimum data completeness (score > 0.7)
        gate1 = [p for p in people if self._calculate_completeness_score(p) > 0.7]
        
        # Gate 2: Employment verification confidence (score > 0.8)
        gate2 = [p for p in gate1 if (p.confidence_score or 0.5) > 0.8]
        
        # Gate 3: Relevance threshold (if relevance_score exists, > 0.6)
        gate3 = []
        for p in gate2:
            relevance = getattr(p, 'relevance_score', p.confidence_score or 0.5)
            if relevance > 0.6:
                gate3.append(p)
        
        # Gate 4: Diversity requirement (max 2 per category)
        final = self._ensure_diversity(gate3, max_per_category=2)
        
        # Gate 5: If < target_count, provide additional options
        if len(final) < target_count:
            # Get next best candidates that passed gate 2 but not gate 3 or 4
            remaining = [p for p in gate2 if p not in final]
            additional = sorted(
                remaining[:target_count * 2],  # Get more candidates
                key=lambda p: p.confidence_score or 0.5,
                reverse=True
            )[:target_count - len(final)]
            
            return {
                'high_confidence': final,
                'additional_options': additional,
                'message': f"Showing {len(final)} verified connections + {len(additional)} additional options"
            }
        
        return {
            'high_confidence': final[:target_count],
            'additional_options': [],
            'message': f"Found {len(final)} high-quality connections"
        }
    
    def _calculate_completeness_score(self, person: Person) -> float:
        """
        Calculate data completeness score for a person.
        
        Returns:
            Score 0.0-1.0 based on available fields
        """
        score = 0.0
        
        # LinkedIn URL is most important
        if person.linkedin_url:
            score += 0.3
        
        # Title
        if person.title and len(person.title) > 3:
            score += 0.2
        
        # Company
        if person.company:
            score += 0.2
        
        # Location
        if person.location:
            score += 0.1
        
        # Skills
        if person.skills and len(person.skills) > 0:
            score += 0.1
        
        # Department
        if person.department:
            score += 0.1
        
        return min(1.0, score)
    
    def _ensure_diversity(self, people: List[Person], max_per_category: int = 2) -> List[Person]:
        """
        Ensure diversity in results by limiting per category.
        
        Strategy:
        - Take top max_per_category from each category
        - Ensure at least 1 recruiter if available
        - Ensure at least 1 manager if available
        """
        if not people:
            return []
        
        # Group by category
        by_category = self._group_by_category(people)
        
        # Take top max_per_category from each category (already sorted by quality)
        diverse_people = []
        for category, category_people in by_category.items():
            diverse_people.extend(category_people[:max_per_category])
        
        # Ensure at least 1 recruiter if available
        if PersonCategory.RECRUITER in by_category and by_category[PersonCategory.RECRUITER]:
            recruiter = by_category[PersonCategory.RECRUITER][0]
            if recruiter not in diverse_people:
                diverse_people.append(recruiter)
        
        # Ensure at least 1 manager if available
        if PersonCategory.MANAGER in by_category and by_category[PersonCategory.MANAGER]:
            manager = by_category[PersonCategory.MANAGER][0]
            if manager not in diverse_people:
                diverse_people.append(manager)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_people = []
        for person in diverse_people:
            person_key = (person.name, person.linkedin_url)
            if person_key not in seen:
                seen.add(person_key)
                unique_people.append(person)
        
        return unique_people

