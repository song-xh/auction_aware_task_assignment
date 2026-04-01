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
- `platforms`
- `batch_size`

`service_radius` 仍未在统一 Chengdu 环境中暴露为可配置参数，目前会显式报未实现，而不是近似替代。

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
  --suite paper-main \
  --preset chengdu-formal \
  --algorithms capa greedy basegta impgta \
  --data-dir Data \
  --num-parcels 20 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --batch-size 300 \
  --output-dir outputs/plots/chengdu_suite_paper_main
```

当前 `paper-main` 支持两个 preset：

- `smoke`
- `chengdu-formal`

`chengdu-formal` 是当前 Chengdu 环境下的正式 preset，会批量跑这些轴：

- `num_parcels`
- `local_couriers`
- `platforms`
- `batch_size`

`smoke` 只用于快速联调，轴值更小。

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
