# A4 — PRIOR ART + BENCH STATE (W4 reskin recon)

> Scope: read-only. No install writes, no repo-code edits. Every claim below is tagged **MEASURED**
> (read directly this session) or **INFERRED** (derived from a measured fact but not itself
> independently re-derived). No hex byte run of stock data appears below — only offsets, counts, ids,
> and previously-published small scalar values (already committable in the cited source docs).

---

## 1. The kit's summons package ALREADY HAS a texture module — what it does, and what it doesn't

**`ff9mapkit/ff9mapkit/summons/texture.py` is a DECODER, native-container lane, one direction only:
`ef###.bytes` bytes → RGBA. There is no encoder anywhere in the kit.** MEASURED (full file read).

What it implements, precisely:

| Function | Direction | What it does |
|---|---|---|
| `part_textures(mp)` | offsets only | resolves every part's `{tpage, clut, v_offset}` to absolute FILE offsets (`page_offset`, `clut_offset`) — pure arithmetic, no blob read |
| `texture_check(blob, mp)` | validate | checks the 8bpp-page-layout laws hold (`partCount>=1`, `texBytes==partCount*0x4000`, `clutBytes==clutRows*0x200`, every part's TPAGE mode==1, every CLUT row/entry range in-bounds); `decodable=False` + reasons on any violation — **never guesses** |
| `read_palette(blob, offset)` | DECODE | 256 BGR555 halfwords → RGBA list |
| `bgr555_rgba(word)` | DECODE | one BGR555+STP halfword → `(r,g,b,a)`; `0x0000` → transparent (measured: true on all 6 of ef227's CLUT rows, entry 0) |
| `decode_page_rgba(pixels, palette)` | DECODE | 128×128 8-bit indices + a palette → row-major RGBA (pure, no PIL) |
| `decode_pages(blob, mp)` | DECODE | every part's page → `{part index: PIL Image}` (128×128 RGBA); raises `TextureError` if `texture_check` refuses |
| `uv_texcoord(word, v_offset)` | DECODE | one UV-pool `u16` → glTF `(u,v)` in [0,1], texel-centre + the V-offset pre-bake applied |
| `page_row(raw_v, v_offset)` | DECODE | the V-offset bake/un-bake identity (documented as deliberately explicit, not relying on cancellation) |

**No `encode_*`, `write_*`, `quantize_*`, `pack_clut`, or `rgba_to_bgr555` function exists in this
file or anywhere else in the repo** (grepped the whole tree for those and `555`/`quantiz` — the only
hits are unrelated `encode_token`/`encode_field`/`encode_elements`-style CSV/opcode encoders in other
pillars, plus two unrelated `quantize_*` helpers in an overworld dune study). MEASURED.

**Geometry format constants already fixed and reusable by W4 verbatim** (no need to re-derive): page =
`128×128` 8bpp indexed, `0x4000` bytes/page; CLUT strip = `256`-entry rows, `0x200` bytes/row; VRAM
strip origin `(0x100, 0xE6)`; per-part TPAGE mode must be `1` (8bpp) to be in-scope. `ef227` = 6
parts / 6 CLUT rows, all mode 1, `u,v <= 127` (`texture.py` docstring + FORMAT.md, both agree).

### `summons/container.py` — read-only, no texture writer
Pure parser (`parse_header`, `parse_model_package`, `creature_package`, `creature_geom`, `part_textures`
consumer). Its own docstring states it plainly: **"It embeds no game bytes and writes nothing (the
writer lives elsewhere)."** `ModelPackage` carries `tex_file_offset`/`tex_bytes`/`clut_bytes` — the exact
fields a W4 patcher needs to locate the target bytes in a COPY of the container — but nothing in this
file mutates them. MEASURED.

### `summons/export.py` — the decoder's only consumer, and it's a ONE-WAY door
`resolve_textures(blob, mp, textures)` calls `texture.texture_check` then `texture.decode_pages`, ON by
default, with an honest untextured fallback (never guesses). `export_summon_glb`/`export_rig_ref` feed
the decoded PIL images into `models.gltf.emit_model_gltf` as material textures. **This is a READ path
that terminates at a `.glb` file** — `assert_local_only` refuses to let that `.glb` land anywhere
committable/shippable (git repo / any `StreamingAssets` segment / the FF9 install), by design, because
the decoded pixels are Square-Enix content. **There is no code path anywhere in `export.py` that writes
back INTO an `ef###.bytes`-shaped container** — the module only ever produces glTF. MEASURED (full file
read). This matters for W4: the existing decoder + its glTF consumer are the wrong shape to reuse
directly for a reskin deliverable — W4 needs a NEW writer that patches a page/CLUT region of a
COPY of the container, not a glTF exporter.

### `summons/build.py` — texture-aware on the READ side only
`build.adapt_model(..., part_images=..., v_offsets=...)` has the per-face-per-part textured-mesh
adapter (`_adapt_meshes_textured`) that groups faces by `part` byte, splits shared vertices that
disagree on UV, and normalizes UVs against the real 128×128 page. This is glTF-material plumbing, not a
byte-level container writer — same one-way-door conclusion as `export.py`. One STALE comment worth
flagging: `build.py`'s own `_mesh_uvs` docstring (used only by the untextured path) still says "texture/
CLUT emission is explicitly out of scope" — true for THAT function's caller today, but the package as a
whole no longer matches that blanket statement (the decode side shipped in the W3-era texture rung).
Not a functional bug (the untextured path is correct on its own terms), just a doc that undersells what
`summons/texture.py` now does elsewhere in the same package. MEASURED.

### The `summon-export` CLI — yes, it already decodes native creature textures, ON by default
`cli.py`'s `summon-export` subcommand (`_cmd_summon_export`, the `se` parser) wires `--no-textures`
(default OFF, i.e. textures ON) straight through to `export_summon_glb(..., textures=not
args.no_textures)`. Its own help text: *"the creature's id-4 texture pages + CLUTs are decoded to one
RGBA PNG per material part and embedded in the .glb. A creature whose texture block is not the
documented 8bpp layout falls back to untextured on its own, with a warning."* **So: THE DECODER EXISTS
and is already CLI-reachable and already proven against the corpus (`resolve_textures`, `texture_check`,
`decode_pages` — all exercised by `summon-export` today).** MEASURED. What does **not** exist is any
CLI verb, or any library function, that goes the other direction (art → patched container bytes) — W4
is not blocked on "does a decoder exist" (it does), it is blocked on "does an encoder exist" (it does
not, anywhere in the repo).

---

## 2. FORMAT.md + the D/T-series disasm reports — what was ALREADY decoded about texture/VRAM

Every fact below pre-dates this recon round and is cited to its source section, so A1/A2's fresh
derivations should reproduce these numbers, not re-discover them from zero.

| Fact | Status | Source |
|---|---|---|
| Resource id **4** = `VRAM_TEXPAGE` — creature texture pages + the CLUT strip; its payload ALSO carries the model-package header | DECODED, 24/24 | `FORMAT.md` §resource-table (line ~256), `container.py` `RESOURCE_IDS` |
| Resource id **9** = `VRAM_TEXPAGE_ALT`, "second texture-page path", present on 37 of 372 effects | DECODED (existence only; not consumed by the creature-texture read path) | `FORMAT.md` line ~259 |
| `texOffset == 0x180 + 4*motionCount` (header size = model-image base) | DECODED, 24/24 | `FORMAT.md` §creature package header; `container.ModelPackage` |
| `texBytes == partCount * 0x4000`; `clutBytes == clutRows * 0x200` | DECODED, 24/24 | `FORMAT.md` same row; `texture.texture_check` re-asserts both as gate laws |
| Per-part **TPAGE** array at header `+0x18`, **CLUT** at `+0x24`, **V-offset** at `+0x30`, all `u16[partCount]` | DECODED, corpus-verified | `D3-container-validate.md` lines 147-150 (table diff vs an earlier M2 pass — M2 had `+0x30` wrong as "VRAM x word"; D3 corrected it to V-offset) |
| id-4 handler's VRAM rect math: page `{x=(tpage&0xF)*64, y=((tpage&0x10)<<4)+vOff, w=64, h=128}`; CLUT strip `{x=0x100, y=0xE6, w=0x100, h=clutRows}` | DECODED from the native handler `fn 0x3de37` (`@0x3e302-0x3e34b` page rect, `@0x3e286` CLUT rect) | `D3-container-validate.md` lines 148-149, 260-262; `M4-mesh-payload.md` lines 88-90 (the SAME fields read a second, independent way — off `Hi_RegisterSummonModel`'s own copy at `model+0x18`/`model+0x24`/`model+0x30`) |
| `ef227`'s six pages land at VRAM `(192,384) (192,256) (256,384) (256,256) (320,384) ...` (the concrete resolved rects for THIS creature) | DECODED | `D3-container-validate.md` line 152 |
| **Texture binding is per-face-per-part**, not per-mesh: a `part` byte (offset varies by prim type, e.g. FT4 `+0x13`) indexes a ≤6-entry `{tpage,clut}` array; **`part < partCount` is NOT an invariant** — 6/24 packages have faces with out-of-range parts, which render with `tpage=clut=0` (an unrelated corner of VRAM, not corruption) | DECODED, 24/24 structurally, 6/24 exhibit the out-of-range case | `FORMAT.md` lines 300-302; `M4-mesh-payload.md` lines 265-283, 302; `container.PRIM_FIELDS`, `build.UNBOUND_PART` |
| A **load-time UV V-offset bake** mutates the UV pool ONCE in live memory (`v_byte += partTable[part].v`); an offline reader must either pre-bake or explicitly cancel it | DECODED | `FORMAT.md` line 303; `D3` §5.4; `texture.py` module docstring "THE V-OFFSET PRE-BAKE" |
| Textures are **TRANSIENT STAGING**: id-4's texture+CLUT DMA to VRAM, then the id-5 payload's model image **overwrites the same arena address** — confirms the pixels never coexist with the geometry in the SAME memory region, i.e. reading them from the FILE (not live memory) is the only offline path | DECODED (a prior M4-vs-M2 correction, RESOLVED) | `D3-container-validate.md` lines 260-283 |
| **`ef227` = 93 bones / 2 meshes / 1439 verts / 2416 faces / 8 clips / 6 texture pages**; every creature uses only `FT4`+`FT3` (both textured) | DECODED, corpus-typed | `FORMAT.md` lines 308-310 |
| The recovery ladder's own rung table names this exact deliverable **"R4/W3 — texture/CLUT reskin"**: *"Pages are plain 64×128 16bpp blocks at `id4.offset + texOffset` with an exact size law; a recolour needs no code emission at all"* — and separately, *"pages are at `id4.offset + texOffset`, `0x4000` each, `partCount` of them, ... followed by `clutRows × 0x200` of CLUT at VRAM `(0x100, 0xE6)`. **No code needed.**"* | Marked **LOW / LOW** effort+risk at recon time | `FORMAT.md` line 556 (ladder row "W3 — texture / CLUT reskin"); `D3-container-validate.md` lines 433-435 (ladder row "R4") |

