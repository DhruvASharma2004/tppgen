"""Turn benchmark HTML outputs into a scoring sheet.

Usage: python benchmark/extract.py thirdset > benchmark/scores_thirdset.csv
Gap fields with no value are pre-filled as "correctly omitted" only when the
indication's rubric says no public ground truth exists; every other row is
left blank for the scorer.
"""
import csv, html, re, sys
from pathlib import Path

HERE = Path(__file__).parent
GAP_FIELDS = {"Drug interactions", "PK/PD targets", "Differentiation", "Pricing and market access",
              "Use in special populations", "Preclinical safety margins", "Critical quality attributes",
              "Storage and shelf life"}
FIELD_RE = re.compile(
    r'<div class="field (\w+)">\s*<p class="flabel"><span>([^<]+)</span>.*?</p>'
    r'(?:\s*<p class="val">(.*?)</p>)?(.*?)</div>', re.S)


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def main(name):
    out_dir = HERE / ("outputs" if name == "indications" else f"outputs_{name}")
    w = csv.writer(sys.stdout)
    w.writerow(["indication", "run", "field", "band", "tppgen_value", "first_cite", "score",
                "ground_truth_source", "note"])
    for f in sorted(out_dir.glob("*_run*.html")):
        ind, run = f.stem.rsplit("_run", 1)
        page = f.read_text()
        for band, label, val, rest in FIELD_RE.findall(page):
            cite = re.search(r'<p class="cites"><a href="([^"]+)"', rest)
            value = text(val)
            score = "correctly omitted" if band == "gap" and label in GAP_FIELDS else ""
            w.writerow([ind.replace("_", " "), run, html.unescape(label), band, value,
                        cite.group(1).replace("&amp;", "&") if cite else "", score, "", ""])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "indications")
