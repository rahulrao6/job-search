"""Fixed company career and team pages scraper"""

import re
from typing import List, Optional, Dict, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter


class CompanyPagesScraper:
    """
    FIXED: Company website scraper that finds people on team pages.
    
    Searches common page patterns:
    - /team, /about/team, /leadership
    - /people, /our-team, /careers
    - Extracts names, titles, LinkedIn URLs
    """
    
    def __init__(self):
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure("company_pages", requests_per_second=1)
        
        # Common URL patterns to check
        self.page_patterns = [
            "/team",
            "/about/team",
            "/about/leadership",
            "/leadership",
            "/people",
            "/our-team",
            "/company/team",
            "/careers/team",
            "/about-us/team",
        ]
        
        # Keywords for categorization
        self.leadership_keywords = [
            "ceo", "cto", "cfo", "coo", "president", "founder", "co-founder",
            "vice president", "vp", "director", "head of", "chief", "executive"
        ]
        
        self.manager_keywords = [
            "manager", "lead", "senior manager", "team lead", "department head",
            "program manager", "product manager", "engineering manager"
        ]
        
        self.recruiter_keywords = [
            "recruiter", "talent", "hr", "human resources", "people operations",
            "talent acquisition", "people partner", "hiring"
        ]
    
    def search_people(self, company: str, title: str, company_domain: Optional[str] = None, **kwargs) -> List[Person]:
        """
        Search company website for team members.
        
        Args:
            company: Company name
            title: Job title (for context)
            company_domain: Company domain (e.g., "google.com")
        
        Returns:
            List of Person objects
        """
        if not company_domain:
            # Try to guess domain from company name
            company_domain = self._guess_domain(company)
            if not company_domain:
                print(f"⚠️  No domain provided for {company}")
                return []
        
        print(f"🔍 Scraping {company_domain} team pages...")
        
        people = []
        for pattern in self.page_patterns:
            url = f"https://{company_domain}{pattern}"
            
            try:
                # Rate limit
                self.rate_limiter.wait_if_needed("company_pages")
                
                # Fetch page
                response = self.http_client.get(url, timeout=10)
                if response.status_code != 200:
                    continue
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract people from page
                page_people = self._extract_people_from_page(soup, company, url)
                people.extend(page_people)
                
                if page_people:
                    print(f"  ✓ Found {len(page_people)} people on {pattern}")
                
            except Exception as e:
                # Silent fail - just skip this page
                continue
        
        # Deduplicate by name
        unique_people = self._deduplicate(people)
        
        if unique_people:
            print(f"✓ Company pages found {len(unique_people)} people")
        else:
            print(f"⚠️  No people found on company pages")
        
        return unique_people
    
    def _extract_people_from_page(self, soup: BeautifulSoup, company: str, page_url: str) -> List[Person]:
        """Extract people from a team page"""
        people = []
        
        # Strategy 1: Look for structured team member cards/sections
        team_selectors = [
            'div.team-member',
            'div.person',
            'div.employee',
            'article.team',
            'div[class*="team"]',
            'div[class*="person"]',
            'div[class*="member"]',
        ]
        
        for selector in team_selectors:
            cards = soup.select(selector)
            for card in cards:
                person = self._extract_person_from_card(card, company, page_url)
                if person:
                    people.append(person)
        
        # Strategy 2: Look for name + title patterns in text
        if not people:
            people = self._extract_from_text_patterns(soup, company, page_url)
        
        return people
    
    def _extract_person_from_card(self, card, company: str, page_url: str) -> Optional[Person]:
        """Extract person info from a team member card"""
        # Find name
        name = None
        name_selectors = ['h2', 'h3', 'h4', '.name', '[class*="name"]', 'strong']
        for selector in name_selectors:
            elem = card.select_one(selector)
            if elem and len(elem.get_text(strip=True)) > 2:
                name = elem.get_text(strip=True)
                break
        
        if not name:
            return None
        
        # Find title
        title = None
        title_selectors = ['.title', '.role', '.position', '[class*="title"]', '[class*="role"]', 'p']
        for selector in title_selectors:
            elem = card.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                # Check if it looks like a title (not too long)
                if text and len(text) < 100 and text != name:
                    title = text
                    break
        
        # Find LinkedIn URL
        linkedin_url = None
        links = card.find_all('a', href=True)
        for link in links:
            href = link['href']
            if 'linkedin.com/in/' in href:
                linkedin_url = href
                break
        
        # Create person
        return Person(
            name=name,
            title=title,
            company=company,
            linkedin_url=linkedin_url,
            source="company_pages",
            evidence_url=page_url,
            category=self._categorize(title) if title else PersonCategory.UNKNOWN,
            confidence_score=0.7 if linkedin_url else 0.5
        )
    
    def _extract_from_text_patterns(self, soup: BeautifulSoup, company: str, page_url: str) -> List[Person]:
        """Fallback: Extract from text patterns like 'John Doe, CEO'"""
        people = []
        
        # Get all text
        text = soup.get_text()
        
        # Pattern: Name, Title or Name - Title
        patterns = [
            r'([A-Z][a-z]+ [A-Z][a-z]+)[,\-–—]\s*([A-Z][a-z\s]+(?:Officer|Manager|Director|Engineer|Designer|Developer))',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for name, title in matches:
                if len(name) > 5 and len(title) > 3:
                    person = Person(
                        name=name.strip(),
                        title=title.strip(),
                        company=company,
                        source="company_pages",
                        evidence_url=page_url,
                        category=self._categorize(title),
                        confidence_score=0.4  # Lower confidence for text extraction
                    )
                    people.append(person)
        
        return people
    
    def _categorize(self, title: str) -> PersonCategory:
        """Categorize person by title"""
        if not title:
            return PersonCategory.UNKNOWN
        
        title_lower = title.lower()
        
        # Check for recruiter
        if any(keyword in title_lower for keyword in self.recruiter_keywords):
            return PersonCategory.RECRUITER
        
        # Check for manager/leadership
        if any(keyword in title_lower for keyword in self.manager_keywords + self.leadership_keywords):
            return PersonCategory.MANAGER
        
        # Check for senior
        if 'senior' in title_lower or 'sr.' in title_lower or 'lead' in title_lower:
            return PersonCategory.SENIOR
        
        return PersonCategory.UNKNOWN
    
    def _deduplicate(self, people: List[Person]) -> List[Person]:
        """Remove duplicates by name"""
        seen = set()
        unique = []
        
        for person in people:
            key = person.name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(person)
        
        return unique
    
    def _guess_domain(self, company: str) -> Optional[str]:
        """Guess company domain from name"""
        # Common company domain mappings
        domain_map = {
            "google": "google.com",
            "meta": "meta.com",
            "facebook": "meta.com",
            "amazon": "amazon.com",
            "apple": "apple.com",
            "microsoft": "microsoft.com",
            "netflix": "netflix.com",
            "tesla": "tesla.com",
            "twitter": "twitter.com",
            "x": "x.com",
            "linkedin": "linkedin.com",
            "uber": "uber.com",
            "airbnb": "airbnb.com",
            "stripe": "stripe.com",
            "spotify": "spotify.com",
            "snapchat": "snap.com",
            "pinterest": "pinterest.com",
            "reddit": "reddit.com",
            "discord": "discord.com",
            "slack": "slack.com",
            "zoom": "zoom.us",
            "salesforce": "salesforce.com",
            "oracle": "oracle.com",
            "ibm": "ibm.com",
            "adobe": "adobe.com",
            "nvidia": "nvidia.com",
            "intel": "intel.com",
            "amd": "amd.com",
            "cisco": "cisco.com",
        }
        
        company_lower = company.lower().strip()
        return domain_map.get(company_lower)

