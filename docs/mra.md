# MRA Baseline Extraction

## Source paper
**Auction-Based Crowdsourced First and Last Mile Logistics**  
Yafei Li, Yifei Li, Yun Peng, Xiaoyi Fu, Jianliang Xu, Mingliang Xu  
IEEE Transactions on Mobile Computing, 2024

---

## Important naming note

The source paper names the algorithm **MRA** = **Multi-round Assignment**.  
However, in your current manuscript and baseline list, this algorithm is referred to as **RMA**.  
For implementation purposes:

- **RMA in your project should be treated as the MRA algorithm from the ACF paper**
- this file is named `rma.md` only to match your current project naming

So below, whenever the source paper says **MRA**, you can read it as the intended **RMA baseline**.

---

# 1. What this baseline actually is

MRA is the main **auction-based multi-round parcel assignment algorithm** in the ACF paper.

It solves a single-platform auction-based crowdsourced FLML problem:
- couriers are already delivering drop-off parcels
- pick-up parcels arrive dynamically
- each courier has preferences over pick-up parcels
- the platform computes bids according to a **multi-attribute reverse Vickrey (MRV)** auction
- couriers with lower bids are better for a parcel
- the platform seeks to maximize **social welfare**

MRA is stronger than the greedy baseline because it:
- constructs a **global bipartite graph** between couriers and pick-up parcels
- processes parcel assignment in **multiple rounds**
- after each round, **recomputes** graph entries affected by newly assigned parcels

So unlike a one-pass greedy allocation, MRA repeatedly updates feasibility and bids after assignments change courier states.

---

# 2. Problem setting and core objects

## 2.1 Pick-up parcel
A pick-up parcel is:

\[
\tau = \langle l_\tau, t_\tau, w_\tau, f_\tau \rangle
\]

where:
- \(l_\tau\): pick-up location
- \(t_\tau\): deadline
- \(w_\tau\): parcel weight
- \(f_\tau\): parcel fare

## 2.2 Drop-off parcel
A drop-off parcel is:

\[
\psi = \langle l_\psi, t_\psi, w_\psi \rangle
\]

where:
- \(l_\psi\): drop-off location
- \(t_\psi\): deadline
- \(w_\psi\): weight

## 2.3 Courier
A courier is:

\[
c = \langle l_c, w_c, t_c, \alpha_c, \beta_c, \Psi_c, \Gamma_c \rangle
\]

where:
- \(l_c\): current location
- \(w_c\): maximum capacity
- \(t_c\): deadline to return to station
- \(\alpha_c, \beta_c\): preference coefficients on parcel attributes, with \(\alpha_c + \beta_c = 1\)
- \(\Psi_c\): assigned drop-off parcels
- \(\Gamma_c\): assigned pick-up parcels

The paper also uses the current **unoccupied capacity**:

\[
\bar{w}_c = w_c - \sum_{\psi \in \Psi_c} w_\psi - \sum_{\tau \in \Gamma_c} w_\tau
\]

For implementation clarity, it is often better to store:
- `max_capacity`
- `occupied_weight`
- `remaining_capacity`

rather than overwriting one symbol for multiple meanings.

## 2.4 Schedule
Each courier has a schedule:

\[
S_c = \langle l_1, l_2, \dots, l_m \rangle
\]

where each point is either a pick-up point or drop-off point.

A valid schedule must satisfy:
1. capacity constraints at all times
2. all parcel deadlines
3. courier return deadline

The paper assumes:
- shortest path travel between two points
- when inserting a new pick-up parcel, **do not reorder existing scheduled points**
- instead, find the **best insertion position** that minimizes extra detour

That assumption matters a lot: MRA does **not** solve a full route re-optimization each time.

---

# 3. Auction model MRA relies on

MRA is built on the paper's **MRV auction model**:
- couriers bid on parcels
- the lower the bid, the better
- the winning courier is paid the **second lowest bid**

The actual social welfare objective depends on the **winner's bid**, not directly on the second-price payment.

---

# 4. Bid computation used by MRA

This is the most important building block.

For a courier \(c\) and parcel \(\tau\), the bid is:

\[
bid(c, \tau)=
\begin{cases}
r_0 + m f_\tau, & \text{if } sum(\tau)=1 \\
r_0 + (\alpha_c \Delta w_\tau + \beta_c \Delta d_\tau) m f_\tau, & \text{if } sum(\tau)\ge 2
\end{cases}
\]

