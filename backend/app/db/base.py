"""
Database Base - Import all models

This file imports all models so that Alembic can detect them
and generate migrations automatically.

IMPORTANT: Any new model must be imported here!
"""

from app.db.session import Base  # noqa: F401

# Import all models so they are registered with Base.metadata
from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.rule import Rule  # noqa: F401
from app.models.alert import Alert  # noqa: F401
from app.models.file_upload import FileUpload  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401

__all__ = ["Base"]