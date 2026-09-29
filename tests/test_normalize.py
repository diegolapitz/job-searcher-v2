from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from app.services.normalize import infer_country, infer_work_mode, json_safe


def test_argentina_location_normalization():
    assert infer_country("Buenos Aires Province, Argentina") == "Argentina"
    assert infer_country("Rosario, Santa Fe") == "Argentina"
    assert infer_country("Buenos Aires, B, AR") == "Argentina"
    assert infer_country("Remote, US") == "United States"
    assert infer_country("São Paulo, São Paulo, Brazil") == "Brazil"


def test_work_mode_uses_location_first():
    assert infer_work_mode("Remote", "May visit an office") == "remote"
    assert infer_work_mode("Buenos Aires", "Modalidad híbrida") == "hybrid"


def test_json_safe_normalizes_connector_types():
    payload = {
        "posted": date(2026, 6, 12),
        "captured": datetime(2026, 6, 12, 18, 30),
        "salary": Decimal("12.50"),
        "missing": float("nan"),
        "nested": [pd.NA, {"value": pd.Timestamp("2026-06-12")}],
    }

    assert json_safe(payload) == {
        "posted": "2026-06-12",
        "captured": "2026-06-12T18:30:00",
        "salary": 12.5,
        "missing": None,
        "nested": [None, {"value": "2026-06-12T00:00:00"}],
    }