where:
- \(r_0\): base revenue / base price
- \(m\): sharing rate
- \(sum(\tau)\): number of couriers bidding for parcel \(\tau\)

Interpretation:
- if only one courier can bid, payment is basic
- if multiple couriers can bid, the bid depends on:
  - capacity suitability
  - detour suitability

## 4.1 Capacity preference term
The paper defines:

\[
\Delta w_\tau = 1 - \frac{w_\tau}{\bar{w}_c}
\]

Interpretation:
- if parcel weight is close to remaining capacity, this term is small / favorable in their bid formulation
- the platform prefers assignments where parcel weight matches courier free capacity well

## 4.2 Detour preference term
The detour ratio is:

\[
\Delta d_\tau =
\min_{1 \le i \le |S_c|-1}
\left(
1 - \frac{p(l_i, l_{i+1})}{p(l_i, l_\tau)+p(l_\tau,l_{i+1})}
\right)
\]

where \(p(\cdot,\cdot)\) is shortest-path distance.

Interpretation:
- try every insertion position between consecutive schedule points
- compute how much detour is induced by inserting parcel \(\tau\)
- choose the insertion with minimum extra detour ratio

## 4.3 Validity before bidding
A courier can bid for a parcel only if:
- the courier can reach parcel location before deadline
- the courier has enough remaining capacity
- a valid schedule still exists after insertion

The paper's Algorithm 1 returns infinity / invalid if not feasible.

---

# 5. The two index/data-structure optimizations used by MRA

A faithful MRA implementation is not just "sort all bids and assign".

The source paper relies on **two indexing/data-structure ideas**:

1. **TS-Tree** for efficient bid computation  
2. **TIL (Time-bounded Inverted List)** for pruning invalid courier-parcel pairs before graph construction

These are not optional in the source design, although a smaller experimental reproduction may first implement a simpler exact version and later optimize.

---

## 5.1 TS-Tree for bid computation

The bid computation algorithm uses a **TS-Tree** to quickly find the small subset of schedule points affected by inserting a new parcel.

### Purpose
Instead of trying insertion against the entire schedule every time, TS-Tree narrows the candidate sub-schedule.

### Internal-node meaning
Each internal node stores a time interval:

\[
[\underline{t}_e, \overline{t}_e]
\]

representing the earliest and latest times relevant to all child nodes.

### What TS-Tree is used for
Given a parcel \(\tau\):
1. compute the time interval when courier \(c\) could arrive at \(l_\tau\)
2. retrieve overlapping schedule portions using TS-Tree
3. only evaluate insertion positions inside that affected sub-schedule
4. choose the insertion position with minimum detour ratio
5. compute the final bid

### Paper Algorithm 1 summary
Input:
- parcel \(\tau\)
- courier \(c\)
- TS-Tree \(tr\)

Output:
- \(bid(c,\tau)\)

