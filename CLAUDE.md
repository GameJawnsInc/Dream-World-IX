# CLAUDE.md — FF9 Custom-Field Toolkit (`ff9mapkit`, Memoria Engine)

> **The working brief — keep it lean.** It holds only durable, every-session facts. The project's
> narrative lives in `git log` (descriptive, ~1 commit per feature) and the deep recipes in the
> project-memory files (§9); don't reproduce them here. As work lands, update **§5 (current state)**
> and add at most a **one-line** entry to **§10 (milestones)** — never a paragraph. (Consolidated
> 2026-06-08; §10 de-journaled to a status list 2026-06-12 — see `git log` for the prior blow-by-blow.)

---

## 1. What this project is now

It began as "add one playable custom room to FF9 (Steam, Memoria engine)." **That is long done.**
It is now **`ff9mapkit`**: a Python toolkit + Blender add-on that compiles a declarative **`field.toml`**
into a complete drop-in Memoria mod — a brand-new FF9 field (camera, walkmesh, painted art, NPCs, dialogue,
gateways, encounters, events, story branching, cutscenes, ladders, jumps, props, save points) — and can
**import/fork any of FF9's ~674 real fields**, carrying their NPCs/props/lighting/dialogue faithfully.
Further pillars: **custom 3D battle backgrounds**, **multi-field campaigns** (Campaign-Editor IDE),
**story-flag tooling**, **items/equipment/shops**. It runs on **stock Memoria** (the shipped mod is
engine-independent; the local *dev* engine adds only an F6 debug menu). Likely the first practical reference
for FF9 custom-field authoring.

**North star — fork FIDELITY, not a release:** keep refining forked fields until the kit can recreate the
*functioning game itself* from them. The measure: "fork a real field → does it play identically?" Do **not**
frame work as "near-release" / "release prep" — that pressure is explicitly unwanted. The *physical* layer
(scene/walkmesh/camera/mechanics/object-carry) is largely faithful + in-game proven; the *narrative-state*
layer is the weak axis (a fork boots at scenario-zero). Honest gap map: **`ff9mapkit/docs/FORK_FIDELITY.md`**.
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
- **Commit FREELY — follow the FF-master merge discipline when hitting tested milestones. NOTHING PUBLIC** —
  no `git push`/remote, no PRs, no PyPI, no forum/Discord posts. Local commits only. (Updated 2026-06-12: the
  old "commit only when asked" gate is LIFTED — commit tested milestones via commit-on-feature-branch → FF
  master (rebase-second); the no-public rule is unchanged. → `feedback-commit-freely`.)

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
| GUI apps | in **`apps/`** — ONE app now (GUI makeover COMPLETE, Phase 6): `ff9_workspace.pyw` (= `ff9_studio.pyw`, the front door) launches the **PySide6 Workspace** — one dockable window: a **journey ▸ campaign ▸ field ▸ object** tree + breadcrumb (**Open Journey…** opens a journeys.toml as the front door — the whole arc loads top-down, lints the namespace guarantee into Problems, and you drill into any member campaign to edit it), and as tabs the **Editor** (field/NPC/gateway/event/marker/cutscene/choice forms + catalog picker), **Map** (campaign graph), **Story State** + **Item & Equip** save editors, **Build & Deploy** (field/campaign/battle, auto-detected), and **Import** (fork a real field; fork-report/read-dialogue/inspect-save), with the **Info Hub** as a sectioned **library** (category sidebar + per-section search + a rich detail pane: facts/animations/movement/parts/aliases + a ready `field.toml` snippet) + a **Ctrl-K** palette + a bottom Output/Problems console; the right **Inspector** gives per-node cards (a field's content rollup + clickable `campaign_graph` cross-refs "exits to / reached from", entity summaries with gateway-destination resolution); dialogue fields (NPC/event/choice) carry a **live FF9-window wrap preview**. Creation is in the shell too — the toolbar folds New/Open into **3 hierarchy dropdowns** (**Field** / **Campaign** / **Journey**, each New + Open): **New Field…** (Ctrl-N) / **New Campaign…** (Ctrl-Shift-N) / **New Journey…** (a commented onboarding `journeys.toml` template) / campaign-root **Add field…** (thin dialogs over `pack.new_project`/`campaign.new_campaign`/`add_field`); plus **undo/redo** (Ctrl-Z / Ctrl-Shift-Z, a checkpoint-diff history over each field's `doc.data`, focus-aware so a focused text field undoes its own typing first). The 8 standalone tkinter `.pyw` (campaign_editor/import/build_gui/editor/dialogue/infohub/storystate/items) were **RETIRED** — everything they did is folded into the Workspace over the same tk-free backends (`editor/{forms,model,theme,feedback,breadcrumb,jobs}`, `campaign`, `save`, `save_items`, `flags`, `infohub`, `dialogue`). PySide6 = optional `gui` extra. → [[project-ff9-gui-makeover]] |
| Reference field scripts | `reference/test2/` (gitignored, 817 HW field-script exports) + `reference/field-manifest.tsv` (HW-index→field-id→name; index ≠ field id) |
| FF9 field assets | `<game>\StreamingAssets\p0data*.bin` (UnityRaw 5.2.3 bundles; UnityPy reads them — `py -m pip install UnityPy`) |

> **Layout in one breath** (full detail → [[project-ff9-git-layout]]): worktrees share one install but each
> deploys into its OWN Memoria mod folder, pinned in a gitignored **`.ff9deploy.toml`** (`mod_folder` +
> scratch-band `id`; override via `--mod-folder`/`$FF9_MOD_FOLDER`). `Memoria.ini [Mod] FolderNames` stacks
> the folders; each folder's own DictionaryPatch/BattlePatch is read at launch. **Distinct ids are required
> even across folders** (EventDB/SceneData are GLOBAL). Slots: master → `FF9CustomMap`/**30000** ·
> `-battle-backgrounds` → `…-bb`/**30001** · `-infohub-catalog` → `…-ih`/**30002**; reach any via F6 → Warp.
> **Field-id bands:** **10-3100** real (locked) · **4000-9899** shipped custom · **30000-32767** dev scratch
> (engine `fldMapNo` is Int16 → max **32767**; a higher id registers but is unreachable).
> **Merge discipline:** make CLAUDE.md edits on the *feature* branch; keep `master` **FF-only** (the second
> concurrent feeder rebases). FF without checkout: `git -C C:\gd\FFIX merge --ff-only <branch>`.

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

**Text-block shadow (stacked worktree folders):** every worktree's test slot defaults `text_block` 1073,
and the engine reads a field's `.mes` from the **highest-priority** `FolderNames` folder that defines it —
so a lower-priority worktree's dialogue is SHADOWED (wrong text, but the *flags* are still correct → F6 →
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

- **Dev engine** = stock Memoria `6b8bb2d5` + the **F6 debug menu only** (`UIKeyTrigger.cs` +
  `Ff9mkDebugMenu.cs`; patch `memoria-patches/s22-debug-menu-f6.patch`). Boosters are manual
  (ini cheats + F1–F4). The *shipped* mod needs none of this — it's engine-independent.
  Revert engine → no-edits rebuild: `tools/restore_memoria_dll.py baseline`; true stock = re-run the patcher.
- **F6 debug menu** (dev build, in **FIELD and BATTLE** — in-game proven 2026-06-09): a draggable tabbed
  IMGUI popup —
  **Warp** (reload field · warp to any registered custom id ≥4000) ·
  **Move** (teleport to x,z · right-click the field to copy the floor (x,z) under the cursor) ·
  **Cheats** (booster toggles · full-heal · give item/gil) ·
  **Flags** (get/set/clear a `gEventGlobal` story flag · snapshot/restore · reset-all) ·
  **Time** (0.25–4× time-scale). The menu is a `DontDestroyOnLoad` MonoBehaviour so its OnGUI already
  draws in battle; the F6 toggle gate (`UIKeyTrigger.Update`) was widened from `FieldHUD` to
  `FieldHUD || BattleHUD`. In battle the field-only **Warp/Move** tabs show a "field only" note and
  no-op; **Cheats/Flags/Time** operate on the shared party/flag/time state (handy for testing battle
  maps). Battle is NOT auto-paused while open (so Time-tab slow-mo persists on close) and NGUI input
  under the popup isn't blocked — keep the window top-left, off the battle command UI. **This SUPERSEDES
  the old single-key F6-reload / F10-reset hotkeys — do not refer to those as current.**
- **The Vivi hut is RETIRED to offline build-oracle status.** The two painted hut rooms (**4000** ext +
  **4002** int, the 100%-kit-authored copy in **`release/FF9CustomMap/`**) were the S0 "can we make ANY
  custom field?" proof; their only remaining job is the **byte-exact golden test** (`examples/vivi-hut/` →
  the provenance manifest SHA), which needs zero in-game upkeep. **Do NOT re-polish the hut in-game — the
  in-game showcase is the World Hub + verbatim forks.** (The live dev `FF9CustomMap` is a churned scratchpad:
  test deploys overwrite scene folders, so the hut's `FBG_N11_HUT_*` scenes are usually absent — redeploy
  from `release/` to actually play it.) Registered: 4000 HUT_EXT, 4002 HUT_INT, **4003 = the shared test slot**.
- **New Game lands via a stock mod field-70 override (`Field(<id>)`), NOT a DLL edit** — the only custom DLL
  is the F6 menu. Currently retargeted to the **Mognet Central journey hub (4600)** (`tools/retarget_newgame_warp.py`
  4600, 2026-06-14; was the old World Hub 4500). The field-70 opening's own fade-out is preserved, so New Game
  fades to black → Field(4600) (seamless, no FMV). The mechanism + seamless-entry lever + starting-state
  capstone → [[project-ff9-new-game-entry]].
- **Versions:** kit `0.9.81`, Blender add-on `0.9.7`. **Provenance gate is CLEARED** — the
  repo ships ZERO Square-Enix bytes; base templates are regenerated from the user's own
  install via `ff9mapkit extract-templates` (patches + SHA-256 manifest). `*.eb.bytes` /
  `*.bgx` / `*.bgi.bytes` are gitignored (except our own hut quad).
- **Open public item (do NOT act):** Memoria PR #1433 (FieldCreatorScene PNG-path fix) — left
  as-is, irrelevant to the toolkit. Nothing else pending; standing constraint = nothing public.

---

## 6. The toolkit at a glance (capabilities — all in-game proven)

`ff9mapkit` compiles `field.toml` → mod. The full content/scripting stack, each verified in
real gameplay and reproducible in Python (zero Hades Workshop):

- **Field & scene:** mint a custom field id (≥4000); single / **scrolling** / **multi-camera**
  cameras; human-painted art layers with depth-based occlusion; walkmesh authored from math OR
  imported/reshaped from a real field.
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
- **Campaigns:** `import-chain <seed>` forks a connected slice of the game into one drop-in mod; the
  **Campaign Editor** IDE (navigator + graph + Map + authoring) edits the multi-field project.
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
  walkmesh collision).

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

**Dev engine** (`project-ff9-memoria-build`)
- Read dev hotkeys in a real MonoBehaviour `Update()` (e.g. `UIKeyTrigger`) via
  `UnityXInput.Input` — **NOT** `HonoLateUpdate` (the ~30 fps logical tick misses `GetKeyDown`).

**Process** — Hades Workshop is fully OUT (atlas-clone UV bug + its export corrupts entry-adds; author `.eb`
in Python, verify with `eb_disasm`/the kit). Never edit a bundled example in place (the form editor's Save
rewrites the byte-exact golden oracle — author on a copy / `ff9mapkit new` / a Blender export). Grep alone
can't prove a field unused (scenario-counter dispatch / runtime-computed ids / scripted `Field()` warps are
invisible to it) — trust the user's game knowledge; NarrowMapList is a camera-WIDTH table, NOT a cutscene
trigger (entry cutscenes run from the `.eb`). → `project_ff9_mint_gotchas`, `feedback_trust_user_game_knowledge`, `project_ff9_has_no_unused_fields`.

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
  675 fields: 55 NPCs lose their tag-3 handler, 0 blocked only by a graftable gesture — an NPC's interactive
  tag-3 IS the field's quest logic, inseparable). Use **`--verbatim`**; read what an NPC does with
  **`fork-report --explain`**. (#13, the story-event director/roster problem, is separate; its CORE is now
  in-game proven — `--verbatim` + `[startup]` shows a beat-correct rotating roster — see §10.)
  → [[project-ff9-fork-fidelity-worklist]].

---

## 9. Project memory (the deep recipes)

Read these on demand — they hold the full technical detail this file only summarizes
(`~/.claude/projects/C--gd-FFIX/memory/`, indexed by `MEMORY.md`):

- `project-ff9-eb-script-tooling` — `.eb` format + opcode tables, Python injection, custom
  text/MES, the F6 debug menu, the cutscene-in-LOOP rule, flag persistence.
- `project-ff9-camera-math` — the projection invariant, decompose/synthesize, scale-1 canvas
  map, character offset, yaw, multi-camera convention.
- `project-ff9-import-frame` — the `vert + orgPos + floor.org` walkmesh frame; simple vs multi-floor forks.
- `project-ff9-novel-bg-pipeline` — painted-BG / overlay-depth / occlusion pipeline.
- `project-ff9-gateway-regions` — region trigger mechanics + IsInQuad dead zones.
- `project-ff9-encounters` — random battles + the after-battle Main_Reinit fix.
- `project-ff9-ate-system` — Active Time Events: the "Press SELECT" optional cutscenes are almost all field-`.eb`
  (GetChoose → `op_0B` jump table); engine does 3 things (blink opcode `AICON=0xD7` — NOT `BARATE`; `winATE=64`
  flag; achievement-only `AteCheck` seen table). `--verbatim` carries them. Full teardown = `docs/ATE_SYSTEM.md`.
- `project-ff9-memoria-build` — local engine build toolchain + auto-deploy + version-match.
- `project-ff9-object-carry` — faithful NPC/prop carry: verbatim `.eb`-entry graft + player-func graft +
  text carry + the v1.5 STARTSEQ-helper closure; the cross-ref remap + the engine facts (tag 2 = push, etc.).
- `project-ff9-savepoint` — the save point = `Menu(4,0)`; synthesize the region, don't graft the cluster.
- `project-ff9-story-flags` — the `gEventGlobal` heap map + the 5 verbs + the safe band (bit 8512) + the
  AES `SavedData_ww.dat` codec.
- `project-ff9-jump-navigation` — navigable jumps = ladder mechanism minus the climb loop; the entry-table fix.
- `project-ff9-battle-backgrounds` — custom 3D battle maps (all tiers) + the raw17 camera recipe.
- `project-ff9-battle-tuning` — battle GAMEPLAY tuning (not backgrounds): the 4-channel model (raw16
  `SB2_MON_PARM` / Data CSVs / battle `.eb` AI / field `.eb` wiring), the no-DLL boundary, the roadmap.
  Full gap map = `docs/BATTLE_DESIGN.md`.
- `project-ff9-infohub-authoring` — place any field model/prop/creature by NAME (archetypes/props/creatures);
  the model→animation join; the Info Hub catalog + viewer + debug arena.
- `project-ff9-import-fidelity` — `import --editable` = a scaffold (faithful carry now exists separately).
- `project-ff9-worldmap-feasibility` — field-chain campaign done; custom overworld = the hardest unstarted.
- `project-ff9-bg-borrow-solution`, `project-ff9-mint-proven`, `project-ff9-mint-gotchas` — minting + BG-borrow + HW dead-ends.
- `feedback_trust_user_game_knowledge`, `project_ff9_has_no_unused_fields`,
  `project_ff9_field_warp_pattern`, `reference_ff9_modding_community` — process + community.

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

**Pillars (all in-game proven):**
- Battle backgrounds — all tiers (reskin / FBX / new-scene / camera), no DLL → [[project_ff9_battle_backgrounds]]
- Campaigns — `import-chain` + the Campaign-Editor IDE → [[project_ff9_worldmap_feasibility]]
- Navigable jumps + save points (synthesized & verbatim save-Moogle) → [[project_ff9_jump_navigation]], [[project_ff9_savepoint]]
- Story flags — `gEventGlobal` mapped, 5 verbs, safe band ≥8512, `[startup]`/`[[on_entry]]` → [[project-ff9-story-flags]]
- Faithful object/NPC carry → verbatim fork (`--verbatim` = the truest fork: real logic + real text) → [[project-ff9-verbatim-fork]], [[project_ff9_object_carry]]
- Non-Zidane donors + PC/party control (`--swap-player`, `[party]`) → [[project-ff9-non-zidane-donors]], [[project-ff9-pc-party-system]]
- Items / equipment / shops + the New-Game starting-state capstone → [[project-ff9-items-equipment]], [[project-ff9-new-game-entry]]
- Campaign-scale New-Game capstone — New Game → a forked verbatim CHAIN that plays its real story (Dali: wake-up → Garnet rejoins @2640), beat/bag/gear seeded on the entry; `tools/retarget_newgame_warp.py` + `import-chain --name-prefix` (cross-worktree FBG/EVT namespace); `deploy_campaign` auto-promotes start-state CSVs to the highest folder + ABORTS on a cross-folder EVT/FBG name collision (`--allow-name-collision` to override) → [[project-ff9-new-game-entry]]
- InfoHub authoring — place any model/prop/creature by name → [[project-ff9-infohub-authoring]]
- `fork-report` — preview a fork's fidelity offline (roster/interaction/player/party/dialogue/items/camera + `--explain`)
- World Hub — a playable journey selector (choice `warp` + `[player] model=` moogle PC): a `journeys.toml` → hub-field **generator** (`ff9mapkit gen-hub`; `docs/JOURNEYS.md` schema — `id`/`name`/`entry`/seed); New Game → hub (seamless); journeys warp into REAL verbatim forks (Dali 4100 + Treno-Pub 4501); an entry **camera-settle** (`[camera] entry_settle`) — the warp-in drift is an F6-debug-warp artifact, the shipped New-Game/gateway entries are clean. → [[project-ff9-world-hub]]
- Multi-campaign journey **assembler** (`ff9mapkit/journey.py`; CLI `lint-journey`/`assemble-journey`; `tools/deploy_journey.py`) — BUILT: one unified `journeys.toml` (`[hub]` + bare `entry=<id>` OR multi-campaign `campaigns`/`entry={campaign,field}`/`[journey.seed]`/`[[journey.link]]` rows); resolves member NAMEs → global ids, assigns disjoint flag windows, lints the GLOBAL id-disjointness guarantee across every campaign of every journey (the §8 "whole job"); folds `hub.render_hub_field_toml` in so one renderer serves bare + multi; and the **deploy orchestration** — `build_deploy_plan`/`render_deploy_playbook`/`apply_link_rewrites` (+ `build_campaign(flag_base=)`, `deploy_campaign --flag-base`): each campaign into its own stacked folder at its flag window, each cross-campaign link realized by byte-patching the boundary `.eb` `Field(seam)` → next entry (`verbatim.remap_fields`, all langs, revert-guarded), then hub + New-Game retarget. `deploy_journey` (dry-run) prints the ordered playbook of proven, revert-guarded steps; `--apply-links` runs the one journey-unique step. ★ **IN-GAME PROVEN (2026-06-13)**: a forked Ice Cavern → Ice Cavern/Outside arc (6200-6211 + 6300, each its own folder/flag window) — walking out the cavern exit (6211) lands in the FORKED Outside (6300), the cross-campaign link firing. Gotcha: `deploy_campaign` wholesale-replaces a folder, so `--apply-links` must run LAST + be re-run after any campaign re-deploy (the playbook warns). ★ **WORLD-MAP LEG DONE + IN-GAME PROVEN (2026-06-13)**: an overworld-seam boundary (exit-to-world-map: a `WorldMap` op, no `Field()` to retarget) is wired by the second link mode **`worldmap_inject`** — body-replace its tag-2 walk-out region with the proven gateway `Field(dst)` warp body, reusing the region's own map-edge zone (no new entry slot / no double-exit). Walking out the forked Ice Cavern ENTRANCE's worldmap exit (6200) now lands in the forked Outside (6300). **The assembler is COMPLETE** (both link modes proven: `field_remap` + `worldmap_inject`). ★ **ONE-SHOT `deploy_journey --apply` + `[journey.seed]` capstone**: `--apply` pre-builds every campaign + the hub offline (fail before any game write), installs the prebuilt dists, applies the links, deploys the hub (auto-extracting its `borrow_field` camera) — New Game UNTOUCHED unless `--wire-newgame` (single-owner); one reverse-order `revert_journey.py`. `[journey.seed]` (scenario/party) bakes into the entry fork's own `.eb` via `build_campaign(seed_blocks=)` → `apply_seed_blocks`/`journey.seed_to_field_blocks` (per-journey-clean); seed inventory/equipment map to mod-GLOBAL New-Game CSVs (lint-warns; per-journey items want scripted `give_item`, a follow-up). Snappy menus: `[[choice]] instant=true` → FF9's `[IMME]` (hub default on). → [[project-ff9-world-hub]]
- Active Time Events — full teardown + BOTH real flavors authorable & ★ IN-GAME PROVEN: the **OPTIONAL** Press-SELECT menu (`[ate]` = prompt + winATE menu + `GetChoose` branch; arms on a story-set avail WORD in `gEventGlobal` byte 236, NOT the scenario — each bit = one menu row) AND the **GREY UNSKIPPABLE** auto-ATE (`[cutscene] ate = true`, default `ate_mode = 6` = the grey force-show bottom-left "ACTIVE TIME EVENT" banner `ActiveTimeEvent.cs`; `ATE(6)…ATE(0)` + winATE caption). PLUS cold-reproduce REAL ATEs in `--verbatim` forks by seeding the beat. Test slots: synth menu @30007 · Lindblum Small-Town-Knight @30006 · real Eiko menu @30009 · real grey-unskippable (Gargant 956, `[startup] scenario=7006`) @30010 · authored grey banner @30008. ★ Mode map (676-field sweep, corrected from a wrong "mode 6 = transition fade" call the USER caught): mode 1 = optional/blue, **mode 6 = grey unskippable**, mode 2 unused, mode 5 = the single field-206 menu-open → [[project-ff9-ate-system]]
- Offline field-art export — assemble Memoria's per-overlay `Overlay{i}.png` straight from the p0data atlas (`scene/bgart.py` + `extract._overlay_art`), replacing the hang-prone in-game `[Export] Field=1` startup dump; byte-exact vs the engine's own `atlas.png` crop, ≤3/255 across all 582 dumped fields (`tools/verify_overlay_export_parity.py`). Batch CLI **`ff9mapkit export-art [<field> | <campaign.toml> | --all]`** = the drop-in (writes `FieldMaps/<FBG>/Overlay{i}.png` + `atlas.png`, no launch); **`--composite`** = one clean background PNG/field (browsable gallery). **`ff9mapkit import-all`** = a foldered whole-game Blender archive (`<out>/<ZONE>/<FBG>/`, lightweight by default) → [[project-ff9-novel-bg-pipeline]]
- Blender MULTI-CAMERA fidelity — the import drops ALL of a field's cameras (`FF9_Camera`+`_01`..) so its walkmesh is framed/modelable under each (not just cam0); and **per-camera ART** (`BGOVERLAY_DEF.camNdx` = which camera paints an overlay) gives each camera its own backdrop instead of all overlays jammed onto cam0's canvas. `compose_background(camera_index=K)` + `background_cam0K.png`; the **View Selected Camera** op matches render-res to a camera's range. 100% per-camera footprint coverage across 14 multi-cam fields; Blender-proven on Crystal World 2934. Editable forks of multi-cam fields warn → use `--verbatim` (faithful multi-cam path) → [[project-ff9-novel-bg-pipeline]]
- Advanced interactables (moving platforms / elevators / lifts) — field `.eb` tile-motion (`MoveTileLoop`=rideable, `MoveTile`=one-shot, `AttachTile`=player rides); `--verbatim` CARRIES them. ★ IN-GAME PROVEN: rode a cold fork of the Lindblum Castle Lift (2151) end-to-end (picked Upper Level → ride → arrived via the live `Field()` seam). Authoring a declarative `[[platform]]` is the FRONTIER (opcode emit covered by `cmdasm`; needs `AttachTile`/`MoveTileLoop` arg semantics + walkmesh-anim authoring — overlaps #13) → [[project-ff9-moving-platforms-elevators]]
- Field logic-map — make a verbatim fork's entangled `.eb` LEGIBLE + EDITABLE in place (sidesteps dead-end #14: don't extract a tag-3, map+edit the whole web). READ (`logic_map.build_logic_map` + `logic-map` CLI + GUI "Script" subtree/badge: entries→routines, resolved RunScript call graph, per-routine dialogue/items/flags) · DECODE (`disasm.decode_switch`: 0x06/0x0B/0x0D case→target, validated 5563/5563 boundary-aligned) · VALIDATE (`eblint.lint_eb`, the ailint analogue: decode/jump+switch-bounds/reachable-terminator, 676 fields lint 0-error) · EDIT (`logic_edit.py` `[[logic_edit]]`: old-guarded, lint-gated value swaps — field/item/gil/txid/flag + a verified `.mes` text splice; a **flag remap that crosses the 0xFF C4/E4 token boundary** is length-changing, rebuilt via the keystone — redirect a donor's narrative gate to a custom flag; **GUI authoring** of edits from the "Script" tree) · ADD (`logic_add.py` `[[logic_add]]`: length-CHANGING guarded additions — set_flag/give_item/give_gil/**show_line** (+ `message=` on any kind to ANNOUNCE its effect, the give_item "Received…" box), Phase 4a prepend + Phase 4b `where="after"` mid-insert, on the `cmdasm` labeled-disassemble→splice→reassemble keystone that relocates jumps/switch; a `show_line` line rides the `[[on_entry]]`-style `.mes` append-and-resolve channel). ★ IN-GAME PROVEN: `[[logic_edit]]` .mes line + give/display operand (2026-06-14, Dali Inn / Ice Cavern chest); GUI-authored Phoenix Down chest, Phase 4a once-guarded give, Phase 4b mid-insert give+gil, `show_line` give_item ANNOUNCE (2026-06-15). **GUI authoring of `[[logic_add]]`** (Script panel "Add effect…": give_item/give_gil/set_flag/show_line, prepend or after-an-instruction, dry-run-validated via `build.dry_run_logic_adds`) — DONE, so the panel authors BOTH value edits + length-changing adds. **Cross-0xFF flag remap** (a `flag_index` edit that crosses the C4/E4 width boundary, keystone-rebuilt) — ★ IN-GAME PROVEN (redirected a real Ice Cavern chest gate to a `[startup]`-set custom flag; lesson: remap EVERY use of the flag or the gate won't latch). **`switch_case` redirect** (re-point a jump-table `0x06/0x0B/0x0D` case/default arm to a different in-function target) — ★ IN-GAME PROVEN (a field-206 ATE warp-menu fork: redirected the top row → row 1's branch, picking it warped to field 112 not 208; ATE armed via a 4-global `[startup]` seed) · **`[[logic_add]] add_case`** (ADD a new dispatch arm to a switch — a scenario value / menu row that runs a reused effect then rejoins the default; `0x0B` contiguous `case="auto"`, `0x06` explicit value) — ★ IN-GAME PROVEN (field-206 Main_Init scenario switch: added case 1950 → give Phoenix Down, `[startup] scenario=1950` fired it on entry, once-guard held). **The ENTIRE logic-map edit tier is now in-game proven.** Known limitation: a `message`/`show_line` in an arm that runs at FIELD LOAD (Main_Init dispatch, pre-usercontrol) does not render — the EFFECT (give/flag) fires, but a bare `WindowSync` can't show at load. ★ Mechanism CORRECTED by the user (2026-06-16): wrapping it INLINE in the `Wait`+`DisableMove` dance does NOT hang — the message OPENS but sits UNDER the entry fade-out overlay (screen black) and its `WindowSync` blocks the fade-in until you press input to dismiss it; recoverable, not a crash, but UX-broken (reverted `8acc7fe`). It can't be fixed in place — an `add_case` arm runs synchronously inside Main_Init *before* the scene/fade exist, so any window it opens is under the black; `[[on_entry]]` works only because it runs as a separate `InitCode` coroutine the frame AFTER Main_Init (post-fade). **The field-load give+announce is ALREADY a built, proven path: a single `[[on_entry]]` block does items+gil+`message`, gated on `requires_scenario`/`requires_flag`** (so `add_case` = dispatch LOGIC, `[[on_entry]]` = load-time give+announce; the "atomic single-block" frontier is moot). ★ A/B IN-GAME PROVEN (2026-06-16, field-206 fork @4003): same `scenario=1950` entry — the add_case message stayed silent, the `[[on_entry]]` give+announce rendered post-fade. **`[[logic_add]] menu_row`** (the full coordinated MENU ROW: add a NEW selectable+labelled choice-menu row — `add_case` dispatch + best-effort `EnableDialogChoices` mask widen + a verified `.mes` row splice/`[PCHC]` count bump) — ★ IN-GAME PROVEN (Black Mage Village inn 3053 fork: the innkeeper's "Will you be staying? Yes/No" menu gained a "Get a free Potion!" row that gives a Potion + box; v1 targets base-0 contiguous, text-gated `[PCHC]`/no-pretag, rows==ncases menus, fails closed on `[PCHM]` + non-1:1 menus; `logic_edit.verified_mes_splice` shared with the dialogue rewrite; 3-lens review hardened the leg-A/leg-C alignment + trailing-tag + pretag-arity guards). **GUI authoring**: the Script panel's "Add menu row…" action (shown on a routine with a choice menu; menu-txid pre-filled, dry-run-gated, revert/undo like the other adds). **The logic-map EDIT tier is now COMPLETE — no open frontier.** → [[project-ff9-field-logic-map]]

**Latest:** kit 0.9.87, 1510 tests (suite ~146s serial / ~64s `-n 6` via pytest-xdist; an in-process static-bundle
cache stops it re-reading the 68 MB event bundle per install-gated call — a "2-hour" run is contention, not a
regression → [[project-ff9-test-suite-perf]]). **Multi-campaign journey ASSEMBLER — BUILT** (`ff9mapkit/journey.py`
+ CLI `lint-journey`/`assemble-journey` + `tools/deploy_journey.py`; 32 tests): one unified `journeys.toml` (`[hub]` + bare
`entry=<id>` OR multi-campaign `campaigns`/`entry={campaign,field}`/`[journey.seed]`/`[[journey.link]]`); `load_journeys`/
`resolve_journey` (member NAMEs → global ids, disjoint flag windows)/`lint_manifest` (the §8 GLOBAL id-disjointness guarantee
across every campaign of every journey — one EventDB namespace, all registered at launch)/`manifest_to_hub_spec`+`generate_hub`
(folds `hub.render_hub_field_toml` so ONE renderer serves bare + multi; `hub.hubspec_from_table` extracted); plus the deploy
orchestration `build_deploy_plan`/`render_deploy_playbook`/`apply_link_rewrites` (+ `build_campaign(flag_base=)`,
`deploy_campaign --flag-base`) — each campaign into its own stacked folder at its flag window, each cross-campaign link a
byte-patch of the boundary `.eb` `Field(seam)`→next entry (`verbatim.remap_fields`, all langs, revert-guarded), then hub +
New-Game retarget; `deploy_journey` (dry-run) prints the ordered playbook of proven revert-guarded steps, `--apply-links`
runs the one journey-unique step. Open §6 decisions resolved in `docs/JOURNEYS.md §9` (NAMEs preferred; link `from.field`/
alias `seam`; `[journey.seed]` IS the story_flags capstone; one-way). ★ **IN-GAME PROVEN (2026-06-13)**: a forked Ice
Cavern → Ice Cavern/Outside arc (`import-chain 300 --verbatim` 6200-6211 + `312 --verbatim` 6300, each its own folder/flag
window) — walking out the cavern exit (6211) warps into the FORKED Outside (6300), the cross-campaign link firing (the
boundary's `Field(312)` seam retargeted → 6300). Gotcha: `deploy_campaign` wholesale-replaces a folder → `--apply-links`
must run LAST + be re-run after any campaign re-deploy (else the link is wiped; symptom = landing on the real id). ★ **WORLD-MAP
LEG DONE + IN-GAME PROVEN (2026-06-13)**: the 2nd link mode `worldmap_inject` (a 5-agent disasm of real fields 300/311/312
found a real overworld handler is byte-identical to the kit gateway template but for its terminal `WorldMap(0xB6)` vs
`Field(0x2B)` op) — body-replace the boundary's tag-2 walk-out region with the proven gateway `Field(dst)` warp body via
`eb.edit.replace_function_body`, reusing the region's own map-edge zone (no new slot/zone/double-exit); walking out the forked
cavern ENTRANCE's worldmap exit (6200) lands in the forked Outside (6300). **The assembler is COMPLETE** (both link modes
proven). Before this: `deploy_campaign` productionized (auto-promote start-state CSVs to
the highest folder + ABORT on a cross-folder EVT/FBG name collision; wires New Game via the field-70 retarget, not the
broken field-100 hop) — ★ **IN-GAME PROVEN**: `--apply` → relaunch → New Game boots straight into the Dali chain.
World-Hub: `gen-hub` generator + New Game → hub → REAL verbatim journeys (Dali 4100 + Treno-Pub 4501) + entry
camera-settle — all IN-GAME PROVEN (the shipped entries are camera-clean; only the F6 debug warp drifts).
Active: **battle TUNING / encounter authoring** (`battle_design`) — recon + Phase 0/1/2/3/4/5: raw16 full codec + golden
round-trip; `[scene]` combat-identity tuning by name; `battle-actions` / `battle-scene` catalogs; the **offline
balance-lint** `scenelint.py`; **`[[battle_action]]`/`[[status]]`** CSV-delta ability/status rebalancing; **Phase 4 —
the `BattlePatch.txt` emitter** (`battlepatch.py`): `[[battle_patch]]` (scene-scoped) + `[[battle_enemy]]`/
`[[battle_attack]]` (global by-name `AnyEnemyByName:`/`AnyAttackByName:` = the campaign-wide WIN) reaching the
BP-only rate arrays / `BonusElement` / `MaxDamageLimit` / `WinCardRate`, the enemy ATTACK table, and scene flags
**without re-packing raw16**; merged non-clobbering into a live `BattlePatch.txt` under `//` markers + the BGM
block; CLI `battle-patch`. ★ **Phases 1 & 4 IN-GAME PROVEN** on the forked EF_R007 Goblin (P1: auto-Protect +
phys-def wall + AP; P4: a `[[battle_patch.attack]]` patched the enemy's normal attack by index — `power`+
`status_set` both landed, the inflicted `StatusSets.csv` bundle showed in-game = the `AA_DATA` enemy-attack lever
works by name; FULLY PROVEN — a follow-up confirmed `AnyEnemyByName: Goblin` (started Poisoned), `AnyAttackByName:
Goblin Punch` (power→1), the `back_attack` scene flag, and a guaranteed `drop_rates` Elixir, i.e. the
campaign-wide by-name channel + BP-only levers + scene flags in one fight). **Phase 5 — player-side CSVs**
(`characterdelta.py`): `[[character]]`→BaseStats.csv (per-id partial) + `[[leveling]]`→Leveling.csv (WHOLE-FILE,
read base 99 / patch / re-emit all 99); range-checked, provenance-clean, + the Leveling deploy shadow-guard; CLI
`characters`. ★ **IN-GAME PROVEN** — a `[[character]]` boost of Vivi + `[party] add` on a New-Game field showed
her tuned stats (40/80/90/45) in the status menu at a fresh New Game (BaseStats lands at the New-Game party build).
**Phase 5b** (`[[ability_gem]]` → AbilityGems.csv): re-cost a support ability's gem requirement by name/id
(committed SupportAbility table; `#! IncludeBoosted` preserved); CLI `ability-gems`. **Phase 6a** — the enemy-AI
**disassembler view** (read-only `battle-ai <scene>`): names the battle `.eb` vocabulary (`op_binary` expr table
+ `0xC0` var decode → `Global.Bit[..]`/`B_CURHP`; `eb.pretty_expr`; `battle/battleai.py` walks Main_Init + per-type
AI by tag), proven by a byte-walk PARITY test vs `read_code`. **Phase 6b** — same-length AI constant patches
(`battle/aipatch.py`): `constant_sites` locates every patchable literal (offset+width, mirroring the decoders),
`battle-ai --sites` lists them, `[[scene.ai_patch]]` (battle.toml) does an `at`/`old`-guarded/`new` in-place edit
(no fpos fixup; applied per-lang to the forked eb). **Phase 6c-i** — the enemy-AI expression **ASSEMBLER**
(`eb/exprasm.py`), the keystone of new-branch authoring: the exact INVERSE of the 6a disassembler
(`assemble(pretty_expr(b)) == b` byte-for-byte, proven against the real EF_R007 AI), CLI `battle-ai --asm`; each
token inverts a `pretty_expr` branch (op / `const`+`const4` / the `0xC0` minimal var encoding / sysvar / obj /
member-ptr). **Phase 6c-ii** — the enemy-AI **COMMAND assembler** (`eb/cmdasm.py`, mirrors `read_code`'s byte-walk
+ resolves `label:`/symbolic jumps in two passes) + **branch insertion** (`battle/aiauthor.py`: `add_ai_function`/
`replace_ai_function` splice an assembled branch via the existing byte-safe `eb.edit` fpos-fixup primitives — the
first LENGTH-CHANGING AI edit), CLI `battle-ai --asm-block`; round-trip proven on the real EF_R007 AI (every
instruction + function byte-for-byte; insertion re-parses everything-else-intact). **Phase 6c-iii** — the enemy-AI
**LINTER** (`battle/ailint.py`: decode / jump-bounds / reachable-RET reachability walk / Attack-idx range — a
**562-scene sweep lints ALL shipping scenes CLEAN**, the soundness proof; CLI `battle-ai --lint`) + the declarative
**`[[scene.ai_function]]`** build surface (`aiauthor.apply_ai_functions`, spliced per-lang AFTER `ai_patch`; the
validate hook lints the COMPOSED shipped eb) — **Phase 6c COMPLETE + ★ IN-GAME PROVEN (2026-06-13)**: a `[[scene.ai_function]]` RET-ing the forked Goblin's tag-5 attack routine (`battle_tests/bt_goblin`) made it stand idle (Phase-4 Poison then killed it). Dispatch model = an enemy turn → tag 7 (ATB); the spawned enemy's ENTRY is bound by Main_Init's `InitObject` (Goblin → entry 2, NOT the labelled "type 0"); the `Attack` cmd lives in **tag 5** → [[project-ff9-battle-tuning]]. ★★ **ESCALATED + IN-GAME PROVEN (2026-06-13)** — beyond RET (stop acting) to CHANGING the attack: reseeding the Goblin's per-slot attack seed (`Instance.Int24[0]` 323→130, a same-length byte patch) made it use **Goblin Punch every turn** instead of Knife. Two load-bearing facts: (a) Main_Init's `SWITCH(B_SYSVAR[31])` keys the AI bind on **`B_SYSVAR[31]` = `btl_scene.PatNum`** (the PICKED PATTERN, NOT the enemy type) — a forked scene whose patterns spawn different types runs the WRONG AI on a right-looking model (fix = 1-byte `InitObject` patch, NOT `monster_count`); (b) an enemy's attack = a per-slot SEED read as `enemy_attack[(Int24[0]>>slot*6)&63]`, so RESEED to change it (forcing the final `Attack({...})` index desyncs from tag-5's per-slot target setup → fizzle); a table attack no AI seeds (Fire here) likely isn't render-wired. ★★★ **BRANCH INSERTION also IN-GAME PROVEN (2026-06-13)** — the length-changing primitive: a 30-byte coin-flip conditional (`SET({B_SYSVAR[0] const(1) B_AND}); JMP_IF`) spliced into tag-5 right before the `Attack` via `eb.edit.insert_in_function` (does the fpos fixup; refuses a straddling jump — both rotation paths flow through it) makes the Goblin pick **Knife vs Goblin Punch each turn**. So every Phase-6c authoring primitive — **stop (RET) · reseed · insert-branch** — now runs in-engine; the full read→author→lint→ship stack is end-to-end proven. ★★★★ **STATE-DRIVEN HP-PHASE AI IN-GAME PROVEN (2026-06-13)** — the capstone: an inserted branch reads the Goblin's OWN battle HP and ENRAGES below half (Knife above 50% → Goblin Punch below), in-game. Self-HP read = `B_SYSLIST[1] B_MEMBER(36)` (cur) / `B_MEMBER(35)` (max) — N is a `btl_scrp.GetCharacterData` switch-case selector (NOT a byte offset; setter symmetric so `B_MEMBER(N) … B_LET_A` WRITES), distinct from the party-slot op_binary `B_CURHP`/`B_MAXHP`; mapped via a 7-agent workflow + a 562-scene sweep (56 bosses use the identical `cur < max/2` via the `_E`/`B_PICK`/`B_COUNT` extract idiom that binds the read target — a bare `B_LT` would not). A real boss-pattern enemy authored end-to-end from the kit, no DLL, lint-clean. Full selector map → [[project-ff9-battle-ai-members]].
★ Phases 2/3/4/5/5b/6a/6b/6c-i/6c-ii/6c-iii each validated by a multi-lens adversarial review (Phase 2: 562-scene sweep; Phase 3: caught
a boot-crash range bug + the cp1252 encoding; Phase 4: caught a `StatusSetId` over-range KeyNotFound crash, a
malformed-toml traceback, + a silent dead-`Battle:` selector; Phase 5: caught a fixture provenance leak + a
missing whole-file shadow-guard; 5b: an unresolvable display name; 6a: a truncated-eb crash; 6b: a 3-byte-immediate
KeyError + the B_CONST4 26-bit mask; 6c-i: an `opXX` back-door that assembled a bare operand-byte → desync, fixed +
`assemble()` now self-verifies its round trip as a library invariant; 6c-ii: a missing flow-terminator check
[RET-less branch runs off the function] + a backward `JMP_IFNOT` the engine reads UNSIGNED; 6c-iii: the linter
decoded `JMP_IFNOT` signed not unsigned [missed the backward-jump fault] + the validate hook lit the un-patched
donor not the composed eb) → [[project-ff9-battle-tuning]],
`docs/BATTLE_DESIGN.md`. Next: Phase 6c is COMPLETE; the deferred tail is raw17 btlseq sequence authoring (new codec + a coordinated raw16+eb+raw17 edit).
Frontier: #13 (story-event director/roster on rotating-cast fields) — ★ **core PROVEN** (a `--verbatim` fork +
`[startup]` shows a beat-correct rotating roster: forking Dali Weapon Shop 354 at SC 2600 vs 11090, the shopkeeper
changed + an NPC appeared, in-game 2026-06-12); the **roster-by-beat analyzer + the synth-fork director skip both
LANDED + IN-GAME PROVEN** (offline beat→cast table via a symbolic Main_Init walk; and a non-`--verbatim` fork now
DROPS cutscene warp-directors — proven on the Dali shop: fixed fork = 1 shopkeeper, director-carried control = 2);
and a fork's auto-spawn now stays in the **main walkmesh region** (not a walled-off behind-counter pocket — the
Dali spawn moved out of the 7-tri pocket into the 21-tri customer area). ★ **#13 TAIL NOW CLOSED** (all in-game
proven): (c.2) the synth fork dedups duplicate-arg `InitObject` sites so a self-positioning NPC no longer stacks
into a duplicate pair; (#9) the synth default spawn now lands on the donor's **real main arrival** (where the
engine drops you walking in — Dali centroid `(83,209)` → real entrance `(439,-122)`), and `fork-report`'s
**Arrival** line flags per-DOOR fidelity, steering it to `--verbatim` (a synth fork can't reconstruct the
per-door table — its gateways are retargeted). → [[project-ff9-fork-fidelity-worklist]].

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
- **F6 debug menu** — the dev-engine in-game tool (Warp/Move/Cheats/Flags/Time).
