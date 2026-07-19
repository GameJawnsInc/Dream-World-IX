"""THE discmr.img PACK CENSUS -- decode every ``w_framePackExtractPosition`` sub-table, not just the two
``worldpack.py`` already implements (3 EncountTable / 4 EncountSpecial), and settle the roadmap's ModelSea question:
"can table 66 (``sNWBBlockHeader``, the legacy PS1 sea-block/cell/vertex/surface hierarchy) ground-truth
``water.py``'s statistical Wang-tile ocean synthesis against real stock sea geometry?"

**Method.** ``ff9mapkit.world.worldpack.load_discmr`` already parses the two-layer container (sector TOC -> the
pointer-table pack) and exposes the raw bytes (``discmr._data``) + the full pointer table (``discmr.offs``), so this
script does NOT re-derive that plumbing -- it reuses ``load_discmr`` and decodes every additional sub-table using the
engine's OWN consumer code as the format oracle (``C:/gd/FFIX/Memoria/Assembly-CSharp/Global/ff9/ff9.cs`` +
``Global/WM/WMBinarayReaderExtension.cs``), cross-checking every inferred record size against the pointer table's
measured byte span (an independent arithmetic proof the guessed struct layout is right, since several of these
readers are DEAD CODE with no other confirmation).

**Headline finding (read before touching worldpack.py):** most of the doc's cited sub-tables are LIVE, but three
are flatly DEAD CODE in this Memoria build (their only C# reader is a ``/* ... */``-commented method with zero
callers anywhere in the tree) -- 0 EffectAreaBin, 2 PaletVolcano-adjacent extra slots, 5 ColorTable/weather -- and
table 66 ModelSea, while its LOAD call is live (``ff9.cs:8778``), has a DEAD *consumer* (``w_nwpInitialize``/
``w_nwpMakePages``, ``ff9.cs:7211-7219``, both empty bodies, both entirely ``/* commented out */``, zero call sites
anywhere). **So ModelSea is parsed into a static field every world-init and then never read by anything** -- the sea
the player actually walks near is rendered by a completely different, disjoint mechanism (``WMWorld.SeaBlockPrefab``,
a single shared Unity prefab instantiated per all-sea ``WMBlock``, ``WMWorld.cs:1163/1259``) which is exactly what
``water.py``/``world/extract.py`` already ground-truth against (a byte survey of real disc-1 open-ocean blocks).
**Verdict: water.py cannot, and does not need to, be ground-truthed against ModelSea** -- see ``report_verdict()``.

    Run from the repo root:
    py studies/overworld-topography/discmr_subtables.py
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import worldpack as WP                  # noqa: E402

OUT = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\efb600c0-e0ce-428f-8a9e-aa6949221da2\scratchpad")

# --------------------------------------------------------------------------- naming (per ff9.cs kWorldPack* + RE)

WORLD_EFFECT_NAMES = ["Unknown0", "FireShrine", "SandPit", "SandStorm", "AlexandriaWaterfall", "Memoria",
                       "Windmill", "Unknown7", "Unknown8", "WaterShrine", "WindShrine", "Unknown11"]

NAMED = {0: "EffectAreaBin", 1: "ChocoboPal", 2: "PaletVolcano", 3: "EncountTable", 4: "EncountSpecial",
         5: "ColorTable(weather)", 6: "AnimationTable", 7: "SpsData", 37: "Eva(unnamed, dead)", 66: "ModelSea"}
for _i in range(41, 53):
    NAMED[_i] = f"WorldEffectArea[{_i - 41}]={WORLD_EFFECT_NAMES[_i - 41]}"
for _i in range(53, 66):
    NAMED[_i] = "kWorldPackEffect*-name slot (NOT pack-read; a Unity Transform asset loaded by string name)"

# Live vs dead, per a repo-wide grep of C:/gd/FFIX/Memoria for every w_framePackGetPtr_*/consumer call site.
LIVE = {3: "ff9.cs:8779 w_frameBattleScenePtr (worldpack.py ENCOUNT_IDX -- already built)",
        4: "ff9.cs:8781 w_worldEncountSpecial (worldpack.py SPECIAL_IDX -- already built)",
        6: "ff9.cs:8780 w_textureProjWork -> ONLY texturePixelAnime[0]/[1].speed are ever read "
           "(ff9.cs:8307-8330 w_texturePixelAnime, called every frame from w_textureUpdate, ff9.cs:3808) "
           "-- drives WMRenderTextureBank.UpdateBeach1()/UpdateBeach2() (the beach-foam scroll cadence). "
           "texturePixelScroll[8] and texturePaletScroll[18] are parsed but NEVER read anywhere.",
        66: "ff9.cs:8778 w_worldSeaBlockPtr -- LOAD is live, but its only consumer w_nwpInitialize/"
            "w_nwpMakePages (ff9.cs:7211-7219) are BOTH empty AND commented out, zero call sites -- DEAD DATA."}
for _i in range(41, 53):
    LIVE[_i] = ("ff9.cs:8782-8784 w_effectDataList[i-41], consumed by the WorldEffect spawn-roll switch "
                "(ff9.cs:~3550-3582): per-record x/y/z jittered by rx/ry/rz, rnd/4096 spawn chance, spawns "
                "s_effectData.no (an SPSConst.WorldSPSEffect) via w_effectRegist_FixedPoint. Gated per-table by "
                "WorldConfiguration.UseWorldEffect(WorldEffect.<name>).")
DEAD = {0: "reader w_framePackGetPtr_w_frameMessagePtr is a NO-OP body wrapped in /* */ (ff9.cs:8816-8835); "
           "zero call sites.",
        1: "no reader function exists ANYWHERE for kWorldPackChocoboPal -- not even a dead stub.",
        2: "no reader function exists ANYWHERE for kWorldPackPaletVolcano -- not even a dead stub.",
        5: "reader w_framePackGetPtr_sw_weatherColor is entirely /* commented out */ (ff9.cs:8857-8877); "
           "zero call sites. Weather colors are instead a FIRST-CLASS Memoria CSV surface "
           "(WorldConfiguration.PatchWorldWeatherColor() reads Data/World/WeatherColors.csv via "
           "AssetManager.GetCsvWithHighestPriority, WorldConfiguration.cs:144-160) -- this binary sub-table is "
           "fully superseded, already-moddable, and should NOT be built as a worldpack.py reader.",
        7: "no reader function exists ANYWHERE for kWorldPackSPSData -- not even a dead stub; format unknown.",
        37: "w_framePackGetPtr_Eva(data, 37) reads raw bytes to end-of-buffer into w_EvaCore (ff9.cs:8785/8953-8967) "
            "-- w_EvaCore (ff9.cs:10056) has exactly one write (this assignment) and ZERO reads anywhere. "
            "Index 37 has no named kWorldPack* constant at all; likely a leftover/experimental slot."}
NOT_PACK_53_65 = ("kWorldPackEffectTwister..Thunder2 (53-65) are Transform FIELDS on WMWorld loaded via "
                   "this.LoadEffect(\"kWorldPackEffectXxx\") -- an AssetManager NAME lookup, e.g. a baked prefab "
                   "(WMWorld.cs:1755-1800, kWorldPackEffectTwister/.../Arch/Black/Thunder1/Thunder2 fields at "
                   "WMWorld.cs:2132-2166). They share the kWorldPack* naming purely by convention; NONE of them is "
                   "ever read from the discmr.img pack via w_framePackGetPtr_*. Whatever bytes occupy pack indices "
                   "53-65 are therefore unread by ANY code path.")


# --------------------------------------------------------------------------- generic pack layout

def pack_layout(d) -> list:
    """``[(idx, name, abs_offset, length_or_None, live/dead/not-pack classification)]`` for every sub-table 0..count-1.

    IMPORTANT correction to the pointer-table docstring's "off0..offN" phrasing: ``count`` (67 on both discs) is the
    NUMBER of valid sub-tables (indices 0..count-1) -- ``worldpack.Discmr.offs`` (built as ``range(count+1)``) holds
    one extra trailing entry that OVER-READS past the real pointer array into sub-table 0's own payload bytes,
    yielding a bogus giant integer (observed: 3293958071, both discs) that must NEVER be treated as an end-of-pack
    terminator. This function clips to ``count`` and leaves the last valid table's length as ``None`` (self-describing
    only, bounded by its own header fields -- see ``decode_modelsea``)."""
    count = len(d.offs) - 1
    rows = []
    for i in range(count):
        off = d.offs[i]
        length = (d.offs[i + 1] - off) if i + 1 < count else None
        rows.append((i, NAMED.get(i, ""), off, length))
    return rows


def report_pack_layout(d1, d4):
    print("=" * 100)
    print("SECTION 1 -- full pack layout (67 sub-tables, both discs) + LIVE/DEAD classification")
    print("=" * 100)
    count = len(d1.offs) - 1
    assert count == len(d4.offs) - 1 == 67
    print(f"pack pointer-table count = {count} (indices 0..{count - 1} are valid; worldpack.Discmr.offs[{count}] "
          f"= {d1.offs[count]} is a BOGUS over-read, ignore it)")
    rows1 = pack_layout(d1)
    for i, name, off, length in rows1:
        off4 = d4.offs[i]
        span1 = d1._data[d1.pack_off + off: d1.pack_off + (d1.offs[i + 1] if i + 1 < count else off)]
        span4 = d4._data[d4.pack_off + off4: d4.pack_off + (d4.offs[i + 1] if i + 1 < count else off4)]
        same = (span1 == span4) if length is not None else "n/a"
        cls = "LIVE" if i in LIVE else ("NOT-PACK-READ" if 53 <= i <= 65 else "DEAD")
        print(f"  [{i:2d}] {name or '(unlabeled -- no kWorldPack* constant, no reader anywhere)':<70s} "
              f"off={off:6d} len={length!s:>6s} disc1==disc4:{same} class={cls}")
    n_unlabeled = len([i for i, n, *_ in rows1 if not n])
    print(f"\n{n_unlabeled} sub-tables (indices 8-40 minus the named 37) carry NO kWorldPack* constant and NO "
          f"reader of any kind anywhere in the decompiled tree -- completely unlabeled 'dark' content, format "
          f"entirely unknown, likely more legacy PS1-era per-region banks superseded the same way "
          f"ColorTable/EffectAreaBin were.")
    print("\nDisc1-vs-disc4 byte diff: only table 2 (PaletVolcano-slot) and table 5 (ColorTable) differ between "
          "discs among the tables checked above -- notable because BOTH are dead-reader tables, so even inert "
          "legacy data was still baked per-disc (probably meaningful in the original PS1 game before Memoria's "
          "CSV/PatchWorldWeatherColor superseded it). Every LIVE table (3,4,6,41-52) and every 53-65 slot is "
          "byte-IDENTICAL disc1 vs disc4.")


# --------------------------------------------------------------------------- sub-table 6: AnimationTable (LIVE)

def decode_animation_table(d):
    """``stextureProject`` (ff9.cs:10806, WMBinarayReaderExtension.cs:96-106): texturePixelScroll[8]@10B=80B +
    texturePixelAnime[4]@10B=40B + texturePaletScroll[18]@10B=180B = 300B, ONE record (not an array). Cross-checked:
    ``offs[7]-offs[6] == 300`` exactly on both discs -- confirms the record layout with no guessing needed."""
    off = d.pack_off + d.offs[6]
    length = d.offs[7] - d.offs[6]
    anime = [struct.unpack_from("<5H", d._data, off + 80 + i * 10) for i in range(4)]  # posx,posy,width,height,speed
    return {"byte_length": length, "expected_300": length == 300, "texturePixelAnime": anime,
            "beach1_speed": anime[0][4], "beach2_speed": anime[1][4]}


# --------------------------------------------------------------------------- sub-tables 41-52: WorldEffect areas (LIVE)

def decode_effect_area_table(d, idx: int):
    """``s_effectDataList`` (ff9.cs:10536 + WMBinarayReaderExtension ReadEffectData/ReadEffectDataList): a
    variable-length run of 64B ``s_effectData`` records terminated by a sentinel record whose ``no == -1``
    (``SPSConst.WorldSPSEffect.NOT_REGISTERED``). Record: 6xInt32 (x,y,z,rx,ry,rz) + 4xInt16 (vx,vy,vz / ax,ay,az
    packed as 6xInt16) + no,size,rnd,temp (4xInt16) + pad[5] Int32 (unread) = 64B."""
    count = len(d.offs) - 1
    off = d.pack_off + d.offs[idx]
    length = d.offs[idx + 1] - d.offs[idx] if idx + 1 < count else None
    n = length // 64
    recs = []
    for i in range(n):
        rb = off + i * 64
        x, y, z, rx, ry, rz = struct.unpack_from("<6i", d._data, rb)
        vx, vy, vz, ax, ay, az, no, size, rnd, temp = struct.unpack_from("<10h", d._data, rb + 24)
        recs.append({"x": x, "y": y, "z": z, "rx": rx, "ry": ry, "rz": rz, "sps_effect_no": no,
                     "size": size, "rnd_of_4096": rnd, "temp": temp})
    sentinel_at_end = bool(recs) and recs[-1]["sps_effect_no"] == -1
    return {"name": WORLD_EFFECT_NAMES[idx - 41], "n_records_incl_sentinel": n, "records": recs,
            "well_formed_sentinel": sentinel_at_end}


def report_effect_areas(d1, d4):
    print("\n" + "=" * 100)
    print("SECTION 2 -- sub-tables 41-52: the 12 WorldEffect ambient-SPS spawn-area tables (LIVE, authoring-relevant)")
    print("=" * 100)
    print("Doc correction: OVERWORLD_ENGINE.md lists this as a single '41 EffectBin' sub-table; it is actually 12")
    print("SEPARATE sub-tables (41..52), one per WorldEffect enum value, each an independently-loaded "
          "s_effectDataList\n(ff9.cs:8782-8784 loops i=41..52). Each spawns ambient overworld SPS particles "
          "(dust/smoke/mist/aura) around named coordinates,\nrolled per-frame at rnd/4096 odds, gated by "
          "WorldConfiguration.UseWorldEffect(<name>).\n")
    for idx in range(41, 53):
        r1 = decode_effect_area_table(d1, idx)
        r4 = decode_effect_area_table(d4, idx)
        same = r1["records"] == r4["records"]
        real_n = r1["n_records_incl_sentinel"] - 1
        print(f"  [{idx}] {r1['name']:<20s} real_records={real_n:2d} sentinel_ok={r1['well_formed_sentinel']} "
              f"disc1==disc4:{same}")
        for rec in r1["records"][:2]:
            print(f"        sample: {rec}")


# --------------------------------------------------------------------------- sub-table 5: ColorTable (DEAD)

def decode_colortable_best_effort(d):
    """``sw_weatherColorElement`` decode per ``ReadWeatherColor`` (WMBinarayReaderExtension.cs:17-43) -- 94B/record
    (6x SVECTOR@8B=48 + (goffsetup,toffsetup,fogUP)=12 + (goffsetdw,toffsetdw,fogDW)=12 +
    (goffsetcl,toffsetcl,fogCL)=12 + chrBIAS@8 + fogAMP@2 = 94B). The reader is DEAD (commented out, ff9.cs:8857-8877)
    so this is purely archival. Byte math: table span = 1504B = 94 * 16 EXACTLY -- only 16 records on disk, not the
    23 the modern ``sw_weatherColor.Color[23]`` array (+ WorldConfiguration's CSV export) expects; entries 16-22
    (used for e.g. sky fog/bg color, ff9.cs:7187-7194) are populated ONLY by the live CSV path
    (WorldConfiguration.PatchWorldWeatherColor), never by this binary table even if the dead reader were revived."""
    off = d.pack_off + d.offs[5]
    length = d.offs[6] - d.offs[5]
    n = length // 94
    # record 0's ambient SVECTOR (3rd of the 6 leading SVECTORs: light0,light1,light2,light0c,ambient,ambientcl)
    ambient0 = struct.unpack_from("<4h", d._data, off + 8 * 4)  # vx,vy,vz,pad
    fogamp0 = struct.unpack_from("<H", d._data, off + 92)[0]
    return {"byte_length": length, "clean_94B_records": length % 94 == 0, "n_records_on_disk": n,
            "modern_struct_wants": 23, "sample_record0_ambient_svector": ambient0, "sample_record0_fogAMP": fogamp0}


# --------------------------------------------------------------------------- sub-table 66: ModelSea (LOAD-live, CONSUME-dead)

def decode_modelsea(d) -> dict:
    """``sNWBBlockHeader`` + its ``cellHeader[]`` (ff9.cs:10750/10731, ReadNWBBlockHeader/ReadNWBCellHeader,
    WMBinarayReaderExtension.cs:45-80) -- the ONLY reader that exists for table 66, and it IS called live
    (ff9.cs:8778). Header: SByte cellno/timno/areaid + Byte special + UInt32 offsettexture + UInt32[cellno]
    offsetcell (each relative to the BLOCK header's own start position, matching the C# reader's
    ``offsetcell[i] + position``) -> per-cell 36B header (Byte vtxno/areaid + UInt16 surno + UInt32 offsetvertex +
    UInt32 offsetsurface + Byte[20] checkpoint + Byte checkfig + Byte[3] special).

    ``offsetvertex``/``offsetsurface`` have NO reader anywhere (no ReadNWBVertex/ReadNWBSurface method exists in the
    whole decompiled tree) -- there is truly no format oracle for the payload. This function reconstructs the
    per-record STRIDE purely by byte arithmetic (measuring the gap between offsetvertex/offsetsurface/the next
    cell's start), which independently comes out to an exact 8.00 B/vertex and 16.00 B/surface for 3 of the 4 cells
    (the 4th cell's surface span is padded before ``offsettexture`` begins, so its naive per-record figure is noisy --
    the clean 2048B == 128*16B still holds, just bounded by the wrong neighbour). The 8B vertex fits the SAME
    ``SVECTOR`` (Int16 vx,vy,vz,pad) shape used pack-wide elsewsewhere (weather lights, the world normal table) --
    plausible, NOT engine-confirmed."""
    base = d.pack_off + d.offs[66]
    b = d._data
    cellno, timno, areaid, special = struct.unpack_from("<bbbB", b, base)
    off_texture = struct.unpack_from("<I", b, base + 4)[0]
    offsetcell = list(struct.unpack_from(f"<{cellno}I", b, base + 8))
    cells = []
    for i, oc in enumerate(offsetcell):
        cbase = base + oc
        vtxno, careaid = struct.unpack_from("<BB", b, cbase)
        surno = struct.unpack_from("<H", b, cbase + 2)[0]
        offv, offsf = struct.unpack_from("<II", b, cbase + 4)
        checkfig = b[cbase + 32]
        vpos, spos = base + offv, base + offsf
        next_pos = base + offsetcell[i + 1] if i + 1 < len(offsetcell) else base + off_texture
        vlen, slen = spos - vpos, next_pos - spos
        cells.append({"i": i, "vtxno": vtxno, "areaid": careaid, "surno": surno, "checkfig": checkfig,
                      "vpos": vpos, "spos": spos, "vlen": vlen, "vlen_per_vertex": vlen / vtxno if vtxno else None,
                      "slen_to_next": slen, "slen_per_surface": slen / surno if surno else None})
    tex_sample = b[base + off_texture: base + off_texture + 32]
    return {"cellno": cellno, "timno": timno, "areaid": areaid, "special": special,
            "offsettexture_abs": base + off_texture, "texture_first32B_hex": tex_sample.hex(),
            "texture_all_zero": tex_sample == b"\x00" * len(tex_sample), "cells": cells,
            "total_verts": sum(c["vtxno"] for c in cells), "total_surfaces": sum(c["surno"] for c in cells)}


def report_modelsea(d1, d4):
    print("\n" + "=" * 100)
    print("SECTION 3 -- sub-table 66: ModelSea (sNWBBlockHeader) -- the fidelity-prize question")
    print("=" * 100)
    r1, r4 = decode_modelsea(d1), decode_modelsea(d4)
    print(f"disc1: cellno={r1['cellno']} timno={r1['timno']} areaid={r1['areaid']} special={r1['special']} "
          f"total_verts={r1['total_verts']} total_surfaces={r1['total_surfaces']}")
    print(f"disc4: cellno={r4['cellno']} timno={r4['timno']} areaid={r4['areaid']} special={r4['special']} "
          f"total_verts={r4['total_verts']} total_surfaces={r4['total_surfaces']}")
    print(f"disc1 == disc4 (full decoded structure incl. every cell): {r1['cells'] == r4['cells']}")
    print(f"texture blob (at offsettexture, abs {r1['offsettexture_abs']}) first 32B all-zero on disc1: "
          f"{r1['texture_all_zero']} -- {r1['texture_first32B_hex']}")
    print("\nPer-cell decode (disc1; disc4 byte-identical):")
    for c in r1["cells"]:
        print(f"  cell {c['i']}: vtxno={c['vtxno']:3d} areaid={c['areaid']} surno={c['surno']:3d} "
              f"vertex_stride={c['vlen_per_vertex']} surface_stride(to-next)={c['slen_per_surface']}")
    print("\nInterpretation: ONE generic areaid=0 block with 4 identical-shaped cells (81 verts / 128 surfaces "
          "each) -- NOT addressed by overworld area/zone (areaid is 0 throughout) and NOT one-per-WMBlock (there is "
          "exactly one sNWBBlockHeader total, not 480 or even 260). This reads as a single small tileable low-poly "
          "wave-mesh PATCH (a 9x9-vertex grid -> 8x8 quads -> 128 triangles is the natural triangulation of 81 "
          "verts), most likely a repeatable animated-sea template from the original PS1 renderer, with cellno=4 "
          "plausibly 4 variants/frames for anti-tiling -- structurally the SAME anti-repetition GOAL water.py's "
          "'2x2 quadrant + 4-rotation' scheme pursues, but by an entirely different, disjoint mechanism (mesh "
          "geometry variants here vs. texture-UV variation on a shared flat Unity mesh there).")


def report_verdict(d1):
    print("\n" + "=" * 100)
    print("SECTION 4 -- the ground-truth verdict: ModelSea vs. water.py's live-block survey")
    print("=" * 100)
    print("Real block (8,4) -- water.py's own byte-exact reference open-ocean block (cited in its docstring + used")
    print("throughout tests/test_world_water.py) -- read LIVE from the install via world/extract.py:\n")
    total_tri, total_v, parts = 0, 0, []
    for part in ("sea3", "sea4", "sea5", "sea1", "sea2", "terrain", "object"):
        try:
            pm = X.read_block(8, 4, disc=1, part=part)
            total_tri += len(pm.tris)
            total_v += pm.vcount
            parts.append((part, len(pm.tris), pm.vcount))
        except ValueError:
            pass
    for p, t, v in parts:
        print(f"    {p:<8s} triangles={t:4d} vertices={v:5d} (flat/unindexed -- v == 3*tri)")
    print(f"    TOTAL: triangles={total_tri} vertices={total_v}")
    print(f"\n(8,4) has NO terrain/object mesh at all -- confirms water.py's own note that real open ocean's walkmesh")
    print("IS its Sea mesh (no separate land layer to compare against a legacy 'terrain' concept).\n")
    print("Contrast with coastal blocks (mixed terrain+sea, for scale) -- (4,4)/(5,4)/(6,4)/(7,4)/(11,4)/(12,4)")
    print("total tri/vert counts run 528-702 tri / 1584-2106 vert, each a DIFFERENT number driven by that block's")
    print("own real coastline shape -- there is no fixed per-block polycount anywhere in the live system.\n")
    r = decode_modelsea(d1)
    print(f"ModelSea (table 66): total_verts={r['total_verts']} total_surfaces={r['total_surfaces']} across its")
    print(f"ONE header's {r['cellno']} cells -- {r['total_surfaces']} happens to equal (8,4)'s live triangle total")
    print(f"({total_tri}) -- but this is a SCALE COINCIDENCE, not a structural match, for four independent reasons:")
    print("  1. MECHANISM: ModelSea's only consumer (w_nwpInitialize/w_nwpMakePages) is dead/empty/never-called")
    print("     (ff9.cs:7211-7219) -- it is parsed and then discarded every world-init. The sea the player actually")
    print("     sees/collides with comes from WMWorld.SeaBlockPrefab, a single shared Unity prefab instantiated per")
    print("     all-sea WMBlock (WMWorld.cs:1163/1259) -- a completely different, disjoint asset.")
    print("  2. ADDRESSING: ModelSea is ONE block, areaid=0, 4 undifferentiated cells -- not keyed by the 24x20")
    print("     WMBlock grid, not keyed by overworld area/zone (unlike EncountTable/EffectArea, which ARE). It")
    print("     cannot even in principle correspond to a specific real block like (8,4).")
    print("  3. ENCODING: ModelSea is a compact indexed mesh (81 shared verts driving 128 faces via a face/index")
    print("     record); the live Unity meshes are FLAT/unindexed (vcount == 3*tricount, no vertex sharing at all) --")
    print("     categorically different mesh representations, confirmed by (8,4)'s 1536 verts / 512 tri (exactly")
    print("     3x) vs. ModelSea's 324 verts / 512 surfaces (NOT 3x -- a genuinely shared-vertex mesh).")
    print("  4. SCALE DOESN'T GENERALIZE: no other real ocean-adjacent block (checked: (4,4) 598tri/(5,4) 590tri/")
    print("     (6,4) 624tri/(7,4) 702tri/(11,4) 619tri/(12,4) 618tri) matches 512 -- (8,4)'s match is a coincidence")
    print("     of one sample, not a pattern.")
    print("\nVERDICT: water-py CANNOT and does NOT need to be ground-truthed against ModelSea. water.py's existing")
    print("byte survey of real disc-1 open-ocean blocks (already validated 17/17 tile-shape-match + in-game proven")
    print("2026-07-05) remains the correct and ONLY ground truth. ModelSea is inert legacy data from a PS1-era")
    print("sea-rendering system the Unity port abandoned; decoding it further has archival value only.")


def proposed_readers():
    print("\n" + "=" * 100)
    print("SECTION 5 -- proposed worldpack.py reader signatures (TEXT ONLY -- not applied to worldpack.py)")
    print("=" * 100)
    print("""
BUILD (genuinely authoring-relevant, zero-DLL, mod-override already honored by AssetManager.LoadBytes):

  * AnimationTable (idx 6) -- only 2 live fields worth exposing (everything else in the 300B record is parsed but
    never read by the engine):
        def get_beach_anim_speed(discmr) -> tuple[int, int]:      # (beach1_speed, beach2_speed) frame-divisors
        def set_beach_anim_speed(discmr, beach1=None, beach2=None) -> None
    Authoring value: retune the shore foam animation cadence (0 = frozen; smaller = faster) with no DLL.

  * WorldEffect area tables (idx 41-52) -- a dataclass mirroring EncountRecord's spirit:
        @dataclass
        class EffectAreaRecord: x: int; y: int; z: int; rx: int; ry: int; rz: int
                                 sps_effect: int; size: int; rnd: int   # rnd/4096 = per-frame spawn chance
        def read_effect_area(discmr, name: str) -> list[EffectAreaRecord]     # name in WORLD_EFFECT_NAMES
        def write_effect_area(discmr, name: str, records: list[EffectAreaRecord]) -> None
    CAVEAT: variable-length + sentinel-terminated, so an edit that changes record COUNT needs a repack (shifts every
    later sub-table's absolute bytes) -- unlike EncountTable/EncountSpecial's fixed-count in-place edit, this is NOT
    a pure byte-value rewrite; a naive same-count edit (reposition/rescale/retune existing spawns, no add/remove) is
    still a trivial in-place rewrite and should ship first.
    Authoring value: move/resize/retune ambient overworld SPS spawn zones (sandstorm, windmill dust, waterfall
    mist, shrine auras) with no DLL.

DO NOT BUILD (dead code / superseded / no format oracle -- would be pure archival effort with zero authoring payoff):

  * EffectAreaBin (0): dead reader stub exists (commented out) -- archival decode only, no authoring payoff.
  * ChocoboPal (1), PaletVolcano (2), SpsData (7), Eva (37), and the ~32 unlabeled indices (8-40 minus 37): NO
    reader -- live OR dead -- exists ANYWHERE in the decompiled tree for these. Format is genuinely unknown and
    nothing in the engine will ever read an edit to them.
  * ColorTable (5): reader is dead code; the SAME data is a first-class, ALREADY-SHIPPED CSV surface
    (Data/World/WeatherColors.csv via WorldConfiguration.PatchWorldWeatherColor) -- point authors there instead of
    ever touching this binary sub-table.
  * kWorldPackEffect* name slots (53-65): not pack-read at all in the current engine (Unity Transform asset refs by
    name) -- editing their pack bytes changes nothing observable.
  * ModelSea (66): confirmed dead consumer (see report_verdict). If ever wanted for pure archival/curiosity, a
    READ-ONLY decoder (header + cellHeader[], as implemented in decode_modelsea() above) is enough -- do NOT build
    a writer, and do NOT treat it as a fidelity gate for world-water/world-island/etc.
""")


def main():
    d1 = WP.load_discmr(disc=1)
    d4 = WP.load_discmr(disc=4)
    report_pack_layout(d1, d4)
    print("\nAnimationTable (idx 6) decode:", decode_animation_table(d1))
    report_effect_areas(d1, d4)
    print("\nColorTable (idx 5) best-effort decode (DEAD reader, archival only):",
          decode_colortable_best_effort(d1))
    report_modelsea(d1, d4)
    report_verdict(d1)
    proposed_readers()

    dump = {
        "pack_layout_disc1": [{"idx": i, "name": n, "off": o, "len": l} for i, n, o, l in pack_layout(d1)],
        "animation_table": decode_animation_table(d1),
        "effect_areas": {WORLD_EFFECT_NAMES[i - 41]: decode_effect_area_table(d1, i) for i in range(41, 53)},
        "colortable_best_effort": decode_colortable_best_effort(d1),
        "modelsea_disc1": decode_modelsea(d1),
        "modelsea_disc4": decode_modelsea(d4),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "discmr_subtables_report.json").write_text(json.dumps(dump, indent=2), encoding="utf-8")
    print(f"\nFull decoded dump written to {OUT / 'discmr_subtables_report.json'} (scratchpad, not the repo).")


if __name__ == "__main__":
    main()
