#!/usr/bin/env python3
"""Start the BriefWorks RQ worker."""

from redis import Redis
from rq import Worker

from app.config import get_settings
from app.logging_config import configure_logging


def main() -> None:
    configure_logging()
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker([settings.rq_queue_name], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
