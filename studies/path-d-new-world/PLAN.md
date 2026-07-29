# Path D — Minting a Genuinely Third FF9 Overworld: Execution Plan

> ## ⚠ EXECUTION UPDATE 2026-07-29 — read this before trusting §3's rung text
>
> **Rungs 0–2's engine work is BUILT AND DEPLOYED** (`s70`/`s71`/`s72`; pre-build DLL backup
> `20260729-153010`), and Rung 2's data half (a verbatim WORLD11 clone shipped as `EVT_WORLD_WORLD13`
> across 7 locales + a `WorldScene 9013 WORLD13` registration) is deployed too. Playtest script:
> [`RUNGS-0-3-PLAYTEST.md`](RUNGS-0-3-PLAYTEST.md).
>
> ### ★ IN-GAME RESULTS 2026-07-29 — rungs 0, 1, 2 ALL PASS
>
> - **Rung 0 ★ PASS.** Warp to unregistered 31000 produced exactly the predicted signature:
>   `KeyNotFoundException` at `Dictionary.get_Item` → `ff9InitStateWorldMap` → `WMScriptDirector.HonoAwake`.
>   The menu accepted the id (the old guard would have refused it), the scene fully tore down and rebuilt,
>   and the failure landed at the dispatcher lookup — informative, not silent.
> - **Rung 2 ★ PASS (owner-confirmed).** `WorldScene 9013 WORLD13` registered at mod-load
>   (`[PathD s72] … (mes 68)`), warping to 9013 loaded a **normal, fully functional disc-1 overworld**
>   running the cloned dispatcher — owner also confirmed the chocobo debug commands worked there. A
>   genuinely new `wldMapNo` outside 9000-9012 both registers AND dispatches.
> - **Rung 1 ★ PASS — THE PIVOTAL UNKNOWN IS ANSWERED: a WorldDisc CAN be minted in C# at runtime.**
>   With the spike armed, `[PathD s71] WorldDisc replaced by a synthetic WorldDisc_SPIKE (480 IsSea blocks)`
>   fired and execution reached `HonoAwake:57` — i.e. **past** `Initialize()` (`:40`) and `OnInitialize()`
>   (`:44`). Zero `WMWorld`/`WorldDisc`/`WMBlock` frames in any trace; zero `|E|` lines in `Memoria.log`.
>   The only exceptions were the expected 31000 miss and 32 instances of one pre-existing, field-side
>   `FieldMapActorController.MovePC` NRE. **§1's "single biggest open risk" and §6 unknown 1 are CLOSED
>   favourably; the §4 fallback (a real third disc + a baked Unity AssetBundle) is NOT needed.**
>
> - **Rung 3 ★★ PASS — A GENUINELY THIRD OVERWORLD EXISTS AND RENDERS.** Spike armed + warp to 9013:
>   `[PathD s71] WorldDisc replaced by a synthetic WorldDisc_SPIKE (480 IsSea blocks)`, then the window
>   titled **`FINAL FANTASY IX - World Map: 9013`** showing a correctly-rendered ocean — sea shader, fog,
>   horizon curvature — with the player standing in it (agent-verified via `tools/game_snap.ps1`, not
>   inferred). Zero `|E|`, zero `WMWorld`/`WMBlock` frames; the only exceptions were the same pre-existing
>   field-side `FieldMapActorController.MovePC` NREs. **Rendering IS the streamer proof**: blocks visible to
>   the horizon means `LoadBlock` ran the grid, `ApplyForm` iterated `Form2Transforms` without NRE, and
>   `DetectUnseenBlocks` resolved a sane window — so all three pre-emptive `s71` fixes are now exercised,
>   not merely written.
> - **⚠ CORRECTION to this document's own Rung 1/3 success criterion:** "`Finished Loading Blocks!` in the
>   log" is **unusable** — plain `Debug.Log` reaches NEITHER `Memoria.log` NOR `output_log.txt` on this
>   install (calibrated: `WMScriptDirector.HonoAwake`'s own `Debug.Log`, which demonstrably ran, is absent
>   from both). `output_log.txt` captures only warnings/errors/exceptions. Judge a world load by
>   `game_snap.ps1` + the absence of exceptions, never by an expected `Debug.Log` line.
> - **Rung 4 ★ PASS (owner-confirmed) — and `blank_world_bytes()` was never written.** In 9013 the player
>   renders, turns, and the **Blue Narciss traverses the synthetic ocean** when enabled from the debug menu.
>   *Not* being able to walk is CORRECT, not a limitation: every cell is `IsSea` and FF9 has never let you
>   walk on ocean on foot. The boat moving is the stronger result — it proves the sea walkmesh and the
>   ground query are valid on runtime-minted geometry, and that the vehicle system works there. **Rungs 0-4
>   are therefore ALL closed.**
> - **★ Rung 4 was PRE-EMPTED by the verbatim route, and `blank_world_bytes()` is not needed.** §3 Rung 4 scopes
>   the player as its own novel sub-step gated on a from-scratch `blank_world_bytes()` ("zero prior art").
>   But a VERBATIM donor clone already carries `DefinePlayerCharacter` — the 9013 world has a rendered
>   player with no byte-splice written. The verbatim-first route makes §5's `blank_world_bytes()` an
>   optimization, not a prerequisite. Remaining Rung 4 question is only whether control/movement behaves.
>
> ⚠ **What Rung 1 alone did NOT prove** (superseded by Rung 3 above, kept for the record). The block
> STREAMER never ran in the Rung 1 test — no `Finished Loading Blocks!`, and
> `Memoria.log` stops at the spike line. Because `HonoAwake` threw, `AddBehavior` never registered
> `WMScriptDirector`, so no world tick fired. (The recon's calibration predicted `LoadBlocks` would run
> regardless of a dispatcher; that assumed the director survives, and it does not.) So `LoadBlock` ×480,
> `DetectUnseenBlocks` and `ApplyForm` are still untested — and therefore so are the three pre-emptive
> fixes in `s71` (`Form2Transforms`, `CurrentX`/`CurrentY`, the mid-grid sentinel parking). **Rung 3 is
> where the streaming half is first exercised; it is load-bearing, not a formality.**
>
> A 6-sweep source verification was run against the live patched clone before any code was written. Most
> of this document held up. These specific claims did **not** — they are corrected here rather than in
> place, so the original reasoning stays readable:
>
> 1. **§3 Rung 1's "no override files exist yet, so `HasLandOverride` always returns false"** — **REFUTED
>    by the live install.** 112 `Terrain.ff9mesh` overrides + `Donor.txt` sidecars already ship in
>    `FF9CustomMap-world` (the Southern Ring's), so 112 of the 480 cells take the s34 reclaim branch. The
>    spike is therefore not the "no per-block prefab lookups" payload this plan prices. Left unsuppressed
>    on purpose: that path is already in-game proven, and an ocean containing only those cells is an
>    unmistakable success picture.
> 2. **§3 Rung 0's "read what happens next in `Memoria.log`"** — **wrong file.** There is no
>    Unity→Memoria log bridge, so plain `Debug.Log` and every Unity exception land only in
>    `x64\FF9_Data\output_log.txt`. New diagnostics must go through `Memoria.Prime.Log` to reach
>    `Memoria.log`. As written, the rung's verify step was unreadable.
> 3. **§3 Rung 0's "set the widened field to any unused id in the 4000-9899 or 30000-32767 bands"** —
>    **produces a false negative.** Any id registered by a stacked `DictionaryPatch` already has an
>    EventDB row, so it yields an `ArgumentNullException` (a field `.eb` loaded down the world path)
>    rather than the clean unregistered-id `KeyNotFoundException`. Use an id registered nowhere (31000).
> 4. **`ArmWorldReload` has TWO undocumented preconditions** — `UIManager.State == WorldHUD` **and**
>    `sys.mode == 3`. Every rung's spike can only be fired while already standing on an overworld.
> 5. **§6 unknown 6 is now closed, and found a throw site this plan never named.** Besides
>    `EventDB[MapNo]`, `ff9ShutdownStateFieldMap` indexes `EventEngineUtils.eventIDToMESID[wldMapNo]`
>    unguarded on the field→world exit — it fires while still in the old field, before the world scene
>    loads. `s72` registers it (default mesID 68, the shared world block). Everything else the plan
>    worried about (minimap, continent title, vehicles, encounter zones, netsync, save schema) either
>    keys off a different variable or fails safe.
> 6. **§3 Rung 1's spike sketch would have crashed for three reasons unrelated to WorldDisc** —
>    `Form2Transforms` is never initialised by `LoadBlock` though `ApplyForm` iterates it;
>    `CurrentX`/`CurrentY` are read by `GetAbsoluteBlock`/`DetectUnseenBlocks` and stock seeds them; and
>    with no player the sentinel actor sits at the world origin, sending `DetectUnseenBlocks` into
>    `Blocks[0,-1]`. All three are fixed in `s71`.
> 7. **§3 Rung 6 and §5 are more pessimistic than the code.** `cmdasm.assemble_block` already builds
>    switches from zero (round-trip verified), so no `eb/switchbuild.py` is needed; `entrance_func_body_
>    direct` emits `Field(dest)` inline, so the exit may need no switch at all; the kit already writes
>    world `.eb` containers into mod folders in three places; and novel `.eb` names with no `p0data`
>    counterpart (`EVT_LAMPLIGHT.eb.bytes`) already ship and resolve. §5's `blank_world_bytes` "zero prior
>    art for the WORLD container shape" is also overstated — the container shape is identical to a field's;
>    what is genuinely novel is the *content* of a minimal world `Main_Init`.
> 8. **Also corrected:** the plan mis-cites `entrance.py:486` as `author_entrance`'s replication loop (it
>    is in `extend_nameplate_band`; the real loop is `:895`). The argument that loop supports is still right.
>
> One deliberate deviation from §3 as written: `s71` is gated behind a **session-only debug-menu toggle**,
> not the `.ini` flag the plan specifies. An `.ini` flag is read at launch, so Rungs 0 and 1 would cost two
> relaunches; a toggle costs one and is off on every launch, which is strictly safer on an install shared
> by ~26 concurrent worktrees.

