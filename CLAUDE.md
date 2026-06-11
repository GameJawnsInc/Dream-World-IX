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
cutscenes, ladders, jumps, props, and save points — and can **import/fork any of FF9's
~674 real fields**, carrying their NPCs/props/lighting/dialogue faithfully. It has grown
several more pillars: **custom 3D battle backgrounds**, **multi-field campaigns** (with a
Campaign-Editor IDE), and **story-flag tooling** (read / name / edit a save's `gEventGlobal`
state). It runs on **stock Memoria** (the shipped mod is engine-independent; a local *dev*
engine adds only an F6 debug menu). Likely the first practical reference for FF9 custom-field
authoring — and broad enough now that the working brief below matters more than any one feature.

**The objective (north star) is fork FIDELITY, NOT a release:** keep refining borrowed/forked fields
until the kit can recreate the *functioning game itself* from them. The measure is "fork a real field →
does it play identically to the original?" Do **not** frame work as "near-release" / "release prep" — that
pressure is explicitly unwanted. Current state of that goal lives in **`ff9mapkit/docs/FORK_FIDELITY.md`**
(the honest gap map): the *physical* layer (scene/walkmesh/camera/mechanics/object carry) is largely
faithful and in-game proven; the *narrative-state* layer is the weak axis (a fork boots at scenario-zero —
no flag presets, one spawn, no C# `NarrowMapList` cutscene). The toolkit lives at `ff9mapkit/` (package
`ff9mapkit/ff9mapkit/`, Blender add-on `ff9mapkit/blender/`). The dev-loop tools live at repo-root `tools/`.

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
| GUI apps | in **`apps/`**: `ff9_studio.pyw` = the **launcher** (front door to all GUIs) · `ff9_import.pyw` (**FFIX Import** — preview fork fidelity (fork-report) / fork a real field with fidelity options as checkboxes / read dialogue / inspect a save; shells out to `py -m ff9mapkit`) · `ff9_build_gui.pyw` (build+deploy — auto-detects **field / campaign / battle map**) · `ff9_editor.pyw` (logic editor) · `ff9_dialogue.pyw` (dialogue editor) · `ff9_infohub.pyw` (Info Hub viewer) · `campaign_editor.pyw` (the all-in-one IDE; hosts the others as tabs incl. **Import**) |
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
  interior — door round-trip, a talking Vivi NPC, and an encounter. The clean packaged copy lives in
  **`release/FF9CustomMap/`** (the known-good source), now **100% kit-authored** — the SE-derived
  Alexandria field-100 door `.eb` was removed in the provenance cleanup (the field-100 path already
  crashed / was off the New-Game route), so the demo is the two painted hut rooms.
- **The live dev `FF9CustomMap` is a churned scratchpad** — test deploys overwrite/remove scene
  folders, so the hut's `FBG_N11_HUT_*` scenes are frequently absent (they are right now;
  FieldMaps holds only the test-slot scenes). **To actually play the hut, redeploy it from
  `release/`.** Registered fields: 4000 HUT_EXT, 4002 HUT_INT, **4003 = the shared test slot**
  (`deploy_field.py`, currently a CPMP ladder fork).
- **Debug New-Game warp** jumps straight to **field 4003** (entrance 11) — NOT through
  Alexandria (the route-through-100 hop was abandoned because field 100 crashes). Field **100
  (Alexandria)** holds the door wiring + known debug-hack breakage (dead `Field(4004)` + a
  spawn inside a gateway zone) — off the New-Game path now; a real story entrance would rebuild it.
- **Versions:** kit `0.9.13`, Blender add-on `0.9.7`. **Provenance gate is CLEARED** — the
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
- `project-ff9-object-carry` — faithful NPC/prop carry: verbatim `.eb`-entry graft + player-func graft +
  text carry + the v1.5 STARTSEQ-helper closure; the cross-ref remap + the engine facts (tag 2 = push, etc.).
- `project-ff9-savepoint` — the save point = `Menu(4,0)`; synthesize the region, don't graft the cluster.
- `project-ff9-story-flags` — the `gEventGlobal` heap map + the 5 verbs + the safe band (bit 8512) + the
  AES `SavedData_ww.dat` codec.
