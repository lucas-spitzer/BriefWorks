from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.pipeline import build_pipeline
from app.repositories.production_runs import ProductionRunRepository
from app.services.queue import enqueue_production_run

logger = logging.getLogger(__name__)


class ProductionRunEnqueueError(RuntimeError):
    """Raised when a production run record exists but could not be queued."""


async def create_and_enqueue_production_run(
    *,
    workspace_id: str,
    owner_id: str,
    source_ids: list[str],
    target_artifacts: list[str],
    settings: Settings,
    production_runs: ProductionRunRepository,
) -> dict[str, Any]:
    pipeline = build_pipeline(target_artifacts)

    row = await production_runs.create(
        {
            "workspace_id": workspace_id,
            "owner_id": owner_id,
            "source_ids": source_ids,
            "target_artifacts": target_artifacts,
            "pipeline": pipeline,
            "status": "queued",
        },
    )

    try:
        enqueue_production_run(settings, row["id"])
    except Exception as exc:
        logger.exception(
            "Failed to enqueue production run %s",
            row["id"],
        )
        await production_runs.update(
            row["id"],
            {
                "status": "failed",
                "error": f"Failed to enqueue production run: {exc}",
            },
        )
        raise ProductionRunEnqueueError(str(exc)) from exc

    return row