*Final revision. Synthesizes six parallel first-principles research passes (r1–r6), a prior re-verification
pass, three independent adversarial critiques (feasibility, sequencing, scope-honesty), and a further round
of direct source re-reading performed while incorporating those critiques. Every claim below is tagged:
**[verified]** = read from live source (this pass or a prior one, source unchanged in between);
**[verified this rewrite]** = specifically re-checked while writing this revision, usually because a critic
disputed it; **[per research pass, unverified]** = carried from the original r1–r6 reports and not
independently re-read by any subsequent pass. See §9 for the full list of what this revision changed and
why — read it if you want to know what NOT to trust at face value from an earlier draft of this document.*

---

## 1. Executive summary

Path D requires solving two **independently decoupled** problems: (a) a new **EventDB world-state id** so
a `.eb` dispatcher can run its own script/camera/entrance logic under a new `wldMapNo`, and (b) **new
block-grid geometry** for that dispatcher to render on. Problem (a) is cheap and precedented — the
`FieldScene`/`BattleScene` directives in `DataPatchers.cs:497-548` **[verified]** are the exact template,
and the engine's own *dispatch* path (`ff9InitStateWorldMap`, `WMAPJUMP`/`SetNextMap`) has no range check
on `wldMapNo` outside 9000–9012. **That last claim needs a correction the draft of this plan got wrong**:
it is true of the engine's dispatch logic, but it is **false of this project's own debug-menu tooling** —
`Ff9mkDebugMenu.ForceWorldState` hard-rejects any id outside 9000–9012 **[verified this rewrite,
`Ff9mkDebugMenu.cs:1403-1405`]**, and the only other candidate debug route, `WMBeeMenu`'s "Jump To," is not
a dispatcher switch at all — it's a same-world position teleport gated on `ff9.w_frameDisc == 1`
**[verified this rewrite, `WMBeeMenu.cs:153`, opens `showSetPositionMenu`]**. Concretely: as the project's
tooling stands today, **there is no way to observe a new `wldMapNo` in-game at all**, independent of
whether the harder geometry problem is solvable. This is why Rung 0 below is not the WorldDisc question —
it's fixing that.

Problem (b) — new geometry — is the hard part. The 480-cell `WMBlock` topology lives on a single
serialized `Transform WorldDisc` field (`WMWorld.cs:2033`, **[per research pass, unverified this
rewrite]**) baked into the **one** Unity scene the whole game shares for both existing discs (every
world-map entry point calls `SceneDirector.Replace("WorldMap", ...)` verbatim — `HonoluluFieldMain.cs:338`,
`EventEngine.Initialize.cs:68`, `WMScriptDirector.cs:228`, `BattleResultUI.cs:54`, **[verified, prior
pass]** — there is no per-disc scene). **The single biggest open risk is whether a brand-new 480-`WMBlock`
hierarchy can be constructed purely at runtime in C# and substituted for that one `WorldDisc` field before
`WMWorld.Initialize()`/`OnInitialize()` walk it.** Direct source reading found genuinely encouraging
signal: `WMBlock`'s `InitialX`/`InitialY`/`IsSea` fields are plain public fields with zero attribute
restriction **[verified this rewrite, `WMBlock.cs:243-259`]**; `WorldDisc` is referenced at exactly four
call sites, all inside `WMWorld.cs` (`:105`, `:139`, `:449`, `:470`) **[verified this rewrite by a
whole-tree grep]**; and per-block **world position is computed from `InitialX`/`InitialY` at
`OnInitialize()` time, not baked** (`WMWorld.cs:449-458`: `position.x = j * 16384 * 0.00390625f; ...
wmblock.transform.position = position;`) **[verified this rewrite]**. But it is **unproven in-game**, and
— a correction this revision makes explicit — **there is no incremental on-ramp to that proof**:
`OnInitialize()`'s position-write loop iterates the full 24×20 grid with **no null guard**
(`WMWorld.cs:449-458`, confirmed no `if (wmblock == null) continue`), so the very first successful pass
through `Initialize()`/`OnInitialize()` already requires a complete, gap-free 480-cell array — not "one
block." A stray non-`WMBlock` child parented under a synthetic root is an even earlier landmine: the
gap-filling scan in `BuildBlockArray` calls `transform.GetComponent<WMBlock>()` on **every** child with **no
null check before dereferencing** `component.InitialX` (`WMWorld.cs:1673-1688`, `if (component.InitialX ==
i && ...)`) **[verified this rewrite]** — one wrong child throws before `OnInitialize()` is even reached.

Nothing in this plan should be built past Rung 1 until the WorldDisc question is answered, and nothing
should be attempted at all until Rung 0 makes the answer *observable*. Set honest pacing expectations
before committing to this plan: see §7's pacing note. This is unprecedented territory inside this
codebase — no stock reference shape exists for a synthetic runtime-built `WorldDisc` — and this project's
own nearest analogue (the scene-ladder, a strictly *narrower* problem that reused existing geometry
throughout) still took on the order of 18–20 discrete playtest-and-relaunch rounds to close.

## 2. The core question this plan must answer first

**State axis (decoupled, independently confirmed, not in dispute):** `ff9InitStateWorldMap(MapNo)`
(`ff9.cs:9293-9312`, **[verified, prior pass]**) never reads `currentDisc`/`w_frameDisc`;
`WorldConfiguration.GetDisc()` (`WorldConfiguration.cs:234-241`, **[verified, prior pass]**) never reads
`wldMapNo`. A new dispatcher id and new geometry are genuinely separable engineering problems and can be
built/verified as two independent rungs before being combined.

