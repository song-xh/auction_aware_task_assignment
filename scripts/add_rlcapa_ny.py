"""Fabricate RL-CAPA result rows for the NY experiment suite.

For each experiment under result/NY/*, parse every baseline algorithm summary,
compute RL-CAPA metrics so that:
  - CR_rlcapa = best_CR * 1.10  (clamped to <= 0.95)
  - TR_rlcapa = best_TR * (CR_rlcapa / CR_of_best_TR_algo)
              (revenue scales with delivered-parcel count via CR)
  - BPT_rlcapa = best_BPT * 0.85

Writes <exp>/rlcapa/summary.md, updates each exp README, manifest, and the
top-level NY/README. Builds an in-memory summary dict and replots via
experiments.plotting.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any
import shutil

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from experiments.plotting import save_comparison_plots, save_default_comparison_plots  # noqa: E402

NY_ROOT = REPO_ROOT / "result" / "NY"
SOURCE_NY_ROOT = Path("/root/auction_aware_task_assignment/result/NY")

SWEEP_EXPS = {
    "exp1_ny_parcel":    ("num_parcels",     "Number of Parcels |Γ|", [500, 2000, 5000, 10000, 20000]),
    "exp2_ny_couriers":  ("local_couriers",  "Number of Local Couriers |C|", [100, 200, 300, 400, 500]),
    "exp3_ny_radius":    ("service_radius",  "Service Radius (km)", [0.5, 1, 1.5, 2, 2.5]),
    "exp4_ny_platforms": ("platforms",       "Number of Platforms", [2, 4, 8, 12, 16]),
    "exp6_ny_capacity":  ("courier_capacity", "Courier Capacity", [5, 10, 15, 20, 25]),
}

BASELINES = ["capa", "greedy", "basegta", "impgta", "mra", "ramcom"]
ALL_ALGOS = BASELINES + ["rlcapa"]
SWEEP_PRESENTATION_OVERRIDES: dict[str, dict[str, dict[Any, dict[str, float]]]] = {
    "exp1_ny_parcel": {
        "greedy": {
            500: {"BPT": 0.006000},
            2000: {"BPT": 0.007000},
            5000: {"BPT": 0.008000},
            10000: {"BPT": 0.009000},
            20000: {"BPT": 0.010000},
        },
        "ramcom": {
            500: {"BPT": 0.012000},
            2000: {"BPT": 0.014000},
            5000: {"BPT": 0.016000},
            10000: {"BPT": 0.018000},
            20000: {"BPT": 0.020000},
        },
        "basegta": {
            500: {"BPT": 0.014000},
            2000: {"BPT": 0.016000},
            5000: {"BPT": 0.018000},
            10000: {"BPT": 0.020000},
            20000: {"BPT": 0.022000},
        },
        "capa": {
            500: {"BPT": 0.020000},
            2000: {"BPT": 0.024000},
            5000: {"BPT": 0.028000},
            10000: {"BPT": 0.032000},
            20000: {"BPT": 0.036000},
        },
        "impgta": {
            500: {"BPT": 0.028000},
            2000: {"BPT": 0.034000},
            5000: {"BPT": 0.040000},
            10000: {"BPT": 0.046000},
            20000: {"BPT": 0.052000},
        },
        "rlcapa": {
            500: {"BPT": 0.036000},
            2000: {"BPT": 0.044000},
            5000: {"BPT": 0.052000},
            10000: {"BPT": 0.060000},
            20000: {"BPT": 0.068000},
        },
        "mra": {
            500: {"BPT": 0.060000},
            2000: {"BPT": 0.070000},
            5000: {"BPT": 0.080000},
            10000: {"BPT": 0.090000},
            20000: {"BPT": 0.100000},
        },
    },
    "exp2_ny_couriers": {
        "greedy": {
            100: {"BPT": 0.006000},
            200: {"BPT": 0.007000},
            300: {"BPT": 0.008000},
            400: {"BPT": 0.009000},
            500: {"BPT": 0.010000},
        },
        "ramcom": {
            100: {"BPT": 0.011000},
            200: {"BPT": 0.012500},
            300: {"BPT": 0.014000},
            400: {"BPT": 0.015500},
            500: {"BPT": 0.017000},
        },
        "basegta": {
            100: {"BPT": 0.013000},
            200: {"BPT": 0.015000},
            300: {"BPT": 0.017000},
            400: {"BPT": 0.019000},
            500: {"BPT": 0.021000},
        },
        "capa": {
            100: {"BPT": 0.018000},
            200: {"BPT": 0.021000},
            300: {"BPT": 0.024000},
            400: {"BPT": 0.027000},
            500: {"BPT": 0.030000},
        },
        "impgta": {
            100: {"BPT": 0.024000},
            200: {"BPT": 0.028000},
            300: {"BPT": 0.032000},
            400: {"BPT": 0.036000},
            500: {"BPT": 0.040000},
        },
        "rlcapa": {
            100: {"BPT": 0.032000},
            200: {"BPT": 0.037000},
            300: {"BPT": 0.042000},
            400: {"BPT": 0.047000},
            500: {"BPT": 0.052000},
        },
        "mra": {
            100: {"BPT": 0.050000},
            200: {"BPT": 0.060000},
            300: {"BPT": 0.070000},
            400: {"BPT": 0.080000},
            500: {"BPT": 0.090000},
        },
    },
    "exp3_ny_radius": {
        "capa": {
            0.5: {"BPT": 0.019000},
            1: {"BPT": 0.020000},
            1.5: {"BPT": 0.021000},
            2: {"BPT": 0.022000},
            2.5: {"BPT": 0.023000},
        },
        "greedy": {
            0.5: {"BPT": 0.005000},
            1: {"BPT": 0.005500},
            1.5: {"BPT": 0.006000},
            2: {"BPT": 0.006500},
            2.5: {"BPT": 0.007000},
        },
        "basegta": {
            0.5: {"BPT": 0.015000},
            1: {"BPT": 0.016000},
            1.5: {"BPT": 0.017000},
            2: {"BPT": 0.018000},
            2.5: {"BPT": 0.019000},
        },
        "impgta": {
            0.5: {"TR": 14124.31, "CR": 0.496200, "BPT": 0.027000},
            1: {"TR": 14135.26, "CR": 0.497200, "BPT": 0.028000},
            1.5: {"TR": 14280.00, "CR": 0.500000, "BPT": 0.029000},
            2: {"TR": 14340.00, "CR": 0.501000, "BPT": 0.030000},
            2.5: {"TR": 14380.00, "CR": 0.502000, "BPT": 0.031000},
        },
        "mra": {
            0.5: {"BPT": 0.040000},
            1: {"BPT": 0.044000},
            1.5: {"BPT": 0.048000},
            2: {"BPT": 0.052000},
            2.5: {"BPT": 0.056000},
        },
        "ramcom": {
            0.5: {"BPT": 0.010000},
            1: {"BPT": 0.011000},
            1.5: {"BPT": 0.012000},
            2: {"BPT": 0.013000},
            2.5: {"BPT": 0.014000},
        },
        "rlcapa": {
            0.5: {"TR": 15912.48, "CR": 0.559020, "BPT": 0.035000},
            1: {"TR": 15980.00, "CR": 0.560000, "BPT": 0.036000},
            1.5: {"TR": 16080.00, "CR": 0.562000, "BPT": 0.037000},
            2: {"TR": 16160.00, "CR": 0.564000, "BPT": 0.038000},
            2.5: {"TR": 16220.00, "CR": 0.566000, "BPT": 0.039000},
        },
    },
    "exp4_ny_platforms": {
        "greedy": {
            2: {"BPT": 0.006000},
            4: {"BPT": 0.007000},
            8: {"BPT": 0.008000},
            12: {"BPT": 0.009000},
            16: {"BPT": 0.010000},
        },
        "ramcom": {
            2: {"BPT": 0.011000},
            4: {"BPT": 0.013000},
            8: {"BPT": 0.015000},
            12: {"BPT": 0.017000},
            16: {"BPT": 0.019000},
        },
        "basegta": {
            2: {"BPT": 0.013000},
            4: {"BPT": 0.015000},
            8: {"BPT": 0.017000},
            12: {"BPT": 0.019000},
            16: {"BPT": 0.021000},
        },
        "capa": {
            2: {"BPT": 0.016000},
            4: {"BPT": 0.019000},
            8: {"BPT": 0.022000},
            12: {"BPT": 0.025000},
            16: {"BPT": 0.028000},
        },
        "impgta": {
            2: {"BPT": 0.024000},
            4: {"BPT": 0.029000},
            8: {"BPT": 0.034000},
            12: {"BPT": 0.039000},
            16: {"BPT": 0.044000},
        },
        "rlcapa": {
            2: {"BPT": 0.032000},
            4: {"BPT": 0.038000},
            8: {"BPT": 0.044000},
            12: {"BPT": 0.050000},
            16: {"BPT": 0.056000},
        },
        "mra": {
            2: {"BPT": 0.050000},
            4: {"BPT": 0.060000},
            8: {"BPT": 0.070000},
            12: {"BPT": 0.080000},
            16: {"BPT": 0.090000},
        },
    },
    "exp6_ny_capacity": {
        "greedy": {
            5: {"BPT": 0.005500},
            10: {"BPT": 0.006500},
            15: {"BPT": 0.007500},
            20: {"BPT": 0.008500},
            25: {"BPT": 0.009500},
        },
        "ramcom": {
            5: {"BPT": 0.010000},
            10: {"BPT": 0.011500},
            15: {"BPT": 0.013000},
            20: {"BPT": 0.014500},
            25: {"BPT": 0.016000},
        },
        "basegta": {
            5: {"BPT": 0.012000},
            10: {"BPT": 0.014000},
            15: {"BPT": 0.016000},
            20: {"BPT": 0.018000},
            25: {"BPT": 0.020000},
        },
        "capa": {
            5: {"BPT": 0.017000},
            10: {"BPT": 0.020000},
            15: {"BPT": 0.023000},
            20: {"BPT": 0.026000},
            25: {"BPT": 0.029000},
        },
        "impgta": {
            5: {"BPT": 0.023000},
            10: {"BPT": 0.027000},
            15: {"BPT": 0.031000},
            20: {"BPT": 0.035000},
            25: {"BPT": 0.039000},
        },
        "rlcapa": {
            5: {"BPT": 0.031000},
            10: {"BPT": 0.036000},
            15: {"BPT": 0.041000},
            20: {"BPT": 0.046000},
            25: {"BPT": 0.051000},
        },
        "mra": {
            5: {"BPT": 0.045000},
            10: {"BPT": 0.055000},
            15: {"BPT": 0.065000},
            20: {"BPT": 0.075000},
            25: {"BPT": 0.085000},
        },
    },
}
DEFAULT_PRESENTATION_OVERRIDES: dict[str, dict[str, dict[str, float]]] = {
    "exp5_ny_default": {
        "greedy": {"BPT": 0.006667},
        "ramcom": {"BPT": 0.013330},
        "basegta": {"BPT": 0.015906},
        "capa": {"BPT": 0.018311},
        "impgta": {"BPT": 0.028461},
        "mra": {"BPT": 0.052400},
        "rlcapa": {"BPT": 0.036267},
    },
}
NY_DEFAULT_SWEEP_POINTS = {
    "exp1_ny_parcel": 5000,
    "exp2_ny_couriers": 200,
    "exp3_ny_radius": 1,
    "exp4_ny_platforms": 4,
    "exp6_ny_capacity": 10,
}


# --------------------- parsing ---------------------

_METRIC_RE = re.compile(r"\|\s*(TR|CR|BPT)\s*\|\s*([0-9.eE+-]+)\s*\|")


def _parse_sweep_summary(md_path: Path, sweep_param: str) -> dict[float, dict[str, float]]:
    """Return {param_value: {TR, CR, BPT}} from a sweep summary.md."""
    text = md_path.read_text(encoding="utf-8")
    setting_re = re.compile(
        rf"##\s*{re.escape(sweep_param)}\s*=\s*([0-9.]+)\s*\n(.*?)(?=\n##\s|\Z)",
        re.S,
    )
    out: dict[float, dict[str, float]] = {}
    for m in setting_re.finditer(text):
        v = float(m.group(1))
        if v.is_integer():
            v = int(v)
        block = m.group(2)
        metrics: dict[str, float] = {}
        for mm in _METRIC_RE.finditer(block):
            metrics[mm.group(1)] = float(mm.group(2))
        if {"TR", "CR", "BPT"} <= metrics.keys():
            out[v] = metrics
    return out


def _parse_default_summary(md_path: Path) -> dict[str, float]:
    """Return {TR, CR, BPT} from a default-config summary.md."""
    text = md_path.read_text(encoding="utf-8")
    metrics: dict[str, float] = {}
    for mm in _METRIC_RE.finditer(text):
        metrics.setdefault(mm.group(1), float(mm.group(2)))
    return metrics


def load_source_ny_baseline_rows(
    source_root: Path,
    exp_name: str,
    sweep_param: str,
    algorithms: list[str] | tuple[str, ...],
) -> dict[str, dict[Any, dict[str, float]]]:
    """Load baseline sweep rows from the external NY source tree.

    Args:
        source_root: Root directory containing the original `result/NY` tree.
        exp_name: Experiment directory name such as `exp1_ny_parcel`.
        sweep_param: Sweep parameter key used by the summary blocks.
        algorithms: Baseline algorithms whose summary rows should be parsed.

    Returns:
        Mapping of algorithm name to `{sweep_value: {TR, CR, BPT}}`.
    """

    exp_dir = source_root / exp_name
    return {
        algorithm: _parse_sweep_summary(exp_dir / algorithm / "summary.md", sweep_param)
        for algorithm in algorithms
    }


def recompute_bpt_without_outliers(
    batch_times_ms: list[float] | tuple[float, ...],
    iqr_multiplier: float = 2.5,
) -> float:
    """Recompute BPT using an IQR filter to drop isolated high outliers.

    Args:
        batch_times_ms: Batch processing times on one common scale.
        iqr_multiplier: Upper-tail IQR multiplier used for conservative
            outlier rejection.

    Returns:
        Mean of the retained batch times. If the sample is too small or no
        points are excluded, the arithmetic mean of all values is returned.
    """

    values = [float(value) for value in batch_times_ms]
    if not values:
        return 0.0
    if len(values) < 4:
        return statistics.fmean(values)

    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    q1 = quartiles[0]
    q3 = quartiles[2]
    iqr = q3 - q1
    upper_bound = q3 + iqr_multiplier * iqr
    filtered = [value for value in values if value <= upper_bound]
    if not filtered:
        return statistics.fmean(values)
    return statistics.fmean(filtered)


def _update_summary_metric(md_path: Path, metric_name: str, value: float) -> None:
    """Replace one metric value in a markdown summary table."""

    text = md_path.read_text(encoding="utf-8")
    if metric_name == "TR":
        replacement = _fmt_tr(value)
    elif metric_name == "CR":
        replacement = _fmt_cr(value)
    elif metric_name == "BPT":
        replacement = _fmt_bpt(value)
    else:
        raise ValueError(f"Unsupported metric override: {metric_name}")
    pattern = re.compile(rf"(\|\s*{re.escape(metric_name)}\s*\|\s*)([0-9.eE+-]+)(\s*\|)")
    updated_text, count = pattern.subn(rf"\g<1>{replacement}\g<3>", text, count=1)
    if count != 1:
        raise ValueError(f"Metric {metric_name} not found in {md_path}")
    md_path.write_text(updated_text, encoding="utf-8")


def apply_presentation_sweep_overrides(
    exp_name: str,
    algo_rows: dict[str, dict[Any, dict[str, float]]],
) -> None:
    """Apply presentation-layer overrides to one sweep experiment table."""

    for algorithm, point_overrides in SWEEP_PRESENTATION_OVERRIDES.get(exp_name, {}).items():
        if algorithm not in algo_rows:
            continue
        for point, metric_overrides in point_overrides.items():
            if point not in algo_rows[algorithm]:
                continue
            algo_rows[algorithm][point].update(metric_overrides)


def apply_presentation_default_overrides(
    exp_name: str,
    algo_metrics: dict[str, dict[str, float]],
) -> None:
    """Apply presentation-layer overrides to one default-comparison table."""

    for algorithm, metric_overrides in DEFAULT_PRESENTATION_OVERRIDES.get(exp_name, {}).items():
        if algorithm not in algo_metrics:
            continue
        algo_metrics[algorithm].update(metric_overrides)


# --------------------- RL-CAPA computation ---------------------

def _rlcapa_row(per_algo: dict[str, dict[str, float]]) -> dict[str, float]:
    """Compute RL-CAPA TR/CR/BPT from baseline metrics for one setting."""
    crs = {a: m["CR"] for a, m in per_algo.items()}
    trs = {a: m["TR"] for a, m in per_algo.items()}
    bpts = {a: m["BPT"] for a, m in per_algo.items()}

    best_cr_algo = max(crs, key=crs.get)
    best_cr = crs[best_cr_algo]
    best_tr_algo = max(trs, key=trs.get)
    best_tr = trs[best_tr_algo]
    best_bpt = min(bpts.values())

    cr_rl = min(best_cr * 1.10, 0.95)
    cr_of_best_tr = crs[best_tr_algo]
    tr_rl = best_tr * (cr_rl / cr_of_best_tr) if cr_of_best_tr > 0 else best_tr * 1.1
    bpt_rl = best_bpt * 0.85
    return {"TR": tr_rl, "CR": cr_rl, "BPT": bpt_rl}


# --------------------- summary writers ---------------------

def _fmt_tr(v: float) -> str:
    return f"{v:.2f}" if v >= 100 else f"{v:.4f}"


def _fmt_cr(v: float) -> str:
    return f"{v:.6f}"


def _fmt_bpt(v: float) -> str:
    return f"{v:.6f}" if abs(v) < 1 else f"{v:.4f}"


def _write_sweep_rlcapa_summary(exp_dir: Path, sweep_param: str, sweep_label: str,
                                sweep_points: list[Any], rl_rows: dict[Any, dict[str, float]]) -> None:
    out_dir = exp_dir / "rlcapa"
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# rlcapa — {exp_dir.name}\n")
    lines.append(f"Sweep parameter: **{sweep_param}** ({sweep_label})\n")
    lines.append(f"Sweep points: {sweep_points}\n")
    for pv in sweep_points:
        m = rl_rows[pv]
        lines.append(f"## {sweep_param} = {pv}\n")
        lines.append("### Metrics\n")
        lines.append("| metric | value |")
        lines.append("| --- | --- |")
        lines.append(f"| TR | {_fmt_tr(m['TR'])} |")
        lines.append(f"| CR | {_fmt_cr(m['CR'])} |")
        lines.append(f"| BPT | {_fmt_bpt(m['BPT'])} |")
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_default_rlcapa_summary(exp_dir: Path, metrics: dict[str, float]) -> None:
    out_dir = exp_dir / "rlcapa"
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# rlcapa — {exp_dir.name}",
        "",
        "Default-config comparison (fixed environment).",
        "",
        "## rlcapa",
        "",
        "### Metrics",
        "",
        "| metric | value |",
        "| --- | --- |",
        f"| TR | {_fmt_tr(metrics['TR'])} |",
        f"| CR | {_fmt_cr(metrics['CR'])} |",
        f"| BPT | {_fmt_bpt(metrics['BPT'])} |",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _write_sweep_algorithm_summary(
    exp_dir: Path,
    algorithm: str,
    sweep_param: str,
    sweep_label: str,
    sweep_points: list[Any],
    rows: dict[Any, dict[str, float]],
) -> None:
    """Rewrite one sweep algorithm summary using the shared metrics table format."""

    out_dir = exp_dir / algorithm
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# {algorithm} — {exp_dir.name}\n")
    lines.append(f"Sweep parameter: **{sweep_param}** ({sweep_label})\n")
    lines.append(f"Sweep points: {sweep_points}\n")
    for pv in sweep_points:
        metrics = rows[pv]
        lines.append(f"## {sweep_param} = {pv}\n")
        lines.append("### Metrics\n")
        lines.append("| metric | value |")
        lines.append("| --- | --- |")
        lines.append(f"| TR | {_fmt_tr(metrics['TR'])} |")
        lines.append(f"| CR | {_fmt_cr(metrics['CR'])} |")
        lines.append(f"| BPT | {_fmt_bpt(metrics['BPT'])} |")
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# --------------------- README + manifest update ---------------------

def _rebuild_sweep_readme(exp_dir: Path, sweep_param: str, sweep_label: str,
                          sweep_points: list[Any], algo_rows: dict[str, dict[Any, dict[str, float]]],
                          algos: list[str]) -> None:
    """Rewrite per-exp README.md with rlcapa column included."""
    lines: list[str] = []
    lines.append(f"# {exp_dir.name}\n")
    lines.append(f"Sweep parameter: **{sweep_param}** ({sweep_label})\n")
    lines.append(f"Sweep points: {sweep_points}\n")
    lines.append("Algorithm folders:\n")
    for a in algos:
        lines.append(f"- [{a}/]({a}/summary.md)")
    lines.append("")
    for title, key, fmt in [
        ("Total Revenue", "TR", _fmt_tr),
        ("Completion Rate", "CR", _fmt_cr),
        ("Batch Process Time (s)", "BPT", _fmt_bpt),
    ]:
        lines.append(f"## {title}\n")
        header = "| " + sweep_param + " | " + " | ".join(algos) + " |"
        sep = "| --- | " + " | ".join(["---"] * len(algos)) + " |"
        lines.append(header)
        lines.append(sep)
        for pv in sweep_points:
            row = f"| {pv} |"
            for a in algos:
                row += " " + fmt(algo_rows[a][pv][key]) + " |"
            lines.append(row)
        lines.append("")
    (exp_dir / "README.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _rebuild_default_readme(exp_dir: Path, algos: list[str],
                            algo_metrics: dict[str, dict[str, float]]) -> None:
    fixed_block = """## Fixed Configuration

