# FORMAT.md — THE SUMMON-CUTSCENE ROUND REPORT

**The round:** decode `FF9SpecialEffectPlugin.dll`'s summon subsystem far enough to (a) settle what the
visible creature *is* and how to track it, and (b) state honestly what it would cost to make summon
cutscenes **decodable / re-importable like every other FF9 layer this project has hit**.

**Inputs:** phase artifacts `M1`–`M5`, `D1`–`D4`, the adversarial verifications `V-*.md`, and the prior
round's `FINDINGS.md` + `A1`–`A5` / `B1`–`B5`. Everything below is stated in its **post-verification**
form: claims the skeptic pass corrected are given corrected, and one prior headline is **retracted**
(§1.3).

All RVAs are image-base-relative for the user's own installed DLL (x64 `ImageBase 0x180000000`;
x86 `0x10000000`). C# cites are relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`. Runtime values live
in zero-on-disk `.bss`/heap — only **layout + logic** are static-recoverable, and runtime-only facts are
labelled as such.

**New this round (synthesis pass), and it is the headline:** the missing stage between the creature's
bone matrices and the pixels — **the world→screen matrix the plugin actually draws with** — is located,
named, and readable at a fixed RVA. §1.2. Reproduce with `py f1_viewmatrix.py`.

---

## 1. THE TRACKING ANSWER

### 1.1 What the visible creature IS — SETTLED

**The creature is the single summon-model slot. Not an eff-model slot, not several.**

The round's motivating hypothesis (that Bahamut might be drawn through the 32-slot `EFFARR` rather than
the 1-slot summon array) is **REFUTED**, independently and structurally:

| line of evidence | cite |
|---|---|
| An eff model is **rigid by construction** — all five `Hi_Register*EffModel` bodies store `0` into `DATA+0x10` (the motion-clip pointer), and the node builder branches on exactly that field | `0x15b17` `0x15bcb` `0x15caf` `0x15d9d` `0x15e7c`; branch `build_world_matrices@0x7820 : 0x7846` |
| There is **no API to bind a motion to an eff model** — the DLL's debug-string roster has `Hi_SetSummonMotion` / `Hi_SetSummonMotFrame` and **no** `Hi_Set*EffModel*Motion` | `refkit.py --list-strings Hi_`, 32 strings `0x4b090..0x4b628` |
| `Hi_DrawEffModelByBone` **reads the summon array** and copies a summon *bone's* world matrix into the eff model's root — eff models hang **off** the creature; they cannot replace it. An inactive summon slot there is a hard **hang**, not a skip | entry `0x167f0`, body cont. `0x16837`; summon array `0x168ea`, bone copy `0x1691b`–`0x16928`; bail → `0x16c80` → `0x151a0` self-loop |
| The summon array is **length 1** (`cmp eax,1; jl`), so there is exactly one creature slot | `Hi_RegisterSummonModel@0x15ee0 : 0x15f14` |
| The slot is **live and drawn** in a real cast: `SummonData+0x40` can be written by nothing but `pose_eval@0x186a0` reached from `Hi_DrawSummonModel@0x17767` (4 direct call sites, no indirect callers image-wide), and the existing log's ROOT rows go all-zero → varying at frame 82 with `active==1` throughout | `V-M1-05`; `sfxmeshprobe.log`, effect **227** = `Bahamut__Full` (`SpecialEffect.cs:99`) |

So: **`summonModels[0]` (RVA `0x220830`, stride `0x58`, `active` @`+0x50`, `data` @`+0x00`) is the
dragon.** The 32-slot `EFFARR` at `0x220230` (stride `0x30`, `active` @`+0x20`) holds its beams, rings,
sparks and props — frequently **hard-parented to one of its 93 bones**. `0x220230 + 32*0x30 == 0x220830`
exactly: the two arrays are adjacent, which is itself a check on all four EFFARR constants.

### 1.2 What its real per-frame transform IS — and the stage the study was missing

There are **three** transforms in the chain, not two. The study has been reading the first.

```
SummonData+0x40   ANCHOR          the (rot,pos,scale) the effect's PS1 program handed Hi_DrawSummonModel
   (pose_eval@0x186a0, written every Draw; the authored SCALE is folded into its 3x3 in place @0x187ab)
        |
        |  build_world_matrices@0x7820, motion branch  (0x7a20.., root compose 0x7edc-0x80a6)
        v
*(MATRIX*)(SummonData+0x38))[k]   BONE WORLD MATRICES      <-- the creature's real world pose
   bones[0].R = R_anchor * clipRotation[0](frame)
   bones[0].t = R_anchor * clipRootTranslation(frame) + T_anchor
        |
        |  ***THE STAGE NOBODY HAD CAPTURED***
        v
M o bones[k]      MODEL-VIEW, fed to the GTE           M = *(MATRIX*)resolve(PsxCtx[+0x14])
        |
        |  GTE RotTransPers @0x3e80
        v
screen (x,y) + otz          <-- what SFX_GetPrim hands managed code
```

**THE VIEW STAGE (new this round, statically proven, `py f1_viewmatrix.py`):**

* `PsxCtx` = the qword at RVA **`0x66C68`**. `PsxCtx[+0x14]` is a **PSX address of a 32-byte
  `MATRIX`** — the current world→screen matrix.
* **Both** per-mesh engines load it and compose it with each bone matrix, i.e. `CompMatrixLV`:
  * `Hi_DrawSummonModel@0x17740 → 0x4eb0`: `rbx = [0x66c68]` @`0x5178`; `ecx = [rbx+0x14]` @`0x5186`;
    `MulMatrix(M, bones[i], local)` @`0x51fa` (`0x3b60`); `GTE.R ← M.R` @`0x5295`, `GTE.T ← M.t`
    @`0x5327`, `GTE.V0 ← bones[i].t` @`0x5376`, `RotTrans` @`0x5390` (`0x3d60`); then the *real* load —
    `GTE.R ← M.R·bone.R` @`0x53a1`, `GTE.T ← M.R·bone.t + M.t` @`0x53bf`–`0x53cc`.
  * the shared emitter `0x56c0`: `rdi = [0x66c68]` @`0x56cd`; `GTE.R ←` @`0x576d`; `[rdi+0x14]`
    @`0x579a`; `GTE.T ←` @`0x57fd`.
* **`SFX_Update` (export `0x1d60` → body `0x13a0..0x1610`) refreshes it every native tick:** it copies
  the installed PSX camera **verbatim, 32 bytes** (`0x69730` rot / `0x69740` trans) into the DLL global
  at RVA **`0x1C1DC8`** (`movups` @`0x150c`/`0x151a`), publishes that global's PSX address into
  `PsxCtx[+0x14]` (`0x1452`→`0x145f`→`0x1475`), installs **OFX = 160** @`0x211FA0`, **OFY = 120**
  @`0x211FA4`, **H** = `word[0x69750]` @`0x211FA8`, and *then* runs the effect tick (`call 0x30d50`
  @`0x15e4`) inside which every `Draw` happens. It returns the tick counter through its `ref` out-param
  (`mov [rdi],eax` @`0x1601` = `SFX.SFX_Update(ref SFX.frameIndex)`).
* **The projection is closed-form** (GTE RTPS `0x3e80`):
  ```
  IR1 = sat16(MAC1)   IR2 = sat16(MAC2)   SZ3 = clamp(MAC3, 0, 0xFFFF)      (0x3f79 / 0x3f91 / 0x3fef)
  q   = (H << 16) / SZ3                     ; SZ3 == 0 -> q = 0x1FFFF        (0x400d-0x401b)
  SX  = clamp( ((IR1 * q) >> 16) + OFX, -1024, 1023 )                        (0x4035-0x4052)
  SY  = clamp( ((IR2 * q) >> 16) + OFY, -1024, 1023 )                        (0x4059-0x4074)
  ```

