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

## R3 — LAMPLIGHT ISLAND ★ DEPLOYED (2026-07-26, relaunch + teleport-judged playtest pending)

The r44 mint at the reserved case-52 slot, exactly as ratified: `world-island` r44 **seed 44 lobes 1**
at (1432,−1176), block (22,18) — seed MEASURED over 14 dry-runs (zero hard texture defects; outline
r_max 47.1u = 1.07× overshoot vs the allowed 1.57×; west/east channels 43.1/57.3u ≈ the design's 44/60u —
lobes-2 candidates narrowed the west channel to ~30-35u and were REJECTED) · the case-**52** native
entrance, plate **"Lamplight"** (locId 51, explored word 98 bit 3), doored beacon at (1424,−1160.2) with
the trigger at its foot → NEW field **6602 LAMPLIGHT** (BG-borrow L. Castle/Telescope 615, keeper moogle
Moglow, walk-out via the donor's own Region4 quad → arrive (1436,−1168) f192) · beacon kit now
5-site (`rebuild_quay_marker.sh lamplight`; FIELD/NAME/CASE parameterized). All offline gates green:
mint probe + 5-site probe + ring closure ALL PASS both discs; 63 dispatchers additive-only proven; 144
targeted tests. **En-route kit catch: THE NAMEPLATE-WIPE BUG** — `deploy_marker_renames` rebuilt 68.mes
from the BASE text, erasing "Lantern Quay" (any 2nd named entrance wiped the 1st; caught ONLY by the
post-deploy byte check); FIXED to merge with the deployed override + regression test + the standing
`marker_renames.toml` registry. Full record + undo: REVERT.md §21. ONE RELAUNCH required (FieldScene
6602); playtest = §21.10 (teleport to (1432,−1176)).

**R3 fix — THE QUICKSAND CASE + THE VIRGIN NAMEPLATE BAND (2026-07-26, re-playtest pending):** the
§21 playtest hit *battle 144 (Antlion)* at the plate — **case 52 is the overworld quicksand's
hardcoded main-loop branch** (`Byte[24]==52 && Confirm → Battle(0,144)`, before the AREA switch in
all 9 free-roam dispatchers; the real quicksand tag lives in WORLD03/09 cell (38,8)). **THE
QUICKSAND CASE LAW: switch-dead is NOT dead** — the corrected census (switch ∧ main-loop ∧ cell-tags
∧ labels) leaves NO clean surgery slot beyond 53: the ratified "ceiling is 2" was wrong. The robust
replacement: **THE VIRGIN CASE BAND 61–64** — past the stock 61-entry name table AND the base-2×59
AREA switch, yet inside func-0xB's unbounded 49+ explored-bit arm (w98 bits 12–15) and the plate
window. Lamplight now rides **case 61**: the A2 self-summon trigger (prior nameplate research's
verified laws) + explored-bit on the warp branch + a navimap-EXTENDED block-68 (split[61]) — **zero
stock bytes touched** (63 dispatchers = pre-R3 + one added func each, byte-proven; quicksand intact,
its per-language stock labels restored exactly). Named-entrance budget: 1 → 5 (53 + 61-64). Record:
REVERT.md §22; re-playtest = §22.8.

**THE EXTENDED NAMEPLATE BAND ★ DEPLOYED (2026-07-26, owner-directed, plate-sanity pending):** the
5-slot cap was ONE script-side arm (func-0xB's `w98 >> (case−49)` dying past 64) — the engine is
unbounded (verified in FF9TextTool/ETb). The kit now splices func-0xB's 114-byte range-arm section
(63 dispatchers; each file's vehicle-switch tail kept verbatim; WORLD02's Byte[35] var form handled)
with arms for **cases 65–90 ∪ 94–155**, explored bits in kit-reserved words (gEventGlobal bytes
2006–2017, a new flags.py BitRegion + the `[[flag]]` validator now enforces reserved regions).
**Named-entrance budget per world: 5 → 93.** Proofs: the stock-section ORACLE + a 256-case
byte-walking interpreter (168 stock-equivalent, 88 new-band correct) + deploy/idempotence byte
checks; 138 tests. `world-entrance --extend-nameplate-band`; auto-runs on any 65+ deploy. Not
entrance-only: the case space serves per-quay names, plate-only POIs (summon without a warp), and
the explored bits are save-persistent per-place "visited" state any `.eb` can read. Record:
REVERT.md §23.

**PER-QUAY NAMES ★ PLAYTEST CONFIRMED (2026-07-26, "all passing and ?/name status holds over
saves" — the extended band is thereby IN-GAME PROVEN, cases 65-68 live):** the four quays moved
off the shared case 53 onto **virgin cases 65–68** (Ashvale/Tidefall/Grimhorn/Larkspur — the
extended band's first consumers; same Field(6601) destination, per-island explored bits at word
2006 bits 0–3). En route the widened ALL-entries census found **THE AIRBORNE SUMMONER**: WORLD08/09
carry a stock airship-flight func summoning case 54 ("Memoria") and case 53 (pre-reveal '  ???  ')
— so case 53's label was NEVER free and R1's "Lantern Quay" rename had been hijacking pre-reveal
Memoria's disc-4 plate (cosmetic, warp-safe). Fixed fully: split[53] restored to stock per
language, the case-53 switch arm un-repointed to default; **THE ONE-CASE FERRY is retired** — the
ring now uses the virgin band exclusively, and the census law is: a case's summoners live in ALL
entries, not just cell tags. Record: REVERT.md §24.

## R4b — THE TABLE IS THE LAW ★ DEPLOYED (2026-07-26; re-playtest pending): the 36-38 law FALSIFIED in-game, the safe road AUTHORED

The R4 playtest fought Lizard Man/Sand Scorpion/Axe Beak/Ironite on "the grass of the island" —
fingerprinted to **Grimhorn's bench** (carried area 12 → zone 5's topo-16/41 rows; three earlier
hypotheses each killed by data). The "topo 36-38 engine law" is FALSE: `ProcessEncount` has no
topograph clause; the roll resolves **zone × topograph × fog off the walked tile's AREA bits**, and
safety is a TABLE HOLE, not an engine gift (the doc's own 2026-07-02 correction was right; the
design round's "verified" law repeated the misreading). **THE FIX — THE SAFE-ROAD AREA STAMP:**
every kit island's open walkable ground → **area 14 (zone 6**, records only at topos 10/36 — a hole
for all our ground topos); canopy keeps area 0 → zone 0 (Python/Goblin/Mu = the region's uniform
fauna); event tiles untouched; 85,236 verts across 112 Terrain files, byte-verified area-bits-only,
full parity, all probes pass. Area choice is cosmetically free (WorldLocationText's only gameplay
caller is the debug title). Ragtime Mouse in canopy = the stock forest special, kept. ⚠ flagged:
the horseshoe carry's 270 STOCK event verts (area 12) — a future audit item. New mints must re-run
the stamp until the kit emitters default it (deferred: identity-net rebaseline). Record: REVERT.md
§26; re-playtest = §26.5.

## R4 — THE FOREST/ENCOUNTER PASS ★ DEPLOYED (2026-07-26; relaunch for the minimap; teleport playtest pending)

The encounter architecture costs ZERO table edits: our tiles' **area 0 → zone 0**, whose topo-37
rows are the stock starter set (**Python/Goblin/Mu**, both fog rows) — we consume the stock table,
never edit it (the corrected census REFUTED the "private zone 24": area 63 = the Yan island's live
table; NO stock-dead 36-38 record exists anywhere). The law verified in-engine: no record ⇒ no
battle + the case-205/EventCollision topo-36-38 gates — open ground is the safe road by
construction. **THE SMALL-HOST LIMIT (measured):** every ring island refuses v1 `world-forest`
(the junction CARRY fails the hole-cycle; r44-class mints fail THE CANOPY STEP LAW with a
degenerate zip, `zipNyMin 0.00`) — route-island canopy awaits the verb's small-host calibration.
**THE BENCH** (island E re-homed per the ratified sketch): seed **137** at (136,−168) — found by a
driver testing hard-clean texture gates AND blob capacity together — carries the proven 132-tri
canopy at (124,−156) (all gates + walk-in sim clean; **donor AREA 7 restamped to 0** — a verbatim
canopy carry imports the donor's encounter zone; restamp to the host's area, now a recorded law)
+ the r13/h3.6 south-lobe hill + the minimap redraw. The region's first encounter island. Record:
REVERT.md §25; playtest = §25.6.

**R3 PLAYTEST CONFIRMED (2026-07-26, "good"):** the case-61 loop works in-game — plate → Confirm →
the lamp room → walk out → the name registers; no battle. The quicksand leg (§22.8 item 4) was not
in-game checked (no Cleyra-era save available) and doesn't need to be: its branch, cell tag, and
per-language labels are byte-identical to stock in every dispatcher — our deploy has nothing left
that could touch it. **R3 is CLOSED.** Next rungs: R4 the forest/encounter pass (carve_forest per
the encounter law; island E's re-site at the free r96 pocket (136,−168)) · R5 the sea lanes +
proper boat boarding.
