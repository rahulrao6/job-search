#!/usr/bin/env python3
"""
Comprehensive testing and improvement script for free sources.
Tests each source individually and shows what works/fails.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Tuple
import time
import json
from datetime import datetime

# Import all sources
from src.core.orchestrator import ConnectionFinder
from src.scrapers.working_free_searcher import WorkingFreeSearcher
from src.sources.smart_company_finder import SmartCompanyFinder


class FreeSourceTester:
    """Test and improve all free sources systematically."""
    
    def __init__(self):
        self.results = {}
        self.finder = ConnectionFinder()
        self.free_searcher = WorkingFreeSearcher()
        self.company_finder = SmartCompanyFinder()
    
    def test_all(self):
        """Run comprehensive tests on all sources."""
        
        # Test companies by size
        test_cases = {
            'large': [
                ('Google', 'Software Engineer'),
                ('Microsoft', 'Product Manager'),
                ('Amazon', 'Data Scientist'),
            ],
            'medium': [
                ('Stripe', 'Software Engineer'),
                ('Databricks', 'Machine Learning Engineer'),
                ('Discord', 'Backend Engineer'),
            ],
            'small': [
                ('Cursor', 'Software Engineer'),
                ('Replicate', 'Engineer'),
                ('Modal', 'Software Engineer'),
                ('Clay', 'Engineer'),
            ],
            'tiny': [
                ('Acme Startup', 'Engineer'),
                ('Unknown Corp', 'Developer'),
            ]
        }
        
        print("🧪 COMPREHENSIVE FREE SOURCE TESTING")
        print("="*60)
        print()
        
        # Test each category
        for size, companies in test_cases.items():
            print(f"\n📊 Testing {size.upper()} companies:")
            print("-"*50)
            
            for company, title in companies:
                self.test_company(company, title, size)
        
        # Print summary
        self.print_summary()
    
    def test_company(self, company: str, title: str, size: str):
        """Test all sources for a specific company."""
        print(f"\n🔍 {company} - {title}")
        
        result = {
            'company': company,
            'title': title,
            'size': size,
            'timestamp': datetime.now().isoformat(),
            'sources': {}
        }
        
        # Test 1: Company domain finder
        print("  → Finding company info...")
        company_info = self.company_finder.find_company_info(company)
        result['company_info'] = company_info
        if company_info['domain']:
            print(f"    ✓ Domain: {company_info['domain']}")
        else:
            print(f"    ✗ No domain found")
        
        # Test 2: Free searcher (DuckDuckGo, Bing, etc.)
        print("  → Testing free search...")
        try:
            free_results = self.free_searcher.search_all(company, title)
            result['sources']['free_search'] = {
                'count': len(free_results),
                'success': len(free_results) > 0,
                'people': [{'name': p.name, 'source': p.source} for p in free_results[:5]]
            }
            print(f"    ✓ Found {len(free_results)} people")
            
            # Show breakdown by source
            by_source = {}
            for person in free_results:
                by_source[person.source] = by_source.get(person.source, 0) + 1
            for source, count in by_source.items():
                print(f"      - {source}: {count}")
                
        except Exception as e:
            result['sources']['free_search'] = {'error': str(e), 'success': False}
            print(f"    ✗ Error: {str(e)[:50]}")
        
        # Test 3: Current orchestrator
        print("  → Testing current system...")
        try:
            current_results = self.finder.find_connections(company, title, use_cache=False)
            total = current_results.get('total_found', 0)
            result['sources']['current_system'] = {
                'count': total,
                'success': total > 0,
                'by_source': current_results.get('source_stats', {})
            }
            print(f"    ✓ Total: {total} people")
            
            # Show source breakdown
            for source, stats in current_results.get('source_stats', {}).items():
                if isinstance(stats, dict) and stats.get('count', 0) > 0:
                    print(f"      - {source}: {stats['count']}")
                elif isinstance(stats, int) and stats > 0:
                    print(f"      - {source}: {stats}")
                    
        except Exception as e:
            result['sources']['current_system'] = {'error': str(e), 'success': False}
            print(f"    ✗ Error: {str(e)[:50]}")
        
        # Store result
        self.results[company] = result
        
        # Small delay between companies
        time.sleep(1)
    
    def print_summary(self):
        """Print comprehensive summary of results."""
        print("\n\n" + "="*60)
        print("📊 SUMMARY REPORT")
        print("="*60)
        
        # Overall stats
        total_companies = len(self.results)
        successful = sum(1 for r in self.results.values() 
                        if any(s.get('success') for s in r['sources'].values()))
        
        print(f"\nOverall Success Rate: {successful}/{total_companies} ({successful/total_companies*100:.0f}%)")
        
        # By company size
        print("\nBy Company Size:")
        for size in ['large', 'medium', 'small', 'tiny']:
            size_results = [r for r in self.results.values() if r['size'] == size]
            if size_results:
                success_count = sum(1 for r in size_results 
                                  if any(s.get('success') for s in r['sources'].values()))
                total_people = sum(r['sources'].get('free_search', {}).get('count', 0) 
                                 for r in size_results)
                avg_people = total_people / len(size_results) if size_results else 0
                
                print(f"  {size.upper()}: {success_count}/{len(size_results)} successful, "
                      f"avg {avg_people:.1f} people/company")
        
        # By source performance
        print("\nSource Performance:")
        source_stats = {}
        
        for result in self.results.values():
            # Free search sources
            free_search = result['sources'].get('free_search', {})
            if free_search.get('people'):
                for person in free_search['people']:
                    source = person['source']
                    source_stats[source] = source_stats.get(source, 0) + 1
            
            # Current system sources
            current = result['sources'].get('current_system', {})
            for source, count in current.get('by_source', {}).items():
                if isinstance(count, int):
                    source_stats[source] = source_stats.get(source, 0) + count
        
        for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count} total results")
        
        # Problem areas
        print("\n⚠️  Problem Areas:")
        failures = []
        for company, result in self.results.items():
            total_found = sum(s.get('count', 0) for s in result['sources'].values() 
                            if isinstance(s, dict))
            if total_found < 5:
                failures.append((company, total_found))
        
        for company, count in sorted(failures, key=lambda x: x[1]):
            print(f"  {company}: only {count} results")
        
        # Save detailed results
        filename = f"free_source_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📁 Detailed results saved to: {filename}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        
        # Check if free search is working
        free_search_total = sum(r['sources'].get('free_search', {}).get('count', 0) 
                               for r in self.results.values())
        
        if free_search_total < 50:
            print("  1. Free search engines are underperforming")
            print("     → Implement Google Custom Search Engine (100 free/day)")
            print("     → Add Bing Search API (1000 free/month)")
            print("     → Fix DuckDuckGo parsing")
        
        # Check small company performance
        small_avg = sum(r['sources'].get('free_search', {}).get('count', 0) 
                       for r in self.results.values() if r['size'] in ['small', 'tiny'])
        small_count = len([r for r in self.results.values() if r['size'] in ['small', 'tiny']])
        
        if small_count > 0 and small_avg / small_count < 10:
            print("  2. Small companies need better coverage")
            print("     → Add GitHub bio search")
            print("     → Search startup databases")
            print("     → Use broader search queries")
        
        print("\n✅ Testing complete!")


def main():
    """Run the comprehensive test."""
    tester = FreeSourceTester()
    tester.test_all()


if __name__ == "__main__":
    main()
