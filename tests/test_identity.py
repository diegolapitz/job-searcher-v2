from app.services.identity import canonical_job_id, normalize_text, normalize_url


def test_normalize_empty_values():
    assert normalize_text(None) == ""
    assert normalize_text(float("nan")) == ""
    assert normalize_text(" N/A ") == ""


def test_normalize_title_variants():
    assert normalize_text("Senior Data Analyst") == normalize_text("Sr. Data Analyst")


def test_url_removes_tracking_parameters():
    assert (
        normalize_url("https://example.com/job/1/?utm_source=x&ref=keep#section")
        == "https://example.com/job/1?ref=keep"
    )


def test_source_id_is_stable_despite_missing_location():
    first = canonical_job_id(
        "linkedin", "li-123", "https://linkedin.com/jobs/123", "Role", "Company", None
    )
    second = canonical_job_id(
        "linkedin", "li-123", "https://linkedin.com/jobs/123", "Role", "Company", ""
    )
    assert first == second


def test_fallback_identity_normalizes_null_location():
    first = canonical_job_id("", None, None, "Process Engineer", "ACME", None)
    second = canonical_job_id("", "", "", "Process Engineer", "ACME", "nan")
    assert first == second
