# CLAUDE.md — FF9 Custom-Field Toolkit (`ff9mapkit`, Memoria Engine)

> **Internal development brief — for AI coding agents (Claude Code), NOT user documentation.** This file
> orients an agent working *on* the toolkit; it is not a guide to *using* it, and it may reference local
> machine paths and dev workflow. **If you're here to use Dream World IX, start with**
> [`README.md`](README.md), [`SETUP.md`](SETUP.md), and the docs in [`ff9mapkit/docs/`](ff9mapkit/docs/).

> **The working brief — keep it lean.** Only durable, every-session facts live here. This file is loaded into
> **every** session, so bytes here are a standing tax. The narrative lives in `git log` (~1 descriptive commit
> per feature); deep procedures live in the skills + project-memory files (both §9); open arcs live in
> `studies/<arc>/PLAN.md`. As work lands, update **§5** and add at most a **one-line** entry to **§10**.
> **§10 house rule, enforced:** one line per pillar, **≤200 chars**, **at most one level of parentheses**,
> no dates, no test counts, no playtest quotes. If it needs more, it belongs in `studies/` or `git log`.

---

## 1. What this project is now

It began as "add one playable custom room to FF9 (Steam, Memoria engine)." **That is long done.** It is now **`ff9mapkit`**: a Python toolkit + Blender add-on that compiles a declarative **`field.toml`** into a complete drop-in Memoria mod — a brand-new FF9 field (camera, walkmesh, painted art, NPCs, dialogue, gateways, encounters, events, story branching, cutscenes, ladders, jumps, props, save points) — and can **import/fork any of FF9's ~674 real fields** faithfully. Further pillars: battles, campaigns/journeys, playable characters, custom models, custom overworld, items/equipment/shops.

**North star — fork FIDELITY:** keep refining forked fields until the kit can recreate the *functioning game itself* from them ("fork a real field → does it play identically?"). The *physical* layer (scene/walkmesh/camera/mechanics/object-carry) is largely faithful + in-game proven; the *narrative-state* layer is the weak axis (a fork boots at scenario-zero). Honest gap map: **`ff9mapkit/docs/FORK_FIDELITY.md`**.

**Where the code lives:** repo root holds the dev-loop tools at `tools/` and the GUI entry at `apps/`. The distribution dir is `ff9mapkit/`; **the Python package root is `ff9mapkit/ff9mapkit/`**. Bare package-relative paths appear throughout this brief, the skills, and the memory store (`content/mognet.py`, `eb/labelasm.py`, `scene/routes.py`, `world/interior.py`, …) — **all of them resolve under `ff9mapkit/ff9mapkit/`, never from the repo root.** Bundled examples live at **`ff9mapkit/examples/`** (vivi-hut, continent-v1, thirteenth-character, boletta, SHOWCASE, …); repo-root `examples/` holds only `stolen-ember`.

---

## 2. Hard constraints (non-negotiable)

- **I cannot PLAY the running game — but I CAN see it in static frames**: `tools/game_snap.ps1`
  captures the live FF9 window to a PNG I can read (PrintWindow; needs windowed/borderless, warns
  on exclusive-fullscreen black). Use it for visual verification (menus, art, alignment) whenever
  the game is up. Behavior/feel still needs the human: after any change that should be visible
  in-game, ask them to playtest and report. Never assume it worked because it built.
- **I cannot paint background art.** Pre-rendered backgrounds + their depth layers are a
  human/art task. (I *do* tell the human exactly where to paint via the projection math.)
- **The human owns final in-game alignment judgment.** I author the camera + walkmesh from
  math (this is solved — §7), but the human confirms it lands on the art in real gameplay.
- **Back up before editing any game/engine file** → `backups/<file>.<timestamp>`. The base
  game + the user's install are the only source of truth if we corrupt something.
