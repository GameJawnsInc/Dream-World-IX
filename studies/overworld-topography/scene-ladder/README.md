# The scene ladder — scripted world objects → world cutscenes

Reopened 2026-07-28, directly unblocked by the F2/9001 flight-scene fix (s64: the overworld
self-heal is hard-gated out of cutscene worlds + an actEye/actAim rig scan protects CUSTOM
scripted scenes). The ladder spends two bodies of decoded knowledge:

- the scripted-object lane trace — `../WORLD-SCRIPTED-OBJECT-LANE-2026-07-25.md` (THE INDEX
  RULE + THE ANIMATION RULE; the `3DModel` + `.eb` entry-add mechanics);
- the F2 world-scene decode — the full 9001 mechanism (the 0xB7/0xB8 EYE/AIM rig camera,
  waypoint `WalkXZY` chains, the `Byte[26]` scene handshake, white fade → `Field()`), record
  in memory `project-ff9-faithful-opening` §"THE 9001 FLIGHT-SCENE BUG".

## Rung 0 — the decorative static ★ CLOSED (2026-07-28, owner: "reads right")

`rung0_quay_ship.py` — the Lantern Ferry's first visible vessel: STOCK model 313 + stock
idle 5106 (the WORLD11-entry-11 pairing) moored off the Lantern Quay's west shore, bow to
the quay. WORLD11 entry 16 (all 7 languages, each patched from its own bytes), armed from
Main_Init after the boat. Both lane laws held on the first deploy; the world tick stayed
alive (plate/HUD/minimap live, the Crimson Narciss unaffected); no mint, no DictionaryPatch
line, **no relaunch** (a stock model needs none — only a minted `3DModel` id registers at
launch). Two-round siting: (18,−1168) read "out in the sea" → re-moored **(29,−1168)**,
~5.5u off the waterline (offline transect: sea to x≤34, topo-58 wall at 35, grass y=3 from
36). Iterate: `--pos X,Z --y FP --face BYTE --deploy` (hot; world re-entry reloads).

## Rung 1a — THE RIG PROOF ★ CLOSED (2026-07-28, six rounds, probe-verified)

`rung1a_rig_proof.py` — the first custom camera rig on the overworld, in-place in 9011:
proximity+Confirm at the ship (case-machine-idle gated) → control lock → eye/aim rig
entries arm → the composed shot (eye 17u WSW of the ship at +6u, aim ON the ship; ship
center-frame, player + beacon behind) → 4s hold → `op_1C` disposal → chase returns.
Probe-verified end state: `WEye=(780.0,6.2,-670.0)` epoch-frame, CAM beside it, the
return tween a short local ease. The road there minted the ladder's core law set:

- **THE RESTORE**: nothing clears `actEye/actAim` — designation lives while a flagged
  actor is ACTIVE; `op_1C` (TerminateEntry, non-self → `DisposeObj`) is the release.
