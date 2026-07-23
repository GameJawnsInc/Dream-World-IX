# T2 — NATIVE MODEL-IMAGE INJECTION (the truest, hardest transplant)

**The slice's question.** Can we replace the summoned creature's GEOMETRY **at the source** — write our own
model into the `ef###.bytes` resource id-5 ("summon model image" → `Hi_RegisterSummonModel`) — so the
**native** pipeline literally animates + draws OUR mesh with the stock skeleton + motion + camera, with **no
overlay at all**?

**The verdict, up front: the id-5 model-image geometry format is PROVEN ROUND-TRIPPABLE and PROVEN WRITABLE.**
A committable writer (`ef_geom_writer.py`, this directory) re-emits every stock creature's geometry block
byte-for-byte, re-assembles the full id-5 model image (geometry + texanim + motion) with the header's own
offset math, and emits a **novel** geometry block (our own vertices/faces) on a 93-bone skeleton that passes
every structural identity the native parser enforces. The geometry write — the piece the roadmap (D2/FORMAT
§4.3 rung **W5**) rated HIGH and feared — **is not the bottleneck. It is closed.** What remains for a native
creature swap is two things that are *not* the geometry format: the untested **W0 loadability gate** (does a
mod-folder `ef###.bytes` override even load?) and **rig conformance** (our model bound to the donor's exact
bone semantics) — and the latter is shared with T1.

