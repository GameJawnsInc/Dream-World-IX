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
