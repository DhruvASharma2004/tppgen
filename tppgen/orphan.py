"""FDA orphan designations.

The OOPD database has no public API; it exports to Excel/CSV from
https://www.accessdata.fda.gov/scripts/opdlisting/oopd/ (search with no criteria
returns everything). Drop that export at ~/.tppgen_cache/orphan.csv and this
module matches against it. Absent, the orphan field is reported as a gap.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

PATH = Path.home() / ".tppgen_cache" / "orphan.csv"


def lookup(term: str) -> list[dict] | None:
    if not PATH.exists():
        return None
    words = [w for w in re.findall(r"[a-z]+", term.lower()) if len(w) > 3]
    if not words:
        return []
    hits = []
    with PATH.open(newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            blob = " ".join(str(v or "") for v in row.values()).lower()
            if all(w in blob for w in words):
                hits.append(row)
    return hits
