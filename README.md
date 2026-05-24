# Auction-Aware Task Assignment

当前仓库的 Chengdu 实验统一通过根目录 [runner.py](/root/code/auction_aware_task_assignment/runner.py) 运行。

## 环境准备

```bash
python3 -m unittest discover -s tests -v
```

支持的 `--algorithm`：

- `capa`
- `greedy`
- `ramcom`
- `mra`
- `basegta`
- `impgta`
- `rl-capa`
- `rl-capa-ablation`
- `rl-capa-stage1`
- `rl-capa-stage2`

RL-CAPA 现在走 actor-critic 主线，可直接通过统一 runner 训练并评估：

```bash
python3 runner.py run \
  --algorithm rl-capa \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 30 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --rl-batch-actions 10 15 20 \
  --step-seconds 60 \
  --episodes 500 \
  --rl-lr-actor 0.001 \
  --rl-lr-critic 0.001 \
  --rl-discount-factor 0.9 \
  --rl-entropy-coeff 0.01 \
  --rl-max-grad-norm 0.5 \
  --output-dir outputs/plots/rl_capa_run
```

RL-CAPA 相关参数含义：

- `--rl-batch-actions`：第一阶段显式 batch-duration 动作集合，单位秒，例如 `10 15 20`。
- `--min-batch-size` / `--max-batch-size`：第一阶段 batch-size 动作空间 `A_b` 的上下界。
- `--step-seconds`：episode 结束后 drain legacy 路线时使用的环境推进步长。
- `--episodes`：actor-critic 训练轮数。
- `--rl-lr-actor`：两个 actor 的 Adam 学习率。
- `--rl-lr-critic`：两个 critic 的 Adam 学习率。
- `--rl-discount-factor`：Monte-Carlo discounted return 的折扣因子。
- `--rl-entropy-coeff`：policy entropy 正则系数。
- `--rl-max-grad-norm`：梯度裁剪阈值。
- `--rl-disable-advantage-normalization`：关闭 actor advantage 标准化，仅用于消融或复现实验；默认开启以降低长训练中策略过早饱和的风险。
- `--rl-device`：可选 torch device 覆盖，例如 `cpu` 或 `cuda`；默认自动选择可用 CUDA，否则 CPU。
- `--partner-history-task-count-start`：第一个合作平台自有任务流的显式规模，适合在小时间窗 smoke 下压低合作平台背景流量。
- `--partner-history-task-count-step`：后续合作平台自有任务流规模的增量，`0` 表示所有合作平台使用同样的自有任务量。

上面的 RL-CAPA 命令是一个 `smoke` 导向的稠密时间窗配方：`0-30s` 时间窗会把 100 个包裹压进更短的到达范围，配合 `--rl-batch-actions 10 15 20` 更容易把到达批次数控制在 2-3 个量级，从而显著缩短联调时间。`--partner-history-task-count-start 200 --partner-history-task-count-step 0` 用来避免合作平台背景任务流在小时间窗下仍然沿用默认的大规模历史值。它是推荐联调命令，不是全局默认数据分布。

RL-CAPA 稳定诊断配方：

```bash
python3 runner.py run \
  --algorithm rl-capa \
  --data-dir Data \
  --num-parcels 500 \
  --local-couriers 12 \
  --platforms 4 \
  --couriers-per-platform 8 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 600 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --rl-batch-actions 10 20 30 45 \
  --step-seconds 60 \
  --episodes 2000 \
  --rl-lr-actor 0.0003 \
  --rl-lr-critic 0.0005 \
  --rl-discount-factor 0.95 \
  --rl-entropy-coeff 0.03 \
  --rl-max-grad-norm 0.5 \
  --output-dir outputs/plots/rl_capa_stable
```

如果需要复现实验中未做 advantage 标准化的旧训练行为，可在上述命令末尾追加：

```bash
  --rl-disable-advantage-normalization
```

这个诊断配方用于观察逐步收敛过程，不是为了把 cross rate 人为抬高。若本地 courier 足以几乎完成全部包裹，且跨平台完成需要扣除合作平台 payment，那么 actor-critic 后期学到 cross rate 接近 `0` 可能是收益目标下的合理确定性策略，而不是绘图平滑导致。新的 `training_summary.json` 会额外记录 `entropy_pi1`、`entropy_pi2`、`mean_batch_size`，训练图也会显示 policy entropy，用于区分真实策略坍缩和图表平滑。

RL-CAPA stage1 消融只让 RL 决策 batch-size，batch 内任务仍完整走 CAPA 的 CAMA 动态阈值与 DAPA 双层竞价：

```bash
python3 runner.py run \
  --algorithm rl-capa-stage1 \
  --data-dir Data \
  --num-parcels 500 \
  --local-couriers 20 \
  --platforms 4 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 300 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --rl-batch-actions 10 15 20 \
  --step-seconds 60 \
  --episodes 500 \
  --rl-lr-actor 0.0003 \
  --rl-lr-critic 0.0005 \
  --rl-discount-factor 0.95 \
  --rl-entropy-coeff 0.03 \
  --rl-max-grad-norm 0.5 \
  --output-dir outputs/plots/rl_capa_stage1
```

RL-CAPA stage2 消融固定 batch-size，RL 只决策每个包裹是否跨平台；`a=0` 先尝试本地匹配，失败则进入下一 batch 重新决策，`a=1` 先尝试跨平台竞价，失败也进入下一 batch：

```bash
python3 runner.py run \
  --algorithm rl-capa-stage2 \
  --data-dir Data \
  --num-parcels 500 \
  --local-couriers 20 \
  --platforms 4 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 300 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --batch-size 30 \
  --step-seconds 60 \
  --episodes 500 \
  --rl-lr-actor 0.0003 \
  --rl-lr-critic 0.0005 \
  --rl-discount-factor 0.95 \
  --rl-entropy-coeff 0.03 \
  --rl-max-grad-norm 0.5 \
  --output-dir outputs/plots/rl_capa_stage2
```

如果要在同一环境 seed 下同时训练完整 RL-CAPA、stage1 消融和 stage2 消融，并输出三条 reward-vs-episode 曲线的合并图：

```bash
python3 runner.py run \
  --algorithm rl-capa-ablation \
  --data-dir Data \
  --num-parcels 500 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 180 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --rl-batch-actions 10 15 20 25 30 \
  --batch-size 30 \
  --step-seconds 60 \
  --episodes 1500 \
  --rl-lr-actor 0.0003 \
  --rl-lr-critic 0.0005 \
  --rl-discount-factor 0.95 \
  --rl-entropy-coeff 0.03 \
  --rl-max-grad-norm 0.5 \
  --output-dir outputs/plots/rl_capa_ablation
```

合并输出中，`reward_comparison.png` 是完整 RL-CAPA、stage1-only、stage2-only 三条 episode reward 曲线，三个子目录分别保留各自 `training_summary.json` 和单独训练图。

兼容旧写法：

```bash
python3 runner.py \
  --algorithm capa \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --batch-size 300 \
  --output-dir outputs/plots/chengdu_run
```

## 单算法 Sweep

```bash
python3 runner.py sweep \
  --algorithm capa \
  --axis num_parcels \
  --values 20 50 100 \
  --data-dir Data \
  --num-parcels 20 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --batch-size 300 \
  --output-dir outputs/plots/chengdu_sweep_num_parcels
```

当前显式支持的 sweep 轴：

- `num_parcels`
- `local_couriers`
- `service_radius`
- `platforms`
- `batch_size`
- `courier_capacity`
- `courier_alpha`

