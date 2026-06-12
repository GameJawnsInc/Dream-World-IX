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
no flag presets, one spawn). (The entry **cutscene** is NOT a gap — it runs from the field's own `.eb`, so a
verbatim fork carries it; the old "C# `NarrowMapList` cutscene" framing was a misread — see §7.) The toolkit lives at `ff9mapkit/` (package
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
| GUI apps | in **`apps/`**: `ff9_studio.pyw` = the **launcher** (front door to all GUIs) · `ff9_import.pyw` (**FFIX Import** — preview fork fidelity (fork-report) / fork a real field with fidelity options as checkboxes / read dialogue / inspect a save; shells out to `py -m ff9mapkit`) · `ff9_build_gui.pyw` (build+deploy — auto-detects **field / campaign / battle map**) · `ff9_editor.pyw` (logic editor) · `ff9_dialogue.pyw` (dialogue editor) · `ff9_infohub.pyw` (Info Hub viewer) · `ff9_storystate.pyw` (**Story State** — inspect / diff / EDIT a save's `gEventGlobal` story state; backup-guarded; calls `save`/`flags` directly) · `campaign_editor.pyw` (the all-in-one IDE; hosts the others as tabs incl. **Import** + **Story State**) |
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
- **New-Game → field 4003 is a MOD FIELD OVERRIDE, NOT a DLL edit** (verified 2026-06-12 by reading the
  deployed DLL's IL + the mod `.eb`s). `EventEngine.NewGame()` in the deployed DLL is **stock** (`fldMapNo = 70`,
  the opening-FMV field). The mod folder `FF9CustomMap` **overrides field 70** (`evt_alex1_ts_opening.eb` =
  `EVT_ALEX1_TS_OPENING` = id 70): it keeps the opening, plays **2 `Cinematic`(0x28) ops** (the ~2 s "Garnet on
  the boat" FMV), then warps `Field(4003)` instead of the stock `Field(50)`. So the whole New-Game-into-a-fork
  path is **engine-independent** (stock Memoria + opening-field overrides); **the ONLY custom DLL is the F6
  menu** — the old "Debug New-Game warp / s12 `fldMapNo` edit" framing was WRONG (the 3× `ldc.i4 4003` in the
  DLL are benign id→string TABLE DATA, not redirect code). To make New Game **seamless**, drop the 2 pre-warp
  `Cinematic` ops in the field-70 override (→ instant `Field(4003)`, no DLL, no `SkipIntros`). The companion
  overrides `EVT_ALEX1_AT_STREET_A` (id 100 → doors to 4003/4004/30100) + `EVT_ALEX1_TS_CARGO_0` (id 50) are the
  walk-through-Alexandria route (separate from the direct New-Game→4003 hop). → memory `project-ff9-new-game-entry`.
- **Versions:** kit `0.9.41`, Blender add-on `0.9.7`. **Provenance gate is CLEARED** — the
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
- Grep alone can't prove a field is unused — a field can be reached by a scenario-counter dispatcher, a
  runtime-computed id, or a *scripted* (non-`SetRegion`) `Field()` warp that `scan_gateways` skips, none of
  which a field-script grep sees. Trust the user's game knowledge over grep. (★ NOT via `NarrowMapList.cs`,
  despite older notes — that's the engine's per-field **camera-WIDTH / widescreen** table, not a cutscene
  trigger; entry cutscenes run from the `.eb`. → `feedback_trust_user_game_knowledge`.)
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
  the weak axis (a fork boots at scenario-zero, one spawn). [The audit's "no C# `NarrowMapList` cutscene" line
  was WRONG — entry cutscenes are `.eb`-borne; see the #10-premise-corrected timeline entry below.] Highest-leverage
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
- **FORKED STORY-CHAIN CAPSTONE — a forked field chain that PROGRESSES the story, in-game proven** (`story_flags`
  branch). `import-chain`'d the 4-field Daguerreo zone into a campaign, wired the full narrative-state stack:
  `[startup]` on the entry (DG_ENT, scenario 11090), the DG_ENT->DG_SRH **story door** advances on exit
  (`set_scenario 11765` + `set_flags 8800`, #3), DG_SRH gates content on that flag (#2). **In-game F6 -> Flags
  proved it**: walking the one door flips ScenarioCounter 11090->11765 AND flag 8800 0->1 — a campaign flag set
  in one forked field, read in another. The FIRST end-to-end demo that a forked chain progresses the story. ★
  Surfaced + fixed a real engine-build bug (memory `project-ff9-region-arming`): **`eb.edit.activate` silently
  lost region arming on fields with >2 regions** (blank Main_Init has 2 `Wait` fillers; the 3rd+ region used a
  raw `insert_bytes` at a stale position -> the 2nd+ insert corrupted -> the region never armed; the campaign's
  on-entry events never fired). Fix: route the fallback through `insert_in_function` (fpos-fixing). Diagnosed by
  an adversarial workflow; `tests/test_arming.py`. **Lessons:** F6 Reload does NOT refresh a campaign field
  (RELAUNCH to load a redeploy); a BG-borrow campaign of a multi-floor field is a MESSY demo surface (carried
  NPCs show orphan text, the carried elevator warps to real fields, content lands on the wrong walkmesh floor) —
  the F6 -> Flags readout is the reliable proof. kit 0.9.14; 810 tests.
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
- **`[[on_entry]]` — gated, once field-LOAD beats (`story_flags` branch; FORK_FIDELITY.md #10, kit 0.9.15).**
  ★ **Premise corrected (2026-06-11):** a field's entry cutscene RUNS FROM ITS OWN `.eb` (entry-0 + actor
  sequences), so a **verbatim** fork already carries it (proven, Vivi/field 100) — the old "fires from the C#
  `NarrowMapList` table, the `.eb` can't carry it" claim was a misread (`NarrowMapList` is the per-field
  camera-WIDTH table, zero cutscene logic). `[[on_entry]]` is still the right hook for a **synthesize** fork
  (which doesn't ship the donor `.eb`) and for ADDING a new gated entry beat: fire a narration `message` and/or
  story writes (`set_scenario`/`set_flags`) the moment the player ENTERS, **once**, but **only when the story
  state matches** (`requires_scenario` = ScenarioCounter `== N`, and/or `requires_flag`). The **gating** is the
  capability — neither `[startup]` (unconditional, every entry) nor `[cutscene]` (ungated, single) can express
  "fire this beat only at scenario N / when bit B is set". Each hook = a code entry armed by `InitCode` in
  Main_Init (the proven narration-cutscene arming, robust for any count post the region-arming fix), so it runs
  at load BEFORE control (hence no movement gate); the gates sit OUTSIDE the once-block, so a hook returns
  without spending its once-flag until its beat is reached. A `message` reuses the cutscene reorder-`Wait` + `DisableMove`/`EnableMove`
  lock. `content/onentry.py` + `build.py` (validate/collect_text/inject/lint) + `flags.py` (name resolution,
  read/write parity); surfaced in the dialogue viewer/editor. Byte-identical when absent; 14 tests, 826 suite.
  Orthogonal to overworld's verbatim/graft/import-chain lane (touches only the declarative-author + lint side).
  *In-game verification (a fork's entry message fires at the right beat) is the human step.*
- **Verbatim CHAINS (`import-chain --verbatim`)** — the verbatim fork extended from one room to a **connected
  SLICE** (**IN-GAME PROVEN** — a 4-field Dali slice: doors warp between the forks (ids verified via F6), each
  runs its real logic + speaks its real dialogue). `write_campaign(verbatim=True)` forks
  EVERY member native + verbatim, and the in-chain `Field()` exits are **retargeted to the chain's own member
  ids** (`content/verbatim.render_retarget` pre-fills the live `[verbatim_eb] retarget` table from the chain's id
  assignment; out-of-chain exits stay live seams). Each member ships its donor `.mes` at the donor's **own
  registered textid** (`EVENT_ID_TO_MES` — keyed in the FieldScene-id space, NOT the event-id space; a valid MesDB
  key so the FieldScene registers. All 676 forkable fields are covered → the `1073` fallback never fires;
  same-zone members share a textid and ship IDENTICAL zone text → no `<id>.mes` clobber). `import-chain --verbatim
  --out C` → `build-all` compiles a drop-in mod whose `.eb`s carry the retargets in their shipped bytes. ★ Three
  bugs caught by an **adversarial review workflow** (not in-game, not the test suite) and fixed: (1) **`[startup]`
  was silently dropped for ANY verbatim fork** — it lived only inside `build_script`, which the verbatim path
  bypasses; the documented "pair with `[startup]` to boot a beat" was a no-op (Dali Inn missed it by booting at
  scenario-zero). Fixed by a shared `build._apply_startup` applied to the verbatim bytes too. (2) the manifest
  graph showed live retargeted scripted/self doors as dead seams → `write_campaign` now adds them as `[[edge]]`s
  (honest reachability). (3) a verbatim member with no native atlas degrades to a declarative stub — now flagged
  loudly in the CLI summary (NOT verbatim). Touches `campaign.py`/`extract.py`/`content/verbatim.py`/`build.py`/
  `cli.py`; kit 0.9.16. Other frontier: New-Game INTO a verbatim chain with a full party.
- **Convergence: `[startup]` + `[[on_entry]]` both fire in a verbatim fork (the two branches unified).** BOTH are
  field-load levers the synthesizer arms in Main_Init, and the verbatim path bypasses build_script — so each was
  silently dropped there. This session unified them: a shared **`build._apply_startup`** AND **`build._apply_on_entry`**
  (the latter factored from `build_script`'s `[[on_entry]]` loop) are now applied to the verbatim bytes too. So a
  verbatim fork (single or chain) boots its `[startup]` beat AND fires its gated, once `[[on_entry]]` state-advances,
  armed onto the **donor's real Main_Init** (`inject_on_entries` works on a populated donor `.eb` — proven 23→24
  entries on Dali Inn, +1 InitCode, round-trips). The one limit: an `[[on_entry]]` **narration message** has no text
  channel in a verbatim fork (the donor `.mes` ships verbatim) → the message is **dropped + warned**, the gated
  state-advance still fires; the verbatim lint now flags only message hooks (was "all ignored"). Reuses story_flags'
  `content/onentry.py` UNCHANGED; touches only `build.py` (the shared helpers) — the minimal convergence surface.
  Offline + end-to-end proven; the in-game "beat fires at scenario N in a verbatim fork" is a natural add to
  story_flags' on_entry deep-dive. kit 0.9.17; 840 tests.
- **message-in-verbatim — an `[[on_entry]]` narration line now SHOWS in a verbatim fork (`story_flags`; IN-GAME
  PROVEN).** Closes the one limit the convergence left: the message was dropped (the donor `.mes` ships verbatim,
  no slot for authored text). Now the authored line is **appended to the donor `.mes` above its max txid**
  (`build._verbatim_on_entry_messages`, floored at `textcarry.CARRY_BASE_TXID` 1000 — the `--carry-text` trick) and
  the hook's `WindowSync` resolves into it. Only the verbatim branch of `build_field` changed (supply the text
  channel) + the now-obsolete lint warning retired; `_apply_on_entry` stays untouched (its `drop_messages` param is a
  general capability). **In-game proven on a Dali-Inn verbatim fork** (slot 30004, `text_block` 187 to dodge the
  1073 shadow): the appended line renders ON TOP of the donor's real logic, `set_flags` 8800→1, the once-flag holds
  on re-entry, and the inn's own NPCs still speak their real lines. ★ Nuance surfaced: in a verbatim fork the donor's
  own Main_Init can set the ScenarioCounter AFTER `[startup]` (the donor's real logic gets the last word) — the
  on_entry gate still matched (the message fired), so it's cosmetic. Touches only `build.py` + `content/onentry.py`
  tests + docs — orthogonal to overworld's non-Zidane (player/eventscan) lane. kit 0.9.18.
- **Non-Zidane donors — a verbatim fork of a non-Zidane field plays IDENTICALLY (in-game proven, Vivi/field 100;
  memory `project-ff9-non-zidane-donors`).** New `overworld` lane: fork a field whose controlled character isn't
  Zidane. A census of all **818** field `.eb` (one events-bundle pass) found **178 non-Zidane-primary** fields, ~80
  *truly playable as a party member* (Vivi 17 / Steiner 24 / Garnet 34 / Eiko-Freya-Amarant 5; the rest are the
  Gargant mount + ~80 cutscene-driver "players" — Brahne/Kuja/Beatrix/Cid/Marcus + endings — a cutscene shape, not
  a control one). ★ **In-game proof:** a `import --verbatim` fork of Vivi's Alexandria street (field 100) warped
  into via F6 plays the real thing — **Vivi renders + animates + shows in the party menu**, and the field's actual
  ticket-girl opening cutscene fires (proving that intro lives in the `.eb` entry-0, NOT a C# `NarrowMapList` table,
  so the verbatim fork carries it + the party setup faithfully). So a CLEAN single-PC, beat-agnostic non-Zidane
  field already forks faithfully with ZERO new code — the engine honors the field's `SetModel`, not the warp-in
  party leader, and the lane does NOT collapse into the party-state problem. The kit was SILENT about who you play
  as; **`fork-report` now has a Player axis** — who you control, single- vs **multi-PC**, and a non-Zidane →
  **`--verbatim`** recipe switch (the `--graft-player-funcs` path drops a non-Zidane player's funcs as `"model"`
  graft-safety = another rig's clips). Multi-PC inference is conservative (pents[0] is NOT reliably the controlled
  PC — the Cargo Ship lists Blank first; flagged non-Zidane only when NO Zidane is among the PCs, e.g. the Treno
  Dagger/Steiner split). Read-only (`forkreport.py` only, reuses the scanners) — clear of story_flags' build.py
  on_entry lane. The frontier is the multi-PC / scenario-gated-player BIND (untested which PC binds). kit 0.9.19;
  843 tests.
- **#5 — softlock / wrong-text lint for a plain (no-carry) import (`story_flags`; FORK_FIDELITY.md #5 LANDED).** A
  plain `import` carries a real field's objects but NOT their player funcs / dialogue text → softlock or wrong text
  in-game. Both halves now caught **offline, build-side**: **(b) the dangling-player-tag SOFTLOCK** was already a
  build-blocking `validate()` error (`_entry_player_call_tags` — a carried `[[object]]` that `RunScript`s the player
  at an un-grafted tag); **(a) un-carried TALKABLE text** is the new lint — `lint_logic` decodes each carried
  object's talk windows (`_entry_window_txids`, mirrors the player-call decoder) and warns when a shown donor txid
  isn't in the `[carry_text]` plan (import `--carry-text`, or author it). Validated on REAL imports: a plain
  `--native` Daguerreo fork flags all 5 talkable NPCs; a `--carry-text` fork (DGLO_FORK) stays silent (no false
  positive); props skipped. Reads only stable build-side data (`[[object]]` bins + the carry plan) — does NOT touch
  the eventscan classifier (overworld's lane). 5 tests; 848 suite. kit 0.9.20.
- **`fork-report` Dialogue axis — the #5 text gap, previewed BEFORE you fork (`story_flags`).** `fork-report` now
  reports a **Dialogue** line (orthogonal to the interaction-safety axis): how many carried NPCs SPEAK (a tag-3
  talk window) + line count (Daguerreo 2F "6 NPC(s) speak 36 line(s)"; Dali Inn "1 / 8"). Their words render WRONG
  unless the fork carries the text → the line says ship with `--carry-text` (or `--verbatim`), pointing at the
  build-side #5 lint as a before-you-fork preview. Read-only, reuses `dialogue.scan_dialogue` filtered to the
  carried objects' talk handlers (`forkreport.py` is story_flags'; no scanner logic of its own). 2 offline tests +
  an install-gated assertion; 850 suite. kit 0.9.21.
- **#7 — wide scrolling fork VERIFIED IN-GAME (`story_flags`; FORK_FIDELITY.md #7, no code).** A native fork of
  the wide Alexandria Main Street (field 3000, walkmesh ~12,800 units across, `[camera.scroll] enabled`) deployed
  to slot 30004 scrolls correctly — the camera pans 1:1 to follow the player across the FULL painting width, art
  stays floor-aligned (no FOV-doubling). The kit's scroll synthesis (`enable_camera_services`/BGCACTIVE, S15) was
  unit-tested only; now proven on a genuinely large field. Pure verification — doc-only.
- **Multi-PC control-bind CRACKED — engine-sourced + IN-GAME PROVEN; `fork-report` names the real controlled PC.**
  A 3-lens workflow (Memoria C# source + donor bytes + a verbatim playtest) settled "which PC binds when a field
  defines several": the engine sets `controlUID = gExec.uid` on each `DefinePlayerCharacter` (0x2C) as it
  EXECUTES (last-write-wins, `EventEngine.DoEventCode.cs`), and entries run their Init in **InitObject (0x09)
  order** — so control binds to the entry whose tag-0 Init runs a 0x2C **unconditionally** and is InitObject'd
  **LATEST**; it is **party-leader-INDEPENDENT** for fixed-SID fields. ★ **In-game proven** (a verbatim fork of
  the Treno Dagger+Steiner room `evt_treno1_tr_qhm_0` — an *alternate event script* for the FBG, shipped over the
  scene): you control **Garnet** (entry 9, last-executed 0x2C), NOT Steiner (entry 10, spawned first), NOT Zidane;
  free-roam, bind persists across gateways; the party MENU still shows Zidane (`controlUID` is decoupled from
  party state). `fork-report`'s Player axis now computes the real binder (`controlled_player`) — e.g. `controls
  Eiko of [Garnet, Eiko]` — replacing the `pents[0]` guess (the FIRST entry, which mispredicts — ac_alt binds
  Eiko, not the first-entry Garnet). Scoped to the non-Zidane lane (validated); a Zidane-present field keeps the
  "likely Zidane party-leader" hedge (control can route through a party slot — the Cargo Ship would mispredict).
  ★ Two process lessons: (1) the FIRST multi-PC probe (ac_alt) BURNED a playtest on a coronation CUTSCENE —
  "0 directors + static roster" ≠ free-roam (the PLAYER entries choreographed the scene); and there is **no
  reliable offline free-roam-vs-cutscene flag** (player-LOOP length doesn't separate: free-roam Vivi-100/Dali-Inn
  at ploop 254/272 vs the ac_alt cutscene at 50), so none was shipped. (2) The clean probe needed an UNAMBIGUOUS
  spawn order (each PC InitObject'd once) — `tr_fbh`'s Dagger re-spawn made it ambiguous; `tr_qhm` was clean.
  Read-only (`forkreport.py` only) — clear of story_flags' build.py lane. kit 0.9.22; 852 tests.
- **Story State GUI console — the story-flag SAVE verbs surfaced (`story_flags`; `apps/ff9_storystate.pyw`).**
  The save-side companion to the Info Hub's story-flag REGISTRY (already a `storyflag` kind): `StoryStateApp`
  loads a save and does **Inspect** (each slot's ScenarioCounter→beat + bits by named region — `save.inspect`
  + `flags.render_report`), **Diff** (A→B delta of two saves/slots — `flags.diff_reports`/`render_diff`), and
  **Edit** (set ScenarioCounter / set+clear story bits → write back). Edit is **backup-guarded** (`.bak` first)
  + **reserved-region-refused**, via a new `save.apply_story_edit` (the in-place edit+backup+write+extra-patch
  as one call, with `dry_run` for Preview; `edit_story_state` stays the shared core with the CLI). Wired into
  the launcher (7 tools) + a Campaign-Editor tab (7 tabs). Closes the gap that `flags-diff`/`save-edit` were
  CLI-only. 3 save tests + a headless `--smoke`; 854 suite. kit 0.9.23.
- **PC / party-control system MAPPED + PC-SWAP and PARTY-ADD proven IN-GAME (`.eb`-only, no DLL).** The
  non-Zidane lane became a full map of FF9's player-control + party-membership system (memory
  `project-ff9-pc-party-system`, via a 4-lens research workflow over the Memoria C# + bytes + the kit). Two
  DECOUPLED mechanisms: **field control** (who you WALK as = the player entry's `SetModel` 0x2F + 6 movement
  anim ids; `DefinePlayerCharacter` 0x2C binds control) vs **party state** (who's in the MENU/BATTLE =
  `party.member[]`, mutated by **`B_PARTYADD`** expr op `0x6D` + a `CharacterOldIndex` Zidane0..Amarant7,
  Beatrix8; `RemoveParty` 0xDD / `SetCharacterData` 0xFE / `SetPartyReserve` 0xB4 are statement ops already in
  the kit optables). ★ **Both `.eb`-only tiers PROVEN IN-GAME via one-off byte-injection probes** (no kit
  feature — overworld's probe lane): **(A) swap who you WALK as** — patched a forked Hangar (Zidane field
  1357) player Init `SetModel`+6 anim ids to Steiner (same-length 2-byte patches) → you walk as **Steiner**,
  animates cleanly, party menu stays Zidane; **(B) add a party member** — injected `partyadd(3=Steiner)`
  (`05 C5 93 7D 03 00 6D 2C 7F`) into Main_Init via `edit.insert_in_function` on a clean no-party-ops base →
  party menu shows **Zidane + Steiner** with valid starting equipment (the 12 PLAYER structs exist at boot).
  FF9 renders only the LEADER in the field (no walking followers). **(C) a BRAND-NEW custom party member** =
  the engine-fork frontier (CharacterId is a fixed DLL enum 0-11; `SetupPartyUID` can't bind a no-event-id
  member; the save layout is fixed; `CharacterBuilder.Spawn` exists but is dormant). NEXT PHASE = an authoring
  CAPABILITY (`import --swap-player <char>` = overworld's fork-transform lane; an `[[add_member]]`/`[party]`
  declarative block = story_flags' `content/`+`build.py` lane) — coordinate before building. Probes are scratch
  (uncommitted); this entry + the memory are the durable record.
- **`import --swap-player <char>` — Tier A productionized (walk as a different existing character).** The
  in-game-proven player-swap probe is now a real fork-transform: `import <field> --swap-player steiner`
  (zidane/vivi/steiner/garnet/freya/quina/eiko/amarant; aliases dagger, salamander) patches the player entry
  Init `SetModel` + the movement anim ids to that rig (same-length width-aware byte patch). Implies `--verbatim`
  (needs the donor's real player entry); party/menu state UNCHANGED (control vs party decoupled). The character
  table is real data extracted from each char's home field (model + eye-height + movement clips). New module
  `ff9mapkit/playerswap.py` (read-only transform) + `--swap-player` wired through `cli.py`; `.eb`-only, no DLL.
  6 tests incl. a Vivi-field→Steiner round-trip + a swap-to-self identity check (proves the baked table matches
  the game). Clear of story_flags' `content/`+`build.py` lane (the party-MEMBERSHIP authoring half stays theirs).
  ★ CAVEAT (warned): the swap repoints only the 6 MOVEMENT clips, so it's CLEAN on a free-roam field (Quina +
  Steiner in-game proven) but on a CUTSCENE field the player's scripted GESTURES (`RunAnimation`, rig-specific)
  glitch on the new model — `playerswap.scripted_gesture_ops` counts them (Vivi field 100 = 15) + the CLI WARNs.
  For STORY fidelity (be a character THROUGH the story) use a verbatim fork at the right beat + the right party,
  not a model swap (fully handling story characters = cross-rig gesture remap or the party/flag path — future).
  kit 0.9.26; 863 tests.
- **`fork-report` Party axis — what a fork does to your PARTY.** Completes the fork-preview (Player / Roster /
  Interactions / Dialogue / Story-gating / **Party**): `fork-report` now decodes a field's party-membership ops
  (which a `--verbatim` fork RUNS) — the literal `B_PARTYADD` (`B_CONST <CharacterOldIndex> 0x6D`) inside expr
  statements + the statement ops `RemoveParty`/`SetPartyReserve`/`SetCharacterData`/`Party`-menu — e.g. field 60
  "adds Zidane, Vivi, Garnet, Marcus; sets the recruitable roster", field 100 "adds Vivi; rebuilds the roster",
  the Dali Inn "opens the change-members menu"; party-neutral fields (the Hangar) get no line (NONE filtered,
  deduped). Read-only (`forkreport.scan_party_ops`, reuses the disasm) — overworld's analysis lane; serves the
  PC/party goal (recipe in memory `project-ff9-pc-party-system`). 4 tests. kit 0.9.27; 867 tests.
- **Modern-save safe-band AUDIT + chest-band provenance fix (`story_flags`; kit 0.9.28, offline, no behavior
  change).** Audited the kit's custom-flag safe band (≥ bit **8512**) against the MODERN Memoria engine's
  `gEventGlobal` usage: **CLEAN** — the engine's highest reads are the Treasure-Hunter rank (bytes 182-186 +
  896-975), voice-acting (510-525), and scenario/words (≤207); the legacy ability-usage at byte 1100+ is
  OLD-format-only (modern saves store it in a separate `gAbilityUsage` JSON field, `JsonParser.cs`
  `ParseEventDataToJson if(!oldSaveFormat)`), so even 1100+ is free. User-confirmed in-game (set bit 8512
  persisted). The audit surfaced + fixed a **provenance inaccuracy in the chest band 8376-8511**: verified from
  real `.eb` bytes (fields 115/300/2203/407 + 44 more) that it's a **byte-identical 130-entry dispatch block**
  compiled verbatim into ~48 chest fields (NOT a "runtime-computed index"), and that the **stock engine never
  reads it** (the TH rank is the SEPARATE 182-186 + 896-975 region — the old `GetTreasureHunterPoints` citation
  was wrong). The band stays real + reserved (48 fields read+write it); only the prose/citation changed in
  `flags.py`/`build.py` + `research/STORY_FLAGS.md`/`make_catalog.py`/`flag_catalog.toml`, plus a regression test
  asserting the chest band ⟂ the engine TH bytes. 868 suite. See memory [[project-ff9-story-flags]].
- **`import-chain --swap-player` — play as one character across a forked region (+ an adversarial-review fix).**
  `import-chain <seed> --swap-player steiner` swaps EVERY verbatim member's player rig (shared
  `extract.apply_player_swap`; `write_campaign(swap_player=…)` per member). ★ An **adversarial review workflow**
  (3 lenses) caught a real bug the test suite + my smoke missed: the swap TARGET via `controlled_player` reskinned
  a CO-ACTOR on **Zidane-present** multi-PC fields (control routes through the party SLOT to the Zidane leader,
  not the last-0x2C binder) — **66/169** fields (Cargo Ship 500 swapped Vivi, left Zidane). Fixed to swap by the
  controlled-**leader model** (`playerswap.leader_model`/`swap_targets`: a Zidane form 98/532 when present, else
  the proven no-Zidane binder; patch ALL entries matching it). Plus: `controlled_player` low-confidence on
  Zidane-present, a distinct `NoSwappablePlayer` (chain skips a no-player member; real corruption ValueErrors
  propagate), true fail-fast char validation, a qualified summary. Lesson: an adversarial review pays for itself
  on chain features — same as the verbatim-chain capstone. kit 0.9.29; 870 tests.
- **`--swap-player` generalized to ANY model — the field-side bridge to custom characters.** `--swap-player`
  (single + chain) now takes a playable name OR **any registered model** (a `GEO_..` name or numeric id — a
  moogle `199`, `GEO_NPC_F0_BMG`): a playable uses its proven home-field table, any other model resolves its 5
  movement clips via the kit's model→animation join (`catalog.npc_anims`) — so you can **walk as a moogle / an
  NPC / a creature** (a static monster raises). This is the field-side mechanism a CUSTOM model would use
  (`SetModel` + movement clips, no DLL), demonstrable now with existing assets. ★ Cross-rig GESTURE remap was
  PROBED + found infeasible (cutscene player gestures are scene-specific — Vivi-100's 15 = KOKE/RECEIVE/KISS_ME,
  0 with a Steiner equivalent — not a shared vocabulary; the `WARN` stays the handling). `playerswap.resolve_char`
  (general) + `cli.py`; overworld's lane (clear of story_flags' party-membership authoring). kit 0.9.30; 873 tests.
- **`[party]` — add/remove party members at field load (`story_flags`; the declarative complement to
  `--swap-player`).** Where `--swap-player` changes who you WALK as (overworld's fork-transform lane), `[party]`
  changes who's in the PARTY (menu + battle roster) — the two are DECOUPLED (control vs party state, memory
  `project-ff9-pc-party-system`); this is the declarative half flagged for our lane. `content/party.py`:
  `add_member` emits the **in-game-proven** `B_PARTYADD` form `05 C5 93 7D <id> 00 6D 2C 7F` (op 0x6D — the
  kit's FIRST expression-opcode emitter; the proven Tier-B probe productionized), `remove_member` = `RemoveParty`
  0xDD via `opcodes.encode`; `inject_party` prepends to Main_Init like `[startup]` (byte-identical when absent).
  Names → CharacterOldIndex (Zidane 0..Blank 11; aliases dagger/salamander; bare 0–11), pinned to
  `forkreport.CHAR_OLD_INDEX` by a test. Wired into build.py via a shared `_apply_party` in BOTH the synthesize
  AND verbatim paths (so a verbatim fork's `[party]` fires too); `validate()` resolves every name; a verbatim
  fork that rebuilds the roster (`SetPartyReserve` 0xB4, runs AFTER our prepend → can wipe the op) gets a build
  WARNING (`field_resets_party`). `.eb`-only, no DLL; FF9 renders only the leader (added member = menu/battle,
  not a field follower); no flag allocation. A brand-new CUSTOM member is still the engine-fork frontier (Tier C).
  ★ An **adversarial-review workflow** (3 lenses) caught two real bugs the 882-test suite missed — both FIXED:
  (1) `inject_party` (+ the pre-existing `[startup]`/`[[on_entry]]`) raised an OPAQUE `ValueError` on the ~11% of
  fields (incl. field 100) whose Main_Init opens with a 0x06 jump table the inserter can't shift past → now the
  verbatim path FAILS CLOSED with a clear `BuildError` (shared `_field_load_inject`); (2) the wipe-warning scanned
  only entry-0/tag-0, but real `SetPartyReserve` lives in object Inits / tag-1 (only 2/111 reset fields keep it in
  Main_Init) → broadened to all non-empty entries' tag-0+tag-1 (catches 111/111). 12 tests (`tests/test_party.py`);
  883 suite. kit 0.9.31. ★ **IN-GAME PROVEN (2026-06-11):** a Daguerreo-2F native fork + `[party] add =
  ["steiner", "freya"]` → New Game → F6-Warp → the party menu shows all 3 (Zidane + Steiner + Freya) with
  starting equipment. Tier B authoring is end-to-end proven.
- **Items & equipment recon + `fork-report` Items/Treasure axis (`items_equipment` branch; memory
  [[project-ff9-items-equipment]]).** First session of the branch: mapped the whole item/equipment surface. ★ The
  headline finding — engine item/equip/shop **STAT data is fully CSV-moddable on STOCK Memoria, NO DLL**
  (`<game>\StreamingAssets\Data\Items\*.csv` — Items/Weapons/Armors/Stats/ItemEffects/ShopItems/MixItems/Synthesis/
  InitialItems — loaded via `AssetManager.EnumerateCsvFromLowToHigh`, merged by id low→high across mod folders →
  partial-CSV delta overrides, the kit's existing data-patch surface; item NAMES = the `.mes` text channel, ordinal-
  indexed). The KIT today knows item **NAMES ONLY** (`_itemdb.py` 0-255 from `RegularItem`; `items.py` resolver;
  `give_item`/`holds=`/F6 cheat/catalog) — no effects/stats/shops/equipment. 3-layer data model (`ItemInfo` + FK→
  `ItemAttack`/`ItemDefence`/`ItemEffect` + `ItemStats`); id bands wpn 0-87 / wrist 88-111 / helm 112-147 / body
  148-191 / accy 192-223 / gem 224-235 / item 236-254; key items a SEPARATE space; equipment teaches abilities
  (`AbilityIds`). Roadmap (all engine-independent): catalog-enrichment first, then reward/party-equip/shop authoring,
  save-side item editor, item-data edit/mint. **Built lever (#fork-fidelity-aligned): `fork-report` Items/Treasure
  axis** — `forkreport.scan_item_ops` decodes `AddItem`(0x48)/`AddGil`(0xCE)/`Menu(2,id)`(shop) off the disassembler
  and reports the treasure/gil/shops a fork reproduces. A `--verbatim` fork RUNS these (byte-identical); a plain/
  synthesize fork has NO item scanner → DROPS them all; shop STOCK is parasitic on the base `ShopItems.csv`. ★ Two
  correctness traps caught by a real-field sweep + fixed: (1) **don't SUM grants across the field's mutually-exclusive
  story branches** (Ether x1 on two paths ≠ x2; gil over the 9,999,999 cap is a scripted sentinel) → report distinct
  items (per-grant max) + gil as a plausible per-grant max; (2) the event `AddItem` id is **pool-encoded** (`id % 1000`:
  0-255 regular, 256-511 key item, 512-611 card, ≥612 engine **no-op** → excluded) per `ff9item.FF9Item_Add_Generic`
  — a plain 0-255 id is named, higher pools classified-but-unnamed. An **adversarial-review workflow** (3 lenses:
  engine-fidelity / Python-correctness / scale-risk over all 676 fields) confirmed the decode is engine-exact + found
  zero false positives, and caught a latent under-report (a computed-id-only `AddItem`/`Menu(2,<expr>)` rendered
  nothing) → fixed + the symmetric **gated-shop** surfacing added (`var_shop` → "opens a story-gated shop", recovers
  42 fields incl. Dali inn 351 / Ice Cavern 300). Read-only (`forkreport.py` only, reuses the disasm; clear of
  overworld's graft + story_flags' build lanes). kit 0.9.32; 897 tests (12 new, atop story_flags' [party] 885).
- **`fork-report` Player axis — swap-friendliness tag.** The Player line now ends with `swap-clean` (a free-roam
  field — `--swap-player` is clean) or `swap: N gesture(s) glitch` (a cutscene field whose player plays N
  scripted gestures that glitch on a swapped rig — only movement clips are swapped). The before-you-fork preview
  of the swap-time `WARN`, for browsing/choosing a swap or demo target (field 1200 `ac_rst_x` = swap-clean + a
  close 3/4 camera = a good visual-test room; Vivi field 100 = swap: 15 glitch). Reuses
  `playerswap.scripted_gesture_ops` (the controlled-leader-targeted count). `.eb`-only, `forkreport.py` only.
  kit 0.9.33; 898 tests.
- **`fork-report` Camera axis — the lens a fork plays through.** A new `Camera` line previews the framing:
  `close`/`medium`/`wide` bucketed by horizontal FOV + the raw pitch/FOV, and flags `scrolling` / multi-camera
  fields (field 1200 `ac_rst_x` = `close (FOV 29.5, pitch 28.8); 2 cameras`; Hangar 1357 = `wide (FOV 61.3, pitch
  0)` — the "super far away" view; Vivi street 100 = `close (FOV 17.2); scrolling` — a tight lens that pans).
  Pairs with the swap-friendliness tag: `swap-clean` + `close` = a good `--swap-player`/demo test room (vs a wide
  shot where models are tiny). The camera is in the scene `.bgs` (not the `.eb`), so it needs the install — a new
  read-only `extract.field_camera_info` (pitch/FOV/scrolling/count, no walkmesh/atlas extract) populates the
  report in `analyze()`; the pure `analyze_eb` is untouched (no camera → line omitted → fixtures byte-identical).
  Reuses `cam.pitch_deg`/`cam.decompose` (no new camera math). 4 tests; clear of story_flags' build + overworld's
  graft lanes. kit 0.9.34; 902 tests.
- **Item stat/effect CATALOG enrichment — the Info Hub now shows what an item DOES (`items_equipment`; the
  roadmap's recommended-first move).** `ff9mapkit items` + the Info Hub item detail were NAMES-ONLY; new
  `itemstats.py` JOINS the five FF9 item-data CSVs (`Items` + FK→`Weapons`/`Armors`/`Stats`/`ItemEffects`) into
  one `ItemStat` per id → weapon Atk+element, armor defence, equip stat bonuses + elemental affinity, consumable
  use-effect, price, type/slot, who-can-equip, abilities taught. `summary()` (one-line) + `facts()` (detail);
  element/category/type bitmasks decode to names. ★ **PROVENANCE-CORRECT (the load-bearing decision):** item
  STATS are game DATA, so — unlike the committed names table `_itemdb.py` — they are **NEVER committed**;
  `itemstats` reads them LIVE from the user's install (`<install>\StreamingAssets\Data\Items\*.csv` = Memoria's
  editable item tables), caches in-memory, ships/commits nothing (PROVENANCE.md:63-64 = "names/ids only, no
  stats"). Columns read from each CSV's `#`-legend (not hard-coded indices → survives the option-driven column
  toggles). Degrades to id+name when the install is unreachable (Info Hub still works offline). Wired into
  `infohub.py` (browse summary + detail facts) + the `items` CLI. 8 tests (pure decoders/parser/formatters +
  graceful-degradation offline; the real join install-gated). Read-only foundation the shop/reward/save-editor
  item pillars read from; clear of story_flags' compose lane + overworld's graft lane (see [[project-ff9-branch-lanes]]).
  ★ A 3-lens adversarial review (provenance / engine-fidelity / Python) verified provenance CLEAN + the mappings
  engine-exact, and caught the one real bug: status-only consumables (Phoenix Down/Antidote, Power 0, effect in
  the `BattleStatus` mask) showed a misleading "use pow 0" -> now the `Status` mask is decoded + the effect line
  is gated on meaningfulness ("effect status Death"; empty-effect accessories show none). kit 0.9.35; 913 tests
  (11 new, atop overworld's Camera 902).
- **`remove_item` — the symmetric take-item reward lever (`items_equipment`; reward ergonomics #2).** `[[event]]`/
  `[[choice]]` could `give_item` but not take one; new `remove_item = [item, count]` (id or name) emits
  `RemoveItem` (0x49) — pair with `give_item` for a TRADE, or alone to CONSUME a quest item. (give-by-name +
  the "Received X" box already worked for ANY item incl. weapons/armor, so this closes the one missing half.)
  `opcodes.remove_item` + `event.take_item` (name-resolved) wired symmetrically into the event + choice builders
  + `validate()` (a sole `remove_item` is a valid action; an unknown name is caught; the engine clamps removal to
  what's held). 4 tests; clear of story_flags' compose lane + overworld's forkreport lane. kit 0.9.36; 917 tests (4 new).
- **`find-rooms` — sweep ALL fields for the best swap/demo TEST ROOMS (the option-#2 room finder; built via an
  understand→implement→review workflow chain).** `ff9mapkit find-rooms` ranks every forkable field as a place to
  walk as a `--swap-player` character / stage a visual test where the model's DETAIL is visible. The proven anchor
  1200 `ac_rst_x` ranks #1; the top list matches the hand-verified clean rooms (1911 Treno, 310 IC cafe, 3055 BMV
  shop…). ★ KEY FINDING (an **understand workflow** validated it against the real game, NOT guessed): **FOV alone is
  NOT a detail proxy** — FF9's projection is orthographic-like (k≈0.93, the camera-math invariant), so a sub-10°
  "FOV" is a far TELEPHOTO (model is a speck), not a close shot. So a "room" is the AND of single-PC + swap-clean +
  PLAYABLE controller + STATIC roster + a close 3/4 camera = bounded FOV (10–45°) AND a 3/4 pitch band (6–48°) AND
  the camera `range_height` ≤420 (the key signal, now exposed from `field_camera_info`) AND no `_CS_` cutscene tag;
  scrolling is a rank demerit. Two-phase for speed (~45s/675 fields): a cheap `.eb`-only prefilter (one
  `EventBundle`) → 75 survivors → the expensive per-field camera read only on those. `forkreport.find_rooms`/
  `room_score`/`RoomSweep`/`format_room_table` + `ROOM_*` constants; `extract.field_camera_info` returns
  `range_w/h`; `ForkReport.cam_range_h`; `_camera_line` gained a `distant` label for sub-10° FOV (corrects the
  Camera axis). ★ A **3-lens adversarial review** caught 4 real bugs the suite missed — a missing low-pitch bound
  (flat side-on rooms ranked too high), a too-loose max-pitch (top-down siblings), a VEHICLE-player donor (a
  submarine field offered as a swap room), and story-event leakage — all fixed (the prefilter now gates on
  playable + static-roster). Read-only; `forkreport.py`/`extract.py`/`cli.py` only — clear of story_flags' build +
  the graft lanes. 12 tests. kit 0.9.37; 925 tests. See memory [[project-ff9-non-zidane-donors]].
- **New-Game-entry mechanism NAILED + a seamless-entry lever (kit 0.9.38; memory `project-ff9-new-game-entry`).**
  A deep playtest+decompile exercise corrected a load-bearing misconception (CLAUDE.md §5 + my own inference):
  New-Game-into-a-custom-field is **NOT a DLL edit** — `EventEngine.NewGame()` in the deployed DLL is **stock**
  (`fldMapNo = 70`, verified by reading the IL: `new Byte[2048]` → 3× `.Clear()` → `ldc.i4.s 70`), the 3× `ldc.i4
  4003` in the DLL are benign id→string TABLE DATA, and the redirect is a **mod field-70 override**
  (`evt_alex1_ts_opening` = `EVT_ALEX1_TS_OPENING` = id 70 → `Field(4003)` after 2 `Cinematic`(0x28) FMV ops).
  So **the ONLY custom DLL is the F6 menu** (the user was right) and the whole New-Game-into-a-fork path is already
  engine-independent. Diagnosed via a structured **4-playtest protocol + a frame-montage of the capture** (the
  ~2 s "Garnet on the boat" is field-70's own FMV; `SkipIntros` is boot-only) + a no-decompiler **targeted IL
  read** of the live DLL. Landed lever: **`eb.edit.nop_cinematics`** + **`tools/skip_opening_fmv.py`** strip the
  pre-warp cinematics from the field-70 override → New Game lands in the target field instantly, pure-mod, no DLL.
  Applied in-game (7 lang copies, backed up; in-game test = human step). Orthogonal to the lanes (a clean dev
  tool); merged ahead of items_equipment's New-Game/equip-CSV work. 1 test; kit 0.9.38.
- **`list-fields --players` / `--non-zidane` — who you play as in each field (kit 0.9.39; the option-#3
  enrichment).** `list-fields --players` annotates the field list with the controlled character; `--non-zidane`
  narrows to the verbatim-fork DONORS (you play as someone other than Zidane), discoverable without forking each.
  ★ **Id-centric** (a player is an `.eb` property), so an alternate event script on a shared background is its OWN
  row — revealing non-Zidane variants the folder-centric `list-fields` hides (the Steiner `_b` scripts 2050-2053
  next to their Zidane `_a` twins). The live `--non-zidane` sweep finds **89 of 675** — 53 playable-cast donors
  (Steiner 19 / Garnet 18 / Vivi 10 / Eiko 4 / Freya, Amarant 1) + 36 cutscene-driver `GEO_SUB` "players" (the
  footer splits them); fewer than the census's looser
  178 because `non_zidane` uses the stricter, in-game-proven definition (non-Zidane only when NO Zidane is among
  the PCs → excludes Zidane-present escape scenes where you actually control Zidane) = the honest "you really play
  as someone else" set. `forkreport.field_players` (sweeps `ID_TO_FBG`, reuses `analyze_eb`'s player resolution,
  one `EventBundle`) + `player_label` + `FieldPlayer` (with a `playable` flag); CLI `_list_fields_with_players`.
  Plain `list-fields` unchanged + fast; a full sweep ~30s. ★ A 2-lens adversarial review caught a root-cause bug:
  **`eventscan.ZIDANE_MODELS` was missing the ZDD disguise (532) + ZDN LOD forms (203/432/668-670)** → Zidane fields
  leaked into the non-Zidane lists (field 401 = `Zidane(ZDD)`); fixed at the root (now covers every
  `GEO_MAIN_*_ZDN`/`_ZDD` form, also correcting find-rooms + the Player axis; count 91→89). Read-only;
  `forkreport.py`/`cli.py`/`eventscan.py` — clear of build + graft lanes. 7 tests. kit 0.9.39; 933 tests. See
  memory [[project-ff9-non-zidane-donors]].
- **`[start_inventory]` / `[[equipment]]` — new-game starting bag & default gear (`items_equipment` roadmap #3;
  the New-Game-capstone SEAM, contract pinned with story_flags — memory [[project-ff9-branch-lanes]]).** Author
  what the player STARTS A NEW GAME with, as engine-independent CSV deltas (stock Memoria): `[start_inventory]`
  → the FULL `Data/Items/InitialItems.csv` (engine reads it HIGHEST-PRIORITY-WINS → replaces the base bag; counts
  clamp 99, dup ids sum) via `content/inventory.py`; `[[equipment]]` → a PARTIAL `Data/Characters/DefaultEquipment.csv`
  (engine MERGES low→high over the base's 15 sets → only named chars change; each row a complete loadout, omitted
  slot = -1 empty) via `content/equipment.py` (char→`EquipmentSetId` is a names/ids-only table, provenance-clean).
  ★ Per the PINNED handoff contract: blocks live on the ENTRY field's `field.toml` ONLY; EMITTED at the mod-write
  stage (`build_mod._emit_start_state`, alongside DictionaryPatch/BattlePatch via `ModLayout` — NOT eb-synthesis;
  these are mod-global files), fires once; lint-WARNS if a block lands on a non-entry field (PRECISE for a campaign
  via the entry member, threaded through `build_mod(entry_project=)`), plus the InitialItems highest-wins/shadow
  caveat. New-game-only scope (read once at new-game init); composes with story_flags' `[startup]`/`[party]` + the
  seamless New-Game entry. ★ Adversarially reviewed (3 lenses): provenance CLEAN (writers deterministic from the
  toml + committed name tables, no game stat data read/committed), and the partial DefaultEquipment confirmed to
  MERGE with the base (no "must define 15 sets" boot crash). `validate()` resolves every name; new `ModLayout`
  paths. 15 tests; clear of story_flags' compose lane (I ship the deltas, they compose). kit 0.9.40; 948 tests
  (15 new, atop overworld's list-fields 933).
- **`--swap-player --neutralize-gestures` — stand cleanly through a cutscene (the option-#4 swap fix).** Makes a
  swapped character STAND/idle through a cutscene field instead of T-posing on the donor rig's scripted gestures.
  On every swap-target player entry it rewrites each `RunAnimation` (0x40) clip + LOOP movement re-sets to the
  swapped rig's OWN idle, leaving `WaitAnimation`/`SetAnimationFlags` intact (timing preserved). ★ **Engine-grounded**
  (a workflow read Memoria `DoEventCode`/`ProcessAnime`): RunAnimation is NAME-keyed via a global clip dict, so a
  foreign donor clip loads a foreign-skeleton clip = the glitch; the rig's idle is already loaded (by the swap's
  SetStandAnimation) so the paired `WaitAnimation` completes — no hang. NOP-ing was REJECTED (orphans the wait).
  Cross-rig gesture REMAP stays infeasible (no shared vocabulary) — neutralize trades emoting for not-glitching;
  for story fidelity use a verbatim fork at the right beat. `playerswap.neutralize_gestures` (reuses `_put_arg`);
  `apply_player_swap(neutralize=)`; `write_campaign(neutralize_gestures=)`. ★ A 2-lens adversarial review caught a
  BLOCKER: swap+neutralize ran as two passes each re-deriving `swap_targets()`, which keys on the SetModel id the
  swap MUTATES → on Zidane-present multi-PC fields (87/668) it DRIFTED to a co-actor (neutralized the wrong entry +
  corrupted a bystander). Fixed: resolve targets ONCE on the original bytes + reuse (the `entry=` override takes a
  list) + a defensive model-match guard; field-500 regression test; chain summary no longer false-WARNs. ★ Surfaced
  a PRE-EXISTING orthogonal issue (spawned as a task): `import` ships a DIFFERENT event script than
  `fork-report`/`list-fields` analyze (field 100: import = Zidane multi-PC, eb_for_id = Vivi single-PC). Offline +
  on-the-real-import-artifact proven (entry 12 Zidane->Steiner, all 24 gestures -> idle). ★ **IN-GAME PROVEN**
  (Alexandria street alxt_map016 forked Vivi->Steiner, 15 gestures): Steiner stands in his idle cleanly through the
  cutscene beats, no T-pose, scene flows normally. ★ The wait duration after neutralize is ENGINE-AUTOMATIC = the
  SUBSTITUTE idle clip's own frame count (`GetCharAnimFrame` reads the loaded clip at runtime; `WaitAnimation` blocks
  on `afExec` until `ProcessAnime` plays it out) -- NOT the original gesture's duration (the engine doesn't preserve
  it); reads natural because the idle has a real length + the scene's macro-pacing is gated by dialogue windows /
  fixed `Wait(N)` ops neutralize leaves intact. Touches `playerswap.py`/`extract.py`/`cli.py`/`campaign.py`. kit
  0.9.41; 951 tests. See memory [[project-ff9-non-zidane-donors]].

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
