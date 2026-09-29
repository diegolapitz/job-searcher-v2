from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from app.config import settings
from app.services.identity import clean_text


@dataclass
class EvaluationResult:
    model: str
    prompt_version: str
    method: str
    profile_match: int
    technical_match: int
    industry_match: int
    career_value: int
    application_feasibility: int
    seniority_match: int
    confidence: int
    priority_score: int
    recommendation: str
    reason: str
    evidence_for: list[str]
    evidence_against: list[str]
    skills: list[str]
    years_experience: str
    english_level: str
    seniority: str
    industry: str
    function_family: str
    visa_sponsorship: bool
    relocation: bool
    raw_response: dict


def calculate_priority(data: dict) -> int:
    fit = (
        data.get("profile_match", 0) * 0.28
        + data.get("technical_match", 0) * 0.16
        + data.get("industry_match", 0) * 0.18
        + data.get("career_value", 0) * 0.14
        + data.get("seniority_match", 0) * 0.08
    )
    feasibility = data.get("application_feasibility", 0)
    confidence = max(40, data.get("confidence", 0)) / 100
    return round((fit * 0.68 + feasibility * 0.32) * confidence)


class JobEvaluator:
    def __init__(self):
        ai_config = settings()["ai"]
        self.enabled = bool(ai_config["enabled"])
        self.model = ai_config["model"]
        self.prompt_version = ai_config["prompt_version"]
        self.max_description_chars = ai_config["max_description_chars"]
        self.max_tokens = ai_config["max_tokens"]
        self.client = anthropic.Anthropic()

    def evaluate(self, job) -> EvaluationResult:
        if not self.enabled:
            return self.keyword_fallback(job)
        prompt = self._prompt(job)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = response.content[0].text.strip()
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text).strip()
            data = json.loads(raw_text)
            data["priority_score"] = calculate_priority(data)
            return self._result(data, "ai")
        except Exception:
            return self.keyword_fallback(job)

    def keyword_fallback(self, job) -> EvaluationResult:
        text = f"{job.title} {job.company} {job.location_text or ''} {job.description or ''}".casefold()
        industry_terms = [
            "manufactur",
            "industrial",
            "process",
            "proceso",
            "plant",
            "planta",
            "chemical",
            "quim",
            "mining",
            "energy",
            "pharma",
            "health",
        ]
        technical_terms = [
            "python",
            "sql",
            "power bi",
            "tableau",
            "analytics",
            "data",
            "estadística",
            "statistics",
        ]
        excludes = ["marketing", "venture capital", "frontend", "mobile developer"]
        industry = min(100, sum(18 for term in industry_terms if term in text))
        technical = min(100, sum(16 for term in technical_terms if term in text))
        profile = round((industry + technical) / 2)
        feasibility = 90 if job.country == "Argentina" else 75 if job.work_mode == "remote" else 25
        if any(term in text for term in excludes):
            profile = min(profile, 15)
        data = {
            "profile_match": profile,
            "technical_match": technical,
            "industry_match": industry,
            "career_value": profile,
            "application_feasibility": feasibility,
            "seniority_match": 60,
            "confidence": 75,
            "recommendation": "review" if profile >= 45 else "discard",
            "reason": "Evaluación heurística por indisponibilidad de AI.",
            "evidence_for": [],
            "evidence_against": ["AI no disponible; requiere revisión manual."],
            "skills": [term for term in technical_terms if term in text][:8],
            "years_experience": "unknown",
            "english_level": "unknown",
            "seniority": "unknown",
            "industry": "industrial" if industry >= 35 else "other",
            "function_family": "unknown",
            "visa_sponsorship": False,
            "relocation": "relocation" in text,
        }
        data["priority_score"] = calculate_priority(data)
        return self._result(data, "keyword_fallback")

    def _result(self, data: dict, method: str) -> EvaluationResult:
        score = int(max(0, min(100, data.get("priority_score", 0))))
        recommendation = data.get("recommendation") or (
            "apply" if score >= 78 else "review" if score >= 55 else "discard"
        )
        return EvaluationResult(
            model=self.model,
            prompt_version=self.prompt_version,
            method=method,
            profile_match=int(data.get("profile_match", 0)),
            technical_match=int(data.get("technical_match", 0)),
            industry_match=int(data.get("industry_match", 0)),
            career_value=int(data.get("career_value", 0)),
            application_feasibility=int(data.get("application_feasibility", 0)),
            seniority_match=int(data.get("seniority_match", 0)),
            confidence=int(data.get("confidence", 0)),
            priority_score=score,
            recommendation=recommendation,
            reason=clean_text(data.get("reason")),
            evidence_for=list(data.get("evidence_for") or []),
            evidence_against=list(data.get("evidence_against") or []),
            skills=list(data.get("skills") or [])[:12],
            years_experience=clean_text(data.get("years_experience")) or "unknown",
            english_level=clean_text(data.get("english_level")) or "unknown",
            seniority=clean_text(data.get("seniority")) or "unknown",
            industry=clean_text(data.get("industry")) or "unknown",
            function_family=clean_text(data.get("function_family")) or "unknown",
            visa_sponsorship=bool(data.get("visa_sponsorship")),
            relocation=bool(data.get("relocation")),
            raw_response=data,
        )

    def _prompt(self, job) -> str:
        description = (job.description or "")[: self.max_description_chars]
        return f"""
Evaluate this job for a chemical/process engineer with industrial plant experience
and skills in Python, SQL, Excel and Power BI. The target is the intersection of
process/manufacturing/operations/healthcare with data and analytics.

Do not collapse fit and feasibility into one judgment. Score each dimension 0-100:
- profile_match
- technical_match
- industry_match
- career_value
- application_feasibility
- seniority_match
- confidence

Feasibility rules:
- Argentina: generally feasible.
- Global remote that accepts Argentina/LATAM: feasible.
- Onsite outside Argentina: low unless explicit visa, work permit or relocation evidence.
- Do not infer visa sponsorship from the country alone.
- ITAR, security clearance, US citizenship or explicit no-sponsorship: feasibility 0.

Return only valid JSON:
{{
  "profile_match": 0,
  "technical_match": 0,
  "industry_match": 0,
  "career_value": 0,
  "application_feasibility": 0,
  "seniority_match": 0,
  "confidence": 0,
  "recommendation": "apply|review|discard",
  "reason": "one concise sentence",
  "evidence_for": ["quoted or paraphrased evidence"],
  "evidence_against": ["quoted or paraphrased evidence"],
  "skills": ["up to 12 normalized skills"],
  "years_experience": "range or unknown",
  "english_level": "level or unknown",
  "seniority": "junior|mid|senior|lead|unknown",
  "industry": "normalized industry",
  "function_family": "normalized role family",
  "visa_sponsorship": false,
  "relocation": false
}}

Title: {job.title}
Company: {job.company}
Location: {job.location_text or "unknown"}
Normalized country: {job.country or "unknown"}
Work mode: {job.work_mode or "unknown"}
Description: {description}
""".strip()
