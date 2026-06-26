from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import time
import logging

from models import AnalyzeTicketRequest, AnalyzeTicketResponse
from analyzer import investigate_ticket

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("investigator")

app = FastAPI(
    title="QueueStorm Investigator API",
    description="AI-powered customer support copilot for Digital Finance",
    version="1.0"
)

# Error handlers to match API spec requirements

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Validation error handler"""
    logger.warning(f"Request validation failed: {exc.errors()}")
    # Extract a clean, non-sensitive error message
    error_msgs = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "invalid value")
        error_msgs.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Malformed input or validation error.",
            "details": error_msgs
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General error fallback"""
    logger.error(f"Unhandled internal error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An internal server error occurred. Please contact support."
        }
    )

# API Routes

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}

@app.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
async def analyze_ticket(payload: AnalyzeTicketRequest):
    """Investigate ticket"""
    start_time = time.time()
    logger.info(f"Received ticket: {payload.ticket_id}")
    
    # Run investigation
    response = investigate_ticket(payload)
    
    duration = time.time() - start_time
    logger.info(f"Processed ticket {payload.ticket_id} in {duration:.4f} seconds")
    return response

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Run uvicorn on port 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
