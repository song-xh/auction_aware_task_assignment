"""Re-render plots for existing experiment result directories with the new style.

Sources:
- exp1/exp4/exp6 (and any other dir with summary.json): load summary.json directly.
- exp2_formal_CD, exp3_formal_CD/exp3_formal: parse the result.md sweep tables.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from experiments.plotting import save_comparison_plots


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULT_ROOT = REPO_ROOT / "result"

ALGO_NAME_MAP = {
    "capa": "capa", "greedy": "greedy", "basegta": "basegta",
    "impgta": "impgta", "mra": "mra", "ramcom": "ramcom",
}

SWEEP_PARAM_MAP = {
    "exp1_formal_CD":      "num_parcels",
    "exp1_formal":         "num_parcels",
    "exp2_formal_CD":      "local_couriers",
    "exp2_couriers":       "local_couriers",
    "exp3_formal":         "service_radius",
    "exp3_radius":         "service_radius",
    "exp4_platforms":      "platforms",
    "exp6_capacity":       "courier_capacity",
}


def _parse_result_md(md_path: Path, sweep_param: str) -> dict[str, Any]:
    """Build a summary-like dict from a result.md file with per-setting algo tables."""
    text = md_path.read_text(encoding="utf-8")
    setting_re = re.compile(rf"##\s*{re.escape(sweep_param)}\s*=\s*([0-9.]+)\s*\n(.*?)(?=\n##\s|\Z)", re.S)
    runs: list[dict[str, Any]] = []
    algos_seen: list[str] = []
    for m in setting_re.finditer(text):
        param_value = float(m.group(1))
        if param_value.is_integer():
            param_value = int(param_value)
        block = m.group(2)
        run: dict[str, Any] = {sweep_param: param_value}
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("|") or "---" in line or "TR" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            algo = cells[0]
            if algo not in ALGO_NAME_MAP:
                continue
            try:
                tr = float(cells[1]); cr = float(cells[2]); bpt = float(cells[3])
            except ValueError:
                continue
            run[algo] = {"algorithm": algo, "metrics": {"TR": tr, "CR": cr, "BPT": bpt}}
            if algo not in algos_seen:
                algos_seen.append(algo)
        runs.append(run)
    runs.sort(key=lambda r: r[sweep_param])
    return {"sweep_parameter": sweep_param, "algorithms": algos_seen, "runs": runs}


def _replot_dir(exp_dir: Path) -> None:
    name = exp_dir.name
    sweep_param = SWEEP_PARAM_MAP.get(name)
    if sweep_param is None:
        print(f"[skip] no sweep param mapping for {name}")
        return
    summary_json = exp_dir / "summary.json"
    if summary_json.exists():
        summary = json.loads(summary_json.read_text())
    else:
        md = exp_dir / "result.md"
        if not md.exists():
            print(f"[skip] {name}: neither summary.json nor result.md")
            return
        summary = _parse_result_md(md, sweep_param)
    save_comparison_plots(summary=summary, output_dir=exp_dir)
    print(f"[ok] replotted {exp_dir.relative_to(REPO_ROOT)} ({len(summary.get('runs', []))} settings)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", nargs="*", default=None,
                    help="Result dir names (relative to result/). Default: built-in CD set.")
    args = ap.parse_args()

    if args.targets:
        targets = [RESULT_ROOT / t for t in args.targets]
    else:
        targets = [
            RESULT_ROOT / "exp1_formal_CD",
            RESULT_ROOT / "exp2_formal_CD",
            RESULT_ROOT / "exp3_formal_CD" / "exp3_formal",
            RESULT_ROOT / "exp1_formal",
            RESULT_ROOT / "exp2_couriers",
            RESULT_ROOT / "exp3_radius",
            RESULT_ROOT / "exp4_platforms",
            RESULT_ROOT / "exp6_capacity",
        ]
    for t in targets:
        if t.exists():
            _replot_dir(t)
        else:
            print(f"[miss] {t}")


if __name__ == "__main__":
    main()
