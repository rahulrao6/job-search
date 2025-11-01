#!/usr/bin/env python3
"""
Test all configured data sources with a sample job search.

Usage:
    python scripts/test_all_sources.py --company "Meta" --title "Software Engineer"
    python scripts/test_all_sources.py --company "Google" --title "Product Manager" --domain "google.com"
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestrator import ConnectionFinder
from dotenv import load_dotenv
import os

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Debug: Check if env vars are loaded
if os.getenv("APOLLO_API_KEY"):
    print(f"✓ Apollo API key loaded")
if os.getenv("SERP_API_KEY"):
    print(f"✓ SerpAPI key loaded")


def main():
    parser = argparse.ArgumentParser(description="Test connection finder with a job search")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--title", required=True, help="Job title")
    parser.add_argument("--domain", help="Company website domain (optional)")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    parser.add_argument("--output", help="Output file path (default: outputs/results.json)")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize finder
    finder = ConnectionFinder()
    
    # Run search
    results = finder.find_connections(
        company=args.company,
        title=args.title,
        company_domain=args.domain,
        use_cache=not args.no_cache,
    )
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        company_clean = args.company.replace(" ", "_").lower()
        output_path = output_dir / f"results_{company_clean}_{timestamp}.json"
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_path}")
    
    # Also create a readable markdown report
    md_path = output_path.with_suffix('.md')
    create_markdown_report(results, md_path)
    print(f"📄 Markdown report: {md_path}")
    
    # Print top connections
    print_top_connections(results)


def create_markdown_report(results: dict, output_path: Path):
    """Create a markdown report of results"""
    lines = []
    
    lines.append(f"# Connection Finder Results\n")
    lines.append(f"**Company:** {results['company']}\n")
    lines.append(f"**Role:** {results['title']}\n")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Total Found:** {results['total_found']} people\n")
    
    lines.append(f"\n## Summary by Category\n")
    for category, count in results['category_counts'].items():
        if count > 0:
            lines.append(f"- **{category.capitalize()}:** {count}\n")
    
    lines.append(f"\n## Top Connections by Category\n")
    
    for category, people in results['by_category'].items():
        if people:
            lines.append(f"\n### {category.capitalize()} ({len(people)} people)\n")
            
            for i, person in enumerate(people, 1):
                lines.append(f"\n#### {i}. {person['name']}\n")
                lines.append(f"- **Title:** {person.get('title', 'N/A')}\n")
                if person.get('linkedin_url'):
                    lines.append(f"- **LinkedIn:** {person['linkedin_url']}\n")
                if person.get('email'):
                    lines.append(f"- **Email:** {person['email']}\n")
                lines.append(f"- **Source:** {person['source']}\n")
                lines.append(f"- **Confidence:** {person['confidence']}\n")
    
    lines.append(f"\n## Data Sources Used\n")
    for source, count in results['source_stats']['by_source'].items():
        lines.append(f"- **{source}:** {count} people found\n")
    
    if results['cost_stats']['total_cost'] > 0:
        lines.append(f"\n## Cost\n")
        lines.append(f"Total API cost: ${results['cost_stats']['total_cost']:.4f}\n")
    
    with open(output_path, 'w') as f:
        f.writelines(lines)


def print_top_connections(results: dict):
    """Print top connections to console"""
    print("\n" + "=" * 60)
    print("🎯 TOP CONNECTIONS TO REACH OUT TO")
    print("=" * 60)
    
    priorities = ['manager', 'recruiter', 'senior', 'peer']
    
    for category in priorities:
        people = results['by_category'].get(category, [])
        
        if people:
            emoji = {
                'manager': '👔',
                'recruiter': '🎯',
                'senior': '⭐',
                'peer': '👥',
            }.get(category, '•')
            
            print(f"\n{emoji} {category.upper()}")
            print("-" * 60)
            
            for i, person in enumerate(people[:3], 1):  # Top 3 per category
                print(f"{i}. {person['name']}")
                if person.get('title'):
                    print(f"   {person['title']}")
                if person.get('linkedin_url'):
                    print(f"   🔗 {person['linkedin_url']}")
                if person.get('email'):
                    print(f"   ✉️  {person['email']}")
                print(f"   Source: {person['source']} | Confidence: {person['confidence']}")
                print()


if __name__ == "__main__":
    main()

