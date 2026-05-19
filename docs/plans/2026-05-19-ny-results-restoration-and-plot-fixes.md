# NY Results Restoration And Plot Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore the NY sweep results to the original per-experiment values, correct CAPA BPT after removing proven outlier batches, update plotting behavior to match the requested presentation rules, and regenerate the NY figures from the corrected data.

**Architecture:** Treat `/root/auction_aware_task_assignment/result/NY` as the baseline source for original NY sweep summaries, because the current workspace `result/NY` has already been mutated by `scripts/add_rlcapa_ny.py` to overwrite each sweep's default point with `exp5_ny_default` metrics. Keep data restoration, BPT recomputation, and plotting changes separate: first restore raw summary content, then correct only the CAPA BPT values supported by detailed evidence, then replot from the repaired summaries with deterministic plotting helpers.

**Tech Stack:** Python, `matplotlib`, existing `experiments.plotting`, existing NY summary markdown files, `pytest`.

---

### Task 1: Freeze The Restoration Inputs

**Files:**
- Modify: `docs/plans/2026-05-19-ny-results-restoration-and-plot-fixes.md`
- Check: `result/NY/README.md`
- Check: `/root/auction_aware_task_assignment/result/NY/README.md`
- Check: `scripts/add_rlcapa_ny.py:294-354`
- Check: `tests/test_add_rlcapa_ny.py`

**Step 1: Record the corruption mechanism**

Read `scripts/add_rlcapa_ny.py:294-354` and write a short execution note in the final implementation summary that `apply_default_metrics_to_sweep_rows()` and `sync_ny_sweep_defaults_from_exp5()` are the source of the sweep-point overwrite.

**Step 2: Diff current vs source NY summaries**

Run:

```bash
diff -ruN result/NY /root/auction_aware_task_assignment/result/NY
```

Expected: differences at least in `README.md`, per-experiment `README.md`, `rlcapa/summary.md`, and any sweep summary whose default point was overwritten.

**Step 3: Capture the exact restore policy**

Use this rule set for the implementation:

```text
1. Baseline algorithms (`capa`, `greedy`, `basegta`, `impgta`, `mra`, `ramcom`) in sweep experiments must revert to the source summaries from `/root/auction_aware_task_assignment/result/NY`.
2. `exp5_ny_default` must remain the default comparison source.
3. Any derived `rlcapa` rows in the workspace must be regenerated from the restored baseline summaries, not copied from the source tree.
4. Top-level and per-experiment README tables must be regenerated from the repaired summaries instead of hand-edited.
```

**Step 4: Add a regression test for “do not overwrite sweep default point from exp5”**

Update `tests/test_add_rlcapa_ny.py` so the desired behavior no longer asserts the old overwrite helper. Replace that test with one that proves the sweep rows stay source-faithful when rebuilding NY plots from already-restored summaries.

**Step 5: Run the focused test**

Run:

```bash
pytest tests/test_add_rlcapa_ny.py -v
```

Expected: fail before the implementation changes.

### Task 2: Investigate CAPA BPT Outliers Before Any Fix

**Files:**
- Modify: `tests/test_plotting.py`
- Modify: `tests/test_add_rlcapa_ny.py`
- Modify: `scripts/add_rlcapa_ny.py`
- Modify: `result/NY/exp5_ny_default/capa/summary.md`
- Check: `/root/auction_aware_task_assignment/result/NY/exp5_ny_default/capa/bpt_over_batches.png`
- Check: `capa/metrics.py:22-26`
- Check: `capa/experiments.py:87-132`

**Step 1: Inventory available detailed BPT evidence**

Verify which NY result artifacts contain batch-level detail:

```bash
find /root/auction_aware_task_assignment/result/NY -type f | rg 'bpt_over_batches|summary|README'
```

Expected: explicit per-batch detail is only available where `bpt_over_batches.png` exists; aggregate summaries alone are not enough to justify outlier removal.

**Step 2: Define a reproducible outlier rule before editing data**

Use a documented statistical rule, for example:

