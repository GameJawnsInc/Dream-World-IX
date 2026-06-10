# Changelog

All notable changes to `ff9mapkit`. Format follows [Keep a Changelog](https://keepachangelog.com);
versioning is [SemVer](https://semver.org). The Blender add-on has its own version, kept in lockstep.

## [Unreleased]

### Added — battle-map pillar (custom 3D battle backgrounds)
- `ff9mapkit battle-import <BBG>` forks a REAL FF9 battle background out of your install (geometry +
  per-submesh textures) into an editable `battle.toml` + `<BBG>.fbx`; `ff9mapkit battle-build` compiles
  it into a Memoria mod; `tools/deploy_battle.py` installs it reversibly into the per-worktree mod
  folder. `battle-list` browses the real BBGs available to fork.
- A battle map is a real textured **3D mesh** (child groups Group_0/2/4/8 = additive/ground/minus/sky)
  shipped as a loose ASCII **FBX** that **stock Memoria** loads instead of the bundle — no engine
  rebuild. **In-game verified** (texture reskin, a synthetic quad, and a byte-faithful BBG_B013
  round-trip). The first practical custom-battle-background pipeline for FF9. See `docs/FORMAT.md`
  → "Battle maps". Provenance-clean: geometry/textures are extracted from your own install at runtime,
  never committed.
- **Tier-c MINT — a brand-new battle SCENE (in-game proven).** `battle-import --fork-scene <DONOR>`
  also forks a real battle's gameplay/sequence/camera/text (raw16 + raw17 + per-lang `.eb` + `.mes`) into
  the project; `battle-build` emits a net-new `BattleScene <id> <NAME> <BBG>` registration plus those
  assets, and `--ship-as BBG_B<N>` ships the geometry under a **brand-new bbg number** (a wholly original
  map — the kit authors a static `.inb` for it). `deploy_battle.py --trigger-field N` repoints a field's
  encounter at the minted scene so you can fight it. No camera authoring needed (the donor's raw17 carries
  a working camera; a static `.inb` dodges the per-id anim tables). **In-game proven**: a net-new
  `BBG_B200` + scene on stock Memoria, fully fightable. The kit's emitted raw16/raw17/eb/mes are
  byte-identical to the hand-built probe verified in real gameplay. Provenance-clean: forked scene assets
  are SE-derived, written to a gitignored project dir, never committed.
- **Tune the fight (`[scene]`).** A minted battle's forked gameplay is now AUTHORABLE, not just a clone:
  a `[scene]` section in battle.toml overrides enemy **positions** (`pos`/`y`/`rot`), **stats**
  (`hp`/`mp`/`gil`/`exp`/`level`/`speed`/`strength`/`magic`/`spirit`), **rewards** (`drop`/`steal`, items
  by name), and the **camera** pose. The kit surgically patches the forked `raw16` (only edited bytes
  change) and keeps enemy TYPES intact so the forked attack sequences stay valid; items resolve by name
  (`"Hi-Potion"`); shared-type edits warn. Validated against the real Evil Forest scene (Goblin HP 33 →
  1500, etc.).
- **Spawn composition (`[scene]`) — recompose AND grow the encounter.** `monster_count` sets how many
  slots spawn (1–4, the engine cap) and a per-slot `type` chooses which enemy fills it (the scene's
  EXISTING types, so the forked raw17 sequences + GEO cover them; made targetable + auto-grounded). It
  writes the composition to EVERY pattern (a deterministic fight) and **re-authors the battle eb's
  `Main_Init` to bind one enemy-AI object per spawned slot** (`InitObject(1+type, 0x80+slot)`, reusing the
  donor's per-type AI entries). That removes the earlier donor-count cap entirely: a mint can now spawn
  MORE enemies than its donor natively did (e.g. a 1-enemy Evil Forest → four Goblins) with no player-model
  twitch — every slot has a real AI object, so no death misroutes into the player
  (`EventEngine.RequestAction`). In-game proven. Errors only if a needed per-type AI entry is absent
  (a non-standard donor eb). raw16 + Main_Init only; raw17 untouched.
- **Opening-camera tweaks (`[scene]`).** `camera_yaw` / `camera_pitch` / `camera_zoom` rotate / tilt / zoom
  a minted battle's opening camera by offsetting the donor's `SFXDataCamera` keyframes in raw17 IN PLACE
  (no offset-table repack). Cracked the "closed DLL camera" frontier: the native FF9SpecialEffectPlugin.dll
  reads the raw17 camera bytes directly (`SFX_StartPlungeCamera` gets the pinned raw17 + camOffset), so this
  renders with NO engine rebuild — in-game proven. Targets `cameraList[CameraNo]` = the raw16 `camera`
  selector. yaw + zoom are predictable; **pitch is an offset onto the donor's base angle (large values can
  dip the camera below the floor — use small steps).** Full from-scratch keyframe authoring (length-changing)
  is a future tier needing the offset repack.

### Added — `give_item` by name; gil can subtract
- `give_item = ["Potion", 1]` — items resolve by name (case/space/hyphen-insensitive) or numeric id,
  baked from Memoria's `RegularItem` enum (`ff9mapkit items` lists them). No more memorizing ids
  (236 = Potion; 232 was Sapphire). Negative `gil` now correctly **subtracts** (`RemoveGil`).

### Added — dialogue choices (`[[choice]]`)
- Talk to an NPC, pick from a menu, and **branch** on the answer — the interaction / puzzle primitive
  (merchant, Yes/No lever, quest-giver). Each option can show a reply, give an item / gil, and set a
  story flag (feeding the same `requires_flag` system). Grounded byte-for-byte in a real FF9 shop
  choice: a synchronous `WindowSync` prompt (rows after `[CHOO]`) + a `GetChoose()` branch. See
  `docs/FORMAT.md` → `[[choice]]`. **In-game verified.**
- The form editor (`ff9mapkit edit`) has a **Choices** section: edit the prompt/NPC and a list of
  options (text / reply / give item / gil / set flag), reorderable, with `give_item` by name.
- A choice can be **zone-triggered** (a lever / sign): `[[choice]] zone = [...]` instead of `npc`.
  Default `trigger = "action"` (stand on the zone and press) — re-usable, "decline" is non-destructive,
  and it can't loop (edge-triggered by the button), like a real FF9 lever. `trigger = "walk"` auto-pops
  on tread (flag-gated for loop-safety; `once` true/false). Movement locks while the menu is open.

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
