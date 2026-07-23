# B4 — What Can We EXTRACT or TRACK to Enable Authoring?

Synthesis slice. Turns the A1–A5 decode into a **ranked engineering menu**, each item tagged
`TRACK` (read live), `AUTHOR` (understand → build), or `BLOCKED` (provenance / runtime-only).

Inputs consumed: `A1-hi-roster.md`, `A2-summon-struct.md`, `A3-managed-boundary.md`,
`A4-primitive-space.md`, `A5-camera-native.md`, and `Memoria/Battle/SFX/SfxMeshProbe.cs` (the
existing s47/s48/s50 probe). B1/B2/B3 files were not yet on the blackboard at write time; their
findings are reconstructed here from the A-slices + calibration and flagged where load-bearing.

---

## 0. The one-paragraph synthesis

The decode splits the summon cinematic into three per-frame streams and tells us exactly which can
be recovered and how:

* **CAMERA — fully recoverable, live.** `SFX_UpdateCamera` hands managed code 13 floats = VIEW +
  near-Z every frame; C# already stamps them onto the Unity camera (`SFX.cs:1590-1605`), and the
  probe already logs them as `VIEW`/`PROJ` rows (`SfxMeshProbe.cs:229-238`). The native decode
  (A5) *ratifies* the managed camera path and confirms the camera is a **data-driven keyframe
  track** (curCam `@RVA 0x69730` fed by stepper fn `@0x2030` from the btlseq camera track) — so
  authoring the camera = authoring that track, the camera_codec lever we already have.
* **CREATURE PLACEMENT (root transform) — recoverable at RUNTIME ONLY, via a memory read, not a
  P/Invoke.** The DLL stores the creature's per-frame root world transform at `DATA+0x40`
  (A2 §5) and its per-bone matrices at `DATA+0x38` (A1/A2 §3), under `summonModels @RVA 0x220830`.
  These are **not** among the 13 exports (A3 §1) — managed code cannot *call* the getters — but the
  struct path is fully static, so a managed probe can **pointer-chase the DLL's own runtime memory**
  (module base + `0x220830` → `+0x00` → `+0x40`) to read the root each frame **without patching the
  DLL and without extracting any asset bytes**. This is the thing that fixes FLIGHT's staging.
* **CREATURE GEOMETRY / SILHOUETTE — only as post-GTE 2D screen primitives (`SFX_GetPrim`), lossy
  (A4).** The world transform is *consumed and discarded* inside the GTE before primitives cross the
  boundary; MESH bounds are pool-polluted to the origin. Recoverable: the on-screen path (from clean
  `PRIM` rows). Not recoverable from this stream: the world transform (that's why we need the memory
  read above). Extracting the actual model vertices/animation = provenance-BLOCKED, always.

---

## 1. The ranked menu

| # | Item | Tag | Buys | Effort |
|---|------|-----|------|--------|
| 1 | **ROOT-transform probe** — log the native summon root world matrix per frame via a managed memory read | TRACK | The staging fix: Bahamut's true per-frame world placement → parent Thomas there faithfully | LOW |
| 2 | **Reprojection-validation pass** — reproject the logged ROOT through the logged VIEW/PROJ, compare to `PRIM` screen centroid | TRACK | Proves ROOT lives in the exported camera's world space ⇒ closes "is v-whatever *faithful*, not just on-screen" | LOW (analysis-only, once #1 lands) |
| 3 | **`.seq` summon-op linter / cutscene inspector** — commit a parser for the summon opcodes + record layout | AUTHOR | Lints a `[[summon]]` block: HideMeshes hex validity, motion-frame range, TexAnim/ABR/RGB targets; powers a cutscene inspector | MEDIUM |
| 4 | **Per-mesh ABR / RGB / TexAnim authoring** — expose the native fine-grained mesh ops the `.seq` already supports | AUTHOR | Finer creature dressing than HideMeshes: per-mesh transparency, tint, UV-anim toggles | MEDIUM |
| 5 | **Camera-track authoring (camera_codec attack-slot sweep)** — confirmed still the right play | AUTHOR | Author the summon camera faithfully; validate authored cameras against captured VIEW/PROJ | (existing lever; decode = ratification) |
| 6 | **Stock Eidolon geometry / animation extraction** | BLOCKED | — | never |
| 7 | **Patched / redistributed `FF9SpecialEffectPlugin.dll`** (e.g. adding a bone-matrix export) | BLOCKED | — | never |

