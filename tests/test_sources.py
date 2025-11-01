"""Test individual data sources"""

import pytest
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.apis.apollo_client import ApolloClient
from src.sources.company_pages import CompanyPagesScraper
from src.sources.github_profiles import GitHubScraper
from src.sources.crunchbase_client import CrunchbaseScraper
from src.sources.google_search import GoogleSearchScraper


class TestApolloClient:
    """Test Apollo.io API client"""
    
    def test_is_configured(self):
        client = ApolloClient()
        # Should work even without API key (will return False)
        assert isinstance(client.is_configured(), bool)
    
    @pytest.mark.skipif(not os.getenv("APOLLO_API_KEY"), reason="No API key")
    def test_search_people(self):
        client = ApolloClient()
        results = client.search_people("Meta", "Software Engineer")
        
        assert isinstance(results, list)
        if results:
            person = results[0]
            assert person.name
            assert person.company


class TestCompanyPagesScraper:
    """Test company website scraper"""
    
    def test_initialization(self):
        scraper = CompanyPagesScraper()
        assert scraper is not None
    
    def test_domain_guess(self):
        scraper = CompanyPagesScraper()
        # Test removed - _guess_domain method no longer exists
        # Method was removed when smart_domain_detector was cleaned up
        assert scraper is not None


class TestGitHubScraper:
    """Test GitHub scraper"""
    
    def test_initialization(self):
        scraper = GitHubScraper()
        assert scraper is not None
    
    def test_org_name_guess(self):
        scraper = GitHubScraper()
        orgs = scraper._guess_org_names("Meta Platforms")
        assert isinstance(orgs, list)
        assert len(orgs) > 0


class TestCrunchbaseScraper:
    """Test Crunchbase scraper"""
    
    def test_initialization(self):
        scraper = CrunchbaseScraper()
        assert scraper is not None


class TestGoogleSearchScraper:
    """Test Google SERP scraper"""
    
    def test_initialization(self):
        scraper = GoogleSearchScraper()
        assert scraper is not None
    
    def test_name_extraction(self):
        scraper = GoogleSearchScraper()
        
        # Test LinkedIn title format
        name = scraper._extract_name_from_title("John Doe - Software Engineer - Meta | LinkedIn")
        assert name == "John Doe"
        
        name = scraper._extract_name_from_title("Jane Smith | Professional Profile | LinkedIn")
        assert name == "Jane Smith"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

