# A3 — THE MANAGED RENDER PATH: VRAM -> screen, and what a hot CLUT/texel recolor touches

> Scope: read-only. No install writes, no repo-code edits, no stock bytes reproduced. All Memoria
> cites are `Assembly-CSharp` relative to `C:/gd/FFIX/Memoria/`. Every claim is tagged **MEASURED**
> (read directly this session, cited to a file:line) or **INFERRED** (derived from a measured fact,
> or carried from a prior round's report, but not itself independently re-derived this session).
> Companion doc `A4-PRIORART.md` (this same `w4-recon/` dir) covers the kit's own texture-decode
> module; this report covers the ENGINE side — how the DLL's texels actually reach a screen pixel
> under `SFXRework`, and whether a container edit needs a relaunch.

---

## 0. HEADLINE

> **The hot-reload guarantee extends cleanly to textures — with an even stronger mechanism than W2/W3
> had.** Every `SFX.Play()` call (i.e. every cast) unconditionally wipes the ENTIRE managed texture
> cache (`PSXTextureMgr.Reset()`, 50 slots, MEASURED) before the container is even handed to the DLL,
> and the DLL re-pushes VRAM/CLUT pixel data into the managed mirror via the same native-callback
> channel the FIRST load used (INFERRED from the loader-script's own replay semantics + the fact the
> managed side assumes a from-scratch VRAM population every cast). A same-length CLUT/texel edit
> inside the container is therefore live on the very next cast, no relaunch — the render-path finding
> matches W2/W3's deploy posture exactly.
>
> **Texture PIXELS and texture IDENTITY cross the native/managed boundary through two completely
> different channels.** Identity (which VRAM tile + which CLUT row a primitive samples) rides on the
> SAME per-primitive struct A3-managed-boundary.md already mapped for geometry (`tpage`/`clut` fields
> on `POLY_FT3/FT4/GT3/GT4`, `SFX_GetPrim`). Pixels never ride that channel — they arrive via a
> SEPARATE, native-INITIATED push through the shared callback function pointer (`BattleCallback`,
> code 100/101/102), which memcpy's a raw VRAM rectangle into a managed `UInt16[524288]` array
> standing in for PS1 VRAM. There is no "GetVRAM" pull export among the DLL's 13 — MEASURED.
>
> **PSX per-texel STP (CLUT entry bit 15) survives the crossing but is collapsed to a binary
> cutout, not a translucency level.** It sets the generated `Texture2D`'s alpha to 0 or 255 only
> (`PSXTexture.ConvertABGR16toABGR32`, MEASURED), and only the **opaque** shader variant even reads
> that alpha (a `texkill` alpha-test in `SFX_OPA_GT`'s fragment program, MEASURED from the actual
> shader source). Real per-primitive translucency (additive/subtractive blending) is a totally
> separate mechanism keyed off the primitive's own ABR bits, not the CLUT. Concrete consequence for
> lever #1 (CLUT recolor): **CLUT entry 0 is the creature's cutout index — literally `0x0000` on all
> six of ef227's rows (cross-confirmed by A4-PRIORART's own `bgr555_rgba` read) — and it must stay
> exactly `0x0000` (RGB **and** STP both zero) or texels punch a hole or turn solid black.**
>
> **Runtime RGB tint (`Hi_ModifySummonModelRGB`) composes with the texture MULTIPLICATIVELY, and the
> observed values are always achromatic (R=G=B), so a hue-shifted CLUT keeps its hue through the tint
> — it only gets darker/brighter, never grey.** MEASURED from the actual `SFX_OPA_GT`/`SFX_ADD_GT`/
> `SFX_SUB_GT` shader source: `finalRGB = texel.rgb * vertexColor.rgb * _Color.rgb`, a pure per-channel
> multiply. A genuinely new risk this surfaces for W4: recolored texel channels that sit brighter than
> stock's neutral-grey-calibrated palette have less headroom before clipping under the effect's own
> `colorIntensity` multiplier (`ColorData[1]`=1.5x, `[2]`=2x, a per-effect static constant) — stock's
> palette was implicitly authored against a 128-baseline that leaves room for that multiply; an
> aggressively bright recolor may not have that room.
>
> **No other texture source shadows ef227.** The only alternate-texture-asset path in the whole render
> pipeline (`AssetManager.Load<Texture2D>("SpecialEffects/ef435/...")`) is hardcoded to exactly one
> effect id, `Special_Necron_Death` (435) — MEASURED, grepped, single call site. Bahamut has no such
> special case; it is 100% native VRAM/CLUT, so the reskin's only shadowing exposure is the ALREADY-
> KNOWN one from W2/W3: `Memoria.ini [Mod] FolderNames` priority order on the whole `ef227` container
> file itself.

