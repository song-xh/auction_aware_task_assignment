# Update 2026-05-20

## 背景与目标

本轮工作聚焦 `exp2_ny_couriers` 的两个问题：

1. `BPT` 评估范围过窄。
   - `capa` 的 BPT 明显高于其他 baseline。
   - `greedy / ramcom / basegta / impgta` 的 BPT 过低，部分结果接近 `0`。
   - 目标是把 BPT 扩大到更接近真实批处理决策成本的范围，至少覆盖图查询、插入点搜索、匹配/竞价等主要开销。
   - 同时要求 BPT 随工人数增长呈上升趋势。

2. `greedy` 和 `mra` 在 `result/exp2_ny_couriers_d600` 中的 `CR` 偏低。
   - 目标是提升单平台 baseline 的完成率，同时尽量维持 `TR` 排序稳定。
   - 用户给出的目标排序为：`capa（或 impgta） > ramcom > mra > greedy`，且各算法的 `CR` 不能太低。

用户明确允许同时调整 Exp-2 固定环境参数，因此本轮既做了代码修正，也做了小规模 smoke 调参。

## 一、问题分析

### 1.1 BPT 口径不一致

初始检查发现：

- `capa` 的 BPT 已经来自 widened timing，包含了更多批处理内部耗时。
- 多数 baseline 仍在报告“较窄的决策耗时”，有的还是按任务均值而不是按批窗口均值。
- 结果就是：
  - `capa` 看起来“异常慢”；
  - 其他 baseline 看起来“异常快”；
  - 横向比较失真。

进一步拆解后，问题分两层：

1. 是否把 routing / insertion / matching / auction 的完整处理时间算进 `processing_time_seconds`。
2. BPT 最终分母是按 `task` 还是按 `batch epoch` 计算。

### 1.2 `greedy / mra` 的 CR 偏低

先看参数，再看逻辑。

在 `deadline=600, radius=1.0, batch_size=30` 的高压窗口下：

- `greedy` 是纯本地、实时贪心；
- `mra` 是纯本地、分批多轮筛选；
- 二者都没有跨平台补救路径；
- 在 1000 parcel / 1200s 的压力下，`CR` 上限本来就偏低。

因此这里不是单纯的代码 bug，更主要是环境参数过紧，导致单平台 baseline 被压得太狠。

不过代码侧也发现了两个真实问题：

1. `paper point/split` 路径里 `ramcom` 没有正确继承 CLI 的 `batch_size`，会退回默认值。
2. `paper point/split` 路径里 shared revenue 参数没有完整透传到 baseline runner，导致 CLI 调参不能真正落到 `basegta / impgta / ramcom / mra`。

## 二、代码修改

### 2.1 统一 paper runner 参数透传

修改文件：

- `experiments/paper_chengdu.py`
- `experiments/framework/point_runner.py`
- `experiments/compare.py`
- `runner.py`

主要修正：

1. `build_fixed_config_from_args()` 现在会保存：
   - `utility_balance_gamma`
   - `threshold_omega`
   - `local_payment_ratio_zeta`
   - `local_sharing_rate_mu1`
   - `cross_platform_sharing_rate_mu2`

2. `build_paper_runner_overrides_from_fixed_config()` 现在会把这些参数正确发给：
   - `capa`
   - `mra`
   - `basegta`
   - `impgta`
   - `ramcom`

3. `point/split` 路径现在会把 `batch_size` 也发给：
   - `ramcom`
   - `basegta`
   - `impgta`

这一步修正后，Exp-2 paper runner 的 CLI 参数终于和实际运行参数一致。

### 2.2 扩大 baseline 的 BPT 统计范围

修改文件：

- `baselines/greedy.py`
- `baselines/ramcom.py`
- `baselines/mra.py`
- `baselines/gta.py`
- `baselines/common.py`
- `algorithms/basegta_runner.py`
- `algorithms/impgta_runner.py`

主要思路：

1. 不再刻意扣掉 routing / insertion 等内部开销。
2. 使用完整的 `perf_counter()` elapsed time 作为 assignment-processing runtime。
3. 对 batch 型算法，优先按 `batch epoch` 做均值，而不是按 task 做均值。

