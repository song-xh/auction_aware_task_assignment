# CAPA μ Sensitivity — Design Spec

Date: 2026-05-29

## Goal

Make CAPA cross-platform revenue genuinely sensitive to the local→cooperating
total sharing rate μ, so a μ sensitivity study has an interior optimum:

- μ too high → cooperating side keeps more, local keeps `(1-μ)·p_τ` too little → TR drops.
- μ too low → cooperating platform refuses (bid invalid) → parcels unassigned → TR drops.

TR = `compute_total_revenue` = `sum(local_platform_revenue)` (local platform revenue).

## Definitions

- `p_τ` = parcel fare.
- μ = total sharing rate local gives the cooperating side.
- ratio `r` splits μ: **μ1 = r·μ** (courier, first layer), **μ2 = (1-r)·μ** (platform, second layer).
- λ_c = courier expected income ratio (fixed constant, intrinsic to courier).
- λ_p = platform expected income/profit ratio (fixed constant, intrinsic to platform).

Sweep: μ ∈ {0.5,0.6,0.7,0.8,0.9}; r ∈ {0.2,0.3,0.4,0.5,0.6,0.7,0.8}.
Defaults (μ-experiment only): μ=0.7, r=0.5.

## Model change (`capa/dapa.py`)

λ-mode is active iff both λ_c and λ_p are set on `CAPAConfig` (else legacy behavior,
existing experiments untouched).

1. `compute_fpsa_bid`: replace `p_τ' = μ1·fare` with `λ_c·fare`. Courier bid magnitude
   becomes intrinsic (independent of μ1):
   `bid = base + (α·detour + β·service)·γ·λ_c·fare`.
2. FPSA per-courier validity (new): drop any courier bid with `bid > μ1·fare` before
   selecting the platform's max bidder. Models local's first-layer willingness.
3. Second layer: replace `μ2·fare` markup with `λ_p·fare`:
   `platform_bid = courier_bid + quality·λ_p·fare` (and the single-winner / fallback paths).
4. Platform validity (kept): `platform_bid ≤ (μ1+μ2)·fare = μ·fare` (existing `payment_limit`).
   This is the cooperating platform's self-selection: when μ small, fixed λ_p markup
   pushes the bid past μ·fare → invalid → unassigned.
5. **Remove** `validate_platform_base_price_constraint` call + import from `run_dapa`
   (function stays in `capa/config.py`). λ_c now governs bid scale, the old
   `p_min ≤ (1-γ)·μ1·fare` check is obsolete and would crash at low μ1.

Revenue split, TR metric, second-price logic: unchanged.

## Config / plumbing

- `capa/models.py` `CAPAConfig`: add `courier_expected_income_ratio_lambda_c: float|None=None`,
  `platform_expected_income_ratio_lambda_p: float|None=None`.
- `capa/config.py`: `DEFAULT_COURIER_EXPECTED_INCOME_LAMBDA_C`,
  `DEFAULT_PLATFORM_EXPECTED_INCOME_LAMBDA_P` (None until tuned, then filled).
- `algorithms/capa_runner.py`: thread λ through runner __init__, `build_capa_runner`,
  `CAPAConfig(...)`, and summary `config` block.
- `experiments/paper_chengdu.py`:
  - argparse: `--courier-lambda-c`, `--platform-lambda-p`, `--total-sharing-rate-mu`, `--sharing-ratio-r`.
  - `build_capa_runner_overrides_from_args`: when μ & r given, derive μ1=r·μ, μ2=(1-r)·μ and
    set `local_sharing_rate_mu1`/`cross_platform_sharing_rate_mu2`; pass λ_c, λ_p.
  - `_build_capa_override_cli_args`: add λ flags (μ1/μ2 already mapped) for formal split subprocesses.

## λ tuning (`scripts/tune_capa_lambda.py`)

Small env: 300 parcels, 20 local couriers, 4 platforms, 5 couriers/platform, fixed seed,
base_price = default 1.0. Reuse `run_chengdu_exp1_num_parcels` point mode.
Cross-sweep λ_c ∈ {0.2,0.3,0.4,0.5,0.6} × λ_p ∈ {0.2,0.3,0.4,0.5}, each evaluated over
μ ∈ {0.5..0.9} at r=0.5. Multi-agent parallel execution.
Selection: (λ_c, λ_p) whose TR(μ) peaks at μ=0.7 and falls at μ=0.5 and μ=0.9.
Write winner into config defaults.

## μ/r sensitivity suite (`scripts/run_capa_mu_sensitivity_suite.py`)

Mirrors `scripts/run_capa_exp1_sensitivity_suite.py`. Shared canonical seeds per preset.
Light cross design:
- μ-sweep at r=0.5: μ ∈ {0.5..0.9}.
- r-sweep at μ=0.7: r ∈ {0.2..0.8}.
Presets: ny @ 5000 parcels (parallel points), formal @ 50000 parcels (serial, memory cap).

## Orchestration

TaskCreate phases. Long runs in background; Monitor watches stdout/summary files,
emits progress + failure signatures, advances phase on completion, reports + aggregates
each stage. Aggregate TR(μ) and TR(r) curves per preset into a final report.

## Verification

- Legacy path: λ unset → one exp1 capa point TR identical to pre-change.
- λ-mode dapa unit tests: validity drop at high bid, λ_p markup applied.
- Full test suite green (after replacing the removed base-price-constraint auction test).
