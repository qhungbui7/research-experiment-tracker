# Research Reviews & Experiment Index

## Layout Convention

Reviews are grouped by experiment first, then by review round. In this folder, "experiment" means one evidence base or research hypothesis under investigation.

```text
reports/reviews/
  README.md
  TRACKER.md
  experiments/
    experiment_001/
      README.md
      round_001/
        CONTEXT.md
        review/
        rebuttals/
```

Use a new round inside an existing `experiment_NNN` folder when a review, audit, rebuttal, or follow-up analysis evaluates the same evidence base. Use a new `experiment_NNN` folder when the reviewed evidence changes materially (e.g. a new algorithm, novel architecture, new benchmark, dataset revision, or full replacement study).

Issue IDs in `TRACKER.md` are global across all experiments. The tracker records both `Experiment` and `Round` so the lineage of every finding is preserved.

## Experiments

| Experiment | Subject | Evidence base | Rounds | Open issues |
| --- | --- | --- | --- | --- |
| experiment_001 | Baseline Verification & Screening | `runs/baseline/` | `round_001` | 0 |

## Rounds

| Experiment | Round | Date | Focus | Trigger | Report | Open issues |
| --- | --- | --- | --- | --- | --- | --- |
| experiment_001 | round_001 | YYYY-MM-DD | Baseline evaluation and smoke tests | Initial reproduction run | `reports/reviews/experiments/experiment_001/round_001/review/baseline_audit.md` | 0 |
