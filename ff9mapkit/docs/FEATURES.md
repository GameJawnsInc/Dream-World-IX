# What `ff9mapkit` can do

The complete capability list. Most of this was, before this toolkit, either impossible without
hand-editing binaries or outright unsolved in the FF9 modding community. Everything marked **✓** has
been verified **in real gameplay** (not just compiled); **◐** is offline-validated (builds + passes the
codec/golden tests) with the full in-game pass still pending.

> New here? Start with the [README](../README.md) quickstart, then [PIPELINE.md](PIPELINE.md) for the
> full authoring walkthrough. This page is the bird's-eye view of *everything*.

---

## Before this toolkit vs. now

| | Before | With `ff9mapkit` |
|---|---|---|
| **Brand-new field** | No shipped FF9 mod had minted one; HW's "Export as Custom Field" produces a broken atlas and corrupts the script when adding entries | Mint a new field ID from a declarative `field.toml`, on a **stock Memoria install** |
| **Camera angle** | The in-game FieldCreator's 5-point solver is mathematically degenerate for a flat floor — no novel angles | Author **any** pitch/yaw/FOV from scratch (the projection was reverse-engineered) |
| **Background art** | Align by trial and error | A **pixel-accurate paint guide** for your exact camera; depth layers + occlusion |
| **Walkmesh** | Hand-author binary, or the editor's unreliable neighbor links | Model in Blender → `.bgi`, **or import a real field's** and reshape it (multi-floor, seam-preserving) |
| **Event script (`.eb`)** | Hex-edit PSX-style bytecode by hand; HW can't add entries | Declarative NPCs / dialogue / gateways / encounters / events / cutscenes, injected byte-exactly |
| **Starting point** | From zero | **Fork any of ~670 real fields** — camera, walkmesh, art, *and* its exits/encounters/music |

---

## Fields

| Capability | | Docs |
|---|---|---|
| Mint a brand-new field ID (declarative `field.toml` → drop-in mod) | ✓ | [PIPELINE](PIPELINE.md), [FORMAT](FORMAT.md) |
| BG-borrow: render a real field's art/walkmesh/camera under your own script | ✓ | [ENGINE](ENGINE.md) |
| Editable custom scene: ship your own art (per-depth layers, occlusion preserved) | ✓ | [PIPELINE](PIPELINE.md) |
| Import / fork any real field (`import`) — camera + walkmesh + art | ✓ | [PIPELINE](PIPELINE.md) |
| …and extract its **exits, encounters, field BGM, movement** from the script | ◐ | [FORMAT](FORMAT.md) |
| Runs on **stock Memoria** — no engine fork required | ✓ | [ENGINE](ENGINE.md) |

## Camera

| Capability | | Docs |
|---|---|---|
| Author any angle from scratch (pitch / yaw / FOV / distance) | ✓ | [PIPELINE](PIPELINE.md) |
| Pixel-accurate paint guide for the chosen camera (floor frame + perspective grid + height poles) | ✓ | [PIPELINE](PIPELINE.md) |
| Scrolling fields (larger-than-screen, view follows the player) | ✓ | [FORMAT](FORMAT.md) |
| Multi-camera with script-driven switch zones (after-battle restore) | ✓ | [FORMAT](FORMAT.md) |
| Borrow a real field's exact matched camera | ✓ | [PIPELINE](PIPELINE.md) |

## Walkmesh

| Capability | | Docs |
|---|---|---|
| Hand-model in Blender → `.bgi` (byte-exact codec) | ✓ | [WALKMESH_EDITING](WALKMESH_EDITING.md) |
| Import a real field's walkmesh (single- and multi-floor) | ✓ | [WALKMESH_EDITING](WALKMESH_EDITING.md) |
| Reshape a multi-floor fork while preserving cross-floor seams | ✓ | [WALKMESH_EDITING](WALKMESH_EDITING.md) |
| Build-time validation: floors reachable, content on-mesh, near-edge, zero-area tris, seams | ✓ | [FORMAT](FORMAT.md) |
| `walkmesh verify` standalone checker | ✓ | [README](../README.md) |
| `lint` = ONE offline pass: schema + logic + flag bands + geometry/placement + layer + camera pitch | ✓ | [README](../README.md) |
| Reserved story-flag-band check (chest / handshake / scratch writes flagged by name) | ✓ | [FORMAT](FORMAT.md) |

