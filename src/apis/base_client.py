"""Base API client interface"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.person import Person


class BaseAPIClient(ABC):
    """Base interface for all API clients"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.source_name = self.__class__.__name__.replace("Client", "").lower()
    
    @abstractmethod
    def search_people(self, company: str, title: str, **kwargs) -> List[Person]:
        """
        Search for people at a company with a specific title.
        
        Args:
            company: Company name
            title: Job title or role
            **kwargs: Additional source-specific parameters
            
        Returns:
            List of Person objects
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the client is properly configured"""
        pass

