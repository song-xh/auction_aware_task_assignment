# review_0515 修复结果

## 已完成修改

1. RAMCOM cross settlement 对齐：
   - 新增 `compute_ramcom_platform_payment()`，最终 cross TR settlement 使用 `ramcom_outer_payment + mu2 * fare` 的统一平台支付口径，并按 fare 封顶。
   - 新增 delivered-only 诊断字段：`cross_payment_total`、`cross_fare_total`、`avg_cross_payment_ratio`、`cross_local_revenue_total`。
   - 诊断统计只汇总 delivered task，避免 rejected、timeout 或未完成任务污染 TR 口径。

2. Chengdu deadline 参数化：
   - 新增 `DEFAULT_CHENGDU_DEADLINE_SECONDS` 和 `deadline_seconds` 实验参数。
   - `build_framework_chengdu_environment()` 读取任务后统一把 local task 与 partner own-task stream 的 `d_time` 改为 `s_time + deadline_seconds`。
   - 原数据集 deadline 保存到 `dataset_d_time`，只用于审计，不参与算法。
   - `ExperimentConfig`、paper runner CLI/fixed config、canonical seed、environment seed/clone、snapshot 均携带 `deadline_seconds`。

3. CAMA 本地收益阈值：
   - 新增 `calculate_local_revenue_score(parcel, config)`，主 score 为 `(1 - zeta) * p_tau`。
   - 新增 `calculate_local_revenue_threshold(scores, omega)`。
   - `run_cama()` 的阈值与 local/auction split 使用 feasible pair 的本地收益 score。
   - Eq.6 utility 仍保留，用于插入位置与同一 parcel 多 courier 的 tie-break，不再作为主阈值目标。
   - `ThresholdHistory` 语义从 utility 累计改为 score 累计。

4. plotting 修复：
   - BPT 标签从 `Balance Per Task` 改为 `Batch Process Time`。
   - 新增 `visible_algorithms_for_metric()`。
   - TR/CR/BPT 均过滤 `basegta`；BPT 额外过滤 `mra`。
   - `save_comparison_plots()` 与 `save_default_comparison_plots()` 使用同一过滤规则。

## 测试证据

- `pytest tests/test_metric_alignment.py -k "ramcom or gta" -v`
  - 结果：31 passed, 13 deselected
- `pytest tests/test_deadline_disturbance.py -v`
  - 结果：10 passed
- `pytest tests/test_capa_local.py tests/test_chengdu_shortlist_runtime.py -v`
  - 结果：6 passed
- `pytest tests/test_plotting.py -v`
  - 结果：3 passed
- `pytest tests/test_paper_canonical_seed_axes.py tests/test_metric_alignment.py::MetricAlignmentTest::test_build_fixed_config_from_args_carries_task_window_sampling tests/test_metric_alignment.py::MetricAlignmentTest::test_environment_seed_preserves_task_window_sampling -v`
  - 结果：17 passed

## 未完成或需单独处理

- 尚未重新生成 Exp1/Exp2/Exp3 formal CD 全量结果与 plots。当前提交只完成代码路径、诊断字段和 targeted 回归。
- 更宽 smoke `pytest tests/test_rl_env_smoke.py tests/test_summary_disposition_fields.py -v` 中，`tests/test_summary_disposition_fields.py` 全部通过，但 `tests/test_rl_env_smoke.py` 有 2 个既有失败：
  - `test_stage1_state_uses_eight_dimensions_and_true_future_window`
  - `test_trainer_uses_eight_dimensional_stage1_networks_and_adam`
- 失败原因：`rl_capa/state_builder.py` 当前定义 `STAGE1_STATE_DIM = 10`，测试期望 8 维。该问题不属于 `docs/review_0515.md` 的四项修改范围，未在本阶段混入 RL 状态维度重构。

## 提交记录

- `dd0c6ac docs: plan review 0515 implementation`
- `d117010 fix(ramcom): align cross settlement diagnostics`
- `6ac8f47 feat(env): parameterize chengdu deadlines`
- `a23401c fix(cama): use local revenue threshold`
- `abf6879 fix(plot): filter comparison baselines`
