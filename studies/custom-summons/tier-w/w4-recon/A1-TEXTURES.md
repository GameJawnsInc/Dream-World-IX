# A1 — THE TEXTURE SUBSTRATE: what a W4 reskin edits, and who else writes it

**TIER W rung 4 recon, strand A1.** Read-only. Nothing was written to the game install; every
stock-derived dump lives under `C:\gd\SCRATCH\summon-format\reskin-w4-recon\A1-*`. Everything below is
offsets, sizes, counts, field values and statistics — no payload bytes.

**Instruments.** `ef_container.py` (the sanctioned container parser), `refkit.py` (x64 DLL disassembly of
the user's own `FF9SpecialEffectPlugin.dll`), `tier_r_disasm.py` + `hle_ops.json` (the effect-program
walk), and the Memoria C# source at `C:/gd/FFIX/Memoria/Assembly-CSharp/`.
Every claim is tagged **[M]** measured (read out of the corpus or the instruction stream) or
**[I]** inferred.

---

## 0. HEADLINE — the four answers

1. **The reskin surface is 466,944 of ef227's 823,296 bytes (56.7%)** — 32 VRAM rects, every one
   fixed-size and same-length by construction. The creature is **8-bit CLUT-indexed** with a 1:1 part→palette map, so a
   palette recolor is **3,072 bytes** for the whole dragon. **[M]**
2. **THE SECOND WRITER IS NOT TEXANIM.** ef227 runs **no** texture animation: its two programs call
   neither op 11 nor op 12, its texanim region is **0 bytes long**, and — corpus-wide — **only 3 of the
   216 HLE ops can reach a VRAM-transfer command at all, and ef227 calls none of them.** **[M]**
3. **THE SECOND WRITER IS THE CHUNK-1 OVERWRITE.** Six VRAM page slots are written by **two different
   container regions** (chunk 0's streamed pages / id-9, then chunk 1's). Recolor one copy and the
   scenery changes look mid-cast. This is W4's exact analog of W3's reciprocal trap. **[M]**
4. **Nothing checksums, and the edit flows through hot per cast** — no magic, no version, no hash
   anywhere on the path; the payload reaches VRAM as a verbatim halfword copy. ⚠ but the decoded-texture
   cache is invalidated **by page uploads, not by CLUT uploads** — a CLUT edit lands only because the
   same cast re-uploads the pages. **[M]**

---

## 1. ef227's texture-class resources — both chunks

Container: 823,296 B (`0xc9000`), 2 chunks, walker cursor lands exactly on the length.

