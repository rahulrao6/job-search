"""Database models matching Supabase schema"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from src.models.person import Person, PersonCategory


class PersonDiscovery(BaseModel):
    """Model for people_discoveries table"""
    id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    person_type: str  # Maps to PersonCategory
    full_name: str
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    confidence_score: Optional[float] = None
    connection_path: Optional[str] = None
    mutual_connections: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    contacted: bool = False
    created_at: Optional[datetime] = None
    
    # Additional fields we might want to store
    company: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    relevance_score: Optional[float] = None
    match_reasons: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class JobRecord(BaseModel):
    """Model for jobs table"""
    id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    source_url: Optional[str] = None
    company_name: str
    company_domain: Optional[str] = None
    job_title: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    department: Optional[str] = None
    scraped_data: Optional[Dict[str, Any]] = None
    required_skills: Optional[List[str]] = None
    nice_to_have_skills: Optional[List[str]] = None
    experience_required: Optional[str] = None
    education_required: Optional[str] = None
    application_deadline: Optional[datetime] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Model for profiles table"""
    id: UUID
    email: str
    full_name: Optional[str] = None
    resume_url: Optional[str] = None
    resume_parsed_data: Optional[Dict[str, Any]] = None
    linkedin_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Extracted fields from resume_parsed_data
    skills: List[str] = Field(default_factory=list)
    past_companies: List[str] = Field(default_factory=list)
    schools: List[str] = Field(default_factory=list)
    current_title: Optional[str] = None
    years_experience: Optional[int] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_resume_data(cls, id: UUID, email: str, resume_data: Optional[Dict[str, Any]] = None):
        """Create UserProfile from resume_parsed_data"""
        if resume_data:
            return cls(
                id=id,
                email=email,
                skills=resume_data.get('skills', []),
                past_companies=resume_data.get('past_companies', []),
                schools=resume_data.get('schools', []),
                current_title=resume_data.get('current_title'),
                years_experience=resume_data.get('years_experience')
            )
        return cls(id=id, email=email)


class APIKey(BaseModel):
    """Model for api_keys table"""
    id: UUID
    user_id: UUID
    key_hash: str
    key_prefix: str
    tier: str = "free"
    searches_per_month: int = 10
    searches_used_this_month: int = 0
    rate_limit_per_minute: int = 5
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class APIKeyContext(BaseModel):
    """Context returned after API key validation"""
    key_id: UUID
    user_id: UUID
    tier: str
    searches_per_month: int
    searches_used_this_month: int
    searches_remaining: int
    rate_limit_per_minute: int
    is_active: bool


def person_to_discovery(person: Person, job_id: Optional[UUID] = None, 
                        user_id: Optional[UUID] = None,
                        relevance_score: Optional[float] = None,
                        match_reasons: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convert Person model to PersonDiscovery dict for Supabase insert.
    Filters out None values and validates required fields.
    """
    discovery = {
        'person_type': person.category.value if person.category else 'unknown',
        'full_name': person.name or '',
        'contacted': False
    }
    
    # Add optional fields only if they have values
    if job_id:
        discovery['job_id'] = str(job_id)
    if user_id:
        discovery['user_id'] = str(user_id)
    if person.title:
        discovery['title'] = person.title
    if person.email:
        discovery['email'] = person.email
    if person.linkedin_url:
        discovery['linkedin_url'] = person.linkedin_url
    if person.confidence_score is not None:
        try:
            discovery['confidence_score'] = float(person.confidence_score)
        except (ValueError, TypeError):
            pass  # Skip invalid confidence scores
    if person.company:
        discovery['company'] = person.company
    if person.department:
        discovery['department'] = person.department
    if person.location:
        discovery['location'] = person.location
    if person.source:
        discovery['source'] = person.source
    if person.evidence_url:
        discovery['connection_path'] = person.evidence_url
    if relevance_score is not None:
        try:
            discovery['relevance_score'] = float(relevance_score)
        except (ValueError, TypeError):
            pass  # Skip invalid relevance scores
    if match_reasons:
        discovery['match_reasons'] = match_reasons
    
    # Validate required fields
    if not discovery.get('full_name'):
        raise ValueError("Person name is required for discovery")
    if not discovery.get('person_type'):
        discovery['person_type'] = 'unknown'
    
    return discovery