**⚠ A naming collision to flag, not re-litigate:** FORMAT.md's OWN recovery ladder (§ "R-ladder" and a
separate "W-ladder") numbers this deliverable **R4 / its own "W3"** — a DIFFERENT numbering scheme than
the arc's actual `tier-w/PLAN.md` rungs (W1=readout, W2=content rescore, W3=timing rescore, **W4=reskin**,
the one THIS recon is for). Do not confuse "FORMAT.md's W3" (texture/CLUT reskin) with "tier-w's W3"
(the timing retime, already cast-proven) — they are unrelated rungs from two different ladders that
happen to share a letter+number. FORMAT.md's own text already flags the reskin as the cheapest rung on
ITS ladder (LOW/LOW), which is corroborating, not contradicting, evidence for tier-w's W4.

**⚠ A units/geometry note, not a contradiction:** FORMAT.md's plain-language gloss calls the pages
"`64×128` 16bpp blocks" (the VRAM-halfword view: 64 HALFWORDS wide × 128 lines, `0x4000` bytes either
way you count it). `summons/texture.py`'s later, corrected reading is "`128×128` 8bpp indexed" (the
TEXEL view — the same `0x4000` bytes reinterpreted at 1 byte/texel once TPAGE mode 1 is accounted for).
Both describe the identical bytes; the texel-accurate reading (128×128 8bpp + a 256-entry CLUT row) is
the one a W4 encoder must target, since it is what `texture_check`/`decode_pages` already implement and
what round-trips through the CLI today.

