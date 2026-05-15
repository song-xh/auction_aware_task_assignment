# review_0515

## 目标

本次审查覆盖四个问题：

1. `result/exp1_formal_CD`、`result/exp2_formal_CD`、`result/exp3_formal_CD` 中 RAMCOM 的 TR 异常偏高，尤其高于作为改进算法的 ImpGTA。
2. deadline 是否在所有算法推进逻辑中真实生效，是否把 batch 等待时间、在路上时间计入，且只约束 pickup，不约束返回 station。
3. CAPA 本地匹配从复杂 utility 改为本地收益阈值：`(1 - zeta) * p_tau`，动态阈值改为所有可行本地匹配 pair 的平均本地收益乘 `omega`。
4. `experiments/plotting.py` 中 BPT 全称错误，并按要求过滤图中的算法。

## 审查依据

- `docs/agent.md`：要求优先遵循论文与审查材料，禁止隐藏 fallback，CAPA 逻辑应模块化并被 RL-CAPA 复用。
- `docs/MinerU_markdown_Competition_and_Cooperation_Global_Task_Assignment_in_Spatial_Crowdsourcing_2039180845507551232.md`：参考 [17] 明确 ImpGTA 是 BaseGTA 的预测增强版，通常应优于 RamCOM，特别是其动态阈值应优于 RamCOM 静态阈值。
- 当前代码：`baselines/ramcom.py`、`baselines/gta.py`、`capa/cama.py`、`capa/utility.py`、`env/chengdu.py`、`rl_capa/env.py`、`experiments/plotting.py`。
- 当前结果：本地 `result/exp1_formal_CD/summary.json`，Windows 挂载路径 `/mnt/c/Users/songxh/Desktop/result/exp2_formal_CD/summary.json`、`/mnt/c/Users/songxh/Desktop/result/exp3_formal_CD/exp3_formal/summary.json`。

## 结果异常证据

### Exp1: num_parcels

| num_parcels | RAMCOM TR | ImpGTA TR | RAMCOM - ImpGTA | TR 最高算法 |
| --- | ---: | ---: | ---: | --- |
| 5000 | 35157.98 | 27393.21 | 7764.77 | ramcom |
| 20000 | 140712.34 | 109466.84 | 31245.49 | ramcom |
| 50000 | 347012.39 | 310772.18 | 36240.21 | basegta |
| 100000 | 688698.92 | 636126.61 | 52572.31 | ramcom |
| 200000 | 1272708.66 | 1191689.23 | 81019.43 | capa |

平均 RAMCOM TR 为 496858.06，平均 ImpGTA TR 为 455089.62，RAMCOM 平均高 41768.44。

### Exp2: local_couriers

| local_couriers | RAMCOM TR | ImpGTA TR | RAMCOM - ImpGTA | TR 最高算法 |
| --- | ---: | ---: | ---: | --- |
| 1000 | 291256.21 | 250953.72 | 40302.50 | ramcom |
| 2000 | 298120.48 | 253836.76 | 44283.72 | ramcom |
| 3000 | 299561.94 | 258211.45 | 41350.48 | ramcom |
| 4000 | 300878.34 | 260682.10 | 40196.25 | ramcom |
| 5000 | 300836.35 | 266925.12 | 33911.22 | ramcom |

平均 RAMCOM TR 为 298130.66，平均 ImpGTA TR 为 258121.83，RAMCOM 平均高 40008.84。

### Exp3: service_radius

| service_radius | RAMCOM TR | ImpGTA TR | RAMCOM - ImpGTA | TR 最高算法 |
| --- | ---: | ---: | ---: | --- |
| 0.5 | 300839.93 | 262075.24 | 38764.68 | ramcom |
| 1.0 | 300157.11 | 256064.30 | 44092.81 | ramcom |
| 1.5 | 298020.75 | 253540.70 | 44480.05 | ramcom |
| 2.0 | 297508.84 | 252787.20 | 44721.65 | ramcom |
| 2.5 | 295499.06 | 254453.81 | 41045.25 | ramcom |

平均 RAMCOM TR 为 298405.14，平均 ImpGTA TR 为 255784.25，RAMCOM 平均高 42620.89。

## 发现 1：RAMCOM 收益偏高的代码原因

### 已对齐的部分

RAMCOM 最终 TR 没有直接使用 expected revenue。它在 `baselines/ramcom.py:442-445` 使用 `compute_local_platform_revenue_for_cross_completion(fare, outer_payment)`，并在 `baselines/ramcom.py:492` 只统计 delivered task 的收益。这个口径与 GTA 的 cross TR 入口一致：`baselines/gta.py:778-781` 也使用 `compute_local_platform_revenue_for_cross_completion(fare, outcome.payment)`。本地单也同样扣除 `zeta * fare`：RAMCOM 在 `baselines/ramcom.py:361-364`，GTA 在 `baselines/gta.py:695-698`。

因此，直接的 `TR = fare - payment` / `fare - zeta * fare` 统计函数不是首要问题。

### 高风险不对齐点

RAMCOM 的 cross payment 来源与 CAPA/GTA 不同，并且当前实现会系统性给 RAMCOM 偏低 payment，从而抬高 local-platform TR。

- RAMCOM 支付由 `estimate_ramcom_outer_payment()` 生成，候选 payment 来自历史值、reservation estimate 和 fare：`baselines/ramcom.py:151-165`。
- 无历史时，接受概率使用 `payment / reservation_payment`：`baselines/ramcom.py:98-103`。
- reservation estimate 近似为 `zeta * fare + distance_km`：`baselines/ramcom.py:75-78`。
- cross 成功后 local-platform revenue 为 `fare - outer_payment`：`baselines/ramcom.py:442-445`。

这意味着在没有真实历史校准时，RAMCOM 常会用接近 `0.2 * fare + distance_km` 的低 payment 完成任务，并保留接近 `0.8 * fare` 的 TR。相比之下，ImpGTA/BaseGTA 的 AIM payment 是 `critical_payment + mu2 * fare`，见 `baselines/gta.py:490-496`，默认 `mu2=0.5` 时 payment 至少包含半个 fare 的共享项，local-platform TR 被显著压低。这解释了 RAMCOM 在 Exp2/Exp3 中 TR 高且接近稳定上限的现象。

### 行为层面异常

参考 [17] 的文字结论是：ImpGTA 通过未来时空分布和动态阈值获得更高 profit，RamCOM 的静态阈值不应稳定压过 ImpGTA。当前实现中 RAMCOM 同时拥有：

- 静态高价值阈值，低于阈值的任务直接转 outer；
- 低 reservation payment；
- 高 acceptance probability；
- 与 ImpGTA 不同的 payment 成本尺度。

这会使 RAMCOM 看起来像一个“低价买外部运力”的算法，而不是与 ImpGTA/CAPA 处于同一支付成本口径下的 baseline。

### 需要验证的根因假设

首要假设：RAMCOM 的异常不是最终 TR 汇总函数重复计数，而是 RAMCOM outer payment 生成与 GTA/CAPA 的平台支付成本尺度不一致，导致 cross assignment 的 local-platform revenue 被高估。

最小验证方式：

1. 在 RAMCOM 结果里额外统计 delivered cross 的平均 `outer_payment / fare`。
2. 在 BaseGTA/ImpGTA 结果里统计 delivered cross 的平均 `platform_payment / fare`。
3. 若 RAMCOM 比例显著低于 ImpGTA/BaseGTA，且 TR 差距主要由 cross 任务贡献，则确认 payment 尺度不一致。
4. 增加单元测试，构造同一 `fare`、同一可行 outer courier、无历史记录场景，证明 RAMCOM 当前 payment 低于 GTA AIM payment，并记录对 TR 的影响。

## 发现 2：deadline 当前有效但来源需要改

### 已有效的部分

CAPA/RL-CAPA batch 推进逻辑已经把 batch 等待计入 deadline：

- `prepare_chengdu_batch()` 先把路线推进到 `batch_end_time`，再把 `runtime.current_time` 设置为 batch end：`env/chengdu.py:1471-1484`。
- 同一函数按 `get_true_deadline(task) >= runtime.current_time` 过滤可进入本轮匹配的任务：`env/chengdu.py:1486-1491`。
- `run_cama()` 和 `run_dapa()` 以 `runtime.current_time` 做 feasibility 检查：`env/chengdu.py:1996-2008`，`capa/cama.py:41-50`，`capa/dapa.py:46-55`。
- RL-CAPA 的 `apply_capa_batch()` 复用同一条 `run_cama()` / `run_chengdu_cross_matching()` 路径：`rl_capa/env.py:359-407`。

在路上时间也已计入：

- `advance_legacy_routes_with_deadline_accounting()` 使用 movement callback 产生的 `completed_at`，没有事件时退化为 `step_end_time`：`env/chengdu.py:1092-1116`。
- 只有 `completed_at <= deadline` 才进入 delivered，否则进入 timed_out：`env/chengdu.py:1117-1128`。
- TR 只统计 delivered task：`baselines/common.py:33-54`，RL-CAPA reward 也只统计 `outcome.on_time` 的 local-platform revenue：`rl_capa/env.py:588-613`。

deadline 当前只影响 pickup，不影响返回 station：

- legacy movement 在完成 `courier.re_schedule[0]` 时发出 delivery event 并删除任务，见 `Framework_ChengDu.py:307-319`、`Framework_ChengDu.py:332-349`。
- 当 `re_schedule` 为空后返回 station 的分支不会产生 task delivery event，见 `Framework_ChengDu.py:351-367`。
- 因此当前 deadline 约束的是到达 pickup task node 的时间，不约束回站。

### 需要修改的部分

deadline 当前来自数据集 `d_time`：

- `Tasks_ChengDu.py:36-48` 直接从第 6 列读取 `d_time`。
- `get_true_deadline()` 返回 `task.d_time`：`env/chengdu.py:410-420`。
- `legacy_task_to_parcel()` 默认把 `get_model_deadline()` 写进 CAPA `Parcel.deadline`：`env/chengdu.py:709-728`。
- `build_framework_chengdu_environment()` 读取任务后没有统一重写 deadline：`env/chengdu.py:2155-2160`、`env/chengdu.py:2193-2215`。

这会让实验被数据集自带 deadline 污染。应新增统一参数，例如 `deadline_seconds`，并在环境构建阶段把所有 local tasks 与 partner own-task streams 的 `d_time` 设置为 `s_time + deadline_seconds`。随后所有算法继续通过 `get_true_deadline()` / `get_model_deadline()` 读取同一个字段。

## 发现 3：utility 与 TR 不单调

当前 CAPA local matching 使用 capacity 与 detour 组成的 utility：

- `calculate_utility()` 计算 `gamma * capacity_ratio + (1 - gamma) * detour_ratio`：`capa/utility.py:517-546`。
- `run_cama()` 每个 parcel 选择 utility 最大的 pair：`capa/cama.py:180-193`。
- 阈值使用所有可行 pair 的 utility 平均值乘 `omega`：`capa/cama.py:207-219`，`capa/models.py:55-87`。

该 utility 衡量的是插入便利性和容量余量，不直接衡量 TR。用户提出的替换方向合理：本地任务被 local courier 完成时 local-platform revenue 固定为 `(1 - zeta) * p_tau`，用这个值作为 local matching score 与阈值，可以让 CAMA 的局部选择和 TR 目标单调一致。

需要注意：如果同一 parcel 有多个可行 courier，所有 pair 的本地收益相同。最佳 courier 的 tie-breaker 应保留插入代价或原 utility 的辅助排序，否则会引入随机或不稳定行为。建议实现为：

- `local_revenue_score = (1 - zeta) * parcel.fare` 作为主 score；
- best pair 选择：先按 `local_revenue_score` 降序，再按 detour/insertion 便利性降序或增量距离升序稳定打破平局；
- 阈值：`T_h = omega * sum(pair.local_revenue_score for pair in all_feasible_pairs) / len(all_feasible_pairs)`；
- `ThresholdHistory` 字段从 `utility_sum` 语义改为 `score_sum`，或者新增 revenue-specific history，避免继续把收益阈值命名为 utility。

## 发现 4：plotting 逻辑需要改

`experiments/plotting.py` 当前存在两处不符合要求：

- BPT 标签写成 `"Balance Per Task"`：`experiments/plotting.py:21-25`，应改为 `"Batch Process Time"`。
- `save_comparison_plots()` 对所有 metric 使用完整 `summary["algorithms"]`：`experiments/plotting.py:98-115`。
- `save_default_comparison_plots()` 也对所有 metric 使用完整算法列表：`experiments/plotting.py:118-143`。

目标规则：

