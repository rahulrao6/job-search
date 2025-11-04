#!/usr/bin/env python3
"""Debug search issues with companies"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.actually_working_free_sources import ActuallyWorkingFreeSources
from src.utils.company_resolver import CompanyResolver
from src.models.job_context import JobContext

def test_company_match_scoring():
    """Test the company matching logic"""
    print("=== Testing Company Match Scoring ===\n")
    
    resolver = CompanyResolver()
    
    # Test cases with expected scores
    test_cases = [
        # (text, company, domain, min_expected_score)
        ("Software Engineer at Anyscale", "Anyscale", "anyscale.com", 0.3),
        ("Anyscale - Software Engineer", "Anyscale", None, 0.2),
        ("Engineer @ Anyscale", "Anyscale", None, 0.3),
        ("Working at Databricks as ML Engineer", "Databricks", None, 0.2),
        ("Ex-Anyscale engineer", "Anyscale", None, 0.0),  # Should reject
        ("Former Databricks employee", "Databricks", None, 0.0),  # Should reject
        ("Software Engineer | Meta", "Meta", None, 0.2),
        ("Google Software Engineer", "Google", None, 0.2),
    ]
    
    for text, company, domain, min_score in test_cases:
        score = resolver.calculate_company_match_score(text, company, domain)
        status = "✓" if score >= min_score else "✗"
        print(f"{status} '{text}'")
        print(f"   Company: {company}, Score: {score:.2f} (expected >= {min_score})")
        print()


def test_search_with_known_company():
    """Test with a well-known company that should have results"""
    print("\n=== Testing Search with Known Company ===\n")
    
    searcher = ActuallyWorkingFreeSources()
    if not searcher.is_configured():
        print("Search not configured")
        return
    
    # Test with Google (should definitely have results)
    print("Searching: Google - Software Engineer")
    results = searcher.search_people("Google", "Software Engineer")
    print(f"Found {len(results)} results")
    
    if results:
        print("\nTop 3 results:")
        for i, person in enumerate(results[:3]):
            print(f"{i+1}. {person.name}")
            print(f"   Title: {person.title}")
            print(f"   Company: {person.company}")
            print(f"   Score: {person.confidence_score:.2f}")
            print(f"   LinkedIn: {person.linkedin_url}")
    else:
        print("No results found - this indicates a problem!")


def test_search_with_obscure_company():
    """Test with obscure company"""
    print("\n\n=== Testing Search with Obscure Company ===\n")
    
    searcher = ActuallyWorkingFreeSources()
    if not searcher.is_configured():
        print("Search not configured")
        return
    
    # Create job context with domain
    job_context = JobContext(
        job_url="https://example.com",
        company="Anyscale",
        company_domain="anyscale.com",
        job_title="Software Engineer"
    )
    
    print("Searching: Anyscale - Software Engineer (with domain)")
    results = searcher.search_people(
        "Anyscale", 
        "Software Engineer",
        job_context=job_context
    )
    print(f"Found {len(results)} results")
    
    if results:
        print("\nTop 3 results:")
        for i, person in enumerate(results[:3]):
            print(f"{i+1}. {person.name}")
            print(f"   Title: {person.title}")
            print(f"   Company: {person.company}")
            print(f"   Score: {person.confidence_score:.2f}")
            

if __name__ == "__main__":
    test_company_match_scoring()
    test_search_with_known_company()
    test_search_with_obscure_company()
