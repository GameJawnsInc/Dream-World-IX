# CLAUDE.md — FF9 Custom-Field Toolkit (`ff9mapkit`, Memoria Engine)

> **Internal development brief — for AI coding agents (Claude Code), NOT user documentation.** This file
> orients an agent working *on* the toolkit; it is not a guide to *using* it, and it may reference local
> machine paths and dev workflow. **If you're here to use Dream World IX, start with**
> [`README.md`](README.md), [`SETUP.md`](SETUP.md), and the docs in [`ff9mapkit/docs/`](ff9mapkit/docs/).

> **The working brief — keep it lean.** Only durable, every-session facts live here. The narrative lives in `git log` (~1 descriptive commit per feature); deep procedures live in the skills + project-memory files (both §9). As work lands, update **§5** and add at most a **one-line** entry to **§10** — never a paragraph.

---

## 1. What this project is now

It began as "add one playable custom room to FF9 (Steam, Memoria engine)." **That is long done.** It is now **`ff9mapkit`**: a Python toolkit + Blender add-on that compiles a declarative **`field.toml`** into a complete drop-in Memoria mod — a brand-new FF9 field (camera, walkmesh, painted art, NPCs, dialogue, gateways, encounters, events, story branching, cutscenes, ladders, jumps, props, save points) — and can **import/fork any of FF9's ~674 real fields** faithfully. Further pillars: battles, campaigns/journeys, playable characters, custom models, custom overworld, items/equipment/shops.

**North star — fork FIDELITY:** keep refining forked fields until the kit can recreate the *functioning game itself* from them ("fork a real field → does it play identically?"). The *physical* layer (scene/walkmesh/camera/mechanics/object-carry) is largely faithful + in-game proven; the *narrative-state* layer is the weak axis (a fork boots at scenario-zero). Honest gap map: **`ff9mapkit/docs/FORK_FIDELITY.md`**. Code lives at `ff9mapkit/` (package `ff9mapkit/ff9mapkit/`, Blender add-on `ff9mapkit/blender/`); the dev-loop tools at repo-root `tools/`.

---

## 2. Hard constraints (non-negotiable)

- **I cannot see the running game.** After any change that should be visible in-game,
  STOP and ask the human to playtest and report. Never assume it worked because it built.
- **I cannot paint background art.** Pre-rendered backgrounds + their depth layers are a
  human/art task. (I *do* tell the human exactly where to paint via the projection math.)
- **The human owns final in-game alignment judgment.** I author the camera + walkmesh from
  math (this is solved — §7), but the human confirms it lands on the art in real gameplay.
- **Back up before editing any game/engine file** → `backups/<file>.<timestamp>`. The base
  game + the user's install are the only source of truth if we corrupt something.
- **One change per in-game test.** When a build breaks, we need to know which edit did it.
- **Commit FREELY when hitting tested milestones.** Single-repo mode (worktrees shelved): commit on a
  feature branch → `master` with a good message. → `feedback-commit-freely`, `project-ff9-git-layout`.
- **PUBLIC status — LIVE.** Dream World IX shipped to public GitHub as **1.0.0b1** (2026-06-22); the old
  "NOTHING PUBLIC" gate is CLEARED. Public PRs / issues / a PyPI release / forum posts are FAIR GAME — but
  treat outward-facing actions (a release, a forum post, a PR to Memoria) as **confirm-first** unless asked.
  → `feedback-commit-freely`, `project-release-readiness`.

**I CAN own, end to end:** the field event script (`.eb` bytecode, authored in Python — no
Hades Workshop), camera + walkmesh math, exits/gateways, triggers, flags, dialogue/text,
encounters + BGM + battle-bg metadata, the whole `ff9mapkit` codebase, the local Memoria
engine build, the build/deploy loop, version control, and all docs/notes.

---

## 3. Environment & key paths