- BPT、TR、CR 图中都不包括 `basegta`。
- BPT 图中额外不包括 `mra`。
- 因此：
  - TR/CR 图：排除 `basegta`。
  - BPT 图：排除 `basegta` 和 `mra`。

## 修改计划

### 阶段 1：RAMCOM payment 诊断与对齐

修改文件：

- `baselines/ramcom.py`
- `baselines/gta.py`
- `algorithms/summary_utils.py`
- `tests/test_metric_alignment.py`
- 新增或更新诊断输出文档：`docs/review_0515_result.md`

步骤：

1. 增加测试：同一 task、同一 outer candidate，比较 RAMCOM 当前 `outer_payment / fare` 与 GTA AIM `payment / fare`。
2. 增加测试：RAMCOM cross TR 只能来自 delivered task，且每个 task 只计一次。
3. 在 RAMCOM/GTA 结果中加入诊断字段：`cross_payment_total`、`cross_fare_total`、`avg_cross_payment_ratio`、`cross_local_revenue_total`。
4. 跑小样本诊断，确认 RAMCOM 是否因 payment ratio 过低导致 TR 偏高。
5. 若确认，修改 RAMCOM 的 CPUL 适配 payment：保留 RamCOM 的任务选择和接受逻辑，但最终 TR settlement 必须使用统一合作支付口径。建议方案是将 accepted outer worker 交给统一 payment evaluator，至少不得低于统一 dispatch cost / platform payment 下界。
6. 重新跑测试并记录修复前后诊断差异。

测试点：

- `pytest tests/test_metric_alignment.py -k "ramcom or gta" -v`
- 小样本 `python -m experiments.run_chengdu_exp1_num_parcels --preset smoke ...`，检查 `avg_cross_payment_ratio`。
- 重新生成 Exp1/Exp2/Exp3 后确认 RAMCOM 不再稳定高于 ImpGTA。

提交点：

- `test(ramcom): expose cross payment ratio mismatch`
- `fix(ramcom): align cross settlement payment with baselines`
- `docs: record ramcom payment diagnosis`

### 阶段 2：deadline 参数化并统一入口

修改文件：

- `Tasks_ChengDu.py`
- `env/chengdu.py`
- `experiments/config.py`
- `experiments/sweep.py`
- `experiments/paper_chengdu.py`
- `rl_capa/env.py` 如需显式传递或记录 deadline 参数
- `tests/test_chengdu_task_loading.py`
- `tests/test_deadline_delivery_accounting.py`
- `tests/test_deadline_disturbance.py`
- `tests/test_rl_env_smoke.py`

步骤：

1. 在 `ExperimentConfig` 增加 `deadline_seconds`，默认使用正式实验指定值。
2. 在 `build_framework_chengdu_environment()` 增加 `deadline_seconds` 参数。
3. 在读取并抽样任务后统一执行 `task.d_time = task.s_time + deadline_seconds`；partner own-task streams 也必须同样处理。
4. 保留原始数据 deadline 到 `raw_d_time` 或 `dataset_d_time`，只用于审计，不参与算法。
5. 更新 `as_environment_kwargs()`、CLI 参数、fixed config、manifest 输出。
6. 检查 deadline disturbance 实验：`deadline_delay` 仍应只改 observed release；`deadline_noise` 应围绕参数化后的 true deadline 生成 observed deadline。
7. 确认 RL-CAPA environment clone 后仍携带参数化 deadline。

测试点：

- 构造任务 `s_time=100, raw d_time=9999, deadline_seconds=300`，断言 `get_true_deadline(task)==400`。
- CAPA batch 等待测试：release=0, deadline_seconds=100, batch=90, pickup travel 后超时，TR=0。
- 返回 station 测试：pickup 在 deadline 前完成但回站在 deadline 后，不应变成 timeout。
- RL-CAPA smoke：accepted but late 的 reward 仍为 0。

提交点：

- `feat(env): parameterize chengdu task deadlines`
- `test(deadline): cover batch wait pickup and return semantics`
- `fix(rl): propagate configured deadline semantics`

### 阶段 3：CAPA 本地收益阈值替换 utility

修改文件：

- `capa/utility.py`
- `capa/models.py`
- `capa/cama.py`
- `capa/config.py`
- `algorithms/capa_runner.py`
- `rl_capa/env.py`
- `tests/test_capa_local.py`
- `tests/test_capa_config.py`
- `tests/test_chengdu_shortlist_runtime.py`

