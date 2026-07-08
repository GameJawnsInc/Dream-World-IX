# Dream World IX 1.0.0b13 — New party members, custom battle scripting, and hand-built overworlds

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* content — and faithfully forking the real game — for the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam/GOG FF9). This is the biggest content release yet: genuinely new engine party members, a declarative channel for custom battle/field/status scripting, from-scratch 3D models and creatures, synthesized overworld oceans and islands, custom music, and more — 164 commits and 3031 passing tests since b12, almost all of it DLL-free.

> Recruit a 14th party member with their own kit, script a life-draining spell in one TOML line, sculpt a walkable island out of open ocean, and drop in your own soundtrack — no engine rebuild required.

## What's new since v1.0.0b12

### 👥 13th & 14th playable characters

A new `[[playable]]` block mints genuinely new engine party members — a 13th and 14th character alongside all 12 canon — each with their own name, stats, battle model, animset, portrait, and a bespoke ability kit, entirely DLL-free.

- `[[playable]]` defines and recruits a genuinely NEW engine `CharacterId` (ids 12–15, up to 4 custom characters): its own name in all 7 languages, stats cloned from a `borrow` donor then overridden, real `B_PARTYADD` recruitment (`recruit = true`), and save/reload persistence.
- Two custom characters proven coexisting — Iviv (id 12, Vivi mage rig) and Steiniv (id 13, Steiner knight rig); the kit auto-allocates distinct CSV / preset / command / ability / model / serial bands per character so they never collide.
- `custom_battle_model` mints an independent, editable copy of the donor's battle model (own serial + BattleParameters row) so reshaping it in Blender never touches the base character — usable even on scenario-formula donors like Zidane/Garnet.
- `custom_battle_anims` + the new `ff9mapkit playable-anims <field.toml> --export <GLB>` / `--edit <GLB> --deploy <MODFOLDER>` loop give the minted model its own editable animset — edit named clips (`23_attack`, `27_cast`) in Blender and route only the changed ones back; `anim_edits = "x.glb"` persists them across re-deploys.
- `portrait = "132x190.png"` sets a custom party-menu avatar via a loose Face-Atlas override, non-destructive to stock/Moguri faces.
- `[playable.abilities]` gives the character its OWN command menu and curated learn list on its own `CharacterPresetId` (band 20–23): `command1`/`command2` slots (+ trance mirrors) and `learn = [{ ability, ap }]`.
- Mint a UNIQUE command — inline `[playable.abilities.command1]` `{ name, abilities }` creates a brand-new `BattleCommandId` with its own ability pool and per-language `com_name.mes` overlay (e.g. Iviv's mixed black+white "Spark").
- Mint a CUSTOM ACTIVE ability — an inline `{ name, from, power, element, mp, rate }` clones a stock donor into a new `Actions.csv` row and retunes it; also takes `status = ["Silence"]` (auto-mints a StatusSets row) and `effect = "[code=MPCost] 0"` (an AbilityFeatures hook for free-in-battle).
- *In-game proven (2026-07-06):* both custom characters recruit, fight with their own models/animsets, cast their minted commands/abilities, and persist through save/reload. Caveats: don't open the in-game rename screen for a custom id (its name comes from the DictionaryPatch), and FF9 renders only the party leader in fields (menu + battle unaffected).

### 🧬 Scripts-DLL — custom battle, field, and status scripting

A new declarative channel mints genuinely new battle formulas, out-of-combat field effects, and custom status ailments into a per-mod plugin DLL the engine loads alongside its own — with no `Assembly-CSharp` rebuild.

- Custom battle FORMULAS from one TOML line: a custom ability's `script = { template = "drain_hp" }` (or `{ body = "<C#>" }`) mints a `[BattleScript(id>=256)]`, compiles it into a mod-owned `Memoria.Scripts.<Mod>.dll`, and repoints the ability's `scriptId` — expressing drain, %-max-HP, and sequencing the data path can't. (A scalar `script = 16` is still just a data re-point and needs no DLL.)
- Four battle templates cloned from FF9 donors: `drain_hp` (deal damage AND heal caster), `drain_mp` (Osmose), `magic_damage`, and `white_wind` — each reading the ability's own power/element/mp tuning.
- Paired FIELD effects: add `script.field = { template = "field_heal_hp" | "field_white_wind" | "field_chakra" | "field_cure_status" | "field_revive" }` and the kit mints a matching `[FieldAbilityScript]` at the same id, so one curative ability works in AND out of combat.
- Custom STATUS ailments: `status = [{ name = "Rebirth", template = "auto_life", power = 50 }]` mints a `[StatusScript]` + a StatusData row (custom id 33–63) + the inflict; templates `auto_life` (revive-once) and `auto_attack`, or a raw `body`/`hooks` escape hatch. (Honest limit: per-tick DoT is unreachable — the tick hook is mask-gated to vanilla statuses.)
- Custom-status HUD icon (`icon = "Regen"`) borrows a vanilla panel sprite, and `over_model = "Haste"` clones a vanilla status's on-model SHP/SPS/tint so a buff is visible on the 3D model.
- `ff9mapkit lint` now blocks a scripted ability with no findable `csc` compiler ($FF9_CSC override, then VS Build Tools Roslyn, then .NET Framework csc), and each build stamps a `<dll>.buildinfo.json` sidecar so deploy/doctor warn OFFLINE on engine-version drift.
- `ff9mapkit battle-telemetry <mod>` installs an IOverload hook logging every battle calc to `ff9mk_battle_telemetry.jsonl`; `--report` summarizes casts, hit%, crit%, and damage per ability/unit (engine defaults transcribed verbatim, every write exception-swallowed).
- *Mostly in-game proven (2026-07-07)* — Soul Leech drain, Lifewell field heal, a Rebirth auto-life revive with on-model chevron, and a real 2-battle telemetry capture. Requires `csc` on the build machine; the DLL loads at the title screen, so **relaunch** after deploy (F6 reload won't pick it up). See `ff9mapkit/docs/SCRIPTS_DLL.md`.

### 🗿 Custom 3D models — round 2

The custom-model pillar grows from editing FF9's models to authoring wholly new animation clips and even whole from-scratch creatures, plus a GUI browser and one-PNG reskins — all still DLL-free.

- `model-anim-new <model> --deploy MODFOLDER [--glb FILE --action NAME]` authors a WHOLLY NEW animation clip (from a Blender `.glb` action or a built-in spin demo) via a `3DModelAnimation` directive — field anim keys are 16-bit, so new clips mint into the 60000–65535 band (in-game proven: a full-body spin on Beatrix's model at key 60000). It also works on minted models.
- A wholly-original creature with ZERO FF9-derived bytes — "Boletta" — ships her own procedural mesh + 5-bone rig + hand-painted texture + authored idle clip, minted as a new GEO id and placed as a talking NPC; she renders, idles, and holds dialogue in-game (worked example `ff9mapkit/examples/boletta/` + tutorial `ff9mapkit/docs/tutorials/12-creature-from-scratch.md`).
- Static meshes (weapons, props) are now editable through the skinned pipeline (a trivial 1-bone rig wraps skeleton-less prefabs), proven with an oversized RuneTooth blade in battle; the weapon extractor now reads the correct battle-model bundle path.
- Overworld actor models can be reskinned AND re-animated with no new code, backed by an authoritative world-model → character map (`GEO_SUB_W0_001` = Zidane, `W0_002` = Garnet, `W0_003` = Chocobo, …); proven with a wide-leg Zidane on the world map.
- Three new no-Blender CLI commands: `model-preview` (software-render a posed PNG still), `model-reskin` (export or deploy edited texture PNGs — the cheapest edit), and `model-deployed` (list/revert a mod folder's loose overrides / reskins / mints / anim overrides).
- GUI Models tab: an illustrated Workspace browser with real software-rendered thumbnails, a detail pane, and the whole export/import/mint round trip; model thumbnails also appear across the Info Hub and pickers, plus a `[[playable]]` character form.
- Deploy now preserves foreign `3DModel`/`3DModelAnimation` lines across a redeploy, and `model-gltf --anims auto` labels clips with friendly names (idle/stand/run/walk/turn), preferring on-foot locomotion.

### 🌊 Custom overworld — synthetic oceans, islands, cliffs, save position

Synthesize brand-new overworld water, islands, and cliffs from scratch — faithful to how FF9 itself builds them — and set exactly where the player stands on the world map.

- `ff9mapkit world-water --cells X,Y` synthesizes graded open-ocean water from a depth field, laying down the real sea-tile vocabulary (Sea3 mid / Sea5 transition / Sea4 deep) with byte-proven UVs and marching-band Wang tiles so shades seam-match with no visible grid; `--deep N|S|E|W` grades toward a coast.
- The synthesized ocean is boat-walkable at the surface (the water walkmesh sits just under Y=0 with the deep-sea topograph) — a boat sails across it while on-foot is blocked, exactly like real ocean.
- A/B fidelity modes: `world-water --verbatim [BX,BY]` drops a real block in unchanged as a reference, `--reproduce [BX,BY]` regenerates a real block with synthesized tiles (validated 17/17 tile-shape match).
- `ff9mapkit world-island --cell BX,BY` synthesizes a fully-custom cliff island — organic coastline + a faithful ~73° rock wall + the real grass language — multi-cell by construction (multi-cell walking is in-game proven; the current capstone is a ~130×88u, 6-block landmass); `--lobes 2-3` builds asymmetric multi-lobe shapes, and the command refuses to deploy if the coastline fails FF9's measured shape/placement census.
- `world-reclaim --profile cliff` turns a reclaimed ocean cell into rolling land that drops via a steep ~73° rock wall to the waterline, textured with the REAL grey-rock atlas (faithful to 208 measured FF9 cliffs).
- `ff9mapkit save-edit --world-pos X,Z` relocates where you spawn on the world map (decoded from `gEventGlobal`'s 24-bit fixed-point layout; Y ground-snapped by the engine); `--world-actor player|chocobo` picks the actor. Also wired into the Workspace Story-State tab.
- *In-game proven:* water looks correct and is boat-walkable (2026-07-06); the multi-cell landmass walks seamlessly (2026-07-07); the cliff profile reads as a faithful wall; the save relocation spawns the player exactly on the new spot. World mesh commands reuse the already-shipped s34 patch (need the existing bundle + a world re-entry); save-position editing needs no engine at all.

### 🎵 Custom music & SFX (DLL-free)

Drop in your own Ogg music and sound effects — swap any of FF9's tracks, mint brand-new song ids, or give a field its own theme — with no engine rebuild. At b12 this was feasibility-RE only; b13 ships it as working CLI and it is in-game proven.

- `ff9mapkit audio-import <input> --song <id> --deploy <modfolder>` REPLACES any music/SFX id with your own file (wav/mp3/ogg/flac/…), transcoding to Ogg Vorbis via ffmpeg and auto-setting `Memoria.ini [Audio] PriorityToOGG=1` (backed up) so your track wins.
- `audio-import <input> --new-song [--id N]` MINTS a brand-new song id (auto-picked in the ≥1000 band) — ADD tracks rather than just swap; trigger with `[music] song = <id>` in a field.
- `ff9mapkit music-list` / `sfx-list` dump the song-id → ResourceID map (cached from the game's resources) so you know which id to override.
- `[music] file = "theme.ogg"` ships a field's OWN theme — the build transcodes, mints a song id, and wires the field to play it (synth fields and verbatim forks alike), with optional `loop_start`/`loop_end` in samples.
- Music auto-loops (a tagless track loops whole); SFX play once; a kind-aware reminder warns if the governing volume is muted. `deploy_field` ships the minted OGG and merges the MusicMetaData manifest across successive deploys.
- *In-game proven* — a chiptune over the battle theme, a boing over the Moogle-welcome SFX, the mint mechanism, and `[music] file` end-to-end. Runs on the stock Memoria audio loader (present in the shipped bundle); requires ffmpeg on PATH. Custom audio loads at startup, so **restart FF9** to hear it (F6 reload won't re-read audio).

### 🎨 Palette-swap enemies + custom weapon models

Recolor a forked battle enemy into a brand-new variant, or reskin an equippable weapon — the classic "Goblin → Goblin Mage" move (and a crimson blade) as one declarative knob each, zero DLL.

- `[[scene.enemy]] skin = { id = 6210, hue = 150 }` recolors a forked battle enemy into a new variant, minting its model at a fresh GEO id (≥6000) and repointing the enemy's Geo@30 — the ORIGINAL creature stays vanilla everywhere else.
- Three composable recolor knobs: `hue` (HSV rotation in degrees), `tint = [r,g,b]` (per-channel multipliers), and `textures = { "<stem>" = "my.png" }` (hand-painted overrides); the alpha/cutout mask is preserved exactly.
- The skinned variant keeps its OWN skeleton and clips, so — unlike a cross-model body re-skin — there's no attack-retarget quirk: it idles, attacks, and dies with its own animations (proven: a hue-150 green Goblin).
- `[[weapon]] model = "GEO_WEP_B1_030"` swaps an equippable weapon's look to a stock model, or `model = { id = 6500, tint = [1.7,0.5,0.5] }` mints a recolored variant (same hue/tint/textures knobs), composing on one row with the item's existing stat deltas (proven: a crimson Rune Tooth).
- Both are zero-DLL data patches (loose FBX + a `3DModel` registration + a model-id poke) with fail-loud offline validation (mint band 6000–32767, duplicate-id rejection, no-op guard). **Relaunch** to register a new minted id.

### 🎭 Rotating-cast / beat-windowed NPCs

Author NPCs that appear only during a story beat — two at one spot with adjacent windows form a rotating cast (a shopkeeper who swaps by disc) — in a few lines of TOML, with zero engine changes.

- New `[[npc]] scenario_min` / `scenario_max` keys gate an NPC on a ScenarioCounter WINDOW `[min, max)` (min inclusive, max exclusive) — outside it the Init returns early (no model, not interactable).
- Because the window is half-open, two NPCs at the same spot with adjacent windows tile cleanly with no overlap and no gap — FF9's real rotating-cast idiom, now authorable. Either bound may be a raw beat or an area name (e.g. `scenario_min = "Dali"`).
- One-sided windows work (`scenario_min` alone = "from this beat on"), and it composes with `requires_flag` (both must hold). Works on synth fields and `--verbatim` forks; an NPC with no window builds byte-identically to before.
- `ff9mapkit lint` now WARNS (advisory) when co-located NPCs have overlapping windows or leave a coverage gap; hard errors guard `scenario_min < scenario_max` and valid ranges. The emitted byte shape round-trips through `fork-report`.
- *In-game proven (2026-07-07):* a mage keeper (SC < 6990) and a soldier keeper (SC ≥ 6990) at one spot swapped cleanly when F6 set ScenarioCounter to 7000. This is the authoring side of fork-fidelity gap #13; carrying a real field's cast faithfully remains `--verbatim` + `[startup] scenario`.

### 🖼️ Experimental: image → explorable field

**EXPERIMENTAL.** A new `image-field` command turns any image plus a hand-traced floor outline into a walkable FF9 field — the picture becomes the painted background and the traced floor becomes real walkmesh you can stand on.

- Brand-new `ff9mapkit image-field <image> --floor "cx,cy …" --out DIR` (did not exist at b12): the image is the background, the floor polygon becomes the walkmesh, and a vanilla camera + a spawn at the floor centroid are authored automatically.
- The floor is un-projected onto the world ground plane by a closed-form perspective homography (FF9's projection is perspective, not orthographic) that round-trips the engine's own `to_canvas` math to ~2e-12 world units, then is outset ~48u past the visual edge so the player can reach the painted edge.
- Repeatable `--foreground PNG` cut-outs are wired in as occluder overlays so foreground objects draw in front of the character.
- Camera tunables `--pitch` (26), `--fov` (42), `--distance` (3000); id/name via `--id` (4003) / `--name` (PICTURE). Output is an ordinary custom-scene project (`<name>.field.toml` + walkmesh.obj + art/) that plugs into the usual deploy → F6 loop and can be hand-edited.
- Pillow-only, zero new dependencies, no engine rebuild. Covered by 9 offline tests (homography round-trip, inv3-vs-transpose guard, above-horizon reject, Int16 guard, end-to-end emit).
- *MVP in-game proven (2026-07-08)* on a synthesized painted-trapezoid test room — the character stands on the floor, walks the trapezoid, and foreshortening reads right. **Scope:** this is the hand-traced-floor MVP; automatic floor detection (numpy) and neural depth bands (an optional `[depth]` onnx extra) are documented future tiers, NOT in this release. Feeding a real photo is the honest next test and remains untested.

### 🖥️ Workspace GUI pass

The PySide6 Workspace grew a screenshot-driven UX overhaul plus the features a visual modding IDE was missing — it now shows the actual room art, deploys with one keystroke, opens by drag-and-drop, and has a Setup & Health doctor.

- Field background THUMBNAILS — the Inspector shows the selected field's room art, campaign Map nodes grow an art band with the real (center-cropped) room, and Import's "Preview fidelity" shows the room you're about to fork (per-user disk cache; disable with `FF9MAPKIT_NO_THUMBS=1`).
- **F9** folds and saves every unsaved edit, then runs the configured deploy for the open target from ANY tab (refuses to deploy stale files if a save fails); also on the breadcrumb "▶ Deploy F9" button and Ctrl-K.
- Drag-and-drop open — drop a `.toml` (journey/campaign/battle/field routed to the right editor), a save file (opens the save docs), or a Blender `.glb` (pre-fills Import ▸ Custom models).
- Setup & Health page — a never-raises "doctor" report checking kit, UnityPy, PySide6, ffmpeg, install, launcher, StreamingAssets, and the Memoria engine, each row with actionable advice, plus Locate game / Run setup / Install engine patches (confirm-first, backed-up DLLs).
- Custom 3D models flow surfaced GUI-first: Info Hub "Export for Blender…" and an Import "Custom 3D models" box (export .glb / import edited .glb / mint from model), verified against the real install (Vivi → 688 KB glb).
- Import round-out — a pre-fork STUDY row (fork-report Preview + "+ explain NPC logic" + a "Study logic…" in-process `.eb` decode), an import-all REFERENCE ARCHIVE box, and FIND-ROOMS "Suggest a test room…"; plus a story-beat slider that drags through ScenarioCounter beats and watches a rotating-cast roster change (proven live on Gargan Roo / field 951 and field 111).
- Custom-music authoring exposed in the Editor `[music]` form (file / loop_start / loop_end + a song catalog picker), session continuity (opt-in reopen-last-project, persisted window/dock/splitter state, a project-tree filter), a recent-projects (MRU) store, and `pack --name` + a "Package (zip)…" button so the funnel ends at a shareable artifact.
- Screenshot-driven fixes — Fusion base style + theme-derived palette repairs light themes on dark-mode Windows 11, the toolbar fits at 1280px, a redesigned Home with entry-point cards, plus a 30-agent adversarial review that fixed 21 QoL/thumbnail defects.
- *Offline / GUI-verified* — desktop-app work, not run in-game, though several flows were verified live against the real install. Locked by `--smoke` + ~50 headless workspace tests.

### 📚 Docs overhaul + tutorials split

The entire user-facing doc set was rewritten for accuracy and technical tone, the monolithic tutorial was broken into an 11-page single-goal set, and the `[[playable]]` block finally got a full schema reference.

- Tutorials reorganized under `ff9mapkit/docs/tutorials/` with an indexed README: 01 first-fork through 10 custom-model (11 links to ANIMATION_EDITING.md), each independently completable; the old `docs/TUTORIAL.md` and root `FORKING_FF9.md` are now stubs pointing in (old links preserved).
- A full accuracy re-verify corrected recipes that would have failed as written — the safe author story-flag band is `[8512, 16320)`, `build --out` IS the mod folder (no `--mod-name` subfolder), the journey entry member is `IC_ENTRANCE`, `requires_flag` is a scalar, and `list-fields` zone codes are FBG substrings (`alxt`/`trno`/`vgdl`).
- `SETUP.md` §7 CLI reference regenerated as a grouped reference (97 subcommands), documenting that global `--game` / `--mod-folder` / `--version` go BEFORE the subcommand, with UnityPy consistently described as the `assets` extra.
- New `FORMAT.md` `[[playable]]` schema section — full key tables for core keys, the custom battle model + animset, `[playable.abilities]`, and inline tables for minting a command / ability / status, with a worked example and the relaunch + New-Game caveats.
- Tone pass across every user-facing doc (first-person voice, internal-brief/provenance references, and marketing superlatives stripped), and a `FORK_FIDELITY.md` census update: an 818-field sweep settled the "phase-switch rotation director" as a phantom (527 phase-switch loops, 0 rotate other cast), clarifying why the destructive synth roster-drop correctly stays narrow.

### 🔧 Engine & fork-fidelity tooling

A new offline fork-gate verification harness closes the long-standing s29 late-disc softlock verification debt.

- `py tools/verify_fork_gates.py --list` / `--emit <field>` — a new OFFLINE scaffold that bakes the s29 gate table with each gate's boot seed (from fork-report) plus an observability verdict and emits a copy-paste fork+deploy+F6 test playbook per target. It scaffolds commands only; it does not run deploys.
- One load-bearing finding: only field 2507 (Ipsen's Castle) is crisply cold-fork-testable because its walkmesh hotfix fires at field LOAD — and it passed in-game (2026-06-23). Every other s29 gate fires mid-cutscene / post-battle / on an abnormal party a cold fork boots past.
- Gates are now classified by verdict — crisp-at-load (2507, proven) / needs-scripted (verify when the zone is forked) / low-signal-party / ending-only — with the recommended disposition to accept the party-guard and Epilogue classes as mechanism-proven (identity-safe). `FORK_IDGATE_MAP.md` gained a verdict column; +8 tests.
- *Harness is DLL-free offline tooling* that runs against the existing engine bundle; the s29 verdicts are in-game proven (2507) or code-verified + identity-safe.

## Engine bundle

**The b13 public engine bundle is UNCHANGED from b12** — the same engine patch set (the fork-fidelity **s23–s33** suite + the **s34** overworld mesh-override) plus the **F6 in-game debug menu** (Go / Cheats / Flags / Time), shipped as `dwix-custom-memoria-*.zip`.

- **If you already have the b12 engine, you do NOT need to re-download it.** Everything new in b13 is either DLL-free or runs on that existing bundle.
- A **novel** (from-scratch / BG-borrow) field runs on **stock Memoria** — as do the headline b13 pillars: custom characters, the Scripts-DLL channel, custom models & creatures, palette-swap enemies & weapon models, custom music/SFX, rotating-cast NPCs, and the experimental image-field.
- A **forked** field needs the shipped s23–s33 fork-donor remap suite (Dante's off-mesh exemption, narrow-map width, fake-battle return, softlock fixes), and the overworld synthesis commands (`world-water` / `world-island` / `world-reclaim`) reuse the already-shipped **s34** mesh-override patch — all present in the unchanged bundle.

## Getting started

- **Windows:** grab the installer `.exe` from the release assets — it bootstraps everything, and can optionally install the engine patches (backed-up, version-aware).
- **From PyPI:** `uv tool install "ff9mapkit[gui,assets,save]"` then `ff9mapkit setup` (detects your FF9 install, saves config, extracts base templates, and reports Memoria status).
- **Already installed?** `uv tool upgrade ff9mapkit`.
- Full walkthrough, prerequisites, and the CLI reference: [SETUP.md](SETUP.md).

## Provenance

Dream World IX ships **NO** FINAL FANTASY IX game data. It operates only on a copy of the game **you** already own, reading and patching your local install at build time. Base templates are regenerated from your own install via `ff9mapkit extract-templates`; no Square-Enix bytes are distributed. This is an unofficial, fan-made toolkit and is **not affiliated with, endorsed by, or associated with Square Enix**.

## License

Dream World IX / `ff9mapkit` is released under the **MIT License** (© 2026 GameJawnsInc). The bundled engine patches modify [Memoria](https://github.com/Albeoris/Memoria), which is likewise MIT-licensed (© Albeoris).