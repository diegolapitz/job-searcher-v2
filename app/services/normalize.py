from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from app.services.identity import clean_text, normalize_text

COUNTRY_PATTERNS = {
    "Argentina": [
        "argentina",
        "buenos aires",
        "cordoba",
        "córdoba",
        "rosario",
        "mendoza",
        "salta",
        "tucuman",
        "tucumán",
        "santa fe",
        "la rioja",
        "zarate",
        "zárate",
    ],
    "Spain": ["spain", "españa", "madrid", "barcelona", "catalonia", "valencia"],
    "Germany": ["germany", "deutschland", "bavaria", "berlin", "hamburg"],
    "United Kingdom": ["united kingdom", "england", "scotland", "wales", "london"],
    "Canada": ["canada", "ontario", "quebec", "alberta", "british columbia"],
    "Australia": ["australia", "queensland", "victoria", "new south wales"],
    "United States": ["united states", "usa", " u.s."],
    "India": ["india"],
    "Brazil": ["brazil", "brasil"],
    "Saudi Arabia": ["saudi arabia"],
    "Singapore": ["singapore"],
    "Kuwait": ["kuwait"],
    "Thailand": ["thailand"],
    "France": ["france"],
    "Netherlands": ["netherlands"],
    "Mexico": ["mexico", "méxico"],
    "Chile": ["chile"],
    "Colombia": ["colombia"],
    "Ireland": ["ireland"],
    "Italy": ["italy", "italia"],
    "Portugal": ["portugal"],
}

COUNTRY_SUFFIXES = {
    "ar": "Argentina",
    "es": "Spain",
    "de": "Germany",
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "au": "Australia",
    "us": "United States",
}


def parse_date(value) -> datetime | None:
    if value is None or clean_text(value) == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    if hasattr(parsed, "to_pydatetime"):
        return parsed.to_pydatetime().replace(tzinfo=None)
    return parsed


def infer_country(location) -> str | None:
    text = clean_text(location).casefold()
    if not text:
        return None
    suffix = re.search(r",\s*([a-z]{2})$", text)
    if suffix and suffix.group(1) in COUNTRY_SUFFIXES:
        return COUNTRY_SUFFIXES[suffix.group(1)]
    for country, patterns in COUNTRY_PATTERNS.items():
        if any(pattern.casefold() in text for pattern in patterns):
            return country
    if re.search(r"\bremote\b|\bremoto\b", text):
        return "Remote"
    return None


def infer_work_mode(location, description="") -> str | None:
    location_text = normalize_text(location)
    text = f"{location_text} {normalize_text(description)}"
    if "hybrid" in text or "hibrido" in text or "hibrida" in text:
        return "hybrid"
    if "remote" in location_text or "remoto" in location_text:
        return "remote"
    if location_text:
        return "onsite"
    return None


def normalize_job(payload: dict) -> dict:
    location = clean_text(payload.get("location"))
    return {
        "title": clean_text(payload.get("title")) or "Untitled role",
        "company": clean_text(payload.get("company")) or "Unknown company",
        "location_text": location or None,
        "country": infer_country(location),
        "work_mode": infer_work_mode(location, payload.get("description")),
        "description": clean_text(payload.get("description")) or None,
        "source": clean_text(payload.get("site") or payload.get("source")).lower(),
        "source_job_id": clean_text(payload.get("id") or payload.get("source_job_id")) or None,
        "source_url": clean_text(payload.get("job_url") or payload.get("source_url")) or None,
        "direct_url": clean_text(payload.get("job_url_direct")) or None,
        "date_posted": parse_date(payload.get("date_posted")),
        "salary_min": _number(payload.get("min_amount")),
        "salary_max": _number(payload.get("max_amount")),
        "salary_currency": clean_text(payload.get("currency")) or None,
        "salary_interval": clean_text(payload.get("interval")) or None,
    }


def json_safe(value):
    """Convert connector payload values to types accepted by SQL JSON columns."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if pd.isna(value) else value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (TypeError, ValueError):
            pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _number(value) -> float | None:
    try:
        if value is None or clean_text(value) == "":
            return None
        number = float(value)
        return None if pd.isna(number) else number
    except (TypeError, ValueError):
        return None
