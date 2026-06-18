#!/usr/bin/env python3
"""Backfill api_usage and cost_usd from existing skill_runs.token_usage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from app.services.skill_run_backfill import backfill_fields_for_skill_run
from app.worker.db import WorkerDatabase


def _needs_backfill(row: dict) -> bool:
    cost_usd = float(row.get("cost_usd") or 0)

    if cost_usd > 0:
        return False

    token_usage = row.get("token_usage") or {}

    if isinstance(token_usage, str):
        token_usage = json.loads(token_usage)

    has_token_usage = isinstance(token_usage, dict) and any(token_usage.values())

    api_usage = row.get("api_usage") or {}

    if isinstance(api_usage, str):
        api_usage = json.loads(api_usage)

    has_api_usage = isinstance(api_usage, dict) and bool(api_usage.get("calls"))

    return has_token_usage or not has_api_usage


def _artifact_manifests_for_skill_run(
    db: WorkerDatabase,
    row: dict,
) -> list[dict]:
    output = row.get("output") or {}

    if isinstance(output, str):
        output = json.loads(output)

    if not isinstance(output, dict):
        return []

    files = output.get("files")

    if not isinstance(files, list):
        return []

    manifests: list[dict] = []

    for file_row in files:
        if not isinstance(file_row, dict):
            continue

        artifact_id = file_row.get("artifact_id")

        if not isinstance(artifact_id, str):
            continue

        artifact = db.get_artifact(artifact_id)

        if not isinstance(artifact, dict):
            continue

        manifest = artifact.get("manifest")

        if isinstance(manifest, dict):
            manifests.append(manifest)

    return manifests


def backfill_skill_runs(
    db: WorkerDatabase,
    rows: list[dict],
    *,
    dry_run: bool,
) -> dict[str, float]:
    updated_runs: list[dict] = []
    production_totals: dict[str, float] = {}

    for row in rows:
        if not _needs_backfill(row):
            continue

        billing = backfill_fields_for_skill_run(
            row,
            artifact_manifests=_artifact_manifests_for_skill_run(db, row),
        )
        updated_runs.append(
            {
                "id": row["id"],
                "production_run_id": row.get("production_run_id"),
                "skill_id": row.get("skill_id"),
                "billing": billing,
            },
        )

    if dry_run:
        for item in updated_runs:
            production_run_id = item.get("production_run_id")

            if production_run_id:
                production_totals[production_run_id] = round(
                    production_totals.get(production_run_id, 0) + item["billing"]["cost_usd"],
                    6,
                )

            print(
                f"[dry-run] {item['skill_id']} ({item['id']}): "
                f"${item['billing']['cost_usd']:.6f} "
                f"({item['billing']['api_usage']['totals']['input_tokens']} in / "
                f"{item['billing']['api_usage']['totals']['output_tokens']} out tokens)",
            )

        return production_totals

    for item in updated_runs:
        db.update_skill_run(
            item["id"],
            {
                "api_usage": item["billing"]["api_usage"],
                "cost_usd": item["billing"]["cost_usd"],
            },
        )
        production_run_id = item.get("production_run_id")

        if production_run_id:
            production_totals[production_run_id] = round(
                production_totals.get(production_run_id, 0) + item["billing"]["cost_usd"],
                6,
            )

        print(
            f"Updated {item['skill_id']} ({item['id']}): "
            f"${item['billing']['cost_usd']:.6f}",
        )

    for production_run_id, _partial in production_totals.items():
        cost_usd = db.sum_skill_run_costs(production_run_id)
        db.update_production_run(production_run_id, {"cost_usd": cost_usd})
        print(f"Updated production run {production_run_id}: ${cost_usd:.6f}")

    return production_totals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-run-id", help="Backfill skill runs for one production run")
    parser.add_argument("--workspace-id", help="Backfill all skill runs in a workspace")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    if not args.production_run_id and not args.workspace_id:
        parser.error("Provide --production-run-id or --workspace-id")

    db = WorkerDatabase()

    if args.production_run_id:
        rows = db.list_skill_runs_for_production_run(args.production_run_id)
    else:
        rows = db.list_skill_runs_for_workspace(args.workspace_id)

    if not rows:
        print("No skill runs found.", file=sys.stderr)
        return 1

    backfill_skill_runs(db, rows, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
