# CAST-PROTOCOL — arming PRIM capture for the M0 depth gate (item (d) prep)

**Status: PROTOCOL ONLY.** Nothing below has been executed by the agent that wrote this document — no
`Memoria.ini` edit, no file copy, no relaunch, no cast. Per this round's brief, those are the user's/a
future agent's actions to take; this file is instructions for that, not a record of what already
happened. All facts below (ini state, deployed-DLL contents, log row tallies) were gathered by
**read-only** inspection of the live install.

---

## 0. Why this exists

`m0/depth_gate.py` (this directory) needs `PRIM` rows to do anything — the live
`sfxmeshprobe.log` currently has none (`CapturePrims` was never armed on the capture that produced it).
Running `depth_gate.py` against it today prints exactly this and exits 0 (verified this round — see the
findings). This document is the full protocol for the ONE cast that unblocks it.

---

> **⚠ ADDENDUM 2026-07-24 — §1's warning MATERIALIZED before the archive happened.** The 5-cast
> log this protocol was written to protect was destroyed at 2026-07-23 ~16:40 by a concurrent
> game relaunch (the user runs many parallel sessions; the install is shared mutable state). The
> round-1 analyses (CAMERA-MATCH / CALIBRATION / EULER) stand as verified records, but their
> reproduction commands against the live log are broken until the next capture — see
> `VERIFY-EULER.md`. Consequences: (a) §1's copy step now applies to **every future capture**,
> and `depth_gate.py` **auto-archives** the live log to `C:\gd\SCRATCH\summon-transplant\logs\`
> before parsing (mtime-keyed, analyzes the snapshot); (b) the ONE cast below now re-establishes
> **everything** — ROOT/MODEL/BONES for the empirical Euler leg *and* the missing PRIM lane —
> since all six existing flags stay armed and the three PRIM lines are added. Standing rule →
> memory `feedback-archive-capture-logs-immediately`.

## 1. Archive the current log FIRST — relaunching WILL destroy it

**The log truncates on every fresh process, not just on first open.** The write path is
`Stream stream = new FileStream(LogPath, FileMode.Create, FileAccess.Write, FileShare.Read);`
(`C:/gd/FFIX/Memoria/Assembly-CSharp/Memoria/Battle/SFX/SfxMeshProbe.cs:228`), lazily run the first time
*anything* is logged in a process (`SfxMeshProbe.cs:34-36`'s own doc comment: *"a CSV-ish per-session
log, recreated (`FileMode.Create`) at the first write of a process — so every game launch starts a fresh
file, never an ever-growing one"*) — `PROBE.md` §3 independently states the same thing. `FileMode.Create`
truncates an existing file to zero length before writing. **Any relaunch with `Enabled=1` still set (and
it is, and must stay set) wipes the current ~22 MB / 5-cast log the instant the game next logs anything.**

Before touching `Memoria.ini`, copy it out:

```
copy "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log" ^
     "C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.20260723-preprim-5casts.log"