⇒ **`bones[k]` are WORLD matrices** (composing `M` again would otherwise double-transform), and the
world→screen mapping is `M` + `(OFX, OFY, H)` — **four fixed RVAs, all plainly readable, none of them
the managed `VIEW`/`PROJ`.**

`M4 §4` already wrote "`GTE.R = camR · boneMatrix[b]`" but never named where `camR` comes from or
connected it to the tracking question. That connection is this round's contribution.

### 1.3 RETRACTED: "reproject the root through the logged VIEW/PROJ"

`FINDINGS.md §3.1` asserted that `SummonData+0x40` is *"the same coordinate system as the logged camera
VIEW/PROJ — which is why `screen = PROJ·VIEW·rootTranslation` reproduces the creature's on-screen
position."* **That is retracted.** `V-M1-06` measured it: the anchor's last on-screen frame is **f107**;
from **f108 to f561 (454/512 frames, 88.7 %)** it projects off-screen — including 126 frames *before* any
freeze, most decisively **f178–233**, where the anchor changes every frame and all seven body meshes are
drawn, yet it projects ~20 screen-heights off in Y and *behind* the camera in view-Z. And the composed
matrix cannot rescue it: Bahamut's clip root-translation track spans only **7–246 units** per axis
(`m5_roottrans.py`) and the authored scale caps at **3.0×**, so `|bones[0].t − anchor.t| ≲ 740` units.

§1.2 explains why cleanly, and gives a fix with **zero free parameters** rather than another guess:

1. **Wrong mapping.** The managed pair is `PsxCamera.PsxMatrix2UnityMatrix(13 floats, cameraOffset)` +
   `PsxProj2UnityProj` (`PsxCamera.cs:103-178`, `SFX.cs:1590-1605`) — a *re-derivation* of the camera for
   the **3D battle models**, with its own off-center frustum convention (`bottom = h/2.2`). The plugin
   drew the creature with `M` + `OFX/OFY/H`. Use that.
2. **Wrong sampling instant.** `SFX_Update` snapshots the camera at the **top of each native tick**;
   `SFX_UpdateCamera` (`battle.cs:86` → `SFXDataCamera.UpdateCamera()` → `SFX.cs:1590`) is what *advances*
   the camera track (`0x1e80` calls the stepper `0x13540` at `0x1e88` and again at `0x1e91`) and runs on
   the managed clock. `SFXDataMesh.Load()` can run **many** `SFX_Update` ticks per managed frame
   (`SFXDataMesh.cs:576-582`), so the logged `VIEW` and the matrix that drew the frame are not required
   to be the same camera state — and Bahamut's track has **15 hard cuts** (D4 §2.1) where one step is
   an entire shot.
3. **Wrong datum, still true.** Node 0 of a 93-bone dragon is not the silhouette centre (M5 Finding D-3);
   and `A4` proved the `PRIM` stream is *already screen space*, so the comparison target must be the
   creature's `PRIM` screen AABB — never `MESH cx,cy` (pool-polluted: `vertCount ≡ 14000`, origin inside
   the AABB in **100 %** of 61,723 rows).

### 1.4 So: exactly how do we capture it

**Yes — the probe must log all 32 eff slots.** But that is the *census*, not the fix. Land **D1's patch**
(`D1-creature-id-probe.md` §3 — a nearly-verbatim-applicable patch to `SfxMeshProbe.cs`, plus a one-line
hook at `SFXDataMesh.cs:653`) **with three additions and one correction**:

**ADD — the VIEW row (the whole point of §1.2).** In the same `LogModels()` body, all passive reads at
fixed RVAs off the already-resolved `PluginBase()`:

```csharp
// VIEW,<effectId>,<frame>,<m00..m22>,<tx>,<ty>,<tz>,<ofx>,<ofy>,<h>,<psxPtr>
// The world->screen MATRIX the plugin composed with every bone this tick, plus the GTE screen params.
//   RVA 0x1C1DC8 = the matrix (SFX_Update@0x13a0 copies the installed camera 0x69730/0x69740 into it
//                  every tick @0x150c/0x151a and publishes its PSX address to PsxCtx[+0x14] @0x1475;
//                  the draw path re-loads it at 0x5178-0x53cc (0x4eb0) and 0x56cd-0x5812 (0x56c0)).
//   RVA 0x211FA0 / 0x211FA4 / 0x211FA8 = OFX / OFY / H  (0x13c4 seeds 160/120/H; the camera stepper
//                  0x13540 rewrites H @0x13ac7; HLE op 146 (fn 0x47e30) can rewrite all three -> LOG them).
//   RVA 0x66C68 -> PsxCtx ; dword PsxCtx[+0x14] logged RAW as the tamper check: if it stops being the
//                  PSX address of 0x1C1DC8 mid-cast, the effect program re-pointed the view and the
//                  0x1C1DC8 read is stale. Constant across the cast == safe.
```
32 bytes + 3 ints + 1 dword per frame. Same provenance class as the camera track the probe has logged
since s48.

**ADD — the composed bone-0 read** (D1 §1/§3.4 already has it): `bones = ReadIntPtr(data + 0x38)`, then
the 32-byte `MATRIX` at `bones[0]`. **Never cache the pointer or the values** — `0x7842` re-points it into
the per-frame packet arena every Draw, and `SFX_Update` re-bases that arena at `0x1459`. `bones == 0` is a
*guaranteed* never-drawn signal (`model_prepare@0x7120 : 0x71f7` zeroes it at register time), so the null
guard is load-bearing, not boilerplate.

**ADD — `rec+0x54`, the native motion-frame counter** (`inc word[rdi+0x54]` @`0x17888`). It distinguishes
"the managed frame outran the native tick" (a repeated row) from a genuinely static frame, and it lets the
offline clip decode (§2) reproduce every bone with no further probing.

**CORRECT — D1 §4.4/§4.5.** Its step-3 bound (`|w − a| ≲ 1000`) is right and worth keeping as a
self-check on the new read. Its step-4 reprojection through `PROJ·VIEW` is the retracted method; replace
it with the native identity, which has **no free parameters and no sign-convention search**:

```
p_view = M.R · bones[0].t + M.t                  (fp12: (M.R·v) >> 12, then + M.t)
SX     = OFX + ((sat16(p_view.x) * ((H<<16) / clamp(p_view.z,0,65535))) >> 16)
SY     = OFY + ((sat16(p_view.y) * (      ...      )) >> 16)
```

**FALSIFIABLE PREDICTION:** on the frames where the creature is framed (~40 % of the cast per the user's
video), `(SX,SY)` lands inside the creature's own `PRIM` screen AABB. If it does, the creature's exact
per-frame screen position is known for the first time — and inverting the *managed* `PROJ·VIEW` at that
screen point yields the Unity world point to hang a rung-7 puppet on (A4 §7 path 1), which is precisely
what FLIGHT has never had. If it does **not**, the raw `PsxCtx[+0x14]` column says whether the effect
program re-pointed `M`, and that is the next (bounded) question — not a guess.

**DO NOT expect the composed matrix to "fix the flight" on its own.** Say it in the commit message: it is
a ≤740-unit refinement of the anchor. The 40,000-unit figure is the authored fly-by (Z `+23808 → −49152`
over frames 153–168) and it is genuine staging data — probe address, orthonormality and linearity all
independently re-verified (`V-M1-06`).

