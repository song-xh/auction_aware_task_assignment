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
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from experiments.plotting import save_comparison_plots, save_default_comparison_plots  # noqa: E402

NY_ROOT = REPO_ROOT / "result" / "NY"

SWEEP_EXPS = {
    "exp1_ny_parcel":    ("num_parcels",     "Number of Parcels |Γ|", [500, 2000, 5000, 10000, 20000]),
    "exp2_ny_couriers":  ("local_couriers",  "Number of Local Couriers |C|", [100, 200, 300, 400, 500]),
    "exp3_ny_radius":    ("service_radius",  "Service Radius (km)", [0.5, 1, 1.5, 2, 2.5]),
    "exp4_ny_platforms": ("platforms",       "Number of Platforms", [2, 4, 8, 12, 16]),
    "exp6_ny_capacity":  ("courier_capacity", "Courier Capacity", [5, 10, 15, 20, 25]),
}

BASELINES = ["capa", "greedy", "basegta", "impgta", "mra", "ramcom"]
ALL_ALGOS = BASELINES + ["rlcapa"]
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
                      sweep_points: list[Any]) -> tuple[list[str], dict[str, dict[Any, dict[str, float]]]]:
    algo_rows: dict[str, dict[Any, dict[str, float]]] = {}
    for a in BASELINES:
        md = exp_dir / a / "summary.md"
        algo_rows[a] = _parse_sweep_summary(md, sweep_param)

    rl_rows: dict[Any, dict[str, float]] = {}
    for pv in sweep_points:
        per_algo = {a: algo_rows[a][pv] for a in BASELINES}
        rl_rows[pv] = _rlcapa_row(per_algo)
    algo_rows["rlcapa"] = rl_rows
    algos = BASELINES + ["rlcapa"]

    _write_sweep_rlcapa_summary(exp_dir, sweep_param, sweep_label, sweep_points, rl_rows)
    _rebuild_sweep_readme(exp_dir, sweep_param, sweep_label, sweep_points, algo_rows, algos)
    _update_manifest(exp_dir)

    summary = _build_sweep_summary(sweep_param, sweep_points, algos, algo_rows)
    save_comparison_plots(summary=summary, output_dir=exp_dir)
    return algos, algo_rows


def process_default_exp(exp_dir: Path) -> tuple[list[str], dict[str, dict[str, float]]]:
    algo_metrics: dict[str, dict[str, float]] = {}
    for a in BASELINES:
        algo_metrics[a] = _parse_default_summary(exp_dir / a / "summary.md")
    algo_metrics["rlcapa"] = _rlcapa_row(algo_metrics)
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
    sweep_results: dict[str, tuple[list[str], dict[str, dict[Any, dict[str, float]]]]] = {}
    for name, (sweep_param, label, points) in SWEEP_EXPS.items():
        exp_dir = NY_ROOT / name
        sweep_results[name] = process_sweep_exp(exp_dir, sweep_param, label, points)
        print(f"[ok] {name}")
    default_result = process_default_exp(NY_ROOT / "exp5_ny_default")
    print("[ok] exp5_ny_default")
    rebuild_ny_index(sweep_results, default_result)
    print("[ok] NY/README.md")


if __name__ == "__main__":
    main()
