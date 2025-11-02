"""Request/response schemas for API validation"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Request Schemas

class SearchRequest(BaseModel):
    """Request schema for /api/v1/search"""
    company: str = Field(..., min_length=1, description="Company name")
    job_title: str = Field(..., min_length=1, description="Job title")
    department: Optional[str] = Field(None, description="Department")
    location: Optional[str] = Field(None, description="Location")
    company_domain: Optional[str] = Field(None, description="Company domain")
    
    # Profile data (optional)
    profile: Optional[Dict[str, Any]] = Field(None, description="User profile data")
    skills: Optional[List[str]] = Field(None, description="User skills")
    past_companies: Optional[List[str]] = Field(None, description="Past companies")
    schools: Optional[List[str]] = Field(None, description="Schools attended")
    current_title: Optional[str] = Field(None, description="Current job title")
    years_experience: Optional[int] = Field(None, description="Years of experience")
    
    # Job context (optional)
    job_url: Optional[str] = Field(None, description="Job posting URL")
    job_description: Optional[str] = Field(None, description="Job description")
    required_skills: Optional[List[str]] = Field(None, description="Required skills for job")
    
    # Filters (optional)
    filters: Optional[Dict[str, Any]] = Field(None, description="Result filters")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence score")
    max_results: Optional[int] = Field(None, gt=0, description="Maximum results to return")
    
    # Preferences (optional)
    preferences: Optional[Dict[str, bool]] = Field(None, description="Search preferences")


class ProfileSaveRequest(BaseModel):
    """Request schema for /api/v1/profile/save"""
    profile: Dict[str, Any] = Field(..., description="Profile data to save")
    user_id: Optional[str] = Field(None, description="User ID (if updating existing)")


class JobAnalyzeRequest(BaseModel):
    """Request schema for /api/v1/job/analyze"""
    job_url: Optional[str] = Field(None, description="Job posting URL")
    job_text: Optional[str] = Field(None, description="Job posting text")
    company: Optional[str] = Field(None, description="Company name")


# Response Schemas

class PersonResponse(BaseModel):
    """Response schema for a person/connection"""
    name: str
    title: Optional[str] = None
    company: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    source: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: str
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    match_reasons: Optional[List[str]] = None
    department: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Response schema for /api/v1/search"""
    success: bool = True
    data: Dict[str, Any]
    
    class Config:
        # Allow arbitrary types for nested dicts
        arbitrary_types_allowed = True


class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = False
    error: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    version: str = "1.0.0"
    sources: Dict[str, Any]
    database: Optional[Dict[str, Any]] = None


class QuotaResponse(BaseModel):
    """Quota response schema"""
    tier: str
    searches_per_month: int
    searches_used_this_month: int
    searches_remaining: int
    rate_limit_per_minute: int


class ProfileResponse(BaseModel):
    """Profile response schema"""
    success: bool = True
    data: Dict[str, Any]


# Helper function to format search results

def format_search_response(
    results: Dict,
    search_id: Optional[str] = None,
    timing: Optional[Dict[str, Any]] = None,
    cost: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format search results into API response format.
    
    Args:
        results: Results from ConnectionFinder
        search_id: Optional search ID
        timing: Optional timing information
        cost: Optional cost information
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "success": True,
        "data": {
            "query": {
                "company": results.get("company", ""),
                "job_title": results.get("title", "")
            },
            "results": {
                "total_found": results.get("total_found", 0),
                "by_category": results.get("by_category", {}),
                "category_counts": results.get("category_counts", {})
            },
            "source_stats": results.get("source_stats", {}),
            "cost_stats": results.get("cost_stats", {})
        }
    }
    
    if search_id:
        response["data"]["search_id"] = search_id
    
    if "insights" in results:
        response["data"]["insights"] = results["insights"]
    
    if timing:
        response["data"]["timing"] = timing
    
    if cost:
        response["data"]["cost"] = cost
    
    return response

