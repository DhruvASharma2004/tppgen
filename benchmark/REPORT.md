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

**Important:** the 97% is an in-sample result; the held-out result is 89% (below). The fixes that raised accuracy from 67% to 97% were made while looking at these same 10 diseases. Quote the held-out figure.

## Held-out result

Ten new diseases, chosen and committed (`e7a3875`) before any run, then run on the same code (`94bae1d`) with no changes: Niemann-Pick type C, MPS I, MPS II, hypophosphatasia, X-linked hypophosphatemia, Friedreich ataxia, acid sphingomyelinase deficiency, Wilson disease, Angelman syndrome, limb-girdle muscular dystrophy.

| Measure | Development set | **Held-out set** |
|---|---|---|
| Accuracy on drafted fields | 97% | **89%** (378 of 423) |
| Recall on fillable fields | 97% | **89%** |
| Fields correctly left blank | 261 of 261 | **267 of 267** |
| Identical across 3 runs | 10 of 10 | **10 of 10** |

**89% is the number to quote** for how tppgen performs on a disease it has not seen.

Comparator fields from FDA labels (route, dosing, formulation, strengths, safety, standard of care) were right in every held-out disease with an approved drug. The errors concentrate in one place:

| Field | Held-out errors (of 10) | Cause |
|---|---|---|
| Primary endpoint | 5 | A PK, immunogenicity or biomarker endpoint outranks the pivotal one when only one or two Phase 3 trials exist (ASMD, HPP, MPS I, MPS II, XLH) |
| Efficacy threshold | 5 | Inherits the primary endpoint |
| Secondary endpoints | 2 | Same cause |
| Target population | 2 | Boilerplate criteria when no drug is approved |
| Orphan designation | 1 | Ontology name ("X-linked dominant hypophosphatemic rickets") does not match FDA wording |

Scores: [`scores_heldout.csv`](scores_heldout.csv) · Outputs: `outputs_heldout/`

The next fix is to take the primary endpoint from the approved drug's label (Section 14, Clinical Studies) when one exists, instead of from trial counts. That fix will be tested on a third, new set.

## Third set (label-based primary endpoint)

Ten more diseases, listed in `thirdset.csv` and committed (`d0b7b76`) before any run: alpha-mannosidosis, MPS IVA, MPS VI, CLN2, nephropathic cystinosis, hereditary angioedema, achondroplasia, Rett syndrome, Charcot-Marie-Tooth 1A, CLN3. Final run on commit `46e842d`, 3 runs each, identical across runs.

**This is not a clean held-out test.** The label endpoint patterns were widened after one third-set label (Naglazyme) was seen (`ea3e762`, `a20ea47`), and a truncation bug was fixed after an MPS I miss (`46e842d`: Section 14 text had been cut at 400 characters). Quote 89% as the held-out number; read this set as a check on the endpoint fix.

| Measure | Held-out set | Third set |
|---|---|---|
| Accuracy on drafted fields | 89% | **85%** (333 of 393) |
| Recall on fillable fields | 89% | **80%** (333 of 417) |
| Fields correctly left blank | 267 of 267 | 273 of 273 |
| Primary endpoint right | 5 of 10 | **8 of 10** |

The endpoint fix worked: the primary endpoint came from the approved label in 4 diseases (achondroplasia, HAE, MPS IVA, Rett), all correct. Two misses remain (alpha-mannosidosis, MPS VI), where the label states its endpoint in wording the patterns do not cover.

New errors, all scored as found:

| Cause | Fields lost per run | Diseases |
|---|---|---|
| Label endpoint wording not matched; primary and threshold fall back to trial counts | 4 | alpha-mannosidosis, MPS VI |
| Epidiolex (LGS, Dravet, TSC) passed the label-names-the-disease check for Rett | 9 | Rett |
| Route or dosing blank although the label gives it | 5 | achondroplasia, CLN2, cystinosis |
| No registered trials, so label population, secondaries and threshold left blank | 3 | MPS IVA |
| Strength from the wrong NDC record | 2 | achondroplasia, cystinosis |
| PD biomarkers not filtered from secondaries | 2 | HAE, cystinosis |
| "Hand function" mapped to the myotonia synonym | 1 | Rett |
| Repeat-dose sentence chosen as dose | 1 | HAE (Kalbitor) |
| Contraception boilerplate as population | 1 | CMT1A |

Scores: [`scores_thirdset.csv`](scores_thirdset.csv) · Outputs: `outputs_thirdset/` · Scoring sheet built with `extract.py`.

Held-out outputs were also rerun on `46e842d`; MPS I now shows the Aldurazyme label endpoint (percent-predicted FVC and 6-minute walk). The 89% score is from the original held-out run and was not rescored.

## Fourth set (clean held-out, after the third-set fixes)

Ten new diseases, committed (`4d4b910`) before any code change or run: primary hyperoxaluria type 1, MPS VII, Lambert-Eaton myasthenic syndrome, paroxysmal nocturnal hemoglobinuria, generalized lipodystrophy, metachromatic leukodystrophy, OTC deficiency, ALS, Canavan disease, GM1 gangliosidosis. Run once on `0352d47`, 3 runs each, identical across runs, scored without code changes.

| Measure | Held-out set 2 | **Held-out set 4** | **Both clean sets** |
|---|---|---|---|
| Accuracy on drafted fields | 89% (378/423) | **85%** (309/363) | **87%** (687/786) |
| Recall on fillable fields | 89% | 76% (309/405) | — |
| Fields correctly left blank | 267/267 | 285/285 | all |
| Primary endpoint right | 5/10 | 5/10 | 10/20 |

**87% across 20 unseen diseases is the number to quote.**

Four diseases were near-perfect (LEMS, MPS VII, PH1, PNH). Errors concentrate in three:

| Cause | Fields lost per run | Diseases |
|---|---|---|
| Approved drug not reachable: Open Targets lists no drug for the term, or the gene therapy has no openFDA label | 14 missing, 2 inaccurate | generalized lipodystrophy (Myalept), MLD (Lenmeldy) |
| Operational, safety or biomarker endpoint ranked first where no label states one | 9 | GM1, MLD, OTC, lipodystrophy |
| Wrong or incomplete standard of care | 3 | ALS (riluzole missing), OTC, lipodystrophy |
| Wrong drug's mechanism | 2 | OTC (carglumic acid), lipodystrophy |
| Orphan name mismatch ("ornithine carbamoyltransferase" vs FDA wording) | 1 | OTC |
| Multi-disease label: endpoint taken from the IgAN study | 1 | PNH (Fabhalta) |
| Boilerplate population | 1 | MLD |

Scores: [`scores_fourthset.csv`](scores_fourthset.csv) · Outputs: `outputs_fourthset/` (left as run on `0352d47`).

Fixes made after scoring (dose sentence chosen for this disease, kit strengths, synonym floor so a few off-target trials cannot add a synonym, multi-disease label endpoints) were checked on sets 1 to 3 only. They are not counted in any number above.

### Cost check for the Claude extraction plan

`token_estimate.py` on 130 cached labels: median 3,634 input tokens per call (Indications + Clinical Studies + 1,500 prompt), 90th percentile 7,733, maximum 12,797. The funding budget assumed 30,000, so the real cost is about a quarter of the estimate.

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

1. Take the primary endpoint from label Section 14 when a drug is approved; test on a third, new set.
2. Fix the five remaining errors above.
3. Add an independent second scorer for a sample of fields.

## Reproduce

```bash
git clone https://github.com/DhruvASharma2004/tppgen.git && cd tppgen
pip install -r requirements.txt
python benchmark/run.py --runs 3
```

Outputs: `benchmark/outputs/` · Scores: `benchmark/scores.csv`
