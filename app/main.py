"""
Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import logging

from app.config import settings
from app.models import (
    ScreeningRequest,
    ScreeningResponse,
    ErrorResponse,
    RiskLevel
)
from app.geoip import geoip_service
from app.risk_engine import risk_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AML Transaction Screening API - Geographic Risk Assessment",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "endpoints": {
            "docs": f"{settings.API_PREFIX}/docs",
            "screen": f"{settings.API_PREFIX}/screen"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post(
    f"{settings.API_PREFIX}/screen",
    response_model=ScreeningResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Screen Transaction",
    description="Screen a transaction for geographic risk based on user country and IP address"
)
async def screen_transaction(request: ScreeningRequest):
    """
    Screen a transaction for AML risk.
    
    This endpoint analyzes the geographic relationship between the user's
    registered country and the IP address location to assess risk.
    
    Risk Levels:
    - LOW: Same country
    - MEDIUM: Neighboring or same region
    - HIGH: Different regions
    - CRITICAL: High-risk country involved
    """
    try:
        logger.info(f"Screening transaction: {request.transaction_id}")
        logger.info(f"User: {request.user_id}, Country: {request.user_country}, IP: {request.ip_address}")
        
        # Step 1: Perform GeoIP lookup
        geoip_result = await geoip_service.lookup(request.ip_address)
        
        if not geoip_result.success:
            # GeoIP failed - return medium risk with warning
            logger.warning(f"GeoIP lookup failed: {geoip_result.error}")
            
            
            return ScreeningResponse(
                status="success",
                screening_id=f"SCR-{uuid.uuid4().hex[:12].upper()}",
                risk_score=50,
                risk_level=RiskLevel.MEDIUM,
                should_block=False,
                confidence=0.0,
                user_country=request.user_country,
                detected_country="UNKNOWN",
                countries_match=False,
                triggered_rules=[],
                recommendation=f"Unable to verify location (GeoIP service error). Proceed with caution or require manual verification. Error: {geoip_result.error}",
                timestamp=datetime.utcnow().isoformat()
            )
        
        ip_country = geoip_result.country_code
        logger.info(f"IP Country detected: {ip_country} ({geoip_result.country_name})")
        
        # Step 2: Assess risk
        risk_score, risk_level, triggered_rules, recommendation = await risk_engine.assess_risk(
            user_country=request.user_country,
            ip_country=ip_country,
            geoip_confidence=geoip_result.confidence
        )
        
        # Step 3: Determine blocking decision
        # Critical = auto-block, High = flag, Medium/Low = allow
        should_block = risk_level == RiskLevel.CRITICAL
        
        # Step 4: Generate response
        response = ScreeningResponse(
            status="success",
            screening_id=f"SCR-{uuid.uuid4().hex[:12].upper()}",
            risk_score=risk_score,
            risk_level=risk_level,
            should_block=should_block,
            confidence=geoip_result.confidence,
            user_country=request.user_country,
            detected_country=ip_country,
            countries_match=(request.user_country == ip_country),
            triggered_rules=triggered_rules,
            recommendation=recommendation,
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info(
            f"Screening complete: {request.transaction_id} | "
            f"Risk: {risk_level.value.upper()} ({risk_score}/100) | "
            f"Block: {should_block}"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error screening transaction: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during screening",
                "details": {"error": str(e)} if settings.DEBUG else {}
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )