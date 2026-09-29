from __future__ import annotations

import time

from jobspy import scrape_jobs

from app.connectors.base import CollectionRequest, CollectionResult


class JobSpyConnector:
    def __init__(self, source: str):
        if source not in {
            "linkedin",
            "indeed",
            "google",
            "glassdoor",
            "zip_recruiter",
        }:
            raise ValueError(f"Unsupported JobSpy source: {source}")
        self.source = source

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        try:
            frame = scrape_jobs(
                site_name=[self.source],
                search_term=request.term,
                location=request.location,
                country_indeed=request.country,
                results_wanted=request.results_wanted,
                hours_old=request.lookback_hours,
                linkedin_fetch_description=self.source == "linkedin",
                google_search_term=(
                    f"{request.term} jobs near {request.location}"
                    if self.source == "google"
                    else None
                ),
                is_remote="remote" in request.location.casefold(),
            )
            jobs = frame.to_dict("records") if frame is not None and not frame.empty else []
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
