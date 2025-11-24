# app/models.py

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum
from datetime import datetime

# --- Enums (Standardized Options) ---

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Status(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

# --- Sub-Models (Nested Parts) ---

class SecurityFlags(BaseModel):
    """Security details inside the response."""
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    is_relay: bool = False

class TriggeredRule(BaseModel):
    """Details of a specific rule that was broken."""
    rule_name: str
    severity: RiskLevel
    description: str
    score_contribution: int

# --- Request Model (Input) ---

class ScreeningRequest(BaseModel):
    """What the user sends to us."""
    transaction_id: str
    user_id: str
    user_country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 code")
    ip_address: str
    
    @field_validator('user_country')
    @classmethod
    def upper_case_country(cls, v):
        return v.upper()

# --- Response Model (Output) ---

class ScreeningResponse(BaseModel):
    """What we send back to the user."""
    status: Status = Status.SUCCESS
    screening_id: str
    
    # Risk Assessment
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    should_block: bool
    confidence: float = Field(..., ge=0, le=1)
    
    # Location Logic
    user_country: str
    detected_country: str
    countries_match: bool
    
    # Security Data
    security: SecurityFlags
    
    # Explainability
    triggered_rules: List[TriggeredRule] = []
    recommendation: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # This ensures the timestamp is serialized to ISO format automatically
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }