"""Tests for RL-CAPA training and evaluation entrypoints."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from capa.models import CAPAConfig
from env.chengdu import ChengduEnvironment
from experiments.seeding import build_environment_seed


class _LinearTravelModel:
    """Provide deterministic distances and travel times for RL train/eval tests."""

    def distance(self, start: object, end: object) -> float:
        """Return an absolute-distance metric in meters."""
        return float(abs(int(end) - int(start)))

    def travel_time(self, start: object, end: object) -> float:
        """Return the same linear metric as travel time in seconds."""
        return self.distance(start, end)


class RLCAPATrainEvaluateTests(unittest.TestCase):
    """Smoke-test the RL-CAPA train/evaluate surface."""

    @staticmethod
    def _drain_one_step(local, partner, seconds, station_set) -> None:
        """Pop one queued task per courier so drain-based tests can terminate."""
        for courier in [*local, *partner]:
            if getattr(courier, "re_schedule", []):
                head = courier.re_schedule.pop(0)
                courier.location = head.l_node
                courier.re_weight = max(0.0, float(getattr(courier, "re_weight", 0.0)) - float(getattr(head, "weight", 0.0)))

    def test_train_and_evaluate_smoke(self) -> None:
        """One tiny training run should emit checkpoints and one evaluation summary."""
        from rl_capa.config import RLCAPAConfig, RLTrainingConfig
        from rl_capa.evaluate import evaluate_rl_capa
        from rl_capa.train import train_rl_capa

        environment = ChengduEnvironment(
            tasks=[SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[],
            partner_couriers_by_platform={
                "P1": [SimpleNamespace(num=1, location=0, station=SimpleNamespace(l_node=0), station_num=1, re_schedule=[], re_weight=0.0, max_weight=5.0, w=0.4, c=0.6, service_score=0.8)]
            },
            station_set=[SimpleNamespace(num=1, l_node=0)],
            travel_model=_LinearTravelModel(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 1.0},
            movement_callback=self._drain_one_step,
        )
        seed = build_environment_seed(environment)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            train_result = train_rl_capa(
                environment_seed=seed,
                capa_config=CAPAConfig(batch_size=60),
                rl_config=RLCAPAConfig(min_batch_size=60, max_batch_size=60, step_seconds=10),
                training_config=RLTrainingConfig(episodes=1, replay_warmup=1, batch_size=1),
                output_dir=output_dir,
            )
            eval_result = evaluate_rl_capa(
                environment_seed=seed,
                capa_config=CAPAConfig(batch_size=60),
                rl_config=RLCAPAConfig(min_batch_size=60, max_batch_size=60, step_seconds=10),
                checkpoint_dir=output_dir / "checkpoints",
                output_dir=output_dir / "eval",
            )
            self.assertIn("episode_returns", train_result)
            self.assertTrue((output_dir / "checkpoints" / "batch_agent.pt").exists())
            self.assertTrue((output_dir / "checkpoints" / "cross_agent.pt").exists())
            self.assertIn("metrics", eval_result)
            self.assertIn("TR", eval_result["metrics"])


if __name__ == "__main__":
    unittest.main()
