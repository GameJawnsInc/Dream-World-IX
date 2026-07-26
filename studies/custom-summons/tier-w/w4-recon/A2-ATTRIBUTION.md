# A2 — THE ATTRIBUTION MAP (ef227 / Bahamut)

> **Recon for W4, THE RESKIN.** Read-only. No game file was written; every stock-derived dump lives
> under `C:\gd\SCRATCH\summon-format\reskin-w4-recon\A2-*`. This report carries offsets, lengths,
> field names, counts, VRAM coordinates and decoded aggregate colours — no stock byte runs.
>
> **Bottom line for the design:** *the creature and the effect's own scenery are texture-disjoint.*
> They share **no texture page, no CLUT, and not one VRAM halfword**. A creature-only recolour is a
> **single contiguous 3,072-byte span** of the container. Lever #1 (CLUT recolour) is not just viable,
> it is unusually clean.

---

## 0. Method, and what is MEASURED vs INFERRED

Everything below was computed from the user's own extracted `ef227.bytes` (823,296 B) with
`ef_container.py`'s validated walker plus three new decodes derived this round (§2). Scripts are
staged at `C:\gd\SCRATCH\summon-format\reskin-w4-recon\a2_*.py`.

| claim class | how it was established |
|---|---|
| **MEASURED** | read directly out of the container and cross-checked by a structural identity that would fail if the field interpretation were wrong (offset chains landing exactly, corpus-wide invariants, visual decode) |
| **DISASSEMBLED** | read out of `FF9SpecialEffectPlugin.dll` at a cited RVA (read-only static analysis, the FORMAT-round posture) |
| **INFERRED** | a stated hypothesis with its falsification named |

Two calibration checks were run before any verdict was trusted, because uncalibrated instruments have
produced confident wrong answers in this arc:

1. **The visual check.** All six creature pages were decoded through their CLUTs and rendered
   (`A2-creature-pages.png`). They are unmistakably Bahamut (§5). A wrong page/CLUT/bpp/stride
   assumption cannot produce a coherent dragon atlas.
2. **The corpus check.** The new `so` record decode was swept over all 372 stock effects
   (`A2-so-record-corpus.txt`): 340 textured records, **340/340** agree between the tpage's colour-depth
   field and the presence of a CLUT word, **340/340** have ABR 0 and page-Y base 256. Zero exceptions.

**Independent agreement with A1.** A1 derived the id-0 header layout, the creature package binding and
— crucially — the same id-9 slot map `{0,1,2,3,6,7}` by a different route (the `info` byte as an enable
mask) than A2's (empirical seam continuity + the loop's own slot arithmetic). Two derivations, one
answer. One disagreement is recorded in §8.

---

## 1. The set, enumerated

ef227 chunk 0 is the creature + the aerial set; chunk 1 is the impact/fire set.

| resource | file span | what it actually is |
|---|---|---|
| c0 id-0 + id-1 | `0x000800..0x029800` | **one continuous VRAM upload stream**: 1 CLUT image (6 rows) + 5 texture pages |
| c0 id-2 | `0x029800..0x02d000` | sub-file archive: 30 entries — 2 models, the camera blocks, AKAO sound sub-files |
| c0 id-3 | `0x02d000..0x032000` | the MIPS effect program (chunk 0) |
| c0 id-9 | `0x032000..0x04a000` | **6 alt texture blocks**, 64×128 each |
| c0 id-4 | `0x04a000..0x063000` | model package header + **the creature's 6 pages** + **the creature's 6 CLUTs** |
| c0 id-5 | `0x063000..0x08a000` | `SUMMON_MODEL` — Bahamut (93 bones / 2 meshes / 1439 verts / 2416 faces) |
| c0 id-6 `MARK_6` | `0x08a000..0x090800` | sub-file archive: **8 entries, 6 of them models** — the aerial scenery |
| c0 id-7 ×2 | `0x090800..0x0a2000` | **AKAO audio banks — NOT geometry** (see §8, correction) |
| c1 id-0 + id-1 ×5 | `0x0a2000..0x0bb000` | VRAM upload stream: 2 CLUT images (2 rows each) + 3 texture pages |
| c1 id-2 | `0x0bb000..0x0c4000` | sub-file archive: 54 entries — **7 models** + sound |
| c1 id-3 | `0x0c4000..0x0c9000` | the MIPS effect program (chunk 1) |

**16 GEOM blocks total** (MEASURED, `ef_container.scan_geom`): 1 creature + 15 effect models, of which
**11 are textured** and 4 are Gouraud/flat-only (no tpage, no CLUT — not reskin targets).

