---
name: forking-ff9-fields
description: Fork or import any of FF9's ~674 real fields into a mod faithfully. Use when the user runs `ff9mapkit import` (`--verbatim`/`--native`/`--editable`), `fork-report`, `find-rooms`, or `list-fields`; wants to clone a shipping room; adds self-contained content onto a verbatim fork; or hits a lost behavior on a forked id (letterbox, off-mesh exemption, fake-battle return, SPS). Modes -- `--verbatim` = whole real `.eb`+`.mes`, remap only `Field()`; `--editable` = re-author scaffold, NOT a clone; `--native` = seamless per-tile. Covers faithful object/NPC/player-func/text carry, non-Zidane donors + `--swap-player`, firing a donor's story-gated cutscene, the scenario-zero narrative-state gap, and dead-end 14 (grafting a render-only talk handler into a non-verbatim fork). A forked field REQUIRES the custom-Memoria fork-gate suite. For building/patching that engine see `building-the-memoria-engine`; for authoring a NEW field from scratch see `authoring-ff9-scenes` + `authoring-ff9-field-scripts`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Forking FF9 Fields

The project's north star: fork a real field -> does it play identically? Keep refining forked
fields until the kit can recreate the *functioning game itself* from them. The honest gap map is
`ff9mapkit/docs/FORK_FIDELITY.md` (physical layer faithful + in-game proven; narrative state = the weak axis).

## Preview first with fork-report

Always run `ff9mapkit fork-report <field>` BEFORE forking — offline, it reads the field's compiled
`.eb` and reports the roster vs interaction axes (independent), story-gated beats, a suggested
`[startup]`, and the verdict: **CLEAN static-roster** (forks faithfully) vs **STORY-EVENT** (a
high-fidelity diorama). `fork-report <field> --explain` decodes the cast's talk routines into
readable English. Doc: `ff9mapkit/docs/FORK_REPORT.md`. Discover donors with `list-fields`
(`--players` / `--non-zidane`) and `find-rooms` (ranked swap/demo test rooms). A defect in the
Workspace's own realfield picker or fork-report panel: the `working-on-the-ff9-workspace` skill.

## Mode-selection decision table

Full matrix + the object-carry checklist: `references/fork-modes.md`. Quick rule: faithful clone ->
`--verbatim`; seamless per-tile art -> `--native`; re-author from a scaffold -> `--editable`
(an authoring scaffold, NOT a clone).

## What carries vs what is lost

Carries: NPCs / props / player-func / lighting / per-language text / object logic (and on
`--verbatim`, the donor's whole real `.eb` + `.mes`). Lost: narrative state — a fork boots at
**scenario-zero** (story-gated NPCs/doors/events default to the not-yet-happened branch), and a
synthesize fork spawns at one fixed point regardless of entrance (per-door spawn is `--verbatim`'s
job). Honest map: `ff9mapkit/docs/FORK_FIDELITY.md`.

## Non-Zidane donors & control bind

Control binds to the LAST `DefinePlayerCharacter` executed at field load (NOT the first — the kit's
old `pents[0]` guess mispredicts). A verbatim fork of a clean single-PC non-Zidane field plays
identically with zero new code. `--swap-player` (+ `--neutralize-gestures`) walks another rig;
`[party]` controls menu/battle party. Read memory `[[project-ff9-non-zidane-donors]]`,
`[[project-ff9-pc-party-system]]`.

## Firing a story-gated cutscene

Three things: fork the RIGHT visit-id (one FBG backs MULTIPLE field ids, one per story-visit —
`fork-report` each candidate), set `[startup] scenario = <the field's gate>` (fork-report's "Home
beat"), and clear the scene's once-flag via `[startup] flags` so it replays. Read memory
`[[project-ff9-fork-gated-cutscene]]`.

## Adding self-contained content onto a verbatim fork

ADDING NEW *self-contained* kit content — `[[npc]]` / `[[gateway]]` / `[[event]]` / `[[prop]]` /
`[[chest]]` — to a verbatim fork IS supported + in-game proven; it seats below the engine's last-9
party band. Pin a campaign chest's `flag = N` explicitly (named `[[flag]]` or safe-band index).
Read memory `[[project-ff9-npc-on-verbatim]]`.

## Dead-end #14 & no-unused-fields

Grafting an EXISTING render-only NPC's talk handler into a NON-verbatim fork is proven 0-tractable
(census of 675 fields: an NPC's interactive tag-3 IS the field's quest logic, inseparable). The
answer is **`--verbatim`**; read what an NPC does with `fork-report --explain`. Do NOT conflate
with the supported additive content above. Also: FF9 has no truly-unused fields — grep cannot
prove a field unused (scenario-counter dispatch / runtime-computed ids / scripted `Field()` warps
are invisible to it); trust the user's game knowledge. Read memory
`[[project-ff9-has-no-unused-fields]]`.

## Why forked -> needs custom Memoria

Any engine behavior hardcoded on a real `fldMapNo` (or FBG name) is LOST on a custom-id fork —
narrow-map letterbox, Dante's off-mesh exemption, the fake-battle return, SPS positions, the menu
LOCATION. So **a FORKED field REQUIRES the s23-s33 fork-gate suite (custom Memoria); a novel field
runs on stock**. One-paragraph summary + the ForkDonorPatch.txt deploy leg:
`references/fork-gate-summary.md`. Building/patching that engine: the
`building-the-memoria-engine` skill.

## Additional resources

- Docs: `ff9mapkit/docs/FORK_FIDELITY.md` (the gap map), `FORK_REPORT.md`, `OBJECT_CARRY.md`,
  `PLAYER_GRAFT.md`, `TEXT_CARRY.md`.
- Memory: `[[project-ff9-verbatim-fork]]` (the truest fork; editable = scaffold-not-clone lives
  here too), `[[project-ff9-object-carry]]`, `[[project-ff9-fork-fidelity-worklist]]`,
  `[[project-ff9-sps-fork]]`, `[[project-ff9-verbatim-music]]`.
