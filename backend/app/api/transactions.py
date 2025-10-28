"""
Transaction API Endpoints

Handles:
- CSV file upload
- Transaction processing
- Transaction listing
- Upload status checking
"""

import pandas as pd
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.core.deps import get_current_active_user
from app.schemas.transaction import (
    CSVUploadResponse,
    CSVProcessingResult,
    FileUploadResponse
)
from app.crud import transaction as crud_transaction
from app.crud import rule as crud_rule
from app.utils.constants import (
    REQUIRED_CSV_COLUMNS,
    FileUploadStatus,
    TransactionType,
    Currency
)

# Import rule engine (we'll create this in Batch 3)
from app.rules.engine import RuleEngine

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ============================================================================
# CSV Upload
# ============================================================================

@router.post("/upload", response_model=CSVProcessingResult)
async def upload_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and process a CSV file of transactions.
    
    For MVP: Processes synchronously (no Celery).
    File must be CSV with required columns.
    """
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    # Read file content
    try:
        content = await file.read()
        file_size = len(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Create file upload record
    file_upload = await crud_transaction.create_file_upload(
        db=db,
        organization_id=current_user.organization_id,
        uploaded_by=current_user.id,
        filename=file.filename,
        file_size=file_size
    )
    
    # Start processing
    start_time = datetime.utcnow()
    errors = []
    
    try:
        # Update status to processing
        await crud_transaction.update_file_upload_status(
            db=db,
            file_upload=file_upload,
            status=FileUploadStatus.PROCESSING,
            started_at=start_time
        )
        
        # Parse CSV
        df = pd.read_csv(
            pd.io.common.BytesIO(content),
            parse_dates=['timestamp']
        )
        
        total_rows = len(df)
        
        # Update total rows
        await crud_transaction.update_file_upload_status(
            db=db,
            file_upload=file_upload,
            status=FileUploadStatus.PROCESSING,
            total_rows=total_rows
        )
        
        # Validate required columns
        missing_columns = set(REQUIRED_CSV_COLUMNS) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Process transactions in batches
        batch_size = 1000
        successful_count = 0
        failed_count = 0
        transactions_data = []
        
        for idx, row in df.iterrows():
            try:
                # Validate and prepare transaction data
                txn_data = {
                    'transaction_id': str(row['transaction_id']),
                    'timestamp': pd.to_datetime(row['timestamp']),
                    'amount': float(row['amount']),
                    'currency': Currency(row.get('currency', 'USD')),
                    'sender_id': str(row['sender_id']),
                    'sender_name': str(row['sender_name']),
                    'sender_country': str(row['sender_country']).upper(),
                    'receiver_id': str(row['receiver_id']),
                    'receiver_name': str(row['receiver_name']),
                    'receiver_country': str(row['receiver_country']).upper(),
                    'transaction_type': TransactionType(row['transaction_type']),
                    'description': str(row.get('description', '')) if pd.notna(row.get('description')) else None,
                    'reference_number': str(row.get('reference_number', '')) if pd.notna(row.get('reference_number')) else None,
                }
                
                transactions_data.append(txn_data)
                successful_count += 1
                
                # Insert batch when it reaches batch_size
                if len(transactions_data) >= batch_size:
                    await crud_transaction.create_transactions_bulk(
                        db=db,
                        organization_id=current_user.organization_id,
                        upload_id=file_upload.id,
                        transactions_data=transactions_data
                    )
                    transactions_data = []
                    
                    # Update progress
                    await crud_transaction.update_file_upload_status(
                        db=db,
                        file_upload=file_upload,
                        status=FileUploadStatus.PROCESSING,
                        processed_rows=successful_count + failed_count,
                        successful_rows=successful_count,
                        failed_rows=failed_count
                    )
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Row {idx + 2}: {str(e)}")  # +2 because of header and 0-index
                continue
        
        # Insert remaining transactions
        if transactions_data:
            await crud_transaction.create_transactions_bulk(
                db=db,
                organization_id=current_user.organization_id,
                upload_id=file_upload.id,
                transactions_data=transactions_data
            )
        
        # Now run rule engine on all uploaded transactions
        # Get active rules
        active_rules = await crud_rule.get_active_rules(
            db=db,
            organization_id=current_user.organization_id
        )
        
        # Initialize rule engine
        rule_engine = RuleEngine(db=db, organization_id=current_user.organization_id)
        
        # Get all transactions from this upload
        from sqlalchemy import select
        from app.models.transaction import Transaction
        
        result = await db.execute(
            select(Transaction).where(Transaction.upload_id == file_upload.id)
        )
        transactions = list(result.scalars().all())
        
        # Run rules on all transactions
        alerts_generated = 0
        for transaction in transactions:
            alerts = await rule_engine.evaluate_transaction(transaction, active_rules)
            alerts_generated += len(alerts)
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Update file upload as completed
        await crud_transaction.update_file_upload_status(
            db=db,
            file_upload=file_upload,
            status=FileUploadStatus.COMPLETED,
            processed_rows=total_rows,
            successful_rows=successful_count,
            failed_rows=failed_count,
            alerts_generated=alerts_generated,
            completed_at=end_time
        )
        
        return CSVProcessingResult(
            upload_id=file_upload.id,
            transactions_imported=successful_count,
            alerts_generated=alerts_generated,
            processing_time_seconds=processing_time,
            errors=errors[:10] if errors else [],  # Return first 10 errors only
            success=True
        )
        
    except Exception as e:
        # Mark upload as failed
        await crud_transaction.update_file_upload_status(
            db=db,
            file_upload=file_upload,
            status=FileUploadStatus.FAILED,
            error_message=str(e),
            completed_at=datetime.utcnow()
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV: {str(e)}"
        )


# ============================================================================
# Get Upload Status
# ============================================================================

@router.get("/uploads/{upload_id}", response_model=FileUploadResponse)
async def get_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the status of a file upload.
    """
    
    from uuid import UUID
    
    try:
        upload_uuid = UUID(upload_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload ID"
        )
    
    file_upload = await crud_transaction.get_file_upload_by_id(
        db=db,
        upload_id=upload_uuid,
        organization_id=current_user.organization_id
    )
    
    if not file_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )
    
    return FileUploadResponse.model_validate(file_upload)