**DO drop `DATA+0x78` from any wish-list.** M5 §9's "log the scale triple" is **FALSIFIED**: `+0x78` is
written to `0x10001000` (= 1.0) at register time (`0x7203`) and again only in `pose_eval`'s *no-scale*
branch (`0x187b5`); when a scale IS passed it is folded **in place** into `DATA+0x40`'s own 3×3 by
`ScaleMatrix 0x3b60` @`0x1879a`/`0x187ab`. The authored scale is recoverable **only** as the column norms
of the logged 3×3 — and `root_reproject.py:43,75` divides by 4096 and calls the result a rotation,
silently discarding a scale that sweeps **0.02× → 3.00×** across a real cast. That is a named defect in
our own file and it is part of why a flight built on the log made the promo worse.

### 1.5 The bonus the same cast buys

* **The eff-slot census** — how many props a stock Eidolon uses, when they arm, which shade modes
  (`slot+0x24`: 0 Solid / 1 Gouraud / 2 Textured), which use `drawOffset` (`+0x26`) or `sliceValue`
  (`+0x28`).
* **A second, independent creature readout.** A `kind=E` row whose anchor moves in lockstep with the
  creature while `hasMotion == 0` is a **bone-parented prop**, and its root **is** a creature bone's world
  matrix, copied verbatim (`0x1691b`–`0x16928`). That is also the exact mechanism a Thomas-swap prop
  should use — zero new machinery.
* **The empirical falsification test for §1.1.** Prediction: `hasMotion == 1` on `kind=S` rows only. A
  `kind=E` row with `hasMotion == 1` would re-open the subsystem question and is a stop-work finding.

---

## 2. THE FORMAT MAP — `ef###.bytes`

Corpus: **all 372 stock `ef###.bytes`**, re-extracted from the user's own `resources.assets` this round
and byte-verified (372/372 present, 0 mismatches, `ef227` = 823,296 B). Parser: **`ef_container.py`**
(this directory — committable; reads a caller-supplied blob, prints offsets/counts, embeds no game bytes).

There is **no magic number and no version field.** The file opens with `u16 chunkCount`. The format's only
self-check is structural: the resource walker's running cursor must land **exactly** on the file length —
and it does, **372/372**.

```
0x0000  u16 chunkCount
0x0002  per chunk: u16 chunkIndex, u16 resourceCount,
        then resourceCount x { u8 id, u8 info, u16 sizeSectors [, u16 extraSectors if id==2 && info!=0] }
0x0400  THE LOADER SCRIPT: 3-byte (code, arg1, arg2) records until code 0x00   (sector 0)
0x0800  first resource payload; every payload is 0x800-sector aligned and sized
```

### 2.1 Section inventory — status by layer

| layer | status | what is known | validated on |
|---|---|---|---|
| **container** (header sector, chunk/resource table, walker rule) | **DECODED** | walker `fn 0xd390`; cursor-equals-length; the extra `u16` is gated on **`info != 0`**, *not* `SFXBinaryFile.cs:64`'s `chunkIndex == 0` (a perfect correlate on stock data, wrong on synthesised data) | 372/372 files |
| **chunkIndex semantics** | **DECODED** | **not an ordinal** — 0 for chunk 0, **1 for every later chunk**; it is a "my payload lands in the *other* half of the double buffer" flag read at `0x3df12` → `0x323200` with exactly three consumers (`0x3e01c`, `0x3e13a`, `0x3e7f5`). `LOAD_CHUNK` keys on the chunk's **table ordinal** (`fn 0x30bd0` vs the 2-word table `0x32321c`) | 0 failures / 372 by ordinal |
| **sub-file directory** ("small files") | **DECODED** | a self-describing table of **signed s32 offsets relative to the table itself** (`fn 0x3d800 : 0x3da8a`); `count == entry[0]/4`. C#'s "u16 offset + `flags==0xFFFF` external file" is a lossy re-reading of a small negative s32 | 381/385 clean; the 4 exceptions are genuine back-references in the two multi-chunk Ark files |
| **resource ids** | **DECODED (11 ids, two dispatch tables)** | see §2.2 | 385 chunks |
| **creature package header** (ids 4+5) | **DECODED** | `texOffset == 0x180 + 4*motionCount` · `texBytes == pageCount*0x4000` · `clutBytes == clutRows*0x200` · per-part **TPAGE/CLUT/V-offset** arrays with their VRAM rects · the motion table at `+0x180` | 24/24 model packages |
| **the model image's internal address map** | **DECODED** | `file = id5.offset + headerRelative − texOffset`; geometry at offset 0; then texanim; then the motion clips; end at `modelBytes` | `geomEnd == firstBlock − texOffset` **24/24**; clip frame counts **66/66** |
| **geometry (`GEOM`) block** | **DECODED end-to-end** | §2.3 | **1005** blocks, 4 chain identities |
| **motion clip** | **DECODED end-to-end** | §2.4 | Bahamut's 8 clips tile with **0 gaps / 0 overlaps** |
| **camera sub-file** | **DECODED (bytes), PARTIAL (meaning)** | §2.5 | ef227's 3 shots |
| **loader script** (the 0x400 stream) | **DECODED (validity map + 6 handlers), PARTIAL (~50 operand semantics)** | §3 | 11,807 opcodes, **0 invalid** |
| **id-3 = the effect program** | **NAMED + BOUNDED, NOT READ** | raw little-endian **MIPS R3000A + the full PlayStation GTE (COP2)** machine code. **THIS is the choreography.** §2.6 | 385 images relocate; opcode histograms + intra-chunk `J`/`JAL` closure |
| **texanim table** | **OPAQUE** | located (`model+0x40` → `DATA+0x70`), format unread | — |
| `geom+0x04`, `geom+0x08`, `MeshDesc+0x00`, `BoneLink.len`, per-record junk bytes, `info` for ids 0/1/9 | **OPAQUE (named)** | carry verbatim; they do not block *reading* | — |

### 2.2 Resource ids — eleven, through **two** dispatch tables in `fn 0x3de37`

The LOAD pass (state 4, table `@0x3ed7c`, index `id−1`, ids 1..10) resolves a destination and the shared
tail `@0x3eca6` memcpy's the payload there; the INTERPRET pass (state 5, table `@0x3ed54`, index `id`,
ids 0..9) acts on it.

| id | meaning | corpus |
|---|---|---|
| 0 | VRAM image list (`{u16 x,y,w,h}` + 16bpp pixels) | 385 |
| 1 | VRAM image continuation | 316 |
| 2 | sub-file archive; its sub-file-0 region is initialised as a linear **arena** via `0x3d670` (the older "AKAO sound" label is unsupported — no SPU code on this path) | 385 |
| 3 | **PS1 main-RAM image = MIPS code + data** → pre-decoder `0xd1a0` | 385 |
| 4 | creature texture pages (`64×128` 16bpp, `0x4000` each) + the CLUT strip; **its payload also carries the model-package header** | 24 |
| 5 | **summon model image** → `Hi_RegisterSummonModel@0x15ee0` | 24 |
| 6 / 7 / 8 | **large payload loads** (2 KB–170 KB) whose interpret arm only flips a load-state byte — *not* zero-payload markers (302 geometry blocks live in 6 and 8) | 24 / 13 / 1 |
| 9 | second texture-page path | 37 |
| **10** | **no interpret arm, but a real load arm** at `0x3ea4c` — appends its payload at the running PSX-RAM cursor `0x323218` and advances it; consumed by the effect's own MIPS program | 4 (`ef381`×3, `ef447`×1) |

**24 effects carry a creature** (ids 4+5+6 always travel together): `ef038 177 179 184 186 210 211 225
226 227 251 261 276 381 431 432 435 438 439 447 493 494 495 498`.

### 2.3 The geometry block — one container, both families

**One PS1-native, indexed-pool, rigid-per-bone-skinned model format**, shared by the summon slot and the
whole eff-model family. Not TMD, not HMD, not PMD — FF9's own, and the **last surviving raw-PSX geometry
in the shipped game**.

