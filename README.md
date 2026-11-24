# tppgen

Drafts the public-data half of a Target Product Profile for a given indication, and
names the half that public data cannot supply.

A TPP has roughly 23 fields. Eleven can be drafted from public records, five can be
benchmarked against what current therapy achieves, and seven exist only inside a
developing company. `tppgen` fills the first sixteen with citations and prints the
last seven as named, empty gaps. It does not invent them.

## Benchmark

Scored against FDA labels, ClinicalTrials.gov and FDA orphan designations with a rubric committed before any run. **87% accuracy on 20 rare diseases the tool had never seen** (two held-out sets of 10, each committed before it was run: 89% and 85%). Every internal-only field was left blank in every run, and repeat runs were identical. Full method, every score and every failure: [`benchmark/REPORT.md`](benchmark/REPORT.md).

## Example

Lambert-Eaton myasthenic syndrome, from the held-out run (`benchmark/outputs_fourthset/`):

| Field | Drafted value | Source |
|---|---|---|
| Population | Firdapse: adults and pediatric patients 6 years and older | FDA label |
| Dosing | 15 mg to 30 mg daily in divided doses (adults) | FDA label |
| Primary endpoint | Change in QMG score and Subject Global Impression score | FDA label, Section 14 |
| Mechanism | Voltage-gated potassium channel blocker (amifampridine) | Open Targets |
| Safety benchmark | Seizures; hypersensitivity, including anaphylaxis | FDA label |
| Orphan designations | 5 existing | FDA OOPD |
| Pricing, differentiation, CQAs, ... | *Gap: internal data, not drafted* | — |

Each drafted field links to the record it came from.

## Install

```bash
git clone https://github.com/DhruvASharma2004/tppgen.git && cd tppgen
pip install -r requirements.txt
```

## Use

```bash
python -m tppgen search "myotonic dystrophy"     # resolve to an ontology term
python -m tppgen build EFO_0004956 --open        # draft the TPP for that term
```

Resolution is a separate step on purpose: a TPP built against the wrong ontology
term is worse than no TPP, so the term is confirmed before any data is pulled.

## How drugs are identified

Searching label full text for a disease name does not work. Any product whose
label merely mentions the disease matches, so for cystic fibrosis an antibiotic
and a vitamin K product outrank the CFTR modulators that actually treat it.

Instead the drug list comes from Open Targets (`drugAndClinicalCandidates`),
ranked by clinical stage, and each drug is then looked up in openFDA **by name**.
Drugs are then scored against the disease's own top targets, by word overlap
against the target's full name rather than its symbol alone — a mechanism string
spells the target out ("cystic fibrosis transmembrane conductance regulator"), so
matching on "CFTR" never fires. Drugs acting on the disease's own targets are
used first, which is the difference between a cystic fibrosis profile led by
CFTR modulators and one led by the antibiotics used for its lung infections.

## Data sources

| Source | Used for | Key | Licence |
| --- | --- | --- | --- |
| [ClinicalTrials.gov v2](https://clinicaltrials.gov/data-api/api) | Endpoints, populations, competitor trials | none | Public |
| [openFDA](https://open.fda.gov/apis/) | Labels, approvals, adverse events | optional | Public domain |
| [Open Targets](https://platform-docs.opentargets.org/data-access/graphql-api) | Term resolution, mechanism, known drugs | none | CC0 |
| [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/) | Mechanism references | optional | Public |
| [FDA OOPD](https://www.accessdata.fda.gov/scripts/opdlisting/oopd/) | Orphan designations | n/a | Public |

DrugBank and the hosted CLUE environment are deliberately **not** used: both require a
commercial agreement. Every source above is free of commercial restriction.

### Optional keys

```bash
export OPENFDA_API_KEY=...   # raises 1,000/day to 120,000/day
export NCBI_API_KEY=...      # raises 3/sec to 10/sec
```

### Orphan designations

The OOPD database has no API. Export the full list to CSV from the FDA search page and
save it at `~/.tppgen_cache/orphan.csv`. Without it, the orphan field reports as a gap.

## Status

Working end to end against all four live APIs, benchmarked on 40 rare diseases
(see Benchmark).

Three correctness rules the output depends on, each the result of a real failure
caught in testing:

1. **Comparators come only from drugs approved in the indication.** A phase 2
   candidate usually holds an approved label for some *other* disease. Drafting
   from those produced a diabetes combination as a comparator for myotonic
   dystrophy. When nothing is approved, every comparator field is a stated gap.
2. **Trials are filtered against their own condition list.** The registry's
   condition search is fuzzy enough that myotonic dystrophy returned oncology
   trials, making progression-free survival the disease's "primary endpoint".
3. **Safety and trial-conduct outcomes are excluded from the efficacy fields.**
   Early-phase trials dominate rare-disease registries, so adverse-event counts
   and visit-attendance measures would otherwise rank above the real endpoints.

Known rough edges: an approved drug is missed when Open Targets lists no drug
for the term or the product has no openFDA label (some gene therapies); where
no label states the primary endpoint, trial counts can still rank a biomarker
or operational measure first; the orphan export must be downloaded by hand.

## Caching

Responses are cached for a week under `~/.tppgen_cache/`. A repeated build costs no
API calls. Delete the directory to force a refresh.

## What this is not

- It drafts; it does not decide. Every drafted field is a starting point to revise.
- Public data skews toward success. Registries and labels over-represent trials that
  read out well and drugs that were approved, so a benchmark built only on those sets
  the bar in the wrong place.
- Registry data is self-reported and sometimes stale.
- No proprietary, internal or confidential data is used.
- Not medical, regulatory or investment advice.
