# What `ff9mapkit` can do

The complete capability list. **✓** = verified **in real gameplay** (not just compiled);
**◐** = offline-validated (builds + passes the codec/golden tests) with the full in-game pass
pending. See the [README](../README.md) for the project overview and
[tutorials/](tutorials/README.md) for walkthroughs.

Engine requirements are per-pillar: everything below runs on **stock Memoria** except where noted
— **forked fields** need the bundled fidelity patch set and **overworld mesh authoring** needs
the `s34` mesh-override patch ([ENGINE.md](ENGINE.md)).

---

## Fields

| Capability | | Docs |
|---|---|---|
| Mint a brand-new field id (declarative `field.toml` → drop-in mod) — stock Memoria | ✓ | [PIPELINE](PIPELINE.md), [FORMAT](FORMAT.md) |
| BG-borrow: render a real field's art/walkmesh/camera under your own script | ✓ | [ENGINE](ENGINE.md) |
| Editable custom scene: ship your own art (per-depth layers, occlusion preserved) | ✓ | [PIPELINE](PIPELINE.md) |
| Fork any of ~674 real fields (`import`) — camera + walkmesh + art + exits/encounters/BGM | ✓ | [PIPELINE](PIPELINE.md) |
| `--native` fork: seam-free per-tile scene (vanilla `.bgs` + atlas) — the recommended art fork | ✓ | [FORK_FIDELITY](FORK_FIDELITY.md) |
| `--verbatim` fork: the field's whole real script + dialogue (real doors, story gating, rotating cast) | ✓ | [FORK_FIDELITY](FORK_FIDELITY.md) |
| Faithful NPC/prop carry on forks (verbatim entry graft, lighting, per-language text) | ✓ | [OBJECT_CARRY](OBJECT_CARRY.md) |
| Fork-fidelity preview before forking (`fork-report`, `--explain`) — roster/story axes, suggested `[startup]` | ✓ | [FORK_REPORT](FORK_REPORT.md) |
| Bulk archive import of the whole game (`import-all`), donor discovery (`find-field`, `find-rooms`) | ✓ | [README](../README.md) |
| Edit a verbatim fork's script in place (`logic-map`, `lint-eb`, `[[logic_edit]]`/`[[logic_add]]`) | ✓ | [FIELD logic-map](FORMAT.md) |
| Chocobo Hot & Cold prize pool + timer (`chocobo-export`, `[chocobo]` on a verbatim forest fork) | ✓ | [FORMAT](FORMAT.md) |
| Non-Zidane donors + walk-as swap (`--swap-player`), party control (`[party]`) | ✓ | [FORMAT](FORMAT.md) |

## Camera

| Capability | | Docs |
|---|---|---|
| Author any angle from scratch (pitch / yaw / FOV / distance) — the projection is fully solved | ✓ | [PIPELINE](PIPELINE.md), [TECHNICAL](TECHNICAL.md) |
| Pixel-accurate paint guide for the chosen camera (floor frame, perspective grid, height poles) | ✓ | [PIPELINE](PIPELINE.md) |
| Per-layer trace-over paint templates (`guide --template`, `paint-template`) | ✓ | [PIPELINE](PIPELINE.md) |
| Scrolling fields (larger-than-screen, view follows the player) | ✓ | [FORMAT](FORMAT.md) |
| Multi-camera with script-driven switch zones (after-battle restore) | ✓ | [FORMAT](FORMAT.md) |
| Borrow a real field's exact matched camera | ✓ | [PIPELINE](PIPELINE.md) |

## Walkmesh

| Capability | | Docs |
|---|---|---|
| Hand-model in Blender → `.bgi` (byte-exact codec) | ✓ | [WALKMESH_EDITING](WALKMESH_EDITING.md) |
| Import a real field's walkmesh (single- and multi-floor) | ✓ | [WALKMESH_EDITING](WALKMESH_EDITING.md) |
| Reshape a multi-floor fork while preserving cross-floor seams | ✓ | [WALKMESH_EDITING](WALKMESH_EDITING.md) |
| Build-time validation: reachability, content on-mesh, near-edge, zero-area tris, seams | ✓ | [FORMAT](FORMAT.md) |
| `walkmesh verify` standalone checker; `lint` = one pass over every offline validator | ✓ | [README](../README.md) |

## Background art

| Capability | | Docs |
|---|---|---|
| Multiple painted layers with explicit depth; foreground occlusion | ✓ | [FORMAT](FORMAT.md), [PIPELINE](PIPELINE.md) |
| Light / shadow (additive & subtractive blend layers) preserved on import | ✓ | [PIPELINE](PIPELINE.md) |
| Native-fork repaint round-trip (`repaint-native`): atlas → spatial layers → seamless re-pack | ✓ | [PIPELINE](PIPELINE.md) |
| Layer aspect / size validation | ✓ | [FORMAT](FORMAT.md) |