- **One change per in-game test.** When a build breaks, we need to know which edit did it.
- **Commit FREELY when hitting tested milestones.** Commit on a feature branch → `master` with a good
  message. → `feedback-commit-freely`, `project-ff9-git-layout`.
- **PUBLIC status — LIVE.** Dream World IX shipped to public GitHub as **1.0.0b1** (2026-06-22); the old
  "NOTHING PUBLIC" gate is CLEARED. Public PRs / issues / a PyPI release / forum posts are FAIR GAME — but
  treat outward-facing actions (a release, a forum post) as **confirm-first** unless asked.
  → `feedback-commit-freely`, `project-release-readiness`.
- **NEVER open a PR to upstream `Albeoris/Memoria`** (they don't want AI-authored contributions). Not
  confirm-first — **banned outright.** This is about submission, not authorship: engine/DLL/C# work is fully
  in scope, it just stays local on the `memoria-patches/` stack pinned at `memoria-patches/BASE_COMMIT`.
  → `feedback-no-memoria-upstream-prs`.

**I CAN own, end to end:** the field event script (`.eb` bytecode, authored in Python — no
Hades Workshop), camera + walkmesh math, exits/gateways, triggers, flags, dialogue/text,
encounters + BGM + battle-bg metadata, the whole `ff9mapkit` codebase, the local Memoria
engine build, the build/deploy loop, version control, and all docs/notes.

---

## 3. Environment & key paths

| Thing | Path |
|---|---|
| Game install | `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\` |
| Live mod folders | `<game>\FF9CustomMap\` and `<game>\FF9CustomMap-world\` (StreamingAssets + DictionaryPatch.txt + BattlePatch.txt each) |
| Memoria source clone | `C:\gd\FFIX\Memoria\` (gitignored; the engine build tree — shared, not per-worktree) |
| Memoria.ini | `<game>\Memoria.ini` (engine toggles; dev build has boosters/ini cheats) |
| Toolkit | `ff9mapkit/` — CLI `py -m ff9mapkit <cmd>` (run from the kit root so the local pkg shadows any editable install) |
| Python package root | `ff9mapkit/ff9mapkit/` — **every bare `content/…`, `eb/…`, `world/…` path in the docs resolves here** |
| Deploy tool | `tools/deploy_field.py <field.toml> [--id N]` (**always pass `--id`** — no flag means the shared 4003 slot, ignoring the toml's own id) |
| GUI app | **`apps/ff9_workspace.pyw`** — the PySide6 **Workspace** front-door (tabs + Info Hub + Ctrl-K palette; PySide6 = optional `gui` extra). → the `working-on-the-ff9-workspace` skill |
| Reference field scripts | `reference/field-manifest.tsv` (HW-index→field-id→name; index ≠ field id). The 817 HW field-script exports are **not in the repo** — they live at `C:\gd\FFIX\reference\test2\` |
| FF9 field assets | `<game>\StreamingAssets\p0data*.bin` (UnityRaw 5.2.3 bundles; UnityPy reads them — `py -m pip install UnityPy`) |

> **Layout in one breath** (full detail → [[project-ff9-git-layout]]; deploy/collision detail → the `deploying-ff9-mods` skill):
> the working repo deploys into its OWN Memoria mod folder, pinned in a gitignored **`.ff9deploy.toml`** (`mod_folder` +
> scratch-band `id`; override via `--mod-folder`/`$FF9_MOD_FOLDER`). `Memoria.ini [Mod] FolderNames` stacks the folders
> **in priority order** — currently `"FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo"`; each folder's own
> DictionaryPatch/BattlePatch is read at launch. **Distinct ids are required even across folders** (EventDB/SceneData are
> GLOBAL — a collision is the classic null-`.eb` black screen). The overworld deploys to its own `-world` folder because
> campaign wholesale-replaces kept wiping `FF9CustomMap`'s WorldMap tree. Reach any slot via **~ → Warp**.
> **Field-id bands:** **10-3100** real (locked) · **4000-9899** shipped custom · **30000-32767** dev scratch
> (engine `fldMapNo` is Int16 → max **32767**; a higher id registers but is unreachable).
> **Scratch-band occupancy — check before minting a bench id:** 30000/30001/30002 (mod-folder slots) ·
> **30100-30200** co-op band (30110 twin altar · 30111 twin vault · 30112 diorama bench · 30100-30102 Stolen Ember) ·
> **30300** summons bench · **30400** Fort Condor / behavior bench · **30410-30415** behavior-tree benches
> (30410 demos · 30411 regression · 30412 showcase · 30413 pooled · 30414 BTROUTE · 30415 BTTABLE).
> **Workflow:** edits on a feature branch → `master`. `C:\gd\FFIX` is the read-only archive.
> ⚠ **Many agent worktrees run concurrently** and share ONE game install, ONE memory store, and ONE set of mod
> folders. Re-verify git and deploy state before any destructive action. → [[user-multi-account-worktree-sprawl]].

---

## 4. The dev loop (no relaunch needed)

The proven fast loop — **edit → deploy → ~**:

1. Author/edit a `field.toml` (by hand, the form editor, or a Blender export).
2. `py tools/deploy_field.py <field.toml> --id N` — builds + deploys reversibly into the slot; reverts the slot's prior deploy; writes a per-id `revert_deploy_<id>.py`.
3. In-game press **~ → Reload field** (re-reads the field's mod files from disk) **or → Warp to field → <id>**.
4. Ask the human to verify. Each change = one commit + one in-game check.

**Relaunch is only needed for:** the FIRST deploy of a *new* id (registers its DictionaryPatch line), a BattlePatch change, or an engine-DLL rebuild. Revert: `py tools/scroll_out/revert_deploy.py` (latest) or `revert_deploy_<id>.py`.
Text-block/`.mes` shadowing across stacked folders (wrong text, right flags) → the `deploying-ff9-mods` skill, [[project-ff9-text-block-shadow]]. Engine DLL builds (**AUTO-DEPLOY, no backup — DANGEROUS**) → the `building-the-memoria-engine` skill, [[project-ff9-memoria-build]].

---

## 5. Current state (keep this updated)

- **Dev engine** = stock Memoria `6b8bb2d5` + our patch stack in **`memoria-patches/`** (37 patches, s12–s58).
  **`memoria-patches/README.md` is the authoritative per-patch status table — read it rather than trusting a
  range quoted anywhere else.** The load-bearing groupings: **s22** debug menu · **s23–s33** the FORK-DONOR
  REMAP suite (every engine gate hardcoded on a real `fldMapNo`/FBG name wrapped to fire for a custom fork id) ·
  **s34/s35** overworld loose-mesh override + overlay-texture cache · **s36–s44, s54–s57** the netsync co-op
  suite · **s45/s46** the Folklore Codex screen + render rig · **s43** the debug-menu hotkey (F6 → tilde) ·
  **s47–s53, s58** the SFX/summon probes and the hybrid drive · **s49/s51** world-script crash guards.
  ⚠ Two distinct patches both numbered **s48** (`s48-debug-vehicle-rows`, `s48-sfx-output-capture`) — a known
  numbering collision; disambiguate by filename. Census + levers → the `building-the-memoria-engine` skill,
  [[project-ff9-doeventcode-fork-gates]], `ff9mapkit/docs/FORK_IDGATE_MAP.md`.
- **⚠ ENGINE-INDEPENDENCE IS SPLIT (durable):** a *novel* field runs on **stock** Memoria; a **FORKED field
  REQUIRES the s23–s33 suite** — so the shipped faithful-opening ships our CUSTOM Memoria (the
  `dwix-custom-memoria-*.zip` bundle IS the dev engine; **the debug menu (~) is user-facing, we keep + grow it**).
  Reverting the engine: check `tools/restore_memoria_dll.py` for the modes that currently work — the historical
  `baseline` set was removed from `backups/`, so that mode can fail loudly. True stock = re-run the patcher.
- **debug menu (~)** (Go / Cheats / Flags / Time; field + battle + overworld; ships in the bundle) → [[project-ff9-f6-overworld-debug]].
- **Vivi hut = retired offline build-oracle** (the byte-exact golden test, `ff9mapkit/examples/vivi-hut/`); do NOT re-polish it in-game.
- **New Game lands via a stock field-70 override (`Field(<id>)`), NOT a DLL edit** — WIPED by every `deploy_campaign` wholesale-replace → RE-RUN `tools/wire_newgame_from_stock.py 6000` after each opening re-deploy. → the `building-ff9-campaigns` skill, [[project-ff9-new-game-entry]].
- **TEXT BLOCKS: `text_block` defaults to the field's OWN id + auto-registers** (`MessageFile <id>`). mesID is ONE FLAT GLOBAL namespace shared with the BASE GAME — `FF9TextTool` merges per-txid cumulatively, so custom text on a REAL block OVERWRITES that location's dialogue with no stacking involved (1073 = Black Mage Village, 8 = Ice Cavern, 22 = Lindblum). There is NO free real block; "pick a real id no higher folder defines" is the ANTI-pattern. **A fork keeps its donor's block** (voice-acting + dual-language key off it). NEVER an offset band — consumption is Int16 (`(Int16)eventIDToMESID[...]`), so `40000+id` wraps and loads zero text. A registration change needs a RELAUNCH; content edits hot-reload (there is no content cache — the `FieldImporter` text guard is dead code). → [[project-ff9-text-block-shadow]], [[feedback-verify-the-cache-write-lands]].
- **STORY FLAGS: the safe band is `FIRST_SAFE_FLAG` = 8712+**, not 8512. Bits **8512-8711 are stock read-mail's
  payload bytes** (whole-byte-written by ordinary play) and **8376-8511 is the MOGNET lock band**. Allocating in
  the old band is a live save-corrupter. Source of truth: `ff9mapkit/ff9mapkit/flags.py`. → [[project-ff9-story-flags]].
- **Versions:** kit `1.0.0b17`, Blender add-on `0.9.28`. **Provenance gate CLEARED at HEAD** — zero Square-Enix binary bytes; templates regenerate from the user's own install (`ff9mapkit extract-templates`); the ONE documented game-text exception = `research/FLAG_LORE.md`'s ≤110-char dialogue excerpts (rationale in `ff9mapkit/docs/PROVENANCE.md`). → [[project-release-readiness]].
- **Test suite:** `py -m pytest -n 6`. **The count lives in [[project-ff9-test-suite-perf]], not here** — and read
  that memory before trusting a green run: **a fresh worktree silently SKIPS 479 byte-level tests** (no extracted
  template cache, so 15 files never even COLLECT and the run still reports green). That is how a black screen
  once reached a playtest. Run the suite in the MAIN repo, or extract templates into the worktree first.

---

## 6. The toolkit at a glance (all in-game proven)

Most capability domains route to a skill — see §9. Scenes (camera/walkmesh/art) · field scripts (NPCs/dialogue/gateways/encounters/cutscenes/ATEs/ladders/jumps/props/save points, and the `[behavior]` tree compiler) · forking (674 real fields, 4 modes, `fork-report`, `import-all`) · battles (incl. custom summons) · campaigns/journeys/World Hub · playable characters · custom models · items/equipment/shops + saves · overworld · the Workspace GUI.
Authoring surfaces: declarative `field.toml`; the scene.toml (spatial) / field.toml (logic) split; the form editor `ff9mapkit edit`; the Blender add-on; Info Hub catalogs (`models|animations|scenes|items|catalog`). Offline validation (I can't see the game): `ff9mapkit lint <toml>` / `ff9mapkit walkmesh verify <path>`.
Always **fork/learn from a real field's bytes** before authoring a new mechanic — every mechanic was grounded byte-for-byte against shipping FF9 data, not invented.

---

## 7. Deep recipes (moved to skills + memory) & process rules

The byte-level gotcha dump that lived here is load-on-demand — camera/canvas/walkmesh/BG-borrow math → `authoring-ff9-scenes`; `.eb` opcodes / RPN expressions / flag persistence / regions / encounters / cutscene choreography / behavior trees → `authoring-ff9-field-scripts`; deploy stack / text-block shadow / EventDB collisions → `deploying-ff9-mods`; fork gates (a hardcoded `fldMapNo`'s four forms + the levers) → `building-the-memoria-engine`.

**Process** — Hades Workshop is fully OUT (atlas-clone UV bug + its export corrupts entry-adds; author `.eb` in Python, verify with `eb_disasm`/the kit). Never edit a bundled example in place (the form editor's Save rewrites the byte-exact golden oracle — author on a copy / `ff9mapkit new` / a Blender export). Grep alone can't prove a field unused (scenario dispatch / computed ids / scripted warps are invisible to it) — trust the user's game knowledge; NarrowMapList is a camera-WIDTH table, NOT a cutscene trigger.
Work incremental + verbatim-first (study real bytes → replicate ONE piece → verify; offline ≠ in-game proof); zones organize, they don't constrain; for visual/positional bugs ask for in-game video EARLY. → `project-ff9-bg-borrow-solution`, `feedback-trust-user-game-knowledge`, `project-ff9-has-no-unused-fields`, `feedback-incremental-verbatim-first`, `feedback-zones-organize-not-constrain`, `feedback-video-for-visual-bugs`.

**Two laws minted the hard way, worth stating once:** *calibrate the instrument before you judge with it* — an
uncalibrated eye/probe has repeatedly produced confident, wrong verdicts (a probe that cannot reproduce the
lifecycle cannot falsify a lifecycle bug; an empty tempdir is not a clean room). And *a law in a docstring is a
wish* — a rule that isn't enforced at the call site isn't enforced.

---

## 8. Dead ends (proven — don't re-explore)

Each of these cost real rounds. The full record is in the linked study/memory; do not re-litigate from scratch.

- **HW "Export as Custom Field" atlas clone** — systemic UV bug (A/B tested on two bases). Use BG-borrow or `--editable` custom scenes.
- **HW adding a new `.eb` entry** — corrupts the file (overwrites the player object). Python only.
- **The FieldCreator editor's 5-point camera anchor on a flat floor** — mathematically degenerate.
- **Encoding a field warp as opcode `0x2A`** — that's `Battle`, not PreloadField → crash/black.
- **A uniform `orgPos/2` walkmesh slide / an `f0`-vs-`+org` frame auto-detector** — the import frame is always `vert + orgPos + floor.org`; no heuristic.
- **Per-pitch `sx/sy` canvas scale** — the map is exact scale-1; the "back-edge drift" was the character collision radius.
- **A no-art camera REFRAME on import** — it replaced the faithful pose on every artless fork and its floor-aim flips sign on up-pitched cameras. Removed.
- **Grafting a render-only NPC's talk handler into a NON-verbatim fork (#14)** — proven 0-tractable (census of 675 fields: an NPC's interactive tag-3 IS the field's quest logic, inseparable). Use **`--verbatim`**; read what an NPC does with **`fork-report --explain`**. Adding NEW *self-contained* kit content to a *verbatim* fork IS supported → [[project-ff9-npc-on-verbatim]].
- **From-scratch massif SYNTHESIS** — falsified over 8 rounds. Statistics reproduce the rock organization's measured properties, never its *look* (**THE FORM LESSON**). Use the carry: `world-mountain`. → [[project-ff9-overworld-interior-topography]].
- **Real content through a synthetic frame is still synthesis** — the v3 bend-carry and the dunes *label-stamp* pipeline both failed this way. A verbatim stamp must carry the **MESH** (verts+uvs+tangents), not row labels. The TRUE MESH CARRY is the working form.
- **The beach-mint ladder** (`world-island --beach`) — falsified over 4 playtests. **SUPERSEDED, goal achieved:** the `(7,17)` ground-retile carry (`world-transplant --ground desert`) puts a real beach on our islands.
- **The dunes MINT at small scale** — closed by law: the family has a **size class** (≥~130-cell footprint), so even genuine stock arrangement quilts on a ~31-cell blob. **SUPERSEDED at real scale** by the true mesh carry.
- **A canyon ISLAND** — off-language by THE WALL-CONTEXT LAW (canyon's red band is never open-sea coastal). Guarded at both chokepoints now.
- **Mixed-biome as a thin desert ribbon along a line** (rungs C/D/E) — **THE RIBBON FALLACY**. Stock's ecotone is the *margin of a desert mass*; the lawful unit is a two-ground landmass. → `studies/overworld-topography/`.
- **Path B: a compiled dynamic Chase/Wander region test in `.eb`** — falsified offline. There is no sound `(x,z)`→region test: cross products overflow the 26-bit CalcStack on 36% of fields, the AABB fallback misclassifies 20.8%, and `PathTo` sums with scripted Walk in the same frame. **KEEP THE DIVIDEND:** stock Memoria already gives `.eb` **computed array indexing** (`flexible_varfunc` token `0xD3`) → [[project-ff9-eb-script-tooling]].
- **Tracking a summon's creature by mesh bounds OR by the primitive stream** — both falsified. The hybrid drive (s58) poses a managed model from the native skeleton instead. → [[project-ff9-custom-summons]].
- **The self-summon `--action-prompt`/`--nameplate` overworld entrance** — too timing-fragile. **SUPERSEDED** by AREA-SWITCH SURGERY (repoint a dead area-switch case), which is the game's real native flow. → [[project-ff9-overworld-action-prompt]].

---

## 9. Project memory & skills (the deep recipes)

The technical detail this file only summarizes lives in two load-on-demand layers.

**Project memory** — `~/.claude/projects/C--gd-Dream-World-IX/memory/`, **122 topic files**. Only the index
**`MEMORY.md`** auto-loads each session; the topic files are read **on demand** by name. The index carries a
one-line hook per file. `project-ff9-skills-migration-plan.md` holds the skill→memory cross-reference table.
⚠ The store is **not under version control** and is **shared by every concurrent worktree session** — snapshot
before bulk edits, and prefer surgical edits over rewrites.
Foundational recipes, by name:
- `project-ff9-eb-script-tooling` (.eb format/opcodes/injection) · `project-ff9-story-flags` (gEventGlobal; safe band **8712+**) · `project-ff9-gateway-regions` (triggers, fade-before-`Field()`) · `project-ff9-encounters` (after-battle Main_Reinit fix)
- `project-ff9-camera-math` (k=14/15, scale-1 canvas) · `project-ff9-import-frame` (`vert + orgPos + floor.org`) · `project-ff9-novel-bg-pipeline` (painted BG / occlusion / `--native`)
- `project-ff9-object-carry` / `project-ff9-verbatim-fork` (faithful carry + the truest fork) · `project-ff9-field-logic-map` (edit a fork's `.eb` in place) · `project-ff9-memoria-build` (engine build toolchain)
- `project-ff9-battle-backgrounds` / `project-ff9-battle-tuning` (battle maps + tuning) · `project-ff9-overworld-coast-mosaic` (THE coast deep recipe — read its LAW INDEX before ANY coast work)

## Skills (load-on-demand procedures — `.claude/skills/`)
- deploying-ff9-mods — deploy/reload(~)/revert loop + collision debugging
- authoring-ff9-field-scripts — .eb bytecode, flags, gateways, encounters, cutscenes, `[behavior]` trees
- forking-ff9-fields — import/verbatim/native/editable + object carry
- authoring-ff9-scenes — camera/walkmesh/BG art from math + field media assets
- laying-out-ff9-fields — axes/cardinals/facing/scale + the offline layout probe (READ BEFORE placing content or narrating a direction)
- authoring-ff9-overworld — world-* terrain/coast (READ LAWS FIRST — bricks saves)
- authoring-ff9-battles — bg + tuning + Scripts-DLL + Overload + custom summons
- creating-ff9-characters — [[playable]] new party members + ability kits
- authoring-ff9-models — model-* import/mint/reskin/anim
- building-the-memoria-engine — DANGEROUS DLL rebuild + fork gates
- building-ff9-campaigns — import-chain / journeys / World Hub / New Game
- editing-ff9-items-and-saves — item/equip/shop CSVs + save-file editing
- working-on-the-ff9-workspace — the PySide6 Workspace GUI + `gui_snap` pixel verification

---

## 10. Milestones (status only — full story in `git log`, detail in §9)

> **Flat status list, NOT a journal.** One line per pillar, ≤200 chars, at most one paren level, no dates,
> no test counts, no playtest quotes. Open arcs keep their status in `studies/<arc>/PLAN.md`, not here.

**Foundations (S0–S23):** recon + build/test loop · MINT custom ids · BG-borrow · painted BGs + occlusion · Python `.eb` authoring · camera math · encounters + after-battle fix · local engine build · the kit + Blender add-on · scrolling · import/fork any real field · offline lint · multi-camera · events/branching/cutscenes · form editor + scene/field split · provenance gate cleared · dialogue choices · ladders · the debug menu · Info Hub catalogs.

**Pillars — all in-game proven:**
- Battle: backgrounds all tiers · tuning + palette-swap enemies · the Overload ONE-HUB · Scripts-DLL formulas/status · battle LOCATIONS → [[project-ff9-battle-tuning]], [[project-ff9-overload-hooks]], [[project-ff9-scripts-dll]], [[project-ff9-battle-locations]]
- Custom summons: the .seq substrate, a from-scratch creature, and the first faithful summon TRANSPLANT → [[project-ff9-custom-summons]], `studies/custom-summons/`
- Models: import/mint/reskin + new-clip authoring + alias-chain battle export + the from-scratch creature → [[project-ff9-custom-models]]
- Characters: 13th + 14th playable, zero DLL — bespoke kits, minted commands, custom abilities/status/effects → [[project-ff9-13th-character]], [[project-ff9-ability-preset-system]]
- Campaigns/journeys: `import-chain` + the Campaign-Editor IDE + the journey assembler + the World Hub + New Game + the first authored STORY campaign → [[project-ff9-stolen-ember-campaign]], [[project-ff9-world-hub]]
- Forking: faithful object/NPC carry + verbatim forks + additive content on them + `fork-report` + non-Zidane donors + gated-door carry → [[project-ff9-verbatim-fork]], [[project-ff9-fork-fidelity-worklist]]
- Field content: jumps · save points · story flags · ATEs · moving platforms · the STORY-EVENT DIRECTOR · Chocobo Hot & Cold → [[project-ff9-story-flags]], [[project-ff9-cutscene-multiactor]]
- Behavior trees ("the .eb programming language"): designer trees compiled to pure `.eb`, pooled units, auto-route, data tables → [[project-ff9-behavior-trees]], `studies/behavior-trees/PLAN.md`
- Fort Condor RTS: the swarm bench, the two-lane skirmish, placement/economy, waves + win/loss — rungs 0-4 → [[project-ff9-fort-condor-rts]], `studies/fort-condor/PLAN.md`
- Scene/art: offline field-art export + native repaint round-trip + FMV + SPS particles → [[project-ff9-novel-bg-pipeline]], [[project-ff9-native-repaint-workflow]], [[project-ff9-sps-authoring]]
- Items/saves: item/equip/shop + the save editor + custom weapon models + item text → [[project-ff9-items-equipment]], [[project-ff9-save-item-layout]]
- Overworld: entrances/buildings · reclaim/coast/island/water · verbatim transplant/fuse/growth · the coast-morph pillar · the first custom continent · productized `world-mountain|forest|hill|mirror|minimap` → [[project-ff9-overworld-coast-mosaic]], [[project-ff9-worldmap-feasibility]]
- Save moogles + MOGNET: the faithful save point, the 42nd moogle, the donor-fork class, read-mail → [[project-ff9-savepoint]], [[project-ff9-mognet-protocol]]
- Folklore Codex: an in-game bestiary submenu + the s46 render rig (live posed creature portraits) → [[project-ff9-folklore-codex-feasibility]], [[project-ff9-ngui-menu-construction]]
- Field entry: `[player] face` + per-entrance `[[player.arrival]]` dispatch + `entry_settle = "auto"` — arc CLOSED → [[project-ff9-field-entry-arrival]]
- Co-op (SHIPPED EXPERIMENTAL; the wire protocol changes release to release — **both machines must run the same DLL**): ghost sync, party/state mirror, battle co-op + diorama, field co-op → [[project-ff9-multiplayer-injector]], `studies/battle-coop/`, `studies/field-coop/`
- Sound: custom music/SFX, DLL-free → [[project-ff9-sound-music]] · GUI/Workspace + onboarding/installer → the `working-on-the-ff9-workspace` skill, [[project-ff9-installer-packaging]]
- Custom vehicles: physics is pure DATA (`TransportControls.csv`); a minted hull sails as a boat — rungs 0-2 → [[project-ff9-overworld-vehicles]], `studies/custom-vehicle/`
- Image→field EXPERIMENTAL → [[project-ff9-image-to-field]]

**Frontier (open arcs — status lives in the study, not here):**
- Overworld interior topography — the two-ground landmass (Rung F) → `studies/overworld-topography/`, [[project-ff9-overworld-interior-topography]]
- Narrative-state fork fidelity (a fork still boots at scenario-zero) → `ff9mapkit/docs/FORK_FIDELITY.md`, [[project-ff9-fork-fidelity-worklist]]
- Co-op field/dialogue lockstep (F3) — two-machine proof pending → `studies/field-coop/`
- Behavior-tree data tables — bench 30415 playtest pending → `studies/behavior-trees/PLAN.md`
- Tetra Master — feasibility done, near-fully data-moddable → [[project-ff9-tetra-master]], `studies/tetra-master/PLAN.md`

**Latest release:** kit **1.0.0b17** (tag pushed, CI green, PyPI live). Full changelog → `ff9mapkit/CHANGELOG.md` / `git log`.

---

## 11. Glossary

- **Field** — one explorable screen with a fixed-perspective pre-rendered background.
- **Walkmesh** — invisible per-floor geometry defining the walkable area + depth.
- **Main_Init / Main_Reinit** — a field script's entry function / its after-battle re-entry (entry-0 tag-10).
- **Gateway** — a region trigger that warps the player between fields.
- **BG-borrow vs custom scene** — reuse a real field's art (DictionaryPatch) vs ship our own `.bgx`+PNGs+`.bgi`.
- **field.toml / scene.toml** — the kit's logic file / Blender's spatial file (merged at build).
- **GLOB vs MAP flag** — save-persistent (`gEventGlobal`) vs per-field-transient story state.
- **debug menu (~)** — the in-game debug tool, shipped in the engine bundle (Go/Cheats/Flags; Time lives inside Cheats). Opened with the tilde/backquote key; was F6 until 2026-07-20 (F6 = stock Memoria's LvMax cheat).
