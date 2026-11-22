# Benchmark rubric (v1)

This rubric is fixed before any benchmark run. It is committed with a timestamp so the rules cannot change after results are seen. Any later change gets a new version number and a stated reason.

## Question

How often does each field that tppgen drafts match the public record it cites? And how often does tppgen leave a field blank when public data cannot support it?

## Indications

Ten rare diseases, listed in `indications.csv`. Eight have at least one FDA-approved therapy, which tests the comparator fields. Two have none, which tests whether tppgen reports the gap instead of inventing a comparator.

## Ground truth, by field type

| Field type | Ground truth |
|---|---|
| Comparator: dosage form, strength, route | Current FDA label (DailyMed) of the approved drug |
| Comparator: safety benchmark | Boxed warning and Warnings and Precautions sections of that label |
| Primary efficacy endpoint | Primary outcome of the pivotal trial on ClinicalTrials.gov, cross-checked with Section 14 of the label |
| Target population | Indications and Usage section of the label; for indications with no approval, eligibility criteria of the largest Phase 2/3 trial |
| Mechanism of action | Mechanism section (12.1) of the label, or the Open Targets record for unapproved candidates |
| Gap fields (7) | Correct answer is always blank with a stated reason |

## Score categories

Each field gets exactly one score:

- **accurate**: matches the ground truth in substance.
- **inaccurate**: states something the ground truth contradicts.
- **unsupported**: states something the cited record does not contain.
- **missing**: left blank, but public ground truth exists.
- **correctly omitted**: left blank, and no public ground truth exists.

"In substance" means the same drug, value, unit and route. Wording differences do not count against a field. A partly right field (for example, the right drug with the wrong strength) is scored **inaccurate**.

## Reported numbers

1. Accuracy on drafted fields = accurate / (accurate + inaccurate + unsupported).
2. Recall on fillable fields = accurate / (accurate + inaccurate + unsupported + missing).
3. Gap discipline = correctly omitted / fields with no public ground truth.

Each number is reported per field type and per indication, with raw counts beside it.

## Procedure

1. Run `python benchmark/run.py` once per indication, 3 runs each. Record the date and the tool's commit hash.
2. Score every field in `scores.csv`, one row per field per run, with a link to the ground-truth record.
3. Publish all outputs, all scores and every failure.

## Known limits

- One scorer (the author). The control is that every score links to a public record anyone can re-check.
- Labels change. Ground truth is the label version in force on the run date.
