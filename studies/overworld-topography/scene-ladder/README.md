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

## Rung 1 — the scripted world scene (NEXT)

Prove the 9001 scene mechanism on OUR content, in-place in dispatcher 9011 (no new world
id needed — the rig ops are plain `.eb`, dispatcher-agnostic; s64's rig scan covers it).
Incremental sub-rungs, one piece per playtest:

- **1a THE RIG PROOF**: lock control, arm invisible eye/aim rig entries (op 0xB7/0xB8) that
  frame the anchored ship, hold, restore. Replicates stock's camera slaving minimally.
- **1b THE SAIL**: the ship runs a waypoint `WalkXZY` lane while the aim rides it — the
  camera tracks a moving subject.
- **1c THE HANDSHAKE**: a `Byte[26]`-style state machine + fade + restore/`Field()` — a
  complete self-contained mini-scene.

Rung 2 (design, owner input wanted): wire the proven scene into the ring's ferry UX — the
diegetic candidates are a DEPARTURE scene (sail-away after boarding at the hall), an
ARRIVAL scene (the ship sails in as the player lands at a quay), or a watch-from-shore
vignette. Stock separate-world scenes (a custom EventDB world id) stay a fallback if
in-9011 proves cramped.