```text
For one CAPA batch-time series, compute Q1, Q3, IQR.
Mark a batch as an outlier only if BPT > Q3 + 1.5 * IQR.
If only one or a few isolated spikes satisfy the rule, drop those points and recompute mean BPT from the remaining batch times.
If no raw batch-time series exists for one sweep point, do not fabricate an outlier correction for that point.
```

**Step 3: Decide the evidence path for each corrected BPT**

Use this decision tree:

```text
1. If raw batch-time values can be reconstructed from an existing artifact or generator input, use them.
2. If only an image exists but the point is clearly isolated and supported by the source summary/figure, document the extracted values and method.
3. If neither raw values nor defensible extraction exists, stop and report that the aggregate summary is not enough to support a data correction.
```

**Step 4: Add a regression test for the correction helper**

Add a unit test around the new helper in `scripts/add_rlcapa_ny.py` or a small result-processing utility module. The test should assert that:

```python
def test_recompute_bpt_without_outlier_uses_trimmed_mean() -> None:
    batch_times = [8.0, 9.0, 8.5, 8.7, 40.0]
    result = recompute_bpt_without_outliers(batch_times)
    assert result == 8.55
```

Adapt the exact expected value to the helper’s rounding policy.

**Step 5: Run the focused tests**

Run:

```bash
pytest tests/test_add_rlcapa_ny.py tests/test_plotting.py -v
```

Expected: fail until the helper and NY-regeneration path are implemented.

### Task 3: Repair The NY Regeneration Pipeline

**Files:**
- Modify: `scripts/add_rlcapa_ny.py`
- Modify: `tests/test_add_rlcapa_ny.py`
- Modify: `result/NY/README.md`
- Modify: `result/NY/exp1_ny_parcel/README.md`
- Modify: `result/NY/exp2_ny_couriers/README.md`
- Modify: `result/NY/exp3_ny_radius/README.md`
- Modify: `result/NY/exp4_ny_platforms/README.md`
- Modify: `result/NY/exp5_ny_default/README.md`
- Modify: `result/NY/exp6_ny_capacity/README.md`
- Modify: `result/NY/*/*/summary.md`

**Step 1: Remove the exp5-to-sweep overwrite path**

Delete or bypass `apply_default_metrics_to_sweep_rows()` / `sync_ny_sweep_defaults_from_exp5()` from the NY rebuild flow. The rebuilt sweep summaries must read from the restored baseline markdown rows directly.

**Step 2: Add a source-tree restore loader**

Implement a small loader that:

```python
def load_source_ny_baseline_rows(source_root: Path, exp_name: str, sweep_param: str, algorithms: Sequence[str]) -> dict[str, dict[Any, dict[str, float]]]:
    ...
```

It should parse the baseline summaries from `/root/auction_aware_task_assignment/result/NY/...`, return sweep rows per algorithm, and preserve the original default-point values.

**Step 3: Regenerate derived `rlcapa` rows from the repaired baseline rows**

Keep the existing `rlcapa` derivation only as a secondary derived layer. Do not let it mutate baseline rows.

**Step 4: Rebuild all NY markdown outputs**

Re-run the summary writers so that:

```text
1. per-algorithm summary.md files match the corrected metrics
2. per-experiment README tables match the corrected summary files
3. top-level result/NY/README.md matches the corrected experiment README tables
```

**Step 5: Run the NY-regeneration tests**

Run:

```bash
pytest tests/test_add_rlcapa_ny.py -v
```

Expected: pass after the pipeline change.

### Task 4: Fix Plotting Behavior To Match The Requested Style

**Files:**
- Modify: `experiments/plotting.py`
- Modify: `tests/test_plotting.py`

**Step 1: Add metric-specific axis formatting helpers**

Implement helpers so plotting behavior is data- and metric-aware:

```python
def _format_cr_percent_axis(ax: Any) -> None: ...
def _format_bpt_axis_ms(ax: Any) -> int: ...
def _format_tr_axis_for_exp1(ax: Any, x_label: str) -> int: ...
def _apply_integer_tick_locator(ax: Any, axis: str, max_ticks: int = 5) -> None: ...
def _legend_location_for_series(metric_name: str, series: Sequence[tuple[str, Sequence[float]]]) -> str: ...
```

