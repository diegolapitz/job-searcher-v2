from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import and_, case, desc, func, or_, select

from app.db import init_db, session_scope
from app.models import Application, Evaluation, Job, JobObservation, Run, SourceRun

app = FastAPI(title="Job Searcher V2 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApplicationUpdate(BaseModel):
    status: str
    rating: int | None = None
    notes: str | None = None


@app.on_event("startup")
def startup() -> None:
    init_db()


def latest_evaluation_subquery():
    return (
        select(Evaluation.job_id, func.max(Evaluation.id).label("evaluation_id"))
        .group_by(Evaluation.job_id)
        .subquery()
    )


def scope_condition(scope: str):
    remote = or_(Job.work_mode == "remote", Job.country == "Remote")
    if scope == "argentina":
        return Job.country == "Argentina"
    if scope == "argentina_remote":
        remote_latam_jobs = select(JobObservation.job_id).where(
            JobObservation.search_id == "remote_latam"
        )
        remote_signal = func.lower(
            func.coalesce(Job.title, "") + " " + func.coalesce(Job.location_text, "")
        )
        return and_(
            Job.id.in_(remote_latam_jobs),
            or_(
                remote,
                remote_signal.contains("remote"),
                remote_signal.contains("remoto"),
                remote_signal.contains("desde casa"),
            ),
        )
    if scope == "remote":
        return remote
    if scope == "usa":
        return Job.country == "United States"
    if scope == "europe":
        return Job.country.in_(
            [
                "United Kingdom",
                "Germany",
                "Spain",
                "France",
                "Netherlands",
                "Ireland",
                "Italy",
                "Portugal",
            ]
        )
    if scope == "latam":
        return Job.country.in_(
            ["Argentina", "Brazil", "Chile", "Colombia", "Mexico", "Remote"]
        )
    return None


@app.get("/api/health")
def health():
    with session_scope() as session:
        latest_run = session.scalar(select(Run).order_by(desc(Run.started_at)).limit(1))
        return {
            "status": "ok",
            "database": "connected",
            "latest_run": _run_dict(latest_run) if latest_run else None,
        }


@app.get("/api/overview")
def overview():
    latest = latest_evaluation_subquery()
    with session_scope() as session:
        total = session.scalar(select(func.count(Job.id))) or 0
        active = session.scalar(select(func.count(Job.id)).where(Job.is_active)) or 0
        high_priority = (
            session.scalar(
                select(func.count(Evaluation.id))
                .join(latest, Evaluation.id == latest.c.evaluation_id)
                .where(
                    Evaluation.priority_score >= 72,
                    Evaluation.application_feasibility >= 55,
                )
            )
            or 0
        )
        argentina = (
            session.scalar(select(func.count(Job.id)).where(Job.country == "Argentina"))
            or 0
        )
        last_30 = datetime.utcnow() - timedelta(days=30)
        recent = (
            session.scalar(select(func.count(Job.id)).where(Job.first_seen_at >= last_30))
            or 0
        )
        return {
            "total_jobs": total,
            "active_jobs": active,
            "high_priority": high_priority,
            "argentina_jobs": argentina,
            "new_last_30_days": recent,
        }


@app.get("/api/jobs")
def jobs(
    q: str = "",
    scope: str | None = None,
    country: str | None = None,
    work_mode: str | None = None,
    source: str | None = None,
    status: str | None = None,
    minimum_priority: int = Query(0, ge=0, le=100),
    minimum_feasibility: int = Query(0, ge=0, le=100),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    latest = latest_evaluation_subquery()
    with session_scope() as session:
        statement = (
            select(Job, Evaluation, Application)
            .outerjoin(latest, Job.id == latest.c.job_id)
            .outerjoin(Evaluation, Evaluation.id == latest.c.evaluation_id)
            .outerjoin(Application, Application.job_id == Job.id)
        )
        if q:
            pattern = f"%{q}%"
            statement = statement.where(
                or_(
                    Job.title.ilike(pattern),
                    Job.company.ilike(pattern),
                    Job.description.ilike(pattern),
                )
            )
        if scope:
            condition = scope_condition(scope)
            if condition is not None:
                statement = statement.where(condition)
        if country:
            statement = statement.where(Job.country == country)
        if work_mode:
            if work_mode == "remote":
                statement = statement.where(
                    or_(Job.work_mode == "remote", Job.country == "Remote")
                )
            else:
                statement = statement.where(Job.work_mode == work_mode)
        if source:
            statement = statement.where(Job.source == source)
        if status:
            statement = statement.where(Application.status == status)
        if minimum_priority:
            statement = statement.where(Evaluation.priority_score >= minimum_priority)
        if minimum_feasibility:
            statement = statement.where(
                Evaluation.application_feasibility >= minimum_feasibility
            )
        statement = (
            statement.order_by(
                desc(func.coalesce(Evaluation.priority_score, 0)),
                desc(Job.first_seen_at),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = session.execute(statement).all()
        return [_job_dict(job, evaluation, application) for job, evaluation, application in rows]


@app.get("/api/filter-options")
def filter_options():
    with session_scope() as session:
        countries = session.execute(
            select(Job.country, func.count(Job.id).label("count"))
            .where(Job.country.is_not(None))
            .group_by(Job.country)
            .order_by(desc("count"))
        ).all()
        modes = session.execute(
            select(Job.work_mode, func.count(Job.id).label("count"))
            .where(Job.work_mode.is_not(None))
            .group_by(Job.work_mode)
            .order_by(desc("count"))
        ).all()
        scopes = []
        for value, label in [
            ("argentina", "Argentina"),
            ("argentina_remote", "Remoto desde AR"),
            ("remote", "Remoto"),
            ("usa", "EE.UU."),
            ("europe", "Europa"),
            ("latam", "LATAM"),
        ]:
            condition = scope_condition(value)
            count = session.scalar(select(func.count(Job.id)).where(condition)) or 0
            scopes.append({"value": value, "label": label, "count": count})
        return {
            "scopes": scopes,
            "countries": [
                {"value": row.country, "label": row.country, "count": row.count}
                for row in countries
            ],
            "work_modes": [
                {"value": row.work_mode, "label": row.work_mode, "count": row.count}
                for row in modes
            ],
        }


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: int):
    with session_scope() as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        evaluation = session.scalar(
            select(Evaluation)
            .where(Evaluation.job_id == job.id)
            .order_by(desc(Evaluation.created_at))
            .limit(1)
        )
        application = session.scalar(
            select(Application).where(Application.job_id == job.id)
        )
        return _job_dict(job, evaluation, application, include_description=True)


@app.put("/api/jobs/{job_id}/application")
def update_application(job_id: int, payload: ApplicationUpdate):
    allowed = {"unreviewed", "saved", "applied", "interview", "rejected", "discarded"}
    if payload.status not in allowed:
        raise HTTPException(400, "Invalid application status")
    with session_scope() as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        application = session.scalar(
            select(Application).where(Application.job_id == job.id)
        )
        if not application:
            application = Application(job_id=job.id)
            session.add(application)
        application.status = payload.status
        application.rating = payload.rating
        application.notes = payload.notes
        application.updated_at = datetime.utcnow()
        if payload.status == "applied" and not application.applied_at:
            application.applied_at = datetime.utcnow()
        session.flush()
        return {"ok": True, "application": _application_dict(application)}


@app.get("/api/market/trends")
def market_trends(days: int = Query(180, ge=30, le=730)):
    since = datetime.utcnow() - timedelta(days=days)
    with session_scope() as session:
        rows = session.execute(
            select(
                func.strftime("%Y-%m", Job.first_seen_at).label("period"),
                func.count(Job.id).label("jobs"),
                func.sum(case((Job.country == "Argentina", 1), else_=0)).label(
                    "argentina"
                ),
                func.sum(case((Job.work_mode == "remote", 1), else_=0)).label("remote"),
            )
            .where(Job.first_seen_at >= since)
            .group_by("period")
            .order_by("period")
        ).all()
        return [
            {
                "period": row.period,
                "jobs": row.jobs,
                "argentina": row.argentina or 0,
                "remote": row.remote or 0,
            }
            for row in rows
        ]


@app.get("/api/market/skills")
def market_skills(limit: int = Query(20, ge=1, le=50)):
    latest = latest_evaluation_subquery()
    counts: dict[str, int] = {}
    with session_scope() as session:
        rows = session.scalars(
            select(Evaluation)
            .join(latest, Evaluation.id == latest.c.evaluation_id)
            .where(Evaluation.skills.is_not(None))
        )
        for evaluation in rows:
            for skill in evaluation.skills or []:
                normalized = str(skill).strip()
                if normalized:
                    counts[normalized] = counts.get(normalized, 0) + 1
    return [
        {"skill": skill, "count": count}
        for skill, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[
            :limit
        ]
    ]


@app.get("/api/system/runs")
def system_runs(limit: int = Query(20, ge=1, le=100)):
    with session_scope() as session:
        runs = session.scalars(select(Run).order_by(desc(Run.started_at)).limit(limit))
        return [_run_dict(run) for run in runs]


@app.get("/api/system/sources")
def source_health():
    with session_scope() as session:
        rows = session.execute(
            select(
                SourceRun.source,
                func.count(SourceRun.id).label("requests"),
                func.sum(SourceRun.result_count).label("results"),
                func.sum(SourceRun.new_count).label("new_jobs"),
                func.sum(SourceRun.description_count).label("descriptions"),
                func.sum(case((SourceRun.status == "failed", 1), else_=0)).label(
                    "failures"
                ),
                func.avg(SourceRun.duration_seconds).label("average_seconds"),
            ).group_by(SourceRun.source)
        ).all()
        return [
            {
                "source": row.source,
                "requests": row.requests,
                "results": row.results or 0,
                "new_jobs": row.new_jobs or 0,
                "descriptions": row.descriptions or 0,
                "failures": row.failures or 0,
                "average_seconds": round(row.average_seconds or 0, 1),
            }
            for row in rows
        ]


def _job_dict(job, evaluation, application, include_description=False):
    payload = {
        "id": job.id,
        "canonical_id": job.canonical_id,
        "title": job.title,
        "company": job.company,
        "location": job.location_text,
        "country": job.country,
        "work_mode": job.work_mode,
        "source": job.source,
        "source_url": job.source_url,
        "date_posted": job.date_posted.isoformat() if job.date_posted else None,
        "first_seen_at": job.first_seen_at.isoformat(),
        "last_seen_at": job.last_seen_at.isoformat(),
        "is_active": job.is_active,
        "is_watchlist_company": job.is_watchlist_company,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "evaluation": _evaluation_dict(evaluation) if evaluation else None,
        "application": _application_dict(application) if application else None,
    }
    if include_description:
        payload["description"] = job.description
    return payload


def _evaluation_dict(evaluation):
    return {
        "priority_score": evaluation.priority_score,
        "profile_match": evaluation.profile_match,
        "technical_match": evaluation.technical_match,
        "industry_match": evaluation.industry_match,
        "career_value": evaluation.career_value,
        "application_feasibility": evaluation.application_feasibility,
        "seniority_match": evaluation.seniority_match,
        "confidence": evaluation.confidence,
        "recommendation": evaluation.recommendation,
        "reason": evaluation.reason,
        "evidence_for": evaluation.evidence_for or [],
        "evidence_against": evaluation.evidence_against or [],
        "skills": evaluation.skills or [],
        "years_experience": evaluation.years_experience,
        "english_level": evaluation.english_level,
        "seniority": evaluation.seniority,
        "industry": evaluation.industry,
        "function_family": evaluation.function_family,
        "visa_sponsorship": evaluation.visa_sponsorship,
        "relocation": evaluation.relocation,
        "method": evaluation.method,
        "prompt_version": evaluation.prompt_version,
    }


def _application_dict(application):
    return {
        "status": application.status,
        "rating": application.rating,
        "notes": application.notes,
        "applied_at": application.applied_at.isoformat()
        if application.applied_at
        else None,
        "updated_at": application.updated_at.isoformat(),
    }


def _run_dict(run):
    return {
        "id": run.id,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status,
        "mode": run.mode,
        "collected_count": run.collected_count,
        "new_count": run.new_count,
        "evaluated_count": run.evaluated_count,
        "shortlisted_count": run.shortlisted_count,
        "notified_count": run.notified_count,
        "error_count": run.error_count,
        "duration_seconds": run.duration_seconds,
    }
