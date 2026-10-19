# Dream World IX 1.0.0b20 — play the story together, and a world map that changes with it

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* content — and faithfully forking the real game — for the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam/GOG FF9). Ten weeks after b19, two players can go through the story together *(experimental)*: the guest follows the host's conversations and fights from FF9's real battle menu. The overworld tools can now sink real islands and make ground, buildings and entrances change with the story. Fields gain memory that survives a save, and verbatim forks now ship each language's own script and text.

*Proof labels:* **playtested** = played by the maintainer · **proven in game** = checked in the running game by the automated test harness · **tested offline** = built and tested, not yet run in game.

**Upgrading? Read these first:**
- **Engine bundle users: install the new bundle.** Co-op partners must update together (protocol v11 → v14; mixed versions refuse to pair). `--ghost-as` is now the host's setting; guests leave theirs off.
- **Re-import forks made before this release** so each language gets its own script and text (campaigns: `ff9mapkit fetch-assets --force`) and BG-borrow/`--editable` forks pick up their donor's engine fixes. Re-importing rewrites `field.toml`, so save hand edits first.
- **Rebuild your fields.** Actors now cast FF9's blob shadow (`shadow = false` opts out). Some tomls b19 accepted now stop with an error that names the fix: a shadow `intensity` above 15, a field id in 9000–9012 or below 4000, a `.bgi` not grouped by floor, a `[behavior]` with no unit or on a verbatim fork.
- **Overworld:** in-place edits now stack (`--fresh` starts over); new land is a battle-free area, not area 0; `world-environment` replaces what lower folders set for a place (`stack = "combine"` keeps the old way); writers refuse cells another deploy owns (`--allow-overwrite`). `world-encounter-rate` only ever changed the Ragtime Mouse — the battle rate is `world-encounter-frequency`.

## Highlights

### 🎮 Co-op through the story *(experimental, engine bundle)*

- **Conversations play in step.** When the host talks to an NPC or uses a save moogle, the scene plays on the guest's screen and the host's presses turn the pages. *(playtested on two PCs)*
- **The guest fights from FF9's real battle menu** and sees the victory and reward screens. A dropped connection no longer throws the guest out of the fight: the guest waits up to 40 seconds and resumes the same battle. *(playtested on two PCs with 6- and 20-second drops)*
- **The guest sees the real attack and spell animations** *(playtested with two game windows on one PC)*, and with `ff9mapkit coop host --ghost-as auto` **appears as the party member they command** — footsteps, held props and lighting included. *(proven in game)*

Known issues: one unexplained host freeze at a battle start; shops untested on two PCs; a following guest has no main menu (by design); after a scripted story battle the guest's lines can run ahead of the host's.

### 🌍 Rewrite the real overworld *(engine bundle)*

- **`world-sink`** turns 43 of disc 1's 49 real islands into open sea, in place — the way disc 4 removes Shimmering Island — and a boat can sail where it stood. `world-minimap` erases the sunk land from both painted maps. *(proven in game)*
- **Ground that changes with the story** on any cell, not just stock's 26 (`world-forms --arm`), plus buildings and entrances that appear or vanish with it (`--building2`, `--entrance2`). The change shows on the next world load, such as a field visit or a battle. *(proven in game)*
- **Mountains and forests, reshaped:** any angle (`--rot`), mountains up to twice as tall (`--rock-height`), a new desert peak, four more forest shapes, and forests up to 1.5× wider (`--spread`). *(playtested)*

### 🏡 Fields with memory

