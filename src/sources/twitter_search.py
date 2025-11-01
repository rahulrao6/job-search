"""Search Twitter/X for people mentioning company in bio"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from src.models.person import Person, PersonCategory
from src.utils.http_client import create_client
from src.utils.rate_limiter import get_rate_limiter


class TwitterSearchScraper:
    """
    Search Twitter/X for people with company in bio.
    
    Uses Nitter instances (Twitter frontends without rate limits).
    100% free, no API needed.
    """
    
    # Nitter instances (Twitter frontends)
    NITTER_INSTANCES = [
        "https://nitter.net",
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
    ]
    
    def __init__(self):
        self.http_client = create_client()
        self.rate_limiter = get_rate_limiter()
        self.rate_limiter.configure("twitter_search", requests_per_second=0.5)
    
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search Twitter for people with company in bio.
        
        Args:
            company: Company name
            title: Job title (used for filtering)
        
        Returns:
            List of Person objects
        """
        people = []
        
        # Try different search strategies
        queries = [
            f"{company} {title}",
            f"{company} engineer",
            f"@{company.lower()}",
        ]
        
        for query in queries[:1]:  # Just try first query for now
            for instance in self.NITTER_INSTANCES:
                try:
                    self.rate_limiter.wait_if_needed("twitter_search")
                    
                    # Search on Nitter
                    search_url = f"{instance}/search?f=users&q={query.replace(' ', '+')}"
                    response = self.http_client.get(search_url, timeout=10)
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find user results
                    user_cards = soup.find_all(['div', 'article'], class_=re.compile(r'timeline-item'))
                    
                    for card in user_cards[:20]:
                        person = self._parse_user_card(card, company, instance)
                        if person:
                            people.append(person)
                    
                    if people:
                        print(f"✓ Twitter found {len(people)} people")
                        return people
                    
                except Exception as e:
                    # Try next instance
                    continue
        
        if not people:
            print(f"⚠️  No Twitter profiles found for {company}")
        
        return people
    
    def _parse_user_card(self, card, company: str, base_url: str) -> Optional[Person]:
        """Parse a user card from Nitter"""
        try:
            # Find username
            username_elem = card.find('a', class_=re.compile(r'username'))
            if not username_elem:
                return None
            
            username = username_elem.get_text(strip=True).lstrip('@')
            
            # Find display name
            name_elem = card.find(['a', 'span'], class_=re.compile(r'fullname'))
            name = name_elem.get_text(strip=True) if name_elem else username
            
            # Find bio
            bio_elem = card.find(['p', 'div'], class_=re.compile(r'bio'))
            bio = bio_elem.get_text(strip=True) if bio_elem else ""
            
            # Check if bio mentions company
            if company.lower() not in bio.lower():
                return None
            
            # Twitter URL (use real Twitter, not Nitter)
            twitter_url = f"https://twitter.com/{username}"
            
            return Person(
                name=name,
                title=bio[:100] if bio else None,  # Use bio as title
                company=company,
                twitter_url=twitter_url,
                source="twitter",
                evidence_url=twitter_url,
                confidence_score=0.6,  # Lower confidence from Twitter
            )
        
        except Exception as e:
            return None

