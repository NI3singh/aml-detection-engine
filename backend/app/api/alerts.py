"""
Alert API Endpoints

Handles:
- List alerts with filtering
- Get alert details
- Review alerts (update status)
- Get alert statistics
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.core.deps import get_current_active_user, get_current_analyst_or_admin
from app.schemas.alert import (
    AlertResponse,
    AlertWithDetails,
    AlertListResponse,
    AlertReview,
    AlertStats,
    DashboardStats
)
from app.schemas.user import MessageResponse
from app.crud import alert as crud_alert
from app.crud import transaction as crud_transaction
from app.utils.constants import AlertSeverity, AlertStatus

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ============================================================================
# List Alerts
# ============================================================================

@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    status: Optional[AlertStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of alerts with filtering and pagination.
    """
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get alerts
    alerts = await crud_alert.get_alerts(
        db=db,
        organization_id=current_user.organization_id,
        severity=severity,
        status=status,
        limit=page_size,
        offset=offset
    )
    
    # Get total count
    total = await crud_alert.count_alerts(
        db=db,
        organization_id=current_user.organization_id,
        severity=severity,
        status=status
    )
    
    # Convert to response format
    alerts_with_details = []
    for alert in alerts:
        alert_dict = AlertWithDetails.model_validate(alert).model_dump()
        
        # Add reviewer name if available
        if alert.reviewed_by_user:
            alert_dict['reviewed_by_name'] = alert.reviewed_by_user.full_name
        
        alerts_with_details.append(AlertWithDetails(**alert_dict))
    
    return AlertListResponse(
        alerts=alerts_with_details,
        total=total,
        page=page,
        page_size=page_size
    )


# ============================================================================
# Get Alert Details
# ============================================================================

@router.get("/{alert_id}", response_model=AlertWithDetails)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific alert.
    """
    
    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID"
        )
    
    alert = await crud_alert.get_alert_by_id(
        db=db,
        alert_id=alert_uuid,
        organization_id=current_user.organization_id
    )
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Convert to response
    alert_dict = AlertWithDetails.model_validate(alert).model_dump()
    
    if alert.reviewed_by_user:
        alert_dict['reviewed_by_name'] = alert.reviewed_by_user.full_name
    
    return AlertWithDetails(**alert_dict)


# ============================================================================
# Review Alert
# ============================================================================

@router.post("/{alert_id}/review", response_model=AlertWithDetails)
async def review_alert(
    alert_id: str,
    review_data: AlertReview,
    current_user: User = Depends(get_current_analyst_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Review an alert and update its status.
    
    Requires analyst or admin role.
    """
    
    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert ID"
        )
    
    # Get alert
    alert = await crud_alert.get_alert_by_id(
        db=db,
        alert_id=alert_uuid,
        organization_id=current_user.organization_id
    )
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update alert status
    updated_alert = await crud_alert.update_alert_status(
        db=db,
        alert=alert,
        status=review_data.status,
        reviewed_by=current_user.id,
        notes=review_data.notes
    )
    
    # Return updated alert
    alert_dict = AlertWithDetails.model_validate(updated_alert).model_dump()
    alert_dict['reviewed_by_name'] = current_user.full_name
    
    return AlertWithDetails(**alert_dict)


# ============================================================================
# Get Alert Statistics
# ============================================================================

@router.get("/stats/summary", response_model=AlertStats)
async def get_alert_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics about alerts for the organization.
    """
    
    # Get counts by status
    status_counts = await crud_alert.count_alerts_by_status(
        db=db,
        organization_id=current_user.organization_id
    )
    
    # Get counts by severity
    severity_counts = await crud_alert.count_alerts_by_severity(
        db=db,
        organization_id=current_user.organization_id
    )
    
    # Get recent alerts
    recent_alerts = await crud_alert.get_recent_alerts(
        db=db,
        organization_id=current_user.organization_id,
        limit=10
    )
    
    # Calculate totals
    total_alerts = sum(status_counts.values())
    
    return AlertStats(
        total_alerts=total_alerts,
        new_alerts=status_counts.get("new", 0),
        under_review=status_counts.get("under_review", 0),
        closed_alerts=status_counts.get("closed", 0),
        false_positives=status_counts.get("false_positive", 0),
        by_severity=severity_counts,
        by_rule_type={},  # TODO: Implement if needed
        recent_alerts=[AlertResponse.model_validate(a) for a in recent_alerts]
    )


# ============================================================================
# Dashboard Statistics
# ============================================================================

@router.get("/stats/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive statistics for dashboard.
    """
    
    # Get transaction counts
    total_transactions = await crud_transaction.count_transactions(
        db=db,
        organization_id=current_user.organization_id
    )
    
    transactions_today = await crud_transaction.count_transactions_today(
        db=db,
        organization_id=current_user.organization_id
    )
    
    # Get alert counts
    total_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=current_user.organization_id
    )
    
    new_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=current_user.organization_id,
        status=AlertStatus.NEW
    )
    
    critical_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=current_user.organization_id,
        severity=AlertSeverity.CRITICAL
    )
    
    high_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=current_user.organization_id,
        severity=AlertSeverity.HIGH
    )
    
    # Get alerts by severity
    severity_counts = await crud_alert.count_alerts_by_severity(
        db=db,
        organization_id=current_user.organization_id
    )
    
    # Get recent alerts
    recent_alerts_data = await crud_alert.get_recent_alerts(
        db=db,
        organization_id=current_user.organization_id,
        limit=10
    )
    
    # Convert to response format
    recent_alerts = []
    for alert in recent_alerts_data:
        alert_dict = AlertWithDetails.model_validate(alert).model_dump()
        if alert.reviewed_by_user:
            alert_dict['reviewed_by_name'] = alert.reviewed_by_user.full_name
        recent_alerts.append(AlertWithDetails(**alert_dict))
    
    return DashboardStats(
        total_transactions=total_transactions,
        transactions_today=transactions_today,
        total_alerts=total_alerts,
        new_alerts=new_alerts,
        critical_alerts=critical_alerts,
        high_alerts=high_alerts,
        recent_alerts=recent_alerts,
        alerts_by_severity=severity_counts,
        pending_uploads=0  # TODO: Implement if needed
    )