# M4 — THE MESH / GEOMETRY PAYLOAD FORMAT (the container `Hi_Register*Model` parses)

Slice M4 of the FF9SpecialEffectPlugin.dll round. The prior round called this piece **"decoded
nowhere."** It is now **decoded end-to-end and validated byte-for-byte against 1005 real geometry
blocks across 372 stock `ef###.bytes` files**, including **Bahamut's own creature model**
(`ef227` @ file offset `0x63000`: **93 bones, 2 meshes, 1439 vertices, 2416 primitives**).

RVAs are image-relative (x64, `ImageBase 0x180000000`; VA = RVA + base). C# cites are relative to
`C:/gd/FFIX/Memoria/Assembly-CSharp/`. Data validation used the already-extracted stock blobs under
`C:/gd/SCRATCH/summon-format/` — **no stock bytes were written into the repo** (§10).

---

## 0. HEADLINE

There is **exactly ONE geometry container** in the plugin, shared by the summon-model family and the
whole Eff-model family. It is a **PS1-native, indexed-pool, rigid-per-bone-skinned model** whose
primitives are **bucketed by the eight PSX `POLY_*` types**. It is *not* TMD, *not* HMD, *not* PMD
(§8) — it is FF9's own, and it is the **last surviving raw-PSX geometry format in the shipped game**
(every other model in the Unity port was converted to Unity meshes; the SFX plugin still renders the
original PS1 data through a software GTE).

Concretely (all offsets proven twice — once from the disassembly, once from stock bytes):

```
GEOM block                      ; the thing SummonData+0x08 / EffData+0x08 points at
 +0x00 u8   flags               ; bit0 = "already relocated" (0 on disk, set at load)
 +0x02 u8   boneCount
 +0x03 u8   meshCount
 +0x0c u32  ->  +0x14           ; pointer slot; the BONE-LINK TABLE begins at +0x18
 +0x10 u32  ->  MESH TABLE      ; == 0x18 + (boneCount-1)*4  (verified on 1005/1005 blocks)
 +0x18      BoneLink[boneCount-1]        ; {u16 len; u8 0; u8 parentBone}
 +0x10 tgt  MeshDesc[meshCount]          ; stride 0x28
            then, per mesh, contiguous: vertsPerBone[] -> positions[] -> primitives[] -> uv[] -> colors[]
```

Everything a re-importer needs — vertex format, face records, per-part texture binding, skeleton
attachment, the exact output protocol — is below. What is still opaque is a short, named list (§7).

---

## 1. HOW THE POINTER GETS THERE (following the data, as asked)

**The `.seq` op → model header → geometry block chain**, all cited:

1. The mega-interpreter's `RegisterSummonModel` case (`@0xf74a-0xf75a`) resolves **operand 0** into
   `rcx` (`0x12740(interp, 0)` → `dword[cmd+0xca8]` → `0x10e0` resolve) and **operand 1** into `rdx`.
   `Hi_RegisterSummonModel(rcx = MODEL HEADER, rdx = per-part texture-window table)`.
2. `Hi_RegisterSummonModel @0x15ee0` copies the header's tables into the record and hands
   `DATA+0x08 = model->geomHandle` to the shared init:
   - `0x15f32/0x15f3f` : `eax = dword[model+0x3c]` → `DATA+0x08` — **the GEOMETRY handle.**
     (A2 called this `modelId`; that is **corrected** — B3 read it right: it is the geometry-table handle.)
   - `0x15f42..0x15fc6` : `dword[model+0x180]` decoded → `DATA+0x10` — the **default motion** clip.
   - `0x1607d..0x160f5` : `dword[model+0x40]` decoded → `DATA+0x70` — the **texanim** table.
   - `0x15fd0..0x16067` : the per-part loop, bound `word[model+4]` (§2).
   - `0x1606c/0x16078` : `call 0x7120(DATA, rec+0x08, stackTable)` — the shared parse.
3. `Hi_RegisterSolidEffModel @0x15ac0` (and `Gou/Tex/TexList/TexPtr` @0x15b70/0x15c20/0x15d30/0x15e10)
   call **the same `0x7120`** with `rdx = 0, r8 = 0` (`0x15b0c-0x15b1e`). **One format, two families.**
4. `Hi_DrawEffModel` real body `@0x16184` calls **the same `0x4eb0` (vertex transform) and `0x56c0`
   (primitive emit)** that `Hi_DrawSummonModel @0x17740` calls (call-graph dump, §9). Proven shared.

### The handle band decoder is a PSX POINTER EMULATOR (new, and it matters for re-import)

The inline `shr edx,0x18 / cmp 0x80 / and 0x3fffff / +0xe0800000 / cmp 0x3ff` idiom (~15 sites) is not
an opaque "resource handle": the constants are the **PlayStation memory map**.

