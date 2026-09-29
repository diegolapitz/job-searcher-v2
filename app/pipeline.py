from __future__ import annotations

import logging
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from sqlalchemy import desc, select

from app.config import searches, settings, source_catalog, watchlist
from app.connectors import (
    AdzunaConnector,
    CatalogATSConnector,
    ComputrabajoConnector,
    HiringRoomConnector,
    JobSpyConnector,
    PublicFeedConnector,
    RemotiveConnector,
    RigzoneConnector,
)
from app.connectors.base import CollectionRequest, CollectionResult
from app.db import session_scope
from app.models import (
    Evaluation,
    Job,
    JobObservation,
    Notification,
    RawJob,
    Run,
    SourceRun,
)
from app.services.evaluator import JobEvaluator
from app.services.identity import canonical_job_id, payload_hash
from app.services.normalize import json_safe, normalize_job
from app.services.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


def build_collection_requests() -> list[tuple[str, CollectionRequest]]:
    results_wanted = int(settings()["results_per_search"])
    requests: list[tuple[str, CollectionRequest]] = []
    for search in searches():
        for term in search["terms"]:
            for location, country in zip(search["locations"], search["countries"], strict=False):
                for source in search["sources"]:
                    requests.append(
                        (
                            source,
                            CollectionRequest(
                                search_id=search["id"],
                                family=search["family"],
                                term=term,
                                location=location,
                                country=country,
                                lookback_hours=int(search["lookback_hours"]),
                                results_wanted=results_wanted,
                            ),
                        )
                    )
    catalog = source_catalog()
    for source, config in catalog.get("catalogs", {}).items():
        if not config.get("enabled", False):
            continue
        for board in config.get("boards", []):
            requests.append(
                (
                    source,
                    CollectionRequest(
                        search_id=f"{source}_{board['slug']}",
                        family="company_catalog",
                        term="",
                        location="",
                        country="",
                        lookback_hours=24 * 365,
                        results_wanted=10_000,
                        options=board,
                    ),
                )
            )

    for source, config in catalog.get("feeds", {}).items():
        if not config.get("enabled", False):
            continue
        requests.append(
            (
                source,
                CollectionRequest(
                    search_id=f"feed_{source}",
                    family="public_feed",
                    term="",
                    location="Remote",
                    country="",
                    lookback_hours=720,
                    results_wanted=int(config.get("results_wanted", 500)),
                    options=config,
                ),
            )
        )

    for source, config in catalog.get("verticals", {}).items():
        if not config.get("enabled", False):
            continue
        for location in config.get("locations", [""]):
            for term in config.get("terms", [""]):
                requests.append(
                    (
                        source,
                        CollectionRequest(
                            search_id=f"{source}_{location or 'global'}",
                            family="industry_vertical",
                            term=term,
                            location=location,
                            country=location,
                            lookback_hours=720,
                            results_wanted=int(config.get("results_wanted", 50)),
                            options=config,
                        ),
                    )
                )

    adzuna = catalog.get("api_sources", {}).get("adzuna", {})
    adzuna_ready = all(os.getenv(name) for name in adzuna.get("requires_env", []))
    if adzuna.get("enabled", False) and adzuna_ready:
        adzuna_terms = [
            "process engineer",
            "manufacturing engineer",
            "reliability engineer",
            "industrial data analyst",
            "operations analytics",
            "continuous improvement",
            "supply chain analytics",
            "automation engineer",
        ]
        for country in adzuna.get("countries", []):
            for term in adzuna_terms:
                requests.append(
                    (
                        "adzuna",
                        CollectionRequest(
                            search_id=f"adzuna_{country['code']}",
                            family="international_market",
                            term=term,
                            location=country["location"],
                            country=country["location"],
                            lookback_hours=720,
                            results_wanted=50,
                            options={**country, "country_code": country["code"], "pages": 2},
                        ),
                    )
                )

    experimental = catalog.get("experimental_jobspy", {})
    representative_terms = [
        "process engineer",
        "industrial data analyst",
        "reliability engineer",
    ]
    for source, config in experimental.items():
        if not config.get("enabled", False):
            continue
        for term in representative_terms:
            requests.append(
                (
                    source,
                    CollectionRequest(
                        search_id=f"experimental_{source}",
                        family="experimental_aggregator",
                        term=term,
                        location="Argentina",
                        country="Argentina",
                        lookback_hours=720,
                        results_wanted=30,
                    ),
                )
            )

    unique: dict[tuple, tuple[str, CollectionRequest]] = {}
    for source, request in requests:
        key = (
            source,
            request.search_id,
            request.term,
            request.location,
            json.dumps(request.options, sort_keys=True, ensure_ascii=False),
        )
        unique[key] = (source, request)
    return list(unique.values())


