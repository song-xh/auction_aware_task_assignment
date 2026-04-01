# Unified Runner And Chengdu Environment Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the repository so that `env/chengdu.py` is the single reusable Chengdu simulation environment and the repository root exposes one unified `runner.py` CLI that selects `capa`, `rl-capa`, `greedy`, `basegta`, or `impgta` through an explicit algorithm registry.

**Architecture:** Keep all environment concerns in `env/chengdu.py`: station generation, courier seeding, task loading, simulation stepping, route draining, and state write-back. Move algorithm selection and orchestration into a root-level `runner.py` plus a thin registry layer that maps CLI algorithm names to strategy adapters. CAPA, Greedy, BaseGTA, and ImpGTA become environment-driven strategies; `rl-capa` is registered now but must fail explicitly with `NotImplementedError` until Phase 5 lands.

**Tech Stack:** Python 3, `argparse`, existing `env/`, `capa/`, `baselines/`, `unittest`, git conventional commits.

---

### Task 1: Define the unified strategy contract and registry

**Files:**
- Create: `algorithms/__init__.py`
- Create: `algorithms/base.py`
- Create: `algorithms/registry.py`
- Test: `tests/test_algorithm_registry.py`

**Step 1: Write the failing test**

```python
def test_registry_exposes_all_supported_algorithm_names():
    from algorithms.registry import get_algorithm_names

    assert get_algorithm_names() == [
        "basegta",
        "capa",
        "greedy",
        "impgta",
        "rl-capa",
    ]


def test_rl_capa_registration_is_explicitly_unimplemented():
    from algorithms.registry import build_algorithm_runner

    runner = build_algorithm_runner("rl-capa")
    with pytest.raises(NotImplementedError):
        runner.run(environment=None, output_dir=None)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_algorithm_registry -v`
Expected: FAIL because `algorithms.registry` does not exist.

**Step 3: Write minimal implementation**

Implement a small contract such as:

```python
class AlgorithmRunner(Protocol):
    def run(self, environment: Any, output_dir: Path | None = None) -> dict[str, Any]:
        ...
```

and a registry such as:

```python
REGISTRY = {
    "capa": build_capa_runner,
    "greedy": build_greedy_runner,
    "basegta": build_basegta_runner,
    "impgta": build_impgta_runner,
    "rl-capa": build_rl_capa_runner,
}
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_algorithm_registry -v`
Expected: PASS

**Step 5: Commit**

```bash
git add algorithms/__init__.py algorithms/base.py algorithms/registry.py tests/test_algorithm_registry.py
git commit -m "feat(runner): add unified algorithm registry contract"
```

### Task 2: Refactor `env/chengdu.py` into a single reusable environment object

**Files:**
- Modify: `env/chengdu.py`
- Modify: `env/__init__.py`
- Test: `tests/test_env_chengdu.py`
- Test: `tests/test_chengdu_runner.py`

**Step 1: Write the failing test**

```python
def test_environment_builds_once_and_exposes_reusable_runtime_methods():
    from env.chengdu import ChengduEnvironment

    environment = ChengduEnvironment.build(
        data_dir=Path("Data"),
        num_parcels=10,
        local_courier_count=2,
        cooperating_platform_count=1,
        couriers_per_platform=1,
    )

    assert hasattr(environment, "advance")
    assert hasattr(environment, "drain")
    assert hasattr(environment, "snapshot_for_algorithm")
    assert hasattr(environment, "apply_assignments")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_env_chengdu tests.test_chengdu_runner -v`
Expected: FAIL because `ChengduEnvironment` does not exist.

**Step 3: Write minimal implementation**

Introduce a single environment class in `env/chengdu.py` that owns:

- immutable build parameters
- current task/courier/platform state
- methods for `advance(seconds)`, `drain()`, `snapshot_for_algorithm(...)`, `apply_assignments(...)`
- helper accessors for local couriers, partner couriers, and task batches

