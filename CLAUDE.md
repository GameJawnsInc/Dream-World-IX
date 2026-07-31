# CLAUDE.md — FF9 Custom-Field Toolkit (`ff9mapkit`, Memoria Engine)

> **Internal development brief — for AI coding agents, NOT user documentation.** It orients an agent
> working *on* the toolkit and references local machine paths. **To USE Dream World IX, start with**
> [`README.md`](README.md), [`SETUP.md`](SETUP.md), and [`ff9mapkit/docs/`](ff9mapkit/docs/).

> **KEEP THIS LEAN — it loads into every session, so bytes here are a standing tax.**
> Only facts that change what an agent DOES on an ordinary day. Everything else has a home already:
> the narrative → `git log` (~1 descriptive commit per feature) · deep procedures → the skills · deep
> knowledge → the project-memory store (its `MEMORY.md` index auto-loads; the topic files are
> on-demand) · open arcs → `studies/<arc>/PLAN.md` · shipped features → `ff9mapkit/CHANGELOG.md`.
> **Do not re-list here what the harness already injects** — the skill roster and the memory index
> arrive in context on their own.
> **§10 house rule, enforced:** one line per entry, ≤200 chars, at most one level of parentheses,
> no dates, no test counts, no playtest quotes. If it needs more, it belongs in `studies/` or `git log`.
> Pre-2026-07-24 detail → [`.claude/archive/brief-2026-07-24-preconsolidation.md`](.claude/archive/brief-2026-07-24-preconsolidation.md).

---

## 1. What this project is now