def connector_for(source: str):
    if source in {"linkedin", "indeed", "google", "glassdoor", "zip_recruiter"}:
        return JobSpyConnector(source)
    if source == "computrabajo":
        return ComputrabajoConnector()
    if source == "remotive":
        return RemotiveConnector()
    if source in {"greenhouse", "ashby", "lever"}:
        return CatalogATSConnector(source)
    if source == "hiringroom":
        return HiringRoomConnector()
    if source in {"remoteok", "jobicy", "arbeitnow"}:
        return PublicFeedConnector(source)
    if source == "adzuna":
        return AdzunaConnector()
    if source == "rigzone":
        return RigzoneConnector()
    raise ValueError(f"Unknown connector: {source}")


def run_pipeline(
    dry_run: bool = False,
    notify: bool = True,
    only_sources: set[str] | None = None,
    max_requests: int | None = None,
) -> dict:
    started = time.perf_counter()
    mode = "dry-run" if dry_run else "live"
    with session_scope() as session:
        run = Run(status="running", mode=mode)
        session.add(run)
        session.flush()
        run_id = run.id

    try:
        return _execute_pipeline(
            run_id,
            dry_run,
            notify,
            started,
            only_sources=only_sources,
            max_requests=max_requests,
        )
    except Exception as exc:
        duration = time.perf_counter() - started
        logger.exception("Run %s failed", run_id)
        with session_scope() as session:
            run = session.get(Run, run_id)
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error_count = max(run.error_count or 0, 1)
            run.duration_seconds = duration
            run.notes = f"{type(exc).__name__}: {exc}"[:4000]
        raise


