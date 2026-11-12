from __future__ import annotations

import os
from functools import lru_cache
from math import isclose
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / ".env", override=False)
load_dotenv(ROOT / ".env", override=True)


def load_yaml(name: str) -> dict[str, Any]:
    path = ROOT / "config" / name
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def settings() -> dict[str, Any]:
    data = load_yaml("settings.yaml")
    db_override = os.getenv("JOB_SEARCHER_DB")
    if db_override:
        data["database_url"] = f"sqlite:///{db_override}"
    return data


@lru_cache(maxsize=1)
def searches() -> list[dict[str, Any]]:
    data = load_yaml("searches.yaml").get("searches", [])
    for search in data:
        if len(search.get("locations", [])) != len(search.get("countries", [])):
            raise ValueError(
                f"Search {search.get('id', '<unknown>')} must pair every location with a country"
            )
    return data


@lru_cache(maxsize=1)
def watchlist() -> list[str]:
    return load_yaml("companies.yaml").get("watchlist", [])


@lru_cache(maxsize=1)
def source_catalog() -> dict[str, Any]:
    return load_yaml("sources.yaml")


@lru_cache(maxsize=1)
def strategy() -> dict[str, Any]:
    data = load_yaml("strategy.yaml")
    if not data.get("version"):
        raise ValueError("config/strategy.yaml must define a version")
    scoring = data.get("scoring", {})
    dimensions = scoring.get("dimensions", {})
    if not dimensions or not isclose(sum(dimensions.values()), 1.0, abs_tol=0.001):
        raise ValueError("Strategy scoring dimensions must sum to 1")
    outer_weight = float(scoring.get("fit_weight", 0)) + float(
        scoring.get("feasibility_weight", 0)
    )
    if not isclose(outer_weight, 1.0, abs_tol=0.001):
        raise ValueError("Strategy fit and feasibility weights must sum to 1")
    return data
