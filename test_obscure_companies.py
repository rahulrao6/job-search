#!/usr/bin/env python3
"""
Test the improved search system with obscure companies.

Tests various edge cases without affecting the live API.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.extractors.job_parser import JobParser
from src.utils.company_resolver import CompanyResolver
from src.scrapers.actually_working_free_sources import ActuallyWorkingFreeSources
from src.models.job_context import JobContext

# Load environment variables
load_dotenv()


def test_company_extraction():
    """Test extraction from various job boards with obscure companies"""
    print("\n=== Testing Company Extraction ===")
    
    parser = JobParser(use_ai=False)  # Test without AI first
    
    test_urls = [
        # Obscure startups
        ("https://jobs.lever.co/replicant", "Replicant"),
        ("https://boards.greenhouse.io/voltrondata/jobs/4372531005", "Voltron Data"),
        ("https://wellfound.com/company/moonhub/jobs", "Moonhub"),
        ("https://jobs.ashbyhq.com/Anyscale", "Anyscale"),
        
        # Direct company pages
        ("https://careers.databricks.com/job/123", "Databricks"),
        ("https://jobs.netflix.com/jobs/456", "Netflix"),
        
        # Ambiguous names
        ("https://builtin.com/job/ai-engineer/root-company", "Root"),
        ("https://boards.greenhouse.io/nova", "Nova"),
        
        # International/Non-English
        ("https://jobs.lever.co/klarna", "Klarna"),
        ("https://careers.spotify.com/job/789", "Spotify"),
    ]
    
    for url, expected_company in test_urls:
        print(f"\nTesting: {url}")
        result = parser.parse(url, auto_fetch=False)  # Don't fetch HTML in test
        print(f"  Expected: {expected_company}")
        print(f"  Extracted: {result.get('company', 'None')}")
        print(f"  Domain: {result.get('company_domain', 'None')}")
        print(f"  Confidence: {result.get('confidence_score', 0):.2f}")


def test_company_resolver():
    """Test company name resolution and domain discovery"""
    print("\n\n=== Testing Company Resolution ===")
    
    resolver = CompanyResolver()
    
    # Test companies from obscure to well-known
    test_companies = [
        # Obscure startups
        ("Replicant", "replicant.com"),
        ("Voltron Data", None),  # Very new company
        ("Moonhub", None),
        ("Anyscale", "anyscale.com"),
        
        # Ambiguous names
        ("Root", "root.io"),
        ("Nova", None),  # Multiple companies named Nova
        ("Bloom", None),  # Very ambiguous
        ("Lattice", "lattice.com"),
        
        # Known aliases
        ("Facebook", "Meta"),
        ("Google", "Google"),
        
        # Edge cases
        ("Root Insurance", "Root Insurance"),
        ("Meta Platforms Inc.", "Meta"),
        ("Apple Computer", "Apple"),
    ]
    
    for company, expected in test_companies:
        normalized = resolver.normalize_company_name(company)
        domain = resolver.get_company_domain(company)
        is_ambiguous = resolver.is_ambiguous_company(company)
        
        print(f"\n{company}:")
        print(f"  Normalized: {normalized}")
        print(f"  Domain: {domain or 'Not found'}")
        print(f"  Ambiguous: {is_ambiguous}")
        
        if expected and normalized != expected and domain != expected:
            print(f"  ⚠️  Expected: {expected}")


def test_search_accuracy():
    """Test search accuracy with obscure companies"""
    print("\n\n=== Testing Search Accuracy ===")
    
    searcher = ActuallyWorkingFreeSources()
    
    # Only test if configured
    if not searcher.is_configured():
        print("⚠️  Search sources not configured. Skipping search tests.")
        print("   Set GOOGLE_API_KEY and GOOGLE_CSE_ID to test search.")
        return
    
    # Test with various company types
    test_searches = [
        # Obscure but real companies
        ("Replicant", "Software Engineer"),
        ("Voltron Data", "Data Engineer"),
        ("Anyscale", "ML Engineer"),
        
        # Ambiguous names requiring good filtering
        ("Root", "AI Engineer"),
        ("Nova", "Product Manager"),
        ("Bloom", "Engineering Manager"),
        
        # Companies with similar names (test false positive filtering)
        ("Lattice", "Software Engineer"),  # Not "Lattice Semiconductor"
        ("Stripe", "Engineer"),  # Not "Stripe Press" or other variants
        
        # Edge case: Very small/new companies
        ("Moonhub", "Recruiter"),
        ("Vanta", "Security Engineer"),
    ]
    
    for company, title in test_searches[:3]:  # Limit to avoid rate limits
        print(f"\n\nSearching: {company} - {title}")
        print("-" * 50)
        
        # Create minimal job context
        job_context = JobContext(
            job_url="https://example.com/job",
            company=company,
            job_title=title,
            job_description=f"Looking for {title} at {company}"
        )
        
        # Search
        results = searcher.search_people(
            company=company,
            title=title,
            job_context=job_context
        )
        
        print(f"Found {len(results)} results")
        
        # Analyze results
        correct_company = 0
        high_confidence = 0
        has_linkedin = 0
        
        for i, person in enumerate(results[:5]):
            print(f"\n  {i+1}. {person.name}")
            print(f"     Title: {person.title or 'Unknown'}")
            print(f"     Company: {person.company}")
            print(f"     Score: {person.confidence_score:.2f}")
            print(f"     LinkedIn: {'✓' if person.linkedin_url else '✗'}")
            
            # Check accuracy
            normalized = searcher.company_resolver.normalize_company_name(person.company)
            if normalized.lower() == searcher.company_resolver.normalize_company_name(company).lower():
                correct_company += 1
            else:
                print(f"     ⚠️  Wrong company detected!")
            
            if person.confidence_score >= 0.7:
                high_confidence += 1
            if person.linkedin_url:
                has_linkedin += 1
        
        # Summary
        if results:
            accuracy = (correct_company / min(len(results), 5)) * 100
            print(f"\n  Accuracy: {accuracy:.0f}% correct company")
            print(f"  Quality: {high_confidence} high confidence, {has_linkedin} with LinkedIn")
        else:
            print("\n  ⚠️  No results found!")


def test_edge_cases():
    """Test specific edge cases that are problematic"""
    print("\n\n=== Testing Edge Cases ===")
    
    resolver = CompanyResolver()
    
    edge_cases = [
        # Companies with special characters
        ("D.E. Shaw", "D.E. Shaw"),
        ("AT&T", "AT&T"),
        ("Barnes & Noble", "Barnes & Noble"),
        
        # Companies with dots in names
        ("Root.io", "Root.io"),
        ("Bit.ly", "Bit.ly"),
        
        # Very short names
        ("X", "X"),
        ("a16z", "a16z"),
        ("e", "e"),  # Yes, there's a company called "e"
        
        # Numbers in names
        ("23andMe", "23andMe"),
        ("1Password", "1Password"),
        ("6sense", "6sense"),
        
        # Foreign companies
        ("Klarna", "Klarna"),
        ("Spotify", "Spotify"),
        ("SAP", "SAP"),
    ]
    
    for company, expected in edge_cases:
        normalized = resolver.normalize_company_name(company)
        print(f"\n{company} -> {normalized}")
        if normalized != expected:
            print(f"  ⚠️  Expected: {expected}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Dynamic Search with Obscure Companies")
    print("=" * 60)
    
    # Run tests
    test_company_extraction()
    test_company_resolver()
    test_search_accuracy()
    test_edge_cases()
    
    print("\n\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