## Content & scripting

| Capability | | Docs |
|---|---|---|
| NPCs (archetypes by name, any GEO model + animations) and `[[prop]]` set-dressing | ✓ | [FORMAT](FORMAT.md), [ARCHETYPES](ARCHETYPES.md) |
| Custom dialogue (own `.mes`, speaker tags, auto-wrap); view/import real dialogue | ✓ | [DIALOGUE](DIALOGUE.md) |
| Dialogue choices (`[[choice]]`) — NPC or zone triggered, item/gil/flag effects | ✓ | [FORMAT](FORMAT.md) |
| Gateways (round-trip doors, walk-out direction), ladders, jumps | ✓ | [FORMAT](FORMAT.md) |
| Save points (`[[savepoint]]` — save→reload into a custom field works) | ✓ | [SAVEPOINT](SAVEPOINT.md) |
| Random encounters (+ battle music, + after-battle reinit) | ✓ | [FORMAT](FORMAT.md) |
| Events: chests / gil / messages / story flags (one-shot or repeatable) | ✓ | [FORMAT](FORMAT.md) |
| Story branching: flag-gated NPCs / gateways / events; save-persistent flags | ✓ | [FORMAT](FORMAT.md) |
| Story-state authoring: `[startup]` beat assert, `[[on_entry]]` gated entry beats, gateway `set_scenario` | ✓ | [FORK_FIDELITY](FORK_FIDELITY.md) |
| Cutscenes: narration + multi-actor choreography (walk/turn/gesture/say, parallel beats, player as actor) | ✓ | [FORMAT](FORMAT.md) |
| Active Time Events — optional (blue) and compulsory (grey) flavors | ✓ | [ATE_SYSTEM](ATE_SYSTEM.md) |
| SPS field particles (fire/smoke/magic) — trigger, carry on forks, author | ✓ | [SPS](SPS.md) |
| Field music rescore (`[music]`, verbatim + synthesized) | ✓ | [FORMAT](FORMAT.md) |
| New-game starting state: `[start_inventory]`, `[[equipment]]` (CSV deltas) | ✓ | [FORMAT](FORMAT.md) |
| Custom shops + synthesis shops (`[[shop]]`, `[[synthesis]]`, `opens_shop`) | ✓ | [FORMAT](FORMAT.md) |
| Item/equipment tuning (`[[weapon]]`/`[[armor]]`/`[[item]]`) + menu text (`[[item_text]]`) | ✓ | [FORMAT](FORMAT.md) |
| Custom playable characters (`[[playable]]`) — new roster id, own name/stats/kit, custom battle model, save-persistent — zero DLL | ✓ | `examples/thirteenth-character/` |

## Campaigns, journeys & the World Hub

| Capability | | Docs |
|---|---|---|
| Fork a connected region into one campaign (`import-chain`; zone / whole-zone / exact-id scoping) | ✓ | [CAMPAIGN_IMPORT](CAMPAIGN_IMPORT.md) |
| Campaign build + cross-field lint (`build-all`, `lint-campaign`) — one merged mod | ✓ | [CAMPAIGN_IMPORT](CAMPAIGN_IMPORT.md) |
| Multi-campaign journeys: links, seeds, per-journey tuning (`journeys.toml`) | ✓ | [JOURNEYS](JOURNEYS.md) |
| Generated World-Hub selector field (New Game → pick a journey → seeded warp) | ✓ | [JOURNEYS](JOURNEYS.md) |
| FF9 reference-arc scaffold (`reference-arcs` — the disc-1 spine as a fork playbook) | ✓ | [JOURNEYS](JOURNEYS.md) |
| Reversible deploys + New Game wiring (`deploy-campaign`, `deploy-journey`, `newgame`) | ✓ | [tutorials 04–05](tutorials/README.md) |
| Story-flag scopes: field / campaign / journey, with lint-enforced disjointness | ✓ | [GLOBAL_RESOURCES](GLOBAL_RESOURCES.md) |

## Battle maps & tuning