```c
GEOM                                   // = decode(SummonData+0x08 / EffData+0x08)
 +0x00 u8  flags                       // bit0 = "already relocated" (0 on disk, set at load)
 +0x02 u8  boneCount                   // 0x7aba / 0x4fdc
 +0x03 u8  meshCount                   // Draw@0x17900 -- the hide-mask bit domain
 +0x04 u32 OPAQUE                      // NOT the block size (falsified)
 +0x08 u32 OPAQUE                      // id/hash-shaped
 +0x0c u32 pBoneTable                  // == 0x14 on disk, 1005/1005; links to the rows at +0x18
 +0x10 u32 pMeshTable                  // == 0x18 + (boneCount-1)*4 , 1005/1005  <-- THE structural law
 +0x14 u32 listHead                    // NOT an invariant: 7/1005 non-zero, incl. ef227 (0xff90)
 +0x18     BoneLink[boneCount-1]       // { s16 length; u8 unused; u8 parentIndex }
 (pMeshTable) MeshDesc[meshCount]      // stride 0x28: u16 OPAQUE, 8 bucket counts, u8 0, s8 otBias,
                                       //   then 5 sub-block offsets
```

Per mesh, the five pools follow in the fixed order `vertsPerBone → positions → primitives → uv → colors`,
**4-byte aligned** — *not* exactly adjacent: **1140 of 4164** links carry a 2-byte pad (M4's "exact
adjacency" is corrected; a writer that packs tight mis-places every sub-block after the first odd-length
pool).

* **Vertex = 8 B** `s16 x,y,z,w`; `w` is never read by the projector (M4's "low byte always `0x01`" is
  **overfit** — 97 distinct values corpus-wide).
* **Skinning is RIGID and RUN-LENGTH**: vertices sorted by bone, `vertsPerBone[b]` gives the run. No
  weights, no per-vertex bone index. `nVert = Σ vertsPerBone`, and `maxVertexIndex == nVert−1` in
  **1041/1041** meshes.
* **Eight `POLY_*` buckets** in a fixed order (`FT4 FT3 GT4 GT3 G4 G3 F4 F3`), counts in the mesh header,
  strides `0x18/0x14/0x20/0x18/0x18/0x14/0x10/0x0c`. `maxUVIndex == uvCount−1` in **969/969** — which
  independently proves u16 UV entries, the 4/3/4/3 per-face UV counts, and that only the four *textured*
  buckets carry UVs.
* **Texture binding is per-face-per-part** via a `part` byte indexing `DATA+0x28` (`{tpage, clut}` ×
  **≤ 6**). ⚠ `part < partCount` is **not** an invariant — 6 of 24 packages use out-of-range parts (they
  render with `tpage=clut=0`).
* **A load-time UV V-offset BAKE mutates the pool once** (`0x7514`/`0x75b7`/`0x7667`/`0x771b`): a tool
  reading a stock file sees **pre-bake** UVs; a tool reading live memory sees **post-bake** UVs.
* Limits: **≤ 7000 vertices/mesh** (`cmp idx,0x1b58` @`0x50b3`), **≤ 6 parts**, model image
  `≤ 0x50000` bytes.

**The 24 stock creatures, decoded from a typed lookup** (`ef227` Bahamut = **93 bones / 2 meshes / 1439
verts / 2416 faces / 8 clips / 6 texture pages**; Odin 97 bones; Ark 49; Atomos 5). **Every creature in the
game uses only `FT4` + `FT3`** — flat-shaded textured quads and tris with inline neutral-grey RGB.

### 2.4 The motion clip — decoded, and small

```c
struct Motion {                 // 0x14 B header; every offset is motion-relative
 +0x00 u16 unknown;             // never read by the pose pipeline
 +0x02 u16 frameCount;
 +0x04 u16 tx; +0x06 u16 ty; +0x08 u16 tz;   // flags bit i SET => literal s16 ; CLEAR => offset -> s16[frameCount]
 +0x0a u8  flags;               // bits 0..2 only
 +0x0c u32 rotKeyOff;           // < 0x10000   -> RotKey[nodeCount]
 +0x10 u32 fineKeyOff;          // < 0x100000  -> RotKey[nodeCount], or 0
};
struct RotKey { u16 a0; s16 a1; u16 a2; s16 flags; };  // per axis: bit SET => literal, CLEAR => track offset
```
Rotation = a **12-bit Euler angle** built from an **8-bit coarse track** (1 byte/frame) plus an optional
**4-bit fine track** (2 frames/byte): `angle = (coarse << 4) | fine`, 4096 units per turn. No
interpolation, no keyframe times, no easing, no blending — **one sample per rendered frame**, advance is
`frame+1`, and loop-vs-hold is a *Draw argument*, not clip data.

**The skeleton is NOT in the clip** — it is in the model, as the `BoneLink` table: a bone's local
translation is a single scalar **length along local Z**, and only the root gets per-frame translation.
Parent index **must be lower** than the child's (the hierarchy pass walks in index order with no sort).

`ef227`: 8 clips, all 93 nodes, contiguous at file `0x07579c..0x089ad4` (82,744 B for the entire
346-frame animation set), pointer table at `0x4a180`. Two independent derivations of those addresses —
M5's structural scan and D3's arithmetic `file = id5.offset + motionOffsets[k] − texOffset` — agree to
the byte.

Cost: **≈1.9–3.1 bytes per bone per frame** for a full 12-bit 3-axis rotation; only 22–56 % of the 279
channels are animated per clip.

⚠ **A first-draw in-place fixup**: `Hi_DrawSummonModel@0x17785-0x177b4` promotes `motion+0x0c`/`+0x10`
from small relative offsets to packed PSX addresses when they are below `0x10000`/`0x100000`. **On disk
they are offsets** — a re-importer emits offsets; a memory reader sees addresses.

### 2.5 The camera sub-file — the same bytes the kit already round-trips

The summon camera is **not** an HLE op. It is loader-script opcode **`0x29 PLAY_CAMERA`** pointing at a
**sub-file inside `ef###.bytes`**, in the **same binary format `SFXDataCamera.Load` reads for raw17 battle
cameras** — the format `ff9mapkit/battle/camera_codec.py` **already round-trips byte-exact**.

`Flags u16` + one `u16` offset per present group + the pointed-at blocks. Three independent derivations
agree (native parser `0x13030`, `SFXDataCamera.cs:29-82`, `camera_codec.py`). Two corrections the native
parser supplies:

1. **`HAS_CUSTOM_POSITION` (bits 4–7) is up to FOUR 6-byte records**, one per set bit, packed in bit
   order — not "3 Int16, sometimes more" (`SFXDataCamera.cs:76-80`). They are 3×`s16` anchor points in the
   **same s16 world space as the eye/target** (hard authoring bound: **±32767**).
2. **`HAS_UNKNOWN` (bit 3) is the SEQUENCE SELECTOR**, not padding: its block is parsed as a command word
   whose entire output is an index 0..2 choosing which of `sequence0/1/2` becomes live
   (`0x13139-0x134f1`). Every one of ef227's camera resources has `flags == 0x9` = one sequence + its
   selector. Calling it "unknown" is what made multi-sequence cameras look unusable.

**Bahamut's entire camera choreography is 460 bytes in 3 blocks** (192 / 228 / 40 B, at sub-file indices
6 / 16 / 47, from `0x29` ops at file `0x40f` / `0x499` / `0x508`). The per-frame chain is named end to
end: install `0x12df0` → parse `0x13030` → stepper `0x13540` (shake `0x14450`, look-at builder `0x14c30`,
roll `atan2`, focal **linear lerp** into `H`) → installed camera `0x69730` → `SFX_UpdateCamera 0x1e80` →
13 floats @`0x211df0`. The angle base is **4096 units per revolution**; `resolve_position@0x145a0` =
`anchor + 4096.8·(cos,sin)`.

