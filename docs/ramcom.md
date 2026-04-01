# RamCOM Baseline Extraction

## Source paper
**Real-Time Cross Online Matching in Spatial Crowdsourcing**  
Yurong Cheng, Boyang Li, Xiangmin Zhou, Ye Yuan, Guoren Wang, Lei Chen  
ICDE 2020

---

## What this baseline actually is

RamCOM is the **randomized cooperative online matching** algorithm in the COM framework.

The paper studies a setting with:
- a **target platform**
- its own **inner crowd workers**
- other platforms' **outer crowd workers**
- sequentially arriving **requests**

The key difference from traditional online matching is that if the target platform cannot or should not use its own workers, it may **borrow workers from other platforms** and pay them an **outer payment**.

RamCOM is designed to outperform the deterministic baseline DemCOM by doing two things:

1. **Do not always greedily reserve inner workers only for current best immediate revenue.**  
   Instead, use a **random threshold on request value** to decide whether a request should preferentially use inner workers.

2. **Do not always use the minimum outer payment.**  
   Instead, choose an outer payment that maximizes the **expected cooperative revenue**, i.e. a trade-off between:
   - revenue kept by the target platform
   - probability that outer workers accept the cooperative request

---

# 1. Problem setting and formal objects

## 1.1 Request
A request is:

\[
r = \langle t, l_r, v_r \rangle
\]

where:
- \(t\): arrival time
- \(l_r\): request location
- \(v_r\): request value, i.e. the payment the requester can bring to the target platform if completed

## 1.2 Inner crowd worker
An inner worker belongs to the **target platform**:

\[
w^{in} = \langle t, l_{w^{in}}, rad_{w^{in}} \rangle
\]

where:
- \(t\): arrival time
- \(l_{w^{in}}\): current location
- \(rad_{w^{in}}\): service radius

## 1.3 Outer crowd worker
An outer worker belongs to a **cooperative platform**:

\[
w^{out} = \langle t, l_{w^{out}}, rad_{w^{out}} \rangle
\]

These workers may be borrowed by the target platform.

## 1.4 Constraints
The matching must satisfy:

1. **Time constraint**  
   A worker can only serve requests that arrive **after** the worker.

2. **1-by-1 constraint**  
   One worker serves at most one request at a time, and one request is served by at most one worker.

3. **Invariable constraint**  
   Once a worker is assigned to a request, that assignment cannot be changed until service completes.

4. **Range constraint**  
   A worker can only serve requests whose locations lie within the worker's service radius.

---

# 2. Revenue model

## 2.1 Revenue if served by an inner worker
If request \(r\) is served by an inner worker, the target platform receives:

\[
v_r
\]