All RVAs are image-base-relative for the user's own `FF9SpecialEffectPlugin.dll` (x64 `ImageBase
0x180000000`). C# cites are `C:/gd/FFIX/Memoria/Assembly-CSharp/…:line`. **Provenance:** the writer/reader are
**code** (committable, embed zero game bytes). Every round-trip harness read only the user's own locally
extracted corpus under `C:/gd/SCRATCH/summon-format/` and emitted **only MATCH/counts**. No stock geometry,
animation, texture, or container bytes were written into the repo. No DLL was modified.

---

## 1. WHAT THE id-5 MODEL IMAGE IS (the format under the swap) — DECODED

The id-5 payload is the **model image**, laid out as three regions the header addresses (D3 §5.2, 24/24 exact):

```
id5.offset + 0                        GEOM block   (skeleton + mesh table + vertex/prim/uv/colour pools)
id5.offset + firstBlock - texOffset   texanim table  (OPAQUE; empty in 19/24 creatures incl. Bahamut)
id5.offset + motion[k]  - texOffset   motion clip k  (M5-decoded; the donor's animation)
id5.offset + modelBytes - texOffset   end of image
```

The **creature package header** (motionCount, partCount, per-part TPAGE/CLUT/V-offset, firstBlock,
modelBytes, the motion table) lives at the **start of the id-4 payload**, not id-5 (D3 §3.2). A full
model-image swap therefore touches **both** id-4 (header + textures) and id-5 (geometry + motion), and must
re-patch the header's offsets to our geometry's new size (§3).

The GEOM block itself (`M4-mesh-payload.md`, re-validated `D3` §4):

```c
GEOM  +0x00 u8 flags(=0)  +0x01 u8(=0)  +0x02 u8 boneCount  +0x03 u8 meshCount
      +0x04 u32 OPAQUE    +0x08 u32 OPAQUE   +0x0c u32 pBoneTable(=0x14)
      +0x10 u32 pMeshTable(== 0x18 + (boneCount-1)*4)       +0x14 u32 listHead
      +0x18 BoneLink[boneCount-1] { s16 length; u8 0; u8 parentIndex }   <-- THE SKELETON
      (pMeshTable) MeshDesc[meshCount] stride 0x28
      per mesh, 4-byte aligned in order: vertsPerBone -> positions -> primitives -> uv -> colors
```

* **Skeleton** = the `BoneLink` table: a bone's local translation is the single scalar `length` along local
  Z, parent index **must be < child index** (`fn 0x7de7 @0x81aa`; M5 §4). `boneCount = u8[geom+0x02]`.
* **Mesh table** = `MeshDesc[]`: the 8 `POLY_*` bucket counts (`FT4 FT3 GT4 GT3 G4 G3 F4 F3`) + `otBias` +
  five GEOM-relative sub-block pointers (`0x14/0x18/0x1c/0x20/0x24`).
* **Skinning is RIGID + RUN-LENGTH** (`fn 0x4eb0 @0x509d`): vertices are sorted by bone, `vertsPerBone[b]`
  gives bone `b`'s run. **This run-length assignment IS "which vertices bind to which bone."** No weights, no
  per-vertex bone index.
* **8 primitive buckets**, fixed order/strides; `part` byte per textured face indexes the ≤6 `{tpage,clut}`
  pairs. Every stock creature uses **only `FT4`+`FT3`** with inline neutral-grey RGB.

---

## 2. WRITABILITY — PROVEN, with byte evidence

Deliverable tool: **`ef_geom_writer.py`** (committable). It lifts a parsed block into a fully-typed
`GeomModel` (bones, per-mesh vertex/primitive/uv/colour arrays, every decoded primitive field) and
`serialize()`s it back. **TYPED** (regenerated from semantic values): every header field, the bone table,
all 8 bucket counts, `otBias`, the five sub-block pointers (**recomputed** from the align-4 layout), the
`vertsPerBone` runs, the vertex pool (s16 x,y,z,w), the UV pool (u16), the colour pool (u32), and every
decoded primitive field. **CARRIED VERBATIM** (the short, named opaque ledger from M4/D3): `geom+0x04`,
`geom+0x08`, `listHead`, `MeshDesc+0x00`, and the per-record junk bytes — exactly the roadmap's "carry the
opaque fields" guidance, not a gap.

### 2.1 GEOM round-trip byte-identity

| test | result |
|---|---|
| **24 stock creatures** — full GEOM block parse → serialize → compare | **24 / 24 byte-identical** (`ef227` `0x1279c B`, Odin `ef261` `0x11d44`, Atomos `ef184` `0x107a4`, …) |
| **1005 GEOM blocks corpus-wide** — every primitive record re-emitted from decoded fields | **135,728 / 135,728 records identical, 0 mismatches**, all 8 buckets (`FT4 20355 · FT3 72542 · GT4 9631 · GT3 24124 · G4 3441 · G3 2417 · F4 81 · F3 3137`) |
| vertsPerBone / positions / uv pools re-emitted from typed values | **1041 / 1041 each** |
| bone table re-emitted from `(len,parent)` | **1005 / 1005** |
| **mesh-table pointer LAYOUT MATH** — recompute all five pointers from the align-4 rule | **1005 / 1005** (proves the layout is deterministic + reconstructible, not carried) |

`py ef_geom_writer.py <ef###.bytes>` reproduces the per-creature line; the corpus record/pool sweep is in
this slice's log. **Nothing forces byte-identity except a correct field-level decode**, and it holds on every
block in the shipped game.

> **The one honest edge:** the raw **colour-pool bytes** were validated only *indirectly* — D3's
> chain-closure identity (184 blocks land exactly on the next block's base) plus the fact that every stock
> creature's colour pool is empty (FT4/FT3 only), so the full-block creature round-trip serializes them
> directly. Every colour *index field* in all 24,124 GT3 / 9,631 GT4 / 3,441 G4 / 2,417 G3 records
> round-trips. The colour-bearing mesh is always the block's **last** mesh (D3 §4.3), whose pool length the
> block never states — a writer receives it from the caller (for a creature, the header's `firstBlock`
> states it). This does not affect a creature swap (no colour pools).

### 2.2 Full id-5 model image + header offset math — PROVEN

Re-assembling `ef227`'s id-5 image as `serialize(geom) + texanim(carried) + motion_clips(carried)` and
recomputing the header offsets from the assembled sizes:

```
assembled image  0x26ad4 B   == original id-5 payload  (byte-identical)
firstBlock   stock 0x1293c  recomputed 0x1293c   (= texOffset 0x1a0 + geomLen 0x1279c)   MATCH
modelBytes   stock 0x26c74  recomputed 0x26c74                                            MATCH
motion[0..7] stock [0x1293c,0x139ac,0x14c88,0x16204,0x19578,0x1b588,0x1f798,0x24c24]      MATCH (all 8)
```

**This is the integration math a swap needs:** when our GEOM block has a *different* byte length, the same
formulas re-place the (carried) texanim + motion clips after it and re-patch `firstBlock`, `modelBytes`, and
every `motion[k]`. Proven exact on the donor's own geometry, so the arithmetic is settled. The container
itself rebuilds byte-identical **371/372** files (the one miss = `ef251`'s single `extra_sectors=5` id-2
region, D3 §2 — a 2-line copy fix); writing the modified payload back into `ef###.bytes` (roadmap **W1**) is
therefore **LOW**, not a research item.

### 2.3 Novel geometry (OUR mesh) accepted by the native structural laws — PROVEN

Emitting a **synthetic** block — our own s16 vertices, our own FT3 faces, run-length-skinned across a
**93-bone** skeleton (matching Bahamut's clip bone count), all opaque fields synthesized as 0 — then parsing
it back with the independent reader and running the format's self-validating linter:

```
emitted novel GEOM block len=0xf74  ->  parsed back: bones=93 meshes=2 verts=372 faces=5
geom_checks: flags_bit0_clear pBoneTable_is_0x14 pMeshTable_law mesh_byte0x12_zero
             chain_vertsPerBone_to_positions chain_positions_to_primitives
             chain_primitives_to_uv chain_uv_to_colors in_bounds   -> ALL PASS
budget: image<=0x50000 ✔  verts/mesh<=7000 ✔  parts<=6 ✔
```

`pMeshTable_law` + the four chain-closure identities are precisely what `fn 0x7120` and the emit engine
`0x56c0` walk. **The write path accepts genuinely new geometry, not just carried stock bytes.**

### 2.4 Does `Hi_RegisterSummonModel` / `model_prepare 0x7120` impose a PSX-address decode a re-emit must satisfy? — ANSWERED: only RELATIVE offsets, PROVEN satisfied

Read directly (`fn 0x7120 @0x7228-0x725e`):

```
0x7228  movzx eax,[rsi]      ; GEOM flags
0x722b  test al,1 ; jne …    ; bit0 set => already relocated, skip (idempotent)
0x7233  mov edx,[rsi+0xc]    ; pBoneTable — a GEOM-BLOCK-RELATIVE OFFSET (0x14 on disk)
0x723d  add rdx,rsi          ; + the GEOM block base  => host pointer
0x7248  call 0x12b00         ; pack host -> PSX address
0x7256  mov [rsi+0xc],eax    ; store the PSX address back, IN PLACE
0x724d  …repeat for [rsi+0x10] (pMeshTable)…
```

**On disk every GEOM-internal pointer is an offset relative to the block base; `0x7120` converts them in
place at first load.** Upstream, the id-5 handler (`@0x3e373`) synthesizes the header's PSX pointers at load —
`header+0x3c = psx(header+texOffset)` (@0x3e39c → `DATA+0x08`, the geom handle `Register` decodes),
`header+0x40 = psx(header+firstBlock)`, and `motion[k] += psx(header)` (@0x3e3c0) — so **`+0x3c/+0x40` are 0
on disk and the motion table holds header-relative offsets** (D3 §5.1).

⇒ A re-emitted blob must present **(a)** correct GEOM-block-relative sub-block offsets and **(b)** correct
header-relative `firstBlock`/`modelBytes`/`motion[]`. It must contain **no absolute PSX address** — all are
synthesized at load. Our writer emits exactly (a) [proven by the 24/24 byte-identity → identical relocation
behaviour] and the assembly recomputes (b) exactly [§2.2]. **Constraint satisfied, PROVEN.** There is one
additional in-place fixup a re-importer emits as offsets, not addresses: `DrawSummonModel@0x17785-0x177b4`
promotes each motion clip's `+0x0c`/`+0x10` from small offsets to packed addresses on first draw (M5 §2.1) —
carried verbatim from the donor motion, so it is a non-issue for a geometry-only swap.

---

## 3. THE CONSTRAINTS A TRANSPLANTED RIG MUST SATISFY (the hard part that remains)

The geometry format is writable; a *faithful* swap that keeps the donor's real animation still has to conform
our model to the donor's rig. These are cited, and a violation renders wrong **silently** (the failure mode is
the `"HIRAISHI ERROR:"` spin-forever hang, `0x151a0`, not an exception — M1 §3).

1. **Same bone COUNT, TOPOLOGY, and SEMANTICS as the donor.** The motion clip indexes bones by number
   (`RotKey[nodeCount]`, walked in index order — M5 §2/§4); `Hi_SetSummonMotion` (op 26) binds it; the pose
   builder reads `boneCount = u8[geom+0x02]`. Bahamut = **93 bones**. Crucially, because the clip stores only
   **local rotations** and the skeleton's **lengths + parenting live in the model**, reproducing the donor's
   animation faithfully requires carrying the donor's **skeleton** (bone lengths + parenting) and skinning our
   mesh so that **bone `k` drives the same body region** as in the donor. The run-length `vertsPerBone`
   assignment is that binding. This is the real transplant difficulty — and it is **identical for T1** (a
   bone-matrix-driven puppet must also pose our mesh by the donor's per-bone transforms, i.e. our mesh bound
   to the donor's bone semantics). Neither approach escapes it.
   * *Escape hatch:* re-author the motion (M5 is decoded + re-authorable, §10 there) against **our own**
     skeleton of any topology — but that **discards the donor's authored animation**, defeating "faithful."
2. **Mesh ordinals are load-bearing.** Ops 157/158 (`Hi_Show/HideSummonModelMesh`) address meshes by **bit
   index** in `SummonData+0x20` (FORMAT §3.4). Keep `meshCount` and ordering = donor (Bahamut = 2).
3. **≤ 6 material parts, ≤ 7000 verts/mesh, model image ≤ 0x50000, VRAM ≤ parts·0x4000 + clutRows·0x200.**
   Bahamut spends `0x26ad4` of `0x50000` — ample headroom.
4. **Textures (roadmap W3, LOW).** A visible custom creature needs its own id-4 texture pages (plain 64×128
   16bpp blocks at `id4.offset + texOffset`, exact size law) + CLUT, and per-face `part` indices. No code
   emission; specified 24/24 (D3 §5.2 / W3).
5. **The opaque fields at synthesis.** `geom+0x04`, `geom+0x08`, `listHead`, `MeshDesc+0x00`, and per-record
   junk: **none is read by the static parse (`0x7120`) or draw (`0x4eb0`/`0x56c0`) path**, and 0 passes the
   linter (§2.3). For a swap, the safe move is to **carry the donor's values** where present (`unknown0`,
   `listHead`) and 0 the per-record junk. In-game safety of the 0/synthesized case is **UNPROVEN** (resolves
   with W0 + one cast; see §5).

---

## 4. THE TWO EXTERNAL GATES (neither is the geometry)

1. **W0 — does a mod-folder `ef###.bytes` override even load?** Source-traced (D2 §1.3: `SFX.cs:1974-1979` →
   `AssetManager.cs:541-627,971-977`) to a predicted path `<modfolder>/FF9_Data/SpecialEffects/ef227` (no
   extension), but **never run**. This gates **all** native writing (T2 and every W-rung). It is a **$0,
   2-cast** experiment: (cast 1) drop a byte-identical copy → cinematic unchanged; (cast 2) flip one `WAIT`
   operand at file `0x400+` → pacing visibly changes. **If W0 fails, T2 is dead without an engine change** and
   T1 becomes the only faithful lane.
2. **Rig conformance** — §3.1. Shared with T1.

---

## 5. WRITABILITY VERDICT + EFFORT DELTA vs T1

**Writability of the id-5 model-image geometry: PROVEN round-trippable / PROVEN writable.** Not PLAUSIBLE, not
BLOCKED. Evidence: 24/24 creature blocks + 1005/1005 all blocks + 135,728/135,728 primitive records + the
full-image assembly with exact header-offset recomputation + a novel block passing every native structural
law + the relocation constraint read from the DLL and satisfied by construction.

### Effort delta — T2 vs T1

| axis | **T1** (bone-matrix-driven managed puppet) | **T2** (native model-image injection — this slice) |
|---|---|---|
| lanes used | **both PROVEN** — managed `SFXDataMesh` loose-FBX render (rung 7 in-game proven) + the s52/s53 probe reads | native container **write** — gated on the untested **W0** |
| geometry write | n/a | **PROVEN** (this slice) — was the feared W5 blocker, now closed |
| rig conformance to donor's 93-bone semantics | **required** (pose our mesh by the donor's per-bone transforms) | **required** (identical problem) — SHARED |
| per-frame runtime work | map PSX bone WORLD matrices → Unity world each frame; map the native PSX camera (`M`+OFX/OFY/H) → Unity (else use Unity's camera and lose the native frame) | **none** — the native pipeline draws + animates + shoots our mesh with zero mapping |
| textures | reuse our FBX materials (Unity shading) | author id-4 pages + CLUT (W3, LOW) |
| fidelity ceiling | MED — modern shading, 15fps sequence-tick sampling, coordinate/camera mapping error surface | **HIGHEST** — exact stock skeleton + motion + native PSX camera + per-mesh hide/ABR/texanim; *it is the creature* |
| external hard gate | none | **W0 loadability (binary unknown)** |
| net effort | **MED** | **MED–HIGH**, but the increment over T1 is **W0 + texture emit + one opaque-field cast** — **NOT the geometry** |

**Bottom line.** T2 is the strictly-higher-fidelity transplant — the native code does all the animation, the
staging, and the camera, which is exactly what every FLIGHT overlay iteration could never fake. Its remaining
cost over T1 is **not** the geometry format (proven writable here) but the **W0 loadability gate** (a $0
2-cast experiment that gates all native writing) plus texture emission (LOW) and one cast to clear the opaque
fields. **Recommendation: run W0 first.** If it passes, T2 is viable and dominant on fidelity; the geometry
writer, header math, and container writer are all in hand. If it fails, T2 requires an engine change and T1 is
the faithful fallback — and *either way* the rig-conformance work (§3.1) is shared and worth starting now.

---

## 6. DELIVERABLES + PROVENANCE

* **`ef_geom_writer.py`** (this directory) — committable GEOM-block writer + round-trip harness. Reads a
  caller-supplied blob, emits bytes for a caller-supplied `GeomModel`, embeds **zero** game bytes. CLI:
  `py ef_geom_writer.py <ef###.bytes>` prints per-creature MATCH.
* All round-trip evidence was produced against `C:/gd/SCRATCH/summon-format/` and this artifact records **only
  counts + MATCH/offsets** — no geometry, animation, texture, or container payload was echoed or committed.
* No DLL was modified or redistributed. Every native claim cites `fn@rva`; every managed claim `file:line`.
* **Hard line for the pipeline:** a stock creature's extracted geometry / skeleton / motion / textures / raw
  `ef###.bytes` stay under `C:/gd/SCRATCH/summon-transplant/` (local, gitignored) — the deliverable is the
  **writer + the conform pipeline** that puts the **user's own** model onto the locally-decoded motion, built
  from the user's own install into their own mod folder, exactly the verbatim-fork precedent. Never ship a
  patched `FF9SpecialEffectPlugin.dll`.
