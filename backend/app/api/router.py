from fastapi import APIRouter

from app.api import health, query

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(query.router)
