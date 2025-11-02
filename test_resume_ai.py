#!/usr/bin/env python3
"""Test resume parsing with OpenAI AI enhancement"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors.resume_parser import ResumeParser

# Sample resume text for testing
sample_resume = """
JOHN DOE
Software Engineer

EDUCATION
Stanford University - Computer Science, B.S. (2018-2022)
MIT - Summer Research Program (2021)

EXPERIENCE
Software Engineer | Google | 2022 - Present
- Built distributed systems using Go and Python
- Led team of 5 engineers

Software Engineer Intern | Microsoft | 2021
- Developed React applications
- Worked with TypeScript and Node.js

SKILLS
Programming Languages: Python, JavaScript, TypeScript, Go, Java
Frameworks: React, Node.js, Django, Flask
Tools: Docker, Kubernetes, AWS, Git
"""

def main():
    print("=" * 60)
    print("🧪 Testing Resume Parser with OpenAI AI")
    print("=" * 60)
    print()
    
    # Check if OpenAI key is set
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY not set in environment")
        return 1
    
    print(f"✅ OPENAI_API_KEY found: {openai_key[:10]}...")
    print()
    
    # Initialize parser
    print("📝 Initializing ResumeParser...")
    parser = ResumeParser(use_ai=True)
    
    print(f"   AI Enabled: {parser.use_ai}")
    print(f"   Client Available: {parser.client is not None}")
    print()
    
    if not parser.use_ai:
        print("⚠️  AI parsing is disabled. This test won't work properly.")
        print("   Check the initialization logs above for errors.")
        return 1
    
    # Test parsing
    print("🤖 Parsing resume text with AI enhancement...")
    print()
    
    try:
        profile = parser.parse(sample_resume)
        
        print("✅ Parsing complete!")
        print()
        print("📊 Results:")
        print(f"   Schools: {profile.schools}")
        print(f"   Companies: {profile.past_companies}")
        print(f"   Skills: {profile.skills}")
        print(f"   Current Title: {profile.current_title}")
        print()
        
        # Check if results look good
        if len(profile.schools) > 0 and len(profile.past_companies) > 0:
            print("✅ AI parsing appears to be working correctly!")
            return 0
        else:
            print("⚠️  Results seem sparse. Check if AI was actually used.")
            return 1
            
    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

