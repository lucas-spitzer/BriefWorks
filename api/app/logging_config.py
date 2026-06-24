import logging

from app.config import get_settings


def configure_logging() -> None:
    """Configure application-wide logging for API and worker processes."""
    level_name = get_settings().infra.log_level
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