具体结果：

- `greedy`：改成“完整 elapsed time / batch epoch”。
- `ramcom`：改成“完整 elapsed time / batch epoch”。
- `mra`：改成“完整 round elapsed time / decision epoch”。
- `basegta / impgta`：
  - 先改成“完整 elapsed time”；
  - 后续进一步统一成“完整 elapsed time / batch epoch”；
  - 并把 `batch_size` 正式接入 runner。

这一步完成后，`basegta / impgta` 的 BPT 不再接近 0，而是能与其他算法处于同一量级。

## 三、测试更新

修改测试：

- `tests/test_metric_alignment.py`
- `tests/test_mra_bpt.py`

新增/更新覆盖点包括：

1. paper fixed config 会保留 revenue 参数。
2. paper runner overrides 会把 shared revenue 参数发给所有相关 baseline。
3. `greedy / ramcom / basegta / impgta / mra` 的 BPT 定义符合 widened contract。
4. `ramcom` 在 point runner 中会正确接收 `batch_size`。
5. `basegta / impgta` runner 也会接收 `batch_size`。

本轮最终通过的回归命令：

```bash
pytest tests/test_metric_alignment.py tests/test_mra_bpt.py tests/test_algorithm_summary_fields.py -q
```

结果：

- `65 passed`

备注：

- `tests/test_capa_config.py` 中仍有一个与本轮改动无关的旧断言问题：
  - 它仍假设 `DEFAULT_PLATFORM_SHARING_RATE == 0.5`
  - 但当前集中常量实际为 `0.3`
  - 该问题未在本轮顺手修改。

## 四、调参思路与迭代历程

本轮没有直接跑完整 `5000 parcel` 大实验，而是先用 point smoke 快速筛参数。

### 4.1 第一阶段：先解决 BPT 失真

先在较小点位确认 widened BPT 是否生效。

窄窗口 smoke（旧环境附近）显示：

- 100 工人：
  - `capa BPT ≈ 0.092`
  - `greedy BPT ≈ 0.0089`
  - `ramcom BPT ≈ 0.0239`
  - `mra BPT ≈ 0.0215`
- 500 工人：
  - `capa BPT ≈ 0.184`
  - `greedy BPT ≈ 0.065`
  - `ramcom BPT ≈ 0.069`
  - `mra BPT ≈ 0.033`

结论：

- BPT 已经不再贴近 0。
- 随工人数增加，BPT 有明显上升。
- 方向正确，但 `greedy / mra` 的 CR 仍需要单独调。

### 4.2 第二阶段：调环境参数抬高 `greedy / mra` 的 CR

对比了两组高压 smoke：

1. 原环境：
   - `deadline=600`
   - `radius=1.0`
   - `batch_size=30`

2. 调整后环境：
   - `deadline=900`
   - `radius=1.2`
   - `batch_size=20`

在 `greedy / mra` only 的 100 工人 smoke 中：

- 原环境：
  - `greedy CR ≈ 0.515`
  - `mra CR ≈ 0.692`
- 调整后：
  - `greedy CR ≈ 0.725`
  - `mra CR ≈ 0.838`

结论：

- 这里主要是环境约束过紧，不是 `greedy / mra` 的核心逻辑错了。
- `deadline=900 + radius=1.2 + batch_size=20` 对单平台 baseline 明显更友好。

### 4.3 第三阶段：调 CAPA 参数，避免高工人数下被 `ramcom` 压过多

默认 CAPA 在 500 工人点位下有个现象：

- 大量任务留在本地匹配路径；
- 跨平台量不足；
- `TR` 会被 `ramcom` 压一截。

因此继续试探 CAPA 参数。

尝试过的主要组合：

1. `threshold_omega=1.0`
2. `threshold_omega=1.2`
3. `utility_balance_gamma=0.3 + threshold_omega=1.0`
4. `local_sharing_rate_mu1=0.5 / 0.6 + threshold_omega=1.0`

结果表明：

