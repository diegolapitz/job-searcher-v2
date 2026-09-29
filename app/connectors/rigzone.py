from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.connectors.base import CollectionRequest, CollectionResult


class RigzoneConnector:
    source = "rigzone"
    base_url = "https://www.rigzone.com"
    headers = {"User-Agent": "Mozilla/5.0 JobSearcherV2/1.0"}

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        try:
            response = requests.get(
                f"{self.base_url}/oil/jobs/search/",
                params={"sk": request.term, "fl": request.location},
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            urls = list(
                dict.fromkeys(
                    urljoin(self.base_url, link.get("href").split("?")[0])
                    for link in soup.select("a[href*='/oil/jobs/postings/']")
                )
            )[: request.results_wanted]
            with ThreadPoolExecutor(max_workers=4) as executor:
                jobs = list(executor.map(self._detail, urls))
            return CollectionResult(
                source=self.source,
                request=request,
                jobs=[job for job in jobs if job],
                duration_seconds=time.perf_counter() - started,
            )
        except Exception as exc:
            return CollectionResult(
                source=self.source,
                request=request,
                error=str(exc),
                duration_seconds=time.perf_counter() - started,
            )

    def _detail(self, url: str) -> dict | None:
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        posting = None
        for script in soup.select("script[type='application/ld+json']"):
            try:
                value = json.loads(script.get_text(strip=True))
            except (TypeError, json.JSONDecodeError):
                continue
            values = value if isinstance(value, list) else [value]
            posting = next(
                (
                    item
                    for item in values
                    if isinstance(item, dict) and item.get("@type") == "JobPosting"
                ),
                posting,
            )
        if posting:
            location = posting.get("jobLocation")
            if isinstance(location, list):
                location = location[0] if location else {}
            address = (location or {}).get("address", {}) if isinstance(location, dict) else {}
            location_text = ", ".join(
                str(address.get(key))
                for key in ("addressLocality", "addressRegion", "addressCountry")
                if address.get(key)
            )
            organization = posting.get("hiringOrganization") or {}
            return {
                "id": re.search(r"/postings/(\d+)", url).group(1),
                "title": posting.get("title"),
                "company": organization.get("name"),
                "location": location_text,
                "description": BeautifulSoup(
                    posting.get("description") or "", "html.parser"
                ).get_text(" ", strip=True),
                "job_url": url,
                "date_posted": posting.get("datePosted"),
                "site": self.source,
            }
        title = soup.find("h1")
        if not title:
            return None
        return {
            "id": re.search(r"/postings/(\d+)", url).group(1),
            "title": title.get_text(" ", strip=True),
            "company": "Unknown company",
            "location": None,
            "description": soup.get_text(" ", strip=True),
            "job_url": url,
            "site": self.source,
        }