Keep legacy-specific loaders and movement hooks private to this module.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_env_chengdu tests.test_chengdu_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add env/chengdu.py env/__init__.py tests/test_env_chengdu.py tests/test_chengdu_runner.py
git commit -m "refactor(env): unify Chengdu simulation environment interface"
```

### Task 3: Port CAPA to the environment-driven strategy interface

**Files:**
- Create: `algorithms/capa_runner.py`
- Modify: `capa/runner.py`
- Modify: `capa/experiments.py`
- Test: `tests/test_capa_runner.py`
- Test: `tests/test_runner_cli.py`

**Step 1: Write the failing test**

```python
def test_capa_strategy_runs_against_unified_environment():
    from algorithms.capa_runner import build_capa_runner

    runner = build_capa_runner(batch_size=300)
    result = runner.run(environment=fake_environment, output_dir=None)

    assert result["algorithm"] == "capa"
    assert "metrics" in result
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_capa_runner tests.test_runner_cli -v`
Expected: FAIL because `algorithms.capa_runner` does not exist.

**Step 3: Write minimal implementation**

Wrap the existing CAPA decision logic so that:

- environment creation is not inside `capa/experiments.py`
- `capa/runner.py` consumes environment snapshots instead of constructing its own top-level lifecycle
- plotting and JSON writing stay optional helper behavior outside the strategy core

`capa/experiments.py` should stop being the primary entrypoint and become a compatibility helper around the new root runner.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_capa_runner tests.test_runner_cli -v`
Expected: PASS

**Step 5: Commit**

```bash
git add algorithms/capa_runner.py capa/runner.py capa/experiments.py tests/test_capa_runner.py tests/test_runner_cli.py
git commit -m "refactor(capa): plug CAPA into unified environment runner"
```

### Task 4: Port Greedy, BaseGTA, and ImpGTA to the same environment lifecycle

**Files:**
- Create: `algorithms/greedy_runner.py`
- Create: `algorithms/basegta_runner.py`
- Create: `algorithms/impgta_runner.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/gta.py`
- Test: `tests/test_baseline_runner.py`
- Test: `tests/test_runner_cli.py`

**Step 1: Write the failing test**

```python
def test_all_baselines_share_same_environment_contract():
    from algorithms.registry import build_algorithm_runner

    for name in ["greedy", "basegta", "impgta"]:
        runner = build_algorithm_runner(name)
        result = runner.run(environment=fake_environment, output_dir=None)
        assert result["algorithm"] == name
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_baseline_runner tests.test_runner_cli -v`
Expected: FAIL because the new strategy wrappers do not exist.

**Step 3: Write minimal implementation**

Refactor baseline code so that:

- Greedy no longer owns top-level experiment control flow
- BaseGTA and ImpGTA use the same environment methods as CAPA
- no baseline directly constructs stations, couriers, or simulation loops outside `env/chengdu.py`