- `project-ff9-jump-navigation` — navigable jumps = ladder mechanism minus the climb loop; the entry-table fix.
- `project-ff9-battle-backgrounds` — custom 3D battle maps (all tiers) + the raw17 camera recipe.
- `project-ff9-import-fidelity` — `import --editable` = a scaffold (faithful carry now exists separately).
- `project-ff9-worldmap-feasibility` — field-chain campaign done; custom overworld = the hardest unstarted.
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
- **InfoHub authoring pillar** (in-game verified; docs `ARCHETYPES.md`) — place any field model/prop/creature
  by NAME, anims auto-resolved via the model→animation join: **NPC archetypes** (`[[npc]] archetype=`, 122 names
  incl. the named story cast), **props** (`[[prop]]` — the GEO_ACC set-dressing catalogue + composite set-pieces +
  `[[npc]] holds=` held items), **creatures** (21 field `GEO_MON`). The **Info Hub** spine + viewer
  (`infohub.py` / `apps/ff9_infohub.pyw`): cross-kind search (name/description/alias), detail, copy-snippet,
  in-game Preview, "Where in FF9?". A debug **arena** (scrolling checkerboard) stages huge models unobstructed.
- **Battle-background pillar** (ALL tiers in-game proven, no DLL rebuild; memory `project-ff9-battle-backgrounds`)
  — a battle map is a real 3D Unity mesh (FBX, groups `Group_0/2/4/8`) + a native-DLL camera, a SEPARATE pillar
  from fields. `ff9mapkit/battle/` + `battle.toml` + `battle-import`/`-build`/`-list` + `deploy_battle.py`:
  texture reskin · loose-FBX custom geometry · net-new `BattleScene` mint · wholly-original `BBG_B###` (>177).
  **Tune the fight** (`[scene]`: enemy positions/stats/rewards + spawn composition that GROWS the encounter by
  re-authoring the battle eb's Main_Init AI binding). **Custom camera** (in-place yaw/pitch/zoom + from-scratch
  opening sweep via `[[scene.camera_keyframes]]` — the closed `FF9SpecialEffectPlugin.dll` is a raw17 CONSUMER).
  A Blender Import/Export Battle Map loop (add-on 0.9.7) closes the visual-reshape gap.
- **Campaign pillar (Pillar D)** (in-game proven; docs `CAMPAIGN_IMPORT.md`) — fork a connected SLICE of the
  real game: **`import-chain <seed>`** BFS-walks the field graph + retargets in-chain gateways to the chain's own
  id band; **`build-all`** / **`lint-campaign`** / **`deploy_campaign.py`** install the whole set reversibly (one
  snapshot, wholesale replace — NOT deploy_field's per-id merge, which sibling-clobbers). The **Campaign Editor**
  (`apps/campaign_editor.pyw`) is a project IDE: member navigator + tree-graph + a visual node-link **Map** +
  authoring (`new-campaign` / `add-field` / rename / remove / set-entry); the Build & Deploy GUI auto-detects
  field/campaign/battle. New-Game-into-a-campaign with a full party is still unsolved (reach the chain via F6→Warp).
- **Navigable jumps** (Ice Cavern ledge/gap hops, in-game proven; memory `project-ff9-jump-navigation`) — a
  region `RunScriptSync`s the player's verbatim jump-arc; the ladder-vs-jump discriminator is the ladder flag
  `AddCharacterAttribute(4)`. `[[jump]]` + `scan_jumps`. Surfaced + fixed the latent **10-slot `.eb` entry-table
  ceiling** (`edit.grow_entry_table` + auto-grow; ≤10-entry fields stay byte-identical, hut golden preserved).
- **Seamless native forks** (in-game proven; memory `project-ff9-novel-bg-pipeline`) — `import <field> --native`
  ships the vanilla `.bgs` verbatim + a high-res atlas + a custom `.bgi`, NO `.bgx` → point-sampled per-tile
  depth = NO seams + correct occlusion (the `.bgx` bilinear path is what forces the seams; studied from Moguri).
  Forks **area<10** fields BG-borrow can't, sources the atlas from the active mod stack (Moguri's 64px), and
  carries the field's 3D-model LIGHTING (`MapConfigData` shipped verbatim as `EVT_<name>.bytes`). Wired into
  campaign import — area<10 members fork native, 0 logic-only stubs.
