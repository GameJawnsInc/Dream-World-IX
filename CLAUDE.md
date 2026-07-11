# CLAUDE.md — FF9 Custom-Field Toolkit (`ff9mapkit`, Memoria Engine)

> **Internal development brief — for AI coding agents (Claude Code), NOT user documentation.** This file
> orients an agent working *on* the toolkit; it is not a guide to *using* it, and it may reference local
> machine paths and dev workflow. **If you're here to use Dream World IX, start with**
> [`README.md`](README.md), [`SETUP.md`](SETUP.md), and the docs in [`ff9mapkit/docs/`](ff9mapkit/docs/).

> **The working brief — keep it lean.** It holds only durable, every-session facts. The project's
> narrative lives in `git log` (descriptive, ~1 commit per feature) and the deep recipes in the
> project-memory files (§9); don't reproduce them here. As work lands, update **§5 (current state)**
> and add at most a **one-line** entry to **§10 (milestones)** — never a paragraph. (Reorganized
> 2026-06-29: §5/§8/§10 de-journaled back to status lines + the memory store re-consolidated — see
> `git log` for the prior blow-by-blow.)

---

## 1. What this project is now

It began as "add one playable custom room to FF9 (Steam, Memoria engine)." **That is long done.**
It is now **`ff9mapkit`**: a Python toolkit + Blender add-on that compiles a declarative **`field.toml`**
into a complete drop-in Memoria mod — a brand-new FF9 field (camera, walkmesh, painted art, NPCs, dialogue,
gateways, encounters, events, story branching, cutscenes, ladders, jumps, props, save points) — and can
**import/fork any of FF9's ~674 real fields**, carrying their NPCs/props/lighting/dialogue faithfully.
Further pillars: **custom 3D battle backgrounds**, **multi-field campaigns** (Campaign-Editor IDE),
**story-flag tooling**, **items/equipment/shops**. **Engine split (§5):** a *novel* field runs on **stock
Memoria**; a *forked* field needs our **custom Memoria** (the s23–s33 fork-donor remap suite) for the
fork→donor logic redirects — so the shipped faithful-opening ships with custom Memoria, not stock. Likely the
first practical reference for FF9 custom-field authoring.

**North star — fork FIDELITY:** keep refining forked fields until the kit can recreate the
*functioning game itself* from them. The measure: "fork a real field → does it play identically?" (Dream
World IX shipped as a public beta — §2; fidelity stays the engineering goal, the beta is the distribution
milestone, not a reason to cut corners.) The *physical* layer (scene/walkmesh/camera/mechanics/object-carry)
is largely faithful + in-game proven; the *narrative-state* layer is the weak axis (a fork boots at
scenario-zero). Honest gap map: **`ff9mapkit/docs/FORK_FIDELITY.md`**.
Code lives at `ff9mapkit/` (package `ff9mapkit/ff9mapkit/`, Blender add-on `ff9mapkit/blender/`); the
dev-loop tools at repo-root `tools/`.

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
  feature branch → `master` with a good message. → `feedback-commit-freely`, `project-single-repo-mode`.
- **PUBLIC status — LIVE.** Dream World IX shipped to public GitHub as **1.0.0b1** (2026-06-22); the old
  "NOTHING PUBLIC" gate is CLEARED. Public PRs / issues / a PyPI release / forum posts are FAIR GAME — but
  treat outward-facing actions (a release, a forum post, a PR to Memoria) as **confirm-first** unless asked.
  → `feedback-commit-freely`, `project-ff9-public-beta`, `project-release-readiness`.

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
| GUI app | **`apps/ff9_workspace.pyw`** — the one front-door app: a PySide6 **Workspace** (a journey ▸ campaign ▸ field ▸ object tree + Inspector). Tabs: Editor / Map / Story State / Item & Equip / Battle / Models / Build & Deploy / Import, plus an Info Hub library + a Ctrl-K palette + a bottom Output/Problems console. The 8 old tkinter `.pyw` were RETIRED into it (same tk-free backends). PySide6 = optional `gui` extra. → [[project-ff9-gui-makeover]] |
| Reference field scripts | `reference/test2/` (gitignored, 817 HW field-script exports) + `reference/field-manifest.tsv` (HW-index→field-id→name; index ≠ field id) |
| FF9 field assets | `<game>\StreamingAssets\p0data*.bin` (UnityRaw 5.2.3 bundles; UnityPy reads them — `py -m pip install UnityPy`) |

