# Adversarial verification: CLAIM `getprim-screenspace`

**VERDICT: CONFIRMED** (with one load-bearing caveat for the round's goal).

## Claim under test
SFX_GetPrim returns primitives whose x0/y0 are already screen-space 2D coordinates
plus otz depth, so the native summon path exposes already-projected positions
(GTE done inside the DLL).

## Independent re-derivation (C# source, not trusting prior evidence)

This is a managed-side claim; it is fully decidable in `Assembly-CSharp` without the DLL,
and I re-derived every link of the chain fresh.

1. **The DllImport signature** — `SFX.cs:753`
   ```
   [DllImport("FF9SpecialEffectPlugin")]
   public static extern IntPtr SFX_GetPrim(ref Int32 otz);
   ```
   Returns a raw pointer into the DLL's primitive list; the depth is handed back through
   the `ref Int32 otz` out-param. The DLL, not C#, produces both.

2. **The caller** — `SFXRender.cs:79-84`
   ```
   Int32 num = 0;
   PSX_LIBGPU.P_TAG* ptr = (PSX_LIBGPU.P_TAG*)SFX.SFX_GetPrim(ref num);
   if (ptr == null) break;
   SFXMesh.GzDepth = -num;      // the otz becomes the per-primitive depth
   SFXRender.Add(ptr);
   ```
   `num` (the otz) is negated into a single `GzDepth` used for the WHOLE primitive.

3. **The primitive struct** — `PSX_LIBGPU.cs:204-223`
   `POLY_F3` (and FT3/G3/GT3/F4/FT4/…) store `public Int16 x0; public Int16 y0; x1,y1,x2,y2…`.
   There is **no per-vertex z field** — a triangle carries three Int16 (x,y) screen pairs
   only. This is the canonical PSX GPU packet layout (post-GTE `SX/SY`).

4. **The vertex build applies NO projection** — `SFXMesh.cs:338-351` (`PolyF3`, cited 340-341)
   ```
   Int32 num  = obj->x0 + drOffsetX;   // pure additive 2D offset
   Int32 num2 = obj->y0 + drOffsetY;
   __gPos[GPosIndex].Set(num, num2, GzDepth);   // x,y = screen; z = the shared otz
   ```
   Every primitive builder (PolyF3/FT3/G3/GT3/F4/FT4/G4/GT4/Sprite/Tile/LineF2, lines
   340-892) does the same: `obj->x{n}+drOffsetX`, `obj->y{n}+drOffsetY`, `GzDepth`. There is
   **no matrix multiply, no world-to-screen, no perspective divide** anywhere on this path.

5. **`drOffsetX/Y` is a drawing-environment translate, not a projection** — `SFXRender.cs:433-437`
   `DR_OFFSET` sets `drOffsetX = (code[1] & 0xFFFF) + widescreen`, `drOffsetY = code[1]>>16`.
   That is the PSX GPU DR_OFFSET packet: a 2D pixel translation. Confirms x0/y0 live in the
   same 2D screen space the offset is expressed in.

6. **Rendered as screen-space** — the mesh goes out with **identity** transforms on both ends:
   `SFXRender.cs:130` sets `camera.worldToCameraMatrix = Matrix4x4.identity` for the whole
   SFX pass, and `SFXMesh.cs:269` draws with `Graphics.DrawMeshNow(_mesh, Matrix4x4.identity)`.
   The vertices are consumed as already-in-screen coordinates.

7. **Independent corroboration** — `PSXGPU.cs:191-195` (`exePolyF3`, the debug-primitive path)
   builds `new Vector3((Single)ObjPtr->x0, (Single)ObjPtr->y0, PSXGPU.zDepth)` — same reading of
   x0/y0 as screen coordinates + a separate scalar depth. Two independent consumers agree.

## Refutation attempts (all failed to refute)
- *Would-be refuter:* SFXMesh applying a world→screen projection to x0/y0. **Not present** —
  every builder only adds a 2D offset (steps 4-5). Refuted the refuter.
- *Error-stub / real-body confusion:* N/A — this is C# source, no .pdata funclets involved.
- *Endianness / fixed-point misread:* x0/y0 are plain `Int16` screen pixels; otz is a plain
  `Int32`. No fixed-point scaling, no byte-swap. Checked.
- *Scratch-buffer mislabel (the prior round's STATIC_TABLE trap):* N/A — the values flow live
  through the P/Invoke return + ref-param, not a zero-on-disk .data buffer.

## The load-bearing caveat (for the orchestrator's actual goal)
The claim is TRUE but its usefulness for **recovering the creature's true per-frame transform
is limited**, and the claim's own wording ("already-projected positions") is exactly why:

- x0/y0 are **2D screen pixels** — the perspective divide already happened inside the DLL's
  GTE. You cannot read a 3D position off them without un-projecting through the exact
  per-frame camera (VIEW+PROJ), which the prior camera work showed both MOVES and zooms.
- The depth is a **single per-primitive OT value** (`GzDepth = -otz`), shared by all 3 verts
  of a triangle (SFXMesh.cs:346-350). It is an ordering-table sort key, coarse and
  primitive-flat — **not** a real per-vertex camera-space z. Un-projection with it recovers
  at best a crude, quantized point, not a rigid transform.
- So SFX_GetPrim confirms the summon's geometry is exposed **already flattened to the
  screen** — which is precisely the reason a data-side method cannot recover the creature's
  true 3D per-frame transform from it. The recoverable 3D transform, if any, lives upstream
  in the DLL's `Hi_Summon*` / bone-matrix subsystem (the array @ base RVA 0x220830, stride
  0x58), BEFORE the GTE projection — not in the GetPrim output. This matches the round's
  NEXT-step direction.

## Bottom line
CONFIRMED: SFX_GetPrim yields screen-space 2D (Int16 x/y) + a single per-primitive otz depth;
the GTE projection is done inside the DLL; the C# side applies zero projection and renders
identity-transformed. The claim's factual content holds on every cited line. The only
correction is to expectations, not to the claim: "already-projected" means depth is gone, so
this path is a dead-end for TRUE-transform recovery — that must come from the pre-projection
bone/matrix subsystem.