- **Story-flag pillar** (`story_flags` branch; memory `project-ff9-story-flags`) — mapped FF9's save-persistent
  `gEventGlobal` end to end (empirical census, 676/676 fields, 0 errors). All **5 verbs**: view + understand
  (`flags.py` registry — scenario→beat table, named bit regions, engine-grounded named word vars; live F6
  story-state readout), **name** (`[[flag]]` by name; safe custom band ≥ bit **8512** — fixes a latent collision
  with real FF9 chest flags 8376-8511), **create** (campaign-shared named flags), **recreate** (`save-edit` — the
  AES-256-CBC `SavedData_ww.dat` codec cracked + the authoritative Memoria plaintext extra-save), plus
  `flags-inspect` and **`flags-diff`** (the A→B story-state delta). Surfaced in the Info Hub (registry browse +
  save inspector).
- **Faithful object / NPC carry arc** (in-game proven; memory `project-ff9-object-carry`; docs OBJECT_CARRY /
  PLAYER_GRAFT / TEXT_CARRY / DIALOGUE) — a fork now CARRIES a real field's content instead of dropping it, each
  step building on the last: the **verbatim `.eb`-entry graft** (renders byte-identical — kills the lossy
  "Zidane in a barrel skin" player-clone) → **3D-model lighting** (MapConfigData) → the **player-function graft**
  (interactions FIRE — push a cask, Zidane turns) → **text carry** (carried NPCs speak the donor's real
  per-language lines) → **v1.5 STARTSEQ-helper closure** (carry the benign concurrent Seq an object launches; +
  the op78 expr-uid remap & multi-`DefinePlayerCharacter` classification fixes). The generalization of the ladder
  `sequences`/`add_function` graft to whole objects + their player funcs. Plus the **dialogue pillar** — the READ
  side of FF9 text (`dialogue.py`: `parse_mes` + `scan_dialogue` + JOIN-on-txid) and a dialogue editor/viewer +
  `import --dialogue` (editable `[[npc]]` stubs). ★ Process lesson: a research workflow overstepped and wrote
  production code (text carry) — scope research workflows so agents CANNOT.
- **Save-point synthesis** (in-game proven; memory `project-ff9-savepoint`) — the functional save is a SINGLE
  opcode `Menu(4, 0)` (`0x75`). SYNTHESIZE it (`[[savepoint]]` region + `Menu(4,0)` + a cosmetic moogle/barrel),
  don't graft the real moogle's un-graftable 7-entry cluster. ★ Resolves the long-open "save → Continue into a
  custom field (id ≥4000)" risk — it WORKS (save → quit → load → back in the custom field).
- **Provenance — the working tree ships ZERO Square-Enix game bytes** — ~217 SE-derived dev artifacts (sessions
  1-9 scratch, pre-dating the gate) `git rm`'d from HEAD; `release/FF9CustomMap/` is 100% kit-authored; old
  bytes remain only in local-only history (never pushed; a full scrub was offered + DECLINED). The toolkit OUTPUT
  was already clean — `extract-templates` regenerates base templates from the user's own install.
- **Unified offline lint** (`story_flags` branch) — `ff9mapkit lint` now runs the WHOLE offline suite in one pass
  (`build.lint_all` → a sectioned `LintReport`): schema + story/flag logic + **reserved flag-band check** +
  walkmesh geometry/placement/layer-art/cutscene-movement (was `walkmesh verify`-only) + camera pitch (was
  `guide`-only). The new `lint_flag_bands` extends the `[[flag]]` safe-band guard to literal `set_flag`/
  `requires_flag` indices — a write into a reserved `gEventGlobal` region (chest 8376-8511 / byte-23 handshake /
  worldmap unlocks / choice scratch) is flagged by name; the kit's 8000+ working band stays clean. Lint-only
  (build output byte- AND warning-identical). Mirrors §2 "I can't see the game" → offline checks are the leverage.
