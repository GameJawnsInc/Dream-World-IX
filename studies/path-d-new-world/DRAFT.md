# Path D — Minting a Genuinely Third FF9 Overworld: Execution Plan

*Drafted from six parallel first-principles research passes (r1–r6) plus direct re-verification this
session of every load-bearing claim in §2 and several in §3–§6. Claims marked **[verified this session]**
were re-read from live source in this pass; claims marked **[per rN]** are carried from that research
agent's report and were spot-checked only where noted. Nothing here traces to a memory-file summary
without a source citation.*

---

## 1. Executive summary

At minimum, Path D requires solving two **independently decoupled** problems that six agents converged
on and this session confirmed directly: (a) a new **EventDB world-state id** so a `.eb` dispatcher can run
its own script/camera/entrance logic (cheap, fully precedented — `FieldScene`/`BattleScene` in
`DataPatchers.cs:497-548` are the exact template, and nothing gates `wldMapNo` outside the fixed
9000–9012 dictionary keys), and (b) **new block-grid geometry** for that dispatcher to render on, which is
the hard part — the 480-cell `WMBlock` topology lives on a single serialized `Transform WorldDisc` field
(`WMWorld.cs:2033`) baked into the **one** Unity scene the whole game shares for both existing discs
(confirmed this session: every world-map entry point calls `SceneDirector.Replace("WorldMap", ...)`
verbatim — `HonoluluFieldMain.cs:338`, `EventEngine.Initialize.cs:68`, `WMScriptDirector.cs:228`,
`BattleResultUI.cs:54` — there is no per-disc scene). **The single biggest open risk is whether a
brand-new 480-`WMBlock` hierarchy can be constructed purely at runtime in C# and substituted for that one
`WorldDisc` field before `WMWorld.Initialize()`/`OnInitialize()` walk it** — this session's direct reading
found genuinely encouraging signal (`WMBlock`'s `InitialX`/`InitialY`/`IsSea` fields carry no
`[NonSerialized]`/attribute restriction and are plain runtime-writable, `WorldDisc` is referenced at only
4 call sites all inside `WMWorld.cs`, and per-block **positions are computed from `InitialX`/`InitialY` at
`OnInitialize()` time, not baked** — `WMWorld.cs:449-458`) but it is **unproven in-game** and gates
everything downstream. Nothing in this plan should be built past Rung 0 until that is answered.

## 2. The core question this plan must answer first

Two research agents (r2, r3) directly addressed the WorldDisc-asset and state-vs-geography questions the
task calls out by name. Their verdicts, reconciled against this session's own re-reads:

**r2's verdict was `uncertain_mixed`.** Its strongest evidence for "baked, not codeable" was the
project's own s34-era comment at `WMWorld.cs:2069-2074` (**[verified this session]**, quoted verbatim
below) documenting a *different* field (`LandDonorPrefab`) hitting a real blackscreen from disturbing
`WMWorld`'s own serialization layout — not from touching `WorldDisc`'s *value* itself. Its strongest
evidence for "codeable in principle" was that `WMWorldPrefabMaker.LoadModelAsset` (`WMWorldPrefabMaker.cs
7-178`) is a complete, if dead, algorithm for building a 24×20 block grid from `Resources.Load` calls, and
that `WMBlock`'s state fields are ordinary assignable fields. r2 could not resolve which side wins without
a runtime probe.

**r3's verdict was more decisive on the *state* axis** but explicitly punted the *geometry* axis to r2/r5's
unknowns: `ff9InitStateWorldMap(MapNo)` (`ff9.cs:9293-9312`, **[verified this session]**) and
`WorldConfiguration.GetDisc()` (`WorldConfiguration.cs:234-241`, **[verified this session]**) are provably
disconnected — the former never reads `currentDisc`/`w_frameDisc`, the latter never reads `wldMapNo`. r3's
"cheap precedented version" (new dispatcher + `WorldMeshOverride` reclaim edits *inside the existing
480-cell grid*) is real and safe, but it is **not** a third world by the task's own definition — it edits
disc 1 or disc 4 in place, same as the Southern Ring. r3 flagged the true third-world question — can
`WorldDisc` itself point somewhere new — as unresolved from source.

**This session's own re-reads move r2's needle further toward "codeable" than either agent stated,
without closing it:**

- `WMBlock : MonoBehaviour` (`WMBlock.cs:6`) declares `IsSea`, `HasSpecialObject`, `IsSwitchable`,
  `InitialX`, `InitialY`, `Number` as plain `public` fields with **no** `[NonSerialized]`,
  `[SerializeField]`, or any other attribute (`WMBlock.cs:243-259`, **[verified this session]**) — nothing
  in the class declaration itself blocks `gameObject.AddComponent<WMBlock>()` + direct field assignment
  from working exactly like any other runtime object construction in this codebase.
- `WorldDisc` is read at **exactly four** locations in the entire `Assembly-CSharp` tree, **all inside
  `WMWorld.cs`**: `BuildBlockArray(this.WorldDisc)` at `:105` (Initialize) and `:449` (OnInitialize), the
  null-guard at `:139`, and `this.root = this.WorldDisc` at `:470` (**[verified this session]**, whole-tree
  grep). This is a small, auditable blast radius for a runtime substitution.
- **Per-block world *position* is computed, not baked.** `OnInitialize()` (`WMWorld.cs:449-458`,
  **[verified this session]**) does `position.x = j * 16384 * 0.00390625f; position.z = i * -16384 *
  0.00390625f;` (i.e. `InitialX/InitialY * 64`) and writes it onto every block's `transform.position` —
  so a freshly built hierarchy needs no baked transform layout, only correct `InitialX`/`InitialY` ints.
