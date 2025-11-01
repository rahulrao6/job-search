"""Advanced company career and team pages scraper"""

import re
from typing import List, Optional, Dict, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter
# from src.utils.smart_domain_detector import detect_company_domain, get_company_info


class CompanyPagesScraper:
    """
    Advanced company website scraper that finds:
    - Leadership teams (CEOs, VPs, Directors)
    - Department heads (Engineering, Product, Sales)
    - Team pages with employee listings  
    - Job posting contacts (hiring managers)
    - About pages with executive profiles
    
    Uses intelligent parsing with multiple extraction strategies.
    """
    
    def __init__(self):
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure("company_pages", requests_per_second=1)  # Be respectful
        
        # Enhanced patterns for different types of people
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
        Advanced search for people on company website.
        
        Args:
            company: Company name
            title: Job title to search for
            company_domain: Company website domain (e.g., "meta.com")
        
        Returns:
            List of Person objects
        """
        # Smart domain detection
        if not company_domain:
            company_domain = detect_company_domain(company, use_web_search=False)
        
        if not company_domain:
            print(f"⚠️  Could not detect domain for {company}")
            return []
        
        # Get comprehensive company information
        company_info = get_company_info(company, company_domain)
        
        print(f"ℹ️  Searching {company_domain} ({company_info['type']} company)")
        
        all_people = set()  # Use set to avoid duplicates
        
        # Strategy 1: Use known career page URLs if available
        if company_info["career_page_urls"]:
            for url in company_info["career_page_urls"][:3]:  # Max 3 career pages
                people = self._scrape_career_page(url, company)
                all_people.update(people)
        
        # Strategy 2: Try common team/leadership pages
        team_people = self._scrape_team_pages(company_domain, company)
        all_people.update(team_people)
        
        # Strategy 3: Look for specific role-related pages
        role_people = self._scrape_role_specific_pages(company_domain, company, title)
        all_people.update(role_people)
        
        # Convert set back to list
        final_people = list(all_people)
        
        if final_people:
            print(f"✓ Company pages found {len(final_people)} people")
            return self._rank_and_filter_people(final_people, title)
        else:
            print(f"⚠️  No people found on company pages for {company}")
            return []
    
    def _scrape_team_pages(self, domain: str, company: str) -> Set[Person]:
        """Scrape team/leadership pages"""
        people = set()
        
        # Comprehensive list of team page paths
        team_paths = [
            "/team", "/about/team", "/company/team", "/our-team",
            "/leadership", "/about/leadership", "/company/leadership", "/executives",
            "/about", "/about-us", "/company/about",
            "/people", "/company/people", "/our-people",
            "/management", "/company/management",
            "/board", "/board-of-directors", "/advisory-board",
            "/founders", "/company/founders"
        ]
        
        for path in team_paths:
            self.rate_limiter.wait_if_needed("company_pages")
            
            try:
                url = f"https://{domain}{path}"
                response = self.http_client.get(url, timeout=10)
                
                if response.status_code == 200:
                    page_people = self._extract_people_from_page(response.text, company, url)
                    if page_people:
                        people.update(page_people)
                        print(f"✓ Found {len(page_people)} people on {path}")
                        
                        # If we found a lot of people, this is probably the main team page
                        if len(page_people) >= 10:
                            break
                            
            except Exception as e:
                continue
        
        return people
    
    def _scrape_role_specific_pages(self, domain: str, company: str, title: str) -> Set[Person]:
        """Look for pages specific to the role being searched"""
        people = set()
        
        # Generate role-specific paths
        role_paths = []
        
        if "engineer" in title.lower() or "developer" in title.lower():
            role_paths.extend([
                "/engineering", "/engineering/team", "/dev-team",
                "/technology", "/tech-team", "/developers"
            ])
        
        if "product" in title.lower():
            role_paths.extend([
                "/product", "/product/team", "/product-team"
            ])
        
        if "sales" in title.lower() or "business" in title.lower():
            role_paths.extend([
                "/sales", "/sales/team", "/business-development"
            ])
        
        if "marketing" in title.lower():
            role_paths.extend([
                "/marketing", "/marketing/team"
            ])
        
        for path in role_paths:
            self.rate_limiter.wait_if_needed("company_pages")
            
            try:
                url = f"https://{domain}{path}"
                response = self.http_client.get(url, timeout=10)
                
                if response.status_code == 200:
                    page_people = self._extract_people_from_page(response.text, company, url)
                    if page_people:
                        people.update(page_people)
                        print(f"✓ Found {len(page_people)} people on role page {path}")
                        
            except Exception as e:
                continue
        
        return people
    
    def _scrape_career_page(self, url: str, company: str) -> Set[Person]:
        """Scrape a specific career page"""
        people = set()
        
        self.rate_limiter.wait_if_needed("company_pages")
        
        try:
            response = self.http_client.get(url, timeout=10)
            if response.status_code == 200:
                page_people = self._extract_people_from_page(response.text, company, url)
                if page_people:
                    people.update(page_people)
                    print(f"✓ Found {len(page_people)} people on career page")
                    
        except Exception as e:
            print(f"⚠️  Error scraping career page {url}: {e}")
        
        return people
    
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

