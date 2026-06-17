# `fork-report` — will this field fork faithfully?

The north star is fork **fidelity**: *fork a real field → does it play identically?* (see
[FORK_FIDELITY](FORK_FIDELITY.md)). `fork-report` answers that **before you fork** — offline, reading the
field's compiled `.eb`, no game running. It tells you what a fork will and won't reproduce, and how to
assert the right story beat.

```
ff9mapkit fork-report 354          # by field id
ff9mapkit fork-report dl_shp       # by FBG-name substring (see `list-fields`)
```

> A bare number here is a **field id** — and so is a bare number to `import` (the two are at parity by design, so
> `import 354` forks the **same** field `fork-report 354` describes). The report's **Suggested authoring** line
> still spells out the `import` command with the field's full **FBG name** for robustness — copy that to fork the
> exact field you reported on.

It's also a one-click **Preview fidelity** button on the Workspace's **Import** surface
(`ff9mapkit/workspace/importdoc.py`): type/Find a field, hit **Preview fidelity**, read the verdict, then import.

## What it reports — two independent axes

A fork can render the right cast yet lose its interactions (or vice-versa), so the two are reported
separately:

- **Roster fidelity** — how many persistent objects a fork carries, how many are **directors** (a
  `Field()`-warp / phase-switch in their LOOP = a cutscene actor carried as an NPC, the rotating-cast /
  stacked-spawn failure mode), and whether content **rotates by story beat** (many ScenarioCounter gates).
- **Interaction fidelity** — per carried NPC, whether its talk handler **ports**: `clean` = fully
  interactive on the fork, `init_only` = renders but its talk is dropped (re-author it), `refuse` = a stub.
- **Dialogue** (the TEXT axis, orthogonal to interaction) — how many carried NPCs **speak** (a tag-3 talk
  window) and how many lines. Their words render **wrong** unless the fork carries the text, so the report
  flags it before you fork: ship with `--carry-text` (remaps the windows) or `--verbatim` (ships the whole
  donor `.mes`). This is the preview of the build-side lint (FORK_FIDELITY.md #5).
- **Items / treasure** — the item/gil grants + shops the field's `.eb` performs (`AddItem` / `AddGil` /
  `Menu(2, id)`). These live **wholly in the `.eb`**, so a `--verbatim` fork RUNS them (carries them
  byte-identically), but a plain/synthesize fork has **no item scanner**, so it **DROPS** every treasure +
  shop. A shop's stock is also **parasitic on the base `ShopItems.csv`** (a fork can't change the inventory).
  Item ids are pool-encoded (`id % 1000`: 0-255 regular, 256-511 key item, 512-611 card, ≥612 inert); a plain
  0-255 regular item is named, the rest are classified but unnamed (the kit catalogs only the regular space).
  Counts are **per-grant maxes, not summed** across the field's mutually-exclusive story branches.

Plus: the controlled **Player** character(s), what a verbatim fork does to your **Party**, **story-gated
doors**, the ScenarioCounter **beats the field gates content on**, a suggested `[startup] scenario` (the
earliest gate — its natural "home" beat), and the `import` recipe.

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
  Items         : opens shop(s) #0  (--verbatim carries these; a plain/synthesize fork DROPS them; shop stock = base ShopItems.csv)

  Verdict: a STORY-EVENT field -- a fork is a high-fidelity diorama, not a faithful slice (rotating cast / cutscene actors)
```

The real Dali Weapon Shop gates content across 11 story beats (Dali → Pandemonium) and carries a cutscene
director — exactly the "rotating shop" that forks into a stacked-NPC mess. Daguerreo 2F, by contrast, reports
a CLEAN static-roster.

## `--explain` — decode the cast's interactions into readable English

`fork-report <field> --explain` traces every carried NPC's **tag-3 talk routine** into plain steps — the real
`.mes` dialogue + items/gil/menus + the funcs it `RunScript`s — and **inlines** those funcs (the Main_Init
shared logic at `uid 0`, the player sequences at `uid 250`/a player entry, a sibling object) so a multi-NPC
sidequest reads as one quest. Each NPC is tagged `[interactive]` or `[render-only -- <why>]`.

Its real value is showing **why a render-only NPC is render-only**: you SEE that its talk routine *is* the
field's own quest logic (shared dialogue branches / a scripted player walk / an item-card economy), not a
graftable gesture — so the fix is **`--verbatim`** (which carries it byte-for-byte), not a graft. This is the
shipped conclusion of the **#14 talk-handler-closure investigation** (proven infeasible by a verified census:
of 55 render-only NPCs across 36 fields, 0 are blocked only by a graftable gesture — every one depends on the
field's own logic). Read the quest, decide per-field. Needs the install for the dialogue text (degrades to
`<line N>` placeholders without it); the structure is `.eb`-only.

## The workflow it fits

1. `fork-report <field>` → pick a field whose verdict is **CLEAN static-roster** for a faithful fork (or accept
   the diorama trade-off for a story-event field).
2. `fork-report <field> --explain` → read what the cast actually does; if its NPCs need their quest logic, fork
   `--verbatim` (else `import --native --graft-player-funcs --carry-text`).
3. `ff9mapkit import <field> --native --graft-player-funcs --carry-text` (the recipe it suggests).
4. Add the suggested `[startup]` block so the fork boots in the right beat.

## How it works (read-only)

It adds **no** carry/scanner logic — it reuses `eventscan.scan_objects_verbatim` (the carry `graft_safety`
classification), `eventscan.scan_gateway_entries` (story-gated doors), and the `flags` beat table
(`SCENARIO_MILESTONES` / `nearest_milestone`). ScenarioCounter gates are found by scanning the bytecode for
the comparison pattern `DC 00 7D <const> <cmp-op>` (a *write* uses `2C`/`3F` instead, so writes are excluded).
The Party axis (`scan_party_ops`) and Items axis (`scan_item_ops`) decode their ops straight off the kit's
disassembler — `scan_item_ops` reads `AddItem`/`AddGil`/`Menu(2,id)` and classifies item ids by the engine's
`id % 1000` pool rule (`ff9item.FF9Item_Add_Generic`). The analysis (`forkreport.analyze_eb`) is pure over
`.eb` bytes and unit-tested offline against a fixture.
