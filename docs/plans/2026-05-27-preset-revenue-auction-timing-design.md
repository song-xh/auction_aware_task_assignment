# Preset Revenue And Auction Timing Design

## Goal

Extend paper-style experiment configuration and metric reporting so that:

- `formal` and `ny` have explicit preset-specific fixed background settings for
  Exp-1 runs.
- Both presets use a default observed deadline duration of `720` seconds.
- Experiment summaries report local-platform revenue split into local and
  cross-platform contributions.
- CAPA reports the elapsed time spent in its DAPA dual-layer auction with both
  full and decision-only timing views.

## Preset Defaults

The preset continues to determine the sweep values. In particular, Exp-1
continues to sweep `num_parcels`; no fixed `num_parcels` value replaces the
`ny` parcel-count axis.

The fixed background settings for Exp-1 are:

| Preset | `local_couriers` | `couriers_per_platform` | `deadline_seconds` |
| --- | ---: | ---: | ---: |
| `formal` | current formal default (`3000`) | current formal default (`500`) | `720` |
| `ny` | `300` | `50` | `720` |

All other fixed settings remain identical to the existing formal defaults
unless explicitly overridden on the command line. A caller-provided flag wins
over the preset default.

Implementation should keep preset-specific fixed overrides centralized rather
than introducing conditionals in each experiment script.

## Revenue Metrics

Every normalized experiment `metrics` payload that currently exposes `TR`
will also expose:

- `local_TR`: local-platform revenue realized by on-time local assignments.
- `cross_TR`: local-platform revenue realized by on-time cross-platform
  assignments.

The invariant is:

```text
TR = local_TR + cross_TR
```

For local-only algorithms, `cross_TR` is `0.0`. For algorithms that may send
parcels to partner couriers, the split is computed from delivered outcomes,
not merely accepted assignments, matching the current delivered-revenue
definition of `TR`.

## CAPA Auction Timing

CAPA uses CAMA for local utility-threshold assignment and DAPA for
cross-platform dual-layer auctioning. CAMA is not an auction, so this feature
does not add a local auction timing metric.

CAPA reports:

- `AT_full`: mean wall-clock DAPA time per recorded matching batch. This
  includes DAPA feasibility evaluation, routing queries, insertion searches,
  FPSA bidding, RVA bidding/payment, and assignment commit work executed
  inside DAPA.
- `AT_single`: mean DAPA decision-processing time per recorded matching batch,
  calculated with the same exclusions currently used by BPT: routing,
  insertion, and movement timing accrued during DAPA are subtracted.

Both measures use the same denominator shape as current CAPA BPT:
`len(batch_reports)`. A batch with no DAPA work contributes zero, reflecting
that no cross-platform auction ran in that matching round.

The timing fields are CAPA-specific experiment output. RL-CAPA and baseline
summaries do not label their cross-handling paths as CAPA auction timing.

## Data Flow

1. Preset resolution builds a fixed configuration before experiment point
   generation, applying `formal` or `ny` background settings and allowing
   explicit CLI values to override them.
2. DAPA records both complete elapsed time and its decision-only elapsed time
   into the batch timing accumulator.
3. CAPA aggregates batch DAPA counters into `AT_full` and `AT_single`.
4. CAPA builds `local_TR` and `cross_TR` from delivered assignments.
5. Baseline algorithms compute the same TR split at the location where
   delivered task identifiers and assignment mode/revenue records are already
   available.
6. Normalized summary and persisted JSON payloads expose the enriched metric
   dictionaries without altering existing `TR`, `CR`, or `BPT` fields.

## Testing

Tests will establish:

- `formal` Exp-1 keeps the current fixed courier scale and resolves a
  `720`-second default deadline.
- `ny` Exp-1 keeps its parcel sweep values while resolving fixed
  `local_couriers=300`, `couriers_per_platform=50`, and
  `deadline_seconds=720`.
- Explicit CLI overrides replace preset defaults.
- CAPA emits `TR`, `local_TR`, `cross_TR`, `AT_full`, and `AT_single`.
- CAPA revenue split uses delivered assignments and sums exactly to `TR`.
- CAPA auction timing is sourced from DAPA only, with
  `AT_full >= AT_single`.
- Local-only baselines emit `cross_TR=0.0`.
- Cross-capable baselines expose delivered local/cross revenue splits.
- Non-CAPA summaries do not expose CAPA `AT_full` or `AT_single`.

