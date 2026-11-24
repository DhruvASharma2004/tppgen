"""openFDA: drug labels, approvals (Drugs@FDA) and adverse events (FAERS).

One service, one quota: 1,000 requests/day/IP without a key, 120,000/day with one.
Set OPENFDA_API_KEY to use the higher allowance.
"""
from __future__ import annotations

import os
import re
from typing import Any

from ._http import request
from .. import cache

BASE = "https://api.fda.gov/drug"


def _params(search: str, limit: int) -> dict[str, Any]:
    params = {"search": search, "limit": limit}
    key = os.environ.get("OPENFDA_API_KEY")
    if key:
        params["api_key"] = key
    return params


def _query(endpoint: str, search: str, limit: int = 20) -> list[dict]:
    payload = {"endpoint": endpoint, "search": search, "limit": limit}
    cached = cache.get("openfda", payload)
    if cached is not None:
        return cached
    try:
        data = request("GET", f"{BASE}/{endpoint}.json", params=_params(search, limit))
        results = data.get("results", [])
    except Exception:
        # openFDA returns 404 for a search with no matches. An empty result is a
        # legitimate answer ("nothing approved in this indication"), not an error.
        results = []
    cache.put("openfda", payload, results)
    return results


def label_for_drug(name: str) -> dict | None:
    """The label for a named drug.

    Searching label full text for a disease name is far too blunt: any product
    whose label merely mentions the disease matches, so an antibiotic used for a
    secondary infection outranks the disease's actual therapies. Drug names come
    from Open Targets instead, and each is looked up here by name.
    """
    if not name:
        return None
    quoted = name.replace('"', "").strip()
    for field in ("openfda.generic_name", "openfda.brand_name", "openfda.substance_name"):
        results = _query("label", f'{field}:"{quoted}"', 1)
        if results:
            return results[0]
    return None


_ALLCAPS = re.compile(r"^[A-Z][A-Z'()/&-]+$")


def _strip_section_heading(text: str) -> str:
    """Drop a leading "5 WARNINGS AND PRECAUTIONS" style heading.

    Done word by word rather than with one regex: a regex character class of
    capitals also swallows the first letter of the sentence that follows
    ("... PRECAUTIONS Hypersensitivity" lost its H), which corrupts the text.
    """
    words = text.split()
    i = 0
    if i < len(words) and re.fullmatch(r"\d+(\.\d+)?", words[i]):
        i += 1
    start = i
    while i < len(words) and (_ALLCAPS.fullmatch(words[i]) or words[i] in ("AND", "OR", "&")):
        i += 1
    # Only strip if it looked like a heading (at least one all-caps word of 3+).
    if i > start and any(len(w) >= 3 for w in words[start:i]):
        return " ".join(words[i:])
    return " ".join(words[start:]) if start else text


def clean(text: str | None, limit: int = 400) -> str | None:
    """Label text ships with section numbers, bullet glyphs and cross-references."""
    if not text:
        return None
    t = re.sub(r"[\u2022\u25cf\u00b7]", " ", text)
    t = re.sub(r"\(\s*\d+(\.\d+)?\s*\)", "", t)   # "( 5.1 )" cross-references
    t = re.sub(r"\s+", " ", t).strip()
    t = _strip_section_heading(t)
    if len(t) <= limit:
        return t
    cut = t[:limit]
    stop = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:stop + 1] if stop > limit * 0.5 else cut).strip() + " ..."