def _execute_pipeline(
    run_id: int,
    dry_run: bool,
    notify: bool,
    started: float,
    only_sources: set[str] | None = None,
    max_requests: int | None = None,
) -> dict:
    requests = build_collection_requests()
    if only_sources:
        requests = [
            item for item in requests if item[0].casefold() in only_sources
        ]
    if max_requests is not None:
        requests = requests[:max_requests]
    results: list[CollectionResult] = []
    workers = int(settings()["parallel_workers"])
    logger.info("Starting run %s with %s collection requests", run_id, len(requests))
    batch_size = int(settings().get("collection", {}).get("request_batch_size", 100))
    for start in range(0, len(requests), batch_size):
        batch = requests[start : start + batch_size]
        logger.info(
            "Collecting request batch %s-%s of %s",
            start + 1,
            min(start + batch_size, len(requests)),
            len(requests),
        )
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(connector_for(source).collect, request): (source, request)
                for source, request in batch
            }
            for future in as_completed(futures):
                source, request = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    logger.exception(
                        "Unhandled connector failure for %s/%s",
                        source,
                        request.search_id,
                    )
                    results.append(
                        CollectionResult(
                            source=source,
                            request=request,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )

    collected = 0
    new_jobs: list[int] = []
    errors = 0
    watchlist_names = [name.casefold() for name in watchlist()]

    with session_scope() as session:
        for result in results:
            source_run = SourceRun(
                run_id=run_id,
                source=result.source,
                search_id=result.request.search_id,
                query=result.request.term,
                location=result.request.location,
                status="failed" if result.error else "success",
                result_count=len(result.jobs),
                description_count=sum(
                    len(str(job.get("description") or "")) >= 100 for job in result.jobs
                ),
                duration_seconds=result.duration_seconds,
                error=result.error,
            )
            session.add(source_run)
            session.flush()
            if result.error:
                errors += 1
                continue

            source_new = 0
            for payload in result.jobs:
                safe_payload = json_safe(payload)
                collected += 1
                normalized = normalize_job(safe_payload)
                if not normalized["source"]:
                    normalized["source"] = result.source
                canonical_id = canonical_job_id(
                    normalized["source"],
                    normalized["source_job_id"],
                    normalized["source_url"],
                    normalized["title"],
                    normalized["company"],
                    normalized["location_text"],
                )
                content_hash = payload_hash(safe_payload)
                job = session.scalar(select(Job).where(Job.canonical_id == canonical_id))
                if job is None:
                    job = Job(
                        canonical_id=canonical_id,
                        **normalized,
                        first_seen_at=datetime.utcnow(),
                        last_seen_at=datetime.utcnow(),
                        last_changed_at=datetime.utcnow(),
                        is_watchlist_company=any(
                            name in normalized["company"].casefold()
                            for name in watchlist_names
                        ),
                        raw_metadata={"families": [result.request.family]},
                    )
                    session.add(job)
                    session.flush()
                    new_jobs.append(job.id)
                    source_new += 1
                else:
                    previous_hash = session.scalar(
                        select(JobObservation.content_hash)
                        .where(JobObservation.job_id == job.id)
                        .order_by(desc(JobObservation.observed_at))
                        .limit(1)
                    )
                    job.last_seen_at = datetime.utcnow()
                    if len(normalized.get("description") or "") > len(job.description or ""):
                        job.description = normalized["description"]
                    if previous_hash and previous_hash != content_hash:
                        job.last_changed_at = datetime.utcnow()

                session.add(
                    RawJob(
                        run_id=run_id,
                        source_run_id=source_run.id,
                        source=normalized["source"],
                        source_job_id=normalized["source_job_id"],
                        source_url=normalized["source_url"],
                        search_id=result.request.search_id,
                        payload=safe_payload,
                        payload_hash=content_hash,
                    )
                )
                session.add(
                    JobObservation(
                        job_id=job.id,
                        run_id=run_id,
                        source=normalized["source"],
                        search_id=result.request.search_id,
                        content_hash=content_hash,
                        changed=False,
                    )
                )
            source_run.new_count = source_new

    evaluated = 0
    ai_evaluated = 0
    shortlisted: list[dict] = []
    if new_jobs:
        evaluator = JobEvaluator()
        ai_config = settings()["ai"]
        ai_limit = 0 if dry_run else int(ai_config["max_evaluations_per_run"])
        minimum_prefilter = int(ai_config["minimum_prefilter_score"])
        threshold = int(settings()["notifications"]["minimum_priority_score"])
        with session_scope() as session:
            preliminary = []
            for job_id in new_jobs:
                job = session.get(Job, job_id)
                preliminary.append((job, evaluator.keyword_fallback(job)))

            ranked_candidates = [
                job.id
                for job, result in sorted(
                    preliminary,
                    key=lambda item: item[1].priority_score,
                    reverse=True,
                )
                if result.priority_score >= minimum_prefilter
                and len(job.description or "") >= 100
            ]
            ai_candidates = set(ranked_candidates[:ai_limit])

            for job, fallback_result in preliminary:
                if not dry_run and evaluator.enabled and job.id in ai_candidates:
                    result = evaluator.evaluate(job)
                    ai_evaluated += 1
                else:
                    result = fallback_result
                session.add(Evaluation(job_id=job.id, **result.__dict__))
                evaluated += 1
                if (
                    not dry_run
                    and
                    result.priority_score >= threshold
                    and result.application_feasibility >= 55
                    and result.recommendation != "discard"
                ):
                    shortlisted.append(
                        {
                            "job_id": job.id,
                            "title": job.title,
                            "company": job.company,
                            "source_url": job.source_url or "#",
                            "priority_score": result.priority_score,
                            "application_feasibility": result.application_feasibility,
                        }
                    )

    notified = 0
    notification_error = None
    if not dry_run and notify and shortlisted:
        maximum = int(settings()["notifications"]["maximum_items"])
        shortlisted = sorted(
            shortlisted, key=lambda item: item["priority_score"], reverse=True
        )[:maximum]
        notifier = TelegramNotifier()
        ok, notification_error = notifier.send(shortlisted)
        with session_scope() as session:
            for item in shortlisted:
                notification = Notification(
                    job_id=item["job_id"],
                    run_id=run_id,
                    attempted_at=datetime.utcnow(),
                    status="sent" if ok else "failed",
                    sent_at=datetime.utcnow() if ok else None,
                    error=notification_error,
                )
                session.add(notification)
        notified = len(shortlisted) if ok else 0

    duration = time.perf_counter() - started
    with session_scope() as session:
        run = session.get(Run, run_id)
        run.status = "partial" if errors else "success"
        run.finished_at = datetime.utcnow()
        run.collected_count = collected
        run.new_count = len(new_jobs)
        run.evaluated_count = evaluated
        run.shortlisted_count = len(shortlisted)
        run.notified_count = notified
        run.error_count = errors
        run.duration_seconds = duration
        run.notes = "; ".join(
            note
            for note in (
                f"ai_evaluations={ai_evaluated}" if not dry_run else None,
                notification_error,
            )
            if note
        ) or None

    return {
        "run_id": run_id,
        "status": "partial" if errors else "success",
        "collected": collected,
        "new_jobs": len(new_jobs),
        "evaluated": evaluated,
        "ai_evaluated": ai_evaluated,
        "shortlisted": len(shortlisted),
        "notified": notified,
        "errors": errors,
        "duration_seconds": round(duration, 1),
    }
