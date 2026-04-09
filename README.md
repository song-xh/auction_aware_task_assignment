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
- `--seed-path`：复用已有 canonical environment seed，保证不同点位或不同轮次使用同一初始环境。

`execution-mode` 的推荐用法：

- 小规模联调：`direct`
- 正式 sweep：`split`
- 单点复现实验：`point`
- `Exp-1` 多轮 CAPA 参数对照：`managed`

如果要按受控方式运行 `Exp-1`，并在 `batch_size=30s` 下做多轮 CAPA 参数试验、把每轮结果先写到 `/tmp`，可以使用：

```bash
python3 experiments/run_chengdu_exp1_num_parcels.py \
  --execution-mode managed \
  --tmp-root /tmp/exp1_managed \
  --output-dir /tmp/exp1_selected \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --batch-size 30 \
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
  - 固定参数默认值：`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`
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
  --poll-seconds 10
```
- `run_chengdu_exp2_couriers.py`
  - 变动参数：`|C| = local_couriers`
  - 固定参数默认值：`|Γ|=3000`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`
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
  --poll-seconds 10
```
- `run_chengdu_exp3_radius.py`
  - 变动参数：`rad = service_radius`
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、`batch_size=300s`
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
  --poll-seconds 10
```
- `run_chengdu_exp4_platforms.py`
  - 变动参数：`|P| = platforms`
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`
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
  --poll-seconds 10
```
- `run_chengdu_exp5_default_compare.py`
  - 变动参数：无
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`
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
  --batch-size 300
```
- `run_chengdu_exp6_capacity.py`
  - 变动参数：courier capacity
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、服务半径 `1.0km`、`batch_size=300s`
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
