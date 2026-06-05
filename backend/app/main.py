from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.services.storage import S3CompatibleStorage


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.app_log_level)
    logger.info(f"Starting RAG-KB backend in {settings.app_env} mode")
    storage = S3CompatibleStorage()
    await storage.ensure_ready()
    _app.state.storage = storage
    yield
    logger.info("Shutting down RAG-KB backend")


app = FastAPI(
    title="RAG-KB API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


app.include_router(api_router)
