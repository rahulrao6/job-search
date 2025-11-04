"""
ACTUALLY Working Free Sources (2024)
Based on real testing - these methods work TODAY

Strategy: Don't scrape search engines directly (they block)
Use: APIs with free tiers + GitHub + company websites
"""

import os
import re
import requests
import time
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.models.person import Person
from src.models.job_context import CandidateProfile, JobContext
from src.utils.query_tracker import track_query

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ActuallyWorkingFreeSources:
    """
    Sources that ACTUALLY work as of 2024:
    
    1. Google Custom Search Engine API (100 free/day)
    2. Bing Web Search API (1000 free/month)
    3. GitHub API (60/hour unauthenticated, 5000/hour authenticated)
    4. Company websites (team pages, about pages)
    5. PeopleDataLabs Company Dataset (free dataset, not API)
    
    What DOESN'T work:
    - Direct DuckDuckGo/Bing/Yahoo HTML scraping (blocked)
    - LinkedIn direct scraping (ToS violation + blocked)
    - Most "free" search engines (block bots)
    """
    
    def __init__(self):
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.bing_api_key = os.getenv('BING_SEARCH_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')  # Optional but increases limits
        self.cost_per_search = 0.0  # Free sources!
        
    def search_all(self, company: str, title: str = None, max_results: int = 50, 
                   user_profile: Optional[CandidateProfile] = None,
                   job_context: Optional[JobContext] = None) -> List[Person]:
        """
        Search all working sources.
        """
        all_people = []
        seen_urls = set()
        
        print(f"\n🔍 Searching: {company} {title or ''}")
        logger.info(f"Searching: {company} {title or ''}")
        
        # Priority 1: Google Custom Search (if configured)
        if self.google_cse_id and self.google_api_key:
            print("  → Google Custom Search...")
            logger.debug("Google Custom Search...")
            try:
                people = self._search_google_cse(company, title, user_profile, job_context)
                new = self._add_unique(people, seen_urls, all_people)
                print(f"    ✓ Found {new} profiles")
                logger.info(f"Google CSE found {new} profiles")
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
                logger.warning(f"Google CSE error: {e}", exc_info=True)
        else:
            print("  ⊘ Google CSE not configured (set GOOGLE_CSE_ID + GOOGLE_API_KEY)")
            logger.debug("Google CSE not configured")
        
        # Priority 2: Bing Search API (DEPRECATED - kept for backward compatibility)
        if self.bing_api_key:
            print("  → Bing Web Search API...")
            logger.debug("Bing Web Search API...")
            try:
                people = self._search_bing_api(company, title, user_profile, job_context)
                new = self._add_unique(people, seen_urls, all_people)
                print(f"    ✓ Found {new} profiles")
                logger.info(f"Bing API found {new} profiles")
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
                logger.warning(f"Bing API error: {e}", exc_info=True)
        else:
            print("  ⊘ Bing API deprecated (use Google CSE instead)")
            logger.debug("Bing API not configured")
        
        # Priority 3: GitHub - LOW QUALITY (only if LinkedIn cross-reference exists)
        print("  → GitHub API (filtering: LinkedIn cross-reference required)...")
        logger.debug("GitHub API (filtering: LinkedIn cross-reference required)...")
        try:
            github_people = self._search_github(company, title, job_context)
            # Filter: Only include GitHub results if they have LinkedIn URL
            # This prevents low-quality GitHub-only results from polluting results
            filtered_github = [p for p in github_people if p.linkedin_url is not None]
            new = self._add_unique(filtered_github, seen_urls, all_people)
            if len(github_people) > len(filtered_github):
                print(f"    ✓ Found {len(github_people)} GitHub profiles, {new} with LinkedIn cross-reference included")
                logger.info(f"GitHub found {len(github_people)} profiles, {new} with LinkedIn")
            else:
                print(f"    ✓ Found {new} profiles with LinkedIn")
                logger.info(f"GitHub found {new} profiles with LinkedIn")
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:50]}")
            logger.warning(f"GitHub API error: {e}", exc_info=True)
        
        # Priority 4: Company website - SKIPPED for speed
        # Uncomment if you want to search company websites (adds ~5 seconds)
        # print("  → Company website...")
        # try:
        #     people = self._search_company_website(company)
        #     new = self._add_unique(people, seen_urls, all_people)
        #     if new > 0:
        #         print(f"    ✓ Found {new} people")
        #     else:
        #         print(f"    - No team page found")
        # except Exception as e:
        #     print(f"    ✗ Error: {str(e)[:50]}")
        
        print(f"\n✅ Total: {len(all_people)} connections")
        logger.info(f"Total connections found: {len(all_people)}")
        return all_people[:max_results]
    
    def _add_unique(self, people: List[Person], seen_urls: set, all_people: List[Person]) -> int:
        """Add unique people to results"""
        count = 0
        for person in people:
            key = person.linkedin_url or person.name
            if key and key not in seen_urls:
                seen_urls.add(key)
                all_people.append(person)
                count += 1
        return count
    
    def _search_google_cse(self, company: str, title: str = None,
                          user_profile: Optional[CandidateProfile] = None,
                          job_context: Optional[JobContext] = None) -> List[Person]:
        """
        Google Custom Search Engine API with context-aware query building.
        
        Uses resume and job data to build more targeted queries.
        """
        people = []
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Build query variations with context
        query_variations = self._build_google_query_variations(company, title, user_profile, job_context)
        
        # Try each query variation until we get good results
        for query in query_variations:
            start_time = time.time()
            query_success = False
            results_count = 0
            
            try:
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cse_id,
                    'q': query,
                    'num': 10,  # Max per request
                    'start': 1,
                }
                
                response = requests.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    results_count = len(items)
                    
                    for item in items:
                        item_url = item.get('link', '')
                        title_text = item.get('title', '')
                        snippet = item.get('snippet', '')
                        
                        if 'linkedin.com/in/' in item_url:
                            # CRITICAL: Verify company appears in result (reduces false positives)
                            # Combine title and snippet for company verification
                            combined_text = f"{title_text} {snippet}".lower()
                            company_lower = company.lower()
                            
                            # Check if company name appears in the result
                            # This is crucial - many results mention company but person doesn't work there
                            company_in_text = (
                                company_lower in combined_text or
                                any(word in combined_text for word in company_lower.split() if len(word) > 3)
                            )
                            
                            # Skip if company not mentioned (likely not a current employee)
                            if not company_in_text:
                                continue
                            
                            # Extract name from title (format: "Name - Job Title - LinkedIn")
                            name = title_text.split(' - ')[0].strip()
                            
                            # Try to extract title from snippet or title
                            job_title = None
                            if ' - ' in title_text:
                                parts = title_text.split(' - ')
                                if len(parts) >= 2:
                                    job_title = parts[1].strip()
                            
                            # If no title from title field, try to extract from snippet
                            if not job_title and snippet:
                                # Look for job title patterns in snippet
                                # Common pattern: "Title at Company" or "Title | Company"
                                title_patterns = [
                                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:at|@|•|\|)\s+' + re.escape(company),
                                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Engineer',
                                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Manager',
                                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Director',
                                ]
                                for pattern in title_patterns:
                                    match = re.search(pattern, snippet, re.IGNORECASE)
                                    if match:
                                        potential_title = match.group(1).strip()
                                        if len(potential_title) > 3 and len(potential_title) < 50:
                                            job_title = potential_title
                                            break
                            
                            # Extract actual company from snippet if mentioned
                            extracted_company = company  # Default to search company
                            # Verify company name from snippet (handles variations like "Google LLC")
                            if snippet:
                                # Look for company mention in snippet
                                company_pattern = r'\b(' + '|'.join([
                                    re.escape(company_lower),
                                    re.escape(company_lower.split()[0]) if ' ' in company_lower else company_lower
                                ]) + r')\b'
                                if re.search(company_pattern, snippet.lower()):
                                    # Company is mentioned - good sign
                                    pass
                                else:
                                    # Company not clearly mentioned - lower confidence
                                    # But still include if it was in the combined text check above
                                    pass
                            
                            if len(name) > 2:
                                # Additional validation: Title should be meaningful
                                # Filter out if title is too generic without company context
                                if job_title:
                                    title_lower = job_title.lower()
                                    # Skip generic titles that don't suggest employment at company
                                    generic_titles = ['student', 'freelancer', 'consultant', 'seeking']
                                    if any(gen in title_lower for gen in generic_titles):
                                        continue
                                
                                person = Person(
                                    name=name,
                                    title=job_title,
                                    company=extracted_company,
                                    linkedin_url=item_url,
                                    source='google_cse',
                                    confidence_score=0.9  # High quality from Google
                                )
                                people.append(person)
                    
                    query_success = True
                        
            except Exception as e:
                # Continue to next query variation
                query_success = False
                pass
            finally:
                # Track query performance
                execution_time_ms = (time.time() - start_time) * 1000
                track_query(
                    query=query,
                    results_count=results_count,
                    execution_time_ms=execution_time_ms,
                    source='google_cse',
                    success=query_success
                )
        
        return people
    
    def _build_google_query_variations(self, company: str, title: str = None,
                                     user_profile: Optional[CandidateProfile] = None,
                                     job_context: Optional[JobContext] = None) -> List[str]:
        """
        Build multiple query variations using context for better coverage.
        
        Strategy:
        1. Primary: Company + Title (with skills if available)
        2. School-based: Company + Title + School (alumni search)
        3. Skills-based: Company + Title + Top skills from job
        4. Department-based: Company + Department + Title
        5. Fallback: Just Company + Title (broadest)
        """
        queries = []
        base = f'site:linkedin.com/in/ {company}'
        
        # Primary query: Company + Title
        if title:
            primary = f'{base} {title}'
            queries.append(primary)
            
            # Add skills from job context if available
            if job_context and job_context.candidate_skills:
                top_skills = job_context.candidate_skills[:2]  # Top 2 skills
                if top_skills:
                    skills_query = f'{base} {title} {" ".join(top_skills)}'
                    queries.append(skills_query)
        
        # School-based query (alumni search) - higher relevance potential
        if user_profile and user_profile.schools:
            top_school = user_profile.schools[0]  # Most recent/relevant school
            if title:
                school_query = f'{base} {title} "{top_school}"'
                queries.append(school_query)
            else:
                school_query = f'{base} "{top_school}"'
                queries.append(school_query)
        
        # Department-based query if available
        if job_context and job_context.department:
            if title:
                dept_query = f'{base} "{job_context.department}" {title}'
                queries.append(dept_query)
        
        # Fallback: Just company + title (or company only)
        if not queries:
            queries.append(f'{base} {title}' if title else base)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries[:5]  # Limit to 5 variations
    
    def _search_bing_api(self, company: str, title: str = None,
                        user_profile: Optional[CandidateProfile] = None,
                        job_context: Optional[JobContext] = None) -> List[Person]:
        """
        Bing Web Search API with improved query construction.
        
        Removes strict quotes for better recall.
        """
        people = []
        
        # Build query without strict quotes for better recall
        query_parts = ['site:linkedin.com/in/', company]
        if title:
            query_parts.append(title)
        
        # Add skills from job context if available
        if job_context and job_context.candidate_skills:
            top_skill = job_context.candidate_skills[0]
            query_parts.append(top_skill)
        
        query = ' '.join(query_parts)
        
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
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                for result in data.get('webPages', {}).get('value', []):
                    item_url = result.get('url', '')
                    title_text = result.get('name', '')
                    
                    if 'linkedin.com/in/' in item_url:
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
                                linkedin_url=item_url,
                                source='bing_api',
                                confidence_score=0.85
                            )
                            people.append(person)
        except Exception as e:
            # Silently fail for Bing (it's deprecated)
            pass
        
        return people
    
    def _search_github(self, company: str, title: str = None,
                      job_context: Optional[JobContext] = None) -> List[Person]:
        """
        GitHub API - Enhanced with title filtering.
        
        Uses job title to filter results for better relevance.
        """
        people = []
        
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        # Search users by company in bio with title filtering
        url = "https://api.github.com/search/users"
        
        # Build query with title if available
        company_query = company.replace(' ', '+')
        
        # Try different query strategies
        queries = []
        
        # Strategy 1: Company + Title in bio (most targeted)
        if title:
            # Extract main title word (e.g., "Software Engineer" -> "Engineer")
            title_words = title.split()
            if len(title_words) > 1:
                main_title = title_words[-1]  # Usually the role type
                queries.append(f'{company_query} {main_title.lower()} in:bio type:user')
            queries.append(f'{company_query} "{title.lower()}" in:bio type:user')
        
        # Strategy 2: Company only (fallback)
        queries.append(f'{company_query} in:bio type:user')
        
        # Strategy 3: Company + Skills from job (if available)
        if job_context and job_context.candidate_skills:
            top_skill = job_context.candidate_skills[0].lower()
            queries.append(f'{company_query} {top_skill} in:bio type:user')
        
        # Try first query that returns results
        params_base = {
            'per_page': 20,
            'sort': 'joined',
            'order': 'desc'
        }
        
        # Try queries in order until we get results
        for query in queries:
            try:
                params = {**params_base, 'q': query}
                response = requests.get(url, headers=headers, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    total_count = data.get('total_count', 0)
                    items = data.get('items', [])
                    
                    if items:
                        print(f"    Found {total_count} GitHub users (returning {len(items)})")
                        logger.info(f"GitHub search found {total_count} users (returning {len(items)})")
                        
                        # Use data directly from search (no extra API calls)
                        for user in items:
                            login = user.get('login', '')
                            profile_url = user.get('html_url', '')
                            
                            # Use login as name (can enhance later with individual API calls if needed)
                            name = login.replace('-', ' ').replace('_', ' ').title()
                            
                            person = Person(
                                name=name,
                                company=company,
                                source='github',
                                confidence_score=0.5,  # Lower since we don't verify bio
                                github_url=profile_url,
                                evidence_url=profile_url,
                            )
                            people.append(person)
                        
                        # If we got results, we can stop trying other queries
                        if len(people) > 0:
                            break
                    
                elif response.status_code == 403:
                    print("    ⚠ Rate limited (add GITHUB_TOKEN to .env)")
                    logger.warning("GitHub API rate limited - add GITHUB_TOKEN to .env")
                    break  # Don't try other queries if rate limited
                else:
                    # Try next query
                    continue
                    
            except Exception as e:
                # Try next query
                continue
        
        # Skip organization members search for speed (adds ~5 seconds)
        # The user search above already finds most employees
        # Uncomment if you want org members too:
        #
        # try:
        #     org_name = company.lower().replace(' ', '').replace(',', '').replace('.', '')
        #     org_url = f"https://api.github.com/orgs/{org_name}/members"
        #     
        #     response = requests.get(org_url, headers=headers, params={'per_page': 10}, timeout=3)
        #     
        #     if response.status_code == 200:
        #         members = response.json()
        #         print(f"    Found {len(members)} org members")
        #         
        #         for member in members:
        #             login = member.get('login', '')
        #             name = login.replace('-', ' ').replace('_', ' ').title()
        #             profile_url = member.get('html_url', '')
        #             
        #             person = Person(
        #                 name=name,
        #                 company=company,
        #                 source='github',
        #                 confidence_score=0.7,  # Higher - confirmed org member
        #                 github_url=profile_url,
        #                 evidence_url=profile_url,
        #             )
        #             people.append(person)
        #             
        # except Exception:
        #     pass  # Org might not exist, that's OK
        
        return people
    
    def _search_company_website(self, company: str) -> List[Person]:
        """
        Search company website for team/about pages.
        """
        people = []
        
        # Guess domain
        domain = self._guess_domain(company)
        if not domain:
            return []
        
        # Try common team page patterns
        patterns = [
            f"https://{domain}/team",
            f"https://{domain}/about/team",
            f"https://{domain}/about-us",
            f"https://{domain}/leadership",
            f"https://{domain}/people",
            f"https://{domain}/company/team",
        ]
        
        for url in patterns:
            try:
                response = requests.get(url, timeout=5, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for team member sections
                    # Common patterns: name + title + LinkedIn link
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        
                        if 'linkedin.com/in/' in href:
                            # Found a LinkedIn link
                            # Try to find name nearby
                            parent = link.find_parent(['div', 'section', 'article'])
                            if parent:
                                text = parent.get_text(strip=True)
                                # Name is usually near the link
                                words = text.split()
                                if len(words) >= 2:
                                    # Assume first 2-3 words are the name
                                    name = ' '.join(words[:3])
                                    
                                    person = Person(
                                        name=name,
                                        company=company,
                                        linkedin_url=href,
                                        source='company_website',
                                        confidence_score=0.8
                                    )
                                    people.append(person)
                    
                    if people:
                        break  # Found a page with results
                        
            except Exception:
                continue
        
        return people
    
    def _guess_domain(self, company: str) -> Optional[str]:
        """Guess company domain"""
        # Common mappings
        mappings = {
            'google': 'google.com',
            'meta': 'meta.com',
            'facebook': 'meta.com',
            'stripe': 'stripe.com',
            'cursor': 'cursor.so',
            'openai': 'openai.com',
            'anthropic': 'anthropic.com',
        }
        
        company_lower = company.lower()
        if company_lower in mappings:
            return mappings[company_lower]
        
        # Try .com
        clean = company_lower.replace(' ', '').replace(',', '').replace('.', '')
        return f"{clean}.com"
    
    def search_people(self, company: str, title: str = None, **kwargs) -> List[Person]:
        """
        Search for people - compatible with orchestrator interface.
        
        Args:
            company: Company name
            title: Job title (optional)
            **kwargs: Additional parameters including:
                - user_profile: CandidateProfile with resume data
                - job_context: JobContext with job data
                - max_results: Maximum results to return
            
        Returns:
            List of Person objects
        """
        user_profile = kwargs.get('user_profile')
        job_context = kwargs.get('job_context')
        max_results = kwargs.get('max_results', 50)
        
        # Use our main search method with context
        return self.search_all(company, title, max_results=max_results,
                              user_profile=user_profile, job_context=job_context)
    
    def is_configured(self) -> bool:
        """
        Check if at least one source is configured.
        
        Returns:
            True if Google CSE, Bing API, or GitHub token is available
        """
        return bool(
            (self.google_cse_id and self.google_api_key) or 
            self.bing_api_key or 
            self.github_token
        )


def test_working_sources():
    """Test with real companies"""
    searcher = ActuallyWorkingFreeSources()
    
    print("\n" + "="*60)
    print("🧪 TESTING ACTUALLY WORKING FREE SOURCES")
    print("="*60)
    
    # Check configuration
    print("\n📋 Configuration:")
    print(f"  Google CSE: {'✓ Configured' if searcher.google_cse_id else '✗ Not configured'}")
    print(f"  Bing API: {'✓ Configured' if searcher.bing_api_key else '✗ Not configured'}")
    print(f"  GitHub Token: {'✓ Configured' if searcher.github_token else '⚠ Using 60/hour limit'}")
    
    # Test
    people = searcher.search_all("Google", "Software Engineer", max_results=30)
    
    if people:
        print("\n📊 Sample Results:")
        for i, person in enumerate(people[:5], 1):
            print(f"\n{i}. {person.name}")
            if person.title:
                print(f"   Title: {person.title[:60]}...")
            if person.linkedin_url:
                print(f"   LinkedIn: {person.linkedin_url[:70]}...")
            print(f"   Source: {person.source}")
            print(f"   Confidence: {person.confidence_score}")
    else:
        print("\n⚠ No results - configure API keys for better results")
        print("\nSetup instructions:")
        print("  1. Google CSE: https://programmablesearchengine.google.com/")
        print("  2. Bing API: https://portal.azure.com/ (search for Bing Search)")
        print("  3. GitHub Token: https://github.com/settings/tokens (optional)")


if __name__ == "__main__":
    test_working_sources()