---

## 1. Q1 — the VRAM -> screen trace, the texture cache, and the hot-reload verdict

### 1.1 The two channels across the boundary

**Channel A — texture IDENTITY, per-primitive, already mapped by `A3-managed-boundary.md`.**
`SFX_GetPrim` (`SFX.cs:751`, wrapper `SFXRender.cs:80`) hands back one `P_TAG*` per call. For the four
textured primitive kinds the creature and its props use (`POLY_FT3`/`FT4`/`GT3`/`GT4`,
`PSX_LIBGPU.cs:258-660`), the struct carries `UInt16 clut` at byte offset 14 and `UInt16 tpage` at byte
offset 22 (`FT3`; `FT4`/`GT3`/`GT4` same relative layout) — small integers, **no pixel data**. `SFXRender`
turns each `(code, clut, tpage)` triple into a 32-bit mesh-batching key via `SFXKey.GetABRTex`
(`SFXKey.cs:32-45`), which is dispatched to `SFXRender.PolyFt3/PolyFt4/PolyGt3/PolyGt4`
(`SFXRender.cs:340-368`).

**Channel B — texture PIXELS, native-PUSHED, not managed-pulled.** There is no "GetVRAM" export among
the DLL's 13 `DllImport`s (`SFX.cs:714-753`, already enumerated exhaustively by A3-managed-boundary.md
§1). Pixel bytes instead cross through the SAME reverse callback A3-managed-boundary.md documented for
sound/vibration/btl_seq — `BattleCallback(Int32 fullCode, ...)` (`SFX.cs:833`) — using three codes:

| callback code | managed handler | direction / effect |
|---|---|---|
| `100` | `PSXTextureMgr.LoadImage(x,y,w,h,(UInt16*)p)` — `SFX.cs:842` | "Load the rectangle `[x,y,w,h]` from a PSX-like Vram (TIM format)" (source's own comment) — the DLL hands managed code a raw pointer `p` into ITS OWN memory; managed code walks it directly with `(UInt16*)p` pointer arithmetic and copies into its own VRAM mirror |
| `101` | `PSXTextureMgr.StoreImage(...)` — `SFX.cs:869` | "Pass the Vram rectangle back to FF9SpecialEffectPlugin.dll" — the reverse direction, managed -> native (background-capture composite handoff) |
| `102` | `PSXTextureMgr.MoveImage(x,y,(Int16*)p)` — `SFX.cs:872` | blit/copy within the managed VRAM mirror, no new pixels |

So: **a shared, unsafe raw-pointer buffer, memcpy'd synchronously inside the callback** — not a getter
API, not a persistent shared-memory region either side polls. MEASURED, `SFX.cs:833-873`.

### 1.2 The managed VRAM mirror, and how a primitive resolves to a Unity texture

`PSXTextureMgr.originalVram` (`PSXTextureMgr.cs:17,464`) is a flat `UInt16[524288]` (`1024*512`) —
a direct managed mirror of PS1 VRAM, indexed `(y*1024+x)`. Callback code 100 writes into it
(`PSXTextureMgr.cs:89-107`); nothing else populates it for the summon path (see §1.4 for the one other
consumer, unrelated to summons).

**Resolving a primitive's `(tpage, clut)` to an actual `Texture2D`:**

```
tag->tpage, tag->clut                                  (Channel A, per-primitive)
    |  SFXKey.GetABRTex()                    SFXKey.cs:32-45
    v
meshKey (packs TP/TX/TY/clutX/clutY + blend bits)
    |  SFXRender.GetMesh(meshKey, code)      SFXRender.cs:566-610  -- batches all prims sharing meshKey
    v
SFXMesh.GetTexture()                          SFXMesh.cs:118-193
    |  SFXKey.GetTextureKey(meshKey)         SFXKey.cs:77-80  -- strips blend bits, keeps TP/TX/TY/clutX/clutY
    v
PSXTextureMgr.GetTexture(UInt32 key)          PSXTextureMgr.cs:192-220
    |  linear scan of a 50-slot cache (SST_MAX_TEXTURE, PSXTextureMgr.cs:462)
    |  HIT  -> return the EXISTING Texture2D, unchanged, NO re-decode
    |  MISS -> claim a free slot, PSXTexture.GenTexture(...)   PSXTexture.cs:23-40
                 -> CreateBufferColor32(TP,TX,TY,w,h,clutX,clutY)  PSXTexture.cs:42-118
                      reads PSXTextureMgr.originalVram AT THAT MOMENT, indexed+palette-looked-up
                 -> texture.SetPixels32(pixels); texture.Apply()
    v
_material.mainTexture = that Texture2D             SFXMesh.cs:240
_material.SetColor(_Color, ColorData[colIntensity] [* SFXColor])   SFXMesh.cs:263-266
Graphics.DrawMeshNow(_mesh, Matrix4x4.identity)     SFXMesh.cs:269
```

**Bahamut's texture pages decode through the 8bpp-indexed branch** (`CreateBufferColor32`'s `case 1`,
`PSXTexture.cs:73-89`): each 16-bit VRAM word yields two 8-bit palette indices, each looked up at
`psxIndexBase + paletteIndex` (`psxIndexBase = (clutX<<4)+(clutY<<10)`, `PSXTexture.cs:46`) — i.e. the
palette itself is ALSO just a rectangle of `originalVram`, addressed by the very same array Channel B
writes into. This matches A4-PRIORART's independent finding (`texture.py`) that ef227's parts are
8bpp/`128x128`/`0x4000`-byte pages with a 256-entry CLUT row per part — MEASURED, both lanes agree.

### 1.3 THE CACHE — 50 slots, keyed by VRAM/CLUT location, not by content or effect id

`PSXTextureMgr.list` is a fixed `PSXTexture[50]` (`SST_MAX_TEXTURE = 50`, `PSXTextureMgr.cs:462`). The
key (`SFXKey.GenerateKey(TP,TX,TY,clutX,clutY)`, `SFXKey.cs:47-55`) packs ONLY where-in-VRAM/CLUT a
texture page+palette combo lives — it carries **no effect id, no content hash, no cast counter**. A
cache HIT returns the stored `Texture2D` verbatim; the pixel decode only happens on a MISS. This is
exactly the shape of cache the task asked about ("does the managed side build texture objects it
caches — keyed how, invalidated when") — and it is genuinely a cache in the stale-data sense: nothing
about a hit re-validates against current VRAM content.

**Invalidation — two independent mechanisms, and the coarser one is what matters for a hot reskin:**

1. **Surgical** — `PSXTextureMgr.ClearKey(x,y)` (`PSXTextureMgr.cs:77-87`), called from the top of every
   `LoadImage`/`MoveImage` write, zeroes the `.key` of any cached slot whose OWN `(tx,ty)` — `tx=x>>6,
   ty=y>>8`, a coarse 64x256-texel tile — matches the just-written region. Forces the next `GetTexture`
   on that key to miss and regenerate.
2. **Wholesale** — `PSXTextureMgr.Reset()` (`PSXTextureMgr.cs:44-53`), called **unconditionally at the
   top of every single `SFX.Play()`** (`SFX.cs:1966`) — i.e. every cast, not just a cast of a
   *different* effect. Every slot's `.key` is set to `PSXTexture.EMPTY_KEY`. **This makes mechanism #1's
   tile-precision moot for the reskin's purposes: the cache starts EMPTY on every single cast,
   regardless of what changed.**

### 1.4 THE HOT-RELOAD VERDICT

**Yes — a same-length CLUT/texel edit inside the container shows up on the very next cast, exactly
like W2's camera edit and W3's timing edit. No relaunch.**

The chain, each link labelled:

1. `AssetManager.LoadBytes("SpecialEffects/ef227", true)` (`SFX.cs:1975`) re-reads the container off
   disc fresh on every `SFX.Play()` — **MEASURED this round is a re-cite; established independently by
   W2-RESCORE.md §5 and re-confirmed by the same call site read here.**
2. `SFX.Play()` calls `PSXTextureMgr.Reset()` (`SFX.cs:1966`) **before** handing the (freshly-read)
   bytes to `SFX_Play` — wiping the ENTIRE Unity-side texture cache regardless of effect identity.
   MEASURED, `SFX.cs:1966` precedes `SFX.cs:1979`'s `SFX.SFX_Play(...)` call in source order.
3. The DLL receives a fresh copy of the container (a pinned managed buffer, `SFX.cs:1978-1979`) and has
   no cross-call persistent state about "already uploaded this VRAM region" — the loader script (the
   `0x400`-offset op stream FORMAT.md §2/§3 already fully decoded) is a state machine over THIS call's
   bytes, and its `id 0`/`id 1`/`id 4` resources are the "VRAM image list"/"continuation"/"creature
   texture pages" the interpret pass pushes via callback 100. **INFERRED** (not re-disassembled this
   session) that this replay genuinely re-fires every cast rather than skipping on some native
   "already loaded" flag — but it is the only reading consistent with (a) the managed side's own design
   assuming a from-scratch VRAM population every cast (point 2, which IS unconditional and MEASURED),
   and (b) W0/W2's already-proven fact that the container is re-read fresh with no persistent native
   state surviving between casts (nothing in the DLL's contract exposes a way to skip re-init — `SFX_Play`
   is the sole entry point, called once per cast, `void` return, no "already loaded" signal).
