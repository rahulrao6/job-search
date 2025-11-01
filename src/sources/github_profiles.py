"""Search GitHub for company employees"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter


class GitHubScraper:
    """
    Search GitHub for employees of a company.
    
    GitHub profiles often list company affiliation.
    Particularly useful for technical roles.
    """
    
    def __init__(self):
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure("github", requests_per_second=1)
    
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search GitHub for people affiliated with a company.
        
        Args:
            company: Company name
            title: Job title (used to filter results)
        
        Returns:
            List of Person objects
        """
        people = []
        
        # Search strategies:
        # 1. Organization members (if company has a GitHub org)
        org_people = self._search_org_members(company, title)
        people.extend(org_people)
        
        # 2. Search user bios for company mention
        bio_people = self._search_user_bios(company, title)
        people.extend(bio_people)
        
        if people:
            print(f"✓ GitHub found {len(people)} people")
        else:
            print(f"⚠️  No GitHub profiles found for {company}")
        
        return people
    
    def _search_org_members(self, company: str, title: str) -> List[Person]:
        """Search for members of a GitHub organization"""
        people = []
        
        # Try common org name patterns
        org_names = self._guess_org_names(company)
        
        for org_name in org_names:
            self.rate_limiter.wait_if_needed("github")
            
            try:
                # Check if org exists and get members
                url = f"https://github.com/orgs/{org_name}/people"
                response = self.http_client.get(url)
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find member links
                member_links = soup.find_all('a', href=re.compile(r'^/[^/]+$'))
                
                for link in member_links[:50]:  # Limit results
                    username = link.get('href').strip('/')
                    
                    # Get user profile
                    user_info = self._get_user_profile(username, company)
                    if user_info:
                        people.append(user_info)
                
                if people:
                    print(f"✓ Found {len(people)} members in GitHub org '{org_name}'")
                    break  # Found the right org
                    
            except Exception as e:
                # Org doesn't exist or is private
                continue
        
        return people
    
    def _search_user_bios(self, company: str, title: str) -> List[Person]:
        """Search GitHub users with company in bio"""
        people = []
        
        self.rate_limiter.wait_if_needed("github")
        
        try:
            # GitHub search for users with company in profile
            # Note: This requires scraping search results
            search_query = f"{company} {title}"
            url = f"https://github.com/search?q={search_query}&type=users"
            
            response = self.http_client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find user results
            user_results = soup.find_all('div', class_=re.compile(r'user-list-item'))
            
            for result in user_results[:20]:  # Limit results
                person = self._parse_user_result(result, company)
                if person:
                    people.append(person)
        
        except Exception as e:
            print(f"⚠️  GitHub search error: {e}")
        
        return people
    
    def _get_user_profile(self, username: str, company: str) -> Optional[Person]:
        """Get details for a GitHub user"""
        self.rate_limiter.wait_if_needed("github")
        
        try:
            url = f"https://github.com/{username}"
            response = self.http_client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get name
            name_elem = soup.find('span', class_=re.compile(r'vcard-fullname'))
            name = name_elem.get_text(strip=True) if name_elem else username
            
            # Get bio (may contain title/role)
            bio_elem = soup.find('div', class_=re.compile(r'user-profile-bio'))
            bio = bio_elem.get_text(strip=True) if bio_elem else ""
            
            # Get company from profile
            company_elem = soup.find('span', class_='p-org')
            profile_company = company_elem.get_text(strip=True) if company_elem else None
            
            # Only include if company matches
            if profile_company and company.lower() in profile_company.lower():
                return Person(
                    name=name,
                    title=bio if bio else None,
                    company=company,
                    github_url=url,
                    source="github",
                    evidence_url=url,
                )
        
        except Exception as e:
            pass
        
        return None
    
    def _parse_user_result(self, result_elem, company: str) -> Optional[Person]:
        """Parse a user from search results"""
        try:
            # Get username and link
            link_elem = result_elem.find('a', class_=re.compile(r'user'))
            if not link_elem:
                return None
            
            username = link_elem.get('href', '').strip('/')
            url = f"https://github.com/{username}"
            
            # Get name if available
            name_elem = result_elem.find('a', href=f"/{username}")
            name = name_elem.get_text(strip=True) if name_elem else username
            
            # Get bio snippet
            bio_elem = result_elem.find('p', class_=re.compile(r'bio'))
            bio = bio_elem.get_text(strip=True) if bio_elem else ""
            
            return Person(
                name=name,
                title=bio if bio else None,
                company=company,
                github_url=url,
                source="github",
                evidence_url=url,
            )
        
        except Exception as e:
            return None
    
    def _guess_org_names(self, company: str) -> List[str]:
        """Guess possible GitHub organization names"""
        clean = company.lower()
        clean = re.sub(r'\s+(inc|llc|ltd|corp|corporation)\.?$', '', clean)
        
        # Common patterns
        patterns = [
            clean.replace(' ', ''),  # "Meta Platforms" -> "metaplatforms"
            clean.replace(' ', '-'),  # "Meta Platforms" -> "meta-platforms"
            company.split()[0].lower(),  # "Meta Platforms" -> "meta"
        ]
        
        return patterns

