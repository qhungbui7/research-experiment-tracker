# Agent & Researcher Operational Guidelines

Guidelines for AI agents and human researchers using `research-experiment-tracker`.

## Core CLI Workflows

### 1. Initialize a Project
To equip any repository with experiment tracking:
```bash
experiment-tracker init --name "<project-name>"
```
This scaffolds `reports/reviews/`, `TRACKER.md`, `README.md`, `CONTEXT.md`, and `.experiment-tracker.json`.

### 2. Pre-Run Experiment Snapshotting
Before executing expensive compute:
```bash
experiment-tracker snapshot \
  --description "CartPole POMDP 5-seed sweep with frozen random traces" \
  --note "screening gate test" \
  --seeds "0,1,2,3,4"
```
This freezes the configuration files into `reports/reviews/snapshots/run_YYYYMMDD_HHMMSS/configs_snapshot/`, records git commit SHA and diff stat into `metadata.json`, and logs an entry to `changelog.md`.

### 3. Post-Run Finalization
Upon experiment completion or interruption:
```bash
experiment-tracker finalize \
  --run-id "run_YYYYMMDD_HHMMSS" \
  --status FULL_RUN \
  --summary-json "runs/experiment_001/run_summary.json"
```
Status choices: `FULL_RUN`, `BUG_RUN`, `OBJ_TERMINATED`, `HUMAN_TERMINATED`, `PARTIAL`, `STOPPED`.

### 4. Integrity Validation
Verify markdown tables, context files, and file references:
```bash
experiment-tracker validate --verbose
```
Must exit with code 0 before handing over experiments.

### 5. Build Interactive Explorer & Lineage Graph
Rebuild the interactive graph and static exports:
```bash
# Generate IDEA_GRAPH.html
experiment-tracker build --format html

# Generate static Mermaid IDEA_GRAPH.md
experiment-tracker build --format mermaid --output reports/reviews/IDEA_GRAPH.md

# Generate standalone folder export with per-file previews
experiment-tracker build --output-dir reports/reviews/IDEA_GRAPH_EXPORT
```

### 6. Serve Live Dashboard
Launch the lightweight local explorer:
```bash
experiment-tracker serve --port 8080 --open
```

---

## Agent Behavioral Rules

1. **Never Silently Rerun:** Before launching sweeps, check `index_completed_runs()` or `run_summary.json` to reuse valid finished seeds.
2. **Preserve Negative Results:** Never delete or conceal runs that refute the working hypothesis. All findings must be recorded in `TRACKER.md`.
3. **Audit Worktree Cleanliness:** If git worktree is dirty, record `uncommitted_changes` in the snapshot so results can be reproduced exactly.
4. **Follow PRINCIPLES.md:** Always pre-register hypotheses, smallest discriminating tests, and stopping criteria in `CONTEXT.md`.