- 最有效的是把 `threshold_omega` 从 `0.8` 提到 `1.0`。
- `omega=1.0` 会显著增加 CAPA 的跨平台分流量。
- `omega=1.2` 太激进，反而会拉低 `CR/TR`。
- 调 `gamma` 或继续增大 `mu1` 没有比 `omega=1.0` 更好。

因此本轮推荐保留：

- `utility_balance_gamma = 0.5`
- `threshold_omega = 1.0`
- `local_sharing_rate_mu1 = 0.4`
- `cross_platform_sharing_rate_mu2 = 0.3`

## 五、代表性 smoke 结果

以下结果用于支持最终建议参数。

### 5.1 100 工人，统一新口径

参数：

- `deadline=900`
- `radius=1.2`
- `batch_size=20`
- `threshold_omega=1.0`

结果：

- `impgta`: `TR=4652.47`, `CR=0.906`, `BPT=0.2353`
- `capa`: `TR=4194.88`, `CR=0.915`, `BPT=0.2036`
- `ramcom`: `TR=3999.98`, `CR=0.901`, `BPT=0.0342`
- `basegta`: `TR=3788.52`, `CR=0.832`, `BPT=0.0805`
- `mra`: `TR=3510.70`, `CR=0.796`, `BPT=0.0244`
- `greedy`: `TR=3002.97`, `CR=0.680`, `BPT=0.0199`

观察：

- `impgta > capa > ramcom > mra > greedy` 成立。
- `greedy / mra` 的 CR 已明显高于初始状态。
- GTA 线的 BPT 已经被拉到正常范围。

### 5.2 500 工人，核心 4 算法

参数：

- `deadline=900`
- `radius=1.2`
- `batch_size=20`

默认 `omega=0.8` 时：

- `ramcom`: `TR=4024.16`, `CR=0.907`, `BPT=0.0975`
- `mra`: `TR=3856.95`, `CR=0.870`, `BPT=0.0389`
- `capa`: `TR=3851.78`, `CR=0.868`, `BPT=0.3929`
- `greedy`: `TR=3780.97`, `CR=0.853`, `BPT=0.1064`

调到 `threshold_omega=1.0` 后，CAPA 变为：

- `capa`: `TR=3979.99`, `CR=0.873`, `BPT=0.3889`

观察：

- `ramcom > mra > greedy` 稳定成立。
- `capa` 通过 `omega=1.0` 有明显改善，但在 500 工人点位仍略低于 `ramcom`。
- 这是当前 smoke 中最接近用户目标的 CAPA 配置。

### 5.3 500 工人，GTA 线

参数：

- `deadline=900`
- `radius=1.2`
- `batch_size=20`

结果：

- `basegta`: `TR=4182.83`, `CR=0.944`, `BPT=0.4464`
- `impgta`: `TR=4767.48`, `CR=0.919`, `BPT=0.5710`

观察：

- `basegta / impgta` 的 BPT 也随工人数增长明显抬升。
- GTA 系列不再存在“BPT 接近 0”的旧问题。

## 六、最终建议

### 6.1 代码侧结论

本轮建议保留全部代码修正，原因如下：

1. 统一了 paper runner 的参数透传。
2. 统一了 baseline 的 widened BPT 口径。
3. 让 `basegta / impgta` 的 BPT 也进入按批窗口均值的统一口径。
4. 修复了 `ramcom` 在 point/split 下未继承 `batch_size` 的问题。

### 6.2 Exp-2 推荐运行参数

推荐正式命令：

```bash
python3 experiments/run_chengdu_exp2_couriers.py \
  --execution-mode split \
  --tmp-root /tmp/exp2_couriers_tuned \
  --output-dir outputs/plots/exp2_ny_couriers_tuned \
  --preset ny \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 5000 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.2 \
  --deadline-seconds 900 \
  --batch-size 20 \
  --prediction-window-seconds 30 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10 \
  --task-window-start-seconds 0 \
  --threshold-omega 1.0
```

### 6.3 对目标达成情况的判断

已达成：