| Capability | | Docs |
|---|---|---|
| Fork a real battle background (`battle-import`) — geometry + per-submesh textures → editable FBX | ✓ | [BATTLE_DESIGN](BATTLE_DESIGN.md) |
| Reskin textures / swap custom FBX geometry onto a real slot — stock engine, no relaunch | ✓ | [FORMAT](FORMAT.md) |
| Mint a new battle scene (`--fork-scene`) or a wholly original map (`--ship-as BBG_B<N>`) | ✓ | [FORMAT](FORMAT.md) |
| Tune the fight: enemy positions / stats / rewards / spawn composition (1–4 enemies) | ✓ | [BATTLE_DESIGN](BATTLE_DESIGN.md) |
| Opening-camera tweaks + authored multi-segment opening sweeps (`[[scene.camera_keyframes]]`) | ✓ | [FORMAT](FORMAT.md) |
| Attack choreography disassemble/edit (`battle-seq`, `btlseq.raw17`) | ✓ | [BATTLE_DESIGN](BATTLE_DESIGN.md) |
| Enemy AI disassembly (`battle-ai`), scene inspection (`battle-scene`) | ✓ | [BATTLE_DESIGN](BATTLE_DESIGN.md) |
| Player-side tuning: base stats, leveling, gems, ability effects (`ability-features`) | ✓ | [BATTLE_DESIGN](BATTLE_DESIGN.md) |
| Mint a brand-new battle **formula** (`script = {template/body}` → `Memoria.Scripts.<Mod>.dll`) — drain / %-max-HP / custom C#, no engine rebuild | ✓ | [SCRIPTS_DLL](SCRIPTS_DLL.md) |
| Pair a **field effect** (`script.field`) so a scripted ability heals/cures out of combat too — same DLL, same scriptId | ✓ | [SCRIPTS_DLL](SCRIPTS_DLL.md) |
| **`[difficulty]`** — declarative enemy scaling / flag-gated "hard mode" (HP/attack/magic, once per battle; players untouched) | ✓ | [SCRIPTS_DLL](SCRIPTS_DLL.md) |
| **`[rebalance]`** — declarative HP-damage multiplier by side (player_damage / enemy_damage, flag-gateable) | ✓ | [SCRIPTS_DLL](SCRIPTS_DLL.md) |
| **`[deathrules]`** — declarative game-over rules (once-per-battle second-wind revive — full Phoenix or short no-summon + `revive_hp`, chance, Eiko auto-revive removal, `on_defeat` warp-instead-of-game-over, flag-gateable) | ✓ | [SCRIPTS_DLL](SCRIPTS_DLL.md) |
| **`[lowhp]`** — the LowHP threshold (when "HP is low" fires: yellow HP + the `LowHP` status; exact fraction, flag-gateable) | ✓ | [SCRIPTS_DLL](SCRIPTS_DLL.md) |
| Battle-calc **telemetry** to a JSONL + balance report (`battle-telemetry`, dev tool) | ✓ | [SCRIPTS_DLL](SCRIPTS_DLL.md) |
| Reshape a battle map in Blender (add-on Import/Export Battle Map) | ✓ | [blender/README](../blender/README.md) |

## Custom 3D models

| Capability | | Docs |
|---|---|---|
| Export any model + rig + textures + animations to glTF (`model-gltf`) or FBX (`model-export`) | ✓ | [CUSTOM_MODELS](CUSTOM_MODELS.md) |
| Blender mesh/texture editing → loose-FBX override, no DLL (`model-import`) | ✓ | [CUSTOM_MODELS](CUSTOM_MODELS.md) |
| Mint a new additive model id ≥ 6000 (`model-mint`) — originals untouched | ✓ | [CUSTOM_MODELS](CUSTOM_MODELS.md) |
| Animation editing: keyframe-edit real clips in Blender, loose `.anim` overrides (`model-anim`) | ✓ | [ANIMATION_EDITING](ANIMATION_EDITING.md) |
| Custom-character animsets (`playable-anims`) | ✓ | [CUSTOM_MODELS](CUSTOM_MODELS.md) |
| One-click add-on Import/Export FF9 Model | ✓ | [blender/README](../blender/README.md) |

## Overworld

The mesh-writing commands (`world-terrain`, `world-reclaim`, `world-coast`, `world-transplant`,
`world-water`, `world-entrance`, `world-deploy`, `world-mesh-build`) require the engine bundle's
`s34` mesh-override patch ([ENGINE.md](ENGINE.md)); the atlas/texture, encounter, environment,
and marker commands are stock-engine.

| Capability | | Docs |
|---|---|---|
| Reshape walkable terrain (hill/crater/ridge/flatten) across blocks, seamlessly (`world-terrain`) | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |
| Reclaim ocean as walkable land (`world-reclaim`); carry real coastlines (`world-coast`) | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |
| Transplant a complete real island — land + beach + Wang'd ocean — to any cell, with 90° rotation + in-cell shift (`world-transplant`) | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |
| Fuse placements into a continent from one layout toml (`world-fuse`), with per-placement shore tweaks — sink a bank (`bank_lower`) + mint a new real-scale beach on it (`virgin_mint`, `pins_from`) | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |
| Synthesize graded open-ocean water (`world-water`) | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |
| Author a custom overworld entrance — trigger + tiles + optional Blender building (`world-entrance`) | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |
| Overworld encounters: re-table + retune frequency (`world-encounters`, `world-encounter-rate`) | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |
| Atlas texturing: extract / catalog / reskin / add tiles; minimap marker renames | ✓ | [OVERWORLD_ENGINE](OVERWORLD_ENGINE.md) |