---

## 2. Three format decodes this round needed (all new, all corpus- or chain-validated)

### 2.1 The `so` record — where a non-creature model's tpage/CLUT lives — MEASURED

The creature gets its texture binding from the model-package header (`ef_container.ModelPackage`,
already decoded). **Effect models get theirs from a 16-byte record that immediately precedes their
GEOM block**, at the head of their sub-file. It was not previously described.

```
so_record                       // at subFileStart; GEOM begins at subFileStart + geomOff
 +0x00 u16 magic     == 0x6F73  ('so')
 +0x02 u16 textured  1 = tpage/clut present, 0 = untextured
 +0x04 u16 geomOff   0x10 when textured, 0x08 when not  -- record base -> GEOM base
 +0x06 u16 OPAQUE    0x0C when textured, 0x08 when not   (340/376 and 36/376, no other value)
 +0x08 u16 tpage     PSX tpage word (textured only)
 +0x0a u16 clut      PSX CLUT word; 0 when the tpage says 15bpp direct colour
 +0x0c u16 OPAQUE    {0, 0x10, 0x20, 0x40, 0x80}
 +0x0e u16 OPAQUE    {0, 0x80}
```

`tpage`: bits0-3 = X base / 64 · bit4 = Y base / 256 · bits5-6 = ABR · bits7-8 = colour depth
(0 = 4bpp, 1 = 8bpp, 2 = 15bpp direct). `clut`: bits0-5 = X / 16 · bits6-14 = Y. Both are the standard
PSX GPU encodings, and bits0-4 of `tpage` are already confirmed by the DLL in
`ef_container.vram_rect` (`(tpage & 0x0F) * 64`, `((tpage & 0x10) << 4)`).

**Corpus validation** (`A2-so-record-corpus.txt`, all 372 files / 1005 GEOM blocks):

| check | result |
|---|---|
| creature blocks (GEOM at id-5 offset 0) | 24 — no `so` record by construction |
| non-creature blocks **with** a `so` record | **376** |
| non-creature blocks **without** one | 605 — reached another way (see §9 OPEN-2) |
| record length histogram | `{0x10: 340, 0x08: 36}` — exactly two shapes |
| `+0x02` textured flag vs record length | `{1: 339, 0: 37}` — 1 mismatch corpus-wide |
| **tpage colour-depth ↔ CLUT presence** | **340 consistent / 0 inconsistent** |
| tpage ABR | **0 in 340/340** |
| tpage Y base | **256 in 340/340** |
| colour-depth histogram | 4bpp 113 · 8bpp 203 · 15bpp 24 |

**For ef227 specifically the coverage is complete: 15/15 non-creature GEOM blocks carry a `so` record.**
Nothing about this target's texture binding is guesswork.

### 2.2 The id-0 / id-1 VRAM upload stream — MEASURED (offset chain closes exactly)

`RESOURCE_IDS[0]`'s "`{u16 x,y,w,h}` records + 16bpp pixels" is right in spirit but has a real header:

```
+0x00 u32 pageBlockRel   -> { u32 pixelDataRel, u32 nPageRects, Rect[nPageRects] }
+0x04 u32 inlineRel      -> nInline x { Rect, u16 pixels[w*h] }   (the CLUT images)
+0x08 u32 nInline
+0x0c u16 nClut4         count of 16-entry CLUT words that follow
+0x0e u16 nClut8         count of 256-entry CLUT words that follow
+0x10 u16 clutWord[nClut4 + nClut8]
Rect = { u16 x, u16 y, u16 w, u16 h }   in 16bpp VRAM halfwords
```

The **id-1 `VRAM_IMAGE_CONT` resources are not separate headers** — the pixel stream simply runs past the
id-0 payload boundary into them, and because resources are sector-contiguous in the file the stream is
linear. (A1's naive per-resource rect decode of id-1 produced `[OVERRUN]` on exactly these resources;
that is the same fact seen from the other side.)

**Self-check, and it is exact in both chunks:** the inline CLUT-image blocks end at the byte
`pixelDataRel` names. c0: `0x68 + 8 + 0xC00 == 0xC70` ✓. c1: `0x40 + (8+0x400) + (8+0x400) == 0x850` ✓.
Then `pixelDataRel + Σ(w·h·2)` lands inside the combined id-0+id-1 payload in both chunks.

### 2.3 id-9 `VRAM_TEXPAGE_ALT` — DISASSEMBLED + empirically confirmed