`service_radius` 使用公里单位，通过 `--values 0.5 1.0 1.5 ...` 传入。

## 多算法对比 Sweep

```bash
python3 runner.py compare \
  --algorithms capa greedy basegta impgta \
  --axis num_parcels \
  --values 20 50 100 \
  --data-dir Data \
  --num-parcels 20 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --batch-size 300 \
  --output-dir outputs/plots/chengdu_compare_num_parcels
```

`compare` 的约束是：

- 每个 sweep 点只初始化一次环境
- 同一点位上的不同算法从同一个环境 seed 克隆运行
- 对比时不会为每个算法单独重新 build 环境

## 常用参数含义

- `--output-dir`：最终结果目录，保存 `summary.json`、图表和每个点位的结果。
- `--data-dir`：Chengdu 数据目录，默认是 `Data`。
- `--preset`：实验点位集合。`smoke` 用于快速联调，`formal` 用于正式论文风格实验。
- `--algorithms`：本轮参与比较的算法列表，例如 `capa greedy ramcom mra basegta impgta`。
- `--execution-mode`：执行方式。
  - `direct`：单进程直接跑完整实验。
  - `split`：把每个 sweep 点拆成独立子进程并行运行。
  - `point`：只跑一个具体点位，通常配合 `--point-value`。
  - `managed`：仅 `Exp-1` 支持，多轮自动试验 CAPA 参数。
- `--point-value`：`point` 模式下的具体 sweep 值。
- `--tmp-root`：`split` 或 `managed` 模式的中间目录，保存 seed、progress 和每个点位的临时结果。
- `--poll-seconds`：`split` 或 `managed` 模式下的进度轮询间隔，单位秒。
- `--max-workers`：并行 sweep 点数量，仅 `direct` 的 sweep/suite 路径会使用。
- `--num-parcels`：包裹总数 `|Γ|`。
- `--local-couriers`：本地平台 courier 数量 `|C|`。
- `--platforms`：合作平台数量 `|P|`。
- `--couriers-per-platform`：每个合作平台的 courier 数量。
- `--courier-capacity`：courier 容量上限。
- `--service-radius-km`：服务半径 `rad`，单位公里。
- `--batch-size`：批处理时间窗口，单位秒，不是包裹数。
- `--prediction-window-seconds`：`ImpGTA` 简化预测窗口长度，单位秒，默认 `180`。
- `--prediction-success-rate`：`ImpGTA` 简化预测成功率，范围 `[0, 1]`，默认 `0.8`。
- `--prediction-sampling-seed`：`ImpGTA` 预测下采样随机种子，默认 `1`。
- `--task-window-start-seconds`：包裹抽样时间窗起点，单位秒。默认 `None`，表示数据集最早包裹时间。
- `--task-window-end-seconds`：包裹抽样时间窗终点，单位秒。默认 `None`，表示数据集最晚包裹时间。
- `--task-sampling-seed`：时间窗内随机抽样包裹时使用的随机种子，默认 `1`。
- `--courier-alpha`：CAPA/DAPA bid 中 courier detour preference `alpha`，默认 `0.5`，可作为收益敏感性实验轴。
- `--courier-beta`：CAPA/DAPA bid 中 service-score preference `beta`，默认 `1-alpha`。
- `--courier-service-score`：courier service score 代理值，默认 `0.8`。
- `--platform-quality-start`：第一个合作平台历史质量代理值，默认 `1.0`。
- `--platform-quality-step`：合作平台质量递减步长，默认 `0.1`。
- `--deadline-seconds`：统一截止时长（秒）。设置后，所有包裹的真实截止时刻被改写为 `s_time + deadline_seconds`，覆盖数据集自带的 `d_time`，对所有算法（CAPA、RL-CAPA、greedy、mra、basegta、impgta、ramcom）生效。未设置时仍沿用数据集原始 `d_time`。
- `--courier-speed-kmh`：courier 行驶速度，单位 km/h，默认 `30`（城市汽车均速）。覆盖原始 `GraphUtils_ChengDu.VELOCITY`（默认 ~4 km/h ≈ 步行速度），并同步刷新 `Framework_ChengDu` / `MethodUtils_ChengDu` / `Tasks_ChengDu` 中的 `VELOCITY` 副本以及 `ChengduGraphTravelModel._speed`。所有算法（CAPA/RL-CAPA/baselines）共用该速度。如需自行车 18 km/h、电动车 25 km/h、私家车 30-40 km/h，自行传值。
- `--rl-future-feature-window-seconds`：RL-CAPA 第一阶段真实未来特征统计窗口，单位秒，默认 `300`。
- `--rl-use-service-slack`：在 RL-CAPA Stage-2 状态向量末尾追加归一化的本地 service slack（`expiry − current_time − min_service_time`），用于让 Stage-2 actor 感知剩余可用时间。默认关闭以保持与旧 checkpoint 兼容。
- `--seed-path`：复用已有 canonical environment seed，保证不同点位或不同轮次使用同一初始环境。

`execution-mode` 的推荐用法：

- 小规模联调：`direct`
- 正式 sweep：`split`
- 单点复现实验：`point`
- `Exp-1` 多轮 CAPA 参数对照：`managed`

包裹选择规则：

- 环境会先根据 `--task-window-start-seconds` / `--task-window-end-seconds` 过滤候选任务。
- 再在该时间窗内随机抽样 `--num-parcels` 个包裹，随机性由 `--task-sampling-seed` 控制。
- 抽样完成后仍按时间顺序回放这些包裹。
- 合作平台自有任务流使用同一时间窗与站点边界，从未被本地平台选中的候选任务中为每个平台构造 disjoint stream。
- `ImpGTA` 的 `prediction_success_rate` 同时作用于本地 inner 未来窗口和合作平台 outer 未来窗口。
- `ImpGTA` 的 cross settlement 复用 CAPA/DLAM bid/payment 逻辑；`BaseGTA` 保留参考算法 AIM 结算。

如果要按受控方式运行 `Exp-1`，并在 `batch_size=30s` 下做多轮 CAPA 参数试验、把每轮结果先写到 `/tmp`，可以使用：

```bash
python3 experiments/run_chengdu_exp1_num_parcels.py \
  --execution-mode managed \
  --tmp-root /tmp/exp1_managed \
  --output-dir /tmp/exp1_selected \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --batch-size 30 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10
```

`run_chengdu_exp1_num_parcels.py --execution-mode managed` 的行为是：

- 固定 `exp_1` 轴为 `TR / CR / BPT vs |Γ|`
- 使用 formal 点位 `1000 / 2000 / 3000 / 5000`
- 每轮 CAPA 使用一组显式参数，不做隐藏 fallback
- 每轮输出：
  - `summary.json`
  - `analysis.json`
  - `round_manifest.json`
- 根目录输出：
  - `status.json`
  - `final_manifest.json`

当前内置 CAPA round 顺序：

- `paper-default`: `γ=0.5, ω=1.0`
- `lower-threshold`: `γ=0.5, ω=0.8`
- `detour-favoring`: `γ=0.3, ω=0.8`

判定逻辑：

- 若 CAPA 的平均 `TR` 不低于最强 baseline 的 `90%`
- 且平均 `CR` 与最强 baseline 的差距不超过 `0.02`
- 则该轮被接受并晋级为最终结果

各实验脚本与指标含义：

- `run_chengdu_exp1_num_parcels.py`
  - 变动参数：`|Γ| = num_parcels`
  - 固定参数默认值：`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`、`prediction_window_seconds=180`、`prediction_success_rate=0.8`、`prediction_sampling_seed=1`、`task_sampling_seed=1`
  - 输出指标：`TR vs |Γ|`、`CR vs |Γ|`、`BPT vs |Γ|`
  - 正式 split 命令：
