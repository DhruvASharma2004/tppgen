"""The field map from the spec, as data.

Band decides what the generator is allowed to do with a field:
  FILLED    - drafted from public records, always with a citation
  BENCHMARK - what current therapy achieves, so the user can set their own bar
  GAP       - named and left empty; public data cannot supply it
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

FILLED, BENCHMARK, GAP = "filled", "benchmark", "gap"


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    section: str
    band: str
    sources: tuple[str, ...] = ()
    note: str = ""


FIELDS: list[Field] = [
    Field("indication", "Target indication", "Indications and usage", FILLED,
          ("Open Targets", "ClinicalTrials.gov")),
    Field("population", "Target population", "Indications and usage", FILLED,
          ("ClinicalTrials.gov",), "Derived from trial eligibility criteria across the indication."),
    Field("route", "Route of administration", "Dosage and administration", FILLED,
          ("ClinicalTrials.gov", "openFDA"), "Routes competitors use, not a proposed route."),
    Field("regimen", "Dosing regimen", "Dosage and administration", FILLED,
          ("openFDA",), "Comparator regimens."),
    Field("formulation", "Formulation", "Dosage forms and strengths", FILLED,
          ("openFDA",), "Approved comparators only."),
    Field("strengths", "Strengths", "Dosage forms and strengths", FILLED,
          ("openFDA",), "Approved comparators only."),
    Field("primary_endpoint", "Primary endpoint", "Efficacy", FILLED,
          ("ClinicalTrials.gov",), "Ranked by frequency across registered trials."),
    Field("secondary_endpoints", "Secondary endpoints", "Efficacy", FILLED,
          ("ClinicalTrials.gov",)),
    Field("moa", "Mechanism of action", "Clinical pharmacology", FILLED,
          ("Open Targets", "PubMed")),
    Field("soc", "Standard of care", "Commercial context", FILLED,
          ("openFDA", "ClinicalTrials.gov")),
    Field("orphan", "Orphan designation status", "Regulatory", FILLED,
          ("FDA OOPD",)),

    Field("efficacy_threshold", "Efficacy threshold", "Efficacy", BENCHMARK,
          ("ClinicalTrials.gov",),
          "Shows what current therapy achieves. Your own go/no-go bar is yours to set."),
    Field("safety_profile", "Safety profile", "Safety and tolerability", BENCHMARK,
          ("openFDA", "FAERS"), "Comparator adverse-event profile."),
    Field("contraindications", "Contraindications", "Safety and tolerability", BENCHMARK,
          ("openFDA",), "Class effects are visible; findings specific to a new drug are not."),
    Field("warnings", "Warnings and precautions", "Safety and tolerability", BENCHMARK,
          ("openFDA",)),
    Field("interactions", "Drug interactions", "Clinical pharmacology", BENCHMARK,
          ("openFDA",), "Known class interactions only."),

    Field("pkpd", "PK/PD targets", "Clinical pharmacology", GAP, (),
          "Comparator data is public; your own targets are not."),
    Field("special_populations", "Use in special populations", "Special populations", GAP, (),
          "A strategic decision about which trials to run, not a fact to look up."),
    Field("preclinical", "Preclinical safety margins", "Nonclinical toxicology", GAP, (),
          "Proprietary."),
    Field("cqa", "Critical quality attributes", "Product quality", GAP, (),
          "Proprietary manufacturing specification."),
    Field("stability", "Storage and shelf life", "Product quality", GAP, (),
          "Supply-chain strategy, set internally."),
    Field("differentiation", "Differentiation", "Commercial context", GAP, (),
          "Your own positioning argument against the standard of care above."),
    Field("pricing", "Pricing and market access", "Commercial context", GAP, (),
          "Confidential commercial data."),
]

BY_KEY = {f.key: f for f in FIELDS}
SECTIONS = list(dict.fromkeys(f.section for f in FIELDS))


def counts() -> dict[str, int]:
    out = {FILLED: 0, BENCHMARK: 0, GAP: 0}
    for f in FIELDS:
        out[f.band] += 1
    return out
