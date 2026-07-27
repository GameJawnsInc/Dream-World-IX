# Tutorials

Single-goal walkthroughs, each independently completable. Prerequisite for all of them: the kit
installed and pointed at an FF9 install (`ff9mapkit setup`, or the manual steps in
[SETUP.md](../../../SETUP.md) §1–2).

The CLI is the canonical surface; the Workspace GUI tutorials (06/07) cover the same flows visually.

| # | Tutorial | Goal | Needs |
|---|---|---|---|
| 01 | [First fork](01-first-fork.md) | Fork a real field, add an NPC, play it | UnityPy |
| 02 | [The dev loop](02-dev-loop.md) | Iterate without relaunching (deploy + ~) | repo checkout |
| 03 | [Original-art field](03-original-art-field.md) | A from-scratch field with your own painted background | an image editor |
| 04 | [Fork a region into a campaign](04-campaign.md) | `import-chain` a connected slice of FF9 into one mod | UnityPy |
| 05 | [Assemble a journey](05-journey.md) | Chain campaigns behind a World-Hub selector, wire New Game | campaigns from 04 |
| 06 | [One field in the Workspace](06-gui-field.md) | The GUI version of 01 | PySide6 (`gui` extra) |
| 07 | [Fork FF9 in the Workspace](07-gui-journey.md) | Fork a multi-arc slice of the game in the GUI, edit a line, deploy | PySide6, UnityPy |
| 08 | [Dialogue choices & a cutscene](08-dialogue-cutscene.md) | A branching choice menu + a scripted actor scene | a field from 01/03 |
| 09 | [Custom battle background](09-battle-background.md) | Fork a 3D battle map, retexture/reshape it, fight in it | UnityPy |
| 10 | [Edit a character model](10-custom-model.md) | Round-trip a model through Blender (mesh + textures) | Blender 4.2+ |
| 11 | [Transplant a model onto a summon](11-summon-transplant.md) | Wear a stock summon's real bones/camera with your own model (Blender round-trip) | Blender 4.2+; hybrid lane needs the custom engine bundle |
| 12 | [Create a creature from scratch](12-creature-from-scratch.md) | An original mesh + rig + animset on a minted id, placed as an NPC | UnityPy |
| 13 | [Edit an animation](../ANIMATION_EDITING.md) | Keyframe-edit a real animation clip in Blender | Blender 4.2+ |
| 14 | [Recolour and reframe a stock summon](14-summon-reskin-rescore.md) | Edit a stock summon's palette and camera in place, no new model (`summon-reskin` / `summon-rescore`) | none — stock Memoria, offline scaffold + a live install |

Pillars without a tutorial yet (reference docs instead):

- **Overworld authoring** (`world-*` commands, islands/terrain/coasts/entrances) — [OVERWORLD_ENGINE.md](../OVERWORLD_ENGINE.md)
- **Custom playable characters** (`[[playable]]`) — `examples/thirteenth-character/` (worked example + README)
- **Custom music / SFX** (`audio-import`, `music-list`, `sfx-list`) — `ff9mapkit audio-import -h`
- **Two-player co-op** (experimental; `coop host` / `coop join`) — [FEATURES.md §Multiplayer](../FEATURES.md#multiplayer-experimental), `ff9mapkit coop -h`
- **Items / equipment / saves** (`items-*`, `save-edit`, `[[item_text]]`) — [SETUP.md §7](../../../SETUP.md#7-cli-command-reference)
- **SPS field particles** — [SPS.md](../SPS.md) · **ATEs** — [ATE_SYSTEM.md](../ATE_SYSTEM.md)
