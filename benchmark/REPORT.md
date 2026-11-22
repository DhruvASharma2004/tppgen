# tppgen benchmark — v1 report

**Date:** 22 November 2026 · **Tool version:** commit `94bae1d` · **Rubric:** [`RUBRIC.md`](RUBRIC.md), committed before any run (`8fa3aac`)

## Summary

tppgen drafted Target Product Profiles for 10 rare diseases, 3 runs each (30 reports, 690 scored fields). Every drafted field was scored against the public record it should match: FDA labels, ClinicalTrials.gov records and the FDA orphan designation database.

| Measure | Result |
|---|---|
| Accuracy on drafted fields | **97%** (414 of 429) |
| Recall on fields public data can fill | **97%** (414 of 429) |
| Fields correctly left blank | **261 of 261** |
| Runs that matched exactly | **10 of 10** indications, all 3 runs identical |

**Important:** this is an in-sample result. The fixes that raised accuracy from 67% to 97% were made while looking at these same 10 diseases. A held-out set of new diseases is needed before this number can be quoted as the tool's general accuracy (see Next steps).

## Indications

Eight with at least one FDA-approved therapy (tests comparator fields): cystic fibrosis, spinal muscular atrophy, Duchenne muscular dystrophy, Pompe disease, Fabry disease, Gaucher disease type 1, phenylketonuria, hereditary transthyretin amyloidosis.

Two with none (tests whether the tool invents comparators): myotonic dystrophy type 1, facioscapulohumeral muscular dystrophy. In both, every comparator field was left blank with the stated reason that no therapy is approved.

## Results by field (run 1; runs 2 and 3 identical)

| Field | Accurate | Inaccurate | Correctly blank |
|---|---|---|---|
| Target indication | 10 | 0 | 0 |
| Target population | 9 | 1 | 0 |
| Route of administration | 8 | 0 | 2 |
| Dosing regimen | 7 | 1 | 2 |
| Formulation | 8 | 0 | 2 |
| Strengths | 7 | 1 | 2 |
| Primary endpoint | 10 | 0 | 0 |
| Secondary endpoints | 10 | 0 | 0 |
| Efficacy threshold | 10 | 0 | 0 |
| Mechanism of action | 9 | 1 | 0 |
| Drug interactions | 7 | 0 | 3 |
| Standard of care | 9 | 1 | 0 |
| Orphan designation status | 10 | 0 | 0 |
| Safety profile | 8 | 0 | 2 |
| Contraindications | 8 | 0 | 2 |
| Warnings and precautions | 8 | 0 | 2 |
| 7 internal-only fields (PK/PD targets, differentiation, pricing, special populations, preclinical margins, CQAs, storage) | — | — | 70 of 70 |

## Remaining errors

1. **DMD dosing:** Viltepso shows a dilution sentence instead of the dose.
2. **Gaucher mechanism:** shows miglustat only; misses enzyme replacement (GBA).
3. **DM1 population:** recurring criteria are generic trial exclusions.
4. **Pompe standard of care:** Opfolda (miglustat, given with Pombiliti) is missing.
5. **SMA strengths:** Zolgensma's strength is missing.

## What changed between the first and final run

| Version | Accuracy | Recall | Main fix |
|---|---|---|---|
| `8fa3aac` | 67% | 62% | Baseline |
| `e24a55d` | — | — | Drop safety, PK and trial-conduct endpoints; drop boilerplate criteria; drop labels whose indication does not name the disease; drop bulk "1 g/g" strengths |
| `c289d78` | — | — | Rank efficacy endpoints from Phase 3/4 trials first |
| `443cd6f` | 88% | 80% | Merge endpoint synonyms (FEV1, Phe, GL-3…); count drugs as approved when their FDA label names the disease |
| `94bae1d` | 96% | 90% | Population from label; dose sentence; dedupe labels; standard of care and mechanism from disease-labelled drugs |
| + orphan data | **97%** | **97%** | FDA orphan designation export loaded |

## Limits

- **In-sample.** See the note above.
- **One scorer.** Scores were drafted with AI assistance and checked by the author. Every row in [`scores.csv`](scores.csv) carries a link and a note so anyone can re-check it.
- **Ten diseases, mostly genetic and well-studied.** Results may not hold for diseases with few trials or unusual naming.
- **Orphan matching** is word-based and undercounts some diseases (hATTR: 5 matches).
- **Labels and registries change.** Ground truth is the record in force on the run date.

## Next steps

1. Pick 10 new rare diseases not used during development, commit the list, then run and score them without changing code. That gives a held-out accuracy figure.
2. Fix the five remaining errors above.
3. Add an independent second scorer for a sample of fields.

## Reproduce

```bash
git clone https://github.com/DhruvASharma2004/tppgen.git && cd tppgen
pip install -r requirements.txt
python benchmark/run.py --runs 3
```

Outputs: `benchmark/outputs/` · Scores: `benchmark/scores.csv`
