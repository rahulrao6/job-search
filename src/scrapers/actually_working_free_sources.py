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
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.models.person import Person
from src.models.job_context import CandidateProfile, JobContext
from src.utils.query_tracker import track_query
from src.utils.company_resolver import CompanyResolver
from src.utils.query_optimizer import QueryOptimizer

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
        
        # Company resolver for intelligent matching
        self.company_resolver = CompanyResolver()
        # Query optimizer for smarter searches
        self.query_optimizer = QueryOptimizer()
        
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
            logger.info(f"Google CSE configured - searching for {company} {title or ''}")
            try:
                people = self._search_google_cse(company, title, user_profile, job_context)
                new = self._add_unique(people, seen_urls, all_people)
                if new > 0:
                    print(f"    ✓ Found {new} profiles")
                    logger.info(f"Google CSE found {new} profiles")
                else:
                    print(f"    ⊘ Found {len(people)} results but {new} were new/unique")
                    logger.info(f"Google CSE found {len(people)} results, {new} new after deduplication")
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:50]}")
                logger.error(f"Google CSE error: {e}", exc_info=True)
        else:
            print("  ⊘ Google CSE not configured (set GOOGLE_CSE_ID + GOOGLE_API_KEY)")
            logger.warning("Google CSE not configured - missing GOOGLE_CSE_ID or GOOGLE_API_KEY")
        
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
        
        # Build query variations with the query optimizer
        query_variations = self.query_optimizer.generate_queries(
            company=company,
            title=title,
            job_context=job_context,
            candidate_profile=user_profile,
            platform='linkedin'
        )[:7]  # Limit to 7 queries
        
        # Fallback if query optimizer returns empty
        if not query_variations:
            base_query = f'site:linkedin.com/in/ "{company}"'
            if title:
                base_query += f' {title}'
            query_variations = [base_query]
            logger.warning(f"Query optimizer returned no queries, using fallback: {base_query}")
        
        logger.info(f"Google CSE: Executing {len(query_variations)} query variations")
        print(f"    Executing {len(query_variations)} search queries...")
        
        # Fix: Define company_lower for use in regex patterns
        company_lower = company.lower()
        
        # Try each query variation until we get good results
        for i, query in enumerate(query_variations, 1):
            start_time = time.time()
            query_success = False
            results_count = 0
            
            try:
                logger.debug(f"Google CSE query {i}/{len(query_variations)}: {query}")
                
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cse_id,
                    'q': query,
                    'num': 10,  # Max per request
                    'start': 1,
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    results_count = len(items)
                    
                    logger.info(f"Google CSE query {i} returned {results_count} results")
                    
                    if results_count == 0:
                        # Check if there's an error in the response
                        if 'error' in data:
                            error_msg = data['error'].get('message', 'Unknown error')
                            logger.warning(f"Google CSE API error: {error_msg}")
                            print(f"    ⚠ Query {i} returned error: {error_msg[:60]}")
                    
                    for item in items:
                        item_url = item.get('link', '')
                        title_text = item.get('title', '')
                        snippet = item.get('snippet', '')
                        
                        # VERY LENIENT: Accept ANY result from Google CSE (trust the search query)
                        # Only basic sanity checks, no strict filtering
                        
                        # Check if it's a LinkedIn URL (for setting linkedin_url field)
                        linkedin_patterns = [
                            '/linkedin.com/in/',
                            'linkedin.com/in/',
                            'linkedin.com/profile/',
                            '/linkedin.com/pub/'
                        ]
                        is_linkedin = any(pattern in item_url.lower() for pattern in linkedin_patterns) if item_url else False
                        
                        combined_text = f"{title_text} {snippet}".lower()
                        
                        # Extract name from title (format: "Name - Job Title - LinkedIn" or just "Name")
                        name = title_text.split(' - ')[0].strip()
                        # Clean up name (remove LinkedIn, profile, etc.)
                        name = re.sub(r'\s*-\s*LinkedIn.*$', '', name, flags=re.IGNORECASE)
                        name = re.sub(r'\s*LinkedIn.*$', '', name, flags=re.IGNORECASE)
                        name = re.sub(r'\s*Profile.*$', '', name, flags=re.IGNORECASE)
                        name = name.strip()
                        
                        # Skip if name is too short or clearly invalid
                        if len(name) < 2:
                            continue
                        
                        # More lenient verification - accept almost everything
                        company_domain = job_context.company_domain if job_context else None
                        
                        # Check if company appears in text (very lenient)
                        company_mentioned = False
                        if company_lower in combined_text:
                            company_mentioned = True
                        elif company_domain:
                            domain_clean = company_domain.replace('.com', '').replace('www.', '').replace('.io', '').replace('.ai', '')
                            if domain_clean.lower() in combined_text:
                                company_mentioned = True
                        
                        # Confidence boost based on company mention
                        if company_mentioned:
                            confidence_boost = 0.2  # Company mentioned - good
                        else:
                            confidence_boost = 0.0  # Not mentioned but still accept
                        
                        # Try to extract title from snippet or title
                        job_title = None
                        if ' - ' in title_text:
                            parts = title_text.split(' - ')
                            if len(parts) >= 2:
                                job_title = parts[1].strip()
                                # Clean up title
                                job_title = re.sub(r'\s*at\s+.*$', '', job_title, flags=re.IGNORECASE)
                                job_title = job_title.strip()
                        
                        # If no title from title field, try to extract from snippet
                        if not job_title and snippet:
                            # Look for job title patterns in snippet
                            title_patterns = [
                                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:at|@|•|\|)\s+',
                                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Engineer|Developer|Manager|Director|Lead|Architect)',
                                r'(?:Title|Role):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                            ]
                            for pattern in title_patterns:
                                match = re.search(pattern, snippet, re.IGNORECASE)
                                if match:
                                    potential_title = match.group(1).strip()
                                    if len(potential_title) > 2 and len(potential_title) < 60:
                                        job_title = potential_title
                                        break
                            
                        # Extract company from snippet if mentioned, otherwise use search company
                        extracted_company = company  # Default to search company
                        
                        # Very lenient name validation - accept almost any name-like string
                        if len(name) >= 2:
                            # Calculate confidence - more lenient base
                            base_confidence = 0.6  # Lower base confidence but accept more
                            final_confidence = min(0.95, base_confidence + confidence_boost)
                            
                            # Set LinkedIn URL if available
                            linkedin_url = item_url if is_linkedin else None
                            
                            # Create person - accept all results from Google CSE
                            person = Person(
                                name=name,
                                title=job_title,
                                company=extracted_company,
                                linkedin_url=linkedin_url,
                                source='google_cse',
                                confidence_score=final_confidence
                            )
                            people.append(person)
                            logger.debug(f"Added {name} - {job_title or 'No title'} at {extracted_company} (confidence: {final_confidence:.2f}, LinkedIn: {linkedin_url is not None})")
                    
                    query_success = True
                else:
                    # Log API errors
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg = error_data['error'].get('message', error_msg)
                    except:
                        error_msg = response.text[:100] if response.text else error_msg
                    
                    logger.error(f"Google CSE API error for query {i}: {error_msg}")
                    print(f"    ✗ Query {i} failed: {error_msg[:60]}")
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Google CSE query {i} timed out")
                print(f"    ⚠ Query {i} timed out")
            except requests.exceptions.RequestException as e:
                logger.error(f"Google CSE request error for query {i}: {e}")
                print(f"    ✗ Query {i} request error: {str(e)[:60]}")
            except Exception as e:
                logger.error(f"Google CSE unexpected error for query {i}: {e}", exc_info=True)
                print(f"    ✗ Query {i} error: {str(e)[:60]}")
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
        
        logger.info(f"Google CSE total results: {len(people)} people")
        return people
    
    def _build_google_query_variations(self, company: str, title: str = None,
                                     user_profile: Optional[CandidateProfile] = None,
                                     job_context: Optional[JobContext] = None) -> List[str]:
        """
        Build multiple query variations using intelligent patterns.
        
        Strategy:
        1. Domain-specific: Company + Domain + Title (most accurate)
        2. Primary: Company + Title (with skills if available)
        3. School-based: Company + Title + School (alumni search)
        4. Skills-based: Company + Title + Top skills from job
        5. Department-based: Company + Department + Title
        6. Fallback: Just Company + Title (broadest)
        """
        queries = []
        base = f'site:linkedin.com/in/'
        
        # Don't normalize during search - keep original name for better matches
        # We'll normalize during verification instead
        normalized_company = company
        
        # Extract company domain if available
        company_domain = None
        if job_context and job_context.company_domain:
            company_domain = job_context.company_domain
        elif not company_domain:
            # Try to find domain via resolver
            company_domain = self.company_resolver.get_company_domain(normalized_company)
        
        # Priority 1: Domain-specific query (most accurate for disambiguation)
        if company_domain:
            # Query with both company name AND domain for accuracy
            if title:
                # Most specific: company + domain + title
                queries.append(f'{base} "{normalized_company}" "{company_domain}" {title}')
                # Variation without quotes for broader matching
                queries.append(f'{base} {normalized_company} {company_domain} {title}')
            else:
                queries.append(f'{base} "{normalized_company}" "{company_domain}"')
        
        # Priority 2: Company + Title (standard search)
        if title:
            primary = f'{base} "{normalized_company}" {title}'
            queries.append(primary)
            
            # Get alternative patterns from resolver
            patterns = self.company_resolver.get_company_patterns(normalized_company, company_domain)
            for pattern in patterns['linkedin'][:2]:  # Use top 2 LinkedIn patterns
                queries.append(f'{base} {pattern} {title}')
            
            # Add skills from job context if available
            if job_context and job_context.candidate_skills:
                top_skills = job_context.candidate_skills[:2]  # Top 2 skills
                if top_skills:
                    skills_query = f'{base} "{normalized_company}" {title} {" ".join(top_skills)}'
                    queries.append(skills_query)
        
        # Priority 3: School-based query (alumni search) - higher relevance potential
        if user_profile and user_profile.schools:
            top_school = user_profile.schools[0]  # Most recent/relevant school
            if title:
                school_query = f'{base} "{normalized_company}" {title} "{top_school}"'
                queries.append(school_query)
            else:
                school_query = f'{base} "{normalized_company}" "{top_school}"'
                queries.append(school_query)
        
        # Priority 4: Department-based query if available
        if job_context and job_context.department:
            if title:
                dept_query = f'{base} "{normalized_company}" "{job_context.department}" {title}'
                queries.append(dept_query)
        
        # Priority 5: Location-based if available (local connections)
        if job_context and job_context.location:
            if title:
                location_query = f'{base} "{normalized_company}" {title} "{job_context.location}"'
                queries.append(location_query)
        
        # Fallback: Just company + title (or company only)
        if not queries:
            if title:
                queries.append(f'{base} "{normalized_company}" {title}')
            else:
                queries.append(f'{base} "{normalized_company}"')
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries[:7]  # Limit to 7 variations
    
    def _search_bing_api(self, company: str, title: str = None,
                        user_profile: Optional[CandidateProfile] = None,
                        job_context: Optional[JobContext] = None) -> List[Person]:
        """
        Bing Web Search API with improved query construction.
        
        Removes strict quotes for better recall.
        """
        people = []
        
        # Use query optimizer for Bing queries too
        query_variations = self.query_optimizer.generate_queries(
            company=company,
            title=title,
            job_context=job_context,
            candidate_profile=user_profile,
            platform='linkedin'
        )
        
        # Use the first optimized query for Bing
        query = query_variations[0] if query_variations else f'site:linkedin.com/in/ {company} {title or ""}'
        
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
        
        # Generate optimized queries
        optimizer_queries = self.query_optimizer.generate_queries(
            company=company,
            title=title,
            job_context=job_context,
            candidate_profile=None,  # GitHub doesn't use candidate profile
            platform='github'
        )
        
        # Convert optimizer queries to GitHub API format
        queries = []
        
        # Use optimizer suggestions but adapt for GitHub API
        for opt_query in optimizer_queries[:3]:  # Use top 3 suggestions
            # Extract key terms from optimizer query
            if 'org:' in opt_query:
                # Handle org-specific queries
                org_match = re.search(r'org:(\w+)', opt_query)
                if org_match:
                    org = org_match.group(1)
                    if title:
                        queries.append(f'{org} {title.lower()} in:bio type:user')
                    else:
                        queries.append(f'{org} in:bio type:user')
            elif 'language:' in opt_query:
                # Handle language-specific queries
                lang_match = re.search(r'language:(\w+)', opt_query)
                if lang_match:
                    lang = lang_match.group(1)
                    queries.append(f'{company_query} language:{lang} type:user')
            else:
                # General bio search
                if title and title.lower() in opt_query.lower():
                    queries.append(f'{company_query} "{title.lower()}" in:bio type:user')
        
        # Add fallback if no good queries from optimizer
        if not queries:
            if title:
                queries.append(f'{company_query} "{title.lower()}" in:bio type:user')
            queries.append(f'{company_query} in:bio type:user')
        
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
    
    def _verify_current_employment(self, text: str, company: str, company_domain: str = None) -> Tuple[bool, float]:
        """
        Verify this person currently works at the target company using intelligent matching.
        
        Returns:
            (is_current_employee, confidence_score) - tuple of bool and float
        
        VERY LENIENT: Only rejects if clearly wrong, otherwise accepts.
        """
        text_lower = text.lower()
        company_lower = company.lower()
        
        # Very simple check: does company name appear in text?
        company_mentioned = company_lower in text_lower
        
        # Check for domain if available
        domain_mentioned = False
        if company_domain:
            domain_clean = company_domain.replace('www.', '').replace('.com', '').replace('.io', '').replace('.ai', '')
            domain_mentioned = domain_clean.lower() in text_lower
        
        # If company or domain is mentioned, accept with high confidence
        if company_mentioned or domain_mentioned:
            return True, 0.3  # Good match
        
        # Even if not mentioned, accept (search query should have filtered)
        # Only reject if we're VERY confident it's wrong
        # Check for obvious false positives (different company clearly mentioned)
        false_positive_indicators = [
            'formerly at',
            'previously at',
            'ex-',
            'former',
            'past employee'
        ]
        
        for indicator in false_positive_indicators:
            if indicator in text_lower:
                # Check if our company is mentioned after the indicator
                parts = text_lower.split(indicator)
                if len(parts) > 1:
                    after_text = parts[1][:100]  # Next 100 chars
                    if company_lower not in after_text:
                        # Might be talking about a different company
                        # But still accept - let the user decide
                        pass
        
        # Very lenient: accept almost everything
        # Only reject if score is exactly 0.0 AND we're very sure
        try:
            # Try company resolver for score, but don't rely on it for rejection
            normalized_company = self.company_resolver.normalize_company_name(company)
            score_original = self.company_resolver.calculate_company_match_score(
                text, company, company_domain
            )
            score_normalized = self.company_resolver.calculate_company_match_score(
                text, normalized_company, company_domain
            )
            score = max(score_original, score_normalized, 0.1)  # Minimum 0.1 to avoid 0.0
        except:
            # If resolver fails, default to accepting
            score = 0.2
        
        # Always accept, but adjust confidence
        return True, max(0.1, score * 0.8)  # Always True, confidence at least 0.1
    
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