Residual: nothing managed converts `(pitch, orientation, roll, distance)` → eye/look-at
(`SFXDataCamera.cs:550-555` is a literal `// TODO`). The math is now *located* (`0x13d40..0x14350` +
`0x14c30`) but not decoded — and it **gates nothing**, because the DLL applies the format correctly by
construction and §1.4's capture loop measures the result.

### 2.6 The one genuinely opaque layer: id 3 = the effect program

**This is where the choreography lives.** Confirmed on real bytes (opcode histograms + jump-target
closure over 8 files; statistics only, no payload echoed):

* Textbook PS1 opcode profile — SPECIAL/ALU dominant, then `LW ADDIU SW SH LHU LUI LH SB BNE` — and
  **`18` = COP2 (the GTE)**, 102 occurrences in `ef261` alone.
* Every `J`/`JAL` resolves inside its own chunk's window under `(PC & 0xF0000000) | (imm26 << 2)`,
  landing exactly in `psxBase = 0x801E7700 + (chunkOrdinal & 1) * 0x5000`. Nothing forces that unless the
  words really are MIPS.
* The DLL **pre-decodes** it (`fn 0xd1a0`: `operator new[]((size/4 + 1) * 16)`, one 16-byte record per
  instruction word) and **interprets** it (`fn 0xe210`, jump table `@0xed18`, index `op − 1`).
* The implemented ISA is **MIPS R3000A integer + COP0 moves + the FULL PlayStation GTE surface**
  (decode entries 61–65 and 89–90 are `SWC2/LWC2/CFC2/CTC2/MFC2/MTC2` and COP2-cofun). 99 decode entries,
  90 implemented.
* Native library calls are `jal 0xFF0000xx` traps caught at `0xec31`; the trap words are **not** in the
  file — they are a DLL-synthesised **216-entry sentinel table** at `.data` RVA `0x68250`
  (x86 `0x50910`), whose PSX base is published to `0x21FF78` at `0x30d2e`.

**Scale — why this is tractable:** Bahamut's entire native choreography is **two entry-point programs**
(chunk 0 program 0 at image offset `0x9d4`; chunk 1 program 0 at `0x108c`) inside code regions of
`0x3120` and `0x42BC` bytes ≈ **7,400 instructions** — the same order as reading one field's `.eb`.
And **capstone-MIPS is already installed** (5.0.7).

⚠ A disassembler must be **reachability-driven from the 16 program offsets**, never a linear sweep:
`[0, headerRel)` is code *and* embedded data (decode rate 50.3 % in `ef508`, 62.0 % in `ef210`).

---

## 3. THE LOADER SCRIPT / OPCODE TABLES

**Two layers are routinely conflated. They are not the same thing.** (Naming discipline — adopt it:)

| name | what it is | authorable by us? |
|---|---|---|
| **battle sequence DSL** (`.seq`) | the **managed** text language (`BattleActionCode`) rungs 1–7 author | **yes** — it is our own language |
| **loader script** | the native 3-byte `(code,arg1,arg2)` stream at file `0x400` | **yes** — plain bytes in `ef###.bytes` |
| **effect program** | the **MIPS machine code** in resource id 3 — **THE choreography** | **no** without a MIPS assembler |
| **battle-scene attack sequence** (raw17 `btlseq`) | the kit's per-scene attack choreography | yes (existing) |

**Corollary: the loader script is not the choreography.** Re-timing it buys retimed *loads* and
re-selected camera/sound sub-files — real, cheap, useful — but the beats a viewer perceives live in the
effect program.

### 3.1 The loader script — the complete validity map (dispatch tables read directly)

| range | source | verdict |
|---|---|---|
| `0x00..0x0F`, `0x14` | jump table `@0x31f58` | **VALID** |
| `0x10..0x13` | all entries → the `_wassert` stub `0x316da` | **INVALID (asserts)** |
| `0x15..0x1F` | `ja 0x316da` @`0x31671` | **INVALID (asserts)** |
| `0x20..0x2F` | qword table `@0x4aff0` (16 real entries) | **VALID** |
| `0x30..0x4F` | rebases past table A into `.rdata` **string bytes** | **ILLEGAL — indirect call into garbage, no assert** |
| `0x50..0x7F` | qword table `@0x4ab80` | VALID where non-NULL; NULL at `0x52 53 54 58 59 5D 60 66 67 68 74..78 7D 7E` (→ call NULL, a crash) |
| `>= 0x80` | `fn 0x49170` → `0xd820` | **VALID** — run program `N = code − 0x80`; a *missing* program is a **silent no-op** (`0xd820` returns −1) |

**Corpus validation: all 11,807 opcodes across 372 files are VALID under this map** — zero in the assert
holes, zero in the illegal band. 56 distinct codes appear; max 216 ops in one file (`ef381`).
A linter gets the illegal band, the NULL slots and the missing-program case for free — and must treat the
two failure classes differently (crash vs silent).

### 3.2 The handlers read directly

| code | handler | native behaviour |
|---|---|---|
| `0x00` | `0x31aad` | **END/HOLD** — rewinds the pointer by 3 (re-executes forever) and notifies the host `0x73000000` |
| `0x01` | `0x31680` | **WAIT** — `arg1==0`: wait `arg2` ticks; `arg1!=0`: block while `channelFlag[arg2] != 0` |
| `0x02` | `0x316af` | **SET_CHANNEL_FLAG** — `byte[0x323180 + arg1] = arg2` |
| `0x05` | `0x31712` | **LOAD_CHUNK** — selects the chunk slot that is the implicit 2nd argument of every `>= 0x20` opcode; keyed by **table ordinal** |
| `0x29` | `0x3bbd0` | **PLAY_CAMERA** — `arg1` = sub-file index; `arg2` = 0 literal / 1 last-used / 2 **random** (LCG `0x41c64e6d`) / 3 table lookup |
| `0x2D` | `0x3bf00` | PLAY_SOUND (sub-file index in `arg1`) |
| `0x80+N` | `0x49170` → `0xd820` | **run program N of the current chunk's 16-entry program table** |

`SFXBinaryFile.cs`'s other names (e.g. `0x02 = PLAY_CASTER_ANIMATION`) are **not** what the native handler
does — treat them as unverified hypotheses. `0x84..0x87` are used in stock data; C# stops the family at
`0x83`. The family is exactly `program index` and is 16 wide (stock uses ≤ 7).

### 3.3 The HLE op table — 216 ops, both builds, and the two we care about

The `0xeea4` "mega-interpreter" of the prior round is really the **HLE syscall dispatcher of a PS1 MIPS
interpreter**: entry `0xee80`, bound `cmp edx,0xd7` (**216 ops**), image-relative jump table `@0x12358`,
parallel `.data` op→fn table `@0x68780` (x86 `@0x50e18`, **same numbers**, same NULL at slot 20).
Operands are the MIPS **O32** argument registers (`getArgInt 0x126c0`, `getArgPtr 0x12740`); the return
goes to `$v0`. The full table — opcode, handler RVA, native fn (x64 + x86), arity, operand kinds — is
committed as **`M3-opcode-table.json`**.

**The summon family (12 ops, every arity doubly confirmed):**