## Background art

| Capability | | Docs |
|---|---|---|
| Multiple painted layers with explicit depth | ✓ | [FORMAT](FORMAT.md) |
| Foreground occlusion (a near layer draws over the player) | ✓ | [PIPELINE](PIPELINE.md) |
| Light / shadow (additive & subtractive blend layers) preserved on import | ✓ | [PIPELINE](PIPELINE.md) |
| Layer aspect / size validation (catch a stretched repaint before launch) | ✓ | [FORMAT](FORMAT.md) |

## Content & scripting

| Capability | | Docs |
|---|---|---|
| NPCs (presets or custom model + animations) | ✓ | [FORMAT](FORMAT.md) |
| Custom dialogue (own `.mes` text, no base-game collision) | ✓ | [FORMAT](FORMAT.md) · [DIALOGUE](DIALOGUE.md) |
| View / import real FF9 dialogue (decode `.eb` + `.mes` → "NPC → text") | ✓ | [DIALOGUE](DIALOGUE.md) |
| Gateways (room-to-room exits, walk-out direction) | ✓ | [FORMAT](FORMAT.md) |
| Random encounters (+ battle music, + after-battle reinit) | ✓ | [FORMAT](FORMAT.md) |
| Events: chests / gil / messages / story flags (one-shot or repeatable) | ✓ | [FORMAT](FORMAT.md) |
| Story branching: flag-gated NPCs / gateways / events (live + across visits) | ✓ | [FORMAT](FORMAT.md) |
| Cutscenes — narration (ordered, control-locked) | ✓ | [FORMAT](FORMAT.md) |
| Cutscenes — actor (NPC walk / turn / emote / teleport / talk) | ✓ | [FORMAT](FORMAT.md) |
| Save-persistent story flags (correct `gEventGlobal` scope) | ✓ | [FORMAT](FORMAT.md) |
| Story-state author surface: `[startup]` asserts the beat on entry; `[[gateway]]` `set_scenario`/`set_flags` advances it on exit | ✓ | [FORK_FIDELITY](FORK_FIDELITY.md) |
| Wire a custom room into the real game world (entrance + exit) | ✓ | [PIPELINE](PIPELINE.md) |

## Front-ends (author however you like)

| Tool | What | Docs |
|---|---|---|
| **CLI** | `new / guide / camera / walkmesh / disasm / build / import / list-fields / lint / pack / edit / dialogue / dialogue-import / doctor` | [README](../README.md) |
| **Blender add-on** | Visually pose the camera, model the walkmesh, place NPC/gateway/event/spawn/cam-zone markers, paint backdrop, import a real field — **and reshape a 3D battle map** (Import/Export Battle Map) | [blender/README](../blender/README.md) |
| **Form editor** (`ff9mapkit edit`) | Dialogue / events / encounters / flags / cutscenes in forms — no TOML | [README](../README.md) |
| **Dialogue editor** (`apps/ff9_dialogue.pyw`) | Every line in one list with a **live FF9-wrap preview**; view/import real stock dialogue | [DIALOGUE](DIALOGUE.md) |
| **FFIX Import** (`apps/ff9_import.pyw`) | Bring content in from the real game: **fork a field** with the fidelity flags as checkboxes (Native art · carry NPCs/props · carry real dialogue · carry the save point), **read** a field's dialogue, **inspect** a save, list fields. Standalone + a Campaign-Editor tab | [FORK_FIDELITY](FORK_FIDELITY.md) |
| **Two-file split** | Blender owns *where* (`scene.toml`), you own *what* (`field.toml`); merged at build | [FORMAT](FORMAT.md) |

