from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_env: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """服务健康检查。后续可扩展为检查依赖服务（PG/Qdrant/Infinity）状态。"""
    from app.core.config import settings

    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        version="0.1.0",
    )
