from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api import scope_condition
from app.db import Base
from app.models import Job, JobObservation


def seeded_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    jobs = [
        Job(canonical_id="arg", title="Process Engineer", company="Example", source="test", country="Argentina", work_mode="remote"),
        Job(canonical_id="usa", title="Data Analyst", company="Example", source="test", country="United States", work_mode="onsite"),
        Job(canonical_id="eur", title="Engineer", company="Example", source="test", country="Germany", work_mode="onsite"),
        Job(canonical_id="latam", title="Analyst", company="Example", source="test", country="Brazil", work_mode="onsite"),
    ]
    session.add_all(jobs)
    session.flush()
    session.add_all([
        JobObservation(job_id=jobs[0].id, source="test", search_id="remote_latam", content_hash="a"),
        JobObservation(job_id=jobs[1].id, source="test", search_id="remote_latam", content_hash="b"),
    ])
    session.commit()
    return session


def count_scope(session: Session, scope: str) -> int:
    return session.scalar(select(func.count(Job.id)).where(scope_condition(scope))) or 0


def test_quick_scopes_return_matching_jobs():
    with seeded_session() as session:
        for scope in ("argentina", "remote", "usa", "europe", "latam"):
            assert count_scope(session, scope) > 0


def test_argentina_remote_uses_remote_latam_search_provenance():
    with seeded_session() as session:
        assert count_scope(session, "argentina_remote") == 1
        remote_latam = session.scalar(
            select(func.count(func.distinct(JobObservation.job_id))).where(
                JobObservation.search_id == "remote_latam"
            )
        )
        assert remote_latam == 2
