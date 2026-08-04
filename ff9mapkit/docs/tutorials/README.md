# Tutorials

Prerequisite for all of them: the kit installed and pointed at an FF9 install (`ff9mapkit setup`,
or the manual steps in [SETUP.md](../../../SETUP.md) §1–2).

## The core track — start here

One continuing build in the Workspace GUI: each step extends the mod made in the previous one,
and ends with a verifiable result in the game. (The Workspace fronts the same engine as the
CLI — the CLI-side tutorials below cover the terminal equivalent of everything here.)

| # | Step | Result |
|---|---|---|
| S1 | [Fork and deploy a field](s1-fork-and-deploy.md) | A forked room in-game under your own id |
| S2 | [Add an NPC and dialogue](s2-add-an-npc.md) | A talking NPC; the edit → deploy → reload loop |
| S3 | [Connect two fields with gateways](s3-gateways.md) | Two rooms, walkable both ways |
| S4 | [Story flags: a chest and a gated NPC](s4-story-flags.md) | Save-persistent state |
| S5 | [A cutscene and music](s5-cutscene-and-music.md) | A once-only entry scene + a BGM pick |
| S6 | [Random encounters](s6-encounters.md) | Battles: scene pool + frequency |
| S7 | [Package a campaign](s7-package-a-campaign.md) | A campaign, a New Game entry, a distributable zip |

## Track C — the CLI

The same competence as the core track, terminal-native.

| # | Step | Result |
|---|---|---|
| C1 | [The CLI: fork, edit, deploy](c1-cli-fork-edit-deploy.md) | S1–S2's build, done from the terminal |
| C2 | [`field.toml` by hand](c2-field-toml-by-hand.md) | Read and write the project file directly |
| C3 | [Deploy automation](c3-deploy-automation.md) | Slots, reverts, mod-folder resolution, relaunch rules |
| C4 | [The GUI ↔ CLI bridge](c4-gui-cli-bridge.md) | Every Workspace action mapped to its verb |

## The rest (being reorganized into tracks)

Single-goal walkthroughs, each independently completable. The CLI is the canonical surface; the
Workspace GUI tutorial (07) covers the journey flow visually.

| # | Tutorial | Goal | Needs |
|---|---|---|---|
| 01 | [First fork](01-first-fork.md) | Fork a real field, add an NPC, play it (superseded by C1 for the core competence — kept for the install-folder-registration detail C1 omits) | UnityPy |
| 02 | [The dev loop](02-dev-loop.md) | Moved — now C3 above | |
| 03 | [Original-art field](03-original-art-field.md) | A from-scratch field with your own painted background | an image editor |
| 04 | [Fork a region into a campaign](04-campaign.md) | `import-chain` a connected slice of FF9 into one mod | UnityPy |
| 05 | [Assemble a journey](05-journey.md) | Chain campaigns behind a World-Hub selector, wire New Game | campaigns from 04 |
| 06 | [One field in the Workspace](06-gui-field.md) | Moved — now S1 + S2 above | |
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
- **Custom playable characters** (`[[playable]]`) — [`examples/thirteenth-character/README.txt`](../../examples/thirteenth-character/README.txt) (worked example + README)
- **Custom music / SFX** (`audio-import`, `music-list`, `sfx-list`) — `ff9mapkit audio-import -h`
- **Two-player co-op** (experimental; `coop host` / `coop join`) — [FEATURES.md §Multiplayer](../FEATURES.md#multiplayer-experimental), `ff9mapkit coop -h`
- **Items / equipment / saves** (`items-*`, `save-edit`, `[[item_text]]`) — [SETUP.md §7](../../../SETUP.md#7-cli-command-reference)
- **Custom overworld** (continents, islands, relief, offline renders, the ~1s reload loop) — [OVERWORLD_RECIPES.md](../OVERWORLD_RECIPES.md)
- **SPS field particles** — [SPS.md](../SPS.md) · **ATEs** — [ATE_SYSTEM.md](../ATE_SYSTEM.md)
- **Battle tuning** (enemy stats/AI/encounter difficulty, distinct from battle backgrounds) — [BATTLE_DESIGN.md](../BATTLE_DESIGN.md)
- **MOGNET (moogle mail)** (`[savepoint.mognet]`) — [SAVEPOINT.md](../SAVEPOINT.md)
- **Behavior-tree / looping actor AI** (patrols, waves, Fort Condor, `[behavior]`) — [BEHAVIOR.md](../BEHAVIOR.md)
- **Save points & props** (`[[savepoint]]` / `[[prop]]`) — [SAVEPOINT.md](../SAVEPOINT.md)
