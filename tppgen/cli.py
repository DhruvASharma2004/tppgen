"""Command line entry point.

  python -m tppgen search "myotonic dystrophy"
  python -m tppgen build EFO_0004956 --out dm1.html
"""
from __future__ import annotations

import argparse
import re
import sys
import webbrowser
from pathlib import Path

from . import aggregate, draft, orphan, render
from .clients import clinicaltrials, openfda, opentargets, pubmed
from .clients._http import ApiError


def cmd_search(args) -> int:
    try:
        hits = opentargets.search_disease(args.term)
    except ApiError as exc:
        print(f"Could not reach Open Targets: {exc}", file=sys.stderr)
        return 1
    if not hits:
        print("No matching disease term. Try a different wording.")
        return 1
    print(f"Candidate terms for {args.term!r}:\n")
    for h in hits:
        print(f"  {h['id']:<16} {h['name']}")
        if h["description"]:
            print(f"  {'':<16} {h['description'][:90]}")
    print("\nRun:  python -m tppgen build <ID>")
    return 0


GENERIC_WORDS = {"disease", "type", "syndrome", "disorder", "deficiency", "the", "and",
                 "with", "hereditary", "familial", "congenital", "of"}


def _disease_terms(name: str, studies: list[dict], top: int = 5) -> list[set[str]]:
    """The disease name plus the condition names trials most often use for it.

    Ontology names differ from label wording ("glycogen storage disease II" vs
    "Pompe disease"), so trial condition lists supply the common synonyms.
    """
    from collections import Counter
    counts = Counter()
    for s in studies:
        for c in s.get("conditions") or []:
            counts[c.lower().strip()] += 1
    names = [name.lower()] + [c for c, _ in counts.most_common(top)]
    terms = []
    for n in names:
        words = {w for w in re.findall(r"[a-z0-9]+", n) if len(w) > 2 and w not in GENERIC_WORDS}
        if words and words not in terms:
            terms.append(words)
    return terms


def _label_is_for(lab: dict, terms: list[set[str]]) -> bool:
    """Keep a label only if its indication names this disease.

    Open Targets marks a drug approved if it is approved anywhere for a related
    term, which brings in a Gaucher product for Pompe or a urea-cycle drug for SMA.
    """
    text = (lab.get("indications") or "").lower()
    if not text:
        return False
    found = set(re.findall(r"[a-z0-9]+", text))
    return any(t <= found for t in terms)


def cmd_build(args) -> int:
    print(f"Resolving {args.efo_id} ...")
    try:
        ot = opentargets.disease_detail(args.efo_id)
    except ApiError as exc:
        print(f"Could not reach Open Targets: {exc}", file=sys.stderr)
        return 1
    if not ot.get("name"):
        print(f"No disease found for {args.efo_id}. Run 'search' first.", file=sys.stderr)
        return 1
    name = ot["name"]
    print(f"  -> {name}")

    print("Fetching registered trials ...")
    try:
        studies = list(clinicaltrials.studies(name, args.max_studies))
    except ApiError as exc:
        print(f"ClinicalTrials.gov unavailable: {exc}", file=sys.stderr)
        studies = []
    print(f"  -> {len(studies)} interventional studies")

    drugs = ot.get("known_drugs") or []
    approved = [d for d in drugs if d["rank"] <= 1]
    on_target = [d for d in approved if d.get("on_target")]
    print(f"  -> {len(drugs)} drugs/candidates in Open Targets; "
          f"{len(approved)} approved, {len(on_target)} acting on the disease's own targets")

    labels: list[dict] = []
    strengths: dict[str, list[str]] = {}
    dosage_forms: dict[str, list[str]] = {}

    # Labels are only looked up for drugs APPROVED IN THIS INDICATION. A phase 2
    # candidate often has an approved label for some other disease (a diabetes
    # combination trialled in myotonic dystrophy), and presenting that label as a
    # comparator for this disease is worse than presenting nothing.
    disease_terms = _disease_terms(name, studies)
    if approved:
        print("Fetching labels for approved therapies ...")
        for d in approved[:args.max_labels]:
            raw = openfda.label_for_drug(d["drug"])
            if not raw:
                continue
            lab = openfda.parse_label(raw)
            if not _label_is_for(lab, disease_terms):
                print(f"     skip {lab.get('brand_name') or d['drug']}: label indication "
                      f"does not name this disease")
                continue
            lab["ot_drug"] = d["drug"]
            lab["ot_phase"] = d["phase"]
            labels.append(lab)
            gn = lab.get("generic_name")
            if gn and gn not in strengths:
                strengths[gn] = openfda.strengths_for_product(gn)
                if not lab.get("dosage_form"):
                    dosage_forms[gn] = openfda.dosage_forms_for_product(gn)
        print(f"  -> {len(labels)} labels matched")
    else:
        print("  -> no approved therapy in this indication; comparator fields "
              "will be reported as gaps")

    print("Fetching mechanism references ...")
    top_target = (ot.get("top_targets") or [{}])[0].get("symbol")
    try:
        refs = pubmed.mechanism_references(name, top_target)
    except ApiError:
        refs = []
    print(f"  -> {len(refs)} references")

    orphan_hits = orphan.lookup(name)
    print(f"  -> orphan designations: "
          f"{'not loaded' if orphan_hits is None else len(orphan_hits)}")

    ctx = {"disease": name, "studies": studies, "labels": labels, "drugs": drugs,
           "ot": ot, "refs": refs, "orphan": orphan_hits,
           "strengths": strengths, "dosage_forms": dosage_forms,
           "has_approved": bool(approved)}
    drafted = draft.build(ctx)
    competitors = aggregate.competitive_table(studies, labels, drugs)

    bands = {b: sum(1 for f in drafted if f["band"] == b) for b in ("filled", "benchmark", "gap")}
    out = Path(args.out or f"tpp-{args.efo_id}.html")
    out.write_text(render.render(name, drafted, competitors), encoding="utf-8")
    print(f"\n{bands['filled']} drafted · {bands['benchmark']} benchmarked · {bands['gap']} gaps")
    print(f"Written to {out.resolve()}")
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="tppgen", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="find the ontology term for a disease")
    s.add_argument("term")
    s.set_defaults(func=cmd_search)

    b = sub.add_parser("build", help="build a draft TPP for a confirmed term")
    b.add_argument("efo_id", help="EFO or MONDO id from 'search', e.g. EFO_0004956")
    b.add_argument("--out", help="output HTML path")
    b.add_argument("--max-studies", type=int, default=300)
    b.add_argument("--max-labels", type=int, default=12,
                   help="how many Open Targets drugs to look up labels for")
    b.add_argument("--open", action="store_true", help="open the page when done")
    b.set_defaults(func=cmd_build)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