**`ff9mapkit`** — a Python toolkit + Blender add-on that compiles a declarative **`field.toml`** into a
drop-in Memoria mod: a brand-new FF9 field (camera, walkmesh, art, NPCs, dialogue, gateways, encounters,
events, cutscenes, props, save points) — and can **import/fork any of FF9's ~674 real fields** faithfully.
Pillars beyond fields: battles, campaigns/journeys, playable characters, custom models, custom overworld,
items/equipment/shops, co-op. (Inventory of what's shipped → the auto-loaded memory index + `ff9mapkit/CHANGELOG.md`.)

**North star — fork FIDELITY:** refine forked fields until the kit can recreate the *functioning game*
from them. The *physical* layer (scene/walkmesh/camera/mechanics/object-carry) is largely faithful and
in-game proven; the *narrative-state* layer is the weak axis — a fork boots at scenario-zero. Honest gap
map: **`ff9mapkit/docs/FORK_FIDELITY.md`**.

**Where code lives:** `tools/` (dev-loop scripts) · `apps/` (GUI entry) · `ff9mapkit/` (distribution) ·
**`ff9mapkit/ff9mapkit/` (the Python package root)**. Bare package-relative paths throughout the docs,
skills, and memory (`content/mognet.py`, `eb/labelasm.py`, `world/interior.py`, …) **all resolve under
`ff9mapkit/ff9mapkit/`, never the repo root.** Bundled examples are at **`ff9mapkit/examples/`**;
repo-root `examples/` holds only `stolen-ember`.

---

## 2. Hard constraints (non-negotiable)

- **I cannot PLAY the game — but I CAN see it in static frames**: `tools/game_snap.ps1` captures the live
  FF9 window to a PNG I can read (needs windowed/borderless). Use it for visual checks whenever the game
  is up. Behavior and feel still need the human — after any change that should be visible in-game, ask
  them to playtest. **Never assume it worked because it built.**
- **I cannot paint background art.** Pre-rendered backgrounds + depth layers are a human/art task. (I *do*
  tell the human exactly where to paint, via the projection math.)
- **The human owns final in-game alignment judgment.** I author camera + walkmesh from math; they confirm
  it lands on the art in real gameplay.
- **Back up before editing any game/engine file** → `backups/<file>.<timestamp>`. The base game + the
  user's install are the only source of truth if we corrupt something.
- **One change per in-game test.** When a build breaks we must know which edit did it.
- **Commit FREELY at tested milestones** — feature branch → `master`, good message. From a worktree you
  cannot check out `master` (the main repo holds it) — use `git -C C:\gd\Dream-World-IX`, and check what
  branch it is actually on first. → `feedback-commit-freely`, [[project-ff9-main-repo-branch-trap]].
- **PUBLIC — LIVE.** Shipped to public GitHub as 1.0.0b1. Public PRs / issues / PyPI / forum posts are
  fair game, but treat outward-facing actions (a release, a post) as **confirm-first** unless asked.
  → `project-release-readiness`.
- **NEVER open a PR to upstream `Albeoris/Memoria`** — banned outright, not confirm-first (they don't want
  AI-authored contributions). Submission ban, not authorship ban: engine/DLL/C# work stays fully in scope,
  local, on the `memoria-patches/` stack. → `feedback-no-memoria-upstream-prs`.

**I CAN own end to end:** the `.eb` event script (authored in Python — no Hades Workshop), camera +
walkmesh math, gateways/triggers/flags, dialogue/text, encounters + BGM + battle-bg metadata, the whole
`ff9mapkit` codebase, the local Memoria engine build, the build/deploy loop, version control, and docs.

---

## 3. Environment & key paths

| Thing | Path |
|---|---|
| Game install | `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\` |
| Live mod folders | `<game>\FF9CustomMap\` and `<game>\FF9CustomMap-world\` (each: StreamingAssets + DictionaryPatch.txt + BattlePatch.txt) |
| Memoria source clone | `C:\gd\FFIX\Memoria\` (gitignored; shared, not per-worktree) |
| Toolkit CLI | `py -m ff9mapkit <cmd>` — run from `ff9mapkit/` so the local pkg shadows any editable install |
| Deploy | `tools/deploy_field.py <field.toml> --id N` — **always pass `--id`**; without it you get the shared 4003 slot, ignoring the toml's own id |
| GUI | `apps/ff9_workspace.pyw` (PySide6 Workspace; optional `gui` extra) |
| Field-script reference | `reference/field-manifest.tsv` (HW-index→field-id→name; **index ≠ field id**). The 817 HW exports are **not in the repo** — `C:\gd\FFIX\reference\test2\` |
| FF9 field assets | `<game>\StreamingAssets\p0data*.bin` (UnityRaw 5.2.3; UnityPy reads them) |

**Deploy layout** (detail → the `deploying-ff9-mods` skill, [[project-ff9-git-layout]]): each worktree
**MUST pin its own deploy target** in a gitignored **`.ff9deploy.toml`** (`mod_folder`; `campaign_id_base`
if you compose a set) — without one you silently share the default folder with every other session.
⚠ **But do NOT pin `id` there.** It is not private: `workspace/builddoc.py:172` is
`tid = self.worktree_id or 4003`, so it RENAMES the Build tab's "Test slot NNNN" radio for whoever
launches the Workspace from that tree — **and that is the human**. It cost a playtest: a pinned scratch id
became the owner's default test slot, their next deploy landed there instead of the in-place target they
meant, and it wiped a room that was mid-playtest. **Pass `--id` explicitly instead** (already mandated
above). The same leak bites tests — pin the path through a seam, never read the real file. Override via
`--mod-folder` / `$FF9_MOD_FOLDER`. `Memoria.ini [Mod] FolderNames` stacks folders in priority order —
currently `"FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo"` — and each folder's own
DictionaryPatch/BattlePatch is read at launch. The overworld has its own `-world` folder because campaign
wholesale-replaces kept wiping `FF9CustomMap`'s WorldMap tree.

⚠ **Distinct ids are required even ACROSS folders — EventDB/SceneData are GLOBAL.** A collision is the
classic null-`.eb` black screen. **Bands:** `10-3100` real (locked) · `4000-9899` shipped custom, but
**`9000-9012` is a RESERVED HOLE** (engine world-map location ids — a `FieldScene` there clobbers the world
scripts) · `30000-32767` dev scratch (`fldMapNo` is Int16, max **32767**; a higher id registers but is
unreachable).
**Before minting an id, read the live registrations** — `<mod folder>/DictionaryPatch.txt` is the only
truth, and it changes as sessions deploy: `grep -oE "FieldScene [0-9]+" <game>/FF9CustomMap/DictionaryPatch.txt`.
(At the time of writing that listed 4003/4005/4007/4008/4012 and 30003, 30020, 30110-30112, 30210, 30300,
30301, 30400, 30410-30415 — treat as a sample, not a registry.)

⚠ **Many agent worktrees run concurrently**, sharing ONE game install, ONE memory store, and ONE set of
mod folders. Re-verify git and deploy state before any destructive action.
→ [[user-multi-account-worktree-sprawl]].

---

## 4. The dev loop (no relaunch needed)

1. Author/edit a `field.toml` (by hand, the form editor, or a Blender export).
2. `py tools/deploy_field.py <field.toml> --id N` — builds + deploys reversibly; reverts the slot's prior
   deploy; writes a per-id `revert_deploy_<id>.py`.
3. In-game press **~ → Reload field** (re-reads the field's mod files) **or → Warp to field → <id>**.
4. Ask the human to verify. Each change = one commit + one in-game check.

**Relaunch only for:** the FIRST deploy of a *new* id (registers its DictionaryPatch line), a BattlePatch
change, or an engine-DLL rebuild (**AUTO-DEPLOYS over the live install with no backup — DANGEROUS**).
Revert a field: `tools/scroll_out/revert_deploy.py` or `revert_deploy_<id>.py`.

---

## 5. Current state — the standing traps that silently cost a playtest

- **Engine-independence is SPLIT.** A *novel* field runs on **stock** Memoria; a **FORKED field REQUIRES
  the s23–s33 fork-gate suite**, so anything shipping forks ships our custom engine (the
  `dwix-custom-memoria-*.zip` bundle IS the dev engine, debug menu included — it's user-facing, keep and
  grow it). Patch stack lives in **`memoria-patches/`**; **its `README.md` is the authoritative per-patch
  status table — trust it over any range quoted elsewhere.** ⚠ Two distinct patches are both numbered
  **s48**; disambiguate by filename. Reverting: check `tools/restore_memoria_dll.py` for modes that still
  work — the historical `baseline` set was removed from `backups/`, so that mode can fail loudly. To get
  back to TRUE stock, re-run the Memoria patcher. → [[project-ff9-memoria-build]].
- **TEXT BLOCKS share ONE FLAT GLOBAL mesID namespace with the BASE GAME.** `FF9TextTool` merges per-txid
  cumulatively, so custom text on a REAL block **overwrites that location's dialogue** (1073 = Black Mage
  Village, 8 = Ice Cavern, 22 = Lindblum). There is NO free real block — "pick a real id no higher folder
  defines" is the ANTI-pattern. `text_block` defaults to the field's OWN id and auto-registers. A fork
  keeps its donor's block (voice acting + dual language key off it). NEVER an offset band: consumption is
  Int16, so `40000+id` wraps and loads zero text. Registration changes need a RELAUNCH; content edits
  hot-reload. → [[project-ff9-text-block-shadow]], [[feedback-verify-the-cache-write-lands]].
- **STORY FLAGS: the safe band is `FIRST_SAFE_FLAG` = 8712+, not 8512.** Bits **8512-8711 are stock
  read-mail payload** (whole-byte-written by ordinary play); **8376-8511 is the MOGNET lock band**.
  Allocating in the old band is a live save-corrupter. Truth: `ff9mapkit/ff9mapkit/flags.py`.
  → [[project-ff9-story-flags]].
- **A green test run in a worktree is not green.** A fresh worktree has no extracted template cache, so a
  large byte-level slice never COLLECTS and the run passes anyway. This is how a black screen once reached
  a playtest. Run in the MAIN repo, or extract templates first. The counts are owned by
  [[project-ff9-test-suite-perf]] — **do not quote a number here.**
- **New Game lands via a stock field-70 override (`Field(<id>)`), not a DLL edit** — and every
  `deploy_campaign` wholesale-replace WIPES it. Re-run `tools/wire_newgame_from_stock.py <id>` after each
  opening re-deploy. → [[project-ff9-new-game-entry]].
- **Never edit a bundled example in place** — the form editor's Save rewrites the byte-exact golden oracle.
  Author on a copy / `ff9mapkit new` / a Blender export. (`ff9mapkit/examples/vivi-hut/` is a retired
  offline build-oracle: do NOT re-polish it in-game.)
- **Provenance gate is CLEAR and must stay so** — zero Square-Enix binary bytes; templates regenerate from
  the user's own install (`ff9mapkit extract-templates`). The one documented game-text exception is
  `research/FLAG_LORE.md`'s ≤110-char excerpts (`ff9mapkit/docs/PROVENANCE.md`).
- **Versions:** kit `1.0.0b17`, Blender add-on `0.9.29`.

---

## 6. The toolkit at a glance

Authoring surfaces: the declarative `field.toml`; the scene.toml (spatial) / field.toml (logic) split; the
form editor `ff9mapkit edit`; the Blender add-on; Info Hub catalogs.
Offline validation (I can't see the game): `ff9mapkit lint <toml>` · `ff9mapkit walkmesh verify <path>`.
Which skill owns which domain: read the auto-injected roster — it is not repeated here.

---

## 7. Deep recipes & process rules

Byte-level detail is load-on-demand in the skills — camera/canvas/walkmesh/BG-borrow math →
`authoring-ff9-scenes` · `.eb` opcodes, RPN, flags, regions, encounters, cutscenes, behavior trees →
`authoring-ff9-field-scripts` · deploy stack, text-block shadow, EventDB collisions → `deploying-ff9-mods` ·
fork gates → `building-the-memoria-engine`.

- **Hades Workshop is fully OUT** — atlas-clone UV bug, and its export corrupts entry-adds. Author `.eb`
  in Python; verify with `eb_disasm` / the kit.
- **Fork or learn from a real field's bytes BEFORE authoring a new mechanic.** Every mechanic in the kit
  was grounded byte-for-byte against shipping FF9 data, not invented. Work incremental and verbatim-first:
  study real bytes → replicate ONE piece → verify. **Offline ≠ in-game proof.**
- **Grep alone cannot prove a field unused** — scenario dispatch, computed ids and scripted warps are
  invisible to it. Trust the user's game knowledge. (NarrowMapList is a camera-WIDTH table, NOT a cutscene
  trigger.) → `feedback-trust-user-game-knowledge`, `project-ff9-has-no-unused-fields`.
- **Calibrate the instrument before you judge with it.** Uncalibrated eyes and probes have repeatedly
  produced confident wrong verdicts here. A probe that cannot reproduce the lifecycle cannot falsify a
  lifecycle bug; an empty tempdir is not a clean room.
- **A law in a docstring is a wish** — a rule not enforced at the call site is not enforced.
- **A parse-level defect is invisible to review.** A `: ` or ` #` inside an unquoted YAML frontmatter
  scalar silently truncates or kills a skill/memory description, with no error anywhere. Verify by
  parsing. → [[project-ff9-yaml-frontmatter-trap]].
- For visual/positional bugs, ask for in-game video EARLY. → `feedback-video-for-visual-bugs`.

---

## 8. Dead ends (proven — don't re-explore)

Each cost real rounds. Full record in the linked study/memory; do not re-litigate from scratch.

- **HW "Export as Custom Field" atlas clone** — systemic UV bug (A/B tested). Use BG-borrow or `--editable`.
- **HW adding a new `.eb` entry** — corrupts the file (overwrites the player object). Python only.
- **The FieldCreator 5-point camera anchor on a flat floor** — mathematically degenerate.
- **Encoding a field warp as opcode `0x2A`** — that's `Battle`, not PreloadField → crash/black.
- **A uniform `orgPos/2` walkmesh slide, or an `f0`-vs-`+org` frame auto-detector** — the import frame is
  always `vert + orgPos + floor.org`. No heuristic.
- **Per-pitch `sx/sy` canvas scale** — the map is exact scale-1; the "back-edge drift" was the character
  collision radius.
- **A no-art camera REFRAME on import** — replaced the faithful pose on every artless fork, and its
  floor-aim flips sign on up-pitched cameras. Removed.
- **Grafting a render-only NPC's talk handler into a NON-verbatim fork (#14)** — 0-tractable across a
  675-field census: an NPC's interactive tag-3 IS the field's quest logic, inseparable. Use `--verbatim`;
  read what an NPC does with `fork-report --explain`. Adding NEW *self-contained* kit content to a
  verbatim fork IS supported → [[project-ff9-npc-on-verbatim]].
- **From-scratch massif SYNTHESIS** — falsified over 8 rounds. **THE FORM LESSON:** statistics reproduce
  the rock organization's measured properties, never its *look*. Use the carry (`world-mountain`).
- **The terrace wall from the decoded tile LANGUAGE** — refuted the tile-language discriminant in 2
  registered rounds: correct tiles on INVENTED MASSING still fail at form (the silhouette is the look's
  carrier). → `studies/path-d-new-world/TERRACE-WALL-PREDICTION.md`.
- **Real content through a synthetic frame is still synthesis** — killed both the v3 bend-carry and the
  dunes label-stamp. A verbatim stamp must carry the **MESH** (verts+uvs+tangents), not row labels.
- **The beach-mint ladder** (`world-island --beach`) — falsified over 4 playtests. **SUPERSEDED, goal
  achieved:** the `(7,17)` ground-retile carry (`world-transplant --ground desert`).
- **The dunes MINT at small scale** — the family has a **size class** (≥~130-cell footprint), so even
  genuine stock arrangement quilts on a ~31-cell blob. **SUPERSEDED at real scale** by the true mesh carry.
- **A canyon ISLAND** — off-language by THE WALL-CONTEXT LAW (canyon's red band is never open-sea coastal).
  Now guarded at both chokepoints.
- **Mixed-biome as a thin desert ribbon along a line** — **THE RIBBON FALLACY**. Stock's ecotone is the
  *margin of a desert mass*; the lawful unit is a two-ground landmass.
- **Path B — a compiled dynamic Chase/Wander region test in `.eb`** — no sound `(x,z)`→region test exists:
  cross products overflow the 26-bit CalcStack on 36% of fields, the AABB fallback misclassifies 20.8%,
  and `PathTo` sums with scripted Walk in the same frame. **KEEP THE DIVIDEND:** stock Memoria already
  gives `.eb` **computed array indexing** (`0xD3`) → [[project-ff9-eb-script-tooling]].
- **Tracking a summon's creature by mesh bounds OR by the primitive stream** — both falsified; the SFX
  hybrid-drive patch poses a managed model from the native skeleton instead.
- **The self-summon `--action-prompt`/`--nameplate` overworld entrance** — too timing-fragile.
  **SUPERSEDED** by AREA-SWITCH SURGERY (repoint a dead area-switch case), the game's real native flow.

---

## 9. Where knowledge lives (project memory & skills)

Four layers, each with one job. **Don't duplicate a fact across them — put the name in the index and the
number in exactly one owner.**

| Layer | What it holds | How you get it |
|---|---|---|
| This brief | every-session facts + hard constraints | auto-loaded |
| **Skills** (`.claude/skills/`) | load-on-demand procedures | roster + descriptions **auto-injected** — read the description, then load the skill |
| **Project memory** (`~/.claude/projects/C--gd-Dream-World-IX/memory/`) | deep recipes, laws, byte-level detail | `MEMORY.md` index auto-loads; topic files on demand by name |
| `ff9mapkit/docs/`, `studies/<arc>/` | canonical specs; per-arc research + open status | read as needed |

⚠ The memory store is **not under version control** and is **shared by every concurrent session** —
snapshot before bulk edits and prefer surgical edits to rewrites.

Read-first gates worth honoring: `authoring-ff9-overworld` before ANY coast/world work (bad geometry under
the spawn bricks the save silently) · `laying-out-ff9-fields` before placing content or narrating a
direction · [[project-ff9-overworld-coast-mosaic]]'s LAW INDEX (its first ~165 lines) before coast edits.

---

## 10. Milestones

> **Flat status list, NOT a journal.** One line per entry, ≤200 chars, one paren level, no dates, no test
> counts, no quotes. The shipped-pillar inventory lives in the memory index (§9); per-arc status in `studies/`.

**Open arcs — status lives in the study, not here:**
- The Southern Ring (the composed world) — ★ BOARD CLOSED: R1-R5 all playtest-confirmed (hub/hall/ferry, plates, forest+encounters, the boat: wake/plate/land-anywhere/seal/standoff) → `studies/overworld-topography/southern-ring/DESIGN.md`
- Overworld interior topography — the two-ground landmass (Rung F): ACCEPTED; the generator fold-back ★ DONE (36-gate one-command junction_compose; THE ONE-SITE WORLD LAW: the map holds exactly one landmass of this class) → `studies/overworld-topography/`
- Narrative-state fork fidelity — a fork still boots at scenario-zero → `ff9mapkit/docs/FORK_FIDELITY.md`
- Co-op field/dialogue lockstep (F3) — two-machine proof pending → `studies/field-coop/`
- Fort Condor fit (rung 5) — data-table substrate proven on bench 30415; awaiting owner ratification
  → `studies/fort-condor/PLAN.md`
- Tetra Master — feasibility done, near-fully data-moddable → [[project-ff9-tetra-master]] (the study dir
  lives on an unmerged branch)
- Summons TIER W ★: W5-W7+W6q cast-proven; W6b-3ii Odin ladder ★★ BPP8 0.96; U1 ★★ the 2nd-array U-displacement cast-proven on ef038, pitch axis open → `studies/custom-summons/tier-w/PLAN.md`
- The scene ladder — ★ rungs 0-3c ALL owner-confirmed: rig cinema + THE FERRY VOYAGE, symmetric origin-port departures + the s69 minimap bracket → `studies/overworld-topography/scene-ladder/`
- Click authoring — ★ Rungs 0-4 + rung 6 gateways owner-confirmed in-game; the floorplan composer 6a-6c built, Floorplan tab shipped → `studies/click-authoring/RUNG6.md`
- Path D, a genuinely new 3rd overworld world — ★★ rungs 0-5a; MESA CARRY: the TOP PASSES; base grammar DECODED (THE BAND-CONTINUATION LAW) — next = the lawful base re-mint → `studies/path-d-new-world/BASE-TILE-GRAMMAR.md`
- Interactive docs (docsite/) — site+CLI-ref+shots+tutorial system BUILT, gates green; core track S1-S7 drafted (playtest pending), CLI track C1-C4 shipped → `studies/interactive-docs/`

**Latest release:** kit **1.0.0b17** (tag pushed, CI green, PyPI live).

---

## 11. Glossary

- **Field** — one explorable screen with a fixed-perspective pre-rendered background.
- **Walkmesh** — invisible per-floor geometry defining the walkable area + depth.
- **Main_Init / Main_Reinit** — a field script's entry function / its after-battle re-entry (entry-0 tag-10).
- **Gateway** — a region trigger that warps the player between fields.
- **BG-borrow vs custom scene** — reuse a real field's art (DictionaryPatch) vs ship our own `.bgx`+PNGs+`.bgi`.
- **field.toml / scene.toml** — the kit's logic file / Blender's spatial file (merged at build).
- **GLOB vs MAP flag** — save-persistent (`gEventGlobal`) vs per-field-transient story state.
- **debug menu (~)** — the in-game debug tool, shipped in the engine bundle (Go/Cheats/Flags; Time is inside
  Cheats). Opened with tilde/backquote; was F6 until 2026-07-20 (F6 = stock Memoria's LvMax cheat key).