> **Layout in one breath** (full detail → [[project-ff9-git-layout]]): the working repo deploys into its OWN
> Memoria mod folder, pinned in a gitignored **`.ff9deploy.toml`** (`mod_folder` + scratch-band `id`; override
> via `--mod-folder`/`$FF9_MOD_FOLDER`). `Memoria.ini [Mod] FolderNames` stacks the folders; each folder's own
> DictionaryPatch/BattlePatch is read at launch. **Distinct ids are required even across folders** (EventDB/
> SceneData are GLOBAL). Slots: master → `FF9CustomMap`/**30000** · `-bb`/**30001** · `-ih`/**30002**; reach any
> via F6 → Warp. **Field-id bands:** **10-3100** real (locked) · **4000-9899** shipped custom · **30000-32767**
> dev scratch (engine `fldMapNo` is Int16 → max **32767**; a higher id registers but is unreachable).
> **Workflow:** single-repo out of `Dream-World-IX` master (worktrees shelved → [[project-single-repo-mode]]);
> make edits on a feature branch → `master`. `C:\gd\FFIX` is the read-only archive (Memoria source + old branches).

---

## 4. The dev loop (no relaunch needed)

The proven fast loop — **edit → deploy → F6**:

1. Author/edit a `field.toml` (by hand, the form editor, or a Blender export).
2. `py tools/deploy_field.py <field.toml> [--id N]` — builds + deploys reversibly into the
   custom-field test slot (default 4003 = `TESTROOM`). It sandboxes ANY field.toml into that
   id+name, reverts the slot's prior deploy, and writes a per-id `revert_deploy_<id>.py`.
3. In-game press **F6 → Reload field** (re-reads the current field's mod files from disk:
   `.eb`/`.mes`/scene/walkmesh/art) **or → Warp to field → <id>**.
4. Ask the human to verify. Each change = one commit + one in-game check.

**Relaunch is only needed for:** the FIRST deploy of a *new* id (to register its
DictionaryPatch line), a BattlePatch change, or an engine-DLL rebuild. Reverting a deploy:
`py tools/scroll_out/revert_deploy.py` (latest) or `revert_deploy_<id>.py`.

**Text-block shadow (stacked mod folders):** every test slot defaults `text_block` 1073,
and the engine reads a field's `.mes` from the **highest-priority** `FolderNames` folder that defines it —
so a lower-priority folder's dialogue is SHADOWED (wrong text, but the *flags* are still correct → F6 →
Flags is the reliable proof). `deploy_field.py` now **warns** (`deploystack.py`) and suggests a free real
mesID; fix = a `text_block` no higher folder defines (it must be a real `MesDB` id — arbitrary ids don't
load), or pin `text_block = N` in `.ff9deploy.toml`. → memory `project-ff9-text-block-shadow`.

**Engine builds** (changing `Assembly-CSharp.dll`): MSBuild VS18 BuildTools, build the csproj
with **`/p:SolutionDir=C:\gd\FFIX\Memoria\`** (trailing `\` required, else mscorlib conflict).
⚠ The build **AUTO-DEPLOYS** to the game (x64+x86 Managed) with **no backup** — back up the
DLL first. Version-match: stay near the installed compile-date's `main` commit (`6b8bb2d5`).
New `.cs` files must be added to the csproj `<Compile Include>`. See memory `project-ff9-memoria-build`.

---

## 5. Current state (keep this updated)

- **Dev engine** = stock Memoria `6b8bb2d5` + the **F6 debug menu** (patch `memoria-patches/s22`; user-facing — it SHIPS in the bundle, see below) +
  the **s23–s33 FORK-DONOR REMAP suite** — every engine gate hardcoded on a real `fldMapNo` (or FBG name) is
  wrapped so it fires for a custom FORK id. Four gate classes, four levers: `== N` compare + local-alias
  `mapNo` (`EffectiveFieldId`, s23/s24/s29/s30), NAME-keyed (`EffectiveFieldName`, s31/s32), and lookup-arg
  (`FieldLocationName`, s33; this also backs the authorable `[field] location`). Plus **s34** (loose-mesh
  overworld override) + **s35** (overlay-texture-cache — kills the slow see-through overlay fade on field
  re-entry / battle-return, ★ in-game proven 2026-07-07). Patches in `memoria-patches/`; the per-site census +
  verification debt live in **`ff9mapkit/docs/FORK_IDGATE_MAP.md`**. The **fork-gate verification harness**
  (`tools/verify_fork_gates.py`) bakes each s29 gate's seed + observability verdict — finding: only 2507 is
  crisply cold-fork-testable (proven); the rest fire mid-beat, so the low-signal-party + ending-only gates are
  accepted as code-verified. → [[project-ff9-doeventcode-fork-gates]], [[project-ff9-fork-verification-harness]].
- **⚠ ENGINE-INDEPENDENCE IS SPLIT (durable):** a *novel* field (BG-borrow / from-scratch) runs on **stock**
  Memoria; a **FORKED field REQUIRES the s23–s33 suite** (else it loses Dante's off-mesh exemption, narrow-map
  width, the fake-battle return, the softlock fixes, etc.). So **the shipped faithful-opening ships our CUSTOM
  Memoria** (stock + s23–s33 + the **F6 menu** — the shipped `dwix-custom-memoria-*.zip` bundle IS the dev
  engine; **F6 is a user-facing tool we KEEP and plan to grow**, ★ in-game verified shipping on a clean
  installer run 2026-06-30) — which is why we ship our own engine + held the PRs. Revert engine → no-edits
  rebuild: `tools/restore_memoria_dll.py baseline`; true stock = re-run the patcher.
- **F6 debug menu** (ships in the engine bundle; in **FIELD, BATTLE, and the OVERWORLD**): a draggable IMGUI popup, **redesigned
  2026-07-03** into a flat dark theme rendered in FF9's own **Alexandria** font (loaded from Memoria's encrypted font bundle;
  font picker Alexandria/System). **4 context-adaptive tabs** — **Go** (on a field: reload · warp to any registered id [+ a
  search filter, + arrival-entrance/ScenarioCounter under "more options"] · teleport; on the overworld: warp-to-field · world
  teleport · vehicle-mode swap · disc 1↔4 · restore control) · **Cheats** (boosters / heal / give) · **Flags** (get/set/clear/
  snapshot a `gEventGlobal` flag + a **BATCH box** — many bit/byte/word ops in one click, all-or-nothing, named ★ presets;
  ★ 2026-07-10) · **Time**. Header shows live context; a **combined pinnable ★-favorite list** of BOTH field
  WARPS and overworld SPOT teleports persists via `PlayerPrefs`. The overworld **"Warp to field"** (game's own
  `SetNextMap`+`nextMode=1`+`attr|=0x1000` transition) fires even when frozen → the reliable **stuck-escape**; **"Restore
  control"** unfreezes in place. The overworld **teleport** defeats Memoria's `SmoothFrameUpdater_World` reverter via `Skip`.
  "Disable control" **defaults OFF** (persisted). All ★ in-game proven → [[project-ff9-f6-overworld-debug]]. Supersedes the old
  single-key F6-reload / F10-reset hotkeys.
- **The Vivi hut is RETIRED to offline build-oracle status.** The painted hut rooms (4000 ext + 4002 int, the
  100%-kit-authored copy in `release/FF9CustomMap/`) were the S0 proof; their only job now is the byte-exact
  golden test (`examples/vivi-hut/` → the provenance manifest SHA). **Do NOT re-polish the hut in-game** — the
  in-game showcase is the World Hub + verbatim forks. (4003 = the shared test slot.)
- **New Game lands via a stock mod field-70 override (`Field(<id>)`), NOT a DLL edit** — currently the forked
  faithful opening (6000 = Prima Vista), with field-70's opening FMV + fade PRESERVED. ★ The override is WIPED
  by every `deploy_campaign` wholesale-replace of FF9CustomMap → RE-RUN `tools/wire_newgame_from_stock.py 6000`
  after each opening re-deploy. → [[project-ff9-new-game-entry]].
- **Versions:** kit `1.0.0b2`, Blender add-on `0.9.20`. **Provenance gate CLEARED at HEAD** — zero Square-Enix
  bytes; base templates are regenerated from the user's own install via `ff9mapkit extract-templates`;
  `*.eb.bytes`/`*.bgx`/`*.bgi.bytes` are gitignored (except our own hut quad). The git-history SE-bytes scrub
  was DONE pre-push (2026-06-22). → [[project-release-readiness]].

---

## 6. The toolkit at a glance (capabilities — all in-game proven)

`ff9mapkit` compiles `field.toml` → mod. The full content/scripting stack, each verified in
real gameplay and reproducible in Python (zero Hades Workshop):

- **Field & scene:** mint a custom field id (≥4000); single / **scrolling** / **multi-camera**
  cameras; human-painted art layers with depth-based occlusion; walkmesh authored from math OR
  imported/reshaped from a real field; the menu/title **place-name** via `[field] location`.
- **Content:** NPCs (any model + animations, by name) · dialogue (speaker tag, auto-wrap) ·
  gateways (round-trip doors) · encounters (+ field/battle BGM, after-battle fix) · **events**
  (chests / gil / story flags / triggers) · **story branching** (flag-gated NPCs / doors /
  events) · **dialogue choices** (NPC + zone, default/cancel rows, static + flag-gated hide) ·
  **cutscenes** (narration v1 + actor walk/path/turn/animation/teleport v2) · **ladders**
  (navigable, vertical/slant/bent shapes, floor/gateway/worldmap tops, re-entry) · **jumps**
  (Ice-Cavern ledge/gap hops) · **props**
  (static set-dressing — chests/tents/save-points/barrels/ladders/signs — via the real FF9 recipe:
  `SetModel` + a static pose + `EnableHeadFocus(0)`; `[[prop]] prop = "chest"` or `model` + `pose`).
- **Import/fork:** `ff9mapkit import <field>` (BG-borrow · `--editable` custom-scene · `--native`
  seamless per-tile fork) + `list-fields` — fork any of **674** real fields (camera + walkmesh +
  gateways/BGM/encounters extracted offline from p0data), **carrying their NPCs/props faithfully**
  · **`ff9mapkit fork-report <field>`** previews fork fidelity BEFORE you fork (roster vs interaction
  axes, story-gated beats, suggested `[startup]`; clean static-roster vs story-event verdict — `forkreport.py`)
  (verbatim `.eb`-entry graft + player-func + lighting + per-language text). Blender "Import FF9 Field"
  gives a visual fork→author loop. **`ff9mapkit import-all`** bulk-imports a foldered, Blender-ready ARCHIVE
  of the whole game (or a `--pattern` zone / a `campaign.toml`) into `<out>/<ZONE>/<FBG>/` — lightweight
  model-against projects (camera+walkmesh+composite `background.png`) by default, `--editable` for the full
  repaintable per-depth scenes; the quick on-disk source-of-truth you copy field folders out of.
- **Battle backgrounds:** author custom 3D battle maps — texture reskin, loose-FBX geometry, a net-new
  fightable scene, or a wholly-original `BBG_B###`; tune the fight (stats/positions/rewards/spawn) and the
  camera (`battle.toml` + `battle-import`/`-build`; a separate pillar from fields, no DLL rebuild).
- **Campaigns:** `import-chain <seed>` forks a connected slice of the game into one drop-in mod (`--whole-zone`
  = the seed's whole zone; **`--ids <ranges>`** = an EXACT id set, scoping the fork to ONE story-state visit — a
  place's revisits are separate id clusters sharing one zone, so `--ids 100-117` forks Alexandria's opening, not
  all 48 revisit screens); the **region catalog** (`data/region_catalog.toml`, the "Browse FF9 regions" picker)
  is generated split-by-visit (one region per cluster, each with a `members` range → `--ids`). The
  **Campaign Editor** IDE (navigator + graph + Map + authoring) edits the multi-field project. **`reference-arcs`**
  (CLI + a New-Journey "FF9 reference arc" option) scaffolds FF9's real story arcs (`data/reference_arcs.toml`, the
  disc-1 spine) into a chained `journeys.toml` + a per-arc `import-chain` fork playbook — the north-star fork-and-test
  harness (a PLAN, not a one-click rebuild).
- **Save points & story flags:** a synthesized `[[savepoint]]` (`Menu(4,0)`, save→reload into a custom
  field works); `[[flag]]` story flags by name; `flags`/`flags-inspect`/`flags-diff`/`save-edit` read,
  compare, and edit a real save's `gEventGlobal` state.
- **Authoring surfaces:** declarative `field.toml`; the **scene.toml (Blender, spatial) /
  field.toml (logic)** split; the **form editor** `ff9mapkit edit`; the **Blender add-on**
  (camera/walkmesh/layers + NPC/gateway/event/spawn/waypoint/cam-zone markers).
- **Info Hub catalogs:** `ff9mapkit models | animations | scenes | items | catalog` — browse
  GEO models, anims, battle scenes, items, fields by name (baked from Memoria source,
  provenance-clean); the model→animation join is engine-sound.
- **Build-time validation** (offline, since I can't see the game): content off the walkmesh /
  within the collision radius of a wall, stranded floors, broken seams, zero-area triangles,
  layer aspect mismatch, camera pitch range, dead story flags, unknown model/item names.
  `ff9mapkit lint <toml>` / `ff9mapkit walkmesh verify <path>`.

Always **fork/learn from a real field's bytes** before authoring a new mechanic — every
mechanic above was grounded byte-for-byte against shipping FF9 data, not invented.

---

## 7. Hard-won facts & gotchas (load-bearing — deep recipes in §9 memory)

**Custom fields / BG**
- Mint via DictionaryPatch `FieldScene <id> <area> <MAPID> <NAME> <textid>`; custom ids ≥ 4000.
- **BG-borrow**: point `<area>`+`<MAPID>` at a real field's art. **`<area>` MUST be ≥ 10** —
  the loader builds `"FBG_N"+area` with no zero-padding and reads exactly 2 chars, so
  single-digit areas (0–9) black-screen. (`--editable` forks remap a low area to ≥10.) → `project-ff9-bg-borrow-solution`.
- Runtime always loads the compiled `.eb` (no text→.eb path). Per-language `.eb` differ ONLY
  in the 84-byte name field; **bytecode is language-identical** → byte-patch the code region at
  the same offset in all 7 langs. → `project-ff9-eb-script-tooling`.

**Camera / projection / canvas** (`project-ff9-camera-math`)
- Invariant: `R_ff9 = diag(1, 14/15, 1)·R_ortho` (vertical-focal aspect; **k = 14/15** is a
  global constant baked into orientation row 1). Author any camera from math (`cam.synth_r_t`).
- **Canvas map is EXACT scale-1**: `canvasX = rawProj.x + w/2`, `canvasY = h/2 − rawProj.y`
  (proven to 0.0005 px vs an in-engine probe). The old per-pitch `sx/sy` (0.926/0.889) were an
  eyeball fit silently absorbing constants — **dead**.
- **Character ground offset = 0** (engine-measured). The legacy `org=(0,0,300)` +
  `CHARACTER_GROUND_OFFSET_Z=298` were a near-cancelling double-count — **ripped**; new
  walkmeshes use `frame="world"` (org=0, no offset).
- `COLLISION_RADIUS_W ≈ 48` (= `bgiRad*4`): the player CENTRE can't reach a walkmesh edge —
  extend the walkmesh ~48u past the painted floor if the player should reach the visual edge.
- **Art / canvas wiring:** logical canvas **384×448**; painted PNGs are **4× upscaled** (a full
  layer = 1536×1792). An overlay's `Position` = top-left logical px (Y-down), `Size` = px/4,
  `Z` = depth (**smaller Z = in front of the character** → occlusion); overlay world placement is
  the scale-1 inverse of `to_canvas`.
- **Scrolling:** build `proj` from the visible **window width (384)** and only widen `Range` for
  a wider painting — naively widening `proj` DOUBLES the FOV (the kit's `[camera] window_width`).
- Yaw: `R = rot_x(pitch)·rot_y(−yaw)` (post-multiply keeps the origin centred). Control
  direction is auto-derived from yaw: `value = round(yaw/360·256) − 1` (front-facing = −1).
- The editor's **5-point anchor solver is degenerate for flat floors** (rank-deficient) — DEAD
  END; use the math, not the editor, for cameras.

**Walkmesh / import** (`project-ff9-import-frame`)
- A real field's walkmesh world position = **`vert + orgPos + floor.org`** (universal; multi-
  floor tiles via per-floor `floor.org`; single-floor `floor.org=0`). This is THE frame rule.
- Real `.bgi` floors are **disjoint vertex sets, corner-origin per floor.** Rebuilding neighbor
  links by shared vertex INDEX loses cross-floor seams → **ship the real `.bgi` verbatim**, or
  reshape via `obj + links` (a position-keyed seam sidecar). The `.bgi` codec is lossless; only
  the `.obj` intermediate drops adjacency.
- **`IsInQuad`/`TreadQuad` test a FAN of consecutive vertex-triplets, not the real polygon** —
  3 collinear points = a zero-area triangle = a DEAD ZONE. Use a convex quad with the last
  vertex DOUBLED. → `project-ff9-gateway-regions`.

**Regions / gateways** (`project-ff9-gateway-regions`)
- Region triggers only fire when `usercontrol == 1`. **Region tag 2 = tread** (every frame in
  the quad), **tag 3 = press-to-interact** (action button), **tag 10 = Main_Reinit** (runs after
  battle). The player must actually REACH the zone (place it where he demonstrably stands).
- Exit walk-out direction is set by the polygon's **point ORDER** (q[0]→q[1] edge first = walk
  forward, no "circle").
- **A field→field warp MUST fade to black BEFORE `Field()`** — else the destination loads *in the
  clear* and the player sees its camera wire up to him (~0.8s of the scroll camera sitting on the
  bare scene centre, player in a corner = the "static screen on spawn"). The proven fade is
  `fade_filter(6,24,0,255,255,255) + wait(25)` (SUB mode → white = screen→black), exactly what
  gateways/ladders/the field-70 opening emit. The kit lever: `content.event.warp(..., fade=True)`
  (choice-warps + cutscene `then_warp` use it). Never insta-warp a player-visible transition.
  `entry_settle` is the *destination*-side complement (assumes the field already loaded black, i.e.
  the source faded). → `project-ff9-world-hub`.

**Encounters / battle** (`project-ff9-encounters`)
- A field cloned from a cutscene field lacks an entry-0 **tag-10 Main_Reinit** → after-battle
  **softlock** (`EnterBattleEnd` suspends objects; nothing resumes them). Fix: add a tag-10 that
  `FadeFilter(2,16,…)` (overrides BattleResultUI's 256-frame timed fade) + re-enables move.
- BattlePatch `Music:` = the akao **song-play id** (0 = Battle Theme), NOT a file number. Field
  BGM = `RunSoundCode(0, <song id>)` (song id, not file number; Vivi's Theme = 9).

**`.eb` scripting** (`project-ff9-eb-script-tooling` — full opcode table; kit `eb/_optables.py` is authoritative)
- Format: 44B header + 84B PSX name → entry table at offset **128** (10 slots × 8B); a
  function's `fpos` is measured from `entryStart+2`; 2-byte opcodes are prefixed `0xFF`.
- Opcode traps worth memorizing: **`Battle = 0x2A`** (NOT PreloadField — encoding a warp as
  0x2A starts a battle on a bad scene id → crash/black); real `PreloadField = 0xFD` is a no-op
  HINT on Steam; `Field = 0x2B` is the real warp; **`0x01` is an undocumented unconditional
  JMP** (don't overwrite a Wait that sits right after it — the activation is skipped). Camera/
  scroll mechanics: **`SETCAM = 0x7E`** (switch active camera), **`BGCACTIVE = 0x71`** (enable
  scroll / camera-services).
- **Expression sub-language**: opcode `0x05` + a `0x7F`-terminated RPN stack; var token byte =
  `0xC0 | (type<<2) | source`. `B_SYSVAR=0x7A` (code 9 = `GetChoose`, reads the picked choice
  row); `GetItemCount` = expr fn `0x64`. Reusable for chests/levers/choices.
- **A talk func (tag 3) MUST be ≥ 9 bytes.** `IsActuallyTalkable` polls `tag3[ip+7]`/`[ip+8]` every frame the
  player is near it → a shorter func indexes past the entry buffer = an `IndexOutOfRangeException` each frame
  (non-fatal, spams `Memoria.log`). The kit pads short talk funcs; non-interactive props are **`bare`** (Init-only,
  no tag-3 — matches shipping set-dressing, dodges the poll).
- **Actor cutscene choreography MUST run in the NPC's LOOP (tag 1), not its Init (tag 0).**
  `ProcessAnime` advances `animFrame` only when `obj.state == 1`; Init runs at `state == 2`, so
  Init-spliced movement updates the transform but FREEZES the skeleton (glide, no emote). Also:
  a **warm-up `Wait(~30)`** before the first actor command (entry-transition settle, else the
  walk circles + the synchronous walk hangs); `SetWalkTurnSpeed(255)` to avoid the
  walk-to-a-point-behind orbit/softlock; **never `WaitTurn`/`WaitAnimation` on a player-cloned
  NPC** (its clips don't complete those → softlock — use instant turns + a fixed `Wait(40)`);
  `MoveInstantXZY` args are `(worldX, −worldY, worldZ)` + `SetPathing(1)` after (it disables
  walkmesh collision). → `project-ff9-cutscene-multiactor`.

**Story flags — persistence** (the bug that bit every once-gated thing)
- A var's **source** decides persistence: **GLOB (src 0) = save-backed `gEventGlobal`** (2048
  bytes, persists across field reloads + saves) vs **MAP (src 1) = per-field, WIPED on every
  field load.** HW naming is INVERTED (HW "GlobBool" = engine **Map** = transient).
- `EventContext.mapvar` is **only 80 bytes** → a high flag index in MAP space is out-of-bounds
  = hard crash. **Use GLOB for chests / story flags / cutscene-once.** The kit uses `GLOB_BOOL
  = 0xC4` (transient dev twin = `MAP_BOOL = 0xC5`) with flag bases in the **8000+** band (clear
  of base-game flags); indices > 0xFF need the long-index token encoding (`class|0x20` + 2-byte
  LE) — which is why the 8000 band works. `gEventGlobal` index N → byte `N>>3`, bit `N&7`.
- A `once=true` event/cutscene won't replay for *testing* once its persistent flag is set —
  use `once=false`, a fresh New Game, a distinct flag index, or F6 → Flags → reset.

**Fork gates / engine** (`project-ff9-memoria-build`, `project-ff9-doeventcode-fork-gates`)
- Read dev hotkeys in a real MonoBehaviour `Update()` (e.g. `UIKeyTrigger`) via
  `UnityXInput.Input` — **NOT** `HonoLateUpdate` (the ~30 fps logical tick misses `GetKeyDown`).
- **Any engine behavior hardcoded on a real `fldMapNo` (or FBG name) is LOST on a custom-id fork.** The
  fork-gate census must sweep it in FOUR forms — a `== N` compare, a local alias (`Int16 mapNo = fldMapNo`),
  a NAME key, and a lookup ARGUMENT — each fixed by a matching lever (`EffectiveFieldId` /
  `EffectiveFieldName` / `FieldLocationName`, the s23–s33 suite). → `ff9mapkit/docs/FORK_IDGATE_MAP.md`.

**Process** — Hades Workshop is fully OUT (atlas-clone UV bug + its export corrupts entry-adds; author `.eb`
in Python, verify with `eb_disasm`/the kit). Never edit a bundled example in place (the form editor's Save
rewrites the byte-exact golden oracle — author on a copy / `ff9mapkit new` / a Blender export). Grep alone
can't prove a field unused (scenario-counter dispatch / runtime-computed ids / scripted `Field()` warps are
invisible to it) — trust the user's game knowledge; NarrowMapList is a camera-WIDTH table, NOT a cutscene
trigger (entry cutscenes run from the `.eb`). → `project-ff9-mint-gotchas`, `feedback-trust-user-game-knowledge`, `project-ff9-has-no-unused-fields`.

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
  what an NPC does with **`fork-report --explain`**. (★ NOT a dead end — don't re-conflate: ADDING NEW
  *self-contained* kit content — `[[npc]]` · `[[gateway]]` · `[[event]]` · `[[prop]]` · `[[chest]]` — to a
  *verbatim* fork IS supported + in-game proven; it seats below the engine's last-9 party band. Different
  problem. → [[project-ff9-npc-on-verbatim]].)

---

## 9. Project memory (the deep recipes)

The full technical detail this file only summarizes lives in the project-memory store, **auto-loaded each
session** and indexed by its `MEMORY.md` (`~/.claude/projects/C--gd-Dream-World-IX/memory/`). Read a topic file
on demand — `MEMORY.md` carries a one-line hook for all ~74. (Consolidated 2026-06-29: the old `C--gd-FFIX`
store was merged in after the single-repo migration left it orphaned; that path is now just a backup.)

The load-bearing foundational recipes, by name:
- `project-ff9-eb-script-tooling` — `.eb` format + opcode tables + Python injection; flag persistence; the F6 menu.
- `project-ff9-camera-math` — the projection invariant (k=14/15), scale-1 canvas, character offset, yaw.
- `project-ff9-import-frame` — the `vert + orgPos + floor.org` walkmesh frame; ship the real `.bgi` verbatim.
- `project-ff9-novel-bg-pipeline` — painted-BG / overlay-depth / occlusion; `--native` is the seam-free path.
- `project-ff9-gateway-regions` — region trigger mechanics + IsInQuad dead zones + the fade-before-`Field()` rule.
- `project-ff9-encounters` — random battles + the after-battle Main_Reinit fix.
- `project-ff9-story-flags` — the `gEventGlobal` heap map + the 5 verbs + the safe band (bit 8512).
- `project-ff9-memoria-build` — local engine build toolchain + auto-deploy + version-match.
- `project-ff9-object-carry` / `project-ff9-verbatim-fork` — faithful NPC/prop carry + the truest fork.
- `project-ff9-field-logic-map` — make a verbatim fork's `.eb` legible + editable in place.
- `project-ff9-battle-backgrounds` / `project-ff9-battle-tuning` — custom battle maps + gameplay tuning.

---

## 10. Milestones (status only — full story in `git log`, detail in §9)

> Keep this a flat status list, NOT a journal. Add a one-line entry when a pillar lands; never a paragraph.
> The narrative is `git log`'s job (~1 descriptive commit per item below) and §9 memory's.

**Foundations (S0–S15):** recon + build/test loop · MINT custom field ids · BG-borrow (area ≥10) · painted
BGs + foreground occlusion · Python `.eb` authoring (NPCs/talk/text) · camera math (scale-1 canvas) ·
connected rooms + encounters + after-battle fix · local Memoria engine build · `ff9mapkit` + Blender add-on ·
scrolling fields.
**Import & authoring (S16–S23):** import/fork any real field (universal walkmesh frame) · faithful `.bgi` +
editable/native forks + multi-floor seams · offline lint suite · multi-camera · events / story branching /
cutscenes + flag persistence · form editor + scene/field split · provenance gate cleared (zero SE bytes) ·
dialogue choices · ladders · the F6 debug menu · Info Hub catalogs.

**Pillars (all in-game proven — detail in the named memory + `git log`):**
- Battle backgrounds — all tiers (reskin / FBX / new-scene / camera), no DLL → [[project-ff9-battle-backgrounds]]
- Battle tuning — enemy + player side + raw17 `btlseq` attack-choreography, no DLL; + **palette-swap enemies** (`[[scene.enemy]] skin` mints a recolored variant model — a battle enemy's Geo@30 takes a minted id, ★ 2026-07-08) → [[project-ff9-battle-tuning]]
- Battle telemetry — `battle-telemetry` logs every calc to a JSONL via the Scripts-DLL **IOverload\*** hooks (first use of the Overload category; `--report` = per-ability balance stats; ★ 2026-07-07; refactored onto the Overload HUB 2026-07-11, same events/CLI) → [[project-ff9-overload-hooks]]
- Overload gameplay surface — the **ONE-HUB architecture** (the engine registers 1 IOverload\* implementer per interface per DLL, last-wins → the kit emits a single regenerated hub; features = plain static classes, mutators-before-observers, a collision gate, GENERIC deploy stickiness) hosting declarative gameplay features off the battle hooks. **`[difficulty]`** (flag-gateable enemy HP/attack/magic scaling, `OnBattleInit`) — ★★ FULLY IN-GAME PROVEN 2026-07-11, both variants (always-on ×2 HP byte-exact via telemetry: Fang 68→136, Goblin 33→66; `flag` gate toggles per-battle with NO relaunch). **`[rebalance]`** (player_damage/enemy_damage HP-damage multiplier, `OnDamageFinalChanges` mutator — the only way to scale PARTY damage; 9999-cap needs Memoria.ini `BreakDamageLimit`) — ★★ FULLY IN-GAME PROVEN 2026-07-11, both variants (2×/0.5× confirmed via telemetry, direction split clean). **The GRANULARITY LAW** (discovered here): a flag-gated Overload feature's toggle latency = its hook's fire cadence — rebalance gates per-HIT (F6→Flags flips it live mid-battle), difficulty per-BATTLE (next battle). Same gate, different granularity from where the hook sits. + the **RETURNING-hook hub mode** (single-owner verdict hooks, fail-safe = vanilla) hosting **`[deathrules]`** (`OnGameOver`: once-per-battle second-wind Phoenix revive / chance / Eiko-removal; flag = fully-vanilla-while-clear; built + offline-proven 2026-07-11, AWAITING playtest — `scratch/deathrules_test.field.toml`) → [[project-ff9-overload-hooks]]
- Scripts-DLL — a mod `Memoria.Scripts.<Mod>.dll` (compiled at deploy vs the installed engine; NO rebuild) hosts 3 in-game-proven declarative plugin surfaces off `[[playable]]`: battle FORMULAS (`script={template/body}` → `[BattleScript(id≥256)]`, e.g. Soul Leech drain), FIELD effects (`script.field` → paired `[FieldAbilityScript]`, works in+out of combat, e.g. Lifewell heal), and STATUS behaviours (`status=[{template/body}]` → `[StatusScript(CustomStatusN 33-63)]` + a minted StatusData row + a `BuffIcon` panel-icon + `over_model` on-model SHP/SPS/tint + a `power` knob, e.g. a revive-on-death Rebirth). Hardened by a lint-time `csc` gate + an engine-version drift warning. ★ all 2026-07-07. The 4th surface (IOverload* battle hooks) now has the HUB + its first shipped-content feature, `[difficulty]` (see the Overload line below) → [[project-ff9-scripts-dll]]
- Battle/party GUI — battle + party config folded into the Workspace (encounter-first) → [[project-ff9-battle-party-gui]]
- Models GUI — a Workspace **Models tab**: an illustrated browser (real software-rendered thumbnails, `model-preview`) + the full edit round-trip + `model-reskin` texture edits + `model-deployed` inventory/revert + a `[[playable]]` form; previews across Info Hub/pickers (CLI → 100 cmds) ★ 2026-07-07 → [[project-ff9-gui-makeover]], [[project-ff9-custom-models]]
- Battle-model export gap CLOSED — `extract.resolve_prefab` replays the engine's alias chain (baked `_modelalias.py`): all 71 alias ids (char battle forms = shared field body + battle overlay + own animset; boss/alt-outfit/F1 aliases) export/preview/reskin/deploy engine-faithfully (overrides land at the DONOR prefab folder, overlay meshes stripped); the 43 unshipped ids refuse actionably; offline-proven byte-identical baselines 2026-07-10 → [[project-ff9-battle-model-export-gap]]
- New-clip authoring — `model-anim-new` mints a wholly NEW animation, DLL-free (Blender `.glb` action or synth; FIELD anim keys are 16-bit → mint band 60000-65535 + full-skeleton keying; + donor-folder reference-anim embed in `model-gltf`) ★ in-game proven 2026-07-08 (BBA whole-body spin) → [[project-ff9-custom-models]]
- **From-scratch creature (Plan-4 capstone)** — a wholly-original creature with ZERO FF9 bytes ("Boletta": procedural mesh+rig+texture → `emit_skinned_fbx` → `[[mint]] fbx=` id 6300 → own `model-anim-new` idle → `[[npc]]`) renders/idles/talks ★ in-game proven 2026-07-08; `deploy_field`'s revert/re-apply now PRESERVES foreign DictionaryPatch lines (matches its own FieldScene/`3DModel`/`3DModelAnimation` by exact id/key, not GEO block) so a between-deploy `model-anim-new` clip survives a redeploy — ★ in-game proven 2026-07-08 (`ff9mapkit/dictpatch.py`) → [[project-ff9-custom-models]]
- Campaigns — `import-chain` + the Campaign-Editor IDE → [[project-ff9-worldmap-feasibility]], [[project-ff9-import-chain-coverage]]
- Multi-campaign journey assembler — both link modes + zero-link deploy-derived auto-wiring → [[project-ff9-world-hub]], [[project-ff9-journey-single-folder]]
- World Hub — playable journey selector (New Game → hub → verbatim forks) → [[project-ff9-world-hub]]
- Navigable jumps + save points (synthesized & verbatim save-Moogle) → [[project-ff9-jump-navigation]], [[project-ff9-savepoint]]
- Story flags — `gEventGlobal` mapped, 5 verbs, safe band ≥8512, field/campaign/journey scopes → [[project-ff9-story-flags]], [[project-ff9-flag-scope-hierarchy]]
- Faithful object/NPC carry → verbatim fork (`--verbatim` = real logic + real text); additive content on a verbatim fork → [[project-ff9-verbatim-fork]], [[project-ff9-npc-on-verbatim]]
- Non-Zidane donors + PC/party control (`--swap-player`, `[party]`) → [[project-ff9-non-zidane-donors]], [[project-ff9-pc-party-system]]
- **13th playable character** — a genuine NEW `CharacterId` (id 12), party member alongside all 12 canon chars, **ZERO DLL** (`[[playable]]` block: CSV allocator + `CharacterDefaultName` + `B_PARTYADD`); ★ fully in-game proven (recruits, own name/stats, fights, save-persists) + a custom (Blender-edited) battle model (`custom_battle_model`) + a custom menu portrait (`portrait`) + an **independent, editable battle ANIMSET** (`custom_battle_anims` — own `Animations/<mintId>/` clips + `3DModelAnimation` regs, donor untouched; ★ in-game proven 2026-07-06) + a **bespoke ABILITY KIT** (`[playable.abilities]` — its OWN `CharacterPresetId` ≥20: own command menu + curated learn list, e.g. a mixed black+white caster; ★ in-game proven 2026-07-06) + a **UNIQUE minted COMMAND** (a `command1`/`command2` inline table `{name, abilities}` → a NEW `BattleCommandId` in the safe band 46/35-40 with its OWN ability pool + `com_name.mes` name overlay, per-id-merged Commands.csv, zero-DLL; ★ in-game proven 2026-07-06) + a **CUSTOM ACTIVE ability** (a pool inline table `{name, from, power, element, mp}` → a NEW `Actions.csv` row in the 192-223 band CLONED from a donor + retuned + `aa_name.mes` overlay — his spells BEHAVE uniquely, not just group uniquely; ListEntry raw-id vs learn `AA:id`; ★ in-game proven 2026-07-06) — which also takes **`status = [names]`** (auto-mints a StatusSets row in a 100+ band + injects the action's `statusIndex`, crash-safe; ★ Silence in-game proven 2026-07-06) and **`effect = "[code=TAG]…"`** (a minted `[[ability_feature]]` `>AA <rawId>` block, `_AA_MAX`→223; ★ `[code=MPCost] 0`→free-in-battle proven 2026-07-06 — a BATTLE-side hook, so the field menu still shows the base cost) → [[project-ff9-ability-preset-system]]) — ★ GENERALIZES: a 2ND custom character (id 13 "Steiniv" on the Steiner KNIGHT rig, its own preset/command/ability in distinct auto-allocated bands) recruits + fights alongside Iviv, in-game proven 2026-07-06 (the roster is an unbounded `Dictionary<CharacterId,PLAYER>` — id 13 works like the proven id 12) → [[project-ff9-13th-character]]
- Items / equipment / shops + save editor + the New-Game starting-state capstone; + **custom weapon models** (`[[weapon]] model` — stock swap or a minted recolored variant; Weapons.csv Model takes a minted GEO name, ★ 2026-07-08) → [[project-ff9-items-equipment]], [[project-ff9-save-item-layout]], [[project-ff9-new-game-entry]]
- `fork-report` (offline fidelity preview) + verbatim-fork SPATIAL authoring (Blender markers) → [[project-ff9-npc-on-verbatim]], [[project-ff9-fork-fidelity-worklist]]
- InfoHub authoring — place any model/prop/creature by name → [[project-ff9-infohub-authoring]]
- Active Time Events — both flavors authorable (optional blue menu + grey unskippable) → [[project-ff9-ate-system]]
- Offline field-art export + native-art repaint round-trip + multi-camera fidelity → [[project-ff9-novel-bg-pipeline]], [[project-ff9-native-repaint-workflow]]
- Advanced interactables (moving platforms / elevators) — `--verbatim` carries; declarative `[[platform]]` is the frontier → [[project-ff9-moving-platforms-elevators]]
- Field logic-map — read/decode/validate/edit/add a verbatim fork's `.eb` in place; whole EDIT tier proven → [[project-ff9-field-logic-map]]
- Verbatim authoring set — `[music]` rescore, `[[npc]] opens_shop`/`choice`, multi-actor `[cutscene]` conductor → [[project-ff9-verbatim-music]], [[project-ff9-cutscene-multiactor]]
- FMV pipeline + SPS field-particle authoring → [[project-ff9-fmv-pipeline]], [[project-ff9-sps-authoring]]
- Onboarding + Windows installer — uv-bootstrap `.exe` + `ff9mapkit setup` (detect FF9 → save config → extract → Memoria report; opt-in `--install-engine`) + Steam/GOG auto-detect + the GUI working for installed (.exe/pip/uv) users → [[project-ff9-installer-packaging]]

**Frontier:** #13 (story-event director/roster on rotating-cast fields) — carry-side (`--verbatim`+`[startup]`) AND
now the AUTHORING side ★ in-game proven: **`[[npc]] scenario_min/scenario_max`** self-gates an NPC on a
ScenarioCounter window `[min,max)` (min incl / max excl) so NPCs at one spot with adjacent windows are a rotating
cast; the gate is the exact byte shape `fork-report` reads back → [[project-ff9-fork-fidelity-worklist]]. Custom
OVERWORLD is now STARTED (no longer "unstarted"): geometry reshape (s34,
★proven), overworld→fork entry (s28, ★proven), and now **authoring a NEW overworld ENTRANCE from scratch** (world-`.eb`
func + tile-bit edit → custom `!` → warp; ★in-game proven 2026-07-01, entered a forked field) → [[project-ff9-worldmap-feasibility]].
The whole entrance flow is FOLDED into one command — **`ff9mapkit world-entrance --cell X Z --field N [--building
m.obj]`** (`world/entrance.py`: clone+patch the `Byte[39]` trigger func → deploy per-language to every dispatcher carrying
the case, stacking + idempotent → tile bits → optional modelled building). **★ FULLY in-game proven 2026-07-01/02 — a
Blender castle on an OPEN plain: renders, blocks cleanly, `!` → forked Ice Cavern, clean round-trip.** The building path
took an engine + kit debug (all landed): s34 now RENDERS an Object override on a BARE cell (else invisible) and
RENDER-ONLY (object-as-collider = invisible back faces); collision = the TERRAIN-59 hull under the building (conforms);
place by bbox-CENTRE (centroid bulges an asymmetric model); pick a cell judged OPEN over the WHOLE block (not 16u — the
"dirt mounds" were natural topo-49 riverbank); solid footprint is SPAWN-fragile (`--hollow-building` = walk-through is
safe). Also **`world-mesh-trim --floor`** (auto-drop a building's low flat base apron) — but the demo Alexandria castle's
"floor" is intertwined with real courtyard/platform geometry, so an auto-remove guts it; use a manual Blender face-delete
for that. Per-language: patch each lang's OWN world .eb (JP dialogue differs). Full saga → [[project-ff9-worldmap-feasibility]].
**Path D — RECLAIM ocean cells as walkable LAND (★ in-game proven 2026-07-02)**: the make-or-break new-continent spike.
The overworld is a fixed 24×20 grid where every sea cell already exists as a `WMBlock` short-circuiting to a shared
`SeaBlockPrefab`; the s34 divert routes a sea cell carrying a loose Terrain override onto a plain LAND donor prefab so
our synthesized flat walkable mesh renders as land (`world-reclaim` CLI; `mesh.flat_block_mesh`/`terrain.reclaim`).
LESSON: the donor cache field on `WMWorld` must be `[NonSerialized]` (a serialized field on the baked MonoBehaviour
→ deserialize-corrupt → blackscreen). **FAITHFUL COAST (★ in-game proven 2026-07-02): `world-coast` carries a REAL FF9
coastline** (terrain + animated `beach1`/`sea`/foam) onto reclaimed ocean via a per-cell `Donor.txt` sidecar → the s34
divert loads that real coastal block as the donor (`ResolveReclaimDonor`/`TryReadDonorPath`); the beach/foam are
animated `WMRenderTextureBank` sub-meshes, NOT terrain tiles, so they must be carried not textured. Bundled an F6
teleport fix (`ForceLoadBlockReadyAt` — warp-then-stuck was a not-yet-`IsReady` destination block, not a short ray).
→ [[project-ff9-overworld-terrain-authoring]]. **FULLY-SYNTHETIC ISLANDS/LANDMASSES ★ in-game proven + SHIPPED 2026-07-07: `world-island`** — organic coast + rock wall +
the real grass/meadow/relief tile language + the RE'd engine PLACEMENT spec as a build gate, MULTI-CELL by construction (tris
clipped at 64u block borders; a 4-block landmass walks seamlessly) — `world/{island,grassland,placement}.py`
(→ [[project-ff9-overworld-placement-rules]], [[project-ff9-overworld-coast-mosaic]]). **VERBATIM ISLAND TRANSPLANT + COMPONENT
TWEAKS ★ in-game proven 2026-07-08** — a complete real island (land+beach+full Wang'd ocean) carried to any custom cell with
position / 0-mod-4 shift / 90°-rotation knobs, then EDITED component-wise on the verbatim baseline (chocobo-track de-quest via the
grass language; a beach-end re-cover with the cap-band asset); the saga distilled the coastline EDIT LAWS (components are
geometry+texture+topo units; end welds are load-bearing — slide connector ASSEMBLIES, never re-draw their boundaries; at 1-column
scale beach length = where the curl begins) + two permanent offline gates (placement census, WELD AUDIT — never hand-type
geometry, real verts are off-lattice floats) — PRODUCTIZED 2026-07-08 as **`ff9mapkit world-transplant`** (`world/transplant.py`:
transplant knobs + `TileRetexture`/`PatchRecover` tweak classes + `--strips auto` island-tongue rule [neighbour blocks are FOREIGN
content, carried only where the donor's own land reaches that border]; `weld_audit` = a general gate in `world/mesh.py`; census
folded in; kit build BYTE-IDENTICAL to the proven island_morph v16 scratch artifact) + the s22 F6 block-dump tool
→ [[project-ff9-overworld-coast-mosaic]]. Remaining overworld frontier: coastline/landmass EDITING is now a
LADDER of in-game-proven tweak classes on verbatim transplants (all 2026-07-08, laws → memory): `VertexDisplace` geometric
moves (visible+smooth bow; a FINE-ADJUSTMENT tool, ~±2.5u — width contrast is the salience cue) and ★ **`RowInsert`, the
GROWTH SEED** — a whole lattice column inserted at a census-clean cut line (split-shift + bit-exact-by-identity seam
extrusion + per-class UV fill), island measurably +4u in-game, seam invisible; then (2026-07-09) `chain_row_inserts`
(multi-cut composition) + the **object-anchor gate** (a donor's prefab Object never moves — its ground must net-0) +
**`cut_census`** (the component-aware line law: a cut may not cross the beach, a beach END-CAP tile on the line, a
PAINTED WASH [a connected non-grass topo-0 patch — paint can't be continued by any per-cell UV fill, 4 strategies
falsified in-game], or object ground; (9,17) = ZERO usable lines, (7,17) = one; a world sweep found **56 donors with
≥2 clean lines**, top (5,2)×12) — ★ the census-clean recipe in-game proven 2026-07-09 ((7,17) grown +4u at its one
clean line, same-tweak-set A/B, "don't see any artifacts"); ★★ MULTI-cut in-game proven 2026-07-09 ((16,17) grown by 2 chained cuts, headland visibly longer, fills seamless;
the SLACK law: growth needs water slack on the shifted frame side); then 2026-07-09: 3 chained cuts +12u in-game measured BUT its sea flagged in-game → two more laws: WANG-strip
water fills translate-clone never mirror (directional tiles), and the STRICT SHORE LAW (sea1/sea2 = shore-bound
COPY-ONLY; cut_census `touches-shallows`) — the single-donor single-axis growth CEILING is 2 cuts/+8u
(qualifying donors: (21,10)/(16,17)★/(13,18)/(8,16)/(7,15)). ★★★ **MULTI-CELL VERBATIM CARRY in-game proven
2026-07-09** — `transplant_region()` / `world-transplant --size NXxNY` carries an N×M donor rect as ONE rigid
assembly (re-partition at target block borders, watertight by construction; per-cell `Donor.txt` sidecars + a
prefab-parts gate; region census with inverse-transform miss backmap; 1×1 = BYTE-IDENTICAL to `transplant()`):
the (9,5)+2×3 island — FF9's ONLY clean multi-block landmass (land-component flood-fill census: every 2-block
rect has foreign frame-touching land) — cloned to (9,9), "fully faithful". + THE WALL LAW: the sliver filter
tests TRUE 3D area, never plan (vertical forest-wall tris are plan-degenerate → silently dropped; latent in
donors (18,15)/(21,10)/(16,17); old baselines left as-is by user call). ★ ROT-90 REGION CARRY in-game proven
2026-07-09 ((9,5)+2×3 → (11,8)+3×2, "good" — rotated re-partition + inverse-mapped sidecars faithful). REGION
cut_census SHIPPED (`--size` + `--grow-cut`) with 3 new laws (empty-cell `gap-vacation`/`spills-into-empty`;
tweak-inverted census backmap; benign frame-T-junction weld split) — but the first region growth cut ✗ FAILED
in-game → **THE RELIEF LAW** (`crosses-relief`, `MAX_CUT_RELIEF=6.0`: a cut's fill is a seam-profile extrusion —
through steep relief it's a terrace band + holes; proven cuts ≤3.5u, the mountain 26.5u; high relief = a
COMPONENT, cut around, never through); net: (9,5)+2×3 has ZERO usable x-GROWTH lines. **★ MULTI-BOUNDARY SEAM
EXTRUSION in-game proven 2026-07-09 ("no artifacts at any of the three spots" — the gap-vacation kill):**
`RowInsert(boundaries=[(plane,z0,z1)])` extrudes the east side's seam profile at an empty cell's border too (west
edge = the bit-exact pre-shift prefab-boundary profile, fills windowed to the empty rows, UVs mirror/clone the
SHIFTED east owner; per-cut bands tile `+i*delta` like the lines); `cut_census` certifies a boundary FILLABLE iff
pure open water (sea3/5/4) → `boundary_fills` triples + a `clean` flag (`gap-vacation` now = unfillable only;
`ok` still = grows land); CLI `--grow-cut` census-validates region lines + auto-wires the fills; + the INTERIOR
BORDER-T weld law ★ (`_split_border_pairs`: one-vert-off-plane near a clip vert = benign T-junction — the
rejected 592 build's 2 undiagnosed x=64 pairs were never a defect; both-exact-on-plane = crack, still fails). On
(9,5)+2×3 the 8 flat WATER lines 580–608 are census-clean SLIDE cuts; the ★ 592 slide (whole island +4u east, 32
boundary tris — the first working RowInsert on a MULTI-CELL base) deployed at (11,1)+2×3, all three inspection
spots clean. Land-growth lines there stay ZERO (relief blocks 640/672). **Z-AXIS RowInsert BUILT 2026-07-09
(deployed awaiting playtest):** `RowInsertZ`/`chain_row_inserts_z`/`cut_census(axis="z")`/CLI `--grow-cut-z` via
the EXACT-ROTATION ADAPTER — never transpose the fill vocabulary by hand: `(x,z)→(−z, x−2048)` is bit-exact both
ways, so the z-cut delegates to the proven x-RowInsert and inherits every law (content south of the line shifts
−delta; chains north→south, `−i*delta`); + the CORNER-SLIVER weld law (a float ~0.02u off a border mints an
on-plane/on-plane pair from its own two edges' clip verts — `_split_border_pairs` judges border pairs as
union-find CLUSTERS: any off-plane witness = benign T-junction, all-on-plane = crack). Real z-census: the
mountain relief-blocks the LAND z-lines too → the (9,5) island's land is UN-GROWABLE on either axis (a component
fact about the donor, not a mechanics gap). The first z-slide deploy (−352, at (0,4)+2×3) surfaced **TWO more
in-game defects, both root-caused + FIXED (kit `1b44071`):** **THE HAIRLINE LAW** ("a seam in the cliff" at a row
border — the degenerate-sliver filter was dropping REAL thin clip fragments [~0.001u], not just true collinear
degenerates [~1e-9]; fixed via `MIN_TRI_AREA2=1e-6` + a **clip-drop ledger gate** [fails on any real dropped area]
+ a **border micro-census** [0.5u-spaced probe pairs, 0.0005u inset, purpose-built for what the coarse census
steps over]) and **THE LATTICE-SEAM LAW** ("stretched" cliff-adjacent water — the unclamped mirror fill wraps the
atlas between OFF-LATTICE seam verts; fixed via `cut_census`'s new `conforming-on-line` risk [flags an off-lattice
on-line vert in open water; terrain off-lattice verts stay legal] + a lattice check on multi-boundary safety). The
corrected line is **−332** (not −352); the island was REDEPLOYED with both fixes — ★ user-confirmed in-game
clean at both defect zones. **SECOND-DONOR SCREEN (2026-07-09):** a direct land-fit slide-window scan (not the
component heuristic) over every data block confirms (9,5)'s clean-small-multi-block-island property does NOT
generalize — nearly every other multi-block landmass is a fragment of a bigger connected coastline. Best
alternative **(10,17)+2×2** (5.5u relief, under the cap, zero objects) carries clean; its LAND lines stay
blocked (`conforming-on-line`/z-lattice-misalignment, not relief) but its 8 water lines are now clean SLIDES
via the SPILL-CLIP law below; deployed (identity) at (9,3)+2×2 as a reference. **THE
BAKED-TERRAIN LAW** closes the "highland fill vocabulary" investigation: topo 17/38/49 turn out to have NO
discrete tile language (92–100% UV-placement-unique within one donor, 65–97% unique map-wide) — hand-painted
murals, the same class as a topo-0 wash. `cut_census` gains a generic (not topo-id-hardcoded) `crosses-baked-
terrain` risk: a singleton UV rect (no sibling anywhere in the donor+strip scan) disqualifies a line; a
genuinely repeating rock patch elsewhere stays fair game. No verdict change for (9,5) (already zero lines via
relief) but the check is live for a future donor whose highland patch survives the relief cap. **CONTINENT STEP
★ deployed:** `world-entrance --building` proved the pillar stack composes — a synthesized watchtower + a warp
(→ field 300) placed directly on the (9,9)+2×3 island clone (cell (19,21)/block(9,10)), `read_block_stacked`
correctly layered onto the prior transplant (confirmed: post-entrance terrain still carries exactly the
transplant's 104 tris for that cell). Rider fixes same day: building-footprint collision is
now EXACT (`split_retarget_by_polygon` splits straddling terrain tris at the hull — the centroid
over/under-shoot fixed, the tower's 36.0 sq-unit footprint bit-exact, `54b4e1d`, ★ in-game proven 2026-07-09
"watchtower collision is fixed"; the entrance trigger-tile
exclusion is exact BY ORDER — the split runs first, pinned `3ed64ae`) + `world-entrance --texture/--tile/
--tile-uv` CLI passthrough (`6096b21` — no more direct-API bypass to texture a building). **THE SPILL-CLIP LAW
(2026-07-09, ★ in-game clean): `spills-into-empty` KILLED** the way gap-vacation was — a cut's spill
into an empty donor cell is CLIPPED at the cell's fixed border (`SpillClip`/`SpillClipZ`, per-part tweaks
appended by `chain_row_inserts[_z](spill_clips=)`; pure clipping of real bytes, zero synthesis; the empty cell
stays TRUE prefab ocean, deploys nothing) when the census certifies a water-column BUDGET (the run of
border-profile-identical open-water columns − 1 — the run's last column becomes the new prefab-facing border,
so the border language is preserved by construction; `cut_census` → `spill_clips (plane,z0,z1,budget)` rows;
CLI `--grow-cut` auto-wires; apply-time gate re-certifies every dropped tri). The unlock: an empty neighbour
column = usable SLACK for any donor whose water butts its own block border — (10,17)+2×2's 8 dead water lines
are clean slides now; the 2-cut slid clone deployed at (2,4)+2×2 beside the (9,3) identity reference — ★
in-game "looks good" + the slide proven by OFFLINE DIFFERENTIAL on the deployed bytes (slid land ==
identity land +8 vertex-for-vertex; sea4 delta −16 == 112 fills − 128 drops exactly; east edge tops at the
border, empty column has NO override — the differential-vs-a-reference-deploy is the verification recipe for
"visually identical by design" tweaks). **THE FUSE LAW (2026-07-09, ★ in-game proven 2026-07-09 — "i don't see any seams along z=-640"): cross-donor
LAYOUTS** — a "continent" is several complete verbatim donors in adjacent target rects, each keeping its own
coast (land never knits — coastlines are components; the WATER knits: sea4 is anti-tiling, sea4-vs-sea4 borders
are always legal). `world-fuse <layout.toml>` + `fuse.fuse_layout()`: every placement gates clean, rects don't
overlap, and every SHARED border certifies row-by-row from the new per-edge `frame_profile` each
transplant_region summary emits (each side prefab or pure on-lattice open water; shallows/land/gaps refuse;
sea3-facing-sea4 grade jumps reported not failed; on-disk collisions refuse without `--allow-overwrite`).
Finding: (10,17)'s WEST frame carries its live sea1 shore system (continues into the real neighbour in situ) —
that edge can only face prefab; its N/S edges are pure sea4. First fuse deployed: (9,5)+2×3 stacked on
(10,17)+2×2 at cols 0-1 rows 7-11, shared border z=-640 (32 rows certified). **BAND-CROSSING RE-WANG: resolved
as research + a census law; the fill build DEFERRED by the numbers (2026-07-09).** THE LEARNED WANG TABLE
(`STRIP_EDGESET`/`strip_edge_set()`, `9361b6f`): a real Wang strip tile is a PURE function of which neighbours
sit deeper — byte-learned over 221 tiles/10 blocks, ZERO contradictions (sea1 = sea5's language one rung down)
→ re-derivation is SOUND; but the payoff scan found only 4 lines map-wide blocked solely by `touches-shallows`
(none land-growing — the growth ceiling is the COMPONENT laws, not the shallow law), so the re-derivation fill
stays designed-and-ready in memory (trigger: a coast-MORPH pillar). The census dividend shipped: **the
STRIP-ACROSS-LINE law** (`87913da`) — a west-seam strip with an E/W deep edge = a band parallel to the cut =
the clone duplicates the transition; retro-flagged the (2,4) slide's 648+652 → law-compliantly REDEPLOYED on
the pure-sea4 pair 692+696. **THE CLIFF-FACE TRANSITION LAWS (2026-07-09, `601a2d6` — the checklist study,
answered offline):** the LIP-ROW VOCABULARY (a face's top edge pins to a painted texel row KEYED BY THE TOP
FAMILY: grass 0.893 / highland-dirt 0.872 / topo-27 0.944 / desert ~0.39 — the lip row IS the transition); the
CONFORMING-CREASE law (99% of lip grass is crease-conforming deformed geometry — no edge-tile class, no blend
family [49|58 negligible], no bevel, sharp ~66° crease, grass rolls ~9° into it); the FREE-BASE law (ZERO
face base edges land on walkable terrain map-wide — topo-58 is coastal-only, bases terminate free at the
waterline; inland terraces are painted murals). Synth cliffs are correct for grass tops (0.893 = the shipped
constant, independently re-derived); a non-grass-top synth must switch rows. Both rows + the laws locked by a
game-gated test. **F6 TRI-COORDINATE READOUT (2026-07-09, `264b666`, ★ in-game proven — "the F6 readout
works"):** ended a recurring coordinate-confusion problem — F6 showed `RealPosition` (absolute un-wrapped;
diverges from every kit coordinate once the overworld wraps). The Position section now leads with the
CANONICAL wrapped triple every kit tool speaks: `world (x,z) · block [x][y] (⌊x/64⌋,⌊−z/64⌋) · cell (x,z)
(⌊x/32⌋,⌊−z/32⌋)`; raw pos shows only when `[wrapped]`; Copy position copies the canonical pair. → F6 memory.
**THE REAL-BUILDING PATH (2026-07-09, ★ in-game proven — "looks right and has collision, warp works"):** the watchtower replaced by a REAL stock
overworld structure (block (20,10), 220 tris after trim_floor) — exported OBJs carry real atlas UVs through the
whole loop (`export_obj`→Blender 5.1→`world-entrance --building`, no `--texture` needed; the round trip was
already vt-clean, zero kit changes); 63 stock Object blocks surveyed, candidates in the session scratchpad
(SE-derived, never commit). **★ THE FIRST CUSTOM CONTINENT in-game proven 2026-07-09** — the content act's
composition half: 4 verbatim donor islands ((9,5)+2×3 fused to (10,17)+2×2 at z=−960, + (7,17) beach + Uaho
(0,0)) as ONE `world-fuse` layout in the SW ocean pocket (rows 12-19), all render + walk, strait seam-free;
layout = `ff9mapkit/examples/continent-v1/` → [[project-ff9-first-continent-proposal]]. Next = the entrance
follow-up (fresh `fork-report` pass over 3-5 candidates — Chocobo's Paradise + Gargan Roo both screened OUT as
story-entangled, see the proposal memory). **★ THE COAST-MORPH PILLAR in-game proven + PRODUCTIZED 2026-07-10**
— cliff-coast morphing on verbatim transplants (`world/coastmorph.py` + `world-transplant --cliff-bump` /
`--cliff-headland`; generic tweak classes 6-8 `DropTris`/`EmitTris`/`SeaBump` in transplant.py): rung 1 = a
≤2.5u conforming bow (land UVs drag, water re-evaluates through its own tile map; the fold gate makes the
2.5u envelope a build-time refusal), rung 2 = a structural HEADLAND (the window's wall REBUILT over a
sin²-pushed outline, one inserted column per gap under the deterministic-U-ramp **k≡old-k (mod 4)** law with
byte-copied cycle UVs incl. wrap seams; native-lattice grass re-fill; sea ZIP-strip back to the new outline).
New laws: COLUMN QUANTIZATION (exactly one 64px rock tile per wall column, strip = exactly 4 tiles — the
U-ramp is deterministic), DROP-DON'T-DRAG (every tri touching a moved vert drops + re-fills natively), WATER
NEVER DRAGS NOR CLAMPS; new offline gates: crack (fill once-edges == region boundary), grain (≤6.6u), WATER
DENSITY (uv-sv inside the real envelope — caught its own first fix), exact sea ledger. Proven at (11,9) bump /
(13,9) headland vs ref (9,9), donor (7,17)'s NE cliff — land round 1, water round 2; + the **BAY** (★ in-game
proven 2026-07-10 at (12,9), `--cliff-bay` / signed `_cliff_reshape` core): the wedge consumes GRASS
(crease-footprint strict-interior drops), a component within reach = offline refusal (D=8 refuses, D=6 built),
beyond-shore zip water = TRANSLATE-CLONES, signed ledger; + ★ **COMPOSED `cliff_lobes`** (in-game proven
2026-07-10 at (10,9), "no seams": a bay between two headlands as ONE reshape — piecewise sin² signed-lobe
profile, `--cliff-lobes "…:3.5,-5,6.5"`). Its 4 laws: the REFINED-CREASE fan vocabulary (half-step-U crease
verts, quantization holds through the fan), the REACH gate (footprint touches only sea4), the FREE EQUAL-ARC
resample (drop-don't-drag makes interior columns free; total ≡ ncols mod 4; phase-table wall UVs; odd-gap
windows legal), the RING-EXTENSION ladder (a sub-grain bay-rim corridor consumes one more grass ring).
Morph row = (9,9)ref/(10,9)composed/(11,9)bump/(12,9)bay/(13,9)headland. + ★ **LIVE-CONTINENT morphs**
(in-game proven 2026-07-10): two bows on continent island A THROUGH its `world-fuse` placement (tweaks ride
`transplant_region`; deploy proof = the byte differential — only the 2 window cells' Terrain+Sea4 changed,
the strait byte-identical). Laws: the BAKED-TERRAIN REFUSAL (mural-topped donors like (9,5) = bow-only, no
fill language — structural morphs refuse cleanly) + the CENSUS DISPLACEMENT INVERSE (a donor hole translates
with a morphed shore and slips the backmap → `VertexDisplace.census_inverse`) + the LOCAL-ENVELOPE window
slider (bent runs + thin sea slivers; the fold precheck is the envelope measure). + ★ **THE BEACH BOW**
(`--beach-bump`, in-game proven 2026-07-10 after a 4-round saga — the beach frontier's rung 1, the first
morph on a SANDY shore): the beach = an interleaved ramp ASSEMBLY (waterline chain = beach1↔sea2 bit-exact
welds / sand-seam chain / end-caps); the bow = ONE cos²-tapered DRAG field over the whole shore system.
Its laws: the LADDER TAPER (a shore morph moves ALL bands in proportion — a waterline-only bow pinched the
wash 4.0→0.8u = a hard band seam) + the WATER-MECHANISM law (small strain ok ≤~16%, sharp strain never,
extrapolated re-evaluation NEVER — per-tile re-eval at field scale = clamp smush + border tiling) +
depth-scaled reach (strain = depth·π/(2·reach)); gates: ribbon (swash 3.3-6.7u envelope), band (≥60%
verbatim width), strain ([0.75,1.33] per edge). ★ Rung 2 STEP 1 in-game proven 2026-07-10
("~indistinguishable"): `beach_rebuild` identity mode — a window's foam/wash/Wang-ring DROPPED and
RE-DERIVED from pure language over the same verts (foam run tile u[0.0156,0.5]/4u-column + separate
end-cap band; sea2 conforming = quadrant-affine continuation; sea1 via the learned table in EMISSION
mode, 20/20 round-trip). The EDGE-SHADE FIELD discovery: strip edge states are Wang SHADES that agree
across tiles (neighbour-band = the thin-band special case; thick bands have interior freedom) — the
field is SHAPE DATA read from the donor. ★★ **STEP 2, the beach SHAPE MORPH, in-game proven 2026-07-10
("both ends blend like the verbatim"): `beach_reshape` / `--beach-reshape` (+ `--beach-rebuild` CLI)** —
the ASSEMBLY slides (sand seam + waterline together, the berm DRAGS, |D|≤2.5), the water ladder RE-LAYS:
width-driven lattice C1 (the ABSOLUTE 2.4-8.4u envelope is the law; ratio-to-old is false — donor columns
jump 4↔8), per-column patchwork PULLBACK + the edge-shade field TRANSPORTED then min-flip re-solved over
the table's 12 sets (every flip = a forced Wang agreement), **sea3's language LEARNED** (quadrant mains,
own v-split 0.50794, DIHEDRAL-8 — rotation-4 misses half; ~90 cells err 0.0000). Its 3 aesthetic laws,
each user-called → byte-confirmed → gated: **HUG** (within-beach swash near-constant — cross-beach
3.3-6.7u is a false within-beach law; the assembly slides as a unit), **SHAPE-CLASS** (convexity is
inherited from the coast: noses grow seaward ≤+46%/len, pockets deepen landward, NEVER cross the chord
to the opposite class — (7,17) is a pocket → landward-only), **CAP-TAPER** (the terminal foam columns
carry the end-cap taper band, not run tiles; emission transports each column's own corner UVs + diagonal
from the donor — identity foam = a verified byte round-trip). Deployed-bytes differential vs the identity
block = the verification recipe. ★ **THE SEAWARD NOSE + IN-PLACE (in-game proven 2026-07-10, "extends
clean with no seams"): the REAL (18,15) nose bowed D=2.5 on the live map via `--in-place`**
(`morph_in_place`: s34's override key is transform.name-GENERIC → per-part loose meshes on ANY real block;
touched parts only, revert = delete; the route forced by THE CARRY REALITY — (7,17) is FF9's ONLY
fully-in-block beach, every nose landmass is a fragment). `beach_bump` = the free-form ASSEMBLY bow
(hug field both sides, shape-class gate, frame pins). Two corrected foundations: THE DEFINITIVE SEAWARD
RULE (per-vert wl→seam direction — global centroids flip on multi-beach islands, mid-tests on curved
runs; both "+45% noses" were pocket misreads) + THE ASYMMETRIC CLASS ENVELOPE (pockets to −46% of length,
true noses ≤ +19% — sand accumulates in concavities; caps 0.25L/0.48L). ★ IN-PLACE CLIFF MORPHS proven
same day ("reads clean on the real island"): the composed LOBES golden build applied to the real (7,17)
NE cliff — `--in-place` now proven for BOTH families (displacement fields + structural drop/emit;
`morph_in_place` gates: IN-PLACE-FRAME [frame vert set byte-unchanged — welds to real neighbours] +
BOUNDS [nothing leaves the cell]). The whole real coastline is now morphable, reversible, no carrying.
★ **THE COAST WINDOW SCANNER shipped same day: `ff9mapkit world-morphs --block BX,BY | --all`**
(`world/coastscan.py`) — beach + cliff windows with per-verb probed CEILINGS + ready-to-run `--in-place`
deploy lines; THE BUILDERS ARE THE ORACLE (probe the real morph fns down a depth ladder + certify via a
morph_in_place dry-run — zero law re-implementation) and the cliff sub-window search is REFUSAL-STEERED
(`window gap K` / `touches seaX first at (X,Z)` refusals name the cuts; ~5s/block). Re-discovers every
proven ceiling; found a better (3,11) nose window than the hand study. ★ THE CLAIMS PROVEN IN-GAME
("it looks good"): the (16,9) D=8 headland — a never-hand-studied window on a wildly curved bay rim
(stock devs −10.7..+30.4), deployed verbatim from the catalog line, the biggest structural morph yet
(121u / 27 gaps). Full-map catalog: **324 windows** (297 cliff: 164 bump / 16 headland / 21 bay; 27
beach: 4 true noses; beach-reshape = exactly 1 lawful window map-wide, (7,17)). ★ THE CLEARANCE GATE
closed the open question: the cliff shape law is PINCH, not class — cliffs are class-free (headland-on-
bay-rim proven), push SHEAR is harmless (the wall REBUILDS; 81° crest shear proven at (16,9)), the real
hazard = the pushed outline pinching (≥4u gate vs self + the block's other cliff base; (21,10) D=8 was
the catalog's 1.7u riskiest line → refuses; the scanner self-corrected to D=6 with zero code change).
★ SEA5 EMISSION in-game proven ("clean, no seams or patches"): the STRIP FAMILY CLOSED — census 1644/1763
cells, 0 inconsistencies, 0 boundary violations over 3875 edges; `strips_rebuild` / `--strips-rebuild`
re-derives every decodable sea1+sea5 cell (UV-only deltas, per-cell re-decode self-check; ~7% inset-rect
residual verbatim). Shore vocabulary now lacks only the end-cap ASSEMBLY synthesis — the last rung
before BEACH-MINT (the sand band closed ★ in-game 2026-07-11, see Path A below). **Path B RESOLVED by falsification (2026-07-10):** the sand band is a single-row
chain-pinned RIBBON (one v-rect stretched over 1.8-6.6u — the old ±2.5 drag cap WAS the language
envelope; row B strictly terminal; the (3,11) spit fold the only multi-row shape) — a widened band has
NO lawful fill, so the growth verb is **`beach_slide` (`--beach-slide`), the FULL-ASSEMBLY SLIDE**: the
land chain rides the profile too, the band translates VERBATIM (rigidity asserted), the berm strip
clips at the translated chain (watchtower splitters), and the vacated shore re-lays via the
**GRADED-LADDER RE-LAY** (pullback through sea5 by the learned table, sea4 grows landward, block-frame
reconcile; coastal sea4 = DIHEDRAL-8 — the sea3 lesson recurring; {sea1,sea5} adjacency is real).
(7,17) ladder: −1/−1.5 + −3..−5.5 build (−2..−2.5 = the lawful width-envelope valley); ★ in-game
proven 2026-07-10 at (16,8) vs (13,8) identity / (14,8) drag ("the seam is gone, looks clean") —
round 1 caught an angle-dependent pinhole → **THE T-VERTEX LAW** (merged-loop re-triangulation +
pos+delta snap + band-edge subdivision + a permanent T-VERTEX GATE; the float32-scale scan is the
honest oracle). **The SEAWARD slide (grass-berm noses, FREE-FORM)** followed same day: zero
column-quantized nose windows exist, so `beach_slide(depth>0)` rides beach_bump's proven
displacement field with the band re-emitted verbatim (drop-don't-drag), **grass PINNED** (the
berm drag deleted) and the vacated strip re-filled with NATIVE GRASS (`_grass_fill_region`) —
true seaward land growth; ceilings (18,15) +2.5 / (16,15) +3.5 (past the bump cap) / (3,13)
+2.5; ★ in-game proven 2026-07-10 in-place at BOTH the real (18,15) +2.5 AND (16,15) +3.5 (the
map's biggest lawful nose growth, the first morph past the drag envelope's depth — "the nose
reads clean, grass blends in fine"). **★ Path A IN-GAME PROVEN 2026-07-11 — the SAND-BAND edge table
byte-learned map-wide** (14 bands / 437 tris: two u-rects P/Q at atlas 270/334/396, per-band v pins,
THE ONE-SHADE LAW — sand's 3 edges are one mutual shade class, every boundary pair byte-observed +
texel-verified homogeneous — caps pin to rect Q/0.3867-outward BECAUSE the cap band is a gradient);
shipped as `sand_rebuild` / `world-transplant --sand-rebuild` (rect-FLIP identity rebuild + the
closure freeze; 210 run tris over 22 blocks; ★ the (10,8) flipped clone vs the (13,8) identity
"reads clean, matches" — sand emission generative like the strips). **THE END-CAP LAWS
byte-learned 2026-07-11 — slot freedom ★ FALSIFIED in-game, the corrected laws byte-proven:**
the global beach texture (4 animated frames, 128×64) is ONE curling-swash composition; THE TAPER
ASYMMETRY — only the BL window FADES (band n 13→4 at u→0), TR is the full-strength curl-out
(the (9,8) BL→TR flip read as "the non-capped straight lines") → THE SLOT LAW: slots TRANSPORT,
mint defaults to BL (the universal fade). Orientation is law, the rest per-cap texel snaps
(4 run families in `FOAM_FAMILIES`, canonical floats in `_CAP_CANON`); shipped as the
mint-facing emitters `emit_foam_cap`/`emit_sand_cap` + `cap_rebuild` / `--cap-rebuild` = the
identity round-trip under an internal byte-equality gate — **70 foam + 34 sand cap tris over
27 blocks ALL byte-exact** (caps have zero freedom beyond snaps: the round-trip IS the
completeness proof); spit/BR/subdivided/skewed/frame-split verbatim; (9,8) redeployed clean.
The shore vocabulary is CLOSED. **★ BEACH-MINT RUNG 1 in-game proven 2026-07-11** ("passes the
visual/seam test, looks narrower"): `beach_mint` / `--beach-mint WIDTH|auto` re-mints a real
beach's sand+foam assembly from chain specs — interfaces pinned (land chain / waterline / end
welds), the seam chain + topology + every UV synthesized (no fan transport; sand P/Q walks +
cap emitters, foam stamps + BL caps); gated by the ribbon/slope/swash envelopes + THE ASSEMBLY
BOUNDARY gate; (7,17)'s width ladder probes 4.6 as the swash ceiling; the (11,7) clone carries
the beach fully re-minted at width 2.5 vs the donor's ~4.1 — the first fully kit-authored beach
assembly in-game. **★ Rung 2a IN-GAME PROVEN 2026-07-11 (the (11,6) land-2.4 mint)**: the
FREE-FOOTPRINT mint — `--beach-mint WIDTH|auto[:LAND]` synthesizes the LAND CHAIN too (interior
L pushed landward, berm-surface conformed, the berm BSP-CLIPPED at the new synthetic chain with
fan-subdivided band columns + the UNION crack gate; (7,17) ladder 0.6–2.6, ribbon-refused at
3.0; zero water delta by deployed-bytes differential). The TRUE virgin-shore mint re-runged to
rung 3; the window study's laws (berm topo-0 only · the lattice adjacency table — sea3 never
touches sea4 · beaches never share verts, 4.06u grass-tongue separators · all 5 wash-fronted
virgin pockets one column short) live in the memory. **Rung 3's blocker CRACKED same day (offline):
THE DEFORMED-TILE RECT LAW** — a strip tile's uv map = a ≤2u×≤2v snap-rect ASSIGNED TO ITS CORNER
VERTS independent of deformation (the map deforms WITH the tile — why position-evaluated fits
falsified) + positional edge-lerps on inserted verts; one snap vocabulary for both tiers (sea1
lattice 186/186, conforming ~95%, residual named+verbatim); the sea1 convergence fans are pure
corner assignment, and the virgin ladder can skip sea3 ({1,5} is real) — `_deformed_strip_groups`
+ `conforming_rebuild` (identity round-trip, zero drift on proven donors) shipped; the first FRESH
deformed-tile emission (the one-cell band-conversion probe) = rung 3's in-game step. 35 golden
tests → [[project-ff9-overworld-coast-mosaic]].
**Chocobo Hot & Cold** — the declarative `[chocobo]` dig prize/timer lane on a verbatim forest fork (`chocobo-export` +
`[[chocobo.prize]]`/`[chocobo.tuning]` → `[[logic_edit]] kind="expr_literal"`, a NEW generic in-expression-literal edit
kind; scan fits all 3 forests, 35 slots each; popup+give+tally agree by construction) — ★ **in-game proven on ALL
THREE forests 2026-07-10** in-place (2950 Elixir/2:01 · 2951 Phoenix Down/2:31 · 2952 Magic Tag/3:01, popups match
gives everywhere) → [[project-ff9-chocobo-hot-cold]].

**Latest:** kit **1.0.0b13** (public betas b3–b9: PyPI + uv-bootstrap Windows installer + `ff9mapkit setup` + Steam/GOG game-detect + GUI-works-installed; **b7** = installer bundles+installs the engine patches [backed-up/version-aware], installed-GUI campaign/journey deploy + New-Game wiring [`ff9mapkit deploy-campaign`/`deploy-journey`/`newgame`; deploy orchestration extracted into `ff9mapkit/deploy.py`+`newgame.py`, the `tools/deploy_*.py` are now thin shims], Workspace app icon; **b8** = installed Workspace lights up the dev test-slot/F6 loop against a checkout via `$FF9_REPO`/cwd-walk [`jobs.resolve_dev_repo`], installer Finished-page wording fix; **b9** = Workspace UX pass [app-wide combo wheel-guard, destination-aware Revert, campaign-Map legend/tooltips, copy/affordance cleanups] + an opt-in, install-aware update check [version chip + once-a-day PyPI check, `ff9mapkit/update_check.py`]; **b10** = Workspace settings pass — a 7-theme picker [Light/Dark + Nord/Dracula/Solarized Dark/Light/Gruvbox, `editor/theme.py` + `prefs.py`, live preview, persisted], Preferences + About dialogs [⚙ menu], a one-click "Upgrade & restart" for installed copies [detached uv-upgrade helper, `_run_upgrade`/`_UPGRADE_PS1`], light-theme tone-down + installer Finished-page clip fix → [[project-ff9-gui-makeover]]; **b11** = maintenance bump, no functional change [cut to give b10's one-click updater a live target to upgrade to]; **b12** = TWO new pillars — custom 3D **MODELS** [`model-gltf`/`-import`/`-mint`/`-anim` + Blender-authored mesh & animation editing + one-click add-on Import/Export Model, all DLL-free → [[project-ff9-custom-models]]] and custom **OVERWORLD** [`world-terrain`/`-reclaim`/`-coast`/`-water`/`-entrance`/`-encounters`/texturing/minimap + F6-on-overworld + the s34 engine patch → [[project-ff9-worldmap-feasibility]]]; F6 got a 4-tab redesign + a "Reload + anims" button; **`world-water`** synthesizes faithful graded open-ocean water from a depth field [marching-band Sea3/Sea5/Sea4, byte-proven UVs, world-coord seam-matching; `world/water.py` → [[project-ff9-overworld-terrain-authoring]]]; **b13** = the biggest content release yet — a **13th & 14th playable character** (`[[playable]]` with bespoke ability kits / minted commands / custom active abilities + status + effect, custom battle model + editable animset + portrait → [[project-ff9-13th-character]], [[project-ff9-ability-preset-system]]), the **Scripts-DLL** battle-formula / field-effect / status-behaviour surfaces + Overload battle telemetry ([[project-ff9-scripts-dll]], [[project-ff9-overload-hooks]]), custom-models round 2 (Models GUI + `model-mint`/`model-anim-new` + the from-scratch creature Boletta → [[project-ff9-custom-models]]), synthetic **overworld** (`world-water` faithful oceans + `world-island` multi-cell cliff landmasses + `world-reclaim --profile cliff` + save overworld-position → [[project-ff9-overworld-coast-mosaic]]), custom **music/SFX** (DLL-free → [[project-ff9-sound-music]]), palette-swap enemies + custom weapon models, rotating-cast NPCs (`[[npc]] scenario_min/max`), EXPERIMENTAL **image→field** ([[project-ff9-image-to-field]]), a Workspace GUI pass + the 2026-07-07 docs overhaul; the **engine bundle is UNCHANGED from b12** — s35 overlay-cache, the s22 block-dump, and s36 multiplayer are held for b14), 3031 tests (`py -m pytest -n 6`). The install-path features are NOT in-game proven on an installed copy yet (user playtests on the laptop). See `git log` + `[[project-ff9-installer-packaging]]` for the onboarding/installer state.

**Docs overhaul (2026-07-07):** user docs accuracy+tone pass at b12 — CLI ref regenerated (97 cmds), F6/patch-range/pillar claims fixed, personalization + internal-brief leakage stripped repo-wide; tutorials split into `ff9mapkit/docs/tutorials/` (11 single-goal pages; `TUTORIAL.md`/`FORKING_FF9.md` = stubs). `[[playable]]` FORMAT.md schema section — DONE 2026-07-07 (full key tables: core / battle-model / abilities / minted command / custom ability / custom status; grounded in the parser + the thirteenth-character example).

**EXPERIMENTAL — image → explorable field (★ MVP in-game proven 2026-07-08):** `ff9mapkit image-field <img> --floor "cx,cy …"` synthesizes a walkable field from ANY image + a hand-traced floor polygon. The floor is un-projected onto the world ground plane into a walkmesh (FF9's field projection is PERSPECTIVE → a closed-form plane HOMOGRAPHY, verified round-trip 2.3e-12; use `cam.inv3(R_view)` NOT transpose — the k=14/15 squash makes R_view non-orthonormal); the image is the painted background; camera + `.bgi`/`.bgx`/deploy are existing proven machinery. Pillow-only MVP (`ff9mapkit/imagefield.py`, 9 tests); grounded by a 10-agent research + adversarial-verify pass. ★ Walked a synth test room at slot 30058 (stands on floor / walks the trapezoid / foreshortening reads right). ★ ANCHORED OCCLUDERS in-game proven 2026-07-09 — `--foreground img.png@cx,cy` sets the cut-out's Z to the actor OT depth at its floor contact (`resz/4 + depthOffset`, FieldMapActor.cs:122): walk-behind = occluded (head pokes past the cut-out's own pixels, the correct coarse behavior), walk-in-front = actor on top; + `--trace` = a self-contained HTML floor tracer (exact canvas crop, pitch-slider horizon, emits the command) — ★ REAL PHOTO proven same day (the user's hallway in-game via the tracer). `--auto-floor` (numpy seeded region grow, refusal-biased, pre-loads the tracer; `ff9mapkit[image]` extra) + a full-res cover-crop fix (pre-fix photo deploys are soft — rebuild to sharpen) shipped 2026-07-09, offline-proven IoU≥0.8. NEXT: neural depth (`[depth]` onnx) auto occluders, refuse/fallback gate + stylizer → [[project-ff9-image-to-field]].

---

## 11. Glossary

- **Field** — one explorable screen with a fixed-perspective pre-rendered background.
- **Walkmesh** — invisible per-floor geometry defining the walkable area + depth.
- **Main_Init / Main_Reinit** — a field script's entry function / its after-battle re-entry
  (entry-0 tag-10).
- **Gateway** — a region trigger that warps the player between fields.
- **BG-borrow vs custom scene** — reuse a real field's art (DictionaryPatch) vs ship our own
  `.bgx`+PNGs+`.bgi`.
- **field.toml / scene.toml** — the kit's logic file / Blender's spatial file (merged at build).
- **GLOB vs MAP flag** — save-persistent (`gEventGlobal`) vs per-field-transient story state.
- **F6 debug menu** — the in-game debug tool, shipped in the engine bundle (Warp/Move/Cheats/Flags/Time).
