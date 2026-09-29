from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(24), default="running")
    mode: Mapped[str] = mapped_column(String(24), default="live")
    collected_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_count: Mapped[int] = mapped_column(Integer, default=0)
    shortlisted_count: Mapped[int] = mapped_column(Integer, default=0)
    notified_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)


class SourceRun(Base):
    __tablename__ = "source_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(50), index=True)
    search_id: Mapped[str | None] = mapped_column(String(100), index=True)
    query: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(24), default="success")
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    description_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)


class RawJob(Base):
    __tablename__ = "raw_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"))
    source_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_runs.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(String(50), index=True)
    source_job_id: Mapped[str | None] = mapped_column(String(200), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    search_id: Mapped[str | None] = mapped_column(String(100), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)

    __table_args__ = (
        Index("ix_raw_job_identity", "source", "source_job_id", "captured_at"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    company: Mapped[str] = mapped_column(String(300), index=True)
    location_text: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(150), index=True)
    region: Mapped[str | None] = mapped_column(String(150))
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    work_mode: Mapped[str | None] = mapped_column(String(30), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), index=True)
    source_job_id: Mapped[str | None] = mapped_column(String(200), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    direct_url: Mapped[str | None] = mapped_column(Text)
    date_posted: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_watchlist_company: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(20))
    salary_interval: Mapped[str | None] = mapped_column(String(30))
    salary_usd_year_min: Mapped[float | None] = mapped_column(Float)
    salary_usd_year_max: Mapped[float | None] = mapped_column(Float)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON)

    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    application: Mapped["Application | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        Index("ix_jobs_company_title", "company", "title"),
        Index("ix_jobs_market_time", "first_seen_at", "country", "source"),
    )


class JobObservation(Base):
    __tablename__ = "job_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(50), index=True)
    search_id: Mapped[str | None] = mapped_column(String(100), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    changed: Mapped[bool] = mapped_column(Boolean, default=False)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(50), index=True)
    method: Mapped[str] = mapped_column(String(30), default="ai")
    profile_match: Mapped[int] = mapped_column(Integer, default=0)
    technical_match: Mapped[int] = mapped_column(Integer, default=0)
    industry_match: Mapped[int] = mapped_column(Integer, default=0)
    career_value: Mapped[int] = mapped_column(Integer, default=0)
    application_feasibility: Mapped[int] = mapped_column(Integer, default=0)
    seniority_match: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    priority_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    recommendation: Mapped[str] = mapped_column(String(30), index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_for: Mapped[list | None] = mapped_column(JSON)
    evidence_against: Mapped[list | None] = mapped_column(JSON)
    skills: Mapped[list | None] = mapped_column(JSON)
    years_experience: Mapped[str | None] = mapped_column(String(50))
    english_level: Mapped[str | None] = mapped_column(String(50))
    seniority: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(100), index=True)
    function_family: Mapped[str | None] = mapped_column(String(100), index=True)
    visa_sponsorship: Mapped[bool] = mapped_column(Boolean, default=False)
    relocation: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_response: Mapped[dict | None] = mapped_column(JSON)

    job: Mapped[Job] = relationship(back_populates="evaluations")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="unreviewed", index=True)
    rating: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    job: Mapped[Job] = relationship(back_populates="application")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"))
    channel: Mapped[str] = mapped_column(String(30), default="telegram")
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("job_id", "channel", name="uq_job_notification_channel"),
    )
