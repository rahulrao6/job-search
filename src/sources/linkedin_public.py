"""LinkedIn public profile scraper with anti-detection"""

import asyncio
import re
import os
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.stealth_browser import create_stealth_browser
from src.utils.rate_limiter import get_rate_limiter
from src.utils.proxy_manager import get_proxy_manager


class LinkedInPublicScraper:
    """
    Scrape LinkedIn public profiles with anti-detection.
    
    ⚠️ WARNING: This violates LinkedIn ToS and may result in account bans.
    Use at your own risk. Recommended to skip unless absolutely necessary.
    
    Safety measures:
    - Very conservative rate limiting (1 request per 5 seconds)
    - Stealth browser
    - Proxy rotation
    - Random delays
    """
    
    def __init__(self):
        self.rate_limiter = get_rate_limiter()
        self.proxy_manager = get_proxy_manager()
        
        # Very conservative rate limiting
        self.rate_limiter.configure(
            "linkedin_public",
            requests_per_second=0.2,  # 1 per 5 seconds
            max_per_hour=50  # Hard limit
        )
        
        # Load cookies if available
        self.cookies = self._load_cookies()
    
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search LinkedIn for people (async wrapper).
        
        ⚠️ Use with caution - violates LinkedIn ToS
        """
        print("⚠️  LinkedIn scraping disabled by default (violates ToS)")
        print("⚠️  Use Apollo.io or Google SERP instead")
        
        # Disabled by default - too risky and not working properly
        return []
        
        # Uncomment below to enable (not recommended):
        # return asyncio.run(self._search_people_async(company, title, **kwargs))
    
    async def _search_people_async(self, company: str, title: str, **kwargs) -> List[Person]:
        """Async implementation of LinkedIn search"""
        people = []
        
        # Get proxy if available
        proxy = self.proxy_manager.get_proxy() if self.proxy_manager.is_configured() else None
        
        async with create_stealth_browser(headless=True, proxy=proxy) as browser:
            page = await browser.new_page()
            
            # Set cookies if available
            if self.cookies:
                await browser.set_cookies(self.cookies)
            
            try:
                # Search for company page first
                company_slug = self._get_company_slug(company)
                
                if company_slug:
                    # Scrape company page for employees
                    people = await self._scrape_company_people(browser, page, company_slug, company, title)
                
                if not people:
                    # Fallback: try search
                    people = await self._search_people_direct(browser, page, company, title)
                
            except Exception as e:
                print(f"⚠️  LinkedIn scraping error: {e}")
        
        if people:
            print(f"✓ LinkedIn found {len(people)} people (⚠️ ToS violation)")
        
        return people
    
    async def _scrape_company_people(self, browser, page, company_slug: str, company: str, title: str) -> List[Person]:
        """Scrape people from company page"""
        people = []
        
        # Navigate to company people page
        url = f"https://www.linkedin.com/company/{company_slug}/people/"
        
        self.rate_limiter.wait_if_needed("linkedin_public")
        await browser.goto(page, url)
        
        # Check if we're blocked or need login
        content = await page.content()
        
        if "authwall" in content.lower() or "login" in page.url:
            print("⚠️  LinkedIn requires authentication - skipping")
            return []
        
        # Parse page
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find employee cards
        # LinkedIn structure changes frequently - try multiple selectors
        cards = soup.find_all(['li', 'div'], class_=re.compile(r'(org-people|people-card)'))
        
        for card in cards[:20]:  # Limit results
            person = self._parse_person_card(card, company)
            if person:
                people.append(person)
        
        return people
    
    async def _search_people_direct(self, browser, page, company: str, title: str) -> List[Person]:
        """Direct LinkedIn search"""
        people = []
        
        # Build search URL
        query = f"{title} {company}"
        url = f"https://www.linkedin.com/search/results/people/?keywords={query}"
        
        self.rate_limiter.wait_if_needed("linkedin_public")
        await browser.goto(page, url)
        
        # Check auth
        content = await page.content()
        
        if "authwall" in content.lower() or "login" in page.url:
            print("⚠️  LinkedIn requires authentication - skipping")
            return []
        
        # Parse results
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find result cards
        cards = soup.find_all(['li', 'div'], class_=re.compile(r'(search-result|entity-result)'))
        
        for card in cards[:20]:
            person = self._parse_person_card(card, company)
            if person:
                people.append(person)
        
        return people
    
    def _parse_person_card(self, card, company: str) -> Optional[Person]:
        """Parse a person from a card element"""
        try:
            # Find profile link
            link = card.find('a', href=re.compile(r'/in/[^/]+'))
            if not link:
                return None
            
            profile_url = link.get('href')
            
            # Clean URL (remove query params)
            if '?' in profile_url:
                profile_url = profile_url.split('?')[0]
            
            # Make absolute
            if not profile_url.startswith('http'):
                profile_url = f"https://www.linkedin.com{profile_url}"
            
            # Find name
            name_elem = card.find(['span', 'div'], class_=re.compile(r'(name|actor)'))
            if not name_elem:
                name_elem = link
            
            name = name_elem.get_text(strip=True)
            
            # Find title
            title_elem = card.find(['div', 'p'], class_=re.compile(r'(occupation|headline)'))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if name and len(name) > 2:
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    linkedin_url=profile_url,
                    source="linkedin_public",
                    evidence_url=profile_url,
                )
        
        except Exception as e:
            pass
        
        return None
    
    def _get_company_slug(self, company: str) -> Optional[str]:
        """Try to guess LinkedIn company slug"""
        # Clean company name
        clean = company.lower()
        clean = re.sub(r'\s+(inc|llc|ltd|corp|corporation)\.?$', '', clean)
        clean = re.sub(r'[^a-z0-9]+', '-', clean)
        clean = clean.strip('-')
        
        return clean
    
    def _load_cookies(self) -> Optional[List[dict]]:
        """Load LinkedIn cookies from environment"""
        cookie_str = os.getenv("LINKEDIN_COOKIES", "")
        
        if not cookie_str:
            return None
        
        try:
            # Parse cookie string
            # Format: li_at=value or JSON array
            if cookie_str.startswith('['):
                # JSON format
                return json.loads(cookie_str)
            else:
                # Simple key=value format
                cookies = []
                for pair in cookie_str.split(';'):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        cookies.append({
                            "name": key.strip(),
                            "value": value.strip(),
                            "domain": ".linkedin.com",
                            "path": "/",
                        })
                return cookies
        
        except Exception as e:
            print(f"⚠️  Failed to parse LinkedIn cookies: {e}")
            return None

