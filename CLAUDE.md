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
| GUI apps | in **`apps/`**: `ff9_studio.pyw` = the **launcher** (front door to all GUIs) · `ff9_import.pyw` (**FFIX Import** — preview fork fidelity (fork-report) / fork a real field with fidelity options as checkboxes / read dialogue / inspect a save; shells out to `py -m ff9mapkit`) · `ff9_build_gui.pyw` (build+deploy — auto-detects **field / campaign / battle map**) · `ff9_editor.pyw` (logic editor) · `ff9_dialogue.pyw` (dialogue editor) · `ff9_infohub.pyw` (Info Hub viewer) · `ff9_storystate.pyw` (**Story State** — inspect / diff / EDIT a save's `gEventGlobal` story state; backup-guarded; calls `save`/`flags` directly) · `campaign_editor.pyw` (the all-in-one IDE; hosts the others as tabs incl. **Import** + **Story State**) |
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
- **Canonical demo content:** two painted "Vivi" hut rooms — **4000** exterior + **4002**
  interior — door round-trip, a talking Vivi NPC, and an encounter. The clean packaged copy lives in
  **`release/FF9CustomMap/`** (the known-good source), now **100% kit-authored** — the SE-derived
  Alexandria field-100 door `.eb` was removed in the provenance cleanup (the field-100 path already
  crashed / was off the New-Game route), so the demo is the two painted hut rooms.
- **The live dev `FF9CustomMap` is a churned scratchpad** — test deploys overwrite/remove scene
  folders, so the hut's `FBG_N11_HUT_*` scenes are frequently absent (they are right now;
  FieldMaps holds only the test-slot scenes). **To actually play the hut, redeploy it from
  `release/`.** Registered fields: 4000 HUT_EXT, 4002 HUT_INT, **4003 = the shared test slot**
  (`deploy_field.py`, currently a CPMP ladder fork).
- **New-Game → field 4003 is a stock mod field-70 override, NOT a DLL edit** — the only custom DLL is the F6
  menu. The mechanism, the seamless-entry lever, and the starting-state capstone → [[project-ff9-new-game-entry]].
- **Versions:** kit `0.9.62`, Blender add-on `0.9.7`. **Provenance gate is CLEARED** — the
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
  gives a visual fork→author loop.
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
- World Hub — a playable journey selector (choice `warp` action + `[player] model=` moogle PC); MVP scaffold IN-GAME PROVEN (talk→pick→warp) → [[project-ff9-world-hub]]

**Latest:** kit 0.9.64, 1224 tests. `deploy_campaign` productionized (auto-promote start-state CSVs to the highest
folder + ABORT on a cross-folder EVT/FBG name collision; wires New Game via the field-70 retarget, not the broken
field-100 hop) — ★ **IN-GAME PROVEN**: `--apply` → relaunch → New Game boots straight into the Dali chain. World-Hub scaffold IN-GAME PROVEN (the select→warp loop).
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
(no fpos fixup; applied per-lang to the forked eb). ★ Phases 2/3/4/5/5b/6a/6b each validated by a multi-lens adversarial review (Phase 2: 562-scene sweep; Phase 3: caught
a boot-crash range bug + the cp1252 encoding; Phase 4: caught a `StatusSetId` over-range KeyNotFound crash, a
malformed-toml traceback, + a silent dead-`Battle:` selector; Phase 5: caught a fixture provenance leak + a
missing whole-file shadow-guard; 5b: an unresolvable display name; 6a: a truncated-eb crash; 6b: a 3-byte-immediate
KeyError + the B_CONST4 26-bit mask) → [[project-ff9-battle-tuning]],
`docs/BATTLE_DESIGN.md`. Next: Phase 6c (new branches + expr assembler + battle linter).
Frontier: #13 (story-event director/roster on rotating-cast fields) — ★ **core PROVEN** (a `--verbatim` fork +
`[startup]` shows a beat-correct rotating roster: forking Dali Weapon Shop 354 at SC 2600 vs 11090, the shopkeeper
changed + an NPC appeared, in-game 2026-06-12); the **roster-by-beat analyzer + the synth-fork director skip both
LANDED** (offline beat→cast table via a symbolic Main_Init walk; and a non-`--verbatim` fork now DROPS cutscene
warp-directors so it's a clean diorama, not a stacked-cutscene mess). Remaining tail: the multi-instance/per-door
sub-bugs → [[project-ff9-fork-fidelity-worklist]].

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
