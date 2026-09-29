from __future__ import annotations

import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from app.connectors.base import CollectionRequest, CollectionResult


def _plain(value) -> str:
    return BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)


class PublicFeedConnector:
    def __init__(self, source: str):
        if source not in {"remoteok", "jobicy", "arbeitnow"}:
            raise ValueError(f"Unsupported public feed: {source}")
        self.source = source

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        try:
            jobs = getattr(self, f"_{self.source}")(request)
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

    def _remoteok(self, request: CollectionRequest) -> list[dict]:
        response = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "JobSearcherV2/1.0"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return [
            {
                "id": item.get("id"),
                "title": item.get("position"),
                "company": item.get("company"),
                "location": item.get("location") or "Remote",
                "description": _plain(item.get("description")),
                "job_url": item.get("url") or item.get("apply_url"),
                "date_posted": item.get("date"),
                "site": self.source,
                "is_remote": True,
                "tags": item.get("tags") or [],
                "min_amount": item.get("salary_min"),
                "max_amount": item.get("salary_max"),
                "currency": "USD",
                "interval": "year",
            }
            for item in data
            if isinstance(item, dict) and item.get("position")
        ]

    def _jobicy(self, request: CollectionRequest) -> list[dict]:
        response = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": min(request.results_wanted, 50)},
            timeout=30,
        )
        response.raise_for_status()
        return [
            {
                "id": item.get("id"),
                "title": item.get("jobTitle"),
                "company": item.get("companyName"),
                "location": item.get("jobGeo") or "Remote",
                "description": _plain(item.get("jobDescription")),
                "job_url": item.get("url"),
                "date_posted": item.get("pubDate"),
                "site": self.source,
                "is_remote": True,
                "job_type": item.get("jobType"),
                "industry": item.get("jobIndustry"),
                "min_amount": item.get("annualSalaryMin"),
                "max_amount": item.get("annualSalaryMax"),
                "currency": item.get("salaryCurrency"),
                "interval": "year",
            }
            for item in response.json().get("jobs", [])
        ]

    def _arbeitnow(self, request: CollectionRequest) -> list[dict]:
        jobs = []
        pages = int(request.options.get("pages", 5))
        cutoff = datetime.now(timezone.utc).timestamp() - request.lookback_hours * 3600
        for page in range(1, pages + 1):
            response = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"page": page},
                timeout=30,
            )
            response.raise_for_status()
            batch = response.json().get("data", [])
            if not batch:
                break
            for item in batch:
                created = item.get("created_at")
                if created and float(created) < cutoff:
                    continue
                jobs.append(
                    {
                        "id": item.get("slug"),
                        "title": item.get("title"),
                        "company": item.get("company_name"),
                        "location": item.get("location"),
                        "description": _plain(item.get("description")),
                        "job_url": item.get("url"),
                        "date_posted": datetime.fromtimestamp(
                            float(created), timezone.utc
                        ).isoformat()
                        if created
                        else None,
                        "site": self.source,
                        "is_remote": item.get("remote"),
                        "tags": item.get("tags") or [],
                    }
                )
        return jobs
