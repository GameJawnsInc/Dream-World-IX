# CLAUDE.md — FF9 Custom-Field Toolkit (`ff9mapkit`, Memoria Engine)

> Read fully at session start, then update **§5 Current state** + the **§10 timeline**
> as work lands. This file was consolidated on **2026-06-08** from ~50 verbose
> session logs into a lean "what's true now." **The full narrative lives in git**
> (`git log` / `git show`) and in the project-memory files (§9) — that's the archive;
> this file is the working brief. Don't re-grow it into a blow-by-blow journal:
> log durable *facts* here and in memory, leave the story to the commits.

---

## 1. What this project is now

It began as "add one playable custom room to FF9 (Steam, Memoria engine)." **That is
long done** — multiple fully-playable minted fields exist, verified in real gameplay.

It is now **`ff9mapkit`**: a Python toolkit + Blender add-on that compiles a declarative
**`field.toml`** into a complete drop-in Memoria mod — a brand-new FF9 field with camera,
walkmesh, painted art, NPCs, dialogue, gateways, encounters, events, story branching,
cutscenes, and ladders — and can **import/fork any of FF9's ~674 real fields**. It runs on
**stock Memoria** (the shipped mod is engine-independent; a local *dev* engine adds only an
F6 debug menu). Likely the first practical reference for FF9 custom-field authoring.

Current work is **feature expansion / research / polish + release prep**, not "ship a room."
The toolkit lives at `ff9mapkit/` (package `ff9mapkit/ff9mapkit/`, Blender add-on
`ff9mapkit/blender/`). The dev-loop tools live at repo-root `tools/`.

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
- **Commit only when the user asks. NOTHING PUBLIC** — no `git push`/remote, no PRs, no PyPI,
  no forum/Discord posts. Local commits only. (Standing instruction, repeated across sessions.)

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
| GUI apps | in **`apps/`**: `ff9_studio.pyw` = the **launcher** (front door to all GUIs) · `ff9_build_gui.pyw` (build+deploy) · `ff9_editor.pyw` (logic editor) · `ff9_infohub.pyw` (Info Hub viewer) |
| Reference field scripts | `reference/test2/` (gitignored, 817 HW field-script exports) + `reference/field-manifest.tsv` (HW-index→field-id→name; index ≠ field id) |
| FF9 field assets | `<game>\StreamingAssets\p0data*.bin` (UnityRaw 5.2.3 bundles; UnityPy reads them — `py -m pip install UnityPy`) |

> **Git layout:** worktrees share one install but each deploys into its OWN Memoria mod folder, so
> they never share a `DictionaryPatch.txt` and can't clobber each other. (The old single-`FF9CustomMap`
> + `--id` scheme broke: `deploy_field.py`'s revert/revert-prior does a WHOLESALE DictionaryPatch
> restore from a pre-deploy snapshot, so a deploy on one worktree silently wiped a sibling's
> `FieldScene` line → black-screen warp to an unregistered id.) Each worktree pins its target in a
> gitignored **`.ff9deploy.toml`** (`mod_folder` + `id`; override via `--mod-folder`/`$FF9_MOD_FOLDER`);
> `Memoria.ini [Mod] FolderNames` stacks the folders and each folder's own DictionaryPatch/BattlePatch
> is read at launch (`DataPatchers.Initialize`). Per-worktree slots live in the scratch band: `C:\gd\FFIX`
> master → `FF9CustomMap`/**30000** · `C:\gd\FFIX-battle-backgrounds` → `FF9CustomMap-bb`/**30001** ·
> `C:\gd\FFIX-infohub-catalog` → `FF9CustomMap-ih`/**30002** (existing worktrees migrate by editing their
> gitignored `.ff9deploy.toml` id + relaunching once to register it). **Distinct ids still required**
> (EventDB/SceneData are GLOBAL, merged from every folder at launch → same id across folders collides).
> New worktree: drop a `.ff9deploy.toml` (id 30000-32767), add its folder to `Memoria.ini FolderNames`,
> relaunch. Reach any slot via F6 → Warp.
> **Field-id bands** (`pack.py`; engine cap: the live `FF9StateSystem.Common.FF9.fldMapNo` is **Int16 → max
> 32767**, so a higher DictionaryPatch id *registers* but is unreachable): **10-3100** real fields (locked) ·
> **4000-9899** shipped custom content in 100-id blocks (`pack.suggest_base`) · **30000-32767** ephemeral
> dev/test scratch slots (the per-worktree deploy targets). Wiring `suggest_base` into `ff9mapkit new` /
> the Campaign Editor is a future task.
> **Merge discipline (keeps CLAUDE.md current, cheaply):** do all CLAUDE.md edits on the *feature*
> branch and let `master` only ever **fast-forward** — it stays a clean receiver, so the FF is
> conflict-free and master's CLAUDE.md never goes stale. FF from this worktree without checking out
> master: `git -C C:\gd\FFIX merge --ff-only infohub-catalog` (keep the master worktree clean first —
> an uncommitted file there blocks the FF; stash it, FF, pop).
> **Two branches feeding master concurrently:** the FF-only model assumes ONE feeder at a time. If the
> *other* branch FFs master while you have un-merged commits, your branch diverges and a plain FF becomes
> impossible — that's expected, NOT an emergency (diverged branches sit fine until the next FF). Fix:
> `git rebase master` (replays your commits onto it; resolve same-file doc conflicts **keep-both**), then
> the `--ff-only` merge above. Deterministic — whoever merges **second** rebases; only files BOTH branches
> edited (e.g. CLAUDE.md §10) conflict, so it's usually one paragraph + a clean replay.

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
  interior — door round-trip, a talking Vivi NPC, an encounter, and an **Alexandria (field 100)
  door**. The clean packaged copy lives in **`release/FF9CustomMap/`** (the known-good source).
- **The live dev `FF9CustomMap` is a churned scratchpad** — test deploys overwrite/remove scene
  folders, so the hut's `FBG_N11_HUT_*` scenes are frequently absent (they are right now;
  FieldMaps holds only the test-slot scenes). **To actually play the hut, redeploy it from
  `release/`.** Registered fields: 4000 HUT_EXT, 4002 HUT_INT, **4003 = the shared test slot**
  (`deploy_field.py`, currently a CPMP ladder fork).
- **Debug New-Game warp** jumps straight to **field 4003** (entrance 11) — NOT through
  Alexandria (the route-through-100 hop was abandoned because field 100 crashes). Field **100
  (Alexandria)** holds the door wiring + known debug-hack breakage (dead `Field(4004)` + a
  spawn inside a gateway zone) — off the New-Game path now; a real story entrance would rebuild it.
- **Versions:** kit `0.9.9`, Blender add-on `0.9.6`. **Provenance gate is CLEARED** — the
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
  (navigable, vertical/slant/bent shapes, floor/gateway/worldmap tops, re-entry) · **props**
  (static set-dressing — chests/tents/save-points/barrels/ladders/signs — via the real FF9 recipe:
  `SetModel` + a static pose + `EnableHeadFocus(0)`; `[[prop]] prop = "chest"` or `model` + `pose`).
- **Import/fork:** `ff9mapkit import <field>` (BG-borrow or `--editable` custom-scene) +
  `list-fields` — fork any of **674** real fields (camera + walkmesh + gateways/BGM/encounters
  extracted offline from p0data). Blender "Import FF9 Field" gives a visual fork→author loop.
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

**Process**
- **Hades Workshop is fully out of the loop** — its custom-field atlas clone has a systemic UV
  bug, and its export CORRUPTS entry-adds. Author `.eb` in Python (verify with `eb_disasm` /
  the kit before deploy). → `project-ff9-mint-gotchas`, `project-ff9-eb-script-tooling`.
- **Never edit a bundled example in place** — the form editor's Save will rewrite the
  byte-exact golden oracle. Author on a copy / `ff9mapkit new` / a Blender export.
- Grep alone can't prove a field is unused — FF9 cutscenes fire from C# tables
  (`NarrowMapList.cs`), not just field scripts. Trust the user's game knowledge over grep.
  → `feedback_trust_user_game_knowledge`, `project_ff9_has_no_unused_fields`.

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
- `project-ff9-bg-borrow-solution`, `project-ff9-mint-proven`, `project-ff9-mint-gotchas` — minting + BG-borrow + HW dead-ends.
- `feedback_trust_user_game_knowledge`, `project_ff9_has_no_unused_fields`,
  `project_ff9_field_warp_pattern`, `reference_ff9_modding_community` — process + community.

---

## 10. Milestone timeline (the trail, compressed — full story in git)

- **S0–1** — Recon; build/test loop proven; field 1357 (Hangar) is a complete playable map.
- **S2–4** — MINT proven (custom field ids work); HW atlas clone is broken → **BG-borrow** the
  solution (real art via DictionaryPatch, area ≥10).
- **S5–8** — Novel painted BGs: borrowed-camera walkmesh, human-painted art, walkmesh↔floor
  alignment + foreground occlusion all working in-game.
- **S9** — `.eb` content authored directly in **Python** (HW dropped): NPCs, talk triggers,
  custom dialogue text (mod `.mes` at a high TXID).
- **S10** — **Camera math cracked**: author/decompose/synthesize ANY angle; exact scale-1
  canvas map; novel-angle room calibrated + walkable.
- **S11** — Two connected painted rooms (gateways) + first encounter with the after-battle fix.
- **S12** — Local Memoria engine build; fade/BGM/encounter/cold-start fixes; custom room wired
  into **Alexandria** (real-world round trip).
- **S13** — **`ff9mapkit` built** (field.toml → mod) + the **Blender add-on**; the back-edge
  anomaly cracked (scale-1 map + collision radius).
- **S14** — Blender visual authoring (camera/walkmesh/markers); bounds tests (concave, yaw);
  scene/field split begins.
- **S15** — **Scrolling fields** (BGCACTIVE) end-to-end + in the kit + Blender.
- **S16** — **Import any real field** from p0data (offline extraction); the universal walkmesh
  frame; simple + multi-floor forks; Blender "Import FF9 Field".
- **S17** — Faithful `.bgi` exporter; editable-art (occlusion-preserving) forks; multi-floor
  seam reconcile; the offline **build-time validation suite**.
- **S18** — Multi-camera (N cams, after-battle restore); the conditional-region primitive →
  **events / story branching / cutscenes** (narration + actor); the flag-persistence fix;
  character-offset measured 0; honest walkmesh.
- **S19** — Authorship suite: **form editor** + scene/field split + linter; **provenance gate
  cleared** (zero SE bytes); stock engine + F6; instant New-Game warp; release-prep docs.
- **S20–21** — Dialogue wrap + cutscene auto-pathing; modern editor UI; **dialogue choices**
  (default/cancel/hide, flag-gated); chest/reward conventions matched to real FF9.
- **S22** — **Ladder import** (shapes, top-actions, re-entry) + the warp-plumbing saga.
- **S23** — The **F6 debug menu** (supersedes old hotkeys); the **Info Hub catalogs**
  (models/anims/scenes/items) + `[[npc]] model` by name; ladder catalogue 100%.
- **InfoHub archetype pillar** (in-game verified) — `catalog.npc_anims`: place **any** of the 154
  field models as a working NPC by name, animations auto-resolved via the model→animation join
  (`[[npc]] model = "GEO_NPC_F0_BMG"`, no `anims` needed); `ff9mapkit models <name>` shows the
  NPC-ready slots. **Named archetypes** layer friendly one-word NPC types on top
  (`[[npc]] archetype = "garnet"` / `"black_mage"` / `"guard"` / `"innkeeper"`; `ff9mapkit archetypes`
  lists them). Builds on the read-only catalogs to make the Info Hub a real authoring pillar.
  **The archetype set is COMPLETE** (122 names / 96 models): every `GEO_NPC` field model with a full
  anim set **plus the named story cast** (`GEO_SUB` — Beatrix / Kuja / Garland / the Tantalus crew /
  the genomes / Quan / Quale / Lani / …), all identified IN-GAME via the gallery loop
  (`tools/build_archetype_gallery.py --group NPC|SUB` + `tools/model_field_usage.py`: place unknown
  models in field 4003, the human warps to each one's real fields via F6 and reports the role).
  **Animations verified in-game** via `tools/build_anim_check.py` (forces a model's idle slot to its
  walk/run clip so a whole row animates in place — walk + run clean across every rig). Full reference
  (roles, real-field locations, JP name origins): **`ff9mapkit/docs/ARCHETYPES.md`** (regenerate with
  `tools/gen_archetype_reference.py`). Guards (pytest): completeness (no unnamed `GEO_NPC`), real-idle
  (no "moonwalk"), curation (every archetype fully animated). Held out: `black_waltz_2` + Trance Kuja
  (special boss models, no standard idle/walk — place by raw model id).
- **Prop pillar** (in-game verified) — the **`[[prop]]`** section places static set-dressing (chests,
  tents, save-points, barrels, ladders, signs) by the real FF9 recipe: `SetModel` + a fixed-pose
  `SetStandAnimation` + **`EnableHeadFocus(0)`** (the engine switch that kills an NPC's turn-to-face),
  grounded byte-for-byte in shipping fields (save-moogle field 300, chest field 115), NOT emulated.
  Two engine-grounded gotchas: **`SetObjectFlags` bit 1 = "show model"** — the shipping props'
  `flags(14)` omits it → the model VANISHES, so we only disable head-focus (don't blanket-set flags);
  and a prop's true pose is a raw `SetStandAnimation` clip the model→anim name-join often lacks (the
  save book rests at 1872 = 'b'+1) → `tools/extract_prop_poses.py` harvests the canonical pose per
  model. **The GEO_ACC set-dressing catalogue is COMPLETE** — every field-placed ACC prop is a named
  archetype (**117 names / 83 models**, `prop_archetypes.py`, pose baked in), each ID'd in-game via the
  prop gallery (`tools/build_prop_gallery.py --arena`, common-first, 6/batch on the no-relaunch arena):
  basics (`chest`/`tent`/`save_book`/`ladder`/`vat`/`aircab`) plus vehicles (`gargant`/`cab_carriage`/
  `gondola`/`parade_float`/`luxury_cab`), statues + ritual (`neptune_statue`/`goddess_statue`/
  `extraction_ring`/`altar`/`wind_mirror`), machinery (`gear_wall`/`hatchery`/`weight_lift`/`pull_chain`),
  weapons (`dagger`/`spear`), and the Madain-Sari kitchen set (`fish`/`pot`/`fishing_rod`) —
  `[[prop]] prop = "chest"` or `model` + `pose`. Aliases throughout; two props (`goddess_statue` GNT,
  `collapsing_floor` KOS) have zeroed/offset origins → they render as a tiny dot alone (view them in-scene).
  Deferred (spawned task): a `[field] location_name` option to hide the borrowed-BG location-name banner.
  **Composite set pieces (in-game verified):** `[[prop]] prop = "<name>"` expands (build.py) to several parts,
  each at the prop's (x,z) plus an optional per-part `(dx,dz)` offset (`prop_archetypes.PROP_COMPOSITES`; tools:
  `find_composite_props.py` / `dump_field_objects.py`). Two ship: **`save_point`** (moogle ON book, co-located;
  the feather/letter are save-animation-only, omitted) and **`scale_set`** (the Desert Palace scale `TNB` LOADED
  — clay/stone/iron on the pans + the wood weight offset beside it). **Pose gotcha:** a set piece often needs a
  field-SPECIFIC pose, not the archetype's cross-field-canonical one — the weights canonically pose OFF-scale
  (hidden inside the body when co-located); field 2203's on-pan poses (6263/6267/6271, scale 2561) render the rack.
  **Held items (`AttachObject` 0x4C):** **`[[npc]] holds = "save_the_queen"`** puts a prop in an NPC's
  hand — attaches at the right hand-bone AND poses BOTH the prop and the holder, **auto-resolved for
  this holder's model** from a catalog of every shipping `AttachObject` (`tools/extract_attach_poses.py`
  → `_held_poses.py`: `(carrier, prop) → (bone, prop_pose, holder_pose)`). `[[prop]] attach_to = "<npc>"`
  is the manual form (uids ARE entry slots, so the kit emits the exact shipping bytes). In-game-verified
  (Beatrix + Save the Queen; a dwarf + cup). **The field-held-prop catalogue is COMPLETE** — every prop a
  character holds in a shipping field is a named archetype (sword/cup/letter/glass/ticket/hand_bell/ +
  axe/wreath/sack/log/vial/dagger_doll/brahne_doll/…), each ID'd in-game via `tools/build_held_gallery.py`
  (places each carrier holding its prop; **`--spotlight <tok>`** = one carrier slowly turning, for an
  unclear item — note: a multi-step turn cutscene only completes its FIRST turn on a player-cloned NPC).
  **GEO_WEP battle weapons do NOT apply** — they're the `B1` battle variant (no `F0`), absent from field
  scripts, so they don't render outside combat; field-held weapons are always `GEO_ACC` props.
- **Engine gotcha — `IsActuallyTalkable` reads `tag3[ip+7]`/`[ip+8]`** (the per-frame talk-icon poll), so
  an object's tag-3 (talk) func MUST be ≥ 9 bytes or it indexes past the entry buffer → an
  `IndexOutOfRangeException` every frame the player is near it. The kit's `_SpeakBTN` was 7 bytes — a
  LATENT bug on every NPC since the first one (logged, non-fatal; found by watching `Memoria.log`). Fix:
  pad short talk funcs to ≥ 9 (dead bytes after RETURN); non-interactive **props are `bare`** (Init-only,
  no tag-3 at all — matches shipping set-dressing, dodges the poll). → `content/npc.py` `bare=`/padding.
- **Battle-background pillar — feasibility + tier (a) proven** (2026-06-09) — battle maps are a SEPARATE
  pillar from fields: real textured **3D Unity meshes** (FBX, child groups `Group_0/2/4/8` = additive/
  ground/minus/sky) + a moving perspective camera computed in a closed native DLL. 177 of them
  (`BBG_B001..177`) in `p0data2.bin`. **Tier (a) — texture reskin of an existing map — is in-game proven**
  on stock Memoria (no DLL rebuild): drop PNGs named by the bundle `Texture2D.m_Name` at
  `…/StreamingAssets/Assets/Resources/BattleMap/BattleModel/battleMap_all/BBG_B###/` in a mod folder; UVs
  wrap the geometry correctly (verified with a per-texture UV checker). Scene wiring mirrors `FieldScene`
  (a `BattleScene` DictionaryPatch line). **Tier (b) — CUSTOM GEOMETRY — is also in-game proven**: Memoria
  loads a loose **FBX** from the mod folder instead of the bundle (`ModelImporter`/`FbxIO`), so a custom 3D
  battle map ships with no engine rebuild — verified with a synthetic quad AND a byte-faithful BBG_B013
  round-trip (one FBX Geometry per submesh named `Geometry::Group_N`, verts/uvs/normals verbatim, Model
  typed "Mesh", per-group PSX shader set in-FBX). **Now a first-class ff9mapkit pillar** (kit 0.9.6):
  `ff9mapkit/ff9mapkit/battle/` + CLI `battle-import`/`battle-build`/`battle-list` + `tools/deploy_battle.py`
  + a `battle.toml` (override an existing slot / `repoint_scene` / experimental `scene_id` mint). The
  earlier `tools/*bbg*` scripts were the proofs; the package supersedes them.
  **Tier (c) — NEW SCENE mint PROVEN in-game (2026-06-09):** a net-new `BattleScene <id>` (forked donor
  EF_R007 / scene 67 → id 5500 on BBG_B013 — raw16 + raw17 + eb + **mes** verbatim) loads + is fightable on
  stock Memoria (2 Goblins, correct rewards/random drops, no softlock). **The camera was NOT the blocker** —
  the donor's raw17 + 3 hardcoded static default poses (`BattleMapCameraController`, picked by the raw16
  pattern's `Camera` byte) render with zero camera authoring (the managed `SFXDataCamera` path is a TODO
  no-op). **Real gotcha: the per-lang battle `.mes` is LOAD-BEARING** — a missing `<id>.mes` → `GetBattleText`
  null → NRE in `DataPatchers.ApplyBattlePatch` → battle loads with map+camera but NO enemies/party (base
  battle text is in `x64/FF9_Data/resources.assets` as `<sceneId>.mes` TextAssets, one per lang; numeric
  `.mes` = battle, field text is named by script). Trigger = a field `SetRandomBattles(…, <id>)` encounter
  (the scene arg IS the battle id). Probe `tools/probe_tierc_scene.py` (reversible `_tierc_revert.py`).
  **C2 — WHOLLY ORIGINAL battle PROVEN in-game (2026-06-09):** a net-new `BBG_B200` (>177; our own FBX +
  blue-tinted textures + a static `INB_B200`) under minted scene 5501 — fought twice, rendered blue (= our
  files loaded, no fallback to real B013), no errors. A new bbg NUMBER is safe with a static `.inb`
  (`nf_BbgNumber` is only `== <id>` compared, never an array index; obj/uv-anim gated on `objanim>0`).
  **C4 — the full mint is WIRED INTO ff9mapkit (kit 0.9.7), in-game proven via the kit's OWN pipeline**
  (a kit-deployed `BBG_B201`/scene 5502 was fightable, survived death→menu→new-game→re-warp→win): `battle-import
  --fork-scene <DONOR> --ship-as BBG_B<N>` forks geometry + scene assets (raw16/raw17/eb/mes, gitignored
  SE-derived), `battle-build` copies them + authors a static INB + emits the `BattleScene` line,
  `deploy_battle.py --trigger-field N` installs reversibly + repoints a field encounter, `battle-list
  --scenes` lists donors. Kit-emitted raw16/raw17/eb/mes are byte-identical to the C2 probe (offline-verified);
  451 tests pass; the throwaway probes were removed (kit supersedes them). **ALL battle tiers done** (a/b/c
  + productized). **TUNE THE FIGHT (kit 0.9.8, in-game proven):** a `[scene]` section in battle.toml
  overrides a minted battle's enemy **positions** (`pos`/`y`/`rot`), **stats** (hp/mp/gil/exp/level/
  speed/strength/magic/spirit), **rewards** (`drop`/`steal`, items by name), and **camera** pose — the kit
  surgically patches the forked `raw16` (only edited bytes change) keeping enemy TYPES so raw17 stays valid
  (`battle/scene_data.py`; confirmed in-game: Goblin/Fang HP 33→1 one-shot + 9999 gil/999 exp/Phoenix Down).
  Also **spawn composition** (kit 0.9.8, in-game proven) — `monster_count` (1–4) + per-slot `type` (existing
  types only) RECOMPOSE *and GROW* the encounter. The kit writes the composition to every pattern AND
  **re-authors the battle eb's `Main_Init`** to bind one enemy-AI object per spawned slot
  (`InitObject(1+type, 0x80+slot)`, reusing the donor's per-type AI entries — entry `1+T` = type T's AI;
  `battle/event_data.py` + the new `eb/edit.replace_function_body`). This BROKE THE DONOR-COUNT LIMIT: a
  mint can now spawn more enemies than the donor natively did (1-enemy EF_R007 → four Goblins, no
  player-model twitch — every slot has a real AI object, so no death misroutes into the player via
  `EventEngine.RequestAction`). Root-caused via an ultracode workflow; the old `monster_count` cap is gone
  (errors only if a needed per-type AI entry is absent).
  **Custom CAMERA — feasibility PROVEN in-game (2026-06-09, ultracode scout + byte-edit probe):** a bespoke
  moving battle camera IS authorable by writing raw17, no DLL rebuild. The closed `FF9SpecialEffectPlugin.dll`
  is a data CONSUMER — `SFX.StartPlungeCamera` pins the raw17 and passes `(ptr,len,camOffset)` to the native
  side, which parses the camera keyframes itself; the managed `SFXDataCamera.Load/UpdateBSC` (which the kit's
  Python port mirrors) have zero call sites = pure spec. Opening shot = `cameraList[CameraNo]`, CameraNo = the
  raw16 pattern `Camera` byte (kit already writes it). Proven by rotating EF_R007's opening cam[0] 180° via an
  IN-PLACE orientation byte-edit (no offset repack) → the swoop visibly flipped. **Tier (i) SHIPPED (kit
  0.9.8, in-game confirmed):** `[scene] camera_yaw / camera_pitch / camera_zoom` offset the opening camera's
  keyframes in place (`battle/camera_data.py`); yaw + zoom predictable, **pitch finicky** (offset onto the
  donor's base angle — a moderate +value dips the camera below the floor, which is see-through from under).
  **Tier (ii) SHIPPED (in-game proven 2026-06-10):** full from-scratch opening-camera SWEEP authoring via
  `[[scene.camera_keyframes]]` (`battle/camera_codec.py` — the offset-table repack mirroring `UpdateBSC`).
  Authored in FF9's REAL opening grammar (surveyed 6 donors w/ `tools/dump_battle_camera.py`): an instant
  establish pose → 2-4 chained `CAMMOVE` segments → the donor's `SAVE_FOR_FIXED|SetCameraPhase(1)` HANDOFF
  (kept verbatim — without it the battle hangs in the intro). **The origin matters as much as the motion:**
  battle centre = world origin, default cams ~4500-5900w out → 1 distance unit ≈ ~450-500 world (not the
  comment's 63), and camera distance is measured FROM THE TARGET — so keyframes ADJUST the donor's PROVEN
  settle pose (yaw/pitch/roll OFFSETS + `zoom` multiplier) rather than absolute world poses: offset 0/zoom 1
  == the game's normal framing (can't mis-origin/super-zoom), and the final keyframe becomes the battle's
  normal camera (SAVE_FOR_FIXED snapshots where the sweep ends). **All battle frontiers cracked** (tier i
  in-place + tier ii sweep). Full recipe + the origin/scale gotchas: memory `project-ff9-battle-backgrounds`.
  Dev/test moved to the scratch id band (§3): battle-bg = field 30001, battle scenes 30010-30019.
- **Creature pillar + debug arena** (in-game verified) — place a battle **monster** as a field object by
  name: **`[[npc]] archetype = "zaghnol"`** / `"lich"` / `"griffin"`. The **`CREATURES`** catalog
  (`archetypes.py`, merged into `names()`/`resolve()`) holds field-RENDERABLE `GEO_MON` models (verified
  in-game — they render + animate as field objects; most also appear in shipping field scripts, a few are
  battle bosses the kit can still place); named in-game via the gallery
  loop (`tools/build_archetype_gallery.py --arena --group MON`, 4/batch — they're huge). **COMPLETE: all 21
  field-creature models named** (lich/ramuh/soulcage/ralvuimago/silver_dragon/zaghnol/red_dragon/antlion/
  griffin/catoblepas/mistodon/behemoth/mu/…), token decodes + JP origins in comments; battle-only models
  that DON'T render (e.g. `DDD`) go in the gallery's `SKIP` set. The **arena** (`tools/build_debug_arena.py`) is a big flat **scrolling
  checkerboard** debug stage for staging huge models without obstruction — pure-stdlib perspective
  checkerboard (`scene/placeholder.write_placeholders`, auto-aligned via `cam.to_canvas`) + a flat walkmesh
  + a scrolling camera, with **pitch-compensated** cells (world cells made ~1/sin(pitch) DEEPER so they read
  square on the tilted floor); the gallery `--arena` flag stages a batch on it, ~1 screen per model.
- **Info Hub spine** (`ff9mapkit/infohub.py`, + `test_infohub.py`) — the UI-agnostic discovery CORE for the
  planned user-facing viewer: `browse(query, kinds)` (cross-kind search over every catalog + the archetype/
  prop/creature/composite tables -- matched on names + comment DESCRIPTIONS + friendly aliases, so 'box' -> shelf
  and 'zidane' -> the ZDN model), `detail(entry, usage_fn=None)` (model + full anims + the auto-resolved 5
  movement slots + composite parts + aliases + the field.toml snippet; `usage_fn` = an injected hook for
  real-FF9 field-locations, so the spine stays install-free), `snippet(entry)` (the `[[npc]]`/`[[prop]]`/
  `give_item`/`[encounter]` block), `find(name, kind)`. All plain dataclasses (Tkinter/web/CLI/JSON). Built
  spine-first ON PURPOSE so a standalone viewer NOW + the **Campaign Editor** suite LATER (+ Blender if ever)
  reuse the same core with no rework. **Frontend:** `apps/ff9_infohub.pyw` (opened from the `apps/ff9_studio.pyw`
  launcher) — a standalone Tkinter window
  (live search/filter, detail pane, copy-snippet; `--smoke` self-test), the first view on the spine
  (user-verified), now with a **Preview in-game** button -- `spine.preview_field_toml(selection)` builds a
  gallery on the **`ff9mapkit/scene/arena.py`** stage (the arena builder, lifted out of `build_debug_arena.py`
  so the package can stage a preview) and deploys it to the test slot -> F6 reloads to see it live, plus a
  **Where in FF9?** button (`detail(usage_fn=...)` via `tools/model_field_usage`, cached) listing the real
  fields that place the selected model -- on-demand so browsing stays install-free. **The Info Hub pillar is
  feature-complete** (spine + viewer: search by name/description, detail, copy-snippet, preview, where-in-FF9).
- **Campaign Editor — Phases 1-3 (the IDE shell):** **Phase 1 (catalog picker, GUI-verified)** -- the Logic
  Editor's name fields gain a **Browse...** button opening a modal Info Hub picker (`ff9mapkit/editor/picker.py`,
  over the spine) that writes the chosen name back -- no more blind typing (a `forms.Field.catalog` hint
  drives it; on NPC **preset** + choice **give_item**). **Phases 2-3 (the IDE window, offline-verified)** --
  the editor/build/infohub apps were refactored to mount on a parent frame (not own `tk.Tk()`; standalone
  launchers preserved), and **`apps/campaign_editor.pyw`** tabs all three over one root (Logic Editor / Info
  Hub / Build & Deploy); the `ff9_studio` launcher offers it as the all-in-one. **Phase 4** (the multi-field
  campaign/project model: linked fields + a gateway graph) remains. 487 tests pass; the spine↔editor reuse
  is the payoff of building spine-first.

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
