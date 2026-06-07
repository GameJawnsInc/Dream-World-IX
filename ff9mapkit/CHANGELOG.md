# Changelog

All notable changes to `ff9mapkit`. Format follows [Keep a Changelog](https://keepachangelog.com);
versioning is [SemVer](https://semver.org). The Blender add-on has its own version, kept in lockstep.

## [Unreleased]

### Added — dialogue choices (`[[choice]]`)
- Talk to an NPC, pick from a menu, and **branch** on the answer — the interaction / puzzle primitive
  (merchant, Yes/No lever, quest-giver). Each option can show a reply, give an item / gil, and set a
  story flag (feeding the same `requires_flag` system). Grounded byte-for-byte in a real FF9 shop
  choice: a synchronous `WindowSync` prompt (rows after `[CHOO]`) + a `GetChoose()` branch. See
  `docs/FORMAT.md` → `[[choice]]`. (In-game proof pending.)

### Added — modern Field Editor look
- The form-based editor (`ff9mapkit edit`) now ships a cohesive theme: a flat `clam`-based palette
  that **matches your Windows light/dark setting** (with a safe light fallback), Segoe UI typography,
  an accent on the primary actions (Save / Build & Test), roomier tree rows, and a colour-tagged
  console log. No new dependency — the palettes + OS probe are pure-stdlib (`editor/theme.py`).

### Changed — provenance: the repo ships no Square Enix game data
- The blank field, exit-region template, and binary test fixtures are no longer committed. They are
  regenerated from the user's **own** FF9 install by the new **`ff9mapkit extract-templates`**
  command, into a local (gitignored) cache. The repo/wheel ship only our copy/insert **patches**
  (our edits + copy offsets) and a SHA-256 manifest — never game bytes. Verified airtight: no patch
  insert run ever duplicates a run in the source field; a built wheel contains zero game bytes.
- `doctor` now reports whether templates are extracted; the byte-level test suite skips cleanly (with
  a pointer to `extract-templates`) when they aren't, so a fresh clone still runs the pure-logic
  tests offline. See [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

Toward the first public **1.0**, remaining:
- Gallery screenshots (`docs/gallery/`).

## [0.9.3] — feature-complete, in-game-verified

The full custom-field pipeline, proven end to end in real gameplay. See
[`docs/FEATURES.md`](docs/FEATURES.md) for the complete capability list and
[`docs/TECHNICAL.md`](docs/TECHNICAL.md) for how the hard parts work. Highlights:

### Fields & camera
- Mint brand-new fields on a **stock Memoria** install (no engine fork).
- BG-borrow and fully-editable custom scenes.
- **Import / fork any of ~670 real fields** — camera, walkmesh, art, and (extracted from the script)
  exits, encounters, field BGM, and movement tuning.
- Author **any camera angle** from scratch; scrolling fields; multi-camera switch zones.

### Walkmesh & art
- Hand-model in Blender or import a real walkmesh; reshape multi-floor forks (seam-preserving).
- Pixel-accurate paint guide; depth layers; foreground occlusion; light/shadow blend layers.
- Build-time validation: reachability, content-on-mesh, near-edge, zero-area tris, seams, layer aspect.

### Content & scripting
- NPCs, custom dialogue, gateways, encounters (+ battle music), events (chests/gil/flags),
  story branching, and cutscenes (narration + actor walk/turn/emote/teleport). Save-persistent flags.

### Front-ends & engineering
- CLI, Blender add-on, form-based logic editor, build GUI; two-file (scene/logic) authoring.
- Byte-exact codecs (`.eb` / `.bgi` / `.bgx` / `.mes`); 254 kit + 47 Blender offline tests;
  opcode + projection math baked from Memoria source.

### Notes
- `0.9.x` unified the CLI and Blender add-on versions; the CLI was previously `0.1.0`.

[Unreleased]: https://github.com/
[0.9.3]: https://github.com/
