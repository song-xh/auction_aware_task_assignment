# Auction-Aware Task Assignment

当前仓库的 Chengdu 实验统一通过根目录 [runner.py](/root/code/auction_aware_task_assignment/runner.py) 运行。

## 环境准备

```bash
python3 -m unittest discover -s tests -v
```

## 单次实验

```bash
python3 runner.py run --algorithm capa --data-dir Data --num-parcels 100 --local-couriers 10 --platforms 2 --couriers-per-platform 5 --batch-size 300 --output-dir outputs/plots/chengdu_run
```

```bash
python3 runner.py run \
  --algorithm capa \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --batch-size 300 \
  --output-dir outputs/plots/chengdu_run
```

支持的 `--algorithm`：

- `capa`
- `greedy`
- `ramcom`
- `mra`
- `basegta`
- `impgta`
- `rl-capa`（当前会显式报未实现）

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

`service_radius` 使用公里单位，通过 `--values 0.5 1.0 1.5 ...` 传入。

当前统一实现将其解释为：

- courier 当前节点到 pick-up 节点的最短路最大服务半径
- 该约束会一致应用到 CAPA、Greedy、BaseGTA、ImpGTA 的可行性过滤

示例：

```bash
python3 runner.py compare \
  --algorithms capa greedy \
  --axis service_radius \
  --values 0.5 1.0 1.5 2.0 2.5 \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --batch-size 300 \
  --output-dir outputs/plots/chengdu_compare_service_radius
```

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

## 预定义 Suite

```bash
python3 runner.py suite \
  --suite chengdu-paper \
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
  --max-workers 4 \
  --output-dir outputs/plots/chengdu_suite_paper
```

当前 `chengdu-paper` 支持两个 preset：

- `smoke`
- `formal`

`formal` 是当前 Chengdu 环境下参考论文实验设计的正式 preset，会批量跑这些轴：

- `num_parcels`
- `local_couriers`
- `service_radius`
- `platforms`
- `courier_capacity`

`smoke` 只用于快速联调，轴值更小。

## Paper-Style 脚本

`experiments/` 目录下提供了与论文实验部分对齐的 Chengdu 脚本入口：

```bash
python3 experiments/run_chengdu_exp1_num_parcels.py --output-dir outputs/plots/exp1 --preset formal --max-workers 4
python3 experiments/run_chengdu_exp2_couriers.py --output-dir outputs/plots/exp2 --preset formal --max-workers 4
python3 experiments/run_chengdu_exp3_radius.py --output-dir outputs/plots/exp3 --preset formal --max-workers 4
python3 experiments/run_chengdu_exp4_platforms.py --output-dir outputs/plots/exp4 --preset formal --max-workers 4
python3 experiments/run_chengdu_exp5_default_compare.py --output-dir outputs/plots/exp5
python3 experiments/run_chengdu_exp6_capacity.py --output-dir outputs/plots/exp6 --preset formal --max-workers 4
python3 experiments/run_chengdu_paper_suite.py --output-dir outputs/plots/chengdu_suite --preset formal --max-workers 4
```

如果要按受控方式运行 `exp_1`，并在 `batch_size=30s` 下做多轮 CAPA 参数试验、把每轮结果先写到 `/tmp`，可以使用：

```bash
python3 experiments/run_exp1_managed.py \
  --tmp-root /tmp/exp1_managed \
  --final-output-dir /tmp/exp1_selected \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --batch-size 30 \
  --max-workers 4
```

`run_exp1_managed.py` 的行为是：

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
- `run_chengdu_exp2_couriers.py`
  - 变动参数：`|C| = local_couriers`
  - 固定参数默认值：`|Γ|=3000`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`
  - 输出指标：`TR vs |C|`、`CR vs |C|`、`BPT vs |C|`
- `run_chengdu_exp3_radius.py`
  - 变动参数：`rad = service_radius`
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、`batch_size=300s`
  - 输出指标：`TR vs rad`、`CR vs rad`、`BPT vs rad`
- `run_chengdu_exp4_platforms.py`
  - 变动参数：`|P| = platforms`
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`
  - 输出指标：`TR vs |P|`、`CR vs |P|`、`BPT vs |P|`
- `run_chengdu_exp5_default_compare.py`
  - 变动参数：无
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、容量 `50`、服务半径 `1.0km`、`batch_size=300s`
  - 输出指标：各算法默认设置下的 `TR`、`CR`、`BPT`
- `run_chengdu_exp6_capacity.py`
  - 变动参数：courier capacity
  - 固定参数默认值：`|Γ|=3000`、`|C|=200`、`|P|=4`、每个平台 `50` 个 courier、服务半径 `1.0km`、`batch_size=300s`
  - 输出指标：`TR vs capacity`、`CR vs capacity`、`BPT vs capacity`
- `run_chengdu_paper_suite.py`
  - 按 preset 批量运行上述所有 sweep
  - 输出：每个实验轴单独的图、`summary.json` 和 suite 级汇总

这些脚本默认使用：

- 同一个 sweep 点只初始化一次环境
- 不同算法共享同一个环境 seed，并从 clone 出来的环境运行
- `--max-workers` 用于并行不同 sweep 点，减少总墙钟时间

推荐的正式实验命令：

```bash
python3 -u experiments/run_exp1_split.py --tmp-root /tmp/exp1_formal_20260405 --output-dir outputs/plots/exp1_formal_20260405 --algorithms capa greedy basegta impgta mra ramcom --data-dir Data --local-couriers 200 --platforms 4 --couriers-per-platform 50 --courier-capacity 50 --service-radius-km 1.0 --batch-size 30 --poll-seconds 10

python3 experiments/run_chengdu_exp2_couriers.py \
  --output-dir outputs/plots/exp2_couriers \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --max-workers 4

python3 experiments/run_chengdu_exp3_radius.py \
  --output-dir outputs/plots/exp3_radius \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --max-workers 4

python3 experiments/run_chengdu_exp4_platforms.py \
  --output-dir outputs/plots/exp4_platforms \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --max-workers 4

python3 experiments/run_chengdu_exp5_default_compare.py \
  --output-dir outputs/plots/exp5_default_compare \
  --algorithms capa greedy ramcom mra basegta impgta

python3 experiments/run_chengdu_exp6_capacity.py \
  --output-dir outputs/plots/exp6_capacity \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --max-workers 4
```

如果要一次性跑完整套：

```bash
python3 experiments/run_chengdu_paper_suite.py \
  --output-dir outputs/plots/chengdu_paper_suite \
  --preset formal \
  --algorithms capa greedy ramcom mra basegta impgta \
  --max-workers 4
```

## 输出文件

实验输出默认写到 `outputs/plots/...`，通常包含：

- `summary.json`
- 每个 sweep 点的算法子目录
- 对比或 suite 的聚合 summary
- CAPA 单次运行时的 `TR/CR/BPT` 批次图

## 说明

- Chengdu 正式实验复用了 [chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py) 中的 legacy 仿真推进逻辑
- `TR`、`CR`、`BPT` 是统一 summary 的默认指标
- `BaseGTA` 和 `ImpGTA` 基于参考文献 [17] 的规则做了仓库适配，具体边界见 [implementation_notes.md](/root/code/auction_aware_task_assignment/docs/implementation_notes.md)
- `capa.experiments` 仍可作为兼容层存在，但不再是推荐入口
