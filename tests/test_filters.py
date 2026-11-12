from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api import _deduplicate_job_rows, scope_condition
from app.db import Base
from app.models import Evaluation, Job


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
    session.add_all(
        [
            Evaluation(
                job_id=job.id,
                model="test",
                prompt_version="test",
                method="test",
                application_feasibility=feasibility,
                recommendation="review",
                reason="test",
            )
            for job, feasibility in zip(jobs, [100, 0, 0, 0], strict=True)
        ]
    )
    session.commit()
    return session


def count_scope(session: Session, scope: str) -> int:
    return session.scalar(select(func.count(Job.id)).where(scope_condition(scope))) or 0


def test_quick_scopes_return_matching_jobs():
    with seeded_session() as session:
        for scope in ("argentina", "remote", "usa", "europe", "latam"):
            assert count_scope(session, scope) > 0


def test_argentina_remote_uses_latest_feasibility_not_search_provenance():
    with seeded_session() as session:
        assert count_scope(session, "argentina_remote") == 1


def test_job_list_hides_exact_cross_source_duplicates():
    linkedin = Job(
        id=1,
        canonical_id="linkedin-copy",
        title="Ingeniero de Procesos",
        company="Mercado Libre",
        location_text="General Guemes, Salta, Argentina",
        source="linkedin",
    )
    indeed = Job(
        id=2,
        canonical_id="indeed-copy",
        title="Ingeniero de Procesos",
        company="Mercado Livre",
        location_text="General Guemes, N, AR",
        source="indeed",
    )

    rows = _deduplicate_job_rows(
        [(linkedin, None, None), (indeed, None, None)]
    )

    assert len(rows) == 1
    assert rows[0][0].source == "linkedin"
