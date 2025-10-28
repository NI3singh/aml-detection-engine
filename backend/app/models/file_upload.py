"""
File Upload Model

Tracks the status of CSV file uploads and processing.

Why Track File Uploads:
- User feedback (show processing status)
- Traceability (which file did transaction come from)
- Error handling (show what went wrong)
- Audit trail (who uploaded what and when)
- Performance monitoring (processing time)

Status Flow:
PENDING → PROCESSING → COMPLETED (or FAILED)
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin
from app.utils.constants import FileUploadStatus


class FileUpload(Base, TenantMixin):
    """
    File upload tracking model.
    
    Tracks CSV file uploads and their processing status.
    Provides real-time feedback to users.
    """
    
    __tablename__ = "file_uploads"
    
    # ========================================================================
    # Foreign Keys
    # ========================================================================
    
    uploaded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who uploaded the file"
    )
    
    # ========================================================================
    # File Information
    # ========================================================================
    
    filename = Column(
        String(500),
        nullable=False,
        comment="Original filename"
    )
    
    file_path = Column(
        String(1000),
        nullable=True,
        comment="Path where file is stored (temporary)"
    )
    
    file_size = Column(
        Integer,
        nullable=True,
        comment="File size in bytes"
    )
    
    # ========================================================================
    # Processing Status
    # ========================================================================
    
    status = Column(
        SQLEnum(FileUploadStatus, name="file_upload_status", create_type=True),
        nullable=False,
        default=FileUploadStatus.PENDING,
        index=True,
        comment="Current processing status"
    )
    
    total_rows = Column(
        Integer,
        nullable=True,
        comment="Total number of rows in CSV"
    )
    
    processed_rows = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of rows processed so far"
    )
    
    successful_rows = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of rows successfully imported"
    )
    
    failed_rows = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of rows that failed validation"
    )
    
    # ========================================================================
    # Error Handling
    # ========================================================================
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )
    
    validation_errors = Column(
        Text,
        nullable=True,
        comment="Detailed validation errors (JSON or text)"
    )
    
    # ========================================================================
    # Timing
    # ========================================================================
    
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing started"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When processing completed"
    )
    
    # ========================================================================
    # Metadata
    # ========================================================================
    
    alerts_generated = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of alerts generated from this upload"
    )
    
    # ========================================================================
    # Relationships
    # ========================================================================
    
    # Many uploads belong to one organization
    organization = relationship(
        "Organization",
        back_populates="file_uploads",
        lazy="selectin"
    )
    
    # Many uploads are done by one user
    uploaded_by_user = relationship(
        "User",
        back_populates="file_uploads",
        lazy="selectin"
    )
    
    # One upload contains many transactions
    transactions = relationship(
        "Transaction",
        back_populates="file_upload",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    
    def __repr__(self) -> str:
        return (
            f"<FileUpload(id={self.id}, "
            f"filename='{self.filename}', "
            f"status={self.status.value})>"
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def is_processing(self) -> bool:
        """Check if file is currently being processed."""
        return self.status == FileUploadStatus.PROCESSING
    
    def is_completed(self) -> bool:
        """Check if processing is complete."""
        return self.status == FileUploadStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if processing failed."""
        return self.status == FileUploadStatus.FAILED
    
    def get_progress_percentage(self) -> float:
        """
        Calculate processing progress percentage.
        
        Returns:
            float: Progress percentage (0-100)
        """
        if not self.total_rows or self.total_rows == 0:
            return 0.0
        return (self.processed_rows / self.total_rows) * 100
    
    def get_success_rate(self) -> float:
        """
        Calculate success rate of processed rows.
        
        Returns:
            float: Success rate percentage (0-100)
        """
        if not self.processed_rows or self.processed_rows == 0:
            return 0.0
        return (self.successful_rows / self.processed_rows) * 100
    
    def get_processing_time_seconds(self) -> float:
        """
        Calculate processing time in seconds.
        
        Returns:
            float: Processing time in seconds, or 0 if not completed
        """
        if not self.started_at:
            return 0.0
        
        end_time = self.completed_at or self.updated_at
        delta = end_time - self.started_at
        return delta.total_seconds()