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

    assert result.confidence >= 65
    assert result.priority_score >= 55


def test_keyword_fallback_does_not_treat_all_remote_jobs_as_globally_feasible():
    evaluator = JobEvaluator.__new__(JobEvaluator)
    evaluator.model = "test"
    evaluator.prompt_version = "test"

    def evaluate(location, description):
        return evaluator.keyword_fallback(
            SimpleNamespace(
                title="Industrial Data Analyst",
                company="Example",
                location_text=location,
                description=description,
                country="Remote",
                work_mode="remote",
            )
        )

    latam = evaluate("Remote", "Remote role open to candidates across LATAM.")
    unknown = evaluate("Remote", "Work with an international analytics team.")
    restricted = evaluate("Your Remote US Home Office", "US home office role.")

    assert latam.application_feasibility == 95
    assert unknown.application_feasibility == 35
    assert restricted.application_feasibility == 0
    assert latam.priority_score > unknown.priority_score > restricted.priority_score


def test_traditional_process_role_requires_a_digital_component():
    evaluator = JobEvaluator.__new__(JobEvaluator)
    evaluator.model = "test"
    evaluator.prompt_version = "test"

    def evaluate(description):
        return evaluator.keyword_fallback(
            SimpleNamespace(
                title="Process Engineer",
                company="Example",
                location_text="Argentina",
                description=description,
                country="Argentina",
                work_mode="onsite",
            )
        )

    conventional = evaluate(
        "Monitor production, maintain procedures and coordinate daily plant routines."
    )
    digital = evaluate(
        "Optimize an industrial process using Python, SQL, advanced analytics, "
        "machine learning and automation with operations stakeholders."
    )

    assert conventional.recommendation == "discard"
    assert digital.priority_score > conventional.priority_score
    assert digital.recommendation != "discard"
