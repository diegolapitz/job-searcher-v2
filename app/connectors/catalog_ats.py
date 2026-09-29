from __future__ import annotations

import time
from html import unescape

import requests
from bs4 import BeautifulSoup

from app.connectors.base import CollectionRequest, CollectionResult


def _text(value) -> str:
    return BeautifulSoup(unescape(str(value or "")), "html.parser").get_text(
        " ", strip=True
    )


class CatalogATSConnector:
    def __init__(self, source: str):
        if source not in {"greenhouse", "ashby", "lever"}:
            raise ValueError(f"Unsupported ATS: {source}")
        self.source = source

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        slug = request.options["slug"]
        company = request.options.get("company") or slug
        try:
            if self.source == "greenhouse":
                jobs = self._greenhouse(slug, company)
            elif self.source == "ashby":
                jobs = self._ashby(slug, company)
            else:
                jobs = self._lever(slug, company)
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

    def _greenhouse(self, slug: str, company: str) -> list[dict]:
        response = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            params={"content": "true"},
            timeout=30,
        )
        response.raise_for_status()
        return [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "company": company,
                "location": (item.get("location") or {}).get("name"),
                "description": _text(item.get("content")),
                "job_url": item.get("absolute_url"),
                "date_posted": item.get("updated_at"),
                "site": self.source,
                "departments": [
                    department.get("name") for department in item.get("departments", [])
                ],
                "offices": [office.get("name") for office in item.get("offices", [])],
            }
            for item in response.json().get("jobs", [])
        ]

    def _ashby(self, slug: str, company: str) -> list[dict]:
        response = requests.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            params={"includeCompensation": "true"},
            timeout=30,
        )
        response.raise_for_status()
        return [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "company": company,
                "location": item.get("location"),
                "description": _text(
                    item.get("descriptionPlain") or item.get("descriptionHtml")
                ),
                "job_url": item.get("jobUrl") or item.get("applyUrl"),
                "date_posted": item.get("publishedAt"),
                "site": self.source,
                "is_remote": item.get("isRemote"),
                "department": item.get("department"),
                "team": item.get("team"),
                "employment_type": item.get("employmentType"),
                "compensation": item.get("compensation"),
            }
            for item in response.json().get("jobs", [])
        ]

    def _lever(self, slug: str, company: str) -> list[dict]:
        response = requests.get(
            f"https://api.lever.co/v0/postings/{slug}",
            params={"mode": "json"},
            timeout=30,
        )
        response.raise_for_status()
        return [
            {
                "id": item.get("id"),
                "title": item.get("text"),
                "company": company,
                "location": (item.get("categories") or {}).get("location"),
                "description": _text(
                    " ".join(
                        [
                            item.get("descriptionPlain") or "",
                            item.get("additionalPlain") or "",
                        ]
                    )
                ),
                "job_url": item.get("hostedUrl") or item.get("applyUrl"),
                "site": self.source,
                "team": (item.get("categories") or {}).get("team"),
                "department": (item.get("categories") or {}).get("department"),
                "commitment": (item.get("categories") or {}).get("commitment"),
                "workplace_type": item.get("workplaceType"),
            }
            for item in response.json()
        ]
