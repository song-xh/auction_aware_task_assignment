"""Registry helpers for the unified top-level algorithm selection flow."""

from __future__ import annotations

from .base import AlgorithmRunner, UnavailableAlgorithmRunner


SUPPORTED_ALGORITHMS = (
    "basegta",
    "capa",
    "greedy",
    "impgta",
    "mra",
    "ramcom",
    "rl-capa",
)


def get_algorithm_names() -> list[str]:
    """Return the canonical list of supported CLI algorithm identifiers."""
    return list(SUPPORTED_ALGORITHMS)


def _build_placeholder_runner(name: str) -> AlgorithmRunner:
    """Return an explicit placeholder runner for algorithms not wired into the root runner yet."""
    if name == "rl-capa":
        return UnavailableAlgorithmRunner(
            algorithm_name=name,
            reason="the actor-critic RL-CAPA runner could not be imported",
        )
    return UnavailableAlgorithmRunner(
        algorithm_name=name,
        reason="the unified runner refactor has not connected this strategy yet",
    )


def build_algorithm_runner(name: str, **kwargs: object) -> AlgorithmRunner:
    """Build the runner object registered to the provided algorithm name."""
    if name not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {name}")
    builder_name = name.replace("-", "_")
    module_name = f"algorithms.{builder_name}_runner"
    function_name = f"build_{builder_name}_runner"
    try:
        module = __import__(module_name, fromlist=[function_name])
        builder = getattr(module, function_name)
    except (ImportError, AttributeError):
        return _build_placeholder_runner(name)
    if not callable(builder):
        raise TypeError(f"Algorithm builder {function_name} in {module_name} is not callable.")
    return builder(**kwargs)
