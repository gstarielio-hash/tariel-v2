# Tariel V2 Migration Charter

Status:

- active until the migration reaches 100%
- `tariel-v2` is the official forward path
- the legacy system is backup and reference only

## Non-negotiable Direction

- `tariel-v2` must become the official system.
- `tariel-web` and the legacy Python/Jinja stack must be treated as backup, reference, or temporary bridge only.
- The main product surface should converge to `Astro + React + TypeScript + Prisma`.
- Python should remain only where it still acts as specialized runtime or where rewrite is not yet justified.

## Migration Scope

This migration is for the whole product, not only the Admin-CEO surface.

The official V2 path must eventually cover:

- `Admin-CEO`
- `Admin-cliente` / tenant portal
- `Inspetor` workspace and related operator surfaces
- `Mesa Avaliadora` / review surface
- shared operational flows, platform APIs, session flows, and cross-portal governance

## Persistence Rule

This file exists so the migration goal is not lost during:

- context compaction
- handoff between agents
- long autonomous loops
- resumptions after partial work

Every migration cycle must read this file before choosing the next slice.

## Operating Rules

- Do not stop for routine product or implementation choices.
- Resolve ordinary migration decisions locally and document them.
- Only stop for a real external blocker:
  - missing credential or secret
  - unavailable external service
  - destructive data-risk decision with no safe fallback
  - conflicting user edits that cannot be merged safely
- If one slice is blocked, move to another safe slice instead of idling.

## Priority Order

1. Finish the slice already in progress.
2. Close the `Admin-CEO` portal end-to-end in v2.
3. Migrate the `Admin-cliente` portal end-to-end in v2.
4. Migrate the `Mesa Avaliadora` / review portal end-to-end in v2.
5. Migrate the `Inspetor` workspace and remove heavy legacy JS/CSS dependence.
6. Remove legacy route and template traffic after validation across the whole product.

## Current Architectural Stance

- TypeScript is the primary language for the official application surface.
- Python is transitional for specialized engines and mature legacy subsystems.
- New web work should default to v2 unless a bridge is strictly necessary.

## Delivery Contract

Each coherent slice should, when feasible:

- update the v2 implementation
- validate locally
- update `docs/LOOP_ORGANIZACAO_FULLSTACK.md`
- create an intentional commit
- push to `origin/main`

## Finish Condition

This charter remains active until the user explicitly declares the migration complete or the legacy system is no longer needed as the production path.
