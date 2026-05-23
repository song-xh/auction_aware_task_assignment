$# Task: Add service-aware slack feature to RL-CAPA Stage-2 state

## Background

The current implementation of RL-CAPA Stage 2 uses the following action semantics:

- `a = 0`: try local assignment first; if local assignment fails and the parcel is not expired, defer it to the next batch.
- `a = 1`: try cross-platform auction first; if cross assignment fails and the parcel is not expired, defer it to the next batch.

Do not change this action semantics.

The current Stage-2 state already includes parcel deadline, current time, estimated local net revenue, batch-level parcel/courier statistics, cross-platform courier statistics, recent cross winning bid, and selected batch size.

We now need to add one compact delay-aware feature to the Stage-2 per-parcel state:

```python
service_slack_i = deadline_i - current_time - min_local_service_time_i
```

This feature should estimate whether parcel `i` can still be served by local couriers before its deadline. It is only a state feature, not a hard rule and not an executed local matching step.

## Goal

Implement an optional Stage-2 state feature named:

```python
service_slack
```

or:

```python
s_svc
```

The goal is to improve RL-CAPA robustness under information delay or noisy observations by allowing the second-stage policy to observe local time feasibility.

Under delay, a parcel may be received later while its deadline remains unchanged. This reduces the remaining service margin. The new feature should expose this effect to the policy.

## Required behavior

### 1. Keep action semantics unchanged

Do not change the existing Stage-2 execution logic:

```python
if action == 0:
    # try local assignment first
    # if local assignment fails and parcel is still valid, defer to next batch

if action == 1:
    # try cross-platform assignment first
    # if cross assignment fails and parcel is still valid, defer to next batch
```

The new feature must only affect the RL policy input, not the deterministic post-action matching logic.

### 2. Add a config flag

Add a config flag:

```bash
--use_service_slack true
```

or:

```bash
--rl_service_slack true
```

Default value must be `false`.

When the flag is false:

- the original RL-CAPA state dimension must remain unchanged;
- old checkpoints and experiments should still run;
- results under old settings should remain identical or nearly identical, except for randomness.

When the flag is true:

- append normalized `service_slack_i` to the Stage-2 per-parcel state;
- update actor/critic input dimensions accordingly;
- save this model as a separate variant, e.g. `RL-CAPA-SVC` or `RL-CAPA-D`.

### 3. Define service_slack

For each parcel `tau_i` in the current Stage-2 decision batch:

```python
service_slack_i = deadline_i - current_time - min_local_service_time_i
```

where:

```python
min_local_service_time_i = min_c T(c, tau_i)
```

`T(c, tau_i)` is the estimated time cost for local courier `c` to serve parcel `tau_i`.

Important:

- Reuse the existing local matching / feasibility / travel-time calculation function if available.
- Do not create an inconsistent duplicate distance or ETA calculation.
- If the code currently computes shortest-path distance and converts it to travel time, use the same logic.
- If the code currently inserts the parcel into the courier route and checks deadline feasibility, use the same estimated additional time or arrival time logic.
- The feature should be computed before action selection, but it must not assign the parcel.

### 4. Candidate local couriers

Compute `min_local_service_time_i` over currently available local couriers.

Preferred rule:

```python
candidate_local_couriers = available local couriers satisfying basic capacity constraints
```

Then:

```python
min_local_service_time_i = min(T(c, tau_i) for c in candidate_local_couriers)
```

If no local courier is available or no local courier satisfies basic capacity constraints:

```python
service_slack_i = -max_deadline_horizon
```

or after normalization:

```python
normalized_service_slack_i = -1.0
```

Do not crash when the candidate set is empty.

### 5. Normalization

Normalize the feature before feeding it into the neural network.

Recommended:

```python
normalized_service_slack_i = clip(
    service_slack_i / max_deadline_horizon,
    -1.0,
    1.0
)
```

where `max_deadline_horizon` should reuse an existing time-normalization constant if available.

If no such constant exists, define one from the experiment setting, e.g.:

```python
max_deadline_horizon = max_deadline - min_current_time
```

or use the maximum parcel deadline horizon used in the dataset configuration.

The feature must allow negative values. Negative service slack is meaningful because it indicates that local service is already risky or infeasible.

### 6. Do not add other features in this task

Do not add:

- raw delay seconds;
- missed window count;
- local feasible courier count;
- cross feasible courier count;
- mean slack;
- recent timeout ratio;
- recent unresolved ratio;
- risk ratio.

This task only adds:

```python
service_slack_i
```

to Stage-2 state.

## Implementation details

### A. Locate Stage-2 state construction

Find the function that builds the Stage-2 per-parcel state. It may contain something equivalent to:

```python
state_i = [
    deadline_i,
    current_time,
    local_net_revenue_i,
    num_unassigned_parcels,
    num_local_couriers,
    avg_local_remaining_capacity,
    num_cross_couriers,
    recent_avg_cross_winning_bid,
    selected_batch_size,
]
```

When `use_service_slack == true`, append:

```python
normalized_service_slack_i
```

The resulting state should be:

```python
state_i = [
    deadline_i,
    current_time,
    local_net_revenue_i,
    num_unassigned_parcels,
    num_local_couriers,
    avg_local_remaining_capacity,
    num_cross_couriers,
    recent_avg_cross_winning_bid,
    selected_batch_size,
    normalized_service_slack_i,
]
```

