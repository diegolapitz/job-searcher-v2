from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import uvicorn
from sqlalchemy import func, select

from app.api import app
from app.config import ROOT
from app.db import init_db, session_scope
from app.migration import migrate_v1
from app.models import Evaluation, Job, RawJob, Run
from app.pipeline import run_pipeline
from app.services.logging import configure_logging


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(prog="job-searcher-v2")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db")
    migrate = subparsers.add_parser("migrate-v1")
    migrate.add_argument("csv", type=Path)
    run = subparsers.add_parser("run")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--no-notify", action="store_true")
    run.add_argument(
        "--sources",
        help="Comma-separated source allowlist, e.g. greenhouse,ashby,hiringroom",
    )
    run.add_argument("--max-requests", type=int)
    serve = subparsers.add_parser("serve")
    serve.add_argument(
        "--port", type=int, default=int(os.getenv("JOB_SEARCHER_API_PORT", "8765"))
    )
    subparsers.add_parser("audit")
    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        print(f"Database initialized under {ROOT / 'data'}")
    elif args.command == "migrate-v1":
        init_db()
        print(json.dumps(migrate_v1(args.csv), indent=2, ensure_ascii=False))
    elif args.command == "run":
        init_db()
        print(
            json.dumps(
                run_pipeline(
                    dry_run=args.dry_run,
                    notify=not args.no_notify,
                    only_sources={
                        source.strip().casefold()
                        for source in (args.sources or "").split(",")
                        if source.strip()
                    }
                    or None,
                    max_requests=args.max_requests,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
    elif args.command == "serve":
        init_db()
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    elif args.command == "audit":
        init_db()
        print(json.dumps(audit_database(), indent=2, ensure_ascii=False))


def audit_database() -> dict:
    with session_scope() as session:
        return {
            "jobs": session.scalar(select(func.count(Job.id))) or 0,
            "raw_snapshots": session.scalar(select(func.count(RawJob.id))) or 0,
            "evaluations": session.scalar(select(func.count(Evaluation.id))) or 0,
            "runs": session.scalar(select(func.count(Run.id))) or 0,
            "missing_location": session.scalar(
                select(func.count(Job.id)).where(Job.location_text.is_(None))
            )
            or 0,
            "missing_description": session.scalar(
                select(func.count(Job.id)).where(Job.description.is_(None))
            )
            or 0,
            "duplicate_canonical_ids": session.scalar(
                select(func.count())
                .select_from(
                    select(Job.canonical_id)
                    .group_by(Job.canonical_id)
                    .having(func.count(Job.id) > 1)
                    .subquery()
                )
            )
            or 0,
        }


if __name__ == "__main__":
    main()
