---
name: authoring-ff9-battles
description: Author custom FF9 battle content, zero DLL rebuild. Use for `battle-import`/`build`/`scene`/`list` (3D battle backgrounds -- reskin, loose-FBX, net-new scene, original `BBG_B###`), `battle-actions`/`ai`/`seq`/`patch`/`telemetry` (enemy+player tuning, AI `B_MEMBER` selectors, raw17 `btlseq` choreography, palette-swap enemies), or the `field.toml` blocks `[difficulty]`/`[rebalance]`/`[deathrules]` and `script`/`script.field`/`status` (the mod Scripts-DLL + Overload one-hub features -- engine battle formulas). Covers the 4-channel model (scene/CSV/AI/field), `BattlePatch Music` = akao song-play id NOT a file number, AI ((36)=cur.hp/(35)=max.hp), `[BattleScript(id>=256)]`/`[FieldAbilityScript]`/`[StatusScript]` compile-at-deploy surfaces, the Overload GRANULARITY LAW and returning-hook fail-safe-vanilla, and the 9999-cap needing `Memoria.ini BreakDamageLimit`. BattlePatch changes need a relaunch. For a playable character's ability KIT (via `[[playable]]`) see `creating-ff9-characters`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Authoring FF9 Battles

Every battle tier is DLL-free (no `Assembly-CSharp.dll` rebuild): backgrounds, stat/AI/choreography tuning, and encounter wiring are data patches on stock Memoria; a genuinely NEW engine formula lives in a separate mod `Memoria.Scripts.<Mod>.dll` compiled at deploy against the installed engine. A `BattlePatch.txt` / DictionaryPatch / Scripts-DLL change needs a game RELAUNCH (not F6-hot). The honest gap map + lever catalog: `ff9mapkit/docs/BATTLE_DESIGN.md`.

## The 4-channel model

Which file for which change — the channels do NOT share a format or merge mode:

1. **Per-enemy stats/affinities/rewards** = per-scene BINARY `dbfile0000.raw16` (`[scene]`/`[[scene.enemy]]` byte-patch, or `BattlePatch.txt` by name — the campaign-wide lever).
2. **Shared player abilities / statuses / growth** = `Data/Battle/*.csv` + `Data/Characters/*.csv` deltas (`[[battle_action]]`, `[[status]]`, `[[character]]`, ...).
3. **Enemy AI** = per-scene `EVT_BATTLE_*.eb` (the SAME `.eb` container + interpreter as field scripts).
4. **Encounter wiring** = per-field-script `SetRandomBattles` (`[encounter]` in field.toml) — not a global formation table.

Detail → `references/battle-tuning.md`.

## Backgrounds: the four tiers

Reskin (drop PNGs) / loose-FBX geometry swap / net-new scene mint (`BattleScene <ID> <NAME> <BBG>` DictionaryPatch + 4 mod assets — the `.mes` is LOAD-BEARING, missing = NRE, empty battle) / wholly original `BBG_B###` number (>177, static `.inb` is safe). CLI: `battle-import` → `battle-build` → `tools/deploy_battle.py` (reversible). If you mint a BG-borrow trigger FIELD for testing, its FieldScene `<area>` must be `>= 10` (single-digit areas black-screen — a FieldScene rule, see CLAUDE.md §7). Detail + camera authoring → `references/battle-backgrounds.md`.

## Tuning: stats / AI / btlseq

- **Stats:** `battle-scene <donor>` inspects a scene; `[scene]`/`[[scene.enemy]]` (raw16) + `[[battle_enemy]]`/`[[battle_attack]]` (BattlePatch by name) cover ~all per-enemy levers; `battle-actions` lists the player-side Actions.csv.
- **AI:** `battle-ai <scene>` disassembles; read a unit's own stats with `B_MEMBER(N)` — **(36)=cur.hp, (35)=max.hp** (NOT `B_CURHP`/`B_MAXHP`, which are party-slot reads). Boss AI gates on absolute HP — retuning `hp` can strand a phase threshold; patch constants via `[[scene.ai_patch]]` or use `[[scene.ai_phase]]` (relative `cur < max/N`).
- **Choreography:** `battle-seq <scene>` reads the raw17 `btlseq` body; `[[scene.seq_patch]]`/`seq_replace`/`seq_insert` edit it. The sequence interpreter ticks **~15 fps** — calibrate `Wait`/`Move` frames.

