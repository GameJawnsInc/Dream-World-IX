# Battle backgrounds — the four tiers

Distilled from memory `project-ff9-battle-backgrounds` (the canonical deep recipe — read it before any
format-level work; exact paths, FBX node rules, and probe history live there). Doc: `ff9mapkit/docs/BATTLE_DESIGN.md`
§2(g). All tiers in-game proven, zero DLL rebuild.

## What a battle map is

A `BBG_B###` (177 exist, BBG_B001-177): a native Unity GameObject from an FBX with child meshes named
`Group_0` (PLUS/additive), `Group_2` (GROUND), `Group_4` (MINUS/subtractive), `Group_8` (SKY), plus PNG
textures. Sidecars: 16-byte `INB_B###.inb` (BBGINFO) and optional `TAM_B###.tab` (tex-anim). Gameplay is
separate: `dbfile0000.raw16` (BTL_SCENE: spawn patterns, enemies, camera byte) + `{sceneId}.raw17`
(btlseq + opening camera). A battle map is a real volumetric 3D mesh with a moving camera — NOT a
field-style painted plane; field camera math does not transfer.

## Tier (a) — texture reskin

Drop PNGs in the mod folder at
`StreamingAssets/Assets/Resources/BattleMap/BattleModel/battleMap_all/<BBG>/<texname>.png`,
where `<texname>` = the bundle `Texture2D.m_Name` (e.g. `image0`..`image7`). Alpha respected. Lowest risk.

## Tier (b) — loose-FBX geometry swap

A loose FBX at `.../battleMap_all/<BBG>/<BBG>.fbx` is found BEFORE the bundle and replaces the map.
The engine-faithful FBX conventions (Mesh-typed nodes, PSX group shaders set in-FBX, polygon-end
index convention) are implemented in `ff9mapkit/battle/fbx.py` — emit via the kit, never hand-build.
Do NOT use UnityPy's OBJ export (it mirrors the map). Reusing an existing bbg number keeps its
camera/INB/tab valid — the cheapest route to new geometry.

## Tier (c) — net-new SCENE (fork a donor verbatim)

Mint `BattleScene <ID> <NAME> <BBG>` (DictionaryPatch) + FOUR mod assets: the raw16, the `<ID>.raw17`,
per-lang `EVT_BATTLE_<NAME>.eb`, and per-lang `<ID>.mes`. Fork all four from ONE donor so they stay
mutually consistent. The `.mes` is LOAD-BEARING, not cosmetic — a missing `<ID>.mes` = an
ApplyBattlePatch NRE = the battle loads with map+camera but NO enemies/party. Trigger via a field
`SetRandomBattles(pattern, <ID>, ...)` — the scene arg IS the battle id.

## Tier (d) — original BBG number

A net-new `BBG_B###` (>177): loose FBX + textures + a static `INB_B###.inb` (bbgnumber set, `texanim=0,
objanim=0` is verified safe — the engine only ever compares bbgnumber `== <id>`, never indexes by it).
`battle-import --fork-scene <DONOR> --ship-as BBG_B<N>` + the `battle-build` mint path emit all of it.

## Camera

The per-frame camera is computed by the closed native `FF9SpecialEffectPlugin.dll`, but it is a data
CONSUMER: the keyframes live in the raw17 and are fully authorable.

- A forked donor's raw17 camera is FREE (carries its working opening swoop).
- `[scene] camera_yaw / camera_pitch / camera_zoom` — in-place offsets on the donor's opening keyframes.
  Yaw + zoom are predictable; PITCH is finicky (offsets an already-high base — a moderate value can dip
  below the single-sided floor mesh). Small steps + test.
- `[[scene.camera_keyframes]]` — a from-scratch opening sweep (`battle/camera_codec.py`). Author OFFSETS
  anchored on the donor's SETTLE pose (offset 0 / zoom 1 == the game's normal framing); never absolute
  world poses (the plugin hides the scale). The final keyframe's pose becomes the whole battle's normal
  camera. The donor's terminating handoff codes must survive (the kit keeps them) or the battle hangs.

Full keyframe grammar, the distance-unit lesson, and the handoff mechanics: memory
`project-ff9-battle-backgrounds`.

## Build & deploy

`battle-import` (fork geometry and/or scene) → edit `battle.toml` → `battle-build` →
`tools/deploy_battle.py` (reversible; `--trigger-field N` repoints a field's encounter). `battle-list`
/ `battle-list --scenes` catalog maps and donor scenes. Blender round-trip: the add-on's Import/Export
Battle Map (export forces Object Mode; uses the kit emitter, not Blender's native FBX).

## Gotchas

- RELAUNCH for the first deploy of a new id (DictionaryPatch) and any BattlePatch change.
- FieldScene + BattleScene share the GLOBAL `EventDB[id]` → distinct ids, incl. across stacked folders.
- A BBG override only shows on a battle that uses THAT bbg — check which scene your trigger points at.
- Ship a tuned battle on a NEW bbg number (`--ship-as`) so it doesn't globally override the donor's real
  map for other mods (e.g. Moguri reskins).
- Dev/test ids live in the scratch band (see CLAUDE.md §3 "Field-id bands").