| chunk | res | id | info | file offset | bytes | what it is |
|---|---:|---:|---:|---|---:|---|
| 0 | 0 | 0 | 5 | `0x800` | `0x15000` | VRAM_IMAGE_LIST — 1 inline rect (the props' CLUT strip) + **5** streamed pages |
| 0 | 1 | 1 | 5 | `0x15800` | `0x14000` | VRAM_IMAGE_CONT — **5** streamed pages |
| 0 | 4 | 9 | 51 | `0x32000` | `0x18000` | VRAM_TEXPAGE_ALT — **6** pages (info is a slot bitmask, §4) |
| 0 | 5 | 4 | 0 | `0x4a000` | `0x19000` | VRAM_TEXPAGE — the **creature package**: header + 6 pages + 6 CLUT rows |
| 1 | 0 | 0 | 1 | `0xa2000` | `0x5000` | VRAM_IMAGE_LIST — 2 inline rects (props CLUTs) + **1** streamed page |
| 1 | 1..5 | 1 | 1 | `0xa7000`,`0xab000`,`0xaf000`,`0xb3000`,`0xb7000` | `0x4000` ea | VRAM_IMAGE_CONT — **1** page each |

**Byte budget of the reskin surface [M]:**

| surface | bytes | share |
|---|---:|---:|
| creature texture pages (6 × `0x4000`) | 98,304 | 11.9 % |
| **creature CLUT strip (6 × `0x200`)** | **3,072** | **0.37 %** |
| effect-owned scenery/prop pages (16 × `0x4000`, ids 0+1) | 262,144 | 31.8 % |
| id-9 alt pages (6 × `0x4000`) | 98,304 | 11.9 % |
| effect-owned prop CLUTs (3 inline rects) | 5,120 | 0.62 % |
| **total** | **466,944** | **56.7 %** |

Full rect-by-rect map: `A1-ef227-vram-writers.txt`.

---

## 2. The creature package (id 4) — the reskin's primary target

### 2.1 Layout **[M]**

Model header at `0x4a000` (the id-4 payload's first byte), `texOffset = 0x1a0 = 0x180 + 4*motionCount`:

```
0x4a000  model header (0x1a0 B): partCount=6  clutRows=6  texBytes=0x18000  clutBytes=0xc00
0x4a1a0  texture pages : 6 x 0x4000, part-ordered            (texBytes == partCount * 0x4000)
0x621a0  CLUT strip    : 6 x 0x200 = 6 rows x 256 entries    (clutBytes == clutRows  * 0x200)
0x62da0  (608 B sector pad, then the id-5 model image at 0x63000)
```

Per-part page offsets are `0x4a1a0 + i*0x4000`; per-part CLUT rows are `0x621a0 + i*0x200`.

### 2.2 Format — 8-bit indexed, one 256-entry palette per part **[M]**

| part | TPAGE | decoded | CLUT word | CLUT VRAM | vOffset | page VRAM rect |
|---:|---:|---|---:|---|---:|---|
| 0 | `0x0093` | xbase 192, ybase 256, ABR 0, **mode 1 = 8bpp-CLUT** | `0x3990` | (256, 230) | 128 | (192, 384, 64, 128) |
| 1 | `0x0093` | " | `0x39d0` | (256, 231) | 0 | (192, 256, 64, 128) |
| 2 | `0x0094` | xbase 256 | `0x3a10` | (256, 232) | 128 | (256, 384, 64, 128) |
| 3 | `0x0094` | " | `0x3a50` | (256, 233) | 0 | (256, 256, 64, 128) |
| 4 | `0x0095` | xbase 320 | `0x3a90` | (256, 234) | 128 | (320, 384, 64, 128) |
| 5 | `0x0095` | " | `0x3ad0` | (256, 235) | 0 | (320, 256, 64, 128) |

* TPAGE decode is the stock PSX field layout: `x = (t & 0xF) * 64`, `y = ((t >> 4) & 1) * 256`,
  `ABR = (t >> 5) & 3`, **`mode = (t >> 7) & 3`** (0 = 4bpp, 1 = 8bpp, 2 = 15bpp direct).
  CLUT decode: `x = (c & 0x3F) * 16`, `y = (c >> 6) & 0x1FF`.
* The rect is **64 halfwords wide × 128 rows** = `0x4000` bytes. At 8bpp that is a **128 × 128 texel page
  of byte indices**. Texel statistics confirm the domain: 5 of the 6 pages use **all 256** distinct index
  values, the sixth uses 251.
* **`part i` ⇄ `CLUT row i`, exactly.** The strip uploads as one rect `(x=256, y=230, w=256, h=clutRows)`
  row-major from `header+texOffset+texBytes`, so source row *i* lands at VRAM y `230+i` — and part *i*'s
  CLUT word names y `230+i`. Verified **24/24** creature packages.
* **CLUT entry = PSX 16-bit `STP | B5 G5 R5`.** Per row: 256 entries, 172–253 distinct, exactly **1**
  all-zero entry (index 0 = the transparent texel), and the **STP bit set on 255 of 256** entries. The
  five-bit channels never exceed 28 of 31 — the stock art leaves headroom, which a brightening recolor
  can spend without clipping. **[M]** (STP semantics is standard PSX. **[I]**)

### 2.3 The whole-corpus shape **[M]** — `A1-corpus-census.txt`

All 24 creature packages, no exceptions:

* `partCount == clutRows` — 24/24
* `texBytes == partCount * 0x4000` — 24/24 · `clutBytes == clutRows * 0x200` — 24/24
* **every part's tpage colour-mode == 1 (8bpp)** — 24/24. There is no 4bpp creature.
* part *i*'s CLUT at VRAM `(256, 0xe6+i)` — 24/24; the `partCount` page rects are all distinct — 24/24
* the page rects walk one fixed ladder in part order:
  `(192,384) (192,256) (256,384) (256,256) (320,384) (320,256)`, truncated to `partCount`
* `partCount ∈ {1, 3, 4, 5, 6}`: 6 → ef211 225 **227** 251 261 381 447 · 5 → ef038 179 184 186 276 ·
  4 → ef210 226 · 3 → ef177 493 494 495 · 1 → ef431 432 435 438 439 498

**⇒ one W4 creature-recolor tool generalises to all 24 stock summons with no per-effect special-casing.**

### 2.4 The upload path **[M]**

`fn 0x3de37` state 5, id-4 arm at **`0x3e272`**:

1. resolves the staged payload (`PsxCtx`-relative, `fn 0x10e0`),
2. **CLUT first** — one host callback `0x64000000` with rect `(0x100, 0xe6, 256, clutRows)`
   (`mov dword [rsp+0x60], 0xe60100` @`0x3e286`; source `header + texOffset + texBytes`, `+8` field),
3. **then the per-part page loop** @`0x3e302`–`0x3e36c` — one `0x64000000` per part, rect computed from
   TPAGE/vOffset exactly as §2.2, source advancing `0x4000` per part (`add rsi, 0x4000` @`0x3e354`).

The host callback is `qword [0x1C1DE8]`; command `0x64000000` = code 100 = **`PSXTextureMgr.LoadImage`**
(`SFXData.cs:643`, `:1119`).

---

## 3. The effect's own set (ids 0 / 1) — scenery and prop textures

### 3.1 The id-0 payload header, read out of `fn 0x3e01c` **[M]**

`ef_container`'s note ("`{u16 x,y,w,h}` records + 16bpp pixels") is right about the record but wrong about
where it starts. The native walk is:

```
id-0 payload P:
  P+0x00  s32 pageBlockRel     -> the streamed-page descriptor
  P+0x04  s32 rectTableRel     -> the INLINE rect stream
  P+0x08  s32 rectCount
  P+rectTableRel : rectCount x { u16 x, u16 y, u16 w, u16 h ; then w*h halfwords, packed }
  P+pageBlockRel+0x00 : s32 pixRel  -> P+pixRel = the base of the 0x4000-page stream
  P+pageBlockRel+0x08 : 8-byte page records { u16 x, u16 y, u16 w, u16 h }
```

Read at `0x3e037` (`rbx = P + s32[P+4]`, `eax = s32[P+8]`, `rbp = s32[P]`), the inline loop
`0x3e050`–`0x3e0bf` (callback per rect, then `rbx += 2*w*h`), and the tail `0x3e0c1`–`0x3e109` which
publishes `psx(P + s32[P+pageBlockRel])` to `0x32323C` and `psx(P + pageBlockRel + 8)` to `0x323234`
before calling the streamer.

### 3.2 The page streamer `fn 0x3dc50` **[M]**

Uploads **`info` pages per tick** — the loop count is `byte[0x323207]`, the current resource's `info`
byte (`@0x3dc59`; the same byte gates id-9 `@0x3df46` and `@0x3e500`) — each forced to `64 × 128`
(`mov dword [rbx+4], 0x800040` @`0x3dc6b`).
It walks the 8-byte record list at `[0x323234]` with a counter at `[0x323238]`: first use → `(rec.x,
rec.y)`; second use → `(rec.x, rec.y + 128)`; the record advances after the second use, or after the
first if `rec.h == 128`. So **a record with `h == 256` yields two stacked pages**.
`id-1` (`fn 0x3e11a`) is a pure continuation: it re-resolves `[0x32323C]` and calls the same streamer —
it carries **no header of its own**, only raw page bytes.

### 3.3 ★ THE `info` BYTE — closed, 738/738 **[M]**

FORMAT §4.5 item 7 listed "the `info` byte for ids 0/1/9" as unread. It is the **page count**:

| id | law | corpus |
|---|---|---|
| 0 | `nbytes == info*0x4000 + a small header region` | **385/385** |
| 1 | `nbytes == info*0x4000` exactly | **316/316** |
| 9 | `info` is a **slot bitmask** (§4); `nbytes == enabledSlots*0x4000` | **37/37** |

And the record list closes against it exactly: ef227 chunk 0 → 5 records × 2 halves = **10** pages =
id-0's 5 + id-1's 5; chunk 1 → 3 records × 2 = **6** pages = 1 + 5×1.

### 3.4 What the inline rects are **[M]**

| chunk | rect | bytes | file offset |
|---|---|---:|---|
| 0 | `(x=0, y=244, w=256, h=6)` | 3,072 | `0x870` |
| 1 | `(x=0, y=242, w=256, h=2)` | 1,024 | `0xa2048` |
| 1 | `(x=0, y=250, w=256, h=2)` | 1,024 | `0xa2450` |

These are **the props' CLUT band** — same geography as the creature's strip (a 256-wide band at y < 256),
and **confirmed by the bindings**: every `so` block found in ef227 (§3.5) names a CLUT at
`(x ∈ {0,192}, y ∈ 244..251)`, i.e. inside these three rects. **5,120 bytes total** — the scenery's whole
palette lever.

### 3.5 The props' bindings — the `so` blocks, and their bit depth **[M]**

`op 206` (native `fn 0x47290`, 15 call sites in ef227) asserts a **`0x6f73` (`'so'`) magic**, then ORs
`(arg2 & 3) << 5` — **the PSX TPAGE ABR field** — into the u16 at `+8 + 4*i` for `i < (u16[+4] - 8)/8`.
So the operand is a texture-binding table of `{u16 tpage, u16 clut}` pairs and **op 206 is a
semi-transparency setter, not a palette writer** (§5.3).

Scanning ef227 for that shape found **11 blocks**, all single-entry, living in the id-2 sub-file archives
and in **id-6 (`MARK_6`)** — the scenery geometry named by THE EFFECT-OWNED SCENERY LAW:

* page bases: x ∈ {448, 512, 576, 704, 832}, ybase 256 — exactly the streamed-page slots of §3.2
* CLUTs: `(0, 244..251)` and `(192, 244)` — exactly the inline rects of §3.4
* colour modes: **5 × 8bpp-CLUT, 5 × 4bpp-CLUT, 1 × 15bpp-direct**

**⚠ The effect's own set is NOT uniformly 8bpp.** Unlike the creature, the scenery mixes 4bpp
(16-entry palettes packed 16-to-a-row), 8bpp (256-entry rows) and direct-colour pages. A scenery recolor
must be driven **from the `so` bindings**, not from a "one row = one palette" assumption.
(The scan is a shape filter, not a proof of completeness — 11 blocks vs 15 op-206 call sites. **[I]**
that the rest are the same shape.)

---

## 4. id 9 — the alternate page path **[M]**

`fn 0x3e4ab`. Eight candidate slots, gated by the `info` bitmask (`test byte [0x323207], bpl`):
slots 0,1 → bit 0 · slots 2,3 → bit 1 · slot 4 → bit 2 · 5 → bit 3 · 6 → bit 4 · 7 → bit 5.
VRAM placement, from the code: `s < 4 → x = ((s & ~1) + 0x18) << 5` else
`x = (((s << 5) - 0x61) & 0xFFC0) + 0x140`; `y = ((s & 1) + 2) * 128`; always `64 × 128`.

ef227: `info = 51 = 0b110011` → slots **0,1,2,3,6,7** = 6 pages = `0x18000` bytes ✓, landing at
`(768,256) (768,384) (832,256) (832,384) (384,256) (384,384)`.
Source is the staged payload at `0x32000`, advancing `0x4000` per enabled slot.

**No id-9 page overlaps the creature** (creature x ∈ 192..383; id-9 x ∈ 384..447, 768..895).

---

## 5. THE SECOND-WRITER QUESTION

### 5.1 Texture animation — ef227 does not run it **[M]**

* **The machinery exists and is tiny.** `Hi_StartSummonTexAnim` (`fn 0x188a0`, HLE op 12) and
  `Hi_StopSummonTexAnim` (`fn 0x18930`, op 11) index `SummonData+0x70` — the texanim table — with
  **stride `0x18` by part**: start sets `byte[+8] |= 3` (or `|= 1` when `flag == 0`), zeroes
  `dword[+0x10]` and writes `0x1000` to `word[+0x16]`; stop does `byte[+8] &= 0xFC`.
* **`SummonData+0x70` has exactly three consumers image-wide**: `fn 0x7120` zeroes it at prepare time
  (`@0x71ff`), `Hi_RegisterSummonModel` fills it from `model[+0x40]` (`@0x160f5`), and ops 11/12 above.
  **No DLL code steps it.** So texanim is *armed* by the effect program and, if it advances at all, does
  so through machinery not on the summon-record path.
* **ef227's own op census** (reachability walk of both programs: `c0` 3,019 instrs / 156 HLE call sites /
  29 distinct ops, `c1` 4,262 / 285 / 39 — 42 distinct in the union): **op 11 absent, op 12 absent.**
  `A1-op-census.txt`.
* **Corpus census, 372 containers / 385 programs**: op 11 → **0 call sites**. op 12 → **2 call sites, in
  exactly one effect: `ef038` (chunk 0, parts 0 and 1, flag 0).**
* **ef227's texanim region is 0 bytes long.** `firstBlock` (the region's start) and the first motion clip
  both resolve to file `0x7579c`. Across the 24 creature packages: **19 have a 0-byte region**; the 5
  that do not are `ef038` (116 B) and `ef177 / ef493 / ef494 / ef495` (364 B each) — and `ef038` is
  precisely the one effect that calls op 12. The correlation is perfect.