## 2.2 Revenue if served by an outer worker
If request \(r\) is served by an outer worker and the target platform pays outer payment \(v'_r\), then the platform keeps:

\[
v_r - v'_r
\]

with \(0 < v'_r \le v_r\).

## 2.3 Total revenue
If:
- \(M^{in}\) is the set of requests served by inner workers
- \(M^{out}\) is the set of requests served by outer workers

then:

\[
Rev = \sum_{r_i \in M^{in}} v_{r_i} + \sum_{r_i \in M^{out}} (v_{r_i} - v'_{r_i})
\]

---

# 3. Acceptance probability model for outer workers

For cooperative matching, RamCOM needs a model for whether an outer worker will accept a request with offered payment.

For an outer worker \(w\), assume it has \(N\) historical completed requests.

Let:
- \(N(v \le v'_r)\): number of history requests whose value is not larger than the offered outer payment \(v'_r\)

Then the paper defines the worker's acceptance probability as:

\[
p_r(v'_r, w) = \frac{N(v \le v'_r)}{N}
\]

Interpretation:
- if the offered cooperative payment is high relative to the worker's historical completed requests, the worker is more likely to accept
- if the offered payment is low, the worker is less likely to accept

This is a **history-based empirical acceptance probability**.

---

# 4. Expected cooperative revenue used by RamCOM

A central idea in RamCOM is that the target platform should not simply minimize the outer payment.

Instead, given:
- a cooperative request \(r\)
- an offered outer payment \(v'_r\)
- a candidate outer worker set \(W\)

the paper defines the **expected revenue**:

\[
E(v'_r, W) = (v_r - v'_r)\cdot p_r(v'_r, W)
\]

where \(p_r(v'_r, W)\) is the probability that **some** worker in \(W\) will accept the request under payment \(v'_r\).

The platform seeks the **maximum expected revenue**:

\[
E(v_r, W)_{\max} = \max_{0 < v'_r \le v_r} E(v'_r, W)
\]

This is the core difference from DemCOM:
- DemCOM tries to estimate the **minimum feasible outer payment**
- RamCOM uses the **payment that maximizes expected cooperative revenue**

---

# 5. High-level intuition of RamCOM

RamCOM tries to reserve inner workers for relatively **high-value requests**.

The core logic is:

1. Draw a **random value threshold**
2. If a request value is **above the threshold**, try to assign it to an inner worker
3. Otherwise, treat it as a candidate **cooperative request**
4. For a cooperative request, compute the outer payment that maximizes expected revenue
5. Use that outer payment to test which outer workers would accept
6. If any accept, assign the request to one of them

This strategy is meant to avoid wasting scarce inner workers on low-value requests.

---

# 6. Exact algorithm flow from the paper

## 6.1 Initialization

The paper defines:

\[
\theta = \lceil \ln(\max(v_r) + 1) \rceil
\]

where \(\max(v_r)\) is the maximum request value among all requests.

Then sample an integer:

\[
k \in \{1,2,\dots,\theta\}
\]

uniformly, i.e. with probability \(1/\theta\).

This defines the randomized threshold:

\[
e^k
\]

The algorithm also initializes:
- \(M = \varnothing\): feasible matching result
- \(Rev = 0\): accumulated revenue

---

## 6.2 Online processing of each arriving request

For each newly arriving request \(r\):

### Step A. Compare request value against threshold
If:

\[
v_r > e^k
\]

then RamCOM **tries inner workers first**.

### Step B. Inner-worker assignment branch
Find all inner workers that can serve the request while satisfying:
- time constraint
- range constraint
- 1-by-1 availability

If one or more valid inner workers exist:
- **randomly choose one valid inner worker**
- assign the request to that inner worker
- update revenue:

\[
Rev \leftarrow Rev + v_r
\]

If no valid inner worker exists, the request will not be completed in this branch; the paper's pseudocode then falls through to the cooperative branch only in the `else` block associated with `v_r \le e^k`.  
This is a point that must be handled carefully in implementation, because the paper's pseudocode is concise and does **not explicitly restate** the fallback behavior for the case \(v_r > e^k\) but no inner worker exists.

**Important implementation note:**  
The paper's worked example says that if a high-value request arrives and no unoccupied inner worker can serve it, then RamCOM asks outer workers to serve it. Therefore, a faithful implementation should treat this as:
- try inner worker first when \(v_r > e^k\)
- if none exists, continue to cooperative handling

This example-level behavior is more precise than the brief pseudocode.

---

## 6.3 Cooperative branch

If the request is treated as a cooperative candidate, RamCOM does:

### Step C. Compute maximum expected outer payment
Use the algorithm of Tong et al. (SIGMOD 2018 dynamic pricing paper cited as [14] in COM) to compute:
- the **maximum expected revenue**
- the corresponding **outer payment** \(v'_r\)

This is **not derived inside the RamCOM paper itself**.  
The COM paper directly uses that external pricing algorithm as a subroutine.

### Step D. Determine candidate outer workers
Find all outer workers that satisfy:
- time constraint
- range constraint
- 1-by-1 availability

Let this set be \(W_r^{out}\).

### Step E. Acceptance sampling for each outer worker
For each worker \(w \in W_r^{out}\):
1. calculate acceptance probability \(p_r(v'_r, w)\)
2. sample a random number \(x \in [0,1]\)
3. if \(x > p_r(v'_r, w)\), remove \(w\) from candidate set
4. else keep \(w\) as an accepting worker

After checking all outer workers:
- if the filtered candidate set is empty, reject request
- otherwise assign the request to one accepted outer worker

### Step F. Revenue update
If outer worker accepts and is assigned:

\[
Rev \leftarrow Rev + (v_r - v'_r)
\]

---

# 7. More explicit pseudocode for implementation

Below is a reconstruction that is closer to executable logic than the concise paper pseudocode.

```python
initialize M = empty
initialize Rev = 0

theta = ceil(log(max_request_value + 1))
k = uniform_random_integer(1, theta)
threshold = exp(k)

for each arriving request r in time order:
    assigned = False

    # Phase 1: prefer inner worker for high-value request
    if r.value > threshold:
        inner_candidates = all available inner workers satisfying:
            - worker.arrival_time <= r.arrival_time
            - distance(worker.location, r.location) <= worker.radius
            - worker currently unoccupied

        if inner_candidates is not empty:
            choose one candidate uniformly at random
            assign request to this inner worker
            remove worker from waiting/available list
            M.add((r, selected_inner_worker, "inner"))
            Rev += r.value
            assigned = True

    # Phase 2: cooperative processing if still unassigned
    if not assigned:
        outer_candidates = all available outer workers satisfying:
            - worker.arrival_time <= r.arrival_time
            - distance(worker.location, r.location) <= worker.radius
            - worker currently unoccupied

        if outer_candidates is empty:
            reject r
            continue

        # external pricing subroutine from cited dynamic pricing work
        outer_payment = argmax_expected_revenue(r, outer_candidates)

        accepted_outer_workers = []
        for w in outer_candidates:
            p = acceptance_probability(outer_payment, w.history)
            x = random_uniform_0_1()
            if x <= p:
                accepted_outer_workers.append(w)

        if accepted_outer_workers is empty:
            reject r
            continue

        # the COM paper says "assign outer crowd workers to serve r"
        # and elsewhere follows nearest-worker style in DemCOM
        # so a practical faithful choice is nearest accepted worker
        selected_outer = choose_nearest(r, accepted_outer_workers)

        assign request to selected_outer
        remove selected_outer from all platforms' waiting lists
        M.add((r, selected_outer, "outer", outer_payment))
        Rev += (r.value - outer_payment)
```

---

# 8. Data structures Codex should build

To implement RamCOM clearly, the following data structures are useful.

## 8.1 Request object
Fields:
- `id`
- `arrival_time`
- `location`
- `value`

## 8.2 Worker object
Fields:
- `id`
- `platform_id`
- `is_inner` or boolean indicating whether worker belongs to target platform
- `arrival_time`
- `location`
- `service_radius`
- `is_available`
- `history_completed_values` (needed for acceptance probability)

## 8.3 Platform state
Fields:
- `inner_waiting_workers`
- `outer_waiting_workers`
- `matched_pairs`
- `revenue`

## 8.4 Matching record
Fields:
- `request_id`
- `worker_id`
- `worker_type` (`inner` / `outer`)
- `outer_payment` (for outer only)
- `obtained_revenue`

---

# 9. Implementation-critical subtleties

## 9.1 RamCOM depends on an external pricing subroutine
This is the single most important limitation when implementing RamCOM from the paper.

The COM paper **does not derive** the procedure for computing the cooperative outer payment in RamCOM.  
Instead, it says:

- call the algorithm in reference [14]
- obtain the maximized expected revenue and corresponding outer payment

Therefore, a fully faithful RamCOM implementation requires either:

1. implementing the dynamic pricing algorithm from the cited SIGMOD 2018 paper, or
2. explicitly declaring an external oracle / module that provides `argmax_expected_revenue`

Without this, one can still implement the **RamCOM control flow**, but cannot claim the exact pricing subroutine is faithful to the source paper.

## 9.2 The paper's pseudocode is slightly compressed
The pseudocode in the paper is short and can hide one ambiguity:
- when \(v_r > e^k\) but no inner worker can serve, should the algorithm reject immediately, or continue to cooperative assignment?

The paper's own example makes clear that such requests should go to the outer-worker branch.  
So the implementation should preserve this behavior.

## 9.3 Randomization enters in two places
RamCOM is randomized in at least two ways:
1. random threshold parameter \(k\)
2. acceptance sampling of each outer worker with probability \(p_r(v'_r, w)\)

If you want reproducible experiments, you must:
- set and log random seeds
- separate training/evaluation seeds if RamCOM is used as a baseline in stochastic experiments

## 9.4 Outer worker deletion rule
The paper states that when an outer worker is assigned, that worker should be deleted from **all waiting lists over all platforms**.  
This matters in a multi-platform simulation.

## 9.5 Nearest-worker choice
The paper explicitly says:
- for inner workers in DemCOM, choose nearest worker
- for outer-worker assignment in DemCOM, greedy nearest accepted outer worker is used
- RamCOM's Algorithm 3 says it calls the relevant lines of Algorithm 1 to assign outer workers

Therefore the simplest faithful interpretation is:
- after filtering accepting outer workers, choose the **nearest accepted outer worker**

---

# 10. What to implement as the baseline if exact external pricing is unavailable

If Codex is implementing a baseline for experimental comparison and the external pricing paper [14] is not being fully reproduced, the code must make the following explicit:

1. **RamCOM control logic is reproduced**
   - random threshold
   - preference for inner workers on high-value requests
   - cooperative fallback
   - worker acceptance sampling
   - revenue accounting

2. **Outer payment computation is only partially faithful unless [14] is also implemented**
   - do not silently replace it and still claim full fidelity
   - isolate it behind a function like:

```python
def estimate_outer_payment_max_expected_revenue(
    request: Request,
    outer_candidates: list[Worker],
    pricing_model: PricingModel,
) -> float:
    ...
```

3. If an approximation is used, mark it clearly in comments/docs as:
   - `RamCOM-style baseline with approximate pricing`
   - not full paper-faithful RamCOM pricing

This is important for experimental honesty.

---

# 11. Minimal faithful checklist for a Codex implementation

A good RamCOM baseline implementation should satisfy all of the following:

- [ ] sequentially process requests online
- [ ] maintain inner and outer worker waiting sets
- [ ] enforce time, range, 1-by-1, and invariable constraints
- [ ] sample \(k\) uniformly from \(\{1,\dots,\theta\}\)
- [ ] compute threshold \(e^k\)
- [ ] high-value requests preferentially try inner workers
- [ ] if not assigned, enter cooperative branch
- [ ] compute outer payment by max-expected-revenue logic
- [ ] compute worker-level acceptance probabilities from history
- [ ] sample acceptance for each candidate outer worker
- [ ] assign to an accepted outer worker if any
- [ ] update revenue with correct inner / outer formulas
- [ ] remove assigned outer worker from all platform waiting lists
- [ ] expose random seed control for reproducibility

---

# 12. Short baseline summary for Codex

If you need a compact implementation summary:

> RamCOM is an online multi-platform request matching baseline.  
> For each arriving request, it samples a global randomized threshold \(e^k\) from request values.  
> Requests whose values exceed the threshold preferentially try to use inner workers.  
> Unassigned or low-value requests are pushed to cooperative matching, where the platform computes an outer payment maximizing expected revenue and samples whether each candidate outer worker accepts the request based on their historical acceptance probability.  
> If at least one outer worker accepts, the request is assigned to an accepted outer worker and the platform gains \(v_r - v'_r\); otherwise the request is rejected.

---

# 13. Suggested filename note

Although the paper writes the algorithm as **RamCom**, you can keep the baseline implementation file or notes as:
- `ramcom.py`
- `ramcom.md`

for naming consistency with your current project.