| op | call | notes |
|---:|---|---|
| 23 | `Hi_RegisterSummonModel(modelPtr, ?)` | free-slot loop bounded to **slot 0 only** |
| 25 | `Hi_DrawSummonModel(rot, pos, scale, slot, loopFlag)` | **5 args**; `loopFlag` bit 0 = loop vs hold-last |
| 26 | `Hi_SetSummonMotion(motionPtr, slot)` | binding a motion always **rewinds** `rec+0x54` |
| 100 | `Hi_SetSummonMotFrame(slot, frame)` | ⚠ an out-of-range seek **WRAPS TO 0**, it does not clamp |
| **157 / 158** | **`Hi_ShowSummonModelMesh` / `Hi_HideSummonModelMesh`(slot, meshOrdinal)** | `DATA+0x20 &= ~(1<<ord)` / `\|= (1<<ord)` — §3.4 |
| 11 / 12 | `Hi_Stop/StartSummonTexAnim(slot, part[, flag])` | op 12's arg2 is a **BOOL** (`setne r8b`) |
| 147 / 65 | `Hi_ModifySummonModelAbr` / `RGB` | ABR operand `0xff` = **silent no-op** |
| 149 / 164 | `Hi_GetSummonBonePos` / `GetSummonBoneMatrix(slot, bone, out*)` | the program queries the creature's skeleton to place sub-effects |

The eff-model family (ops 6, 19, 21, 22, 24, 145, 151, 154, 155, 162, 163, 171, 185, 191, 193, 196, 198,
199, 200, 206) is co-equal in the same table — nothing in the dispatcher privileges either.

### 3.4 The per-mesh SHOW/HIDE ops — reachable, but COARSE, and the precision claim is refuted

* **Semantics + lifecycle are exact.** The mask is a `u32` at `SummonData+0x20`, **re-read on every mesh
  of every frame** (`0x17910`-`0x17919`), so an external write lands on the very next Draw. A hidden
  mesh's polys are **never generated** — they never enter the GTE, the ordering table, or `SFX_GetPrim`.
  The setter has **no bounds check** (`shl eax,cl` wraps mod 32); bits ≥ `meshCount` are inert.
  `Hi_DrawEffModel` and friends contain **zero** references to `ModelData+0x20` — it is summon-only.
* ⚠ **THE GRANULARITY REFUTATION.** The bit indexes the GEOM `meshCount`. Census of **all 24
  creature-bearing effects**: `meshCount ∈ {2,3}`, **max 3**. **Bahamut has exactly 2 meshes.** So the
  native mask offers **2–3 bits of granularity on a real summon**, where our managed `HideMeshes=` SFXKey
  filter cut the same creature into **7** usable body groups. `FINDINGS §2.4`'s "precision: exact 1 bit ↔
  1 model mesh" comparison is **REFUTED as a practical advantage**. Any design that assumed "hide the
  wings, keep the body" natively is dead on arrival — the wings are not a separate mesh.
* ✅ **Its real value is the TOTAL hide.** `mask = (1<<meshCount)-1` (`0x3` for ef227) is a complete,
  guaranteed, hash-independent, **emission-free** full-body hide — strictly better than the managed
  filter on every axis except granularity, which the Thomas swap does not need. It leaves the
  bone-parented eff-model props rendering, which is exactly the wanted behaviour.
* ⚠ **You cannot emit ops 157/158 as data.** They are HLE calls reachable only from the effect's own MIPS
  program. The prior round's menu item #5 ("emit the native Show/Hide `.seq` opcode") is **not
  implementable as stated**. The available route is a managed `Marshal.WriteInt32(DATA+0x20, mask)`
  re-asserted each frame before `SFX.SFX_Update` (`SFXData.cs:331`/`:347`) — a **runtime write** into the
  plugin's state, one class more invasive than the s52 read, and therefore an **owner go/no-go**, not a
  recommendation.
* **OPEN (runtime-only):** the mask's *initial* value. `SummonData` is `modelStruct + 0x90` in **PSX RAM**
  owned by the effect program (op 208, `fn 0x47330 : 0x47423/0x47449`); nothing in `SFX_Play`, op 208 or
  `Hi_RegisterSummonModel` writes `+0x20`. If that buffer is program-image-resident it is **file bytes**
  (an authorable initial visibility set); if BSS it is zero. **Do not assume zero** — the §1.4 probe's
  mask column settles it in one cast, and simultaneously detects whether the program stomps it with a raw
  `sw`.

---

## 4. THE ROADMAP TO DECODABLE / RE-IMPORTABLE SUMMON CUTSCENES

Effort: **LOW** ≤ 1 session · **MED** 2–4 sessions / 1 playtest round · **HIGH** 5+ sessions / multiple
playtests.

### 4.1 The strategic answer first

**The READ half is essentially already won and is a packaging job, not a research job.** The container
walks 372/372, the geometry passes two chain identities on 1005/1005 blocks, the motion tiles 8/8 with
zero gaps, all 216 native ops are pinned, and the camera sub-file is a format the kit **already
round-trips byte-exact**. What remains for a full summon-cutscene *disassembler* is **one decode** (the
MIPS program) and **a CLI**.

**The WRITE half splits sharply.** Editing a **stock** summon in place — retime, recolour, re-shoot,
re-point — is cheap and is the project's own north star (*"recreate the game from forks"*) applied to the
last opaque island. Building a **from-scratch native** summon is strictly dominated: it would take a MIPS
assembler, a container emitter, a conformant creature *and* an authored camera to reach a place the
**managed** route already occupies in-game (rung 7 renders our own rigged, animated FBX in a live battle;
rung 5 put genuinely new visual content in an FF9 summon; rung 6 is a real text DSL the kit can lint).

**The managed route's missing piece was never the creature — it was STAGING**, and §1 is the fix for
that.

### 4.2 TIER R — READ (a committable parser / inspector / disassembler). *This is the user's stated goal.*

| rung | delivers | depends on | effort | risk |
|---|---|---|---|---|
| **R1 — container inspector** | ship `ef_container.py` into the kit + a `summon-inspect` CLI: chunk/resource table, all 11 ids, sub-file directory, id-3 program table, creature package (bones/meshes/clips/pages/CLUT rows), and the loader-script listing with the full validity map | done — parser validated 372/372 | **LOW** | LOW |
| **R2 — geometry parser** | skeleton, mesh table, vertex pools, all 8 buckets, per-part tpage/clut, the UV bake. The `pMeshTable` law + the chain identities double as a free self-validating linter | R1 | **LOW–MED** | LOW–MED (must implement **align-4**, header-relative addressing, and must **not** gate on `listHead` / `firstBlock == motion[0]` / `part < partCount`) |
| **R3 — motion parser** | clip header, the 12-bit coarse+fine encoding, root tracks, the frame rule. Makes a stock creature's entire skeletal animation **computable offline** | R2 (the skeleton lives in the model) | **LOW–MED** | LOW |
| **R4 — camera read/write** | parse + re-emit an effect's camera keyframe tracks; type the custom-position group; name the selector block | R1 + a corpus round-trip over the 24 creature effects | **LOW** | MED — the *bytes* are readable; the **geometric meaning** needs W-CAM before an authored shot can be previewed offline |
| **R5 — the effect-program disassembler** *(the headline)* | a readable listing of a stock summon's **actual** choreography — the layer opaque since this study began. capstone-MIPS decodes; `M3-opcode-table.json` names the 216 calls; a small `$a0..$a3` constant tracker names arguments | §2.6 + one 4-byte constant (the HLE table's PSX base at `0x21FF78`) | **LOW–MED** | MED |
| **R6 — the probe fix + trace** *(**do this first** — §5)* | the creature's true per-frame world pose **and its exact screen position**; the 32-slot census; the motion-frame counter | the s52 probe already resolves the module base | **LOW** | LOW — reads only |

**R-tier exit criterion — "a summon cutscene is decodable":** `summon-inspect ef227` prints the container
map, the creature package (93 bones / 2 meshes / 8 clips / 6 pages), the camera keyframe tracks with their
absolute shot clock, the loader script, and an annotated MIPS listing of both programs naming every `Hi_*`
call. **Nothing in that requires a write.**