| band | test | meaning | host mapping |
|---|---|---|---|
| main RAM | top byte `0x80`, `val & 0x0fffffff < 0x200000` | PSX KUSEG0 RAM, **2 MB** | `val - g_psxBase32 + g_psxBasePtr` |
| banked | `val & 0xc00000 == 0xc00000`, top byte ≥ 0 | bank-indexed resource | `(topByte*0x20 + 8)` table `@0x576a10` |
| scratchpad | `val + 0xe0800000 <= 0x3ff` | PSX **1 KB scratchpad** `0x1f800000` | base `@0x5789e8` |

**Consequence for a re-importer:** inside the GEOM block every sub-block pointer is stored **on disk
as an offset relative to the GEOM block base**, and `0x7120` converts it in place
(`mov edx,[rsi+0xc]; add rdx,rsi; call 0x12b00; mov [rsi+0xc],eax` @`0x7233-0x7256`) — pointer → PSX
address. The model *header*'s `+0x3c/+0x40/+0x180` are already PSX addresses when Register runs.

---

## 2. THE MODEL HEADER (the summon wrapper — Eff models skip it)

`Hi_RegisterSummonModel`'s `rcx`. Only the summon family has it; `Register*EffModel` passes the raw
geometry VA instead. Field map, every entry cited:

| off | type | role | evidence |
|---|---|---|---|
| `+0x04` | u16 | **partCount** (materials), **max 6** | loop bound `cmp di,word[rsi+4]` @`0x15fd0`, `movsx eax,word[rsi+4]` @`0x1604f` |
| `+0x18` | u16[partCount] | per-part **TPAGE** | `movzx eax,word[r8-0xc]` @`0x16000` (r8 = model+0x24+2i) → `rec+0x08+4i` |
| `+0x24` | u16[partCount] | per-part **CLUT** | `movzx eax,word[r8]` @`0x1600f` → `rec+0x0a+4i` |
| `+0x30` | u16[partCount] | per-part **texture V-offset** | `movzx eax,word[r8+0xc]` @`0x16016` → the bake table (§5.4) |
| `+0x3c` | u32 | **GEOMETRY** handle | `0x15f32`→`DATA+0x08` @`0x15f3f` |
| `+0x40` | u32 | **texanim** table handle | `0x1607d`→`DATA+0x70` @`0x160f5` |
| `+0x180` | u32 | **default motion** handle | `0x15f42`→`DATA+0x10` @`0x15fc6` |

**Why max 6 is structural, not a guess:** the three arrays tile exactly —
`0x18 + 6*2 = 0x24`, `0x24 + 6*2 = 0x30`, `0x30 + 6*2 = 0x3c` (the geometry pointer). And the two
destination arrays inside the 0x58-byte record tile exactly too: `rec+0x08 + 6*4 = 0x20`,
`rec+0x20 + 6*8 = 0x50` (`rec+0x50` = the `active` byte, A2). Two independent 6-fits.

