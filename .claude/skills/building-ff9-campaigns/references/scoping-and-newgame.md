# Scoping a chain fork (`--whole-zone` / `--ids`) + the New-Game re-wire checklist

Distilled from memory `project-ff9-import-chain-coverage`, `project-ff9-new-game-entry`, and
`project-ff9-world-hub`, plus `ff9mapkit/docs/CAMPAIGN_IMPORT.md` (§2.7) and
`ff9mapkit/docs/JOURNEYS.md` (§5). Load-bearing rules below are quoted VERBATIM from those files
(blockquotes); everything else is a pointer — read the named source before going deeper.

## Contents

1. Why a bare `import-chain <seed>` under-forks
2. `--whole-zone` — fork the seed's whole zone
3. `--ids <ranges>` — fork ONE story-state visit
4. Cross-zone scripted-warp leaks + the leak lint
5. New-Game entry — the stock field-70 override
6. THE RE-WIRE TRAP — `deploy-campaign` wipes the override
7. Journey deploys — New-Game knobs + run `--apply-links` last

## 1. Why a bare `import-chain <seed>` under-forks

From `project-ff9-import-chain-coverage`:

> `import-chain <seed>` discovers fields by walking the **door graph** (walk-in gateways), but FF9 story
> zones move you screen-to-screen by **SCRIPTED cutscene transitions** (~41% of all connectivity), which the
> walk records as dead-end SEAMS and does NOT follow

So cutscene-driven zones fork tiny while linear walk-in dungeons fork fine (measured: ice_cavern=12,
dali=8 = good; alexandria=2 of 38, evil_forest=1 of 13, treno=1 of 19 = collapsed). A second cause:
some seeds are isolated screens whose only exits are scripted warps (evil_forest's real entrance is
250, not the isolated 152).

## 2. `--whole-zone` — fork the seed's whole zone

> **Fix = `import-chain --whole-zone`** (kit, commit `fc61912`): seed EVERY forkable field in the seed's zone(s)
> (from ID_TO_FBG), not just the door-reachable slice — the seed stays first (so `entry_field` is the intended
> entry), `max_fields` auto-raised to fit.

A zone-coverage hint in the dry-run report flags an isolated seed ("forked 1 of 13 forkable fields
in zone evft — try --whole-zone"). Whole-zone KEEPS other-disc `_a/_b/_w` variants — prune as needed.

## 3. `--ids <ranges>` — fork ONE story-state visit

> A place's revisits in FF9 are **separate field-id clusters that SHARE the background art** (same FBG)

E.g. Alexandria town (`alxt`) = 100-117 opening · 1850-1865 return · 2050-2054 · 2450-2457 ruined
(`_w` art) · 3000 ending. So `--whole-zone` on an `alxt` seed forks all **48** screens (every visit,
most dormant), while `--ids 100-117` forks exactly the opening cluster (18 fields). The mechanism
that makes it sound:

> feeding the cluster as walk seeds is NOT enough — `chain.walk` with `zones=None` bounds to
> the seed's ZONE, so a same-zone walk-in door still leaks a sibling visit (repro: `--ids 100-117` pulled in 1850-1856).
> Fix = **`chain.walk(restrict_ids=set)`**: an edge to a field OUTSIDE the set becomes a portal, never followed.

The region catalog (`data/region_catalog.toml`, the GUI "Browse FF9 regions" picker) is generated
split-by-visit: one region per id-gap cluster, each with a `members` range that `fork_command` emits
as `--ids`. Cluster boundaries are an id-gap heuristic — the toml is hand-editable to correct.

## 4. Cross-zone scripted-warp leaks + the leak lint

`--whole-zone` is per-ZONE, so it closes within-zone scripted gaps only:

> a cross-zone scripted `Field()` to a field whose zone was never seeded is invisible to it.

The leak lint is BUILT: `lint-campaign` / `lint-journey` flag any scripted/portal seam whose target
NO member forks (a SCRIPTED leak prints as a FORCED warp — softlock-class; a PORTAL as a softer
walk-out door; warnings go to STDERR). Declare intended arc boundaries with
`[[journey]] exits = [<field ids>]` so only real-bug leaks remain. Fixing a live leak WITHOUT a
re-fork (a re-fork shifts `id_base+i` and breaks saves): the id-preserving surgical-append recipe in
`ff9mapkit/docs/CAMPAIGN_IMPORT.md` §2.7.

## 5. New-Game entry — the stock field-70 override

From `project-ff9-new-game-entry`:

> `EventEngine.NewGame()` in the **deployed** DLL is **STOCK**: `fldMapNo = 70`

The mod folder `FF9CustomMap` OVERRIDES field 70: its `.eb` keeps the opening FMV + fade, then warps
`Field(<entry>)` instead of the stock `Field(50)`. So: New Game -> stock field 70 -> the mod's
override -> your entry field. No DLL edit anywhere. The target must be a REGISTERED field with
DEPLOYED assets — from `project-ff9-world-hub`:

> **A registered-but-ASSETLESS field id CRASHES on warp** — `EventEngine.StartEvents(null ebFileData)` ->
> `ArgumentNullException: buffer`.

> **A DictionaryPatch FieldScene line != a deployed field — VERIFY THE `.eb`/scene EXIST, not just the registration.**

## 6. THE RE-WIRE TRAP — `deploy-campaign` wipes the override

> every `deploy_campaign` wholesale-replace of
> FF9CustomMap WIPES the override → after a fresh campaign deploy there is NOTHING to retarget, so
> deploy_campaign's New-Game wiring just WARNS + skips and New Game boots the STOCK opening (not the fork).

The fix is the create-from-stock tool (NOT `tools/retarget_newgame_warp.py`, which only PATCHES an
existing override — after a wipe there is nothing to patch):

> `py tools/wire_newgame_from_stock.py <entry-id>` extracts stock field 70 from p0data, repoints its terminal
> `Field(50)`→`Field(<id>)` (length-preserving `remap_fields`), writes the override for all 7 langs (bytecode is
> language-identical; the FMV+fade are PRESERVED — `skip_opening_fmv.py` after for a seamless boot). Reversible
> (`scroll_out/revert_newgame_from_stock.py`). ★ RECURRING: RE-RUN it after EVERY opening re-deploy (the wipe).

For the shipped faithful opening (Prima Vista, field 6000) that is:

```
py tools/wire_newgame_from_stock.py 6000
```

Checklist after ANY `deploy-campaign` / `deploy_campaign.py` / journey re-deploy that touches
`FF9CustomMap`:

1. Re-run `py tools/wire_newgame_from_stock.py <entry-id>` (6000 for the faithful opening).
2. Optional seamless boot: `py tools/skip_opening_fmv.py` (NOPs the 2 pre-warp Cinematic ops).
3. Verify with a real New Game — debug-warp/mid-game warps skip the New-Game-only CSV seeding.

## 7. Journey deploys — New-Game knobs + run `--apply-links` last

`deploy-journey` does not claim New Game on its own:

> **New Game is NOT touched by default** (GameJawns flagged the auto-retarget as hijacking): the field-70
> override is SINGLE-OWNER, so forcing it would clobber an existing hub (e.g. the live World Hub 4500).

Pick the landing with `--newgame {none,hub,entry}` (`ff9mapkit/docs/JOURNEYS.md` §5): **none** =
reach the hub via the debug menu (~); **hub** = the selector menu (`retarget_newgame_warp`); **entry** = straight
into the opening field (`wire_newgame_from_stock`; single-journey arcs). And the sibling rule — the
same wholesale-replace wipe hits the cross-campaign link patches:

> `deploy_campaign` WHOLESALE-replaces a mod folder, so `--apply-links` must
> run **LAST** and be **re-run after ANY campaign re-deploy** — else the link patch is wiped and you land on the
> REAL target id

Both are one class of trap: a wholesale folder replace destroys every post-deploy byte-patch (the
New-Game override, the link rewrites). Re-run those steps last, every time.
