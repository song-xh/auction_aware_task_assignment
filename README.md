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

RL-CAPA 现在走 actor-critic 主线，可直接通过统一 runner 训练并评估：

```bash
python3 runner.py run \
  --algorithm rl-capa \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --min-batch-size 10 \
  --max-batch-size 20 \
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

- `--min-batch-size` / `--max-batch-size`：第一阶段 batch-size 动作空间 `A_b` 的上下界。
- `--step-seconds`：episode 结束后 drain legacy 路线时使用的环境推进步长。
- `--episodes`：actor-critic 训练轮数。
- `--rl-lr-actor`：两个 actor 的 Adam 学习率。
- `--rl-lr-critic`：两个 critic 的 Adam 学习率。
- `--rl-discount-factor`：Monte-Carlo discounted return 的折扣因子。
- `--rl-entropy-coeff`：policy entropy 正则系数。
- `--rl-max-grad-norm`：梯度裁剪阈值。
- `--rl-device`：可选 torch device 覆盖，例如 `cpu` 或 `cuda`；默认自动选择可用 CUDA，否则 CPU。

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
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10
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
  --batch-size 300 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10
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
  --batch-size 300 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10
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
  --batch-size 300 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10
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
  --batch-size 300 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1
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
  --batch-size 300 \
  --prediction-window-seconds 180 \
  --prediction-success-rate 0.8 \
  --prediction-sampling-seed 1 \
  --poll-seconds 10
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
