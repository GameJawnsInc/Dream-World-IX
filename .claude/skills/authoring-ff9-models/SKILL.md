---
name: authoring-ff9-models
description: Import, mint, reskin, and animate custom 3D FF9 models, all DLL-free. Use for any `model-*` command (`model-export`/`import`/`gltf`/`mint`/`anim`/`anim-new`/`preview`/`reskin`/`deployed`, `playable-anims`), adding a custom NPC/creature/weapon model, editing a mesh/skeleton/texture in Blender, minting a new animation clip, or building a from-scratch creature. Covers loose skinned+animated FBX/glTF (anims bind by bone name), FIELD anim ids are 16-bit -> mint band 60000-65535, the battle-model `resolve_prefab` alias chain (71 alias ids deploy at the DONOR prefab folder, overlay meshes stripped, 43 refuse), bone display labels (`bone012_R_hand`, `--plain-bones` opts out), `model-anim-new` clips surviving a redeploy, and the from-scratch pipeline (procedural mesh+rig -> `emit_skinned_fbx` -> `[[mint]] fbx=`). The Blender add-on exports the artifact and prints the CLI command; it never subprocesses the toolkit. To wire a model to a playable character see `creating-ff9-characters`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Authoring FF9 Models

Every `model-*` command is DLL-free: the engine probes a loose `Models/{typeInt}/{geoId}/{geoId}.fbx` before the bundle, and animations are legacy Unity clips "bound by bone NAME (`bone{id:D3}`)" — only names must match. Canonical doc: `ff9mapkit/docs/CUSTOM_MODELS.md`; deep recipe: memory `[[project-ff9-custom-models]]`.

## Export/import/preview round-trip

`model-export` (engine-layout FBX + PNGs) · `model-gltf` (Blender-ready `.glb` with clips) · `model-import` (edited `.glb` back in; auto-detects the source, auto-falls back to a hybrid re-rig) · `model-preview` (offline software render). Detail → `references/model-pipeline.md`.

## Reskin/recolor

`model-reskin` exports textures / deploys edited PNGs — the engine swaps textures BY NAME for every bundle-loaded model, so a texture edit needs no mesh. `model-deployed` inventories and reverts a mod folder's loose model state. Detail → `references/model-pipeline.md`.

## Mint

`model-mint <src> --id N` / the `[[mint]]` field.toml block mints a brand-new GEO id: "real GEO ids are 0..5511 → mint band ≥ 6000"; NEVER reuse a real GEO name. A custom weapon's Weapons.csv Model takes a minted GEO name. A new id registers at launch → one relaunch. Detail → `references/model-pipeline.md`.

## New animation clips

`model-anim-new` mints a wholly new clip. Two traps: **FIELD anim ids are 16-bit** — "A field-playable anim key MUST fit UInt16 (≤65535)" → mint band **60000–65535** — and "a NEW clip must key the FULL skeleton" (an unkeyed neck + head-focus = the spinning-head artifact). Minted clips survive a field redeploy: `ff9mapkit/dictpatch.py` preserves foreign DictionaryPatch lines by exact id/key. Detail → `references/model-pipeline.md`; editing EXISTING clips → `ff9mapkit/docs/ANIMATION_EDITING.md`.

## Battle-model alias chain

A battle form is usually NOT its own prefab: `extract.resolve_prefab` replays the engine's alias chain (baked `_modelalias.py`), so **71 alias ids** export/preview/reskin/deploy engine-faithfully — overrides land at the DONOR prefab folder, overlay meshes are stripped — and the **43 unshipped ids** refuse actionably. Detail → `references/battle-model-alias.md`.

## Bone display labels

`model-gltf` names bone nodes `bone012_R_hand` (anatomical display aliases; baked `_bonelabeldb`, 83% of FF9 bones; +x = the character's RIGHT, face = −z). Labels are DISPLAY ONLY — binding stays by bone number/path; `--plain-bones` opts out. Read memory `[[project-ff9-bone-semantic-labels]]`.

## From-scratch creature

Zero FF9 bytes: procedural mesh+rig+texture → `emit_skinned_fbx` → `[[mint]] fbx=` → `model-anim-new` idle → `[[npc]] model=<mintId>`. Worked example: `ff9mapkit/examples/boletta/` + `ff9mapkit/docs/tutorials/12-creature-from-scratch.md`. Detail → `references/model-pipeline.md`.

## The add-on exports, does not orchestrate

The Blender add-on does ONLY the `.glb` I/O and reports (+ clipboard-copies) the `ff9mapkit model-import …` command for the user to run — it never subprocesses the toolkit. Read memory `[[feedback-blender-addon-exports-artifacts]]` before touching any add-on operator.

## Additional resources

- `ff9mapkit/docs/CUSTOM_MODELS.md` — the design doc + load-bearing evidence index (source file:line).
- `ff9mapkit/docs/ANIMATION_EDITING.md` — the Blender clip-editing tutorial + its footguns.
- Memory (read on demand): `[[project-ff9-custom-models]]` (THE deep recipe), `[[project-ff9-battle-model-export-gap]]` (alias chain), `[[project-ff9-bone-semantic-labels]]` (labels).
- To wire a custom model/animset/portrait to a `[[playable]]` character, see the `creating-ff9-characters` skill.