- **THE AIM-DRAG TRAP → s66**: with an AIM rig armed, `ff9.cs` dragged `w_moveActorPtr`
  onto the camera-aim var every frame — stock only ever drags the inert dummy; a
  controlled player got teleported (the (797,−656) ejection = the ship's RENDER pos).
  s66 gates the drag to the dummy.
- **THE WRAP-EPOCH LAW → s68**: the world draws in a wrap epoch that shifts with seam
  traversals; actor TRANSFORMS are kept epoch-correct (`SetAbsolutePositionOf`) but
  `ProcessEvents` published the rig camera from canonical `actor.pos[]` → the camera
  landed ~a half-map from the streamed world. s68 publishes from the wmActor transform
  (canonical fallback; stock scenes load fresh → identical). Corollary: author runtime
  world positions SHIP-RELATIVE off a live actor's `f[]` (the stock rig idiom) — never
  absolute constants (only world-load-time arming may use those; the rung-0 ship does).
- **THE ARG2 Y-DOMAIN**: `MoveInstantXZY`/`WalkXZY` arg2 negates into `pos[1]`, and the
  `f[1]` READ negates too — pass-through cancels (stock's aim), constants encode UP as
  `(-h*256)&0xFFFF`, and an inline read-modify-write UP offset SUBTRACTS.
- **THE STOCK-SHAPE lesson**: every deviation from stock WORLD01's rig shape (absolute
  coords, plus-signed lift) cost a playtest round; the shape was load-bearing throughout.

Instrument: `memoria-patches/s67-rig-probe.patch` (fires while any rig is armed, any
world + a 90-frame tail; reads BOTH position domains and the REAL render camera =
`WMWorld.MainCamera`). **KEPT LIVE for rung 1b** — remove when the sail rung closes.

## Rung 1b — THE SAIL ★ CLOSED (2026-07-28, two rounds; video-verified)

`rung1b_sail.py` — the camera tracks a moving subject: Confirm → the composed shot → the
ship comes about and sails 40u due south at speed 60 with the aim re-pinned per frame and
the eye dollying in → returns, snaps onto the mooring facing the quay → control back
(owner video: full arc + re-moor + chase restore). Round 1 SOFTLOCKED and minted two laws:

- **THE CARROT LAW**: a blocking `WalkXZY` RE-READS its argument expressions every frame —
  a self-relative target recedes with each step and the walk never terminates. THAT is why
  stock caches ship-relative targets into Instance vars before walking. Walk targets are
  CONSTANTS (canonical constants are frame-correct — `RealPosition` is the engine's
  absolute tracker; probe-confirmed `pos[]` stays canonical).
- **THE RIG-RADIUS LAW**: `EventCollision.Collision` mode 0 (MoveToward's call) BYPASSES
  the tag-2/3 candidacy gate — every cid-4 actor is a radius candidate. The aim, re-pinned
  onto the hull at distance ~0, collided every frame; MoveToward reverted the transform
  and the per-frame writeback mirrored the revert into `pos[]` (probe: the ship
  oscillating ±one step forever while the eye's dolly 17u away completed cleanly). Rigs
  are camera hardware, not bodies: `SetObjectLogicalSize(0,0,0)` on rigs + scenery ship.

**Known polish item (diagnosed, deferred — owner's call whether to spend an engine round):**
the scene reads slightly juddery vs free-roam. Frame analysis of the owner's 60fps capture:
the world simulates at WorldTPS≈28 → 2:3 pulldown; the smoother lerps the camera between
ticks but screen velocity still varies per frame, and script `SetPosition` motion is
teleport-class to the smoother. Stock scene worlds (9001) ride the same machinery — this
matches stock-scene fidelity; free-roam is the smoother's tuned path. s69 candidate:
SmoothFrameUpdater_World treatment of rig-driven cameras + script-moved actors. Cheap
scene-side mitigation meanwhile: slower pans / farther eye (smaller per-tick steps).

## Rung 1c — THE HANDSHAKE ★ CLOSED (2026-07-28, two rounds; owner: "clean and repeatable")

`rung1c_handshake.py` — the complete self-contained mini-scene: the fade bracket masks
both camera cuts AND the post-scene chase ease (all behind black), and the phase byte
(Map.Byte[50], free per the used-census 24-42) carries the director→cast handshake — the
EYE's dolly waits on phase 1, the stock Byte[26] idiom. Round 1 hardlocked on a stuck
white screen and minted:

- **THE FADE SEMANTICS**: `FadeFilter` = WIPERGB 0xEC → `SceneDirector.InitFade((mode&2)
  ? Sub : Add, frames, CMY)`. The dominant ×65 form `(2,24,0,255,255,255)` SUBTRACTS full
  white = fade to BLACK (stock brackets scenes through black); mode-0 full white is an
  ADDITIVE WASH that HOLDS (the ×11 flash form — NOT a fade-in); the restore is the ×18
  `(3,16,0,0,0,0)` form — subtract zero, lerp the filter to nothing. **The lesson: a
  census without the HANDLER is pattern-matching, not semantics — read the case first**
  (the F2 record's "white fade" phrasing was the same misread).

**RUNG 1 IS COMPLETE**: trigger → rig camera → tracked motion → phases → fades → restore,
all in-place in a free-roam world, repeatable, on stock scene idioms + s66/s68. (The s67
probe was removed and the Memoria.Prime x64 copy trued at the 2026-07-29 closed-game
build — the patch file remains re-appliable history.)

Rung 2 (design, owner input wanted): wire the proven scene into the ring's ferry UX — the
diegetic candidates are a DEPARTURE scene (sail-away after boarding at the hall), an
ARRIVAL scene (the ship sails in as the player lands at a quay), or a watch-from-shore
vignette. Stock separate-world scenes (a custom EventDB world id) stay a fallback if
in-9011 proves cramped.

## Rung 2 — THE DEPARTURE ★ 2a+2b CLOSED (2026-07-28, owner: "it works")

The ferry is a voyage. **2a** (`rung2a_departure.py`, three rounds): the pending-port code in
`Global.Byte[1872]` (`flags.FERRY_DEPART_BYTE`, the kit-world-flags band) auto-fires the
sail-away on world entry — player show-bit-hidden with the anchor's foot arm parked
(**THE DISPATCH LAW**, v11: `Global.Byte[190]` is the world's DefinePlayerCharacter dispatch —
0 = the anchor, 7 = the Narciss, an UNCLAIMED value = no controlled player = the black-screen
brick; park the anchor's own stock latch `Map.Byte[37]=1` instead, restore 0 at close), the
1c scene sails OUT only and the
ship rides THROUGH the closing fade (leg split around the FadeFilter — the blocking-walk
idiom), then behind black: re-moor, rig disposal, the anchor's per-port tags 61-64 snap the
player to the chosen shore at its PROBED ground height (round 1 buried the player: a wrong
scripted y is not rescued by the ground snap), unhide, reveal. The code pre-clears — no save
can replay-loop. **2b** (`dc1263bd`): the kit ferry lane's departure arms (`depart_code` +
`stage_arrive`, lint-guarded, FORMAT.md) — the hall's four ports write codes 1-4 and stage
at the Lantern Quay. (Ashvale first shipped as a plain no-voyage home-port arm; the owner
read that as a silent warp with the wrong moogle line — ALL ports sail now, code 1.)

**The entry seam — CLOSED (owner-confirmed):** the ~1s of standing at the Ashvale shore and
the "camera snap" after the hall→world transition were both the same artifact — the visible
free-roam entry before the scene owned the frame. Gone with the v5-v11 ladder (Main_Init
prologue black + rigs arm at construction, navi disarm, show-bit hide under the parked
`Map.Byte[37]` latch). No open scene items remain on the ladder.

**The ladder's arc complete: rungs 0 → 2b in one day** — a decorative static became a rig-
tracked, phase-coordinated, fade-bracketed cinematic voyage wired into shipped ring UX, on
two engine fixes (s66/s68), one instrument (s67, since removed), and ten in-game-earned laws.

## Rung 3 — THE ARRIVAL ★ v2 OWNER-CONFIRMED (2026-07-29, "good, moves during destination cutscene")

`rung3_arrival.py` (supersedes 2a's teleport-close; deploy on top of the v11 world) — the
voyage's second half: behind the departure's closing black the whole theater relocates to
the chosen port (ship to probed approach waters, hidden player ashore, rigs re-armed, the
EYE placed per port via **`MoveInstantXZYEx` 0xAD** — ORDER LAW: `InitObject`'s tag-0 runs
on LATER frames, so an Ex override of a fresh rig must sit after an `op_22` settle), then
reveals the ferry sailing in and docking before the final black hands over ashore. The ship
STAYS DOCKED at the destination (Main_Init re-moors home on next world load). Lanes + every
camera point probed offline (`probe_arrival_lanes.py`, all-wet verdicts at all 4 ports).
**v2 (the owner's framing notes):** the theater moved CLOSE-IN — approach 20u off the dock,
tight 3/4-astern eye (8/8/+7u) so ship AND shore sit inside the ~45u world fog (the v1 shore
at ~56u read as empty ocean) — and the reveal fade no longer blocks, so the ship is under
way as the black lifts (the departure's own no-wait-fade trick at the other end).

## Rung 3c — ORIGIN-PORT DEPARTURES ★ CLOSED (2026-07-29, owner-confirmed: all four ports stage at the boarding quay; minimap bracket clean both ways after the s69 relaunch)

`rung3c_origin_departure.py` (supersedes rung 3's director + prologue; deploy on top) — the
voyage's first half stops assuming Ashvale: the departure theater stages at the port the
player boarded from, sailing the ARRIVE lanes in REVERSE (dock → 28u → fade → 40u into fog,
the proven Ashvale leg-split generalized; `probe_departure_lanes.py`, all out-lanes + the
12u-out/14u-abeam eyes WET at all four ports). Fully symmetric: leave from where you
boarded, arrive where you booked. Same-port bookings play out-and-back at one quay.

**THE BANKED DESIGN HAD A LATENT FLAW, found at build time:** it read the anchor's saved
world position (`Global.Int24[64]/[69]`) in the departure prologue — but the ferry arm's
STAGE PRESET (worldexit `arrive_writes` → the Lantern Quay) overwrites those vars in the
hall, before the world ever loads. The classifier would have read (60,−1168) every voyage
and silently classified Ashvale — a no-op indistinguishable from working. The repair is
hall-side: the kit's depart arm now caches `Global.Int24[64]` (the mirror record of where
the player STOOD entering the hall, intact all through the visit) into
`Global.Int24[flags.FERRY_ORIGIN_X_INT24]` (=1873, the kit-world band's last 3 bytes)
BEFORE the preset — `content/choice.py`, lint-covered by `test_ferry_lane.py`, hall 6601
rebuilt + redeployed (label-normalized structural diff vs live = exactly the 4 cache
writes). Dropping the preset instead was REJECTED: the canonical New-Game path (hub → hall,
never on the world) would spawn at garbage coords — the actor-brick class.

**The classifier** (prologue, `Map.Byte[52]`): X-only box tests, `|x − quay_x| < 64u`
against the quay trigger sites (420/1204/700 for ports 2/3/4; 48 falls to the default) —
X alone separates all four quays, and 0/garbage/stale-non-quay values default to port 1 =
today's exact behavior. The design's flagged risk — signed compares on negative Int24 —
is RESOLVED SOUND from engine source (EBin.cs:1858: the Int24 read sign-extends via an
SByte cast; B_MINUS/B_LT are signed Int32), and moot here since X is always positive.

**Staging discipline:** the origin theater relocates behind the prologue's held black —
ship → origin dock at moor face, HIDDEN ANCHOR → origin shore (tags 61-64: rung 3 never
played a theater away from the anchor; streaming/epoch caution), rigs disposed + re-armed
so their ship-relative init lands at the new dock (an `op_22(2)` first lets the
prologue-armed rigs finish constructing before disposal), eye overridden per port
(`MoveInstantXZYEx` after the settle — THE ORDER LAW), reveal, hold 30, come about, sail.
The arrival half is rung 3 verbatim. Origin 1 reproduces the owner-confirmed Ashvale
departure (same dock/legs/speed; the eye moves to the probed (15,−1180)).

**THE MINIMAP BRACKET (v2, from the first playtest — voyages confirmed at all four ports;
the minimap was the one bug set):** leaving with the minimap CLOSED arrived to an INERT
minimap at the wrong screen position; leaving it OPEN re-armed fine but showed through both
cutscenes. One root cause, engine-grounded: `RunWorldCode(2,x)` → `SetMinimapVisible` toggles
the panel but syncs the HUD state machine ONLY on world 9005 (upstream Fix #670's narrow
scope), and `WorldHUD.Update()` lays out / animates the minimap only while
`currentState == HUD` — so the close's `(2,1)` activated an unmanaged panel (inert, prefab
position), while the open case showed through the scenes because the HUD's DEFERRED `Show()`
re-activates the panel per `ff9.w_naviMode` AFTER the prologue's `(2,0)`. Fix, two halves:
**s69** (`memoria-patches/s69-minimap-visible-state.patch`) generalizes Fix #670 — state sync
on every world, guarded to the two HUD states so FullMap is never yanked; **the v2 script
bracket** caches `Global.Byte[100]` (keventNaviModeNo, the persisted navi mode the world
init seeds `w_naviMode` from and the Select toggle commits back to) into `Map.Byte[53]`,
zeroes both it and `w_naviMode` (`RunWorldCode(4,0)`) in the prologue so the deferred Show
keeps the panel closed for the whole voyage, and restores + conditionally re-opens
(`(4,1)`+`(2,1)`) behind the final black ONLY if it was open at boarding. The bracket
REQUIRES s69 (without it the close re-open itself goes inert). DLL backup `20260729-080314`.

Revert: `py rung3_arrival.py --deploy` (world) + `backups/scene-ladder/EVT_LANTERN_HALL.*`
(hall) + `py tools/restore_memoria_dll.py 20260729-080314` (engine). Without the hall
redeploy the cache byte stays 0 and every departure classifies Ashvale — the pre-3c
behavior, gracefully.
