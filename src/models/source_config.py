"""Source configuration model"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SourceStatus(str, Enum):
    """Health status of a data source"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISABLED = "disabled"


class SourceConfig(BaseModel):
    """Configuration for a data source"""
    
    name: str
    enabled: bool = True
    requires_auth: bool = False
    
    # Rate limiting
    rate_limit: float = 1.0  # requests per second
    max_requests_per_hour: Optional[int] = None
    
    # Cost tracking
    cost_per_request: float = 0.0
    
    # Priority (1 = highest)
    priority: int = 1
    
    # Health monitoring
    status: SourceStatus = SourceStatus.HEALTHY
    failure_count: int = 0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    
    class Config:
        use_enum_values = True

