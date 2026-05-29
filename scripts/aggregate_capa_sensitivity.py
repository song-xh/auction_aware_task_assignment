"""Aggregate exp1 + zeta/omega sensitivity runs into one markdown report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "outputs" / "plots"
REPORT_PATH = OUT_ROOT / "capa_sensitivity_summary.md"

FORMAL_POINTS = (5000, 20000, 50000, 100000, 200000)
NY_POINTS = (500, 2000, 5000, 10000, 20000)
ZETA_RUNS = ("baseline", "zeta_0.1", "zeta_0.3", "zeta_0.4", "zeta_0.5")
OMEGA_RUNS = ("omega_0.5", "omega_0.6", "omega_0.7", "omega_0.8", "omega_0.9", "omega_1.0")


def load_capa_metrics(summary_path: Path) -> dict:
    """Return CAPA `metrics` dict from a point summary file."""

    with summary_path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    return summary["capa"]["metrics"]


def fmt(value: float, precision: int = 4) -> str:
    """Format a float for the markdown table."""

    return f"{value:.{precision}f}"


def make_exp1_table(preset: str, points: Iterable[int]) -> str:
    """Build exp1 markdown table for one preset."""

    header = (
        "| num_parcels | TR | local_TR | cross_TR | CR | BPT | AT_full | AT_single | "
        "delivered | timed_out | final_threshold |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows: list[str] = []
    for p in points:
        metrics = load_capa_metrics(OUT_ROOT / f"exp1_capa_{preset}_rerun" / f"point_{p}" / "summary.json")
        rows.append(
            "| {p} | {tr} | {ltr} | {ctr} | {cr} | {bpt} | {atf} | {ats} | {dlv} | {to} | {th} |\n".format(
                p=p,
                tr=fmt(metrics["TR"], 2),
                ltr=fmt(metrics["local_TR"], 2),
                ctr=fmt(metrics["cross_TR"], 2),
                cr=fmt(metrics["CR"]),
                bpt=fmt(metrics["BPT"], 6),
                atf=fmt(metrics["AT_full"], 6),
                ats=fmt(metrics["AT_single"], 6),
                dlv=metrics["delivered_parcels"],
                to=metrics["timed_out_parcels"],
                th=fmt(metrics["final_local_revenue_threshold"]),
            )
        )
    return header + "".join(rows)


def make_zeta_table(preset: str, point: int) -> str:
    """Build zeta sensitivity table for one preset-point pair."""

    root = OUT_ROOT / f"sens_zeta_{preset}_{point}"
    th_star_path = root / "th_star.json"
    th_star = json.loads(th_star_path.read_text())["final_local_revenue_threshold"]
    header = (
        f"\n### preset={preset}, point={point}, Th*={th_star:.6f} (固定阈值，仅 baseline 用动态)\n\n"
        "| run | zeta | threshold_mode | TR | local_TR | cross_TR | CR |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    rows: list[str] = []
    for tag in ZETA_RUNS:
        metrics = load_capa_metrics(root / tag / "summary.json")
        if tag == "baseline":
            zeta_val = "0.2"
            mode = "dynamic"
        else:
            zeta_val = tag.split("_", 1)[1]
            mode = f"fixed={th_star:.4f}"
        rows.append(
            "| {tag} | {z} | {m} | {tr} | {ltr} | {ctr} | {cr} |\n".format(
                tag=tag,
                z=zeta_val,
                m=mode,
                tr=fmt(metrics["TR"], 2),
                ltr=fmt(metrics["local_TR"], 2),
                ctr=fmt(metrics["cross_TR"], 2),
                cr=fmt(metrics["CR"]),
            )
        )
    return header + "".join(rows)


def make_omega_table(preset: str, point: int) -> str:
    """Build omega sensitivity table for one preset-point pair."""

    root = OUT_ROOT / f"sens_omega_{preset}_{point}"
    header = (
        f"\n### preset={preset}, point={point} (动态阈值，仅 omega 变化)\n\n"
        "| omega | TR | local_TR | cross_TR | CR | final_threshold |\n"
        "|---|---|---|---|---|---|\n"
    )
    rows: list[str] = []
    for tag in OMEGA_RUNS:
        metrics = load_capa_metrics(root / tag / "summary.json")
        rows.append(
            "| {o} | {tr} | {ltr} | {ctr} | {cr} | {th} |\n".format(
                o=tag.split("_", 1)[1],
                tr=fmt(metrics["TR"], 2),
                ltr=fmt(metrics["local_TR"], 2),
                ctr=fmt(metrics["cross_TR"], 2),
                cr=fmt(metrics["CR"]),
                th=fmt(metrics["final_local_revenue_threshold"]),
            )
        )
    return header + "".join(rows)


def main() -> int:
    """Write capa_sensitivity_summary.md aggregating all stages."""

    parts: list[str] = ["# CAPA exp1 重跑 + zeta/omega 敏感性汇总\n\n"]
    parts.append(
        "Canonical seed per preset shared across all stages. CAPA only.\n"
        "- formal task window: [0, 14398]s; ny task window: [0, 3600]s.\n"
        "- seed: outputs/shared_pool/{formal,ny}/canonical_seed.pkl.\n"
        "- baseline zeta=0.2, omega=0.8.\n\n"
    )

    parts.append("## 实验 A：exp1 重跑\n\n### preset=formal\n\n")
    parts.append(make_exp1_table("formal", FORMAL_POINTS))
    parts.append("\n### preset=ny\n\n")
    parts.append(make_exp1_table("ny", NY_POINTS))

    parts.append("\n## 实验 B：zeta 敏感性（固定阈值）\n")
    parts.append(make_zeta_table("formal", 50000))
    parts.append(make_zeta_table("ny", 5000))

    parts.append("\n## 实验 C：omega 敏感性（动态阈值）\n")
    parts.append(make_omega_table("formal", 50000))
    parts.append(make_omega_table("ny", 5000))

    REPORT_PATH.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
