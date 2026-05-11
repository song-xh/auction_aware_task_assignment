"""Paper-style Chengdu experiment presets derived from the paper's evaluation axes."""

from __future__ import annotations


DEFAULT_CHENGDU_PAPER_ALGORITHMS = (
    "capa",
    "greedy",
    "ramcom",
    "mra",
    "basegta",
    "impgta",
    "rl-capa-infer",
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
            "deadline_delay": [5, 10],
            "deadline_noise": [-20, 0, 20],
        },
        "formal": {
            "num_parcels": [5000, 20000, 50000, 100000, 200000],
            "local_couriers": [1000, 2000, 3000, 4000, 5000],
            "service_radius": [0.5, 1.0, 1.5, 2.0, 2.5],
            "platforms": [2, 4, 8, 12, 16],
            "courier_capacity": [25, 50, 75, 100, 125],
            "courier_alpha": [0.1, 0.3, 0.5, 0.7, 0.9],
            "deadline_delay": [5, 10, 15, 20, 30, 60],
            "deadline_noise": [-20, -15, -10, -5, 0, 5, 10, 15, 20],
        },
        "ny": {
            "num_parcels": [500, 2000, 5000, 10000, 20000],
            "local_couriers": [100, 200, 300, 400, 500],
            "service_radius": [0.5, 1.0, 1.5, 2.0, 2.5],
            "platforms": [2, 4, 8, 12, 16],
            "courier_capacity": [25, 50, 75, 100, 125],
            "courier_alpha": [0.1, 0.3, 0.5, 0.7, 0.9],
            "deadline_delay": [5, 10, 15, 20, 30, 60],
            "deadline_noise": [-20, -15, -10, -5, 0, 5, 10, 15, 20],
        },
    }
}