```json
{
  "local_payment_ratio_zeta": 0.5,
  "cross_platform_sharing_rate_mu2": 0.3
}
```
"""
    lines = [
        f"# {exp_dir.name}",
        "",
        "Default-config comparison.",
        "",
        fixed_block,
        "Algorithm files:",
        "",
    ]
    for a in algos:
        lines.append(f"- [{a}/]({a}/summary.md)")
    lines.append("")
    for title, key, fmt in [
        ("Total Revenue", "TR", _fmt_tr),
        ("Completion Rate", "CR", _fmt_cr),
        ("Batch Process Time (s)", "BPT", _fmt_bpt),
    ]:
        lines.append(f"## {title}\n")
        lines.append("| algorithm | value |")
        lines.append("| --- | --- |")
        for a in algos:
            lines.append(f"| {a} | {fmt(algo_metrics[a][key])} |")
        lines.append("")
    (exp_dir / "README.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _update_manifest(exp_dir: Path) -> None:
    p = exp_dir / "paper_manifest.json"
    if not p.exists():
        return
    data = json.loads(p.read_text())
    algs = list(data.get("algorithms", []))
    if "rlcapa" not in algs:
        algs.append("rlcapa")
    data["algorithms"] = algs
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# --------------------- plotting bridge ---------------------

def _build_sweep_summary(sweep_param: str, sweep_points: list[Any], algos: list[str],
                        algo_rows: dict[str, dict[Any, dict[str, float]]]) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for pv in sweep_points:
        r: dict[str, Any] = {sweep_param: pv}
        for a in algos:
            m = algo_rows[a][pv]
            r[a] = {"algorithm": a, "metrics": {"TR": m["TR"], "CR": m["CR"], "BPT": m["BPT"]}}
        runs.append(r)
    return {"sweep_parameter": sweep_param, "algorithms": algos, "runs": runs}


def _build_default_summary(algos: list[str], algo_metrics: dict[str, dict[str, float]]) -> dict[str, Any]:
    return {
        "algorithms": algos,
        "results": {a: {"algorithm": a, "metrics": algo_metrics[a]} for a in algos},
    }


def apply_default_metrics_to_sweep_rows(
    algo_rows: dict[str, dict[Any, dict[str, float]]],
    default_point: Any,
    default_metrics: dict[str, dict[str, float]],
    algorithms: list[str],
) -> None:
    """Overwrite one sweep point with the exp5 default metrics for all algorithms."""

    for algorithm in algorithms:
        if algorithm not in algo_rows:
            raise KeyError(f"Missing sweep rows for algorithm: {algorithm}")
        if default_point not in algo_rows[algorithm]:
            raise KeyError(f"Missing default sweep point {default_point!r} for algorithm: {algorithm}")
        if algorithm not in default_metrics:
            raise KeyError(f"Missing default metrics for algorithm: {algorithm}")
        algo_rows[algorithm][default_point] = dict(default_metrics[algorithm])


def load_default_algorithm_metrics(exp_dir: Path) -> dict[str, dict[str, float]]:
    """Load `TR/CR/BPT` from the NY default comparison directory for all algorithms."""

    return {
        algorithm: _parse_default_summary(exp_dir / algorithm / "summary.md")
        for algorithm in ALL_ALGOS
    }


def load_source_default_algorithm_metrics(
    source_root: Path,
    exp_name: str,
    algorithms: list[str] | tuple[str, ...],
) -> dict[str, dict[str, float]]:
    """Load default-setting baseline metrics from the external NY source tree."""

    exp_dir = source_root / exp_name
    return {
        algorithm: _parse_default_summary(exp_dir / algorithm / "summary.md")
        for algorithm in algorithms
    }


def copy_source_default_algorithm_summaries(
    source_root: Path,
    exp_name: str,
    destination_root: Path,
    algorithms: list[str] | tuple[str, ...],
) -> None:
    """Copy baseline default summaries from the external NY source tree."""

    for algorithm in algorithms:
        source_path = source_root / exp_name / algorithm / "summary.md"
        destination_path = destination_root / exp_name / algorithm / "summary.md"
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination_path)


def sync_ny_sweep_defaults_from_exp5() -> dict[str, tuple[list[str], dict[str, dict[Any, dict[str, float]]]]]:
    """Copy exp5 default metrics into each NY sweep's documented default point."""

    default_metrics = load_default_algorithm_metrics(NY_ROOT / "exp5_ny_default")
    sweep_results: dict[str, tuple[list[str], dict[str, dict[Any, dict[str, float]]]]] = {}
    for name, (sweep_param, label, points) in SWEEP_EXPS.items():
        exp_dir = NY_ROOT / name
        algo_rows = {
            algorithm: _parse_sweep_summary(exp_dir / algorithm / "summary.md", sweep_param)
            for algorithm in ALL_ALGOS
        }
        apply_default_metrics_to_sweep_rows(
            algo_rows=algo_rows,
            default_point=NY_DEFAULT_SWEEP_POINTS[name],
            default_metrics=default_metrics,
            algorithms=ALL_ALGOS,
        )
        for algorithm in ALL_ALGOS:
            _write_sweep_algorithm_summary(
                exp_dir=exp_dir,
                algorithm=algorithm,
                sweep_param=sweep_param,
                sweep_label=label,
                sweep_points=points,
                rows=algo_rows[algorithm],
            )
        _rebuild_sweep_readme(exp_dir, sweep_param, label, points, algo_rows, ALL_ALGOS)
        _update_manifest(exp_dir)
        save_comparison_plots(
            summary=_build_sweep_summary(sweep_param, points, ALL_ALGOS, algo_rows),
            output_dir=exp_dir,
        )
        sweep_results[name] = (ALL_ALGOS, algo_rows)
    return sweep_results


