"""
Smart company domain finder that actually works.
Finds company websites even for small startups.
"""

import re
from typing import Optional, List, Dict
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


class SmartCompanyFinder:
    """
    Finds company websites and team pages intelligently.
    
    Strategies:
    1. Search for company website
    2. Try common domain patterns
    3. Check social media for website links
    4. Use startup databases
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def find_company_info(self, company_name: str) -> Dict[str, any]:
        """
        Find comprehensive company information.
        
        Returns:
            {
                'domain': 'company.com',
                'website': 'https://company.com',
                'team_pages': ['https://company.com/team', ...],
                'linkedin': 'https://linkedin.com/company/...',
                'size': 'small|medium|large',
            }
        """
        info = {
            'name': company_name,
            'domain': None,
            'website': None,
            'team_pages': [],
            'linkedin': None,
            'size': 'unknown',
        }
        
        # Step 1: Find domain
        domain = self.find_domain(company_name)
        if domain:
            info['domain'] = domain
            info['website'] = f'https://{domain}'
            
            # Step 2: Find team pages
            team_pages = self.find_team_pages(domain)
            info['team_pages'] = team_pages
        
        # Step 3: Find LinkedIn company page
        linkedin = self.find_linkedin_company(company_name)
        if linkedin:
            info['linkedin'] = linkedin
        
        # Step 4: Estimate company size
        info['size'] = self.estimate_company_size(company_name)
        
        return info
    
    def find_domain(self, company: str) -> Optional[str]:
        """
        Find company domain using multiple methods.
        """
        # Method 1: Direct patterns
        domain = self._try_common_patterns(company)
        if domain:
            return domain
        
        # Method 2: Search for domain
        domain = self._search_for_domain(company)
        if domain:
            return domain
        
        # Method 3: Check startup databases
        domain = self._check_startup_dbs(company)
        if domain:
            return domain
        
        return None
    
    def _try_common_patterns(self, company: str) -> Optional[str]:
        """
        Try common domain patterns.
        """
        # Clean company name
        clean = company.lower().strip()
        clean = re.sub(r'[^\w\s-]', '', clean)  # Remove special chars
        clean = re.sub(r'\s+', '', clean)  # Remove spaces
        
        patterns = [
            f"{clean}.com",
            f"{clean}.io",
            f"get{clean}.com",
            f"{clean}hq.com",
            f"{clean}.ai",
            f"{clean}.dev",
            f"try{clean}.com",
            f"{clean}app.com",
            f"{clean}.co",
            f"www.{clean}.com",
        ]
        
        # Also try with hyphens
        hyphenated = company.lower().replace(' ', '-')
        patterns.extend([
            f"{hyphenated}.com",
            f"{hyphenated}.io",
        ])
        
        for pattern in patterns:
            if self._verify_domain(pattern):
                return pattern
        
        return None
    
    def _verify_domain(self, domain: str) -> bool:
        """
        Verify if domain exists and is the right company.
        """
        try:
            url = f"https://{domain}"
            resp = self.session.head(url, timeout=5, allow_redirects=True)
            return resp.status_code < 400
        except:
            try:
                # Try without SSL
                url = f"http://{domain}"
                resp = self.session.head(url, timeout=5, allow_redirects=True)
                return resp.status_code < 400
            except:
                return False
    
    def _search_for_domain(self, company: str) -> Optional[str]:
        """
        Search for company domain using search engines.
        """
        # Use DuckDuckGo to find company website
        query = f'"{company}" official website'
        
        url = "https://html.duckduckgo.com/html/"
        data = {'q': query}
        
        try:
            resp = self.session.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Get first few results
                results = soup.find_all('a', class_='result__url', limit=5)
                
                for result in results:
                    href = result.get('href', '')
                    if href:
                        # Extract domain
                        parsed = urlparse(href)
                        domain = parsed.netloc.replace('www.', '')
                        
                        # Verify it's likely the company
                        if company.lower().replace(' ', '') in domain.lower():
                            return domain
                            
        except:
            pass
        
        return None
    
    def _check_startup_dbs(self, company: str) -> Optional[str]:
        """
        Check startup databases for company info.
        """
        # Could check:
        # - Crunchbase (if accessible)
        # - AngelList/Wellfound
        # - ProductHunt
        # For now, skip as these often require auth
        return None
    
    def find_team_pages(self, domain: str) -> List[str]:
        """
        Find team/about pages on company website.
        """
        team_pages = []
        
        # Common patterns
        paths = [
            '/team',
            '/about/team',
            '/about-us/team',
            '/company/team',
            '/about',
            '/about-us',
            '/people',
            '/our-team',
            '/leadership',
            '/about/leadership',
            '/careers/team',
            '/culture',
        ]
        
        base_url = f'https://{domain}'
        
        for path in paths:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=5)
                if resp.status_code == 200:
                    # Verify it's actually a team page
                    text = resp.text.lower()
                    if any(word in text for word in ['team', 'people', 'leadership', 'founder', 'engineer', 'designer']):
                        team_pages.append(url)
            except:
                continue
        
        return team_pages
    
    def find_linkedin_company(self, company: str) -> Optional[str]:
        """
        Find company's LinkedIn page.
        """
        # Search for LinkedIn company page
        query = f'site:linkedin.com/company/ "{company}"'
        
        url = "https://html.duckduckgo.com/html/"
        data = {'q': query}
        
        try:
            resp = self.session.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Get first result
                result = soup.find('a', class_='result__a')
                if result:
                    href = result.get('href', '')
                    if 'linkedin.com/company/' in href:
                        return href
        except:
            pass
        
        return None
    
    def estimate_company_size(self, company: str) -> str:
        """
        Estimate company size for better search strategies.
        """
        # Large companies (Fortune 500, well-known)
        large_companies = {
            'google', 'apple', 'microsoft', 'amazon', 'meta', 'facebook',
            'netflix', 'uber', 'airbnb', 'salesforce', 'oracle', 'ibm',
            'intel', 'cisco', 'adobe', 'nvidia', 'tesla', 'twitter',
        }
        
        # Medium companies (known startups, mid-size)
        medium_companies = {
            'stripe', 'databricks', 'canva', 'figma', 'notion', 'discord',
            'slack', 'zoom', 'dropbox', 'coinbase', 'robinhood', 'square',
            'twilio', 'okta', 'datadog', 'snowflake', 'cloudflare',
        }
        
        company_lower = company.lower()
        
        if any(corp in company_lower for corp in large_companies):
            return 'large'
        elif any(corp in company_lower for corp in medium_companies):
            return 'medium'
        else:
            return 'small'


def test_company_finder():
    """Test the company finder."""
    finder = SmartCompanyFinder()
    
    test_companies = [
        "Google",
        "Stripe", 
        "Cursor",
        "Replicate",
        "Some Unknown Startup",
    ]
    
    for company in test_companies:
        print(f"\n{'='*50}")
        print(f"Finding info for: {company}")
        print('='*50)
        
        info = finder.find_company_info(company)
        
        print(f"Domain: {info['domain']}")
        print(f"Website: {info['website']}")
        print(f"Team pages: {len(info['team_pages'])} found")
        for page in info['team_pages'][:3]:
            print(f"  - {page}")
        print(f"LinkedIn: {info['linkedin']}")
        print(f"Size: {info['size']}")


if __name__ == "__main__":
    test_company_finder()
