from app.connectors.catalog_ats import CatalogATSConnector


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_greenhouse_normalizes_board_payload(monkeypatch):
    monkeypatch.setattr(
        "app.connectors.catalog_ats.requests.get",
        lambda *args, **kwargs: FakeResponse(
            {
                "jobs": [
                    {
                        "id": 42,
                        "title": "Process Engineer",
                        "location": {"name": "Buenos Aires, Argentina"},
                        "content": "<p>Improve industrial processes.</p>",
                        "absolute_url": "https://example.test/jobs/42",
                        "updated_at": "2026-06-15T00:00:00Z",
                        "departments": [{"name": "Manufacturing"}],
                        "offices": [],
                    }
                ]
            }
        ),
    )

    jobs = CatalogATSConnector("greenhouse")._greenhouse("example", "Example")

    assert jobs[0]["id"] == 42
    assert jobs[0]["company"] == "Example"
    assert jobs[0]["description"] == "Improve industrial processes."


def test_ashby_preserves_remote_and_compensation(monkeypatch):
    monkeypatch.setattr(
        "app.connectors.catalog_ats.requests.get",
        lambda *args, **kwargs: FakeResponse(
            {
                "jobs": [
                    {
                        "id": "abc",
                        "title": "Industrial Data Analyst",
                        "location": "Remote - Americas",
                        "descriptionPlain": "Analyze manufacturing data.",
                        "jobUrl": "https://example.test/abc",
                        "isRemote": True,
                        "compensation": {"currencyCode": "USD"},
                    }
                ]
            }
        ),
    )

    jobs = CatalogATSConnector("ashby")._ashby("example", "Example")

    assert jobs[0]["is_remote"] is True
    assert jobs[0]["compensation"]["currencyCode"] == "USD"
