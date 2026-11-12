from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache

import anthropic

from app.config import settings, strategy
from app.services.identity import clean_text, normalize_text


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


def calculate_priority(data: dict, scoring: dict | None = None) -> int:
    scoring = scoring or strategy()["scoring"]
    fit = sum(
        data.get(dimension, 0) * float(weight)
        for dimension, weight in scoring["dimensions"].items()
    )
    feasibility = data.get("application_feasibility", 0)
    raw_priority = (
        fit * float(scoring.get("fit_weight", 0.70))
        + feasibility * float(scoring.get("feasibility_weight", 0.30))
    )
    confidence = max(
        int(scoring.get("confidence_floor", 55)), data.get("confidence", 0)
    ) / 100
    penalty_weight = float(scoring.get("confidence_penalty_weight", 0.25))
    confidence_factor = 1 - penalty_weight * (1 - confidence)
    return round(raw_priority * confidence_factor)


@lru_cache(maxsize=2048)
def _prepared_term(term: str) -> tuple[bool, str]:
    cleaned = clean_text(term)
    return cleaned.endswith("*"), normalize_text(cleaned.removesuffix("*"))


def _matches(text: str, terms: list[str]) -> list[str]:
    normalized = normalize_text(text)
    padded = f" {normalized} "
    tokens = normalized.split()
    matches = []
    for term in terms:
        prefix_match, normalized_term = _prepared_term(term)
        if not normalized_term:
            continue
        if prefix_match:
            found = any(token.startswith(normalized_term) for token in tokens)
        else:
            found = f" {normalized_term} " in padded
        display_term = clean_text(term).removesuffix("*")
        if found and display_term not in matches:
            matches.append(display_term)
    return matches


def _score(matches: list[str], points_per_match: int, base: int = 0) -> int:
    return min(100, base + len(matches) * points_per_match)


