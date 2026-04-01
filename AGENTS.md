# CLAUDE.md

## Project Overview

This is the codebase for the paper "Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics". It implements CAPA (heuristic) and RL-CAPA (reinforcement learning) methods for cross-platform parcel assignment.

## Critical Rule: Read Before Code

Before writing ANY code, you MUST read `docs/agent.md` — it is the authoritative implementation specification. Follow its phased workflow strictly.

## Source-of-truth Priority

1. `docs/Auction-Aware_Crowdsourced_Parcel_Assignment_for_Cooperative_Urban_Logistics.md` (paper)
2. `docs/MinerU_markdown_Competition_and_Cooperation_Global_Task_Assignment_in_Spatial_Crowdsourcing_2039180845507551232.md` (reference [17])
3. `docs/review.md` (reviewer comments)
4. `docs/agent.md` (implementation spec)
5. Current repository code

If code and paper disagree, **the paper wins**.

## Forbidden Patterns

- NO fallback/degradation/backup logic
- NO "if failed then greedy" or "if missing then random"
- NO fake RL wrappers or fixed policies labeled as DDQN
- NO claiming features exist if not actually implemented

## Code Standards

- Every function has a docstring (purpose, args, returns)
- Type annotations on all public functions
- CAPA modules (CAMA, DAPA, utility, constraints) must be independent, reusable modules
- RL environment imports CAPA modules — never copy-paste CAPA logic

## Git Workflow

- Commit after completing each Phase (see `docs/agent.md`)
- Use conventional commit messages: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `experiment:`
- Create feature branches for major changes
- Tag milestones: `v0.1-audit`, `v0.2-capa`, `v0.3-rl-capa`, `v0.4-experiments`

## Package Installation

Use `pip install` or `pip install --break-system-packages` freely. Full authority to install any needed dependencies.

## Key Commands

```bash
python -m scripts.run_capa --config configs/capa/default.yaml
python -m scripts.train_rl_capa --config configs/rl_capa/default.yaml
python -m scripts.run_experiments --suite paper_main
python -m scripts.run_experiments --suite reviewer_supplement
```