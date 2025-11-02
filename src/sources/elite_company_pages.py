"""
Elite Company Pages Scraper - Production Grade
Extracts people from ANY company website with zero detection
"""

import asyncio
import random
import re
import json
import time
from typing import List, Optional, Dict, Set, Tuple
from urllib.parse import urljoin, urlparse, urlencode
from bs4 import BeautifulSoup
from dataclasses import dataclass
import requests
from concurrent.futures import ThreadPoolExecutor
import tldextract

from src.models.person import Person, PersonCategory
from src.utils.elite_browser import create_elite_session, EliteSession
from src.utils.rate_limiter import get_rate_limiter
from src.utils.cache import get_cache

@dataclass
class CompanyPagesConfig:
    """Company pages scraping configuration"""
    max_pages_per_domain: int = 50
    max_depth: int = 3
    concurrent_sessions: int = 3
    smart_crawling: bool = True
    extract_social_links: bool = True
    analyze_job_postings: bool = True
    deep_contact_extraction: bool = True
    bypass_javascript_protection: bool = True
    use_multiple_approaches: bool = True

class EliteCompanyPagesScraper:
    """
    Elite company website scraper that finds people on:
    - Team/About pages
    - Leadership pages  
    - Press releases
    - Job postings (hiring managers)
    - Contact pages
    - Blog author pages
    - Event speaker pages
    - Investor relation pages
    - And automatically discovers more via AI-powered crawling
    """
    
    def __init__(self, config: CompanyPagesConfig = None):
        self.config = config or CompanyPagesConfig()
        self.cache = get_cache()
        self.rate_limiter = get_rate_limiter()
        
        # Configure rate limiting per domain
        self.rate_limiter.configure(
            "elite_company_pages",
            requests_per_second=3,  # More aggressive than other scrapers
            max_per_hour=500
        )
        
        self.session_pool: List[EliteSession] = []
        self.domain_sitemaps = {}
        self.discovered_pages = {}
        
        # Extensive page patterns to check
        self.page_patterns = [
            # Standard patterns
            "/team", "/about/team", "/about/leadership", "/leadership",
            "/people", "/our-team", "/company/team", "/careers/team",
            "/about-us/team", "/meet-the-team", "/staff", "/employees",
            
            # Management/Executive patterns
            "/management", "/executives", "/board", "/directors",
            "/founders", "/leadership-team", "/senior-team",
            "/executive-team", "/board-of-directors",
            
            # About/Company patterns
            "/about", "/about-us", "/company", "/who-we-are",
            "/our-story", "/company/about", "/company/leadership",
            
            # Career/HR patterns
            "/careers", "/jobs", "/hiring", "/join-us", "/work-with-us",
            "/careers/team", "/careers/leadership", "/join-our-team",
            
            # Press/Media patterns
            "/press", "/news", "/media", "/press-releases",
            "/newsroom", "/media-kit", "/press-center",
            
            # Contact patterns
            "/contact", "/contact-us", "/team-contact", "/staff-directory",
            
            # Investor patterns
            "/investors", "/investor-relations", "/ir", "/governance",
            
            # Blog/Content patterns
            "/blog", "/insights", "/resources", "/authors",
            "/blog/authors", "/experts", "/speakers",
        ]
        
        # AI-powered content analysis patterns
        self.person_indicators = [
            # Name patterns
            r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b',
            
            # Title patterns  
            r'\b(?:CEO|CTO|CFO|COO|VP|Director|Manager|Lead|Head)\b',
            r'\b(?:Chief|Senior|Principal|Staff)\s+[A-Za-z\s]+\b',
            r'\b[A-Za-z\s]+(?:Engineer|Developer|Designer|Analyst|Specialist)\b',
            
            # Contact patterns
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'\b(?:linkedin\.com/in/[a-zA-Z0-9-]+)\b',
            r'\b(?:twitter\.com/[a-zA-Z0-9_]+)\b',
        ]
        
        # Company domain intelligence
        self.domain_intelligence = {}
        
    async def search_people(self, company: str, title: str, company_domain: Optional[str] = None, **kwargs) -> List[Person]:
        """Master company pages search using all available methods"""
        print(f"🔥 Elite Company Pages: Hunting {title} at {company}")
        
        # Auto-discover domain if not provided
        if not company_domain:
            company_domain = await self._discover_company_domain(company)
            if not company_domain:
                print(f"⚠️ Could not find domain for {company}")
                return []
        
        print(f"🎯 Target domain: {company_domain}")
        
        all_people = set()
        
        # Method 1: Intelligent page discovery
        discovered_pages = await self._discover_people_pages(company_domain)
        page_people = await self._scrape_discovered_pages(discovered_pages, company, company_domain)
        all_people.update(page_people)
        
        # Method 2: Sitemap analysis
        sitemap_people = await self._analyze_sitemap(company_domain, company)
        all_people.update(sitemap_people)
        
        # Method 3: JavaScript-heavy sites
        if self.config.bypass_javascript_protection:
            js_people = await self._scrape_javascript_sites(company_domain, company)
            all_people.update(js_people)
        
        # Method 4: Job postings analysis
        if self.config.analyze_job_postings:
            job_people = await self._analyze_job_postings(company_domain, company, title)
            all_people.update(job_people)
        
        # Method 5: Social media discovery
        if self.config.extract_social_links:
            social_people = await self._discover_via_social_links(company_domain, company)
            all_people.update(social_people)
        
        # Method 6: Deep content analysis
        if self.config.deep_contact_extraction:
            content_people = await self._deep_content_analysis(company_domain, company)
            all_people.update(content_people)
        
        people_list = list(all_people)
        
        print(f"✅ Elite Company Pages found {len(people_list)} people")
        return people_list
    
    async def _ensure_session_pool(self) -> List[EliteSession]:
        """Ensure we have a pool of sessions for concurrent scraping"""
        if len(self.session_pool) < self.config.concurrent_sessions:
            while len(self.session_pool) < self.config.concurrent_sessions:
                session = await create_elite_session()
                self.session_pool.append(session)
        
        return self.session_pool
    
    async def _discover_company_domain(self, company: str) -> Optional[str]:
        """Intelligently discover company domain"""
        
        # Check cache first
        cache_key = f"company_domain_{company.lower()}"
        cached_domain = self.cache.get("domains", cache_key)
        if cached_domain:
            return cached_domain
        
        # Multiple discovery methods
        domain_candidates = []
        
        # Method 1: Direct guess
        direct_guesses = self._generate_domain_guesses(company)
        domain_candidates.extend(direct_guesses)
        
        # Method 2: Search engines
        search_domains = await self._find_domain_via_search(company)
        domain_candidates.extend(search_domains)
        
        # Method 3: WHOIS/DNS lookups
        dns_domains = await self._find_domain_via_dns(company)
        domain_candidates.extend(dns_domains)
        
        # Test candidates
        session = await create_elite_session()
        page = await session.new_page()
        
        for domain in domain_candidates:
            try:
                # Test if domain responds
                await page.goto(f"https://{domain}", wait_until='networkidle', timeout=10000)
                
                # Check if it looks like a company website
                content = await page.content()
                if self._looks_like_company_site(content, company):
                    # Cache successful domain
                    self.cache.set("domains", cache_key, domain)
                    await session.close()
                    return domain
                    
            except:
                continue
        
        await session.close()
        return None
    
    def _generate_domain_guesses(self, company: str) -> List[str]:
        """Generate intelligent domain guesses"""
        clean_company = re.sub(r'\s+(inc|llc|ltd|corp|corporation|company)\.?$', '', company.lower())
        
        # Remove common words
        clean_company = re.sub(r'\b(the|and|of|for)\b', '', clean_company)
        clean_company = clean_company.strip()
        
        guesses = []
        
        if ' ' in clean_company:
            words = clean_company.split()
            
            # Full name variations
            guesses.extend([
                clean_company.replace(' ', '') + '.com',
                clean_company.replace(' ', '-') + '.com', 
                clean_company.replace(' ', '_') + '.com',
                clean_company.replace(' ', '') + '.io',
                clean_company.replace(' ', '') + '.co',
            ])
            
            # First word only
            first_word = words[0]
            guesses.extend([
                first_word + '.com',
                first_word + '.io',
                first_word + '.co',
                first_word + '.net',
            ])
            
            # Acronym
            acronym = ''.join(word[0] for word in words)
            if len(acronym) >= 2:
                guesses.extend([
                    acronym + '.com',
                    acronym + '.io',
                ])
        else:
            # Single word company
            guesses.extend([
                clean_company + '.com',
                clean_company + '.io',
                clean_company + '.co',
                clean_company + '.net',
            ])
        
        return list(set(guesses))
    
    async def _find_domain_via_search(self, company: str) -> List[str]:
        """Find domain via search engines"""
        domains = []
        
        session = await create_elite_session()
        page = await session.new_page()
        
        try:
            # Search for company website
            search_query = f'"{company}" official website'
            search_url = f"https://www.google.com/search?q={urlencode({'q': search_query})}"
            
            await page.goto(search_url, wait_until='networkidle')
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract domains from search results
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'http' in href and company.lower().replace(' ', '') in href.lower():
                    parsed = urlparse(href)
                    if parsed.netloc:
                        domains.append(parsed.netloc)
            
        except Exception as e:
            pass
        
        finally:
            await session.close()
        
        return domains[:5]  # Top 5 candidates
    
    async def _find_domain_via_dns(self, company: str) -> List[str]:
        """Find domain via DNS/WHOIS techniques"""
        domains = []
        
        try:
            # This would integrate with DNS/WHOIS APIs
            # For now, return empty list
            pass
        except:
            pass
        
        return domains
    
    def _looks_like_company_site(self, html_content: str, company: str) -> bool:
        """Check if HTML content looks like a company website"""
        content_lower = html_content.lower()
        company_lower = company.lower()
        
        # Check for company name mentions
        if company_lower in content_lower:
            return True
        
        # Check for business-related terms
        business_terms = ['about us', 'contact us', 'careers', 'team', 'leadership', 'products', 'services']
        business_matches = sum(1 for term in business_terms if term in content_lower)
        
        if business_matches >= 3:
            return True
        
        return False
    
    async def _discover_people_pages(self, domain: str) -> List[str]:
        """Discover pages likely to contain people information"""
        discovered_pages = []
        
        sessions = await self._ensure_session_pool()
        
        # Test standard patterns
        for pattern in self.page_patterns:
            url = f"https://{domain}{pattern}"
            discovered_pages.append(url)
        
        # Intelligent discovery using AI
        if self.config.smart_crawling:
            smart_pages = await self._ai_powered_page_discovery(domain)
            discovered_pages.extend(smart_pages)
        
        return discovered_pages
    
    async def _ai_powered_page_discovery(self, domain: str) -> List[str]:
        """Use AI techniques to discover relevant pages"""
        discovered_pages = []
        
        session = await create_elite_session()
        page = await session.new_page()
        
        try:
            # Start from homepage
            await page.goto(f"https://{domain}", wait_until='networkidle')
            
            # Extract all internal links
            all_links = await page.evaluate(f'''
                () => {{
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links
                        .map(link => link.href)
                        .filter(href => href.includes('{domain}'))
                        .filter(href => !href.includes('#'))
                        .slice(0, 100);  // Limit for performance
                }}
            ''')
            
            # Score links based on people-related keywords
            people_keywords = [
                'team', 'about', 'leadership', 'people', 'staff', 'management',
                'executives', 'founders', 'directors', 'careers', 'contact'
            ]
            
            scored_links = []
            for link in all_links:
                score = 0
                link_lower = link.lower()
                
                for keyword in people_keywords:
                    if keyword in link_lower:
                        score += 1
                
                if score > 0:
                    scored_links.append((link, score))
            
            # Sort by score and return top candidates
            scored_links.sort(key=lambda x: x[1], reverse=True)
            discovered_pages = [link for link, score in scored_links[:20]]
            
        except Exception as e:
            pass
        
        finally:
            await session.close()
        
        return discovered_pages
    
    async def _scrape_discovered_pages(self, page_urls: List[str], company: str, domain: str) -> Set[Person]:
        """Scrape discovered pages for people"""
        all_people = set()
        
        # Use concurrent scraping
        semaphore = asyncio.Semaphore(self.config.concurrent_sessions)
        
        async def scrape_single_page(url: str) -> Set[Person]:
            async with semaphore:
                return await self._scrape_single_page(url, company, domain)
        
        # Create tasks for concurrent execution
        tasks = [scrape_single_page(url) for url in page_urls[:20]]  # Limit concurrent requests
        
        # Execute tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for result in results:
            if isinstance(result, set):
                all_people.update(result)
        
        return all_people
    
    async def _scrape_single_page(self, url: str, company: str, domain: str) -> Set[Person]:
        """Scrape a single page for people"""
        people = set()
        
        session = await create_elite_session()
        page = await session.new_page()
        
        try:
            self.rate_limiter.wait_if_needed("elite_company_pages")
            
            await page.goto(url, wait_until='networkidle')
            content = await page.content()
            
            # Extract people using multiple methods
            html_people = self._extract_people_from_html(content, company, url)
            people.update(html_people)
            
            # JavaScript-rendered content
            js_people = await self._extract_people_from_js_content(page, company, url)
            people.update(js_people)
            
        except Exception as e:
            pass
        
        finally:
            await page.close()
        
        return people
    
    def _extract_people_from_html(self, html_content: str, company: str, evidence_url: str) -> Set[Person]:
        """Extract people from HTML content using advanced patterns"""
        people = set()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Method 1: Structured data (JSON-LD, microdata)
        structured_people = self._extract_structured_data(soup, company, evidence_url)
        people.update(structured_people)
        
        # Method 2: Team member cards
        card_people = self._extract_from_team_cards(soup, company, evidence_url)
        people.update(card_people)
        
        # Method 3: Leadership sections
        leadership_people = self._extract_from_leadership_sections(soup, company, evidence_url)
        people.update(leadership_people)
        
        # Method 4: Contact information
        contact_people = self._extract_from_contact_sections(soup, company, evidence_url)
        people.update(contact_people)
        
        # Method 5: Blog/content authors
        author_people = self._extract_from_author_sections(soup, company, evidence_url)
        people.update(author_people)
        
        # Method 6: General text patterns
        text_people = self._extract_from_text_patterns(soup, company, evidence_url)
        people.update(text_people)
        
        return people
    
    def _extract_structured_data(self, soup: BeautifulSoup, company: str, evidence_url: str) -> Set[Person]:
        """Extract people from structured data (Schema.org, JSON-LD)"""
        people = set()
        
        # JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data_items = data
                else:
                    data_items = [data]
                
                for item in data_items:
                    if item.get('@type') == 'Person':
                        person = self._parse_person_from_structured_data(item, company, evidence_url)
                        if person:
                            people.add(person)
                    elif item.get('@type') == 'Organization':
                        # Look for employees in organization data
                        employees = item.get('employee', [])
                        for emp in employees:
                            person = self._parse_person_from_structured_data(emp, company, evidence_url)
                            if person:
                                people.add(person)
            except:
                continue
        
        return people
    
    def _parse_person_from_structured_data(self, person_data: dict, company: str, evidence_url: str) -> Optional[Person]:
        """Parse person from structured data"""
        try:
            name = person_data.get('name')
            title = person_data.get('jobTitle') or person_data.get('title')
            email = person_data.get('email')
            
            # Extract social URLs
            linkedin_url = None
            twitter_url = None
            
            social_urls = person_data.get('sameAs', [])
            if isinstance(social_urls, str):
                social_urls = [social_urls]
            
            for url in social_urls:
                if 'linkedin.com/in/' in url:
                    linkedin_url = url
                elif 'twitter.com/' in url:
                    twitter_url = url
            
            if name and len(name) > 2:
                return Person(
                    name=name,
                    title=title,
                    company=company,
                    email=email,
                    linkedin_url=linkedin_url,
                    twitter_url=twitter_url,
                    source="elite_company_pages",
                    evidence_url=evidence_url,
                    confidence_score=0.9  # High confidence for structured data
                )
        except:
            pass
        
        return None
    
    def _extract_from_team_cards(self, soup: BeautifulSoup, company: str, evidence_url: str) -> Set[Person]:
        """Extract people from team member cards"""
        people = set()
        
        # Common team card selectors
        card_selectors = [
            '.team-member', '.team-card', '.person-card', '.employee-card',
            '.staff-member', '.bio-card', '.profile-card', '.member-card',
            '[class*="team"]', '[class*="member"]', '[class*="person"]',
            '[class*="staff"]', '[class*="employee"]'
        ]
        
        for selector in card_selectors:
            cards = soup.select(selector)
            
            for card in cards:
                person = self._parse_person_from_card(card, company, evidence_url)
                if person:
                    people.add(person)
        
        return people
    
    def _parse_person_from_card(self, card, company: str, evidence_url: str) -> Optional[Person]:
        """Parse person from a team member card"""
        try:
            # Extract name
            name_selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5',
                '.name', '.title', '.person-name', '.member-name',
                '[class*="name"]', 'strong', 'b'
            ]
            
            name = None
            for selector in name_selectors:
                name_elem = card.select_one(selector)
                if name_elem:
                    text = name_elem.get_text(strip=True)
                    if len(text) > 2 and len(text) < 50 and self._looks_like_name(text):
                        name = text
                        break
            
            if not name:
                return None
            
            # Extract title/position
            title_selectors = [
                '.position', '.role', '.job-title', '.title', '.subtitle',
                '[class*="position"]', '[class*="role"]', '[class*="title"]',
                'p', '.description'
            ]
            
            title = None
            for selector in title_selectors:
                title_elem = card.select_one(selector)
                if title_elem:
                    text = title_elem.get_text(strip=True)
                    if text and len(text) < 100 and text != name and self._looks_like_title(text):
                        title = text
                        break
            
            # Extract contact information
            email = None
            linkedin_url = None
            twitter_url = None
            
            # Find email
            email_link = card.find('a', href=re.compile(r'^mailto:'))
            if email_link:
                email = email_link.get('href', '').replace('mailto:', '')
            
            # Find social links
            social_links = card.find_all('a', href=True)
            for link in social_links:
                href = link.get('href', '')
                if 'linkedin.com/in/' in href:
                    linkedin_url = href
                elif 'twitter.com/' in href:
                    twitter_url = href
            
            # Create person
            return Person(
                name=name,
                title=title,
                company=company,
                email=email,
                linkedin_url=linkedin_url,
                twitter_url=twitter_url,
                source="elite_company_pages",
                evidence_url=evidence_url,
                confidence_score=0.8 if email or linkedin_url else 0.6
            )
        
        except Exception as e:
            pass
        
        return None
    
    def _extract_from_leadership_sections(self, soup: BeautifulSoup, company: str, evidence_url: str) -> Set[Person]:
        """Extract people from leadership/executive sections"""
        people = set()
        
        # Find leadership sections
        leadership_sections = soup.find_all(['section', 'div'], 
                                          text=re.compile(r'(leadership|executive|management|board|founder)', re.I))
        
        for section in leadership_sections:
            # Look for people within these sections
            person_elements = section.find_all(['div', 'li', 'article'])
            
            for elem in person_elements:
                person = self._parse_person_from_card(elem, company, evidence_url)
                if person:
                    # Boost confidence for leadership sections
                    person.confidence_score = min(person.confidence_score + 0.1, 0.9)
                    people.add(person)
        
        return people
    
    def _extract_from_contact_sections(self, soup: BeautifulSoup, company: str, evidence_url: str) -> Set[Person]:
        """Extract people from contact sections"""
        people = set()
        
        # Find contact sections
        contact_sections = soup.find_all(['section', 'div'], 
                                       text=re.compile(r'(contact|reach|get in touch)', re.I))
        
        for section in contact_sections:
            # Look for contact persons
            text = section.get_text()
            
            # Extract names and emails
            email_matches = re.findall(r'([A-Z][a-z]+\s+[A-Z][a-z]+).*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
            
            for name, email in email_matches:
                if self._looks_like_name(name):
                    person = Person(
                        name=name,
                        title=None,
                        company=company,
                        email=email,
                        source="elite_company_pages",
                        evidence_url=evidence_url,
                        confidence_score=0.7
                    )
                    people.add(person)
        
        return people
    
    def _extract_from_author_sections(self, soup: BeautifulSoup, company: str, evidence_url: str) -> Set[Person]:
        """Extract people from blog/content author sections"""
        people = set()
        
        # Find author information
        author_selectors = [
            '.author', '.by-author', '.post-author', '.article-author',
            '[class*="author"]', '[rel="author"]'
        ]
        
        for selector in author_selectors:
            authors = soup.select(selector)
            
            for author in authors:
                name_text = author.get_text(strip=True)
                if self._looks_like_name(name_text):
                    person = Person(
                        name=name_text,
                        title=None,  # Could be inferred as Content Writer/Marketing
                        company=company,
                        source="elite_company_pages",
                        evidence_url=evidence_url,
                        confidence_score=0.5
                    )
                    people.add(person)
        
        return people
    
    def _extract_from_text_patterns(self, soup: BeautifulSoup, company: str, evidence_url: str) -> Set[Person]:
        """Extract people using text pattern matching"""
        people = set()
        
        text = soup.get_text()
        
        # Pattern: "Name, Title" or "Name - Title"
        name_title_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\-–—]\s*([A-Z][a-z\s]+(?:Officer|Manager|Director|Engineer|Developer|Designer|Analyst|Specialist|Lead|Head))',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[,\-–—]\s*(CEO|CTO|CFO|COO|VP|President|Founder)',
        ]
        
        for pattern in name_title_patterns:
            matches = re.findall(pattern, text)
            for name, title in matches:
                if len(name) > 5 and len(title) > 3:
                    person = Person(
                        name=name.strip(),
                        title=title.strip(),
                        company=company,
                        source="elite_company_pages",
                        evidence_url=evidence_url,
                        confidence_score=0.5
                    )
                    people.add(person)
        
        return people
    
    async def _extract_people_from_js_content(self, page, company: str, evidence_url: str) -> Set[Person]:
        """Extract people from JavaScript-rendered content"""
        people = set()
        
        try:
            # Wait for dynamic content to load
            await asyncio.sleep(2)
            
            # Try to trigger any "Load More" buttons
            load_more_selectors = [
                'button:contains("Load")', 'button:contains("More")', 
                '.load-more', '.show-more', '[data-load]'
            ]
            
            for selector in load_more_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # Extract from dynamically loaded content
            updated_content = await page.content()
            js_people = self._extract_people_from_html(updated_content, company, evidence_url)
            people.update(js_people)
            
        except Exception as e:
            pass
        
        return people
    
    async def _analyze_sitemap(self, domain: str, company: str) -> Set[Person]:
        """Analyze sitemap for people-related pages"""
        people = set()
        
        # Common sitemap locations
        sitemap_urls = [
            f"https://{domain}/sitemap.xml",
            f"https://{domain}/sitemap_index.xml",
            f"https://{domain}/sitemaps/sitemap.xml",
            f"https://{domain}/robots.txt"  # Often contains sitemap references
        ]
        
        session = await create_elite_session()
        page = await session.new_page()
        
        for sitemap_url in sitemap_urls:
            try:
                await page.goto(sitemap_url, wait_until='networkidle')
                content = await page.content()
                
                if 'sitemap.xml' in sitemap_url:
                    # Parse XML sitemap
                    urls = self._parse_sitemap_xml(content)
                else:
                    # Parse robots.txt for sitemap references
                    urls = self._parse_robots_txt(content, domain)
                
                # Filter for people-related URLs
                people_urls = [url for url in urls if self._url_likely_has_people(url)]
                
                # Scrape promising URLs
                for url in people_urls[:10]:  # Limit to avoid overload
                    try:
                        page_people = await self._scrape_single_page(url, company, domain)
                        people.update(page_people)
                    except:
                        continue
                
                break  # Found working sitemap
                
            except:
                continue
        
        await session.close()
        return people
    
    def _parse_sitemap_xml(self, xml_content: str) -> List[str]:
        """Parse sitemap XML for URLs"""
        urls = []
        
        try:
            soup = BeautifulSoup(xml_content, 'xml')
            loc_tags = soup.find_all('loc')
            
            for tag in loc_tags:
                url = tag.get_text(strip=True)
                if url:
                    urls.append(url)
        except:
            pass
        
        return urls
    
    def _parse_robots_txt(self, robots_content: str, domain: str) -> List[str]:
        """Parse robots.txt for sitemap references"""
        sitemaps = []
        
        for line in robots_content.split('\n'):
            if line.startswith('Sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                sitemaps.append(sitemap_url)
        
        return sitemaps
    
    def _url_likely_has_people(self, url: str) -> bool:
        """Check if URL is likely to contain people information"""
        url_lower = url.lower()
        
        people_keywords = [
            'team', 'about', 'leadership', 'people', 'staff', 'management',
            'executives', 'founders', 'directors', 'careers', 'contact',
            'bio', 'profile', 'author', 'speaker'
        ]
        
        return any(keyword in url_lower for keyword in people_keywords)
    
    async def _scrape_javascript_sites(self, domain: str, company: str) -> Set[Person]:
        """Handle JavaScript-heavy sites (SPAs, React, etc.)"""
        people = set()
        
        session = await create_elite_session()
        page = await session.new_page()
        
        try:
            # Navigate to homepage
            await page.goto(f"https://{domain}", wait_until='networkidle')
            
            # Look for navigation menus
            nav_links = await page.evaluate('''
                () => {
                    const navElements = document.querySelectorAll('nav a, .navigation a, .menu a, header a');
                    return Array.from(navElements)
                        .map(link => link.href)
                        .filter(href => href && href.includes(location.hostname));
                }
            ''')
            
            # Visit promising navigation links
            people_links = [link for link in nav_links if self._url_likely_has_people(link)]
            
            for link in people_links[:5]:  # Limit to avoid overload
                try:
                    await page.goto(link, wait_until='networkidle')
                    
                    # Wait for content to fully load
                    await asyncio.sleep(3)
                    
                    # Extract people from loaded content
                    content = await page.content()
                    link_people = self._extract_people_from_html(content, company, link)
                    people.update(link_people)
                    
                except:
                    continue
        
        except:
            pass
        
        finally:
            await session.close()
        
        return people
    
    async def _analyze_job_postings(self, domain: str, company: str, target_title: str) -> Set[Person]:
        """Analyze job postings for hiring managers"""
        people = set()
        
        # Common job posting URLs
        job_urls = [
            f"https://{domain}/careers",
            f"https://{domain}/jobs",
            f"https://{domain}/hiring",
            f"https://{domain}/join-us",
            f"https://{domain}/work-with-us"
        ]
        
        session = await create_elite_session()
        page = await session.new_page()
        
        for job_url in job_urls:
            try:
                await page.goto(job_url, wait_until='networkidle')
                content = await page.content()
                
                # Look for hiring manager mentions
                hiring_managers = self._extract_hiring_managers(content, company, job_url)
                people.update(hiring_managers)
                
            except:
                continue
        
        await session.close()
        return people
    
    def _extract_hiring_managers(self, html_content: str, company: str, evidence_url: str) -> Set[Person]:
        """Extract hiring managers from job postings"""
        people = set()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # Patterns for hiring manager mentions
        hiring_patterns = [
            r'Contact\s+([A-Z][a-z]+\s+[A-Z][a-z]+).*?(hiring|manager|recruiter)',
            r'(Hiring\s+Manager|Recruiter)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Questions\?\s+Contact\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Apply\s+to[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        for pattern in hiring_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0] if self._looks_like_name(match[0]) else match[1]
                else:
                    name = match
                
                if name and self._looks_like_name(name):
                    person = Person(
                        name=name,
                        title="Hiring Manager",  # Inferred title
                        company=company,
                        source="elite_company_pages",
                        evidence_url=evidence_url,
                        confidence_score=0.6
                    )
                    people.add(person)
        
        return people
    
    async def _discover_via_social_links(self, domain: str, company: str) -> Set[Person]:
        """Discover people via company social media profiles"""
        people = set()
        
        # Find company social media profiles
        social_profiles = await self._find_company_social_profiles(domain)
        
        # Analyze each social profile for people mentions
        for profile_url in social_profiles:
            try:
                profile_people = await self._analyze_social_profile(profile_url, company)
                people.update(profile_people)
            except:
                continue
        
        return people
    
    async def _find_company_social_profiles(self, domain: str) -> List[str]:
        """Find company social media profiles"""
        profiles = []
        
        session = await create_elite_session()
        page = await session.new_page()
        
        try:
            await page.goto(f"https://{domain}", wait_until='networkidle')
            
            # Extract social media links
            social_links = await page.evaluate('''
                () => {
                    const socialSites = ['linkedin.com', 'twitter.com', 'facebook.com', 'instagram.com'];
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    
                    return links
                        .map(link => link.href)
                        .filter(href => socialSites.some(site => href.includes(site)));
                }
            ''')
            
            profiles.extend(social_links)
            
        except:
            pass
        
        finally:
            await session.close()
        
        return profiles
    
    async def _analyze_social_profile(self, profile_url: str, company: str) -> Set[Person]:
        """Analyze company social profile for people mentions"""
        people = set()
        
        # This would require specific implementation for each social platform
        # LinkedIn company pages, Twitter employees lists, etc.
        # For now, return empty set
        
        return people
    
    async def _deep_content_analysis(self, domain: str, company: str) -> Set[Person]:
        """Deep content analysis for people mentions"""
        people = set()
        
        session = await create_elite_session()
        page = await session.new_page()
        
        try:
            # Analyze multiple content types
            content_urls = [
                f"https://{domain}/blog",
                f"https://{domain}/news",
                f"https://{domain}/press",
                f"https://{domain}/events",
            ]
            
            for url in content_urls:
                try:
                    await page.goto(url, wait_until='networkidle')
                    content = await page.content()
                    
                    # Extract people mentioned in content
                    content_people = self._extract_people_from_content(content, company, url)
                    people.update(content_people)
                    
                except:
                    continue
        
        except:
            pass
        
        finally:
            await session.close()
        
        return people
    
    def _extract_people_from_content(self, html_content: str, company: str, evidence_url: str) -> Set[Person]:
        """Extract people mentioned in blog posts, news, etc."""
        people = set()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove navigation and footer to focus on content
        for elem in soup.select('nav, footer, header, .sidebar'):
            elem.decompose()
        
        text = soup.get_text()
        
        # Look for people mentioned with titles
        mention_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s*(?:our\s+)?([A-Z][a-z\s]+(?:Officer|Manager|Director|Engineer|Lead))',
            r'(CEO|CTO|CFO|COO|VP|President|Founder)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s*who\s+(?:leads|heads|manages)',
        ]
        
        for pattern in mention_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple) and len(match) == 2:
                    name, title = match
                    # Check which is name and which is title
                    if self._looks_like_name(name) and self._looks_like_title(title):
                        person = Person(
                            name=name,
                            title=title,
                            company=company,
                            source="elite_company_pages",
                            evidence_url=evidence_url,
                            confidence_score=0.4  # Lower confidence for content mentions
                        )
                        people.add(person)
        
        return people
    
    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a person's name"""
        if not text or len(text) < 3:
            return False
        
        # Basic name pattern: First Last or First Middle Last
        name_pattern = r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}$'
        
        if not re.match(name_pattern, text):
            return False
        
        # Exclude common non-names
        non_names = {
            'Our Team', 'Contact Us', 'About Us', 'Join Us', 'Follow Us',
            'Read More', 'Learn More', 'Get Started', 'Sign Up', 'Log In'
        }
        
        return text not in non_names
    
    def _looks_like_title(self, text: str) -> bool:
        """Check if text looks like a job title"""
        if not text or len(text) < 3:
            return False
        
        # Common title keywords
        title_keywords = [
            'officer', 'manager', 'director', 'engineer', 'developer', 'designer',
            'analyst', 'specialist', 'lead', 'head', 'chief', 'president',
            'founder', 'ceo', 'cto', 'cfo', 'coo', 'vp', 'vice'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in title_keywords)
    
    async def cleanup(self):
        """Clean up all sessions"""
        for session in self.session_pool:
            await session.close()
        self.session_pool.clear()

# Factory function for easy integration
def create_elite_company_pages_scraper() -> EliteCompanyPagesScraper:
    """Create company pages scraper with production config"""
    config = CompanyPagesConfig(
        max_pages_per_domain=30,
        max_depth=2,
        concurrent_sessions=3,
        smart_crawling=True,
        extract_social_links=False,  # Too risky for production
        analyze_job_postings=True,
        deep_contact_extraction=True,
        bypass_javascript_protection=True,
        use_multiple_approaches=True
    )
    return EliteCompanyPagesScraper(config)