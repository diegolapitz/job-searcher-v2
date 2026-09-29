from types import SimpleNamespace

from app.services.evaluator import JobEvaluator, calculate_priority


def test_priority_rewards_feasibility():
    base = {
        "profile_match": 85,
        "technical_match": 80,
        "industry_match": 90,
        "career_value": 80,
        "seniority_match": 70,
        "confidence": 90,
    }
    feasible = calculate_priority({**base, "application_feasibility": 90})
    infeasible = calculate_priority({**base, "application_feasibility": 5})
    assert feasible > infeasible
    assert feasible - infeasible >= 20


def test_low_confidence_reduces_priority():
    data = {
        "profile_match": 90,
        "technical_match": 90,
        "industry_match": 90,
        "career_value": 90,
        "application_feasibility": 90,
        "seniority_match": 90,
    }
    assert calculate_priority({**data, "confidence": 90}) > calculate_priority(
        {**data, "confidence": 40}
    )


def test_keyword_fallback_can_surface_strong_jobs():
    evaluator = JobEvaluator.__new__(JobEvaluator)
    evaluator.model = "test"
    evaluator.prompt_version = "test"
    job = SimpleNamespace(
        title="Industrial Process Data Analyst",
        company="Example",
        location_text="Buenos Aires, Argentina",
        description=(
            "Manufacturing plant process optimization with Python, SQL, "
            "Power BI, statistics, analytics and predictive maintenance."
        ),
        country="Argentina",
        work_mode="onsite",
    )

    result = evaluator.keyword_fallback(job)

    assert result.confidence == 75
    assert result.priority_score >= 55
