"""
Transaction CRUD Operations

Handles all database operations for transactions.
Optimized for bulk operations (CSV uploads).
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction
from app.models.file_upload import FileUpload
from app.utils.constants import FileUploadStatus


# ============================================================================
# Create Operations
# ============================================================================

async def create_transaction(
    db: AsyncSession,
    organization_id: UUID,
    upload_id: Optional[UUID],
    **transaction_data
) -> Transaction:
    """
    Create a single transaction.
    
    Args:
        db: Database session
        organization_id: Organization ID
        upload_id: File upload ID (if from CSV)
        **transaction_data: Transaction fields
        
    Returns:
        Transaction: Created transaction
    """
    transaction = Transaction(
        organization_id=organization_id,
        upload_id=upload_id,
        **transaction_data
    )
    
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    return transaction


async def create_transactions_bulk(
    db: AsyncSession,
    organization_id: UUID,
    upload_id: Optional[UUID],
    transactions_data: List[dict]
) -> int:
    """
    Create multiple transactions efficiently (bulk insert).
    
    Args:
        db: Database session
        organization_id: Organization ID
        upload_id: File upload ID
        transactions_data: List of transaction dictionaries
        
    Returns:
        int: Number of transactions created
    """
    transactions = [
        Transaction(
            organization_id=organization_id,
            upload_id=upload_id,
            **txn_data
        )
        for txn_data in transactions_data
    ]
    
    db.add_all(transactions)
    await db.commit()
    
    return len(transactions)


# ============================================================================
# Read Operations
# ============================================================================

async def get_transaction_by_id(
    db: AsyncSession,
    transaction_id: UUID,
    organization_id: UUID
) -> Optional[Transaction]:
    """
    Get transaction by ID.
    
    Args:
        db: Database session
        transaction_id: Transaction ID
        organization_id: Organization ID (for security)
        
    Returns:
        Transaction or None
    """
    result = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.id == transaction_id,
                Transaction.organization_id == organization_id
            )
        )
    )
    return result.scalar_one_or_none()


async def get_transactions_by_sender(
    db: AsyncSession,
    sender_id: str,
    organization_id: UUID,
    time_from: Optional[datetime] = None,
    time_to: Optional[datetime] = None,
    limit: Optional[int] = None
) -> List[Transaction]:
    """
    Get transactions by sender ID within time range.
    
    Used by high-frequency and velocity rules.
    
    Args:
        db: Database session
        sender_id: Sender's account ID
        organization_id: Organization ID
        time_from: Start time (optional)
        time_to: End time (optional)
        limit: Maximum number of results
        
    Returns:
        List of transactions
    """
    query = select(Transaction).where(
        and_(
            Transaction.sender_id == sender_id,
            Transaction.organization_id == organization_id
        )
    )
    
    if time_from:
        query = query.where(Transaction.timestamp >= time_from)
    
    if time_to:
        query = query.where(Transaction.timestamp <= time_to)
    
    query = query.order_by(Transaction.timestamp.desc())
    
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_transactions_by_accounts(
    db: AsyncSession,
    account_ids: List[str],
    organization_id: UUID,
    time_window_minutes: int,
    reference_time: datetime
) -> List[Transaction]:
    """
    Get recent transactions involving specific accounts.
    
    Used by rapid movement rule to find transaction chains.
    
    Args:
        db: Database session
        account_ids: List of account IDs
        organization_id: Organization ID
        time_window_minutes: Time window in minutes
        reference_time: Reference timestamp
        
    Returns:
        List of transactions
    """
    time_from = reference_time - timedelta(minutes=time_window_minutes)
    
    result = await db.execute(
        select(Transaction)
        .where(
            and_(
                Transaction.organization_id == organization_id,
                Transaction.timestamp >= time_from,
                Transaction.timestamp <= reference_time,
                (
                    Transaction.sender_id.in_(account_ids) |
                    Transaction.receiver_id.in_(account_ids)
                )
            )
        )
        .order_by(Transaction.timestamp.asc())
    )
    
    return list(result.scalars().all())


async def count_transactions(
    db: AsyncSession,
    organization_id: UUID
) -> int:
    """
    Count total transactions for an organization.
    
    Args:
        db: Database session
        organization_id: Organization ID
        
    Returns:
        int: Number of transactions
    """
    result = await db.execute(
        select(func.count(Transaction.id))
        .where(Transaction.organization_id == organization_id)
    )
    return result.scalar_one()


async def count_transactions_today(
    db: AsyncSession,
    organization_id: UUID
) -> int:
    """
    Count transactions created today.
    
    Args:
        db: Database session
        organization_id: Organization ID
        
    Returns:
        int: Number of transactions today
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(func.count(Transaction.id))
        .where(
            and_(
                Transaction.organization_id == organization_id,
                Transaction.created_at >= today_start
            )
        )
    )
    return result.scalar_one()


# ============================================================================
# File Upload Operations
# ============================================================================

async def create_file_upload(
    db: AsyncSession,
    organization_id: UUID,
    uploaded_by: UUID,
    filename: str,
    file_size: int
) -> FileUpload:
    """
    Create a file upload record.
    
    Args:
        db: Database session
        organization_id: Organization ID
        uploaded_by: User ID who uploaded
        filename: Original filename
        file_size: File size in bytes
        
    Returns:
        FileUpload: Created record
    """
    file_upload = FileUpload(
        organization_id=organization_id,
        uploaded_by=uploaded_by,
        filename=filename,
        file_size=file_size,
        status=FileUploadStatus.PENDING,
        total_rows=0,
        processed_rows=0,
        successful_rows=0,
        failed_rows=0,
        alerts_generated=0
    )
    
    db.add(file_upload)
    await db.commit()
    await db.refresh(file_upload)
    
    return file_upload


async def update_file_upload_status(
    db: AsyncSession,
    file_upload: FileUpload,
    status: FileUploadStatus,
    **kwargs
) -> FileUpload:
    """
    Update file upload status and fields.
    
    Args:
        db: Database session
        file_upload: FileUpload to update
        status: New status
        **kwargs: Additional fields to update
        
    Returns:
        FileUpload: Updated record
    """
    file_upload.status = status
    
    for key, value in kwargs.items():
        if hasattr(file_upload, key):
            setattr(file_upload, key, value)
    
    await db.commit()
    await db.refresh(file_upload)
    
    return file_upload


async def get_file_upload_by_id(
    db: AsyncSession,
    upload_id: UUID,
    organization_id: UUID
) -> Optional[FileUpload]:
    """
    Get file upload by ID.
    
    Args:
        db: Database session
        upload_id: Upload ID
        organization_id: Organization ID
        
    Returns:
        FileUpload or None
    """
    result = await db.execute(
        select(FileUpload)
        .where(
            and_(
                FileUpload.id == upload_id,
                FileUpload.organization_id == organization_id
            )
        )
    )
    return result.scalar_one_or_none()