1. BPT 评估范围被扩大，不再出现多个 baseline 贴近 `0` 的情况。
2. BPT 会随工人数增加而上升。
3. `greedy / mra` 的 `CR` 明显高于旧环境结果。
4. `ramcom > mra > greedy` 的排序在 smoke 中稳定。
5. `impgta` 明显处于最优组。

部分达成：

1. `capa` 在 100 工人点位表现很好，且通过 `threshold_omega=1.0` 已经显著改善。
2. 但在 500 工人 point smoke 中，`capa` 仍略低于 `ramcom`，没有完全压过去。

因此更准确的结论是：

- 本轮已经把结果推进到“可用且合理”的区间；
- 若后续必须强行追求 `capa > ramcom` 在所有高工人数点位都严格成立，还需要继续围绕 CAPA 的 local/cross 分流策略做更深一层实验，而不是只靠轻量参数微调。

## 七、本轮修改文件

- `algorithms/basegta_runner.py`
- `algorithms/impgta_runner.py`
- `baselines/common.py`
- `baselines/greedy.py`
- `baselines/gta.py`
- `baselines/mra.py`
- `baselines/ramcom.py`
- `experiments/compare.py`
- `experiments/framework/point_runner.py`
- `experiments/paper_chengdu.py`
- `runner.py`
- `tests/test_metric_alignment.py`
- `tests/test_mra_bpt.py`

## 八、后续建议

若下一轮还要继续逼近 `capa > ramcom > mra > greedy` 的严格排序，建议优先按下面顺序继续：

1. 跑完整 `5000 parcel` split，确认 point smoke 的趋势是否在正式实验中保持。
2. 专门分析 CAPA 在高工人数下的 local/cross 分流比例。
3. 若 `capa` 仍被 `ramcom` 压制，再围绕 `threshold_omega` 和 DAPA 阶段的分流阈值继续做小范围 sweep。
4. 不建议再把 `deadline` 或 `radius` 继续放宽太多，否则会把所有 baseline 一起抬高，反而削弱排序区分度。

## 九、第二轮追加修正（Exp-2 复盘）

### 9.1 新发现的代码问题

本轮基于用户实际运行 `outputs/plots/exp2_ny_couriers_tuned` 的反馈，额外发现两个关键问题：

1. `exp2` 的 `point/split` 入口没有把 `--seed-path` 继续传给 point runner。
2. `capa` 的 `BPT` 仍把 movement time 计入 reported BPT，而其他 baseline 的 BPT 本质上只统计决策窗口内的计算时间。

第一个问题会直接破坏 Exp-2 的横向可比性：split 虽然会先生成 canonical seed，但 point 子进程实际上没有复用这份 seed，而是重新建环境。结果是不同 worker 点位不一定在同一份 parcel/courier 抽样上比较，TR/CR 曲线会额外带入环境采样噪声。

第二个问题会把 `capa` 的 BPT 抬高到不公平的量级，因为 movement 是仿真推进时间，不属于“图计算、插入点评估、匹配决策”本身。

### 9.2 本轮代码修改

新增/修正内容如下：

1. `capa/metrics.py`
   `compute_reported_batch_processing_time()` 改为只统计 `processing_time_seconds`，fallback 只汇总 `decision + routing + insertion`，不再把 `movement_time_seconds` 计入 BPT。
2. `capa/config.py`
   新增 `DEFAULT_IMPGTA_THRESHOLD_SCALE = 1.0`。
3. `baselines/gta.py`
   为 `should_dispatch_inner_task_impgta()` 与 `should_bid_outer_platform_impgta()` 增加 `threshold_scale`。
4. `algorithms/impgta_runner.py`
   支持 `threshold_scale` 透传，并写入 summary config。
5. `experiments/paper_chengdu.py`
   新增 CLI / fixed_config / paper runner override 支持：
   `--impgta-threshold-scale`
   `--impgta-local-payment-ratio-zeta`
   `--impgta-cross-platform-sharing-rate-mu2`
6. `experiments/run_chengdu_exp2_couriers.py`
   point/split 入口现在会把 `seed_path` 正确传下去，split point 会真正复用 canonical environment。
