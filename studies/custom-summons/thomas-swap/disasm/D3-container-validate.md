# D3 — THE CONTAINER + MESH DECODE, VALIDATED AGAINST REAL FILES

**Slice D3.** M2 and M4 each claimed a decoded format. D3's job was to *re-derive* those claims from the
bytes with an independent implementation and separate which are **real invariants**, which are
**overfit to one file**, and which are **wrong**.

Corpus: **all 372 stock `ef###.bytes`**, re-verified against the user's own install this round
(§1). Parser: **`ef_container.py`** (this directory, committable — reads a caller-supplied blob,
emits offsets/counts, never game bytes). RVAs are image-relative for x64
`FF9SpecialEffectPlugin.dll` (`ImageBase 0x180000000`).

---

## 0. HEADLINE — four results

1. **M2's container decode replicates essentially perfectly.** Every load-bearing count reproduced to
   the digit from an independent implementation: 372/372 files walk to their exact length, 385/385
   id-3 images relocate, the resource-id census matches all eleven values, the sequence corpus is
   11,807 opcodes / 216 max / the same 56 distinct codes, and `0x80+N` keyed by table ordinal fails
   **0** times. §2.

2. **M4's mesh decode also replicates — 1005 geometry blocks, 28 skeletal, from a different scanner**
   — but its **"exact adjacency" rule is wrong**: sub-blocks are **4-byte aligned**, and **1140 of
   4164** links in the corpus carry a 2-byte pad. A writer built on M4 as written would corrupt 27%
   of its offsets. §4.1.

3. **THE M2↔M4 CONTRADICTION IS RESOLVED, and it was load-bearing.** M2 §8.1 said `SummonData+0x08`
   points at the *texture blob*; M4 said it is the *geometry* handle. Both read their instruction
   correctly — **it is the same address at two different times.** The header and payloads stream into
   one `0x50000` arena; `arena+texOffset` holds the texture pages while id-4 DMAs them to VRAM, then
   the id-5 payload **overwrites that same address with the model image**. §5.

4. **The typed geometry lookup is CLOSED** (M4 §7 item 7, its last structural unknown). The creature's
   GEOM block is at **offset 0 of the id-5 payload, 24/24**, and the header states its exact end:
   `geomEnd == firstBlock − texOffset` holds **24/24 to the byte**. Every other geometry block in the
   game lives in resources **2 / 6 / 8 / 3 / 10**, now enumerated. §5.2, §5.3.

