# Experiment History Streams And Paper Sweep Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan step by step, with review between major sections.

## Goal

Repair the experiment layer so that:

1. cooperating-platform own-task streams are independent of the local `num_parcels` axis and remain fixed within one canonical experiment seed,
2. the paper sweep presets and fixed defaults match the requested new experiment scales,
3. experiment summaries persist the additional local/cooperation metrics and wall-clock timing needed for analysis.

## Constraints

- Keep the unified Chengdu environment as the single source of experiment initialization.
- Do not add fallback or degraded execution paths.
- Do not change the algorithmic semantics of CAPA or baselines beyond the requested experiment-record and own-task-stream corrections.
- Preserve existing summary keys such as `TR`, `CR`, `BPT`, `delivered_parcels`, and `accepted_assignments`.
- Every section below must land with tests before commit.

## Section 1: Decouple cooperating-platform own-task streams from local parcel count

### Intended behavior

- `partner_tasks_by_platform` must be generated once during canonical environment construction.
- Each cooperating platform must receive its own deterministic stream length.
- Those stream lengths must not depend on the local platform `num_parcels`.
- Deriving a smaller `num_parcels` point from a canonical seed must only truncate local tasks, not partner own-task streams.
- Reducing the `platforms` axis may filter out whole partner platforms, but it must not truncate the retained platforms' own-task streams.

### Implementation outline

1. Extend experiment/environment configuration with explicit partner own-task stream sizing parameters.
2. Replace `tasks_per_platform` sampling with per-platform deterministic counts.
3. Stop truncating `partner_tasks_by_platform` inside `derive_environment_from_seed`.
4. Preserve deterministic behavior for split-process seeded experiments.

### Files

- `env/chengdu.py`
- `experiments/config.py`
- `experiments/paper_chengdu.py`
- `experiments/seeding.py`
- `tests/test_paper_canonical_seed_axes.py`
- `tests/test_metric_alignment.py`
- new focused test file if needed

### Verification

- Environment seed retains full partner own-task streams after `num_parcels` derivation.
- Partner own-task stream sizes differ by platform and remain stable across derived `num_parcels` points.
- ImpGTA still sees partner own-task streams after cloning and derivation.

### Commit

- `fix(experiments): decouple partner task streams from local parcel axis`

## Section 2: Update paper sweep presets and fixed defaults

### Intended behavior

- `exp_1`: `num_parcels = [1000, 2000, 5000, 10000, 20000]`
- default `num_parcels` for other groups: `5000`
- `exp_2`: `local_couriers = [100, 200, 300, 400, 500]`
- default `local_couriers` for other groups: `200`
- `exp_3`: unchanged
- `exp_4`: `platforms = [2, 4, 8, 12, 16]`, default `4`
- `exp_5`: unchanged
- `exp_6`: `courier_capacity = [25, 50, 75, 100, 125]`, default `50`

### Implementation outline

1. Update formal preset arrays.
2. Update `DEFAULT_CHENGDU_PAPER_FIXED_CONFIG`.
3. Keep canonical-seed build behavior consistent with the new maximum points.

### Files

- `experiments/paper_config.py`
- `experiments/paper_chengdu.py`
- tests covering preset values and defaults

### Verification

- Preset lookup returns the new arrays.
- Fixed defaults used by point/split wrappers reflect the new requested defaults.

### Commit

- `config(experiments): update Chengdu paper sweep presets`

## Section 3: Enrich experiment records and runner summaries

### Intended behavior

Every algorithm summary should still expose normalized `metrics`, and additionally record:

- cooperating platform own-task counts,
- cooperating platform accepted cross-platform task counts,
- cooperating platform realized cooperative revenue after sharing,
- local platform local-match count,
- local platform cross-platform match count,
- local platform unresolved parcel count,
- experiment start time,
- experiment end time,
- experiment duration in seconds.

### Implementation outline

1. Add a shared summary builder/helper to avoid six runner-specific ad hoc payloads.
2. Extend CAPA summary directly from `CAPAResult`.
3. Extend baselines to return the extra counts needed for summary assembly.
4. Keep backward-compatible keys in `metrics`.

### Files

- `algorithms/capa_runner.py`
- `algorithms/basegta_runner.py`
- `algorithms/impgta_runner.py`
- `algorithms/greedy_runner.py`
- `algorithms/mra_runner.py`
- `algorithms/ramcom_runner.py`
- `baselines/gta.py`
- `baselines/greedy.py`
- `baselines/mra.py`
- `baselines/ramcom.py`
- new shared helper under `algorithms/`
- focused tests for summary shape and values

### Verification

- Existing metrics remain present.
- Added summary fields are populated for CAPA and all baselines.
- CAPA / GTA / RamCOM cross-platform counts and revenues are consistent with the algorithm result.

### Commit

- `experiment(experiments): enrich Chengdu run summaries`

## Final verification

Run the targeted tracked test set covering:

- environment seeding and derivation,
- ImpGTA partner-stream usage,
- experiment preset/default behavior,
- algorithm summary payloads.

If a broader suite is blocked by missing optional dependencies such as `torch`, document that explicitly in the final report instead of claiming a full pass.
