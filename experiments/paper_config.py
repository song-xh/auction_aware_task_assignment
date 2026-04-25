"""Paper-style Chengdu experiment presets derived from the paper's evaluation axes."""

from __future__ import annotations


DEFAULT_CHENGDU_PAPER_ALGORITHMS = (
    "capa",
    "greedy",
    "ramcom",
    "mra",
    "basegta",
    "impgta",
)


PAPER_SUITE_PRESETS: dict[str, dict[str, dict[str, list[float]]]] = {
    "chengdu-paper": {
        "smoke": {
            "num_parcels": [20, 50],
            "local_couriers": [2, 4],
            "service_radius": [0.5, 1.5],
            "platforms": [1, 2],
            "courier_capacity": [25, 50],
            "courier_alpha": [0.3, 0.7],
        },
        "formal": {
            "num_parcels": [1000, 2000, 3000, 5000],
            "local_couriers": [50, 100, 150, 200, 250],
            "service_radius": [0.5, 1.0, 1.5, 2.0, 2.5],
            "platforms": [2, 4, 8, 12, 16],
            "courier_capacity": [25, 50, 75, 100, 125],
            "courier_alpha": [0.1, 0.3, 0.5, 0.7, 0.9],
        },
    }
}
