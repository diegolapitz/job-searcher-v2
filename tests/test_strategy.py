from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import strategy
from app.db import Base
from app.models import Evaluation, Job, Run
from app.scheduler import run_scheduler
from app.services import reevaluate as reevaluate_module


def test_strategy_is_versioned_and_owns_operational_thresholds():
    active = strategy()

    assert active["version"]
    assert active["status"] in {"active", "needs_review"}
    assert active["version"] == "v3.0-industrial-digital-agency"
    assert active["thresholds"]["today_priority"] == 72
    assert active["thresholds"]["today_feasibility"] == 60
    assert active["thresholds"]["maximum_daily_review"] == 12
    assert active["thresholds"]["notification_priority"] >= 0


def test_reevaluation_only_writes_once_for_current_strategy(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def isolated_session_scope():
        session = test_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(reevaluate_module, "session_scope", isolated_session_scope)
    with isolated_session_scope() as session:
        session.add(
            Job(
                canonical_id="strategy-test-job",
                title="Industrial Process Data Analyst",
                company="Example",
                location_text="Buenos Aires, Argentina",
                country="Argentina",
                work_mode="onsite",
                source="test",
                description="Manufacturing process analytics with Python and SQL.",
            )
        )

    first = reevaluate_module.reevaluate_jobs(use_ai=False)
    second = reevaluate_module.reevaluate_jobs(use_ai=False)

    assert first["eligible_jobs"] == 1
    assert first["evaluated_jobs"] == 1
    assert second["eligible_jobs"] == 0
    with isolated_session_scope() as session:
        assert session.scalar(select(func.count(Evaluation.id))) == 1
        assert session.scalar(select(func.count(Run.id))) == 1


def test_scheduler_can_execute_one_bounded_cycle(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.scheduler.run_pipeline",
        lambda **kwargs: calls.append(kwargs) or {"status": "success"},
    )

    run_scheduler(
        interval_hours=1,
        notify=False,
        only_sources={"remoteok"},
        max_requests=1,
        max_cycles=1,
    )

    assert calls == [
        {
            "notify": False,
            "only_sources": {"remoteok"},
            "max_requests": 1,
        }
    ]


def test_scheduler_rejects_non_positive_interval():
    with pytest.raises(ValueError, match="greater than zero"):
        run_scheduler(interval_hours=0, max_cycles=1)
