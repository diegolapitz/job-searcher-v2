from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from app.connectors.base import CollectionRequest, CollectionResult


class ComputrabajoConnector:
    source = "computrabajo"
    base_url = "https://ar.computrabajo.com"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        ),
        "Accept-Language": "es-AR,es;q=0.9",
    }

    def collect(self, request: CollectionRequest) -> CollectionResult:
        started = time.perf_counter()
        try:
            slug = quote(request.term.casefold().replace(" ", "-"))
            response = requests.get(
                f"{self.base_url}/trabajo-de-{slug}",
                headers=self.headers,
                timeout=20,
            )
            response.raise_for_status()
            jobs = self._parse_listing(response.text)
            with ThreadPoolExecutor(max_workers=4) as executor:
                jobs = list(executor.map(self._enrich, jobs))
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

    def _parse_listing(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[dict] = []
        seen_urls: set[str] = set()
        for article in soup.find_all("article", class_="box_offer"):
            link = article.find("a", class_="js-o-link")
            if not link:
                continue
            href = (link.get("href") or "").split("#")[0]
            if href and not href.startswith("http"):
                href = self.base_url + href
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)
            company = article.find(
                "a", attrs={"offer-grid-article-company-url": True}
            )
            location = "Argentina"
            for paragraph in article.find_all("p"):
                classes = paragraph.get("class") or []
                if "fs16" in classes and not paragraph.find(
                    "a", attrs={"offer-grid-article-company-url": True}
                ):
                    span = paragraph.find("span")
                    if span:
                        location = span.get_text(" ", strip=True)
                        break
            jobs.append(
                {
                    "title": link.get_text(" ", strip=True),
                    "company": company.get_text(" ", strip=True) if company else None,
                    "location": location,
                    "job_url": href,
                    "site": self.source,
                }
            )
        return jobs

    def _enrich(self, job: dict) -> dict:
        try:
            response = requests.get(job["job_url"], headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            detail = soup.find("div", class_="box_detail")
            description = ""
            if detail:
                content = detail.find("div", class_=lambda value: value and "mb40" in value)
                if content:
                    description = content.get_text(" ", strip=True)
            job["description"] = description
        except Exception:
            job["description"] = ""
        return job
