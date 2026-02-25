import sys

from loguru import logger

from app.config import settings


def setup_logging() -> None:
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{extra[request_id]} | {extra[clinic_id]} | "
        "<level>{message}</level>"
    )

    logger.configure(extra={"request_id": "", "clinic_id": ""})

    # Console output
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # JSON file output
    logger.add(
        "logs/mezbon.log",
        format=log_format,
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="gz",
        serialize=True,
    )
