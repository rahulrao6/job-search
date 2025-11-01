#!/usr/bin/env python3
"""
Demo of the working job referral connection finder system.

This shows how the system finds LinkedIn profiles and other connections
for job seekers, completely FREE without expensive APIs.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.orchestrator import ConnectionFinder
from dotenv import load_dotenv

load_dotenv()


def demo_connection_finder():
    """Demo the complete connection finding system"""
    
    print("🚀 JOB REFERRAL CONNECTION FINDER - WORKING DEMO")
    print("="*80)
    print("This system finds recruiters, managers, and other connections at companies")
    print("for job referrals - completely FREE, no expensive APIs needed!")
    print("="*80)
    
    # Initialize the finder
    finder = ConnectionFinder()
    
    # Demo companies and roles
    demo_searches = [
        {
            "company": "Google",
            "role": "Software Engineer",
            "description": "Entry-level software engineering position"
        },
        {
            "company": "Amazon", 
            "role": "Product Manager",
            "description": "Product management role"
        },
        {
            "company": "Microsoft",
            "role": "Data Analyst", 
            "description": "Data analytics position"
        },
        {
            "company": "Apple",
            "role": "UX Designer",
            "description": "User experience design role"
        }
    ]
    
    for search in demo_searches:
        print(f"\n{'='*70}")
        print(f"🏢 Company: {search['company']}")
        print(f"💼 Role: {search['role']}")
        print(f"📝 Description: {search['description']}")
        print('='*70)
        
        # Find connections
        results = finder.find_connections(
            company=search['company'],
            title=search['role']
        )
        
        # Extract key information
        total_found = results.get('total_found', 0)
        by_category = results.get('by_category', {})
        source_stats = results.get('source_stats', {})
        
        print(f"\n✅ Found {total_found} potential connections!")
        
        # Show top connections by category
        print("\n🎯 TOP CONNECTIONS TO REACH OUT TO:")
        
        categories_shown = 0
        for category in ['recruiter', 'manager', 'senior', 'peer']:
            people = by_category.get(category, [])
            if people and categories_shown < 3:  # Show up to 3 categories
                print(f"\n{category.upper()}S:")
                for i, person in enumerate(people[:2], 1):  # Top 2 per category
                    print(f"  {i}. {person['name']} - {person['title']}")
                    print(f"     LinkedIn: {person['linkedin_url']}")
                    
                    # Show why they're a good connection
                    if category == 'recruiter':
                        print(f"     💡 Recruiters can directly refer you!")
                    elif category == 'manager':
                        print(f"     💡 Managers make hiring decisions!")
                    elif category == 'peer':
                        print(f"     💡 Peers can provide insider referrals!")
                        
                categories_shown += 1
        
        # Show sources used
        print(f"\n📊 Data sources used:")
        for source, stats in source_stats.items():
            if isinstance(stats, dict) and stats.get('total', 0) > 0:
                print(f"  • {source}: {stats['unique']} profiles")
            elif isinstance(stats, int) and stats > 0:
                print(f"  • {source}: {stats} profiles")
    
    # Final summary
    print("\n" + "="*80)
    print("🎉 HOW THIS HELPS YOU:")
    print("="*80)
    print("1. 🎯 TARGETED OUTREACH: Connect with the RIGHT people who can refer you")
    print("2. 💰 COMPLETELY FREE: No expensive LinkedIn Sales Navigator or APIs needed")  
    print("3. 📈 HIGHER SUCCESS: Referrals have 10x higher success rate than cold applications")
    print("4. 🚀 FAST RESULTS: Get connections in seconds, not hours of manual searching")
    
    print("\n💡 NEXT STEPS:")
    print("1. Pick your top 5 connections from the results")
    print("2. Send personalized LinkedIn connection requests")
    print("3. Mention specific things about their background")
    print("4. Ask for a quick chat about the role")
    print("5. Get that referral!")
    
    print("\n✅ Demo complete! The system works with ANY company and role.")


if __name__ == "__main__":
    demo_connection_finder()
