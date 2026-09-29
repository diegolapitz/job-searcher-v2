from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


EMPTY_VALUES = {"", "nan", "none", "null", "n/a", "na", "-"}


def clean_text(value) -> str:
    text = "" if value is None else str(value)
    if text.strip().lower() in EMPTY_VALUES:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(value) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"\b(senior|sr|junior|jr)\b\.?", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value) -> str:
    url = clean_text(value)
    if not url:
        return ""
    split = urlsplit(url)
    clean_query = [
        (key, val)
        for key, val in parse_qsl(split.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "trk", "tracking"))
    ]
    return urlunsplit(
        (split.scheme.lower(), split.netloc.lower(), split.path.rstrip("/"), urlencode(clean_query), "")
    )


def source_identity(source: str, source_job_id, source_url) -> str:
    source = normalize_text(source)
    external_id = clean_text(source_job_id)
    if external_id:
        return f"{source}:id:{external_id}"
    url = normalize_url(source_url)
    if url:
        return f"{source}:url:{url}"
    return ""


def canonical_job_id(
    source: str,
    source_job_id,
    source_url,
    title,
    company,
    location,
) -> str:
    preferred = source_identity(source, source_job_id, source_url)
    if preferred:
        material = preferred
    else:
        material = "|".join(
            (normalize_text(title), normalize_text(company), normalize_text(location))
        )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def payload_hash(payload: dict) -> str:
    keys = (
        "title",
        "company",
        "location",
        "description",
        "date_posted",
        "min_amount",
        "max_amount",
    )
    material = "|".join(clean_text(payload.get(key)) for key in keys)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