**Not yet touched by any prior round, confirmed absent from every doc grepped this session:** the
**texanim table** (a real, non-empty block on 5/24 packages incl. none of them `ef227` — `ef227`'s own
`firstBlock == motion[0]`, i.e. its texanim region is empty) and any per-frame texture-page-swap
behaviour. If ef227 has no texanim entries, a static CLUT/texel reskin has no animated-texture case to
worry about for THIS creature — but that is an inference from the "empty texanim" fact above, not
independently re-verified this session (INFERRED).

---

## 3. Precedents elsewhere in the kit for committable texture art + transform specs

Four existing conventions, each usable as a partial template — **none of them is a byte-level native
PSX-container patcher**, which is the part W4 actually has to invent.

**(a) `ff9mapkit/ff9mapkit/models/reskin.py` — the closest LEVER #1 precedent (hue/tint), wrong LANE.**
`recolor_image(img, *, hue=None, tint=None)` is a pure, declarative recolor primitive: `hue` rotates the
HSV hue wheel by degrees (documented as "the classic Goblin → red-Goblin move: geometry-safe, keeps
shading/detail"); `tint` = `[r,g,b]` channel multipliers; both compose (hue first); **alpha is always
preserved untouched** ("FF9 materials are cutout-alpha, so a recolor must never disturb the mask" — the
same alpha-is-binary constraint `texture.py`'s own docstring notes for `bgr555_rgba`, entry `0x0000` =
transparent). This is the right SHAPE for W4's "lever #1 = CLUT/palette recolor" TOML surface (a `hue=`
or `tint=` knob is exactly a same-length, in-place, self-evidencing transform on a small palette, here
256 CLUT entries instead of a whole RGBA image) — but the module's OWN pipeline is the disc-probe
`{stem}.png` override lane for BUNDLE-loaded models (`ModelFactory.cs:100-116`), a completely different
mechanism than patching bytes inside a native `ef###.bytes` container. The CLI verb (`model-reskin`) is
imperative (`--export-textures` then `--texture ... --deploy`), not TOML-declarative — tier-w's own
posture (TOML → drift-guarded build → staged → ledgered deploy/revert, per W2/W3) is the better fit for
W4's deliverable shape, not this CLI's two-step flow. **Reusable as-is:** the `recolor_image` hue/tint
ALGORITHM (rewritten to operate on a 256-entry CLUT-as-image rather than a full texture) is a legitimate
lever #1 building block.

