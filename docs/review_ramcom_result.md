# RamCOM CPUL 适配审查结果

## 审查范围

- `baselines/ramcom.py`
- `algorithms/ramcom_runner.py`
- `runner.py`
- `tests/test_metric_alignment.py`

## 当前结论

RamCOM 当前保留的是原文的随机阈值与外部最大期望收益支付机制，并通过 CPUL 统一环境完成可行性、路径插入、收益、CR 和 BPT 统计。审查未发现 RamCOM 调用 DAPA、FPSA、RVA、CAPA 动态阈值或 RL-CAPA 训练/策略模块。

## 修改内容

1. 修复外部 courier 无经验历史时必然拒绝的问题。
   - 新增 `estimate_reservation_payment()`，用 CPUL 插入结果中的 `distance_meters` 和统一本地 courier payment ratio 估计 reservation payment。
   - `worker_acceptance_probability()` 在无经验历史但有 reservation 时使用单调接受模型 `min(1, payment / reservation)`。
   - `cooperative_acceptance_probability()` 对 reservation 列表进行长度对齐，避免 `zip` 截断漏掉候选 courier。

2. 修复 RamCOM 外部支付搜索域。
   - 新增 `RamCOMPaymentEstimate` 和 `estimate_ramcom_outer_payment()`。
   - 支付候选集合包含 `fare`、经验历史阈值、reservation 阈值。
   - 仍按 RamCOM 公式 `(fare - payment) * Pr_accept` 最大化期望收益。
   - tie-break 使用更小 payment，然后更高集合接受概率。

3. 补齐 batch 与 trace 接入。
   - `run_ramcom_baseline_environment()` 新增 `batch_size` 参数，并按 `group_legacy_tasks_by_batch()` 分 batch，batch 内按到达时间顺序逐个决策。
   - 保存 `theta`、`k`、`threshold`、`max_fare`、`acceptance_model`、`payment_search`、`batch_size`。
   - 保存每个 parcel 的 `decision_trace`，包括分支、可行候选数量、`payment_e`、期望收益、集合接受概率、外部采样结果、最终 courier/platform 或拒绝原因。

4. 补齐统一 runner。
   - `RamCOMAlgorithmRunner` 接收并传递 `batch_size`。
   - 根入口 `runner.py build_algorithm_kwargs()` 对 `ramcom` 传递 `--batch-size`。
   - `decision_trace` 保存在 summary 顶层，不放入 `metrics`，避免 CLI 单次运行打印大量 trace。

5. 补齐回归测试。
   - reservation-based acceptance。
   - 无经验历史时仍可通过 reservation 模型进行跨平台分配。
   - 外部支付搜索使用 reservation 候选。
   - 阈值、支付模型、trace 元数据输出。
   - `runner.py` 对 RamCOM 传递 `batch_size`。
   - RamCOM runner 不把 trace 放入标量 metrics 打印路径。

## 与 CPUL 框架对齐情况

- 可行性：继续调用 `build_legacy_feasible_insertions()`，包含容量、deadline、路径插入、service radius、路网 travel model 等统一逻辑。
- 状态更新：继续调用 `apply_assignment_to_legacy_courier()` 并失效对应 snapshot/insertion cache。
- 本地收益：继续调用 `compute_local_platform_revenue_for_local_completion()`。
- 跨平台收益：继续调用 `compute_local_platform_revenue_for_cross_completion()`，其中 `platform_payment` 使用 RamCOM 自身选出的 `payment_e`。
- CR：继续用 `compute_delivered_legacy_task_count()` 的实际 delivered 结果。
- BPT：继续使用当前 baseline 口径的 assignment decision time，不把路网 routing 和插入搜索时间重复计入。

## 保留的 RamCOM 原始机制

