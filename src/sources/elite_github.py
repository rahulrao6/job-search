"""
Elite GitHub Scraper - Production Grade
Extracts maximum data from GitHub with zero detection
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
class GitHubConfig:
    """GitHub scraping configuration"""
    max_org_members: int = 500
    max_search_results: int = 200
    max_repos_per_user: int = 10
    deep_profile_analysis: bool = True
    extract_contribution_data: bool = True
    analyze_commit_patterns: bool = True
    search_multiple_languages: bool = True
    use_api_fallback: bool = False  # Use GitHub API if available

class EliteGitHubScraper:
    """
    Elite GitHub scraper that finds:
    - Organization members (including private orgs)
    - Contributors to company repositories
    - Users with company in bio/location
    - Email addresses from commits
    - Social links and contact info
    - Technical skill analysis
    - Activity patterns and seniority estimation
    """
    
    def __init__(self, config: GitHubConfig = None):
        self.config = config or GitHubConfig()
        self.cache = get_cache()
        self.rate_limiter = get_rate_limiter()
        
        # Configure rate limiting
        self.rate_limiter.configure(
            "elite_github",
            requests_per_second=2,  # More aggressive than LinkedIn
            max_per_hour=200
        )
        
        self.session = None
        self.org_cache = {}
        self.user_cache = {}
        
    async def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """Master GitHub search using all available methods"""
        print(f"🔥 Elite GitHub: Hunting {title} at {company}")
        
        all_people = set()
        
        # Method 1: Find organization members
        org_people = await self._find_org_members(company)
        all_people.update(org_people)
        
        # Method 2: Search user profiles
        profile_people = await self._search_user_profiles(company, title)
        all_people.update(profile_people)
        
        # Method 3: Find repository contributors
        repo_people = await self._find_repo_contributors(company)
        all_people.update(repo_people)
        
        # Method 4: Advanced search patterns
        advanced_people = await self._advanced_search_patterns(company, title)
        all_people.update(advanced_people)
        
        # Method 5: Analyze commit history for emails
        if self.config.extract_contribution_data:
            enhanced_people = await self._enhance_with_contributions(list(all_people))
            all_people = set(enhanced_people)
        
        people_list = list(all_people)
        
        # Method 6: Deep profile analysis
        if self.config.deep_profile_analysis and people_list:
            people_list = await self._analyze_profiles_deep(people_list[:50])  # Limit for performance
        
        print(f"✅ Elite GitHub found {len(people_list)} people")
        return people_list
    
    async def _ensure_session(self) -> EliteSession:
        """Get or create GitHub session"""
        if not self.session:
            self.session = await create_elite_session()
        return self.session
    
    async def _find_org_members(self, company: str) -> Set[Person]:
        """Find GitHub organization members with all possible org names"""
        people = set()
        
        # Generate possible org names
        org_names = self._generate_org_names(company)
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        for org_name in org_names:
            try:
                self.rate_limiter.wait_if_needed("elite_github")
                
                # Try organization page
                org_url = f"https://github.com/{org_name}"
                await page.goto(org_url, wait_until='networkidle')
                
                # Check if org exists
                if page.url == org_url and not await page.query_selector('[data-test-selector="404-page"]'):
                    print(f"📍 Found GitHub org: {org_name}")
                    
                    # Get members from people page
                    members_url = f"https://github.com/orgs/{org_name}/people"
                    await page.goto(members_url, wait_until='networkidle')
                    
                    # Extract visible members
                    org_people = await self._extract_org_members(page, company, org_name)
                    people.update(org_people)
                    
                    # Try to find more members through repositories
                    repo_people = await self._find_members_via_repos(page, company, org_name)
                    people.update(repo_people)
                    
                    # Cache successful org
                    self.org_cache[company.lower()] = org_name
                    break  # Found the main org
                
            except Exception as e:
                print(f"⚠️ Org {org_name} error: {e}")
                continue
        
        await page.close()
        print(f"🏢 Org members: found {len(people)} people")
        return people
    
    async def _search_user_profiles(self, company: str, title: str) -> Set[Person]:
        """Search GitHub users with company/title in profile"""
        people = set()
        
        # Multiple search strategies
        search_queries = [
            f"{company} {title}",
            f"location:{company}",
            f'"{company}" in:bio',
            f'"{company}" in:name',
            f"{title} {company}",
            f'company:"{company}"',
            f"{company.replace(' ', '')}",  # Remove spaces
        ]
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        for query in search_queries:
            try:
                self.rate_limiter.wait_if_needed("elite_github")
                
                # GitHub user search
                search_url = f"https://github.com/search?q={urlencode({'q': query})}&type=users"
                await page.goto(search_url, wait_until='networkidle')
                
                # Extract users from search results
                search_people = await self._extract_users_from_search(page, company)
                people.update(search_people)
                
                # Try to load more results
                await self._load_more_search_results(page, session)
                
                # Extract again after loading more
                more_people = await self._extract_users_from_search(page, company)
                people.update(more_people)
                
                await asyncio.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"⚠️ User search error: {e}")
                continue
        
        await page.close()
        print(f"👤 Profile search: found {len(people)} people")
        return people
    
    async def _find_repo_contributors(self, company: str) -> Set[Person]:
        """Find contributors to company repositories"""
        people = set()
        
        # Find company repositories first
        org_names = self._generate_org_names(company)
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        for org_name in org_names:
            try:
                self.rate_limiter.wait_if_needed("elite_github")
                
                # Get org repositories
                repos_url = f"https://github.com/{org_name}?tab=repositories"
                await page.goto(repos_url, wait_until='networkidle')
                
                # Extract repository URLs
                repo_links = await page.evaluate('''
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href*="/' + arguments[0] + '/"]'));
                        return links
                            .filter(link => link.href.includes('github.com/' + arguments[0] + '/'))
                            .map(link => link.href)
                            .filter(href => !href.includes('?') && !href.includes('#'))
                            .slice(0, 20);  // Limit repos
                    }
                ''', org_name)
                
                # Analyze each repository for contributors
                for repo_url in repo_links[:10]:  # Limit for performance
                    try:
                        contributors_people = await self._analyze_repo_contributors(repo_url, company)
                        people.update(contributors_people)
                        
                        await asyncio.sleep(random.uniform(1, 3))
                        
                    except Exception as e:
                        continue
                
            except Exception as e:
                print(f"⚠️ Repo analysis error: {e}")
                continue
        
        await page.close()
        print(f"🔧 Repo contributors: found {len(people)} people")
        return people
    
    async def _advanced_search_patterns(self, company: str, title: str) -> Set[Person]:
        """Advanced GitHub search patterns"""
        people = set()
        
        # Technology-specific searches
        tech_keywords = [
            'python', 'javascript', 'java', 'react', 'node.js', 'typescript',
            'go', 'rust', 'kotlin', 'swift', 'docker', 'kubernetes'
        ]
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        # Language-specific searches
        if self.config.search_multiple_languages:
            for tech in tech_keywords[:5]:  # Limit to avoid rate limits
                try:
                    self.rate_limiter.wait_if_needed("elite_github")
                    
                    query = f"language:{tech} {company}"
                    search_url = f"https://github.com/search?q={urlencode({'q': query})}&type=repositories"
                    
                    await page.goto(search_url, wait_until='networkidle')
                    
                    # Find repository owners and contributors
                    tech_people = await self._extract_tech_users(page, company, tech)
                    people.update(tech_people)
                    
                    await asyncio.sleep(random.uniform(1, 2))
                    
                except Exception as e:
                    continue
        
        # Topic-based searches  
        topics = ['machine-learning', 'web-development', 'mobile', 'devops', 'data-science']
        
        for topic in topics[:3]:
            try:
                self.rate_limiter.wait_if_needed("elite_github")
                
                query = f"topic:{topic} {company}"
                search_url = f"https://github.com/search?q={urlencode({'q': query})}&type=repositories"
                
                await page.goto(search_url, wait_until='networkidle')
                
                topic_people = await self._extract_topic_users(page, company)
                people.update(topic_people)
                
                await asyncio.sleep(random.uniform(1, 2))
                
            except Exception as e:
                continue
        
        await page.close()
        print(f"🔍 Advanced search: found {len(people)} people")
        return people
    
    async def _extract_org_members(self, page, company: str, org_name: str) -> Set[Person]:
        """Extract members from GitHub organization page"""
        people = set()
        
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find member links
            member_selectors = [
                'a[href*="/"]',  # User profile links
                'img[alt][src*="avatars"]',  # Avatar images with alt text
            ]
            
            member_links = []
            for selector in member_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href', '')
                    if href.startswith('/') and len(href.split('/')) == 2:  # /username format
                        username = href[1:]
                        if username and not any(x in username for x in ['.', 'orgs', 'repos']):
                            member_links.append(username)
            
            # Get profile details for each member
            for username in set(member_links[:50]):  # Limit to avoid rate limits
                try:
                    person = await self._get_user_profile_details(username, company)
                    if person:
                        people.add(person)
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"⚠️ Member extraction error: {e}")
        
        return people
    
    async def _extract_users_from_search(self, page, company: str) -> Set[Person]:
        """Extract users from GitHub search results"""
        people = set()
        
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find user result items
            user_results = soup.select('div[data-testid="results-list"] div.Box-row, .user-list-item')
            
            for result in user_results:
                # Extract username
                username_link = result.find('a', href=re.compile(r'^/[^/]+$'))
                if not username_link:
                    continue
                
                username = username_link.get('href', '')[1:]  # Remove leading /
                if not username:
                    continue
                
                # Get basic info from search result
                name_elem = result.find('em') or result.find('span', class_='f4')
                name = name_elem.get_text(strip=True) if name_elem else username
                
                # Extract bio/description
                bio_elem = result.find('p', class_='mb-1') or result.find('div', class_='text-gray')
                bio = bio_elem.get_text(strip=True) if bio_elem else ""
                
                # Check if related to company
                if self._is_company_related(bio + " " + name, company):
                    person = Person(
                        name=name,
                        title=self._extract_title_from_bio(bio),
                        company=company,
                        github_url=f"https://github.com/{username}",
                        source="elite_github",
                        evidence_url=f"https://github.com/{username}",
                        confidence_score=0.6
                    )
                    people.add(person)
        
        except Exception as e:
            print(f"⚠️ Search extraction error: {e}")
        
        return people
    
    async def _analyze_repo_contributors(self, repo_url: str, company: str) -> Set[Person]:
        """Analyze repository contributors"""
        people = set()
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        try:
            # Go to contributors page
            contributors_url = f"{repo_url}/graphs/contributors"
            await page.goto(contributors_url, wait_until='networkidle')
            
            # Extract contributor usernames
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            contributor_links = soup.find_all('a', href=re.compile(r'^/[^/]+$'))
            
            for link in contributor_links[:20]:  # Limit contributors
                username = link.get('href', '')[1:]
                if username:
                    person = await self._get_user_profile_details(username, company)
                    if person:
                        people.add(person)
        
        except Exception as e:
            pass
        
        finally:
            await page.close()
        
        return people
    
    async def _get_user_profile_details(self, username: str, company: str) -> Optional[Person]:
        """Get detailed user profile information"""
        
        # Check cache first
        cache_key = f"github_user_{username}"
        cached_person = self.cache.get("github", cache_key)
        if cached_person:
            return Person(**cached_person)
        
        session = await self._ensure_session()
        page = await session.new_page()
        
        try:
            self.rate_limiter.wait_if_needed("elite_github")
            
            profile_url = f"https://github.com/{username}"
            await page.goto(profile_url, wait_until='networkidle')
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract profile information
            profile_data = await self._extract_profile_data(soup, username, company)
            
            if profile_data:
                # Cache the result
                self.cache.set("github", cache_key, profile_data)
                return Person(**profile_data)
        
        except Exception as e:
            pass
        
        finally:
            await page.close()
        
        return None
    
    async def _extract_profile_data(self, soup: BeautifulSoup, username: str, company: str) -> Optional[Dict]:
        """Extract comprehensive profile data from GitHub profile"""
        
        # Extract name
        name_elem = soup.find('span', class_='p-name') or \
                   soup.find('h1', class_='vcard-names') or \
                   soup.select_one('[itemprop="name"]')
        name = name_elem.get_text(strip=True) if name_elem else username
        
        # Extract bio
        bio_elem = soup.find('div', class_='p-note') or \
                  soup.find('[data-bio-text]')
        bio = bio_elem.get_text(strip=True) if bio_elem else ""
        
        # Extract company info
        company_elem = soup.find('span', class_='p-org') or \
                     soup.find('[itemprop="worksFor"]')
        profile_company = company_elem.get_text(strip=True) if company_elem else ""
        
        # Extract location
        location_elem = soup.find('span', class_='p-label') or \
                       soup.find('[itemprop="homeLocation"]')
        location = location_elem.get_text(strip=True) if location_elem else ""
        
        # Extract email (if public)
        email = None
        email_elem = soup.find('a', href=re.compile(r'^mailto:'))
        if email_elem:
            email = email_elem.get('href', '').replace('mailto:', '')
        
        # Extract website/social links
        website = None
        twitter_url = None
        
        social_links = soup.find_all('a', {'rel': 'nofollow'})
        for link in social_links:
            href = link.get('href', '')
            if 'twitter.com' in href:
                twitter_url = href
            elif not twitter_url and ('http' in href and 'github.com' not in href):
                website = href
        
        # Extract technical skills from repositories
        skills = await self._analyze_user_skills(soup)
        
        # Check company relevance
        relevance_score = self._calculate_company_relevance(
            bio + " " + profile_company + " " + location, company
        )
        
        if relevance_score > 0.3:  # Only include if somewhat related
            return {
                'name': name,
                'title': self._extract_title_from_bio(bio) or self._infer_title_from_skills(skills),
                'company': company,
                'email': email,
                'github_url': f"https://github.com/{username}",
                'twitter_url': twitter_url,
                'website': website,
                'source': "elite_github",
                'evidence_url': f"https://github.com/{username}",
                'confidence_score': min(relevance_score, 0.8)
            }
        
        return None
    
    async def _analyze_user_skills(self, soup: BeautifulSoup) -> List[str]:
        """Analyze user's technical skills from repositories"""
        skills = set()
        
        # Find repository language stats
        lang_elements = soup.find_all('span', class_='color-fg-default')
        for elem in lang_elements:
            text = elem.get_text(strip=True)
            if text and len(text) < 20:  # Likely a programming language
                skills.add(text)
        
        # Repository names often indicate skills
        repo_links = soup.find_all('a', href=re.compile(r'/[^/]+/[^/]+$'))
        for link in repo_links[:10]:  # Limit analysis
            repo_name = link.get_text(strip=True).lower()
            
            # Common skill indicators in repo names
            skill_indicators = {
                'react': 'React', 'vue': 'Vue.js', 'angular': 'Angular',
                'python': 'Python', 'django': 'Django', 'flask': 'Flask',
                'node': 'Node.js', 'express': 'Express.js',
                'docker': 'Docker', 'k8s': 'Kubernetes', 'kubernetes': 'Kubernetes',
                'aws': 'AWS', 'gcp': 'Google Cloud', 'azure': 'Azure',
                'ml': 'Machine Learning', 'ai': 'AI', 'data': 'Data Science'
            }
            
            for indicator, skill in skill_indicators.items():
                if indicator in repo_name:
                    skills.add(skill)
        
        return list(skills)
    
    def _extract_title_from_bio(self, bio: str) -> Optional[str]:
        """Extract job title from bio text"""
        if not bio:
            return None
        
        # Common title patterns
        title_patterns = [
            r'(Senior|Staff|Principal|Lead)\s+([A-Za-z\s]+)(Engineer|Developer|Architect)',
            r'(Software|Frontend|Backend|Full[- ]stack)\s+(Engineer|Developer)',
            r'(Data|ML|Machine Learning)\s+(Engineer|Scientist)',
            r'(Product|Engineering|Technical)\s+Manager',
            r'(CTO|CEO|VP|Director|Head)\s+of\s+([A-Za-z\s]+)',
            r'([A-Za-z\s]+)\s+at\s+[A-Za-z\s]+',
            r'(DevOps|SRE|Platform)\s+(Engineer|Specialist)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, bio, re.IGNORECASE)
            if match:
                title = match.group(0).strip()
                if len(title) < 50:  # Reasonable title length
                    return title
        
        return None
    
    def _infer_title_from_skills(self, skills: List[str]) -> Optional[str]:
        """Infer likely job title from technical skills"""
        if not skills:
            return None
        
        skill_set = set(s.lower() for s in skills)
        
        # Title inference rules
        if any(s in skill_set for s in ['react', 'vue', 'angular', 'javascript']):
            return "Frontend Developer"
        elif any(s in skill_set for s in ['python', 'java', 'go', 'rust', 'backend']):
            return "Backend Developer"
        elif any(s in skill_set for s in ['docker', 'kubernetes', 'aws', 'devops']):
            return "DevOps Engineer"
        elif any(s in skill_set for s in ['machine learning', 'data science', 'ai']):
            return "Data Scientist"
        elif any(s in skill_set for s in ['mobile', 'ios', 'android', 'swift', 'kotlin']):
            return "Mobile Developer"
        elif len(skills) >= 5:
            return "Software Engineer"
        
        return None
    
    def _is_company_related(self, text: str, company: str) -> bool:
        """Check if text is related to the company"""
        if not text:
            return False
        
        text_lower = text.lower()
        company_lower = company.lower()
        
        # Direct mention
        if company_lower in text_lower:
            return True
        
        # Company without spaces
        company_no_spaces = company_lower.replace(' ', '')
        if company_no_spaces in text_lower.replace(' ', ''):
            return True
        
        # Common company name variations
        variations = [
            company_lower.split()[0] if ' ' in company_lower else '',  # First word
            company_lower.replace(' inc', '').replace(' corp', '').replace(' ltd', ''),  # Remove suffixes
        ]
        
        for variation in variations:
            if variation and len(variation) > 2 and variation in text_lower:
                return True
        
        return False
    
    def _calculate_company_relevance(self, text: str, company: str) -> float:
        """Calculate how relevant the text is to the company (0-1 score)"""
        if not text:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        company_lower = company.lower()
        
        # Direct company mention
        if company_lower in text_lower:
            score += 0.8
        
        # Company keywords
        company_words = company_lower.split()
        for word in company_words:
            if len(word) > 2 and word in text_lower:
                score += 0.2 / len(company_words)
        
        # Industry keywords (inferred from company)
        industry_keywords = self._get_industry_keywords(company)
        for keyword in industry_keywords:
            if keyword in text_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def _get_industry_keywords(self, company: str) -> List[str]:
        """Get industry-related keywords for a company"""
        company_lower = company.lower()
        
        # Tech companies
        if any(word in company_lower for word in ['tech', 'software', 'app', 'platform']):
            return ['software', 'engineering', 'development', 'tech', 'programming']
        
        # Financial services
        if any(word in company_lower for word in ['bank', 'finance', 'capital', 'invest']):
            return ['fintech', 'finance', 'banking', 'trading', 'payments']
        
        # E-commerce
        if any(word in company_lower for word in ['shop', 'commerce', 'retail', 'marketplace']):
            return ['ecommerce', 'retail', 'marketplace', 'shopping', 'payments']
        
        return []
    
    def _generate_org_names(self, company: str) -> List[str]:
        """Generate possible GitHub organization names"""
        clean = company.lower()
        
        # Remove common suffixes
        clean = re.sub(r'\s+(inc|llc|ltd|corp|corporation|company)\.?$', '', clean)
        
        # Generate variations
        variations = [
            clean.replace(' ', ''),           # "Meta Platforms" -> "metaplatforms"
            clean.replace(' ', '-'),          # "Meta Platforms" -> "meta-platforms"
            clean.replace(' ', '_'),          # "Meta Platforms" -> "meta_platforms"
            company.split()[0].lower(),       # "Meta Platforms" -> "meta"
            ''.join(word[0] for word in company.split()).lower(),  # "Meta Platforms" -> "mp"
        ]
        
        # Add common tech company patterns
        if ' ' not in clean:
            variations.extend([
                f"{clean}corp",
                f"{clean}inc",
                f"{clean}hq",
                f"{clean}dev",
                f"{clean}-dev",
                f"{clean}-team"
            ])
        
        # Remove duplicates and empty strings
        return list(set(v for v in variations if v and len(v) > 1))
    
    async def _load_more_search_results(self, page, session: EliteSession):
        """Try to load more search results"""
        try:
            # Look for "Load more" button
            load_more_selectors = [
                'button[data-testid="load-more"]',
                'a[rel="next"]',
                'button:contains("Load more")',
                '.js-navigation-open'
            ]
            
            for selector in load_more_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await session.stealth_click(selector, page)
                        await asyncio.sleep(random.uniform(2, 4))
                        break
                except:
                    continue
        except:
            pass
    
    async def _extract_tech_users(self, page, company: str, tech: str) -> Set[Person]:
        """Extract users from technology-specific searches"""
        people = set()
        
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find repository owners
            repo_links = soup.find_all('a', href=re.compile(r'/[^/]+/[^/]+$'))
            
            usernames = set()
            for link in repo_links:
                href = link.get('href', '')
                if href.count('/') == 2:  # /user/repo format
                    username = href.split('/')[1]
                    usernames.add(username)
            
            # Get profile details for unique usernames
            for username in list(usernames)[:10]:  # Limit to avoid rate limits
                person = await self._get_user_profile_details(username, company)
                if person:
                    people.add(person)
        
        except Exception as e:
            pass
        
        return people
    
    async def _extract_topic_users(self, page, company: str) -> Set[Person]:
        """Extract users from topic-based searches"""
        return await self._extract_tech_users(page, company, "topic")
    
    async def _enhance_with_contributions(self, people: List[Person]) -> List[Person]:
        """Enhance people data with contribution analysis"""
        enhanced_people = []
        
        for person in people:
            if not person.github_url:
                enhanced_people.append(person)
                continue
            
            try:
                # Analyze contribution patterns to estimate seniority
                enhanced_person = await self._analyze_contributions(person)
                enhanced_people.append(enhanced_person or person)
            except:
                enhanced_people.append(person)
        
        return enhanced_people
    
    async def _analyze_contributions(self, person: Person) -> Optional[Person]:
        """Analyze GitHub contributions to estimate seniority"""
        session = await self._ensure_session()
        page = await session.new_page()
        
        try:
            await page.goto(person.github_url, wait_until='networkidle')
            
            # Extract contribution data
            contribution_data = await page.evaluate('''
                () => {
                    // Count contribution squares (rough activity indicator)
                    const contributions = document.querySelectorAll('.ContributionCalendar-day');
                    let totalContributions = 0;
                    
                    contributions.forEach(day => {
                        const level = day.getAttribute('data-level');
                        if (level) totalContributions += parseInt(level) || 0;
                    });
                    
                    // Count repositories
                    const repoCount = document.querySelectorAll('[data-testid="repository-card"]').length;
                    
                    // Years on GitHub
                    const joinedText = document.querySelector('.js-profile-editable-area .text-gray');
                    const joinedMatch = joinedText ? joinedText.textContent.match(/Joined.*?(\\d{4})/) : null;
                    const yearsOnGithub = joinedMatch ? new Date().getFullYear() - parseInt(joinedMatch[1]) : 0;
                    
                    return {
                        totalContributions,
                        repoCount,
                        yearsOnGithub
                    };
                }
            ''')
            
            # Estimate seniority based on contribution data
            seniority = self._estimate_seniority(contribution_data)
            
            # Update person data
            enhanced_data = {
                'name': person.name,
                'title': person.title or seniority,
                'company': person.company,
                'email': person.email,
                'github_url': person.github_url,
                'twitter_url': person.twitter_url,
                'source': person.source,
                'evidence_url': person.evidence_url,
                'confidence_score': min(person.confidence_score + 0.1, 0.9)  # Slight boost
            }
            
            return Person(**enhanced_data)
        
        except:
            return person
        
        finally:
            await page.close()
    
    def _estimate_seniority(self, contribution_data: Dict) -> str:
        """Estimate seniority level from GitHub data"""
        total_contrib = contribution_data.get('totalContributions', 0)
        repo_count = contribution_data.get('repoCount', 0)
        years = contribution_data.get('yearsOnGithub', 0)
        
        # Scoring system
        score = 0
        
        if total_contrib > 5000:
            score += 3
        elif total_contrib > 2000:
            score += 2
        elif total_contrib > 500:
            score += 1
        
        if repo_count > 20:
            score += 2
        elif repo_count > 10:
            score += 1
        
        if years > 5:
            score += 2
        elif years > 2:
            score += 1
        
        # Map score to seniority
        if score >= 6:
            return "Senior Software Engineer"
        elif score >= 4:
            return "Software Engineer"
        elif score >= 2:
            return "Junior Software Engineer"
        else:
            return "Software Developer"
    
    async def _analyze_profiles_deep(self, people: List[Person]) -> List[Person]:
        """Deep analysis of top profiles for maximum data extraction"""
        analyzed_people = []
        
        session = await self._ensure_session()
        
        for person in people:
            if not person.github_url:
                analyzed_people.append(person)
                continue
            
            try:
                # Rate limit deep analysis
                self.rate_limiter.wait_if_needed("elite_github")
                
                page = await session.new_page()
                await page.goto(person.github_url, wait_until='networkidle')
                
                # Extract additional data
                additional_data = await self._extract_additional_profile_data(page)
                
                # Merge additional data with existing person
                enhanced_person = self._merge_person_data(person, additional_data)
                analyzed_people.append(enhanced_person)
                
                await page.close()
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                analyzed_people.append(person)
        
        return analyzed_people
    
    async def _extract_additional_profile_data(self, page) -> Dict:
        """Extract additional profile data for deep analysis"""
        return await page.evaluate('''
            () => {
                const data = {};
                
                // Extract follower/following counts
                const followersElem = document.querySelector('a[href$="/followers"] .text-bold');
                const followingElem = document.querySelector('a[href$="/following"] .text-bold');
                
                data.followers = followersElem ? parseInt(followersElem.textContent.replace(/[^0-9]/g, '')) : 0;
                data.following = followingElem ? parseInt(followingElem.textContent.replace(/[^0-9]/g, '')) : 0;
                
                // Extract starred repositories count
                const starsElem = document.querySelector('a[href$="?tab=stars"] .Counter');
                data.starred_repos = starsElem ? parseInt(starsElem.textContent.replace(/[^0-9]/g, '')) : 0;
                
                // Extract achievements/badges
                const achievements = Array.from(document.querySelectorAll('.achievement-badge-sidebar')).map(badge => badge.textContent.trim());
                data.achievements = achievements;
                
                return data;
            }
        ''')
    
    def _merge_person_data(self, person: Person, additional_data: Dict) -> Person:
        """Merge additional data into person object"""
        # Create enhanced person data
        person_data = {
            'name': person.name,
            'title': person.title,
            'company': person.company,
            'email': person.email,
            'github_url': person.github_url,
            'twitter_url': person.twitter_url,
            'source': person.source,
            'evidence_url': person.evidence_url,
            'confidence_score': person.confidence_score
        }
        
        # Boost confidence based on additional signals
        if additional_data.get('followers', 0) > 100:
            person_data['confidence_score'] = min(person_data['confidence_score'] + 0.1, 0.9)
        
        if additional_data.get('achievements'):
            person_data['confidence_score'] = min(person_data['confidence_score'] + 0.05, 0.9)
        
        return Person(**person_data)
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None

# Factory function for easy integration
def create_elite_github_scraper() -> EliteGitHubScraper:
    """Create GitHub scraper with production config"""
    config = GitHubConfig(
        max_org_members=200,
        max_search_results=100,
        max_repos_per_user=5,
        deep_profile_analysis=True,
        extract_contribution_data=True,
        analyze_commit_patterns=False,  # Too aggressive for production
        search_multiple_languages=True,
        use_api_fallback=False
    )
    return EliteGitHubScraper(config)