* The table's internal format stays **UNREAD** (FORMAT lists it OPAQUE; the region sizes do not divide by
  `partCount * 0x18`, so it is not a bare record array). **It does not gate W4** — ef227 has none.

> **VERDICT: a static recolor of ef227 cannot be flickered or reverted by texture animation. There is no
> texanim source data to co-transform.** A W4 tool that generalises must still **refuse or warn** on
> `ef038` / `ef177` / `ef493-495` until the table is read.

### 5.2 No effect program can rewrite VRAM in ef227 **[M]**

Built the direct-call graph over all 646 `.pdata` functions and asked which HLE handlers reach a
VRAM-transfer command word:

| command | code | meaning | issuing functions |
|---|---:|---|---|
| `0x64000000` | 100 | **LoadImage** (CPU → VRAM) | `0x2cd0`, `0x31060`, `0x312d0`, `0x315f1`, `0x3dc85`, `0x3de37` |
| `0x65000000` | 101 | StoreImage (VRAM → CPU) | `0x2d20`, `0x31d31`, `0x31f03` |
| `0x66000000` | 102 | **MoveImage** (VRAM → VRAM) | `0x2fe0` |

**Only 3 of the 216 HLE ops reach any of them**: op 0 → `0x2cd0` (LoadImage), op 1 → `0x2d20`
(StoreImage), op 166 → `0x2fe0` (MoveImage). **ef227 calls none of the three.**