步骤：

1. 新增 `calculate_local_revenue_score(parcel, config)`，返回 `(1 - zeta) * parcel.fare`。
2. 新增收益阈值函数：`calculate_local_revenue_threshold(pair_scores, omega)`。
3. 将 `CandidatePair` 中的主比较字段从 `utility.value` 切换为 local revenue score；若保留 `UtilityEvaluation`，只能作为 tie-break / 插入位置记录。
4. 更新 `ThresholdHistory` 语义，累计 pair 的 local revenue score，而不是 capacity/detour utility。
5. `run_cama()` 中：
   - all feasible pairs 仍枚举不变；
   - best pair 对每个 parcel 按 revenue score 选主项；
   - threshold 用所有 feasible pair 的 revenue score；
   - `pair.score >= threshold` 进入 local，否则进入 DAPA。
6. 保留 DAPA 与后续流程不变。
7. 更新配置文档和 runner 参数说明，弱化或移除 `utility_balance_gamma` 对 local threshold 的影响，避免 CLI 暴露一个不再参与主决策的参数。

测试点：

- 两个 parcel：低 fare 但 detour 好，高 fare 但 detour 稍差，旧 utility 会选低 fare，新逻辑必须保留高 fare local。
- 阈值测试：给定 fares `[10, 20, 30]`、`zeta=0.2`、`omega=1.0`，阈值应为 `16.0`。
- threshold history 跨 batch 累计收益均值。
- RL-CAPA `apply_capa_batch()` 走同一 CAMA 后测试通过。

提交点：

- `test(cama): specify revenue-based local threshold`
- `fix(cama): replace utility threshold with local revenue score`
- `fix(rl): use revenue-based CAMA through shared modules`

### 阶段 4：plotting 过滤与标签修复

修改文件：

- `experiments/plotting.py`
- 新增或更新 `tests/test_plotting.py`

步骤：

1. 将 BPT 标签改为 `Batch Process Time`。
2. 增加 helper：`visible_algorithms_for_metric(metric_name, algorithms)`。
3. 对 `save_comparison_plots()` 应用过滤：
   - `basegta` 对 TR/CR/BPT 全部过滤；
   - `mra` 仅对 BPT 过滤。
4. 对 `save_default_comparison_plots()` 应用同一过滤。
5. 添加测试，不必真实画图，可 patch `_save_line_plot()` 检查 series 算法列表。

测试点：

- TR series 不含 `basegta`，含 `mra`。
- CR series 不含 `basegta`，含 `mra`。
- BPT series 不含 `basegta` 和 `mra`。
- `METRIC_LABEL["BPT"] == "Batch Process Time"`。

提交点：

- `fix(plot): correct bpt label and filter baselines`

### 阶段 5：回归与正式实验重跑

步骤：

1. 运行 targeted tests：
   - `pytest tests/test_metric_alignment.py -k "ramcom or gta" -v`
   - `pytest tests/test_deadline_delivery_accounting.py tests/test_deadline_disturbance.py -v`
   - `pytest tests/test_capa_local.py tests/test_chengdu_shortlist_runtime.py -v`
   - `pytest tests/test_plotting.py -v`
2. 运行更广的 smoke：
   - `pytest tests/test_rl_env_smoke.py tests/test_summary_disposition_fields.py -v`
3. 重新生成 Exp1/Exp2/Exp3 formal CD 结果。
4. 重新生成 plots 和 `result.md`。
5. 在 `docs/review_0515_result.md` 写入：
   - RAMCOM/ImpGTA 修复前后 TR 对比；
   - cross payment ratio 对比；
   - deadline 参数值；
   - plotting 输出检查。

提交点：

- `experiment: rerun formal cd sweeps after revenue and deadline fixes`
- `docs: summarize review 0515 fixes and results`

## 当前不直接修改代码的原因

本轮用户要求是“审查思考结果，以及对应的修改计划步骤、测试点、提交点”写入 `docs/review_0515.md`。RAMCOM 的异常需要先用 payment ratio 诊断锁定根因，再修改 settlement；deadline 参数化和 CAMA 阈值替换会影响所有正式实验和 RL-CAPA，必须按上述测试顺序推进，避免把多个行为变化混在一个不可解释的实验结果里。
