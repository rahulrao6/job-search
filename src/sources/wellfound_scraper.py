"""Scrape AngelList/Wellfound for startup employees"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter


class WellfoundScraper:
    """
    Scrape Wellfound (formerly AngelList) for startup employees.
    
    Good for startups and tech companies.
    100% free, no API needed.
    """
    
    def __init__(self):
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure("wellfound", requests_per_second=0.5)
    
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search Wellfound for company employees.
        
        Args:
            company: Company name
            title: Job title
        
        Returns:
            List of Person objects
        """
        people = []
        
        # Try to find company page
        company_slug = self._get_company_slug(company)
        if not company_slug:
            print(f"⚠️  Company '{company}' not found on Wellfound")
            return []
        
        self.rate_limiter.wait_if_needed("wellfound")
        
        try:
            # Access company page
            url = f"https://wellfound.com/company/{company_slug}"
            response = self.http_client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find team section
            people = self._extract_team_members(soup, company, url)
            
            if people:
                print(f"✓ Wellfound found {len(people)} people")
            else:
                print(f"⚠️  No people found on Wellfound for {company}")
            
        except Exception as e:
            print(f"⚠️  Wellfound error: {e}")
        
        return people
    
    def _get_company_slug(self, company: str) -> Optional[str]:
        """Get Wellfound company slug"""
        # Clean company name
        slug = company.lower()
        slug = re.sub(r'\s+(inc|llc|ltd|corp|corporation)\.?$', '', slug)
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        
        # Try to verify it exists
        try:
            self.rate_limiter.wait_if_needed("wellfound")
            response = self.http_client.get(
                f"https://wellfound.com/company/{slug}",
                timeout=10
            )
            if response.status_code == 200:
                return slug
        except:
            pass
        
        return None
    
    def _extract_team_members(self, soup, company: str, url: str) -> List[Person]:
        """Extract team members from company page"""
        people = []
        
        # Look for team/people sections
        team_sections = soup.find_all(['div', 'section'], class_=re.compile(r'(team|people|member)'))
        
        for section in team_sections:
            # Find person cards
            cards = section.find_all(['div', 'article'], recursive=True)
            
            for card in cards:
                person = self._parse_person_card(card, company, url)
                if person:
                    people.append(person)
        
        return people
    
    def _parse_person_card(self, card, company: str, url: str) -> Optional[Person]:
        """Parse a person card"""
        try:
            # Find name
            name_elem = card.find(['h3', 'h4', 'a'], class_=re.compile(r'name'))
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            # Find title/role
            title_elem = card.find(['span', 'p'], class_=re.compile(r'(title|role)'))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Find LinkedIn if available
            linkedin_link = card.find('a', href=re.compile(r'linkedin\.com'))
            linkedin_url = linkedin_link.get('href') if linkedin_link else None
            
            if name and len(name) > 2:
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    linkedin_url=linkedin_url,
                    source="wellfound",
                    evidence_url=url,
                    confidence_score=0.7,
                )
        
        except Exception as e:
            pass
        
        return None

