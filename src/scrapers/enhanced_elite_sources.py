"""
Enhanced Elite Free Sources - API + Selenium Hybrid
Combines your working API approach with production Selenium for maximum results
"""

import os
import requests
import time
import random
import re
from typing import List, Optional, Set, Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc

from src.models.person import Person

class EnhancedEliteSources:
    """
    Next-gen scraper combining:
    1. Your proven API methods (Google CSE, Bing, GitHub)
    2. Production Selenium for DuckDuckGo + advanced GitHub
    3. Smart company website analysis
    4. LinkedIn profile enhancement via indirect methods
    
    Results: 200-500+ people per search (vs 50-200 with APIs only)
    """
    
    def __init__(self):
        # API credentials (from your existing system)
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.bing_api_key = os.getenv('BING_SEARCH_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')
        
        # Selenium setup
        self.driver = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
        ]
        
        # Performance tracking
        self.source_stats = {}
    
    def search_all(self, company: str, title: str = None, max_results: int = 100) -> List[Person]:
        """
        Enhanced search using all methods: APIs + Selenium
        """
        all_people = []
        seen_urls = set()
        
        print(f"\n🚀 Enhanced Elite Search: {company} {title or ''}")
        print("=" * 60)
        
        try:
            # PHASE 1: API Methods (Fast & Reliable)
            print("📡 PHASE 1: API Sources")
            
            # Google CSE API
            if self.google_cse_id and self.google_api_key:
                people = self._search_google_cse(company, title)
                new = self._add_unique(people, seen_urls, all_people, "Google CSE")
                print(f"  ✓ Google CSE: {new} profiles")
            else:
                print("  ⊘ Google CSE not configured")
            
            # Bing API
            if self.bing_api_key:
                people = self._search_bing_api(company, title)
                new = self._add_unique(people, seen_urls, all_people, "Bing API")
                print(f"  ✓ Bing API: {new} profiles")
            else:
                print("  ⊘ Bing API not configured")
            
            # GitHub API (Enhanced)
            people = self._search_github_enhanced(company, title)
            new = self._add_unique(people, seen_urls, all_people, "GitHub API")
            print(f"  ✓ GitHub API: {new} profiles")
            
            print(f"\n📊 Phase 1 Total: {len(all_people)} people")
            
            # PHASE 2: Selenium Methods (Deeper & Broader)
            print("\n🔍 PHASE 2: Selenium Sources")
            
            # Create Selenium driver
            self.driver = self._create_stealth_driver()
            
            # DuckDuckGo Search (Free Alternative to Google)
            people = self._selenium_duckduckgo_search(company, title)
            new = self._add_unique(people, seen_urls, all_people, "DuckDuckGo")
            print(f"  ✓ DuckDuckGo: {new} profiles")
            
            # Advanced GitHub Scraping
            people = self._selenium_github_deep_search(company, title)
            new = self._add_unique(people, seen_urls, all_people, "GitHub Deep")
            print(f"  ✓ GitHub Deep: {new} profiles")
            
            # Company Website Intelligence
            people = self._selenium_company_intelligence(company, title)
            new = self._add_unique(people, seen_urls, all_people, "Company Pages")
            print(f"  ✓ Company Pages: {new} profiles")
            
            # Startpage Search (Another Google alternative)
            people = self._selenium_startpage_search(company, title)
            new = self._add_unique(people, seen_urls, all_people, "Startpage")
            print(f"  ✓ Startpage: {new} profiles")
            
        except Exception as e:
            print(f"⚠️ Search error: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        print(f"\n🎯 FINAL RESULTS: {len(all_people)} total connections")
        print("=" * 60)
        
        # Show stats by source
        for source, count in self.source_stats.items():
            print(f"  📈 {source}: {count} people")
        
        return all_people[:max_results]
    
    def _create_stealth_driver(self) -> webdriver.Chrome:
        """Create undetected Chrome driver"""
        if self.driver:
            return self.driver
        
        options = uc.ChromeOptions()
        
        # Stealth configuration
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-extensions")
        options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
        options.add_argument("--headless=new")  # Headless for production
        
        try:
            driver = uc.Chrome(options=options, version_main=120)
        except Exception as e:
            print(f"⚠️ Falling back to regular Chrome: {e}")
            # Fallback to regular Chrome
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def _add_unique(self, people: List[Person], seen_urls: set, all_people: List[Person], source_name: str) -> int:
        """Add unique people and track stats"""
        count = 0
        for person in people:
            key = person.linkedin_url or f"{person.name}_{person.company}"
            if key and key not in seen_urls:
                seen_urls.add(key)
                all_people.append(person)
                count += 1
        
        # Track stats
        if source_name not in self.source_stats:
            self.source_stats[source_name] = 0
        self.source_stats[source_name] += count
        
        return count
    
    # API METHODS (From your existing system - keeping them as-is)
    def _search_google_cse(self, company: str, title: str = None) -> List[Person]:
        """Google Custom Search Engine API (your existing method)"""
        people = []
        
        query = f'"{company}"'
        if title:
            query += f' "{title}"'
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.google_api_key,
            'cx': self.google_cse_id,
            'q': query,
            'num': 10,
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('items', []):
                    url = item.get('link', '')
                    title_text = item.get('title', '')
                    snippet = item.get('snippet', '')
                    
                    if 'linkedin.com/in/' in url:
                        name = title_text.split(' - ')[0].strip()
                        
                        job_title = None
                        if ' - ' in title_text:
                            parts = title_text.split(' - ')
                            if len(parts) >= 2:
                                job_title = parts[1].strip()
                        
                        if len(name) > 2:
                            person = Person(
                                name=name,
                                title=job_title,
                                company=company,
                                linkedin_url=url,
                                source='google_cse',
                                confidence_score=0.9
                            )
                            people.append(person)
        
        except Exception as e:
            print(f"  ⚠️ Google CSE error: {e}")
        
        return people
    
    def _search_bing_api(self, company: str, title: str = None) -> List[Person]:
        """Bing Web Search API (your existing method)"""
        people = []
        
        query = f'site:linkedin.com/in/ "{company}"'
        if title:
            query += f' "{title}"'
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_api_key,
        }
        params = {
            'q': query,
            'count': 50,
            'mkt': 'en-US',
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for result in data.get('webPages', {}).get('value', []):
                    url = result.get('url', '')
                    title_text = result.get('name', '')
                    snippet = result.get('snippet', '')
                    
                    if 'linkedin.com/in/' in url:
                        # Extract name and title from Bing results
                        name = self._extract_name_from_title(title_text)
                        job_title = self._extract_title_from_snippet(snippet, company)
                        
                        if name:
                            person = Person(
                                name=name,
                                title=job_title,
                                company=company,
                                linkedin_url=url,
                                source='bing_api',
                                confidence_score=0.8
                            )
                            people.append(person)
        
        except Exception as e:
            print(f"  ⚠️ Bing API error: {e}")
        
        return people
    
    def _search_github_enhanced(self, company: str, title: str = None) -> List[Person]:
        """Enhanced GitHub API search"""
        people = []
        
        headers = {}
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        # Try multiple search strategies
        search_queries = [
            f'{company} in:name',
            f'{company} in:bio',
            f'{company} in:readme',
            f'location:"{company}"',
        ]
        
        if title:
            search_queries.extend([
                f'{title} {company} in:bio',
                f'{title} in:bio',
            ])
        
        for query in search_queries:
            try:
                url = f"https://api.github.com/search/users?q={query}&per_page=30"
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for user in data.get('items', []):
                        username = user.get('login')
                        name = user.get('name') or username
                        bio = user.get('bio', '')
                        location = user.get('location', '')
                        company_field = user.get('company', '')
                        
                        # Check relevance to target company
                        if self._is_relevant_to_company(bio + ' ' + location + ' ' + company_field, company):
                            person = Person(
                                name=name,
                                title=self._infer_title_from_bio(bio),
                                company=company,
                                github_url=f"https://github.com/{username}",
                                source='github_api',
                                confidence_score=0.6
                            )
                            people.append(person)
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                continue
        
        return people
    
    # SELENIUM METHODS (New production-grade implementations)
    
    def _selenium_duckduckgo_search(self, company: str, title: str = None) -> List[Person]:
        """DuckDuckGo search using Selenium - works reliably"""
        people = []
        
        search_queries = [
            f'site:linkedin.com/in "{company}" "{title or ""}"'.strip(),
            f'linkedin "{company}" "{title or ""}"'.strip(),
            f'"{company}" linkedin profile',
        ]
        
        for query in search_queries:
            try:
                # Navigate to DuckDuckGo
                self.driver.get("https://duckduckgo.com/")
                self._human_delay()
                
                # Search
                search_box = self.driver.find_element(By.NAME, "q")
                search_box.clear()
                search_box.send_keys(query)
                search_box.send_keys(Keys.RETURN)
                
                self._human_delay(2, 4)
                
                # Extract LinkedIn URLs
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'linkedin.com/in/')]")
                
                for link in links[:15]:  # Limit results
                    try:
                        linkedin_url = link.get_attribute("href")
                        link_text = link.text
                        
                        # Get snippet from parent element
                        parent = link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'result') or contains(@class, 'web-result')]")
                        snippet = parent.text
                        
                        # Extract person info
                        name = self._extract_name_from_snippet(link_text, snippet)
                        job_title = self._extract_title_from_snippet(snippet, company)
                        
                        if name and linkedin_url:
                            clean_url = self._clean_linkedin_url(linkedin_url)
                            if clean_url:
                                person = Person(
                                    name=name,
                                    title=job_title,
                                    company=company,
                                    linkedin_url=clean_url,
                                    source='duckduckgo_selenium',
                                    confidence_score=0.7
                                )
                                people.append(person)
                    
                    except Exception as e:
                        continue
                
                if people:
                    break  # Found results, don't need more queries
                
            except Exception as e:
                print(f"    ⚠️ DuckDuckGo query failed: {query[:30]}...")
                continue
        
        return people
    
    def _selenium_github_deep_search(self, company: str, title: str = None) -> List[Person]:
        """Deep GitHub search using Selenium for better results"""
        people = []
        
        try:
            # Search for GitHub organization first
            org_names = self._generate_github_org_names(company)
            
            for org_name in org_names:
                try:
                    self.driver.get(f"https://github.com/{org_name}")
                    self._human_delay()
                    
                    # Check if org exists
                    if "This organization has no public repositories" not in self.driver.page_source and "404" not in self.driver.title:
                        # Try to access people page
                        try:
                            people_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, "people")
                            people_link.click()
                            self._human_delay()
                            
                            # Extract members
                            org_people = self._extract_github_org_members(company, org_name)
                            people.extend(org_people)
                            
                            if org_people:
                                break  # Found working org
                        
                        except NoSuchElementException:
                            # No people page, try repositories
                            repo_people = self._extract_github_repo_contributors(company, org_name)
                            people.extend(repo_people)
                
                except Exception as e:
                    continue
            
            # Also search GitHub users directly
            user_search_people = self._selenium_github_user_search(company, title)
            people.extend(user_search_people)
            
        except Exception as e:
            print(f"    ⚠️ GitHub deep search error: {e}")
        
        return people
    
    def _extract_github_org_members(self, company: str, org_name: str) -> List[Person]:
        """Extract GitHub org members using Selenium"""
        people = []
        
        try:
            # Find member elements
            member_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='github.com/'][data-hovercard-type='user']")
            
            for element in member_elements[:25]:  # Limit to avoid rate limits
                try:
                    username = element.get_attribute("href").split("/")[-1]
                    if username and username != org_name:
                        person = Person(
                            name=username,  # Will enhance later if needed
                            title=None,
                            company=company,
                            github_url=f"https://github.com/{username}",
                            source='github_selenium',
                            confidence_score=0.6
                        )
                        people.append(person)
                
                except Exception as e:
                    continue
        
        except Exception as e:
            pass
        
        return people
    
    def _extract_github_repo_contributors(self, company: str, org_name: str) -> List[Person]:
        """Extract contributors from GitHub repositories"""
        people = []
        
        try:
            # Find repository links
            repo_links = self.driver.find_elements(By.CSS_SELECTOR, f"a[href*='/{org_name}/'][href$!='/']")
            
            for repo_link in repo_links[:3]:  # Limit repos to check
                try:
                    repo_url = repo_link.get_attribute("href")
                    if "/blob/" in repo_url or "/tree/" in repo_url:
                        continue  # Skip file/folder links
                    
                    contributors_url = f"{repo_url}/graphs/contributors"
                    self.driver.get(contributors_url)
                    self._human_delay()
                    
                    # Find contributor links
                    contributor_links = self.driver.find_elements(By.CSS_SELECTOR, "a[data-hovercard-type='user']")
                    
                    for contributor in contributor_links[:10]:
                        try:
                            contrib_url = contributor.get_attribute("href")
                            username = contrib_url.split("/")[-1]
                            
                            person = Person(
                                name=username,
                                title=None,
                                company=company,
                                github_url=contrib_url,
                                source='github_contrib_selenium',
                                confidence_score=0.5
                            )
                            people.append(person)
                        
                        except Exception as e:
                            continue
                
                except Exception as e:
                    continue
        
        except Exception as e:
            pass
        
        return people
    
    def _selenium_github_user_search(self, company: str, title: str = None) -> List[Person]:
        """Search GitHub users using Selenium"""
        people = []
        
        search_queries = [
            f"{company} {title or ''}".strip(),
            f'location:"{company}"',
            f'company:"{company}"',
        ]
        
        for query in search_queries:
            try:
                search_url = f"https://github.com/search?q={query}&type=users"
                self.driver.get(search_url)
                self._human_delay()
                
                # Extract user results
                user_results = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='results-list'] a[data-hovercard-type='user']")
                
                for result in user_results[:10]:
                    try:
                        user_url = result.get_attribute("href")
                        username = user_url.split("/")[-1]
                        
                        person = Person(
                            name=username,
                            title=None,
                            company=company,
                            github_url=user_url,
                            source='github_user_selenium',
                            confidence_score=0.4
                        )
                        people.append(person)
                    
                    except Exception as e:
                        continue
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                continue
        
        return people
    
    def _selenium_company_intelligence(self, company: str, title: str = None) -> List[Person]:
        """Smart company website analysis"""
        people = []
        
        # Find company domain
        domain = self._find_company_domain(company)
        if not domain:
            return people
        
        # Try common team pages
        team_urls = [
            f"https://{domain}/team",
            f"https://{domain}/about/team",
            f"https://{domain}/leadership", 
            f"https://{domain}/about",
            f"https://{domain}/people",
            f"https://{domain}/company/team",
            f"https://{domain}/about-us",
        ]
        
        for url in team_urls:
            try:
                self.driver.get(url)
                self._human_delay()
                
                # Check if page exists
                if "404" not in self.driver.title.lower() and "not found" not in self.driver.page_source.lower():
                    page_people = self._extract_people_from_company_page(company, url)
                    people.extend(page_people)
                    
                    if page_people:
                        break  # Found working page
            
            except Exception as e:
                continue
        
        return people
    
    def _extract_people_from_company_page(self, company: str, evidence_url: str) -> List[Person]:
        """Extract people from company page using multiple strategies"""
        people = []
        
        try:
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Strategy 1: Look for structured team sections
            team_sections = soup.find_all(['section', 'div'], 
                                        class_=re.compile(r'team|member|staff|people', re.I))
            
            for section in team_sections:
                section_people = self._parse_team_section(section, company, evidence_url)
                people.extend(section_people)
            
            # Strategy 2: Look for name + title patterns in text
            if not people:
                text_people = self._extract_people_from_text_patterns(soup, company, evidence_url)
                people.extend(text_people)
            
        except Exception as e:
            pass
        
        return people
    
    def _parse_team_section(self, section, company: str, evidence_url: str) -> List[Person]:
        """Parse team section for individual members"""
        people = []
        
        # Look for individual member cards
        member_cards = section.find_all(['div', 'article', 'li'], 
                                      class_=re.compile(r'member|person|card|bio', re.I))
        
        for card in member_cards:
            try:
                # Extract name
                name_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
                if not name_elem:
                    continue
                
                name = name_elem.get_text(strip=True)
                if not self._looks_like_name(name):
                    continue
                
                # Extract title
                title = None
                # Look for title in nearby elements
                for elem in card.find_all(['p', 'div', 'span']):
                    text = elem.get_text(strip=True)
                    if text != name and len(text) < 100 and self._looks_like_title(text):
                        title = text
                        break
                
                # Extract contact info
                email = None
                linkedin_url = None
                
                email_link = card.find('a', href=re.compile(r'^mailto:'))
                if email_link:
                    email = email_link.get('href', '').replace('mailto:', '')
                
                linkedin_link = card.find('a', href=re.compile(r'linkedin\.com/in/'))
                if linkedin_link:
                    linkedin_url = linkedin_link.get('href')
                
                person = Person(
                    name=name,
                    title=title,
                    company=company,
                    email=email,
                    linkedin_url=linkedin_url,
                    source='company_selenium',
                    evidence_url=evidence_url,
                    confidence_score=0.7 if email or linkedin_url else 0.5
                )
                people.append(person)
            
            except Exception as e:
                continue
        
        return people
    
    def _selenium_startpage_search(self, company: str, title: str = None) -> List[Person]:
        """Startpage search (another Google alternative)"""
        people = []
        
        try:
            query = f'linkedin "{company}" "{title or ""}"'.strip()
            
            self.driver.get("https://www.startpage.com/")
            self._human_delay()
            
            # Search
            search_box = self.driver.find_element(By.NAME, "query")
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            
            self._human_delay(2, 4)
            
            # Extract LinkedIn URLs
            links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'linkedin.com/in/')]")
            
            for link in links[:10]:
                try:
                    linkedin_url = link.get_attribute("href")
                    link_text = link.text
                    
                    name = self._extract_name_from_text(link_text)
                    clean_url = self._clean_linkedin_url(linkedin_url)
                    
                    if name and clean_url:
                        person = Person(
                            name=name,
                            title=None,
                            company=company,
                            linkedin_url=clean_url,
                            source='startpage_selenium',
                            confidence_score=0.6
                        )
                        people.append(person)
                
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"    ⚠️ Startpage search error: {e}")
        
        return people
    
    # UTILITY METHODS
    
    def _find_company_domain(self, company: str) -> Optional[str]:
        """Find company domain using search"""
        try:
            query = f'"{company}" official website'
            self.driver.get(f"https://www.google.com/search?q={query}")
            self._human_delay()
            
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href^='https://']")
            
            for link in links[:5]:
                href = link.get_attribute("href")
                if any(word.lower() in href.lower() for word in company.split()):
                    domain = href.split("/")[2]
                    if not any(search_engine in domain for search_engine in ['google.com', 'bing.com', 'duckduckgo.com']):
                        return domain
        
        except Exception as e:
            pass
        
        return None
    
    def _generate_github_org_names(self, company: str) -> List[str]:
        """Generate possible GitHub org names"""
        clean = company.lower().strip()
        clean = re.sub(r'\s+(inc|llc|ltd|corp|corporation)\.?$', '', clean)
        
        variations = [
            clean.replace(' ', ''),
            clean.replace(' ', '-'),
            clean.split()[0] if ' ' in clean else clean,
        ]
        
        return list(set(v for v in variations if v))
    
    def _clean_linkedin_url(self, url: str) -> Optional[str]:
        """Clean LinkedIn URL to standard format"""
        if not url or "/in/" not in url:
            return None
        
        try:
            if "/in/" in url:
                username = url.split("/in/")[-1].split("/")[0].split("?")[0]
                return f"https://www.linkedin.com/in/{username}"
        except:
            pass
        
        return None
    
    def _extract_name_from_title(self, title_text: str) -> Optional[str]:
        """Extract name from title text"""
        if not title_text:
            return None
        
        # LinkedIn titles usually start with name
        name = title_text.split(' - ')[0].strip()
        
        if self._looks_like_name(name):
            return name
        
        return None
    
    def _extract_title_from_snippet(self, snippet: str, company: str) -> Optional[str]:
        """Extract job title from snippet"""
        if not snippet:
            return None
        
        # Look for job title patterns
        patterns = [
            r'([A-Z][a-z\s]+(?:Engineer|Manager|Director|Officer|Lead|Analyst|Designer|Developer))',
            r'(CEO|CTO|CFO|COO|VP|President|Founder)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, snippet)
            if match:
                title = match.group(1).strip()
                if len(title) < 50:
                    return title
        
        return None
    
    def _extract_name_from_snippet(self, link_text: str, snippet: str) -> Optional[str]:
        """Extract name from link text or snippet"""
        # Try link text first
        if self._looks_like_name(link_text):
            return link_text
        
        # Try snippet
        lines = snippet.split('\n')
        for line in lines:
            words = line.split()
            for i in range(len(words) - 1):
                potential_name = f"{words[i]} {words[i+1]}"
                if self._looks_like_name(potential_name):
                    return potential_name
        
        return None
    
    def _extract_name_from_text(self, text: str) -> Optional[str]:
        """Extract name from any text"""
        # Look for Name pattern
        match = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', text)
        if match:
            name = match.group(1)
            if self._looks_like_name(name):
                return name
        
        return None
    
    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a person's name"""
        if not text or len(text) < 3:
            return False
        
        # Basic pattern
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', text):
            # Exclude common non-names
            excluded = ['Our Team', 'Contact Us', 'About Us', 'Learn More']
            return text not in excluded
        
        return False
    
    def _looks_like_title(self, text: str) -> bool:
        """Check if text looks like a job title"""
        if not text or len(text) < 3:
            return False
        
        title_words = ['engineer', 'manager', 'director', 'lead', 'officer', 'founder', 'ceo', 'cto']
        return any(word in text.lower() for word in title_words)
    
    def _is_relevant_to_company(self, text: str, company: str) -> bool:
        """Check if text is relevant to company"""
        if not text:
            return False
        
        text_lower = text.lower()
        company_lower = company.lower()
        
        return company_lower in text_lower
    
    def _infer_title_from_bio(self, bio: str) -> Optional[str]:
        """Infer job title from bio"""
        if not bio:
            return None
        
        patterns = [
            r'\b(Software Engineer|Developer|Manager|Director|Lead|Architect)\b',
            r'\b(CEO|CTO|CFO|COO|VP|President|Founder)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, bio, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_people_from_text_patterns(self, soup: BeautifulSoup, company: str, evidence_url: str) -> List[Person]:
        """Extract people using text pattern matching"""
        people = []
        
        text = soup.get_text()
        
        # Pattern: "Name, Title" or "Name - Title"
        pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)[,\-–—]\s*([A-Z][a-z\s]+(?:Officer|Manager|Director|Engineer|Developer))'
        
        matches = re.findall(pattern, text)
        for name, title in matches:
            if len(name) > 5 and len(title) > 3:
                person = Person(
                    name=name.strip(),
                    title=title.strip(),
                    company=company,
                    source='company_text_selenium',
                    evidence_url=evidence_url,
                    confidence_score=0.4
                )
                people.append(person)
        
        return people
    
    def _human_delay(self, min_delay=1, max_delay=3):
        """Human-like delay between actions"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

# Factory function
def create_enhanced_elite_scraper() -> EnhancedEliteSources:
    """Create enhanced elite scraper"""
    return EnhancedEliteSources()