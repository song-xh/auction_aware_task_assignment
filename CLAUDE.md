- Think before acting. Read existing files before writing code.
- Be concise in output but thorough in reasoning.
- Prefer editing over rewriting whole files.
- Do not re-read files you have already read.Test your code before declaring done.
- No sycophantic openers or closing fluff.
- Keep solutions simple and direct.
- User instructions always override this file.
  
# CLAUDE.md

## Critical Rule
Before writing ANY code, read `docs/rl_capa_algo.md` — it is the authoritative RL-CAPA implementation specification.

## Source-of-truth Priority
1. `docs/rl_capa_algo.md` (revised RL-CAPA spec, this is the ONLY valid RL design)
2. Paper markdown files in project root (for CAPA/DAPA/CAMA details)
3. `review.md` (reviewer comments)
4. Existing codebase (if code disagrees with spec, spec wins)

## Architecture Constraint
RL-CAPA uses **policy-gradient actor-critic**, NOT DQN/DDQN. The old DDQN design is obsolete.
- 4 networks: π1 (actor1), π2 (actor2), V1 (critic1), V2 (critic2)
- Shared environment, single platform-level reward R_t
- V2 receives second-stage state s_t^(2) AND first-stage action a_t^(1) as environmental condition
- π2 is factorized per-parcel with shared parameters

## Forbidden Patterns
- NO fallback/degradation/backup logic
- NO DQN/DDQN (the old design is replaced)
- NO fake RL wrappers or fixed policies
- NO claiming features exist if not implemented
- NO "if failed then greedy" or "if missing then random"

## Code Standards
- Every function has a docstring (purpose, args, returns)
- Type annotations on all public functions
- CAPA modules must be independent, importable by RL environment
- RL environment imports CAPA modules — never copy-paste

## Git Workflow
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`
- Tag milestones: `v0.3-rl-capa-actor-critic`

## Key Commands
```bash
python -m scripts.train_rl_capa --config configs/rl_capa/default.yaml
python -m scripts.eval_rl_capa --config configs/rl_capa/default.yaml
```