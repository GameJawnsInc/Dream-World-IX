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

## Rung 1b — THE SAIL (NEXT)

The ship runs a ship-relative waypoint `WalkXZY` lane while the aim rides it (per-frame
re-pin, stock entry-2 shape) — the camera tracks a moving subject; fold the eye dolly
back in. Also owed here: hide/park the player during the shot if the scene calls for it.

## Rung 1c — THE HANDSHAKE

A `Byte[26]`-style state machine + fade + restore/`Field()` — a complete self-contained
mini-scene (the fade also masks the return tween).

Rung 2 (design, owner input wanted): wire the proven scene into the ring's ferry UX — the
diegetic candidates are a DEPARTURE scene (sail-away after boarding at the hall), an
ARRIVAL scene (the ship sails in as the player lands at a quay), or a watch-from-shore
vignette. Stock separate-world scenes (a custom EventDB world id) stay a fallback if
in-9011 proves cramped.
