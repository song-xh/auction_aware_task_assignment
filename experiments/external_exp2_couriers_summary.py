"""Aggregate external Chengdu Exp-2 courier results into repo-style artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from experiments.plotting import save_comparison_plots


DEFAULT_EXPERIMENT_NAME = "exp2_cd_couriers_tuned"
PREFERRED_ALGORITHM_ORDER = [
    "capa",
    "greedy",
    "basegta",
    "impgta",
    "mra",
    "ramcom",
    "rlcapa",
]
PLOT_METRICS = ("TR", "CR", "BPT")
DETAIL_METRICS = ("delivered_parcels", "accepted_assignments", "timed_out_parcels")
TARGET_TIMEZONE = ZoneInfo("Asia/Shanghai")


def build_sweep_summary(source_dir: Path, *, experiment_name: str | None = None) -> dict[str, Any]:
    """Build a normalized sweep summary from per-point external result folders.

    Args:
        source_dir: External experiment directory containing `point_*` folders.
        experiment_name: Optional display name for markdown/report output.

    Returns:
        Sweep-level summary payload suitable for markdown rendering and plotting.
    """

    point_dirs = sorted(
        (
            child for child in source_dir.iterdir()
            if child.is_dir() and child.name.startswith("point_") and (child / "summary.json").exists()
        ),
        key=_point_sort_key,
    )
    if not point_dirs:
        raise ValueError(f"No point_* summaries found under {source_dir}")

    discovered_algorithms: list[str] = []
    runs: list[dict[str, Any]] = []
    point_overview: list[dict[str, Any]] = []
    all_started_at: list[str] = []
    all_finished_at: list[str] = []
    total_duration_seconds = 0.0

    for point_dir in point_dirs:
        payload = json.loads((point_dir / "summary.json").read_text(encoding="utf-8"))
        point_value = int(payload.get("local_couriers", _point_sort_key(point_dir)))
        run: dict[str, Any] = {"local_couriers": point_value}
        point_started_at: list[str] = []
        point_finished_at: list[str] = []
        point_duration_seconds = 0.0

        for algorithm in _ordered_algorithms(_discover_algorithms(payload)):
            discovered_algorithms.append(algorithm)
            algorithm_payload = dict(payload[algorithm])
            metrics = dict(algorithm_payload.get("metrics", {}))
            timing = dict(algorithm_payload.get("timing", {}))
            detail_metrics = {
                detail_metric: metrics[detail_metric]
                for detail_metric in DETAIL_METRICS
                if detail_metric in metrics
            }
            run[algorithm] = {
                "algorithm": algorithm,
                "metrics": _normalize_metrics(metrics),
                "detail_metrics": detail_metrics,
                "timing": timing,
            }
            started_at = timing.get("started_at")
            finished_at = timing.get("finished_at")
            duration_seconds = float(timing.get("duration_seconds", 0.0))
            if started_at:
                point_started_at.append(str(started_at))
                all_started_at.append(str(started_at))
            if finished_at:
                point_finished_at.append(str(finished_at))
                all_finished_at.append(str(finished_at))
            point_duration_seconds += duration_seconds
            total_duration_seconds += duration_seconds

        runs.append(run)
        point_overview.append(
            {
                "local_couriers": point_value,
                "earliest_started_at": _min_iso_timestamp(point_started_at),
                "latest_finished_at": _max_iso_timestamp(point_finished_at),
                "total_duration_seconds": point_duration_seconds,
            }
        )

    return {
        "experiment_name": experiment_name or DEFAULT_EXPERIMENT_NAME,
        "source_dir": str(source_dir),
        "summary_file": "summary.json",
        "sweep_parameter": "local_couriers",
        "algorithms": _ordered_algorithms(discovered_algorithms),
        "runs": runs,
        "point_overview": point_overview,
        "global_timing": {
            "earliest_started_at": _min_iso_timestamp(all_started_at),
            "latest_finished_at": _max_iso_timestamp(all_finished_at),
            "total_duration_seconds": total_duration_seconds,
        },
    }


def render_markdown_summary(summary: dict[str, Any]) -> str:
    """Render the normalized sweep summary as a markdown report.

    Args:
        summary: Sweep-level summary produced by `build_sweep_summary`.

    Returns:
        Markdown text containing overview tables, per-point tables, and plot links.
    """

    experiment_name = str(summary.get("experiment_name", DEFAULT_EXPERIMENT_NAME))
    sweep_parameter = str(summary["sweep_parameter"])
    algorithms = [str(algorithm) for algorithm in summary.get("algorithms", [])]
    runs = list(summary.get("runs", []))
    point_overview = list(summary.get("point_overview", []))
    global_timing = dict(summary.get("global_timing", {}))
    settings = [run[sweep_parameter] for run in runs]

    lines = [f"# {experiment_name} 汇总", ""]
    lines.extend(
        [
            "## 全局信息",
            "",
            "| 项目 | 内容 |",
            "| --- | --- |",
            f"| 实验目录 | `{summary.get('source_dir', '')}` |",
            f"| 汇总文件 | `{summary.get('summary_file', 'summary.json')}` |",
            f"| 扫描参数 | `{sweep_parameter}` |",
            f"| 实验设置 | {', '.join(str(value) for value in settings)} |",
            f"| 算法 | {', '.join(algorithms)} |",
            f"| 设置数量 | {len(settings)} |",
            f"| 最早开始时间 | {_format_iso_for_markdown(global_timing.get('earliest_started_at'))} |",
            f"| 最晚结束时间 | {_format_iso_for_markdown(global_timing.get('latest_finished_at'))} |",
            f"| 算法总耗时 | {_format_duration(global_timing.get('total_duration_seconds', 0.0))} |",
            "",
            "## 实验设置总览",
            "",
            f"| {sweep_parameter} | 最早开始 | 最晚结束 | {len(algorithms)}个算法总耗时 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for point in point_overview:
        lines.append(
            "| {value} | {start} | {finish} | {duration} |".format(
                value=point[sweep_parameter],
                start=_format_iso_for_markdown(point.get("earliest_started_at")),
                finish=_format_iso_for_markdown(point.get("latest_finished_at")),
                duration=_format_duration(point.get("total_duration_seconds", 0.0)),
            )
        )

    for run in runs:
        point_value = run[sweep_parameter]
        lines.extend(
            [
                "",
                f"## {sweep_parameter} = {point_value}",
                "",
                "| 算法 | TR | CR | BPT | delivered_parcels | accepted_assignments | timed_out_parcels | 开始时间 | 结束时间 | 耗时 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for algorithm in algorithms:
            if algorithm not in run:
                continue
            metrics = dict(run[algorithm]["metrics"])
            detail_metrics = dict(run[algorithm].get("detail_metrics", {}))
            if not detail_metrics:
                detail_metrics = {
                    detail_metric: metrics[detail_metric]
                    for detail_metric in DETAIL_METRICS
                    if detail_metric in metrics
                }
            timing = dict(run[algorithm].get("timing", {}))
            lines.append(
                "| {algorithm} | {tr:.2f} | {cr:.5f} | {bpt:.6f} | {delivered} | {accepted} | {timed_out} | {started} | {finished} | {duration} |".format(
                    algorithm=algorithm,
                    tr=float(metrics["TR"]),
                    cr=float(metrics["CR"]),
                    bpt=float(metrics["BPT"]),
                    delivered=detail_metrics.get("delivered_parcels", ""),
                    accepted=detail_metrics.get("accepted_assignments", ""),
                    timed_out=detail_metrics.get("timed_out_parcels", ""),
                    started=_format_iso_for_markdown(timing.get("started_at")),
                    finished=_format_iso_for_markdown(timing.get("finished_at")),
                    duration=_format_duration(timing.get("duration_seconds", 0.0)),
                )
            )

    for metric_name in PLOT_METRICS:
        lines.extend(
            [
                "",
                f"## {metric_name} by algorithm and {sweep_parameter}",
                "",
                "| Algorithm | " + " | ".join(str(run[sweep_parameter]) for run in runs) + " |",
                "|---|" + "---:|" * len(runs),
            ]
        )
        for algorithm in algorithms:
            values = []
            for run in runs:
                metric_value = float(run[algorithm]["metrics"][metric_name])
                if metric_name == "TR":
                    values.append(f"{metric_value:.2f}")
                else:
                    values.append(f"{metric_value:.6f}")
            lines.append(f"| {algorithm} | " + " | ".join(values) + " |")

    lines.extend(
        [
            "",
            "## Plots",
            "",
            "![bpt_vs_local_couriers.png](bpt_vs_local_couriers.png)",
            "",
            "![cr_vs_local_couriers.png](cr_vs_local_couriers.png)",
            "",
            "![tr_vs_local_couriers.png](tr_vs_local_couriers.png)",
        ]
    )
    return "\n".join(lines) + "\n"


def write_summary_artifacts(source_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Generate the sweep summary bundle under the requested output directory.

    Args:
        source_dir: External result directory containing `point_*` folders.
        output_dir: Destination directory for summary and plot artifacts.

    Returns:
        The normalized sweep summary used to render the artifacts.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_sweep_summary(source_dir, experiment_name=output_dir.name)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(render_markdown_summary(summary), encoding="utf-8")
    save_comparison_plots(summary=summary, output_dir=output_dir)
    return summary


def main() -> int:
    """Parse CLI arguments and generate summary artifacts."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path, help="External Exp-2 result root.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Destination artifact directory.")
    args = parser.parse_args()
    write_summary_artifacts(source_dir=args.source_dir, output_dir=args.output_dir)
    return 0


