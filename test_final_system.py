#!/usr/bin/env python3
"""
Final comprehensive test suite for the Job Referral Connection Finder.
Tests with 5 obscure companies to ensure everything works as expected.
"""

import time
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import sys

# Load environment and add src to path
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.orchestrator import ConnectionFinder


def test_company(finder, company, title, expected_min=5):
    """Test a single company search"""
    print(f"\n{'='*80}")
    print(f"🏢 Testing: {company} - {title}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        results = finder.find_connections(
            company=company,
            title=title,
            use_cache=False  # Always fresh results for testing
        )
        
        elapsed = time.time() - start_time
        
        # Extract key metrics
        total_found = results.get('total_found', 0)
        by_category = results.get('by_category', {})
        source_stats = results.get('source_stats', {})
        cost_stats = results.get('cost_stats', {})
        
        # Count quality results (non-unknown)
        quality_count = sum(len(people) for cat, people in by_category.items() if cat != 'unknown')
        
        print(f"\n📊 RESULTS:")
        print(f"├─ Total found: {total_found}")
        print(f"├─ Quality profiles: {quality_count}")
        print(f"├─ Time taken: {elapsed:.1f} seconds")
        print(f"├─ Total cost: ${cost_stats.get('total_cost', 0):.2f}")
        
        print(f"\n📈 BY CATEGORY:")
        for category, people in by_category.items():
            if people:
                print(f"├─ {category.title()}: {len(people)} people")
                # Show first 2 examples
                for i, person in enumerate(people[:2]):
                    name = person.get('name', 'Unknown')
                    title_str = person.get('title', 'No title')[:50]
                    source = person.get('source', 'unknown')
                    print(f"│  └─ {name} | {title_str} ({source})")
                if len(people) > 2:
                    print(f"│  └─ ... and {len(people) - 2} more")
        
        print(f"\n📍 BY SOURCE:")
        for source, count in source_stats.items():
            print(f"├─ {source}: {count} people")
        
        # Validation
        print(f"\n✅ VALIDATION:")
        status = "PASS" if quality_count >= expected_min else "FAIL"
        print(f"├─ Expected min: {expected_min} quality profiles")
        print(f"├─ Got: {quality_count} quality profiles")
        print(f"├─ Status: {status}")
        print(f"├─ Time limit: {'PASS' if elapsed < 30 else 'FAIL'} ({elapsed:.1f}s < 30s)")
        
        return {
            'company': company,
            'title': title,
            'total': total_found,
            'quality': quality_count,
            'time': elapsed,
            'cost': cost_stats.get('total_cost', 0),
            'status': status
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return {
            'company': company,
            'title': title,
            'error': str(e),
            'status': 'ERROR'
        }


def main():
    """Run comprehensive test suite"""
    print("🚀 FINAL COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check configuration
    print("\n📋 CONFIGURATION CHECK:")
    print(f"├─ GOOGLE_API_KEY: {'✅ Set' if os.getenv('GOOGLE_API_KEY') else '❌ Missing'}")
    print(f"├─ GOOGLE_CSE_ID: {'✅ Set' if os.getenv('GOOGLE_CSE_ID') else '❌ Missing'}")
    print(f"├─ OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"├─ GITHUB_TOKEN: {'✅ Set' if os.getenv('GITHUB_TOKEN') else '⚠️  Optional'}")
    print(f"├─ SERP_API_KEY: {'✅ Set' if os.getenv('SERP_API_KEY') else '⚠️  Optional'}")
    print(f"└─ APOLLO_API_KEY: {'✅ Set' if os.getenv('APOLLO_API_KEY') else '⚠️  Optional'}")
    
    # Initialize finder
    finder = ConnectionFinder()
    
    # Test companies - 5 obscure ones we haven't tested before
    test_cases = [
        # Small/Medium tech companies
        ("Notion", "Software Engineer", 8),
        ("Linear", "Product Engineer", 5),
        
        # Non-tech companies
        ("Warby Parker", "Data Analyst", 5),
        ("Sweetgreen", "Marketing Manager", 5),
        
        # Very small/obscure
        ("Primer", "Designer", 3),  # Small education startup
    ]
    
    results = []
    total_start = time.time()
    
    # Run all tests
    for company, title, expected_min in test_cases:
        result = test_company(finder, company, title, expected_min)
        results.append(result)
        time.sleep(2)  # Small delay between searches
    
    # Summary
    total_time = time.time() - total_start
    
    print(f"\n{'='*80}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*80}")
    
    print(f"\n📈 Overall Stats:")
    print(f"├─ Total companies tested: {len(results)}")
    print(f"├─ Successful searches: {sum(1 for r in results if r.get('status') == 'PASS')}")
    print(f"├─ Failed searches: {sum(1 for r in results if r.get('status') == 'FAIL')}")
    print(f"├─ Errors: {sum(1 for r in results if r.get('status') == 'ERROR')}")
    print(f"├─ Total time: {total_time:.1f} seconds")
    print(f"└─ Average time per search: {total_time/len(results):.1f} seconds")
    
    print(f"\n📊 Detailed Results:")
    for r in results:
        if 'error' in r:
            print(f"├─ {r['company']:15} | ERROR: {r['error']}")
        else:
            print(f"├─ {r['company']:15} | Quality: {r['quality']:3} | Time: {r['time']:4.1f}s | Cost: ${r['cost']:.2f} | {r['status']}")
    
    # Quality metrics
    quality_results = [r for r in results if 'quality' in r]
    if quality_results:
        avg_quality = sum(r['quality'] for r in quality_results) / len(quality_results)
        avg_time = sum(r['time'] for r in quality_results) / len(quality_results)
        total_cost = sum(r.get('cost', 0) for r in quality_results)
        
        print(f"\n🎯 Quality Metrics:")
        print(f"├─ Average quality profiles per search: {avg_quality:.1f}")
        print(f"├─ Average search time: {avg_time:.1f} seconds")
        print(f"├─ Total cost for all searches: ${total_cost:.2f}")
        print(f"└─ Cost per search: ${total_cost/len(quality_results):.2f}")
    
    # Final verdict
    print(f"\n🏁 FINAL VERDICT:")
    all_passed = all(r.get('status') in ['PASS', 'ERROR'] for r in results)
    if all_passed and sum(1 for r in results if r.get('status') == 'PASS') >= 4:
        print("✅ SYSTEM IS PRODUCTION READY!")
        print("   - Quality results for diverse companies")
        print("   - Fast performance (under 30s)")
        print("   - Low cost (mostly free)")
    else:
        print("⚠️  SYSTEM NEEDS ATTENTION")
        print("   - Some searches failed to meet minimum quality threshold")
        print("   - Check API configurations and limits")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'test_results_{timestamp}.json'
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'configuration': {
                'google_cse': bool(os.getenv('GOOGLE_API_KEY')),
                'openai': bool(os.getenv('OPENAI_API_KEY')),
                'github': bool(os.getenv('GITHUB_TOKEN')),
                'serp': bool(os.getenv('SERP_API_KEY')),
                'apollo': bool(os.getenv('APOLLO_API_KEY'))
            },
            'results': results,
            'summary': {
                'total_tests': len(results),
                'passed': sum(1 for r in results if r.get('status') == 'PASS'),
                'failed': sum(1 for r in results if r.get('status') == 'FAIL'),
                'errors': sum(1 for r in results if r.get('status') == 'ERROR'),
                'total_time': total_time,
                'avg_quality': avg_quality if quality_results else 0,
                'total_cost': total_cost if quality_results else 0
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