- `BuildBlockArray` (`WMWorld.cs:1673-1690`) fills `array[i,j]` by **linear-scanning every child looking
  for a matching `InitialX`/`InitialY`** — it does *not* require children in any particular order, but a
  gap (no child matching some `(i,j)`) leaves that cell `null`, and `OnInitialize()`'s position-write loop
  (`Blocks[j,i].transform.position = ...`) has **no null guard** — a missing cell is a hard
  `NullReferenceException`, not a graceful skip. **A from-scratch WorldDisc must supply exactly one
  `WMBlock` for every one of the 480 `(x,y)` pairs 0–23 × 0–19, no gaps, no duplicates** (a duplicate
  silently last-write-wins in `BuildBlockArray`'s loop, per r1).
- The MonoBehaviour-serialization blackscreen class documented at `WMWorld.cs:2069-2074` (quoted: *"WMWorld
  is a MonoBehaviour baked into the pre-built WorldDisc prefab; adding a SERIALIZED (public) field shifts
  its serialization layout, so the baked component deserializes corrupt"*) is about **adding a new C#
  field to the `WMWorld` class itself**, changing what Unity expects to deserialize from the *existing*
  baked component's byte stream. **Assigning a new value into the existing `public Transform WorldDisc`
  field at runtime does not touch that class layout at all** — this is a different risk class, and nothing
  found this session suggests it is unsafe by the same mechanism. This distinction was not drawn explicitly
  by any of the six agents and materially changes the risk read.
- `Wrap()` (`WMWorld.cs:1077-1108`, **[verified this session]**) — the torus-shift loop `OnInitialize()`
  spins in (`while (!this.Wrap())`) — early-returns `true` (loop exits) whenever `ff9.w_moveActorPtr` is
  `null` or is the dummy character. Since `OnInitialize()` runs before any `.eb` `Init` code has had a
  chance to call `DefinePlayerCharacter`, this loop is very unlikely to spin more than once on a fresh
  world — a genuine infinite-loop risk is **not** supported by this reading, though it is not proven safe
  either (needs the in-game probe).

**Verdict for this plan: genuinely uncertain, leaning codeable, and it is Rung 0 — not because the
research disagreed irreconcilably, but because the disagreement is real and the fastest way to close it is
a five-minute in-game spike, not more reading.** Everything past Rung 1 is provisional on Rung 0's result.

**The state-vs-geography decoupling (r3) is independently confirmed, cleanly, and is not in dispute.**
`ff9InitStateWorldMap` never touches disc/mesh state; `GetDisc()`/`SetDisc()` never touch `wldMapNo`. This
means Rung 1 (new dispatcher id) and Rung 0 (WorldDisc swap) can be **built and verified as two separate,
parallel-safe rungs** before being combined — exactly the kind of small independently-testable step the
project's own house style (the scene-ladder) uses.

## 3. Rung-by-rung build sequence

Each rung names exact files, cites what's proven-safe vs new, and ends with a cheap check before advancing.
Rungs 0 and 1 are ordered first and are **independent of each other** — do Rung 0 first because it gates
everything (a "no" answer there forces a full redesign toward the heavier AssetBundle path in §7); Rung 1
is cheap, low-risk, and can run any time before Rung 2 needs it.

### Rung 0 — THE WORLDDISC SPIKE (resolves the core question)

**Goal:** prove or disprove that a brand-new 480-`WMBlock` hierarchy, built purely in C# at runtime, can be
substituted for `WMWorld.WorldDisc` and survive `Initialize()`/`OnInitialize()` without crashing, and that
the resulting world is enterable (even if visually blank/black — geometry dressing is Rung 2).

**Files touched:** one throwaway engine patch, `memoria-patches/s70-worlddisc-runtime-spike.patch` (next
free number confirmed — highest existing is `s69-minimap-visible-state.patch`), modeled on the project's
own precedent for exactly this kind of disposable diagnostic: `s63-world-scene-probe.patch` (**removed
after answering its question in two rounds**, per `memoria-patches/README.md`) and `s67-rig-probe.patch`
(**kept live only through the rung it served**). Hook point: a static helper
`Memoria.World.WorldDiscSpike.MaybeBuildFakeDisc(WMWorld world)` called at the **very top** of
`WMWorld.Initialize()`, before line 105's `BuildBlockArray` call — gated behind an `.ini` flag or a debug
menu button so it never fires for a normal disc-1/4 load. It should:
1. Create a fresh `GameObject("WorldDisc_SPIKE").transform` parented under whatever `Initialize()` already
   parents `TranslatingObjectsGroup` to (`GameObject.Find("WorldMapRoot")`, `WMWorld.cs:97,102`).
2. Loop `x in 0..23, y in 0..19`, `AddComponent<WMBlock>()` a child, set `InitialX=x`, `InitialY=y`,
   `IsSea=true` (forces every cell through `LoadBlock`'s reclaim branch, `WMWorld.cs:490-500`, sidestepping
   the disc-interpolated prefab lookup entirely — see Rung 2's design note).
3. Assign `world.WorldDisc = thatTransform` before returning.

**Already proven-safe (cite):** `WMBlock`'s fields are plain assignable (`WMBlock.cs:243-259`, verified
this session); `WorldDisc`'s 4 call sites are fully enumerated (verified this session); the reclaim/donor
path this spike deliberately routes into (`WMWorld.cs:490-500`, `ResolveReclaimDonor`) is the **already
in-game-proven** s34 Path-D mechanism, not new code.

**Genuinely new/risky:** nothing like this has been built or tested. Candidate failure modes to watch for:
a crash inside `OnInitialize()`'s position-write loop (should not happen if all 480 cells are present, no
gaps); a crash or hang in `Wrap()`'s loop (analysis above says unlikely but unverified); a crash in
`ShiftBlocks`/the four `ShiftXAllBlocks` variants (r1: ~15 raw-literal torus-wrap sites, none disc-aware,
should operate purely on `this.Blocks` and be agnostic to where blocks came from — but unverified against a
totally synthetic array); the self-heal patch `s39-world-selfheal-control.patch` (`ff9.w_worldSelfHealControl`)
recovering (or failing to recover) a "no controlled actor" state on a world with zero real content.

**Cheap verify:** deploy the spike DLL, use the debug-menu World tab (`Ff9mkDebugMenu.cs`, per
`project-ff9-f6-overworld-debug`) to trigger the flag and enter, OR simplest: temporarily wire it to fire
unconditionally on the very next `WorldMap` scene load and warp there via the existing debug menu's
"Jump To" (`WMBeeMenu.cs:127-153`, only active on `disc==1` per r1 — use disc 1). **Success criterion:**
the screen does not black-screen/hang; `Memoria.log` shows no NRE inside `WMWorld`'s `Initialize`/
`OnInitialize`/`OnUpdateLoading`; the player is dropped somewhere without an immediate crash (it will look
like empty ocean — that's expected, no dressing yet). **Failure criterion:** any NRE inside the functions
above, or an infinite load. **On failure:** do not attempt further engineering on the "swap WorldDisc"
architecture — fall back to §7's heavier "extend GetDisc/SetDisc to a real 3rd disc value + author a real
`WorldDiscN` Unity prefab via an AssetBundle" path, which is a materially larger, Unity-Editor-dependent
effort (see r2/r6's unresolved AssetBundle unknowns in §6).

Remove or gate the spike patch immediately after the answer is in hand, per house style.

### Rung 1 — THE WORLDSCENE DIRECTIVE (proves the state axis, independent of Rung 0)

**Goal:** register a genuinely new `wldMapNo` (e.g. 9013 — one past the reserved 9000-9012 hole this
project already treats as sacred, see CLAUDE.md §3) and confirm the engine reaches and runs a **cloned**
`.eb` dispatcher for it, landing on the **existing** disc-1 `WorldDisc` (no new geometry yet — this rung
answers "can I even get a script to run under a new id," nothing more).

**Files touched:**
- Engine: `memoria-patches/s71-worldscene-directive.patch` — a new `DataPatchers.cs` branch, modeled
  **exactly** on `FieldScene` (`DataPatchers.cs:497-529`, verified this session) and `BattleScene`
  (`:530-548`), but simpler (no FBG art registration needed — this is r3's own proposed shape, confirmed
  against the live directive-dispatch pattern this session):
  ```csharp
  else if (String.Equals(entry[0], "WorldScene") && entry.Length >= 3)
  {
      // eg.: WorldScene 9013 CUSTOM_WORLD
      if (FF9DBAll.EventDB == null) continue;
      Int32 ID;
      if (!Int32.TryParse(entry[1], out ID)) continue;
      FF9DBAll.EventDB[ID] = "EVT_WORLD_" + entry[2];
      // ships at Assets/Resources/CommonAsset/EventEngine/EventBinary/World/{Lang}/EVT_WORLD_{entry[2]}.eb.bytes
  }
  ```
  `FF9DBAll.EventDB` is confirmed (`FF9DBAll.Events.cs:7`, verified this session) a plain
  `Dictionary<Int32,String>`, already runtime-mutated by two sibling directives — this is a copy-paste, not
  novel engine work. Optionally also write `ff9.eventWorldMaps.Add((Int16)ID)` (`ff9.cs:10511`, a mutable
  `HashSet<Int16>`, verified this session) if the state should be treated as cutscene-only (skips a couple
  of free-roam-only codepaths per r5/r1 — not needed for a free-roam world).
- Kit: `ff9mapkit/ff9mapkit/world/entrance.py` needs **no change** to *discover* the new dispatcher once
  it exists (`load_all_dispatchers`'s `_WORLD_RE` regex, `entrance.py:84,87`, verified this session, is
  fully generic — confirmed by direct read). What's missing is a way to **author** one from nothing (see
  Rung 1's kit gap below and §5).
- New kit function: `ff9mapkit/ff9mapkit/data/__init__.py` needs a `blank_world_bytes()` sibling to the
  existing `blank_field_bytes()` (`data/__init__.py:32`, verified this session — confirmed no world
  counterpart exists). Cheapest instantiation: clone the smallest real free-roam donor, **WORLD02** (8144
  bytes per r4's direct byte-decode this session's predecessor — not independently re-verified by this
  plan but internally consistent with `entrance.py`'s regex-discovery mechanism), strip it down to r4's
  decoded minimal `Main_Init` (arm one `InitObject`'d avatar entry that calls `DefinePlayerCharacter`,
  `Map.Byte[24]=100`, `RET`) using the kit's own proven-generic `eb/edit.py`/`eb/cmdasm.py` primitives
  (r4: verified no field-vs-world branch exists anywhere in `eb/model.py`/`eb/edit.py`).

**Already proven-safe (cite):** the `.eb` container format is disc/world-agnostic (r4, and the
scene-ladder's own `rung3c_origin_departure.py` already edits real `EVT_WORLD_WORLD11.eb.bytes` with the
exact same `eb.model`/`eb.edit` primitives fields use); `DefinePlayerCharacter` (opcode `0x2C`) is a
one-line `controlUID` write with the free-roam camera (`w_cameraUpdate`, `ff9.cs:2665-2691` per r4)
deriving everything else automatically — no separate camera-init opcode exists.

**Genuinely new/risky:** the `WorldScene` directive itself is new engine code (small, low-risk, but
untested); whether **any other** hardcoded table besides `EventDB`/`eventIDToMESID` silently assumes
exactly the 13 known `wldMapNo` values is unresolved (r3's own flagged unknown — a targeted grep sweep is
cheap, see §6).

**Cheap verify:** deploy, tilde-warp (or debug-menu "Jump To") to 9013. **Success:** the screen loads
*something* on the existing disc-1 WorldDisc (since Rung 1 alone doesn't touch geometry) without a crash,
`Memoria.log` clean, and the debug probe (or a simple `Log.Message` in the cloned `Main_Init`) confirms the
new `.eb` actually executed. **Failure:** an immediate crash on warp, or the engine silently falling back
to a real dispatcher — either would falsify r3's "EventDB has no range check" claim and needs its own
investigation before Rung 2.

### Rung 2 — THE MINIMAL THIRD WORLD (combine 0 + 1)

**Goal:** the first genuine Path D artifact — dispatcher 9013 (Rung 1) running against a fresh, dedicated
480-block `WorldDisc` (Rung 0), every cell dressed via the **already-proven** reclaim/donor + s34
loose-mesh-override machinery instead of any new baked asset, with one `DefinePlayerCharacter`'d avatar so
the player can stand and free-roam on it.

**Files touched:**
- Engine: fold Rung 0's spike into a real, permanent hook (`memoria-patches/s72-third-worlddisc.patch`),
  triggered not by a debug flag but by `wldMapNo == 9013` (or whatever range this project reserves for
  Path-D worlds) checked at the top of `WMWorld.Initialize()`. **Design decision to validate at this
  rung, not before:** rather than widening `WorldConfiguration.GetDisc()`'s `{1,4}` domain (which per r1/r5
  is capped in *three* independent places — `GetDisc()`'s ternary, `SetDisc`'s log-only gate, and
  `w_fileSystemConstructor`'s strict 2-way `Server1`/`Server4` branch, `ff9.cs:3621-3644` per r5) — **keep
  `currentDisc`/`w_frameDisc` at 1** (so every asset-dressing consumer downstream of `GetDisc()` keeps
  working unmodified) and use a **separate, new sentinel** purely for the `WorldMeshOverride` per-cell
  lookup namespace (see next bullet). This sidesteps the entire `{1,4}`-domain risk surface r1/r5 mapped
  out, at the cost of every Path-D world's cells being forced through the reclaim path (already the
  design, since every cell is `IsSea=true`).
- Engine: extend `Memoria.World.WorldMeshOverride`'s per-cell key (currently `(disc, x, y)`,
  `WorldMeshOverride.cs`, confirmed generic over `disc` this session and by r1) so cells belonging to a
  Rung-0-built `WorldDisc` are looked up under a **reserved sentinel disc number never equal to 1 or 4**
  (e.g. `9`) instead of `world.currentDisc`. **This is the one deliberate architectural fork this plan
  proposes beyond what any research agent stated outright** — flagged explicitly as new synthesis, to be
  validated (not assumed) at this rung: it avoids a real disc-1/4 override-namespace collision (a Path-D
  cell at grid coord (5,5) would otherwise share its override file path with a real Southern-Ring edit to
  disc-1 block (5,5) — a genuine, previously-unflagged collision risk this session's own tracing surfaced).
  If validation shows the sentinel-disc approach doesn't fit cleanly (e.g. `LoadBlock`'s reclaim call sites
  assume `disc == currentDisc` more deeply than this plan's read of `WMWorld.cs:490-537` suggests), fall
  back to a dedicated new function pair (`HasThirdWorldOverride`/`TryReadThirdWorldDonorPath`) rather than
  overloading the `disc` parameter's meaning.
- Kit: a new `ff9mapkit/ff9mapkit/world/thirdworld.py` (or extend `entrance.py`) with a
  `mint_world_disc(cells: dict[(x,y): CellSpec])` that emits the loose `.ff9mesh` files at the sentinel
  namespace's path convention (mirrors `mesh.py:override_relpath`'s existing generic `f'.../Disc{disc}/...'`
  formatting, just fed the sentinel value — **no change needed to `mesh.py` itself**, confirmed generic
  this session).

**Already proven-safe (cite):** the reclaim-donor mechanism (`ResolveReclaimDonor`, `WMWorld.cs:517-537`)
is **in-game-proven** as of s34 for reclaiming ocean cells on the *real* disc 1/4 grids; this rung reuses
it verbatim, just against a synthetic `WorldDisc`. The `.ff9mesh` loose-format itself
(`WorldMeshOverride.cs:158-221`) needs zero engine change to read a different disc-tag value — it's a
plain integer used in a `String.Format` path.

**Genuinely new/risky:** the sentinel-disc namespace fork described above (untested); whether
`LoadBlock(Int32 disc, WMBlock block)`'s reclaim branch (`WMWorld.cs:490-500`) can be safely called with a
`disc` value that never equals `world.currentDisc` without some other downstream consumer (materials,
`WMBlockPrefab` component expectations on the donor) choking — the donor prefab itself still comes from a
REAL disc-1 block via `LandDonorPrefab`, so this should be low-risk, but is unverified.

**Cheap verify:** deploy, warp to 9013. **Success:** the player spawns on a (default-flat/donor-textured)
480-cell field distinct from real disc 1/4 geography wherever a `.ff9mesh` override was authored, can
free-roam without falling through the world or brick-spawning (watch for the `no controlled actor`
self-heal firing — `s39-world-selfheal-control.patch`'s own documented TODO flags its degenerate fallback
`(768,-640)` as "may be sea," worth spot-checking here), and the torus wrap (`Wrap()`) doesn't glitch at
the grid edges. **This is the milestone that actually proves Path D is real** — everything before it is
infrastructure, everything after it is polish/scope.

### Rung 3 — SHAPE THE GRID (real geometry, not just donor patches)

**Goal:** move past "480 identical reclaimed-donor cells" to an intentionally designed landmass — reuse
the kit's already-generalized `world/terrain.py`, `world/island.py`, `world/coastmorph.py` etc. against the
new sentinel namespace instead of disc 1/4.

**Files touched:** kit-side only — `world/terrain.reshape/coast/reclaim` (`terrain.py:32-34,87-88,213-216`,
confirmed open-`disc:int=1` this session's predecessor per r6, forward the sentinel value the same as any
other int), `world/island.landmass`, `world/coastmorph.*` (all confirmed generic over `disc` per r6's
exhaustive census — **14 public builders, zero `{1,4}` checks found**). **No engine change** should be
needed here if Rung 2's sentinel-namespace fork holds — this is the payoff of that design choice.

**Genuinely new/risky:** `texgates.py`'s acceptance thresholds were empirically calibrated **only against
disc-1 stock ground samples** (Cleyra/grass/dunes families, per r6, `texgates.py:37-38` citing
`studies/overworld-topography/out/foldback/texgates_calibration_raw.json`) — untested whether they
generalize to a stylistically new world's synthesized geometry. Treat this as a real, separate risk to
re-calibrate, not assume.

**Cheap verify:** offline first — `ff9mapkit walkmesh verify`-class checks plus the kit's own offline
placement simulator (`project-ff9-overworld-placement-rules`) against the new grid's authored `.ff9mesh`
files before ever deploying; then in-game via `game_snap.ps1` capture per the coast-work house law ("READ
memory `project-ff9-overworld-coast-mosaic` before coast work" — applies here unchanged).

### Rung 4 — ENTRANCE / EXIT (connect it to the rest of the game)

**Goal:** a real field can `WMAPJUMP` into 9013, and 9013 can `Field()` back out to a real field — i.e.
Path D stops being a dead-end debug destination and becomes reachable through ordinary play.

**Files touched:** kit — extend `world/entrance.py`'s `author_entrance` machinery (already proven generic
over any discovered dispatcher, `entrance.py:731-1039` per r4) to also target 9013; author the field-side
gateway the normal way (`authoring-ff9-field-scripts` skill, `WMAPJUMP` opcode `0xB6`,
`EventEngine.DoEventCode.cs:2458-2462`, r4). **Known kit gap (r4):** `eb/edit.py`'s switch tooling
(`find_switch`/`repoint_switch_case`, `edit.py:383-455`) only edits an **existing** switch — 9013's own
`.eb` entry 1 AREA switch (if it needs multiple exit destinations) has no case-count yet and must be
hand-assembled via `cmdasm.assemble_block` (proven mechanically capable, `cmdasm.py:112-127`, but no
reusable "build a switch from zero cases" helper exists — build one here or accept a single hardcoded exit
for day one).

**Cheap verify:** enter 9013 from a real field via a normal gateway, walk to the exit trigger, confirm
landing back on a real field with story state intact (this also re-tests r3's flagged "was the state
axis genuinely reachable in time relative to New Game boot" unknown, in the cheapest possible way — via a
mid-game warp rather than New Game).

## 4. Engine patch inventory

All follow the project's own `sNN-<slug>.patch` convention (next free number confirmed this session:
highest existing file is `s69-minimap-visible-state.patch`, so this plan starts at **s70**).

| Patch | Scope (one line, README style) |
|---|---|
| `s70-worlddisc-runtime-spike.patch` | THROWAWAY diagnostic (remove after Rung 0 closes, per the `s63`/`s67` precedent): builds a synthetic 480-`WMBlock` `Transform` and swaps it into `WMWorld.WorldDisc` before `Initialize()`'s first `BuildBlockArray` call, gated behind a debug flag, to prove/disprove runtime WorldDisc construction is survivable. |
| `s71-worldscene-directive.patch` | New `DataPatchers.cs` `"WorldScene"` directive — the `FieldScene`/`BattleScene` sibling — writes `FF9DBAll.EventDB[ID] = "EVT_WORLD_" + name` at mod-load time so a brand-new `wldMapNo` is reachable via `WMAPJUMP`/debug-warp without a DLL rebuild per authored world. |
| `s72-third-worlddisc.patch` | Promotes s70 from spike to permanent: on `wldMapNo == <reserved Path-D id(s)>`, builds/caches a real 480-`WMBlock` hierarchy from kit-authored data and assigns it to `WMWorld.WorldDisc`; every cell forced through the existing reclaim path (`IsSea=true`) under a **new reserved sentinel disc-tag** (not 1, not 4) so `WorldMeshOverride`'s per-cell lookup never collides with real disc-1/4 override edits. |
| *(deferred, only if Rung 0 fails)* `sNN-real-third-disc.patch` | Heavier fallback: widen `WorldConfiguration.GetDisc()`'s ternary (`WorldConfiguration.cs:240`) and `WMWorld.SetDisc`'s `{1,4}` gate (`WMWorld.cs:1661`) to a real third disc value, plus a new `w_fileImagenameServerX` branch in `w_fileSystemConstructor` (`ff9.cs:3621-3644`) — **blocked on producing a real `WorldMap/Prefabs/WorldDiscN/...` baked `GameObject` asset**, which needs Unity Editor / AssetBundle authoring the kit does not currently have (§6, unknown #2). Do not start this until Rung 0 has definitively failed. |

Everything else this plan touches (encounters, minimap, continent banners — §8) is **explicitly out of
scope** for the engine-patch inventory at this stage; see §8 for why.

## 5. Kit work inventory

**Already generalizes, zero change needed** (verified this session against `entrance.py`, `data/__init__.py`;
trusted from r6's exhaustive per-file census for the rest, which this session spot-checked and found
consistent with the actual `world/` directory listing — 27 files, matches r6 exactly): `mesh.py`,
`discmirror.py`, `worldpack.py` (module functions only — see gap below for its CLI wrapper),
`entrance.py`'s dispatcher-discovery half, `encounter.py`, `navimap.py`, `orphangate.py`, `interior.py`,
`island.py`, `islandbeach.py`, `coastscan.py`, `coastmorph.py`, `terrain.py`, `transplant.py`, `fuse.py`,
`water.py`, `blendio.py`, `palette.py`, `atlas.py`, `placement.py`, `grassland.py`, `texgates.py` (code
generalizes; its *calibration data* may not, see Rung 3).

**New modules/functions this plan requires:**
- `ff9mapkit/ff9mapkit/data/__init__.py`: **`blank_world_bytes(donor="WORLD02")`** — a
  `blank_field_bytes()` sibling. **[Confirmed gap this session]** — no such function exists today.
- A **world-dispatcher orchestrator** (new file or extend `entrance.py`) analogous to `build.py`'s
  field-construction flow: `field.toml`-style declarative input → `blank_world_bytes()` + splice a minimal
  `Main_Init` (avatar `InitObject`, `DefinePlayerCharacter`, `Map.Byte[24]=100`) using `eb.cmdasm`/`eb.edit`
  primitives already proven generic over world bytes (r4, and the scene-ladder study's own direct
  world-`.eb` edits).
- A **"build a switch from zero cases" helper** in `eb/edit.py` (or a new `eb/switchbuild.py`) — today's
  `find_switch`/`repoint_switch_case` (`edit.py:383-455`) only edit an existing switch; needed for Rung 4's
  multi-exit dispatch if a single hardcoded exit isn't enough for day one.
- `ff9mapkit/ff9mapkit/world/thirdworld.py` (Rung 2/3): the sentinel-namespace cell authoring surface —
  wraps `mesh.override_relpath`/`deploy_override` with the reserved sentinel disc-tag instead of 1/4, and
  a `mint_world_disc(cells)` helper that emits the full 480-cell `InitialX/InitialY/IsSea` manifest the
  engine patch (`s72`) reads to build the runtime hierarchy.
- CLI: new verbs `world-mint` (Rung 2/3, wraps `thirdworld.py`) and `world-scene` (Rung 1, wraps the
  `WorldScene` DictionaryPatch line + `blank_world_bytes`-based dispatcher authoring). Also **fix**
  `cli.py:7955`'s `world-encounters --disc` `choices=[1, 4]` restriction (a one-line CLI-only cap; the
  underlying `worldpack.load_discmr` has no such restriction, per r6) if/when a Path-D world gets its own
  encounter table (§8 — not day one).

**Confirmed genuine gaps that do NOT generalize and need real rework, not a call-site tweak (r6, spot-checked
this session against the actual file for `environment.py`):**
- `ff9mapkit/ff9mapkit/world/environment.py`: mirrors the engine's own literal `Disc4` NCalc keyword
  (`WorldConfiguration.cs:93`'s token grammar) — there is no generic `DiscN`/`World<N>` form on either
  side. A Path-D world's own weather/mist condition needs a new engine grammar keyword first (out of scope
  for Rung 0-4; defer per §8).
- `ff9mapkit/ff9mapkit/world/locate.py`: hardcodes `WORLD_EB_CONTAINER =
  'eventbinary/world/us/evt_world_world00.eb'` (a single literal path) — the entrance-geography decoder
  only ever reads WORLD00's table today. Needs a real parameter, not a default change, to cover a Path-D
  dispatcher. Not needed until Rung 4 wants `locate`-style tooling for the new world's own entrances.

## 6. Open unknowns requiring a live probe

Consolidated from all six agents' `unknowns` lists, deduplicated, with the cheapest concrete experiment for
each. Items already closed by this session's direct source reads are marked accordingly and removed from
the "needs a probe" set.

**Closed by this session's source reading (no probe needed):**
- ~~r2's "does the WorldMap scene hold one or two WorldDisc hierarchies"~~ — **closed**: exactly one Unity
  scene, `"WorldMap"`, loaded from every entry point (`HonoluluFieldMain.cs:338` etc.), so exactly one
  baked `WorldDisc` topology is shared by disc 1 and disc 4 today.
- ~~r5's "is WMBlock's InitialX/InitialY/IsSea attribute-restricted from runtime construction"~~ —
  **closed, favorably**: plain public fields, no attributes (`WMBlock.cs:243-259`).
- ~~r1's "is WMWorldPrefabMaker.LoadModelAsset reachable at runtime"~~ — r1/r2 already independently
  confirmed zero call sites via grep; this session did not re-run that grep but has no reason to doubt it,
  and Rung 2's design deliberately routes around this dead code entirely (uses the live reclaim path
  instead), making the question moot for this plan.

**Still open — needs a live/runtime probe, cheapest experiment named:**

1. **[THE Rung 0 question]** Can a runtime-built `WMBlock` hierarchy be substituted for `WorldDisc` without
   crashing `Initialize()`/`OnInitialize()`/`Wrap()`/the shift machinery? — **Experiment: Rung 0 itself**,
   the `s70` spike. No cheaper probe exists; this must be run in-game.
2. Does `AssetManager.Load<T>(...)` (used at `WMWorld.cs:512` for per-block visual dressing) resolve
   against **any** name a mod bundle supplies, or is it capped to the two shipped `WorldDisc1`/`WorldDisc4`
   AssetBundles? — **Experiment:** only relevant if Rung 0 fails and the plan falls back to §4's deferred
   "real third disc" patch; probe by attempting `world-mint` to author a trivial mod `.assetBundle` (via
   whatever the project's existing AssetBundle-authoring capability is, if any — **this itself is an
   unknown**: does the toolkit have ANY Unity-Editor-adjacent asset-authoring path today? A cheap first
   step is simply grepping the kit for `.assetbundle`/`AssetBundle` authoring code before assuming none
   exists.
3. Does `discmr.img`'s zone/record-table shape (355 records / 25 zones / 65 areas, `worldpack.py`'s
   `_AREA_ZONE`/`_ZONE_FIGURE` constants) actually hold for disc-4's real file, and would it hold for a
   Path-D world's own pack (if one is ever built)? — **Experiment:** `py -m ff9mapkit world-extract
   --disc 4` (or equivalent) against the live install and diff the parsed shape against disc-1's; cheap,
   offline, no engine involvement. Not needed until §8's "encounters" scope is actually opened.
4. What does `WorldConfiguration.GetDisc()`/`WMWorld.SetDisc()` actually do at runtime with a disc value
   outside `{1,4}` (e.g. does `AssetManager.Load<GameObject>` returning `null` NRE immediately at
   `WMWorld.cs:552`, as the source suggests, or is there an untraced guard)? — **Experiment:** this plan's
   architecture (§3 Rung 2) deliberately avoids ever needing to answer this by keeping `currentDisc` at 1;
   only relevant if forced onto the §4 fallback patch. If needed: debug-menu `SetDisc(5)` and watch
   `Memoria.log` for the exact crash signature.
5. Is `Wrap()`'s `while (!this.Wrap())` loop in `OnInitialize()` genuinely safe on a synthetic array (this
   session's read says likely-safe because `w_moveActorPtr` is null/dummy at that point, but this is
   inference, not proof)? — **Experiment:** covered by Rung 0's own success/failure signal; watch
   specifically for a hang (not just a crash) during the spike.
6. Does any OTHER hardcoded table beyond `EventDB`/`eventIDToMESID` assume exactly the 13 known `wldMapNo`
   values (r3's flagged unknown — minimap tables, save schema, netsync)? — **Experiment:** a targeted
   grep sweep (`grep -rn "wldMapNo\s*==" --include=*.cs`, `grep -rn "9000\|9001\|...\|9012" --include=*.cs`
   restricted to comparison/switch contexts) before Rung 1, cheap and offline; this session did not run
   it exhaustively.
7. Whether `w_naviLocationPos`'s outer `[2,64]` dimension (r5, `ff9.cs:10393`) or the continent-title switch
   (r5, `ff9.cs:8838-8852`, session-corrected from the task's originally-cited but wrong line 8683) would
   throw or silently no-op for a Path-D world's `wldMapNo`/`w_naviMapno` — **Experiment:** covered
   implicitly by Rung 2/4's in-game verify (watch the minimap and any title-banner UI for a crash vs. a
   silently-blank/degenerate render); not worth a dedicated probe before then, and explicitly **out of
   scope to fix** at this stage (§8).
8. Whether `texgates.py`'s acceptance thresholds (calibrated only against disc-1 stock samples) generalize
   to synthesized Path-D terrain — **Experiment:** run the existing `texgates` calibration harness
   (`studies/overworld-topography/out/foldback/texgates_calibration_raw.json`'s generating script) against
   Rung 3's first authored cells and compare pass rates to the disc-1 baseline, offline.
9. r6's own closing caveat, worth repeating verbatim as a plan-level discipline: **every "already
   generalizes" verdict in r6's census is a claim about the *code*, not about whether the underlying *data*
   (a 4th disc-shaped container, a matching table shape) exists or would parse correctly** — no agent
   executed anything against the live install this session for the world/ package specifically (this
   plan's own re-verification pass focused on engine C# and two kit facts, not a full kit-side runtime
   probe). **Recommended standing discipline for every rung above: run the relevant kit function against
   the real install once, offline, before trusting its "generalizes" label in a deploy.**

## 7. Honest cost/risk assessment

| Rung | Size | Can it fail and force a redesign? |
|---|---|---|
| 0 — WorldDisc spike | **S** (one throwaway patch, one in-game check) | **Yes — the pivotal one.** Failure forces the entire plan onto the §4 fallback (real 3rd disc + baked AssetBundle asset), which is **XL** and blocked on an asset-authoring capability the project doesn't currently have (unknown #2, §6). This is why it's Rung 0 and not buried later. |
| 1 — WorldScene directive | **S** (one small `DataPatchers.cs` branch, one `blank_world_bytes()` kit function) | **Low risk.** Heavily precedented (`FieldScene`/`BattleScene` copy-paste), and r3's decoupling claim was independently confirmed this session by direct source read of both sides of the boundary. Safe incremental win regardless of Rung 0's outcome — it's useful infrastructure even under the §4 fallback. |
| 2 — Minimal third world (combine 0+1) | **M–L** | Depends entirely on Rung 0. If Rung 0 succeeds, this is mostly plumbing + the untested sentinel-namespace fork (a real but contained risk — worst case it needs a second small design iteration, not a rewrite). If Rung 0 partially succeeds (world loads but some subsystem misbehaves), this rung absorbs that risk. |
| 3 — Shape the grid | **M** (mostly reuse) | Low engineering risk (14 already-generic kit builders per r6) but real **design/calibration** risk (texgates thresholds, §6 unknown #8) — could require a full re-calibration pass, not a redesign. |
| 4 — Entrance/exit | **M** | Low-to-moderate; the missing "build a switch from zero" helper is a bounded, well-scoped gap (r4 already named the exact primitives needed), not an unknown. |
| §4 fallback (real 3rd disc, only if Rung 0 fails) | **XL** | This is the redesign path itself — new engine gates in 3 places (r1/r5) *plus* a genuinely new baked Unity asset the toolkit cannot currently author. Treat as a separate, much larger initiative if reached. |

**Overall sizing for "a genuinely third, minimally playable overworld" (Rungs 0–4, Rung 0 succeeding): L,
multi-session, mostly kit-side once the two engine patches (s71/s72) land.** If Rung 0 fails: XL and gated
on a capability (Unity asset authoring) this plan cannot scope without first answering §6 unknown #2.

## 8. What NOT to build yet

Scope discipline, grounded in r5's census of exactly which per-world tables are dense/hardcoded vs open —
**all of the following are tempting because the kit's Python side already "generalizes" over them, but
every one of them either (a) is capped by a dense or hardcoded engine table unrelated to Rungs 0-4's actual
gates, or (b) only matters once a Path-D world already exists and is entered, i.e. is pure polish on top of
an unproven foundation:**

- **Encounters / a real `discmr.img` pack for the new world.** `w_worldZoneFigure`/`w_worldZoneInfo`
  (`Byte[26]` each, `ff9.cs:1415-1444`) and `w_worldAreaZone` (`Byte[64]`, **fully dense, all 64 slots
  used**, `ff9.cs:1348-1414`) are hardcoded-size tables with **no free area id** — giving a new world its
  own unentangled zone requires an engine change to widen them (r5), and even then `w_fileSystemConstructor`
  (`ff9.cs:3621-3644`) has no third `w_fileImagenameServer` slot to load a distinct pack file from at all.
  A Path-D world can get *some* encounters for free by reusing an existing area id (data-only), but that
  silently entangles with whatever real stock place currently owns that zone — acceptable as a documented
  placeholder, not as a shipped design. **Wait until Rungs 0-4 are proven; then decide whether reused-zone
  encounters are good enough or whether the table-widening engine work is worth it.**
- **Minimap landmark markers for the new world.** `w_naviLocationPos` (`ff9.navipos[2,64]`,
  `ff9.cs:10393`) has a hardcoded **2-world outer dimension**; `w_naviMapno`'s selector is a hardcoded
  `w_frameScenePtr >= 5990` threshold (`ff9.cs:8833-8836`), not derived from `wldMapNo` or `currentDisc` at
  all. Getting markers onto a Path-D world is a real engine change (widen `[2,64]` → `[3,64]`, extend
  `w_naviGetPos`'s if/else-if, `ff9.cs:7094-7110`) that is **entirely orthogonal to whether the world
  exists and is enterable** — pure UI polish. Defer.
- **A distinct continent-title banner.** Two independent hardcoded ceilings stack (r5, session-corrected
  line number): the `w_frameScenePtr`→`titleId` switch (`ff9.cs:8838-8852`, exactly 4 literal
  `scenePtr` cases, no data hook) and `GetContinentName`'s 4-case switch (`WorldConfiguration.cs:343-353`,
  falls through to `String.Empty` on a miss — silent, not a crash, which is itself a reason it's safe to
  simply leave blank for now rather than engineer). **Ship with no banner; it degrades gracefully.**
- **Vehicles on the new world.** `w_fileImagenameServer1`/`Server4`'s 2-way branch (`ff9.cs:3621-3644`)
  gates the model/stat/temp pack files vehicles' physics data ultimately derives from, same table family as
  encounters above. The existing `TransportControls.csv`-driven vehicle system (`project-ff9-overworld-vehicles`)
  is proven on the *existing* two discs; porting it to a Path-D world is a distinct, separately-scoped
  effort layered on top of a working Rung 2-4, not part of them.
- **A named `WorldPlace`/`WorldEffect` semantic hook** (e.g. a bespoke "this world's own destroyed-town
  toggle") — both are closed C# enums (`Memoria/World/WorldPlace.cs`, `Memoria/World/WorldEffect.cs`, r5);
  a new named concept needs an enum-member engine change. The *unkeyed* `Mist`/`Rain`/`Light`/`Title`
  NCalc tokens remain genuinely open for weather/lighting polish once there's a world to polish — but
  that's a later rung, not part of proving the world exists.
- **`environment.py`'s `Disc4` keyword generalization** and **`locate.py`'s multi-dispatcher rework** (§5) —
  both are real, identified kit gaps, but neither blocks Rungs 0-4; both are pure authoring-convenience work
  for whenever a Path-D world needs its own weather condition or its own entrance-geography tooling, which
  is downstream of "does the world exist at all."

**The one-sentence discipline:** every item above answers "how does the new world *feel* once it's real";
Rungs 0-2 answer "is a new world even *possible*." Do not spend an engine round on any of §8 before Rung 2
has an owner-confirmed in-game check, exactly the way the scene-ladder study didn't wire minimap/vehicle
polish before its own core rig-and-dispatch loop closed.