"""Scrape Crunchbase for company leadership"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter


class CrunchbaseScraper:
    """
    Scrape Crunchbase for company leadership and employee data.
    
    Crunchbase shows leadership, founders, and key employees publicly.
    Particularly good for startups and public companies.
    """
    
    def __init__(self):
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure("crunchbase", requests_per_second=0.5)
    
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search Crunchbase for people at a company.
        
        Args:
            company: Company name
            title: Job title to filter for
        
        Returns:
            List of Person objects
        """
        people = []
        
        # Get company permalink
        company_permalink = self._get_company_permalink(company)
        if not company_permalink:
            print(f"⚠️  Company '{company}' not found on Crunchbase")
            return []
        
        # Scrape company page for people
        people = self._scrape_company_people(company_permalink, company)
        
        if people:
            print(f"✓ Crunchbase found {len(people)} people")
        else:
            print(f"⚠️  No people found on Crunchbase for {company}")
        
        return people
    
    def _get_company_permalink(self, company: str) -> Optional[str]:
        """Get Crunchbase permalink for company"""
        self.rate_limiter.wait_if_needed("crunchbase")
        
        # Known company permalink mappings
        permalink_map = {
            "meta": "meta-platforms",
            "facebook": "meta-platforms",
            "meta platforms": "meta-platforms",
            "google": "google",
            "alphabet": "google",
            "microsoft": "microsoft",
            "amazon": "amazon",
            "apple": "apple",
        }
        
        company_lower = company.lower().strip()
        if company_lower in permalink_map:
            return permalink_map[company_lower]
        
        try:
            # Clean company name for URL
            clean = company.lower()
            clean = re.sub(r'\s+(inc|llc|ltd|corp|corporation)\.?$', '', clean)
            clean = re.sub(r'[^a-z0-9]+', '-', clean)
            clean = clean.strip('-')
            
            # Try to access company page
            url = f"https://www.crunchbase.com/organization/{clean}"
            response = self.http_client.get(url)
            
            if response.status_code == 200:
                return clean
        
        except Exception as e:
            pass
        
        return None
    
    def _scrape_company_people(self, permalink: str, company: str) -> List[Person]:
        """Scrape people from company Crunchbase page"""
        people = []
        
        self.rate_limiter.wait_if_needed("crunchbase")
        
        try:
            url = f"https://www.crunchbase.com/organization/{permalink}"
            response = self.http_client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Crunchbase shows leadership in specific sections
            # Look for team/people sections
            
            # Pattern 1: Leadership cards
            person_cards = soup.find_all(['div', 'article'], 
                                        class_=re.compile(r'(person|employee|team-member)', re.I))
            
            for card in person_cards:
                person = self._parse_person_card(card, company, url)
                if person:
                    people.append(person)
            
            # Pattern 2: Structured lists with "Board Members and Advisors" section
            if not people:
                people = self._parse_people_lists(soup, company, url)
        
        except Exception as e:
            print(f"⚠️  Crunchbase scraping error: {e}")
        
        return people
    
    def _parse_person_card(self, card, company: str, evidence_url: str) -> Optional[Person]:
        """Parse a person from a card element"""
        try:
            # Find name
            name_elem = card.find(['h3', 'h4', 'a'], class_=re.compile(r'name', re.I))
            if not name_elem:
                name_elem = card.find('a', href=re.compile(r'/person/'))
            
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            # Find title
            title_elem = card.find(['span', 'p'], class_=re.compile(r'(title|role|position)', re.I))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Find LinkedIn if available
            linkedin_link = card.find('a', href=re.compile(r'linkedin\.com'))
            linkedin_url = linkedin_link.get('href') if linkedin_link else None
            
            if name and len(name) > 2:
                # Categorize based on title
                category = PersonCategory.UNKNOWN
                if title:
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ['ceo', 'founder', 'president', 'director', 'vp', 'head']):
                        category = PersonCategory.MANAGER
                
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    linkedin_url=linkedin_url,
                    source="crunchbase",
                    category=category,
                    evidence_url=evidence_url,
                )
        
        except Exception as e:
            pass
        
        return None
    
    def _parse_people_lists(self, soup, company: str, evidence_url: str) -> List[Person]:
        """Parse people from list structures"""
        people = []
        
        # Find links to person profiles
        person_links = soup.find_all('a', href=re.compile(r'/person/[^/]+$'))
        
        for link in person_links[:30]:  # Limit results
            try:
                name = link.get_text(strip=True)
                
                # Find associated title (usually nearby)
                parent = link.find_parent(['div', 'li', 'tr'])
                title = None
                
                if parent:
                    # Look for title in parent
                    title_elem = parent.find(['span', 'p'], class_=re.compile(r'(title|role)', re.I))
                    if not title_elem:
                        # Look for text after the link
                        text = parent.get_text(strip=True)
                        # Remove name from text to get title
                        text = text.replace(name, '').strip(' ,-')
                        if text and len(text) < 100:
                            title = text
                    else:
                        title = title_elem.get_text(strip=True)
                
                if name and len(name) > 2:
                    people.append(Person(
                        name=name,
                        title=title,
                        company=company,
                        source="crunchbase",
                        evidence_url=evidence_url,
                    ))
            
            except Exception as e:
                continue
        
        return people

