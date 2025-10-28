"""
Constants and Enumerations

Centralizing all constants makes it easier to maintain and modify values.
Using Python Enums provides type safety and IDE autocompletion.

Why Enums:
- Type-safe (can't accidentally use wrong value)
- Auto-completion in IDE
- Easy to add new values
- Self-documenting code
"""

from enum import Enum


# ============================================================================
# User & Organization Related
# ============================================================================

class UserRole(str, Enum):
    """
    User roles within an organization.
    
    - ADMIN: Full access, can manage users and rules
    - ANALYST: Can review alerts and view transactions
    - VIEWER: Read-only access to dashboards
    """
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


# ============================================================================
# Transaction Related
# ============================================================================

class TransactionType(str, Enum):
    """
    Types of financial transactions.
    
    Common transaction types in AML monitoring.
    """
    WIRE = "WIRE"                    # Wire transfer
    ACH = "ACH"                      # Automated Clearing House
    CARD = "CARD"                    # Card payment
    CHECK = "CHECK"                  # Check payment
    CASH = "CASH"                    # Cash transaction
    INTERNAL = "INTERNAL"            # Internal transfer
    INTERNATIONAL = "INTERNATIONAL"  # Cross-border transfer
    OTHER = "OTHER"                  # Other types


class Currency(str, Enum):
    """
    Supported currency codes (ISO 4217).
    
    Can be extended as needed.
    """
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
    INR = "INR"
    # Add more as needed


# ============================================================================
# Rule Related
# ============================================================================

class RuleType(str, Enum):
    """
    Types of AML rules implemented in the system.
    
    Each rule type corresponds to a specific detection pattern.
    """
    LARGE_TRANSACTION = "large_transaction"
    HIGH_FREQUENCY = "high_frequency"
    RAPID_MOVEMENT = "rapid_movement"
    HIGH_RISK_COUNTRY = "high_risk_country"
    ROUND_AMOUNT = "round_amount"
    VELOCITY_CHANGE = "velocity_change"
    # Future: Add ML-based rules here


# ============================================================================
# Alert Related
# ============================================================================