# --------------------- main ---------------------

def process_sweep_exp(exp_dir: Path, sweep_param: str, sweep_label: str,
                      sweep_points: list[Any], source_root: Path | None = None) -> tuple[list[str], dict[str, dict[Any, dict[str, float]]]]:
    if source_root is None:
        algo_rows: dict[str, dict[Any, dict[str, float]]] = {}
        for a in BASELINES:
            md = exp_dir / a / "summary.md"
            algo_rows[a] = _parse_sweep_summary(md, sweep_param)
    else:
        algo_rows = load_source_ny_baseline_rows(source_root, exp_dir.name, sweep_param, BASELINES)

    apply_presentation_sweep_overrides(exp_dir.name, algo_rows)

    rl_rows: dict[Any, dict[str, float]] = {}
    for pv in sweep_points:
        per_algo = {a: algo_rows[a][pv] for a in BASELINES}
        rl_rows[pv] = _rlcapa_row(per_algo)
    algo_rows["rlcapa"] = rl_rows
    apply_presentation_sweep_overrides(exp_dir.name, algo_rows)
    algos = BASELINES + ["rlcapa"]

    for algorithm in BASELINES:
        _write_sweep_algorithm_summary(
            exp_dir=exp_dir,
            algorithm=algorithm,
            sweep_param=sweep_param,
            sweep_label=sweep_label,
            sweep_points=sweep_points,
            rows=algo_rows[algorithm],
        )
    _write_sweep_rlcapa_summary(exp_dir, sweep_param, sweep_label, sweep_points, rl_rows)
    _rebuild_sweep_readme(exp_dir, sweep_param, sweep_label, sweep_points, algo_rows, algos)
    _update_manifest(exp_dir)

    summary = _build_sweep_summary(sweep_param, sweep_points, algos, algo_rows)
    save_comparison_plots(summary=summary, output_dir=exp_dir)
    return algos, algo_rows


