# D1 — THE TRACKING FIX: identify the visible creature and capture its real transform

**Slice question:** design the probe extension that logs, per frame, every candidate native model's
identity + world transform (all 32 eff slots **and** the summon slot), so ONE instrumented cast
empirically settles which slot is the on-screen dragon and yields its true trajectory.

**Deliverable:** a nearly-verbatim-applicable patch to
`C:/gd/FFIX/Memoria/Assembly-CSharp/Memoria/Battle/SFX/SfxMeshProbe.cs` (§3), the identification
protocol (§4), volume control (§5), provenance (§6).

All RVAs are module-base-relative (x64 `ImageBase 0x180000000`, x86 `0x10000000`). Every constant in
the patch carries an `fn@rva` citation. Runtime values are zero-on-disk `.bss`/heap; only LAYOUT +
LOGIC are static-recoverable.

---

## 0. HEADLINE — read this before writing any code

1. **The EFFARR hypothesis is refuted and D1 does not re-open it.** M1 §7 and M5 §7 independently
   proved it (eff models are structurally rigid — all five registrars null `DATA+motion`, there is no
   `Hi_Set*EffModelMotion` string in the image, and `Hi_DrawEffModelByBone` *reads the summon array*
   to parent an eff model to a creature bone). The eff-slot rows in this patch exist as a **runtime
   falsification test** of that static proof and as the first census of what else is on screen — not
   as a tracking candidate.

2. **The s52 ROOT probe is reading the right array, the right slot, and a *real* field — and the
   composed-matrix fix is a REFINEMENT, not the explanation for the bad promo.** M5 §5 gives the law:
   `bone[0].t = R_root · clipRootTranslation(frame) + T_root`, and M5 §5's own measurement is that
   Bahamut's clip root-translation track spans only **7–246 units per axis**. With the authored scale
   capped at 3.0×, the composed translation can differ from the logged anchor by **at most ≈ 740
   units** — it cannot move a 40,000-unit staging point. Anyone expecting `+0x38` to "fix the flight"
   will be disappointed and will waste a playtest. Say it in the commit message.

3. **The actual answer to "the logged trajectory does not match where the creature visibly is" is that
   it DOES match** — M5 §8 segmented the existing 512-frame capture and it reproduces the user's
   4-phase video beat for beat (fly-down `Y −4096→+4092`; a 73k-unit Z fly-by over 25 frames; then a
   **stationary** creature from frame 301 to 561 while the camera does the work). A summon that
   "floats in the air and charges the beam with the camera on him" **is** a frozen root. The prior
   verdict was a mis-segmentation, and the ~40,000 figure is the fly-by, not the charge.

4. **What is actually missing, and what this patch is really for:** (a) the authored **scale**, which
   `root_reproject.py:43,75` discards (M5 Finding B); (b) a **framing datum** — the root point is node
   0 of a 93-bone skeleton and is not the silhouette centre (M5 Finding D-3); (c) an **empirical
   identity check** that the thing being tracked is the thing on screen. This patch delivers a
   reprojection-ready world transform for every model, an aggregate silhouette envelope, and a
   full-slot census, in one cast.

5. **NEW THIS SLICE — M5 §9 item 2 is FALSIFIED. Do NOT log `DATA+0x78` "the scale triple".** An
   image-wide sweep of every non-stack `[reg+0x78]` access finds exactly **two writers and one
   reader**, and none of them ever stores an authored scale:
   * `model_prepare@0x7120 : 0x7203` — `mov dword[rcx+0x78], 0x10001000` (register time, = 1.0).
   * `pose_eval@0x186a0 : 0x187b5` — `mov dword[rsi+0x78], 0x10001000` — **and this is inside the
     `scale == NULL` branch** (`test r15,r15; je 0x187b2` @`0x18761`).
   * `0x5560 : 0x5575` — `movsx edx, word[rcx+0x78]`, called only from that same no-scale branch
     (`0x187c0`).
   When a scale IS passed, `pose_eval` builds a local SVECTOR from it (`0x18763`–`0x187a6`) and calls
   `ScaleMatrix 0x3b60(rbx, local, rbx)` with `rcx == r8 == rbx == DATA+0x40` (`0x1879a`/`0x18797`) —
   i.e. **the scale is folded IN PLACE into `DATA+0x40`'s 3×3 and `+0x78` is never touched.**
   `DATA+0x78` is therefore *always* `1.0` and carries zero information. The authored scale is
   recoverable **only** as the column norms of the logged 3×3 — exactly what M5 Finding B measured.
   This patch logs the 3×3 of the *composed* matrix, which inherits the same scale (the compose loads
   `DATA+0x40` incl. `S` into the GTE at `0x7edc`–`0x7f04` before multiplying the clip rotation).

6. **NEW THIS SLICE — an un-drawn model is provably NULL, not garbage.** `model_prepare@0x7120 :
   0x71f7` explicitly zeroes `[rcx+0x38]` (the bones pointer) at register time (x86 twin:
   `0x6980 : 0x69cc`, `mov dword[edi+0x20],0`). So `bones == 0` is a *guaranteed* "this model has
   never been drawn" signal, and the probe can never read arena garbage for a never-drawn slot. This
   removes the single biggest correctness hazard from the design.

---

## 1. Where the per-frame transform lives — the exact reads

Two transforms per model, both needed:

| | x64 | x86 | what it is |
|---|---|---|---|
| **anchor** | `DATA+0x40` | `DATA+0x24` | the `(rot,pos,scale)` the `.seq` handed `Draw` this frame, composed by `pose_eval@0x186a0` (x86 `0x14600 : 0x14610 lea esi,[edi+0x24]`). Rotation **already multiplied by the authored scale** (§0.5). This is what s52 logs today. |
| **composed** | `*(MATRIX*)(DATA+0x38)`, node 0 | `*(MATRIX*)(DATA+0x20)`, node 0 | the matrix actually fed to the GTE, built every Draw by the node builder `0x7820` (x86 `0x70c0 : 0x70e0 mov [edx+0x20],esi`). Under a motion this is `anchor ∘ clip[frame]`; for a rigid eff model it is the anchor with columns 1,2 negated and the translation verbatim. |

Within a PSX `MATRIX` (32 B, **identical on both arches**): rotation `9 × s16` fp12 at `+0x00..+0x11`,
translation `3 × s32` at `+0x14/+0x18/+0x1c`.

**The bones pointer is a HOST pointer, directly dereferenceable from managed code.**
`DrawSummonModel@0x17740` decodes the arena cursor from PSX space *before* the call and re-encodes the
returned cursor *after* (`0x17879 call 0x12940` host→PSX, result to `[ctx+0x24]` @`0x17885`); the x86
build shows the same shape explicitly (`push dword[eax+0x24]; call 0x100010d0` → host, `0x13df1`–
`0x13e06`). Contrast `DATA+0x08`, which holds a **PSX-format** geometry address (needs the
`0x7120 : 0x7130-0x71d4` decode) and is therefore **not** naively dereferenceable — that is why the
bone-count is an ini parameter in §3 and not a runtime read (§5.4).

---

## 2. THE CONSTANT SETS — both arches, every value cited

Everything below was re-derived this slice from the user's own DLL, not copied from a prior artifact.

### 2.1 The summon array (LENGTH 1 — the creature)

| item | x64 | x86 | evidence |
|---|---|---|---|
| record base RVA | `0x220830` | `0x20869c` | x64 `Hi_RegisterSummonModel@0x15f01`; x86 `Hi_DrawEffModelByBone@0x13550 : 0x135b8 add ecx, 0x1020869c` |
| stride (unused, len 1) | `0x58` | `0x54` | x64 `imul rax,rsi,0x58` @`0x168f1`; x86 `imul ecx,eax,0x54` @`0x135b5` |
| `active` u8 | `rec+0x50` | `rec+0x4c` | x64 `cmp byte[rax+rcx+0x50],r14b` @`0x168f5`; x86 `cmp byte[ecx+0x4c],0` @`0x135be` |
| `data` ptr | `rec+0x00` | `rec+0x00` | x64 `mov rax,[rax+rcx]` @`0x16900`; x86 `mov ecx,[ecx]` @`0x135c8`; also `mov ebx,[edi]` @`0x13dcf` |
| **motion frame counter u16** | `rec+0x54` | `rec+0x50` | x64 `inc word ptr [rdi+0x54]` @`0x17888` (rdi = record, since `mov rax,[rdi]` = DATA @`0x1788c`); x86 `inc word ptr [edi+0x50]` @`0x13e33`, read @`0x13dd8`, clamp-write @`0x13ded` |

### 2.2 The eff-model array (32 slots — the props)

| item | x64 | x86 | evidence |
|---|---|---|---|
| base RVA | `0x220230` | `0x20819c` | x64 `Hi_RegisterSolidEffModel@0x15ac0 : lea rbx,[rip+0x20a75d]` @`0x15acc`; x86 `mov esi, 0x1020819c` @`0x12d84`, and `[esi*8+0x1020819c]` @`0x13570` |
| stride | `0x30` | `0x28` | x64 `add rbx,0x30` @`0x15add`; x86 `add esi,0x28` @`0x12d97` (+ index form `lea esi,[eax+eax*4]; [esi*8+base]` = ×40 @`0x1355e`) |
| slot count | `32` | `32` | `cmp eax,0x20; jl` — x64 `0x15ae1`, x86 `0x12d9a` |
| `data` ptr | `+0x00` | `+0x00` | x64 `cmp qword[rbx],0`-shape; x86 `cmp dword[esi],0` @`0x12da1`, `mov edi,[esi*8+base]` @`0x13570` |
| `active` u8 | `+0x20` | `+0x1c` | x64 `cmp byte[rbx+0x20],dil` @`0x15ad5`; x86 `cmp byte[esi+0x1c],0` @`0x12d90`, `cmp byte[esi*8+0x102081b8],0` @`0x13561` (0x2081b8 = base+0x1c) |
| `shadeMode` u16 | `+0x24` | `+0x20` | x64 `mov dword[rbx+0x24],<0\|1\|2>` @`0x15afd`; x86 `mov dword[esi+0x20],eax` @`0x12db6` |
| `drawOffset` u16 | `+0x26` | `+0x22` | same dword store covers both u16s (M1 §2) |
| `sliceValue` u16 | `+0x28` | `+0x24` | x64 `Hi_SetEffModelSlice@0x18abb`; x86 `mov word[esi+0x24],ax` @`0x12db9` |

### 2.3 The shared `ModelData` block (identical struct, pointer-size-shifted)

| field | x64 | x86 | evidence |
|---|---|---|---|
| `motion` ptr (**0 ⇒ rigid**) | `+0x10` | `+0x0c` | x64 node builder branch `mov r14,[rcx+0x10]; test r14,r14; jne` @`0x7846`; x86 `mov edi,[edx+0xc]; test edi,edi; jne` @`0x70d5`/`0x70e3`; registrars null it — x64 `0x15b17`, x86 `mov dword[eax+0xc],0` @`0x12dcd` |
| `parent` DATA ptr | `+0x30` | `+0x1c` | x64 `mov rax,[rcx+0x30]` @`0x784f`; x86 `mov eax,[edx+0x1c]` @`0x70eb` |
| **`bones`** ptr (host) | `+0x38` | `+0x20` | x64 `mov qword[rcx+0x38],r8` @`0x7842`; x86 `mov dword[edx+0x20],esi` @`0x70e0`; consumer `mov ecx,[ecx+0x20]` @`0x135d5` |
| **`root`** MATRIX (anchor) | `+0x40` | `+0x24` | x64 `lea rbx,[rcx+0x40]` @`0x186b2`; x86 `lea esi,[edi+0x24]` @`0x14610`; ByBone writes 32 B there — x86 `movdqu [eax+0x24]` / `[eax+0x34]` @`0x135eb`/`0x135f5` |
| `scale` triple (**always 1.0 — do not log**) | `+0x78` | `+0x54` | x64 `0x7203`/`0x187b5`; x86 `mov dword[edi+0x54],0x10001000` @`0x69e1` — §0.5 |
| bones zeroed at register | `+0x38` | `+0x20` | x64 `mov qword[rcx+0x38],rbp(=0)` @`0x71f7`; x86 `mov dword[edi+0x20],0` @`0x69cc` — §0.6 |
| MATRIX stride / trans offsets | `0x20` / `+0x14,+0x18,+0x1c` | same | `shl rcx,5` @`0x16914`; x86 `shl eax,5` @`0x135db` |

---

## 3. THE PATCH — `SfxMeshProbe.cs`

Style-matched to the existing s47/s48/s52 code: capitalized BCL aliases, one bespoke `Load*()` per ini
key, `String.Format(CultureInfo.InvariantCulture, …)`, every entry point wrapped in try/catch, layered
guards, arch selection via `IntPtr.Size`, module base via the existing `PluginBase()`.

### 3.1 New ini flags — add to the flag block (after `CaptureRoot`, line ~77)

```csharp
        // s53 -- arms LogModels(): the per-frame identity + world transform of EVERY candidate native
        // model -- all 32 Eff-model slots AND the 1-slot summon array. Requires Enabled=1 as well (it is
        // called from inside the Enabled-gated block, and a MODEL row is only useful alongside the
        // VIEW/PROJ rows LogCamera writes for the same frame). Off by default -- a normal install never
        // does the native memory read. See LogModels().
        public static readonly Boolean CaptureModels = LoadCaptureModels();

        // s53 -- volume gate for LogModels(). 1 (default): emit a MODEL row only for slots whose active
        // flag is set, PLUS one edge row whenever a slot's active flag CHANGES -- so the census of which
        // slots ever existed, and exactly when, survives at ~zero cost. 0: emit all 33 slots every frame.
        public static readonly Boolean ModelsActiveOnly = LoadModelsActiveOnly();

        // s53 -- hard cap on MODEL/BONES rows for the process lifetime, same contract as PrimCap: the row
        // that crosses it writes ONE truncation marker and every row after is dropped, so a short log
        // always SAYS it is short. Default 120000 (a full 550-frame cast with all 33 slots active is
        // ~18000 rows, so the default is ~6x headroom).
        public static readonly Int32 ModelsRowCap = LoadModelsRowCap();

        // s53 -- OPTIONAL bone-cloud AABB for the SUMMON slot only (0 = off, the default). The plugin does
        // not expose the node count in directly-readable memory (it lives at u8[geom+0x02] behind a
        // PSX->host address decode), so the count is supplied here; for Bahamut/ef227 it is 93 (decoded
        // offline, M5 section 3). Emits ONE aggregate row per frame -- centroid + AABB, never per-bone
        // data (see the provenance note on LogModels()). Clamped to 128.
        public static readonly Int32 ModelsBoneCount = LoadModelsBoneCount();
```

### 3.2 New loaders — add beside `LoadCaptureRoot()` (line ~144)

```csharp
        private static Boolean LoadCaptureModels()
        {
            try
            {
                return IniFile.MemoriaIni.GetSetting("SfxProbe", "CaptureModels", "0").Trim() == "1";
            }
            catch
            {
                return false;
            }
        }

        private static Boolean LoadModelsActiveOnly()
        {
            try
            {
                return IniFile.MemoriaIni.GetSetting("SfxProbe", "ModelsActiveOnly", "1").Trim() != "0";
            }
            catch
            {
                return true;
            }
        }

        private static Int32 LoadModelsRowCap()
        {
            try
            {
                String raw = IniFile.MemoriaIni.GetSetting("SfxProbe", "ModelsCap", "120000").Trim();
                Int32 cap;
                if (Int32.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out cap) && cap > 0)
                    return cap;
                return 120000;
            }
            catch
            {
                return 120000;
            }
        }

        private static Int32 LoadModelsBoneCount()
        {
            try
            {
                String raw = IniFile.MemoriaIni.GetSetting("SfxProbe", "ModelsBoneCount", "0").Trim();
                Int32 n;
                if (Int32.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out n) && n > 0)
                    return n > 128 ? 128 : n;
                return 0;
            }
            catch
            {
                return 0;
            }
        }
```

### 3.3 New banner lines — add inside `Writer`'s init block (after the ROOT line, line ~163)

```csharp
                        _writer.WriteLine("# MODEL,effectId,frame,kind,slot,active,hasMotion,hasParent,aux0,aux1,aux2,ax,ay,az,wx,wy,wz,m00,m01,m02,m10,m11,m12,m20,m21,m22,bones32");
                        _writer.WriteLine("#   kind S = the summon slot (aux0 = motion frame counter, aux1/aux2 = 0); kind E = an eff slot (aux0 = shadeMode, aux1 = drawOffset, aux2 = sliceValue)");
                        _writer.WriteLine("#   ax,ay,az = the DRAW ANCHOR translation; wx,wy,wz + m00..m22 = the COMPOSED world matrix actually fed to the GTE; bones32 = low 32 bits of the node-matrix pointer (0 = this model has never been drawn)");
                        _writer.WriteLine("# BONES,effectId,frame,n,cx,cy,cz,minX,minY,minZ,maxX,maxY,maxZ  (summon node-translation AABB + centroid; aggregate only)");
```

### 3.4 The body — add after `LogSummonRoot()` (line ~366)