## Multiplayer (experimental)

Two-player co-op ("ghost sync"): each player sees the other walk a shared field in real time, and
the host can grant the guest party slots to command in battle plus a "visitor mode" that dresses the
ghost as a real party member and follows the host between screens. Requires the Dream World IX
custom engine's `s36`/`s37` netsync patches ([ENGINE.md](ENGINE.md)), which are not yet in the
pre-built engine bundle. Every save stays each player's own.

| Capability | | Docs |
|---|---|---|
| One-command session setup — room deploy + config + session code + TLS bridge (`coop host`, `coop join ff9-XXXX`) | ✓ | `coop -h` |
| Internet play through a public rendezvous relay (random private session codes), or direct LAN (`coop host --lan`) | ✓ | `coop -h` |
| Battle co-op — guest spectates, or commands granted party slots with the full menu set (`--guest-slots`, `--guest-wait`) | ✓ | `coop -h` |
| Visitor mode — the ghost dresses as a party member, follow-host auto-warp + encounter pause (`--ghost-as`, `--follow-host`) | ✓ | `coop -h` |
| Print the current co-op config in human terms (`coop show`); hot-reload — a running game applies changes in seconds | ✓ | `coop -h` |
| The Workspace **Co-op** tab: point-and-click host/join + the Play-style panel for all of the above | ✓ | Workspace → Co-op |

## Audio & video

| Capability | | Docs |
|---|---|---|
| Custom music/SFX: replace or mint an Ogg Vorbis track, looping — DLL-free (`audio-import`) | ✓ | `audio-import -h` |
| Field BGM rescore + per-encounter battle BGM | ✓ | [FORMAT](FORMAT.md) |

## Save & story-state tooling

| Capability | | Docs |
|---|---|---|
| Decode / diff a save's story state (`flags-inspect`, `flags-diff`); story-flag registry (`flags`) | ✓ | [GLOBAL_RESOURCES](GLOBAL_RESOURCES.md) |
| Write story state (`save-edit`) — scenario + flags |  ✓ | [GLOBAL_RESOURCES](GLOBAL_RESOURCES.md) |
| Items / equipment / gil / stats / AP read + write (`items-inspect`, `items-set-*`) | ✓ | [README](../README.md) |

## Front-ends

| Tool | What | Docs |
|---|---|---|
| **CLI** | 105 commands across the families above | [SETUP §7](../../SETUP.md#7-cli-command-reference) |
| **Workspace GUI** (PySide6) | One dockable window: journey ▸ campaign ▸ field ▸ object tree; Editor / Map / Story State / Item & Equip / Battle / Models / Build & Deploy / Import tabs; Info Hub library; Ctrl-K palette; Setup & Health; F9 deploy; field-art + 3D-model thumbnails; themes + update check | [SETUP §6](../../SETUP.md#6-the-gui-workspace-optional) |
| **Blender add-on** | Camera posing, walkmesh modeling, markers, field import, battle-map + model round-trips | [blender/README](../blender/README.md) |
| **Form editor** (`ff9mapkit edit`) | Field logic in forms — stdlib Tkinter, no PySide6 needed | [README](../README.md) |
| **Two-file split** | Blender owns *where* (`scene.toml`), the logic file owns *what* (`field.toml`); merged at build | [FORMAT](FORMAT.md) |

## Validation

- **Byte-exact codecs** — `.eb` script, `.bgi` walkmesh, `.bgx`/`.bgs` scene, `.mes` text all
  round-trip real game data byte-for-byte; building the worked examples reproduces
  in-game-verified assets exactly.
- **Offline golden-master suite** — ~2,850 kit tests + the Blender add-on suite; correctness is
  provable without launching the game.
- **Grounded in source** — opcode tables and camera/projection math are baked from the Memoria
  engine source; the `.eb` and scene formats were reverse-engineered and byte-verified.

## Out of scope

- **Painting background art / battle-map textures** — the kit produces pixel-accurate guides and
  forks real geometry; the painting itself is a manual art step.
- **Fully arbitrary battle cameras from absolute coordinates** — the closed
  `FF9SpecialEffectPlugin.dll` hides the world scale, so authored sweeps are expressed as
  offsets/zoom around the donor's proven framing (multi-segment crane/orbit openings ARE
  authorable; a from-nothing world-unit pose is not).
- **Running the game** — final visual alignment and behavior are verified by manual playtesting.
- **Shipping Square Enix game data** — game-derived assets are regenerated from the local install
  ([PROVENANCE.md](PROVENANCE.md)).

Platform: developed and verified on **Windows** (path/launcher resolution assumes a Windows FF9
install).