Detail + the B_MEMBER selector map → `references/battle-tuning.md`.

## Palette-swap enemies

`[[scene.enemy]] skin = { id = <mint>, hue = N }` (or `tint`/`textures`; optional `from`) mints a recolored variant model — a battle enemy's `Geo@30` takes a MINTED model id (i16, cap 32767). The variant keeps its OWN skeleton + Mot clips (no attack-retarget quirk). Needs a relaunch (DictionaryPatch `3DModel` line). → memory `[[project-ff9-battle-tuning]]`.

## Scripts-DLL surfaces

Three compile-at-deploy plugin surfaces in ONE mod DLL, no engine rebuild (relaunch to load): battle FORMULAS `script = { template/body }` → `[BattleScript(id>=256)]`; paired FIELD effects `script.field` → `[FieldAbilityScript]` (same scriptId, works in AND out of combat); STATUS behaviours `status = [{ template/body }]` → `[StatusScript]` (CustomStatus 33-63) + a minted StatusData row + `BuffIcon` panel icon + `over_model` on-model visual. Canonical doc: `ff9mapkit/docs/SCRIPTS_DLL.md`. Detail → `references/scripts-dll-overload.md`.

## Overload one-hub

From the brief (CLAUDE.md §10), verbatim: "the engine registers 1 IOverload\* implementer per interface per DLL, last-wins → the kit emits a single regenerated hub; features = plain static classes, mutators-before-observers, a collision gate, GENERIC deploy stickiness". "THE GRANULARITY LAW: a flag-gated Overload feature's toggle latency = its hook's fire cadence." Returning hooks (`OnGameOver`) are SINGLE-OWNER with fail-safe = vanilla. Laws quoted in full → `references/scripts-dll-overload.md`.

## [difficulty] / [rebalance] / [deathrules]

- `[difficulty]` — flag-gateable enemy HP/attack/magic scaling (`OnBattleInit`; flag bites per-BATTLE).
- `[rebalance]` — `player_damage`/`enemy_damage` HP-damage multiplier (`OnDamageFinalChanges`; flag bites per-HIT — the only way to scale what the PARTY deals). Damage past 9999 needs `Memoria.ini [Battle] BreakDamageLimit = 1` (the hook fires pre-cap; the engine clamps right after).
- `[deathrules]` — once-per-battle second-wind revive / `chance` / Eiko-removal on the `OnGameOver` verdict; flag clear = fully vanilla.

All three in-game proven 2026-07-11. → `references/scripts-dll-overload.md`.

## Telemetry & gotchas

- `battle-telemetry <mod> | --off | --report | --clear` — logs every calc to a JSONL; `--report` = per-ability balance stats. Telemetry IS the verification oracle for `[difficulty]`/`[rebalance]` (byte-exact scaled numbers).
- `BattlePatch Music:` = the akao **song-play id** (0 = Battle Theme), NOT a file number.
- BattlePatch / DictionaryPatch / Scripts-DLL changes need a RELAUNCH; F6 → Reload does not re-read them. Fully QUIT FF9 before a redeploy that touches the DLL (the running process memory-maps it — the title screen still holds it).
- FieldScene + BattleScene share the GLOBAL `EventDB[id]` — ids must be distinct across both, and across stacked mod folders.

## Boundary

This skill owns ENGINE formulas (`[BattleScript]`), battle backgrounds/tuning/AI/choreography, and `[difficulty]`/`[rebalance]`/`[deathrules]`. A playable character's `[[playable]]` ability KIT (CharacterPresetId, minted commands, custom active abilities, statuses attached to a character's spells, portraits, battle models/animsets) belongs to `creating-ff9-characters`.

## Additional resources

- Docs (Layer 3): `ff9mapkit/docs/BATTLE_DESIGN.md` (lever map, formats, roadmap), `ff9mapkit/docs/SCRIPTS_DLL.md` (formulas, Overload, toolchain, troubleshooting).
- Memory recipes (Layer 2, read on demand): [[project-ff9-battle-backgrounds]], [[project-ff9-battle-tuning]], [[project-ff9-battle-ai-members]], [[project-ff9-scripts-dll]], [[project-ff9-overload-hooks]].