```csharp
        // s53 -- THE MODEL CENSUS + THE TRUE PER-FRAME TRANSFORM. Requires [SfxProbe] Enabled=1 AND
        // CaptureModels=1 (both default 0). One row per candidate native model per frame:
        //
        //   kind 'S' -- the SUMMON model array (RVA x64 0x220830 / x86 0x20869c). LENGTH 1: this is the
        //               summoned creature itself. It is the ONLY model in the plugin that can carry a
        //               motion clip, hence the only one that can be an animated creature.
        //   kind 'E' -- the 32-slot EFF-MODEL array (RVA x64 0x220230 / x86 0x20819c, stride 0x30/0x28).
        //               Structurally RIGID: all five Hi_Register*EffModel bodies store DATA+motion = 0
        //               (x64 0x15b17/0x15bcb/0x15caf/0x15d9d/0x15e7c; x86 0x12dcd) and the DLL exposes no
        //               Hi_Set*EffModelMotion at all. These are the beams/rings/sparks/props, frequently
        //               HARD-PARENTED to one of the creature's bones by Hi_DrawEffModelByBone
        //               (x64 0x168ea-0x16928 / x86 0x135b5-0x135f5), which copies a summon BONE's world
        //               matrix straight into the eff model's own root.
        //
        // WHY BOTH: the round's motivating hypothesis was that the visible creature might be drawn through
        // the eff array rather than the single summon slot. Static analysis refuted that
        // (disasm/M1-effmodel-array.md section 7, disasm/M5-motion-payload.md section 7). These rows turn
        // the refutation into an EMPIRICAL one that a single cast can check: the prediction is that
        // hasMotion == 1 on exactly one row kind in the whole log, and that kind is 'S'. A kind 'E' row
        // with hasMotion == 1 would falsify the static reading and re-open the subsystem question.
        //
        // THE TWO TRANSFORMS (this is the s52 correction). ax,ay,az is the DRAW ANCHOR -- the (rot,pos,
        // scale) the effect's own command stream handed Hi_DrawSummonModel this frame, written by
        // pose_eval (x64 0x186a0 / x86 0x14600) into DATA+0x40 (x86 +0x24). That is what the s52 ROOT row
        // logs, and it is only HALF the transform. wx,wy,wz + m00..m22 is the COMPOSED matrix the plugin
        // actually feeds the GTE: node 0 of the array at *(DATA+0x38) (x86 +0x20), rebuilt every Draw by
        // the node builder (x64 0x7820 / x86 0x70c0) as  bone0.R = R_root * clipRotation[0](frame)  and
        // bone0.t = R_root * clipRootTranslation(frame) + T_root  (x64 0x7edc-0x80a6).
        //
        // TWO THINGS THAT WILL OTHERWISE COST A PLAYTEST:
        //  * The composed translation is a REFINEMENT, not a rescue. Bahamut's clip root-translation track
        //    spans 7-246 units per axis and the authored scale caps at 3.0x, so |composed - anchor| is
        //    bounded near ~740 units. It cannot explain a 40,000-unit staging point -- and it does not need
        //    to: that figure is the authored fly-by, and the long constant stretch late in the cast is the
        //    creature genuinely hovering while the camera moves onto it.
        //  * The authored SCALE is folded into the anchor's 3x3 in place by ScaleMatrix (0x3b60, called at
        //    0x187ab with rcx == r8 == DATA+0x40) and is NOT stored at DATA+0x78 -- that field is written
        //    to 1.0 at register time (0x7203) and re-written to 1.0 only in pose_eval's scale == NULL
        //    branch (0x187b5), and is read by exactly one function (0x5575). It is always 1.0 and carries
        //    no information. Recover the scale OFFLINE as the column norms of the logged 3x3; the composed
        //    matrix inherits it, because the compose loads DATA+0x40 (incl. S) into the GTE at 0x7edc.
        //
        // SAFETY: model_prepare (x64 0x7120 : 0x71f7 / x86 0x6980 : 0x69cc) explicitly zeroes the bones
        // pointer at register time, so bones == 0 is a GUARANTEED "never drawn" signal -- the probe can
        // never read arena garbage for a never-drawn slot. A slot that WAS drawn earlier but is not drawn
        // this frame keeps its last-drawn values (the node arena is per-frame and linear); such a slot is
        // simply frozen in the log, which for the identification question is indistinguishable from
        // "parked" and equally means "not the creature".
        //
        // PROVENANCE: transforms + ids + flags = STAGING/CHOREOGRAPHY, the same class as the camera track
        // this file already logs and the mesh-bounds row it has logged since s47. This method reads NO
        // geometry (no vertices, triangles, UVs or textures -- the geometry pointer at DATA+0x08 is a PSX
        // address it never even decodes), and it emits NO per-bone matrices: the only bone data that can
        // leave here is the single aggregate BONES row (a centroid + AABB, an irreversible 93x3 -> 6
        // reduction, identical in kind to the MESH row's own center+extents). There is deliberately no
        // code path in this class that can write a per-bone matrix. It patches no DLL and calls no plugin
        // export; it only reads state the plugin itself just computed.
        //
        //   MODEL,<effectId>,<frame>,<kind>,<slot>,<active>,<hasMotion>,<hasParent>,<aux0>,<aux1>,<aux2>,
        //         <ax>,<ay>,<az>,<wx>,<wy>,<wz>,<m00..m22>,<bones32>
        //   BONES,<effectId>,<frame>,<n>,<cx>,<cy>,<cz>,<minX>,<minY>,<minZ>,<maxX>,<maxY>,<maxZ>

        private static readonly Boolean Arch64 = (IntPtr.Size == 8);

        // The summon-model array -- LENGTH 1. x64 Hi_RegisterSummonModel@0x15f01 / x86 0x135b8.
        private static readonly Int64 SummonRecRva = Arch64 ? 0x220830L : 0x20869cL;
        private static readonly Int32 SummonActiveOff = Arch64 ? 0x50 : 0x4c;   // x64 0x168f5 / x86 0x135be
        private static readonly Int32 SummonMotFrameOff = Arch64 ? 0x54 : 0x50; // x64 0x17888 / x86 0x13e33

        // The eff-model array -- 32 slots. x64 0x15acc / x86 0x12d84.
        private static readonly Int64 EffArrRva = Arch64 ? 0x220230L : 0x20819cL;
        private static readonly Int32 EffStride = Arch64 ? 0x30 : 0x28;         // x64 0x15add / x86 0x12d97
        private static readonly Int32 EffActiveOff = Arch64 ? 0x20 : 0x1c;      // x64 0x15ad5 / x86 0x12d90
        private static readonly Int32 EffShadeOff = Arch64 ? 0x24 : 0x20;       // x64 0x15afd / x86 0x12db6
        private static readonly Int32 EffDrawOffOff = Arch64 ? 0x26 : 0x22;     // same dword store
        private static readonly Int32 EffSliceOff = Arch64 ? 0x28 : 0x24;       // x64 0x18abb / x86 0x12db9
        private const Int32 EffSlotCount = 32;                                  // cmp eax,0x20 -- x64 0x15ae1 / x86 0x12d9a

        // The shared ModelData block (same struct on both arches, pointer-size-shifted).
        private static readonly Int32 DataMotionOff = Arch64 ? 0x10 : 0x0c;     // x64 0x7846 / x86 0x70d5
        private static readonly Int32 DataParentOff = Arch64 ? 0x30 : 0x1c;     // x64 0x784f / x86 0x70eb
        private static readonly Int32 DataBonesOff = Arch64 ? 0x38 : 0x20;      // x64 0x7842 / x86 0x70e0
        private static readonly Int32 DataRootOff = Arch64 ? 0x40 : 0x24;       // x64 0x186b2 / x86 0x14610

        // A PSX MATRIX is 32 bytes on BOTH arches: 3x3 s16 fp12 at +0x00..+0x11, s32 translation at +0x14.
        private const Int32 MatrixStride = 0x20;
        private const Int32 MatrixTransOff = 0x14;

        private static Int32 _modelRowCount;
        private static Boolean _modelCapWarned;
        private static Byte _lastSummonActive = 0xFF;
        private static readonly Byte[] _lastEffActive = new Byte[EffSlotCount];
        private static Boolean _effActiveSeeded;

        public static void LogModels()
        {
            if (!Enabled || !CaptureModels)
                return;
            StreamWriter w = Writer;
            if (w == null)
                return;
            try
            {
                IntPtr baseAddr = PluginBase();
                if (baseAddr == IntPtr.Zero)
                    return;
                if (_modelRowCount >= ModelsRowCap)
                {
                    if (!_modelCapWarned)
                    {
                        _modelCapWarned = true;
                        w.WriteLine("# MODEL CAPTURE TRUNCATED at " + ModelsRowCap.ToString(CultureInfo.InvariantCulture) +
                            " rows (raise [SfxProbe] ModelsCap=<N>, or leave ModelsActiveOnly=1 for the bounded mode)");
                        w.Flush();
                    }
                    return;
                }
                if (!_effActiveSeeded)
                {
                    _effActiveSeeded = true;
                    for (Int32 i = 0; i < EffSlotCount; i++)
                        _lastEffActive[i] = 0xFF; // force one edge row per slot on the first tick
                }
                Int32 frame = SFX.frameIndex;
                Int32 effectId = (Int32)SFX.currentEffectID;
                Int64 modBase = baseAddr.ToInt64();
                Boolean wrote = false;

                // ---- the SUMMON slot (length 1) -- the creature ----
                IntPtr rec = new IntPtr(modBase + SummonRecRva);
                Byte sActive = Marshal.ReadByte(rec, SummonActiveOff);
                if (!ModelsActiveOnly || sActive != 0 || sActive != _lastSummonActive)
                {
                    IntPtr sData = (sActive == 0) ? IntPtr.Zero : Marshal.ReadIntPtr(rec);
                    Int32 motFrame = (UInt16)Marshal.ReadInt16(rec, SummonMotFrameOff);
                    WriteModelRow(w, effectId, frame, 'S', 0, sActive, sData, motFrame, 0, 0);
                    if (sData != IntPtr.Zero && ModelsBoneCount > 0)
                        WriteBoneAabb(w, effectId, frame, sData);
                    wrote = true;
                }
                _lastSummonActive = sActive;

                // ---- the 32 EFF slots -- the props ----
                for (Int32 i = 0; i < EffSlotCount; i++)
                {
                    IntPtr slot = new IntPtr(modBase + EffArrRva + (Int64)i * EffStride);
                    Byte eActive = Marshal.ReadByte(slot, EffActiveOff);
                    Boolean edge = (eActive != _lastEffActive[i]);
                    _lastEffActive[i] = eActive;
                    if (ModelsActiveOnly && eActive == 0 && !edge)
                        continue;
                    IntPtr eData = Marshal.ReadIntPtr(slot);           // may be NULL: slots >= the effect's
                    if (eActive == 0)                                  // declared pool count keep data == 0
                        eData = IntPtr.Zero;                           // (Hi_InitEffModel, x64 0x15940)
                    Int32 shade = (UInt16)Marshal.ReadInt16(slot, EffShadeOff);
                    Int32 drawOff = (UInt16)Marshal.ReadInt16(slot, EffDrawOffOff);
                    Int32 slice = (UInt16)Marshal.ReadInt16(slot, EffSliceOff);
                    WriteModelRow(w, effectId, frame, 'E', i, eActive, eData, shade, drawOff, slice);
                    wrote = true;
                }
                if (wrote)
                    w.Flush();
            }
            catch
            {
                // A probe must never take the real battle render down with it -- least of all one doing
                // raw native memory reads. Any bad read/state just skips this frame's MODEL rows.
            }
        }

        // ONE row. Reads only: the two pointer FLAGS (motion/parent, as booleans -- never the pointees),
        // the anchor translation, and node 0 of the composed matrix array. No geometry, no bone loop.
        private static void WriteModelRow(StreamWriter w, Int32 effectId, Int32 frame, Char kind, Int32 slot,
            Byte active, IntPtr data, Int32 aux0, Int32 aux1, Int32 aux2)
        {
            Int32 hasMotion = 0, hasParent = 0;
            Int32 ax = 0, ay = 0, az = 0;
            Int32 wx = 0, wy = 0, wz = 0;
            Int32 m00 = 0, m01 = 0, m02 = 0, m10 = 0, m11 = 0, m12 = 0, m20 = 0, m21 = 0, m22 = 0;
            UInt32 bones32 = 0u;
            if (data != IntPtr.Zero)
            {
                hasMotion = (Marshal.ReadIntPtr(data, DataMotionOff) != IntPtr.Zero) ? 1 : 0;
                hasParent = (Marshal.ReadIntPtr(data, DataParentOff) != IntPtr.Zero) ? 1 : 0;
                IntPtr anchor = new IntPtr(data.ToInt64() + DataRootOff);
                ax = Marshal.ReadInt32(anchor, MatrixTransOff);
                ay = Marshal.ReadInt32(anchor, MatrixTransOff + 4);
                az = Marshal.ReadInt32(anchor, MatrixTransOff + 8);
                // bones == 0 is GUARANTEED for a model that has never been drawn (model_prepare zeroes it
                // at register time, x64 0x71f7 / x86 0x69cc) -- so this is never a garbage read.
                IntPtr bones = Marshal.ReadIntPtr(data, DataBonesOff);
                if (bones != IntPtr.Zero)
                {
                    bones32 = (UInt32)(bones.ToInt64() & 0xFFFFFFFFL);
                    m00 = Marshal.ReadInt16(bones, 0);
                    m01 = Marshal.ReadInt16(bones, 2);
                    m02 = Marshal.ReadInt16(bones, 4);
                    m10 = Marshal.ReadInt16(bones, 6);
                    m11 = Marshal.ReadInt16(bones, 8);
                    m12 = Marshal.ReadInt16(bones, 10);
                    m20 = Marshal.ReadInt16(bones, 12);
                    m21 = Marshal.ReadInt16(bones, 14);
                    m22 = Marshal.ReadInt16(bones, 16);
                    wx = Marshal.ReadInt32(bones, MatrixTransOff);
                    wy = Marshal.ReadInt32(bones, MatrixTransOff + 4);
                    wz = Marshal.ReadInt32(bones, MatrixTransOff + 8);
                }
            }
            w.WriteLine(String.Format(CultureInfo.InvariantCulture,
                "MODEL,{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25:X8}",
                effectId, frame, kind, slot, active, hasMotion, hasParent, aux0, aux1, aux2,
                ax, ay, az, wx, wy, wz,
                m00, m01, m02, m10, m11, m12, m20, m21, m22, bones32));
            _modelRowCount++;
        }

        // The OPTIONAL framing datum: one AGGREGATE row per frame over the summon model's node-translation
        // cloud -- centroid + axis-aligned bounds, nothing else. This is the thing FLIGHT has never had:
        // node 0 is the root of a long-necked 93-bone skeleton and is NOT the silhouette centre, so a
        // reprojection or a puppet sized on node 0 alone is systematically wrong.
        //
        // The node COUNT is an ini parameter, not a runtime read, on purpose: the count lives at
        // u8[geom+0x02] behind a PSX->host address decode of DATA+0x08 (x64 0x7120 : 0x7130-0x71d4), and
        // replicating that decode from managed code would mean pointing this probe at the geometry blob --
        // exactly the thing it must not touch. For ef227 (Bahamut__Full) the count is 93, decoded OFFLINE
        // from the container (M5 section 3). An over-large count reads adjacent arena bytes; that shows up
        // offline as an absurd AABB, which is the intended self-check. Clamped to 128 by the loader.
        //
        // PROVENANCE: 93x3 numbers in, 6 out, every frame -- an irreversible reduction, the same class of
        // datum as the mesh-bounds center+extents this file has logged since s47. Per-bone matrices are
        // NEVER emitted and no code path here can emit them; dumping them across a cast would reconstruct
        // the stock skeletal animation, which is out of bounds.
        private static void WriteBoneAabb(StreamWriter w, Int32 effectId, Int32 frame, IntPtr data)
        {
            Int32 n = ModelsBoneCount;
            if (n <= 0)
                return;
            IntPtr bones = Marshal.ReadIntPtr(data, DataBonesOff);
            if (bones == IntPtr.Zero)
                return;
            Int64 bb = bones.ToInt64();
            Int64 sx = 0L, sy = 0L, sz = 0L;
            Int32 minX = Int32.MaxValue, minY = Int32.MaxValue, minZ = Int32.MaxValue;
            Int32 maxX = Int32.MinValue, maxY = Int32.MinValue, maxZ = Int32.MinValue;
            for (Int32 k = 0; k < n; k++)
            {
                IntPtr m = new IntPtr(bb + (Int64)k * MatrixStride);
                Int32 x = Marshal.ReadInt32(m, MatrixTransOff);
                Int32 y = Marshal.ReadInt32(m, MatrixTransOff + 4);
                Int32 z = Marshal.ReadInt32(m, MatrixTransOff + 8);
                sx += x; sy += y; sz += z;
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
                if (z < minZ) minZ = z;
                if (z > maxZ) maxZ = z;
            }
            w.WriteLine(String.Format(CultureInfo.InvariantCulture,
                "BONES,{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11}",
                effectId, frame, n, sx / n, sy / n, sz / n, minX, minY, minZ, maxX, maxY, maxZ));
            _modelRowCount++;
        }
```

