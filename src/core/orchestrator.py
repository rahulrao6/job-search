"""Main orchestrator for finding connections"""

import os
import yaml
import time
from pathlib import Path
from typing import List, Dict, Optional
from src.models.person import Person, PersonCategory
from src.models.job_context import CandidateProfile, JobContext
from src.db.models import UserProfile, JobRecord
from src.utils.cache import get_cache
from src.utils.cost_tracker import get_cost_tracker
from src.services.profile_matcher import ProfileMatcher

# Import all sources
from src.apis.apollo_client import ApolloClient
from src.sources.company_pages import CompanyPagesScraper
from src.sources.github_profiles import GitHubScraper
from src.sources.crunchbase_client import CrunchbaseScraper
from src.sources.google_search import GoogleSearchScraper
from src.sources.linkedin_public import LinkedInPublicScraper
from src.sources.twitter_search import TwitterSearchScraper
from src.sources.wellfound_scraper import WellfoundScraper

from .aggregator import PeopleAggregator
from .categorizer import PersonCategorizer
from src.utils.openai_enhancer import get_openai_enhancer
from src.utils.person_validator import get_validator


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
        'company_pages': 0.6,         # Direct company website scraping
        'company_website': 0.6,       # Company team pages
        
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
        print(f"\n🔍 Finding connections for {title} at {company}...")
        print("=" * 60)
        
        # Track start time for timeout management
        start_time = time.time()
        max_search_time = 25  # Leave 5 seconds buffer for processing
        
        # Check cache
        cache_key = {"company": company, "title": title}
        if use_cache:
            cached = self.cache.get("connections", cache_key)
            if cached:
                print("✓ Using cached results")
                return cached
        
        # Auto-detect company domain if not provided
        if not company_domain:
            company_domain = self._guess_company_domain(company)
            if company_domain:
                print(f"ℹ️  Auto-detected domain: {company_domain}")
        
        # Initialize aggregator and categorizer
        aggregator = PeopleAggregator()
        categorizer = PersonCategorizer(target_title=title)
        
        # Waterfall approach: Quality sources first
        free_sources = ['elite_free']  # Only quality free sources (Google CSE, etc.)
        paid_sources = ['google_serp', 'apollo']
        min_people_threshold = 10  # Focus on quality over quantity
        
        # Phase 1: Run FREE sources first
        print("\n🆓 Phase 1: Free Sources (Cost: $0)")
        print("-" * 40)
        
        for source_name in free_sources:
            if source_name not in self.sources:
                continue
                
            source_instance = self.sources[source_name]
            source_config = self.config['sources'].get(source_name, {})
            
            if not source_config.get('enabled', True):
                print(f"⊘ {source_name}: disabled")
                continue
            
            # Check if source requires auth and is configured
            if hasattr(source_instance, 'is_configured'):
                if not source_instance.is_configured():
                    print(f"⊘ {source_name}: not configured (missing API key)")
                    continue
            
            print(f"\n▶ Running {source_name}...")
            
            try:
                # Call search_people on each source with context
                kwargs = {}
                if company_domain and source_name == "company_pages":
                    kwargs["company_domain"] = company_domain
                
                # Pass user profile and job context for tailored searches
                if user_profile:
                    kwargs["user_profile"] = user_profile
                if job_context:
                    kwargs["job_context"] = job_context
                
                people = source_instance.search_people(company, title, **kwargs)
                
                if people:
                    aggregator.add_batch(people)
                
            except Exception as e:
                print(f"⚠️  {source_name} error: {e}")
        
        # Check if we have enough QUALITY people (LinkedIn profiles)
        all_people = aggregator.get_all()
        quality_people = [p for p in all_people if p.source not in ['github', 'github_legacy']]
        github_people = [p for p in all_people if p.source in ['github', 'github_legacy']]
        current_count = len(quality_people)
        github_count = len(github_people)
        
        print(f"\n📊 Free sources found:")
        print(f"  - Quality results (LinkedIn profiles): {current_count} people")
        print(f"  - GitHub results (for enrichment): {github_count} people")
        
        # Check if we have time for paid sources
        elapsed_time = time.time() - start_time
        
        # Phase 2: Only use paid sources if we need more results AND have time
        if current_count < min_people_threshold and elapsed_time < 15:  # Only if < 15 seconds elapsed
            print(f"\n💳 Phase 2: Premium Sources (Need {min_people_threshold - current_count} more)")
            print("-" * 40)
            
            for source_name in paid_sources:
                if source_name not in self.sources:
                    continue
                    
                source_instance = self.sources[source_name]
                source_config = self.config['sources'].get(source_name, {})
                
                if not source_config.get('enabled', True):
                    print(f"⊘ {source_name}: disabled")
                    continue
                
                # Check if source requires auth and is configured
                if hasattr(source_instance, 'is_configured'):
                    if not source_instance.is_configured():
                        print(f"⊘ {source_name}: not configured (missing API key)")
                        continue
                
                print(f"\n▶ Running {source_name}...")
                
                try:
                    # Pass context for paid sources too
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
                            print(f"✓ Reached threshold ({min_people_threshold}+ people), stopping paid searches")
                            break
                    
                except Exception as e:
                    print(f"⚠️  {source_name} error: {e}")
        else:
            print(f"✅ Sufficient results from free sources! Skipping paid APIs.")
        
        # Get all unique people
        all_people = aggregator.get_all()
        
        # VALIDATE: Remove false positives before processing
        print(f"\n▶ Validating {len(all_people)} people (removing false positives)...")
        validator = get_validator(company)
        validated_people = validator.validate_batch(all_people)
        print(f"✓ Kept {len(validated_people)} valid people (filtered {len(all_people) - len(validated_people)} false positives)")
        
        # Use OpenAI to enhance if available (but skip if running out of time)
        elapsed_time = time.time() - start_time
        enhancer = get_openai_enhancer()
        if enhancer.enabled and validated_people and elapsed_time < 20:
            # Limit enhancement based on time remaining
            max_enhance = 20 if elapsed_time < 15 else 10
            print(f"\n▶ Using OpenAI to enhance data (up to {max_enhance} people)...")
            validated_people = enhancer.enhance_batch(validated_people, title, max_enhance=max_enhance)
        elif elapsed_time >= 20:
            print(f"\n⏱️ Skipping OpenAI enhancement (time limit)")
        
        # Categorize people
        categorized_people = categorizer.categorize_batch(validated_people)
        
        # Group by category
        by_category = self._group_by_category(categorized_people)
        
        # Sort within each category by source quality, then confidence
        by_category = self._sort_by_quality(by_category)
        
        # Show ALL connections (not just top 5)
        # Users requested to see all data, not limited results
        
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
        print(f"\n🔍 Finding connections for {title} at {company} (with context)...")
        print("=" * 60)
        
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
                print("🚀 Elite free sources loaded (Google CSE, GitHub API, Company Pages)")
            else:
                print("⚠️  Free sources not configured - add GOOGLE_API_KEY and GOOGLE_CSE_ID to .env")
        except ImportError as e:
            print(f"⚠️  Free sources not available: {e}")
        
        # Tier 2: Premium APIs (enhancement/backup)
        sources['google_serp'] = GoogleSearchScraper()  # Quality: 1.0 - Best results (paid)
        sources['apollo'] = ApolloClient()              # Quality: 0.9 - Professional data (paid)
        
        # Tier 3: Legacy GitHub (minimal fallback only)
        sources['github_legacy'] = GitHubScraper()      # Quality: 0.3 - Basic fallback
        
        print(f"📊 Initialized {len(sources)} data sources")
        print("   Primary: Google CSE (LinkedIn profiles)")
        print("   Secondary: GitHub (usernames for enrichment)")
        print("   Backup: Paid APIs (SerpAPI, Apollo)")
        
        return sources
    
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
    
    def _sort_by_quality(self, by_category: Dict[PersonCategory, List[Person]]) -> Dict[PersonCategory, List[Person]]:
        """
        Sort people within each category by quality:
        1. Source quality (SerpAPI > Apollo > GitHub)
        2. Confidence score
        
        This ensures high-quality results (with LinkedIn URLs, metadata) appear first,
        and low-quality results (GitHub with minimal data) appear last.
        """
        for category in by_category:
            by_category[category] = sorted(
                by_category[category],
                key=lambda p: (
                    self.SOURCE_QUALITY_SCORES.get(p.source, 0.5),  # Primary: source quality
                    p.confidence_score  # Secondary: confidence
                ),
                reverse=True
            )
        
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
        print("\n" + "=" * 60)
        print(f"📊 RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total unique people found: {results['total_found']}")
        print(f"\nBy category:")
        
        for category, count in results['category_counts'].items():
            if count > 0:
                emoji = {
                    'manager': '👔',
                    'recruiter': '🎯',
                    'senior': '⭐',
                    'peer': '👥',
                    'unknown': '❓',
                }.get(category, '•')
                print(f"  {emoji} {category.capitalize()}: {count}")
        
        print(f"\nSources used:")
        for source, count in results['source_stats']['by_source'].items():
            print(f"  • {source}: {count} people")
        
        print(f"\nMulti-source matches (high confidence): {results['source_stats']['multi_source_matches']}")
        
        total_cost = results['cost_stats']['total_cost']
        if total_cost > 0:
            print(f"\n💰 Total API cost: ${total_cost:.4f}")
        
        print("\n" + "=" * 60)