---

## 2. TRACK #1 — the ROOT-transform probe (the FLIGHT-staging fix)

**What it fixes.** FLIGHT v7 is "in-frame by construction (551/551)" but its *faithfulness* — "Thomas
is wherever Bahamut was" — is unvalidated because no data-side method recovers Bahamut's world
transform (A4 §6, README). The root transform at `DATA+0x40` IS that placement (A2 §5): the pose
evaluator `@0x186a0` builds it each `Hi_DrawSummonModel` from the `(rot,pos)` args, i.e. it is the
creature's per-frame **world root**. Reading it per frame gives the exact staging curve to hang a
replacement model on.

**Why a memory read, not a P/Invoke.** The 13 exports (A3 §1) are the *entire* native contract, and
none of them is a bone/matrix/transform getter. `Hi_GetSummonBoneMatrix @0x18630` and
`Hi_GetSummonBonePos @0x185b0` are **interpreter-internal** ops (A1 §2 — reached only through the
`.seq` mega-interpreter `@0xeea4`), not exports. So managed code cannot *call* them. But A1/A2/A5 all
establish the **struct path is fully static**: `summonModels` base RVA `0x220830`, stride `0x58`,
`rec+0x00` → DATA, root at `DATA+0x40` (rot `+0x40`, trans `+0x54/+0x58/+0x5c`), gated by `rec+0x50`
active. Managed C# can resolve the plugin's load base (`Process.Modules`) and `Marshal.Read*` that
chain directly — reading the DLL's *own runtime state*, not modifying it.

**Provenance verdict: SANCTIONED, with a hard scope line.** Reading to understand is allowed; we do
not patch or redistribute the DLL, and we do not write asset bytes. The **root transform is
choreography/staging** — the same class of data as the camera track we already log — NOT geometry
(no vertices) and NOT the animation clip. **Do NOT log the full per-bone matrix array across frames**
(`DATA+0x38[]`): dumping every bone's pose over a whole cast would reconstruct the skeletal animation
= extracting stock animation bytes = BLOCKED. The probe must log **the single root matrix only**.

**Smallest viable probe patch (managed-only, `memoria-patches/`, never a shipped DLL):**

Add to `Memoria/Battle/SFX/SfxMeshProbe.cs` a new `ROOT` row, resolved once and read in the existing
per-frame hook that already fires alongside `LogFrame`/`LogCamera` in `SFXDataMesh.Runtime.Render()`.