class AlertSeverity(str, Enum):
    """
    Severity levels for alerts.
    
    Helps analysts prioritize their review queue.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """
    Alert lifecycle status.
    
    Tracks the review and resolution process.
    """
    NEW = "new"                          # Just created, not reviewed
    UNDER_REVIEW = "under_review"        # Analyst is investigating
    CLOSED = "closed"                    # Confirmed suspicious, escalated
    FALSE_POSITIVE = "false_positive"    # Determined to be legitimate


# ============================================================================
# File Upload Related
# ============================================================================

class FileUploadStatus(str, Enum):
    """
    Status of CSV file processing.
    
    Tracks the lifecycle of uploaded files.
    """
    PENDING = "pending"          # File uploaded, queued for processing
    PROCESSING = "processing"    # Currently being processed
    COMPLETED = "completed"      # Successfully processed
    FAILED = "failed"           # Processing failed with errors


# ============================================================================
# Country Codes
# ============================================================================

# ISO 3166-1 alpha-2 country codes
# Full list: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2

HIGH_RISK_COUNTRIES = {
    "KP",  # North Korea (Democratic People's Republic of Korea)
    "IR",  # Iran (Islamic Republic of Iran)
    "SY",  # Syria (Syrian Arab Republic)
    "CU",  # Cuba
    "VE",  # Venezuela (Bolivarian Republic of Venezuela)
    "MM",  # Myanmar (Burma)
    "BY",  # Belarus
    "ZW",  # Zimbabwe
    "SD",  # Sudan
    "SS",  # South Sudan
}

# Common country names to codes mapping (for CSV processing)
COUNTRY_NAME_TO_CODE = {
    "united states": "US",
    "usa": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "canada": "CA",
    "germany": "DE",
    "france": "FR",
    "italy": "IT",
    "spain": "ES",
    "china": "CN",
    "japan": "JP",
    "india": "IN",
    "australia": "AU",
    "brazil": "BR",
    "mexico": "MX",
    "russia": "RU",
    "south korea": "KR",
    "korea": "KR",
    # Add more mappings as needed
}


# ============================================================================
# CSV Processing
# ============================================================================

REQUIRED_CSV_COLUMNS = [
    "transaction_id",
    "timestamp",
    "amount",
    "currency",
    "sender_id",
    "sender_name",
    "sender_country",
    "receiver_id",
    "receiver_name",
    "receiver_country",
    "transaction_type",
]

# Optional CSV columns (nice to have but not required)
OPTIONAL_CSV_COLUMNS = [
    "description",
    "reference_number",
    "channel",
]


# ============================================================================
# Rule Default Parameters
# ============================================================================

DEFAULT_RULE_PARAMETERS = {
    RuleType.LARGE_TRANSACTION: {
        "threshold_amount": 10_000.00,
        "currency": "USD",
    },
    RuleType.HIGH_FREQUENCY: {
        "max_transactions": 10,
        "time_window_minutes": 60,
    },
    RuleType.RAPID_MOVEMENT: {
        "max_hops": 3,
        "time_window_minutes": 30,
    },
    RuleType.HIGH_RISK_COUNTRY: {
        "high_risk_countries": list(HIGH_RISK_COUNTRIES),
    },
    RuleType.ROUND_AMOUNT: {
        "round_threshold": 1_000.00,
        "tolerance": 0.01,  # Consider amounts within 1% as "round"
    },
    RuleType.VELOCITY_CHANGE: {
        "multiplier": 3.0,  # Alert if volume increases by 3x
        "baseline_window_days": 30,
        "comparison_window_days": 7,
    },
}


# ============================================================================
# Time Constants
# ============================================================================

SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7
DAYS_PER_MONTH = 30  # Approximate


# ============================================================================
# Pagination
# ============================================================================

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000


# ============================================================================
# Messages
# ============================================================================

class ErrorMessage:
    """Standardized error messages."""
    
    # Authentication
    INVALID_CREDENTIALS = "Invalid email or password"
    ACCOUNT_DISABLED = "Account is disabled"
    INSUFFICIENT_PERMISSIONS = "Insufficient permissions"
    TOKEN_EXPIRED = "Token has expired"
    TOKEN_INVALID = "Invalid token"
    
    # User
    USER_NOT_FOUND = "User not found"
    USER_ALREADY_EXISTS = "User with this email already exists"
    WEAK_PASSWORD = "Password is too weak"
    
    # Organization
    ORGANIZATION_NOT_FOUND = "Organization not found"
    
    # Transaction
    TRANSACTION_NOT_FOUND = "Transaction not found"
    INVALID_CSV_FORMAT = "Invalid CSV format"
    CSV_TOO_LARGE = "CSV file is too large"
    MISSING_REQUIRED_COLUMNS = "CSV is missing required columns"
    
    # Rule
    RULE_NOT_FOUND = "Rule not found"
    INVALID_RULE_PARAMETERS = "Invalid rule parameters"
    
    # Alert
    ALERT_NOT_FOUND = "Alert not found"
    ALERT_ALREADY_REVIEWED = "Alert has already been reviewed"
    
    # File Upload
    FILE_NOT_FOUND = "File upload not found"
    FILE_PROCESSING = "File is still being processed"
    
    # General
    INTERNAL_ERROR = "An internal error occurred"
    NOT_FOUND = "Resource not found"
    VALIDATION_ERROR = "Validation error"


class SuccessMessage:
    """Standardized success messages."""
    
    USER_CREATED = "User created successfully"
    USER_UPDATED = "User updated successfully"
    LOGIN_SUCCESS = "Login successful"
    LOGOUT_SUCCESS = "Logout successful"
    
    TRANSACTION_CREATED = "Transaction created successfully"
    FILE_UPLOADED = "File uploaded successfully"
    FILE_PROCESSING_STARTED = "File processing started"
    
    RULE_CREATED = "Rule created successfully"
    RULE_UPDATED = "Rule updated successfully"
    RULE_DELETED = "Rule deleted successfully"
    
    ALERT_REVIEWED = "Alert reviewed successfully"
    ALERT_UPDATED = "Alert updated successfully"