- **Dialogue-pillar polish** (`story_flags` branch) — `ff9mapkit dialogue` now also takes a **`campaign.toml`**
  (auto-detected) and reviews EVERY member field's authored dialogue in one pass (per-field + a roll-up), and
  `dialogue-import` now says WHY a real field's text is unresolved (UnityPy missing / no install / block didn't
  cover the txids → `--zone-id`). Spine: `dialogue.campaign_dialogue` + `flag_overflow` + `text_source_status`.
- **Story-flag registry depth — engine-reader pass v2** (`story_flags` branch; research `STORY_FLAGS.md` §8) —
  the original engine-reader scan grepped `gEventGlobal[<const>]` directly and missed the wrapper-accessor form
  (`ushort_gEventGlobal(92)`); re-scanning the full 45-site fixed-index set recovered the **worldmap Navi
  known-location words** `WorldmapKnownLocationsF0..F3` (bytes 92/94/96/98, UInt16, tier a, `keventNaviLocF0..F3`).
  Naming bytes 92–99 reclassifies that slice of the "write-only worldmap-unlock bits" as recognized word data
  (`flags-inspect` reports `WorldmapKnownLocationsF0 = N`). `NAMED_WORDS` kept tier-(a)-pure (tested).
- **FFIX Import GUI** (`story_flags` branch; `apps/ff9_import.pyw`) — surfaces the "import from game data" CLI
  commands so the `import` fidelity flags become **checkboxes** (Field tab: Native/BG-borrow/Editable art +
  carry NPCs/dialogue/stubs/save-point; Read & Inspect tab: `dialogue-import` / `flags-inspect` /
  `list-fields` / `extract-templates`). Shells out to `py -m ff9mapkit` from the kit root + streams output;
  standalone (launcher) + a Campaign-Editor **Import** tab. Pure `import_args()` is smoke-tested. Note: the
  field filter matches the **FBG technical name** (`grgr`, `alxt`, `tshp`), not friendly names — `Find…` lists
  them. Orthogonal to the graft lane (subprocess-based; only `apps/` + the launcher list).
