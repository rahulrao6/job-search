"""Apollo.io API client"""

import os
from typing import List, Optional
import requests
from src.models.person import Person, PersonCategory
from src.utils.rate_limiter import get_rate_limiter
from src.utils.cost_tracker import get_cost_tracker
from .base_client import BaseAPIClient


class ApolloClient(BaseAPIClient):
    """
    Apollo.io API client for finding people at companies.
    
    Free tier: 50 credits/month
    Docs: https://apolloio.github.io/apollo-api-docs/
    """
    
    BASE_URL = "https://api.apollo.io/api/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("APOLLO_API_KEY"))
        self.rate_limiter = get_rate_limiter()
        self.cost_tracker = get_cost_tracker()
        
        # Configure rate limiting (1 request per second for free tier)
        self.rate_limiter.configure("apollo", requests_per_second=1)
    
    def is_configured(self) -> bool:
        """Check if API key is available"""
        return bool(self.api_key)
    
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search for people at a company with a specific title.
        
        Args:
            company: Company name
            title: Job title to search for
            **kwargs: Additional filters (location, seniority, etc.)
        
        Returns:
            List of Person objects
        """
        if not self.is_configured():
            print(f"⚠️  Apollo API key not configured, skipping")
            return []
        
        # Rate limit
        self.rate_limiter.wait_if_needed("apollo")
        
        # Build search query for /contacts/search endpoint
        params = {
            "q_organization_name": company,
            "person_titles": [title],
            "page": 1,
            "per_page": 25,  # Get 25 results
        }
        
        # Add optional filters
        if "location" in kwargs:
            params["person_locations"] = [kwargs["location"]]
        
        # Apollo requires API key in header, not body
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            # Use the contacts/search endpoint
            response = requests.post(
                f"{self.BASE_URL}/contacts/search",
                json=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Check for free tier limitations
            if "error" in data and "free plan" in data.get("error", "").lower():
                print(f"⚠️  Apollo free tier doesn't include contact search. Upgrade required.")
                print(f"   Error: {data.get('error', 'Unknown')}")
                return []
            
            # Track cost (free tier but still track usage)
            # Note: Each result uses 1 email credit from your 10k/month
            credits_used = len(data.get("contacts", []))
            self.cost_tracker.record_request("apollo", cost=0.0)
            
            # Parse results
            people = []
            for person_data in data.get("contacts", []):
                person = self._parse_person(person_data, company)
                if person:
                    people.append(person)
            
            if len(people) > 0:
                print(f"✓ Apollo found {len(people)} people (used {credits_used} of 10k free credits)")
            else:
                # Check if it's a free tier limitation (0 results could mean no access)
                pagination = data.get("pagination", {})
                total_entries = pagination.get("total_entries", 0)
                if total_entries == 0:
                    # This might indicate free tier limitation - log it but don't spam
                    pass  # Silent skip - free tier may not have search access
            
            return people
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"⚠️  Apollo authentication failed - check API key")
            elif e.response.status_code == 403:
                # Check if it's a free tier limitation
                try:
                    error_data = e.response.json()
                    if "free plan" in error_data.get("error", "").lower():
                        print(f"⚠️  Apollo free tier doesn't include contact search. Upgrade required for search access.")
                    else:
                        print(f"⚠️  Apollo access denied: {error_data.get('error', 'Unknown')}")
                except:
                    print(f"⚠️  Apollo access denied (403)")
            elif e.response.status_code == 429:
                print(f"⚠️  Apollo rate limit exceeded")
            else:
                print(f"⚠️  Apollo error: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Apollo unexpected error: {e}")
            return []
    
    def _parse_person(self, data: dict, company: str) -> Optional[Person]:
        """Parse Apollo API response into Person object"""
        try:
            name = data.get("name")
            if not name:
                return None
            
            # Get title and categorize
            title = data.get("title")
            
            # Build LinkedIn URL if we have linkedin_url
            linkedin_url = data.get("linkedin_url")
            
            # Get email
            email = data.get("email")
            
            return Person(
                name=name,
                title=title,
                company=company,
                linkedin_url=linkedin_url,
                email=email,
                source="apollo",
                department=data.get("departments", [None])[0] if data.get("departments") else None,
                location=data.get("city"),
                evidence_url=linkedin_url,
            )
        except Exception as e:
            print(f"⚠️  Failed to parse Apollo person: {e}")
            return None