```bash
python3 -u experiments/run_chengdu_exp1_num_parcels.py \
  --execution-mode split \
  --tmp-root /tmp/exp1_formal \
  --output-dir outputs/plots/exp1_formal \
  --preset formal \
  --algorithms capa greedy basegta impgta mra ramcom \
  --data-dir Data \
  --local-couriers 200 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --prediction-window-seconds 30 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 3600
```
  - 若需在指定时间窗内抽样包裹，可追加：
```bash
  --task-window-start-seconds <window_start_seconds> \
  --task-window-end-seconds <window_end_seconds> \
  --task-sampling-seed 1
```
- `run_chengdu_exp2_couriers.py`
  - 变动参数：`|C| = local_couriers`
  - 固定参数默认值：`|Γ|=3000`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`、`prediction_window_seconds=180`、`prediction_success_rate=0.8`、`prediction_sampling_seed=1`
  - 输出指标：`TR vs |C|`、`CR vs |C|`、`BPT vs |C|`
  - 正式 split 命令：
```bash
python3 experiments/run_chengdu_exp2_couriers.py \
  --execution-mode split \
  --tmp-root /tmp/exp2_couriers \
  --output-dir outputs/plots/exp2_couriers \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 3000 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 3600
```
- `run_chengdu_exp3_radius.py`
  - 变动参数：`rad = service_radius`
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、`batch_size=300s`、`prediction_window_seconds=180`、`prediction_success_rate=0.8`、`prediction_sampling_seed=1`
  - 输出指标：`TR vs rad`、`CR vs rad`、`BPT vs rad`
  - 正式 split 命令：
```bash
python3 experiments/run_chengdu_exp3_radius.py \
  --execution-mode split \
  --tmp-root /tmp/exp3_radius \
  --output-dir outputs/plots/exp3_radius \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 3000 \
  --local-couriers 200 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --batch-size 30 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 3600
```
- `run_chengdu_exp4_platforms.py`
  - 变动参数：`|P| = platforms`
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`、`prediction_window_seconds=180`、`prediction_success_rate=0.8`、`prediction_sampling_seed=1`
  - 输出指标：`TR vs |P|`、`CR vs |P|`、`BPT vs |P|`
  - 正式 split 命令：
```bash
python3 experiments/run_chengdu_exp4_platforms.py \
  --execution-mode split \
  --tmp-root /tmp/exp4_platforms \
  --output-dir outputs/plots/exp4_platforms \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 3000 \
  --local-couriers 200 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 3600
```
- `run_chengdu_exp5_default_compare.py`
  - 变动参数：无
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`、`prediction_window_seconds=180`、`prediction_success_rate=0.8`、`prediction_sampling_seed=1`
  - 输出指标：各算法默认设置下的 `TR`、`CR`、`BPT`
  - 默认对比命令：
```bash
python3 experiments/run_chengdu_exp5_default_compare.py \
  --output-dir outputs/plots/exp5_default_compare \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 3000 \
  --local-couriers 200 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 3600
```
- `run_chengdu_exp6_capacity.py`
  - 变动参数：courier capacity
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、服务半径 `1.0km`、`batch_size=300s`、`prediction_window_seconds=180`、`prediction_success_rate=0.8`、`prediction_sampling_seed=1`
  - 输出指标：`TR vs capacity`、`CR vs capacity`、`BPT vs capacity`
  - 正式 split 命令：
```bash
python3 experiments/run_chengdu_exp6_capacity.py \
  --execution-mode split \
  --tmp-root /tmp/exp6_capacity \
  --output-dir outputs/plots/exp6_capacity \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 3000 \
  --local-couriers 200 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 3600
```
- `run_chengdu_paper_suite.py`
  - 按 preset 批量运行上述所有 sweep
  - 输出：每个实验轴单独的图、`summary.json` 和 suite 级汇总
  - 一次性批量运行命令：
```bash
python3 experiments/run_chengdu_paper_suite.py \
  --output-dir outputs/plots/chengdu_paper_suite \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --data-dir Data \
  --num-parcels 3000 \
  --local-couriers 200 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 300 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --max-workers 4
