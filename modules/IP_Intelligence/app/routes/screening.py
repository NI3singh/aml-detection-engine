# app/routes/screening.py

from fastapi import APIRouter, HTTPException, status
from app.models import ScreeningRequest, ScreeningResponse, Status
from app.services.ip_intelligence import ip_intelligence
import uuid
import logging

# Create a router instance
router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/screen", 
    response_model=ScreeningResponse,
    summary="Screen a Transaction",
    description="Analyze IP and User Country against DBs (Tor/VPN/Clean) and External API."
)
async def screen_transaction(request: ScreeningRequest):
    """
    Main Screening Endpoint.
    """
    try:
        logger.info(f"🔍 Request: {request.transaction_id} | User: {request.user_country} | IP: {request.ip_address}")
        
        # 1. Call the Brain
        analysis_result = await ip_intelligence.analyze_ip(
            ip=request.ip_address,
            user_country=request.user_country
        )
        
        # 2. Construct the Response
        # We merge the analysis result (risk scores) with the request info (ids)
        response = ScreeningResponse(
            status=Status.SUCCESS,
            screening_id=f"SCR-{uuid.uuid4().hex[:12].upper()}",
            
            # Request Data Pass-through
            user_country=request.user_country,
            
            # Intelligence Data
            detected_country=analysis_result["detected_country"],
            countries_match=analysis_result["countries_match"],
            risk_score=analysis_result["risk_score"],
            risk_level=analysis_result["risk_level"],
            should_block=analysis_result["should_block"],
            confidence=analysis_result["confidence"],
            security=analysis_result["security"],
            triggered_rules=analysis_result["triggered_rules"],
            recommendation=analysis_result["recommendation"]
        )
        
        logger.info(f"✅ Result: {request.transaction_id} -> {analysis_result['risk_level']} ({analysis_result['risk_score']})")
        return response

    except Exception as e:
        logger.error(f"💥 Error processing {request.transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Risk Engine Error: {str(e)}"
        )