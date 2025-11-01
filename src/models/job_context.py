"""Job context data model"""

from typing import List, Optional
from pydantic import BaseModel


class JobContext(BaseModel):
    """
    Complete context for a job search.
    
    This is what comes from your upstream service.
    """
    
    # Job posting info
    job_url: str
    job_html: Optional[str] = None  # Raw HTML of job posting
    job_text: Optional[str] = None  # Extracted text
    
    # Extracted from job posting
    company: Optional[str] = None
    company_domain: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    
    # Candidate info
    candidate_resume: str  # Resume text
    candidate_linkedin_url: Optional[str] = None
    
    # Extracted from resume
    candidate_schools: List[str] = []  # Universities attended
    candidate_past_companies: List[str] = []  # Previous employers
    candidate_skills: List[str] = []
    
    # User answers to questions
    user_context: Optional[dict] = None  # Any additional context


class CandidateProfile(BaseModel):
    """Parsed candidate profile"""
    
    name: Optional[str] = None
    current_title: Optional[str] = None
    schools: List[str] = []
    past_companies: List[str] = []
    skills: List[str] = []
    linkedin_url: Optional[str] = None
    
    # For alumni matching
    graduation_years: dict = {}  # school -> year
    company_tenures: dict = {}  # company -> years

