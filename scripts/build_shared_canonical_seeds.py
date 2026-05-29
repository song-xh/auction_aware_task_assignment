"""Build canonical Chengdu environment seeds shared across exp1/sensitivity runs.

For each preset in {formal, ny}, the canonical seed contains the *maximum*
preset num_parcels and the partner-history-task layout. Downstream point
runs derive each point environment as a deterministic prefix of this seed,
so every point/sensitivity variant sees the same parcels and the same
partner history.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.chengdu import ChengduEnvironment
from experiments.paper_chengdu import (
    _canonical_environment_kwargs_for_axis,
    build_preset_fixed_config,
)
from experiments.paper_config import PAPER_SUITE_PRESETS
from experiments.seeding import build_environment_seed, save_environment_seed


SHARED_POOL_ROOT = Path("outputs/shared_pool")
AXIS = "num_parcels"


def build_seed_for_preset(preset_name: str) -> Path:
    """Build and persist one canonical seed for the requested preset."""

    fixed_config = build_preset_fixed_config(preset_name)
    axis_values = PAPER_SUITE_PRESETS["chengdu-paper"][preset_name][AXIS]
    kwargs = _canonical_environment_kwargs_for_axis(
        axis=AXIS,
        axis_values=axis_values,
        fixed_config=fixed_config,
    )
    print(
        f"[{preset_name}] building canonical env: "
        f"num_parcels={kwargs['num_parcels']}, "
        f"task_window=[{fixed_config['task_window_start_seconds']}, {fixed_config['task_window_end_seconds']}], "
        f"local_couriers={kwargs['local_courier_count']}, "
        f"platforms={kwargs['cooperating_platform_count']}, "
        f"task_sampling_seed={kwargs['task_sampling_seed']}",
        flush=True,
    )
    environment = ChengduEnvironment.build(**kwargs)
    seed = build_environment_seed(environment)
    out_dir = SHARED_POOL_ROOT / preset_name
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_path = out_dir / "canonical_seed.pkl"
    save_environment_seed(seed, seed_path)
    print(f"[{preset_name}] canonical seed written: {seed_path}", flush=True)
    return seed_path


def main() -> int:
    """Build canonical seeds for both formal and ny presets."""

    for preset_name in ("formal", "ny"):
        build_seed_for_preset(preset_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