`fn 0x3E4AB` (the id-9 interpret arm) is an **8-slot** loop (`cmp esi, 8` @`0x3e5bf`) uploading fixed
**64×128** blocks (`r13d = 0x40` @`0x3e4d7`, `r14d = r13 + 0x40` @`0x3e4ee`), each slot gated by a mask
bit and the payload cursor advancing `0x4000` only on an uploaded slot (`add r15, 0x4000` @`0x3e5a9`).
Destination arithmetic, read at `0x3e50d..0x3e553`:

```
y = ((i & 1) + 2) * 128                                   ; 256 for even i, 384 for odd
x = ((i & ~1) + 24) * 32                     if i < 4     ; 768, 768, 832, 832
x = ((( i << 5) - 0x61) & 0xFFC0) + 0x140    if i >= 4    ; 320, 320, 384, 384
```

**The enable mask is the resource's own `info` byte** (INFERRED, and A1 reached it independently):
`info = 51 = 0b110011` with the loop's bit-advance pattern (one bit shared by slots 0/1, one by 2/3,
then one bit each) enables slots **{0, 1, 2, 3, 6, 7}** — exactly six, matching the six 0x4000 blocks in
the `0x18000`-byte payload.

⇒ **id-9 payload block *k* → VRAM (768,256), (768,384), (832,256), (832,384), (384,256), (384,384).**

**Two independent empirical confirmations** (this is why it is safe to build on):

* **Slots 0/1.** The `MARK_6` sky-dome model reads an 8bpp page spanning VRAM halfwords 704–831, but
  chunk 0's own page list only covers 704–767. Placing id-9 blocks 0 and 1 at (768,256)/(768,384)
  makes the rendered sky **seamless across the join** (`A2-sky-with-id9.png`). A wrong placement
  produces a visible discontinuity; there is none.
