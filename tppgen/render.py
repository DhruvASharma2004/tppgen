"""Render the draft as one self-contained HTML page."""
from __future__ import annotations

import html
import json
from datetime import date

from . import fields

BAND_LABEL = {
    "filled": "Drafted from public data",
    "benchmark": "Benchmark — current therapy",
    "gap": "Gap — you must supply this",
}

CSS = """
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Helvetica,sans-serif;
     color:#15181d;background:#f6f7f9}
.wrap{max-width:860px;margin:0 auto;padding:48px 24px 96px}
h1{font-size:30px;line-height:1.25;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:#5c6470;margin:0 0 28px;font-size:15px}
.ratio{display:flex;gap:8px;margin:0 0 36px;flex-wrap:wrap}
.pill{font-size:12.5px;padding:5px 11px;border-radius:999px;border:1px solid;font-weight:500}
.pill.filled{color:#15603a;border-color:#a9d9bf;background:#eaf7f0}
.pill.benchmark{color:#8a5a04;border-color:#f0d29a;background:#fdf6e7}
.pill.gap{color:#6b7280;border-color:#d7dbe0;background:#f0f2f4}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.07em;color:#6b7280;
   margin:40px 0 12px;font-weight:600}
.field{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:16px 18px;margin:0 0 10px}
.field.gap{background:#fbfcfd;border-style:dashed}
.flabel{font-weight:600;font-size:15px;margin:0 0 4px;display:flex;justify-content:space-between;
        align-items:baseline;gap:12px}
.band{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap}
.band.filled{color:#15603a}.band.benchmark{color:#8a5a04}.band.gap{color:#9aa1ab}
.val{margin:0;font-size:14.5px;color:#262b33;word-break:break-word}
.note{margin:6px 0 0;font-size:13px;color:#6b7280;font-style:italic}
.cites{margin:8px 0 0;font-size:12.5px;color:#6b7280}
.cites a{color:#2a5db0;text-decoration:none;margin-right:10px}
.cites a:hover{text-decoration:underline}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;
      border-radius:10px;overflow:hidden;font-size:13.5px}
th{text-align:left;background:#f0f2f5;padding:9px 12px;font-size:12px;text-transform:uppercase;
   letter-spacing:.05em;color:#5c6470}
td{padding:9px 12px;border-top:1px solid #eef0f3;vertical-align:top}
td a{color:#2a5db0;text-decoration:none}
.limits{margin-top:44px;padding:20px 22px;background:#fff;border:1px solid #e3e6ea;border-radius:10px}
.limits h3{margin:0 0 10px;font-size:14px}
.limits li{font-size:13.5px;color:#434a55;margin-bottom:6px}
footer{margin-top:36px;font-size:12.5px;color:#8a919b}
"""

LIMITS = [
    "This tool drafts; it does not decide. Every drafted field is a starting point to revise.",
    "Seven fields cannot be filled from public data at all. They are named rather than invented.",
    "Public data skews toward success: registries and labels over-represent trials that read out "
    "well and drugs that were approved. A benchmark built only on those sets the bar in the wrong place.",
    "Registry data is self-reported and sometimes stale; endpoint wording is inconsistent across sponsors.",
    "No proprietary, internal or confidential data is used. Public APIs only.",
]


def _esc(x) -> str:
    return html.escape(str(x)) if x is not None else ""


def _field_html(f: dict) -> str:
    cites = "".join(
        f'<a href="{_esc(c.get("url"))}" target="_blank" rel="noopener">{_esc(c.get("name") or c.get("nct_id") or "source")}</a>'
        for c in f.get("citations", []) if c.get("url")
    )
    body = f'<p class="val">{_esc(f["value"])}</p>' if f.get("value") else ""
    note = f'<p class="note">{_esc(f["note"])}</p>' if f.get("note") else ""
    return f"""<div class="field {f['band']}">
  <p class="flabel"><span>{_esc(f['label'])}</span><span class="band {f['band']}">{BAND_LABEL[f['band']]}</span></p>
  {body}{note}
  {f'<p class="cites">{cites}</p>' if cites else ''}
</div>"""


def _table_html(rows: list[dict], limit: int = 40) -> str:
    head = "<tr><th>Type</th><th>Name</th><th>Sponsor</th><th>Stage</th><th>Status / mechanism</th></tr>"
    body = ""
    for r in rows[:limit]:
        name = _esc(r.get("name"))
        if r.get("url"):
            name = f'<a href="{_esc(r["url"])}" target="_blank" rel="noopener">{name}</a>'
        body += (f"<tr><td>{_esc(r.get('kind'))}</td><td>{name}</td>"
                 f"<td>{_esc(r.get('sponsor'))}</td><td>{_esc(r.get('phase'))}</td>"
                 f"<td>{_esc(r.get('status'))}</td></tr>")
    more = f"<footer>Showing {min(limit, len(rows))} of {len(rows)} records.</footer>" if len(rows) > limit else ""
    return f"<table>{head}{body}</table>{more}"


def render(disease: str, drafted: list[dict], competitors: list[dict]) -> str:
    counts = {b: sum(1 for f in drafted if f["band"] == b) for b in ("filled", "benchmark", "gap")}
    sections = ""
    for section in fields.SECTIONS:
        items = [f for f in drafted if f["section"] == section]
        if not items:
            continue
        sections += f"<h2>{_esc(section)}</h2>" + "".join(_field_html(f) for f in items)

    limits = "".join(f"<li>{_esc(x)}</li>" for x in LIMITS)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Draft TPP — {_esc(disease)}</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>Draft Target Product Profile</h1>
<p class="sub">{_esc(disease)} · generated {date.today().isoformat()} from public sources</p>
<div class="ratio">
  <span class="pill filled">{counts['filled']} drafted</span>
  <span class="pill benchmark">{counts['benchmark']} benchmarked</span>
  <span class="pill gap">{counts['gap']} gaps</span>
</div>
{sections}
<h2>Competitive landscape</h2>
{_table_html(competitors)}
<div class="limits"><h3>What this draft is not</h3><ul>{limits}</ul></div>
<footer>Sources: ClinicalTrials.gov · openFDA · Open Targets · PubMed · FDA OOPD.
Generated by tppgen. Not medical, regulatory or investment advice.</footer>
</div></body></html>"""