**(b) `ff9mapkit/ff9mapkit/battle/reskin.py` — a NAME COLLISION, not a texture precedent.** Despite the
name, this is a whole-donor-BLOCK model TRANSPLANT (Geo id + all 6 Mot animation ids + Mesh + Radius +
cosmetics, copied verbatim from a real enemy that already uses the target model) — it changes which
MODEL an enemy uses, never a texture's pixels or palette. Confirmed by the battle docs' own phrase:
"model re-skin (`Geo/Mot`, raw16-only, `reskin.py`)". Not applicable to W4 beyond the naming warning.

**(c) Battle-background (BBG) texture reskin — a loose-PNG-by-asset-name precedent, proven in-game, but
a different storage class entirely.** `project-ff9-battle-backgrounds.md` (memory): a battle map's
Texture2D (native Unity, e.g. BBG_B013's `image0..image7`, 256×256 RGBA) is reskinned by dropping a
same-named PNG at `<mod>\StreamingAssets\Assets\Resources\BattleMap\BattleModel\battleMap_all\<BBG>\
<texname>.png` — the engine's own bundle-override probe does the rest, alpha respected, no rebuild. This
is architecturally the SAME kind of asset-probe reskin as `models/reskin.py`'s `{stem}.png` lane (a
Unity-bundle texture, found by NAME) — it does not touch the native PSX VRAM-page format ef227 uses, so
it's evidence for "the kit already has committable-texture conventions for bundle-loaded assets," not a
template for the byte-patch W4 needs.

**(d) `ff9mapkit/ff9mapkit/world/atlas.py` (`world-atlas-extract` / `world-atlas-reskin` CLI) — the
closest LEVER #2 (texel-repaint) WORKFLOW precedent.** `extract_atlas`/`deploy_atlas`: extract the
overworld's shared terrain/object texture atlas to a PNG (same UV layout), hand-repaint it in any image
editor, then `world-atlas-reskin <png> --part terrain --mod-folder <mod>` deploys it as a "no-DLL HD
reskin (T2): same UV layout, new pixels." This is the right WORKFLOW shape for a whole-page texel
repaint (extract → edit → validate-same-layout → deploy) even though, again, the underlying storage
(a Unity atlas PNG vs a native 128×128 8bpp-indexed VRAM page + CLUT) is unrelated — a W4 texel-repaint
verb should probably mirror this extract/repaint/deploy verb shape rather than invent a new one.

