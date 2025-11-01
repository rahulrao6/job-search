"""Person data model"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field


class PersonCategory(str, Enum):
    """Categories of people to target for referrals"""
    MANAGER = "manager"
    RECRUITER = "recruiter"
    PEER = "peer"
    SENIOR = "senior"
    UNKNOWN = "unknown"


class Person(BaseModel):
    """Unified person record from any data source"""
    
    # Core identification
    name: str
    title: Optional[str] = None
    company: str
    
    # Contact & profile info
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    
    # Metadata
    source: str  # Which data source found this person
    category: PersonCategory = PersonCategory.UNKNOWN
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Additional context
    department: Optional[str] = None
    location: Optional[str] = None
    experience_years: Optional[int] = None
    skills: List[str] = Field(default_factory=list)
    
    # Evidence & tracking
    evidence_url: Optional[str] = None  # URL where we found this person
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Cost tracking
    api_cost: float = 0.0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def __hash__(self):
        """Hash based on name and company for deduplication"""
        return hash((self.name.lower(), self.company.lower()))
    
    def __eq__(self, other):
        """Equality based on name and company"""
        if not isinstance(other, Person):
            return False
        return (self.name.lower() == other.name.lower() and 
                self.company.lower() == other.company.lower())

