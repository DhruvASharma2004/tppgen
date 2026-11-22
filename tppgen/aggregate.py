"""Turn raw records into the evidence each TPP field needs.

Every value carries the records it came from. A field with no supporting record
is returned as None and rendered as a gap, never filled with a plausible guess.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field as dc_field
from typing import Any

PHASE_ORDER = ["PHASE1", "PHASE2", "PHASE3", "PHASE4", "EARLY_PHASE1", "NA"]


@dataclass
class Evidence:
    """A drafted value plus the records behind it."""
    value: Any
    citations: list[dict] = dc_field(default_factory=list)
    n: int = 0

    @property
    def supported(self) -> bool:
        return self.value is not None and self.n > 0


def _norm_endpoint(text: str) -> str:
    """Sponsors write the same endpoint many ways. Normalise before counting."""
    t = text.lower().strip()
    t = re.sub(r"\[[^\]]*\]", " ", t)           # drop "[Time Frame: ...]" fragments
    t = re.sub(r"\b(change|changes) (from|in) baseline (in|of)?\b", "change in ", t)
    t = re.sub(r"\bnumber of (participants|patients|subjects) with\b", "incidence of ", t)
    t = re.sub(r"\b(participants|patients|subjects)\b", "", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


SAFETY_PATTERNS = re.compile(
    r"adverse event|^safety\b|safety and tolerab|tolerability|toxicit|"
    r"dose[- ]limiting|\bdlts?\b|\bteaes?\b|\baes?\b|serious adverse|side effect|"
    r"treatment[- ]emergent",
    re.I,
)


OPERATIONAL_PATTERNS = re.compile(
    r"informed consent|study visit|enroll|recruit|retention|feasibilit|attendance|"
    r"protocol (adherence|compliance|deviation)|questionnaire completion|"
    r"number of (subjects|participants) (who |that )?(provided|completed|attended)",
    re.I,
)


def is_safety_endpoint(text: str) -> bool:
    """Safety and tolerability outcomes are not efficacy measures.

    Early-phase trials dominate rare-disease registries, and their primary
    outcome is almost always an adverse-event count. Ranking those as the
    disease's primary endpoint puts a safety measure in the efficacy section.
    """
    return bool(SAFETY_PATTERNS.search(text or ""))


def is_operational_endpoint(text: str) -> bool:
    """Trial-conduct measures: consent, visits attended, recruitment, feasibility.

    These say nothing about whether the drug works, but small rare-disease
    feasibility studies register them as primary outcomes.
    """
    return bool(OPERATIONAL_PATTERNS.search(text or ""))


def rank_endpoints(studies: list[dict], which: str = "primary_outcomes", top: int = 8,
                   efficacy_only: bool = False) -> Evidence:
    counter: Counter[str] = Counter()
    examples: dict[str, dict] = {}
    for s in studies:
        seen = set()
        for raw in s.get(which) or []:
            if efficacy_only and (is_safety_endpoint(raw) or is_operational_endpoint(raw)):
                continue
            norm = _norm_endpoint(raw)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            counter[norm] += 1
            examples.setdefault(norm, {"text": raw, "nct_id": s["nct_id"], "url": s["url"]})
    if not counter:
        return Evidence(None)
    ranked = [
        {"endpoint": examples[k]["text"], "trials": v, "example": examples[k]}
        for k, v in counter.most_common(top)
    ]
    return Evidence(ranked, [e["example"] for e in ranked], len(studies))


def summarise_population(studies: list[dict], top: int = 6) -> Evidence:
    """What the registered trials actually enrol: age bounds, sex, and common criteria."""
    ages, sexes, criteria = Counter(), Counter(), Counter()
    cited = []
    for s in studies:
        if s.get("min_age"):
            ages[f"≥ {s['min_age']}"] += 1
        if s.get("sex"):
            sexes[s["sex"]] += 1
        text = s.get("eligibility_text") or ""
        for line in text.splitlines():
            line = line.strip(" -•\t")
            if 20 < len(line) < 140 and not line.lower().startswith(("inclusion", "exclusion")):
                criteria[line] += 1
        if s.get("url"):
            cited.append({"nct_id": s["nct_id"], "url": s["url"]})
    if not studies:
        return Evidence(None)
    return Evidence(
        {
            "age_bounds": ages.most_common(3),
            "sex": sexes.most_common(3),
            "recurring_criteria": [c for c, n in criteria.most_common(top) if n > 1],
        },
        cited[:5],
        len(studies),
    )


def competitive_table(studies: list[dict], labels: list[dict], drugs: list[dict] | None = None) -> list[dict]:
    """Approved drugs and registered trials in one list, most advanced first.

    Approved drugs come from Open Targets (one row per molecule). Labels are
    joined on for the link; several manufacturers of one generic are one row,
    not twenty.
    """
    rows: list[dict] = []
    label_by_drug = {
        (l.get("ot_drug") or "").lower(): l for l in labels if l.get("ot_drug")
    }
    for d in drugs or []:
        if not d.get("drug"):
            continue
        lab = label_by_drug.get(d["drug"].lower(), {})
        rows.append({
            "kind": "Approved" if d.get("rank", 9) <= 1 else "Candidate",
            "name": d["drug"],
            "sponsor": lab.get("manufacturer"),
            "phase": d.get("phase") or "Unknown",
            "status": d.get("mechanism") or "",
            "route": lab.get("route"),
            "url": lab.get("url"),
            "_rank": d.get("rank", 9),
        })

    for s in studies:
        names = ", ".join(i["name"] for i in s.get("interventions", []) if i.get("name"))
        phases = s.get("phases") or []
        rows.append({
            "kind": "Trial",
            "name": names or s.get("title"),
            "sponsor": s.get("sponsor"),
            "phase": ", ".join(phases) or "NA",
            "status": s.get("status"),
            "route": None,
            "url": s.get("url"),
            "_rank": 5 + min((["PHASE4", "PHASE3", "PHASE2", "PHASE1"].index(p)
                              for p in phases if p in ("PHASE4", "PHASE3", "PHASE2", "PHASE1")),
                             default=4),
        })

    rows = [r for r in rows if r.get("name")]
    rows.sort(key=lambda r: (r["_rank"], r["name"]))
    for r in rows:
        r.pop("_rank", None)
    return rows


def routes(studies: list[dict], labels: list[dict]) -> Evidence:
    counter = Counter(l["route"] for l in labels if l.get("route"))
    cites = [{"name": l.get("brand_name"), "url": l.get("url")} for l in labels if l.get("route")]
    if not counter:
        return Evidence(None)
    return Evidence(counter.most_common(5), cites[:5], sum(counter.values()))


def safety_benchmark(labels: list[dict], top: int = 5) -> Evidence:
    """Contraindications and warnings as the approved comparators state them."""
    items = []
    for lab in labels[:top]:
        if not (lab.get("contraindications") or lab.get("warnings")):
            continue
        items.append({
            "drug": lab.get("brand_name") or lab.get("generic_name"),
            "contraindications": (lab.get("contraindications") or "")[:600],
            "warnings": (lab.get("warnings") or "")[:600],
            "url": lab.get("url"),
        })
    if not items:
        return Evidence(None)
    return Evidence(items, [{"name": i["drug"], "url": i["url"]} for i in items], len(items))