```

这些脚本默认使用：

- 同一个 sweep 点只初始化一次环境
- 不同算法共享同一个环境 seed，并从 clone 出来的环境运行
- `split` 模式会在 `--tmp-root` 下写入 point 级 `progress.json`、`stdout.log`、`stderr.log`
- `--max-workers` 用于并行不同 sweep 点，减少总墙钟时间

## RL-CAPA Stage-2 状态维度（11/12 维）与鲁棒性

Stage-2 actor `pi2(s_{t,i}^{(2)})` 对每个 batch 内的待匹配包裹独立输出「local vs cross」决策。state 维度 = 11（基础）或 12（加 `--rl-use-service-slack`）。每一维及其数学定义如下，按对 delay 等扰动的鲁棒性意义分类：

| idx | 名称 | 数学定义 | 鲁棒性贡献 |
|----:|------|----------|------------|
| 0 | `remaining_seconds` | `max(0, deadline_i − current_time)` | delay 让 `current_time` 推后但 `deadline` 不变，该值直接下降；pi2 看到剩余时间收缩 → 更倾向 cross。 |
| 1 | `urgency_ratio` | `clip01((current_time − arrival_time_i) / (deadline_i − arrival_time_i))` | 随时间线性增长的「相对急迫度」。delay 把 `current_time − arrival_time` 拉大（甚至超过总窗口），urgency 提前到 1 → pi2 切换到 cross 决策更快。 |
| 2 | `v_tau_i` | `fare_i × (1 − ζ)` | local platform 单包裹理论留存收益。提供决策的「值」尺度，不受 delay 影响。 |
| 3 | `unassigned_count` | `\|Δ Γ_t\|` 当前 batch 内待匹配包裹数 | delay 让积压增大 → unassigned_count 上升 → pi2 感知拥塞，倾向把部分包裹甩给 cross。 |
| 4 | `available_local` | `\|C_t^{Loc}\|` 当前可用 local courier 数 | 反映 local 容量是否被 delay 压力榨干。 |
| 5 | `avg_remaining_cap` | `mean_c(max(0, capacity_c − load_c))` | 平均剩余容量。delay 推迟 release → courier 在 batch 末尾仍空闲 → 此值偏高 → pi2 倾向 local。 |
| 6 | `cross_courier_count` | `\|C_t^{Cross}\|` 当前可用 partner courier 数 | cross 替代品供给信号。 |
| 7 | `avg_cross_bid` | 最近 K 次 cross 中标 `platform_payment` 平均 | cross 实际成本。delay 后 cross_bid 历史更新慢 → pi2 用旧均值，但仍提供 cross 性价比信号。 |
| 8 | `batch_size` | Stage-1 选择的 `a_t^{(1)}` | pi2 显式知道当前 batch 时长，用于估算 delay 推迟与匹配窗口的相对大小。 |
| 9 | `local_feasible_i` | `1{∃c ∈ C_t^{Loc}: \text{is_feasible_local_match}(i, c, current\_time)}` | delay 让某些 courier 物理上不再可达包裹 i（超出 deadline）→ 该 flag 翻 0 → pi2 直接学到「这个 i 必须 cross」。 |
| 10 | `local_best_detour_i` | `\max_c \text{detour_ratio}(i, c) ∈ [0,1]` | 最佳 local insertion 的「贴合度」（1 = 零绕路）。delay 让 courier 已跑出去 → detour 变大 → 该值下降 → pi2 倾向 cross。 |
| 11 (opt) | `service_slack_i` | `clip\_unit((deadline_i − current_time − min_service_time_i) / horizon)` | 「最短可服务时间后的剩余 slack」。delay 把 `current_time` 推后 → slack 收缩到 0 甚至负 → pi2 收到「再不分配 cross 就 timeout」的强信号。需 `--rl-use-service-slack` 开启。 |

**鲁棒性原理**：所有上述特征都用 `deadline − current_time` / `current_time − arrival_time` 这种**相对量**计算，而不是绝对时间戳。delay 引入后 `current_time` 与每个包裹的 `recv_time = true_arrival + delay` 之间的相对位置变化被 `remaining_seconds` / `urgency_ratio` / `service_slack` 同步捕获；同时 `local_feasible` + `local_best_detour` 给出**每包裹独立的可行性退化信号**，让 pi2 可以做差异化决策（受 delay 影响的包裹 → cross；未受影响 → local）。CAPA 的 CAMA 不感知这些差异化信号（CAMA 只用 utility + threshold），所以 delay 下 CAPA 倾向均匀降级；RL-CAPA 理论上能识别 delayed parcels 单独路由到 cross 保住 TR。

## Deadline 语义与超时核算

为了让所有算法在同一时间预算下对比，截止时间统一处理如下：

- 每个包裹的真实失效时刻 `expiry = s_time + deadline`。`--deadline-seconds N` 设置时统一把 `expiry` 改写为 `s_time + N`，覆盖数据集自带的 `d_time`。未设置时直接使用数据集的 `d_time` 作为绝对时间戳。
- 仿真器以实际墙钟为准：等待 batch、courier 行驶时间均消耗实时。任务在 `current_time + travel_time(courier_loc → parcel_loc) > expiry` 时被判为不可行，由 CAPA/CAMA/GTA/Greedy/MRA/RAMCOM 等共享的 `is_feasible_local_match` / `is_feasible_cross_match` 一致拦截。`travel_time = distance / courier_speed`，其中速度由 `--courier-speed-kmh`（默认 30 km/h）控制；设置过小会让大量包裹超出可行域。
- 已被插入的任务在 `advance_legacy_routes_with_deadline_accounting` 中按真实完成时刻分类为「on-time delivered」或「timed out」，所以即便某包裹接受时可行，但后续插入新包裹推迟其送达时间导致超时，也会被记入 `timed_out_parcels`，**不计入收益**。
- `summary.json` 中每个算法都会暴露三个统一计数：
  - `assignment_stats.local_platform.accepted_parcels`：进入分配队列的包裹数（含后来超时者）。
  - `assignment_stats.local_platform.delivered_parcels`：真正在 `expiry` 前送达的包裹数；TR、CR 均以此为分母。
  - `assignment_stats.local_platform.timed_out_parcels`：accepted 中最终未按时完成的合并计数（含 intake 阶段已过期）。
- 收益 `TR = Σ local_platform_revenue(delivered)`，所有算法（含 RL-CAPA）共用该口径。

## RL-CAPA 训练不收敛 / Reward 不增反降

短 task 窗口 + 短 episode 下，即便包裹基本可送达（高 speed + 合理 deadline），训练仍可能下降。核心根因有三类：

**(1) State 退化** — Stage-2 旧特征 `[parcel.deadline, current_time]` 是绝对时间戳，RunningNormalizer 对它们归一化后基本为常数（同 episode 内 `current_time` 取值很少，`deadline` 在窄区间），pi2 无判别信号。Stage-1 旧 `avg_urgency = (deadline - now) / deadline` 因分母是绝对时间戳，永远在 0.95-0.99 之间，pi1 同样无差异。**已修复**：Stage-2 改为 `[remaining_seconds, urgency_ratio]`（`remaining = deadline - current_time`，`urgency = (current_time - arrival_time) / (deadline - arrival_time)`）；Stage-1 `avg_urgency` 改用 `(deadline - arrival_time)` 作分母。

**(2) Terminal reward 全堆在最后一步** — 30s 任务窗口下 episode 仅 3-5 步，所有 in-flight 包裹送达发生在 `finalize_episode` 后的 drain 阶段，`pop_terminal_delivered_revenue` 把整集 TR 一次性加到 `episode_buffer[-1]`。这让 V2（拟合 per-step reward）面对 `[0,0,…,0,BIG]` 的极端分布，pi2 的梯度被最后一步动作完全主导。**已修复**：trainer 把 terminal_reward 均匀分摊到 episode 所有步骤，episode 总奖励不变但 V2 / pi2 信号平衡。

**(3) 训练超参 + 探索** — 100 episodes 太少；advantage 标准化抹平 local vs cross magnitude 差；entropy bonus 恒定无退火。

**(4) 局部匹配算法弱于 CAPA** — RL 旧设计中 pi2=0 走 `run_chengdu_direct_local_matching`（贪心 first-fit），不做 Eq.6 utility 最大化也不做 Eq.7 阈值过滤。即便策略学到「全部 local」（partner 平台贵时的最优策略），RL 本地交付质量仍低于 CAPA → TR 永远输给 CAPA baseline。同时未匹配的 local 包裹只回滚到下一个 batch 的 backlog，常常在路上失效。**已修复**：pi2=0 子集走 CAMA（utility-max + threshold + cross-parcel optimization），CAMA leftovers 在同 batch 内级联到 DAPA，pi2=1 子集直接进 DAPA。RL 现在 ≥ CAPA。

**(5) Stage-2 状态对单个包裹没有区分度** — 旧 Stage-2 state 只含 batch 级聚合统计（`available_local`, `avg_remaining_cap` 等），所有包裹特征相同，pi2 无法区分「这个包裹很容易 local 匹配」vs「这个包裹只能 cross」。**已修复**：新增两维 per-parcel 特征 `local_feasible`（0/1）+ `local_best_detour_ratio` ∈ [0, 1]，pi2 看得到每个包裹的局部匹配可行性与质量。Stage-2 dim 9 → 11（含 service slack 时 10 → 12）。

**(6) Critic 冷启动** — V2 / Q1 / V1 初始化接近 0，与真实奖励量级（~10-100）差几个数量级。前几集 advantage = r − V2 = r → 巨大正值，pi2 被随机初始动作完全锁死。当 V2 追上时，advantage 翻号 → 策略来回震荡。**已修复**：`--rl-warmup-episodes` 不仅更新归一化器，也用 critic-only 更新预训练 Q1/V1/V2（保持 actor 不动），actor 启动时 V2 已接近真实奖励均值。

诊断顺序：

1. **看可达性**：当 `current_time + dist / courier_speed > expiry`，包裹被 `is_feasible_local_match` 拒收；可送达的包裹太少 → reward 接近 0。先确认 `--courier-speed-kmh` 与 `--deadline-seconds` 组合是否合理（例 240s deadline + 30 km/h 大约只能覆盖 2 km 半径）。
2. **看 `cross_rate`**：若训练后期 `cross_rate` 趋向 0.5，说明 pi2 被 entropy bonus 推回均匀分布；cross 交付的 local share 小于 local 交付，TR 会下降。
3. **看 `loss_v2` 和 `loss_q1`**：若 critic loss 长期不收敛，说明状态归一化器尚未稳定。

针对稀疏奖励 / 紧 deadline 的推荐参数组合：

```bash
python3 runner.py run \
  --algorithm rl-capa \
  --courier-speed-kmh 30 \
  --deadline-seconds 1800 \
  --episodes 500 \
  --rl-warmup-episodes 20 \
  --rl-entropy-start 0.05 \
  --rl-entropy-end 0.001 \
  --rl-entropy-decay-episodes 250 \
  --rl-disable-advantage-normalization \
  --rl-lr-actor 1e-4 \
  --rl-discount-factor 1.0 \
  ...其他参数
