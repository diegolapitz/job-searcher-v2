from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.config import settings, watchlist
from app.db import session_scope
from app.models import Evaluation, Job, JobObservation, RawJob, Run
from app.services.identity import canonical_job_id, payload_hash
from app.services.normalize import normalize_job, parse_date


def migrate_v1(csv_path: str | Path) -> dict[str, int]:
    source_path = Path(csv_path).resolve()
    frame = pd.read_csv(source_path, low_memory=False)
    counters = {"rows": len(frame), "jobs_created": 0, "jobs_updated": 0, "evaluations": 0}
    watchlist_names = [name.casefold() for name in watchlist()]

    with session_scope() as session:
        run = Run(
            status="running",
            mode="migration",
            started_at=datetime.utcnow(),
            notes=f"Migrated from {source_path}",
        )
        session.add(run)
        session.flush()

        for _, row in frame.iterrows():
            payload = {
                key: (None if pd.isna(value) else value)
                for key, value in row.to_dict().items()
            }
            normalized = normalize_job(payload)
            canonical_id = canonical_job_id(
                normalized["source"],
                normalized["source_job_id"],
                normalized["source_url"],
                normalized["title"],
                normalized["company"],
                normalized["location_text"],
            )
            job = session.scalar(select(Job).where(Job.canonical_id == canonical_id))
            found_at = parse_date(payload.get("_found_date")) or datetime.utcnow()
            if job is None:
                job = Job(
                    canonical_id=canonical_id,
                    **normalized,
                    first_seen_at=found_at,
                    last_seen_at=found_at,
                    last_changed_at=found_at,
                    is_watchlist_company=any(
                        name in normalized["company"].casefold() for name in watchlist_names
                    ),
                    raw_metadata={"v1_category": payload.get("_category")},
                )
                session.add(job)
                session.flush()
                counters["jobs_created"] += 1
            else:
                job.last_seen_at = max(job.last_seen_at, found_at)
                if len(normalized.get("description") or "") > len(job.description or ""):
                    job.description = normalized["description"]
                counters["jobs_updated"] += 1

            raw = RawJob(
                run_id=run.id,
                source=normalized["source"] or "v1",
                source_job_id=normalized["source_job_id"],
                source_url=normalized["source_url"],
                search_id="v1_import",
                captured_at=found_at,
                payload=payload,
                payload_hash=payload_hash(payload),
            )
            session.add(raw)
            session.add(
                JobObservation(
                    job_id=job.id,
                    run_id=run.id,
                    source=normalized["source"] or "v1",
                    search_id="v1_import",
                    observed_at=found_at,
                    content_hash=payload_hash(payload),
                    changed=False,
                )
            )

            if payload.get("ai_score") is not None:
                score = int(float(payload.get("ai_score") or 0))
                country_feasibility = (
                    90
                    if normalized["country"] == "Argentina"
                    else 75
                    if normalized["work_mode"] == "remote"
                    else 30
                )
                skills = [
                    item.strip()
                    for item in str(payload.get("ai_skills") or "").split(",")
                    if item.strip() and item.strip().casefold() != "nan"
                ]
                session.add(
                    Evaluation(
                        job_id=job.id,
                        created_at=found_at,
                        model="claude-haiku-v1-import",
                        prompt_version="v1-import",
                        method=(
                            "keyword_fallback"
                            if "filtro keyword" in str(payload.get("ai_reason")).casefold()
                            else "ai"
                        ),
                        profile_match=score,
                        technical_match=score,
                        industry_match=score,
                        career_value=score,
                        application_feasibility=country_feasibility,
                        seniority_match=60,
                        confidence=55,
                        priority_score=round(score * 0.68 + country_feasibility * 0.32),
                        recommendation="apply" if score >= 85 else "review" if score >= 55 else "discard",
                        reason=str(payload.get("ai_reason") or ""),
                        evidence_for=[],
                        evidence_against=["Imported evaluation; dimensions were estimated."],
                        skills=skills,
                        years_experience=str(payload.get("ai_years_exp") or "unknown"),
                        english_level=str(payload.get("ai_english") or "unknown"),
                        seniority=str(payload.get("job_level") or "unknown"),
                        industry=str(payload.get("_category") or "unknown"),
                        function_family="unknown",
                        visa_sponsorship=_truthy(payload.get("ai_visa_sponsorship")),
                        relocation=False,
                        raw_response={"v1_import": True, "legacy_score": score},
                    )
                )
                counters["evaluations"] += 1

        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.collected_count = len(frame)
        run.new_count = counters["jobs_created"]
        run.evaluated_count = counters["evaluations"]
    _write_receipt(source_path, counters)
    return counters


def _truthy(value) -> bool:
    return str(value).casefold() in {"true", "1", "yes", "si", "sí"}


def _write_receipt(source_path: Path, counters: dict[str, int]) -> None:
    receipt = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": str(source_path),
        "settings": settings(),
        "result": counters,
    }
    output = Path(__file__).resolve().parents[1] / "docs" / "migration-v1-receipt.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
