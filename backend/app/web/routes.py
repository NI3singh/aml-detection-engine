"""
Web Routes - HTML Pages

Serves HTML pages using Jinja2 templates.
Uses HTMX for dynamic updates without full page reloads.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user_optional, get_current_active_user
from app.models.user import User
from app.crud import alert as crud_alert
from app.crud import transaction as crud_transaction
from app.utils.constants import AlertStatus, AlertSeverity

router = APIRouter(tags=["Web Pages"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


# ============================================================================
# Helper Functions
# ============================================================================

def add_user_to_context(request: Request, user: User = None):
    """Add user info to template context."""
    return {
        "request": request,
        "user": user,
        "is_authenticated": user is not None
    }


# ============================================================================
# Public Pages
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user: User = Depends(get_current_user_optional)
):
    """
    Home page - redirects to dashboard if logged in, otherwise to login.
    """
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: User = Depends(get_current_user_optional)
):
    """
    Login page.
    """
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    context = add_user_to_context(request, user)
    return templates.TemplateResponse("login.html", context)


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    user: User = Depends(get_current_user_optional)
):
    """
    Registration page.
    """
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    context = add_user_to_context(request, user)
    return templates.TemplateResponse("register.html", context)


# ============================================================================
# Protected Pages (Require Authentication)
# ============================================================================

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Main dashboard page.
    """
    # Get summary statistics
    total_transactions = await crud_transaction.count_transactions(
        db=db,
        organization_id=user.organization_id
    )
    
    transactions_today = await crud_transaction.count_transactions_today(
        db=db,
        organization_id=user.organization_id
    )
    
    total_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=user.organization_id
    )
    
    new_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=user.organization_id,
        status=AlertStatus.NEW
    )
    
    critical_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=user.organization_id,
        severity=AlertSeverity.CRITICAL
    )
    
    high_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=user.organization_id,
        severity=AlertSeverity.HIGH
    )
    
    # Get recent alerts
    recent_alerts = await crud_alert.get_recent_alerts(
        db=db,
        organization_id=user.organization_id,
        limit=10
    )
    
    # Get alerts by severity
    severity_counts = await crud_alert.count_alerts_by_severity(
        db=db,
        organization_id=user.organization_id
    )
    
    context = add_user_to_context(request, user)
    context.update({
        "total_transactions": total_transactions,
        "transactions_today": transactions_today,
        "total_alerts": total_alerts,
        "new_alerts": new_alerts,
        "critical_alerts": critical_alerts,
        "high_alerts": high_alerts,
        "recent_alerts": recent_alerts,
        "severity_counts": severity_counts
    })
    
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(
    request: Request,
    user: User = Depends(get_current_active_user)
):
    """
    CSV upload page.
    """
    context = add_user_to_context(request, user)
    return templates.TemplateResponse("upload.html", context)


@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Alerts listing page.
    """
    # Get all alerts (first 50)
    alerts = await crud_alert.get_alerts(
        db=db,
        organization_id=user.organization_id,
        limit=50,
        offset=0
    )
    
    # Get total count
    total_alerts = await crud_alert.count_alerts(
        db=db,
        organization_id=user.organization_id
    )
    
    context = add_user_to_context(request, user)
    context.update({
        "alerts": alerts,
        "total_alerts": total_alerts,
        "AlertSeverity": AlertSeverity,
        "AlertStatus": AlertStatus
    })
    
    return templates.TemplateResponse("alerts.html", context)


@router.get("/alerts/{alert_id}", response_class=HTMLResponse)
async def alert_detail_page(
    alert_id: str,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Alert detail page.
    """
    from uuid import UUID
    
    try:
        alert_uuid = UUID(alert_id)
    except ValueError:
        return RedirectResponse(url="/alerts", status_code=302)
    
    alert = await crud_alert.get_alert_by_id(
        db=db,
        alert_id=alert_uuid,
        organization_id=user.organization_id
    )
    
    if not alert:
        return RedirectResponse(url="/alerts", status_code=302)
    
    context = add_user_to_context(request, user)
    context.update({
        "alert": alert,
        "AlertStatus": AlertStatus
    })
    
    return templates.TemplateResponse("alert_detail.html", context)