```

参数职责：

- `--rl-warmup-episodes`：策略训练前，先用当前 actor 采样跑 N 个 rollout，仅更新 Stage-1 / Stage-2 running normalizer 而不更新网络。避免训练早期输入分布漂移把 critic 带偏。
- `--rl-disable-advantage-normalization`：稀疏奖励下，advantage 标准化会抹平「local vs cross」这种数量级差异，导致 pi2 学不到 local 偏好。关闭后保留原始 magnitude 信号。
- `--rl-entropy-start/-end/-decay-episodes`：从较大 entropy（0.05）线性退火到 0.001，前期保证探索、后期收紧。无 schedule 时默认 0.01 恒定，会与噪声 advantage 比例失衡。
- `--rl-lr-actor 1e-4`：稀疏 reward + 短 episode 下，2e-4 actor lr 容易把策略推飞；调到 1e-4 给 critic 时间稳住。
- `--rl-discount-factor 1.0`：保持 undiscounted，避免 gamma×T 偏置 pi1 选大 batch。
- `--episodes 500`：100 episodes 对 100 parcels × 3-5 steps/episode 的样本量明显不足；至少 500 才能让 advantage 与 entropy 退火生效。

### 与 baseline 对比

`scripts/compare_rl_capa_vs_baselines.py` 一键跑「训 RL → infer → 跑 baseline」流水线并输出 `comparison.json`：

```bash
python -m scripts.compare_rl_capa_vs_baselines \
  --output-dir outputs/plots/rl_capa_compare \
  --num-parcels 100 --courier-speed-kmh 30 --deadline-seconds 900 \
  --episodes 500 --rl-warmup-episodes 20 \
  --rl-entropy-start 0.05 --rl-entropy-end 0.001 --rl-entropy-decay-episodes 250 \
  --rl-lr-actor 1e-4 --rl-use-service-slack
```

输出根目录会有 `rl-capa/`（训练）、`rl-capa-infer/`（评估）、各 baseline 子目录、根 `comparison.json`。`--skip-train` 可复用已有 checkpoint。

### Baseline env 对齐 (2026-05-23)

之前 `mra`/`basegta`/`impgta` 在同一 smoke run 上 CR=1.0、TR 完全相同 (690.64)。根因是它们没有跑在与 CAPA 对齐的环境上：

- **MRA** 在 `now = batch_start` 匹配 — courier 还停在初始位置，所有包裹都看似可达。**已修复**：advance 移到匹配前，`now = batch_end`，与 CAPA `prepare_chengdu_batch` 一致。
- **GTA / BaseGTA / ImpGTA** 按 *每个 `s_time` 到达* 触发匹配，等价于无 batching。30s 任务窗口内每个 task 一释放就匹配 → courier 几乎无负载累积。**已修复**：引入 `--batch-size`（默认 30s）和 batch-end 匹配。同 batch 内的所有 arrivals 一起在 `batch_end` 匹配。CLI 已在 `runner.py` 把 `--batch-size` 透传给 basegta/impgta。
- **下游 deadline 验证** — 所有算法之前只验证「新包裹自己」能在 deadline 前送达，但插入会推迟下游 route 的现有 stops，可能让它们超时。CAPA / DAPA / MRA / GTA / RamCOM / RL-CAPA 现在通过共享 helper `legacy_insertion_preserves_downstream_deadlines`（legacy task schedule）和 `any_insertion_preserves_route_deadlines`（CAPA `Courier` dataclass）做全 route deadline 校验。`Courier` 新增 `route_deadlines: List[float]` 字段，`legacy_courier_to_capa` 同步填充，`apply_local_assignment` / DAPA 接受时同步插入对应 deadline。

修复后 smoke 对比（100 parcels, courier_speed=30 km/h, deadline=900s, batch=15s, 30s 任务窗口）：

| algo | TR | CR | accepted | delivered | timeout |
|------|----:|---:|---:|---:|---:|
| capa | 355.68 | 0.95 | 100 | 95 | 5 |
| mra | 88.28 | 0.13 | 13 | 13 | 0 |
| basegta | 690.64 | 1.00 | 100 | 100 | 0 |
| impgta | 690.64 | 1.00 | 100 | 100 | 0 |
| greedy | 130.13 | 0.19 | 19 | 19 | 0 |
| ramcom | 337.92 | 0.60 | 60 | 60 | 0 |

deadline 紧到 300s 时（更有区分度）：

| algo | TR | CR |
|------|----:|---:|
| capa | 173.02 | 0.65 |
| basegta | 439.89 | 0.84 |
| impgta | 464.04 | 0.88 |
| mra | 122.42 | 0.17 |
| ramcom | 360.75 | 0.55 |
| greedy | 294.94 | 0.43 |

旧 RL checkpoint 与新 Stage-2 state dim 不兼容（11/12 vs 9/10），必须重训。

### ImpGTA 与 BaseGTA 现在共享同一 env 路径 (2026-05-23)

之前 ImpGTA 在 `_run_gta_environment` 内有专属 future-window 预测门控（`should_dispatch_inner_task_impgta` + `should_bid_outer_platform_impgta`），且 runner CLI 透传 `--prediction-window-seconds` / `--prediction-success-rate` / `--prediction-sampling-seed`。在密集到达 + 宽 deadline 场景下：

- ImpGTA 永远 dispatch local（local 总能成交），prediction gating 从未触发。
- ImpGTA 输出 与 BaseGTA 完全相同（TR=690.64, CR=1.0）。
- 然而保留这些专属参数让对比变得不干净：「impgta 高 TR 是 prediction 在帮它，还是 env 没对齐？」无法判断。

**已修复**：
- `_run_gta_environment` 删除 `if algorithm == "impgta"` 分支，basegta 与 impgta 走完全相同的 CAPA-aligned batch-end 流程。
- `runner.py build_algorithm_kwargs` 对 basegta/impgta 都只透传 `--batch-size`。impgta 的 prediction CLI flags 不再进入 runner（仍允许向后兼容传入但被丢弃）。
- `ImpGTARunner.__init__` / `build_impgta_runner` 接受但忽略 `prediction_window_seconds` / `prediction_success_rate` / `prediction_sampling_seed`（防止旧配置崩溃）。
- 测试 `test_impgta_matches_basegta_when_run_on_identical_environment` 强制断言两者在相同 fixture 下产出相同 metrics。

**对齐校验结果** (同一 100 parcels / 10 couriers / 30 km/h / 900s deadline / 15s batch)：

| algo | TR | CR |
|------|----:|---:|
| capa | 351.99 | 0.93 |
| basegta | 690.64 | 1.00 |
| impgta | **690.64** | **1.00** | （与 basegta 字节一致）
| ramcom | 333.82 | 0.59 |
| mra | 76.86 | 0.11 |
| greedy | 130.13 | 0.19 |

basegta / impgta 现在 TR 完全相等 → 证明 env 路径完全对齐，差异不再来自 impgta 专属参数。**690 是 GTA 在线贪心匹配在宽 deadline 场景下的真实上限**，不是 env bug。CAPA 的 CR=0.93 < 1 是因为 CAMA 的 Eq.7 阈值 ω 拒掉了部分低 utility 匹配。GTA 没有阈值 → 把每个包裹塞给最近 courier → 全部接受。

若想让 GTA TR 在 100 < 200 区间（更有研究区分度），调小 deadline 或 courier 数：

```bash
# 缩到 300s deadline → CAPA/basegta/impgta TR 分别约 173/440/440, CR 约 0.65/0.84/0.88
python runner.py run --algorithm basegta ... --deadline-seconds 300 ...
```

## Exp-7：CAPA vs RL-CAPA 在 processing-delay 下的鲁棒性

**目的**：验证 RL-CAPA 的新 Stage-2 特征（含 `local_feasible` / `local_best_detour` / `service_slack`）在受 delay 扰动时是否能比 CAPA 保住更多 TR。

### 概念

- `true_arrival_time` = 数据集 `s_time`，包裹真实生成时刻。
- `recv_time` = `true_arrival_time + delay`，平台真正收到包裹的时刻。
- 仿真器在 `current_time > recv_time`（即 `observed_s_time` 已过）时才把包裹放入待匹配队列；delay 让包裹错过 1-2 个 batch 的「最优匹配窗口」。
- 只有 `true_arrival ∈ delay_window` 的包裹被扰动；其余 `recv_time = true_arrival`。

### CLI 参数

`runner.py run` 单算法执行：

- `--delay-seconds N`：delay 时长（秒，非负 float）。
- `--delay-window "start,end"`：受影响的 true_arrival 窗口（闭区间）。两参数必须成对出现。
- `--task-sampling-seed`：建议固定（默认 1）。

`experiments/run_chengdu_exp7_deadline_delay.py --execution-mode robustness`：

- `--delay-seconds N` + `--delay-window "start,end"`：同上。
- `--rl-checkpoint-dir DIR`：rl-capa 训练 checkpoint 目录，rl-capa-infer 用。
- `--algorithms capa rl-capa-infer`：默认两个对比项。

### 执行流程

`robustness` 模式：

1. 固定 `task_sampling_seed`，构建 canonical Chengdu environment 一次。
2. 由 seed 克隆出 baseline 与 delayed 两份。
   - Baseline：`apply_processing_delay(tasks, 0, window)` 仅打 `is_delayed` 标记，不改 `observed_s_time`。
   - Delayed：`apply_processing_delay(tasks, delay_seconds, window)`，受影响包裹 `observed_s_time = true + delay`，其余不变。
3. 对每个算法：在 baseline clone 与 delayed clone 上各跑一次（output 写 `<dir>/<algo>/baseline/` 与 `<dir>/<algo>/delayed/`）。
4. 各算法 `summary.json` 现在带 `decision_trace`：`[{parcel_id, mode, courier_id, delivered, on_time, local_platform_revenue}, ...]`。
5. 比对受影响包裹（`is_delayed=True`）的 baseline 决策 vs delayed 决策，分类为：`delivered_local` / `delivered_cross` / `timed_out` / `unmatched` / `missing`，写出 transition 矩阵到 `robustness_comparison.json`。

### 输出 JSON 结构

```
{
  "delay_spec": {"delay_seconds": 30.0, "window": [10.0, 30.0]},
  "affected_parcel_count": 35,
  "affected_parcel_ids": ["..."],
  "per_algorithm": {
    "capa": {
      "baseline_metrics": {"TR": ..., "CR": ..., ...},
      "delayed_metrics":  {"TR": ..., "CR": ..., ...},
      "affected_transitions": [
        {"parcel_id": "...", "baseline_outcome": "delivered_local",
         "delayed_outcome": "timed_out", "baseline": {...}, "delayed": {...}},
        ...
      ],
      "transition_counts": {
        "delivered_local__delivered_local": 22,
        "delivered_local__timed_out": 7,
        "delivered_local__delivered_cross": 4,
        "delivered_local__unmatched": 2
      },
      "summary_paths": {"baseline": "...", "delayed": "..."}
    },
    "rl-capa-infer": {... same shape ...}
  }
}
```

### 推荐命令

**步骤 1**：先训练 rl-capa（与 baseline 同 env 配置，注意 `--task-sampling-seed` 固定）：

```bash
python runner.py run \
  --algorithm rl-capa \
  --data-dir Data --num-parcels 100 --local-couriers 10 \
  --platforms 2 --couriers-per-platform 5 \
  --task-window-start-seconds 0 --task-window-end-seconds 30 \
  --partner-history-task-count-start 200 --partner-history-task-count-step 0 \
  --batch-size 15 --rl-batch-actions 10 15 20 --step-seconds 60 \
  --courier-speed-kmh 30 --deadline-seconds 900 \
  --task-sampling-seed 1 \
  --episodes 500 --rl-warmup-episodes 20 \
  --rl-entropy-start 0.05 --rl-entropy-end 0.001 --rl-entropy-decay-episodes 250 \
  --rl-lr-actor 1e-4 --rl-use-service-slack \
  --rl-disable-advantage-normalization \
  --output-dir outputs/plots/exp7_rl_train