### B. Update network input dimensions

Find where the Stage-2 actor/critic input dimension is defined.

If `use_service_slack == false`:

```python
stage2_state_dim = original_stage2_state_dim
```

If `use_service_slack == true`:

```python
stage2_state_dim = original_stage2_state_dim + 1
```

Ensure both actor and critic receive the correct dimension.

### C. Check checkpoint compatibility

If old checkpoints are loaded with `use_service_slack == false`, they should load normally.

If `use_service_slack == true`, require a separately trained checkpoint. Do not silently load old incompatible checkpoints unless the code already supports partial loading safely.

Add a clear error message if checkpoint dimensions mismatch:

```text
Checkpoint state dimension does not match current Stage-2 state dimension.
Please retrain or disable --use_service_slack.
```

### D. Logging

When `use_service_slack == true`, log summary statistics per episode or per evaluation run:

```python
mean_service_slack
p10_service_slack
min_service_slack
ratio_negative_service_slack
```

These logs are for debugging and analysis only.

## Delay robustness compatibility

This feature should work with the existing delay experiment if implemented.

Under information delay:

- `recv_time = true_arrival_time + delay`
- `deadline` remains unchanged
- `current_time` at reception is larger
- therefore `service_slack_i` should decrease naturally

Do not shift deadlines when delay is injected.

## Self-check requirements

After implementation, run the following checks.

### Check 1: Feature formula

Create or run a small controlled test:

Given:

```python
deadline = 100
current_time = 70
min_local_service_time = 20
```

Expected:

```python
service_slack = 100 - 70 - 20 = 10
```

Given:

```python
deadline = 100
current_time = 90
min_local_service_time = 20
```

Expected:

```python
service_slack = -10
```

### Check 2: Delay reduces service_slack

For the same parcel and same courier:

No delay:

```python
current_time = 60
deadline = 100
min_local_service_time = 20
service_slack = 20
```

With 20s delay:

```python
current_time = 80
deadline = 100
min_local_service_time = 20
service_slack = 0
```

Expected:

`service_slack` must decrease when the parcel is received later.

### Check 3: Empty local courier set

If there are no available local couriers:

Expected:

- no crash;
- normalized service slack is set to `-1.0` or a documented negative fallback;
- Stage-2 state dimension is still correct.

### Check 4: Flag-off behavior

Run the original RL-CAPA with:

```bash
--use_service_slack false
```

Expected:

- Stage-2 state dimension equals original dimension;
- old checkpoint can load;
- action execution logic unchanged;
- no new feature appears in the state vector.

### Check 5: Flag-on behavior

Run RL-CAPA with:

```bash
--use_service_slack true
```

Expected:

- Stage-2 state dimension increases by exactly 1;
- actor and critic input dimensions are updated;
- training starts without shape mismatch;
- evaluation starts without shape mismatch;
- feature statistics are logged.

### Check 6: Action semantics unchanged

Add debug counters or assertions to confirm:

For `action == 0`:

- local assignment is attempted first;
- failed local assignments are deferred to the next batch if the parcel is not expired.

For `action == 1`:

- cross-platform assignment is attempted first;
- failed cross assignments are deferred to the next batch if the parcel is not expired.

The new `service_slack` feature must not directly force local or cross decisions.

### Check 7: Revenue logic unchanged

Confirm that adding `service_slack` does not change:

- local revenue calculation;
- cross-platform payment calculation;
- auction logic;
- capacity constraints;
- deadline feasibility checks;
- batch transition logic.

Only the RL state input should change.

### Check 8: Normalization range

During training/evaluation, assert or log:

```python
-1.0 <= normalized_service_slack_i <= 1.0
```

for every Stage-2 parcel state.

### Check 9: Delay experiment sanity

If the delay experiment exists, run a small delay sweep:

```python
delay_max = [0, 30]
```

Expected:

- average service slack under `delay_max=30` should be lower than under `delay_max=0`;
- ratio of negative service slack should be higher or equal under `delay_max=30`.

## Expected output from Codex

After implementation, report:

1. Modified files.
2. The exact function where Stage-2 state is built.
3. The exact function used to compute `min_local_service_time_i`.
4. Whether the feature uses shortest-path ETA, route-insertion ETA, or another existing local travel-time estimate.
5. The new config flag name and default value.
6. The old and new Stage-2 state dimensions.
7. The commands used for a minimal training/evaluation smoke test.
8. The result of all self-checks above.

## Important design note

`service_slack_i` is not a hard-coded heuristic decision rule. It is a state feature. The policy should still learn whether to choose local-first or cross-first based on the full state and reward.

Do not implement logic such as:

```python
if service_slack_i < 0:
    action = 1
```

This is forbidden.

The feature should only help the policy learn that, under delay, local-first may become risky when the local service margin is small or negative.

## Additional instruction

Current code semantics take priority over older manuscript wording:

- `a = 0` means local-first;
- `a = 1` means cross-first;
- both failed local-first and failed cross-first parcels enter the next batch if they are still valid.

Do not modify the action definition to `defer-vs-auction`. This task only adds the `service_slack` state feature.
