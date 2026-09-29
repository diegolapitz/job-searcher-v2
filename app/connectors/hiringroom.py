from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.connectors.base import CollectionRequest, CollectionResult


class HiringRoomConnector:
    source = "hiringroom"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        ),
        "Accept-Language": "es-AR,es;q=0.9",
    }

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        slug = request.options["slug"]
        company = request.options.get("company") or slug
        base_url = f"https://{slug}.hiringroom.com"
        try:
            response = requests.get(
                f"{base_url}/jobs", headers=self.headers, timeout=30
            )
            response.raise_for_status()
            paths = list(
                dict.fromkeys(
                    re.findall(r"/jobs/get_vacancy/[a-f0-9]+", response.text)
                )
            )
            with ThreadPoolExecutor(max_workers=4) as executor:
                jobs = list(
                    executor.map(
                        lambda path: self._detail(urljoin(base_url, path), company),
                        paths,
                    )
                )
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

    def _detail(self, url: str, company: str) -> dict | None:
        response = requests.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("h1") or soup.find("h2")
        if not title:
            return None
        text = soup.get_text(" ", strip=True)
        location = None
        location_match = re.search(
            r"([A-ZÁÉÍÓÚÑ][^|]{2,80},\s*[^|]{2,50},\s*Argentina)", text
        )
        if location_match:
            location = location_match.group(1).strip()
        description_node = soup.select_one(
            ".description, .job-description, #description, [class*='description']"
        )
        return {
            "id": url.rstrip("/").split("/")[-1],
            "title": title.get_text(" ", strip=True),
            "company": company,
            "location": location or "Argentina",
            "description": description_node.get_text(" ", strip=True)
            if description_node
            else text,
            "job_url": url,
            "site": self.source,
        }
