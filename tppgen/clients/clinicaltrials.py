"""ClinicalTrials.gov API v2. No key required. Source of endpoints, populations, competitors."""
from __future__ import annotations

import re
from typing import Any, Iterator

from ._http import request

BASE = "https://clinicaltrials.gov/api/v2"
from .. import cache  # noqa: E402


def _studies_page(condition: str, page_token: str | None, page_size: int) -> dict:
    params: dict[str, Any] = {
        # Quoted: an unquoted multi-word condition matches studies carrying only
        # some of the words, which drags in unrelated disease areas.
        "query.cond": f'"{condition}"',
        "filter.advanced": "AREA[StudyType]INTERVENTIONAL",
        "pageSize": page_size,
        "countTotal": "true",
    }
    if page_token:
        params["pageToken"] = page_token
    return request("GET", f"{BASE}/studies", params=params)


def fetch_studies(condition: str, max_studies: int = 300) -> list[dict]:
    """Every interventional study registered for the condition, up to max_studies."""
    cached = cache.get("ctgov", {"cond": condition, "max": max_studies})
    if cached is not None:
        return cached

    out: list[dict] = []
    token: str | None = None
    while len(out) < max_studies:
        page = _studies_page(condition, token, min(100, max_studies - len(out)))
        out.extend(page.get("studies", []))
        token = page.get("nextPageToken")
        if not token:
            break
    cache.put("ctgov", {"cond": condition, "max": max_studies}, out)
    return out


def parse_study(study: dict) -> dict:
    """Flatten one study to the fields the TPP needs. Missing stays None, never guessed."""
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    conditions = p.get("conditionsModule", {}).get("conditions", []) or []
    design = p.get("designModule", {})
    arms = p.get("armsInterventionsModule", {})
    outcomes = p.get("outcomesModule", {})
    elig = p.get("eligibilityModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})

    interventions = arms.get("interventions", []) or []
    return {
        "nct_id": ident.get("nctId"),
        "conditions": conditions,
        "title": ident.get("briefTitle"),
        "status": p.get("statusModule", {}).get("overallStatus"),
        "phases": design.get("phases") or [],
        "sponsor": sponsor.get("name"),
        "sponsor_class": sponsor.get("class"),
        "interventions": [
            {"type": i.get("type"), "name": i.get("name")} for i in interventions
        ],
        "primary_outcomes": [
            o.get("measure") for o in (outcomes.get("primaryOutcomes") or []) if o.get("measure")
        ],
        "secondary_outcomes": [
            o.get("measure") for o in (outcomes.get("secondaryOutcomes") or []) if o.get("measure")
        ],
        "eligibility_text": elig.get("eligibilityCriteria"),
        "sex": elig.get("sex"),
        "min_age": elig.get("minimumAge"),
        "max_age": elig.get("maximumAge"),
        "healthy_volunteers": elig.get("healthyVolunteers"),
        "url": f"https://clinicaltrials.gov/study/{ident.get('nctId')}" if ident.get("nctId") else None,
    }


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2}


def _is_on_condition(study: dict, disease_words: set[str]) -> bool:
    """Keep only studies that actually list this condition.

    The registry's condition search is fuzzy: a search for myotonic dystrophy
    returns oncology trials whose endpoints then dominate the ranking. Checking
    the study's own condition list is the cheap, reliable filter.
    """
    if not disease_words:
        return True
    for cond in study.get("conditions") or []:
        cw = _words(cond)
        if cw and len(disease_words & cw) / len(disease_words) >= 0.6:
            return True
    return False


def studies(condition: str, max_studies: int = 300) -> Iterator[dict]:
    disease_words = _words(condition)
    for raw in fetch_studies(condition, max_studies):
        parsed = parse_study(raw)
        if _is_on_condition(parsed, disease_words):
            yield parsed