## Engineering (how it's trusted)

- **Byte-exact codecs** — the `.eb` script, `.bgi` walkmesh, `.bgx`/`.bgs` scene, and `.mes` text all
  round-trip real game data byte-for-byte; building the worked examples reproduces in-game-verified
  assets exactly.
- **Offline golden-master validation** — 254 kit + 47 Blender tests; correctness is proven without
  ever launching the game (which honors the "can't see the running game" constraint).
- **Grounded in source** — opcode tables and camera/projection math are baked from the Memoria engine
  source, not guessed; the `.eb` and scene formats were reverse-engineered and verified.
- **No engine dependency** — the output runs on an unmodified Memoria install.

---

## Battle maps (custom 3D battle backgrounds)

| Capability | | Docs |
|---|---|---|
| Fork a real battle background (`battle-import`) — geometry + per-submesh textures → editable FBX | ✓ | [FORMAT](FORMAT.md) |
| Reskin textures / swap custom FBX geometry onto a real slot (stock engine, no rebuild) | ✓ | [FORMAT](FORMAT.md) |
| **Mint a brand-new battle scene** (`--fork-scene`) — net-new `BattleScene` id with forked gameplay/camera/text | ✓ | [FORMAT](FORMAT.md) |
| **Wholly original map** (`--ship-as BBG_B<N>`) — custom geometry under a new bbg number + authored static INB | ✓ | [FORMAT](FORMAT.md) |
| **Tune the fight** (`[scene]`) — override enemy positions / stats / rewards / camera pose on a mint | ✓ | [FORMAT](FORMAT.md) |
| **Spawn composition** (`[scene]` `monster_count` + per-slot `type`) — recompose AND grow the encounter (1–4 enemies; re-authors the eb's enemy-AI binding so a mint can exceed the donor's count) | ✓ | [FORMAT](FORMAT.md) |
| **Opening-camera tweaks** (`[scene]` `camera_yaw` / `camera_pitch` / `camera_zoom`) — rotate/tilt/zoom a minted battle's opening shot (in-place raw17 edit; the native plugin renders it, no DLL rebuild) | ✓ | [FORMAT](FORMAT.md) |
| **Author the opening sweep** (`[[scene.camera_keyframes]]`) — a from-scratch multi-segment crane/orbit in FF9's real opening-camera grammar; keyframes are offsets/zoom around the battle's proven framing, so it always stays framed and ends on the normal shot | ✓ | [FORMAT](FORMAT.md) |
| Deploy reversibly + repoint a field encounter to trigger it (`deploy_battle.py --trigger-field`) | ✓ | [FORMAT](FORMAT.md) |
| **Reshape a battle map in Blender** — import a BBG's Group_0/2/4/8 geometry + textures, edit, re-export an engine-faithful FBX (the add-on's Import/Export Battle Map) | ✓ | [blender/README](../blender/README.md) |

---

## Not in scope (by design)

Honest limits — the kit deliberately does **not**:
- **Paint your background art / battle-map textures** — it gives you a pixel-accurate guide and forks
  the real geometry; the painting is yours.
- Author a **fully arbitrary battle camera from absolute coordinates** — the closed `FF9SpecialEffectPlugin.dll`
  hides the exact world scale, so authored sweeps are expressed as offsets/zoom *around the donor's proven
  framing* (which always frames the fight), not as raw world poses. A multi-segment opening crane/orbit IS
  authorable (`[[scene.camera_keyframes]]`); a from-nothing pose in world units is not.
- Generate **world-map** content (the overworld + its terrain/encounters; no world-map pillar yet).
- Run the game or judge final visual alignment — that's the human playtest step.
- Ship Square Enix's game data — game-derived blobs are sourced from *your own* install.

Platform: developed and verified on **Windows** (the core is stdlib Python; path/launcher resolution
assumes a Windows FF9 install).
