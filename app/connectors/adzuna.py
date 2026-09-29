from __future__ import annotations

import os
import time

import requests
from bs4 import BeautifulSoup

from app.connectors.base import CollectionRequest, CollectionResult


class AdzunaConnector:
    source = "adzuna"

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")
        if not app_id or not app_key:
            return CollectionResult(
                source=self.source,
                request=request,
                error="ADZUNA_APP_ID/ADZUNA_APP_KEY not configured",
                duration_seconds=time.perf_counter() - started,
            )
        country = request.options.get("country_code", "gb")
        jobs = []
        try:
            for page in range(1, int(request.options.get("pages", 2)) + 1):
                response = requests.get(
                    f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}",
                    params={
                        "app_id": app_id,
                        "app_key": app_key,
                        "results_per_page": request.results_wanted,
                        "what": request.term,
                        "where": request.location,
                        "max_days_old": max(1, request.lookback_hours // 24),
                        "content-type": "application/json",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                for item in response.json().get("results", []):
                    jobs.append(
                        {
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "company": (item.get("company") or {}).get("display_name"),
                            "location": (item.get("location") or {}).get("display_name"),
                            "description": BeautifulSoup(
                                item.get("description") or "", "html.parser"
                            ).get_text(" ", strip=True),
                            "job_url": item.get("redirect_url"),
                            "date_posted": item.get("created"),
                            "site": self.source,
                            "min_amount": item.get("salary_min"),
                            "max_amount": item.get("salary_max"),
                        }
                    )
            return CollectionResult(
                source=self.source,
                request=request,
                jobs=jobs,
                duration_seconds=time.perf_counter() - started,
            )
        except Exception as exc:
            return CollectionResult(
                source=self.source,
                request=request,
                error=str(exc),
                duration_seconds=time.perf_counter() - started,
            )
