"""Compose field values from aggregated evidence.

Rule enforced here: a FILLED or BENCHMARK field with no supporting record is
demoted to a gap with the reason "no public record found", rather than drafted.
"""
from __future__ import annotations

from typing import Any

from . import aggregate, fields
from .fields import BENCHMARK, FILLED, GAP


NO_APPROVED = ("No therapy is approved in this indication, so there is no "
               "comparator to draft from. This is the whitespace, not a data gap.")


def _name(lab: dict) -> str:
    return lab.get("brand_name") or lab.get("generic_name") or lab.get("ot_drug") or "unnamed product"


def _entry(f: fields.Field, text: Any, citations: list[dict], band: str | None = None) -> dict:
    return {
        "key": f.key,
        "label": f.label,
        "section": f.section,
        "band": band or f.band,
        "sources": list(f.sources),
        "note": f.note,
        "value": text,
        "citations": citations,
    }


def _demote(f: fields.Field, reason: str) -> dict:
    return _entry(f, None, [], band=GAP) | {"note": reason}


def build(ctx: dict) -> list[dict]:
    """ctx carries: disease, studies, labels, ot (Open Targets detail), refs, orphan."""
    studies = ctx["studies"]
    labels = ctx["labels"]
    ot = ctx.get("ot") or {}
    out: list[dict] = []

    for f in fields.FIELDS:
        if f.band == GAP:
            out.append(_entry(f, None, []))
            continue

        if f.key == "indication":
            name = ot.get("name") or ctx["disease"]
            cite = [{"name": name, "url": ot.get("url")}] if ot.get("url") else []
            out.append(_entry(f, f"{name} ({ot.get('id', 'term not resolved')})", cite))

        elif f.key == "population":
            ev = aggregate.summarise_population(studies)
            if not ev.supported:
                out.append(_demote(f, "No registered trials found for this indication."))
                continue
            v = ev.value
            parts = []
            if v["age_bounds"]:
                parts.append("Age " + ", ".join(f"{a} ({n} trials)" for a, n in v["age_bounds"]))
            if v["sex"]:
                parts.append("Sex: " + ", ".join(f"{s.lower()} ({n})" for s, n in v["sex"]))
            if v["recurring_criteria"]:
                parts.append("Recurring criteria: " + "; ".join(v["recurring_criteria"][:4]))
            out.append(_entry(f, " · ".join(parts), ev.citations))

        elif f.key == "route":
            ev = aggregate.routes(studies, labels)
            if not ev.supported:
                out.append(_demote(f, NO_APPROVED if not ctx.get("has_approved") else "Labels found, but none state this."))
                continue
            out.append(_entry(f, ", ".join(f"{r.lower()} ({n})" for r, n in ev.value), ev.citations))

        elif f.key == "strengths":
            found = []
            for lab in labels[:4]:
                strengths = ctx.get("strengths", {}).get(lab.get("generic_name") or "", [])
                if strengths:
                    found.append((_name(lab), "; ".join(strengths[:4]), lab.get("url")))
            if not found:
                out.append(_demote(f, NO_APPROVED if not ctx.get("has_approved") else "No marketed strengths found in the NDC directory."))
                continue
            out.append(_entry(f, " · ".join(f"{n}: {v}" for n, v, _ in found),
                              [{"name": n, "url": u} for n, _, u in found]))

        elif f.key == "formulation":
            found = []
            for lab in labels[:4]:
                form = lab.get("dosage_form")
                if not form:
                    forms = ctx.get("dosage_forms", {}).get(lab.get("generic_name") or "", [])
                    form = "; ".join(forms[:3]) if forms else None
                if form:
                    found.append((_name(lab), form, lab.get("url")))
            if not found:
                out.append(_demote(f, NO_APPROVED if not ctx.get("has_approved") else "Labels found, but none state a dosage form."))
                continue
            out.append(_entry(f, " · ".join(f"{n}: {v}" for n, v, _ in found),
                              [{"name": n, "url": u} for n, _, u in found]))

        elif f.key == "regimen":
            key_map = {"regimen": "dosage"}
            vals = [(_name(l), l.get(key_map[f.key]), l.get("url"))
                    for l in labels if l.get(key_map[f.key])]
            if not vals:
                out.append(_demote(f, NO_APPROVED if not ctx.get("has_approved") else "Labels found, but none state this."))
                continue
            text = " · ".join(f"{n}: {str(v)}" for n, v, _ in vals[:3])
            out.append(_entry(f, text, [{"name": n, "url": u} for n, _, u in vals[:4]]))

        elif f.key in ("primary_endpoint", "secondary_endpoints"):
            which = "primary_outcomes" if f.key == "primary_endpoint" else "secondary_outcomes"
            ev = aggregate.rank_endpoints(studies, which, efficacy_only=True)
            if not ev.supported:
                ev = aggregate.rank_endpoints(studies, which)
            if not ev.supported:
                out.append(_demote(f, "No registered trials reported this outcome type."))
                continue
            text = "; ".join(f"{r['endpoint'][:120]} ({r['trials']} trials)" for r in ev.value[:5])
            out.append(_entry(f, text, ev.citations[:5]))

        elif f.key == "moa":
            drugs = ctx.get("drugs") or []
            targets = ot.get("top_targets", [])
            # Drugs arrive ranked by clinical stage. An approved therapy's
            # mechanism describes this disease; a phase 1 candidate's may not.
            on_target = [d for d in drugs if d.get("mechanism") and d.get("on_target")
                         and d.get("rank", 9) <= 2]
            advanced = [d for d in drugs if d.get("mechanism") and d.get("rank", 9) <= 2]
            pool = on_target or advanced or [d for d in drugs if d.get("mechanism")]
            if not pool and not targets:
                out.append(_demote(f, "No mechanism data in Open Targets for this term."))
                continue
            seen, lines = set(), []
            for d in pool:
                m = d["mechanism"]
                if m in seen:
                    continue
                seen.add(m)
                stage = f", {d['phase']}" if d.get("phase") else ""
                lines.append(f"{m} ({d['drug']}{stage})")
                if len(lines) == 4:
                    break
            if targets:
                lines.append("Top associated targets: " +
                             ", ".join(f"{t['symbol']} ({t['score']})" for t in targets[:5] if t.get("symbol")))
            cites = ([{"name": ot.get("name"), "url": ot.get("url")}] if ot.get("url") else []) + \
                    [{"name": r["title"][:70], "url": r["url"]} for r in ctx.get("refs", [])[:4]]
            out.append(_entry(f, " · ".join(lines), cites))

        elif f.key == "soc":
            drugs = ctx.get("drugs") or []
            approved = [d["drug"] for d in drugs if d.get("rank", 9) <= 1 and d.get("drug")]
            late = [s for s in studies if any(p in ("PHASE3", "PHASE4") for p in s.get("phases") or [])]
            if not approved and not late:
                out.append(_demote(f, "No approved drugs or late-phase trials found."))
                continue
            text = (f"{len(approved)} approved: " + ", ".join(approved[:8])
                    if approved else "No approved drug recorded for this indication.")
            if len(approved) > 8:
                text += f" (+{len(approved) - 8} more)"
            text += f" · {len(late)} trials in phase 3 or 4."
            out.append(_entry(f, text, [{"name": _name(l), "url": l.get("url")} for l in labels[:5]]))

        elif f.key == "orphan":
            orphan = ctx.get("orphan")
            if orphan is None:
                out.append(_demote(f, "Orphan designation export not loaded; see README."))
                continue
            text = (f"{len(orphan)} existing designation(s) matching this indication."
                    if orphan else "No existing orphan designation found for this indication.")
            out.append(_entry(f, text, [{"name": "FDA OOPD",
                                         "url": "https://www.accessdata.fda.gov/scripts/opdlisting/oopd/"}]))

        elif f.key == "efficacy_threshold":
            ev = aggregate.rank_endpoints(studies, "primary_outcomes", efficacy_only=True)
            if not ev.supported:
                out.append(_demote(
                    f, "Registered trials report only safety endpoints, so there is no "
                       "efficacy measure to benchmark against yet."))
                continue
            top_ep = ev.value[0]["endpoint"]
            if ctx.get("has_approved"):
                text = (f"Most-used efficacy endpoint across registered trials: {top_ep[:140]}. "
                        "Set your own threshold against what approved therapy achieves on it.")
            else:
                # Nothing is approved, so there is no performance to beat. The
                # endpoint still tells you what regulators and sponsors measure.
                text = (f"Most-used efficacy endpoint across registered trials: {top_ep[:140]}. "
                        "No therapy is approved here, so there is no benchmark to beat — "
                        "this is the measure your candidate will be judged on, and any "
                        "clinically meaningful effect is the bar.")
            entry = _entry(f, text, ev.citations[:3])
            if not ctx.get("has_approved"):
                # The field's standing note assumes an approved comparator exists.
                entry["note"] = ("No approved therapy exists in this indication, so "
                                 "this is the measure, not a performance to beat.")
            out.append(entry)

        elif f.key in ("contraindications", "warnings", "safety_profile"):
            ev = aggregate.safety_benchmark(labels)
            if not ev.supported:
                out.append(_demote(f, NO_APPROVED if not ctx.get("has_approved") else "Labels found, but none state this."))
                continue
            key = {"contraindications": "contraindications", "warnings": "warnings",
                   "safety_profile": "warnings"}[f.key]
            text = " · ".join(f"{i['drug']}: {i[key]}" for i in ev.value[:2] if i.get(key))
            out.append(_entry(f, text or None, ev.citations))

        elif f.key == "interactions":
            vals = [(_name(l), l.get("interactions"), l.get("url"))
                    for l in labels if l.get("interactions")]
            if not vals:
                out.append(_demote(f, NO_APPROVED if not ctx.get("has_approved") else "No interaction text in the labels found."))
                continue
            out.append(_entry(f, " · ".join(f"{n}: {v}" for n, v, _ in vals[:2]),
                              [{"name": n, "url": u} for n, _, u in vals[:2]]))

    return out