4. Consequently the very first primitive of the very next cast that needs a texture is guaranteed a
   cache MISS (step 2 emptied every slot) and `GenTexture` reads `PSXTextureMgr.originalVram` **as it
   stands after step 3's callback replay** — i.e. the recolored bytes, if the callback already ran that
   cast's VRAM pushes before the first textured primitive draws (which it must, structurally: the loader
   script's resource loads happen before the effect program that emits draw primitives can run, by the
   container's own `container/chunk/resource` ordering FORMAT.md already validated on 372/372 files).

**This is a STRONGER guarantee than W2/W3 needed.** Camera/timing edits relied on "the container bytes
aren't cached." A texture edit additionally benefits from an UNCONDITIONAL per-cast wipe of the
*consuming* Unity-side cache, which removes even the theoretical edge case of a stale GPU-uploaded
`Texture2D` surviving a same-effect re-cast (e.g. testing an edit, reverting, re-testing in one game
session) — `PSXTextureMgr.list[i].texture` objects are REUSED (not destroyed) across casts if the size
matches (`PSXTexture.GenTexture`'s `if (texture==null || tw!=w || th!=h)` guard, `PSXTexture.cs:25-30`),
but their PIXELS are always rewritten by `CreateBufferColor32` on the guaranteed-miss regeneration, so
reuse of the Texture2D *object* never means reuse of stale *pixels*.

**One capacity note, not a blocker for lever #1:** the 50-slot cache has no eviction beyond
`Reset()`/`ClearKey` — if a single cast ever needs more than 50 *distinct* `(TP,TX,TY,clutX,clutY)`
combinations live at once, `GetTexture` hits `Debug.Assert(false); return null` (`PSXTextureMgr.cs:188,
218`), a genuine (if apparently never-hit-in-stock-play) failure mode. **This is pre-existing engine
behavior, unrelated to and not worsened by lever #1** — an in-place CLUT recolor touches the SAME
`(TP,TX,TY,clutX,clutY)` coordinates stock already uses (same page layout, same CLUT row addresses), so
it creates zero NEW distinct keys. It would only become relevant if lever #2 (texel repaint) ever
changed a part's TPAGE/CLUT VRAM coordinates — worth a gate check at that point, not now.

---

## 2. Q2 — PSX STP semantics: what the managed renderer preserves, and what a careless flip does

### 2.1 Where STP is read, exactly

`PSXTexture.ConvertABGR16toABGR32` (`PSXTexture.cs:120-132`) is the ONLY place a raw 16-bit VRAM/CLUT
halfword's bit 15 (`0x8000`, the STP bit) is consulted, during `Texture2D` generation:

```csharp
if ((num & 0x8000) != 0)        // STP set
    pixels[i].a = 255;           //   -> ALWAYS opaque, regardless of RGB
else if ((num & 0x7FFF) != 0)   // STP clear, RGB non-zero
    pixels[i].a = 255;           //   -> opaque
else                              // STP clear, RGB == 0 (raw halfword == 0x0000)
    pixels[i].a = 0;              //   -> fully transparent (cutout)
```

**This collapses STP to a binary alpha (0 or 255) — there is no intermediate "translucent" alpha value
anywhere in this conversion.** MEASURED, direct read of the source.

That alpha is consumed in exactly one place downstream: `SFX_OPA_GT`'s fragment program
(`Memoria.Patcher/StreamingAssets/Shaders/SFX_OPA_GT.txt:56-72`, MEASURED — this is the actual shipped
shader source, a `d3d9`-target assembly dump, not a guess from naming):

```
texld  r0, t0, s0                     ; sample texel -> r0 (rgba, alpha from ConvertABGR16toABGR32)
mad    r1, r0.w, v0.w, -c0.x          ; r1 = texel.a * vtxAlpha - _Threshold
mul    r0, r0, v0                     ; r0 = texel * vertexColor
mov    oC0, r0
texkill r1                            ; DISCARD the fragment if r1 < 0
```

`_Threshold` defaults to `0.0295` (~7.5/255) or `0.05` per-effect (`SFXMesh.cs:267`, keyed off a
static per-effect bit, `SFX.colThreshold`). Since alpha only ever comes out as `0` or `255` (`0.0` or
`1.0` normalized) from `ConvertABGR16toABGR32`, this alpha test is a **hard binary cutout**, not a
translucency gradient: `texel.a==0` always discards (a hole), `texel.a==255` always passes (fully
solid). **The `SFX_ADD_GT`/`SFX_SUB_GT` fragment programs have NO `texkill` and NO alpha test at all**
(`SFX_ADD_GT.txt:57-69`, `SFX_SUB_GT.txt:58-71` — both just `texld; mul; mov`) — so **STP has ZERO
visible effect on the additive/subtractive (translucent VFX) shader path.** Real per-primitive
translucency intensity there comes from the primitive's own ABR rate (`SFXMesh.AbrAlphaData = {63,127,
127,31}`, `SFXMesh.cs:941-946`, indexed by `tpage>>5&3` via `SFXKey.tmpABR`) baked into vertex alpha —
a **completely separate mechanism from CLUT/STP**, already established as primitive-header data (not
CLUT data) by the earlier boundary work.

### 2.2 What a careless STP flip does, concretely

Because only the **opaque** shader (`SFX_OPA_GT`/`SFX_OPA_G`) reads it, and only as a 0/255 cutout gated
by whether the raw RGB is also zero:

| stock entry | recolor mistake | visible result |
|---|---|---|
| `RGB=(0,0,0)`, `STP=0` (the transparent/cutout convention) | recolor tool sets `STP=1` but leaves RGB at `(0,0,0)` | the texel flips from **invisible (hole)** to **solid black** — a black patch appears where the creature/scenery mesh should show background or an underlying layer through a gap |
| `RGB=(0,0,0)`, `STP=1` (an intentional opaque black, e.g. a shadow/outline detail) | recolor tool clears `STP` without also nudging RGB off pure black | the texel flips from **solid black** to **invisible** — a hole punches through what should be a solid dark region (outline, pupil, shadow) |
| any `RGB != (0,0,0)` | STP flipped either direction | **no visible change** — alpha is `255` either way; STP is inert for non-black texels |

**The load-bearing risk is entirely concentrated on near-black palette entries**, and specifically on
**CLUT entry 0**: `A4-PRIORART.md` independently measured (via the kit's own `texture.py`,
`bgr555_rgba`) that entry 0 is literally `0x0000` on **all six** of ef227's CLUT rows — i.e. it is
structurally the creature's cutout index, cross-confirmed from a second, independent lane (the kit's
decoder) against this session's reading of the actual consuming shader. **Concrete guidance for lever
#1 (CLUT recolor): leave entry 0 byte-identical (`0x0000`, both fields) on every row unless the goal is
deliberately to add or remove a cutout region, and any hue/palette transform applied to the OTHER 255
entries must not incidentally drive one of them to exactly `(0,0,0)` with `STP` clear** (which would
silently create a NEW unintended hole) **or away from `(0,0,0)` if `STP` is clear and RGB was already
zero** (turning an intended hole solid). A hue-rotation or palette-map that special-cases "if
source==0x0000, keep 0x0000" is a one-line guard that removes this whole risk class.

---

## 3. Q3 — how runtime RGB (`Hi_ModifySummonModelRGB`/`Hi_ModifyEffModelRGB`) composes with texels

### 3.1 The managed compositing formula — MEASURED directly from the shipped shader source

All three relevant shaders (`SFX_OPA_GT`, `SFX_ADD_GT`, `SFX_SUB_GT`,
`Memoria.Patcher/StreamingAssets/Shaders/*.txt`) share the same vertex-stage color math:

```
r0.xyz = vertexColor.rgb * _Color.rgb        ; vertexColor = the primitive's own r0/g0/b0 (VbCol)
oD0.xyz = r0.xyz * vertexColor.a             ; further scaled by per-vertex alpha (ABR rate / shade)
```

and the same fragment-stage math (differing only in the presence/absence of the OPA variant's
`texkill`, §2.1):

```
r0 = tex2D(_MainTex, uv)      ; the CLUT-decoded texel, from PSXTextureMgr.GetTexture (§1.2)
oC0 = r0 * v0                 ; texel * (vertexColor * _Color * vertexAlpha)
```

So the full chain, in order, is a **pure per-channel MULTIPLY**:

```
finalRGB = texel.rgb  *  primitiveColor.rgb (r0/g0/b0, normalized 0..1)  *  _Color.rgb  *  vertexAlphaFactor
```

`_Color` is set per-draw in `SFXMesh.Render()` (`SFXMesh.cs:263-266`) to
`ColorData[SFX.colIntensity]` (optionally further multiplied by `SFXDataMesh.SFXColor` when a
`RunningInstance` supplies one — a hook used by the kit's OWN authored/reworked effect lane, not
relevant to a native ef227 cast). `ColorData` is `{(1,1,1,1), (1.5,1.5,1.5,1), (2,2,2,1)}`
(`SFXMesh.cs:52-55`), and `SFX.colIntensity` is a **static per-effect constant** derived once at
`SFX.Play()` time from a bit-packed lookup table (`SFX.playParam[effNum]`, `SFX.cs:1952-1956`) — fixed
for the whole cast, not a per-frame ramp. (This session did not decode `playParam`'s literal value for
index 227 specifically — low value for the reskin question, the mechanism is what matters.)

### 3.2 Where `Hi_ModifySummonModelRGB`'s values actually land — INFERRED, cross-lane

The only color-carrying field ANY textured primitive crosses the boundary with is `r0/g0/b0`
(`POLY_FT3`/`FT4`/`GT3`/`GT4`, `PSX_LIBGPU.cs`) — confirmed exhaustive: `A3-managed-boundary.md`'s full
13-export enumeration has no separate "set global tint" channel the managed side reads. FORMAT.md §2.3
independently states Bahamut's own primitives ship "inline neutral-grey RGB" (i.e. a `128,128,128`
baseline — the PSX convention for "no tint, texture passes through unmodified" under a x2-scaled
multiply, matching `ColorData[0]=(1,1,1,1)` being the DEFAULT `colIntensity`, not the shader's `2,2,2,1`
*Properties* default which is overridden every draw). `EF227-CHOREOGRAPHY.md` (tier-r) records
`Hi_ModifySummonModelRGB` (op 65) firing with **all three args always equal**
(`$a1=$a2=$a3=0xffffffe0` = -32 signed, or `=0xffffffa0` = -96 signed) during exactly the ticks W3
already identified as an "arrival ramp" phase, and separately records that W3's own offline emulator
tracks an "RGB" value that must read `0` at the correct phase boundary and reads `+44` (over-bright) in
the deliberate mis-retime falsifier (W3-RETIME.md §5 item 7) — i.e. this native call's argument is
almost certainly a **signed delta from the 128 baseline**, computed by the SAME arrival-progress ramp
W3 already reverse-engineered, and it is applied natively (baked into the r0/g0/b0 bytes of whatever
`Hi_DrawSummonModel` emits that frame) **before** the primitive ever reaches `SFX_GetPrim`. This part —
what happens *inside* the DLL before the boundary — is **INFERRED**, not re-disassembled this session;
what happens *after* the boundary (§3.1) is MEASURED with high confidence (actual shader assembly, not
inference from naming).

### 3.3 The concrete design consequence asked for

**A hue-shifted CLUT under this grey-tint phase DOES still show the hue.** The compositing is a
per-channel multiply and the observed runtime deltas are always achromatic (`R=G=B`, i.e. a uniform
scalar, not a per-channel color cast). Multiplying three channels by the SAME scalar preserves every
hue/saturation ratio between them — it only changes luminance. Concretely: if lever #1 recolors
Bahamut's palette from its stock blue-grey toward, say, crimson, the entrance phase (ticks ~95-119,
where the two sampled deltas are negative — darkening toward black) will show a **darker crimson**, not
grey and not the stock hue — and it will ramp back to full-saturation crimson at the same tick the
stock cinematic ramps back to full brightness, because the ramp is driven by the same clock W3 already
proved doesn't move under a same-length recolor.

**A genuinely new risk this surfaces, worth carrying into lever #1's authoring guidance:** stock's
palette is implicitly calibrated against the `128`-baseline, `colIntensity`-multiplied pipeline — a
channel at `128` under a `2x` `colIntensity` phase lands at exactly `256`(clamped `255`), i.e. stock's
neutral grey has just enough headroom to hit full brightness and no more, by design. A recolor that
pushes a channel already near `255` in the palette will clip identically under any phase where
`colIntensity` is `1.5x`/`2x` (or a positive `Hi_ModifySummonModelRGB` delta fires, unobserved in the
two sampled negative values but structurally possible at other ticks) in a way stock's own palette
never does, because stock was never authored anywhere near that ceiling. Not a blocker — just a reason
to keep recolored palette entries a little below full saturation/value if a hue-preserving-but-vivid
recolor is the goal, and to sanity-check the result against the exact ticks where `Hi_ModifySummonModelRGB`
is known to fire (EF227-CHOREOGRAPHY.md's own op-65 table).

---

## 4. Q4 — any other texture source that could shadow the container edit

### 4.1 Searched and ruled out for ef227

- **No DLL-external creature texture asset path exists for Bahamut.** The one and only place the
  managed side loads a `Texture2D` via `AssetManager.Load<Texture2D>(...)` for anything under
  `SpecialEffects/` is `PSXTextureMgr.SpEff435()` (`PSXTextureMgr.cs:293-345`), and it is gated
  `if (effNum == SpecialEffect.Special_Necron_Death)` at its **single call site**
  (`SFX.cs:1972-1973`). Grepped the whole `Assembly-CSharp` tree for `SpecialEffects/ef` outside that
  one case (see command output, this session) — every other hit is the `.seq`-text /
  `PlayerSequence.seq` machinery (W3's "third clock," already fully mapped, text not textures) or the
  raw-bytes container load itself. **ef227 has none of this — it is 100% native VRAM/CLUT, no
  loose-PNG shadow risk.** MEASURED (grep + call-site read).
- **No HD-texture-pack / texture-cache-folder toggle exists for SFX.** Grepped
  `Assembly-CSharp/Memoria/Configuration*` for `HDTexture`/`SFXHD`/`TexturePack`/`HighRes.*Texture` —
  zero hits anywhere in the assembly. `Configuration.Graphics.SFXSmoothTexture` (referenced throughout
  `SFXMesh.cs`/`SFXDataMesh.cs`) is a **filter-mode toggle only** (`FilterMode.Point` vs `.Bilinear`,
  `ModelFactory.SetMatFilter`) — it changes how the SAME texture is sampled, never which bytes are
  sampled. MEASURED.
- **`PSX_LIBGPU.originalVram`/`PSX_LIBGPU.LoadImage` is DEAD CODE — do not confuse it with the live
  path.** `PSX_LIBGPU.cs` (the struct-definitions file) declares its OWN `UInt16[524288] originalVram`
  and an unsafe `LoadImage(RECT*, UInt32*)` (`PSX_LIBGPU.cs:25-48,73`) — a **second, differently-typed,
  entirely unused** VRAM mirror. Grepped every caller of `PSX_LIBGPU.LoadImage`/`.originalVram` in the
  whole assembly: the only hits are inside `PSX_LIBGPU.cs` itself (MEASURED, this session). The LIVE
  VRAM mirror the whole render path actually reads is exclusively `PSXTextureMgr.originalVram`
  (§1.2-1.3). Worth naming explicitly so a future reader grepping for "originalVram" doesn't chase the
  wrong array.
- **`PSXTextureMgr.LoadTCBInVram`** (`PSXTextureMgr.cs:414-449`) writes into the SAME shared
  `originalVram` array from a totally different source — `.tcb` SPS-particle binaries (the project's
  own [SPS authoring] pillar, `project-ff9-sps-authoring`). This is not a texture SOURCE for the
  summon path, but it is a **second writer of the same shared VRAM mirror**: if a field's SPS particle
  system and a summon cast were ever concurrently active and happened to collide on the same VRAM tile
  coordinates, one could stomp the other. Out of scope for W4 (summons and field SPS don't run
  concurrently in the cases this project ships), flagged only because it's the one place the "one
  shared mutable VRAM array, multiple independent writers" shape recurs.

### 4.2 The one shadow risk that DOES apply — already known, re-confirmed here

The only real shadowing exposure for a container-level texture edit is the **same one W2/W3 already
established and guarded**: `Memoria.ini [Mod] FolderNames` stacks mod folders in priority order, and
`AssetManager.LoadBytes("SpecialEffects/ef227", ...)` probes each folder in that order — a mod folder
earlier in the list shipping its own `ef227` wins, silently (`suppressMissingError = true`, no log
either way). This is not a NEW finding; it is the identical mechanism the camera/timing rungs already
documented and it applies unchanged to a texture-only edit, because the override unit is the WHOLE
container file, not a sub-resource.

---

## 5. Cite index (fast lookup)

- DllImport enumeration (no VRAM pull export): `Global/SFX/SFX.cs:714-753` (re-cite, mapped fully by
  `thomas-swap/disasm/A3-managed-boundary.md`).
- Callback VRAM push (codes 100/101/102): `Global/SFX/SFX.cs:833,840-844,868-873`.
- Managed VRAM mirror + its writers: `Global/PSXTexture/PSXTextureMgr.cs:17,44-53,77-107,124-162,464`.
- Texture cache (50 slots, key = VRAM/CLUT location): `Global/PSXTexture/PSXTextureMgr.cs:164-220,462`.
- VRAM -> `Texture2D` decode incl. STP->alpha: `Global/PSXTexture/PSXTexture.cs:23-132`.
- Primitive `tpage`/`clut` struct fields: `Global/PSX_LIBGPU.cs:258-660` (`POLY_FT3/FT4/GT3/GT4`).
- Dead second VRAM mirror (do not confuse): `Global/PSX_LIBGPU.cs:25-48,73`.
- meshKey construction from `(tpage,clut)`: `Global/SFXKey.cs:32-55`.
- Primitive dispatch + mesh batching: `Global/SFXRender/SFXRender.cs:209-322,340-384,566-610`.
- Per-vertex color from primitive header -> `VbCol`: `Global/SFXMesh/SFXMesh.cs:366-814` (`PolyFt3` etc).
- `_alpha`/ABR rate table + shade-alpha doubling: `Global/SFXMesh/SFXMesh.cs:78-116,931-946`.
- Render: texture bind, `_Color` set, draw call: `Global/SFXMesh/SFXMesh.cs:235-274`.
- `SFX.Play()`: cache wipe + fresh container read, no relaunch: `Global/SFX/SFX.cs:1937-1987` (esp.
  `:1966` `PSXTextureMgr.Reset()`, `:1975` `AssetManager.LoadBytes`).
- `SFXDataMesh.Runtime` (SFXRework native driver) routes through the SAME `SFXRender.Update()`/
  `SFXMesh` path, only changing who drives the per-frame tick:
  `Memoria/Battle/SFX/SFXDataMesh.cs:556-654` (`Load`/`Begin`/`Render`).
  `EffectMaterial`/`RunningInstance.TryGetCustomColor` (the kit's OWN authored-effect color-override
  hook) is a **separate, unrelated** managed-only path (`SFXDataMesh.cs:108-205`) that native ef227
  does not use — noted only so it isn't mistaken for part of the native pipeline.
- Shader source (compositing formula + STP cutout), shipped as readable d3d9 asm:
  `Memoria.Patcher/StreamingAssets/Shaders/SFX_OPA_GT.txt`, `SFX_ADD_GT.txt`, `SFX_SUB_GT.txt`.
- The one hardcoded alternate-texture-source special case (Necron only, not applicable to Bahamut):
  `Global/PSXTexture/PSXTextureMgr.cs:293-345`, call site `Global/SFX/SFX.cs:1972-1973`.
- `Hi_ModifySummonModelRGB`/`Hi_ModifyEffModelRGB` observed args (native side, INFERRED semantics):
  `studies/custom-summons/tier-r/EF227-CHOREOGRAPHY.md:104,121,137,151,240` etc.
- CLUT entry 0 == `0x0000` on all six ef227 rows (independent cross-lane confirmation): this session's
  companion report `studies/custom-summons/tier-w/w4-recon/A4-PRIORART.md` §1 (`bgr555_rgba`).

---

## 6. Bottom line for W4's locked frame

1. **Lever #1 (CLUT/palette recolor) is hot-reload-safe by the SAME mechanism family as W2/W3**, with
   an extra, unconditional per-cast cache wipe on the managed side that makes the guarantee even
   cleaner than the camera/timing rungs needed. No relaunch, no partial-cache edge case.
2. **The one hard rule a recolor tool must encode:** CLUT entry 0 (measured `0x0000` on all six of
   ef227's rows) is the creature's transparent/cutout index for the OPAQUE shader path; keep it
   byte-identical, or treat any accidental drift to/from exactly `(0,0,0)` with `STP` clear as a
   hole-punch/solid-patch bug, not a rendering glitch to chase elsewhere.
3. **Hue survives the runtime tint** because the tint is achromatic and the compositing is a straight
   multiply — a recolor's hue reads correctly at every tick, including the ~95-119 and ~85 (per the
   choreography doc's `c1` sample) darkening windows.
4. **Headroom, not hue, is the thing to watch** — keep recolored channel values a little short of full
   value/saturation so the effect's own `colorIntensity` multiplier (1x/1.5x/2x, static per effect) has
   the same clipping margin stock's neutral-grey-calibrated palette was implicitly authored with.
5. **No other texture source competes with the container override for ef227** — the reskin's only
   shadowing exposure is the already-known, already-guarded `FolderNames` priority order on the whole
   container file.
