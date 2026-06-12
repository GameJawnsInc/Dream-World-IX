# World Hub — a playable journey selector (MVP scaffold)

A **World Hub** is a playable field that lets the player pick which **journey** to play, then warps them
in. A *journey* = a complete playable arc (one or more chained campaign slices). The hub's only job is
**select → (optionally seed) → warp**; it's decoupled from journey internals — it needs only
`{name, entry field id, optional seed}` per row. It is **NOT** a custom worldmap (no engine fork — just a
field + a dialogue-choice menu + warps). See the deep notes in memory `project-ff9-world-hub`.

This scaffold has three fields:

| File | Id | Role |
|---|---|---|
| `hub.field.toml` | 4500 | The hub. Walk as a Moogle, talk to Stiltzkin → a journey menu. |
| `journey_one.field.toml` | 4501 | A trivial destination (Black Mage Village backdrop). |
| `journey_two.field.toml` | 4502 | A trivial destination (Treno backdrop). |

## How it works

- **Moogle PC** — `[player] model = 199` re-skins the field avatar to a Moogle (the new `[player] model=`
  option; movement clips auto-resolved via the Info Hub model→animation join). Control ≠ party — the party
  menu is unchanged; the Moogle is just who you *walk* as.
- **The menu** — a normal `[[npc]]` (Stiltzkin) + `[[choice]]`. Each option has `warp = <entry id>` (the new
  choice **warp action**) and optionally `set_scenario`. Picking a row plays the transition sound and
  `Field()`s into that journey — grounded in real FF9 talk-handler warps (the Dali innkeeper, the airship).
- **One-way** — to switch journeys, start a New Game (which will land back on the hub once the New-Game
  override is wired — a follow-up).

## Setup (provenance: you supply the game bytes)

The backdrops BG-borrow real FF9 rooms, so each field needs that room's **camera**, extracted from *your*
install (the repo ships zero game data — `*.bgx` is gitignored here). Extract the three cameras once:

```bash
# from the kit root (ff9mapkit/)
py - <<'PY'
from pathlib import Path; from ff9mapkit import extract; import tempfile, shutil
for fid, name in [("950","camera_hub.bgx"), ("1463","camera_j1.bgx"), ("1908","camera_j2.bgx")]:
    t = Path(tempfile.mkdtemp()); extract.extract_field(fid, t)
    shutil.copyfile(t/"camera.bgx", Path("examples/world_hub")/name)
PY
```

## Deploy + playtest the loop

The three fields use distinct ids (4500/4501/4502 — EventDB is global), so deploy each:

```bash
py tools/deploy_field.py examples/world_hub/hub.field.toml         --id 4500
py tools/deploy_field.py examples/world_hub/journey_one.field.toml --id 4501
py tools/deploy_field.py examples/world_hub/journey_two.field.toml --id 4502
```

Then **relaunch once** (to register the three new ids), and in-game:

1. **F6 → Warp → 4500** (the hub).
2. You're a Moogle. Walk to **Stiltzkin** and talk.
3. Pick **The Black Mage Village** or **Treno** → you should warp into that field (the arrival NPC confirms).
4. **Stay here** closes the menu without warping.

That's the **select → seed → warp** loop. (New Game → hub, and a real forked-slice journey, are the next
steps — see below.)

## What's a scaffold vs a real hub

- **Scaffold (this):** hand-authored, trivial destinations, reached via F6 → Warp.
- **Real hub (next):** (a) retarget the **field-70 New-Game override** to 4500 in the highest mod folder so
  New Game lands here; (b) point each journey at a real `import-chain --verbatim` slice (story_flags' lane)
  with its own `[startup]`/`[party]` so it boots in the right beat with the right party; (c) a `[[journey]]`
  block + a generator (`journeys.toml` → the hub) so journeys auto-appear ("hardcoded MVP → generator").

## Placement

Spawn / NPC coordinates are confirmed **in-game** (per the kit's hard constraint — the camera/walkmesh are
the borrowed field's). The player spawns use each room's real player spawn (guaranteed on-floor); nudge the
narrator if it lands off the walkmesh.
