# main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import db_client
from app.routes.screening import router as screening_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Lifecycle Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executes startup and shutdown logic.
    """
    # 1. Startup: Connect to DB
    logger.info("🚀 Starting AML Risk Engine...")
    db_client.connect()
    
    # Optional: Quick DB Ping to ensure connection is alive
    try:
        await db_client.get_db().command("ping")
        logger.info("✅ MongoDB Connection verified!")
    except Exception as e:
        logger.error(f"❌ MongoDB Ping Failed: {e}")
    
    yield  # The application runs here
    
    # 2. Shutdown: Close DB
    logger.info("🛑 Shutting down...")
    db_client.close()

# --- App Initialization ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="V4 AML Risk Engine with Hybrid DB/API Intelligence",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan # Attach the lifecycle manager
)

# --- Middleware (CORS) ---
# Allows your frontend (if you have one) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(screening_router, prefix=settings.API_PREFIX, tags=["Screening"])

# --- Health Check ---
@app.get("/health", tags=["System"])
async def health_check():
    """
    Simple health check to see if the system is up.
    """
    return {
        "status": "operational",
        "version": settings.VERSION,
        "mode": "debug" if settings.DEBUG else "production"
    }

@app.get("/")
async def root():
    return {"message": "AML Risk Engine V4 is running. Go to /api/v1/docs for Swagger UI."}

# --- Dev Server Entry Point ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )