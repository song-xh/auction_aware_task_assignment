"""Public exports for the Phase 4 CAPA implementation."""

from .cama import run_cama
from .dapa import run_dapa
from .models import CAPAConfig, CAPAResult, CooperatingPlatform, Courier, Parcel
from .runner import run_capa
from .travel import DistanceMatrixTravelModel


def run_chengdu_experiment(*args, **kwargs):
    """Import the Chengdu experiment entrypoint lazily to avoid env/capa circular imports."""
    from .experiments import run_chengdu_experiment as _run_chengdu_experiment

    return _run_chengdu_experiment(*args, **kwargs)

__all__ = [
    "CAPAConfig",
    "CAPAResult",
    "CooperatingPlatform",
    "Courier",
    "DistanceMatrixTravelModel",
    "Parcel",
    "run_cama",
    "run_capa",
    "run_chengdu_experiment",
    "run_dapa",
]