- **Persistent tables** (`persist = true`) survive battles and save/load. **`[scene.ledger]`** lets a battle write how it went into a field's saved table, and **`[[behavior.stream]]`** gives seeded dice rolls the build can predict — persisted, a reload can't re-roll them. *(proven in game)*
- **`[household]`** builds a whole needs-driven life sim from one block; see [`ff9mapkit/examples/household/`](https://github.com/GameJawnsInc/Dream-World-IX/tree/master/ff9mapkit/examples/household). *(proven in game; feel not yet playtested)*
- **Floor sensors** (`on_floor`, `same_floor`, `other_floor`) let a behavior tree ask which walkmesh floor someone stands on. *(proven in game)*

### 📸 Photo mode and moving props

- **`[photo]`**: Select freezes the camera, the d-pad pans the painting, R1 hides actors and L1 adds a warm tint. *(playtested)*
- **`[[prop]] motion`**: props orbit, shuttle, bob, spin, swing or hover; `ff9mapkit motion` previews the path. *(proven in game)*
- Both are for novel fields (not forks) and need no engine patch.

### 🧵 Forks that ship every language's own script and text *(engine bundle)*

- Verbatim forks no longer give all seven languages the US-English script or swap US and UK text, and battle AI patches land on the right line in every language. *(tested offline; not yet played in another language)*
- BG-borrow and `--editable` imports record their donor, so the engine's per-room fixes and the menu's place name apply, and carried objects are lit and shadowed like the real room. *(proven in game)*
- **`story-trace`** and **`fork-report --trace`** show which script wrote each story flag and where a fork's writes differ from the real game's; the forked opening through Alexandria Castle and a hub-booted Dali morning matched the real game flag for flag. Recording needs the engine bundle and the in-game test harness. *(proven in game)*

## Also new, and fixed

- **Authoring:** behavior trees can hold a pose, change numbers over time (`adjust`, `[[behavior.drift]]`) and pick a table's lowest or highest entry (`[[behavior.pick]]`) *(proven in game)*; `image-field` re-runs keep your hand-added content, the Floorplan tab imports traced rooms, and Blender add-on 0.9.30 exports multi-floor walkmeshes in the engine's order *(tested offline)*. New tutorials: [a playable character](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/tutorials/15-playable-character.md), [a custom continent](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/tutorials/16-custom-continent.md), [automated in-game testing](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/TEST_HARNESS.md).
- **Fixed in game:** leaving a kit-built room no longer leaves an "Error Env Play()" window in the next real field; the player exists from the first frame; `[[platform]]` land rides no longer fling the player; a `[behavior]` timer no longer follows you out; overworld seams and entrance triggers hold, and boats no longer sail under reclaimed land. *(proven in game)*
- **Fixed offline:** concurrent deploys take turns, and a failed one no longer tears down the working deploy; `battle.toml` `[[battle_enemy]]`/`[[battle_patch]]`/`[[battle_attack]]` rows now apply instead of being silently ignored; `import-chain` no longer crashes on a PyPI install; a root `--game` reaches every command; a map-marker rename no longer adds a stray carriage return to every overworld message. *(tested offline)*

## Engine bundle

**Rebuilt this release:** `dwix-custom-memoria-1.0.0b20.zip`, a from-source build of the full patch stack on the same pinned Memoria base. New since b19: co-op (protocol v14), story-switching overworld cells, a fix for the `~` warp dragging a countdown along, and a fix for a stock Memoria bug that flooded the log during the New Game opening. An early Journal menu, the in-game test harness and the story-write recorder ride along, all off unless you switch them on; co-op stays off until `[Netsync]` is configured.

**Do you need it?** A **novel** field needs no engine patch. Forks, the overworld mesh verbs and co-op need the bundle. Anyone can rebuild it from `memoria-patches/` ([ENGINE.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/ENGINE.md)).

## Getting started

- **Windows:** grab the installer `.exe` from the release assets — it bootstraps everything, and can optionally install the engine patches (backed-up, version-aware).
- **From PyPI:** `uv tool install "ff9mapkit[gui,assets,save]"` then `ff9mapkit setup`. **Already installed?** `uv tool upgrade ff9mapkit`, then reinstall the engine bundle and the Blender add-on (**0.9.30**).
- [SETUP.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/SETUP.md) has the full walkthrough · every change: [CHANGELOG.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/CHANGELOG.md) · [known issues](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/KNOWN_ISSUES.md).

## Provenance

Dream World IX ships **NO** FINAL FANTASY IX game data. It operates only on a copy of the game **you** already own, reading and patching your local install at build time. Base templates are regenerated from your own install via `ff9mapkit extract-templates`; no Square-Enix bytes are distributed, apart from the small, owner-granted exceptions listed in [PROVENANCE.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/PROVENANCE.md). This is an unofficial, fan-made toolkit and is **not affiliated with, endorsed by, or associated with Square Enix**.

## License

Dream World IX / `ff9mapkit` is released under the **MIT License** (© 2026 GameJawnsInc). The bundled engine patches modify [Memoria](https://github.com/Albeoris/Memoria), which is likewise MIT-licensed (© Albeoris).
