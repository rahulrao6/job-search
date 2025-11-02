"""Main orchestrator for finding connections"""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from src.models.person import Person, PersonCategory
from src.utils.cache import get_cache
from src.utils.cost_tracker import get_cost_tracker

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
    
    # Source quality scores (higher = better data quality) - UPDATED FOR ELITE SOURCES
    SOURCE_QUALITY_SCORES = {
        # Elite Sources (Primary)
        'elite_orchestrator': 0.9,    # Best free solution: API + Selenium hybrid
        'google_cse': 0.85,           # Google Custom Search via elite orchestrator
        'bing_api': 0.8,              # Bing Web Search via elite orchestrator
        'duckduckgo_selenium': 0.75,  # DuckDuckGo via production Selenium
        'github_api': 0.7,            # Enhanced GitHub API via elite orchestrator
        'company_selenium': 0.65,     # Company pages via production Selenium
        'startpage_selenium': 0.7,    # Startpage via production Selenium
        
        # Premium APIs (Backup)
        'google_serp': 1.0,           # Best: SerpAPI with LinkedIn URLs + metadata
        'serpapi': 1.0,               # SerpAPI variant
        'apollo': 0.9,                # Good: Professional database
        
        # Legacy Sources (Fallback only)
        'github_legacy': 0.3,         # Basic GitHub (minimal metadata)
        'github': 0.3,                # Legacy GitHub scraper
        
        # Deprecated/Disabled Sources
        'company_pages': 0.2,         # Old company scraper (mostly broken)
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
        
        # Run each enabled source
        for source_name, source_instance in self.sources.items():
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
                # Call search_people on each source
                kwargs = {}
                if company_domain and source_name == "company_pages":
                    kwargs["company_domain"] = company_domain
                
                people = source_instance.search_people(company, title, **kwargs)
                
                if people:
                    aggregator.add_batch(people)
                
            except Exception as e:
                print(f"⚠️  {source_name} error: {e}")
        
        # Get all unique people
        all_people = aggregator.get_all()
        
        # VALIDATE: Remove false positives before processing
        print(f"\n▶ Validating {len(all_people)} people (removing false positives)...")
        validator = get_validator(company)
        validated_people = validator.validate_batch(all_people)
        print(f"✓ Kept {len(validated_people)} valid people (filtered {len(all_people) - len(validated_people)} false positives)")
        
        # Use OpenAI to enhance if available (increased limit for production)
        enhancer = get_openai_enhancer()
        if enhancer.enabled and validated_people:
            print(f"\n▶ Using OpenAI to enhance data (up to 50 people)...")
            # Enhance more people in production for better categorization
            validated_people = enhancer.enhance_batch(validated_people, title, max_enhance=50)
        
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
        
        # Tier 1: ELITE SOURCES ORCHESTRATOR (Primary - handles 80%+ of use cases)
        try:
            from src.scrapers.elite_sources_integration import EliteSourcesAdapter
            sources['elite_orchestrator'] = EliteSourcesAdapter()  # Quality: 0.9 - Best free solution
            print("🚀 Elite Sources Orchestrator loaded - expect 200-500+ results per search")
        except ImportError as e:
            print(f"⚠️  Elite orchestrator not available: {e}")
            # Fallback to basic API sources
            from src.scrapers.actually_working_free_sources import ActuallyWorkingFreeSources
            sources['elite_free'] = ActuallyWorkingFreeSources()
        
        # Tier 2: Premium APIs (enhancement/backup)
        sources['google_serp'] = GoogleSearchScraper()  # Quality: 1.0 - Best results (paid)
        sources['apollo'] = ApolloClient()              # Quality: 0.9 - Professional data (paid)
        
        # Tier 3: Legacy GitHub (minimal fallback only)
        sources['github_legacy'] = GitHubScraper()      # Quality: 0.3 - Basic fallback
        
        print(f"📊 Initialized {len(sources)} data sources")
        print("   Primary: Elite Sources Orchestrator (API + Selenium)")
        print("   Backup: Paid APIs (SerpAPI, Apollo)")
        print("   Fallback: Legacy GitHub")
        
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