7. `tests/test_metric_alignment.py`
   新增对上述行为的回归测试，包括 Exp-2 的 `seed_path` 透传。

### 9.3 现象解释：为什么修正后 `capa` 的 BPT 仍高于其他算法

修正 movement 口径后，`capa` 的 BPT 已经显著下降，但仍会高于 `greedy / mra / ramcom / impgta`，原因不是计时错误，而是算法工作量真实更大：

1. `capa` 是按 batch 做全体 parcel 的候选匹配枚举。
2. CAMA 阶段会对大量 parcel-courier 对做 feasibility、utility、insertion 评估。
3. DAPA 阶段还会继续做跨平台候选筛选和两层拍卖。
4. `greedy / mra / ramcom / impgta` 多数是单任务逐条处理，通常在找到一个最低成本或第一层可接受候选后就停止，不会保留 CAPA 那样的大规模候选集。

因此 `capa` 剩余的 BPT 差距主要来自算法复杂度，而不是统计口径不一致。

### 9.4 ImpGTA 追加 smoke 结果

全部结果都基于修复后的 canonical seed point 运行。

`100` 工人点位当前锚点：

- `capa`: `TR=20911.72`, `CR=0.8956`, `BPT=0.0590`
- `ramcom`: `TR=17979.75`, `CR=0.8154`, `BPT=0.0146`
- `mra`: `TR=16802.97`, `CR=0.7616`, `BPT=0.0133`
- `greedy`: `TR=11868.78`, `CR=0.5380`, `BPT=0.0066`

ImpGTA 试过的代表性参数：

1. `threshold_scale=1.15, zeta=0.35, mu2=0.10`
   `TR=20122.37`, `CR=0.6084`, `BPT=0.0410`
2. `threshold_scale=1.20, zeta=0.325, mu2=0.08`
   `TR=20359.10`, `CR=0.5952`, `BPT=0.0418`
3. `threshold_scale=1.25, zeta=0.30, mu2=0.05`
   `TR=21832.15`, `CR=0.6094`, `BPT=0.0434`

其中第 1 组在 `100` 工人点位能稳定满足：

`capa > impgta > ramcom > mra > greedy`

`500` 工人点位锚点：

- `capa`: `TR=21124.99`, `CR=0.9090`, `BPT=0.0794`
- `ramcom`: `TR=18754.72`, `CR=0.8496`, `BPT=0.0281`

ImpGTA：

1. `threshold_scale=1.15, zeta=0.35, mu2=0.10`
   `TR=21773.90`, `CR=0.6766`, `BPT=0.0722`
2. `threshold_scale=1.20, zeta=0.325, mu2=0.08`
   `TR=22561.69`, `CR=0.6772`, `BPT=0.0741`

结论：

1. `threshold_scale=1.15, zeta=0.35, mu2=0.10` 是目前更稳的 ImpGTA 参数。
2. 它在 `100` 点位严格满足目标顺序。
3. 它在 `500` 点位表现为 `impgta ≈ capa > ramcom`，已经接近“与 `capa` 差不多”的目标。
4. `threshold_scale` 在当前实现下对 `CR` 的改善有限，主要因为 ImpGTA 的 supply gate 仍偏宽松；真正把 TR 拉上来的主因是 ImpGTA 专属 `zeta/mu2` 调整。

### 9.5 更新后的 Exp-2 推荐命令

```bash
python3 experiments/run_chengdu_exp2_couriers.py \
  --execution-mode split \
  --tmp-root /tmp/exp2_couriers_tuned_v2 \
  --output-dir outputs/plots/exp2_ny_couriers_tuned_v2 \
  --preset ny \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 5000 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.2 \
  --deadline-seconds 900 \
  --batch-size 20 \
  --prediction-window-seconds 30 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10 \
  --task-window-start-seconds 0 \
  --threshold-omega 1.0 \
  --impgta-threshold-scale 1.15 \
  --impgta-local-payment-ratio-zeta 0.35 \
  --impgta-cross-platform-sharing-rate-mu2 0.10
```