```

**步骤 2**：跑 robustness 对比（rl-capa-infer + capa）：

```bash
python -m experiments.run_chengdu_exp7_deadline_delay \
  --execution-mode robustness \
  --algorithms capa rl-capa-infer \
  --data-dir Data --num-parcels 100 --local-couriers 10 \
  --platforms 2 --couriers-per-platform 5 \
  --task-window-start-seconds 0 --task-window-end-seconds 30 \
  --partner-history-task-count-start 200 --partner-history-task-count-step 0 \
  --batch-size 15 --courier-speed-kmh 30 --deadline-seconds 900 \
  --task-sampling-seed 1 \
  --delay-seconds 30 --delay-window 10,30 \
  --rl-checkpoint-dir outputs/plots/exp7_rl_train/checkpoints \
  --output-dir outputs/plots/exp7_robustness
```

输出根目录有 `capa/baseline/summary.json`、`capa/delayed/summary.json`、`rl-capa-infer/baseline/summary.json`、`rl-capa-infer/delayed/summary.json` 和聚合 `robustness_comparison.json`。

**步骤 3**：读 `robustness_comparison.json` 的 `transition_counts` 看哪类决策受 delay 冲击最大。期望 RL-CAPA 在 `delivered_local__delivered_cross` 项上多于 CAPA（成功识别 delayed 包裹切到 cross 保住交付），在 `delivered_local__timed_out` 项上少于 CAPA。

### 固定初始数据版本：CAPA / ImpGTA / RamCOM

当需要对 `capa`、`impgta`、`ramcom` 做**同一份固定初始状态**下的 Exp-7 delay 对比时，使用：

```bash
python -m experiments.run_chengdu_exp7_fixed_delay_compare \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 30 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --batch-size 15 \
  --deadline-seconds 900 \
  --task-sampling-seed 1 \
  --delay-window 10,30 \
  --delay-values 5 10 20 30 60 \
  --algorithms capa impgta ramcom \
  --data-cache-dir Data/delay \
  --data-mode auto \
  --output-dir outputs/plots/exp7_fixed_delay_compare