Keep algorithm-specific decision logic in `baselines/`, but move orchestration into the new strategy wrappers.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_baseline_runner tests.test_runner_cli -v`
Expected: PASS

**Step 5: Commit**

```bash
git add algorithms/greedy_runner.py algorithms/basegta_runner.py algorithms/impgta_runner.py baselines/greedy.py baselines/gta.py tests/test_baseline_runner.py tests/test_runner_cli.py
git commit -m "refactor(baselines): route greedy and gta baselines through unified environment"
```

### Task 5: Add the root-level unified `runner.py` CLI

**Files:**
- Create: `runner.py`
- Create: `tests/test_runner_cli.py`
- Modify: `README.md`

**Step 1: Write the failing test**

```python
def test_runner_cli_dispatches_selected_algorithm():
    completed = subprocess.run(
        [
            "python3",
            "runner.py",
            "--algorithm",
            "capa",
            "--data-dir",
            "Data",
            "--num-parcels",
            "10",
            "--local-couriers",
            "2",
            "--platforms",
            "1",
            "--couriers-per-platform",
            "1",
            "--batch-size",
            "300",
            "--output-dir",
            "outputs/plots/test_runner_cli",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_runner_cli -v`
Expected: FAIL because `runner.py` does not exist.

**Step 3: Write minimal implementation**

Implement a root CLI that:

- parses common Chengdu environment parameters once
- loads the algorithm from `algorithms.registry`
- builds `ChengduEnvironment`
- runs the selected algorithm
- writes `summary.json` and optional plots
- raises a clear `NotImplementedError` path for `rl-capa`

Document the new CLI in `README.md` and demote older entrypoints to compatibility status.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_runner_cli -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runner.py README.md tests/test_runner_cli.py
git commit -m "feat(cli): add unified root runner for Chengdu algorithms"
```

### Task 6: Add explicit `rl-capa` placeholder behavior without fake implementation

**Files:**
- Create: `algorithms/rl_capa_runner.py`
- Modify: `algorithms/registry.py`
- Test: `tests/test_algorithm_registry.py`
- Modify: `docs/implementation_notes.md`

**Step 1: Write the failing test**

```python
def test_rl_capa_cli_fails_explicitly_without_fallback():
    completed = subprocess.run(
        ["python3", "runner.py", "--algorithm", "rl-capa", "--data-dir", "Data"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "not implemented" in completed.stderr.lower()
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_algorithm_registry tests.test_runner_cli -v`
Expected: FAIL because no explicit `rl-capa` strategy exists yet.

**Step 3: Write minimal implementation**

Add a registered strategy object that raises:

```python
raise NotImplementedError("rl-capa is not implemented yet; use capa or baselines for Chengdu experiments.")
```

Document this boundary in `docs/implementation_notes.md`. Do not add any fallback to `capa`.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_algorithm_registry tests.test_runner_cli -v`
Expected: PASS

**Step 5: Commit**

```bash
git add algorithms/rl_capa_runner.py algorithms/registry.py tests/test_algorithm_registry.py tests/test_runner_cli.py docs/implementation_notes.md
git commit -m "docs(runner): register rl-capa placeholder without fallback"
```

### Task 7: Remove obsolete entrypoint duplication and compatibility debt

**Files:**
- Modify: `capa/experiments.py`
- Modify: `capa/__init__.py`
- Modify: `README.md`
- Test: `tests/test_env_chengdu.py`
- Test: `tests/test_runner_cli.py`

**Step 1: Write the failing test**

```python
def test_root_runner_is_the_documented_primary_entrypoint():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "python3 runner.py --algorithm capa" in readme
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_runner_cli -v`
Expected: FAIL if README and compatibility wrappers still present the old module entrypoints as primary.

**Step 3: Write minimal implementation**

After the new runner is stable:

- keep `capa/experiments.py` only as a compatibility wrapper or helper library
- keep `capa/__init__.py` exports minimal
- ensure all documentation points to `runner.py` first
- remove any now-dead helper path that duplicates runner orchestration

Do not delete reusable CAPA or baseline logic. Only remove duplicate orchestration.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_runner_cli tests.test_env_chengdu -v`
Expected: PASS

**Step 5: Commit**

```bash
git add capa/experiments.py capa/__init__.py README.md tests/test_runner_cli.py tests/test_env_chengdu.py
git commit -m "refactor(entrypoints): make root runner the canonical experiment interface"
```

### Task 8: Full verification and integration commit

**Files:**
- Verify all files touched above
- Optionally update: `docs/code_audit_report.md`

**Step 1: Run full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 2: Run smoke commands**

Run:

```bash
python3 runner.py --algorithm capa --data-dir Data --num-parcels 5 --local-couriers 2 --platforms 1 --couriers-per-platform 1 --batch-size 300 --output-dir outputs/plots/smoke_capa
python3 runner.py --algorithm greedy --data-dir Data --num-parcels 5 --local-couriers 2 --platforms 1 --couriers-per-platform 1 --batch-size 300 --output-dir outputs/plots/smoke_greedy
python3 runner.py --algorithm basegta --data-dir Data --num-parcels 5 --local-couriers 2 --platforms 1 --couriers-per-platform 1 --batch-size 300 --output-dir outputs/plots/smoke_basegta
python3 runner.py --algorithm impgta --data-dir Data --num-parcels 5 --local-couriers 2 --platforms 1 --couriers-per-platform 1 --batch-size 300 --output-dir outputs/plots/smoke_impgta
```

Expected: all four complete and write `summary.json`; `rl-capa` exits with explicit not-implemented error.

**Step 3: Final commit**

```bash
git add -A
git commit -m "refactor(runner): unify Chengdu environment and algorithm entrypoints"
```

**Step 4: Tag milestone**

```bash
git tag -a v0.2.1-unified-runner -m "Unified Chengdu environment and root runner completed"
```

## Design Notes And Guardrails

- `env/chengdu.py` must not contain algorithm-specific branching such as `if algorithm == "capa"`.
- `runner.py` must not reimplement simulation movement, task batching, or courier seeding.
- `rl-capa` must be a clear, explicit non-implementation until real RL code exists.
- Baseline and CAPA runners should share the same environment lifecycle, not the same heuristic code.
- Every task above ends with a git commit; do not batch the whole refactor into one giant commit.
