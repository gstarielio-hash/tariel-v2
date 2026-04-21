---
name: tariel-v2-autonomous-migration-worker
description: Use when the goal is to continue the Tariel V2 migration autonomously until completion, resolving routine implementation decisions locally, validating each coherent slice, updating the migration loop doc, and committing and pushing safe progress to origin/main.
---

# Tariel V2 Autonomous Migration Worker

Use this skill in `/home/gabriel/Área de trabalho/TARIEL/tariel-v2` when the user wants uninterrupted migration progress with TypeScript-first ownership and minimal need for follow-up decisions.

## Permanent inputs

Before choosing each new slice, read:

- `docs/TARIEL_V2_MIGRATION_CHARTER.md`
- `docs/LOOP_ORGANIZACAO_FULLSTACK.md`

Treat the charter as the permanent migration policy until the migration reaches 100%.

## Mission

- Make `tariel-v2` the official system.
- Treat the legacy Python/Jinja system as backup, reference, or temporary bridge only.
- Prefer `Astro + React + TypeScript + Prisma` for product-facing web surfaces.
- Keep Python only where it still acts as specialized runtime or where rewrite is not yet justified.

## Work rules

- Do not stop for ordinary product or implementation choices.
- Preserve productive behavior first.
- Do not revert unrelated user changes.
- Stage explicit paths only.
- If a slice is partially blocked, move to the next safe slice instead of idling.
- Stop only for a real external blocker:
  - missing secret or credential
  - unavailable external service
  - destructive data risk with no safe fallback
  - conflicting user edits that cannot be merged safely

## Priority order

1. Finish the slice already in progress.
2. Close the Admin portal end-to-end in V2.
3. Migrate the Client portal.
4. Migrate the Reviewer portal.
5. Migrate the Inspector workspace and remove heavy legacy JS/CSS dependence.
6. Remove legacy route and template traffic after validation.

When a more specific user directive exists for the current slice, follow it first.

## Slice workflow

1. Read the charter and the latest loop doc state.
2. Inspect `git status --short`, relevant diffs, and the smallest safe slice that advances the official V2 path.
3. Prefer complete vertical cuts over mock-only UI when feasible:
   - Astro page
   - server read/write helpers
   - Prisma-backed persistence
   - legacy bridge only when needed
4. Validate with the lightest commands that still prove the slice:
   - Astro/TS SSR: `./bin/npm22 run check && DATABASE_URL='postgresql:///tariel_dev' ./bin/npm22 run build`
   - Python touched: `python -m py_compile ...` and targeted `pytest`
   - Always: `git diff --check`
5. Update `docs/LOOP_ORGANIZACAO_FULLSTACK.md` after each completed coherent slice.
6. Create a narrow commit with an intentional message.
7. Push to `origin/main` when the local package is coherent and validated.

## Decision heuristics

- Prefer landing production-safe read/write slices in Admin before expanding surface area.
- Be honest when auth, step-up, or actor binding are transitional. Do not claim full security before it exists.
- Keep the UI usable during migration, but do not freeze progress waiting for perfect visual parity.
- If the legacy backend is still the source of truth for a rule, port the read model first, then the write path, then remove the bridge.
- When choosing between a broad rewrite and a thin compatible slice, prefer the thin compatible slice that can ship now.

## Required end-of-package report

When a package is completed or blocked, respond with:

- status
- validation run
- commit SHA and message
- push result
- next slice queued
- list of altered files