- `theta = ceil(log(max_fare + 1))`
- `k ~ Uniform({1, ..., theta})`
- `threshold = exp(k)`
- `fare > threshold` 时优先随机选择本地可行 courier。
- 低价值 parcel 或本地不可行高价值 parcel 进入外部 courier 决策。
- 外部 payment 通过最大期望收益 `(fare - payment) * Pr_accept` 选择。
- 外部 courier 接受通过 seeded random sampling。
- 不执行平台层二次拍卖。

## 接受概率模型

当前记录为 `empirical_history_or_reservation_based`：

- 若 courier 有历史完成值，使用经验分布。
- 若无历史值，使用 CPUL reservation-based monotonic model。

这是因为 Chengdu 统一环境中并没有真实外部 courier 接受/拒绝支付的历史记录；reservation 模型是缺失真实接受数据时的显式复现假设，已写入结果字段。

## 支付搜索方式

当前记录为 `history_or_reservation_candidates`：

- 不使用任意网格步长。
- 不调用 DAPA/FPSA/RVA。
- 候选支付由历史阈值、reservation 阈值和 fare 组成。

## 测试结果

```text
python3 -m unittest \
  tests.test_metric_alignment.MetricAlignmentTest.test_ramcom_uses_delivered_count_for_cr \
  tests.test_metric_alignment.MetricAlignmentTest.test_ramcom_bpt_is_mean_assignment_time_per_task \
  tests.test_metric_alignment.MetricAlignmentTest.test_ramcom_acceptance_uses_reservation_when_history_missing \
  tests.test_metric_alignment.MetricAlignmentTest.test_ramcom_outer_payment_uses_reservation_candidates_without_history \
  tests.test_metric_alignment.MetricAlignmentTest.test_ramcom_can_assign_outer_worker_without_empirical_history \
  tests.test_metric_alignment.MetricAlignmentTest.test_ramcom_reports_threshold_payment_and_trace_metadata \
  tests.test_metric_alignment.MetricAlignmentTest.test_runner_builds_ramcom_batch_size_kwargs \
  tests.test_metric_alignment.MetricAlignmentTest.test_ramcom_runner_keeps_trace_out_of_printed_metrics -v

Ran 8 tests in 0.002s
OK

python3 -m unittest \
  tests.test_capa_config.CAPAConfigCentralizationTests.test_baseline_default_sources_are_centralized \
  tests.test_capa_config.CAPAConfigCentralizationTests.test_default_chengdu_config_reuses_centralized_defaults -v

Ran 2 tests in 0.000s
OK

python3 -m py_compile baselines/ramcom.py algorithms/ramcom_runner.py runner.py tests/test_metric_alignment.py
OK
```

## 小规模真实环境 smoke

命令：

```bash
python3 runner.py run \
  --algorithm ramcom \
  --data-dir Data \
  --num-parcels 30 \
  --local-couriers 5 \
  --platforms 2 \
  --couriers-per-platform 2 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 120 \
  --partner-history-task-count-start 10 \
  --partner-history-task-count-step 0 \
  --batch-size 30 \
  --output-dir /tmp/ramcom_review_smoke
```

结果：

```text
method=RamCOM-CPUL
theta=3
k=1
threshold=2.718281828459045
max_fare=11.1
TR=209.69188
CR=0.9666666666666667
BPT=0.0
delivered_parcels=29
accepted_assignments=29
local_assignment_count=28
cross_assignment_count=1
unresolved_parcel_count=1
partner_cross_assignment_counts={'P2': 1}
```

`/tmp/ramcom_review_smoke/summary.json` 中已确认 `decision_trace` 保存于 summary 顶层，`metrics` 中只保留标量/配置字段。

## 仍需人工确认

- reservation payment 当前使用 `local_payment_ratio * fare + insertion_distance_km`。这不是 RamCOM 原文给出的参数，而是 CPUL 缺少真实接受记录时的显式复现假设；如果后续能从数据或论文补充 courier reservation/bid 公式，应替换该估计函数。
- RamCOM 原文是 online 算法，当前适配为 CPUL batch 输入下 batch 内按到达时间逐个处理；该设定已和现有实验框架对齐，但需要在论文实验说明中标注。