class JobEvaluator:
    def __init__(self):
        ai_config = settings()["ai"]
        self.strategy = strategy()
        self.enabled = bool(ai_config["enabled"] and os.getenv("ANTHROPIC_API_KEY"))
        self.model = ai_config["model"]
        self.prompt_version = self.strategy["version"]
        self.max_description_chars = ai_config["max_description_chars"]
        self.max_tokens = ai_config["max_tokens"]
        self.client = anthropic.Anthropic() if self.enabled else None

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
        active_strategy = getattr(self, "strategy", strategy())
        heuristic = active_strategy["heuristic"]
        scoring = active_strategy["scoring"]
        text = f"{job.title} {job.company} {job.location_text or ''} {job.description or ''}"
        strong_industry_terms = heuristic.get("strong_industry_terms", [])
        context_industry_terms = heuristic.get("context_industry_terms", [])
        technical_terms = heuristic.get("technical_terms", [])
        career_terms = heuristic.get("career_value_terms", [])
        ownership_terms = heuristic.get("ownership_terms", [])
        strong_industry_matches = _matches(text, strong_industry_terms)
        context_industry_matches = _matches(text, context_industry_terms)
        industry_matches = strong_industry_matches + context_industry_matches
        technical_matches = _matches(text, technical_terms)
        career_matches = _matches(text, career_terms)
        ownership_matches = _matches(text, ownership_terms)
        industry = min(
            100,
            len(strong_industry_matches)
            * int(heuristic.get("strong_industry_points_per_match", 18))
            + len(context_industry_matches)
            * int(heuristic.get("context_industry_points_per_match", 5)),
        )
        technical = _score(
            technical_matches, int(heuristic.get("technical_points_per_match", 12))
        )
        career = _score(career_matches, 12, 20) + min(24, len(ownership_matches) * 8)
        career = min(100, career)

        role_group, function_family, role_evidence = self._match_role(active_strategy, job)
        role_base = {"core": 82, "adjacent": 66, "exploratory": 50}.get(
            role_group, 0
        )
        profile = round(technical * 0.35 + industry * 0.30 + career * 0.35)
        profile = max(profile, role_base)
        if strong_industry_matches and industry >= 25 and technical >= 35:
            profile = max(profile, 74)
            career = max(career, 70)
            if function_family == "unknown":
                function_family = "Industrial Analytics and Applied Data"
        if role_group == "core":
            career = max(career, 78)
            technical = max(technical, 55)
            industry = max(industry, 45)
        elif role_group == "adjacent":
            career = max(career, 66)
            technical = max(technical, 45)
            industry = max(industry, 40)
        elif role_group == "exploratory":
            career = max(career, 55)

        requires_industry = function_family in heuristic.get(
            "industry_required_role_families", []
        )
        if requires_industry and not strong_industry_matches:
            career = min(career, 60)
            industry = min(industry, 25)
            profile = min(profile, 50)

        title_alignment = bool(role_evidence) or bool(
            _matches(job.title or "", heuristic.get("target_title_terms", []))
        )
        robust_intersection = industry >= 50 and technical >= 50 and career >= 75
        if not strong_industry_matches or not (
            title_alignment or robust_intersection
        ):
            career = min(career, 60)
            profile = min(profile, 55)

        excluded_families = self._excluded_families(
            active_strategy,
            job.title or "",
            strong_industry=bool(strong_industry_matches),
            technical=technical,
            career=career,
        )
        if excluded_families:
            profile = min(profile, 18)
            career = min(career, 18)

        seniority, seniority_match, years_experience = self._seniority(job, text)
        feasibility_config = active_strategy["feasibility"]
        feasibility, feasibility_evidence, visa_sponsorship, relocation = (
            self._feasibility(job, text, feasibility_config)
        )

        description_length = len(job.description or "")
        if description_length >= 1000:
            confidence = 82
        elif description_length >= 200:
            confidence = 75
        elif description_length >= 100:
            confidence = 65
        else:
            confidence = 55
        data = {
            "profile_match": profile,
            "technical_match": technical,
            "industry_match": industry,
            "career_value": career,
            "application_feasibility": feasibility,
            "seniority_match": seniority_match,
            "confidence": confidence,
            "recommendation": "review",
            "reason": "Evaluación v3 por señales de rol, industria, tecnología, carrera y factibilidad.",
            "evidence_for": [
                *(f"Familia objetivo: {function_family}" for _ in role_evidence[:1]),
                *(f"Señales técnicas: {', '.join(technical_matches[:5])}" for _ in technical_matches[:1]),
                *(f"Señales industriales: {', '.join(industry_matches[:5])}" for _ in industry_matches[:1]),
                *(f"Valor de carrera: {', '.join(career_matches[:4])}" for _ in career_matches[:1]),
            ],
            "evidence_against": [
                "AI no disponible; requiere revisión manual.",
                *feasibility_evidence,
                *(f"Familia excluida: {family}" for family in excluded_families),
            ],
            "skills": technical_matches[:12],
            "years_experience": years_experience,
            "english_level": "unknown",
            "seniority": seniority,
            "industry": "industrial" if industry >= 35 else "other",
            "function_family": function_family,
            "visa_sponsorship": visa_sponsorship,
            "relocation": relocation,
        }
        data["priority_score"] = calculate_priority(data, scoring)
        thresholds = active_strategy["thresholds"]
        if excluded_families or feasibility <= 0 or seniority_match <= 20:
            data["recommendation"] = "discard"
        elif data["priority_score"] >= int(thresholds.get("high_priority", 82)):
            data["recommendation"] = "apply"
        elif data["priority_score"] >= int(thresholds.get("ai_prefilter_priority", 45)):
            data["recommendation"] = "review"
        else:
            data["recommendation"] = "discard"
        return self._result(data, "keyword_fallback")

    @staticmethod
    def _match_role(active_strategy: dict, job) -> tuple[str, str, list[str]]:
        candidates = []
        title = job.title or ""
        for group_rank, group in enumerate(("core", "adjacent", "exploratory")):
            for family in active_strategy.get("role_families", {}).get(group, []):
                terms = list(family.get("titles_es", [])) + list(
                    family.get("titles_en", [])
                )
                title_matches = _matches(title, terms)
                if title_matches:
                    candidates.append(
                        (
                            group_rank,
                            int(family.get("priority", 99)),
                            group,
                            family.get("family", "unknown"),
                            title_matches,
                        )
                    )
        if not candidates:
            return "", "unknown", []
        _, _, group, family, evidence = min(candidates)
        return group, family, evidence

    @staticmethod
    def _excluded_families(
        active_strategy: dict,
        text: str,
        *,
        strong_industry: bool,
        technical: int,
        career: int,
    ) -> list[str]:
        excluded = []
        digital_context = technical >= 35 or career >= 60
        for family in active_strategy.get("role_families", {}).get("excluded", []):
            matches = _matches(text, family.get("titles_and_keywords", []))
            if not matches:
                continue
            family_name = family.get("family", "unknown")
            normalized_family = normalize_text(family_name)
            if (
                "traditional process engineering" in normalized_family
                and strong_industry
                and digital_context
            ):
                continue
            if (
                "generic business intelligence" in normalized_family
                and strong_industry
                and digital_context
            ):
                continue
            if (
                "generic data science" in normalized_family
                and strong_industry
                and digital_context
            ):
                continue
            if "routine quality" in normalized_family and digital_context:
                continue
            excluded.append(family_name)
        return excluded

    @staticmethod
    def _seniority(job, text: str) -> tuple[str, int, str]:
        title = clean_text(job.title).casefold()
        if any(term in title for term in ("director", "head of", "vice president", "vp ")):
            seniority, score = "lead", 20
        elif any(term in title for term in ("manager", "gerente", "jefe", "superintendente")):
            seniority, score = "lead", 45
        elif any(term in title for term in ("lead", "lider", "líder")):
            seniority, score = "lead", 55
        elif re.search(r"\b(senior|sr|ssr)\b", title):
            seniority, score = "senior", 68
        elif any(term in title for term in ("junior", " jr", "jr.", "trainee", "pasante")):
            seniority, score = "junior", 82
        else:
            seniority, score = "mid", 85

        years = [
            int(value)
            for value in re.findall(
                r"(\d{1,2})\s*\+?\s*(?:years?|anos?)[^.]{0,40}(?:experience|experiencia)",
                normalize_text(text),
            )
        ]
        required_years = max(years, default=None)
        if required_years is not None:
            if required_years >= 8:
                score = min(score, 15)
            elif required_years >= 6:
                score = min(score, 30)
            elif required_years >= 5:
                score = min(score, 50)
        return seniority, score, f"{required_years}+" if required_years else "unknown"

    @staticmethod
    def _feasibility(job, text: str, config: dict) -> tuple[int, list[str], bool, bool]:
        evidence = []
        sponsorship_matches = _matches(text, config.get("sponsorship_terms", []))
        relocation_matches = _matches(text, config.get("relocation_terms", []))
        hard_restrictions = _matches(text, config.get("hard_restriction_terms", []))
        visa_sponsorship = bool(sponsorship_matches)
        relocation = bool(relocation_matches)

        if job.country in config.get("home_countries", []):
            return int(config.get("home_country_score", 100)), evidence, visa_sponsorship, relocation

        if hard_restrictions:
            evidence.append(
                f"Restricción legal/geográfica: {', '.join(hard_restrictions[:3])}."
            )
            return 0, evidence, visa_sponsorship, relocation

        if job.work_mode == "remote" or job.country == "Remote":
            restricted = _matches(text, config.get("remote_restricted_terms", []))
            eligible = _matches(text, config.get("remote_eligible_terms", []))
            if restricted:
                evidence.append(
                    f"Remoto restringido: {', '.join(restricted[:3])}."
                )
                feasibility = int(config.get("remote_restricted_score", 0))
            elif eligible:
                feasibility = int(config.get("remote_score", 95))
            else:
                feasibility = int(config.get("remote_unknown_score", 35))
                evidence.append("El alcance geográfico del remoto no está confirmado.")
            return feasibility, evidence, visa_sponsorship, relocation

        if visa_sponsorship or relocation:
            return int(config.get("foreign_with_support_score", 75)), evidence, visa_sponsorship, relocation
        evidence.append("Presencial extranjero sin sponsorship o relocation explícitos.")
        return int(config.get("foreign_onsite_score", 10)), evidence, visa_sponsorship, relocation

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
        active_strategy = self.strategy
        profile = active_strategy["profile"]
        role_families = active_strategy.get("role_families", {})
        feasibility_rules = "\n".join(
            f"- {rule}" for rule in active_strategy["feasibility"].get("instructions", [])
        )
        extra_instructions = "\n".join(
            f"- {rule}" for rule in active_strategy.get("ai", {}).get("extra_instructions", [])
        )
        targets = ", ".join(
            family["family"]
            for group in ("core", "adjacent", "exploratory")
            for family in role_families.get(group, [])
        )
        exclusions = ", ".join(
            family["family"] for family in role_families.get("excluded", [])
        )
        priority_industries = ", ".join(
            active_strategy.get("industries", {}).get("priority", [])
        )
        seniority_rules = active_strategy.get("seniority", {}).get("notes", "")
        return f"""
Evaluate this job using strategy {active_strategy['version']}.

Candidate profile: {profile['summary']}
Target role families: {targets}
Excluded role families: {exclusions}
Priority industries: {priority_industries}
Seniority rules: {seniority_rules}

Do not collapse fit and feasibility into one judgment. Score each dimension 0-100:
- profile_match
- technical_match
- industry_match
- career_value
- application_feasibility
- seniority_match
- confidence

Feasibility rules:
{feasibility_rules}

Additional evaluation rules:
{extra_instructions}

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