### 4.3 TIER W — WRITE / RE-IMPORT

| rung | delivers | depends on | effort | risk |
|---|---|---|---|---|
| **W0 — THE GATE: prove the container override loads** | cast 1: drop a **byte-identical** copy at `<mod>/FF9_Data/SpecialEffects/ef227` → the cinematic must be unchanged. cast 2: flip one `WAIT` operand at file `0x400+` → the pacing must visibly change | source-traced end to end (`SFX.cs:1974-1979` → `AssetManager.cs:541-627,971-977`); **never run** | **LOW** (2 casts) | LOW — revert = delete one file |
| **W1 — container writer** | rebuild from parsed parts; acceptance = **byte-identity round-trip 372/372**. Must use the native `info != 0` rule, keep `headerRel` 4-aligned, write `chunkIndex` as 0-then-1s, and clamp pool counts (≤32 eff, ≤1 summon) | R1 + W0 | **LOW–MED** | LOW |
| **W2 — loader-script patcher + linter** | retimed loads, camera/sound sub-file re-selection, program ordering, channel waits | W1 | **LOW** | LOW |
| **W3 — texture / CLUT reskin** | **the first visible custom content through the native path.** Pages are plain `64×128` 16bpp blocks at `id4.offset + texOffset` with an exact size law; a recolour needs **no code emission at all** | W1 | **LOW** | LOW |
| **W4 — camera-track authoring** | author a native summon's shot list: cuts, dollies, the near-Z/H zoom | W1 + R4 | **MED** | MED — blind-write-and-playtest until W-CAM |
| **W-CAM — decode the spherical→matrix step** | turns R4 from "write bytes" into "author". Bounded target set: `0x13d40..0x14350`, `0x14c30`, `resolve_position@0x145a0` (K = 4096.8 **confirmed**), `lookup_anchor@0x148f0` | R4 | **MED** | **LOW–MED, and its validation is free**: predict `VIEW`/`PROJ` offline and compare against the probe's already-logged rows |
| **W5 — MODEL-PACKAGE SWAP** ("our creature inside a stock cinematic, natively") | replace id-4 + id-5 while keeping the donor's program, script, cameras and sound — the donor's choreography drives our creature | W1 + a geometry emitter + **R5** | **HIGH** | **HIGH** |
| **W6 — from-scratch native summon (MIPS emission)** | — | R5 + assembler + W1 + emitter + W4 | **HIGH+** | **DO NOT BUILD** (§4.1) |

**W5's hard conformance constraints** (a rig violating any of these renders wrong, *silently*): parent
index < child index · a bone's local translation is a **single scalar along local Z** · mesh **ordinals**
are load-bearing (ops 157/158 address by bit index) · clip count and frame counts must satisfy the
program's op-26/op-100 arguments (and op 100 **wraps**) · bone **indices** are queried by number (ops
149/164/162) · ≤ 6 parts · ≤ 7000 verts/mesh · model image ≤ `0x50000` · **failure mode is a hang, not an
exception** (`0x151a0` spins forever after formatting `"HIRAISHI ERROR:"` into a *discarded stack buffer*
— recoverable only by attaching a debugger or reading `DBGCTX 0x220890`). **Lint offline; never ship an
unvalidated container.**

**The id-fork law (mirrors the field lane):** `SFX_Play` stores the effect number at `0x3678E8` and native
code compares it against literals (`0x12d`, `0x7e`, `0xb8`, `0x95`), and `SFX.cs` carries further
name/id-keyed special cases. **A fresh native effect id inherits none of them** ⇒ for the native lane,
**fork an existing id in place**; mint fresh ids only on the managed lane.

### 4.4 The recommendation

1. **INVEST — TIER R (R6 → R1 → R5).** This *is* the stated goal, it is nearly all packaging, it is
   provenance-clean, and it makes every stock summon's choreography readable.
2. **INVEST — the cheap half of TIER W: W0 → W1 → W2 → W3, plus W-CAM.** These make stock summons
   **editable in place**. W3 buys visible custom content through the native path for LOW effort.
3. **DEFER — W5.** It is the only path to a stock-grade *native* creature and is specified well enough to
   attempt, but it must wait on R5 (you cannot conform a rig to a program you cannot read) and W0.
4. **DO NOT BUILD — W6.**
5. **Kit shape:** author `[[summon]]` against the **managed** lane (the proven one). Expose the native
   lane as a separate read/fork family (`summon-inspect`, `summon-disasm`, `summon-fork`). **Do not
   conflate them** — different provenance rules, different failure modes.

### 4.5 Cheapest unknowns, ranked by unblock-value ÷ cost