### 3.5 The hook — `SFXDataMesh.cs`, `Runtime.Render()`, immediately after line 653

```csharp
                SfxMeshProbe.LogSummonRoot();
                // s53 -- the full per-frame model census: all 32 eff slots + the summon slot, each with
                // its identity flags and its COMPOSED world matrix (the s52 ROOT row logs only the draw
                // anchor). Read here, after this frame's native Draw has run, so every row shares this
                // SFX.frameIndex with the VIEW/PROJ rows above -- the offline reprojection joins on frame.
                // Self-gated on [SfxProbe] CaptureModels=1 (off by default); no-op on non-summon casts.
                SfxMeshProbe.LogModels();
```

That is the **only** call-site edit. `using System.Runtime.InteropServices;` and the `GetModuleHandle`
P/Invoke already exist in the file (s52).

### 3.6 Arming block for `Memoria.ini`

```ini
[SfxProbe]
Enabled = 1
CaptureRoot = 1          ; keep: the ROOT row is the anchor half, and existing offline tooling parses it
CaptureModels = 1        ; NEW -- the s53 census + composed transform
ModelsActiveOnly = 1     ; NEW -- active slots + activation edges only (default)
ModelsCap = 120000       ; NEW
ModelsBoneCount = 93     ; NEW -- 93 = Bahamut/ef227's node count (M5 section 3); 0 disables the BONES row
```