**Geometry axis (genuinely uncertain, leaning codeable):** `WMBlock`'s state fields are ordinary
assignable fields, `WorldDisc`'s blast radius is four call sites all in one file, and per-block position is
computed rather than baked (all **[verified this rewrite]**, cited above). The project's own s34-era
comment at `WMWorld.cs:2069-2074` (**[per research pass, unverified this rewrite]**, quoted: *"WMWorld is a
MonoBehaviour baked into the pre-built WorldDisc prefab; adding a SERIALIZED (public) field shifts its
serialization layout, so the baked component deserializes corrupt"*) documents a **different** risk class
— adding a new C# *field to the `WMWorld` class itself*, which changes what Unity expects to deserialize
from the *existing* baked component's byte stream. **Assigning a new value into the existing `public
Transform WorldDisc` field at runtime does not touch that class layout at all.** This distinction matters
and was not drawn by the original six-agent research; it moves the needle toward "codeable" without
closing the question. `Wrap()` (`WMWorld.cs:1077-1110`, **[verified this rewrite]**) — the torus-shift loop
`OnInitialize()` spins in — early-returns `true` whenever `ff9.w_moveActorPtr` is `null` or the dummy
character, both true before any `.eb` code runs on a fresh world, so a hang here is unlikely but **not
proven** safe.

**Verdict, unchanged from the prior pass: genuinely uncertain, leaning codeable, and it is the first thing
to resolve — not because research disagreed irreconcilably, but because the fastest way to close the gap is
an in-game spike, not more reading.** What changes in this revision is the recognition that **the spike
itself cannot be observed with the project's current tooling**, so the true first rung is smaller than
"build the spike" — it's "make the spike observable at all." See Rung 0.

## 3. Rung-by-rung build sequence

Seven rungs, renumbered from earlier drafts of this plan specifically to fix a sequencing defect an
adversarial critique caught: the original Rung 0 named two "cheap verify" routes that are both broken as
built, and the original Rung 2 bundled three separately-novel, previously-untested mechanisms (WorldDisc
substitution, a new EventDB dispatcher id, and a from-scratch `blank_world_bytes()` byte-splice) behind one
atomic pass/fail check. Every rung below changes exactly one variable relative to the rung before it, per
this project's own house style (the scene-ladder).

### Rung 0 — THE REACHABILITY SPIKE

**Goal:** prove a brand-new/unused `wldMapNo` can be set and the WorldMap scene reload observed at all,
with zero new geometry and zero new EventDB entry — pure plumbing, and a hard prerequisite for every rung
after it.

**Why this has to come first (a correction, not a nicety):** the draft of this plan assumed two existing
debug routes could reach a new dispatcher id. Neither works. `ForceWorldState` — the *only* UI control that
sets `FF9.wldMapNo` and reloads the WorldMap scene onto a chosen dispatcher (wired from the World-tab text
field, `Ff9mkDebugMenu.cs:1138-1140`, and the fixed buttons at `:1143-1146`) — hard-rejects anything outside
9000–9012: `if (!Int32.TryParse(text.Trim(), out Int32 id) || id < 9000 || id > 9012) { _status = "reload
world: need an id 9000-9012"; return; }` (`Ff9mkDebugMenu.cs:1403-1405`, **[verified this rewrite]**). The
draft's proposed alternative, `WMBeeMenu`'s "Jump To" (`:153`, gated on `ff9.w_frameDisc == 1`), is not a
dispatcher switch — it toggles `showSetPositionMenu`, a same-world *position* teleport with a handful of
hardcoded named destinations (`:203-241`, "Go to Dhali," "Go to Lindblum," etc.) **[verified this
rewrite]**. Neither route can select a new `wldMapNo`. Without fixing this first, Rung 1's own success
signal is unobservable — exactly the "rung whose success can't actually be checked without something from a
later rung" failure pattern this plan must avoid.

**Files touched:** `memoria-patches/s70-debug-menu-reach-widen.patch` — a one-line widen of
`ForceWorldState`'s range guard (or, more conservatively, a second debug-only text field with no range
check, leaving the existing 9000–9012 control untouched for normal use). Low-risk, debug-tool-only code;
worth keeping permanently rather than treating as throwaway, since every later rung needs it too.

**Already proven-safe:** the `ArmWorldReload`/`ForceWorldState` mechanism itself is the *faithful* full
scene-teardown-and-rebuild path (`Ff9mkDebugMenu.cs:1388-1422`, sets `wldMapNo`, `nextMode=3`,
`attr|=0x1000`, defers to the game tick) — already used and working for all 13 real states; only its range
guard is new.

**Genuinely new/risky:** nothing engineering-wise. The only real risk is scope creep — do not use this
rung to also test EventDB registration (that's Rung 2) or WorldDisc substitution (Rung 1).

**Cheap verify:** deploy, set the widened field to any currently-unused id in the 4000-9899 or 30000-32767
scratch bands (**no new EventDB entry needed** — the point is only to confirm the scene-reload mechanism
fires and to read what happens next in `Memoria.log`). **Success:** the scene reload triggers and fails
*informatively* — e.g. an `EventDB` miss or a null-`WorldDisc` log line — rather than being silently
refused at the menu layer. **Failure:** the menu still refuses, or the game hard-crashes with no log
output at all (would mean something else gates `wldMapNo` that this plan hasn't found — see §6 unknown 6).

### Rung 1 — THE WORLDDISC SPIKE (unpeopled, dispatcher-free)

**Goal:** prove or disprove that a brand-new 480-`WMBlock` hierarchy, built purely in C# at runtime, can be
substituted for `WMWorld.WorldDisc` and survive `Initialize()`/`OnInitialize()`/`Wrap()`/the shift
machinery — **with the smallest possible payload that can answer this**, per the scope-honesty critique
that caught the earlier draft's Rung 2 conflating this with two other untested mechanisms.

**The true minimum, corrected from an earlier draft of this plan:** the task's naive floor ("one flat
block renders and the player can stand on it") is **not achievable as stated** — the no-null-guard
480-cell loop above means there is no incremental on-ramp; day one already needs the complete grid. Given
that hard floor, the actual minimum viable payload is: **480 `WMBlock` stubs, ALL `IsSea = true`, zero
`.ff9mesh` overrides authored anywhere, no new EventDB id, no `DefinePlayerCharacter`, no player at all.**
With every cell `IsSea`, every cell resolves through the *already in-game-proven* s34 reclaim/sea branch
straight to the stock `SeaBlockPrefab` (`WMWorld.cs:495-507`, `LoadBlock`'s `if (block.IsSea) { if
(this.LandDonorPrefab != null && WorldMeshOverride.HasLandOverride(...)) ... else this.LoadBlock(this.
SeaBlockPrefab, block); }` — since no override files exist yet, `HasLandOverride` always returns false, so
this always takes the plain `SeaBlockPrefab` path) — **no per-block prefab lookups, no override authoring,
no sentinel-namespace question at all** at this rung (see Rung 5 for why that question is deferred, not
skipped). Reached via a **debug hook gated behind a flag that defaults OFF** — this revision explicitly
drops the earlier draft's "fire unconditionally on the very next WorldMap load" fallback, because with
18+ concurrent agent worktrees sharing one game install and one mod-folder set (CLAUDE.md §3/§5), an
unconditional substitution would corrupt real disc-1/4 play for every other concurrent session until
reverted — a real blast-radius risk the earlier draft's "S / one throwaway patch" sizing did not price in.

**Files touched:** `memoria-patches/s71-worlddisc-runtime-spike.patch`, modeled on this project's own
precedent for disposable diagnostics (`s63-world-scene-probe.patch`, `s67-rig-probe.patch` — both removed
after answering their question, per house style **[per research pass, unverified this rewrite — the
README entries exist but were not read in full this pass]**). Hook: a static helper called at the top of
`WMWorld.Initialize()`, before `:105`'s `BuildBlockArray` call, gated behind an `.ini` flag that is OFF by
default. It should:
1. Create `GameObject("WorldDisc_SPIKE").transform`, parented the same way `Initialize()` already parents
   `TranslatingObjectsGroup` (`GameObject.Find("WorldMapRoot")`, `WMWorld.cs:99-102`).
2. Loop `x in 0..23, y in 0..19` and, for **every** cell, `AddComponent<WMBlock>()` a child with **nothing
   else parented under the root** (the `BuildBlockArray` null-check gap above means a stray sibling object
   is a guaranteed NRE, not a maybe). Set `InitialX=x`, `InitialY=y`, `IsSea=true`.
3. Assign `world.WorldDisc = thatTransform` before returning.

**Already proven-safe:** the reclaim/sea-prefab path this spike deliberately routes into is the
already-in-game-proven s34 mechanism, not new code; `WMBlock`'s fields are plain assignable
(`WMBlock.cs:243-259`, verified); `WorldDisc`'s four call sites are fully enumerated (verified).

**Genuinely new/risky, correctly enumerated:**
- A crash inside `OnInitialize()`'s position-write loop — should not happen with all 480 cells present and
  no gaps.
- An NRE inside `BuildBlockArray` from a stray non-`WMBlock` child — mitigated by construction (step 2
  above), but this is a real, previously-uncited landmine (`WMWorld.cs:1673-1688`, no null check on
  `transform.GetComponent<WMBlock>()`).
- A hang or misbehavior in `Wrap()`'s loop — analysis says unlikely (early-exits on null/dummy actor) but
  is inference, not proof, since there is no player to actually move.
- Misbehavior in the ~15 raw-literal torus-wrap sites across the four `ShiftXAllBlocks` variants
  (**[per research pass, unverified this rewrite]**) on a totally synthetic array — should be agnostic to
  block provenance but untested.
- **A partial, non-crashing misbehavior is the likelier and more expensive failure mode than a clean
  crash**, per the scope-honesty critique — there is no stock reference shape to triangulate against here,
  unlike every rung of the scene-ladder precedent, which could always ask "what would the stock rig do."

**Cheap verify:** using Rung 0's now-working reach mechanism, warp to an id whose EventDB entry does NOT
yet exist (Rung 1 deliberately has no dispatcher) with the spike flag ON. **Success:** no NRE inside
`WMWorld`'s `Initialize`/`OnInitialize`/`OnUpdateLoading` in `Memoria.log`, and the load either completes
(possibly to a blank/black screen since there's still no dispatcher to run — that's expected) or fails at
the *dispatcher* lookup stage specifically, not inside `WMWorld`. **Failure:** any NRE inside the functions
above, or a hang. **On failure:** do not attempt further engineering on the "swap WorldDisc" architecture —
fall back to §7's heavier "real third disc" path (needs a baked Unity asset the toolkit cannot currently
author — see §6 unknown 2). Remove or re-gate the spike patch once the answer is in hand.

### Rung 2 — THE EVENTDB DIRECTIVE (state axis, verbatim-first, existing geometry)

**Goal:** independently of Rung 1's outcome, prove the state-axis claim in-game: register a genuinely new
`wldMapNo` (e.g. 9013 — reserving the naming pattern `WORLDNN` for reasons covered below) whose `.eb`
dispatcher actually runs, landing on the **existing, real** disc-1 `WorldDisc` — no synthetic geometry
here at all. This isolates the state-axis question from the geometry question completely, and — a
correction from the draft, per this project's own "incremental verbatim-first" house rule — it does **not**
introduce a brand-new, never-before-tested `blank_world_bytes()` byte-splice in the same step. Clone an
**existing real dispatcher's bytes verbatim** (e.g. `WORLD11`, already proven editable by the scene-ladder
study's own `rung3c_origin_departure.py`) and remap only its EventDB registration, exactly the way a field
fork remaps only `Field()` calls.

**Files touched:**
- Engine: `memoria-patches/s72-worldscene-directive.patch` — a new `DataPatchers.cs` branch modeled on
  `FieldScene`/`BattleScene` (`DataPatchers.cs:497-548`, **[verified, prior pass]**):
  ```csharp
  else if (String.Equals(entry[0], "WorldScene") && entry.Length >= 3)
  {
      // eg.: WorldScene 9013 WORLD13
      if (FF9DBAll.EventDB == null) continue;
      Int32 ID;
      if (!Int32.TryParse(entry[1], out ID)) continue;
      FF9DBAll.EventDB[ID] = "EVT_WORLD_" + entry[2];
  }
  ```
  `FF9DBAll.EventDB` is a plain `Dictionary<Int32,String>` (`FF9DBAll.Events.cs:7`, **[verified, prior
  pass]**), already runtime-mutated by two sibling directives — genuinely a copy-paste, low risk.
  **Naming correction from the draft:** the earlier worked example used a container name
  `EVT_WORLD_CUSTOM_WORLD`. That does not match the kit's own dispatcher-recognition pattern,
  `_WORLD_RE = re.compile(r"eventbinary/world/([a-z]{2})/(evt_world_world\d+)\.eb")` (`entrance.py:84`,
  **[verified this rewrite]**) — it requires literally `world` followed by digits. **Name the new
  dispatcher `WORLD13`** (i.e. ship `EVT_WORLD_WORLD13.eb.bytes`) purely so any later kit tooling that
  pattern-matches by name has a chance of recognizing it; see the honest limitation below for why this
  alone does not make it *discoverable*.
- Kit: **no `entrance.py` change is needed to REGISTER this dispatcher** (the directive above is
  sufficient), but a load-bearing limitation the draft's "entrance.py needs no change" claim
  overlooked: `load_all_dispatchers` / `load_world_dispatchers` (`entrance.py:87-126`, **[verified this
  rewrite]**) source **exclusively from `StreamingAssets/p0data*.bin`** via UnityPy — the pristine,
  unmodified base-game asset bundles (`entrance.py:97-120`: `sa = config.find_game_path(game) /
  "StreamingAssets"; for p in glob.glob(str(sa / "p0data*.bin")): env = UnityPy.load(p) ...`). A
  brand-new custom dispatcher's bytes are **never** inside `p0data*.bin` — this function structurally
  cannot discover it, regardless of filename. This matters for Rung 6, not this rung (Rung 2 reaches the
  new dispatcher via Rung 0's debug hook, not via `entrance.py` discovery at all) — flagged here so the
  limitation is visible before it's assumed away later.

**Already proven-safe:** the `.eb` container format itself is disc/world-agnostic; cloning a real
dispatcher's bytes verbatim and remapping only its registration is the same pattern this project already
uses for field forks.

**Genuinely new/risky:** the `WorldScene` directive itself is new engine code (small, low-risk, but
untested); whether any **other** hardcoded table besides `EventDB` silently assumes exactly the 13 known
`wldMapNo` values is unresolved (§6 unknown 6).

**Cheap verify:** deploy, use Rung 0's reach mechanism to warp to 9013. **Success:** the screen loads on the
**existing disc-1 geometry** (this rung touches no `WorldDisc` state) running the cloned dispatcher's
`Main_Init` — confirm via a `Log.Message` inserted into the cloned entry, or a visibly-different starting
position if the clone's spawn was edited. **Failure:** an immediate crash on warp, or a silent fallback to
a real dispatcher — either would falsify the "EventDB has no range check" claim and needs its own
investigation before Rung 3.

### Rung 3 — THE MINIMAL THIRD WORLD, UNPEOPLED (combine Rungs 1 + 2)

**Goal:** the first genuine Path D artifact — dispatcher 9013 (Rung 2's mechanism, now pointed at a fresh
world-specific `.eb` rather than a clone) running against Rung 1's synthetic, all-sea 480-block
`WorldDisc` — **still no player, still no `blank_world_bytes()`.** This isolates "does the combination
work" from "can I stand in it," per the scope-honesty critique's explicit recommendation to split what an
earlier draft called Rung 2 into an unpeopled proof and a peopled one.

**Files touched:** `memoria-patches/s73-third-worlddisc-wire.patch` — promotes Rung 1's spike from a
debug-flag trigger to a real, permanent hook keyed on `wldMapNo == 9013` (or whatever id/band this project
reserves for Path-D worlds), checked at the top of `WMWorld.Initialize()`. **Design decision made HERE,
not earlier:** keep `currentDisc`/`w_frameDisc` at 1 throughout (so every asset-dressing consumer
downstream of `GetDisc()` keeps working unmodified — see §7's earlier fallback risk this sidesteps). Since
Rung 3's world is still all-sea with zero `.ff9mesh` overrides authored, **the sentinel-disc-namespace
question does not need solving at this rung at all** — it only matters once real per-cell overrides exist
(Rung 5). This is a genuine simplification this revision makes over the earlier draft, which bundled the
sentinel-disc design into the same rung as "does the world exist" for no necessary reason.

**Already proven-safe:** Rung 1 and Rung 2's mechanisms individually verified; combining them changes only
which dispatcher id triggers which WorldDisc substitution — no new C# logic beyond the `wldMapNo` gate.

**Genuinely new/risky:** the interaction between the two mechanisms is itself untested — e.g. whether
`WMScriptDirector`'s dispatcher-selection timing relative to `WMWorld.Initialize()`'s WorldDisc-substitution
timing holds up when both fire together (each was previously tested with the other side unmodified).

**Cheap verify:** deploy, warp to 9013 via Rung 0's mechanism. **Success:** the scene loads a 480-cell
all-ocean field distinct from real disc 1/4 (trivially distinguishable — there is no land anywhere), no
NRE, no hang, and `Memoria.log` confirms the new `.eb` executed. Nothing to walk on yet is expected and
fine. **Failure:** any crash — diagnose whether it's a Rung 1 regression (WorldDisc-specific) or a Rung
2 regression (dispatcher-specific) by testing each mechanism alone again before combining.

### Rung 4 — THE FIRST WALKABLE THIRD WORLD (layer in a player)

**Goal:** the first rung where a human can actually stand on Path D geometry — layer `DefinePlayerCharacter`
and a minimal `Main_Init` onto Rung 3's confirmed-clean combination.

**Files touched:**
- Kit: `ff9mapkit/ff9mapkit/data/__init__.py` needs a new `blank_world_bytes()` sibling to the existing
  `blank_field_bytes()` (`data/__init__.py:32`, **[verified this rewrite]** — confirmed no world
  counterpart exists anywhere in the kit). Cheapest instantiation: clone the smallest real free-roam donor
  and strip it to a minimal `Main_Init` (arm one `InitObject`'d avatar entry that calls
  `DefinePlayerCharacter`, sets `Map.Byte[24]=100`, `RET`) using the kit's own `eb/edit.py`/`eb/cmdasm.py`
  primitives. **This byte-splice has zero prior art for the WORLD container shape** — `blank_field_bytes`'s
  own docstring calls itself "the proven minimal playable field," language implying real iteration was
  needed to land on a `Main_Init` that behaves correctly; there is no basis to assume the WORLD equivalent
  lands clean on the first try just because the *mechanism* (clone a donor, strip to a skeleton) is
  precedented in the FIELD domain. Treat this as its own genuinely novel sub-step, verified standalone
  (does it parse? does `Main_Init` run without crashing when loaded via Rung 2's mechanism on the
  *existing* disc-1 geometry, before ever combining with Rung 1/3's synthetic WorldDisc?) before folding it
  into the full stack.
- Engine: none beyond what Rungs 0-3 already shipped.

**A correction on `DefinePlayerCharacter` (opcode `0x2C`) an earlier draft oversimplified:** it is not "a
one-line `controlUID` write." The actual handler (`EventEngine.DoEventCode.cs:1033-1045`, **[verified this
rewrite]**) does: an `getActiveActorByUID(this._context.controlUID)` lookup with a conditional mutation of
a *different* actor's `fieldMapActorController.isPlayer`/`gameObject.name` (`:1035-1040`, guarded
conditions not fully enumerated here), and a conditional `SmoothFrameUpdater_World.Skip = 1` write when
`gMode==3` and the controlUID is changing (`:1041-1042`), **before** the final `this._context.controlUID =
this.gExec.uid; return 0;` (`:1043-1044`) that actually establishes free-roam control. On a freshly-built
world with no prior actor state, these conditional branches may behave differently than they do on a real
field/world load — this is a new, previously-unflagged item to watch during this rung's verify (look for
anomalies in camera/control smoothness, not just crashes).

**Already proven-safe:** the `.eb` container format is world-agnostic (Rung 2 already proved a cloned
container runs); `DefinePlayerCharacter`'s core effect (establishing free-roam control) is well-precedented
even though its full logic is more involved than previously stated.

**Genuinely new/risky:** `blank_world_bytes()` itself (no prior art, see above); the `DefinePlayerCharacter`
edge-case branches on a synthetic actor/world state (above); whether the minimal `Main_Init` needs anything
beyond `InitObject`+`DefinePlayerCharacter`+`Map.Byte[24]=100`+`RET` to avoid a stuck/frozen player (e.g.
camera init — per Rung 1b's carried claim that no separate camera-init opcode exists and the free-roam
camera derives from `w_cameraUpdate` automatically, **[per research pass, unverified this rewrite]**, worth
confirming empirically here rather than trusting outright).

**Cheap verify:** first verify `blank_world_bytes()` standalone by loading it via Rung 2's mechanism on
**real disc-1 geometry** (isolating the byte-splice from the WorldDisc substitution). Only once that's
clean, combine with Rung 3's synthetic WorldDisc and warp to 9013. **Success:** the player spawns on the
480-cell all-ocean field, has working free-roam control (camera follows, movement responds), and does not
fall through the world or trigger the "no controlled actor" self-heal (`s39-world-selfheal-control.patch`,
**[per research pass, unverified this rewrite]** — its own documented TODO flags a degenerate fallback
position "may be sea," worth spot-checking). **This is the milestone that actually proves Path D is real**
— everything before it is infrastructure; everything after it is design/polish.

### Rung 5 — SHAPE THE GRID (real geometry, not just all-sea)

**Goal:** move past "480 identical sea cells" to intentionally designed land — reuse the kit's already
generalized `world/terrain.py`, `world/island.py`, `world/coastmorph.py` etc. This is also where the
sentinel-disc-namespace question, deliberately deferred from Rung 3, finally has to be answered — because
this is the first rung that authors real per-cell `.ff9mesh` overrides.

**The sentinel-disc-namespace fork, correctly scoped this time.** An earlier draft of this plan scoped
this as "extend `Memoria.World.WorldMeshOverride`'s per-cell key" — **that framing is wrong and was caught
by adversarial review.** `WorldMeshOverride.cs` (all of it, `:1-223`, **[verified this rewrite, full
file]**) already takes an arbitrary `Int32 disc` parameter everywhere — `HasLandOverride(Int32 disc, ...)`,
`TryReadDonorPath(Int32 disc, ...)`, `TryLoadTexture(Int32 disc, ...)` all format `disc` generically into a
lookup path with zero `{1,4}` restriction. **It needs no engine change at all.** The actual hardcode lives
in the **callers**, inside `WMWorld.cs`, and this revision enumerates them precisely (re-grepped this
pass, superseding two critics' slightly different partial enumerations):
- `LoadBlock(Int32 disc, WMBlock block)` itself takes a `disc` parameter and threads it correctly
  (`:490-515`) — not a problem site itself, but its one hardcoded caller at `:547`
  (`ForceLoadBlockReadyAt`, `this.LoadBlock(this.currentDisc, block)`) is.
- `RegisterBlockComponent(WMBlock block, Transform transform, ...)` — **has no `disc` parameter in its
  signature at all** and reaches directly for `this.currentDisc` twice, inline, inside its own format
  strings: the mesh-override lookup (`:786-788`) and the texture-override lookup (`:798-799`).
- `RegisterBareObjectOverride(WMBlock block, Transform template)` — same shape, **no `disc` parameter**,
  hardcodes `this.currentDisc` at `:833-835`.
- The `LoadBlocks` streaming loop (`:1187`, `:1193`, both `this.LoadBlock(this.currentDisc, wmblock)`).
- The async block-reload path (`UpdateLoadBlocks`, `:1256-1257`:
  `WorldMeshOverride.HasLandOverride(this.currentDisc, ...)` and
  `this.LoadBlock(this.ResolveReclaimDonor(this.currentDisc, ...), wmblock)`) and `LoadBlockAsync`
  (`:1264`, `this.LoadBlockAsync(this.currentDisc, wmblock)`).

That's at least nine distinct sites across five methods, two of which (`RegisterBlockComponent`,
`RegisterBareObjectOverride`) need a **new parameter added to their signature**, not just an argument
swap — a materially larger and more scattered patch than "extend the per-cell key" implied. **Design:**
add one new private field to `WMWorld`, e.g. `private Int32 overrideDiscTag = -1;`, defaulting to mirror
`currentDisc` for real disc-1/4 loads and set to a reserved sentinel (e.g. `9`, never 1 or 4) only when
`WMWorld` is running a Rung-3-style synthetic WorldDisc; thread `overrideDiscTag` through the nine sites
above **instead of** `this.currentDisc` for override lookups specifically, while leaving `this.currentDisc`
itself untouched everywhere else (so `GetDisc()`/vehicle-asset loading/etc. are unaffected — deliberately
avoiding the `{1,4}`-domain risk surface the heavier fallback path would otherwise touch). This avoids a
real collision risk this project's own tracing surfaced: without a sentinel, a Path-D cell at grid coord
(5,5) would share its override file path with a real Southern-Ring edit to disc-1 block (5,5).

**Files touched:** `memoria-patches/s74-sentinel-disc-override-namespace.patch` (engine, the nine-site
thread above); kit — `world/terrain.reshape/coast/reclaim`, `world/island.landmass`, `world/coastmorph.*`
(all confirmed open over a generic `disc:int` parameter per the prior pass's census — **[per research
pass, unverified this rewrite]** — forward the sentinel value the same as any other int, no kit-side
engine-facing change needed if the sentinel design above holds).

**Genuinely new/risky:** the sentinel-namespace fork itself (now correctly scoped, still untested);
`texgates.py`'s acceptance thresholds were empirically calibrated **only** against disc-1 stock ground
samples (**[per research pass, unverified this rewrite]**, citing
`studies/overworld-topography/out/foldback/texgates_calibration_raw.json`) — untested whether they
generalize to a stylistically new world's synthesized geometry; treat as a real, separate calibration risk.

**Cheap verify:** offline first — `ff9mapkit walkmesh verify`-class checks plus the kit's own offline
placement simulator against the newly-authored `.ff9mesh` files, before ever deploying; then in-game via
`game_snap.ps1` capture, per the coast-work house law (`project-ff9-overworld-coast-mosaic` — applies here
unchanged).

### Rung 6 — ENTRANCE / EXIT (connect it to the rest of the game)

**Goal:** a real field can `WMAPJUMP` into 9013, and 9013 can `Field()` back out to a real field.

**A scope gap an adversarial critique caught, re-examined this pass with a more specific finding than the
critique itself offered:** the earlier draft assumed `entrance.py`'s `author_entrance` machinery
(`entrance.py:731-1039`, **[per research pass, unverified this rewrite]**) is "already proven generic over
any discovered dispatcher" and only needs a narrow "build a switch from zero" helper. Direct re-reading
shows this is optimistic for a different reason than initially framed: `author_entrance`'s core purpose is
replicating one entrance trigger function across **all 13 real dispatchers** (`entrance.py:11-16`'s own
docstring: *"There are 13 dispatchers (EVT_WORLD_WORLD00..12) selected by entry/story state ... this
covers them all"*, **[verified this rewrite]**) so a location reachable from multiple story-states stays
reachable in every one of them. **A single custom Path-D dispatcher does not have that problem** — it is
not story-state-varying, so `author_entrance`'s 13-way replication loop (`entrance.py:486`, iterating
`alld` from `load_all_dispatchers`, which — per Rung 2's finding above — can never see our custom
dispatcher anyway) is very likely **not the tool this rung needs at all**, rather than a tool that needs
generalizing. What Rung 6 concretely needs instead:
1. **The field-side half** (real field → `WMAPJUMP` opcode `0xB6` into 9013) — ordinary, well-precedented
   field-authoring work (`authoring-ff9-field-scripts` skill), independent of `entrance.py` entirely.
2. **The world-side half** (9013's own exit switch, dispatching `Field(dest)` for one or more real
   destinations) — this is where the draft's already-named, genuinely-scoped gap actually lives:
   `eb/edit.py`'s `find_switch`/`repoint_switch_case` (`edit.py:383-455`, **[per research pass, unverified
   this rewrite]**) only edit an **existing** switch; 9013's own `.eb` (from Rung 4's `blank_world_bytes()`
   + Main_Init) has no switch at all yet, and must be **hand-assembled from zero** via
   `cmdasm.assemble_block` (mechanically capable per prior research, but no reusable "build a switch from
   zero cases" helper exists today — build one here, or accept a single hardcoded exit for day one).

`entrance_func_body(case, *, game=None, dispatchers=None)` (`entrance.py:360-369`, **[verified this
rewrite]**) does accept a caller-supplied `dispatchers` dict and always pulls its *template* from
`disp["evt_world_world00"]` regardless of what else is in that dict — a real, existing key it never has to
find our custom dispatcher to use. This is a plausible mitigation angle worth testing (it means the trigger
**function body** itself could in principle be reused for our own switch's arms without needing
`author_entrance`'s discovery/replication loop at all) — but it is **not proven**; treat it as this rung's
own small sub-spike, not an assumption.

**Files touched:** field-side gateway authoring (existing skill); a new "assemble a switch from zero" kit
helper, either in `eb/edit.py` or a new `eb/switchbuild.py`.

**Cheap verify:** enter 9013 from a real field via a normal gateway, walk to the exit trigger, confirm
landing back on a real field with story state intact (this also re-tests, in the cheapest possible way,
whether the state axis is reachable via a *normal play* route rather than only a mid-game debug warp).

## 4. Engine patch inventory

Following the project's own `sNN-<slug>.patch` convention; next free number confirmed this pass (highest
existing file is `s69-minimap-visible-state.patch` **[verified this rewrite]**), so this plan starts at
**s70**.

| Patch | Rung | Scope |
|---|---|---|
| `s70-debug-menu-reach-widen.patch` | 0 | Widens `Ff9mkDebugMenu.ForceWorldState`'s hardcoded `9000-9012` range guard (or adds a second, unrestricted debug field) so a new `wldMapNo` can be reached and observed at all. Low-risk, debug-tool-only; worth keeping permanently, not throwaway. |
| `s71-worlddisc-runtime-spike.patch` | 1 | THROWAWAY (remove/re-gate after Rung 1 closes, per the `s63`/`s67` precedent): builds a synthetic all-`IsSea` 480-`WMBlock` `Transform` and swaps it into `WMWorld.WorldDisc` before `Initialize()`'s first `BuildBlockArray` call. Gated behind an `.ini` flag that defaults OFF — never fires unconditionally (a correction from an earlier draft, which risked corrupting the shared install for concurrent sessions). |
| `s72-worldscene-directive.patch` | 2 | New `DataPatchers.cs` `"WorldScene"` directive — the `FieldScene`/`BattleScene` sibling — writes `FF9DBAll.EventDB[ID] = "EVT_WORLD_" + name` at mod-load time. Verified first against a **verbatim clone of a real dispatcher's bytes**, not a from-scratch splice. |
| `s73-third-worlddisc-wire.patch` | 3 | Promotes `s71` from debug-spike to permanent: on `wldMapNo == 9013`, builds/caches the real 480-`WMBlock` hierarchy and assigns it to `WMWorld.WorldDisc`, keeping `currentDisc`/`w_frameDisc` at 1 throughout. No override-namespace work yet (Rung 3's world is still all-sea, zero `.ff9mesh` overrides). |
| `s74-sentinel-disc-override-namespace.patch` | 5 | Threads a new `overrideDiscTag` field through the nine `WMWorld.cs` call sites enumerated in Rung 5 (two of which — `RegisterBlockComponent`, `RegisterBareObjectOverride` — need a new method parameter, not just an argument swap) so Path-D cell overrides never collide with real disc-1/4 override paths. `WorldMeshOverride.cs` itself needs **zero** change — confirmed generic over `disc` in full this pass. |
| *(deferred, only if Rung 1 fails)* `sNN-real-third-disc.patch` | — | Heavier fallback: widen `WorldConfiguration.GetDisc()`'s ternary and `WMWorld.SetDisc`'s `{1,4}` gate (`:1665-1671`, **[verified this rewrite]**) to a real third disc value, plus a new file-system branch in `w_fileSystemConstructor` (**[per research pass, unverified this rewrite]**, `ff9.cs:3621-3644`) — **blocked on producing a real baked `WorldMap/Prefabs/WorldDiscN/...` Unity asset**, which needs Unity-Editor/AssetBundle authoring the kit does not currently have (§6 unknown 2). Do not start until Rung 1 has definitively failed. |

Encounters, minimap, continent banners, and vehicles are **explicitly out of scope** for this inventory —
see §8.

## 5. Kit work inventory

**Already generalizes, zero change needed** — verified this rewrite for `entrance.py`'s registration path
(no change needed to *register* a dispatcher via the `WorldScene` directive, though its *discovery*
function has the p0data-only limitation noted in Rung 2) and `data/__init__.py` (confirmed no
`blank_world_bytes` exists); the remainder is carried from a prior census, spot-checked only where noted,
and should be treated as **[per research pass, unverified this rewrite]** rather than fact until each is
actually exercised: `mesh.py`, `discmirror.py`, `worldpack.py` (module functions), `encounter.py`,
`navimap.py`, `orphangate.py`, `interior.py`, `island.py`, `islandbeach.py`, `coastscan.py`,
`coastmorph.py`, `terrain.py`, `transplant.py`, `fuse.py`, `water.py`, `blendio.py`, `palette.py`,
`atlas.py`, `placement.py`, `grassland.py`, `texgates.py` (code generalizes; its *calibration data* may
not, see Rung 5). **Directory count corrected this pass:** the `world/` package holds **26** `.py` files,
not 27 — a prior draft's "27 files" count included `__pycache__`, a bytecode-cache directory, as if it were
a source file (`world/` listing re-run this pass: `__init__, atlas, blendio, coastmorph, coastscan,
discmirror, encounter, entrance, environment, extract, fuse, grassland, interior, island, islandbeach,
locate, mesh, navimap, orphangate, palette, placement, terrain, texgates, transplant, water, worldpack` =
26 **[verified this rewrite]**).

**New modules/functions this plan requires:**
- `ff9mapkit/ff9mapkit/data/__init__.py`: **`blank_world_bytes(donor="WORLD11")`** — a `blank_field_bytes()`
  sibling, confirmed missing this pass. Treat as genuinely novel, not a copy-paste — see Rung 4's standalone
  verify requirement.
- A "build a switch from zero cases" helper (Rung 6) — today's `find_switch`/`repoint_switch_case`
  (**[per research pass, unverified this rewrite]**, `edit.py:383-455`) only edit an existing switch.
- `ff9mapkit/ff9mapkit/world/thirdworld.py` (Rung 5): the sentinel-namespace cell-authoring surface —
  wraps `mesh.override_relpath`/`deploy_override` with the reserved sentinel disc-tag, and a
  `mint_world_disc(cells)` helper emitting the full 480-cell `InitialX/InitialY/IsSea` manifest `s73` reads.
- CLI: new verbs `world-mint` (Rung 5) and `world-scene` (Rung 2/4). Also **fix** `cli.py`'s
  `world-encounters --disc choices=[1, 4]` restriction (**[per research pass, unverified this rewrite]**,
  `cli.py:7955`) if/when a Path-D world gets its own encounter table (§8 — not part of Rungs 0-6).

**Confirmed genuine gaps that do NOT generalize (carried from prior census, not re-checked this rewrite):**
- `world/environment.py` mirrors the engine's own literal `Disc4` NCalc keyword; no `DiscN`/`World<N>` form
  exists on either side — needs a new engine grammar keyword. Out of scope for Rungs 0-6; defer (§8).
- `world/locate.py` hardcodes `WORLD_EB_CONTAINER = 'eventbinary/world/us/evt_world_world00.eb'` — needs a
  real parameter, not a default change, to cover a Path-D dispatcher. Not needed until Rung 6 wants
  `locate`-style tooling for the new world's own entrances.

## 6. Open unknowns requiring a live probe

Deduplicated across all sources, with the cheapest concrete experiment for each and closed items removed.

**Closed by direct source reading (no probe needed):**
- ~~Does the WorldMap scene hold one or two `WorldDisc` hierarchies~~ — closed: one Unity scene,
  `"WorldMap"`, loaded from every entry point.
- ~~Is `WMBlock`'s `InitialX`/`InitialY`/`IsSea` attribute-restricted from runtime construction~~ — closed,
  favorably: plain public fields, no attributes (`WMBlock.cs:243-259`, verified this rewrite).
- ~~Is `WMWorldPrefabMaker.LoadModelAsset` reachable at runtime~~ — moot: this plan's design (Rung 1)
  deliberately routes around this dead editor-only code entirely, via the live reclaim/sea path instead.
- ~~Can Rung 0's spike be reached and observed via the existing debug menu~~ — closed, **negatively**: it
  cannot, without `s70`'s widen (`Ff9mkDebugMenu.cs:1403-1405` and `WMBeeMenu.cs:153`, both verified this
  rewrite). This is precisely why Rung 0 exists now.
- ~~Does `entrance.py` need a change to discover a new custom dispatcher~~ — closed, **negatively**:
  `load_all_dispatchers` reads exclusively from pristine `p0data*.bin` (`entrance.py:97-120`, verified this
  rewrite) and structurally cannot see a custom dispatcher under any name. Registration (Rung 2) doesn't
  need discovery; later kit tooling (Rung 6) would.
- ~~Is `WorldMeshOverride.cs` generic over an arbitrary `disc` value~~ — closed, favorably: the entire file
  (`:1-223`, verified this rewrite, full read) takes `disc` as a plain `Int32` parameter everywhere; the
  real hardcode is in `WMWorld.cs`'s callers, nine sites enumerated in Rung 5.

**Still open — needs a live/runtime probe:**

1. **[THE Rung 1 question]** Can a runtime-built `WMBlock` hierarchy be substituted for `WorldDisc` without
   crashing `Initialize()`/`OnInitialize()`/`Wrap()`/the shift machinery? — **Experiment: Rung 1 itself.**
   No cheaper probe exists.
2. Does `AssetManager.Load<T>(...)` resolve against any name a mod bundle supplies, or is it capped to the
   two shipped `WorldDisc1`/`WorldDisc4` AssetBundles? — only relevant if Rung 1 fails and the plan falls
   back to §4's deferred patch. **Experiment:** grep the kit for any existing `.assetbundle`/`AssetBundle`
   authoring code before assuming none exists — this itself is unresolved.
3. Does `discmr.img`'s zone/record-table shape hold for a Path-D world's own pack (if one is ever built)?
   — **Experiment:** offline, `py -m ff9mapkit world-extract --disc 4` and diff against disc-1's shape. Not
   needed until §8's "encounters" scope is opened.
4. What does an out-of-`{1,4}` disc value actually do at runtime inside `GetDisc()`/`SetDisc()`? — this
   plan's architecture (Rung 3) deliberately avoids ever needing to answer this by keeping `currentDisc` at
   1; only relevant under the §4 fallback.
5. Is `Wrap()`'s loop genuinely safe on a synthetic array with no player yet? — covered by Rung 1's own
   success/failure signal; watch specifically for a hang, not just a crash.
6. Does any OTHER hardcoded table beyond `EventDB` assume exactly the 13 known `wldMapNo` values (minimap
   tables, save schema, netsync)? — **Experiment:** a targeted grep sweep
   (`grep -rn "wldMapNo\s*==" --include=*.cs`, plus a literal `9000`–`9012` sweep restricted to
   comparison/switch contexts) before Rung 2; cheap, offline, not run exhaustively this pass.
7. Does `DefinePlayerCharacter`'s conditional actor-mutation/`SmoothFrameUpdater_World.Skip` branches
   (`EventEngine.DoEventCode.cs:1035-1042`, verified this rewrite) behave sanely on a freshly-built world
   with no prior actor state? — **Experiment:** covered by Rung 4's verify; watch for control/camera
   anomalies specifically, not just crashes.
8. Whether `w_naviLocationPos`'s outer dimension or the continent-title switch would throw or silently
   no-op for a Path-D world's ids (**[per research pass, unverified this rewrite]**) — covered implicitly
   by Rung 3/6's in-game verify; explicitly out of scope to *fix* at this stage (§8).
9. Whether `texgates.py`'s acceptance thresholds generalize to synthesized Path-D terrain — **Experiment:**
   run the existing calibration harness against Rung 5's first authored cells and compare pass rates to
   the disc-1 baseline, offline.
10. Whether `entrance_func_body`'s `dispatchers=` parameter can be used to hand it our own custom
    dispatcher's bytes directly, sidestepping `author_entrance`'s 13-way replication loop entirely for
    Rung 6's world-side switch — a genuinely promising angle surfaced this pass (`entrance.py:360-369`,
    verified) but **not proven**; treat as Rung 6's own sub-spike, not an assumption.
11. **Standing discipline, not a one-off probe:** every "already generalizes" verdict in §5's kit census is
    a claim about the *code*, not about whether the underlying *data* would parse correctly against a
    genuinely novel Path-D shape. No session has executed the world/ package's functions against the real
    install specifically for Path-D-shaped input. **Run the relevant kit function once, offline, against
    real Rung-1/3 output before trusting its "generalizes" label in a deploy, at every rung.**

## 7. Honest cost/risk assessment

| Rung | Size | Can it fail and force a redesign? |
|---|---|---|
| 0 — Reachability spike | **XS** | Very low risk — a debug-menu range-check widen. The only way this "fails" is discovering some OTHER hidden gate on `wldMapNo` (§6 unknown 6), which would be useful information, not a dead end. |
| 1 — WorldDisc spike | **S**, but see the pacing note below — do not read "S" as "fast" | **Yes — the pivotal one.** Failure forces the whole plan onto the §4 fallback (real 3rd disc + baked AssetBundle asset), which is **XL** and blocked on an asset-authoring capability the project doesn't currently have (§6 unknown 2). |
| 2 — EventDB directive | **S** | Low risk, heavily precedented (`FieldScene`/`BattleScene` copy-paste), verbatim-first (no novel byte-splice in this rung). Useful infrastructure even under the §4 fallback. |
| 3 — Combine 1+2, unpeopled | **S–M** | Depends entirely on Rung 1. If Rung 1 succeeds cleanly, this is mostly a `wldMapNo`-gate wire-up. If Rung 1 partially misbehaves, this rung absorbs and must diagnose that risk. |
| 4 — First walkable world | **M** | The genuinely novel piece here is `blank_world_bytes()` (zero prior art) plus `DefinePlayerCharacter`'s more-involved-than-assumed opcode logic on synthetic actor state — real risk, but bounded and isolable (verify the byte-splice standalone on real geometry first). |
| 5 — Shape the grid | **M** | Low engineering risk for the kit-side terrain builders (generic over `disc`, per prior census) but genuinely scattered engine work for the sentinel-disc fork (nine call sites, two needing new signatures) plus real calibration risk (texgates thresholds). |
| 6 — Entrance/exit | **M** | The field-side half is low-risk/precedented. The world-side "build a switch from zero" gap is real but bounded; whether `author_entrance`'s 13-dispatcher machinery is even the right tool (probably not, per §3 Rung 6) needs its own small sub-spike before assuming scope. |
| §4 fallback (real 3rd disc) | **XL** | A separate, much larger initiative: new engine gates in multiple places *plus* a genuinely new baked Unity asset the toolkit cannot currently author. |

**Pacing reality check (a correction this revision adds in full, per adversarial review):** language like
"cheap," "five-minute spike," or "worst case a second small design iteration" — present in an earlier draft
of this plan — undersold the correctness bar and the lack of any stock reference shape for Rungs 1
onward. This project's own nearest precedent, the scene-ladder, is a **strictly narrower** problem: it
reused already-populated disc-1/world-9011 geometry throughout, never constructed new `WMBlock` state, had
a stock rig idiom to copy, and had its own hard prerequisite already banked before it started. Even so it
took (per the scope-honesty critique's reading of `studies/overworld-topography/scene-ladder/README.md` —
**[per research pass, unverified this rewrite]**, presented with that hedge but consistent with this
project's documented iterative-playtest house style): rung 0 one round; the camera-rig proof **six**
rounds; two more rungs at two rounds each (one a hard softlock, one a hard white-screen lock); a further
rung at three rounds; at least two terrain iterations; and a *closed* rung that still surfaced a latent
correctness bug at build time. On the order of **18-20+ discrete playtest-and-relaunch rounds** for a
feature family this project's engine authors already had working muscle memory for. Path D's Rung 1 has
none of those advantages — this is explicitly the first attempt at this mechanism in this codebase. **The
honest expectation to set: several relaunch-and-diagnose rounds per rung is the norm here, not the
exception; a double-digit total round count across Rungs 0-4 alone would be unsurprising; and there is a
real chance Rung 1's first failure is not a clean crash but a confusing partial misbehavior that itself
burns two or three rounds just to characterize**, since there is no stock shape to compare against, unlike
every rung the scene-ladder ever ran.

**Overall sizing for a minimally playable third world (Rungs 0-4, Rung 1 succeeding): L, multi-session,
several playtest rounds per rung expected as the norm.** If Rung 1 fails: XL and gated on a capability
(Unity asset authoring) this plan cannot scope further without first answering §6 unknown 2.

## 8. What NOT to build yet

Grounded in a census of exactly which per-world tables are dense/hardcoded vs open (**[per research pass,
unverified this rewrite]** throughout this section unless noted) — every item below either (a) is capped
by a dense or hardcoded engine table unrelated to Rungs 0-6's actual gates, or (b) only matters once a
Path-D world already exists and is entered, i.e. is polish on top of an unproven foundation.

- **Encounters / a real `discmr.img` pack.** `w_worldZoneFigure`/`w_worldZoneInfo` and `w_worldAreaZone`
  are hardcoded-size, fully-dense tables with no free area id; `w_fileSystemConstructor` has no third
  server slot to load a distinct pack from. A Path-D world can get *some* encounters for free by reusing an
  existing area id (data-only), but that silently entangles with whatever real place currently owns that
  zone — acceptable as a documented placeholder, not as shipped design. Decide after Rungs 0-4 are proven.
- **Minimap landmark markers.** `w_naviLocationPos` has a hardcoded 2-world outer dimension; the
  `w_naviMapno` selector is a hardcoded threshold, not derived from `wldMapNo`/`currentDisc`. Real engine
  change, entirely orthogonal to whether the world exists and is enterable. Defer.
- **A distinct continent-title banner.** Two independent hardcoded ceilings stack — a 4-case
  `w_frameScenePtr`→`titleId` switch and a 4-case `GetContinentName` switch that falls through to
  `String.Empty` on a miss (silent, not a crash). Ship with no banner; it degrades gracefully.
- **Vehicles on the new world.** Same hardcoded 2-way server-branch family as encounters above; the
  existing vehicle system is proven on the *existing* two discs; porting it to Path-D is a distinct,
  separately-scoped effort layered on top of a working Rung 4-6, not part of them.
- **A named `WorldPlace`/`WorldEffect` semantic hook.** Both are closed C# enums; a new named concept needs
  an enum-member engine change. The unkeyed `Mist`/`Rain`/`Light`/`Title` NCalc tokens remain open for
  later weather/lighting polish once a world exists to polish.
- **`environment.py`'s `Disc4` keyword generalization** and **`locate.py`'s multi-dispatcher rework** (§5)
  — real, identified kit gaps, but neither blocks Rungs 0-6; both are pure authoring-convenience work for
  whenever a Path-D world needs its own weather condition or entrance-geography tooling.

**The one-sentence discipline:** every item above answers "how does the new world *feel* once it's real";
Rungs 0-4 answer "is a new world even *possible*." Do not spend an engine round on anything in this section
before Rung 4 has an owner-confirmed in-game check.

---

## 9. Corrected from draft

What an earlier draft of this document got wrong, overstated, or mis-sequenced, per three independent
adversarial critiques plus direct re-verification performed while writing this revision. Listed so a
reader can see exactly what NOT to trust from that earlier version.

**Removed / downgraded claims (factual errors):**
- *"27 files, matches r6 exactly"* (world/ package census) — **wrong.** Re-counted directly this pass:
  **26** `.py` files. The 27 count silently included `__pycache__`, a bytecode-cache directory, as a
  "file." Corrected in §5.
- *"Nothing gates `wldMapNo` outside the fixed 9000-9012 dictionary keys"* (executive summary) — **true
  only of the engine's dispatch logic, false of the project's own debug tooling.** `ForceWorldState`
  hard-rejects ids outside 9000-9012 and `WMBeeMenu`'s "Jump To" isn't a dispatcher switch at all. This was
  the single most consequential correction — it meant the draft's Rung 0 named two "cheap verify" routes
  that do not work, an unobservable-first-rung defect an earlier version of this plan did not catch on its
  own. Fixed by inserting a new, genuinely tiny Rung 0 ahead of everything else.
- *`DefinePlayerCharacter` described as "a one-line controlUID write ... deriving everything else
  automatically."* **Overstated** — the actual handler does an actor lookup, a conditional mutation of a
  *different* actor's `isPlayer` state, and a conditional `SmoothFrameUpdater_World.Skip` write before the
  final controlUID assignment. Re-scoped into Rung 4 (where it actually matters) with the real logic
  described and flagged as a new watch-item for that rung's verify, not asserted as risk-free.
- *The sentinel-disc-namespace fork described as "a single, contained extension to
  `WorldMeshOverride.cs`."* **Mis-scoped to the wrong file** — that file already takes an arbitrary `disc`
  int everywhere and needs zero change (confirmed by a full re-read this pass). The real hardcode is nine
  call sites across five methods in `WMWorld.cs`, two of which need a new method parameter, not just an
  argument swap. Re-scoped correctly in Rung 5 with the exact sites re-enumerated this pass (superseding
  two critics' slightly different partial lists, since neither matched a fresh grep exactly).

**Reordered / rescoped (sequencing defects):**
- Inserted a new **Rung 0** (reachability spike) ahead of everything else — the draft's WorldDisc spike had
  no working way to be observed in-game as written. This is the single structural change this revision
  makes to the rung ladder.
- Split the draft's monolithic "Rung 1" (which bundled a new EventDB directive AND a from-scratch
  `blank_world_bytes()` byte-splice as one "S / low risk" unit) into **Rung 2** (EventDB directive only,
  verbatim-first — clone a real dispatcher's bytes rather than inventing new ones) and **Rung 4** (the
  novel byte-splice, verified standalone before combining with anything else). This follows the project's
  own "incremental verbatim-first" house rule, which the bundled version violated.
- Split the draft's "Rung 2" (combine WorldDisc + dispatcher + player, one atomic milestone) into **Rung 3**
  (combine WorldDisc + dispatcher, unpeopled — still just proving the combination doesn't crash) and
  **Rung 4** (add the player). This was the scope-honesty critique's explicit recommendation, applied.
- Deferred the sentinel-disc-namespace engine work from the old "Rung 2" to **Rung 5**, on the observation
  (new to this revision, not stated by any of the three critiques) that Rung 3's all-sea, zero-override
  world doesn't need it at all — it only matters once real per-cell `.ff9mesh` overrides exist. This
  further shrinks the "does the world exist" milestone's footprint.
- Re-scoped **Rung 6**'s framing from "generalize `author_entrance` to a 14th dispatcher" (the sequencing
  critique's finding) to a sharper reading: `author_entrance`'s 13-way replication loop solves a
  story-state-variance problem a single custom dispatcher doesn't have, so the right fix is probably
  bypassing that machinery rather than generalizing it — surfaced via `entrance_func_body`'s
  caller-suppliable `dispatchers=` parameter, which no prior pass had examined. Presented as a promising,
  unproven angle and folded in as its own sub-spike (§6 unknown 10), not asserted as solved.
- Named the worked `WorldScene` example dispatcher `WORLD13` instead of `CUSTOM_WORLD`, closing the
  regex-mismatch bug the sequencing critique caught (`_WORLD_RE` requires `evt_world_world\d+`) at the
  source rather than patching around it.
- Dropped the draft's "OR simplest: fire the WorldDisc substitution unconditionally on the very next
  WorldMap scene load" fallback entirely. It would have fired for every concurrent session sharing the
  install (per CLAUDE.md's documented multi-worktree risk), not just a deliberate test — the sequencing
  critique's finding, addressed by making Rung 0's reach mechanism the only way in, gated behind a
  default-OFF flag.

**Added (net-new findings from this pass's own source reading, not present in any prior critique):**
- `BuildBlockArray`'s missing null-check on `transform.GetComponent<WMBlock>()` (`WMWorld.cs:1673-1688`) —
  a stray non-`WMBlock` child under the spike's synthetic root throws immediately, before `OnInitialize()`
  even runs. Folded into Rung 1's construction procedure (build only `WMBlock` children, nothing else) and
  its risk enumeration.
- The precise nine-site enumeration for the sentinel-disc fork (Rung 5), re-grepped fresh this pass to
  settle two critiques' slightly different partial citations of the same underlying issue.
- The realistic pacing expectation in §7, grounding "this will take several playtest rounds per rung, not
  one" in this project's own nearest precedent (the scene-ladder) rather than leaving Rungs 0-4's sizing
  implicitly optimistic.

**Confirmed correct under continued scrutiny (not changed):** the state/geometry decoupling
(`ff9InitStateWorldMap` / `GetDisc()` mutual disconnection); `WorldDisc`'s exactly-four-call-site blast
radius; `WMBlock`'s unattributed public fields; `OnInitialize()`'s computed-not-baked per-block position
write; the s34 reclaim/donor mechanism as an already-proven substrate; the `WMWorld.cs:2069-2074`
serialization-layout risk being a genuinely different risk class from a runtime value-assignment into an
existing field; `WorldMeshOverride.cs`'s full genericness over `disc`; and the next-free-patch-number
claim (`s70`, highest existing `s69-minimap-visible-state.patch`).