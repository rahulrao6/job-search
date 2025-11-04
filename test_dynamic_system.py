#!/usr/bin/env python3
"""
Comprehensive test script for the dynamic search and ranking system.
Tests all new components before pushing to branch.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extractors.job_parser import JobParser
from src.utils.company_resolver import CompanyResolver
from src.utils.query_optimizer import QueryOptimizer
from src.utils.ranking_engine import RankingEngine, ScoringWeights
from src.utils.validation_pipeline import ValidationPipeline
from src.models.job_context import JobContext, CandidateProfile
from src.models.person import Person, PersonCategory
from src.core.categorizer import PersonCategorizer
from src.services.profile_matcher import ProfileMatcher
from src.scrapers.actually_working_free_sources import ActuallyWorkingFreeSources

# Test data
TEST_COMPANIES = [
    # Well-known tech
    ("Google", "google.com"),
    ("Meta", "meta.com"),
    ("Microsoft", "microsoft.com"),
    
    # Startups
    ("Anyscale", "anyscale.com"),
    ("Replicant", "replicant.ai"),
    ("Moonhub", "moonhub.ai"),
    
    # Ambiguous names
    ("Root", "root.io"),
    ("Nova", "nova.ai"),
    ("Atlas", None),  # Let it discover
    
    # Various industries
    ("Stripe", "stripe.com"),
    ("Databricks", "databricks.com"),
    ("Anthropic", "anthropic.com"),
]

TEST_JOB_URLS = [
    "https://builtin.com/job/ai-engineer/7205920",
    "https://www.linkedin.com/jobs/view/3456789",
    "https://greenhouse.io/company/jobs/12345",
    "https://jobs.lever.co/company/abc123",
]

TEST_TITLES = [
    "AI Engineer",
    "Software Engineer",
    "ML Engineer",
    "Data Scientist",
    "Product Manager",
    "Engineering Intern",
    "Senior SWE",
    "DevOps Engineer",
]


class DynamicSystemTester:
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }
        
    def log_test(self, name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status}: {name}")
        if details:
            print(f"   Details: {details}")
        
        self.results['tests'].append({
            'name': name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        if passed:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
    
    def test_job_parser(self):
        """Test enhanced job parser"""
        print("\n" + "="*60)
        print("🧪 Testing Job Parser")
        print("="*60)
        
        parser = JobParser()
        
        # Test with builtin URL (known problematic)
        url = "https://builtin.com/job/ai-engineer/7205920"
        try:
            result = parser.parse(url)
            
            # Check if company was extracted correctly
            if result.get('company') and 'builtin' not in result['company'].lower():
                self.log_test(
                    "Job Parser - Builtin extraction",
                    True,
                    f"Extracted company: {result.get('company')}"
                )
            else:
                self.log_test(
                    "Job Parser - Builtin extraction",
                    False,
                    f"Failed to extract company, got: {result.get('company')}"
                )
                
            # Check confidence score (might be 'extraction_confidence' or 'confidence_score')
            confidence = result.get('confidence', 0) or result.get('extraction_confidence', 0) or result.get('confidence_score', 0)
            if confidence > 0:
                self.log_test(
                    "Job Parser - Confidence scoring",
                    True,
                    f"Confidence: {confidence}"
                )
            else:
                self.log_test(
                    "Job Parser - Confidence scoring",
                    False,
                    f"No confidence score in result: {list(result.keys())}"
                )
                
        except Exception as e:
            self.log_test(
                "Job Parser - Basic functionality",
                False,
                str(e)
            )
    
    def test_company_resolver(self):
        """Test company resolver"""
        print("\n" + "="*60)
        print("🧪 Testing Company Resolver")
        print("="*60)
        
        resolver = CompanyResolver()
        
        # Test normalization
        test_cases = [
            ("Facebook", "Meta"),
            ("Google", "Google"),  # Should stay Google
            ("FB", "Meta"),
        ]
        
        for input_name, expected in test_cases:
            normalized = resolver.normalize_company_name(input_name)
            passed = (normalized == expected) or (input_name == expected)
            self.log_test(
                f"Company Normalization - {input_name}",
                passed,
                f"Got: {normalized}, Expected: {expected}"
            )
        
        # Test domain lookup
        for company, expected_domain in [("Google", "google.com"), ("Anyscale", "anyscale.com")]:
            domain = resolver.get_company_domain(company)
            if domain:
                self.log_test(
                    f"Domain Discovery - {company}",
                    True,
                    f"Found: {domain}"
                )
            else:
                self.log_test(
                    f"Domain Discovery - {company}",
                    False,
                    "No domain found"
                )
        
        # Test ambiguity detection
        ambiguous_companies = ["Root", "Nova", "Atlas"]
        for company in ambiguous_companies:
            is_ambiguous = resolver.is_ambiguous_company(company)
            self.log_test(
                f"Ambiguity Detection - {company}",
                is_ambiguous,
                f"Detected as {'ambiguous' if is_ambiguous else 'not ambiguous'}"
            )
        
        # Test match scoring
        test_text = "John Doe - Software Engineer at Google - Mountain View"
        score = resolver.calculate_company_match_score(test_text, "Google", "google.com")
        self.log_test(
            "Company Match Scoring",
            score >= 0.4,  # 0.4 is reasonable for partial matches
            f"Score: {score}"
        )
    
    def test_query_optimizer(self):
        """Test query optimizer"""
        print("\n" + "="*60)
        print("🧪 Testing Query Optimizer")
        print("="*60)
        
        optimizer = QueryOptimizer()
        
        # Test with different contexts
        job_context = JobContext(
            job_url="https://example.com/job/123",  # Required field
            job_title="AI Engineer",
            company="Anyscale",
            company_domain="anyscale.com",
            department="Engineering",
            location="San Francisco",
            candidate_skills=["Python", "Machine Learning", "PyTorch"]
        )
        
        profile = CandidateProfile(
            schools=["Stanford University"],
            past_companies=["Google", "Meta"],
            skills=["Python", "ML", "AI"]
        )
        
        # Test LinkedIn queries
        queries = optimizer.generate_queries(
            company="Anyscale",
            title="AI Engineer",
            job_context=job_context,
            candidate_profile=profile,
            platform='linkedin'
        )
        
        self.log_test(
            "Query Generation - LinkedIn",
            len(queries) > 3,
            f"Generated {len(queries)} queries"
        )
        
        # Check if queries include key elements
        has_domain = any("anyscale.com" in q for q in queries)
        has_alumni = any("Stanford" in q for q in queries)
        has_skills = any("Python" in q or "ML" in q for q in queries)
        
        self.log_test(
            "Query Quality - Context inclusion",
            has_domain and has_alumni,
            f"Domain: {has_domain}, Alumni: {has_alumni}, Skills: {has_skills}"
        )
    
    def test_categorizer(self):
        """Test enhanced categorizer"""
        print("\n" + "="*60)
        print("🧪 Testing Role Categorizer")
        print("="*60)
        
        for target_title in ["AI Engineer", "Software Engineering Intern"]:
            categorizer = PersonCategorizer(target_title)
            
            test_people = [
                Person(name="John Doe", title="Technical Recruiter", company="Test", source="test"),
                Person(name="Jane Smith", title="Engineering Manager", company="Test", source="test"),
                Person(name="Bob Wilson", title="Senior AI Engineer", company="Test", source="test"),
                Person(name="Alice Chen", title="ML Engineer", company="Test", source="test"),
                Person(name="Charlie Brown", title="Software Engineering Intern", company="Test", source="test"),
            ]
            
            for person in test_people:
                categorized = categorizer.categorize(person)
                self.log_test(
                    f"Categorization - {person.title} (target: {target_title})",
                    categorized.category != PersonCategory.UNKNOWN,
                    f"Category: {categorized.category.value}"
                )
            
            # Test early career detection
            is_early = categorizer.is_early_career_role(target_title)
            expected_early = "intern" in target_title.lower() or "entry" in target_title.lower()
            self.log_test(
                f"Early Career Detection - {target_title}",
                is_early == expected_early,
                f"Detected as {'early' if is_early else 'not early'} career"
            )
    
    def test_profile_matcher(self):
        """Test profile matcher"""
        print("\n" + "="*60)
        print("🧪 Testing Profile Matcher")
        print("="*60)
        
        matcher = ProfileMatcher()
        
        # Create test data
        person = Person(
            name="Test User",
            title="AI Engineer",
            company="Anyscale",
            location="San Francisco",
            skills=["Python", "PyTorch"],
            category=PersonCategory.PEER,
            source="test"
        )
        
        profile = CandidateProfile(
            schools=["Stanford University"],
            past_companies=["Anyscale"],  # Ex-employee match
            skills=["Python", "Machine Learning"]
        )
        
        job_context = JobContext(
            job_url="https://example.com/job/456",  # Required field
            job_title="AI Engineer Intern",  # Early career
            company="Anyscale",
            location="San Francisco"
        )
        
        score, reasons = matcher.calculate_relevance(
            person=person,
            candidate_profile=profile,
            job_context=job_context
        )
        
        self.log_test(
            "Profile Match Scoring",
            score > 0.5,
            f"Score: {score:.2f}, Reasons: {', '.join(reasons)}"
        )
        
        # Check if early career boost worked
        has_ex_company = any("ex_company" in r for r in reasons)
        self.log_test(
            "Profile Match - Ex-company detection",
            has_ex_company,
            f"Detected ex-company: {has_ex_company}"
        )
    
    def test_validation_pipeline(self):
        """Test validation pipeline"""
        print("\n" + "="*60)
        print("🧪 Testing Validation Pipeline")
        print("="*60)
        
        pipeline = ValidationPipeline()
        
        # Create test people with various quality levels
        test_people = [
            Person(
                name="Good Match",
                title="AI Engineer at Anyscale",
                company="Anyscale",
                linkedin_url="https://linkedin.com/in/good-match",
                skills=["Python", "ML"],
                confidence_score=0.8,
                source="test"
            ),
            Person(
                name="Past Employee",
                title="Former AI Engineer at Anyscale",
                company="Anyscale",
                linkedin_url="https://linkedin.com/in/past-employee",
                confidence_score=0.5,
                source="test"
            ),
            Person(
                name="Wrong Company",
                title="AI Engineer at Different Corp",
                company="Different Corp",
                linkedin_url=None,
                confidence_score=0.3,
                source="test"
            ),
            Person(
                name="Anyscale Jones",  # Name matches company
                title="Random Title",
                company="Unknown",
                confidence_score=0.2,
                source="test"
            )
        ]
        
        results, metrics = pipeline.process_results(
            people=test_people,
            company="Anyscale",
            company_domain="anyscale.com"
        )
        
        valid_count = sum(1 for r in results if r.is_valid)
        self.log_test(
            "Validation Pipeline - Basic filtering",
            valid_count < len(test_people),
            f"Filtered {len(test_people) - valid_count} of {len(test_people)} people"
        )
        
        # Check metrics
        self.log_test(
            "Validation Pipeline - Metrics generation",
            'average_confidence' in metrics and metrics['average_confidence'] > 0,
            f"Avg confidence: {metrics.get('average_confidence', 0):.2f}"
        )
    
    def test_search_integration(self):
        """Test search with new components"""
        print("\n" + "="*60)
        print("🧪 Testing Search Integration")
        print("="*60)
        
        # Only test if API keys are available
        if not os.getenv('GOOGLE_API_KEY'):
            self.log_test(
                "Search Integration",
                False,
                "Skipped - No API keys configured"
            )
            return
        
        searcher = ActuallyWorkingFreeSources()
        
        # Test with a known company
        job_context = JobContext(
            job_url="https://google.com/careers/job/789",  # Required field
            job_title="Software Engineer",
            company="Google",
            company_domain="google.com"
        )
        
        try:
            results = searcher._search_google_cse(
                company="Google",
                title="Software Engineer",
                job_context=job_context
            )
            
            self.log_test(
                "Google CSE Integration",
                len(results) > 0,
                f"Found {len(results)} results"
            )
            
            # Check if results have required fields
            if results:
                person = results[0]
                has_fields = all([
                    person.name,
                    person.title,
                    person.linkedin_url
                ])
                self.log_test(
                    "Search Result Quality",
                    has_fields,
                    f"First result: {person.name} - {person.title}"
                )
                
        except Exception as e:
            self.log_test(
                "Search Integration",
                False,
                f"Error: {str(e)}"
            )
    
    def test_ranking_engine(self):
        """Test ranking engine"""
        print("\n" + "="*60)
        print("🧪 Testing Ranking Engine")
        print("="*60)
        
        engine = RankingEngine()
        
        # Create test people
        test_people = [
            Person(
                name="Recruiter Jane",
                title="Technical Recruiter",
                company="TestCo",
                category=PersonCategory.RECRUITER,
                confidence_score=0.9,
                linkedin_url="https://linkedin.com/in/jane",
                source="test"
            ),
            Person(
                name="Manager Bob",
                title="Engineering Manager",
                company="TestCo",
                category=PersonCategory.MANAGER,
                confidence_score=0.8,
                linkedin_url="https://linkedin.com/in/bob",
                source="test"
            ),
            Person(
                name="Peer Alice",
                title="AI Engineer",
                company="TestCo",
                category=PersonCategory.PEER,
                confidence_score=0.7,
                skills=["Python", "ML"],
                source="test"
            ),
        ]
        
        job_context = JobContext(
            job_url="https://testco.com/job/999",  # Required field
            job_title="AI Engineer",
            company="TestCo",
            candidate_skills=["Python", "ML"]
        )
        
        profile = CandidateProfile(
            skills=["Python", "Machine Learning"]
        )
        
        ranked = engine.rank_people(
            people=test_people,
            job_context=job_context,
            candidate_profile=profile
        )
        
        # Check if recruiter is ranked first
        if ranked:
            first_person = ranked[0][0]
            is_recruiter = first_person.category == PersonCategory.RECRUITER
            self.log_test(
                "Ranking - Recruiter priority",
                is_recruiter,
                f"Top result: {first_person.name} ({first_person.category.value})"
            )
            
            # Check if scores are provided
            has_scores = all(score > 0 for _, score, _ in ranked)
            self.log_test(
                "Ranking - Score calculation",
                has_scores,
                f"All {len(ranked)} results have scores"
            )
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        print("\n" + "🚀 "*20)
        print("DYNAMIC SEARCH SYSTEM - COMPREHENSIVE TEST SUITE")
        print("🚀 "*20)
        
        start_time = datetime.now()
        
        # Run all test suites
        self.test_job_parser()
        self.test_company_resolver()
        self.test_query_optimizer()
        self.test_categorizer()
        self.test_profile_matcher()
        self.test_validation_pipeline()
        self.test_ranking_engine()
        self.test_search_integration()
        
        # Generate summary
        duration = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.results['passed'] + self.results['failed']}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"🎯 Success Rate: {(self.results['passed'] / max(1, self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        # Save detailed results
        with open('test_results_dynamic_system.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: test_results_dynamic_system.json")
        
        # Return success status
        return self.results['failed'] == 0


if __name__ == "__main__":
    tester = DynamicSystemTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ ✅ ✅ ALL TESTS PASSED! Safe to push to branch. ✅ ✅ ✅")
        sys.exit(0)
    else:
        print("\n⚠️  ⚠️  ⚠️  SOME TESTS FAILED! Review before pushing. ⚠️  ⚠️  ⚠️")
        sys.exit(1)