| Thing | Path |
|---|---|
| Game install | `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\` |
| Live mod folder | `<game>\FF9CustomMap\` (StreamingAssets + DictionaryPatch.txt + BattlePatch.txt) |
| Memoria source clone | `C:\gd\FFIX\Memoria\` (gitignored; the engine build tree — shared, not per-worktree) |
| Memoria.ini | `<game>\Memoria.ini` (engine toggles; dev build has boosters/ini cheats) |
| Toolkit | `ff9mapkit/` — CLI `py -m ff9mapkit <cmd>` (run from the kit root so the local pkg shadows any editable install) |
| Deploy tool | `tools/deploy_field.py <field.toml> [--id N]` (default test slot = field 4003) |
| GUI app | **`apps/ff9_workspace.pyw`** — the PySide6 **Workspace** front-door (tabs + Info Hub + Ctrl-K palette; PySide6 = optional `gui` extra). → [[project-ff9-gui-makeover]] |
| Reference field scripts | `reference/test2/` (gitignored, 817 HW field-script exports) + `reference/field-manifest.tsv` (HW-index→field-id→name; index ≠ field id) |
| FF9 field assets | `<game>\StreamingAssets\p0data*.bin` (UnityRaw 5.2.3 bundles; UnityPy reads them — `py -m pip install UnityPy`) |

> **Layout in one breath** (full detail → [[project-ff9-git-layout]]; deploy/collision detail → the `deploying-ff9-mods` skill):
> the working repo deploys into its OWN Memoria mod folder, pinned in a gitignored **`.ff9deploy.toml`** (`mod_folder` +
> scratch-band `id`; override via `--mod-folder`/`$FF9_MOD_FOLDER`). `Memoria.ini [Mod] FolderNames` stacks the folders;
> each folder's own DictionaryPatch/BattlePatch is read at launch. **Distinct ids are required even across folders**
> (EventDB/SceneData are GLOBAL). Slots: master → `FF9CustomMap`/**30000** · `-bb`/**30001** · `-ih`/**30002**; reach any
> via F6 → Warp. **Field-id bands:** **10-3100** real (locked) · **4000-9899** shipped custom · **30000-32767** dev
> scratch (engine `fldMapNo` is Int16 → max **32767**; a higher id registers but is unreachable). **Workflow:**
> single-repo out of `Dream-World-IX` master (worktrees shelved → [[project-ff9-git-layout]]); edits on a feature
> branch → `master`. `C:\gd\FFIX` is the read-only archive (Memoria source + old branches).

---

## 4. The dev loop (no relaunch needed)

The proven fast loop — **edit → deploy → F6**:

1. Author/edit a `field.toml` (by hand, the form editor, or a Blender export).
2. `py tools/deploy_field.py <field.toml> [--id N]` — builds + deploys reversibly into the test slot (default 4003 = `TESTROOM`); reverts the slot's prior deploy; writes a per-id `revert_deploy_<id>.py`.
3. In-game press **F6 → Reload field** (re-reads the field's mod files from disk) **or → Warp to field → <id>**.
4. Ask the human to verify. Each change = one commit + one in-game check.

**Relaunch is only needed for:** the FIRST deploy of a *new* id (registers its DictionaryPatch line), a BattlePatch change, or an engine-DLL rebuild. Revert: `py tools/scroll_out/revert_deploy.py` (latest) or `revert_deploy_<id>.py`.
Text-block/`.mes` shadowing across stacked folders (wrong text, right flags) → the `deploying-ff9-mods` skill, [[project-ff9-text-block-shadow]]. Engine DLL builds (**AUTO-DEPLOY, no backup — DANGEROUS**) → the `building-the-memoria-engine` skill, [[project-ff9-memoria-build]].

---

## 5. Current state (keep this updated)

- **Dev engine** = stock Memoria `6b8bb2d5` + the **F6 debug menu** (s22) + the **s23–s33 FORK-DONOR REMAP suite** (every engine gate hardcoded on a real `fldMapNo`/FBG name wrapped to fire for a custom fork id) + **s34** (loose-mesh overworld override) + **s35** (overlay-texture cache) + **s36** (netsync co-op ghost sync — LAN TCP + internet WS-relay) + **s37** (netsync BATTLE co-op B0+B1 — wire v3 typed frames, spectate panel, `GuestSlots` remote commands). Patches in `memoria-patches/`; census + levers → the `building-the-memoria-engine` skill, [[project-ff9-doeventcode-fork-gates]], `ff9mapkit/docs/FORK_IDGATE_MAP.md`.
- **⚠ ENGINE-INDEPENDENCE IS SPLIT (durable):** a *novel* field runs on **stock** Memoria; a **FORKED field REQUIRES the s23–s33 suite** — so the shipped faithful-opening ships our CUSTOM Memoria (the `dwix-custom-memoria-*.zip` bundle IS the dev engine; **F6 is user-facing, we keep + grow it**). Revert engine → `tools/restore_memoria_dll.py baseline`; true stock = re-run the patcher.
- **F6 debug menu** (Go / Cheats / Flags / Time; field + battle + overworld; ships in the bundle) → [[project-ff9-f6-overworld-debug]].
- **Vivi hut = retired offline build-oracle** (the byte-exact golden test, `examples/vivi-hut/`); do NOT re-polish it in-game. (4003 = the shared test slot.)
- **New Game lands via a stock field-70 override (`Field(<id>)`), NOT a DLL edit** — WIPED by every `deploy_campaign` wholesale-replace → RE-RUN `tools/wire_newgame_from_stock.py 6000` after each opening re-deploy. → the `building-ff9-campaigns` skill, [[project-ff9-new-game-entry]].
- **Versions:** kit `1.0.0b15`, Blender add-on `0.9.23`. **Provenance gate CLEARED at HEAD** — zero Square-Enix bytes; templates regenerate from the user's own install (`ff9mapkit extract-templates`). → [[project-release-readiness]].

---

## 6. The toolkit at a glance (all in-game proven)

Every capability domain routes to a skill — see the §9 Skills block: scenes (camera/walkmesh/art) · field scripts (NPCs/dialogue/gateways/encounters/cutscenes/ATEs/ladders/jumps/props/save points) · forking (674 real fields, 4 modes, `fork-report`, `import-all`) · battles · campaigns/journeys/World Hub · playable characters · custom models · items/equipment/shops + saves · overworld.
Authoring surfaces: declarative `field.toml`; the scene.toml (spatial) / field.toml (logic) split; the form editor `ff9mapkit edit`; the Blender add-on; Info Hub catalogs (`models|animations|scenes|items|catalog`). Offline validation (I can't see the game): `ff9mapkit lint <toml>` / `ff9mapkit walkmesh verify <path>`.
Always **fork/learn from a real field's bytes** before authoring a new mechanic — every mechanic was grounded byte-for-byte against shipping FF9 data, not invented.

---

## 7. Deep recipes (moved to skills + memory) & process rules

The byte-level gotcha dump that lived here is now load-on-demand — camera/canvas/walkmesh/BG-borrow math → `authoring-ff9-scenes`; `.eb` opcodes / RPN expressions / flag persistence / regions / encounters / cutscene choreography → `authoring-ff9-field-scripts`; deploy stack / text-block shadow / EventDB collisions → `deploying-ff9-mods`; fork gates (a hardcoded `fldMapNo`'s four forms + the levers) → `building-the-memoria-engine`.

**Process** — Hades Workshop is fully OUT (atlas-clone UV bug + its export corrupts entry-adds; author `.eb` in Python, verify with `eb_disasm`/the kit). Never edit a bundled example in place (the form editor's Save rewrites the byte-exact golden oracle — author on a copy / `ff9mapkit new` / a Blender export). Grep alone can't prove a field unused (scenario dispatch / computed ids / scripted warps are invisible to it) — trust the user's game knowledge; NarrowMapList is a camera-WIDTH table, NOT a cutscene trigger.
Work incremental + verbatim-first (study real bytes → replicate ONE piece → verify; offline ≠ in-game proof); zones organize, they don't constrain; for visual/positional bugs ask for in-game video EARLY. → `project-ff9-bg-borrow-solution`, `feedback-trust-user-game-knowledge`, `project-ff9-has-no-unused-fields`, `feedback-incremental-verbatim-first`, `feedback-zones-organize-not-constrain`, `feedback-video-for-visual-bugs`.

---

## 8. Dead ends (proven — don't re-explore)

- **HW "Export as Custom Field" atlas clone** — systemic UV bug (A/B tested on two bases). Use
  BG-borrow or `--editable` custom scenes instead.
- **HW adding a new `.eb` entry** — corrupts the file (overwrites the player object). Python only.
- **The FieldCreator editor's 5-point camera anchor on a flat floor** — mathematically degenerate.
- **Encoding a field warp as opcode `0x2A`** — that's `Battle`, not PreloadField → crash/black.
- **A uniform `orgPos/2` walkmesh slide / an `f0`-vs-`+org` frame auto-detector** — the import
  frame is always `vert + orgPos + floor.org`; no heuristic.
- **Per-pitch `sx/sy` canvas scale** — the map is exact scale-1; the "back-edge drift" was the
  character collision radius, not a map error.
- **Grafting a render-only NPC's talk handler into a NON-verbatim fork (#14)** — proven 0-tractable (census of
  675 fields: an NPC's interactive tag-3 IS the field's quest logic, inseparable). Use **`--verbatim`**; read
  what an NPC does with **`fork-report --explain`**. (Adding NEW *self-contained* kit content to a *verbatim*
  fork IS supported — a different problem → [[project-ff9-npc-on-verbatim]].)

---

## 9. Project memory & skills (the deep recipes)

The full technical detail this file only summarizes lives in the project-memory store, **auto-loaded each session** and indexed by its `MEMORY.md` (`~/.claude/projects/C--gd-Dream-World-IX/memory/`) — a one-line hook for all **90** topic files (consolidated 2026-07-11; MEMORY.md's skills cross-reference maps each skill to the memory files it loads). Foundational recipes, by name:
- `project-ff9-eb-script-tooling` (.eb format/opcodes/injection) · `project-ff9-story-flags` (gEventGlobal, safe band 8512) · `project-ff9-gateway-regions` (triggers, fade-before-`Field()`) · `project-ff9-encounters` (after-battle Main_Reinit fix)
- `project-ff9-camera-math` (k=14/15, scale-1 canvas) · `project-ff9-import-frame` (`vert + orgPos + floor.org`) · `project-ff9-novel-bg-pipeline` (painted BG / occlusion / `--native`)
- `project-ff9-object-carry` / `project-ff9-verbatim-fork` (faithful carry + the truest fork) · `project-ff9-field-logic-map` (edit a fork's `.eb` in place) · `project-ff9-memoria-build` (engine build toolchain)
- `project-ff9-battle-backgrounds` / `project-ff9-battle-tuning` (battle maps + tuning) · `project-ff9-overworld-coast-mosaic` (THE coast deep recipe — read before ANY coast work)

## Skills (load-on-demand procedures -- .claude/skills/)
- deploying-ff9-mods — deploy/F6/revert loop + collision debugging
- authoring-ff9-field-scripts — .eb bytecode, flags, gateways, encounters, cutscenes
- forking-ff9-fields — import/verbatim/native/editable + object carry
- authoring-ff9-scenes — camera/walkmesh/BG art from math
- authoring-ff9-overworld — world-* terrain/coast (READ LAWS FIRST — bricks saves)
- authoring-ff9-battles — bg + tuning + Scripts-DLL + Overload
- creating-ff9-characters — [[playable]] new party members + ability kits
- authoring-ff9-models — model-* import/mint/reskin/anim
- building-the-memoria-engine — DANGEROUS DLL rebuild + fork gates
- building-ff9-campaigns — import-chain / journeys / World Hub / New Game
- editing-ff9-items-and-saves — item/equip/shop CSVs + save-file editing

---

## 10. Milestones (status only — full story in `git log`, detail in §9)

> Keep this a flat status list, NOT a journal. Add a one-line entry when a pillar lands; never a paragraph.

**Foundations (S0–S23):** recon + build/test loop · MINT custom ids · BG-borrow (area ≥10) · painted BGs + occlusion · Python `.eb` authoring · camera math (scale-1 canvas) · encounters + after-battle fix · local engine build · the kit + Blender add-on · scrolling · import/fork any real field · faithful `.bgi` + editable/native forks · offline lint · multi-camera · events/branching/cutscenes + flag persistence · form editor + scene/field split · provenance gate cleared (zero SE bytes) · dialogue choices · ladders · the F6 menu · Info Hub catalogs.

**Pillars (all in-game proven — detail in the named memory + `git log`):**
- Battle: backgrounds all tiers · tuning + palette-swap enemies · telemetry · the Overload ONE-HUB (`[difficulty]`/`[rebalance]`/`[lowhp]`/`[deathrules]` incl. second wind + on_defeat wipe-warp with OUTPOSTS ("last camp entered", the kit's first computed `Field(<var>)`); the GRANULARITY LAW; returning hooks single-owner) · Scripts-DLL formulas/field-effects/status → [[project-ff9-battle-backgrounds]], [[project-ff9-battle-tuning]], [[project-ff9-overload-hooks]], [[project-ff9-scripts-dll]]
- Models: import/mint/reskin + new-clip authoring (band 60000-65535) + alias-chain battle export + bone display labels + the from-scratch creature → [[project-ff9-custom-models]], [[project-ff9-battle-model-export-gap]], [[project-ff9-bone-semantic-labels]]
- Characters: 13th + 14th playable (`[[playable]]`, zero DLL — bespoke kits, minted commands, custom abilities + status + effect, custom battle model/animset/portrait) → [[project-ff9-13th-character]], [[project-ff9-ability-preset-system]]
- Campaigns/journeys: `import-chain` + the Campaign-Editor IDE + the journey assembler + the World Hub + the New-Game starting-state capstone + **the FIRST authored STORY campaign** (The Stolen Ember, `examples/stolen-ember` — the full narrative vocabulary composed on one 3-field/4-beat arc, ★ in-game proven end-to-end incl. save persistence + sabotage-proof cutscenes; the composition hardened the conductor: control WATCHDOG + follow-walks → [[project-ff9-stolen-ember-campaign]]) → [[project-ff9-import-chain-coverage]], [[project-ff9-world-hub]], [[project-ff9-journey-single-folder]]
- Forking: faithful object/NPC carry + verbatim forks + additive content on them + `fork-report` (+ Party-need & Story-writes axes) + non-Zidane donors + rotating-cast NPCs (`scenario_min/max`) + player-call gated-door carry (★ CLOSED — all 3 census carries 254/553/1904 in-game proven incl. sprint-entry + the 1904 full door-OPEN choreography (gesture + BG tile-anim swing + push-through walk); the ARMING-ORDER law — player InitObject before door InitRegion, `activate(after_player=True)`) → [[project-ff9-verbatim-fork]], [[project-ff9-npc-on-verbatim]], [[project-ff9-fork-fidelity-worklist]], [[project-ff9-non-zidane-donors]], [[project-ff9-pc-party-system]]
- Field content: jumps + save points + story flags (3 scopes) + ATEs + moving platforms (`--verbatim` carries; declarative `[[platform]]` = frontier) + the field logic-map + the verbatim authoring set (`[music]`, `opens_shop`, multi-actor cutscenes) + the STORY-EVENT DIRECTOR (`[[cutscene]]` DISPATCH: several beat-gated `requires_scenario`/`set_scenario` scenes per field, distinct-gate rule — a field re-stages itself across the story; closes #13 with the rotating cast) + Chocobo Hot & Cold + InfoHub authoring → [[project-ff9-story-flags]], [[project-ff9-field-logic-map]], [[project-ff9-chocobo-hot-cold]], [[project-ff9-moving-platforms-elevators]], [[project-ff9-cutscene-multiactor]]
- Scene/art: offline field-art export + native repaint round-trip + FMV + SPS particles → [[project-ff9-novel-bg-pipeline]], [[project-ff9-native-repaint-workflow]], [[project-ff9-fmv-pipeline]], [[project-ff9-sps-authoring]]
- Items/saves: item/equip/shop + the save editor + custom weapon models + item text → [[project-ff9-items-equipment]], [[project-ff9-save-item-layout]], [[project-ff9-item-text]]
- Overworld: entrances/buildings + reclaim/coast/island/water + verbatim transplant/fuse/growth + the coast-morph pillar + beach-mint (rungs 1–3 + the REAL-SCALE island-B mint: `bank_lower` + the per-column lip anchor; DECLARATIVE in fuse layouts/CLI — zero-byte-diff proven) + the FIRST CUSTOM CONTINENT (`examples/continent-v1/`) → [[project-ff9-overworld-coast-mosaic]], [[project-ff9-worldmap-feasibility]], [[project-ff9-first-continent-proposal]]
- Sound: custom music/SFX, DLL-free → [[project-ff9-sound-music]] · GUI/Workspace + onboarding/installer → [[project-ff9-gui-makeover]], [[project-ff9-installer-packaging]] · Multiplayer ghost-sync (s36) — LAN direct-TCP AND internet WS-relay ★ both in-game proven 2026-07-11; one-command setup **`ff9mapkit coop host|join`** + the in-game status overlay (★ proven 2026-07-12, cross-version pairing OK) + a Workspace **Co-op tab** (smoke-proven; ⚠ a session THROUGH the tab is UNVERIFIED — deferred, needs the second machine) + **`[Netsync]` hot-reload** (a running game applies coop-CLI/tab/hand edits in ~2s, ★ proven 2026-07-12) + **co-op EVERYWHERE** (`TargetField=0` default — ghosts on any shared screen, session-long transport, field-0 sentinel fixes the frozen-ghost-on-leave bug; ★ solo tier proven 2026-07-12) + **non-Zidane ghosts** (wire v2: the ghost wears the peer's own model + their submesh mask, Zidane = fallback only; ★ solo tier proven 2026-07-12 incl. mid-session re-dress; MIXED DLL VERSIONS NO LONGER SYNC — update both machines; cross-machine bits → the memory's LAPTOP BACKLOG) + **ghost lighting** (the mapconfig per-char `_Color` tint replicated at spawn — the last cosmetic gap, ★ proven 2026-07-12; the ghost has NO known cosmetic gaps left) + **BATTLE co-op B0+B1 (s37, wire v3)** — spectate panel + networked controller-2 (`[Netsync] GuestSlots`, [1-8]/[0] assist keys, RemoteMenuOpen WAIT-freeze, digit swallow; ★ solo tier proven 2026-07-12, two-machine pending — v3 rejects v2 peers, update BOTH DLLs; → `studies/battle-coop/`); ⚠ public ship deliberately HELD — flesh out multiplayer first, no release/bundle re-cut until asked (.NET bridge exe dropped; engine-auto-spawn bridge = consideration only) → [[project-ff9-multiplayer-injector]] · Image→field EXPERIMENTAL → [[project-ff9-image-to-field]]

**Frontier:** the REAL-SCALE island-B mint is ★ FULLY PROVEN (beach approved + cliffs "look good now, no more gashes" — the per-COLUMN lip anchor + the V-IN-BAND gate close the coast-morph/beach-mint arc); the OVERWORLD deploys to the dedicated **`FF9CustomMap-world`** folder (campaign wholesale-replaces kept wiping FF9CustomMap's WorldMap tree) → [[project-ff9-overworld-coast-mosaic]], [[project-ff9-git-layout]]; the CONTINENT ENTRANCE pair ★ IN-GAME PROVEN (--field-direct + the arrive= worldmap exit; the waystation 6500 full loop closes on island C); `world-minimap` ★ IN-GAME PROVEN (the geometry-REGISTERED art frame; art-true chosen — the ~30px-west icon bias is an s37 engine candidate) → [[project-ff9-worldmap-feasibility]]; declarative `[[platform]]`; the story-event director (#13) — authoring side proven → [[project-ff9-fork-fidelity-worklist]]; **INTERIOR TOPOGRAPHY** is the active study arc (the 260-block census + the TERRACE LAW; the FOREST rung ★ in-game proven — the CANOPY CARRY + STEP laws, verbatim blob carry on the (3,14) bench pad; the GRASS-ISLAND CANVAS is ★ IN-GAME PROVEN — archipelago island E, `world-island` seed 55 at (344,−1152) blocks (4–5,17–18)+(6,18) in FF9CustomMap-world (round 1 minted the missing-block law + the OPEN-OCEAN TARGET gate now IN world-island); the FOREST is RE-HOMED onto E's west lobe ★ IN-GAME PROVEN ("walked the whole rim aggressively, no more sticking") — the stuck report minted the COMPREHENSIVE CANOPY STEP LAW (climb = surface-to-surface per ~0.44u foot step; vertical walls un-hittable; DESCENT ALWAYS LEGAL — ff9.rayDistance is dead code, placement sim corrected) + the per-station rim lift + the perimeter walk-in gate (`forest_rehome.py`); the (3,14) bench is RETIRED (real land restored); the HILL AT SCALE ★ IN-GAME PROVEN ("looks natural, walkable from all sides" — the measured grass-hill language: slope p99 28.6°, pure-grass summits real, raised-cosine H=4.2/R=18 as pure-Y displacement of deployed bytes); the PLATEAU-EDGE study ★ DONE (the 27u rim / soft 50° crest / NO lip row inland / interior walls = a QUANTIZED 128px TILE LANGUAGE not the coastal strip and not murals — synthesis ON pending the rock tile-neighbor decode / STACKED 4–10u faces / the NO-FOOT-PASS finding: the altitude worlds never connect by walking, terraces need no ramp); the ROCK TILE-NEIGHBOR decode ★ DONE (86 tiles in 4-col ROLE BANDS crest/body/base, ONE tile per ~4.7u wall quad course, WINDOWED CONTINUATION with band wrap — the terrace-wall rung is UNBLOCKED with a full synthesis recipe); next on E: the terrace+wall build rung / carried stream/falls / `world-forest`+`world-hill` productization) → [[project-ff9-overworld-interior-topography]], `studies/overworld-topography/`.
**Latest:** kit **1.0.0b15**, 3283 tests (`py -m pytest -n 6`) — the Overload battle-balance hub (`[difficulty]`/`[rebalance]`/`[deathrules]`), Chocobo Hot & Cold, the first hand-built continent + the coast-morph pillar + beach-mint (shore vocabulary now closed), battle-model export gap closed, bone display labels, image-field `--auto-floor`/real-photo proof, and the skills+brief refactor (§9); the engine bundle is unchanged from b12/b13 (s35, the s22 block-dump, s36 multiplayer still held for a from-source rebuild). Full changelog → `ff9mapkit/CHANGELOG.md` / `git log`.

---

## 11. Glossary

- **Field** — one explorable screen with a fixed-perspective pre-rendered background.
- **Walkmesh** — invisible per-floor geometry defining the walkable area + depth.
- **Main_Init / Main_Reinit** — a field script's entry function / its after-battle re-entry (entry-0 tag-10).
- **Gateway** — a region trigger that warps the player between fields.
- **BG-borrow vs custom scene** — reuse a real field's art (DictionaryPatch) vs ship our own `.bgx`+PNGs+`.bgi`.
- **field.toml / scene.toml** — the kit's logic file / Blender's spatial file (merged at build).
- **GLOB vs MAP flag** — save-persistent (`gEventGlobal`) vs per-field-transient story state.
- **F6 debug menu** — the in-game debug tool, shipped in the engine bundle (Go/Cheats/Flags/Time).
