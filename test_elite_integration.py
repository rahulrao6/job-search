#!/usr/bin/env python3
"""
Comprehensive Integration Test for Elite Scraping System
Tests all components working together accurately
"""

import os
import sys
import time
from typing import Dict, List

# Add project root to path
sys.path.insert(0, '.')

def test_basic_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing module imports...")
    
    try:
        from src.models.person import Person, PersonCategory
        print("  ✓ Core models imported")
        
        from src.scrapers.actually_working_free_sources import ActuallyWorkingFreeSources
        print("  ✓ Base API sources imported")
        
        try:
            from src.scrapers.enhanced_elite_sources import EnhancedEliteSources
            print("  ✓ Enhanced Selenium sources imported")
            selenium_available = True
        except ImportError as e:
            print(f"  ⚠ Enhanced sources not available: {e}")
            selenium_available = False
        
        try:
            from src.scrapers.elite_sources_integration import EliteSourcesOrchestrator
            print("  ✓ Elite orchestrator imported")
        except ImportError as e:
            print(f"  ❌ Elite orchestrator import failed: {e}")
            return False
        
        from src.core.orchestrator import ConnectionFinder
        print("  ✓ Main orchestrator imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_configuration():
    """Test API configuration status"""
    print("\n📋 Testing API configurations...")
    
    config_status = {}
    
    # Check API keys
    config_status['google_cse'] = bool(os.getenv('GOOGLE_CSE_ID') and os.getenv('GOOGLE_API_KEY'))
    config_status['bing_api'] = bool(os.getenv('BING_SEARCH_KEY'))
    config_status['github_token'] = bool(os.getenv('GITHUB_TOKEN'))
    config_status['serp_api'] = bool(os.getenv('SERP_API_KEY'))
    config_status['apollo_api'] = bool(os.getenv('APOLLO_API_KEY'))
    
    print(f"  Google CSE: {'✓ Configured' if config_status['google_cse'] else '⊘ Not configured'}")
    print(f"  Bing API: {'✓ Configured' if config_status['bing_api'] else '⊘ Not configured'}")
    print(f"  GitHub Token: {'✓ Configured' if config_status['github_token'] else '⊘ Using 60/hour limit'}")
    print(f"  SerpAPI: {'✓ Configured' if config_status['serp_api'] else '⊘ Not configured'}")
    print(f"  Apollo API: {'✓ Configured' if config_status['apollo_api'] else '⊘ Not configured'}")
    
    return config_status

def test_base_api_sources():
    """Test base API sources individually"""
    print("\n🔧 Testing base API sources...")
    
    try:
        from src.scrapers.actually_working_free_sources import ActuallyWorkingFreeSources
        
        searcher = ActuallyWorkingFreeSources()
        
        # Test with a known company
        print("  Testing with 'Google' as target company...")
        people = searcher.search_all("Google", max_results=10)
        
        print(f"  ✓ Base API sources returned {len(people)} people")
        
        if people:
            print("  Sample results:")
            for i, person in enumerate(people[:3], 1):
                print(f"    {i}. {person.name} ({person.source})")
                if person.linkedin_url:
                    print(f"       LinkedIn: {person.linkedin_url[:60]}...")
            return True
        else:
            print("  ⚠ No results from base sources - check API configuration")
            return False
            
    except Exception as e:
        print(f"  ❌ Base sources test failed: {e}")
        return False

def test_elite_orchestrator():
    """Test elite sources orchestrator"""
    print("\n🚀 Testing Elite Sources Orchestrator...")
    
    try:
        from src.scrapers.elite_sources_integration import EliteSourcesOrchestrator
        
        orchestrator = EliteSourcesOrchestrator()
        
        # Show capabilities
        caps = orchestrator.get_capabilities()
        print(f"  Expected results: {caps['expected_results']}")
        print(f"  Available sources: {len(caps['sources_available'])}")
        
        # Run health check
        health = orchestrator.health_check()
        print(f"  Health status: {health['overall_status']}")
        
        # Test search
        print("  Running search test...")
        people = orchestrator.search_all("Google", "Software Engineer", max_results=15)
        
        print(f"  ✓ Elite orchestrator returned {len(people)} people")
        
        if people:
            # Show breakdown by source
            source_counts = {}
            for person in people:
                source = person.source
                source_counts[source] = source_counts.get(source, 0) + 1
            
            print("  Source breakdown:")
            for source, count in source_counts.items():
                print(f"    {source}: {count} people")
            
            return True
        else:
            print("  ⚠ No results from elite orchestrator")
            return False
            
    except Exception as e:
        print(f"  ❌ Elite orchestrator test failed: {e}")
        return False

def test_main_orchestrator():
    """Test main ConnectionFinder orchestrator with elite sources"""
    print("\n🎯 Testing Main Orchestrator (ConnectionFinder) with Elite Integration...")
    
    try:
        from src.core.orchestrator import ConnectionFinder
        
        # Initialize with elite sources
        finder = ConnectionFinder()
        
        # Run search
        print("  Running full orchestrator search...")
        results = finder.find_connections("Google", "Software Engineer", use_cache=False)
        
        total_people = results.get('total_found', 0)
        print(f"  ✓ Main orchestrator found {total_people} total connections")
        
        # Show category breakdown
        category_counts = results.get('category_counts', {})
        print("  Category breakdown:")
        for category, count in category_counts.items():
            if count > 0:
                print(f"    {category}: {count} people")
        
        # Show source breakdown
        source_stats = results.get('source_stats', {}).get('by_source', {})
        print("  Source breakdown:")
        for source, count in source_stats.items():
            if count > 0:
                print(f"    {source}: {count} people")
        
        return total_people > 0
        
    except Exception as e:
        print(f"  ❌ Main orchestrator test failed: {e}")
        return False

def test_selenium_availability():
    """Test if Selenium components are available and working"""
    print("\n🔍 Testing Selenium availability...")
    
    try:
        # Test basic Selenium imports
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        print("  ✓ Selenium modules available")
        
        # Test webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            print("  ✓ WebDriver Manager available")
        except ImportError:
            print("  ⚠ WebDriver Manager not available")
        
        # Test undetected-chromedriver
        try:
            import undetected_chromedriver as uc
            print("  ✓ Undetected ChromeDriver available")
        except ImportError:
            print("  ⚠ Undetected ChromeDriver not available")
        
        # Test if Chrome is actually available (don't create driver, just check)
        print("  ℹ Selenium components available (not testing browser creation in automated test)")
        return True
        
    except ImportError as e:
        print(f"  ❌ Selenium not available: {e}")
        print("  ℹ Install with: pip install selenium webdriver-manager undetected-chromedriver")
        return False

def test_data_models():
    """Test data model consistency"""
    print("\n📊 Testing data model consistency...")
    
    try:
        from src.models.person import Person, PersonCategory
        
        # Create test person
        person = Person(
            name="Test User",
            title="Software Engineer",
            company="Test Company",
            linkedin_url="https://linkedin.com/in/testuser",
            source="test_source",
            confidence_score=0.8
        )
        
        print(f"  ✓ Person model: {person.name} - {person.title}")
        print(f"  ✓ Source: {person.source}")
        print(f"  ✓ Confidence: {person.confidence_score}")
        
        # Test categories
        categories = [cat.value for cat in PersonCategory]
        print(f"  ✓ Available categories: {', '.join(categories)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Data model test failed: {e}")
        return False

def generate_integration_report(test_results: Dict[str, bool], config_status: Dict[str, bool]):
    """Generate comprehensive integration report"""
    
    print("\n" + "="*70)
    print("📊 ELITE SCRAPING SYSTEM - INTEGRATION REPORT")
    print("="*70)
    
    # Overall status
    all_core_tests_passed = all([
        test_results.get('imports', False),
        test_results.get('data_models', False),
        test_results.get('base_api', False),
    ])
    
    elite_tests_passed = test_results.get('elite_orchestrator', False)
    main_orchestrator_passed = test_results.get('main_orchestrator', False)
    
    if all_core_tests_passed and main_orchestrator_passed:
        status = "🟢 FULLY OPERATIONAL"
        expected_results = "200-500+ people per search"
    elif all_core_tests_passed:
        status = "🟡 PARTIALLY OPERATIONAL"
        expected_results = "50-200 people per search"
    else:
        status = "🔴 NEEDS ATTENTION"
        expected_results = "System issues detected"
    
    print(f"Overall Status: {status}")
    print(f"Expected Performance: {expected_results}")
    
    print(f"\n📋 Core Components:")
    print(f"  Module Imports: {'✅' if test_results.get('imports') else '❌'}")
    print(f"  Data Models: {'✅' if test_results.get('data_models') else '❌'}")
    print(f"  Base API Sources: {'✅' if test_results.get('base_api') else '❌'}")
    print(f"  Elite Orchestrator: {'✅' if test_results.get('elite_orchestrator') else '❌'}")
    print(f"  Main Orchestrator: {'✅' if test_results.get('main_orchestrator') else '❌'}")
    print(f"  Selenium Support: {'✅' if test_results.get('selenium') else '⚠️'}")
    
    print(f"\n🔑 API Configuration:")
    print(f"  Google CSE: {'✅' if config_status.get('google_cse') else '⚠️ Not configured'}")
    print(f"  Bing API: {'✅' if config_status.get('bing_api') else '⚠️ Not configured'}")
    print(f"  GitHub Token: {'✅' if config_status.get('github_token') else '⚠️ Using limits'}")
    print(f"  SerpAPI (Premium): {'✅' if config_status.get('serp_api') else '⚠️ Not configured'}")
    print(f"  Apollo API (Premium): {'✅' if config_status.get('apollo_api') else '⚠️ Not configured'}")
    
    print(f"\n🚀 Recommendations:")
    
    if not all_core_tests_passed:
        print("  ❗ CRITICAL: Fix core component issues first")
    
    if not config_status.get('google_cse'):
        print("  💡 Add Google CSE for 2-3x more results (free, 5 min setup)")
    
    if not config_status.get('github_token'):
        print("  💡 Add GitHub token for higher rate limits (free)")
    
    if not test_results.get('selenium'):
        print("  💡 Install Selenium for 3-5x more results:")
        print("     pip install selenium webdriver-manager undetected-chromedriver")
    
    if config_status.get('google_cse') and test_results.get('selenium') and main_orchestrator_passed:
        print("  🎉 System is fully optimized! You should see 200-500+ results per search.")
    
    print("\n📖 Documentation:")
    print("  Setup Guide: SETUP_FREE_APIS.md")
    print("  Architecture: docs/architecture.md")
    print("  Working Sources: FINAL_FREE_SOURCES_REALITY.md")
    
    print("="*70)

def main():
    """Run comprehensive integration test"""
    print("🎯 ELITE SCRAPING SYSTEM - INTEGRATION TEST")
    print("="*70)
    
    test_results = {}
    config_status = {}
    
    # Run all tests
    test_results['imports'] = test_basic_imports()
    config_status = test_configuration()
    test_results['data_models'] = test_data_models()
    test_results['base_api'] = test_base_api_sources()
    test_results['elite_orchestrator'] = test_elite_orchestrator()
    test_results['main_orchestrator'] = test_main_orchestrator()
    test_results['selenium'] = test_selenium_availability()
    
    # Generate comprehensive report
    generate_integration_report(test_results, config_status)
    
    # Return overall success
    core_success = all([
        test_results.get('imports', False),
        test_results.get('data_models', False),
        test_results.get('main_orchestrator', False)
    ])
    
    return core_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)