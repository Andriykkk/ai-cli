"""
Basic Routes
Root and health check endpoints
"""

from datetime import datetime
from fastapi import APIRouter

# Create router
router = APIRouter(tags=["basic"])


@router.get("/")
async def root():
    return {"message": "AI CLI Server", "version": "0.1.0"}


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}