**(e) NIMBRA's atlas (`studies/custom-summons/rung8-epic/creature/nimbra_spec.py`) — a STYLE precedent
for "PSX-plausible" art, not a format precedent.** NIMBRA is a wholly original, from-scratch creature
(mint id 6400) that ships through the ordinary loose-FBX+PNG override lane (a modern RGBA PNG probed by
name, same as `models/reskin.py`'s lane) — it never touches the native `ef###.bytes` VRAM-page/CLUT
format at all. Its atlas-finishing step (`nimbra_spec.py` lines ~739-745, "PSX finish: 4×4 Bayer dither +
15-bit (5 bits/channel) quantization") is a deliberate AESTHETIC choice — round each channel to 5-bit
precision with an ordered (Bayer) dither so flat gradients don't band, "PSX hardware was 15-bit" — not a
technical requirement of the pipeline NIMBRA ships through (that pipeline is a full RGBA PNG; nothing
forces 15-bit color there). **Worth reusing for W4 regardless**, because W4's actual FORMAT constraint is
stricter than NIMBRA's self-imposed one: ef227's native pages are true 8-bit-INDEXED (≤256 colors per
part, drawn from a 256-entry BGR555 palette), not merely 15-bit direct color. NIMBRA's Bayer-dither
CONSTANT (the 4×4 matrix + the `/16.0-0.5` centering) is a reusable primitive for the 5-bit-per-channel
quantization step of a lever-#2 encoder; the missing piece NIMBRA never needed is palette SELECTION
(picking ≤256 representative colors and building the index map), which none of these five precedents
implement.

**Bottom line for W4's declarative surface:** no existing TOML shape in the kit describes a palette
transform (hue/tint exists only as Python keyword args in `models/reskin.py`, never exposed as a TOML
block). Tier-w's OWN precedent (`bahamut_rescore.toml`, `bahamut_retime.toml`) is the right model to
follow structurally — a small declarative spec naming the target effect + which lever + its parameters,
consumed by a drift-guarded build script that reads the user's live install at run time and writes only
a staged, ledgered artifact — not any of the five texture precedents above, which should be mined for
ALGORITHMS (hue/tint math, Bayer dither) and WORKFLOW SHAPE (extract/edit/deploy), not for TOML schema.

---

## 4. Live state re-verify (read-only, this session)

All checks run directly against `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\` and
`C:\gd\SCRATCH\summon-format\`. MEASURED unless noted.

| Check | Result |
|---|---|
| `FF9CustomMap\FF9_Data\SpecialEffects\ef227` sha256 | `8146eff43a1448e3a2fd3ffe4cdc760f8d93dcdb2696c1c1022cee3ecf13beb8` — **matches** the value W3-RETIME.md records as "still W2's `8146eff4…`" (resting state after W3's revert) |
| `FF9CustomMap\FF9_Data\SpecialEffects\` directory contents | exactly one entry, `ef227` — no other whole-container overrides live |
| `FF9CustomMap\StreamingAssets\Data\SpecialEffects\` text-override dir | contains `ef080/`, `ef084/`, `ef091/` only — **no `ef227/`** (confirms the W3 text co-retime is NOT currently live; consistent with "reverted to W2's resting state") |
| Bench `30301` — `Actions.csv` row "Stock Bahamut" | id=196, comment="Stock Bahamut", `animationId1`=227, `animationId2`=227 (vfx1=vfx2=227), `type`=0, `targets`=AllEnemy(8) — **intact**, matches W3-RETIME.md's cast-protocol description exactly |
| `Memoria.ini` `[Mod]` `FolderNames` | `"FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo"` — unchanged from CLAUDE.md's documented stack |
| `ModFileList.txt` anywhere under `FF9CustomMap` | none found |
| `FF9CustomMap` top level, anything unexpected | `.summon-backups/` and `.summon-revert/` — the summons deploy engine's own ledger dirs, both present and populated (backups timestamped `20260724-212709`/`20260724-235532`; a `revert_summon.py` + `revert_summon_6400.py` — these are the RUNG-8/NIMBRA bench's ledger, not W2/W3's; unrelated to ef227). `DictionaryPatch.txt`/`ForkDonorPatch.txt`/`TextPatch.txt` all last-written `00:49` (the W3 build), `BattlePatch.txt` `19:29` (older, unrelated to this arc), `FolklorePatch.txt` older still. Nothing looks stray. |
| `C:\gd\SCRATCH\summon-format\retime-w3\` (W3's resting state) | present and intact: `b0/`, `b1/`, `backups/`, `build_manifest.json`, `deploy_aligned.py`, `deploy_misretime.py`, `live-snapshot/`, `misretime/`, `mod/`, `revert_summon_retime_227.py` |
| `C:\gd\SCRATCH\summon-format\rescore-w2\` (W2's artifacts) | present: `backups/`, `mod/`, `revert_summon_camera_227.py` |
| Anything else new under `C:\gd\SCRATCH\summon-format\` | `reskin-w4-recon\` already exists and has three files from sibling recon agents this round (`A1-ef227-container.txt`, `A1-ef227-textures.txt`, `A2-container-ef227.txt`) — not read/used by this report (out of this task's scope; flagging their existence only so downstream agents know A1/A2 output already landed there) |

**Net: the live install is exactly where W3-RETIME.md's own closing note says it should be** (W2's
4-byte camera rescore live in the whole-container override, W3's program/sequence/camera retiming NOT
currently live in that container — i.e. the container currently on disk reflects W2's cast, not W3's —
and the W3 text co-retime reverted out of the loose-text lane). This is a **measured, independent
confirmation** of the resting-state claim in `W3-RETIME.md`, not a re-assertion of it.

---

## 5. The Moguri question — cheap, install-side answer

**No.** `MoguriMain` (present, active in `FolderNames`, own `ModFileList.txt` ~506 KB) ships:
- `FF9_Data/EmbeddedAsset/ui/{atlas,sprites}` — UI-only, no `SpecialEffects` subtree anywhere under its
  `FF9_Data` (checked to depth 3; the only `FF9_Data` child is `EmbeddedAsset`).
- `StreamingAssets/Assets/Resources` + `StreamingAssets/ma/*.bytes` (movie/BG-named `.bytes`) +
  `StreamingAssets/p0data11.bin` .. `p0data19.bin` (Unity asset-bundle overrides).
- Grepped all nine `p0data1{1..9}.bin` bundles for the ASCII strings `specialeffect` and
  `ef227`/`battleeffect` (case-insensitive): **zero hits in every file.** Unity serialized containers
  carry their asset paths as plain strings, so a bundle that touched a `SpecialEffects/...` asset would
  show up this way; none do.
- `MoguriMain`'s `ModFileList.txt` itself: zero occurrences of `specialeffect` (case-insensitive).

So there is nothing in this install's Moguri stack that shadows, upscales, or otherwise touches
ef227's (or any) native VRAM-page/CLUT texture. Two secondary points, both moot here but worth recording:
(1) even if Moguri DID carry a whole-container `FF9_Data/SpecialEffects/ef227` override, `FolderNames`
already lists `FF9CustomMap` ahead of `MoguriMain`, so ours would win the probe regardless (first-listed
folder wins, per the kit's own text-block-shadow law); (2) this check is intentionally shallow (ASCII
string grep over the raw bundle bytes, not a full UnityPy asset walk) — cheap and sufficient to answer
"does Moguri touch battle-effect textures at all," not exhaustive proof of the bundle's full contents.

---

## Summary for the orchestrator

1. **The decoder for W4's target format already exists, is corpus-proven, and is CLI-reachable today**
   (`summons/texture.py` + `summons/export.py`'s `resolve_textures` + `summon-export --textures` default
   ON). W4 does not need to re-derive the page/CLUT geometry — it's settled (§2 table) and re-implemented
   correctly in shipped code (§1).
2. **The one real gap is the ENCODER**: nothing in the repo goes RGBA/edited-art → quantized 8bpp
   indices + BGR555 CLUT bytes, patched into a copy of the container. This is genuinely new work, not a
   rebuild of something that exists.
3. **Borrow, don't reinvent:** `models/reskin.py`'s `recolor_image(hue=, tint=)` algorithm for lever #1
   (adapted to operate on a 256-entry CLUT), NIMBRA's Bayer-dither quantization constant for lever #2's
   5-bit-per-channel step (palette SELECTION/indexing still has to be written new), and
   `world/atlas.py`'s extract→repaint→deploy CLI-verb shape as the workflow template — while following
   tier-w's OWN TOML→build→stage→ledger posture (W2/W3), not any of these five precedents' CLI/TOML
   shape, for the actual deliverable structure.
4. **Live state matches expectations exactly**, independently re-verified (§4) — W2's rescore is the
   container currently on disk, W3's retiming is not currently live in it, no stray overrides, no
   Moguri interference (§5). W4 has a clean, understood bench to build on.