```

(`C:/gd/SCRATCH/summon-transplant/` already exists as this study's local-only stock-derived-artifact
folder; `logs/` is a new subfolder under it — create it if `copy`/`mkdir` doesn't do so automatically.)
This preserves the 5-cast PSXCAM/MODEL/BONES dataset every other M0 sub-item and `flight_v9_solve.py` /
`matrix_solve.py` / `root_reproject.py` were built and verified against, untouched, for later comparison
or re-analysis.

---

## 2. No engine rebuild needed — verified by direct binary inspection, correcting a stale doc

`PROBE.md` §9 still says *"⚠ `s48-sfx-output-capture.patch` is AUTHORED AND STATICALLY VERIFIED ONLY — it
has not been compiled or deployed."* **That line is stale.** `memoria-patches/README.md`'s own s48 row
says s48 (which adds `CapturePrims`/`LogPrim`) was *"★ BUILT + DEPLOYED 2026-07-22 ... the CapturePrims
works"*, and the currently-deployed DLL is s53's build (built on s52, itself sequentially after s47/s48).
A sibling agent's `m0/M1A-PLAN.md` flagged the same staleness from the changelog; this round
**independently re-confirmed it by reading the deployed bytes directly**, not just trusting either
document:

```powershell
$path = 'C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/x64/FF9_Data/Managed/Assembly-CSharp.dll'
(Get-FileHash $path -Algorithm SHA256).Hash
# -> 3CCA581CC551882BFFED0C1408E4D2A0E9FA8E86BF0B3F3CBB315EFD14D5FC4B  (matches s53's recorded build sha "3cca581c…")
```

Searching the same file's bytes for the relevant identifiers (ASCII for compiled metadata *names* —
type/method/field names live in the ECMA-335 `#Strings` heap, UTF-8/single-byte; UTF-16 for string
*literals* used in code — ini-key names and log-row tags live in the `#US` heap, UTF-16) finds **all** of
`LogPrim`, `CapturePrims`, `PrimSummary`, `CaptureModels`, `LogModels`, `ModelsBoneCount` (ASCII —
identifiers) and `PrimCap`, `PSXCAM`, `PRIM CAPTURE TRUNCATED`, `ModelsCap` (UTF-16 — literals) present in
the currently-deployed x64 DLL. **`CapturePrims` is already compiled in; arming it is a pure
`Memoria.ini` edit + relaunch, not a DLL rebuild.** (No engine build tooling was invoked to confirm this —
only reading the already-deployed file's bytes.)

---

## 3. The `Memoria.ini` edit

Current live `[SfxProbe]` section (read this round, verbatim):

```ini
[SfxProbe]
Enabled = 1
CaptureRoot = 1
CaptureModels = 1
ModelsActiveOnly = 1
ModelsCap = 120000
ModelsBoneCount = 93
```

**Change it to** (KEEP all six existing lines exactly as-is — the brief is explicit that these stay; ADD
the three below):

```ini
[SfxProbe]
Enabled = 1
CaptureRoot = 1
CaptureModels = 1
ModelsActiveOnly = 1
ModelsCap = 120000
ModelsBoneCount = 93
CapturePrims = 1
PrimSummary = 0
PrimCap = 3000000
```

Notes on the three additions:

- **`CapturePrims = 1`** — the one flag that actually matters this round; arms `SfxMeshProbe.LogPrim()`
  (hooked at the top of `SFXRender.Add()`, `Global/SFXRender/SFXRender.cs:209-216` — every decoded native
  primitive, before mesh-batching).
- **`PrimSummary = 0`** — explicit, though it's also the default. **Do NOT set this to 1** — `PrimSummary=1`
  collapses to one `PRIMSUM` row per frame (a count + a bounding box), which has **no per-primitive
  `otz`/`x`/`y`** and is useless for `depth_gate.py` (it needs the individual `PRIM` rows).
- **`PrimCap = 3000000`**, raised from the 200000 default. `FORMAT.md` §L541/§600 warns a full cast can
  emit **10–100×** the ~17,000–19,000 MESH-row-per-cast volume at the raw-primitive level — i.e.
  plausibly 170,000–1,900,000 `PRIM` rows for ONE ~40 s cast. The default 200000 cap would almost
  certainly truncate partway through (visibly — a `# PRIM CAPTURE TRUNCATED` marker line, never silent —
  but still not what we want: a cast that stops recording PRIM data before the fire-column phase misses
  exactly the frames most likely to show body-wrapping interleave). 3,000,000 gives headroom above the
  upper estimate for a single cast.

Expect the resulting log to be substantially larger than the current ~22 MB **for a single cast** (the
current 22 MB holds 5 casts of PSXCAM/MODEL/BONES/MESH/CAM/VIEW/PROJ/ROOT data with **zero** PRIM rows;
one cast's worth of PRIM rows alone could plausibly add tens of MB). Not a problem for `depth_gate.py`
(it streams, never loads the whole file) — just don't be surprised.

---

## 4. What to have deployed on the bench for THIS cast

**Recommendation: run `py studies/custom-summons/thomas-swap/build_thomas.py --calibrate` — NOT a plain
`revert_thomas.py` (rung-7's resting state), and NOT leaving the currently-deployed FLIGHT v10.1 in
place.** Reasoning, worked from source rather than assumed:

**(a) Does FLIGHT v10.1's `HideMeshes=` actually suppress the creature's own `PRIM` rows?** The brief's
own framing says "hidden BODY meshes emit no body prims" as an established fact; tracing the *currently
deployed* mechanism's own code path this round finds otherwise, and the discrepancy matters enough to
flag rather than silently defer to either source:

- `SFXData.PlaySFX()` (`Memoria/Battle/SFX/SFXData.cs:136-154`) does nothing native — it only appends a
  `RunningInstance(frameStart, preventMeshByKey, preventMeshByIndex, ...)` to a managed list. No native
  call, no write into `SummonData`.
- `SFXDataMesh.cs Runtime.Render()` (`:611-669`): `SFXRender.Update()` (`:619`) runs **unconditionally**
  every frame `SFX.isUpdated` — this is the call that drives `SFX.SFX_GetPrim` → `SFXRender.Add(ptr)` →
  `SfxMeshProbe.LogPrim()` (`SFXRender.cs:79-86,209-216`). Nothing in that call chain reads
  `run.preventedMeshKeys` at all.
  `run.preventedMeshKeys` is checked **only** in the *later*, separate loop at `:661-670`, which decides
  whether to actually call `SFXRender.commandBuffer[i].Render(i)` (the `DrawMeshNow` draw) for an
  *already-batched* `SFXMesh` — i.e. it is a **visual, post-decode, post-log suppression**: skip painting
  this mesh to the screen, not skip generating/logging its primitives.
- Consequence: for the **managed** `HideMeshes=` mechanism FLIGHT v10.1 uses (`BattleActionCode.cs:394-419
  TryGetArgMeshList`, TRANSPLANT.md §2.1's "safer first cut... needs no native write"), `LogPrim` should
  fire for the creature's own body primitives **the same as if nothing were hidden** — the prevention
  happens strictly downstream of the probe hook. This is a *different* mechanism from the one FORMAT.md
  §3.4 documents as genuinely preventing primitive generation (the **native** mask at `SummonData+0x20`,
  ops 157/158, "a hidden mesh's polys are never generated — they never enter the GTE, the ordering table,
  or `SFX_GetPrim`") — that native write is explicitly **not yet built** (TRANSPLANT.md §2.1: an "owner
  go/no-go" feature, deferred) and is **not** what FLIGHT v10.1 currently uses.
- So: on my own read, whether FLIGHT v10.1 is deployed or not should **not** change what `PRIM` rows get
  logged for the creature's own body — only what gets *drawn to the screen* (irrelevant to an offline log
  analysis). Take this as a **flagged, sourced disagreement with the brief's framing**, not a confident
  override of it — if a future round finds a *different* hide path actually in play (e.g. the native mask
  after all, or a `SFXMesh.Begin()`-time key filter this trace missed), re-derive from there.

**(b) `Reflect=True` is not a FLIGHT-v10.1-specific perturbation.** `build_thomas.py:139`:
`ANCHOR_BASE = "PlaySFX: SFX=Bahamut__Full ; Reflect=True"` — this is the **common base line for every
mode this script emits, including `--calibrate`** (`:38,67`: *"`--calibrate` omits the [HideMeshes]
clause entirely (Bahamut's real mesh renders... byte-identical to the stock donor's own line)"* still
includes `Reflect=True`). The existing (5-cast) PSXCAM/BONES/MODEL data in the current log was itself
captured under this same bench convention. `Reflect` is not something to "revert away" — it's the bench's
standing baseline.

**(c) The one thing `--calibrate` removes that this trace could not fully rule out:** FLIGHT v10.1's
`PlayerSequence.seq` also splices in a custom `StartThread…EndThread` block driving **Thomas's own actor**
(a separate managed object) in parallel with the native Bahamut cast. This trace found no evidence it
touches `SummonData`/`PsxCtx`/`SFX.frameIndex` (it should be driving an unrelated managed actor via
ordinary `PlayAnimation`/`Turn`/`MoveToTarget`-style ops, not the native plugin), but "no evidence found
this round" is weaker than "removed entirely." **`--calibrate` is a single flag, already tooled, already
used for exactly this purpose in round 1** (`PROBE.md` §8: the s47 calibration cast — *"Bahamut's mesh
fully unsuppressed... this calibration cast pre-dates Thomas's own JSON mesh entirely"*) — it costs
nothing extra to remove the one variable this round couldn't fully close, so do that rather than rely on
the trace alone. **Do not use `revert_thomas.py`/rung-7 either** — rung-7's own resting state is *still* a
custom `ef084` splice (Iviv's clip, `Start=0/End=60`), not the byte-identical-to-stock-donor state
`--calibrate` specifically is.

**Net: run `py build_thomas.py --calibrate`, not `revert_thomas.py`, before the M0 cast.** Per `PROBE.md`
§2's own note, if the GEO mint (`3DModel 6200 GEO_MON_B0_M200`) is already registered (it is — confirmed
registered live, line 62/68 of `DictionaryPatch.txt`, per `m0/M1A-PLAN.md`'s own inspection this round),
`--calibrate` needs no *extra* relaunch beyond the one already required for the `Memoria.ini` edit above —
one relaunch covers both.

---

## 5. The cast itself

1. **Archive the log** (§1).
2. **Edit `Memoria.ini`** (§3) — close FF9 first if running.
3. **Run** `py studies/custom-summons/thomas-swap/build_thomas.py --calibrate` (deploys the calibration
   manifest into `ef084/`; see §4).
4. **Launch FF9 fresh** (both the ini change and the calibration deploy need a real relaunch — a `~`
   "Reload field" does not re-read `Memoria.ini`).
5. **Warp to the bench**: `~` → Warp → field **30300** (or load the bench save), get into the field's
   battle (scene **67**) — `PROBE.md` §2's established route.
6. **Cast Iviv → Spark → Bahamut Cinema.** Let the **whole** cast play through (chant → camera cut →
   charge → Mega-Flare → fire column → exit, ~40 s) — a partial cast under-samples exactly the phases
   (P8/P9 ground-reign, the fire-column tail) most likely to show body-wrapping interleave.
7. **Cast it ONCE.** (Multiple casts are fine mechanically — the MODEL-lane frame reset the orchestrator
   already identified for the existing 5-cast log would apply again — but one clean cast is all this
   round needs and keeps the log smaller.)
8. **Quit.** The log is complete once the cast has finished playing (every line flushed on write,
   `SfxMeshProbe.cs`'s own convention) — no need to wait for a clean process exit, but quitting normally
   is simplest.

---

## 6. What this one cast unblocks

- **`m0/depth_gate.py`'s real analysis** (this round's item (d)) — run
  `py m0/depth_gate.py` (defaults to the live install log) once the cast is done. It will no longer print
  the graceful-degrade message; it will print the per-frame/per-phase overlap table and a verdict. Sanity
  step first: run with `--verbose` on a short slice, or just read the printed `otz` percentiles, and
  sanity-check `DEPTH_EPS`/`AABB_PAD_PX` (both PLACEHOLDER constants in the script, flagged in its own
  docstring) against the real distribution before trusting the NATIVE/HYBRID verdict for real.
- **M0 sub-item (c)** (TRANSPLANT.md §2.4: *"fix the PSX→Unity scale/sign from the `BONES`/`PRIM` AABB"*)
  — also needs `PRIM` rows (cross-referencing the `BONES` world AABB against the `PRIM` screen AABB), so
  this same cast closes that gap too, not just item (d).
- **`FORMAT.md` §5.4 step 5's falsifiable prediction** (the creature's native-GTE-reprojected screen point
  should land inside its own `PRIM` AABB on framed frames) — `depth_gate.py`'s `self_calibrate_offset_x()`
  operationalizes a version of exactly this check (matching `PRIM`s by depth-and-y-proximity to the
  creature's own computed position) as a byproduct of building its widescreen-offset estimate; its printed
  `n=<samples>` count is a direct, free readout of whether that prediction is landing at all on this
  install's aspect ratio.
- **M0 sub-items (a)/(b)** (the camera-match / `VIEW`≈`PSXCAM` measurements) do **not** need this cast —
  they only need `PSXCAM`+`VIEW`/`PROJ`, already present in the archived 5-cast log; a sibling agent's
  work in this same `m0/` directory (`M1A-PLAN.md`) is scoped there, not blocked by this protocol.

---

## 7. Afterward (optional hygiene)

`CapturePrims=1` costs nothing on a normal, non-summon-casting play session (one cached-bool read per
call site, `SfxMeshProbe.cs`'s own zero-cost-when-off convention still applies — the flag only matters
while a native effect is actually decoding primitives). It is safe to leave armed. If a future round wants
smaller everyday logs, set `CapturePrims = 0` (or delete the three added lines) and relaunch — no rebuild,
same as arming it.
