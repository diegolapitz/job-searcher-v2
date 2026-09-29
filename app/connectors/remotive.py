from __future__ import annotations

import time

import requests

from app.connectors.base import CollectionRequest, CollectionResult


class RemotiveConnector:
    source = "remotive"

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        try:
            response = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": request.term, "limit": request.results_wanted},
                timeout=15,
            )
            response.raise_for_status()
            jobs = []
            for item in response.json().get("jobs", []):
                jobs.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "company": item.get("company_name"),
                        "location": item.get("candidate_required_location") or "Remote",
                        "description": item.get("description"),
                        "job_url": item.get("url"),
                        "date_posted": str(item.get("publication_date") or "")[:10],
                        "site": self.source,
                        "is_remote": True,
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
