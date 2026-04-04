# 0404 Review Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit why CAPA underperforms RamCOM in the current Chengdu environment and why the Chengdu simulation runs slowly, then document paper-faithful repair directions without changing the active experiment.

**Architecture:** Read the paper's experimental claims, trace the current Chengdu environment and algorithm runners, compare CAPA and baseline execution semantics, identify root-cause mismatches and performance hotspots, and write a design-quality review memo with concrete file-level modification guidance.

**Tech Stack:** Python, legacy Chengdu simulator, CAPA modules, unified environment/runner documentation.

---

### Task 1: Trace experiment semantics and fairness gaps

**Files:**
- Create: `docs/review_0404.md`
- Reference: `env/chengdu.py`
- Reference: `algorithms/capa_runner.py`
- Reference: `baselines/ramcom.py`
- Reference: `baselines/greedy.py`
- Reference: `baselines/gta.py`
- Reference: `docs/Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics.md`

**Step 1: Read the paper's Exp-1 and Exp-4 claims**

Extract the claims about:
- `TR / CR / BPT vs |Γ|`
- `TR / CR / BPT vs |P|`
- why CAPA should beat RamCOM in `TR`
- when `CR` should saturate and then fall

**Step 2: Trace the current unified Chengdu execution flow**

Confirm:
- how the canonical environment is built
- how local and partner couriers are created
- whether partner platforms receive their own future task streams
- whether CAPA actually matches once per batch or repeatedly inside a batch

**Step 3: Write the root-cause section**

Document:
- environment-side causes
- algorithm-side causes
- which causes are likely primary versus secondary

**Step 4: Commit**

```bash
git add docs/plans/2026-04-04-review-0404-analysis-plan.md docs/review_0404.md
git commit -m "docs(plan): add 0404 review analysis plan"
```

### Task 2: Trace performance hotspots and optimization levers

**Files:**
- Modify: `docs/review_0404.md`
- Reference: `capa/utility.py`
- Reference: `capa/cama.py`
- Reference: `capa/dapa.py`
- Reference: `baselines/common.py`
- Reference: `baselines/mra.py`
- Reference: `GraphUtils_ChengDu.py`
- Reference: `capa/experiments.py`

**Step 1: Follow the shortest-path and insertion-selection call chain**

Locate:
- where shortest paths are requested
- where insertion positions are searched
- where the same courier-task pair is recomputed multiple times

**Step 2: Identify duplicate work and data-structure bottlenecks**

Document:
- `getShortPath` behavior
- repeated legacy-to-CAPA projection
- repeated feasible insertion construction
- repeated graph rebuilds in `MRA`

**Step 3: Write the staged optimization plan**

Split the proposals into:
- low-risk caching and pruning
- medium-risk simulator and runner refactors
- algorithm-specific optimizations

**Step 4: Commit**

```bash
git add docs/review_0404.md
git commit -m "docs: add 0404 CAPA fairness and performance review"
```
