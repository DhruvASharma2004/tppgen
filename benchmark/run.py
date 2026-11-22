"""Run tppgen across the benchmark indications.

    python benchmark/run.py            # fill missing IDs, then build every indication 3 times
    python benchmark/run.py --runs 1   # one run each

Outputs go to benchmark/outputs/<indication>_run<N>.html.
An empty efo_id in indications.csv is filled from the first Open Targets search hit.
Check those IDs by hand before scoring.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from tppgen.clients import opentargets  # noqa: E402


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    path = HERE / "indications.csv"
    rows = list(csv.DictReader(path.open()))

    for row in rows:
        if not row["efo_id"]:
            hits = opentargets.search_disease(row["search_term"])
            row["efo_id"] = hits[0]["id"] if hits else ""
            print(f"{row['indication']}: {row['efo_id'] or 'NOT FOUND'}"
                  f"{' (' + hits[0]['name'] + ')' if hits else ''}")
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    out_dir = HERE / "outputs"
    out_dir.mkdir(exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip() or "unknown"
    log = (out_dir / "runlog.txt").open("a")

    for row in rows:
        if not row["efo_id"]:
            continue
        for n in range(1, args.runs + 1):
            out = out_dir / f"{slug(row['indication'])}_run{n}.html"
            print(f"\n== {row['indication']} run {n}")
            rc = subprocess.run([sys.executable, "-m", "tppgen", "build", row["efo_id"],
                                 "--out", str(out)], cwd=ROOT).returncode
            log.write(f"{date.today()}\t{commit}\t{row['indication']}\t{row['efo_id']}\t"
                      f"run{n}\trc={rc}\n")
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
