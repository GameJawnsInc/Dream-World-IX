---
name: building-ff9-campaigns
description: Assemble multi-field FF9 campaigns and multi-campaign journeys / a World Hub, and wire the New Game entry. Use for `import-chain` (`--whole-zone` / `--ids` to scope one story-state visit), `build-all`/`lint-campaign`/`new-campaign`/`add-field`/`deploy-campaign`, `gen-hub`/`lint-journey`/`assemble-journey`/`deploy-journey`, `reference-arcs`, or `newgame`. Covers `import-chain` door-walk misses ~41% -> `--whole-zone`; a place's revisits are separate id clusters -> `--ids 100-117` forks one visit, not all 48 screens; `deploy-campaign` wholesale-replaces `FF9CustomMap` and WIPES the New-Game override (re-run `wire_newgame` after every opening/campaign re-deploy); journey single-folder merge must concatenate EVERY root `*Patch.txt`; `reference-arcs` scaffolds a PLAN not a one-click rebuild; New Game lands via the stock field-70 `Field(<id>)` override (target must be a registered field). For forking a single field see `forking-ff9-fields`; for deploy mechanics see `deploying-ff9-mods`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Building FF9 Campaigns

Multi-field campaigns (`campaign.toml`), multi-campaign journeys (`journeys.toml`), the World Hub
selector, and New-Game wiring. For forking/authoring a SINGLE field, use the `forking-ff9-fields`
skill; for mod-folder / id-band / test-slot deploy mechanics, use `deploying-ff9-mods`.

## Scoping a fork

`import-chain <seed>` walks the door graph only — scripted cutscene transitions (~41% of FF9
connectivity) are recorded as seams, not followed, so cutscene-driven zones fork tiny. Fix =
`--whole-zone` (seed every forkable field in the seed's zone). But a place's revisits are
SEPARATE id clusters sharing one zone: `--ids 100-117` forks Alexandria's opening visit
(18 fields), not all 48 revisit screens. Details, real numbers, and the cross-zone leak lint ->
`references/scoping-and-newgame.md`.

## Campaign build / lint / deploy

`new-campaign` (empty manifest) · `add-field` (blank room, or fork a real field in) · `build-all`
(compile every member into ONE staged mod; auto-lints) · `lint-campaign` (offline: ids, edges,
flags, leak warnings) · `deploy-campaign` (reversible but DESTRUCTIVE: one snapshot, then a
wholesale mod-folder replace — never a per-id merge). Canonical doc + worked Ice Cavern example:
`ff9mapkit/docs/CAMPAIGN_IMPORT.md`.

## Journey assembly + the single-folder merge

`gen-hub` (emit the selector field from a `journeys.toml`) · `lint-journey` · `assemble-journey` ·
`deploy-journey` (dry-run playbook by default; `--apply` one-shot). Cross-campaign links auto-wire
from the forks' real `.eb` seams — a journey needs ZERO `[[journey.link]]` rows; both link modes
are proven: `field_remap` (a `Field()` seam retargeted) and `worldmap_inject` (an overworld
walk-out region body-replaced). `--single-folder` merges the whole journey into ONE mod folder —
the merge MUST concatenate EVERY root `*Patch.txt` (copying `ForkDonorPatch.txt` entry-last-wins
instead of concatenating broke the fork-donor engine gates). Schema: `ff9mapkit/docs/JOURNEYS.md`;
merge recipe + live-fix: read memory [[project-ff9-journey-single-folder]].

## World Hub

New Game -> hub (a journey-selector field) -> verbatim forks. The hub is thin: select -> seed ->
warp; its folder is highest-priority and owns the field-70 override. Read
[[project-ff9-world-hub]] — it also carries the fade-before-`Field()` warp rule and the
vehicle-field seam edge case (a `WorldMap` op in a nav-menu func is NOT a walk-out boundary).

## reference-arcs (a plan)

`reference-arcs` scaffolds FF9's real story arcs (`data/reference_arcs.toml`, the disc-1 spine)
into a chained `journeys.toml` + a per-arc `import-chain` fork playbook. It is a PLAN, not a
one-click rebuild: fork each arc, reconcile entry/links, deploy, playtest.

## New-Game entry + the re-wire trap

New Game lands via the stock mod field-70 override (`Field(<id>)`), NOT a DLL edit; the target
must be a REGISTERED field with deployed assets. **`deploy-campaign`'s wholesale replace of
`FF9CustomMap` WIPES the field-70 override -> re-run `py tools/wire_newgame_from_stock.py 6000`
after EVERY opening/campaign re-deploy.** Full checklist (incl. `deploy-journey --newgame` and
the run-`--apply-links`-last rule): `references/scoping-and-newgame.md`; deep recipe:
[[project-ff9-new-game-entry]].

## Flag scope at campaign / journey tier

field-local < campaign-shared < journey-global `[[flag]]` — all the SAME `gEventGlobal` array,
only the naming scope differs; the campaign tier is the workhorse. Read
[[project-ff9-story-flags]] and [[project-ff9-flag-scope-hierarchy]]; the allocation-band table
lives in `ff9mapkit/docs/GLOBAL_RESOURCES.md`.

## Additional resources

- `ff9mapkit/docs/CAMPAIGN_IMPORT.md` — import-chain / build-all / deploy-campaign, schema + worked example.
- `ff9mapkit/docs/JOURNEYS.md` — the `journeys.toml` schema + the assembler reference.
- `ff9mapkit/docs/GLOBAL_RESOURCES.md` — global id/flag namespaces + the kit's allocation bands.
- Memory: [[project-ff9-import-chain-coverage]], [[project-ff9-journey-single-folder]],
  [[project-ff9-new-game-entry]], [[project-ff9-first-continent-proposal]].
