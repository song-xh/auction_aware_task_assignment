# Batch-End Matching and Route Deadline Feasibility Design

## Problem

The CPUL paper requires assignments to be made at the end of each batch, and
requires a valid courier schedule to respect every parcel deadline after a new
pickup is inserted. The current repository has three mismatches:

- `baselines/gta.py` runs BaseGTA and ImpGTA at each arrival time instead of a
  CPUL-comparable batch boundary.
- `baselines/mra.py` groups tasks into batches but evaluates each bucket at its
  start time and advances routes only after matching.
- CAPA-backed feasibility checks confirm that the new parcel can be reached,
  but do not verify that inserting it leaves later route stops on time. GTA's
  independent legacy insertion routine has the same gap.

Reference [17] defines BaseGTA and ImpGTA as real-time algorithms. Applying
batch-end decisions to them is an intentional evaluation adaptation requested
for comparison against CAPA, not a claim that it reproduces [17]'s timing.

## Approach

Use a narrowly scoped shared validation path:

1. Extend CAPA courier snapshots with aligned `route_deadlines` metadata.
   Legacy projection fills those deadlines from queued task objects; assignments
   append/insert the accepted parcel deadline alongside the route location.
2. Add an exact route-insertion search that considers only insertion positions
   where traversal from `now` reaches the new parcel and every affected
   existing route stop by its deadline. Use it wherever an assignment selects
   an insertion position: CAMA, DAPA, shared baseline helpers, Greedy, MRA, and
   RL/environment direct-local paths.
3. Keep GTA's existing route model and AIM/ImpGTA rules, but add equivalent
   route replay inside its legacy insertion candidate evaluation.
4. Give BaseGTA/ImpGTA a batch-size parameter and process arrived tasks only
   after moving simulation state to each batch end. Give MRA the same
   movement-before-decision and `now=batch_end` ordering.

An alternative would migrate GTA to CAPA snapshots, but that would conflate a
timing correction with a baseline rewrite. Another alternative is rejecting
timed-out deliveries only after execution; that leaves bidding and revenue
decisions based on infeasible assignments. Neither is appropriate here.

## Invariants

- No accepted insertion may make its new parcel or a later queued stop exceed
  a known deadline.
- Missing deadline metadata for synthetic `Courier` route fixtures does not
  invent constraints; legacy routes and newly assigned CAPA routes carry
  deadline metadata explicitly.
- Route feasibility is enforced before an assignment is committed; no greedy,
  random, or backup assignment is introduced.
- BaseGTA/ImpGTA retain their local/AIM/prediction decisions; only the
  observation/decision boundary changes to batch end.
- MRA retains multi-round graph matching and recomputation after assignments.

## Verification

The regression suite will add:

- CAPA local and DAPA cross tests where the shortest insertion reaches the new
  parcel but delays an existing downstream stop beyond its deadline.
- A legacy shared-baseline insertion test and a GTA-specific insertion test for
  the same downstream deadline condition.
- BaseGTA and ImpGTA tests proving the evaluator receives the batch-end time.
- An MRA test proving feasible-edge construction happens at batch end after
  route progression.

Existing metric, deadline-accounting, RL smoke, shortlist, and full repository
tests will be rerun after implementation.
