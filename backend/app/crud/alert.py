"""
Alert CRUD Operations

Handles all database operations for alerts.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.transaction import Transaction
from app.models.rule import Rule
from app.models.user import User
from app.utils.constants import AlertSeverity, AlertStatus


# ============================================================================
# Create Operations
# ============================================================================

async def create_alert(
    db: AsyncSession,
    organization_id: UUID,
    transaction_id: UUID,
    rule_id: UUID,
    severity: AlertSeverity,
    details: dict
) -> Alert:
    """
    Create a new alert.
    
    Args:
        db: Database session
        organization_id: Organization ID
        transaction_id: Transaction ID
        rule_id: Rule ID
        severity: Alert severity
        details: Additional details about why alert was triggered
        
    Returns:
        Alert: Created alert
    """
    alert = Alert(
        organization_id=organization_id,
        transaction_id=transaction_id,
        rule_id=rule_id,
        severity=severity,
        status=AlertStatus.NEW,
        details=details
    )
    
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    
    return alert


# ============================================================================
# Read Operations
# ============================================================================

async def get_alert_by_id(
    db: AsyncSession,
    alert_id: UUID,
    organization_id: UUID
) -> Optional[Alert]:
    """
    Get alert by ID with related data.
    
    Args:
        db: Database session
        alert_id: Alert ID
        organization_id: Organization ID
        
    Returns:
        Alert or None
    """
    result = await db.execute(
        select(Alert)
        .where(
            and_(
                Alert.id == alert_id,
                Alert.organization_id == organization_id
            )
        )
        .options(
            selectinload(Alert.transaction),
            selectinload(Alert.rule),
            selectinload(Alert.reviewed_by_user)
        )
    )
    return result.scalar_one_or_none()


async def get_alerts(
    db: AsyncSession,
    organization_id: UUID,
    severity: Optional[AlertSeverity] = None,
    status: Optional[AlertStatus] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Alert]:
    """
    Get alerts with filtering.
    
    Args:
        db: Database session
        organization_id: Organization ID
        severity: Filter by severity
        status: Filter by status
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        List[Alert]: List of alerts
    """
    query = select(Alert).where(Alert.organization_id == organization_id)
    
    if severity:
        query = query.where(Alert.severity == severity)
    
    if status:
        query = query.where(Alert.status == status)
    
    query = (
        query
        .options(
            selectinload(Alert.transaction),
            selectinload(Alert.rule),
            selectinload(Alert.reviewed_by_user)
        )
        .order_by(desc(Alert.created_at))
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_alerts(
    db: AsyncSession,
    organization_id: UUID,
    limit: int = 10
) -> List[Alert]:
    """
    Get most recent alerts.
    
    Args:
        db: Database session
        organization_id: Organization ID
        limit: Number of alerts to return
        
    Returns:
        List[Alert]: Recent alerts
    """
    result = await db.execute(
        select(Alert)
        .where(Alert.organization_id == organization_id)
        .options(
            selectinload(Alert.transaction),
            selectinload(Alert.rule),
            selectinload(Alert.reviewed_by_user)
        )
        .order_by(desc(Alert.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_alerts(
    db: AsyncSession,
    organization_id: UUID,
    severity: Optional[AlertSeverity] = None,
    status: Optional[AlertStatus] = None
) -> int:
    """
    Count alerts with optional filtering.
    
    Args:
        db: Database session
        organization_id: Organization ID
        severity: Filter by severity
        status: Filter by status
        
    Returns:
        int: Number of alerts
    """
    query = select(func.count(Alert.id)).where(
        Alert.organization_id == organization_id
    )
    
    if severity:
        query = query.where(Alert.severity == severity)
    
    if status:
        query = query.where(Alert.status == status)
    
    result = await db.execute(query)
    return result.scalar_one()


async def count_alerts_by_status(
    db: AsyncSession,
    organization_id: UUID
) -> dict:
    """
    Count alerts grouped by status.
    
    Args:
        db: Database session
        organization_id: Organization ID
        
    Returns:
        dict: Status counts
    """
    counts = {
        "new": 0,
        "under_review": 0,
        "closed": 0,
        "false_positive": 0
    }
    
    for status in AlertStatus:
        count = await count_alerts(db, organization_id, status=status)
        counts[status.value] = count
    
    return counts


async def count_alerts_by_severity(
    db: AsyncSession,
    organization_id: UUID
) -> dict:
    """
    Count alerts grouped by severity.
    
    Args:
        db: Database session
        organization_id: Organization ID
        
    Returns:
        dict: Severity counts
    """
    counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0
    }
    
    for severity in AlertSeverity:
        count = await count_alerts(db, organization_id, severity=severity)
        counts[severity.value] = count
    
    return counts


# ============================================================================
# Update Operations
# ============================================================================

async def update_alert_status(
    db: AsyncSession,
    alert: Alert,
    status: AlertStatus,
    reviewed_by: UUID,
    notes: Optional[str] = None
) -> Alert:
    """
    Update alert status and review information.
    
    Args:
        db: Database session
        alert: Alert to update
        status: New status
        reviewed_by: User ID who reviewed
        notes: Optional notes
        
    Returns:
        Alert: Updated alert
    """
    alert.status = status
    alert.reviewed_by = reviewed_by
    alert.reviewed_at = datetime.utcnow()
    
    if notes:
        alert.notes = notes
    
    await db.commit()
    await db.refresh(alert)
    
    return alert


async def add_alert_note(
    db: AsyncSession,
    alert: Alert,
    note: str
) -> Alert:
    """
    Add or append a note to an alert.
    
    Args:
        db: Database session
        alert: Alert to update
        note: Note text
        
    Returns:
        Alert: Updated alert
    """
    if alert.notes:
        alert.notes = f"{alert.notes}\n\n{note}"
    else:
        alert.notes = note
    
    await db.commit()
    await db.refresh(alert)
    
    return alert