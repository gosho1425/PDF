from fastapi import APIRouter
from app.api.v1 import papers, extractions, jobs, export

api_router = APIRouter()
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(extractions.router, prefix="/extractions", tags=["extractions"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