The one *loader-script* opcode that can upload is **`0x07`** (its handler `0x318a2` owns the
`0x64000000` at `0x3193e`). **ef227's 93-op sequence does not use `0x07`** (only 9 of 372 containers do).

**⇒ during a Bahamut cast, every VRAM write comes from the resource state machine (`0x3de37` / the
streamer `0x3dc50`) — i.e. from container bytes, once each, at load/stream time.**

### 5.3 What ef227's program *does* mutate, and why it is harmless to a recolor **[M]**

* **op 206 (×15)** — ORs an ABR (semi-transparency) mode into every tpage word of an `so` binding table
  (§3.5). It never touches the CLUT word, the page base, the colour-mode bits, or any texel. A recolor is
  orthogonal; it does mean the **blend mode of the props is program state, not container state**.
* **op 65 `Hi_ModifySummonModelRGB` (×5)** — a per-frame RGB modulation on the creature's primitives
  (`SummonData+0xa0/+0xa4`, seeded at `fn 0x7120` `@0x720a`). It **multiplies over** the palette, so a
  CLUT recolor composes with it rather than being overwritten. **[I]** on the exact blend; **[M]** that
  it is a record field, not a texture write.
* **op 155 `Hi_ModifyEffModelRGB` (×14)** — the same for the eff-model props.