```

该脚本会先固定 local platform 的 pick-up parcels 和 cooperating platforms 的 own-task streams，再让每个算法执行 6 次仿真：

- baseline（无 delay）
- 5s
- 10s
- 20s
- 30s
- 60s

#### 数据缓存参数

- `--data-cache-dir DIR`：固定数据输出目录。默认 `Data/delay`。
- `--data-mode auto|reuse|regenerate`：
  - `auto`：若 `DIR/manifest.json` 已存在，则直接复用已有固定数据；否则重新生成。
  - `reuse`：强制复用已有固定数据；若 `manifest.json` 不存在则报错。
  - `regenerate`：忽略已有缓存，重新生成 canonical pick-up parcels、partner task streams、以及 5 个 delayed CSV。

#### 固定数据输出

在 `Data/delay` 下会生成：

- `pick-up-parcels.csv`
- `pick-up-parcels-delay-5s.csv`
- `pick-up-parcels-delay-10s.csv`
- `pick-up-parcels-delay-20s.csv`
- `pick-up-parcels-delay-30s.csv`
- `pick-up-parcels-delay-60s.csv`
- `partner-tasks-P1.csv`, `partner-tasks-P2.csv`, ...
- `canonical-environment-seed.pkl`
- `manifest.json`

其中 local CSV 同时保留：

- `true_release_time`
- `observed_release_time`
- `true_deadline`
- `observed_deadline`
- `is_delayed`

这样可以直接审计哪些包裹被 delay 扰动，以及扰动后平台实际“看到”的时间戳。

#### 汇总输出

聚合结果写到：

- `outputs/plots/exp7_fixed_delay_compare/summary.json`

按算法组织，每个 delay 都会记录：

- `baseline_metrics`
- `delayed_metrics`
- `metric_deltas`
- `affected_parcel_ids`
- `transition_counts`
- `affected_outcome_totals`

这里的 compare 只针对 `delay_window` 内被标记为 `is_delayed=True` 的包裹，而不是全部包裹。

### 评估侧两个隐藏 bug + 修复（2026-05-24）

排查 RL-CAPA 训练时 reward~810 但 infer TR=490 的「评估远低于训练」诡异现象时发现两个独立 bug：

**Bug 1 — `evaluate_core.evaluate` 用 argmax/threshold 评估随机策略**：训练用 `Bernoulli.sample()` 随机采样动作，eval 用 `(probs > 0.5).long()` 阈值化。当 pi2 没收敛（`entropy_pi2 ≈ ln(2) ≈ 0.687`），probs 在 0.5 附近随机漂移。一旦略 > 0.5，eval 把**所有**包裹都判 cross；训练时只有 ~55%，TR 立刻塌方。

**修复**：`evaluate(eval_stochastic=True)` 默认改为随机采样，匹配训练分布。同时 `evaluate_rl_capa(eval_seeds=5)` 默认跑 5 个种子求平均消除单 trial 噪声。同一 checkpoint 实测 `STOCHASTIC TR=908 vs DETERMIN. TR=464`，差距 100%——这就是「训练高 / infer 低」的全部来源。

**Bug 2 — paper 脚本 `--courier-capacity` / `--service-radius-km` 默认值与 `runner.py` 不一致**：用户用 `runner.py` 训练 → `--courier-capacity` 默认 `None` → 框架默认 75；用 `experiments/run_chengdu_exp7_deadline_delay.py --execution-mode robustness` 评估 → paper 默认 `50.0` / `1.0 km`。同一份 checkpoint 在 capacity=50 + radius=1km 的紧约束环境下评估，等于换了一个 env，TR 自然降几倍。

**修复**：`experiments/paper_chengdu.py` 把 `--courier-capacity` 和 `--service-radius-km` 默认值都改为 `None`，与 `runner.py` 对齐。需要复现 paper 风格的紧约束时，显式传 `--courier-capacity 50 --service-radius-km 1.0`。

**修复后实测**（同一 checkpoint `exp7_rl_train_randomized_300p`，300 parcels / 20 local / 4 platforms × 5 / 720s deadline / delay=30s @ window 20-40）：

| 算法 | baseline TR | delayed TR | TR drop | drop ratio |
|------|------------:|-----------:|--------:|-----------:|
| CAPA | 688.86 | 652.53 | 36.34 | 5.3% |
| RL-CAPA | **823.25** | **801.69** | **21.56** | **2.6%** |

- 基准 RL-CAPA 比 CAPA TR 高 **19.5%**。
- 受 delay 扰动后 RL-CAPA 仍高出 CAPA **22.8%**，且自身 TR drop 只有 CAPA 的 **59%** —— 满足「delay 鲁棒性 RL-CAPA 优于 CAPA」目标。
- transition 分析：CAPA 受 delay 后有 `delivered_local__timed_out` (2 个本地被推到 timeout)；RL-CAPA 主动把 8 个原本 local 的延迟包裹切换到 cross (`delivered_local__delivered_cross`)，更好利用新特征 `service_slack` + `local_feasible` 做条件路由。

### 训练时 delay 域随机化（domain randomization）

实测发现：

| 训练设置 | baseline TR | delayed TR | TR 损失 | 关键模式 |
|---------|------------:|-----------:|--------:|----------|
| 无 delay 训练 | 232.49 | 222.43 | 10.06 | RL 决策**字节等于** CAPA（pi2 学会了 CAMA-cascade pattern）。 |
| 固定 delay 训练（30s @ window 10-30） | 81.95 | 82.07 | -0.12 | **崩塌为 all-cross**：pi2 把 100 包裹全推 cross，0 local。TR 暴跌 65%。 |
| 随机 delay 训练（`Uniform[0, 60]` @ window 10-30） | 226.40 | 226.99 | -0.58 | RL 21 local / 41 cross / 38 unmatched，与 CAPA 接近但 -3% TR。pi2 维持分化策略。 |

固定 delay 训练的失败说明 pi2 必须看到**delay 与无 delay 的混合分布**才能学到「条件触发 cross」而不是「无条件 cross」。

**新增 CLI 参数**（runner.py，仅训练时生效）：

- `--rl-train-delay-max-seconds N`：每个 episode 从 `Uniform[0, N]` 采样 delay 时长，50% 概率采到 0 保留无扰基线分布。
- `--rl-train-delay-window "start,end"`：受随机 delay 影响的 true_arrival 窗口；必须与 `--rl-train-delay-max-seconds > 0` 一同提供。
- 实现：`RLCAPAEnv._maybe_inject_train_delay` 在 `reset()` 内每集重采样 delay 并 `apply_processing_delay` 应用到克隆 env.tasks。

**推荐训练命令**（替换 prior step 1）：

```bash
python runner.py run \
  --algorithm rl-capa \
  --data-dir Data --num-parcels 100 --local-couriers 10 \
  --platforms 2 --couriers-per-platform 5 \
  --task-window-start-seconds 0 --task-window-end-seconds 30 \
  --partner-history-task-count-start 200 --partner-history-task-count-step 0 \
  --batch-size 15 --rl-batch-actions 10 15 20 --step-seconds 60 \
  --courier-speed-kmh 30 --deadline-seconds 720 \
  --task-sampling-seed 1 \
  --rl-train-delay-max-seconds 60 --rl-train-delay-window 10,30 \
  --episodes 500 --rl-warmup-episodes 20 \
  --rl-entropy-start 0.05 --rl-entropy-end 0.001 --rl-entropy-decay-episodes 250 \
  --rl-lr-actor 1e-4 --rl-use-service-slack \
  --rl-disable-advantage-normalization \
  --output-dir outputs/plots/exp7_rl_train_randomized
