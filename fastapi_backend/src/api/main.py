from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.typing import typing_router

# Initialize FastAPI with basic metadata
app = FastAPI(
    title="Typing Speed Monitor API",
    description="REST API for tracking and computing typing speed statistics.",
    version="0.1.0",
)

# Keep existing CORS allowing broad access; restrict to common methods and headers as requested
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Root health check remains
@app.get("/", summary="Health Check")
def health_check():
    """Simple health endpoint to verify the service is up."""
    return {"message": "Healthy"}

# Readiness endpoint
@app.get("/ready", summary="Readiness Check")
def readiness_check():
    """Readiness endpoint to signal the service is ready to accept traffic."""
    return {"status": "ready"}

# Include typing router under /api prefix
app.include_router(typing_router, prefix="/api")