| # | unknown | cost | unblocks |
|---|---|---|---|
| 1 | **Does `M` (RVA `0x1C1DC8`) + `H/OFX/OFY` reproject `bones[0]` onto the creature's `PRIM` AABB?** (§1.4) | 1 cast | **The tracking pillar.** Also settles the eff-vs-summon question empirically and the hide-mask's initial value. |
| 2 | **Does a mod-folder `ef###.bytes` override load?** (W0) | 2 casts, $0 | **ALL of TIER W.** |
| 3 | **The HLE table's PSX base** — one 4-byte read at `pluginBase+0x21FF78` (and `+0x21FF7C`) | one probe row | Turns R5 from control flow into **named choreography, offline, forever**. Read *both*; the one indexing a 216×4 span the programs load from is the table. |
| 4 | **The live `PsxCtx*`** — actually **SOLVED this round**: it is the qword at RVA `0x66C68` (M3 §7.2's open item 2) | — | The runtime opcode trace (M3 rung B): `ctx+0xda0` thread, `ctx+0xc98+tid*0x80` `$a0..$a3`, `ctx+0x2dc8/0x2dcc` the pending trap word ⇒ **the real opcode timeline of a real cast**. |
| 5 | **The camera's spherical→matrix step** (W-CAM) | MED, validation free | Offline camera authoring + preview. |
| 6 | `geom+0x04`, `geom+0x08`, `MeshDesc+0x00`, `BoneLink.len` | LOW–MED | A byte-exact geometry **writer** (carry-verbatim suffices for a whole-block swap). |
| 7 | The texanim table format; the `info` byte for ids 0/1/9; the `0x29 arg2` table-lookup field; camera outer-flag bit 9 | LOW | Emitting *new* resources / full camera authoring. Preserve-don't-invent until read. |
| 8 | **A `.pdata`-invisible-leaf sweep for `refkit`** | LOW | **Instrument hygiene, and it already bit twice**: `Hi_InitEffModel@0x15940` was invisible to `xrefs_to`, and `SFX_Update`'s own thunk (`jmp 0x13a0` @`0x1d60`) is in a gap — §1.2 would have been missed by a `.pdata`-only search. 353 gaps / ~9.9 KB of `.text` lie outside `RUNTIME_FUNCTION` ranges. Add `refkit.gap_sweep(pe)` + `include_gaps=True`; cross-check against x86, which has no `.pdata` at all. |

---

## 5. IMMEDIATE NEXT ACTION

**Land the extended probe and take ONE instrumented Bahamut cast.** LOW effort, read-only, no DLL patch,
provenance-clean, and it closes the round's motivating bug with a zero-free-parameter check.

### 5.1 Build

1. Apply **`D1-creature-id-probe.md` §3** to `C:/gd/FFIX/Memoria/Assembly-CSharp/Memoria/Battle/SFX/SfxMeshProbe.cs`
   (new ini flags §3.1, loaders §3.2, banner §3.3, `LogModels()` + `WriteModelRow()` + `WriteBoneAabb()`
   §3.4) and the single call-site line at `SFXDataMesh.cs:653` (§3.5).
2. **Add the `VIEW` row** of §1.4 to the same method — `Marshal.Copy` 32 bytes from
   `PluginBase() + 0x1C1DC8`, three `ReadInt32`s from `+0x211FA0/+0x211FA4/+0x211FA8`, and the raw
   `PsxCtx[+0x14]` tamper check (`ReadIntPtr(PluginBase()+0x66C68)` → `ReadInt32(ctx + 0x14)`).
3. **Add** `rec+0x54` (already in D1's `aux0` for `kind=S`) and the **hide mask** `DATA+0x20` as a column
   (settles D4 §4 open items 1+2 for free).
4. Rebuild the engine DLL per the `building-the-memoria-engine` skill. ⚠ **AUTO-DEPLOYS, no backup.**

### 5.2 Arm

```ini
[SfxProbe]
Enabled          = 1
CaptureRoot      = 1        ; keep -- existing offline tooling parses the ROOT row
CaptureModels    = 1        ; the s53 census + composed transform + the VIEW row
ModelsActiveOnly = 1        ; active slots + activation edges only
ModelsCap        = 120000
ModelsBoneCount  = 93       ; ef227's node count (decoded offline); 0 disables the BONES row
CapturePrims     = 1        ; REQUIRED -- the PRIM rows are the comparison target
```

### 5.3 Capture

One battle, one Bahamut cast (effect **227**), then quit. Log:
`C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log`
(**sample/grep — never read whole**; the existing one is 97 MB+).

### 5.4 Read out — in this order, each step a prediction that can fail

1. **Subsystem test.** `hasMotion == 1` on `kind=S` rows only. A `kind=E` row with `hasMotion == 1` is a
   **stop-work** finding.
2. **Drawn test.** `kind=S` has `bones32 != 0` from the first drawn frame on (≈ f82 on the existing
   capture).
3. **Composition self-check.** `|(wx,wy,wz) − (ax,ay,az)| ≲ 1000` every frame. If it is huge with a stable
   `bones32`, the bones offset is wrong for this arch.
4. **Tamper check.** the raw `PsxCtx[+0x14]` column is **constant** all cast. If it changes, the effect
   program re-pointed the view matrix and the `0x1C1DC8` read is stale — that is the next question, not a
   guess.
5. **THE REPROJECTION (the point of the round).** Per frame, `p_view = (M.R·bones[0].t)>>12 + M.t`, then
   `SX = OFX + ((sat16(p_view.x)·((H<<16)/clamp(p_view.z,0,65535)))>>16)`, same for `SY`.
   **Predicted:** `(SX,SY)` lands inside the creature's own `PRIM` screen AABB on the framed frames
   (≈ 35–45 % of drawn frames), and leaves frame during the final phase as the camera follows the fire
   column. Filter `PRIM` to the creature's body keys using the `HideMeshes` split already recorded in
   `PROBE.md §2`; compare against the projected **`BONES` AABB corner hull**, not a single point (node 0
   of a long-necked dragon is not the silhouette centre).
6. **If step 5 lands** — re-stage FLIGHT: for each frame take the measured screen point and invert the
   *managed* `PROJ·VIEW` at a chosen depth plane to get the Unity world point to hang the rung-7 puppet
   on (A4 §7 path 1). That is the honest form of "faithful = wherever Bahamut was", and it is the first
   time it is **measured** rather than constructed.
7. **Also fix `root_reproject.py`** (`:43`, `:75`, `:88`): decompose `SummonData+0x40` as `R·S` —
   `s = column norms / 4096`, `R = M/(4096·s)` — and carry `s` into any puppet transform. Today the file's
   `FIXED = 4096.0` comment is factually wrong.

**Do not sell the composed matrix as the flight fix.** It is a ≤740-unit refinement. The fix is the
mapping (§1.2) and the scale (step 7).

---

## 6. PROVENANCE LEDGER

* **No stock content was committed.** No creature geometry, animation payload, texture, `ef###.bytes`
  container, or MIPS disassembly listing was written into the repository at any point in this round.
* **No DLL was modified, patched, or redistributed, and none will be.** Every native claim comes from
  **read-only** static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 **and**
  x86) and is cited `fn@rva`; the output is RVAs, mnemonics, struct offsets, table indices and control
  flow.
* **Extracted stock binaries live only under `C:/gd/SCRATCH/summon-format/`** (372 `ef###.bytes`,
  extracted from the user's own install by the study's UnityPy recipe; re-verified this round as complete
  and byte-true). Everything quoted from them in any artifact is **structural** — offsets, counts, sizes,
  indices, opcode histograms, field statistics. No payload was echoed or copied.
* **Committable code from this round:** `refkit.py`, `ef_container.py` (the container/geometry parser —
  reads a caller-supplied blob, prints offsets and counts, embeds no game bytes), `M3-opcode-table.json`,
  the `m1_*`/`m2_*`/`m4_*`/`m5_*`/`d4_*`/`c8_*`/`v*_*` analysis helpers, **`f1_viewmatrix.py`** (this
  round's §1.2 reproduction), and the `.md` reports. All of them read the user's own DLL/blobs at runtime
  and emit addresses and statistics only.
* **The probe extension** (§5) patches **Memoria's open-source `Assembly-CSharp`** — the sanctioned lane —
  and performs **passive reads** of the plugin's runtime state, the same class as the camera track logged
  since s48 and the root transform logged since s52. It writes no shippable asset bytes.
* **Hard lines, unchanged.** Dumping `bones[1..N-1]` across a cast reconstructs the stock skeletal
  animation = **BLOCKED**; the probe logs bone 0 plus a single irreversible aggregate (a 93×3 → 6
  centroid+AABB reduction) and has **no code path** that can emit per-bone data. R5 disassembly listings
  of Square's PS1 code are derived stock content and stay under `C:/gd/SCRATCH/summon-format/`. A modified
  stock container (W-tier) is a **build-time transform of the user's own install into their own mod
  folder** — never committed, never redistributed, exactly the verbatim-fork precedent. **Never produce or
  ship a patched `FF9SpecialEffectPlugin.dll`.**
* **Runtime-only facts are labelled as such throughout** and asserted only as *layout*: the summon record
  array, the `SummonData` block, the bone array, the view matrix `0x1C1DC8`, `OFX/OFY/H`, the `PsxCtx`,
  the MIPS register files and the camera scratch are all zero-on-disk `.bss`/heap.

---

## 7. REPRODUCTION

```
cd studies/custom-summons/thomas-swap/disasm
py f1_viewmatrix.py          # section 1.2 end to end: the view stage + the projection constants
py refkit.py                 # self-test: 646 .pdata functions, the Hi_Summon* roster by string-xref
py ef_container.py <blob>    # section 2: container + model package + geometry  (blob from C:/gd/SCRATCH/)
```

Assertions that must hold:
`0x220230 + 32*0x30 == 0x220830` ·
`ft[157]-base == 0x187e0`, `ft[158]-base == 0x18840` (table `0x68780`) · `ft[20] == 0` ·
`exports["SFX_Update"] == 0x1d60` and the byte there is `0xE9` targeting `0x13a0` ·
`struct.unpack('<d', read_rva(pe,0x4b6a8,8)) == 2π`, `0x4b6c0 == 4096.0`, `0x4b690 == 1.0` ·
`ef227` chunk 0 `headerRel == 0x3120` with one program at `0x9d4`; chunk 1 `0x42bc` / `0x108c` ·
`parse_geom(ef227, id5.offset)` → 93 bones / 2 meshes; `mesh_count` over the 24 creature effects → `{2:21, 3:3}` ·
`parse_sequence(ef227)` → three `0x29` ops, `arg1 ∈ {6,16,47}`, all `arg2 == 0`, blocks 192/228/40 B, flags `0x9`.
