# A4 — THE PRIMITIVE-SPACE PUZZLE (RESOLVED)

**The cheap gate that unblocks interpretation.** Open problem: the s50 probe logs per-frame MESH
bounds + VIEW/PROJ matrices, but native primitives (`SFX_GetPrim` output) *do not project sanely*
through the captured VIEW/PROJ — even though `SFXMesh` builds each vertex as
`(x0+drOffsetX, y0+drOffsetY, GzDepth)`, which reads like a plain mesh vertex under those matrices.
This slice resolves it and states whether every projection-based conclusion in the study stands or falls.

Cites are `Assembly-CSharp` relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/` unless noted; log rows
are from `C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log`
(effectId 227 = the study cast).

---

## 0. Headline resolution (three facts, all proven by source **and** by the live log)

1. **`SFX_GetPrim` emits ALREADY-PROJECTED 2D PSX-GPU primitives — screen space, not world.**
   Each primitive's `x0,y0` (Int16) is a final **screen-pixel** coordinate (the *output* of the
   DLL's internal GTE), and the per-primitive `otz` is an **ordering-table depth-sort scalar**, not
   a metric Z. The 3D → 2D projection already happened *inside the plugin*; only the flattened 2D
   result escapes across the P/Invoke line. (Agrees with and sharpens A3 §0.1.)

2. **The probe's `MESH` bounds are POST-projection (screen space), AND pool-polluted.** `cx,cy,cz /
   ex,ey,ez` are `mesh._mesh.bounds` over a **fixed 14000-slot vertex array** whose unused tail sits
   at `(0,0,0)`. Every MESH AABB therefore contains the origin on all three axes — **100.0%** of a
   61,723-row sample — with `max.z` pinned to `0` in 88.6%. The box is anchored to the origin, never
   tightly fitted to the drawn creature. `vertCount` is a constant **14000** on every row — the tell.

3. **"Doesn't project sanely" is a CATEGORY ERROR, now explained.** The logged VIEW/PROJ describe the
   camera for the **3D battle models** (party/enemies/a real ModelFactory model), in PSX-GTE world
   units. The primitives are already in **screen space**. Re-running screen-space coordinates through
   a 3D perspective camera mis-transforms them — which is exactly why the study's own diagnostic
   landed "only ~8/324 frames on screen." **The creature's true per-frame 3D world transform is NOT
   present anywhere in the `SFX_GetPrim` / MESH stream. It was consumed and discarded by the GTE.**

**Verdict on the study:** every conclusion that reads MESH bounds `cx,cy,cz` as *Bahamut's 3D world
position* and re-projects it through VIEW/PROJ is **VOID** (details + ledger in §6). What survives:
the creature's **screen** trajectory is directly recoverable — but from the un-pooled `PRIM` rows,
and **without any projection** (§7).

---

## 1. What `SFX_GetPrim` returns (the space, from source)

`SFX_GetPrim(ref Int32 otz)` returns an `IntPtr` to one PSX `P_TAG` primitive and writes the
primitive's ordering-table depth into `otz` (`SFX.cs:753` DllImport; `:827` wrapper). The harvest
loop (`SFXRender.cs:77-86`):

```
for (;;) {
    Int32 num = 0;
    P_TAG* ptr = (P_TAG*)SFX.SFX_GetPrim(ref num);   // ptr = one decoded PSX GPU primitive
    if (ptr == null) break;
    SFXMesh.GzDepth = -num;                            // <-- the "Z" is just -otz
    SFXRender.Add(ptr);
    SFXRender.primCount++;
}
```

This is the canonical PSX **ordering-table** `GetPrim` pattern: the plugin has already run its GTE,
produced screen-space primitives, and threaded them onto an OT keyed by depth. `SFX_GetPrim` walks
that OT and hands back each primitive with its OT depth bucket. Two independent proofs that the
`P_TAG` payload is post-projection screen space:

- **Every consumer treats `x0..x3` as pixels.** `SFXRender.FixWidescreenFace` (`:651-784`) compares
  `x` against literal `0`, `160`, `320` and shifts by a widescreen pixel offset; `IsFullWidthRect`
  tests `x0==0 && x1==320` (`:786-789`); `SPRT`/`TILE` build quads `(x0,y0)..(x0+w,y0+h)` in pixel
  width/height (`SFXMesh.cs:816-888`). None of this is meaningful on 3D world coordinates.
- **`otz` is written as the vertex Z verbatim, one value for the whole primitive.** `GzDepth = -num`
  is set once per primitive and stamped identically onto every vertex of that primitive (see §2). A
  genuine 3D primitive under a perspective camera has *per-vertex* depth; a single shared Z is the
  signature of a post-GTE 2D primitive carrying one depth-sort key.

## 2. How `SFXMesh` builds the vertex (why the "Z" is a sort key)

Every `PolyXxx`/`Sprite`/`Tile`/`LineXxx` builder writes:

```
Int32 num  = obj->x0 + drOffsetX;      // screen pixel X + PSX draw-env offset
Int32 num2 = obj->y0 + drOffsetY;      // screen pixel Y
__gPos[..].Set(num, num2, GzDepth);    // Z = GzDepth = -otz, SHARED by all verts of the primitive
```

(`SFXMesh.cs:340-346` PolyF3, identical in :366-, :400-, :438-, :483-, :521-, :567-, :617-, :670-,
:750-, :816-, :858-, :890-, :908-.) `drOffsetX/Y` are the PSX GPU draw-environment offset
(`DR_OFFSET`, `SFXRender.cs:433-437`) plus the widescreen shim (`CalculateWidescreenOffsetX`,
`:791-794`) — still pixel-space. So the built mesh vertex is **(screen_x, screen_y, −otz)**: a
2D screen point with a per-primitive depth-sort scalar in the Z slot.

`GzDepth` scale: the logged Z runs ~`[-65535, +16]` in the cast, i.e. bounded by `SFX.fxFarZ = 65535`
(`SFX.cs:1600`). Consecutive primitives in one frame get consecutive descending values (frame 58:
`-30000, -29984, -29952, -29936, …` — see §5). That descending-in-draw-order-within-the-far-Z-scale
shape is an **OT depth key**, not a world coordinate.

## 3. How the mesh is drawn (why "object space == world space" is a trap phrase)

`SFXMesh.Render()` draws with `Graphics.DrawMeshNow(_mesh, Matrix4x4.identity)` (`SFXMesh.cs:269`).
The identity **object** matrix is why the probe comment (`SfxMeshProbe.cs:46-48`) and `PROBE.md:84`
call the bounds "world space." That is true only in the trivial Unity sense (no object transform) —
**but that "world" is PSX screen space.** It is emphatically *not* the 3D battlefield world where the
camera, party and enemies live.

Two draw paths exist, and they differ in whether they neutralize the view matrix:

- `SFXRender.Render()` forces `camera.worldToCameraMatrix = Matrix4x4.identity` around the draw
  (`SFXRender.cs:130,135`) — screen-space verts drawn under identity view.
- `SFXDataMesh.Runtime.Render()` — the path that actually runs the mesh/JSON casts **and that hosts
  the probe hooks** — has that identity override **commented out** (`SFXDataMesh.cs:640`) and draws
  the command buffer directly (`:650-665`). `SfxMeshProbe.LogFrame` + `LogCamera` fire here
  (`:643,648`), capturing `camera` in whatever state `SFX.UpdateCamera()` last left it.

Either way the primitives render at their baked screen pixels; the camera matrices in play are for
the **3D** content, harvested separately.

## 4. What VIEW/PROJ actually are (the 3D-model camera, not the primitives')

`SFX.UpdateCamera()` (`SFX.cs:1590-1604`) copies 13 floats out of `SFX_UpdateCamera` and stamps:

```
camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array, cameraOffset);  // VIEW
camera.projectionMatrix    = PsxCamera.PsxProj2UnityProj(fxNearZ, 65535);           // PROJ
```

- **VIEW** = a real 3×3 GTE rotation (fp12, `/4096`) + translation `(pmat[9], -pmat[10],
  -(pmat[11]+zoffset))` — a genuine **world→camera** transform in PSX-GTE world units
  (`PsxCamera.cs:103-120`). Log row (frame 11): translation `(-316, -286, -2651)` — hundreds/thousands
  scale.
- **PROJ** = `PerspectiveOffCenter(-HalfScreenWidth, HalfScreenWidth, -h/2.2, h·(1-1/2.2), nearZ, 65535)`
  — a genuine **3D perspective** off-center frustum whose only per-frame free variable is `nearZ`
  (the zoom) (`PsxCamera.cs:122-178`). Log row: `m32=-1` (the perspective-divide row), `m11` sweeping
  ~2.33..4.65 across the cast = the documented FOV zoom.

These matrices operate on **PSX-GTE world coordinates** (translations in the thousands). Feeding them
a **screen-pixel** point like `(195.5, 110, 0)` treats a screen coordinate as a world coordinate: the
perspective divide and the −2651 view translation produce nonsense. That is the whole of the "doesn't
project sanely" puzzle. (A3 §4 covers the camera recovery; A4's contribution is that the primitives
live in a *different space* than these matrices describe, so they must never be pushed through them.)

## 5. The live log confirms every claim

Raw rows (effectId 227):

```
# header
# MESH,effectId,frame,index,keyHex,vertCount,triCount,cx,cy,cz,ex,ey,ez
# PRIM,effectId,frame,index,code,vertHint,otz,x,y