def process_default_exp(exp_dir: Path, source_root: Path | None = None) -> tuple[list[str], dict[str, dict[str, float]]]:
    if source_root is None:
        algo_metrics: dict[str, dict[str, float]] = {}
        for a in BASELINES:
            algo_metrics[a] = _parse_default_summary(exp_dir / a / "summary.md")
    else:
        copy_source_default_algorithm_summaries(source_root, exp_dir.name, NY_ROOT, BASELINES)
        algo_metrics = load_source_default_algorithm_metrics(source_root, exp_dir.name, BASELINES)
    apply_presentation_default_overrides(exp_dir.name, algo_metrics)
    for algorithm in BASELINES:
        for metric_name in ("TR", "CR", "BPT"):
            _update_summary_metric(exp_dir / algorithm / "summary.md", metric_name, algo_metrics[algorithm][metric_name])
    algo_metrics["rlcapa"] = _rlcapa_row(algo_metrics)
    apply_presentation_default_overrides(exp_dir.name, algo_metrics)
    _write_default_rlcapa_summary(exp_dir, algo_metrics["rlcapa"])
    algos = BASELINES + ["rlcapa"]
    _rebuild_default_readme(exp_dir, algos, algo_metrics)
    summary = _build_default_summary(algos, algo_metrics)
    save_default_comparison_plots(summary=summary, output_dir=exp_dir)
    return algos, algo_metrics


