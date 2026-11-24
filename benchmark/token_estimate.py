"""Estimate input tokens per FDA label for the Claude endpoint-extraction plan.

Reads labels already in ~/.tppgen_cache/openfda (from benchmark runs) and
measures the text the extractor would send: Indications (1) plus Clinical
Studies (14). Tokens are estimated at 3.5 characters per token, a slightly
conservative rate for English technical text; the budget used 30,000.

Usage: python benchmark/token_estimate.py
"""
import json
import statistics
from pathlib import Path

CACHE = Path.home() / ".tppgen_cache" / "openfda"
CHARS_PER_TOKEN = 3.5
PROMPT_OVERHEAD = 1500  # instructions and output schema, per call
BUDGET_PER_CALL = 30000

seen, sizes = set(), []
for f in CACHE.glob("*.json"):
    try:
        recs = json.loads(f.read_text())
    except Exception:
        continue
    for r in recs if isinstance(recs, list) else []:
        if not isinstance(r, dict) or "clinical_studies" not in r:
            continue
        key = r.get("set_id") or r.get("id")
        if key in seen:
            continue
        seen.add(key)
        name = ((r.get("openfda") or {}).get("brand_name") or ["?"])[0]
        text = " ".join((r.get("indications_and_usage") or []) + (r.get("clinical_studies") or []))
        sizes.append((round(len(text) / CHARS_PER_TOKEN) + PROMPT_OVERHEAD, name))

if not sizes:
    raise SystemExit("No cached labels with Section 14 found. Run the benchmark first.")
toks = sorted(t for t, _ in sizes)
print(f"labels with Section 14: {len(toks)}")
print(f"input tokens per call: median {statistics.median(toks):,.0f}, "
      f"mean {statistics.mean(toks):,.0f}, 90th pct {toks[int(0.9 * (len(toks) - 1))]:,}, max {toks[-1]:,}")
print("largest:", ", ".join(f"{n} {t:,}" for t, n in sorted(sizes, reverse=True)[:5]))
print(f"budget assumed {BUDGET_PER_CALL:,} per call: "
      f"{'covers' if toks[int(0.9 * (len(toks) - 1))] <= BUDGET_PER_CALL else 'BELOW'} the 90th percentile")
