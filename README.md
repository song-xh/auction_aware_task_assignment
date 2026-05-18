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

### RL-CAPA 域随机化 (Domain Randomization) 训练配方 — 用于 Exp-7/Exp-8

Exp-7 (deadline 处理延迟) 与 Exp-8 (deadline 噪声) 的鲁棒性比较需要 **一次性** 训练一份对 deadline 扰动鲁棒的 RL-CAPA checkpoint，再以 `rl-capa-infer` 加载这份 checkpoint 进行多扰动幅度推断（详见下面 Exp-7/Exp-8 一节）。训练命令：

```bash
python3 runner.py run \
  --algorithm rl-capa \
  --data-dir Data \
  --num-parcels 3000 \
  --local-couriers 200 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 3600 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --rl-batch-actions 10 15 20 25 30 \
  --step-seconds 60 \
  --episodes 1500 \
  --rl-lr-actor 0.0003 \
  --rl-lr-critic 0.0005 \
  --rl-discount-factor 1.0 \
  --rl-entropy-start 0.05 \
  --rl-entropy-end 0.005 \
  --rl-entropy-decay-episodes 1000 \
  --rl-max-grad-norm 0.5 \
  --rl-domain-randomize \
  --rl-domain-randomize-seed 0 \
  --output-dir outputs/plots/rl_capa_robust_500
```

`--rl-domain-randomize` 打开后，RL-CAPA 在每个 episode 开始时随机抽取一组 `(delay_seconds, noise_percent)`：

- delay 从 `{0, 5, 10, 15, 20, 30, 60}` 中均匀抽样（默认 `(0,) + DEADLINE_DELAY_VALUES`，可用 `--rl-domain-randomize-delays` 覆盖）。
- noise 从 `{0, ±5, ±10, ±15, ±20}` 中均匀抽样（默认 `(0,) + DEADLINE_NOISE_VALUES`，可用 `--rl-domain-randomize-noises` 覆盖）。
- 抽样后通过 `apply_processing_delay` / `apply_deadline_noise` 注入到本 episode 克隆环境上的 task；真实 release/deadline 不变，只有模型感知到的 `observed_s_time` / `observed_d_time` 受扰动。

要点：

- 同时包含 `(0, 0)` 这个 clean 角点，确保策略不会在 clean baseline 上退化。
- 训练完成后 checkpoint 落在 `outputs/plots/rl_capa_robust_500/rl-capa/checkpoints`，与 Exp-7/Exp-8 的 `rl-capa-infer` 默认 `rl_checkpoint_dir` 对齐，可直接被加载推断（参见 P1 修改的 `experiments/paper_chengdu.py` 默认值）。
- `--rl-domain-randomize-seed` 控制 sampler 的 RNG，方便复现。
- `training_summary.json` 多出 `episode_disturbance` 字段，按 episode 记录抽到的 `(delay, noise)`，方便事后核对采样分布。
- stage1/stage2 的 `recent_timeout_ratio`、`recent_unresolved_ratio`、`observed_slack_ratio` 在训练期间持续累计，policy 会借助这些 drift signal 学到针对扰动的策略。

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
- `--rl-future-feature-window-seconds`：RL-CAPA 第一阶段真实未来特征统计窗口，单位秒，默认 `300`。
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
    --num-parcels 5000 --local-couriers 200 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 10 --service-radius-km 1.0

  Exp-2 — parcels ∈ {500,2000,5000,10000,20000}, default 2000
  python -m experiments.run_chengdu_exp1_num_parcels \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp1_num_parcels_NY \
    --tmp-root /tmp/chengdu_exp1_num_parcels_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 5000 --local-couriers 200 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 10 --service-radius-km 1.0

  Exp-3 — platforms ∈ {2,4,8,12,16}, default 4, couriers/platform=50
  python -m experiments.run_chengdu_exp4_platforms \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp4_platforms_NY \
    --tmp-root /tmp/chengdu_exp4_platforms_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 5000 --local-couriers 200 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 10 --service-radius-km 1.0

  Exp-4 — courier capacity ∈ {25,50,75,100,125}, default 50
  python -m experiments.run_chengdu_exp6_capacity \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp6_capacity_NY \
    --tmp-root /tmp/chengdu_exp6_capacity_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 5000 --local-couriers 200 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 10 --service-radius-km 1.0

  Exp-5 — service radius ∈ {0.5,1,1.5,2,2.5}, default 1
  python -m experiments.run_chengdu_exp3_radius \
    --execution-mode split --preset ny \
    --output-dir outputs/plots/chengdu_exp3_radius_NY \
    --tmp-root /tmp/chengdu_exp3_radius_NY \
    --algorithms capa greedy ramcom mra basegta impgta \
    --num-parcels 5000 --local-couriers 200 \
    --platforms 4 --couriers-per-platform 50 \
    --courier-capacity 10 --service-radius-km 1.0