### 5.4 ★ THE REAL SECOND WRITER — the chunk-1 overwrite **[M]**

Six VRAM page slots receive bytes from **two different places in the container**:

| VRAM slot | writer A | writer B |
|---|---|---|
| (576, 256) 64×128 | c0 id-1 res1 page1 @`0x19800` | c1 id-0 res0 page0 @`0xa2850` |
| (576, 384) | c0 id-1 res1 page2 @`0x1d800` | c1 id-1 res1 page0 @`0xa7000` |
| (640, 256) | c0 id-1 res1 page3 @`0x21800` | c1 id-1 res2 page0 @`0xab000` |
| (640, 384) | c0 id-1 res1 page4 @`0x25800` | c1 id-1 res3 page0 @`0xaf000` |
| (832, 256) | c0 **id-9 slot2** @`0x3a000` | c1 id-1 res4 page0 @`0xb3000` |
| (832, 384) | c0 **id-9 slot3** @`0x3e000` | c1 id-1 res5 page0 @`0xb7000` |

The two chunks stream at different sequence ticks (`LOAD_CHUNK` appears twice in ef227's script), so the
content of those six slots **changes mid-cast**. Recolor only chunk 0's copy and the scenery reverts to
stock colour partway through; recolor only chunk 1's and the first half stays stock.

> **THE W4 CO-TRANSFORM LAW (proposed): a reskin is per-VRAM-SLOT, not per-resource. Every container
> region that writes a slot must be transformed with the same map, or the look changes when the chunk
> boundary passes.** This is the texture analog of W3's "all four clocks move together".
>
> **The creature is exempt** — its 6 pages and its CLUT strip are written by chunk 0's id-4 and by
> nothing else. Lever #1 (creature palette recolor) has **exactly one writer**.

---

## 6. Integrity, caching, and same-length-ness

### 6.1 No checksum anywhere on the path **[M]**

* The container has **no magic number, no version field, no checksum** — its only self-check is
  structural (the walker's cursor must equal the file length; 372/372).
* The load pass memcpy's the payload to its destination and the interpret pass hands the staged pointer
  straight to the host callback. **No transform is applied to texel or CLUT bytes.** The one documented
  in-place load-time mutation on the model path is the **UV V-offset bake** (`0x7514`/`0x75b7`/`0x7667`/
  `0x771b`) — it rewrites *UV indices*, never texels or palettes.
* Managed side: `PSXTextureMgr.LoadImage(x,y,w,h,p)` is a **verbatim halfword copy** into
  `originalVram[1024*512]` — no decode, no hash, no substitution.

### 6.2 The cache, and the one trap in it **[M]**

There **is** a decoded-texture cache: `PSXTextureMgr.list[SST_MAX_TEXTURE]`, keyed by
`SFXKey.GenerateKey(TP, TX, TY, clutX, clutY)` = `0x8000 | clutX(6) | clutY(9)<<6 | TX(4)<<16 |
TY(1)<<20 | TP(2)<<21` — i.e. **the full binding, including the palette coordinates**.

`LoadImage` calls `ClearKey(x, y)` first, which does `x >>= 6; y >>= 8` and invalidates every cache entry
whose **page** matches.

> ⚠ **A CLUT upload lands on page `(4, 0)`; the creature's texture pages are `(3,1) (4,1) (5,1)`. So the
> CLUT upload does NOT invalidate the decoded textures that use it.** The recolor lands anyway because
> the *same* id-4 arm re-uploads all six pages right after the CLUT (§2.4), and each page upload
> invalidates its own page. **Correct, but for a reason one step removed** — a future engine change that
> skipped redundant page uploads would silently strand a CLUT-only edit. State this in the W4 build.

Beyond the cache there is no staleness: `SFX.Play` re-reads the container per cast through
`AssetManager.LoadBytes("SpecialEffects/ef227")` with **no cache** (W2 §5), and `SFXDataMesh.Load()` runs
the full native load pass with `BattleCallbackDummyLoadImages = true` (`SFXDataMesh.cs:514,601`), so the
uploads happen **every cast**. Same hot, silent-fallback, no-relaunch posture W2/W3 already proved.

### 6.3 Same-length by construction **[M]**

Every editable region has a size the format states or derives — nothing is length-prefixed by content:

| region | size law | fixed? |
|---|---|---|
| creature page *i* | `0x4000` | yes |
| creature CLUT row *i* | `0x200` (256 × u16) | yes |
| id-0 inline rect *k* | `w*h*2`, with `w,h` in the record | yes, if the rect header is untouched |
| streamed page (ids 0/1) | `0x4000`, count = `info` | yes |
| id-9 page | `0x4000`, count = popcount-of-slots(`info`) | yes |

A palette or texel edit therefore never moves the resource table, never changes a sector count, and never
disturbs the walker's cursor-equals-length invariant. **The W2/W3 drift-guard + same-length-splice
posture transfers unchanged.**

### 6.4 One managed side-door worth knowing about **[M]**

`PSXTextureMgr` already contains a **hardcoded managed texture-substitution lane** for **effect 435**:
`eff435Tex[]` / `eff435Key[]` bind loose PNGs (`SpecialEffects/ef435/Background0.png`, …) to specific
`SFXKey`s (`PSXTextureMgr.cs:295-340`). That is proof that a full-resolution repaint lane is mechanically
available — but it is **id-specific engine code**, not data, so it is **out of scope for W4's stock-bytes-
untouched gate**. Recording it as a known lever #3, deliberately not taken.

---

## 7. Census bonus — will the W4 tool generalise?

| axis | answer |
|---|---|
| creature packages | **Fully uniform, 24/24** (§2.3). One tool, no special cases. |
| creature palette recolor | Uniform: `partCount` pages ⇄ `partCount` 256-entry rows, 8bpp, 1:1. |
| texanim exposure | **19/24 have no texanim region at all**; 5 do (`ef038 177 493 494 495`), and only `ef038` arms it. Gate the tool on `firstBlock == min(motionOffsets)`. |
| effect-owned set (ids 0/1) | Uniform *mechanism* (`info` = page count, 385/385 + 316/316), non-uniform *content*: mixed 4/8/15-bpp bindings per effect. Needs the `so`-binding drive. |
| id-9 | Present in 28 of 372 files (37 resources); the bitmask law holds 37/37. |
| coverage | id-0 in **372/372** files, id-1 in 236, id-4 in 24, id-9 in 28. |
| multi-writer slots | ef227 has 6. **Any multi-chunk effect can have them** — the W4 build must compute the VRAM-slot → writers map per effect and refuse a partial recolor. |

---

## 8. What A1 did NOT settle

1. **The texanim table's internal format** — still OPAQUE. Region sizes (116 B for 5 parts, 364 B for 3)
   do not divide by `partCount * 0x18`, so it is not a bare record array; ops 11/12 index at stride `0x18`
   from the base. Not needed for ef227. Settle it only if W4 targets `ef038` or `ef177/493-495`.
2. **Who *steps* a running texanim.** No DLL code reads `SummonData+0x70` besides ops 11/12, so if
   `ef038`'s animation advances, it advances somewhere this scan did not look (most likely the effect
   program's own MIPS stores into PSX RAM). **[I]**
3. **Completeness of the `so`-block scan** — 11 blocks found by shape vs 15 op-206 call sites in ef227.
   The prop bindings are almost certainly reachable exactly via op 206's `$a0`, which the R2 argument
   tracker can resolve; that is the clean way to enumerate them.
4. **Whether the id-1 continuation truly re-resolves the same PSX address into a re-staged buffer.**
   The counting closes exactly (10 = 5+5, 6 = 1+5×1), so the *effect* is settled; the pointer mechanics
   are **[I]**.
5. **The props' per-slot bit depth is per-binding, not per-page** — a page can in principle be addressed
   at two depths. Not observed, not excluded.

---

## 9. Files

Dumps (SCRATCH, stock-derived): `C:\gd\SCRATCH\summon-format\reskin-w4-recon\`
`A1-ef227-container.txt` · `A1-ef227-textures.txt` · `A1-ef227-vram.txt` ·
`A1-ef227-vram-writers.txt` · `A1-ef227-so-blocks.txt` · `A1-op-census.txt` · `A1-corpus-census.txt`
