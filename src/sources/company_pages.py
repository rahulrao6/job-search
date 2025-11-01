"""Scrape company career and team pages"""

import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter


class CompanyPagesScraper:
    """
    Scrape company websites for employee information.
    
    Target pages:
    - Team/About pages
    - Leadership pages
    - Job postings (hiring manager names)
    """
    
    def __init__(self):
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure("company_pages", requests_per_second=2)
    
    def search_people(self, company: str, title: str, company_domain: Optional[str] = None, **kwargs) -> List[Person]:
        """
        Search for people on company website.
        
        Args:
            company: Company name
            title: Job title to search for
            company_domain: Company website domain (e.g., "meta.com")
        
        Returns:
            List of Person objects
        """
        if not company_domain:
            # Try to guess domain
            company_domain = self._guess_domain(company)
        
        if not company_domain:
            print(f"⚠️  No domain provided for {company}, skipping company pages")
            return []
        
        people = []
        
        # Try common team/about page paths
        team_paths = [
            "/team",
            "/about/team",
            "/about-us",
            "/leadership",
            "/about/leadership",
            "/company/team",
            "/people",
        ]
        
        for path in team_paths:
            self.rate_limiter.wait_if_needed("company_pages")
            
            try:
                url = f"https://{company_domain}{path}"
                response = self.http_client.get(url)
                
                page_people = self._extract_people_from_page(
                    response.text, company, url
                )
                people.extend(page_people)
                
                if page_people:
                    print(f"✓ Found {len(page_people)} people on {path}")
                    break  # Found a good page, don't need to check others
                    
            except Exception as e:
                # Page doesn't exist or error - continue to next path
                continue
        
        if people:
            print(f"✓ Company pages found {len(people)} people")
        else:
            print(f"⚠️  No people found on company pages for {company}")
        
        return people
    
    def _guess_domain(self, company: str) -> Optional[str]:
        """Try to guess company domain from name"""
        # Clean company name
        clean = company.lower()
        clean = re.sub(r'\s+(inc|llc|ltd|corp|corporation)\.?$', '', clean)
        clean = re.sub(r'[^a-z0-9]', '', clean)
        
        # Common company domain patterns
        guesses = [
            f"{clean}.com",
            f"{clean}.io",
        ]
        
        # Try to verify domain exists
        for domain in guesses:
            try:
                response = self.http_client.get(f"https://{domain}", timeout=5)
                if response.status_code == 200:
                    return domain
            except:
                continue
        
        return None
    
    def _extract_people_from_page(self, html: str, company: str, url: str) -> List[Person]:
        """Extract people names and titles from a team page"""
        soup = BeautifulSoup(html, 'html.parser')
        people = []
        
        # Look for common patterns for team member cards
        # Pattern 1: div/article with person info
        containers = soup.find_all(['div', 'article', 'section'], 
                                   class_=re.compile(r'(team|member|person|employee|profile)', re.I))
        
        for container in containers:
            person = self._extract_person_from_container(container, company, url)
            if person:
                people.append(person)
        
        # Pattern 2: Structured lists
        # Look for name-title pairs in lists
        if not people:
            people = self._extract_from_lists(soup, company, url)
        
        return people
    
    def _extract_person_from_container(self, container, company: str, url: str) -> Optional[Person]:
        """Extract person info from a container element"""
        try:
            # Find name (usually in h2, h3, h4, or strong)
            name_elem = container.find(['h2', 'h3', 'h4', 'h5', 'strong', 'span'], 
                                       class_=re.compile(r'name', re.I))
            if not name_elem:
                name_elem = container.find(['h2', 'h3', 'h4', 'h5'])
            
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            # Find title (usually nearby or in class with "title" or "role")
            title_elem = container.find(['p', 'span', 'div'], 
                                       class_=re.compile(r'(title|role|position)', re.I))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Find LinkedIn if available
            linkedin_url = None
            linkedin_link = container.find('a', href=re.compile(r'linkedin\.com'))
            if linkedin_link:
                linkedin_url = linkedin_link.get('href')
            
            if name and len(name) > 2 and len(name) < 100:
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    linkedin_url=linkedin_url,
                    source="company_pages",
                    evidence_url=url,
                )
        except Exception as e:
            pass
        
        return None
    
    def _extract_from_lists(self, soup, company: str, url: str) -> List[Person]:
        """Extract people from list structures"""
        people = []
        
        # Find all text that looks like "Name - Title" or "Name, Title"
        text = soup.get_text()
        
        # Pattern: Name followed by dash or comma and title
        pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–—,]\s*([A-Z][a-z\s]+)'
        matches = re.findall(pattern, text)
        
        for name, title in matches[:20]:  # Limit to avoid false positives
            if len(name) > 2 and len(title) > 2:
                people.append(Person(
                    name=name.strip(),
                    title=title.strip(),
                    company=company,
                    source="company_pages",
                    evidence_url=url,
                ))
        
        return people

