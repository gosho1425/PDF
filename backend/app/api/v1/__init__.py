from fastapi import APIRouter
from app.api.v1 import settings_router, papers_router, scan_router

api_router = APIRouter()
api_router.include_router(settings_router.router, prefix="/settings", tags=["Settings"])
api_router.include_router(papers_router.router,   prefix="/papers",   tags=["Papers"])
api_router.include_router(scan_router.router,     prefix="/scan",     tags=["Scan"])