---

## 4. THE IDENTIFICATION PROTOCOL

One cast + this log settles it. Each step is a **prediction that can fail**; failures are informative
and are listed with what they would mean.

### 4.1 Step 0 — establish the phase segmentation from the log itself, not from the video

Do not try to frame-match a video. The cast segments itself. Take the `kind=S` rows and compute per
frame `s = mean(column norms of m00..m22) / 4096` (the authored scale) and the translation. M5 §8 did
exactly this on the existing ROOT capture and recovered the user's four phases:

| frames (existing 227 capture) | scale | reading |
|---|---|---|
| 50–81 | matrix all-zero | registered, **not yet drawn** |
| 82–115 | 1.50 | **phase 1 — flying down** (`Y −4096 → +4092`) |
| 116–152 | 1.48 → 0.02 → 2.10 | recede / re-enter / rush in |
| 153–177 | 3.00 | **phase 2 — the fly-by** (`Z +23808 → −49152`, 25 frames) |
| 178–300 | 1.00 | settle |
| 301–561 | 1.50 | **phases 3+4 — hovers, charges; the camera does the work** (translation constant) |

Re-derive it on the new capture from `kind=S`. The phase table is the ruler everything else is measured
against.

### 4.2 Step 1 — the subsystem test (decisive, needs no projection)

**Prediction:** `hasMotion == 1` on `kind=S` rows only; **all** `kind=E` rows have `hasMotion == 0`.

* Confirms M1 §7 / M5 §7 empirically: an eff model structurally cannot be an animated creature, so the
  visible dragon is the summon slot.
