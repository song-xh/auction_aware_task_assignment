"""Generic managed multi-round experiment controller."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

from .models import ManagedRoundSpec


def run_managed_rounds(
    round_specs: Sequence[ManagedRoundSpec],
    round_output_dir_builder: Callable[[int, ManagedRoundSpec], Path],
    round_executor: Callable[[ManagedRoundSpec, Path], dict[str, Any]],
    round_analyzer: Callable[[dict[str, Any], ManagedRoundSpec], dict[str, Any]],
    round_promoter: Callable[[Path], None],
) -> dict[str, Any]:
    """Run managed rounds until one round is accepted.

    Args:
        round_specs: Ordered managed round specifications.
        round_output_dir_builder: Builds the output directory for one round.
        round_executor: Executes one round and returns its summary.
        round_analyzer: Scores one round summary and returns an analysis payload with `accepted`.
        round_promoter: Promotes the accepted round output to its final location.

    Returns:
        Final managed manifest describing all attempted rounds.
    """

    round_manifests: list[dict[str, Any]] = []
    for round_index, round_spec in enumerate(round_specs, start=1):
        round_output_dir = round_output_dir_builder(round_index, round_spec)
        summary = round_executor(round_spec, round_output_dir)
        analysis = round_analyzer(summary, round_spec)
        round_manifest = {
            "round_index": round_index,
            "round_name": round_spec.name,
            "round_output_dir": str(round_output_dir),
            "summary": summary,
            "analysis": analysis,
        }
        round_manifests.append(round_manifest)
        if bool(analysis.get("accepted")):
            round_promoter(round_output_dir)
            return {
                "accepted_round_index": round_index,
                "accepted_round_name": round_spec.name,
                "rounds": round_manifests,
            }
    return {
        "accepted_round_index": None,
        "accepted_round_name": None,
        "rounds": round_manifests,
    }