```csharp
// s51 (proposed) -- read the native summon ROOT world transform straight out of the plugin's
// runtime memory using the STATICALLY-recovered layout (studies/.../disasm/A2 §5, A1 §1).
// summonModels @ RVA 0x220830, stride 0x58; rec+0x00 -> DATA; root PSX MATRIX @ DATA+0x40
// (rot 9xInt16 @+0x40, trans 3xInt32 @+0x54/+0x58/+0x5c); active gate rec+0x50.
// Managed MEMORY READ of the plugin's own state -- NOT a DLL patch, NOT asset bytes.
// Logs ONLY the root (staging/choreography, camera-class), never the per-bone array.
private static IntPtr _pluginBase = IntPtr.Zero;
private static Boolean _pluginBaseTried;

private static IntPtr PluginBase()
{
    if (_pluginBaseTried) return _pluginBase;
    _pluginBaseTried = true;
    try {
        foreach (System.Diagnostics.ProcessModule m in
                 System.Diagnostics.Process.GetCurrentProcess().Modules) {
            if (m.ModuleName != null &&
                m.ModuleName.StartsWith("FF9SpecialEffectPlugin",
                    StringComparison.OrdinalIgnoreCase)) {
                _pluginBase = m.BaseAddress; break;
            }
        }
    } catch { }
    return _pluginBase;
}

public static void LogSummonRoot()   // call right after LogCamera(camera) in Runtime.Render()
{
    if (!Enabled) return;
    StreamWriter w = Writer;
    if (w == null) return;
    try {
        IntPtr b = PluginBase();
        if (b == IntPtr.Zero) return;
        IntPtr rec = b + 0x220830;                       // &summonModels[0]  (slot 0; LENGTH==1, A2 §1)
        if (Marshal.ReadByte(rec + 0x50) == 0) return;   // not active -> no summon loaded this frame
        IntPtr data = (IntPtr)Marshal.ReadInt64(rec);    // DATA block ptr
        if (data == IntPtr.Zero) return;
        // root rotation (9x Int16, GTE fp12 /4096) then translation (3x Int32, GTE world units)
        Int16 r0=Marshal.ReadInt16(data+0x40), r1=Marshal.ReadInt16(data+0x42), r2=Marshal.ReadInt16(data+0x44);
        Int16 r3=Marshal.ReadInt16(data+0x46), r4=Marshal.ReadInt16(data+0x48), r5=Marshal.ReadInt16(data+0x4A);
        Int16 r6=Marshal.ReadInt16(data+0x4C), r7=Marshal.ReadInt16(data+0x4E), r8=Marshal.ReadInt16(data+0x50);
        Int32 tx=Marshal.ReadInt32(data+0x54), ty=Marshal.ReadInt32(data+0x58), tz=Marshal.ReadInt32(data+0x5C);
        w.WriteLine(String.Format(CultureInfo.InvariantCulture,
            "ROOT,{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12}",
            SFX.frameIndex, r0,r1,r2,r3,r4,r5,r6,r7,r8, tx,ty,tz));
        w.Flush();
    } catch {
        // A probe must never take the battle render down with it.
    }
}
```

Gate it on the same `Enabled` flag (or a new `[SfxProbe] CaptureRoot=1` sub-flag mirroring
`CapturePrims`). One call site: alongside `SfxMeshProbe.LogCamera(camera)` in
`Memoria/Battle/SFX/SFXDataMesh.cs` (`Runtime.Render()`, the `:643/:648` co-located hook). Zero-cost
when disabled (single bool read). **Files touched:** `SfxMeshProbe.cs` (+~45 lines), `SFXDataMesh.cs`
(+1 call). Nothing else. **Effort: LOW.**

**Caveats to record with the data:**
* `rec+0x50` active and `data != 0` are the only validity guards; the whole read is `try`-wrapped so
  a stale/torn pointer during teardown (cleared at `@0xf90d`, A2 §2) can never crash the render.
