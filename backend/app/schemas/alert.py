"""
Alert Pydantic Schemas

Defines data validation for:
- Alert responses
- Alert review/update
- Alert statistics
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.utils.constants import AlertSeverity, AlertStatus, RuleType
from app.schemas.transaction import TransactionResponse


# ============================================================================
# Request Schemas (Input)
# ============================================================================

class AlertReview(BaseModel):
    """Schema for reviewing an alert."""
    
    status: AlertStatus = Field(
        ...,
        description="New status for the alert"
    )
    
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Analyst's notes about the alert"
    )


class AlertFilter(BaseModel):
    """Schema for filtering alerts."""
    
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    rule_type: Optional[RuleType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ============================================================================
# Response Schemas (Output)
# ============================================================================

class RuleResponse(BaseModel):
    """Schema for rule in API responses."""
    
    id: UUID
    name: str
    description: Optional[str]
    rule_type: RuleType
    is_active: bool
    
    model_config = {
        "from_attributes": True
    }


class AlertResponse(BaseModel):
    """Schema for alert in API responses."""
    
    id: UUID
    organization_id: UUID
    transaction_id: UUID
    rule_id: UUID
    severity: AlertSeverity
    status: AlertStatus
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context about why alert was triggered"
    )
    notes: Optional[str]
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class AlertWithDetails(AlertResponse):
    """Alert with transaction and rule details."""
    
    transaction: TransactionResponse
    rule: RuleResponse
    reviewed_by_name: Optional[str] = None


class AlertListResponse(BaseModel):
    """Schema for list of alerts."""
    
    alerts: List[AlertWithDetails]
    total: int = Field(
        ...,
        description="Total number of alerts"
    )
    page: int = Field(
        default=1,
        description="Current page number"
    )
    page_size: int = Field(
        default=50,
        description="Number of items per page"
    )


class AlertStats(BaseModel):
    """Statistics about alerts."""
    
    total_alerts: int
    new_alerts: int
    under_review: int
    closed_alerts: int
    false_positives: int
    
    by_severity: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of alerts by severity"
    )
    
    by_rule_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of alerts by rule type"
    )
    
    recent_alerts: List[AlertResponse] = Field(
        default_factory=list,
        description="Most recent alerts"
    )


class DashboardStats(BaseModel):
    """Combined statistics for dashboard."""
    
    # Transactions
    total_transactions: int
    transactions_today: int
    
    # Alerts
    total_alerts: int
    new_alerts: int
    critical_alerts: int
    high_alerts: int
    
    # Recent activity
    recent_alerts: List[AlertWithDetails] = Field(
        default_factory=list,
        description="Most recent 10 alerts"
    )
    
    # Alerts by severity
    alerts_by_severity: Dict[str, int] = Field(
        default_factory=dict
    )
    
    # Processing status
    pending_uploads: int = Field(
        default=0,
        description="Number of files being processed"
    )