```

**目前差距**：randomized-delay 训练后 RL 仍比 CAPA 低 ~3% TR。下一步优化方向：

1. **`is_delayed_i` 显式特征**：把 `parcel.is_delayed` 标志加入 Stage-2 state（dim 12→13）。pi2 直接看到「这个包裹被延迟」标记，无需从 `local_feasible` / `service_slack` 间接推断。当前的「相对量」特征对小幅 delay 不够敏感（30s 在 720s deadline 下只占 4%）。
2. **Reward shaping**：当 pi2=1 拯救了一个 CAPA 会 timeout 的 parcel，给 +bonus；当 pi2=1 把一个本可 local-deliver 的 parcel 推给 cross 拿到更低 revenue，给 -penalty。让 pi2 学到「只对受扰包裹切 cross」的精细策略。
3. **更多 episodes（500-1000）**：12 维 state 训练样本不足，pi2 可能未收敛。
4. **Curriculum**：从无 delay 开始，逐 episode 递增 delay 上限。

### 1000-episode 域随机化训练（达成目标，2026-05-24）

把 episodes 从 200 提到 1000，规模 300 parcels / 20 local / 4×5 partner，配合修复后的评估流程后，**域随机化训练后的 RL-CAPA 在 baseline 与 delayed 两个口径都打过 CAPA，且 TR 损失只有 CAPA 的 59%**。

**训练指令**（输出落到 `outputs/plots/exp7_rl_train_randomized_300p/`）：

```bash
python runner.py run \
  --algorithm rl-capa \
  --data-dir Data --num-parcels 300 --local-couriers 20 \
  --platforms 4 --couriers-per-platform 5 \
  --task-window-start-seconds 0 --task-window-end-seconds 180 \
  --partner-history-task-count-start 200 --partner-history-task-count-step 0 \
  --batch-size 15 --rl-batch-actions 10 15 20 --step-seconds 60 \
  --courier-speed-kmh 30 --deadline-seconds 720 \
  --task-sampling-seed 1 \
  --rl-train-delay-max-seconds 60 --rl-train-delay-window 20,40 \
  --episodes 1000 --rl-warmup-episodes 20 \
  --rl-entropy-start 0.05 --rl-entropy-end 0.001 --rl-entropy-decay-episodes 250 \
  --rl-lr-actor 1e-4 --rl-use-service-slack \
  --rl-disable-advantage-normalization \
  --output-dir outputs/plots/exp7_rl_train_randomized_300p
```

**Robustness 对比指令**（输出 `outputs/plots/exp7_robustness_stochastic/robustness_comparison.json`）：

```bash
python -m experiments.run_chengdu_exp7_deadline_delay \
  --execution-mode robustness \
  --algorithms capa rl-capa-infer \
  --data-dir Data --num-parcels 300 --local-couriers 20 \
  --platforms 4 --couriers-per-platform 5 \
  --task-window-start-seconds 0 --task-window-end-seconds 180 \
  --partner-history-task-count-start 200 --partner-history-task-count-step 0 \
  --batch-size 30 --courier-speed-kmh 30 --deadline-seconds 720 \
  --task-sampling-seed 1 \
  --rl-batch-actions 10 15 20 \
  --delay-seconds 30 --delay-window 20,40 \
  --rl-checkpoint-dir outputs/plots/exp7_rl_train_randomized_300p/checkpoints \
  --rl-use-service-slack \
  --output-dir outputs/plots/exp7_robustness_stochastic
```

**结果**（同 task_sampling_seed=1，eval_seeds=5 平均）：

| Algo | baseline TR | baseline CR | delayed TR | delayed CR | TR drop | drop ratio |
|------|------------:|------------:|-----------:|-----------:|--------:|-----------:|
| CAPA | 688.86 | 0.807 | 652.53 | 0.813 | 36.34 | 5.3% |
| RL-CAPA | **823.25** | **0.863** | **801.69** | **0.860** | **21.56** | **2.6%** |

- baseline RL > CAPA **+19.5% TR**；delayed RL > CAPA **+22.8% TR**。
- RL TR drop = CAPA drop 的 **59%** → 更鲁棒。
- transition_counts：RL 把 **8 个**原本 local 的延迟包裹主动切到 cross（`delivered_local__delivered_cross`），CAPA 同条件下让 **2 个**本地包裹掉进 timeout，RL 利用 `service_slack` + `local_feasible` 做了条件路由。

**目标达成**：「保证 rl-capa 在引入 delay 情况下比 capa 更优」 ✓ —— TR 高 + drop 小 + 决策有差异化转移证据。

**前提条件**（不满足任一会丢效果）：
- 训练与评估必须用同一组 env 默认值。本轮已统一 `--courier-capacity` / `--service-radius-km` 默认为 `None`；如果要复现 paper 紧约束（capacity 50 + radius 1km），训练评估都要显式带这两个 flag。
- 评估必须用随机采样模式（已设默认 `eval_stochastic=True` + `eval_seeds=5`），否则 pi2 未收敛时阈值化会把 TR 砍半。
- RL infer 必须传 `--rl-batch-actions 10 15 20` 和 `--rl-use-service-slack` 让 pi1 输出维度和 Stage-2 state dim 与 checkpoint 对齐。

### 扫描多个 delay 强度

按需手动跑多个 `--delay-seconds` 取值并比较 `delayed_metrics.TR`。例如 `0 / 10 / 30 / 60` 四组，画 TR-vs-delay 曲线。`direct` / `split` 模式仍跑老的 axis sweep（`DEADLINE_DELAY_VALUES`），适合多点扫描时使用。

### 进一步优化方向（未在本轮实现）

- **Sequential GRU pi2**：用 `nn.GRUCell` 顺序决策，hidden state 携带「已分配 local 数量、剩余 courier 容量」上下文。当前 pi2 是并行 Bernoulli，对包裹间互相挤占的耦合无感。需要选定 parcel 排序（建议按 urgency 降序）+ 在每步喂入 `prev_action`。
- **真正的 per-step courier 状态更新**：sequential pi2 内部维护 courier 容量/route 的 mock 更新，pi2 看到「采纳第 k 个包裹后第 k+1 个包裹的可行 courier 已减少」。
- **Reward attribution by accept-step**：把 delivery_outcome 归属到 *接受* 该包裹的 step 而不是 *送达* 那一步。需要 runtime 维护 `accepted_step_by_task_id` 映射。

## 输出文件

实验输出默认写到 `outputs/plots/...`，通常包含：

- `summary.json`
- 每个 sweep 点的算法子目录
- 对比或 suite 的聚合 summary
- CAPA 单次运行时的 `TR/CR/BPT` 批次图

```bash
Exp-1 — local couriers ∈ {100,200,300,400,500}, default 300
  python -m experiments.run_chengdu_exp2_couriers \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp2_couriers_NY \
    --tmp-root /tmp/chengdu_exp2_couriers_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 2000 --local-couriers 300 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 50 --service-radius-km 1.0

  Exp-2 — parcels ∈ {500,2000,5000,10000,20000}, default 2000
  python -m experiments.run_chengdu_exp1_num_parcels \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp1_num_parcels_NY \
    --tmp-root /tmp/chengdu_exp1_num_parcels_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 2000 --local-couriers 300 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 50 --service-radius-km 1.0

  Exp-3 — platforms ∈ {2,4,8,12,16}, default 4, couriers/platform=50
  python -m experiments.run_chengdu_exp4_platforms \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp4_platforms_NY \
    --tmp-root /tmp/chengdu_exp4_platforms_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 2000 --local-couriers 300 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 50 --service-radius-km 1.0

  Exp-4 — courier capacity ∈ {25,50,75,100,125}, default 50
  python -m experiments.run_chengdu_exp6_capacity \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp6_capacity_NY \
    --tmp-root /tmp/chengdu_exp6_capacity_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 2000 --local-couriers 300 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 50 --service-radius-km 1.0

  Exp-5 — service radius ∈ {0.5,1,1.5,2,2.5}, default 1
  python -m experiments.run_chengdu_exp3_radius \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp3_radius_NY \
    --tmp-root /tmp/chengdu_exp3_radius_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 2000 --local-couriers 300 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 50 --service-radius-km 1.0

```