* **If any `kind=E` row shows `hasMotion == 1`** the static reading is wrong — five registrar bodies
  and a missing symbol all disagree — and the subsystem question re-opens. Treat that as a stop-work
  finding, not a nuance.

### 4.3 Step 2 — the drawn test

**Prediction:** `kind=S` has `bones32 != 0` from the first drawn frame onward (≈ frame 82 on the
existing capture, where the anchor transitions all-zero → non-zero), and every frame after.

`bones32 == 0` is a guaranteed never-drawn signal (§0.6). A summon slot that is `active==1` but has
`bones32 == 0` for the whole cast would mean `Hi_DrawSummonModel` never ran — which the existing log
already refutes, since only `pose_eval` called from `Hi_DrawSummonModel` can write the anchor.

### 4.4 Step 3 — the composition self-check (validates the NEW read)

**Prediction:** for `kind=S`, `|(wx,wy,wz) − (ax,ay,az)| ≤ ~1000 units` on every frame.

Derivation: `bone0.t = R_root·clipRootT(frame) + T_root` (M5 §5), `|clipRootT| ≤ 246` per axis across
all eight Bahamut clips (`m5_roottrans.py`), `|R_root| ≤ 3.0` (the scale sweep). So the correction is
bounded near 740.

* If the bound holds — the new read is correct **and** it confirms §0.2: the composed matrix is a
  refinement, not the missing 40,000 units. Do not sell it as the flight fix.
* If `|w − a|` is huge or erratic — the bones pointer is being read at the wrong offset for this arch,
  or the arena was recycled before the read. Check `bones32` for constancy across frames first.

### 4.5 Step 4 — the reprojection (the real identity test)

For each frame, join `MODEL` to that frame's `VIEW` and `PROJ` rows and project every candidate.

**The world-space convention is derivable, so do not brute-force it.** `PsxCamera.PsxMatrix2UnityMatrix
(Single[], Single)` (`Global/PSX/PsxCamera.cs:103-120`) builds `worldToCameraMatrix` from the plugin's
13 floats with the sign pattern

```
 +  -  +        m03 =  pmat[9]
 -  +  -        m13 = -pmat[10]
 -  +  -        m23 = -(pmat[11] + zoffset)
```

which factors as `R_unity = A · R_psx · B` with `A = diag(1,−1,−1)` and `B = diag(1,−1,1)`, and
`t_unity = A · t_psx`. Since the view matrix consumes a *world* point, the plugin-space point must be
pre-mapped by `B`:

> **`p_unity = (wx, −wy, wz)`** — X and Z keep their sign, Y flips.

Then `clip = PROJ · VIEW · [p_unity, 1]`, `ndc = clip.xy / clip.w`, `screen = ((ndc.x+1)/2·W,
(1−ndc.y)/2·H)`.

**Units are already compatible — no scale factor.** Measured on the existing capture: `VIEW`
translation spans `x ∈ [−10623, 12088]`, `y ∈ [−25792, 2060]`, `z ∈ [−20545, 21101]`; `ROOT`
translation spans `x ∈ [−1224, 2048]`, `y ∈ [−23567, 16384]`, `z ∈ [−49152, 23808]`. Same order of
magnitude, same space. (M5 Finding D already excluded a pure sign error — it tried all eight sign
conventions and got `|r| ≤ 0.24` — so a failure here is **not** a convention problem; go to §4.6.)