* **Slots 2/3.** The `MARK_6` model at tpage X=832 renders as coherent grey cloud sheet from id-9
  blocks 2/3, and as incoherent noise from the only other candidate (chunk 1's page at the same X) —
  `A2-id9-slots.png`, tiles 1 vs 2.

Note the **load order**: id-9 sits *before* id-4 in chunk 0's resource table, so even if the slot map
were wrong about slots 4/5, the creature's own id-4 upload lands last and wins. The creature's texels
are not at risk from id-9 in any reading.

---

## 3. THE ATTRIBUTION MAP

### 3.1 The creature — 6 parts, 1:1 with page and CLUT, no sharing at all

All six parts are **8bpp indexed, 128×128 texels, one 256-entry CLUT each**. Every part's UVs span
`U[1,127] V[0,127]`, i.e. each part uses **100 % of its own page block and nothing outside it**. The
`vOffset` bake (`0x7514`/`0x75b7`/`0x7667`/`0x771b`) selects which 128-row half of the page column the
part occupies; on disk the UVs are pre-bake.

| part | faces | mesh | tpage | VRAM page rect | **page file** | CLUT VRAM | **CLUT file** |
|---:|---:|---|---|---|---|---|---|
| 0 | 468 | 1 | `0x093` X=192 | (192, 384, 64, 128) | `0x04A1A0..0x04E1A0` | (256, 230) | `0x0621A0..0x0623A0` |
| 1 | 350 | 1 | `0x093` X=192 | (192, 256, 64, 128) | `0x04E1A0..0x0521A0` | (256, 231) | `0x0623A0..0x0625A0` |
| 2 | 512 | 0,1 | `0x094` X=256 | (256, 384, 64, 128) | `0x0521A0..0x0561A0` | (256, 232) | `0x0625A0..0x0627A0` |
| 3 | 396 | 0 | `0x094` X=256 | (256, 256, 64, 128) | `0x0561A0..0x05A1A0` | (256, 233) | `0x0627A0..0x0629A0` |
| 4 | 397 | 0 | `0x095` X=320 | (320, 384, 64, 128) | `0x05A1A0..0x05E1A0` | (256, 234) | `0x0629A0..0x062BA0` |
| 5 | 293 | 0 | `0x095` X=320 | (320, 256, 64, 128) | `0x05E1A0..0x0621A0` | (256, 235) | `0x062BA0..0x062DA0` |

Faces sum to **2416** = the GEOM's own face count ✓. Every face in both meshes carries a `part` byte in
0..5 — there are no out-of-range parts in ef227 (the 6-of-24 exception FORMAT §2.3 warns about does not
apply here).

**Palette liveness** (bounds what a recolour must touch): 1,536 CLUT entries total; **1,525 are live**
(referenced by at least one texel and not the fully-transparent `0x0000` entry). Each part's CLUT holds
exactly one `0x0000` entry — the transparent slot a recolour must preserve. Parts 0,1,2,4,5 use all 256
indices; part 3 uses 251. The six CLUT rows are **byte-distinct** — there is no shared palette to
exploit; a coherent creature recolour is six independent 512-byte transforms.

### 3.2 The effect's own set — 11 textured models

| GEOM | sub-file home | v/f | buckets | tpage → VRAM X, bpp | CLUT VRAM | **CLUT file** | what it renders |
|---|---|---|---|---|---|---|---|
| `0x029E14` | c0 id-2 sub[7] | 81/76 | FT4·64 FT3·4 F3·8 | `0x099` X=576 8bpp | (0, 249) | `0x001270..0x001470` | **the aerial ground plane** (satellite terrain) |
| `0x02BA28` | c0 id-2 sub[11] | 48/24 | FT4·24 | `0x019` X=576 4bpp | (0, 244) | `0x000870..0x000890` | water / ice sheet |
| `0x08A030` | MARK_6 sub[0] | 100/160 | GT3·160 | `0x018` X=512 4bpp | (0, 244) | `0x000870..0x000890` | sky gradient shell |
| `0x08C418` | MARK_6 sub[2] | 51/32 | FT4·32 | `0x09D` X=832 8bpp | (0, 248) | `0x001070..0x001270` | cloud sheet |
| `0x08D888` | MARK_6 sub[4] | 33/20 | FT4·8 GT4·12 | `0x017` X=448 4bpp | (192, 244) | `0x0009F0..0x000A10` | cloud band A |
| `0x08DCCC` | MARK_6 sub[5] | 224/192 | FT4·192 | `0x09B` X=704 8bpp | (0, 245) | `0x000A70..0x000C70` | **the sky dome** (largest scenery mesh) |
| `0x08FC20` | MARK_6 sub[6] | 33/20 | FT4·8 GT4·12 | `0x017` X=448 4bpp | (192, 244) | `0x0009F0..0x000A10` | cloud band B |
| `0x0BB0E8` | c1 id-2 sub[1] | 60/40 | GT4·40 | `0x017` X=448 4bpp | (192, 244) | `0x0009F0..0x000A10` | cloud band C |
| `0x0BC30C` | c1 id-2 sub[8] | 80/60 | FT4·20 GT4·40 | `0x09D` X=832 8bpp | (0, 251) | `0x0A2650..0x0A2850` | the fire column |
| `0x0BE030` | c1 id-2 sub[15] | 81/64 | FT4·64 | `0x119` X=576 **15bpp** | — none — | — | direct-colour panel (see §9 OPEN-1) |
| `0x0C2264` | c1 id-2 sub[37] | 112/96 | FT4·96 | `0x097` X=448 8bpp | (0, 246) | `0x000C70..0x000E70` | impact / energy rings |

Untextured (no reskin surface): `0x08B85C` (MARK_6 sub[1], G4/G3), `0x0BD7F8`, `0x0C11B4`, `0x0C3230`
(all c1 id-2, G4/F4). Their colour is per-vertex in the geometry, not in any palette.

**Sub-file listings**, with every entry classified (model / camera / AKAO / data), are in
`A2-attribution.txt`.

### 3.3 The complete VRAM map (every halfword ef227 writes, with its file source)

| VRAM x | y | w | h | file offset | bytes | writer | what |
|---:|---:|---:|---:|---|---:|---|---|
| 256 | 230 | 256 | 6 | `0x0621A0` | 3,072 | id-4 | **creature CLUT strip, 6 rows** |
| 0 | 242 | 256 | 2 | `0x0A2048` | 1,024 | c1 id-0 | eff CLUT rows 242–243 |
| 0 | 244 | 256 | 6 | `0x000870` | 3,072 | c0 id-0 | **eff CLUT rows 244–249** |
| 0 | 250 | 256 | 2 | `0x0A2450` | 1,024 | c1 id-0 | eff CLUT rows 250–251 |
| 192 | 256/384 | 64 | 128 | `0x04E1A0` / `0x04A1A0` | 16,384 ea | id-4 | creature parts 1 / 0 |
| 256 | 256/384 | 64 | 128 | `0x0561A0` / `0x0521A0` | 16,384 ea | id-4 | creature parts 3 / 2 |
| 320 | 256/384 | 64 | 128 | `0x05E1A0` / `0x05A1A0` | 16,384 ea | id-4 | creature parts 5 / 4 |
| 384 | 256/384 | 64 | 128 | `0x042000` / `0x046000` | 16,384 ea | id-9 | lightning / motes (slots 6,7) |
| 448 | 256 | 64 | 256 | `0x001470` | 32,768 | c0 id-0 | clouds (4bpp) + rings (8bpp) |
| 512 | 256 | 64 | 256 | `0x009470` | 32,768 | c0 id-0 | sky gradient |
| 576 | 256 | 64 | 256 | `0x019470` | 32,768 | c0 id-0 | aerial ground (left half) |
| 576 | 256 | 64 | 256 | `0x0A2850` | 32,768 | c1 id-0 | **overwrites the above at chunk-1 time** |
| 640 | 256 | 64 | 256 | `0x021470` | 32,768 | c0 id-0 | aerial ground (right half) |
| 640 | 256 | 64 | 256 | `0x0AA850` | 32,768 | c1 id-0 | **overwrites the above at chunk-1 time** |
| 704 | 256 | 64 | 256 | `0x011470` | 32,768 | c0 id-0 | sky dome (left half) |
| 768 | 256/384 | 64 | 128 | `0x032000` / `0x036000` | 16,384 ea | id-9 | sky dome (right half), slots 0,1 |
| 832 | 256/384 | 64 | 128 | `0x03A000` / `0x03E000` | 16,384 ea | id-9 | cloud sheet, slots 2,3 |
| 832 | 256 | 64 | 256 | `0x0B2850` | 32,768 | c1 id-0 | **fire column — overwrites id-9 slots 2,3** |

---

## 4. THE OVERLAP VERDICT

### 4.1 Creature × scenery: **fully disjoint. Zero contact.**

Computed exactly, not by bounding box: every model's covered VRAM halfwords were accumulated as the
union of its **per-face** UV bounding boxes and intersected pairwise (`A2-coverage.txt`).

```
creature page columns (64-halfword) : {192, 256, 320}         y 256..511
scenery page columns                : {448, 512, 576, 640, 704, 768, 832}
creature CLUT cells                 : (256,230) (256,231) (256,232) (256,233) (256,234) (256,235)
scenery  CLUT cells                 : (0,244) (192,244) (0,245) (0,246) (0,248) (0,249) (0,251)

page-span overlap creature x scenery : NONE
exact halfword overlap creature x scenery : NONE
CLUT cell intersection : EMPTY
```

The creature occupies VRAM `x ∈ [192, 384)` and its palettes occupy `x ∈ [256, 512), y ∈ [230, 236)`.
No effect model reaches below `x = 448`, and no effect CLUT sits above row 241. Column `[384, 448)` —
id-9's lightning — is the buffer between them and is referenced by no GEOM model at all.

**⇒ "creature-only", "scenery-only" and "whole set" are three cleanly separable scopes. A creature CLUT
recolour cannot touch the scenery, and vice versa. There is no shared-palette hazard across that line.**

### 4.2 Beam / aura / prop models × the creature: also disjoint

The question "do the BEAM/aura effect models share CLUTs with the creature" has the same answer: no.
Every drawn prop in ef227 is either one of the 11 textured effect models above (all bound to rows
244–251) or an untextured Gouraud mesh with no palette at all. Nothing in the effect's model set is
bound to rows 230–235.

### 4.3 Sharing *within* the scenery — this is where the care is needed

**CLUT sharing (2 groups):**

| CLUT | file | shared by |
|---|---|---|
| (0, 244), 16 entries | `0x000870..0x000890` (32 B) | water/ice sheet `0x02BA28` **and** sky gradient `0x08A030` |
| (192, 244), 16 entries | `0x0009F0..0x000A10` (32 B) | cloud bands A/B/C — `0x08D888`, `0x08FC20`, `0x0BB0E8` |

Every other scenery CLUT is used by exactly one model. So of 11 textured models, **8 have a private
palette**; two 32-byte palettes cover the other 3+2.

**Page sharing (real, and two flavours):**

* **Dual-depth packing — the sharp edge.** VRAM column 448 rows 321–383 is read as **4bpp cloud band**
  (CLUT 192,244) *and* as **8bpp energy rings** (CLUT 0,246) — 4,032 halfwords addressed by both, at
  different bit depths. The artist packed a 4-bit picture into byte values the 8-bit palette maps to
  black. **A texel repaint there changes two pictures at once. A CLUT recolour there does not** — the
  two readings have separate palettes.
* **Time-shared columns.** Chunk 1's page uploads land on VRAM x = 576, 640 and 832, which chunk 0
  already filled. Byte-compared, chunk 0's and chunk 1's payloads at x=576 differ in 93.0 % of bytes and
  at x=640 in 89.6 % — genuinely different art, not a redundant re-upload. Column 832 is written by
  id-9 (chunk-0 time, cloud sheet) then by chunk 1 (fire column). **A repaint of a time-shared column
  must patch both sources or the look changes only for part of the cast.**
* Other same-depth page overlaps (aerial ground vs water sheet at 576; sky dome across 704+768) are
  listed in `A2-coverage.txt`.

---

## 5. SANITY ANCHOR — do the attributed CLUTs decode to Bahamut?

**Yes, decisively.** `A2-creature-pages.png` renders all six parts through their attributed CLUTs
(3×2 tiling, left→right = tpage 147/148/149, top row = `vOffset` 128):

| part | what the decode shows |
|---|---|
| 0 | **the violet/magenta wing membrane**, with the radiating vein pattern, plus dark horn |
| 1 | dark plum-black scaled hide, and **cream/ivory claws, spurs and horn tips** |
| 2 | **amber-gold neck and belly plating** over dark hide |
| 3 | the dark plum-black body mass (the least colourful page) |
| 4 | **gold ribbed underbelly / tail segments** plus bone-cream claw |
| 5 | scale rows, **gold plates** and cream claws |

That is the canonical Bahamut: **violet wings, cream/bone claws and horns, gold belly plating, dark
plum-black hide.** The one caution for a recolour tool: the flat mauve field filling the unused atlas
area is *not* a body colour — it is the pad colour and it occupies 12–22 % of every page, so any
"dominant colour" statistic taken over a whole page is dominated by padding. Weight by UV coverage.

**The scenery decodes are equally coherent** (`A2-eff-textures.png`, dominant colours weighted over each
model's own UV region):

| model | dominant decoded colours | reads as |
|---|---|---|
| `0x029E14` aerial ground | `#212921` 12 % · `#293129` 11 % · `#213121` 9 % | **the desaturated green satellite-view terrain the W2 cast saw** |
| `0x08A030` sky gradient | `#102142` 22 % · `#214263` 12 % · `#18395A` 11 % | deep blue sky shell |
| `0x08DCCC` sky dome | `#000063` · `#000073` · `#00007B` + white | blue sky with white cumulus |
| `0x0BC30C` fire column | 75 % black + `#E7C673` | amber flame on transparent |
| `0x0C2264` rings | 58 % black + `#9C5200`, `#8C4200` | orange energy rings on transparent |

The W2 cast's "satellite-view terrain that is not the arena" is now a named byte region: model
`0x029E14`, CLUT file `0x001270..0x001470`, texels in c0 pages at file `0x019470` and `0x021470`.

---

## 6. THE BYTE-REGION EDIT MENU

All offsets are into the 823,296-byte `ef227` container. Every region is **same-length, in-place** —
the container's sector/table arithmetic is untouched, so W1's byte-exact round-trip and the W2/W3 drift
guards keep working unchanged.

### (a) CREATURE-ONLY CLUT RECOLOUR — **one contiguous span, 3,072 bytes**

| region | length | contents |
|---|---:|---|
| `0x0621A0 .. 0x062DA0` | **0xC00 = 3,072 B** | the whole creature CLUT strip: 6 rows × 256 × BGR555 |

Sub-addressable per body region, if the recolour should be selective:

| part | region | length | body region (from §5) |
|---:|---|---:|---|
| 0 | `0x0621A0..0x0623A0` | 512 B | **wing membrane** (violet) |
| 1 | `0x0623A0..0x0625A0` | 512 B | hide + **claws/horns** (cream) |
| 2 | `0x0625A0..0x0627A0` | 512 B | neck/belly **plating** (gold) |
| 3 | `0x0627A0..0x0629A0` | 512 B | body mass (dark) |
| 4 | `0x0629A0..0x062BA0` | 512 B | tail/underbelly **plating** (gold) |
| 5 | `0x062BA0..0x062DA0` | 512 B | scales + plates + claws |

Rules a transform must honour (all MEASURED): entries are **little-endian BGR555 with bit15 = STP**;
each row's single `0x0000` entry is the fully-transparent texel and must stay `0x0000`; bit15 is set on
essentially every live entry and controls semi-transparency blending, so a hue rotation must preserve
bit 15 rather than recompute the whole word; 1,525 of the 1,536 entries are live.

**0.37 % of the container. Nothing else in the file needs to move.**

### (b) SCENERY-ONLY CLUT RECOLOUR — 3 spans, 5,120 bytes

| region | length | rows | referenced by |
|---|---:|---|---|
| `0x000870 .. 0x001470` | 0xC00 = 3,072 B | 244–249 (c0) | 7 of the 11 textured models |
| `0x0A2048 .. 0x0A2448` | 0x400 = 1,024 B | 242–243 (c1) | no GEOM model — sprite/other draws |
| `0x0A2450 .. 0x0A2850` | 0x400 = 1,024 B | 250–251 (c1) | fire column (row 251) |

Scoped to individual set pieces:

| set piece | CLUT region | length |
|---|---|---:|
| water/ice sheet + sky gradient (**shared**) | `0x000870..0x000890` | 32 B |
| cloud bands A+B+C (**shared**) | `0x0009F0..0x000A10` | 32 B |
| **sky dome** | `0x000A70..0x000C70` | 512 B |
| energy rings | `0x000C70..0x000E70` | 512 B |
| *(unreferenced by any model — row 247)* | `0x000E70..0x001070` | 512 B |
| cloud sheet | `0x001070..0x001270` | 512 B |
| **aerial ground plane** | `0x001270..0x001470` | 512 B |
| fire column | `0x0A2650..0x0A2850` | 512 B |
| *(unreferenced by any model — rows 242, 243, 250)* | `0x0A2048..0x0A2448`, `0x0A2450..0x0A2650` | 1,024 + 512 B |

Live-entry counts per row (a recolour's real working set) are in §3.1's companion dump: row 244 has
223/256 non-transparent, 245 → 255, 246 → 119, 248 → 255, 249 → 256, 251 → 169.

### (c) WHOLE SET — 4 spans, 8,192 bytes

`0x000870..0x001470` + `0x0621A0..0x062DA0` + `0x0A2048..0x0A2448` + `0x0A2450..0x0A2850`.
**1.0 % of the container**, and no two spans interact.

### (d) If lever #2 (texel repaint) is ever wanted — the surfaces

| surface | region | length | notes |
|---|---|---:|---|
| creature texels | `0x04A1A0 .. 0x0621A0` | 98,304 B | 6 × (128×128 8bpp), 1:1 with part, **no sharing anywhere** — the safest repaint target in the file |
| c0 scenery pages | `0x001470 .. 0x029470` | 163,840 B | 5 × (64×256 hw); column 448 carries the **dual-depth trap** |
| c1 scenery pages | `0x0A2850 .. 0x0BA850` | 98,304 B | 3 × (64×256 hw); overwrites c0 at x=576/640 and id-9 at x=832 |
| id-9 alt blocks | `0x032000 .. 0x04A000` | 98,304 B | 6 × (64×128 hw) at slots {0,1,2,3,6,7} |

Because each creature part owns its 0x4000 block outright, a per-body-part texel repaint needs no
masking at all — which is the opposite of the scenery situation.

---

## 7. What this means for the W4 design

1. **Lever #1 is the right lever and the scope question has a clean answer.** Creature-only is a single
   3,072-byte contiguous span; whole-set is four spans totalling 8,192 bytes. No scope requires touching
   geometry, UVs, the loader script, the effect program, or any camera byte — so W2's and W3's edits and
   W4's are provably orthogonal and can ship in one container.
2. **The committable surface is a palette transform keyed by (part | set-piece) name**, exactly the
   posture the frame locks: a TOML naming e.g. `creature.wing`, `creature.plating`, `scenery.ground`,
   each with a hue/sat/value rotation or an explicit 256-entry map, compiled against the *user's own*
   extracted container at build time. Zero stock bytes in the repo.
3. **Two guard rails the builder must enforce** (they are the only ways to get a wrong-looking cast from
   a correct-looking edit):
   - a CLUT write must preserve the `0x0000` transparent entry and bit 15 of every other entry;
   - the two shared scenery CLUTs (32 B each) recolour **more than one set piece** — either the schema
     forbids naming them individually, or it names the *group*.
4. **THE EFFECT-OWNED SCENERY LAW gets a sharper form.** The set is not merely "authored to look right
   from its own camera" — it is *authored to look right from its own camera and it is texture-disjoint
   from the creature*. So the reskin can be scoped independently of the rescore: recolouring the ground
   plane does not touch Bahamut, and recolouring Bahamut does not touch the ground.
5. **The full-cast look also depends on time-shared columns.** If W4 ever repaints texels rather than
   palettes, the aerial ground and the x=832 column each have two byte sources for two phases of the
   same cast. Palette recolour is immune to this; texel repaint is not.

---

## 8. Corrections to the record

1. **`MARK_7` is NOT geometry.** `PLAN.md` §"THE EFFECT-OWNED SCENERY LAW" says ef227 chunk 0 carries
   "a `MARK_6` (26 KB) and two `MARK_7` (70 KB) **geometry resources**". Both `MARK_7` payloads
   (`0x090800` and `0x099800`) open with the ASCII tag `AKAO` and contain **zero** GEOM blocks; the
   corpus-wide GEOM census in FORMAT §2.3 also lists no id-7 blocks at all. The scenery lives in
   **`MARK_6` (6 models) and the two id-2 sub-file archives (2 + 7 models)**. The law itself stands —
   only the resource attribution was wrong. The reskin's scenery scope is unaffected in substance but
   its *byte* scope changes: the 70 KB of `MARK_7` is audio and is not a reskin surface.
2. **`RESOURCE_IDS[2]`'s legacy `SOUND_AKAO` label is doubly misleading here.** FORMAT already retired
   the "AKAO sound" reading of id 2 in favour of "sub-file archive"; ef227's id-2 archives hold models,
   cameras *and* AKAO sub-files together. The actual AKAO-tagged bulk is in id 7.
3. **A1 vs A2, one disagreement.** A1's listing shows chunk 1's id-0 with **one** page-block record;
   A2 reads **three** — (576,256,64,256), (640,256,64,256), (832,256,64,256) — from `nPageRects = 3` at
   `0x0A2024`. A2's reading is the one that closes: `pixelDataRel(0x850) + 3 × 0x8000 = 0x18850` fits
   inside the combined c1 id-0 + 5×id-1 payload (`0x19000`), whereas one page would leave `0x14000`
   bytes of continuation resources unexplained, and the fire-column model at tpage X=832 would have no
   chunk-1 source. **Recommend A2's count**; it is a one-line check for whoever reconciles.

---

## 9. Open items (none of them gate the W4 design)

| # | open | why it does not gate | how to settle |
|---|---|---|---|
| **1** | Model `0x0BE030` (c1 sub[15], tpage `0x119` = **15bpp direct colour**, 64 FT4 faces) renders as chromatic noise from every candidate byte source tried (c0 pages 3/4, c1 pages 0/1). | It has **no CLUT** — it is invisible to lever #1 in every scope. | Either its page is written by a source not yet enumerated, or the 15bpp reading is a mis-set colour-depth field the GPU ignores in practice. Decide only if lever #2 is taken; check the c1 program's draw for this sub-file index. |
| **2** | 605 of 1005 corpus GEOM blocks have **no** `so` record. | ef227 is 15/15 covered; the target is fully mapped. | Sweep the effects that use them for an alternative wrapper, or trace the register call in their programs. Only matters when W4 generalises past ef227. |
| **3** | id-9's slot-enable mask read as the `info` byte is INFERRED (though A1 and A2 agree and slots 0–3 are empirically confirmed). | Slots 4/5 vs 6/7 changes nothing for the creature (id-4 loads after id-9 and wins) and nothing for any CLUT. | Falsifier: if the map were wrong, the sky dome's right half would not join seamlessly — it does. A second: an `info` byte whose popcount ≠ payload-block count anywhere in the 37 id-9-bearing effects would break the mask reading. |
| **4** | `so` record fields `+0x06`, `+0x0C`, `+0x0E` remain OPAQUE. | They are not texture bindings; a same-length CLUT edit never touches them. | Carry verbatim, per the preserve-don't-invent rule. |

---

## 10. Artifacts

Under `C:\gd\SCRATCH\summon-format\reskin-w4-recon\` (stock-derived — scratch only):

| file | what |
|---|---|
| `A2-attribution.txt` | the full listing: sub-file classification, VRAM map, per-model attribution + coverage |
| `A2-coverage.txt` | exact per-face halfword coverage and the pairwise overlap matrix |
| `A2-so-record-corpus.txt` | the 372-file `so`-record sweep |
| `A2-container-ef227.txt`, `A2-raw-ef227.json` | container walk + machine-readable attribution |
| `A2-creature-pages.png` | **the calibration image** — all 6 creature pages through their CLUTs |
| `A2-eff-textures.png` | all 11 textured scenery/prop models' texture regions |
| `A2-sky-with-id9.png` | the id-9 slot-0/1 seam proof |
| `A2-id9-slots.png`, `A2-id9-blocks.png`, `A2-chunk1-pages.png` | the id-9 and time-shared-column tests |
| `a2_attrib.py`, `a2_render.py`, `a2_corpus.py`, `a2_cover.py`, `a2_final.py`, `a2_walk.py` | the analysis scripts (read a caller-supplied blob; embed no game bytes) |

**Provenance:** no stock bytes were written into the repository; no game or engine file was modified;
every DLL claim comes from read-only static analysis of the user's own installed
`FF9SpecialEffectPlugin.dll` and is cited `fn@rva`.