* Slot is hard-coded 0 (array LENGTH == 1, A2 §1). Correct for all stock single-creature summons.
* The root at `DATA+0x40` is overwritten every Draw from the Draw args; between the constructor seed
  (`@0x1691f`) and the first Draw it holds the seed, not a live pose — only rows during active
  drawing are meaningful (they'll have advancing `SFX.frameIndex`).

---

## 3. TRACK #2 — the reprojection-validation pass

Once #1 logs `ROOT` and the probe already logs `VIEW`/`PROJ` on the same `SFX.frameIndex`, an
**offline** analysis (no new engine code) can test the load-bearing hypothesis:

> `screen ≈ PROJ · VIEW · (ROOT.translation, in GTE world units)` should land on the per-frame
> `PRIM` screen centroid of the creature's body keys (A4 §7).

If it does, we have proven the ROOT transform lives in the **same world space** the exported camera
uses (A5 §7's "projection identity" `screen = PROJ·VIEW·world`), which means: (a) the ROOT read is
the genuine world placement, and (b) parenting Thomas at that world transform tracks him for free
under `Camera.main` — the honest form of "faithful = wherever Bahamut *was*," not merely "on screen."
If it does NOT match, ROOT is in a different basis (e.g. seated relative to `curCam` per
`resolve_position @0x147f4`, A5 §5) and the transform must be composed with that basis first — the
mismatch itself tells us which. Either way this is the experiment that converts FLIGHT from
"in-frame by construction" to "validated faithful." **Uses:** `matrix_solve.py` (already the
projection lib) + the extended log. **Effort: LOW, analysis-only.**

---

## 4. AUTHOR #3 — the `.seq` summon-op linter / cutscene inspector

**What it is.** A committable format parser (no stock bytes) that decodes the summon-relevant slice
of the `.seq`/SFX command stream and the runtime record layout, for linting `[[summon]]` blocks and
building a cutscene inspector. Grounds:

* **Opcode → handler map** from the `.rdata` dispatch table `tbl@0x68780..0x68cf8` (A1 §2/§3): each
  summon op's table slot is enumerated (e.g. `Hi_HideSummonModelMesh` `tbl@0x68c70`,
  `Hi_SetSummonMotion` `tbl@0x68850`, `Hi_DrawSummonModel` `tbl@0x68848`, `Hi_StartSummonTexAnim`
  `tbl@0x687e0`, `Hi_ModifySummonModelAbr` `tbl@0x68c18`, `Hi_ModifySummonModelRGB` `tbl@0x68988`).
* **Argument semantics** from A2: HideMeshes = a **u32 bitmask, set-bit = hidden, ≤32 slots**
  (`DATA+0x20`); motion frame must be `< frameCount = u16[motion+2]` (`SetSummonMotFrame` clamp
  `@0x17aac`); TexAnim indexes a stride-`0x18` array (`DATA+0x70`); ABR `0xff` = no-op sentinel
  (`@0x18af7`).

**What it enables (all without extracting stock bytes):**
* Lint a `[[summon]]` HideMeshes hex: warn on bits ≥ the model's mesh count, warn on the full-mask
  "hide everything" foot-gun, explain "set bit = hidden."
* Lint SetSummonMotFrame values against the clip's `frameCount` (catch the silent `frame=0` reset).
* A **cutscene inspector**: given a cast, correlate the ROOT/VIEW/PROJ/PRIM probe streams into a
  per-frame timeline (creature placement + camera + on-screen footprint) — a debugging/authoring view.

**Provenance verdict: SANCTIONED.** This writes analysis + a parser for our own `[[summon]]` authoring
grammar and the decoded op semantics; it reads no shippable asset bytes and produces no DLL. **Files:**
new module under `ff9mapkit/` (the study milestone already names "the `.seq` codec/linter"); consumes
this disasm dir's tables. **Effort: MEDIUM.**

---

## 5. AUTHOR #4 — per-mesh ABR / RGB / TexAnim (finer than HideMeshes)

**The B2 question — does native give finer control than our HideMeshes, worth exposing?** Yes, and a
precision correction is owed first:

* Our shipping **`HideMeshes=<hex>`** operates **managed-side, post-`SFX_GetPrim`**: it filters the
  harvested primitive stream by `SFXMeshBase._key` (the SFXKey ABR/texture/tpage hash) —
  `BattleActionCode.cs` `TryGetArgMeshList`. It culls *after* rasterization, keyed by a blend/texture
  hash.
* The **native `DATA+0x20` hideMask** (A2 §2) is set by `Hi_HideSummonModelMesh(meshIdx)` as a bit
  per **mesh ordinal**, checked *inside* `Hi_DrawSummonModel` *before* the mesh is rasterized to
  primitives. Different layer, different index space. A2 §2's "the hex IS this bitmask" is therefore
  **imprecise** — they are two distinct culling mechanisms; useful to record as a correction, because
  it means our HideMeshes and the native op are not interchangeable and can even disagree.

**What native adds beyond hide** — driven by `.seq` ops we can author (all in the dispatch table):
* `Hi_ModifySummonModelAbr` (`tbl@0x68c18`) — per-mesh **semi-transparency / blend mode**.
* `Hi_ModifySummonModelRGB` (`tbl@0x68988`) — per-mesh **RGB tint**.
* `Hi_StartSummonTexAnim`/`Stop` (`tbl@0x687e0/0x687d8`) — per-mesh **UV/texture animation** toggle.

Exposing these in the `[[summon]]` grammar gives creature dressing our HideMeshes can't: fade a mesh
instead of hard-hiding it, recolor, or start/stop a texture scroll — the vocabulary a real authored
summon needs. **Provenance: SANCTIONED** (we emit `.seq` data, not a DLL). **Effort: MEDIUM** — needs
the `.seq` opcode+arg encoding for these three confirmed against a real cast (the linter in #3 is the
natural home). **Caveat:** the exact `.seq` byte encoding of each op's operands is NOT yet decoded
here (A1 gives the handler + the runtime effect, not the on-disk operand layout) — that decode is the
gating sub-task before this ships.

---

## 6. AUTHOR #5 — the camera lever (confirmed, not superseded)

**Is a managed camera-authoring lever (camera_codec attack-slot sweep) still the right play vs
anything the native decode opened?** **Yes — the decode ratifies it, opens nothing better.** A5
establishes the summon camera is a **keyframe-animation track**: `curCam @0x69730` is filled by the
stepper `@0x2030` accumulating a translation/rotation track (`@0x2087/0x207c`), seeded from the
loaded btlseq camera data. `SFX_UpdateCamera` just converts the currently-installed camera to the 13
floats. So there is **no hidden native "camera brain"** to hook — the camera is *data*, exactly the
thing camera_codec authors. Two concrete affordances the decode grants:

1. **Author** the summon camera by writing the attack-slot camera track (the existing camera_codec
   sweep); the per-frame **zoom is a single scalar** — the near-Z `array[12]` = curCam `H @0x69750`
   (A5 §3), so a "47°→24° push-in" is one animated value, not an FOV field.
2. **Validate** any authored camera by capturing the live `VIEW`/`PROJ` probe rows and diffing
   against intent — the boundary hands the whole matrix over cleanly every frame (A3 §4).

**Provenance: SANCTIONED** (managed authoring of a data track). **Effort: existing lever**; the decode
is confirmation + the zoom-is-near-Z simplification.

---

## 7. BLOCKED (provenance / runtime-only)

* **Stock Eidolon geometry (vertices/UVs) or animation clips (per-bone keyframes).** Never written
  anywhere. The model + motion live inside `ef###.bytes`, opaque across the boundary (A3 §3); the
  per-bone matrix array (`DATA+0x38[]`) is runtime scratch and dumping it across frames reconstructs
  the animation asset. Hard line: probe logs the **root only** (§2), never the bone array over time.
* **A patched or redistributed `FF9SpecialEffectPlugin.dll`.** The clean way to *call*
  `Hi_GetSummonBoneMatrix` from managed code would be to add an export — **BLOCKED**. The sanctioned
  substitute is the managed memory read (§2), which touches no DLL bytes. (Patching the *open-source
  Memoria Assembly-CSharp* — where `SfxMeshProbe.cs` lives — is the normal, sanctioned lane; that is
  not the SE binary.)
* **Inverting `SFX_GetPrim` / MESH bounds to a world transform.** Not a provenance block but a
  physics one (A4): the transform was consumed by the GTE; the primitives are screen-space, the MESH
  bounds pool-polluted to the origin. Any "reproject the bounds as a world position" method is VOID
  (A4 §6). The world transform must come from §2's memory read, not this stream.

---

## 8. The single recommended next action

**Land TRACK #1 (the ROOT probe) + TRACK #2 (the reprojection check).** It is LOW effort, managed-only
on `memoria-patches/`, provenance-clean (root = choreography, not asset bytes; no DLL patch), and it
is the ONE thing that closes the study's actual open problem — the creature's true per-frame staging
that "no data-side method could recover." A single instrumented cast yields the ROOT curve; the
reprojection check confirms it's the faithful world placement; FLIGHT then hangs Thomas on real data
instead of on constructed coverage.

---

## 9. Provenance

Analysis + a proposed managed-only probe patch outline + committable-parser scope. No stock
geometry/animation bytes written; no DLL patched or redistributed. The proposed probe reads the
plugin's **runtime** memory (root transform only) using statically-recovered offsets — a read, not a
modification. Every native claim cites `fn@rva`; every managed claim cites `file:line`. Runtime values
(`0x220830`+ scratch, `DATA` block) are zero-on-disk and are only ever *read live*, never asserted
statically.
