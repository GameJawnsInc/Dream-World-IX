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
| GUI app | **`apps/ff9_workspace.pyw`** — the one front-door app: a PySide6 **Workspace** (a journey ▸ campaign ▸ field ▸ object tree + Inspector). Tabs: Editor / Map / Story State / Item & Equip / Battle / Build & Deploy / Import, plus an Info Hub library + a Ctrl-K palette + a bottom Output/Problems console. The 8 old tkinter `.pyw` were RETIRED into it (same tk-free backends). PySide6 = optional `gui` extra. → [[project-ff9-gui-makeover]] |
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
  (`FieldLocationName`, s33; this also backs the authorable `[field] location`). Patches in `memoria-patches/`;
  the per-site census + verification debt (which patches are still ⚠ IN-GAME UNVERIFIED) live in
  **`ff9mapkit/docs/FORK_IDGATE_MAP.md`** → [[project-ff9-doeventcode-fork-gates]], [[project-ff9-fork-verification-harness]].
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
  snapshot a `gEventGlobal` flag) · **Time**. Header shows live context; a **combined pinnable ★-favorite list** of BOTH field
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
- Battle tuning — enemy + player side + raw17 `btlseq` attack-choreography, no DLL → [[project-ff9-battle-tuning]]
- Scripts-DLL — a custom ability's `script = {template/body}` mints a NEW battle FORMULA (a `[BattleScript(id≥256)]` in a mod `Memoria.Scripts.<Mod>.dll`, compiled at deploy vs the installed engine; NO engine rebuild). ★ P1 (raw bind) + P2→P4 (declarative channel) in-game proven 2026-07-07 (Iviv's "Soul Leech" drain) → [[project-ff9-scripts-dll]]
- Battle/party GUI — battle + party config folded into the Workspace (encounter-first) → [[project-ff9-battle-party-gui]]
- Campaigns — `import-chain` + the Campaign-Editor IDE → [[project-ff9-worldmap-feasibility]], [[project-ff9-import-chain-coverage]]
- Multi-campaign journey assembler — both link modes + zero-link deploy-derived auto-wiring → [[project-ff9-world-hub]], [[project-ff9-journey-single-folder]]
- World Hub — playable journey selector (New Game → hub → verbatim forks) → [[project-ff9-world-hub]]
- Navigable jumps + save points (synthesized & verbatim save-Moogle) → [[project-ff9-jump-navigation]], [[project-ff9-savepoint]]
- Story flags — `gEventGlobal` mapped, 5 verbs, safe band ≥8512, field/campaign/journey scopes → [[project-ff9-story-flags]], [[project-ff9-flag-scope-hierarchy]]
- Faithful object/NPC carry → verbatim fork (`--verbatim` = real logic + real text); additive content on a verbatim fork → [[project-ff9-verbatim-fork]], [[project-ff9-npc-on-verbatim]]
- Non-Zidane donors + PC/party control (`--swap-player`, `[party]`) → [[project-ff9-non-zidane-donors]], [[project-ff9-pc-party-system]]
- **13th playable character** — a genuine NEW `CharacterId` (id 12), party member alongside all 12 canon chars, **ZERO DLL** (`[[playable]]` block: CSV allocator + `CharacterDefaultName` + `B_PARTYADD`); ★ fully in-game proven (recruits, own name/stats, fights, save-persists) + a custom (Blender-edited) battle model (`custom_battle_model`) + a custom menu portrait (`portrait`) + an **independent, editable battle ANIMSET** (`custom_battle_anims` — own `Animations/<mintId>/` clips + `3DModelAnimation` regs, donor untouched; ★ in-game proven 2026-07-06) + a **bespoke ABILITY KIT** (`[playable.abilities]` — its OWN `CharacterPresetId` ≥20: own command menu + curated learn list, e.g. a mixed black+white caster; ★ in-game proven 2026-07-06) + a **UNIQUE minted COMMAND** (a `command1`/`command2` inline table `{name, abilities}` → a NEW `BattleCommandId` in the safe band 46/35-40 with its OWN ability pool + `com_name.mes` name overlay, per-id-merged Commands.csv, zero-DLL; ★ in-game proven 2026-07-06) + a **CUSTOM ACTIVE ability** (a pool inline table `{name, from, power, element, mp}` → a NEW `Actions.csv` row in the 192-223 band CLONED from a donor + retuned + `aa_name.mes` overlay — his spells BEHAVE uniquely, not just group uniquely; ListEntry raw-id vs learn `AA:id`; ★ in-game proven 2026-07-06) — which also takes **`status = [names]`** (auto-mints a StatusSets row in a 100+ band + injects the action's `statusIndex`, crash-safe; ★ Silence in-game proven 2026-07-06) and **`effect = "[code=TAG]…"`** (a minted `[[ability_feature]]` `>AA <rawId>` block, `_AA_MAX`→223; ★ `[code=MPCost] 0`→free-in-battle proven 2026-07-06 — a BATTLE-side hook, so the field menu still shows the base cost) → [[project-ff9-ability-preset-system]]) — ★ GENERALIZES: a 2ND custom character (id 13 "Steiniv" on the Steiner KNIGHT rig, its own preset/command/ability in distinct auto-allocated bands) recruits + fights alongside Iviv, in-game proven 2026-07-06 (the roster is an unbounded `Dictionary<CharacterId,PLAYER>` — id 13 works like the proven id 12) → [[project-ff9-13th-character]]
- Items / equipment / shops + save editor + the New-Game starting-state capstone → [[project-ff9-items-equipment]], [[project-ff9-save-item-layout]], [[project-ff9-new-game-entry]]
- `fork-report` (offline fidelity preview) + verbatim-fork SPATIAL authoring (Blender markers) → [[project-ff9-npc-on-verbatim]], [[project-ff9-fork-fidelity-worklist]]
- InfoHub authoring — place any model/prop/creature by name → [[project-ff9-infohub-authoring]]
- Active Time Events — both flavors authorable (optional blue menu + grey unskippable) → [[project-ff9-ate-system]]
- Offline field-art export + native-art repaint round-trip + multi-camera fidelity → [[project-ff9-novel-bg-pipeline]], [[project-ff9-native-repaint-workflow]]
- Advanced interactables (moving platforms / elevators) — `--verbatim` carries; declarative `[[platform]]` is the frontier → [[project-ff9-moving-platforms-elevators]]
- Field logic-map — read/decode/validate/edit/add a verbatim fork's `.eb` in place; whole EDIT tier proven → [[project-ff9-field-logic-map]]
- Verbatim authoring set — `[music]` rescore, `[[npc]] opens_shop`/`choice`, multi-actor `[cutscene]` conductor → [[project-ff9-verbatim-music]], [[project-ff9-cutscene-multiactor]]
- FMV pipeline + SPS field-particle authoring → [[project-ff9-fmv-pipeline]], [[project-ff9-sps-authoring]]
- Onboarding + Windows installer — uv-bootstrap `.exe` + `ff9mapkit setup` (detect FF9 → save config → extract → Memoria report; opt-in `--install-engine`) + Steam/GOG auto-detect + the GUI working for installed (.exe/pip/uv) users → [[project-ff9-installer-packaging]]

**Frontier:** #13 (story-event director/roster on rotating-cast fields) — core + tail in-game proven →
[[project-ff9-fork-fidelity-worklist]]. Custom OVERWORLD is now STARTED (no longer "unstarted"): geometry reshape (s34,
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
→ [[project-ff9-overworld-terrain-authoring]]. Remaining overworld frontier: author coastlines FROM SCRATCH (vs real-piece
mosaics); scale to a real CONTINENT (towns+entrances via `world-entrance --building`); texture new geometry (atlas UVs).

**Latest:** kit **1.0.0b9** (public betas b3–b9: PyPI + uv-bootstrap Windows installer + `ff9mapkit setup` + Steam/GOG game-detect + GUI-works-installed; **b7** = installer bundles+installs the engine patches [backed-up/version-aware], installed-GUI campaign/journey deploy + New-Game wiring [`ff9mapkit deploy-campaign`/`deploy-journey`/`newgame`; deploy orchestration extracted into `ff9mapkit/deploy.py`+`newgame.py`, the `tools/deploy_*.py` are now thin shims], Workspace app icon; **b8** = installed Workspace lights up the dev test-slot/F6 loop against a checkout via `$FF9_REPO`/cwd-walk [`jobs.resolve_dev_repo`], installer Finished-page wording fix; **b9** = Workspace UX pass [app-wide combo wheel-guard, destination-aware Revert, campaign-Map legend/tooltips, copy/affordance cleanups] + an opt-in, install-aware update check [version chip + once-a-day PyPI check, `ff9mapkit/update_check.py`]; **b10** = Workspace settings pass — a 7-theme picker [Light/Dark + Nord/Dracula/Solarized Dark/Light/Gruvbox, `editor/theme.py` + `prefs.py`, live preview, persisted], Preferences + About dialogs [⚙ menu], a one-click "Upgrade & restart" for installed copies [detached uv-upgrade helper, `_run_upgrade`/`_UPGRADE_PS1`], light-theme tone-down + installer Finished-page clip fix → [[project-ff9-gui-makeover]]; **b11** = maintenance bump, no functional change [cut to give b10's one-click updater a live target to upgrade to]; **b12** = TWO new pillars — custom 3D **MODELS** [`model-gltf`/`-import`/`-mint`/`-anim` + Blender-authored mesh & animation editing + one-click add-on Import/Export Model, all DLL-free → [[project-ff9-custom-models]]] and custom **OVERWORLD** [`world-terrain`/`-reclaim`/`-coast`/`-entrance`/`-encounters`/texturing/minimap + F6-on-overworld + the s34 engine patch → [[project-ff9-worldmap-feasibility]]]; F6 got a 4-tab redesign + a "Reload + anims" button), 2651 tests (`py -m pytest -n 6`). The install-path features are NOT in-game proven on an installed copy yet (user playtests on the laptop). See `git log` + `[[project-ff9-installer-packaging]]` for the onboarding/installer state.

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
