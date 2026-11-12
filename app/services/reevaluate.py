from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, or_, select

from app.config import settings
from app.db import session_scope
from app.models import Evaluation, Job, Run
from app.services.evaluator import JobEvaluator


def reevaluate_jobs(
    *,
    use_ai: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    evaluator = JobEvaluator()
    strategy_version = evaluator.prompt_version
    latest = (
        select(Evaluation.job_id, func.max(Evaluation.id).label("evaluation_id"))
        .group_by(Evaluation.job_id)
        .subquery()
    )

    with session_scope() as session:
        statement = (
            select(Job)
            .outerjoin(latest, Job.id == latest.c.job_id)
            .outerjoin(Evaluation, Evaluation.id == latest.c.evaluation_id)
            .order_by(desc(Job.first_seen_at))
        )
        if not force:
            statement = statement.where(
                or_(
                    Evaluation.id.is_(None),
                    Evaluation.prompt_version != strategy_version,
                )
            )
        if limit is not None:
            statement = statement.limit(limit)
        jobs = list(session.scalars(statement))

    if not jobs:
        return {
            "run_id": None,
            "strategy_version": strategy_version,
            "status": "dry-run" if dry_run else "success",
            "eligible_jobs": 0,
            "evaluated_jobs": 0,
            "ai_evaluations": 0,
            "heuristic_evaluations": 0,
            "force": force,
        }

    preliminary = [(job, evaluator.keyword_fallback(job)) for job in jobs]
    ai_limit = (
        int(settings()["ai"]["max_evaluations_per_run"])
        if use_ai and evaluator.enabled
        else 0
    )
    ai_candidates = {
        job.id
        for job, result in sorted(
            preliminary, key=lambda item: item[1].priority_score, reverse=True
        )[:ai_limit]
        if len(job.description or "") >= 100
    }

    results = []
    ai_evaluated = 0
    for job, fallback_result in preliminary:
        if job.id in ai_candidates:
            result = evaluator.evaluate(job)
            ai_evaluated += int(result.method == "ai")
        else:
            result = fallback_result
        results.append((job.id, result))

    run_id = None
    if not dry_run:
        with session_scope() as session:
            run = Run(
                status="running",
                mode="reevaluation",
                started_at=datetime.utcnow(),
                notes=f"strategy={strategy_version}",
            )
            session.add(run)
            session.flush()
            run_id = run.id
            for job_id, result in results:
                session.add(Evaluation(job_id=job_id, **result.__dict__))
            run.status = "success"
            run.finished_at = datetime.utcnow()
            run.evaluated_count = len(results)
            run.notes = f"strategy={strategy_version}; ai_evaluations={ai_evaluated}"

    return {
        "run_id": run_id,
        "strategy_version": strategy_version,
        "status": "dry-run" if dry_run else "success",
        "eligible_jobs": len(jobs),
        "evaluated_jobs": len(results),
        "ai_evaluations": ai_evaluated,
        "heuristic_evaluations": len(results) - ai_evaluated,
        "force": force,
    }
