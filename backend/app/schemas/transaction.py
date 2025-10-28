"""
Transaction Pydantic Schemas

Defines data validation for:
- CSV upload requests
- Transaction responses
- File upload status

Why separate schemas:
- Validation happens at API boundary
- Clear contract between frontend and backend
- Type-safe data handling
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.utils.constants import TransactionType, Currency, FileUploadStatus


# ============================================================================
# Request Schemas (Input)
# ============================================================================

class TransactionCreate(BaseModel):
    """Schema for creating a single transaction."""
    
    transaction_id: str = Field(
        ...,
        max_length=255,
        description="External transaction ID"
    )
    
    timestamp: datetime = Field(
        ...,
        description="When the transaction occurred"
    )
    
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Transaction amount (must be positive)"
    )
    
    currency: Currency = Field(
        default=Currency.USD,
        description="Currency code"
    )
    
    sender_id: str = Field(
        ...,
        max_length=255,
        description="Sender's account ID"
    )
    
    sender_name: str = Field(
        ...,
        max_length=255,
        description="Sender's name"
    )
    
    sender_country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Sender's country code (ISO 3166-1 alpha-2)"
    )
    
    receiver_id: str = Field(
        ...,
        max_length=255,
        description="Receiver's account ID"
    )
    
    receiver_name: str = Field(
        ...,
        max_length=255,
        description="Receiver's name"
    )
    
    receiver_country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Receiver's country code (ISO 3166-1 alpha-2)"
    )
    
    transaction_type: TransactionType = Field(
        ...,
        description="Type of transaction"
    )
    
    description: Optional[str] = Field(
        None,
        description="Transaction description/memo"
    )
    
    reference_number: Optional[str] = Field(
        None,
        max_length=255,
        description="External reference number"
    )
    
    @field_validator('sender_country', 'receiver_country')
    @classmethod
    def country_code_uppercase(cls, v: str) -> str:
        """Ensure country codes are uppercase."""
        return v.upper()


class CSVUploadResponse(BaseModel):
    """Response after CSV upload."""
    
    upload_id: UUID = Field(
        ...,
        description="File upload ID"
    )
    
    filename: str = Field(
        ...,
        description="Uploaded filename"
    )
    
    status: FileUploadStatus = Field(
        ...,
        description="Processing status"
    )
    
    message: str = Field(
        ...,
        description="Status message"
    )
    
    total_rows: Optional[int] = Field(
        None,
        description="Total rows in CSV"
    )


class CSVProcessingResult(BaseModel):
    """Result of CSV processing."""
    
    upload_id: UUID
    transactions_imported: int = Field(
        ...,
        description="Number of transactions successfully imported"
    )
    
    alerts_generated: int = Field(
        ...,
        description="Number of alerts generated"
    )
    
    processing_time_seconds: float = Field(
        ...,
        description="Time taken to process"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages if any"
    )
    
    success: bool = Field(
        ...,
        description="Whether processing was successful"
    )


# ============================================================================
# Response Schemas (Output)
# ============================================================================

class TransactionResponse(BaseModel):
    """Schema for transaction in API responses."""
    
    id: UUID
    organization_id: UUID
    transaction_id: str
    timestamp: datetime
    amount: Decimal
    currency: Currency
    sender_id: str
    sender_name: str
    sender_country: str
    receiver_id: str
    receiver_name: str
    receiver_country: str
    transaction_type: TransactionType
    description: Optional[str]
    reference_number: Optional[str]
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class TransactionListResponse(BaseModel):
    """Schema for list of transactions."""
    
    transactions: List[TransactionResponse]
    total: int = Field(
        ...,
        description="Total number of transactions"
    )
    page: int = Field(
        default=1,
        description="Current page number"
    )
    page_size: int = Field(
        default=50,
        description="Number of items per page"
    )


class FileUploadResponse(BaseModel):
    """Schema for file upload status."""
    
    id: UUID
    filename: str
    status: FileUploadStatus
    total_rows: Optional[int]
    processed_rows: int
    successful_rows: int
    failed_rows: int
    alerts_generated: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    model_config = {
        "from_attributes": True
    }
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if not self.total_rows or self.total_rows == 0:
            return 0.0
        return (self.processed_rows / self.total_rows) * 100


class TransactionStats(BaseModel):
    """Statistics about transactions."""
    
    total_transactions: int
    total_amount: Decimal
    transactions_today: int
    amount_today: Decimal
    top_senders: List[dict]
    top_receivers: List[dict]