PRIM,227,11,1,98,TILE,0.0000,275,110        <- full-screen 80px tile grid: x∈{35,115,195,275}, y∈{0,110}
MESH,227,11,0,00800000,14000,16,195.5,110.0,0.0,195.5,110.0,0.0

# a summon frame (creature-scale meshes):
MESH,227,58,1,0039BE40,14000,128,202.0,138.5,-15000.0,217.0,216.5,15000.0
MESH,227,58,3,0099BD00,14000,432,193.5,126.0,-6264.0,358.5,357.0,6264.0

# the same frame's un-pooled creature primitives (FT4 = textured quads):
PRIM,227,58,0,44,FT4,-30000.0000,368,-78
PRIM,227,58,1,44,FT4,-29984.0000,325,-28
PRIM,227,58,2,44,FT4,-29952.0000,272,-70
...
PRIM,227,58,15,44,FT4,-29568.0000,-12,2
```

Empirical facts extracted:

| Observation | Value | Meaning |
|---|---|---|
| PRIM `x,y` range | x∈`[-12..386]`, y∈`[-78..63]` (frame 58) | **screen pixels** (0..320 native + widescreen drOffset, off-screen allowed), NOT thousands-scale world |
| MESH `cx,cy` range | ~`(129..202, 108..170)` | same screen-pixel band as background tiles — the creature is *not* in world units either |
| MESH `vertCount` | **14000 on every row** | `_mesh.vertices = VbPos` assigns the whole fixed array (§8) — pool tell |
| Origin ∈ AABB | **100.0%** of 61,723 rows (x,y,z all) | unused pool verts at `(0,0,0)` are always inside the box |
| `max.z == 0` | 88.6% | Z = −otz ≤ 0, so the pool's `z=0` pins the near face; box spans `[−deepest_otz, 0]` |
| PRIM `otz` (=GzDepth) | descends `-30000,-29984,…` per primitive, bounded by farZ 65535 | **depth-SORT key**, monotonic in draw order — not a world Z |

The MESH bounds of the 432-tri creature key `0099BD00` illustrate the pollution exactly:
`cz=-6264, ez=6264` ⇒ Z ∈ `[-12528, 0]` (far face pinned to the pool's 0); `cx=193.5, ex=358.5` ⇒
X ∈ `[-165, 552]` (spans the origin, inflated by the zero-slots and any stale tail). The AABB center
`(193.5, 126)` is the **midpoint between the origin and the far primitive corner**, ≈ half-screen —
it is *not* the creature's screen centroid, and certainly not a world position.

## 6. Adjudication of the study's projection-based conclusions

| Study artifact / claim | Status | Why |
|---|---|---|
| `PROBE.md:84` — "MESH `cx,cy,cz` = mesh.bounds, **world space**" | **MISLEADING → correct to "PSX screen space (post-GTE), pool-polluted"** | object==world is only the identity *object* matrix; the coords are screen pixels + an OT depth-sort Z (§1-3,5) |
| `matrix_solve.py` premise — "put Thomas at Bahamut's **measured world position**; the per-frame VIEW+PROJ reproduce his screen position for free" | **VOID** | there is no measured world position in this data; `(cx,cy,cz)` are screen-x/y + sort-Z. Re-projecting them through the 3D-model camera is a category error |
| `matrix_solve.py` "X,Y = bounds CENTER (body sits near origin, \|X\|,\|Y\|<512)" | **VOID as world-XY; REINTERPRET as corrupted screen-XY** | "small numbers" = screen pixels, not world-near-origin; and the center is pool-pulled toward the origin, so it is not even the screen centroid |
| `matrix_solve.py` "Z = FAR CORNER `2·cz` = body world depth (thousands)" | **VOID** | `2·cz` = the deepest primitive's −otz (an OT depth bucket on the `[0,65535]` farZ scale), pinned opposite the pool's 0. Coarse, quantized, offset — monotonic in depth but not a recoverable world coordinate. The noted ~2× center-vs-farcorner ambiguity is itself the symptom that this axis is not a real coordinate |
| The self-diagnostic "only ~8/324 frames land on screen with far-corner Z (~50 with center Z)" | **EXPLAINED, expected** | projecting screen-space points through a 3D perspective camera *should* scatter off-screen; the ~8 that land are coincidence. This number is evidence *against* the world-position reading, not a tuning knob |
| The deployed **FLIGHT v7** ("in-frame by construction, 551/551") | **NOT invalidated** | v7 does not depend on recovering a world transform; it constructs on-screen coverage directly. But its *faithfulness* ("Thomas is wherever Bahamut was") cannot be validated from bounds (§7) |
| A3 §0.1 / §0.3 (creature transform never crosses the boundary; only 2D footprint + lossy `otz`) | **CONFIRMED + strengthened** | A4 adds the source mechanism (GzDepth=−otz, per-primitive shared Z) and the 100% origin-containment proof that even the 2D footprint is pool-corrupted in the MESH rows |

## 7. What IS recoverable, and how (the actionable part)

**The creature's per-frame SCREEN trajectory is recoverable today — no projection, no matrices.**
Because the primitives are already at their final screen positions, the answer to "where does the
creature appear on screen each frame" is *directly in the data*:

- **Use the `PRIM` rows, not the MESH bounds.** `PRIM.x, PRIM.y` are the un-pooled per-primitive
  vertex0 screen pixels (`SfxMeshProbe.cs:315-316,340-342`). Compute the per-frame screen AABB /
  centroid of the creature's own body keys' primitives (filter by `keyHex`/`code` — the body meshes
  identified in `PROBE.md`), and you have the true screen path including the deliberate off-screen
  swoops (off-screen shows up as `x<0` / `x>320`, e.g. frame-58 `x=-12`). Requires `[SfxProbe]
  CapturePrims=1`.
- **Do NOT use MESH `cx,cy`** as the screen position — it is pulled toward the origin by the pool
  (§5, §8). If only MESH rows are available, a pool-correction is possible but lossy: the box is
  `[min(real,0) .. max(real,0)]`, so the *real* extent is one-sided and cannot be separated from the
  zero-pinned side without the per-primitive data.

**Placing a real 3D model (rung-7 Thomas) faithfully requires Bahamut's WORLD transform, which is
NOT in this stream.** Two paths:

1. **Screen-match via inverse projection (available now).** Pick a target screen point from the
   `PRIM` data and a chosen depth plane, then invert `PROJ·VIEW` (both logged, both real for the 3D
   camera) to get a world point that projects there. This reproduces Bahamut's *screen* position under
   the real moving/zooming camera without ever needing his true world position. This is the honest
   form of "faithful = wherever Bahamut was **on screen**."
2. **Recover the true world transform from plugin internals (the next disasm step).** The world
   position/orientation of the summoned creature lives only inside the DLL. Candidate sources for the
   following round: the decoded summon-model array (`+0x00` data ptr, `+0x10` motion ptr, `@RVA
   0x220830`, stride 0x58 — this round's calibration) and its Get-bone-position / Get-bone-matrix
   consumers, and/or `SFX_SendFloatData type 1` = "camera-target world pos" (A3 §5). These are the
   only places a *metric* creature transform exists; the primitive stream never carries it.

## 8. Appendix — the pool-pollution mechanism (exact)

`SFXMesh` instances are pooled: `SFXRender.meshOrigin[64]` is allocated once (`SFXRender.cs:14-18`)
and reused each frame via `meshEmpty` (`:59-61`, hand-out `:605-609`). Each `SFXMesh` owns a
**fixed-size** vertex buffer `VbPos = new Vector3[VERTICES_MAX]` with `VERTICES_MAX = 14000`
(`SFXMesh.cs:18, 988`). Per frame:

- `Begin()` sets `VbOffset = 0` but **does not clear `VbPos`** (`SFXMesh.cs:200-206`).
- `PolyXxx()` writes only `VbPos[0 .. VbOffset)` — the real primitives for this frame.
- `End()` does `_mesh.vertices = VbPos;` — assigns the **entire 14000-length array**
  (`SFXMesh.cs:213`), so `mesh.vertexCount == 14000` and Unity computes `mesh.bounds` over all 14000.

Slots `[VbOffset .. 13999]` are therefore either `(0,0,0)` (never touched → zero-init) or **stale**
vertices from a previous frame/effect that used this pooled mesh more deeply. The AABB is the union
of the real primitives with `(0,0,0)` and that stale tail — hence the invariants measured in §5:
`vertCount≡14000`, origin always contained (100%), far-Z face pinned to 0 (88.6%). This is a textbook
Unity "assigned a fixed over-sized vertex array" bounds artifact, and it is why any *centroid/extent*
read off the MESH rows is unreliable while the *per-primitive* `PRIM` rows are clean.

---

### One-line résumé for the blackboard
`SFX_GetPrim` = post-GTE **screen-space** primitives (x,y pixels; z = −otz depth-**sort** key);
MESH bounds = those screen coords, **pool-polluted to the origin** (vertCount≡14000, origin∈AABB
100%); the logged VIEW/PROJ are the **3D-model** camera and must never be applied to the primitives.
⇒ the creature's **screen** path is recoverable from `PRIM` rows (no projection); its **world**
transform is absent from this stream and must come from DLL internals. Every "reproject the bounds as
a world position" conclusion is **VOID**.