```

### Exp-7 / Exp-8 — Deadline 处理延迟与噪声鲁棒性

Exp-7 (deadline 处理延迟) 与 Exp-8 (deadline 噪声) 现在默认以 `rl-capa-infer` 加 `ramcom` 作为对照算法：`DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS = ("rl-capa-infer", "ramcom")`。RL-CAPA 一侧加载上节 **域随机化训练** 产出的 `outputs/plots/rl_capa_robust_500/rl-capa/checkpoints` 单一 checkpoint，不再随每个扰动幅度重新训练，从而构成纯粹的鲁棒性比较。

运行前提：先按照上节命令训练 `outputs/plots/rl_capa_robust_500/` checkpoint；否则 `rl-capa-infer` 加载会报 `FileNotFoundError`。

Exp-7（处理延迟，axis 取自 `DEADLINE_DELAY_VALUES = (5, 10, 15, 20, 30, 60)` 秒）：

```bash
python3 -m experiments.run_chengdu_exp7_deadline_delay \
  --execution-mode split --preset formal \
  --output-dir outputs/plots/chengdu_exp7_deadline_delay \
  --tmp-root /tmp/chengdu_exp7_deadline_delay \
  --data-dir Data \
  --num-parcels 3000 --local-couriers 200 \
  --platforms 4 --couriers-per-platform 50 \
  --courier-capacity 50 --service-radius-km 1.0 \
  --batch-size 30 \
  --task-window-start-seconds 0 --task-window-end-seconds 3600
```

Exp-8（perceived-deadline 噪声，axis 取自 `DEADLINE_NOISE_VALUES = (-20, -15, -10, -5, 0, 5, 10, 15, 20)` 百分比）：

```bash
python3 -m experiments.run_chengdu_exp8_deadline_noise \
  --execution-mode split --preset formal \
  --output-dir outputs/plots/chengdu_exp8_deadline_noise \
  --tmp-root /tmp/chengdu_exp8_deadline_noise \
  --data-dir Data \
  --num-parcels 3000 --local-couriers 200 \
  --platforms 4 --couriers-per-platform 50 \
  --courier-capacity 50 --service-radius-km 1.0 \
  --batch-size 30 \
  --task-window-start-seconds 0 --task-window-end-seconds 3600
```

每个 axis 点的 `summary.json` 现在包含四个 TR-损失归因字段，可直接用于论文中分解损失来源：

- `expired_at_intake`: 算法首次见到任务时，真实 deadline 已过 → 任务未被接受。
- `accepted_but_timed_out`: 算法接受任务，但完成时间晚于真实 deadline → 已分配但无收益。
- `rejected_observed_deadline`: 算法以感知 deadline 判定不可行，主动放弃 → infeasibility 拒绝。
- `expired_due_to_true_deadline`: 上述前两项之和，等价于真实-deadline 总损失。

如需切换回过去 "rl-capa 每点重训" 的 narrative（非鲁棒性实验），显式传 `--algorithms rl-capa ramcom` 覆盖默认即可。
