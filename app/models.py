"""
Pydantic Models for Request/Response
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityDetails(BaseModel):
    """Security flags related to the IP address."""
    is_vpn: bool = Field(..., description="Is a commercial VPN")
    is_proxy: bool = Field(..., description="Is a known proxy")
    is_tor: bool = Field(..., description="Is a Tor exit node")
    is_relay: bool = Field(..., description="Is a relay/anonymizer")

class ScreeningRequest(BaseModel):
    """Request model for transaction screening."""
    
    transaction_id: str = Field(
        ...,
        description="Unique transaction identifier",
        examples=["TXN12345"]
    )
    user_id: str = Field(
        ...,
        description="User identifier",
        examples=["USER789"]
    )
    user_country: str = Field(
        ...,
        description="User's registered country (ISO 3166-1 alpha-2)",
        min_length=2,
        max_length=2,
        examples=["US"]
    )
    ip_address: str = Field(
        ...,
        description="IP address of the transaction",
        examples=["45.12.34.56"]
    )
    amount: Optional[float] = Field(
        None,
        description="Transaction amount (optional for V1)",
        examples=[100.00]
    )
    
    @field_validator('user_country')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Ensure country code is uppercase."""
        return v.upper()
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Basic IP address validation."""
        parts = v.split('.')
        if len(parts) != 4:
            raise ValueError('Invalid IP address format')
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                raise ValueError('Invalid IP address format')
        return v


class TriggeredRule(BaseModel):
    """Details of a triggered rule."""
    
    rule_name: str = Field(..., description="Name of the rule")
    severity: RiskLevel = Field(..., description="Severity level")
    description: str = Field(..., description="Human-readable description")
    score_contribution: int = Field(..., description="Points added to risk score")


class ScreeningResponse(BaseModel):
    """Response model for transaction screening."""
    
    status: str = Field(..., description="Response status", examples=["success"])
    screening_id: str = Field(..., description="Unique screening identifier")
    
    # Risk Assessment
    risk_score: int = Field(..., description="Risk score (0-100)", ge=0, le=100)
    risk_level: RiskLevel = Field(..., description="Risk level category")
    should_block: bool = Field(..., description="Recommendation to block transaction", examples=[False])
    confidence: float = Field(..., description="Confidence in assessment (0-1)", ge=0, le=1)
    
    # Details
    user_country: str = Field(..., description="User's registered country")
    detected_country: str = Field(..., description="Country detected from IP")
    countries_match: bool = Field(..., description="Whether countries match")

    security: SecurityDetails = Field(..., description="IP security flags")
    
    # Triggered Rules
    triggered_rules: List[TriggeredRule] = Field(default_factory=list)
    
    # Recommendation
    recommendation: str = Field(..., description="Action recommendation")
    
    # Metadata
    timestamp: str = Field(..., description="Screening timestamp (ISO 8601)")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    status: str = Field(default="error", description="Response status")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")