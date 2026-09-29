from collections import Counter

from app.pipeline import build_collection_requests, connector_for


def test_exhaustive_collection_plan_contains_all_enabled_sources():
    requests = build_collection_requests()
    counts = Counter(source for source, _ in requests)

    assert len(requests) > 1800
    assert counts["linkedin"] > 700
    assert counts["indeed"] > 700
    assert counts["computrabajo"] > 200
    assert counts["greenhouse"] >= 6
    assert counts["hiringroom"] >= 10
    assert counts["rigzone"] == 60
    assert counts["remoteok"] == 1
    assert counts["arbeitnow"] == 1


def test_every_planned_source_has_a_connector():
    sources = {source for source, _ in build_collection_requests()}
    for source in sources:
        assert connector_for(source) is not None