**New record fields (extend A2's `SummonRec`):**
```c
/*+0x08*/ struct { u16 tpage; u16 clut; } part[6];   // <- model+0x18[] / model+0x24[]; also DATA+0x28
/*+0x20*/ u16 partWindow[6][4];                      // <- Register arg1 (operand 1), copied verbatim
/*+0x51*/ u8  hasPartWindow;                         // = (arg1 != 0)   @0x15fcd
```
`DATA+0x28 = &rec[0x08]` (`0x71d9`) — this is the array every textured primitive's part byte indexes.

---

## 3. THE GEOMETRY BLOCK — header + skeleton + mesh table

Parsed by `0x7120` (init) → its continuation `0x7233..0x780e` (relocate + bake).

```c
struct Geom {                    // = decode(DATA+0x08)
/*+0x00*/ u8  flags;             // bit0 = relocated. `test al,1; jne <done>` @0x722b -> the whole
                                 // relocation+bake runs ONCE per loaded resource (idempotent).
/*+0x01*/ u8  zero;              // 0 in 992/992 sampled blocks
/*+0x02*/ u8  boneCount;         // `movzx eax,byte[rdx+2]` @0x4fdc (the per-bone transform loop bound)
/*+0x03*/ u8  meshCount;         // `cmp byte[rsi+3],dil` @0x72ca ; `byte[meshTbl+3]` Draw@0x17900 ;
                                 //  ModifyRGB walker @0x848d
/*+0x04*/ u32 unknownA;          // OPAQUE (not a total size — falsified on real blocks, §7)
/*+0x08*/ u32 unknownB;          // OPAQUE (looks like an id/hash)
/*+0x0c*/ u32 pBoneTable;        // relocated @0x7233-0x7256 ; ON DISK == 0x14 in 1005/1005 blocks.
                                 //  decode(+0xc) + 4 == +0x18 == the bone-link rows (fn 0x7de7 @0x813e/0x81a2/0x81aa)
/*+0x10*/ u32 pMeshTable;        // relocated @0x724d-0x7260 ; ON DISK == 0x18 + (boneCount-1)*4
/*+0x14*/ u32 listHead;          // 0 on disk (988/992); runtime slot the +0xc pointer addresses
/*+0x18*/ BoneLink bone[boneCount-1];
};
struct BoneLink { u16 len; u8 zero; u8 parentBone; };   // 4 B
```

**The `pMeshTable == 0x18 + (boneCount-1)*4` identity is THE structural law of the format** and the
single strongest evidence in this slice: it holds on **1005/1005** validated blocks, from 1-bone
effect props (mesh table at `0x18`) to Odin's 97-bone creature (mesh table at `0x1a0`). Nothing
forces that equality except a correct header decode.

**The bone-link table is the skeleton.** `fn 0x7de7` composes bone matrices from it:
`ecx=[DATA+8]` → decode → geom (`@0x80aa`), `edx=[geom+0xc]` → decode → `rdi` (`@0x813e`),
`lea rbp,[rdi+4]` (`@0x81a2`) = geom+0x18, `movzx edi,byte[rbp+3]` (`@0x81aa`) = `parentBone`,
`shl rdi,5; add rdi,r13` (`@0x81b2`) = `boneMatrix[parentBone]` (stride 0x20 = the PSXMATRIX, A2 §3).
Validated on Bahamut: 92 rows for 93 bones, `byte2 == 0` in 92/92, `len` **consistent per parent**
(0 conflicts), repeats = branch re-entries (row 9 returns to bone 1 to start a sibling limb).

```c
struct MeshDesc {                // stride 0x28 ; `lea rcx,[rax+rax*4]; lea r8,[rdx+rcx*8]` @0x58fe
/*+0x00*/ u16 unknown;           // OPAQUE (not nVert — falsified on 1012/1012 meshes)
/*+0x02*/ u16 nFT4;              // the EIGHT primitive-bucket counts, in emission order
/*+0x04*/ u16 nFT3;
/*+0x06*/ u16 nGT4;
/*+0x08*/ u16 nGT3;
/*+0x0a*/ u16 nG4;
/*+0x0c*/ u16 nG3;
/*+0x0e*/ u16 nF4;
/*+0x10*/ u16 nF3;
/*+0x12*/ u8  zero;              // 0 in 1012/1012
/*+0x13*/ s8  otBias;            // OT base = otBase + (8 - otBias)*4   (`movsx rax,byte[r8+0x13]` @0x5af7)
/*+0x14*/ u32 pVertsPerBone;     // -> u16[boneCount]     (0x4eb0 @0x5020)
/*+0x18*/ u32 pPositions;        // -> SVECTOR[nVert]      (0x4eb0 @0x50f3, `lea r12,[rcx+r13*8]` @0x517f)
/*+0x1c*/ u32 pPrimitives;       // -> the 8 contiguous lists (0x56c0 @0x5979)
/*+0x20*/ u32 pUV;               // -> u16[] uv pool       (0x56c0 @0x590b)
/*+0x24*/ u32 pColors;           // -> u32[] rgb palette   (0x56c0 @0x59e3)
};
```
The five sub-block pointers are relocated together at register time
(`0x72e0..0x7336`, five `0x12b00` calls, `lea rbx,[rbx+0x28]`).

---

## 4. THE VERTEX + SKINNING MODEL (fn `0x4eb0`, the per-mesh transform pass)

```
for b in 0..boneCount-1:                              # outer loop, `dec rax` @0x5514, rax = byte[geom+2]
    n = u16[pVertsPerBone + b*2]                      # @0x509d ; running r13 accumulates the vertex base
    GTE.R = camR · boneMatrix[b]                      # MulMatrix 0x3b60 @0x51fa
    GTE.T = camR · boneTrans[b] + camT                # 0x3d60 @0x5390, TR regs @0x211f54
    for each group of 3 vertices (r12 += 0x18):       # `lea rbx,[rbx+0x18]` @0x5442, `sub ebp,3` @0x5446
        load V0,V1,V2 from pPositions[..]             # 6 dwords = 3 x 8 bytes
        RotTransPers  x3                              # `call 0x3e80` ecx=0,1,2 @0x5449/0x5453/0x545d
        store -> SXY[idx] @0x2191a0 , OTZ[idx] @0x212440
    bones += 0x20 ; boneParams += 0x20                # @0x550c/0x5510
```

* **Vertex record = 8 bytes**: `s16 x, s16 y, s16 z, s16 w`. `w` is loaded into the unused half of the
  GTE VZ register and **never read** by `0x3e80` — leftover authoring data (in Bahamut's mesh0 it has
  436 distinct non-zero values, low byte always `0x01`; most plausibly a packed normal index).
* **Skinning is RIGID and RUN-LENGTH**: vertices are sorted by bone; `vertsPerBone[b]` gives the run.
  There is no per-vertex weight and no per-vertex bone index — the bone is implied by the run.
  (B3 §6c's "per-vertex bone index" reading is **corrected** by this.)
* `nVert = Σ vertsPerBone` — and it is exact: on Bahamut mesh0, `Σ = 797` and the largest vertex index
  appearing in any primitive is **796**. On the 59-bone Fenrir model, `Σ = 744`, max index **743**.
* Bound check: `cmp idx, 0x1b58` → **7000 vertices max per mesh** (`@0x50b3`, and in every emit loop).
* The SXY/OTZ scratch arrays are **per-mesh**, rebuilt by `0x4eb0` before each `0x56c0` (Draw's loop
  `call 0x4eb0` @`0x17922` then `call 0x56c0` @`0x179a8`).

---

## 5. THE PRIMITIVE (FACE) RECORDS — all eight types

`pPrimitives` addresses **one contiguous block holding all eight lists back to back, in this fixed
order**, each list `count[i]` records of `stride[i]` bytes. Both readers walk it this way: the
register-time UV bake (`0x7514`/`0x75b7`/`0x7667`/`0x771b`, the four textured lists) and the emit
engine (`0x5b0d` → `0x70f8`, all eight, `add rsi, <stride>` per record).

| # | type | code | count @ | src stride | out packet | tag len | emit builder |
|---|---|---|---|---|---|---|---|
| 0 | POLY_FT4 | `0x2c` | mesh+0x02 | **0x18** | 0x28 | 9 | `0x5b30..0x5e4f` |
| 1 | POLY_FT3 | `0x24` | mesh+0x04 | **0x14** | 0x20 | 7 | `0x5e80..0x6195` |
| 2 | POLY_GT4 | `0x3c` | mesh+0x06 | **0x20** | 0x34 | 0xc | `0x61c0..0x648b` |
| 3 | POLY_GT3 | `0x34` | mesh+0x08 | **0x18** | 0x28 | 9 | `0x64b0..0x6778` |
| 4 | POLY_G4  | `0x38` | mesh+0x0a | **0x18** | 0x24 | 8 | `0x67a0..0x69f3` |
| 5 | POLY_G3  | `0x30` | mesh+0x0c | **0x14** | 0x1c | 6 | `0x6a20..0x6c6f` |
| 6 | POLY_F4  | `0x28` | mesh+0x0e | **0x10** | 0x18 | 5 | `0x6c90..0x6ea3` |
| 7 | POLY_F3  | `0x20` | mesh+0x10 | **0x0c** | 0x14 | 4 | `0x6ed0..0x70f8` |
|   | terminator | `0xff` | — | — | — | — | `@0x710b` |

The `|2` semi-transparent variants (`0x2e/0x26/0x3e/0x36`) are written at `0x5dee/0x6131/0x641d/0x670c`.
Cross-checked in the **x86** build (same 8 codes + both `|2` variants + `0xff`, byte-pattern scan) and
against the managed consumer: `SFXRender.Add` switches on `tag->code & 252` with cases
32/36/40/44/48/52/56/60 (`SFXRender.cs:216-256`) — **exactly this set**, and the `&252` mask is why the
ABR bit is invisible to C#.

### 5.1 Record layouts

`v*` = vertex index (into `pPositions`), `n*` = UV index (into `pUV`), `c*` = colour index (into
`pColors`), `part` = index into `DATA+0x28` (the per-part `{tpage,clut}` pair), `flg` = flag byte.

```c
// FT4  0x18 : v0 v1 v2 v3 | n0 n1 n2 n3 | r g b part | ?? flg ?? ??
//   verts  @+0x00,02,04,06   0x5b30/0x5b32     uvidx @+0x08,0a,0c,0e   0x5cf9/0x5cdf
//   rgb dword @+0x10 -> prim+4 (0x5c7b/0x5c85) ; part @+0x13 (0x5cd7) ; flg @+0x15 (0x5baf/0x5ddd)
// FT3  0x14 : v0 v1 v2 | part | r g b ?? | n0 n1 n2 | flg ??
//   verts @+0x00,02,04 (0x5e80/0x5e82) ; part @+0x06 (0x6009) ; rgb dword @+0x08 -> prim+4 (0x5fbb)
//   uvidx @+0x0c,0e,10 (0x607d/0x6080) ; flg @+0x12 (0x5ef6/0x611a)
// GT4  0x20 : v0 v1 v2 v3 | n0 n1 n2 n3 | c0 c1 | ?? ?? ?? ?? | c2 c3 | flg part | ??
//   verts @+0x00..06 (0x61c0/0x61c2) ; uvidx @+0x08,0a,0c,0e (0x63c7/0x63ca)
//   colidx @+0x10,12 (0x638a) and @+0x14,16 (0x6353) ; flg @+0x1c (0x6261/0x6413) ; part @+0x1d (0x6386)
// GT3  0x18 : v0 v1 v2 | n0 n1 n2 | ?? ?? ?? | flg | c0 c1 c2 | part | ??
//   verts @+0x00,02,04 (0x64b0/0x64b2) ; uvidx @+0x06 (0x66d2) and @+0x08,0a (0x66d6)
//   colidx @+0x10,12 (0x6690) and @+0x14 (0x6693) ; flg @+0x0f (0x6526/0x6702) ; part @+0x16 (0x668c)
// G4   0x18 : v0 v1 v2 v3 | c0 c1 c2 c3 | ?? ?? ?? ?? flg ?? ?? ??
//   verts @+0x00..06 (0x67a0/0x67a2) ; colidx @+0x08,0a (0x6957) and @+0x0c,0e (0x692e) ; flg @+0x14 (0x6841)
// G3   0x14 : v0 v1 v2 | ?? | c0 c1 c2 | ... | flg ...
//   verts @+0x00,02,04 (0x6a20/0x6a22) ; colidx @+0x08,0a (0x6be6) and @+0x0c (0x6be9) ; flg @+0x13 (0x6a96)
// F4   0x10 : v0 v1 v2 v3 | r g b ?? | ?? flg ?? ??
//   verts @+0x00..06 (0x6c90) ; rgb dword @+0x08 -> prim+4 (0x6e15/0x6e28) ; flg @+0x0d (0x6d31)
// F3   0x0c : v0 v1 v2 | ?? ?? | r g b flg
//   verts @+0x00,02,04 (0x6ed0/0x6ed3) ; rgb dword @+0x08 -> prim+4 (0x7029/0x702c) ; flg @+0x0b (0x6f47)
```

Note the recurring PSX idiom: where a record carries an inline RGB (`FT4/FT3/F4/F3`), it is stored as a
**whole dword copied straight into the output packet's `rgbc0`**, and the dword's 4th byte occupies the
packet's `code` slot — which the builder then overwrites. FF9 reuses that otherwise-dead byte for the
**part index** in `FT4` (`+0x13`) and for the **flag byte** in `F3` (`+0x0b`); in `FT3` (`+0x0b`) and
`F4` (`+0x0b`) it is genuinely junk.

### 5.2 The flag byte (identical in all eight types)

* **bit1 = skip the backface test.** Every builder does `test byte[rsi+flgOff], 2; jne <emit>`; when
  clear it computes the 2D cross product of the projected corners and **drops the face if `<= 0`**
  (`0x5c6b/0x5c6e`, `0x5fab/0x5fae`, `0x631e/0x6321`, `0x68f9/0x68fc`, `0x6de5/0x6de8`, …).
  So **backface culling is per-face data**, done in screen space after projection.
* **bit0 = enable semi-transparency**, and **bits 5..7 = the ABR mode**: `and al,0xe0; or word[prim+..],ax;
  or byte[prim+7],2` (`0x5de1-0x5dee` FT4, `0x6124-0x6131` FT3, `0x6417-0x641d` GT4, `0x6706-0x670c` GT3).
  Proven for the four **textured** types; the four untextured builders test bit1 but do not apply the
  ABR bit — flagged as an asymmetry, not asserted either way.
  (Real sample: Bahamut-family G4/G3 records carry `flg = 0x23` = ABR-on, mode 1, no-cull.)

### 5.3 Where UVs, CLUTs and TPAGEs actually come from

```
prim->uv0 | (clut  << 16)   ; clut  = part[boneIdx].clut  = model+0x24[part]     (0x5da3-0x5dba)
prim->uv1 | (tpage << 16)   ; tpage = part[boneIdx].tpage = model+0x18[part]     (0x5dbd-0x5dc5)
prim->uv2 , prim->uv3       ; plain u16 from the pool                            (0x5dc8-0x5dd9)
uvWord = u16[pUV + n_k*2]   ; == (u | v<<8) — exactly a PSX (u8 u, u8 v) pair
colour = u32[pColors + c_k*4]  -> prim->rgbc{0..3}                               (0x6398-0x63c4)
```
So **texture binding is per-face-per-part, not per-mesh**: one mesh can mix up to 6 materials, and the
`part` byte is the material selector. This is the mechanism a re-importer must honour.

### 5.4 The one-time V-offset BAKE (a load-time mutation — do not miss it)

Inside the same `0x7120` continuation, after relocation, the four **textured** lists are walked again
(`0x7520`, `0x75d0`, `0x7673`, `0x7730`) and for every not-yet-touched UV entry:

```
byte[pUV + n*2 + 0] += partTable[part].u      ; == 0 for summon models (Register writes 0 @0x16005)
byte[pUV + n*2 + 1] += partTable[part].v      ; == model+0x30[part]   (Register @0x16016)
```
guarded by a per-index "visited" bytemap borrowed from the SXY scratch (`0x2191a0`, memset per mesh at
`0x7370-0x738d`, size `0x6d60`). The whole pass is fenced by the `flags` bit0, so it runs **exactly
once** per loaded resource. **A tool that reads a stock `ef###.bytes` sees pre-bake UVs; a tool that
reads live memory sees post-bake UVs.**

---

## 6. HOW IT REACHES `SFX_GetPrim` (the output protocol, which constrains all of the above)

Per mesh (`Draw @0x17910-0x179b8`): skip if `bt [DATA+0x20], meshIdx` (the hide mask, A2/FINDINGS §2.4)
→ `0x4eb0` fills SXY/OTZ → `0x56c0` installs the GTE matrix and runs the eight builders in list order.
Each builder writes a genuine PSX packet — the layouts match `PSX_LIBGPU.cs` field-for-field
(`POLY_FT4` `tag@0, rgbc0@4, xy0@8, uv0|clut@0xc, xy1@0x10, uv1|tpage@0x14, xy2@0x18, uv2@0x1c,
xy3@0x20, uv3@0x24`, size 0x28 — `PSX_LIBGPU.cs:317-...`; `POLY_GT4` size 0x34 —
`PSX_LIBGPU.cs:561-...`), stamps `byte[prim+3] = tagLen`, computes the OT bucket
(`Σ OTZ[v] >> 6`, clamped `[0,0xfff]` — quads; the tri builders instead average the three GTE OTZ
registers, `×0x1000/3 >> 14`, then `>>2`), and links the packet with the classic PSX `addPrim`
xor-swap, storing **packed handles** in the table (`call 0x12b00` inside the swap).

`DATA+0x18` receives the first emitted packet (`0x5a6d-0x5a73`) — that is the chain
`Hi_ModifySummonModelRGB`'s walker (`0x83d0/0x83f5`) later re-colours, dispatching on `byte[p+7]` via
the jump table `@0x8730/0x8754` with `(code & 0x3c) - 0x20`, `0xff` = end, `0xe1` = an 8-byte GPU
command. Independent confirmation of the same eight codes and their packet sizes.

`DATA+0x00 & 0x10` = a whole-model skip flag checked at `0x5818` before any emission (B3's
"`[DATA+0x20]` bit4" is **corrected** to `DATA+0x00` bit4).

**Managed side:** `SFX_GetPrim` walks that OT; `SFXRender.Add` dispatches on `code & 252`;
`SFXMesh.Poly*` turns each packet into `(x0 + drOffsetX, y0 + drOffsetY, GzDepth = -otz)` triangles.
Which is why FINDINGS §4 holds: the geometry the plugin *parses* is 3D; what *escapes* is 2D.

---

## 7. DECODED vs OPAQUE (honest ledger)

**DECODED (and data-validated):** the geom header (`flags/boneCount/meshCount/pBoneTable/pMeshTable`);
the bone-link table and its location law; the mesh descriptor incl. all 8 counts and all 5 sub-block
pointers; the vertex record (8 B, s16 xyz); the run-length rigid skinning; the UV pool (u16 = u|v<<8);
the colour pool (u32 RGB, genuinely shared — Bahamut-family G4 records reuse indices); all eight
primitive record strides and their vertex/UV/colour/part/flag field offsets; the flag byte's cull bit;
the per-part tpage/clut/V-offset binding; the load-time V-offset bake; the file-relative-offset
storage convention; the full mapping onto `POLY_*` output.

**OPAQUE (named, so the next round can close them):**
1. `geom+0x04` (u32) and `geom+0x08` (u32). `+0x04` is **not** the block size (falsified: block
   `ef227@0x8b85c` has `+0x04 = 0xac0` while its colour table alone starts at `0xa0c` and needs
   `0x1a0` more bytes). `+0x08` looks like an id/hash.
2. `MeshDesc+0x00` (u16). **Not** `nVert` (falsified on 1012/1012 meshes). Values cluster on
   `0x900/0x1a00/0x1e00/0x1f0/0x104/0x320` — smells like a default TPAGE/VRAM coordinate.
3. `BoneLink.len` exact semantics — a per-parent scalar (0 conflicts over 92 rows), almost certainly
   the bone length, but the arbiter is the bone-matrix composer `fn 0x7de7`, only partially read here.
4. The per-record "junk" bytes: `FT4 +0x14, +0x16..17`; `FT3 +0x0b, +0x13`; `GT4 +0x18..1b, +0x1e..1f`;
   `GT3 +0x0c..0e, +0x17`; `G4 +0x10..13, +0x15..17`; `G3 +0x06..07, +0x0e..12`;
   `F4 +0x0b, +0x0c, +0x0e..0f`; `F3 +0x06..07`. Some are certainly padding; `FT4+0x14` varies per
   face in real data (Bahamut mesh0: `0x80/0xd2/0x44/…`).
5. The **texture payload itself**. `tpage`/`clut` are PSX VRAM coordinates; the pixels arrive through a
   *different* resource + `PSXTextureMgr`, not through this container. Out of slice, and the real gate
   on "render a stock creature elsewhere".
6. The **motion clip** format (`DATA+0x10`) — that is B2's slice; `fn 0x7a42` is its decompressor
   (packed per-bone nibble/byte deltas keyed by frame, `0x7c40..0x7d38`).
7. Which container resource id carries a geom block — I located blocks by content scan, not by walking
   `SFXBinaryFile`'s chunk table to a typed resource. (Bahamut's lands on `0x63000`, a `0x800` sector
   boundary, so the mapping is probably trivial; not proven.)

---

## 8. IS IT A KNOWN PS1 FORMAT? (the prior-art question)

**No — and that is a *positive* finding, not a gap.** Compared against the three candidates:

| | TMD | HMD | **this format** |
|---|---|---|---|
| primitive typing | per-primitive 4-byte header (`olen/ilen/flag/mode`), self-describing | primitive-header chains per block | **eight fixed-order buckets with counts in the mesh header** |
| UVs | inline in the primitive | inline | **shared indexed pool** (`pUV`, u16 index) |
| colours | inline | inline | **shared indexed palette** (`pColors`, u32 index) |
| normals | indexed pool (`NORMAL`) | indexed | **absent** (the vertex's 4th word is unread) |
| skinning | none (TMD is rigid multi-object) | joint/coord blocks | **run-length rigid, `vertsPerBone[]` + a parent-link table** |
| vertex | `SVECTOR` 8 B | `SVECTOR` 8 B | `SVECTOR` 8 B ✔ (the one genuine TMD inheritance) |

So it is **FF9's own model format** — the "bucketed + pooled + run-length-skinned" organisation, sharing
only the `SVECTOR` and the `POLY_*` output vocabulary with Sony's libgpu/libgte. Practical
consequences: (a) no third-party TMD tool will read it; (b) a parser is ~300 lines and is **already
specified completely enough by this document to write**; (c) the format is *simpler* than TMD to emit,
because the writer chooses the bucket instead of encoding a mode byte.

**A lead worth one hour, not asserted here:** the same eight-bucket organisation is what FF9's PS1
field/battle models are documented to use in the Qhimm/Hades-Workshop lineage. If that matches, the
summon container is not a special case but *the* FF9 PS1 model format, and any prior tooling for it
transfers. Verify against the kit's own model knowledge before relying on it.

---

## 9. VALIDATION AGAINST REAL STOCK DATA (the part that makes this falsifiable)

Method: scan every `ef###.bytes` at 4-byte alignment; accept a candidate only if **all** hold —
`flags&1 == 0`, `+0x01 == 0`, `pMeshTable == 0x18 + (boneCount-1)*4`, every sub-block pointer in
range, and **both chain-closure identities** exact:

* `pPositions + nVert*8 == ` (some other sub-block offset, or EOF), where `nVert = Σ vertsPerBone`
* `pPrimitives + Σ(count[i] * stride[i]) == ` (some other sub-block offset, or EOF)

Nothing forces either identity unless every count, every stride and the vertex size are right.

| result | value |
|---|---|
| files scanned | **372** stock `ef###.bytes` |
| geometry blocks passing **all** checks | **1005** |
| of which skeletal (boneCount > 1) | **28** |
| independent third check: `pUV + 2*(4·nFT4 + 3·nFT3 + 4·nGT4 + 3·nGT3) == pColors` | **1012 / 1012 meshes, exact** |

That third identity independently proves (a) UV entries are u16, (b) exactly the four *textured*
buckets carry UV indices, (c) their per-face UV counts are 4/3/4/3, (d) the pool ordering.

**Decoded stock creatures** (`effect id → SpecialEffect`, `Memoria/Data/Battle/SpecialEffect.cs`):

| ef | effect | bones | meshes | geometry |
|---|---|---|---|---|
| **227** | **Bahamut__Full** | **93** | 2 | mesh0 `FT4=39 FT3=1326`, 797 verts · mesh1 `FT4=44 FT3=1007`, 642 verts — **2416 faces / 1439 verts** @`0x63000` |
| 261 | Odin__Full | 97 | 3 | 2302 faces |
| 251 | Madeen__Full | 93 | 2 | 2074 faces |
| 210 / 226 | Fenrir_Earth / Fenrir_Wind | 59 | 2 | 1482 faces (same model, both files) |
| 381 / 447 | Ark__Full / Ark__Short | 49 | 2 | 1981 faces |
| 184 | Atomos__Full | 5 | 2 | 1994 faces |
| 431/432/435/438/439/498 | boss deaths + Grand_Cross | 56 | 2 | 865 faces |
| 094 / 154 / 237 | Death / LV5_Death / Roulette | 19 | 3 | 354 faces |

**Spot-decode of Bahamut (real bytes) — every index bound is exact, off-by-none:**

| | mesh0 | mesh1 |
|---|---|---|
| `nVert` (= Σ vertsPerBone) vs max vertex index | **797** vs **796** | **642** vs **641** |
| `uvCount` (= 4·nFT4 + 3·nFT3) vs max UV index | **4134** vs **4133** | **3197** vs **3196** |
| max `part` index | **5** (⇒ partCount = 6, the structural maximum) | 2 |

Every `FT4/FT3` carries `rgb = 80 80 80` (the PSX neutral grey); positions bbox
`x[-419,419] y[-130,302] z[-450,968]`.
The 59-bone Fenrir model: `maxVertexIndex = 743` vs `nVert = 744`, `maxUVIndex = 4148` vs
`uvCount = 4149`, `part ≤ 3`, FT3 UV indices strictly sequential `0,1,2 / 3,4,5 / 6,7,8`
(→ an emitter can simply write UV entries in face order).

**Corrected en route:** ef227 was initially reported as having *no* skeletal model — an artifact of a
64-bone cap in the first scan pass. Bahamut has **93**. Recorded because it is exactly the kind of
instrument artifact that would have poisoned the roadmap.

**Call-graph proof of the shared path** (`m4_dis.py` + a call scan):
`DrawEffModel@0x16184 → {0x186a0, 0x4eb0, 0x56c0, 0x7820, 0x9150}` ·
`DrawSummonModel@0x17740 → {0x186a0, 0x4eb0, 0x56c0, 0x7820}`. The second emit engine `0x9150`
reads the **same** MeshDesc (`+0x1c/+0x20/+0x24` handles, `+0x13` OT bias, `+0x02` count, stride 0x28 —
`0x9393/0x93a0/0x940e/0x9478/0x957b/0x95a6`). Three such engines exist per build (x64
`0x58f9 / 0x9150 / ~0xb700`; x86 mirrors all three) — the same eight codes in each.

---

## 10. WHAT THIS UNLOCKS (for the re-import pillar)

1. **A committable parser is now writable from this document alone** — header → bone links → mesh
   table → per-mesh pools → 8 typed face lists. That is the missing half of "summon cutscenes are
   decodable like everything else."
2. **A writer is the easy direction.** Emitting is *simpler* than TMD: choose a bucket, append fixed
   records, write pools, patch five offsets per mesh + two in the header. The `pMeshTable` law and the
   two chain identities double as a free self-validating linter.
3. **This is the true creature lane for the Thomas swap.** `SFXDataMeshConverter.ExportAsSFXModel`
   (`SFXDataMeshConverter.cs:112`) writes a **post-projection, per-frame, screen-space vertex soup**
   keyed by `SFXKey` — the rung-5 `.sfxmodel` route bakes flattened frames. The container decoded here
   is the **3D model with a skeleton**, upstream of the GTE. Replacing the creature at *this* layer is
   the difference between compositing a sprite and swapping a rigged model.
4. **The provenance line stays clean and is unchanged by this slice**: shipping a *parser* is fine;
   shipping *parsed stock creature geometry* is not. Everything above is layout + logic; the only stock
   bytes touched live under `C:/gd/SCRATCH/summon-format/` and none were copied into the repo.
5. **Next concrete step (small, high-yield):** close §7 items 1–3 by decoding `fn 0x7de7` fully (it
   consumes `BoneLink` and the two unknown header dwords are adjacent), then walk `SFXBinaryFile`'s
   chunk table to a *typed* resource id for geometry so a tool can find models by table lookup instead
   of by content scan.

---

## 11. FUNCTION LEDGER (this slice)

| rva | role |
|---|---|
| `0x15ee0` | `Hi_RegisterSummonModel` — model header → record; per-part tables; `DATA+0x08/0x10/0x70` |
| `0x15ac0` / `0x15b70` / `0x15c20` / `0x15d30` / `0x15e10` | `Register{Solid,Gou,Tex,TexList,TexPtr}EffModel` — same `0x7120`, `rdx=r8=0` |
| **`0x7120`** (body → `0x780e`) | **THE PARSER**: zero DATA, decode geom, relocate `geom+0xc/+0x10` and each mesh's 5 pointers, bake per-part UV V-offsets |
| **`0x4eb0`** | per-mesh vertex pass: per-bone runs, GTE matrix compose, `RotTransPers` ×3 → SXY/OTZ |
| **`0x56c0`** (engine `0x58f9`) | per-mesh primitive emit: the eight `POLY_*` builders + OT link |
| `0x9150` | second emit engine (Eff-model variant) — identical MeshDesc |
| `0x7de7` | bone-matrix composer — the `BoneLink` consumer (`geom+0xc → +0x18`, `byte+3 = parentBone`) |
| `0x7a42` | motion decompressor (B2's slice) — reads `byte[geom+2]` for the bone count |
| `0x83d0` / `0x83f5` | `ModifySummonModelRGB` output walker — confirms codes + packet sizes |
| `0x12940` / `0x12b00` / `0x10e0` | PSX-pointer ↔ host-pointer relocation |
| `0x3e80` / `0x3b60` / `0x3d60` | GTE `RotTransPers` / `MulMatrix` / `RotTrans` |
| `0x12740` | `.seq` operand fetch (`arg0..arg3` at `cmd+0xca8/0xcac/0xcb0/0xcb4`) |

**Data:** `0x2191a0` per-vertex SXY (also the bake's visited map) · `0x212440` per-vertex OTZ ·
`0x211f40/0x211f54` GTE R/T · `0x576a10` handle bank table · `0x5789e8` PSX scratchpad base.

**Tools added (committable, read the user's own DLL, emit RVAs only):**
`m4_dis.py` (range / `.pdata`-function disassembler), `m4_scan.py` (find every site that decodes a
packed handle from a given struct offset). The data-validation script ran out of the scratchpad and
reads only `C:/gd/SCRATCH/summon-format/`.

## 12. PROVENANCE

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 + x86):
RVAs, mnemonics, struct offsets, control flow. **No DLL was modified.** Validation read
already-extracted stock `ef###.bytes` under `C:/gd/SCRATCH/summon-format/` and emitted only
**counts, offsets and field statistics** — no geometry, no animation payload, no texture bytes were
copied anywhere, and nothing was written into the repository. Every native claim cites `fn@rva`;
every managed claim cites `file:line`.