- **Fork-fidelity audit + the `[startup]` preset block** (`story_flags` branch; `ff9mapkit/docs/FORK_FIDELITY.md`)
  — the **north star is fork FIDELITY, not a release** (§1): "fork a real field → does it play identically?" The
  audit (7-dimension workflow) found the *physical* layer faithful + in-game proven, the *narrative-state* layer
  the weak axis (a fork boots at scenario-zero, one spawn, no C# `NarrowMapList` cutscene). Highest-leverage
  orthogonal fix = **`[startup]`** (`content/startup.py`): preset the ScenarioCounter (`scenario = N|"area"`,
  via `set_var(GLOB_UINT16, 0, v)` — token 0xDC) + story bits (`flags = [{flag, value}]`) unconditionally,
  prepended to Main_Init (`edit.insert_in_function`, byte-safe; golden identical when absent). Lint flags
  reserved-region presets; real story bits below 8512 are allowed (the point). A fork can now boot in the right
  beat. Touches only `build.py` + `content/startup.py` — clear of the save-moogle graft lane.
- **Fork-fidelity in-game verification + `[[gateway]]` on-exit advance (#3)** (`story_flags` branch) — A1/A2
  **verified in real gameplay**: `[startup]` asserts the beat (F6 reads ScenarioCounter 2600/Dali, 10000/Daguerreo)
  and a faithful `--native` fork of a CLEAN static-roster field (Daguerreo 2F) RENDERS its real NPCs while the
  simple ones are fully interactive (turn + real carry-text lines + the shopkeeper opens the shop/inn menu). The
  contrast with a forked STORY-EVENT field (Dali Weapon Shop — `Field()`-warp DIRECTORS carried as NPCs → stacked /
  letterbox spawns) pinpointed two bounded carry gaps now in the worklist: **#13** event-actor-vs-standing-NPC
  classification + **#14** talk-handler `RunScript`-closure (both GRAFT LANE — overworld's). An ad-hoc scan that
  ranks all 674 fields by their count of `Field()`-warp DIRECTOR objects (0-director = cleanly forkable) picked
  the donor — the seed of a future `fork-report` (a per-field "what will/won't this fork reproduce" preview). New lever
  **#3 LANDED**: `[[gateway]]` gains `set_scenario`/`set_flags` (the write-side complement to `[startup]`) so a
  forked CHAIN progresses the beat — the `set_var` writes prepend to the gateway Range behind a usercontrol guard +
  any `requires_flag` gate, just before `Field()`; reuses `startup.startup_body`, validate + reserved-band lint
  mirror `[startup]`. Touches only `content/gateway.py` + `build.py` (orthogonal to overworld's import-scanner
  lane). kit 0.9.12; 787 tests.
- **`fork-report` — preview a real field's fork fidelity, OFFLINE** (`story_flags` branch; `ff9mapkit/forkreport.py`;
  the realized `fork-report` the ad-hoc scan above seeded). `ff9mapkit fork-report <field>` reads the compiled `.eb`
  (no game) and reports two INDEPENDENT axes — **roster fidelity** (# carried objects, # `Field()`-warp DIRECTORS,
  whether content rotates by beat) and **interaction fidelity** (per-NPC `graft_safety`: `clean`/`init_only`/`refuse`)
  — plus story-gated doors, the ScenarioCounter **beats the field gates content on** (scan for `DC 00 7D <const> <cmp>`),
  and a suggested `[startup] scenario` (earliest gate) + `import` recipe. Verdict: clean static-roster (forks faithfully)
  vs story-event (diorama). Validated against the real Dali shop (STORY-EVENT: 1 director, 11 beats Dali→Pandemonium —
  the rotating cast, now machine-readable) + Daguerreo (CLEAN). **Read-only** — reuses `eventscan.scan_objects_verbatim`/
  `scan_gateway_entries` + the `flags` beat table, adds NO carry/scanner logic (clear of overworld's lane). The design
  was grounded by a parallel understand workflow (4 read-only agents validating each signal on real fields); the
  scenario-inference heuristic was proven before baking it in. Pure `analyze_eb` unit-tested offline against the
  ALEX100 fixture. kit 0.9.13; 802 tests.
- **Verbatim SAVE-MOOGLE carry — the iconic FF9 save point, CARRIED (not synthesized) into a custom field
  (in-game proven; `import --save-moogle`; memory `project-ff9-savepoint`).** The cluster the object-carry research
  deferred as "structurally un-graftable" now forks faithfully (P1–P6.1, all on master): **P1** scoped cluster
  recognition (the hidden Moogle model 220 + its book/feather/tent, BFS over RunScript refs) + un-skip; **P2** the
  player-pose surgery (player funcs 13/14/15 graft, sibling-uid remap); **P3** trigger-chain + flag-integrity (no
  dangling refs; the cluster reads chest flags 8376–8511 = its verbatim mognet/treasure logic, validating
  `FIRST_SAFE_FLAG=8512`); **P4** the user-facing `[[save_moogle]]` wrapper (`import --save-moogle` ⇒ the cluster as
  `[[object]]`/`[[player_func]]` blocks + a marker); **P5** in-game gate → surfaced **THE CONTROLLER DEPENDENCY**:
  the Moogle is a PUPPET driven by the donor's **entry-0 tag-1** save-sequence DIRECTOR (a 44-instr loop that
  advances the Moogle's state via shared MAP vars `d5 20`/`e5 47 01`) — not an object, so the object carry missed
  it; **P6** the **director graft** (`eventscan.extract_savepoint_director` → `graft_director` = `replace_function_body`
  into the fork's empty entry-0 tag-1; references no entries → verbatim, no remap; the save-flash `SetBackgroundColor`
  NOP'd); **P6.1** the **spawn-flash fix** (`spawn_settle_mismatch` auto-normalizes the Moogle's Init Y `-362`→`-2`
  so it spawns at its rest pose, not standing-on-the-barrel-then-dropping — a real field's entrance fade hides that
  one-shot settle, a fork's doesn't). ★ P6.1 cracked by an **in-game video capture**, not static analysis (the
  `feedback-video-for-visual-bugs` memory). The **re-talk-after-cancel softlock is also RESOLVED** — P6.1's
  consistent spawn=rest pose fixed the return-from-barrel state too. The verbatim save-Moogle carry is COMPLETE.
- **Narrative-state fidelity arc** (the weak axis advanced; `ff9mapkit/docs/FORK_FIDELITY.md` #1-4 + #2b) — a fork
  now *behaves* more like its story beat, not just looks like it: **`[startup]`** presets (ScenarioCounter + story
  bits, prepended to Main_Init); **`import` auto-routes area<10 → native** (early-game fields — Alexandria/Cargo
  Ship/Dali — fork at last, in-game proven); **story-BRANCH doors** (>1 dest at one zone) flagged with a
  `requires_flag` stub + a `lint_logic` co-zone warning; **`[[gateway]]` `set_scenario`/`set_flags`** advance the
  ScenarioCounter/flags when the player takes an exit (so a chain progresses the story); and **story-GATED doors
  carried VERBATIM** — a real `if(flag)` door is a complex multi-flag state machine (NOT a single `requires_flag`),
  so `scan_gateway_entries` classifies it, the import emits a `[[gateway_carry]]` block + `.gatewayN.bin` sidecar,
  and `graft_gateway_entry` grafts the whole entry + retargets its `Field()` ids. **In-game proven (Dali Inn):**
  the forked door loads, runs, and stays GATED (closed at scenario-zero) instead of the declarative always-open —
  its GLOB conditions read the `[startup]` state (toggling its flags 2064/2073/2078 via F6 makes the gate respond).
  35/~50 gated entries are self-contained (carried); the **remaining limit** is the door-only carry not
  reconstructing MAP/transient vars the field's *main* logic (entry-0) sets, + the 15 ref-bearing gated entries
  (left as seams). Carrying entry-0 is the next frontier.
- **Verbatim-`.eb` fork (`import --verbatim`)** — the **entry-0 carry, productionized + in-game proven** (the
  truest "recreate the field from its bytes"). Entry-0's `Main_Init` arms the field's objects + gates the cast by
  ScenarioCounter, and the gated doors read MAP vars it sets — references that only resolve if the WHOLE donor
  entry LAYOUT is kept. So this mode ships the donor's entire `.eb` (entry-0 + every object + every gateway, slots
  intact) and the build runs it **AS-IS** (only `Field()` destinations remapped) instead of re-synthesizing.
  **In-game (Dali Inn): the field plays its real logic** — the gated door OPENS (its MAP-var deps satisfied, vs
  #2b's gated-closed door-only carry), the cast gates by story beat (consistent across re-entry). `content/verbatim.py`
  (`remap_fields` + `verbatim_eb`) + a `[verbatim_eb]` block (sidecar + a `retarget` template); `build_field` ships
  it when present (else synthesizes — golden byte-identical); pair with `[startup]` to boot a beat. **It also SPEAKS
  (P2, in-game proven):** the donor's WHOLE `.mes` ships too (`dialogue.extract_field_mes` → a `verbatim_mes.json`
  sidecar → the field's text block), and the verbatim `.eb`'s index-txids resolve straight into it (base-game field
  text is index-implicit) — NO remap, unlike `--carry-text`'s append-and-remap. ★ Per-lang gotcha (fixed): the 14
  same-zone `.mes` blocks carry no language in the name, so selecting by COVERAGE handed every language the longest
  (German) block — a `us` fork spoke German until `extract_field_mes` was switched to select by **`lang_score`**.
  The only LIMIT left is cosmetic: an F6-warp has no entrance fade to mask first-frame model streaming (a heavy
  model flickers in; faithful, fade-hidden in real play). **The verbatim fork is the most faithful mode — a real
  slice of the game (scene + real logic + real text) from one command.**

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