**Step 2: Update the line-plot behavior**

Change `_save_line_plot()` so it:

```text
1. never places the legend at the plot center
2. uses only upper/lower + left/center/right legend anchors
3. draws a visible legend frame
4. shrinks legend size when there are many series
5. limits y ticks to roughly 4 and never more than 5
6. prefers integer tick labels
7. renders CR as percent integers
8. renders BPT in ms and uses 10^n style scaling when needed
9. renders exp1 TR in log10 units so the y-axis can show 1, 2, 3, ...
```

**Step 3: Update the grouped-bar/default-comparison behavior**

Apply the same metric-specific y-axis conventions to `_save_grouped_bar_plot()` and `save_default_comparison_plots()`, including `CR (%)`, `BPT (ms)`, integer tick counts, and framed legends where legends exist.

**Step 4: Expand plotting tests**

Add focused assertions in `tests/test_plotting.py` for:

```python
def test_cr_axis_uses_percent_integers() -> None: ...
def test_bpt_axis_uses_ms_and_power_of_ten_label() -> None: ...
def test_exp1_tr_axis_uses_log10_labeling() -> None: ...
def test_line_plot_legend_avoids_center_and_has_frame() -> None: ...
def test_y_ticks_do_not_exceed_five() -> None: ...
```

**Step 5: Run the plotting tests**

Run:

```bash
pytest tests/test_plotting.py -v
```

Expected: pass after the plotting update.

### Task 5: Recompute Corrected CAPA BPT And Regenerate NY Figures

**Files:**
- Modify: `scripts/add_rlcapa_ny.py`
- Modify: `result/NY/**/*.md`
- Modify: `result/NY/**/*.png`
- Modify: `result/NY/**/*.eps`

**Step 1: Apply only evidence-backed CAPA BPT corrections**

For every NY experiment point where a CAPA outlier is proven by detailed batch evidence, recompute:

```text
corrected_bpt = mean(non_outlier_batch_times)
```

Then update the affected `capa/summary.md`, any per-experiment README table, and the top-level NY README table.

**Step 2: Regenerate comparison figures from the corrected summaries**

Run the NY regeneration entrypoint or an equivalent script path that:

```text
1. reads restored baseline rows
2. applies the approved CAPA BPT corrections
3. rebuilds rlcapa rows if the workspace still tracks them
4. writes updated markdown tables
5. re-renders all `tr_*.png/.eps`, `cr_*.png/.eps`, `bpt_*.png/.eps`, and default comparison plots
```

**Step 3: Verify the repaired plots visually**

Inspect at least:

```text
result/NY/exp1_ny_parcel/tr_vs_num_parcels.png
result/NY/exp1_ny_parcel/cr_vs_num_parcels.png
result/NY/exp1_ny_parcel/bpt_vs_num_parcels.png
result/NY/exp5_ny_default/default_tr_comparison.png
result/NY/exp5_ny_default/default_cr_comparison.png
result/NY/exp5_ny_default/default_bpt_comparison.png
```

Expected: no sweep-point dip caused by exp5 substitution, legend no longer blocks the center, CR uses percent integers, BPT uses ms presentation, and exp1 TR is visually compressed by log scaling.

**Step 4: Run the full targeted verification**

Run:

```bash
pytest tests/test_add_rlcapa_ny.py tests/test_plotting.py -v
```

Expected: pass.

**Step 5: Run a repository status check**

Run:

```bash
git status --short
```

Expected: only the intended code, test, plan, markdown, and regenerated figure artifacts are changed.

### Task 6: Summarize Remaining Risk Before Closeout

**Files:**
- Modify: `docs/plans/2026-05-19-ny-results-restoration-and-plot-fixes.md`

**Step 1: Record any unfixable data gap**

If any CAPA BPT point could not be corrected because only an aggregate summary exists and no defensible detailed batch series can be recovered, record that explicitly in the final response and do not silently patch the number.

**Step 2: Record the verification evidence**

The final response must include:

```text
1. which NY sweep points were restored from the external source tree
2. which CAPA BPT values were recomputed and why
3. which plots were regenerated
4. the exact pytest commands that passed
```

