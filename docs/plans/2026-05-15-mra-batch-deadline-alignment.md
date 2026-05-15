# MRA Batch Deadline Alignment Plan

## Goal

Align MRA batch processing with CAPA's batch-end semantics so MRA does not evaluate parcels before the full batch wait time has elapsed, and verify whether other batch-based baselines share the same issue.

## Plan

1. Audit batch usage across baseline and runner modules.
2. Add regression coverage for MRA matching at batch end and expiring parcels whose true deadline passes during the batch wait.
3. Change MRA from batch-start matching to batch-end matching, including deadline-aware route advancement before matching.
4. Re-run MRA, metric alignment, and deadline disturbance tests.
5. Commit only the MRA fix, regression tests, and this plan.

## Findings

- MRA was the affected batch baseline: it grouped tasks by batch but matched each group at the batch start.
- CAPA and RL-CAPA already use `prepare_chengdu_batch`, which advances to `batch_end_time` and filters by true deadline before matching.
- RamCOM also groups tasks by batch, but it processes tasks in arrival-time order inside each group and advances the simulator to each task arrival; it does not expose the same "future task at batch start" bug.
- Greedy receives `batch_size` through the runner API but dispatches per arrival and does not batch-match tasks early.

## Verification

- `pytest tests/test_mra_bpt.py -v`
- `pytest tests/test_metric_alignment.py -v`
- `pytest tests/test_deadline_disturbance.py -v`
