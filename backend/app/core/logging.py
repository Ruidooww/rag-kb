import logging as stdlib_logging
import sys
from pathlib import Path

from loguru import logger

LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"


class InterceptHandler(stdlib_logging.Handler):
    def emit(self, record: stdlib_logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=level, format=LOG_FORMAT)

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.add(
        logs_dir / "app.log",
        level=level,
        format=LOG_FORMAT,
        retention="7 days",
        rotation="10 MB",
    )

    intercept_handler = InterceptHandler()
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        std_logger = stdlib_logging.getLogger(logger_name)
        std_logger.handlers = [intercept_handler]
        std_logger.propagate = False
        std_logger.setLevel(level)
