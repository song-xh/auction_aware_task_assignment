"""Run Exp-8 deadline-noise sweep in a single Python process with fork workers.

Parses the Chengdu road graph once + loads the canonical seed once, then forks
workers via multiprocessing so seed pages stay shared via copy-on-write. Each
worker derives one noise point in place and runs CAPA, avoiding the per-point
graph-parse + 4x seed-deepcopy overhead of the subprocess pool runner.

Usage:
    python -m experiments.run_exp8_inproc --scale 50000p
    python -m experiments.run_exp8_inproc --scale 5000p --max-parallel 3
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
import traceback
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.chengdu import ChengduEnvironment, set_courier_speed_kmh
from experiments.deadline_disturbance import (
    DEADLINE_NOISE_AXIS,
    DEADLINE_NOISE_VALUES,
    derive_deadline_noise_environment,
)
from experiments.paper_chengdu import DEFAULT_CHENGDU_PAPER_FIXED_CONFIG
from experiments.seeding import build_environment_seed, load_environment_seed, save_environment_seed

SCALE_CONFIGS = {
    "5000p": {
        "num_parcels": 5000,
        "local_couriers": 300,
        "platforms": 4,
        "couriers_per_platform": 50,
        "task_window_start_seconds": 0,
        "task_window_end_seconds": 900,
        "noise_window": (300.0, 600.0),
        "partner_history_task_count_start": 2000,
        "partner_history_task_count_step": 0,
        "seed_dir": Path("/tmp/chengdu_exp8_5000p_inproc"),
        "default_output": Path("outputs/plots/exp8_capa_5000p_noise_sweep_inproc"),
    },
    "50000p": {
        "num_parcels": 50000,
        "local_couriers": 3000,
        "platforms": 4,
        "couriers_per_platform": 200,
        "task_window_start_seconds": 0,
        "task_window_end_seconds": 1800,
        "noise_window": (300.0, 900.0),
        "partner_history_task_count_start": 2000,
        "partner_history_task_count_step": 0,
        "seed_dir": Path("/tmp/chengdu_exp8_50000p_inproc"),
        "default_output": Path("outputs/plots/exp8_capa_50000p_noise_sweep_inproc"),
    },
}

NOISE_VALUES = list(DEADLINE_NOISE_VALUES)  # [-20, -15, -10, -5, 0, 5, 10, 15, 20]


def _read_available_mb() -> float:
    """Read MemAvailable from /proc/meminfo in MiB; -1 if unavailable."""
    try:
        with open("/proc/meminfo", "r") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return -1.0


def _adaptive_parallel(scale: str, requested: int) -> int:
    """Cap parallelism based on free RAM to avoid OOM."""
    avail_mb = _read_available_mb()
    if avail_mb < 0:
        return requested
    # 50000p: ~1.5 GB per child after derive + CAPA peak
    # 5000p:  ~0.3 GB per child
    per_child_mb = 1500 if scale == "50000p" else 300
    safe = max(1, int(avail_mb // per_child_mb))
    return max(1, min(requested, safe))


def _build_or_load_seed(scale_cfg: dict, log_path: Path) -> Path:
    """Build canonical seed if missing, else return existing path."""
    seed_path = scale_cfg["seed_dir"] / "canonical_seed.pkl"
    if seed_path.exists():
        msg = f"[seed] Reusing {seed_path}"
        print(msg, flush=True)
        with log_path.open("a") as fh:
            fh.write(msg + "\n")
        return seed_path
    msg = f"[seed] Building canonical environment for {scale_cfg['num_parcels']}p..."
    print(msg, flush=True)
    with log_path.open("a") as fh:
        fh.write(msg + "\n")
    fixed = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    fixed.update({
        "num_parcels": scale_cfg["num_parcels"],
        "local_couriers": scale_cfg["local_couriers"],
        "platforms": scale_cfg["platforms"],
        "couriers_per_platform": scale_cfg["couriers_per_platform"],
        "task_window_start_seconds": scale_cfg["task_window_start_seconds"],
        "task_window_end_seconds": scale_cfg["task_window_end_seconds"],
        "partner_history_task_count_start": scale_cfg["partner_history_task_count_start"],
        "partner_history_task_count_step": scale_cfg["partner_history_task_count_step"],
    })
    env = ChengduEnvironment.build(
        data_dir=Path(fixed["data_dir"]),
        num_parcels=int(fixed["num_parcels"]),
        local_courier_count=int(fixed["local_couriers"]),
        cooperating_platform_count=int(fixed["platforms"]),
        couriers_per_platform=int(fixed["couriers_per_platform"]),
        service_radius_km=fixed.get("service_radius_km"),
        courier_capacity=fixed.get("courier_capacity"),
        task_window_start_seconds=fixed.get("task_window_start_seconds"),
        task_window_end_seconds=fixed.get("task_window_end_seconds"),
        task_sampling_seed=int(fixed["task_sampling_seed"]),
        partner_history_task_count_start=int(fixed["partner_history_task_count_start"]),
        partner_history_task_count_step=int(fixed["partner_history_task_count_step"]),
        courier_alpha=float(fixed["courier_alpha"]),
        courier_service_score=float(fixed["courier_service_score"]),
        platform_quality_start=float(fixed["platform_quality_start"]),
        platform_quality_step=float(fixed["platform_quality_step"]),
        courier_speed_kmh=30.0,
    )
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    save_environment_seed(build_environment_seed(env), seed_path)
    msg = f"[seed] Saved to {seed_path}"
    print(msg, flush=True)
    with log_path.open("a") as fh:
        fh.write(msg + "\n")
    return seed_path


_SHARED_SEED = None  # Populated in the parent before fork; inherited via CoW.


def _worker_run_point(noise_value: float, scale_cfg: dict, output_dir: Path, batch_size: int) -> dict:
    """Run one noise point in a forked worker. Returns the point summary dict."""
    from algorithms.registry import build_algorithm_runner
    from experiments.seeding import clone_environment_from_seed

    point_dir = output_dir / f"point_{_token(noise_value)}"
    point_dir.mkdir(parents=True, exist_ok=True)
    log_h = (point_dir / "stdout.log").open("w", encoding="utf-8")
    err_h = (point_dir / "stderr.log").open("w", encoding="utf-8")
    sys.stdout = log_h
    sys.stderr = err_h
    try:
        t0 = time.time()
        print(f"[worker pid={os.getpid()}] noise={noise_value} start", flush=True)
        seed = _SHARED_SEED
        if seed is None:
            raise RuntimeError("Worker did not inherit _SHARED_SEED from parent fork.")
        # Derive a fresh point environment from the shared seed (CoW-friendly).
        env = derive_deadline_noise_environment(
            seed,
            noise_percent=noise_value,
            noise_window=scale_cfg.get("noise_window"),
        )
        print(f"[worker] derive_env done in {time.time()-t0:.1f}s; running CAPA...", flush=True)

        progress_path = point_dir / "progress.json"

        def progress_cb(event: dict) -> None:
            try:
                with progress_path.open("w") as fh:
                    json.dump({"axis_value": noise_value, "last_event": event, "updated_at": time.time()}, fh)
            except Exception:
                pass

        runner = build_algorithm_runner("capa", batch_size=batch_size)
        # CAPA runner mutates env; pass clone to be safe.
        capa_env = clone_environment_from_seed(build_environment_seed(env))
        result = runner.run(
            environment=capa_env,
            output_dir=point_dir / "capa",
            progress_callback=progress_cb,
        )
        summary = {DEADLINE_NOISE_AXIS: noise_value, "capa": result}
        with (point_dir / "summary.json").open("w") as fh:
            json.dump(summary, fh, indent=2)
        print(f"[worker] noise={noise_value} done in {time.time()-t0:.1f}s", flush=True)
        return {"value": noise_value, "ok": True, "elapsed": time.time() - t0, "point_dir": str(point_dir)}
    except Exception as exc:
        traceback.print_exc(file=err_h)
        return {"value": noise_value, "ok": False, "error": str(exc), "point_dir": str(point_dir)}
    finally:
        log_h.close()
        err_h.close()


def _token(value: float) -> str:
    text = str(value)
    return text.replace("-", "neg").replace(".", "_")


def _drive_workers(values: list[float], scale_cfg: dict, output_dir: Path, batch_size: int, max_parallel: int, log_path: Path) -> list[dict]:
    """Launch worker forks bounded by max_parallel, log per-point status."""
    ctx = mp.get_context("fork")
    pending = list(values)
    in_flight: dict[float, mp.Process] = {}
    parent_conns: dict[float, mp.connection.Connection] = {}
    results: list[dict] = []

    def _spawn(value: float) -> None:
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        def _wrap() -> None:
            res = _worker_run_point(value, scale_cfg, output_dir, batch_size)
            child_conn.send(res)
            child_conn.close()
        proc = ctx.Process(target=_wrap)
        proc.start()
        in_flight[value] = proc
        parent_conns[value] = parent_conn
        msg = f"[run] launch noise={value} pid={proc.pid}"
        print(msg, flush=True)
        with log_path.open("a") as fh:
            fh.write(msg + "\n")

    while pending or in_flight:
        while pending and len(in_flight) < max_parallel:
            _spawn(pending.pop(0))
        done_vals: list[float] = []
        for v, proc in in_flight.items():
            if not proc.is_alive():
                done_vals.append(v)
        for v in done_vals:
            proc = in_flight.pop(v)
            conn = parent_conns.pop(v)
            try:
                res = conn.recv() if conn.poll(timeout=1.0) else {"value": v, "ok": False, "error": "no result from worker"}
            except EOFError:
                res = {"value": v, "ok": False, "error": "EOF from worker"}
            conn.close()
            proc.join()
            status = "OK" if res.get("ok") else f"FAILED ({res.get('error')})"
            elapsed = res.get("elapsed", 0)
            msg = f"[run] done noise={v} {status} elapsed={elapsed:.1f}s rc={proc.exitcode}"
            print(msg, flush=True)
            with log_path.open("a") as fh:
                fh.write(msg + "\n")
            results.append(res)
        if in_flight:
            time.sleep(15)
    return results


def _aggregate(results: list[dict], output_dir: Path, log_path: Path) -> dict:
    runs = []
    for res in sorted(results, key=lambda r: r["value"]):
        if not res.get("ok"):
            continue
        summary_path = Path(res["point_dir"]) / "summary.json"
        with summary_path.open("r") as fh:
            runs.append(json.load(fh))
    summary = {"sweep_parameter": DEADLINE_NOISE_AXIS, "algorithms": ["capa"], "runs": runs}
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2)
    try:
        from experiments.plotting import save_comparison_plots
        save_comparison_plots(summary=summary, output_dir=output_dir)
    except Exception as exc:
        print(f"[agg] plot save failed: {exc}", flush=True)
    msg = f"[agg] aggregated {len(runs)}/{len(results)} runs → {output_dir / 'summary.json'}"
    print(msg, flush=True)
    with log_path.open("a") as fh:
        fh.write(msg + "\n")
    return summary


def main() -> int:
    """Parse args, build shared seed in parent, fork workers, aggregate."""
    parser = argparse.ArgumentParser(description="In-process Exp-8 noise sweep with fork workers.")
    parser.add_argument("--scale", choices=list(SCALE_CONFIGS.keys()), required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--max-parallel", type=int, default=3, help="Requested max fork workers; auto-capped by RAM.")
    parser.add_argument("--noise-values", default=None, help="Optional comma-separated subset of noise values.")
    args = parser.parse_args()

    scale_cfg = SCALE_CONFIGS[args.scale]
    output_dir = Path(args.output_dir) if args.output_dir else scale_cfg["default_output"]
    output_dir.mkdir(parents=True, exist_ok=True)
    scale_cfg["seed_dir"].mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "inproc_run.log"
    log_path.write_text(f"Exp-8 inproc run scale={args.scale} max_parallel_req={args.max_parallel}\n", encoding="utf-8")

    # Pin Chengdu graph velocity to 30 km/h before any travel-model is constructed,
    # so the parent's ChengduGraphTravelModel and all forked workers use the same
    # speed runner.py applies by default. Mismatch with the default 0.0011 km/s
    # (≈4 km/h) silently corrupted prior sweeps with backlog + timeout inflation.
    set_courier_speed_kmh(30.0)

    seed_path = _build_or_load_seed(scale_cfg, log_path)

    # Load seed once in parent; forked workers inherit via CoW.
    print(f"[parent pid={os.getpid()}] loading seed into shared memory...", flush=True)
    global _SHARED_SEED
    t0 = time.time()
    _SHARED_SEED = load_environment_seed(seed_path)
    print(f"[parent] seed loaded in {time.time()-t0:.1f}s; |tasks|={len(_SHARED_SEED.tasks)}", flush=True)

    requested = max(1, int(args.max_parallel))
    capped = _adaptive_parallel(args.scale, requested)
    msg = f"[parent] adaptive parallel: requested={requested} → effective={capped} (free={_read_available_mb():.0f} MiB)"
    print(msg, flush=True)
    with log_path.open("a") as fh:
        fh.write(msg + "\n")

    if args.noise_values:
        values = [float(x) for x in args.noise_values.split(",") if x.strip()]
    else:
        values = list(NOISE_VALUES)

    results = _drive_workers(values, scale_cfg, output_dir, args.batch_size, capped, log_path)
    _aggregate(results, output_dir, log_path)
    failed = [r for r in results if not r.get("ok")]
    print(f"[done] total={len(results)} failed={len(failed)}", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
