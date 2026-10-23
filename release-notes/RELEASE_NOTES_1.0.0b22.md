# Dream World IX 1.0.0b22 — play the story together, and a world map that changes with it

**Dream World IX** is a modding toolkit for the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam/GOG FF9).

This update moves co-op from experimental to beta, improves some overworld tools, and adds more .eb script functionality.


## Highlights

### 🎮 Co-op through the story *(BETA, needs engine bundle)*

- **Cutscenes and dialogues sync.** When the host talks to an NPC or uses a save moogle, the scene plays on the guest's screen, and the guest's game follows the host's dialogue and copies their choices.
- **The guest fights from FF9's real battle menu** and sees the victory and reward screens. A dropped connection no longer throws the guest out of the fight: the guest waits up to 40 seconds and resumes the same battle.
- **The guest sees the real attack and spell animations.** Set **They appear as** to **Auto** in the host's Co-op tab and the guest also looks like the party member they command, on both screens — footsteps, held props and lighting included.
- **Both players need the b22 engine bundle.** A b19 game and a b22 game refuse to pair.

Known issues: one unexplained host freeze at a battle start; a following guest has no main menu (by design); after a scripted story battle the guest's lines can run ahead of the host's; monsters that resize themselves in battle show at normal size on the guest. Report issues on the repo, in discord, or to my twitter @GameJawnsInc.

### 🌍 Rewrite the real overworld *(engine bundle)*

- **`world-sink`** turns 43 of disc 1's 49 real islands into open sea, in place — the way disc 4 removes Shimmering Island.
- **Ground that changes with the story** on any cell, not just stock's 26 (`world-forms --arm`), plus buildings and entrances that appear or vanish with it (`--building2`, `--entrance2`).
- **Mountains and forests, reshaped:** any angle (`--rot`), mountains up to twice as tall (`--rock-height`), a new desert peak, four more forest shapes, and forests up to 1.5× wider (`--spread`). 

### 🏡 Fields with memory

- **Persistent tables** (`persist = true`) survive battles and save/load. **`[scene.ledger]`** lets a battle write how it went into a field's saved table, and **`[[behavior.stream]]`** gives seeded dice rolls the build can predict — persisted, a reload can't re-roll them.
- **`[household]`** builds a whole needs-driven life sim from one block; see [`ff9mapkit/examples/household/`](https://github.com/GameJawnsInc/Dream-World-IX/tree/master/ff9mapkit/examples/household).
- **Floor sensors** (`on_floor`, `same_floor`, `other_floor`) let a behavior tree ask which walkmesh floor someone stands on.

### 📸 Photo mode and moving props

- **`[photo]`**: Select freezes the camera, the d-pad pans the painting, R1 hides actors and L1 adds a warm tint.
- **`[[prop]] motion`**: props orbit, shuttle, bob, spin, swing or hover.
- Both are for novel fields (not forks) and need no engine patch.

### 🧵 Forks that ship every language's own script and text *(engine bundle)*

- Verbatim forks no longer give all seven languages the US-English script or swap US and UK text, and battle AI patches land on the right line in every language.
- BG-borrow and `--editable` imports record their donor, so the engine's per-room fixes and the menu's place name apply, and carried objects are lit and shadowed like the real room.
- **`story-trace`** and **`fork-report --trace`** show which script wrote each story flag and where a fork's writes differ from the real game's; the forked opening through Alexandria Castle and a hub-booted Dali morning matched the real game flag for flag. Recording needs the engine bundle and the in-game test harness.

## Also new, and fixed

- **Authoring:** behavior trees can hold a pose, change numbers over time (`adjust`, `[[behavior.drift]]`) and pick a table's lowest or highest entry (`[[behavior.pick]]`). `image-field` re-runs keep your hand-added content, the Floorplan tab imports traced rooms, and Blender add-on 0.9.30 exports multi-floor walkmeshes in the engine's order. New tutorials: [a playable character](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/tutorials/15-playable-character.md), [a custom continent](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/tutorials/16-custom-continent.md), [automated in-game testing](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/TEST_HARNESS.md).
- **Fixed in game:** leaving a kit-built room no longer leaves an "Error Env Play()" window in the next real field; the player exists from the first frame; `[[platform]]` land rides no longer fling the player; a `[behavior]` timer no longer follows you out; overworld seams and entrance triggers hold, and boats no longer sail under reclaimed land.
- **Fixed offline:** concurrent deploys take turns, and a failed one no longer tears down the working deploy; `battle.toml` `[[battle_enemy]]`/`[[battle_patch]]`/`[[battle_attack]]` rows now apply instead of being silently ignored; `import-chain` no longer crashes on a PyPI install; a root `--game` reaches every command; a map-marker rename no longer adds a stray carriage return to every overworld message.

## Engine bundle

**Rebuilt this release:** `dwix-custom-memoria-1.0.0b22.zip`, a from-source build of the full patch stack on the same pinned Memoria base. New since b19: co-op (protocol v14), a fix for stock Memoria leaking memory on every sound effect (the bundle now also replaces `SaXAudio.dll`), story-switching overworld cells, a fix for the `~` warp dragging a countdown along, and a fix for a stock Memoria bug that flooded the log during the New Game opening. An early Journal menu, the in-game test harness and the story-write recorder ride along, all off unless you switch them on; co-op stays off until `[Netsync]` is configured.

**Do you need it?** A **novel** field needs no engine patch. Forks, the overworld mesh verbs and co-op need the bundle. Anyone can rebuild it from `memoria-patches/` ([ENGINE.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/ENGINE.md)).

## Getting started

- **Windows:** grab the installer `.exe` from the release assets — it bootstraps everything, and can optionally install the engine patches (backed-up, version-aware).
- **From PyPI:** `uv tool install "ff9mapkit[gui,assets,save]"` then `ff9mapkit setup`. **Already installed?** `uv tool upgrade ff9mapkit`, then reinstall the engine bundle and the Blender add-on (**0.9.30**).
- [SETUP.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/SETUP.md) has the full walkthrough · every change: [CHANGELOG.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/CHANGELOG.md) · [known issues](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/KNOWN_ISSUES.md).

## Provenance

Dream World IX ships **NO** FINAL FANTASY IX game data. It operates only on a copy of the game **you** already own, reading and patching your local install at build time. Base templates are regenerated from your own install via `ff9mapkit extract-templates`; no Square-Enix bytes are distributed, apart from the small, owner-granted exceptions listed in [PROVENANCE.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/PROVENANCE.md). This is an unofficial, fan-made toolkit and is **not affiliated with, endorsed by, or associated with Square Enix**.

## License

Dream World IX / `ff9mapkit` is released under the **MIT License** (© 2026 GameJawnsInc). The bundled engine patches modify [Memoria](https://github.com/Albeoris/Memoria), which is likewise MIT-licensed (© Albeoris).
