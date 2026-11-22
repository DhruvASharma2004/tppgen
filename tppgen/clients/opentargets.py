"""Open Targets Platform GraphQL API. CC0, no key, one endpoint.

Used for two things: resolving free text to an EFO/MONDO term, and pulling
mechanism and known-drug context for that disease.
"""
from __future__ import annotations

import re

from ._http import request
from .. import cache

ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"

SEARCH_QUERY = """
query DiseaseSearch($q: String!) {
  search(queryString: $q, entityNames: ["disease"], page: {index: 0, size: 8}) {
    hits { id name description }
  }
}
"""

DISEASE_QUERY = """
query DiseaseDetail($efoId: String!) {
  disease(efoId: $efoId) {
    id
    name
    description
    therapeuticAreas { id name }
    drugAndClinicalCandidates {
      count
      rows {
        maxClinicalStage
        drug {
          id
          name
          drugType
          mechanismsOfAction {
            uniqueActionTypes
            rows { mechanismOfAction actionType targetName }
          }
        }
      }
    }
    associatedTargets(page: {index: 0, size: 15}) {
      rows { score target { id approvedSymbol approvedName } }
    }
  }
}
"""


def _gql(query: str, variables: dict) -> dict:
    payload = {"query": query, "variables": variables}
    cached = cache.get("opentargets", payload)
    if cached is not None:
        return cached
    data = request("POST", ENDPOINT, json=payload)
    if "errors" in data:
        raise RuntimeError(f"Open Targets rejected the query: {data['errors']}")
    result = data.get("data", {})
    cache.put("opentargets", payload, result)
    return result


def search_disease(text: str) -> list[dict]:
    """Candidate ontology terms for free text. The user confirms one before anything runs."""
    hits = _gql(SEARCH_QUERY, {"q": text}).get("search", {}).get("hits", []) or []
    return [
        {
            "id": h.get("id"),
            "name": h.get("name"),
            "description": (h.get("description") or "")[:200],
            "url": f"https://platform.opentargets.org/disease/{h.get('id')}",
        }
        for h in hits
    ]


_ROMAN = {"i": 4, "ii": 3, "iii": 2, "iv": 1}


def pretty_stage(stage: str | None) -> str:
    """APPROVAL -> Approved, PHASE_2_3 -> Phase 2/3."""
    t = (stage or "").strip()
    if not t:
        return "Unknown"
    if t.upper().startswith("APPROV"):
        return "Approved"
    if t.upper().startswith(("PHASE", "EARLY_PHASE")):
        parts = [p for p in t.upper().replace("EARLY_PHASE", "EARLY PHASE").split("_") if p]
        nums = [p for p in parts if p.isdigit()]
        head = "Early phase" if t.upper().startswith("EARLY") else "Phase"
        return f"{head} {'/'.join(nums)}" if nums else head
    return t.replace("_", " ").capitalize() if t.isupper() else t


def stage_rank(stage: str | None) -> int:
    """Map a clinical stage to a sort rank, 0 = approved.

    Open Targets spells this field inconsistently across releases ("Approved",
    "Phase IV", "Phase 4", a bare "4"), so parse rather than match a fixed table.
    """
    t = (stage or "").strip().lower()
    if not t:
        return 9
    if "approv" in t or "market" in t:
        return 0
    token = t.replace("phase", "").strip()
    if token in _ROMAN:
        return _ROMAN[token]
    for digit, rank in (("4", 1), ("3", 2), ("2", 3), ("1", 4)):
        if digit in token:
            return rank
    return 9


def disease_detail(efo_id: str) -> dict:
    disease = _gql(DISEASE_QUERY, {"efoId": efo_id}).get("disease") or {}
    cand = (disease.get("drugAndClinicalCandidates") or {}).get("rows") or []
    targets = (disease.get("associatedTargets") or {}).get("rows") or []


    known: list[dict] = []
    seen_drugs: set[str] = set()
    for row in cand:
        drug = row.get("drug") or {}
        dname = drug.get("name")
        if not dname or dname.lower() in seen_drugs:
            continue
        seen_drugs.add(dname.lower())
        moa_rows = ((drug.get("mechanismsOfAction") or {}).get("rows")) or []
        first = moa_rows[0] if moa_rows else {}
        known.append(
            {
                "drug": drug.get("name"),
                "type": drug.get("drugType"),
                "mechanism": first.get("mechanismOfAction"),
                "action_type": first.get("actionType"),
                "phase": pretty_stage(row.get("maxClinicalStage")),
                "rank": stage_rank(row.get("maxClinicalStage")),
                "target": first.get("targetName"),
            }
        )

    # Score each drug against the disease's top associated targets. Many drugs
    # trialled in a disease treat its complications rather than the disease
    # itself (antibiotics in cystic fibrosis), and those should not be presented
    # as the disease's mechanism.
    def _words(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2}

    # Exact symbols (CFTR) and the word sets of each target's full name. A
    # mechanism string usually spells the target out ("cystic fibrosis
    # transmembrane conductance regulator"), so a symbol match alone never
    # fires; word overlap against the full name catches it.
    symbols: set[str] = set()
    name_words: list[set[str]] = []
    for r in targets[:5]:
        t = r.get("target") or {}
        if t.get("approvedSymbol"):
            symbols.add(t["approvedSymbol"].lower())
        if t.get("approvedName"):
            ws = _words(t["approvedName"])
            if ws:
                name_words.append(ws)

    for entry in known:
        blob = f"{entry.get('mechanism') or ''} {entry.get('target') or ''}"
        tokens = _words(blob)
        hit = any(sym in tokens for sym in symbols)
        if not hit:
            for ws in name_words:
                if len(ws & tokens) / len(ws) >= 0.6:
                    hit = True
                    break
        entry["on_target"] = hit

    # Most advanced first; within a stage, drugs acting on the disease's own
    # targets ahead of those treating its complications.
    known.sort(key=lambda d: (d["rank"], not d["on_target"], d["drug"] or ""))

    return {
        "id": disease.get("id"),
        "name": disease.get("name"),
        "description": disease.get("description"),
        "therapeutic_areas": [t.get("name") for t in (disease.get("therapeuticAreas") or [])],
        "known_drugs": known,
        "top_targets": [
            {
                "symbol": (r.get("target") or {}).get("approvedSymbol"),
                "name": (r.get("target") or {}).get("approvedName"),
                "score": round(r.get("score") or 0, 3),
            }
            for r in targets
        ],
        "url": f"https://platform.opentargets.org/disease/{disease.get('id')}" if disease.get("id") else None,
    }
