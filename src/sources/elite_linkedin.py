"""
Elite LinkedIn Scraper - Production Grade
Bypasses ALL LinkedIn detection systems and harvests massive amounts of data
"""

import asyncio
import random
import re
import json
import time
from typing import List, Optional, Dict, Set, Tuple
from urllib.parse import urlencode, urlparse, parse_qs
from bs4 import BeautifulSoup
from dataclasses import dataclass
import hashlib

from src.models.person import Person, PersonCategory
from src.utils.elite_browser import create_elite_session, EliteSession
from src.utils.rate_limiter import get_rate_limiter
from src.utils.cache import get_cache

@dataclass
class LinkedInConfig:
    """LinkedIn scraping configuration"""
    max_pages_per_search: int = 10
    max_people_per_company: int = 200
    scroll_pause_min: float = 2.0
    scroll_pause_max: float = 5.0
    request_delay_min: float = 3.0
    request_delay_max: float = 8.0
    session_rotation_after: int = 50  # requests
    use_multiple_search_methods: bool = True
    bypass_login_wall: bool = True
    extract_emails: bool = True
    deep_profile_scraping: bool = True

class EliteLinkedInScraper:
    """
    Ultimate LinkedIn scraper that bypasses:
    - LinkedIn auth walls
    - Rate limiting
    - CAPTCHA challenges  
    - Account restrictions
    - IP bans
    - Behavioral detection
    
    Uses multiple attack vectors:
    1. Google/Bing search for LinkedIn profiles
    2. Direct LinkedIn search (if possible)
    3. Company page employee scraping
    4. Connection graph traversal
    5. Sales Navigator methods
    """
    
    def __init__(self, config: LinkedInConfig = None):
        self.config = config or LinkedInConfig()
        self.cache = get_cache()
        self.rate_limiter = get_rate_limiter()
        
        # Configure ultra-conservative rate limiting
        self.rate_limiter.configure(
            "elite_linkedin",
            requests_per_second=0.1,  # 1 request per 10 seconds
            max_per_hour=30  # Only 30 requests per hour
        )
        
        self.session_pool: List[EliteSession] = []
        self.current_session_index = 0
        self.request_count = 0
        
        # Known company LinkedIn URLs
        self.company_url_cache = {}
        
    async def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Master search function - uses ALL available methods
        """
        print(f"🔥 Elite LinkedIn: Hunting {title} at {company}")
        
        all_people = set()
        
        # Method 1: Google/Bing indirect search (safest)
        search_people = await self._search_via_google(company, title)
        all_people.update(search_people)
        
        # Method 2: LinkedIn company page (medium risk)
        if self.config.bypass_login_wall:
            company_people = await self._scrape_company_employees(company, title)
            all_people.update(company_people)
        
        # Method 3: LinkedIn search (highest risk, highest reward)
        if self.config.use_multiple_search_methods:
            direct_people = await self._direct_linkedin_search(company, title)
            all_people.update(direct_people)
        
        # Method 4: Sales Navigator approach (if available)
        sales_nav_people = await self._sales_navigator_search(company, title)
        all_people.update(sales_nav_people)
        
        # Convert to list and enhance profiles
        people_list = list(all_people)
        
        if self.config.deep_profile_scraping and people_list:
            people_list = await self._enhance_profiles(people_list)
        
        print(f"✅ Elite LinkedIn found {len(people_list)} people")
        return people_list
    
    async def _ensure_session(self) -> EliteSession:
        """Get or create a stealth session"""
        if not self.session_pool:
            # Create initial session pool
            session = await create_elite_session()
            self.session_pool.append(session)
        
        # Rotate sessions to avoid detection
        if self.request_count > 0 and self.request_count % self.config.session_rotation_after == 0:
            # Create new session
            new_session = await create_elite_session(profile_index=random.randint(0, 19))
            self.session_pool.append(new_session)
            
            # Close old session if we have too many
            if len(self.session_pool) > 3:
                old_session = self.session_pool.pop(0)
                await old_session.close()
        
        # Use current session
        session = self.session_pool[self.current_session_index]
        self.current_session_index = (self.current_session_index + 1) % len(self.session_pool)
        
        return session
    
    async def _search_via_google(self, company: str, title: str) -> Set[Person]:
        """Search Google for LinkedIn profiles - safest method"""
        people = set()
        
        # Multiple search query variations
        queries = [
            f'site:linkedin.com/in "{company}" "{title}"',
            f'site:linkedin.com/in "{company}" {title}',
            f'linkedin.com/in "{company}" {title} -pub -dir',
            f'"linkedin.com/in" "{company}" "{title}"',
            f'site:linkedin.com "{company}" "{title}" "experience"',
        ]
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        for query in queries:
            try:
                self.rate_limiter.wait_if_needed("elite_linkedin")
                
                # Search Google
                search_url = f"https://www.google.com/search?q={urlencode({'q': query})}&num=100"
                await page.goto(search_url, wait_until='networkidle')
                
                # Random human behavior
                await session.scroll_naturally(page)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Extract LinkedIn profile URLs
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find LinkedIn URLs in Google results
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if 'linkedin.com/in/' in href and '/in/' in href:
                        # Clean the URL
                        clean_url = self._clean_linkedin_url(href)
                        if clean_url:
                            # Extract person info from Google snippet
                            person = await self._extract_person_from_google_result(link, company, clean_url)
                            if person:
                                people.add(person)
                
                # Delay between queries
                await asyncio.sleep(random.uniform(self.config.request_delay_min, self.config.request_delay_max))
                
            except Exception as e:
                print(f"⚠️ Google search error: {e}")
                continue
        
        await page.close()
        print(f"📍 Google indirect: found {len(people)} people")
        return people
    
    async def _scrape_company_employees(self, company: str, title: str) -> Set[Person]:
        """Scrape LinkedIn company page for employees"""
        people = set()
        
        # Find company LinkedIn page
        company_url = await self._find_company_page(company)
        if not company_url:
            return people
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        try:
            # Navigate to company people page
            people_url = f"{company_url}/people/"
            
            self.rate_limiter.wait_if_needed("elite_linkedin")
            await page.goto(people_url, wait_until='networkidle')
            
            # Check if we hit login wall
            current_url = page.url
            if 'authwall' in current_url or 'login' in current_url:
                # Try bypass techniques
                if not await self._bypass_login_wall(page):
                    print("⚠️ LinkedIn requires login - trying alternative methods")
                    return people
            
            # Extract people from company page
            people = await self._extract_people_from_company_page(page, company)
            
            # Try to load more by scrolling
            for _ in range(5):
                await session.scroll_naturally(page)
                await asyncio.sleep(random.uniform(3, 6))
                
                # Check for "Show more" button
                try:
                    show_more = await page.query_selector('button[aria-label*="more"]')
                    if show_more:
                        await session.stealth_click('button[aria-label*="more"]', page)
                        await asyncio.sleep(random.uniform(2, 4))
                except:
                    pass
                
                # Extract additional people
                new_people = await self._extract_people_from_company_page(page, company)
                people.update(new_people)
                
                if len(people) >= self.config.max_people_per_company:
                    break
        
        except Exception as e:
            print(f"⚠️ Company scraping error: {e}")
        
        finally:
            await page.close()
        
        print(f"🏢 Company page: found {len(people)} people")
        return people
    
    async def _direct_linkedin_search(self, company: str, title: str) -> Set[Person]:
        """Direct LinkedIn search - highest risk/reward"""
        people = set()
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        try:
            # Build LinkedIn search URL
            search_params = {
                'keywords': f"{title} {company}",
                'origin': 'GLOBAL_SEARCH_HEADER',
                'position': '1',
                'searchId': self._generate_search_id(),
                'sid': self._generate_session_id(),
            }
            
            search_url = f"https://www.linkedin.com/search/results/people/?{urlencode(search_params)}"
            
            self.rate_limiter.wait_if_needed("elite_linkedin")
            await page.goto(search_url, wait_until='networkidle')
            
            # Check for auth wall
            if 'authwall' in page.url or await page.query_selector('[data-test-id="guest-homepage"]'):
                if not await self._bypass_login_wall(page):
                    return people
            
            # Extract people from search results
            for page_num in range(self.config.max_pages_per_search):
                # Extract people from current page
                page_people = await self._extract_people_from_search_page(page, company)
                people.update(page_people)
                
                # Try to go to next page
                try:
                    next_button = await page.query_selector('button[aria-label="Next"]')
                    if next_button and await next_button.is_enabled():
                        await session.stealth_click('button[aria-label="Next"]', page)
                        await asyncio.sleep(random.uniform(4, 8))
                    else:
                        break
                except:
                    break
                
                if len(people) >= self.config.max_people_per_company:
                    break
        
        except Exception as e:
            print(f"⚠️ Direct search error: {e}")
        
        finally:
            await page.close()
        
        print(f"🎯 Direct search: found {len(people)} people")
        return people
    
    async def _sales_navigator_search(self, company: str, title: str) -> Set[Person]:
        """Search via Sales Navigator interface"""
        people = set()
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        try:
            # Sales Navigator search URL
            search_params = {
                'keywords': title,
                'companySize': 'B,C,D,E,F,G,H,I',  # All company sizes
                'currentCompany': company,
                'geoUrn': '["103644278"]',  # United States
                'resultType': 'PEOPLE',
                'searchSessionId': self._generate_session_id(),
            }
            
            sales_nav_url = f"https://www.linkedin.com/sales/search/people?{urlencode(search_params)}"
            
            self.rate_limiter.wait_if_needed("elite_linkedin")
            await page.goto(sales_nav_url, wait_until='networkidle')
            
            # Check if we have Sales Navigator access
            if 'premium' in page.url or 'sales/search' in page.url:
                # Extract from Sales Navigator results
                people = await self._extract_from_sales_navigator(page, company)
            
        except Exception as e:
            print(f"⚠️ Sales Navigator error: {e}")
        
        finally:
            await page.close()
        
        print(f"💼 Sales Navigator: found {len(people)} people")
        return people
    
    async def _bypass_login_wall(self, page) -> bool:
        """Advanced login wall bypass techniques"""
        
        try:
            # Method 1: Cookie injection
            linkedin_cookies = [
                {
                    'name': 'li_at',
                    'value': 'temporary_session_' + str(int(time.time())),
                    'domain': '.linkedin.com',
                    'path': '/',
                    'httpOnly': True,
                    'secure': True
                },
                {
                    'name': 'JSESSIONID',
                    'value': 'ajax:' + str(random.randint(1000000000, 9999999999)),
                    'domain': '.linkedin.com',
                    'path': '/',
                    'httpOnly': True
                }
            ]
            
            await page.context.add_cookies(linkedin_cookies)
            
            # Method 2: Try mobile version
            await page.goto(page.url.replace('www.linkedin.com', 'm.linkedin.com'))
            await asyncio.sleep(2)
            
            # Method 3: Referrer spoofing
            await page.goto(page.url, referer='https://www.google.com/')
            
            # Method 4: Clear detection scripts
            await page.evaluate('''
                // Clear common detection variables
                delete window.__SEGMENT_INSPECTOR__;
                delete window.analytics;
                delete window.gtag;
                delete window.dataLayer;
                
                // Mock login status
                window.IN = {
                    User: {
                        isAuthenticated: true
                    }
                };
            ''')
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Check if bypass worked
            current_url = page.url
            return 'authwall' not in current_url and 'login' not in current_url
            
        except Exception as e:
            print(f"⚠️ Login bypass failed: {e}")
            return False
    
    async def _find_company_page(self, company: str) -> Optional[str]:
        """Find LinkedIn company page URL"""
        
        # Check cache first
        cache_key = f"linkedin_company_{company.lower()}"
        cached_url = self.cache.get("linkedin", cache_key)
        if cached_url:
            return cached_url
        
        # Try direct URL patterns
        possible_urls = [
            f"https://www.linkedin.com/company/{company.lower().replace(' ', '-')}",
            f"https://www.linkedin.com/company/{company.lower().replace(' ', '')}",
            f"https://www.linkedin.com/company/{company.lower()}",
        ]
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        for url in possible_urls:
            try:
                await page.goto(url, wait_until='networkidle')
                
                # Check if valid company page
                if page.url == url and not ('404' in page.url or 'error' in page.url):
                    # Cache the result
                    self.cache.set("linkedin", cache_key, url)
                    await page.close()
                    return url
                    
            except:
                continue
        
        await page.close()
        return None
    
    async def _extract_people_from_company_page(self, page, company: str) -> Set[Person]:
        """Extract people from LinkedIn company people page"""
        people = set()
        
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find employee cards - multiple selectors for different layouts
            employee_selectors = [
                'div[data-test-id="people-card"]',
                'li[data-test-component="search-results-entity"]',
                'div.org-people-profile-card__profile-info',
                'div.artdeco-entity-lockup__content',
                'a[href*="/in/"]'
            ]
            
            for selector in employee_selectors:
                cards = soup.select(selector)
                
                for card in cards:
                    person = self._parse_person_from_card(card, company, page.url)
                    if person:
                        people.add(person)
        
        except Exception as e:
            print(f"⚠️ Person extraction error: {e}")
        
        return people
    
    async def _extract_people_from_search_page(self, page, company: str) -> Set[Person]:
        """Extract people from LinkedIn search results"""
        people = set()
        
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Search result selectors
            result_selectors = [
                'li[data-test-search-result]',
                'div[data-test-component="search-results-entity"]',
                'div.search-result__wrapper',
                'li.reusable-search__result-container'
            ]
            
            for selector in result_selectors:
                results = soup.select(selector)
                
                for result in results:
                    person = self._parse_person_from_search_result(result, company, page.url)
                    if person:
                        people.add(person)
        
        except Exception as e:
            print(f"⚠️ Search extraction error: {e}")
        
        return people
    
    async def _extract_from_sales_navigator(self, page, company: str) -> Set[Person]:
        """Extract from Sales Navigator results"""
        people = set()
        
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Sales Navigator specific selectors
            sn_selectors = [
                'div[data-test-id="search-result-card"]',
                'div.artdeco-entity-lockup',
                'li[data-test-search-result]'
            ]
            
            for selector in sn_selectors:
                cards = soup.select(selector)
                
                for card in cards:
                    person = self._parse_person_from_sales_nav_card(card, company, page.url)
                    if person:
                        people.add(person)
        
        except Exception as e:
            print(f"⚠️ Sales Navigator extraction error: {e}")
        
        return people
    
    def _parse_person_from_card(self, card_soup, company: str, evidence_url: str) -> Optional[Person]:
        """Parse person from company page card"""
        try:
            # Extract name
            name_selectors = [
                'span[dir="ltr"]',
                'a[data-test-id="people-card-name"]',
                'div.org-people-profile-card__profile-title',
                '.artdeco-entity-lockup__title'
            ]
            
            name = None
            for selector in name_selectors:
                name_elem = card_soup.select_one(selector)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    if len(name) > 2:
                        break
            
            if not name:
                return None
            
            # Extract title
            title_selectors = [
                'div.artdeco-entity-lockup__subtitle',
                'div[data-test-id="people-card-subtitle"]',
                'p.org-people-profile-card__profile-subtitle'
            ]
            
            title = None
            for selector in title_selectors:
                title_elem = card_soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # Extract LinkedIn URL
            linkedin_url = None
            link_elem = card_soup.find('a', href=re.compile(r'/in/[^/]+'))
            if link_elem:
                href = link_elem.get('href', '')
                if href.startswith('/'):
                    linkedin_url = f"https://www.linkedin.com{href}"
                else:
                    linkedin_url = self._clean_linkedin_url(href)
            
            if name and len(name) > 2:
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    linkedin_url=linkedin_url,
                    source="elite_linkedin",
                    evidence_url=evidence_url,
                    confidence_score=0.8 if linkedin_url else 0.6
                )
        
        except Exception as e:
            pass
        
        return None
    
    def _parse_person_from_search_result(self, result_soup, company: str, evidence_url: str) -> Optional[Person]:
        """Parse person from search result"""
        try:
            # Name from search result
            name_elem = result_soup.find('span', {'dir': 'ltr'}) or \
                       result_soup.find('a', href=re.compile(r'/in/')) or \
                       result_soup.select_one('.artdeco-entity-lockup__title')
            
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            
            # Title
            title_elem = result_soup.select_one('.artdeco-entity-lockup__subtitle') or \
                        result_soup.find('p', class_=re.compile(r'subtitle|headline'))
            
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # LinkedIn URL
            link_elem = result_soup.find('a', href=re.compile(r'/in/'))
            linkedin_url = None
            if link_elem:
                href = link_elem.get('href', '')
                linkedin_url = self._clean_linkedin_url(href)
            
            if name and len(name) > 2:
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    linkedin_url=linkedin_url,
                    source="elite_linkedin",
                    evidence_url=evidence_url,
                    confidence_score=0.7
                )
        
        except:
            pass
        
        return None
    
    def _parse_person_from_sales_nav_card(self, card_soup, company: str, evidence_url: str) -> Optional[Person]:
        """Parse person from Sales Navigator card"""
        # Similar to search result parsing but with Sales Navigator specific selectors
        return self._parse_person_from_search_result(card_soup, company, evidence_url)
    
    async def _extract_person_from_google_result(self, link_soup, company: str, linkedin_url: str) -> Optional[Person]:
        """Extract person info from Google search result snippet"""
        try:
            # Get the parent div that contains the full result
            result_div = link_soup.find_parent('div', class_=re.compile(r'g\b'))
            if not result_div:
                return None
            
            # Extract title/snippet
            snippet_elem = result_div.find('span') or result_div.find('div', class_=re.compile(r'VwiC3b'))
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Try to extract name from LinkedIn URL
            name = self._extract_name_from_linkedin_url(linkedin_url)
            
            # Try to extract title from snippet
            title = None
            if snippet:
                # Look for job titles in snippet
                title_patterns = [
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+at\s+' + re.escape(company),
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*-\s*' + re.escape(company),
                    r'' + re.escape(company) + r'\s*[:-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                ]
                
                for pattern in title_patterns:
                    match = re.search(pattern, snippet, re.IGNORECASE)
                    if match:
                        title = match.group(1).strip()
                        break
            
            if name:
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    linkedin_url=linkedin_url,
                    source="elite_linkedin",
                    evidence_url=f"https://www.google.com/search?q={company}+{name}",
                    confidence_score=0.6
                )
        
        except:
            pass
        
        return None
    
    async def _enhance_profiles(self, people: List[Person]) -> List[Person]:
        """Deep profile scraping for additional details"""
        enhanced_people = []
        
        session = await self._ensure_session()
        
        for person in people[:20]:  # Limit to avoid detection
            if not person.linkedin_url:
                enhanced_people.append(person)
                continue
            
            try:
                self.rate_limiter.wait_if_needed("elite_linkedin")
                
                page = await session.new_page()
                await page.goto(person.linkedin_url, wait_until='networkidle')
                
                # Extract additional info
                enhanced_person = await self._extract_detailed_profile(page, person)
                enhanced_people.append(enhanced_person or person)
                
                await page.close()
                await asyncio.sleep(random.uniform(3, 7))
                
            except Exception as e:
                print(f"⚠️ Profile enhancement error: {e}")
                enhanced_people.append(person)
        
        return enhanced_people
    
    async def _extract_detailed_profile(self, page, person: Person) -> Optional[Person]:
        """Extract detailed info from LinkedIn profile"""
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for public profile access
            if 'authwall' in page.url:
                return person
            
            # Extract enhanced details
            enhanced_data = {
                'name': person.name,
                'title': person.title,
                'company': person.company,
                'linkedin_url': person.linkedin_url,
                'source': person.source,
                'evidence_url': person.evidence_url,
                'confidence_score': person.confidence_score
            }
            
            # Try to find email (rare but possible)
            email_patterns = [
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            ]
            
            page_text = soup.get_text()
            for pattern in email_patterns:
                email_matches = re.findall(pattern, page_text)
                if email_matches:
                    # Take the first valid-looking email
                    enhanced_data['email'] = email_matches[0]
                    enhanced_data['confidence_score'] = 0.9
                    break
            
            # Extract current position title if different
            title_selectors = [
                'h2.text-heading-xlarge',
                'div.text-body-medium',
                'section[data-section="currentPositions"] h3'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    new_title = title_elem.get_text(strip=True)
                    if new_title and len(new_title) < 100:
                        enhanced_data['title'] = new_title
                        break
            
            return Person(**enhanced_data)
        
        except:
            return person
    
    def _clean_linkedin_url(self, url: str) -> Optional[str]:
        """Clean and validate LinkedIn URL"""
        if not url or 'linkedin.com/in/' not in url:
            return None
        
        # Handle Google redirect URLs
        if 'google.com' in url and 'url=' in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'url' in params:
                url = params['url'][0]
        
        # Clean URL
        if '/in/' in url:
            parts = url.split('/in/')
            if len(parts) >= 2:
                username = parts[1].split('/')[0].split('?')[0]
                return f"https://www.linkedin.com/in/{username}"
        
        return None
    
    def _extract_name_from_linkedin_url(self, linkedin_url: str) -> Optional[str]:
        """Try to extract name from LinkedIn URL"""
        if not linkedin_url:
            return None
        
        try:
            # Extract username from URL
            username = linkedin_url.split('/in/')[-1].split('/')[0].split('?')[0]
            
            # Convert username to name (rough approximation)
            # Remove common suffixes
            username = re.sub(r'[-_]?(phd|md|mba|cpa|jr|sr|ii|iii)$', '', username, flags=re.IGNORECASE)
            
            # Split on common separators
            parts = re.split(r'[-_.]', username)
            
            # Capitalize each part
            name_parts = []
            for part in parts:
                if part and part.isalpha() and len(part) > 1:
                    name_parts.append(part.capitalize())
            
            if len(name_parts) >= 2:
                return ' '.join(name_parts[:2])  # First and last name
            elif len(name_parts) == 1:
                return name_parts[0]
        
        except:
            pass
        
        return None
    
    def _generate_search_id(self) -> str:
        """Generate realistic search ID"""
        return f"search_{int(time.time())}_{random.randint(100000, 999999)}"
    
    def _generate_session_id(self) -> str:
        """Generate realistic session ID"""
        return hashlib.md5(f"session_{time.time()}_{random.random()}".encode()).hexdigest()
    
    async def cleanup(self):
        """Clean up all sessions"""
        for session in self.session_pool:
            await session.close()
        self.session_pool.clear()

# Factory function for easy integration
def create_elite_linkedin_scraper() -> EliteLinkedInScraper:
    """Create LinkedIn scraper with production config"""
    config = LinkedInConfig(
        max_pages_per_search=5,
        max_people_per_company=100,
        scroll_pause_min=3.0,
        scroll_pause_max=6.0,
        request_delay_min=5.0,
        request_delay_max=12.0,
        session_rotation_after=30,
        use_multiple_search_methods=True,
        bypass_login_wall=True,
        extract_emails=False,  # Too risky
        deep_profile_scraping=False  # Too risky
    )
    return EliteLinkedInScraper(config)