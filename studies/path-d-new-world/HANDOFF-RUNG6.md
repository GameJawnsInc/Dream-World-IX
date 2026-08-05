# HANDOFF — Path D Rung 6: ENTRANCE / EXIT (connect 9013 to the real game)

> Written 2026-08-05 by the audit session at the close of rungs 0–5. This file is the
> session-starting brief; the AUTHORITATIVE spec is `PLAN.md` §3 Rung 6 — read it in full
> before writing anything. Where this file and PLAN.md disagree, PLAN.md wins, except where
> a "NEW SINCE PLAN" note below records a capability that postdates it.

> ⚠ **CORRECTED 2026-08-05 (Rung 6 session, byte-verified against the live install):** point 2
> below is WRONG — 9013's `.eb` is NOT blank. It is a byte-exact per-locale clone of pristine
> stock WORLD11 (sha-matched, all 7 langs), so it already carries the full base-2 AREA switch
> (41 live / 18 dead arms), func-0xB, 41 inherited cell-tag triggers, and the entry-14 arrival
> mechanism (`mapIndex==0` → stamp WORLD11's stock default; nonzero → the persisted world-position
> record, i.e. `worldexit.arrive_writes()`'s exact vars). No switch-from-zero, no
> `cmdasm.assemble_block`, no eb-src authoring is needed for the exit. Point 3's sub-spike is
> CONFIRMED and stronger than hoped: `entrance_func_body_direct(dest, world_state=9013,
> prompt=True, dispatchers=load_world_dispatchers(game))` + `eb.edit.add_function` splice
> cleanly onto WORLD13's raw bytes (proven offline on the live bytes; only `author_entrance`
> itself is p0data-locked). eb-src round-trips the file but object-0 is a `raw=` entry —
> verifier only. See `rung6/` in this study dir for the build.

## Mission

A real field can `WMAPJUMP` (field opcode `0xB6`) into world id **9013**, and 9013 can
`Field(dest)` back out to a real field. **Definition of done = PLAN.md's cheap verify:**
enter 9013 from a real field via a normal gateway, walk to an exit trigger, land back on a
real field with story state intact — a normal-play round trip, no debug warp. Owner
playtests each half separately first (one change per in-game test).

## State you inherit (rungs 0–5 CLOSED)

- The 9013 world exists, boots, and its coast is owner-confirmed clean island-wide
  (V-shore corner, 2026-08-02). Bench reproducible: `bench_pipeline.py all`, gated by
  `terrain_gate.py` (10 gates, one command). Generators refuse a corner-less deploy.
- The engine chain is BUILT and on the stack — `memoria-patches/README.md` is the
  authoritative per-patch status table (house rule): s70 (debug reach-widen), s71
  (throwaway spike, retired-not-deleted), s72 (`WorldScene` directive), s73 (permanent
  wire, band 9013–9099), s74 (sentinel-disc override namespace, sentinel disc **9**),
  s75 (clone mode + mist). Read those six README rows — each records landmines already
  priced (see Traps below).
- Geometry iterates at ~1s: `~ → World → Reload overworld on state` re-reads every loose
  `.ff9mesh`. RELAUNCH only for DictionaryPatch/`WorldScene` registration lines,
  BattlePatch, FolderNames, or a DLL rebuild.
- Laws: NEXT-STUDIES.md "Carry-forward laws" (overhang-context, defect-follows-authorship,
  score-against-the-neighbour, exact-repair, hot-path) — they cost 13 playtests to learn.

## The rung's actual shape (PLAN.md §3 Rung 6, condensed)

1. **Field-side half** — ordinary field authoring (`authoring-ff9-field-scripts` skill):
   a gateway/trigger in a real-or-scratch field executing `WMAPJUMP` into 9013.
   Independent of `entrance.py` entirely.
2. **World-side half** — 9013's own `.eb` needs an exit switch dispatching `Field(dest)`.
   **`author_entrance` is NOT the tool**: its purpose is replicating a trigger across all
   13 story-state dispatchers, and `load_all_dispatchers` cannot see a custom dispatcher
   anyway. `eb/edit.py`'s `find_switch`/`repoint_switch_case` only edit an EXISTING
   switch; 9013's blank world `.eb` has none — the switch must be built from zero
   (`cmdasm.assemble_block`), or accept ONE hardcoded exit for day one.
3. **Sub-spike, unproven**: `entrance_func_body(dispatchers=)` always templates from
   `evt_world_world00` (a real key), so the trigger FUNCTION BODY may be reusable for our
   switch arms without `author_entrance`'s discovery loop. Test it; do not assume it.

**NEW SINCE PLAN:** the `.eb` source round-trip shipped and is playtest-proven
(`eb-src`/`eb-asm` + `--against` splice edits, slot 30810 — `studies/eb-roundtrip/PLAN.md`,
rungs 1–4+6–7 done). Evaluate authoring the switch-from-zero in eb-src FIRST — it may
collapse the "switchbuild helper" cost to a source-level edit. If it can't express it,
fall back to `cmdasm.assemble_block` per the plan.

## Read-first gates (mandatory, in this order)

1. `PLAN.md` §3 Rung 6 + §4 patch inventory + §5 kit inventory + §6 open unknowns + §8
   what-NOT-to-build (encounters/minimap/banners/vehicles are OUT of this rung's scope).
2. `memoria-patches/README.md` rows s70–s75.
3. Memories: `project-ff9-path-d-new-world` (BAND-CONTINUATION law, runtime state),
   `project-ff9-overworld-worlds` (the 13 dispatchers + exit cascade),
   `project-ff9-overworld-action-prompt` (IF the exit uses the native action-prompt lane:
   surgery case 53 or virgin band 61–64; **case 52 is the quicksand BATTLE — never it**),
   `project-ff9-eb-script-tooling` (**opcode `0x2A` is Battle, NOT a warp**),
   `project-ff9-gateway-regions` (fade BEFORE `Field()`).
4. The `authoring-ff9-overworld` skill — **bad geometry under the spawn bricks the save
   silently**; the 9013 entry point's ground must be census-clean before any owner enters
   through it.
5. `project-ff9-world-scene-rigs` only if the entrance gets a camera move.

## Traps already priced (do not re-learn)

- `ArmWorldReload` (debug route) needs `UIManager.State == WorldHUD` AND `sys.mode == 3` —
  it only fires while already standing on an overworld. The REAL dispatch path
  (`ff9InitStateWorldMap` → `EventDB[MapNo]`) has no such gate.
- **EventDB is ONE flat last-write-wins namespace across FieldScene/BattleScene/WorldScene
  and every stacked folder.** Before minting any id (field-side test fields included),
  grep BOTH live `DictionaryPatch.txt` files. Field scratch band: 30000–32767.
- The `WorldScene` directive defaults mesID **68** (the shared world text block). Do NOT
  mint a new message id for the world side — it would shadow a real location's dialogue.
- s74's special-object guard suppresses stock landmarks (219/389/91/115) on the synthetic
  disc; s74 splits `TryReadDonorPath` so donors resolve — if a beach/sea carry silently
  drops on 9013, re-read that README row before debugging anything else.
- Deploys: pin your own `.ff9deploy.toml`; the world overrides live in
  `FF9CustomMap-world`; the deploy ledger (`.ff9world.jsonl`) refuses foreign bytes —
  if it refuses YOURS, read the last ledger line before reaching for force.
- A DLL rebuild AUTO-DEPLOYS over the live install with no backup — back up first, and
  batch engine edits so the relaunch tax is paid once.

## Suggested first moves

1. Read the gates above; then re-verify the live install state (another session may have
   deployed since this handoff — check the ledger + DictionaryPatch, never assume).
2. Run the sub-spike: can `entrance_func_body(dispatchers=)`'s template drive our switch
   arms? (Offline disassembly comparison first; no deploy.)
3. Decide eb-src vs `cmdasm` for the world-side switch on a THROWAWAY copy of 9013's
   `.eb`, verified by `eb_disasm` round-trip before any deploy.
4. Field-side half first, on a scratch field (30xxx): gateway → `WMAPJUMP` 9013. Owner
   tests entry alone (spawn ground census-clean first).
5. Then the world-side exit with ONE hardcoded destination. Owner tests the round trip.
6. Commit at each tested milestone; merge to master at the owner's word; run the eb/world
   domain test subsets pre-merge (the nightly gate owns the full suite).
