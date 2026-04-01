# Auction-Aware Task Assignment

本仓库当前可直接运行的实验入口如下。

## 环境准备

```bash
python3 -m unittest discover -s tests -v
```

## 统一入口

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

支持的 `--algorithm`：

- `capa`
- `greedy`
- `basegta`
- `impgta`
- `rl-capa`（当前会显式报未实现）

## 单次 CAPA 实验

```bash
python3 -m capa.experiments \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --batch-size 300 \
  --output-dir outputs/plots/chengdu_capa
```

参数说明：

- `batch-size` 是时间窗口，单位为秒
- 输出包含 `summary.json`、`TR/CR/BPT` 曲线图

## 单次 baseline 实验

### Greedy

```bash
python3 - <<'PY'
from pathlib import Path
from capa.experiments import run_chengdu_greedy_baseline

summary = run_chengdu_greedy_baseline(
    data_dir=Path("Data"),
    num_parcels=100,
    local_courier_count=10,
    batch_size=300,
    output_dir=Path("outputs/plots/chengdu_greedy"),
)
print(summary)
PY
```

### BaseGTA

```bash
python3 - <<'PY'
from pathlib import Path
from capa.experiments import run_chengdu_basegta_baseline

summary = run_chengdu_basegta_baseline(
    data_dir=Path("Data"),
    num_parcels=100,
    local_courier_count=10,
    cooperating_platform_count=2,
    couriers_per_platform=5,
    output_dir=Path("outputs/plots/chengdu_basegta"),
)
print(summary)
PY
```

### ImpGTA

```bash
python3 - <<'PY'
from pathlib import Path
from capa.experiments import run_chengdu_impgta_baseline

summary = run_chengdu_impgta_baseline(
    data_dir=Path("Data"),
    num_parcels=100,
    local_courier_count=10,
    cooperating_platform_count=2,
    couriers_per_platform=5,
    output_dir=Path("outputs/plots/chengdu_impgta"),
    prediction_window_seconds=180,
)
print(summary)
PY
```

## 参数 sweep

### CAPA sweep

```bash
python3 - <<'PY'
from pathlib import Path
from capa.experiments import run_chengdu_parameter_sweep

summary = run_chengdu_parameter_sweep(
    data_dir=Path("Data"),
    output_dir=Path("outputs/plots/chengdu_sweep_num_parcels"),
    sweep_parameter="num_parcels",
    sweep_values=[20, 50, 100],
    fixed_config={
        "num_parcels": 20,
        "local_courier_count": 10,
        "cooperating_platform_count": 2,
        "couriers_per_platform": 5,
        "batch_size": 300,
    },
)
print(summary)
PY
```

### CAPA vs Greedy 对比 sweep

```bash
python3 - <<'PY'
from pathlib import Path
from capa.experiments import run_chengdu_comparison_sweep

summary = run_chengdu_comparison_sweep(
    data_dir=Path("Data"),
    output_dir=Path("outputs/plots/chengdu_compare_greedy_num_parcels"),
    sweep_parameter="num_parcels",
    sweep_values=[20, 50, 100],
    fixed_config={
        "num_parcels": 20,
        "local_courier_count": 10,
        "cooperating_platform_count": 2,
        "couriers_per_platform": 5,
        "batch_size": 300,
    },
)
print(summary)
PY
```

## 结果文件

实验输出默认写到 `outputs/plots/...`，通常包含：

- `summary.json`
- `tr_over_batches.png` / `tr_vs_*.png`
- `cr_over_batches.png` / `cr_vs_*.png`
- `bpt_over_batches.png` / `bpt_vs_*.png`

## 说明

- Chengdu 正式实验复用了 `env/chengdu.py` 中的 legacy 仿真推进逻辑
- CAPA 当前已实现，RL-CAPA 尚未实现
- `BaseGTA` 和 `ImpGTA` 基于参考文献 [17] 的规则做了仓库适配，具体边界见 `docs/implementation_notes.md`