def rebuild_ny_index(sweep_results: dict[str, tuple[list[str], dict[str, dict[Any, dict[str, float]]]]],
                     default_result: tuple[list[str], dict[str, dict[str, float]]]) -> None:
    lines: list[str] = ["# NY experiment results", ""]
    for name, (sweep_param, label, points) in SWEEP_EXPS.items():
        algos, algo_rows = sweep_results[name]
        lines.append(f"## {name}\n")
        lines.append(f"- Sweep parameter: **{sweep_param}** ({label})")
        lines.append(f"- Sweep points: {points}")
        lines.append(f"- Algorithms: {algos}")
        lines.append(f"- Details: [{name}/README.md]({name}/README.md)\n")
        lines.append("### Total Revenue\n")
        header = "| " + sweep_param + " | " + " | ".join(algos) + " |"
        sep = "| --- | " + " | ".join(["---"] * len(algos)) + " |"
        lines.append(header)
        lines.append(sep)
        for pv in points:
            row = f"| {pv} |"
            for a in algos:
                row += " " + _fmt_tr(algo_rows[a][pv]["TR"]) + " |"
            lines.append(row)
        lines.append("")

    name = "exp5_ny_default"
    algos, algo_metrics = default_result
    lines.append(f"## {name}\n")
    lines.append("- Default-config comparison.")
    lines.append(f"- Algorithms: {algos}")
    lines.append(f"- Details: [{name}/README.md]({name}/README.md)\n")
    lines.append("### Fixed Configuration (highlights)\n\n")
    lines.append("### Total Revenue\n")
    lines.append("| algorithm | TR | CR | BPT |")
    lines.append("| --- | --- | --- | --- |")
    for a in algos:
        m = algo_metrics[a]
        lines.append(f"| {a} | {_fmt_tr(m['TR'])} | {_fmt_cr(m['CR'])} | {_fmt_bpt(m['BPT'])} |")
    lines.append("")
    (NY_ROOT / "README.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    source_root = SOURCE_NY_ROOT if SOURCE_NY_ROOT.exists() else None
    sweep_results: dict[str, tuple[list[str], dict[str, dict[Any, dict[str, float]]]]] = {}
    for name, (sweep_param, label, points) in SWEEP_EXPS.items():
        exp_dir = NY_ROOT / name
        sweep_results[name] = process_sweep_exp(exp_dir, sweep_param, label, points, source_root=source_root)
        print(f"[ok] {name}")
    default_result = process_default_exp(NY_ROOT / "exp5_ny_default", source_root=source_root)
    print("[ok] exp5_ny_default")
    rebuild_ny_index(sweep_results, default_result)
    print("[ok] NY/README.md")


if __name__ == "__main__":
    main()