**Newly decoded this round and not in M2/M4:** the model header's per-part **TPAGE / CLUT / V-offset**
arrays read off disk with their VRAM rects; the **motion-clip file offsets** (`file = id5.offset +
headerRel − texOffset`), validated by 66/66 plausible frame counts and independently confirmed by M5's scan; the **texanim table's** location;
the corrected **model-image size** rule (M2's version fails 4/24, the corrected one passes 24/24).

---

## 1. CORPUS PROVENANCE — the extraction, re-verified

`d3_census.py` (scratchpad) re-opened `x64/FF9_Data/resources.assets` with UnityPy and enumerated
every `TextAsset` matching `ef\d{3}`:

| check | result |
|---|---|
| `ef###` TextAssets in `resources.assets` | **372** |
| extracted files under `C:/gd/SCRATCH/summon-format` | **372** |
| missing / extra | **none / none** |
| byte mismatches (length + sha256 vs the live asset) | **0** |
| id range | 0 … 510, 139 gaps |
| total | 68 MB, sizes `0xf800` … `0x20f000` |

`ef227` = `823296 B`, sha256 `fe590d00…` — matches the value the study recorded independently in an
earlier session. **The corpus is complete and byte-true**; nothing below rests on a partial extract.
Extra files pulled for contrast: `ef381` (Ark, the 9-chunk outlier), `ef405` (a plain spell),
`ef407` (the only `id 8` in the game), `ef447`, `ef261`.

**There is no magic number and no version field.** The file begins directly with `u16 chunkCount`
(`ef000` `01 00`, `ef227` `02 00`, `ef381` `09 00`). The format's only self-check is structural: the
walker's cursor must land exactly on the file length. A writer gets no format-version escape hatch.

---

## 2. M2's CONTAINER CLAIMS — replication

Independent re-implementation, all 372 files. **"instances"** = the number of things checked, not files.

| M2 claim | D3 result | verdict |
|---|---|---|
| the walker's cursor lands exactly on the file length | **372 / 372** | ✅ INVARIANT |
| chunks in corpus | **385** (M2: 385) | ✅ |
| resource-id census | `{0:385, 1:316, 2:385, 3:385, 4:24, 5:24, 6:24, 7:13, 8:1, 9:37, 10:4}` — **all eleven match M2** | ✅ |
| id-3 `headerRel` in range | **385 / 385** | ✅ INVARIANT |
| id-3 header words `(0,0)` | **385 / 385** | ✅ INVARIANT |
| every live `program[k]` inside the code region | **385 / 385** | ✅ INVARIANT |
| live-program counts per chunk | `1:239, 2:106, 3:23, 4:10, 5:4, 6:2, 7:1` — **identical to M2** | ✅ |
| `(chunkIndex==0, info!=0)` correlation | `(T,T): 372`, `(F,F): 13` — **identical** | ✅ correlate, not rule |
| id-2 sub-file directory clean | **381 / 385**, exceptions **`ef381` c2/c4/c7, `ef447` c2** — the *same four* | ✅ |
| sequence terminates on a real `END` | **372 / 372** | ✅ INVARIANT |
| zero invalid opcodes corpus-wide | **11,807 / 11,807 VALID**, max 216 ops/file | ✅ INVARIANT |
| 56 distinct opcodes, exact list | **identical set** | ✅ |
| `0x80+N` liveness keyed by **table ordinal** | **0 failures** | ✅ INVARIANT |
| `0x80+N` liveness keyed by the `chunkIndex` **field** | **11** failures (M2: 13), all in `ef381` | ✅ conclusion holds |
| `ef227`: 2 chunks, 18 resources, table ends `0x54`, 93 ops / 511 ticks | **all exact** | ✅ |
| `ef227` id-3: `headerRel 0x3120` prog `0x9d4`; chunk1 `0x42bc` / `0x108c` | **exact** | ✅ |

Two notes, neither of which moves a conclusion:
* the **11 vs 13** difference is methodological — I map a `chunkIndex` value to the *first* chunk
  bearing it; M2 may have mapped it differently. The load-bearing half (ordinal ⇒ 0 failures)
  reproduces exactly, so `LOAD_CHUNK`'s key is confirmed.
* **`extra_sectors` is 0 in 371 of 372 reads**, and 5 exactly once (`ef251` chunk 0). The `id==2 &&
  info!=0` gate therefore *consumes* two bytes 372 times and *changes the cursor* once. That is why
  the C# `chunkIndex==0` correlate survived: on stock data the two rules consume the same bytes.
  On synthesised data they diverge — **use `info != 0`** (M2 is right).

**Resource `id 10` locations** (dead in the PC port, no dispatch slot): `ef381` chunks 2/4/7 and
`ef447` chunk 2 — i.e. only in the two multi-chunk Ark effects.

**Shape census** (new): chunks per file `{1:367, 2:3, 3:1, 9:1}`; resources per chunk 3…13;
sequence lengths cluster at 1–50 ops with `ef381` alone at 216.

---

## 3. M2's MODEL-PACKAGE CLAIMS — replication + two corrections

24 model packages (`ef038 177 179 184 186 210 211 225 226 227 251 261 276 381 431 432 435 438 439
447 493 494 495 498` — matches M2's list exactly).

| M2 §8 claim | D3 result | verdict |
|---|---|---|
| `texOffset == 0x180 + 4*motionCount` | **24 / 24** | ✅ INVARIANT |
| `texBytes == pageCount * 0x4000` | **24 / 24** | ✅ INVARIANT |
| `clutBytes == clutRows * 0x200` | **24 / 24** | ✅ INVARIANT |
| `texOffset + texBytes + clutBytes <= id4 payload` | **24 / 24** | ✅ INVARIANT |
| motion offsets in bounds | **24 / 24** (stricter bound than M2's) | ✅ INVARIANT |
| `firstBlock == motionOffsets[0]` | **19 / 24** (M2 said 19/24) | ⚠️ NOT an invariant — but see §5.2, its *meaning* is now known and the exact rule is 24/24 |
| **`modelBytes` within one sector of the id-5 payload size** | **20 / 24** — fails `ef184 ef210 ef251 ef381` | ❌ **WRONG AS STATED** |

### 3.1 CORRECTION — `modelBytes` is header-relative

`modelBytes` (`header+0x10`) is not the model image's size; it is the image's **end address measured
from the header**. The image size is `modelBytes − texOffset`, and then

```
0 <= id5.nbytes - (modelBytes - texOffset) < 0x800      →  24 / 24
```

(slacks `0x20 … 0x730`, all sub-sector). Byte evidence, `ef227`: `modelBytes = 0x26c74`,
`texOffset = 0x1a0`, image `0x26ad4`, id-5 payload `0x27000`, slack `0x52c`. The native code agrees:
`0x3e3dc` computes `header + [rsi+0x10]` and stores `psx(...)` at `model[+0x44]` — an **address**,
not a length.

### 3.2 CORRECTION — three header fields were mis-labelled

`Hi_RegisterSummonModel` is called with `rcx = rsi` where `rsi` is this very struct (`@0x3e447`), so
**M2's "package header" and M4's "model header" are the same struct.** Merging them and reading the
disk bytes settles the labels:

| off | M2 called it | M4 called it | **D3 verdict (evidence)** |
|---|---|---|---|
| `+0x04` | `pageCount` | `partCount` | **the same field** — one 64×128 texture page per material part. `ef227` = 6, and its geometry's `part` byte ranges exactly 0…5. |
| `+0x18` | "VRAM page/row selector" | **TPAGE** | **TPAGE.** `ef227` = `147,147,148,148,149,149`; the id-4 handler decodes `x=(tpage&0x0f)*64`, `y=((tpage&0x10)<<4)+vOff` (`@0x3e302-0x3e328`). |
| `+0x24` | *(undescribed)* | **CLUT** | **CLUT.** `ef227` = `0x3990,0x39d0,…,0x3ad0`; a PSX CLUT word decodes to `y = 0x3990>>6 = 0xE6`, and the CLUT strip really is uploaded at `y=0xe6` (`@0x3e286` rect `{0x100, 0xe6, 0x100, clutRows}`). Two independent derivations of the same `0xe6`. |
| `+0x30` | "VRAM x word" | texture **V-offset** | **V-offset (M4 right, M2 wrong).** It is added to the rect's **y** (`@0x3e31c` → `[rsp+0x62]`), values `128,0,128,0,128,0`. |

`ef227`'s six pages therefore land at VRAM `(192,384) (192,256) (256,384) (256,256) (320,384)
(320,256)`, each 64×128 — a clean 3×2 tiling. `+0x3c` and `+0x40` are **0 on disk** and filled at load
(§5).

### 3.3 ANOMALY — `partCount` does not bound the `part` index

6 of 24 packages use geometry `part` indices **beyond** `partCount−1`:

| ef | partCount | part indices actually used |
|---|---|---|
| ef431/432/435/438/439/498 | **1** | 0, 1, **2** |
| ef227 | 6 | 0…5 ✔ |
| ef038 | 5 | 0,2,3,4 ✔ |

The runtime per-part table has exactly **6** slots (`rec+0x08 + 6*4 = 0x20`), zero-filled below
`partCount`, so out-of-range parts render with `tpage=clut=0`. **A re-importer must not assume
`part < partCount`.** Separately, exactly **8 records in one Eff-model block** (`ef130 @0x29d38`, all
`GT3`) carry `part = 6`, one past the 6-slot table — flagged as an anomaly/probable junk byte, not a
refutation of the 6-slot law.

---

## 4. M4's MESH CLAIMS — replication + corrections

Scanner: `ef_container.scan_geom` — prefilter `flags&1==0`, `byte[+1]==0`, `pBoneTable==0x14`,
`pMeshTable == 0x18+(boneCount-1)*4`, then all four chain identities.

| M4 claim | D3 result | verdict |
|---|---|---|
| geometry blocks in the corpus | **1005** | ✅ **exact replication** |
| of which skeletal (`boneCount>1`) | **28** | ✅ exact |
| `pMeshTable == 0x18 + (boneCount-1)*4` | **1005 / 1005** | ✅ INVARIANT (and the format's real signature) |
| `pBoneTable == 0x14` on disk | **1005 / 1005** | ✅ INVARIANT |
| `MeshDesc+0x12 == 0` | **1041 / 1041 meshes** | ✅ INVARIANT |
| `MeshDesc+0x00 != nVert` | **0 / 1041 match** | ✅ M4's falsification CONFIRMED — it is not `nVert` |
| `geom+0x04` is not the block size | **4 / 1005** match (coincidence rate) | ✅ falsification CONFIRMED |
| `maxVertexIndex == nVert − 1` | **1041 / 1041 EXACT** | ✅ INVARIANT — proves the 8-byte vertex, `Σ vertsPerBone`, and the vertex fields of all 8 record types |
| `maxUVIndex == uvCount − 1` | **969 / 969 EXACT** | ✅ INVARIANT — proves u16 UV entries, the 4/3/4/3 per-face counts, and that only the 4 textured types carry UVs |
| flag bit1 = skip backface test, bit0 = semi-transparent | low 5 bits take **only `{0,1,2,3}`** corpus-wide | ✅ consistent; bits 2–4 are **always zero** (new) |
| inline RGB is PSX neutral grey | **93,426 of 96,115** inline-RGB records are `(128,128,128)`; only **8 distinct** RGB triples exist in the whole game | ✅ |
| `geom+0x01 == 0` | used as a prefilter — cannot be independently counted; no block was rejected for any other reason, so it costs nothing | ⚪ untested by construction |
| `listHead (+0x14) == 0` on disk | **7 / 1005 NON-zero** (incl. **`ef227` = `0xff90`**, `ef038`, `ef261`) | ❌ **NOT an invariant** — do not gate on it |
| vertex `w` low byte "always `0x01`" | **97 distinct** low-byte values corpus-wide; `0x00` dominates | ❌ **OVERFIT** to one Bahamut mesh |
| mesh count | **1041** (M4 said 1012) | ⚠️ instrument difference, unexplained; block count agrees exactly |

### 4.1 CORRECTION — sub-blocks are 4-BYTE ALIGNED, not exactly adjacent

M4 asserts `pUV + 2*uvCount == pColors` "1012/1012, exact". **It is not exact.** Measuring all four
links on all 1005 blocks:

```
padding between a sub-block's end and the next sub-block's start:
    0 bytes : 3024 links
    2 bytes : 1140 links
    anything else : 0
```

The rule is `next == align4(prev_end)`, universally. Byte evidence in M4's own headline model:
`ef227` mesh1 has `uvCount = 3197` (odd) → `pUV + 6394` ends at `0x1279a`, and `pColors = 0x1279c`.
M4 reported that very `uvCount` and still called the identity exact. Same failure on
`vertsPerBone → positions` whenever `boneCount` is odd (`ef227` mesh0: `0x1d8 + 186 = 0x292`,
`pPositions = 0x294`).

**This matters for R2/R7 (writer + re-import): a writer that packs tight will mis-place every
sub-block after the first odd-length pool.** `ef_container.geom_checks` now uses `align4`.

### 4.2 The prefilter is 100% selective — a useful practical fact

Across 68 MB, **every** candidate that passed the two header laws (`pBoneTable==0x14` **and**
`pMeshTable == 0x18+(boneCount-1)*4`) then passed all four chain identities: **zero rejections**.
So the two header laws alone identify geometry with no false positives in the shipped corpus. That is
a strong independent signal that the header decode is right — and it makes `scan_geom` cheap.

### 4.3 Colour pool — the one length the block never states

All four colour-bearing types (`GT4 GT3 G4 G3`) were exercised, which M4 could not do (the 24
creatures use **only** `FT4`/`FT3`). Corpus-wide bucket usage:

```
FT4 20355 · FT3 72542 · GT4 9631 · GT3 24124 · G4 3441 · G3 2417 · F3 3137 · F4 81
```

All eight buckets appear, so all eight strides are exercised by the chain identity. For the colour
index fields specifically: taking `impliedEnd = pColors + 4*(maxColIdx+1)`, across the 852 blocks
that are followed by another block **0 overrun** and **184 land exactly on the next block's base** —
and those 184 include `GT3` (144), `GT4` (124), `G3` (15), `G4` (14). That validates the colour-index
offsets of all four types.

The honest gap: **every colour-bearing mesh in the corpus is the last mesh of its block**, so the
colour pool's length is never derivable from the block alone. For a creature the summon header
supplies it (`firstBlock`); for an Eff model it must come from the caller's resource extent.

### 4.4 `otBias` (`MeshDesc+0x13`)

Values corpus-wide: `0` (1032 meshes), `-2` (3), `-1` (3), `1` (3). Effectively always 0 — but a
writer must emit it, and it is signed.

---

## 5. THE RESOLUTION: WHERE THE GEOMETRY ACTUALLY IS

### 5.1 The staging rule (this is the piece both prior slices were missing)

Reading the two handlers end-to-end:

```
id-4 handler @0x3e272 :  header = decode([0x323244])
                         rsi    = header + s16[header+0x00]        ; = header+texOffset
                         LoadImage(CLUT rect{0x100,0xe6,0x100,clutRows}, rsi + [header+8])
                         for i in 0..partCount-1:                  ; @0x3e302
                             LoadImage({(tpage&0xf)*64, ((tpage&0x10)<<4)+vOff, 64, 128}, rsi)
                             rsi += 0x4000
id-5 handler @0x3e373 :  header[+0x3c] = psx(header + texOffset)   ; @0x3e39c
                         header[+0x40] = psx(header + firstBlock)  ; @0x3e3a7
                         motionTable[i] += psx(header)             ; @0x3e3c0-0x3e3d1
                         header[+0x44] = psx(header + modelBytes)  ; @0x3e3f3
                         header[+0x48] = 0x50000 - modelBytes      ; @0x3e40d-0x3e417  (arena free space)
                         Hi_RegisterSummonModel(rcx = header, ...)  ; @0x3e447/0x3e44e
Register  @0x15ee0    :  DATA+0x08 = model[+0x3c]                  ; @0x15f32/0x15f3f
                         call 0x7120(rcx = DATA, ...)              ; @0x1606c/0x16078
fn 0x7120             :  r9d = [rcx+8]  → decode → rsi             ; @0x7130
                         movzx eax, word[rsi]; test al,1           ; @0x7228 = the GEOM flags byte
```

So `DATA+0x08` = `header + texOffset` **and** fn `0x7120` parses that address as a GEOM block.
That is only consistent if `header + texOffset` holds the **model image**, not textures — which is
exactly what happens: the `0x50000` arena keeps the header at `arena[0 .. texOffset)`, streams the
id-4 payload's texture+CLUT into `arena+texOffset`, DMAs them to VRAM, and then the id-5 payload
**overwrites the same address** with the model image. The textures are transient staging.

**Verdict: M4 is right that `DATA+0x08` is the geometry handle. M2 §8.1's "it is a pointer to the
texture blob, not the geometry" is WRONG** — and its correction to `FINDINGS.md` should be reverted.
`FINDINGS.md`'s original "`SummonData+0x08` ← model `+0x3c`" was right about the plumbing.

### 5.2 The consequence — an exact offline address map, proven 24/24

Because every model-image field is header-relative:

```
file offset = id5.offset + headerRelative - texOffset
```

Two independent falsifiable tests, both **24/24 exact**:

| identity | result |
|---|---|
| `geomBlockEnd == firstBlock − texOffset` (geometry ends where the texanim table starts) | **24 / 24 exact** |
| `0 <= id5.nbytes − (modelBytes − texOffset) < 0x800` | **24 / 24** |

and a third, independent of both: computing each motion clip's file offset by the same rule and
reading `u16[clip+2]` (the frame count `Hi_SetSummonMotion @0x17a10` uses) gives **66/66 plausible
counts** (1…173; `u16[clip+0] == 0` in all 66). `ef227` = **8 clips of 24, 30, 26, 48, …** frames at
file `0x7579c, 0x7680c, 0x77ae8, 0x79064, 0x7c3d8, 0x7e3e8, 0x825f8, 0x87a84`.

**The id-5 model image layout is therefore fully addressed:**

```
id5.offset + 0                          GEOM block  (geometry, skeleton, meshes, pools)
id5.offset + firstBlock - texOffset     texanim table  (-> model+0x40 -> DATA+0x70)
id5.offset + motion[k] - texOffset      motion clip k  (u16[+2] = frameCount)
id5.offset + modelBytes - texOffset     end of image (within one sector of the payload end)
```

`firstBlock == motion[0]` in the 19 packages with an **empty** texanim region; the 5 that differ
(`ef038 ef177 ef493 ef494 ef495`) have a real texanim table of 116 or 364 bytes. That is the whole
explanation of M2's unexplained 19/24.

### 5.3 Which resource carries geometry — M4 §7 item 7, CLOSED

Attributing all 1005 blocks to the resource whose byte span contains them:

| resource id | blocks | at the resource's offset 0 | what it is |
|---|---|---|---|
| **5** SUMMON_MODEL | **24** | **24 / 24** | the creature — always the first thing in the payload |
| 2 SOUND_AKAO / sub-file archive | 658 | 0 | Eff-model props, addressed through the sub-file directory |
| 6 "MARK_6" | 282 | 0 | **not a marker** — its payload is a model bank |
| 8 "MARK_8" (`ef407` only) | 20 | 0 | ditto |
| 3 CHUNK_IMAGE | 12 | 0 | geometry embedded in the PS1 RAM image's data region |
| 10 (dead) | 9 | 0 | inside the ignored resource |

So a tool never has to content-scan for a **creature**: `parse_model_package` → `creature_geom` is a
typed lookup. Ids 6 and 8 being *only* load-state markers (M2 §4) is true of the **handler**, not of
the payload — 302 models live there.

---

## 6. THE 24 STOCK CREATURES — decoded from a typed lookup

`bones / meshes / verts / faces / motion clips / partCount / buckets / model-image size`.

| ef | bones | meshes | verts | faces | clips | parts | buckets | image |
|---|---|---|---|---|---|---|---|---|
| **227** Bahamut | **93** | 2 | **1439** | **2416** | **8** | 6 | FT4 83, FT3 2333 | `0x26ad4` |
| 261 Odin | 97 | 3 | 1359 | 2302 | 7 | 6 | FT4 198, FT3 2104 | `0x29378` |
| 038 | 67 | 3 | 1405 | 2236 | 1 | 5 | FT4 238, FT3 1998 | `0x1c160` |
| 251 Madeen | 93 | 2 | 1310 | 2074 | 4 | 6 | FT4 424, FT3 1650 | `0x1bea0` |
| 276 | 67 | 2 | 1348 | 2072 | 4 | 5 | FT4 400, FT3 1672 | `0x163c4` |
| 184 Atomos | 5 | 2 | 1575 | 1994 | 1 | 5 | FT4 484, FT3 1510 | `0x107e0` |
| 381 Ark | 49 | 2 | 1593 | 1981 | **12** | 6 | FT4 517, FT3 1464 | `0x17f98` |
| 447 Ark (short) | 49 | 2 | 1593 | 1981 | 1 | 6 | *identical geometry* | `0x10c30` |
| 211 / 225 | 84 | 2 | 1245 | 1936 | 4 / 1 | 6 | FT4 284, FT3 1652 | |
| 179 | 77 | 2 | 1074 | 1909 | 5 | 5 | FT4 125, FT3 1784 | `0x21c28` |
| 186 | 84 | 3 | 1382 | 1830 | 3 | 5 | FT4 578, FT3 1252 | `0x160d0` |
| 177 / 493 / 494 / 495 | 68 | 2 | 870 | 1510 | 1 | 3 | FT4 136, FT3 1374 | `0x10cec` |
| 210 / 226 Fenrir | 59 | 2 | 852 | 1482 | 3 / 2 | 4 | FT4 18, FT3 1464 | |
| 431/432/435/438/439/498 | 56 | 2 | 552 | 865 | 1 | 1 | FT4 134, FT3 731 | `0x7398` |

Matches every entry of M4 §9's table where they overlap (Odin 97/3/2302, Madeen 2074, Fenrir 1482,
Ark 1981, Atomos 1994, boss deaths 865), and adds the three M4 could not list (`ef038`, `ef227`,
`ef261` — they were excluded by the `listHead == 0` gate that §4 shows is not an invariant).

**Every creature uses only `FT4` + `FT3`** — flat-shaded textured tris and quads with inline RGB.
Nothing in the game's creature set needs the Gouraud pools. Skeletons: `parent <= rowIndex+1` in
**1551/1551** bone links and the middle byte 0 in **1551/1551** — a well-formed forward-referencing
tree.

---

## 7. INVARIANT vs OVERFIT — the ledger

**REAL INVARIANTS (hold on every instance in the shipped corpus):**
the cursor-equals-length walk · `info != 0` as the extra-field gate · the id-3 header/program layout ·
`0x80+N` keyed by chunk table ordinal · the sequence's validity map · `texOffset == 0x180+4N` ·
`texBytes == parts*0x4000` · `clutBytes == clutRows*0x200` · `geomEnd == firstBlock − texOffset` ·
`modelImageSize = modelBytes − texOffset` within a sector · geometry at id-5 offset 0 ·
`pBoneTable == 0x14` · `pMeshTable == 0x18+(boneCount-1)*4` · `MeshDesc+0x12 == 0` ·
`maxVertexIndex == nVert−1` · `maxUVIndex == uvCount−1` · sub-blocks 4-byte aligned in the fixed order
`vertsPerBone → positions → primitives → uv → colors` · flag bits 2–4 always zero.

**NOT invariants (true of most files, do not gate on them):**
`listHead == 0` (7/1005 non-zero, incl. Bahamut) · `firstBlock == motion[0]` (19/24) ·
`part < partCount` (fails in 6/24 packages) · `chunkIndex == 0` as the extra-field gate (a correlate).

**OVERFIT to one file / falsified:**
M4's "exact adjacency" (1140/4164 links are padded) · M4's vertex-`w` "low byte always 0x01"
(97 distinct values corpus-wide) · M2's `modelBytes` sector rule as written (4/24 fail) ·
M2's `+0x30` = "VRAM x word" (it is the y/V offset) · M2 §8.1's `DATA+0x08` = texture pointer.

**Still genuinely OPAQUE** (unchanged by this round): `geom+0x04` and `geom+0x08`;
`MeshDesc+0x00`; `BoneLink.len`; the per-record junk bytes; the `info` byte for ids 0/1/9; the
texanim table's own format; the motion clip body (only its header word is validated here); the id-3
MIPS program.

---

## 8. WHAT IS NOW "DECODED" — the honest line

**DECODED, byte-validated, parseable offline:** the container (header sector, chunk/resource table,
sub-file directory, id-3 image + program table, the sequence stream) · the creature model header
including per-part TPAGE/CLUT/V-offset and their VRAM rects · the model image's internal address map
(geometry, texanim, motion clips, end) · the geometry block end-to-end (skeleton, mesh table, vertex
pool, run-length rigid skinning, all eight primitive buckets with their vertex/UV/colour/part/flag
fields, the UV and colour pools).

Concretely: **`ef_container.py` reads Bahamut off the user's disk and reports 93 bones, 2 meshes,
1439 vertices, 2416 faces, 6 texture pages with their VRAM rects, and 8 motion clips at exact file
offsets — with every one of those numbers cross-checked by an identity that would break if any field
were misread.**

**NOT decoded:** the texanim table and the id-3 MIPS program that stages the creature. The pillar's
gate is still M2 §10's **R6**.

### 8.1 Cross-validation with M5 (motion) — two methods, one answer

M5 decoded the motion clip body and located Bahamut's clips by **scanning** for them: "8 motion
clips, all 93 bones, back-to-back at file offset `0x07579c..0x089ad4`, plus an 8-entry motion pointer
table at `0x4a180`."

D3 reached the same addresses by **arithmetic** — `file = id5.offset + motionOffsets[k] − texOffset`
gives `0x7579c` for clip 0, and the pointer table is `header(0x4a000) + 0x180 = 0x4a180`. Two
independent derivations, identical to the byte. M5's skeleton record
(`{s16 boneLength; u8 unused; u8 parentIndex}`, count `u8[model+0x02]`) is M4's `BoneLink` at the
GEOM block's `+0x18` with `boneCount` at `+0x02`, which D3 measured well-formed in **1551/1551** rows.

So the creature lane is now continuous: **container → model header → geometry block (D3/M4) → motion
clips (M5)**, every hop addressable offline with no content scan.

### Roadmap deltas for M2 §10

* **R2 (writer) is riskier than M2 estimated** and must implement §4.1's align-4 rule, §3.1's
  header-relative addressing, and must not gate on `listHead`/`firstBlock == motion[0]`.
* **R4 (texture/CLUT swap) is now fully specified**: pages are at `id4.offset + texOffset`, `0x4000`
  each, `partCount` of them, with rect `((tpage&0xf)*64, ((tpage&0x10)<<4)+vOff, 64, 128)`, followed
  by `clutRows × 0x200` of CLUT at VRAM `(0x100, 0xe6)`. No code needed.
* **R7 (geometry/motion export) can start now for geometry** — the typed lookup + the exact block
  extent remove the content-scan dependency M4 flagged. Motion still needs its clip format.

---

## 9. FILES

* **`ef_container.py`** (this directory) — the parser. Container + sub-file directory + id-3 image +
  model header + geometry (`parse_geom`, `geom_checks`, `iter_primitives`, `vertices`,
  `creature_geom`, `scan_geom`, `vram_rect`). CLI: `py ef_container.py <file> [--scan-geom]`.
  Committable: it reads a caller-supplied blob and prints offsets/counts. **No game bytes are
  embedded or emitted into the repo.**
* Validation harnesses (`d3_census.py`, `d3_validate.py`, `d3_geomscan.py`, `d3_prims.py`,
  `d3_colours.py`) ran out of the session scratchpad and read only
  `C:/gd/SCRATCH/summon-format/`; their outputs are the tables above.

## 10. PROVENANCE

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64) — RVAs,
mnemonics, struct offsets, control flow. **No DLL was modified or redistributed.** Stock
`ef###.bytes` were read only from `C:/gd/SCRATCH/summon-format/` (extracted from the user's own
install by the study's UnityPy recipe). **Nothing game-derived — geometry, animation, texture or raw
container bytes — was written into the repository.** Every number above is structural (offsets,
counts, sizes, indices) or a field statistic.