Pseudo-logic:
1. initialize bid to infinity
2. if courier can reach parcel before deadline and weight fits:
   - compute feasible arrival interval by dual search
   - query TS-Tree for affected sub-schedule \(S'_c\)
   - insert \(\tau\) into \(S'_c\) at minimum-detour position
   - compute bid with the formula above
3. return bid

### Complexity stated by paper
\[
O(\log |S_c| + |S'_c|)
\]

---

## 5.2 TIL index for pruning candidates before graph construction

MRA does not compare every courier with every parcel naively.

It uses a **Time-bounded Inverted List (TIL)**.

### Purpose
Quickly find candidate courier-parcel pairs that are **likely feasible**.

### Basic idea
1. Partition the road network into grid cells
2. For each grid cell, index the couriers that may pass through it
3. For each such courier, record the time interval during which the courier may pass that cell

### Reachable area of a courier
The paper defines a courier's reachable area as the set of grid cells the courier may pass through before deadline.

For each reachable grid cell \(g\), the platform stores the interval:

\[
[t_{c}^{g-}, t_{c}^{g+}]
\]

where:
- \(t_{c}^{g-}\): earliest arrival time at cell \(g\)
- \(t_{c}^{g+}\): latest departure time from cell \(g\)

They are computed as:

\[
t_{c}^{g-} = t_n + t_{min}(l_c, g)
\]

\[
t_{c}^{g+} = t_c - t_{min}(l_h, g)
\]

where:
- \(t_n\): current time
- \(l_c\): courier current location
- \(l_h\): station location
- \(t_{min}\): shortest travel time

### How TIL is used for a parcel
For parcel \(\tau\):
1. identify the grid cell containing \(l_\tau\)
2. retrieve couriers indexed in that cell
3. keep only couriers whose reachable interval overlaps the parcel's feasible pick-up interval
4. only for those candidate pairs, compute real bids

This avoids building all \( |C|\times|\Gamma| \) pairs.

---

# 6. MRA algorithm proper

Now the main algorithm.

---

## 6.1 High-level idea

Given:
- courier set \(C\)
- pick-up parcel set \(\Gamma\)

MRA does:

1. use TIL to find candidate courier-parcel pairs
2. compute valid bids for those pairs
3. build a weighted bipartite graph:
   - left side: couriers
   - right side: pick-up parcels
   - edge exists if courier can serve parcel
   - edge weight = courier bid for that parcel
4. repeatedly process the graph in **rounds**
5. in each round:
   - sort all current edges by increasing bid
   - assign parcel-courier pairs whose edge is the lowest bid for that parcel
   - remove conflicting parcel and courier edges in current round
6. after each round:
   - remove assigned parcels from graph
   - update bids of couriers that received new parcels
   - remove infeasible edges
7. stop when graph becomes empty

So MRA is:
- not Hungarian matching
- not simple greedy one pass
- not global exact matching
- but a repeated graph-based selection with state updates after each round

---

## 6.2 Bipartite graph definition

Construct graph \(G\) where each edge is:

\[
e = \langle c, \tau, bid(c,\tau)\rangle
\]

Edge exists only if:
- courier is feasible for parcel
- bid is finite

---

## 6.3 Paper pseudocode reconstruction

The source paper gives Algorithm 3:

Input:
- courier set \(C\)
- pick-up parcel set \(\Gamma\)

Output:
- parcel assignment \(M\)

### Stage 1. Graph construction
1. initialize \(M = \varnothing\), \(G = \varnothing\)
2. use TIL to find candidate assignments \(M'\)
3. for each \((c,\tau)\in M'\):
   - compute \(bid(c,\tau)\) with Algorithm 1
   - if bid is valid, add edge \(\langle c,\tau,bid(c,\tau)\rangle\) to \(G\)

### Stage 2. Multi-round assignment
While \(G\) is not empty:
1. create list \(L\) of all edges in \(G\), sorted by ascending bid
2. while \(L\) is not empty:
   - let \(e\) be first edge in \(L\)
   - if \(e.bid\) is the **lowest bid for parcel \(e.\tau\)** in the current graph \(G\):
     - assign parcel \(e.\tau\) to courier \(e.c\)
     - add \(e\) to matching \(M\)
     - remove from \(L\):
       - all entries involving parcel \(e.\tau\)
       - all entries involving courier \(e.c\)
3. after one round:
   - update graph \(G\) based on new assignments in \(M\)
   - remove edges for already assigned parcels
   - recompute bids for couriers whose states changed after receiving new parcels
   - remove couriers that have no remaining capacity or no valid bids

Return \(M\).

---

# 7. More implementation-oriented pseudocode

Below is a clearer executable reconstruction.

```python
def run_mra(couriers, parcels, til_index):
    matching = []
    graph_edges = []

    # Step 1: candidate generation using TIL
    candidate_pairs = find_candidate_pairs_via_til(couriers, parcels, til_index)

    # Step 2: graph construction
    for courier, parcel in candidate_pairs:
        bid = compute_bid(courier, parcel)   # Algorithm 1 with TS-Tree support
        if bid != INF:
            graph_edges.append(Edge(courier, parcel, bid))

    # Step 3: multi-round assignment
    while graph_edges:
        round_list = sorted(graph_edges, key=lambda e: e.bid)
        used_couriers = set()
        used_parcels = set()
        round_assignments = []

        for edge in round_list:
            if edge.courier.id in used_couriers:
                continue
            if edge.parcel.id in used_parcels:
                continue

            # lowest bid for this parcel in current graph
            best_edge_for_parcel = min(
                (e for e in graph_edges if e.parcel.id == edge.parcel.id),
                key=lambda e: e.bid,
                default=None,
            )

            if best_edge_for_parcel is not None and best_edge_for_parcel is edge:
                round_assignments.append(edge)
                used_couriers.add(edge.courier.id)
                used_parcels.add(edge.parcel.id)

        # commit assignments of the current round
        for edge in round_assignments:
            assign_parcel_to_courier(edge.parcel, edge.courier)
            matching.append(edge)

        # update courier schedules / capacities / indexes
        update_states_after_round(round_assignments)

        # rebuild or incrementally update graph
        graph_edges = update_graph_after_round(
            graph_edges=graph_edges,
            committed_assignments=round_assignments,
            couriers=couriers,
            remaining_parcels=[p for p in parcels if not p.is_assigned],
            til_index=til_index,
        )

    return matching
```

---

# 8. Why MRA is better than the greedy baseline

The greedy baseline in the ACF paper processes parcels in a simple parcel-by-parcel way:
- for each parcel, find the lowest-bid courier now
- assign immediately

MRA improves this because:
- it constructs a **global candidate graph**
- within a round, it prefers **lowest-bid edges parcel-wise**
- then **updates courier states and bids**
- and runs another round

This lets it recover assignments that a one-pass greedy method would miss.

---

# 9. Exact update logic after each round

This part is easy to implement incorrectly.

After a round commits assignments, the paper says to update graph \(G\) as follows:

## 9.1 Remove assigned parcels
Any edge involving a parcel already assigned must be removed permanently.

## 9.2 Recompute bids for couriers that got new parcels
If courier \(c\) receives a new pick-up parcel in this round:
- its remaining capacity changes
- its schedule changes
- therefore its bid to all still-unassigned parcels may change

So for all remaining parcels reachable by this courier, the algorithm must recompute:
- feasibility
- best insertion position
- detour ratio
- bid value

## 9.3 Remove invalid courier-parcel pairs
If after the update:
- courier capacity is exhausted, or
- parcel deadline no longer feasible, or
- schedule insertion invalid

then the corresponding edge must be removed.

## 9.4 Remove dead couriers
If a courier has:
- no remaining capacity, or
- no valid candidate parcel left

that courier effectively disappears from further graph processing.

---

# 10. Example logic from the paper

The paper gives a running example with:
- 2 couriers \(c_1, c_2\)
- 6 pick-up parcels \(\tau_1,\dots,\tau_6\)

The assignment proceeds in three rounds:
- **Round 1**: assign \(\tau_6\) to \(c_2\), assign \(\tau_1\) to \(c_1\)
- update bids and remove assigned parcels
- **Round 2**: assign \(\tau_5\) to \(c_2\), parcel \(\tau_3\) is delayed to next round because current first edge is not the lowest bid for that parcel in the graph
- **Round 3**: assign \(\tau_3\) and \(\tau_2\)
- \(\tau_4\) remains unassigned due to capacity limits

This example shows an important property:

> The first edge in the sorted list is **not always committed**.  
> It is committed only if it is also the parcel's current lowest-bid edge in graph \(G\).

That rule must be implemented exactly.

---

# 11. Output of MRA

The paper returns a parcel assignment set \(M\), but for a practical implementation you should store, for each matched pair:

- `parcel_id`
- `courier_id`
- `winning_bid`
- `payment` = second lowest bid among valid couriers for that parcel, if you want full auction bookkeeping
- insertion position / updated schedule
- round index

Even though the social welfare objective depends on winner bid, the MRV auction mechanism also needs the second-lowest bid payment for economic statistics.

---

# 12. Complexity stated by the paper

The paper gives time complexity:

\[
O\Big(
n g \log m
+ m n (\log |S_c| + |S'_c|)
+ n|L|\log |L|
\Big)
\]

where:
- \(g\): number of grids
- \(m\): number of couriers
- \(n\): number of pick-up parcels
- \(|L|\): number of graph entries

Interpretation:
1. candidate generation via TIL
2. graph construction with bid computation
3. multi-round processing with sorted edge lists

---

# 13. Implementation-critical cautions

## 13.1 MRA is not a standard assignment solver
Do not replace it with:
- Hungarian matching
- min-cost max-flow
- greedy first-come-first-serve
- simple "assign lowest bid once" rule

Those are different algorithms.

## 13.2 Bid recomputation is essential
The moment a courier gets a new parcel:
- route/schedule changes
- capacity changes
- bids to future parcels change

If your implementation does not recompute bids after each round, it is **not MRA**.

## 13.3 Candidate generation via TIL is part of the paper design
A small reproduction may initially brute-force all courier-parcel pairs, but then:
- it is a simplified reproduction of MRA logic
- not the full performance-oriented paper implementation

So you should distinguish:
- `rma_exact_slow_reference`
- `rma_indexed`
if both versions exist

## 13.4 TS-Tree is part of bid computation
Similarly, if your code recomputes insertion position by scanning the whole schedule without TS-Tree:
- it may still preserve algorithmic correctness
- but it is not the exact optimized implementation described in the paper

Again, it should be documented honestly.

## 13.5 Second-price payment bookkeeping
The source paper is auction-based.  
Even if assignment only needs the lowest bid for winner selection, the economic model also needs:
- winner
- second-lowest bid payment

For baseline comparisons focused on completion ratio / social welfare, winner selection may matter most.  
But for faithful reproduction of the auction baseline, payment logic should be preserved.

---

# 14. Recommended module decomposition for Codex

A clean implementation should separate:

## 14.1 Entities
- `Parcel`
- `DropoffParcel`
- `Courier`
- `ScheduleEntry`
- `Edge`

## 14.2 Distance / travel-time utilities
- shortest-path distance
- travel-time estimation
- insertion detour calculation

## 14.3 Schedule feasibility
- check deadline feasibility
- check capacity feasibility
- compute best insertion position

## 14.4 Bid computation
- `compute_capacity_ratio`
- `compute_detour_ratio`
- `compute_bid`
- `compute_second_lowest_payment`

## 14.5 TS-Tree
- build
- update after insertion/removal
- query overlapping sub-schedule

## 14.6 TIL index
- build reachable areas
- insert courier
- update courier after state change
- query candidate couriers for parcel

## 14.7 MRA runner
- graph construction
- per-round edge sorting
- round assignment
- graph update
- final auction result

---

# 15. Minimal faithful checklist for a Codex implementation

A good RMA/MRA implementation should satisfy:

- [ ] represent pick-up parcels, drop-off parcels, couriers, and schedules explicitly
- [ ] enforce capacity and deadline feasibility before bidding
- [ ] compute bids using the MRV bid formula
- [ ] compute detour ratio by insertion into existing schedule without reordering all old points
- [ ] build candidate courier-parcel pairs
- [ ] construct weighted bipartite graph with bid weights
- [ ] process graph in multiple rounds
- [ ] in each round, sort edges by bid
- [ ] assign an edge only if it is the parcel's current lowest-bid edge
- [ ] prevent using the same courier twice in a round
- [ ] remove assigned parcels after each round
- [ ] recompute bids for couriers whose state changed
- [ ] update schedule/capacity after each committed assignment
- [ ] continue until graph empty
- [ ] optionally compute second-lowest payment for economic metrics

---

# 16. What can be simplified and what cannot

## Can be simplified, but must be documented
- using brute-force candidate generation instead of TIL
- scanning whole schedule instead of TS-Tree
- using Euclidean distance instead of full road-network shortest path for a toy reproduction

## Cannot be changed if you still want to call it RMA/MRA
- must remain **multi-round**
- must remain **bid-graph-based**
- must **recompute bids after assignments**
- must follow **lowest-bid-for-parcel** rule inside each round
- must remain **auction-based**, not arbitrary heuristic

---

# 17. Short baseline summary for Codex

If you need a compact implementation summary:

> RMA in your project should be implemented as the MRA algorithm from the ACF paper.  
> Build candidate courier-parcel pairs, compute auction bids for feasible pairs, construct a bipartite graph whose edge weights are bids, then repeatedly process the graph in rounds. In each round, sort edges by increasing bid and commit an edge only if it is the current lowest-bid edge for that parcel; after committing assignments, update courier schedules/capacities and recompute affected bids. Continue until no feasible edges remain.

---

# 18. Suggested filename note

Although the source paper uses **MRA**, naming this note or implementation as:
- `rma.py`
- `rma.md`

is acceptable if your current project baseline list already uses **RMA**.  
Just document once that **RMA = MRA baseline from the ACF paper**.