**Prediction:** the `kind=S` projected point is inside the viewport for ≈ 35–45 % of drawn frames
(the user's "~40 % of the cast has the creature framed"), specifically during phases 1–3, and leaves
the frame during phase 4 as the camera follows the fire column.

**Prediction:** no `kind=E` slot's projected point tracks the creature *independently* — an eff slot
that appears to track it should be explained by §4.7 (it is parented to a creature bone), not by being
the creature.

### 4.6 Step 5 — if the reprojection still fails, the fault is the TARGET, not the source

M5 Finding D's three candidate causes, now with scale and composition removed as suspects:

1. **The comparison target.** `MESH cx,cy` is a post-batch centroid of one blend key, selected by row
   count rather than identity. Use the `PRIM` stream instead, filtered to the creature's mesh keys
   from the `--calibrate` cast's `HideMeshes` split (PROBE.md §2), and compare against the **`BONES`
   AABB projected corner hull**, not a single point.
2. **The datum.** Node 0 is the skeleton root, not the silhouette centre. This is exactly what the
   `BONES` row exists to fix: project the AABB's 8 corners and compare hulls.
3. **Depth ordering / `otz`.** The `PRIM` rows carry `otz`; a creature primitive and a background
   primitive at the same screen point are separable by depth.

### 4.7 Step 6 — the eff-slot census (the round's bonus, and the Thomas-swap's real lane)

From the same log, offline:

* **How many eff slots does a stock Eidolon use, and when.** The activation edges give the timeline.
* **Which shade modes** (`aux0`: 0 = Solid, 1 = Gouraud, 2 = Textured) and which use `drawOffset`
  (`aux1`, overrides the mode switch) or `sliceValue` (`aux2`, the dissolve/materialise plane).
* **Which are bone-parented.** `Hi_DrawEffModelByBone` copies a summon **bone's world matrix verbatim**
  into the eff model's own root (`0x1691b`–`0x16928`). So a `kind=E` row whose `ax,ay,az` moves in
  lockstep with the creature — while the slot is a rigid model with `hasMotion == 0` — is a
  bone-parented prop, and its anchor **is** a creature bone's world position. That is (a) a second,
  independent creature-position readout to cross-check the summon slot against, and (b) the exact
  mechanism a Thomas-swap prop should use, since it needs zero new machinery.

### 4.8 What would make this round's conclusion wrong

* Any `kind=E` row with `hasMotion == 1` (§4.2).
* `kind=S` `active == 0` for the whole cast, or `bones32 == 0` for the whole cast (§4.3) — would mean
  the creature is drawn by a third path this study has not found.
* `|w − a|` grossly exceeding the ~1000-unit bound with a stable `bones32` (§4.4) — would mean the
  composition law (M5 §5) is misread.

---

## 5. VOLUME CONTROL

| control | default | effect |
|---|---|---|
| `CaptureModels` | `0` | the whole feature is off; zero syscalls, zero reads, zero rows |
| `ModelsActiveOnly` | `1` | emit a row only for `active != 0`, **plus one edge row whenever a slot's active flag changes**, so the "which slots ever existed and when" census survives at ~zero cost |
| `ModelsCap` | `120000` | hard lifetime cap on MODEL+BONES rows; the crossing row writes one `# MODEL CAPTURE TRUNCATED` marker and everything after is dropped — a short log always **says** it is short (the s48 `PrimCap` contract, verbatim) |
| `ModelsBoneCount` | `0` | the `BONES` aggregate row is OFF unless a node count is supplied; clamped to 128 |

**Worst case arithmetic.** 33 rows/frame × 551 frames = **18,183 rows** ≈ 2.7 MB — i.e. the *unbounded*
mode is already smaller than the existing 2.76 MB log and ~35× under the cap. With `ModelsActiveOnly=1`
it is far less (a stock Eidolon is not expected to hold 32 props live). `BONES` adds at most one row per
frame. Per-frame cost: 1 + 32 slot reads of 1 byte each, then ~15 small reads per *emitted* row; one
`Flush()` per frame, matching `LogFrame`'s shape rather than the per-row flush `LogPrim` uses.

**Deliberately NOT added:** a frame-decimation knob. The whole point is a per-frame trajectory; a
decimated one cannot be differentiated or reprojected against per-frame camera rows.

---

## 6. PROVENANCE — where the line is, and why this patch is on the right side

**Sanctioned (this patch):**
* Model **identity + flags**: slot index, active byte, shade mode, draw offset, slice value, and two
  pointer *booleans* (`hasMotion`, `hasParent`). These are engine state, not content.
* Model **world transforms**: the draw anchor translation and node 0's composed matrix. This is
  staging/choreography — the identical class as the camera track this file has logged since s48 and the
  root transform it has logged since s52.
* The **`BONES` aggregate**: centroid + AABB over the node-translation cloud. An irreversible 93×3 → 6
  reduction per frame, the same class as the `MESH` row's `cx,cy,cz,ex,ey,ez` logged since s47.

**Out of bounds, and structurally impossible in this code:**
* Per-bone matrices across a cast — that reconstructs the stock skeletal animation. **There is no code
  path in the patch that emits per-bone data**; `WriteBoneAabb` accumulates min/max/sum inside its loop
  and writes only after it. That is the enforcement, not a comment.
* Geometry. The patch never decodes `DATA+0x08` (the PSX geometry address) and never reads a vertex,
  triangle, UV, or texel. The node count is an ini parameter *precisely so that* the probe never has to
  point itself at the geometry blob.
* Motion-clip payload bytes. Not read.

**Also unchanged:** no DLL is patched, no plugin export is called. Every read is of state the plugin
itself computed microseconds earlier, exactly as an external debugger would observe it. Any extracted
`ef###.bytes` used for the offline node-count stays under `C:/gd/SCRATCH/summon-format/`.

---

## 7. Cite index

**x64 DLL.** summon array `0x220830` (`0x15f01`, `0x168ea`); active `+0x50` (`0x168f5`); motion frame
`+0x54` (`0x17888`). EFFARR `0x220230` (`0x15acc`); stride `0x30` (`0x15add`); count 32 (`0x15ae1`);
active `+0x20` (`0x15ad5`); shade `+0x24` (`0x15afd`); slice `+0x28` (`0x18abb`).
`ModelData`: motion `+0x10` (`0x7846`), parent `+0x30` (`0x784f`), bones `+0x38` (`0x7842`), root
`+0x40` (`0x186b2`), scale-that-is-always-1.0 `+0x78` (`0x7203`, `0x187b5`, read `0x5575`).
`pose_eval@0x186a0` (identity seed `0x186ca`-`0x186dc`; rot chain `0x186f6`/`0x18703`/`0x18729`;
translation copy `0x18738`-`0x18749`; scale branch `0x18761`, local build `0x18763`-`0x187a6`,
`ScaleMatrix 0x3b60` in place `0x18797`/`0x1879a`/`0x187ab`).
`model_prepare@0x7120` (PSX→host decode `0x7130`-`0x71d4`; bones zeroed `0x71f7`; scale 1.0 `0x7203`).
node builder `0x7820` (bones store `0x7842`; branch `0x7846`/`0x784f`/`0x7856`; rigid `0x797a`-`0x7a0f`;
root compose `0x7edc`-`0x80a6`). `DrawSummonModel@0x17740` (arena decode `0x13df1`-analogue; pose call
`0x1786e`; arena commit `0x17873`-`0x17885`; advance `0x17888`).
`Hi_DrawEffModelByBone@0x167f0` body `0x16837` (summon array `0x168ea`, bone copy `0x1691b`-`0x16928`).

**x86 DLL (independent re-derivation, this slice).** summon array `0x20869c` stride `0x54` active
`+0x4c` (`0x135b5`-`0x135be`); motion frame `rec+0x50` (`0x13dd8`, `0x13ded`, `0x13e33`).
EFFARR `0x20819c` stride `0x28` count 32 active `+0x1c` shade `+0x20` slice `+0x24` handle `+0x1e`
(`0x12d84`-`0x12ddb`, `0x13561`-`0x13570`).
`ModelData`: motion `+0x0c` (`0x70d5`, `0x12dcd`), parent `+0x1c` (`0x70eb`), bones `+0x20` (`0x70e0`,
`0x135d5`, zeroed `0x69cc`), root `+0x24` (`0x14610`, `0x135eb`/`0x135f5`), scale `+0x54` = 1.0
(`0x69e1`). MATRIX stride `0x20` (`0x135db`). meshCount `byte[geom+3]` via `DATA+0x08` (`0x13e40`-
`0x13e4a`).

**C#.** `Memoria/Battle/SFX/SfxMeshProbe.cs` (the s47/s48/s52 file this patches);
`Memoria/Battle/SFX/SFXDataMesh.cs:641-654` (the `Runtime.Render()` hook block);
`Global/PSX/PsxCamera.cs:103-120` (`PsxMatrix2UnityMatrix` — the world-space sign convention of §4.5);
`Global/SFX/SFX.cs:1590-1604` (`UpdateCamera`, which installs `worldToCameraMatrix`/`projectionMatrix`);
`Memoria/Data/Battle/SpecialEffect.cs:99` (`Bahamut__Full = 227`).

**Runtime figures** are aggregate statistics over our own `sfxmeshprobe.log` (2.76 MB, effect 227,
551 camera frames / 512 root frames), read by sampling — never in full, never echoed as payload.