def parse_label(label: dict) -> dict:
    openfda = label.get("openfda", {})

    def first(key: str) -> str | None:
        vals = openfda.get(key) or []
        return vals[0] if vals else None

    def text(key: str) -> str | None:
        vals = label.get(key) or []
        return vals[0] if vals else None

    app_no = first("application_number")
    return {
        "brand_name": first("brand_name"),
        "generic_name": first("generic_name"),
        "manufacturer": first("manufacturer_name"),
        "application_number": app_no,
        "route": first("route"),
        "dosage_form": first("dosage_form"),
        "indications": clean(text("indications_and_usage")),
        # Searched for the dose sentence, never shown whole; the dose is often
        # past the first 400 characters (Brineura, Kalbitor).
        "dosage": clean(text("dosage_and_administration"), limit=20000),
        "contraindications": clean(text("contraindications")),
        "warnings": clean(text("warnings_and_cautions") or text("warnings")),
        "adverse_reactions": clean(text("adverse_reactions")),
        "interactions": clean(text("drug_interactions")),
        "mechanism": clean(text("mechanism_of_action")),
        # Full Section 14: the primary-endpoint sentence is often past the first
        # 400 characters (Aldurazyme), and this text is only searched, never shown.
        "clinical_studies": clean(text("clinical_studies"), limit=50000),
        "url": (
            f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app_no.lstrip('NDABLA')}"
            if app_no else None
        ),
    }


def faers_reactions(drug_name: str, limit: int = 10) -> list[dict]:
    """Most-reported adverse reactions for a drug. Counts are reports, not rates."""
    payload = {"drug": drug_name, "limit": limit}
    cached = cache.get("faers", payload)
    if cached is not None:
        return cached
    params = _params(f'patient.drug.medicinalproduct:"{drug_name}"', 1)
    params["count"] = "patient.reaction.reactionmeddrapt.exact"
    params.pop("limit", None)
    try:
        data = request("GET", f"{BASE}/event.json", params=params)
        results = data.get("results", [])[:limit]
    except Exception:
        results = []
    cache.put("faers", payload, results)
    return results


def _ndc_records(generic_name: str, brand_name: str | None, limit: int) -> list[dict]:
    """NDC records for this product. Brand first: a generic-name search also
    returns other products and bulk ingredients (Cystaran for Cystadrops)."""
    if brand_name:
        recs = _query("ndc", f'brand_name:"{brand_name.replace(chr(34), "")}"', limit)
        if recs:
            return recs
    if not generic_name:
        return []
    return _query("ndc", f'generic_name:"{generic_name.replace(chr(34), "")}"', limit)


def routes_for_product(generic_name: str, brand_name: str | None = None) -> list[str]:
    """Routes from the NDC directory, for labels with no openfda.route."""
    out: list[str] = []
    for rec in _ndc_records(generic_name, brand_name, 5):
        for r in rec.get("route") or []:
            if r not in out:
                out.append(r)
    return out


def dosage_forms_for_product(generic_name: str, limit: int = 5, brand_name: str | None = None) -> list[str]:
    """Dosage forms from the NDC directory. Many labels omit openfda.dosage_form."""
    if not generic_name and not brand_name:
        return []
    out: list[str] = []
    for rec in _ndc_records(generic_name, brand_name, limit):
        form = rec.get("dosage_form")
        if form and form not in out:
            out.append(form)
    return out


def strengths_for_product(generic_name: str, limit: int = 5, brand_name: str | None = None) -> list[str]:
    """Marketed strengths, from the NDC directory. The label does not carry these."""
    if not generic_name and not brand_name:
        return []
    results = _ndc_records(generic_name, brand_name, limit)
    out: list[str] = []
    for rec in results:
        for ing in rec.get("active_ingredients") or []:
            strength = (ing.get("strength") or "").strip()
            # Bulk-ingredient listings read "1 kg/kg"; that is a packaging
            # record, not a dose, and it is noise in a TPP.
            # A strength "per kg" is a bulk record too ("8 g/kg"), not a vial.
            if (not strength or re.match(r"^[\d.]+\s*(k?g)/[\d.]*\1$", strength, re.I)
                    or re.search(r"/\s*[\d.]*\s*kg$", strength, re.I)):
                continue
            label = f"{ing.get('name', '')} {strength}".strip()
            if label and label not in out:
                out.append(label)
    return out
