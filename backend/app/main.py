"""
Main FastAPI Application

This is the entry point for the AML Transaction Monitoring System.
Initializes all routers, middleware, and configurations.

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.transactions import router as transactions_router
from app.api.alerts import router as alerts_router
from app.web.routes import router as web_router

# ============================================================================
# Create FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Anti-Money Laundering Transaction Monitoring System",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ============================================================================
# CORS Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Mount Static Files
# ============================================================================

# Uncomment if you add static files (images, custom CSS, etc.)
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ============================================================================
# Include API Routers
# ============================================================================

# API routes under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")

# Web routes (HTML pages) - no prefix
app.include_router(web_router)

# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to dashboard."""
    return RedirectResponse(url="/dashboard")

# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: System status
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Run on application startup.
    
    Can be used for:
    - Database connection verification
    - Cache warming
    - Loading initial data
    """
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"📊 Dashboard: http://localhost:8000/dashboard")
    print(f"📚 API Docs: http://localhost:8000/api/docs")
    
    # Verify database connection
    from app.db.session import check_db_connection
    db_connected = await check_db_connection()
    
    if db_connected:
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")

# ============================================================================
# Shutdown Event
# ============================================================================

@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown.
    
    Cleanup tasks:
    - Close database connections
    - Clear caches
    - Save state
    """
    print(f"👋 Shutting down {settings.PROJECT_NAME}")

# ============================================================================
# Exception Handlers (Optional - Add as needed)
# ============================================================================

# from fastapi.exceptions import RequestValidationError
# from fastapi.responses import JSONResponse

# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request, exc):
#     """Custom validation error handler."""
#     return JSONResponse(
#         status_code=422,
#         content={"detail": "Validation error", "errors": exc.errors()}
#     )

# ============================================================================
# Development Info
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("="*50)
    print(f"🛡️  {settings.PROJECT_NAME}")
    print("="*50)
    print("\n📖 Starting development server...")
    print("\n🌐 URLs:")
    print("   - Dashboard: http://localhost:8000/dashboard")
    print("   - Login: http://localhost:8000/login")
    print("   - API Docs: http://localhost:8000/api/docs")
    print("\n⚙️  Press CTRL+C to stop\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )