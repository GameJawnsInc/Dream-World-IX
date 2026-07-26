# THE SOUTHERN RING — the composed world (ratified 2026-07-25)

**The design** (the judged hybrid; full judgment in `out/world-design/design_judgment.json`, canvas in `canvas.json`):
Design C's spine — the four southern-band clusters read as PORTS on a route, one new island (Lamplight, r44, sited to PRESERVE the wrapwater corridor) — with Design A's grafts (THE LANTERN FERRY: a shared saloon field whose berth doors are worldmap gateways — sail where the sea is block-proven open, ferry where it is not; THE ONE-CASE FERRY: every quay shares case 53 / one nameplate; the four measured dock coords) and Design B's law adopted as the level-design principle: **THE TOPOGRAPH 36-38 ENCOUNTER LAW — overworld battles fire ONLY on forest/brush ground; open ground is the safe road, carved canopy IS the gameplay.** B's continent shelved for a future arc (pending the seam-wrap fix). En-route laws: THE LOBE-OVERSHOOT ERROR (outline rmax/radius median 1.34 — size mints accordingly); the nameplate ceiling is 2 (cases 52/53), not 18.

**R1 — THE DRY LOOP ★ DEPLOYED + byte-verified 2026-07-25 (playtest pending):**
New Game → field-70 override (2-byte diff, FMV/fade preserved) → hub 4600 (SOUTHERN_RING_HUB, Gargan Roo borrow, Stiltzkin narrator; the probe caught + fixed a 76u actor jam → 400u) → "The Southern Ring" (scenario 4100) → Field 6601 (LANTERN_HALL, Daguerreo borrow, purser moogle, savepoint, own text block) → berth door → worldmap (60,−1168) facing east on the junction island's west shore → the **Lantern Quay** case-53 native entrance at (48,−1168) → back to 6601. Zero terrain bytes; both fields BG-borrow synthesized (stock-Memoria clean, no fork gates); 44/44 disc parity; every touched file backed up; full undo in `REVERT.md`. En-route catches: this worktree had NO `.ff9deploy.toml` (created; was sharing the 4003 slot); the fresh-worktree template trap; deploy_field's sandbox rename (--name required); the recipe's `--nameplate` flag superseded (the surgery form is `--nameplate-name` alone); hub slugs must match `^[A-Za-z0-9_]+$`.

**Playtest asks (owner, after ONE relaunch):** (1) New Game lands in the hub, camera settled; (2) Stiltzkin walk-up-and-talkable, actors apart; (3) the choice warps to the Lantern Hall fully drawn; (4) "Not yet, kupo..." closes clean; (5) the berth door → west shore, facing inland; (6) `~ → World` reads **9011** (9009 = the state-record addendum is R2's first fix); (7) walk onto the quay → "?" plate → enter → the name registers "Lantern Quay" thereafter.

**Next rungs (sketch):** R2 = the state-record addendum (if 9009) + the remaining three quays (one-case) + the ferry berth rows · R3 = Lamplight island (r44 mint at (1432,−1176), overshoot-sized) · R4 = the forest gameplay pass (carve_forest per the encounter law; island E's re-site at the free r96 pocket (136,−168)) · R5 = the sea-lane probe for the sailable west arc.

## R2a — THE WORLDEXIT FIX (2026-07-25): the 9009 fall-through diagnosed to TWO kit bugs; the designed 1062 addendum REFUTED and replaced

Playtest: "i hit 9009 docked at the airship" — the predicted diagnostic, but the DESIGNED fix (seed GLOB 1062=9011) was REFUTED by the diagnosis run (the STOP rule fired; the authorization was not spent): with routing fixed but the position bug intact, the player would have landed at world (0,0) OPEN OCEAN — the actor-brick class. The real causes, both in `content/worldexit.py`:
1. **THE KEY-62 TRAP**: preset key 62's cascade arm is `D8:2=0; WorldMap(9009)` in ALL FOUR scenario bands — band-invariant; the scenario was never the problem. **Key 35** is the shipping disc-correct idiom (13 stock fields): a BARE WorldMap per band (9011/9003/9007/9008), preset survives, state re-derived from the current band for free.
2. **THE WRONG-BLOCK BUG**: `_POS_*` wrote the VEHICLE-composite actor's mirror block (C8:83..91); the ON-FOOT avatar reads C8:64/D8:67/C8:69/D4:72 (mirrored per-frame by every dispatcher's player object). The kit's own `save.py` (WORLD_POS_X_OFF=64/Z=69) had it right all along — the two layers disagreed.
**THE WARM-MIRROR MASK (the law):** the in-game-proven waystation-6500 loop had proven THE MIRROR, not the preset — its arrive bytes were inert (the direct route records 1062 → the computed lane; D8:2 stayed nonzero; the per-frame mirror held the walked-in tile 8u from the authored arrive). A COLD START (fresh New Game, mirror at 0,0,0) is the discriminating test for any arrival mechanism.
**The fix (owner-authorized v2):** `arrive_writes()` now writes BOTH blocks (72 B, on-foot first) + `POSITION_PRESET_KEY 62→35`; REGION_KEY_RETURN stays 62 (the no-arrive path is untouched). The stale test expectation updated with a key-62 regression guard; 193 tests green (game-gated tests genuinely ran). Redeployed 6601 only (7 .eb files, +36 B each, hot-reload). The 1062 lane: unnecessary for the ring; additive-only if ever wanted, seeded by the entry handler, never hardcoded. Flagged: the waystation example will emit corrected bytes on its next build (behavior improves; the deployed 6500 is untouched).
**Re-test:** fresh New Game (no relaunch) → expect the west shore, facing inland, `~ → World` = 9011.

## R2b — THE LANTERN BEACON (2026-07-25/26): the quay marker, playtested through four passes

The quay's visible marker is DEPLOYED + PLAYTESTED: a from-scratch closed lantern-beacon tower
(generator `mint_quay_beacon.py`, 25 siting gates baked in) on the proven building layer — Object mesh
idall 4078, collision = 14 terrain-hull tiles topo-59, anchor (48,−1160.5) with the trigger at its foot
(the ≥1u hull-to-trigger margin and cz ≥ −1160.70 southern limit live in the generator + rebuild script).
En-route: the harbour-gate carry was REJECTED in playtest (embedded water z-fight + single-sided culling —
a carried structure is authored for its stock site) and fully reverted; **the render-only building law is
CONDITIONAL** (a donor-backed/reclaimed cell's Object override IS walkmeshed ahead of Terrain —
`--building-idall 4078` is the fix, doc'd in OVERWORLD_ENGINE.md); locate.py's area→place naming was
refuted (census in `../object-census/`). Full record + undo: REVERT.md §9–11.

**Owner acceptance with one folded-forward item — THE ENTRANCE-FACE LAW:** a symmetric tower makes even
an abutting trigger read as offset, because the trigger IS "the door." **R2 must add a south-face
entrance feature (recessed doorway/lintel/steps) to the beacon generator**; all four quays (including
this one, on its R2 rebuild) pick it up. The beacon + `rebuild_quay_marker.sh` + `--building-idall` are
the reusable kit for the three remaining quays.

## R2 — THE ONE-CASE FERRY ★ DEPLOYED (2026-07-26, playtest pending)

**Site ruling (owner, AskUserQuestion):** the quays are **Ashvale + Tidefall + Grimhorn + Larkspur** — the
judgment's measured dock list. The "four southern-band clusters" prose was unsatisfiable from measurement
(Sandreach is dockless; Larkspur is mid-map): the ferry reads as a ROUTE, not a band. Tidefall's trigger
moved to the rank-2 dock **(420,−1232)** — the design coord (412,−1224) cannot host the doored beacon
(hull crosses the (6,19)/(6,18) seam).

**The build (93 install files, NO relaunch, `FF9CustomMap` untouched; full record REVERT.md §13–16):**
3 new case-53 quay entrances (63 dispatcher files, +3 funcs each, every pre-existing body byte-identical)
+ the doored beacon at all four quays (Ashvale rebuilt restore-first; THE ENTRANCE-FACE LAW satisfied)
+ 4 **east-wall depth-staggered berth alcoves** in 6601 (the lateral 4-door row is REFUTED by projection —
all four lanes land off-painting within 54 px) + per-berth **sign zones** (a placard actor cannot satisfy
the 300u spacing law in a 410u corridor; zones cost nothing) + the Purser moved to the west wall (he stood
inside berth IV's mouth). Sign flags **8760–8763 set EXPLICITLY** — the `[[event]]` default allocates
below `FIRST_SAFE_FLAG` (kit-audit chip filed).

**Laws minted en route:** THE BBOX-CENTRE DRIFT (`--building-at` re-anchors the bbox centre — an
asymmetric mesh slides off its gated anchor; `Site.building_at` publishes the corrected value) · the
trigger-idall invariant is **event/area, never raw equality** (Grimhorn's desert ground makes 16452) ·
the SITES↔hall-arrive duplication is now cross-probed (`probe_quay_sites.py` parses the hall toml —
editing one side can no longer silently half-break the ring).

**A0 dropped (owner disposability ruling):** the Grimhorn horseshoe aux was WIPED by a later island run
(no runnable script; reconstruction = a `world-mountain` re-run through the quay site). Grimhorn ships
without its falls.

**Deferred:** per-quay nameplates (3 dead high AREA cases + 3 block-68 locIds — cosmetic; all four plates
read "Lantern Quay", and one visit names all four via the shared explored bit) · R3 Lamplight · R4 the
forest/encounter pass · R5 the sea lanes.

**Playtest loop:** New Game → hub → hall → read each berth sign → out each berth → land on each shore
facing inland → beacon at the trigger's foot, door facing you → "?" → "Lantern Quay" → re-enter the hall.
No relaunch required (`~ → Reload field` / world re-entry applies everything).

## R2c — THE FERRY LANE (2026-07-26): the berth row superseded by stock's own idiom

**The alcove row FAILED playtest comprehension** ("super clustered... randomly trigger 1 of 2 warps"):
the spawn sat inside berth III's depth band, the sign zones occupied the corridor's CENTER, the warp
zones ate the east half of the walk lane, and the borrowed art paints no doors — **THE INVISIBLE-DOOR
LESSON** (now in the `laying-out-ff9-fields` skill): a layout can pass every spacing warning and still
be unplayable; the probe measures geometry, not comprehension.

**Replaced by the productized `[[ferry]]` kit lane** (owner-ruled): an NPC dialogue-choice worldmap
exit — the Purser asks "Where shall we sail, kupo?", rows for the four ports, a MANDATORY decline arm
appended LAST (bare CANCEL returns the last row). Desugars to the proven `[[choice]]` pipeline; each
destination arm runs the same `worldexit` body as a gateway (both blocks + key 35). The hall now holds
exactly four things — spawn, ledger+savepoint, Purser, and the single restored R1 south-door exit
(home port Ashvale). The Purser moved BACK east: at the west-wall spot the restored door quad reached
him — **re-derive every actor-vs-zone relation after ANY zone reshape** (second instance of the class).
Flags 8760–8763 freed; ring-closure probe parses ferry rows + door vs `SITES` (169 checks). 14 files,
hot. Record: REVERT.md §17.

**R2c fix (2026-07-26):** the Purser softlock root-caused — **THE MOVEMENT-GATE CONTEXT LAW**: a walk-on
region's usercontrol prologue (`ifnot IsMovementEnabled → return`) is NOT portable into a talk handler,
which has already disabled movement — the exit silently bails after the reply window and the player is
frozen with no window. `worldmap_exit_body(gate=)` now context-aware (ferry arms gate=False; gateways
unchanged); lint rejects `dialogue` + `[[ferry]]` on one NPC (was shipping dead text). Hall final form:
spawn + the Purser, ZERO regions — the south door and the ledger/savepoint deleted, saving is the menu's
"Log the passage" row (latched `Menu(4,0)`), decline still LAST. `.eb` 7703→5600 B, 14 files, hot.
Record: REVERT.md §18.

**R2 PLAYTEST CONFIRMED (2026-07-26):** all four ferry choices sail correctly and the Confirm hijack is
gone. En-route casualty: boarding the crimson boat at its islet no longer fires (the range window's true
branch fails in-game) — logged in `studies/custom-vehicle/README.md`, boat DORMANT until R5 by owner
ruling. R2 is CLOSED; next rungs R3 Lamplight · R4 forest pass · R5 sea lanes + proper boarding.
