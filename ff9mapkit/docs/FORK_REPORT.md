# `fork-report` — will this field fork faithfully?

The north star is fork **fidelity**: *fork a real field → does it play identically?* (see
[FORK_FIDELITY](FORK_FIDELITY.md)). `fork-report` answers that **before you fork** — offline, reading the
field's compiled `.eb`, no game running. It tells you what a fork will and won't reproduce, and how to
assert the right story beat.

```
ff9mapkit fork-report 354          # by field id
ff9mapkit fork-report dl_shp       # by FBG-name substring (see `list-fields`)
```

> A bare number here is a **field id** (not a map number — `import` interprets a bare number as a map id, so
> `354` means different fields to the two commands). That's why the report's **Suggested authoring** line spells
> out the `import` command with the field's full **FBG name** — copy that to fork the exact field you reported on.

It's also a one-click **Preview fidelity** button in the FFIX Import GUI (`apps/ff9_import.pyw`, standalone and
the Campaign Editor's Import tab): type/Find a field, hit **Preview fidelity**, read the verdict, then import.

## What it reports — two independent axes

A fork can render the right cast yet lose its interactions (or vice-versa), so the two are reported
separately:

- **Roster fidelity** — how many persistent objects a fork carries, how many are **directors** (a
  `Field()`-warp / phase-switch in their LOOP = a cutscene actor carried as an NPC, the rotating-cast /
  stacked-spawn failure mode), and whether content **rotates by story beat** (many ScenarioCounter gates).
- **Interaction fidelity** — per carried NPC, whether its talk handler **ports**: `clean` = fully
  interactive on the fork, `init_only` = renders but its talk is dropped (re-author it), `refuse` = a stub.

Plus: **story-gated doors**, the ScenarioCounter **beats the field gates content on**, a suggested
`[startup] scenario` (the earliest gate — its natural "home" beat), and the `import` recipe.

## The verdict

- **CLEAN static-roster** — a native fork renders the cast faithfully (the simple NPCs stay interactive;
  re-author the rest). The good case.
- **STORY-EVENT field** — a fork is a high-fidelity *diorama*, not a faithful slice: rotating cast and/or
  cutscene-director objects. Pick a beat with `[startup] scenario` and expect to re-author interactions.

## Example

```
fork-report: fbg_n06_vgdl_map103_dl_shp_0  (field 354, EVT_DALI_V_DL_SHP)

  Roster        : 5 carried object(s) (4 NPC, 1 prop) - 1 director(s), 1 multi-instance  -> STORY-EVENT
  Interactions  : 3 fully interactive, 1 render-only, 1 stub  (faithful carry = --graft-player-funcs --carry-text)
  Story gating  : 0 gated door(s); ScenarioCounter gates at 2600 (Dali) ... 11090 (Pandemonium)
  Home beat     : suggested [startup] scenario = 2600 "Dali" (the earliest gate -- adjust to the beat you're forking)

  Verdict: a STORY-EVENT field -- a fork is a high-fidelity diorama, not a faithful slice (rotating cast / cutscene actors)
```

The real Dali Weapon Shop gates content across 11 story beats (Dali → Pandemonium) and carries a cutscene
director — exactly the "rotating shop" that forks into a stacked-NPC mess. Daguerreo 2F, by contrast, reports
a CLEAN static-roster.

## The workflow it fits

1. `fork-report <field>` → pick a field whose verdict is **CLEAN static-roster** for a faithful fork (or accept
   the diorama trade-off for a story-event field).
2. `ff9mapkit import <field> --native --graft-player-funcs --carry-text` (the recipe it suggests).
3. Add the suggested `[startup]` block so the fork boots in the right beat.

## How it works (read-only)

It adds **no** carry/scanner logic — it reuses `eventscan.scan_objects_verbatim` (the carry `graft_safety`
classification), `eventscan.scan_gateway_entries` (story-gated doors), and the `flags` beat table
(`SCENARIO_MILESTONES` / `nearest_milestone`). ScenarioCounter gates are found by scanning the bytecode for
the comparison pattern `DC 00 7D <const> <cmp-op>` (a *write* uses `2C`/`3F` instead, so writes are excluded).
The analysis (`forkreport.analyze_eb`) is pure over `.eb` bytes and unit-tested offline against a fixture.