def _discover_algorithms(payload: dict[str, Any]) -> list[str]:
    """Return algorithm keys from one per-point summary payload."""

    return [
        key for key, value in payload.items()
        if key != "local_couriers" and isinstance(value, dict) and "metrics" in value
    ]


def _ordered_algorithms(algorithms: Iterable[str]) -> list[str]:
    """Return stable algorithm order with preferred paper-style priority."""

    unique = []
    for algorithm in algorithms:
        if algorithm not in unique:
            unique.append(algorithm)
    preferred = [algorithm for algorithm in PREFERRED_ALGORITHM_ORDER if algorithm in unique]
    extras = sorted(algorithm for algorithm in unique if algorithm not in preferred)
    return preferred + extras


def _normalize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Keep the sweep-level metric subset required for comparison tables and plots."""

    return {
        "TR": float(metrics["TR"]),
        "CR": float(metrics["CR"]),
        "BPT": float(metrics["BPT"]),
    }


def _point_sort_key(point_dir: Path) -> int:
    """Extract the numeric sweep coordinate from a `point_*` directory name."""

    return int(point_dir.name.removeprefix("point_"))


def _min_iso_timestamp(values: list[str]) -> str | None:
    """Return the earliest ISO timestamp from a non-empty collection."""

    if not values:
        return None
    return min(values, key=datetime.fromisoformat)


def _max_iso_timestamp(values: list[str]) -> str | None:
    """Return the latest ISO timestamp from a non-empty collection."""

    if not values:
        return None
    return max(values, key=datetime.fromisoformat)


def _format_iso_for_markdown(timestamp: Any) -> str:
    """Format one ISO timestamp in Asia/Shanghai for markdown tables."""

    if not timestamp:
        return ""
    dt = datetime.fromisoformat(str(timestamp)).astimezone(TARGET_TIMEZONE)
    return dt.strftime("%Y-%m-%d %H:%M:%S CST")


def _format_duration(seconds: Any) -> str:
    """Render a duration in seconds as `HH:MM:SS`."""

    total_seconds = max(0, int(round(float(seconds))))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


if __name__ == "__main__":
    raise SystemExit(main())
