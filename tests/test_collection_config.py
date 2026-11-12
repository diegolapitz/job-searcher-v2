from collections import Counter

from app.pipeline import build_collection_requests, connector_for


def test_exhaustive_collection_plan_contains_all_enabled_sources():
    requests = build_collection_requests()
    counts = Counter(source for source, _ in requests)

    assert 350 <= len(requests) <= 500
    assert counts["linkedin"] == 163
    assert counts["indeed"] == 163
    assert counts["computrabajo"] == 12
    assert counts["greenhouse"] >= 6
    assert counts["hiringroom"] >= 10
    assert counts["rigzone"] == 60
    assert counts["remoteok"] == 1
    assert counts["arbeitnow"] == 1

    planned = [request for _, request in requests if request.search_id == "industrial_digitalization"]
    assert planned
    assert all(
        request.options["strategy_version"] == "v3.0-industrial-digital-agency"
        for request in planned
    )
    assert all(request.options["negative_terms"] for request in planned)


def test_every_planned_source_has_a_connector():
    sources = {source for source, _ in build_collection_requests()}
    for source in sources:
        assert connector_for(source) is not None
