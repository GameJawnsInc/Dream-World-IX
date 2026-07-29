r"""TIER W rung W6b-3 -- THE ARCHIVE RUNG'S OWN GATE RUNNER.  `py w6b3_gates.py` prints G0..G9.

W6b-2 closed with **2,139** scenery page-cells still DEPTH-UNKNOWN and named an id-2 ARCHIVE MODEL as
the most plausible reader behind W6b-1's three in-game depth surprises.  W6b-3 tested that hypothesis.
The hypothesis's PREMISE is FALSE -- `reskin.attribution` already walks every sub-file id -- and the
real blindness is in the RECORD READER: the `so` record is a MULTI-PART BINDING ARRAY and
`reskin.so_record` probes only two lengths, so **126 records and all 309 of their binding slots** are
invisible to the kit.  THIS FILE RE-MEASURES EVERY NUMBER `W6b3-ARCHIVE.md` sec 0-8 states, from the
corpus and the SCRATCH lane artifacts, so the record quotes nothing it cannot re-derive:

G0  CALIBRATE THE INSTRUMENT BEFORE JUDGING WITH IT.  This file's own tpage decoder against
    `reskin`'s field extraction over all 512 nine-bit words; then TWO KNOWN ANSWERS re-found before
    anything is believed -- KA1 ef211's column-704 binding (THE DOME's own column, w6b2_gates H0's
    first known answer) and KA2 the ef226 outlier `reskin.so_record`'s OWN docstring names by offset
    AND value; then slot 0 == `so_record` on 340/340 and the population `attribution` publishes.
    ⚠ AND THE LIMIT OF ALL FOUR IS PRINTED: none of them evaluates a byte only the NEW reading
    reaches (refuter 1 finding #3).  The rung with power over a P>=2 byte is G6's CLUT-arity test.
G1  THE POPULATION AND THE FORMAT.  981 non-creature GEOM blocks by resource; 502 records / 649
    slots / 126 invisible records / 309 invisible slots; the part-count histogram; `arrayB == 8+4P`
    (the INDEPENDENT halfword -- `recLen == 8+8P` is near-tautological and is flagged as such);
    `recordBase + recLen == geomBase`; the recordless residue closing 502 + 444 + 35 = 981; the
    container counts; and TWO of L1's stated numbers CORRECTED (36/36 not 37/37, 465/465 not 465/466).
G2  THE HYPOTHESIS'S PREMISE, FALSIFIED.  `EC.scan_geom` is a whole-blob needle scan with no
    resource filter, so the census walker already descends into the id-2 archive: the kit's own
    bindings are mapped back to their owning resource here, WITHOUT re-implementing the walker.
G3  THE SWEEP AND THE REACH.  109 declared cells (106 scenery + 3 CREATURE -- the pivot that
    explains both L1's 106 and its "cells the container NEVER UPLOADS"); 73 new-vs-all-channels;
    65 unanimous + 8 dual; the channels re-derived LIVE (P from the shipped table, G from the
    containers); every double-count check; and the residue arithmetic closing 2,385 = 246 + 2,139
    = 1,278 + 861 with the reach's ACTUAL movement on it stated.
G4  THE GHOST-LAYER VERDICT, SCORED PREDICTION BY PREDICTION.  ef446 / ef251 / ef429, three
    predicates each (declared column, UV cover on CORRECTED UVs, spill target), plus the two
    containers' recordless populations.  0 hits, 4 misses, 2 vacuous passes.
G5  CONFLICTS, AGREEMENT, AND THE BASE RATE THE AGREEMENT MUST BEAT.  The comparable set under BOTH
    definitions (22 and L2's 21); the FLAT contradictions by name with both predicates; and refuter
    2's TAUTOLOGY CONTROL, which the agreement statistic does not clear.
G6  THE CONTROLS -- a reading never contrasted with a wrong one is an assertion.  L1's four; refuter
    1's three added nulls; refuter 2's part-byte range test (the first check from OUTSIDE the
    record's own header); the critic's SPLIT-ARRAY control (the alternative the game's own creature
    header motivates); and ★ THE CLUT-ARITY TEST -- the round's only calibration with power over a
    P>=2 byte, with its own four nulls.
G7  THE DEFLATION.  65 -> 26 clean, and why the census's own multi-palette flag is VACUOUS here;
    plus the SAFETY finding -- five palettes the SHIPPED kit publishes as DERIVED PRIVATE that a
    dropped record contradicts.
G8  THE CRITIC'S CORRECTIONS, RE-MEASURED.  The UV cover read off the pool INDEX rather than the
    pool (calibrated against `repaint.bound_models` FIRST); five of the 65 relabelled from inherited
    to DIRECT; the wall re-tested from the other side; and the archive directory shown to be
    residency, not a draw reference.
G9  PROVENANCE: an AST-level byte-constant scan of every NEW file `git status` reports.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format and the lane artifacts under
texel-w6b\w6b3\ ONLY -- no install read, NO deploy, no install write, no git commit.  ~1 min.
"""
from __future__ import annotations

import json
import os
import random
import re
import struct
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402
from ff9mapkit.summons import depth_attribution as DA            # noqa: E402

#: THE SANCTIONED PARSER, reached the way every W6b lane reaches it -- `reskin`'s own re-export of
#: the kit's `ff9mapkit.summons.container`, so this file and the kit read one parser, not two.
EC = RS.EC

CORPUS = W.SCRATCH_CORPUS
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
W6B = os.path.join(SCRATCH, "texel-w6b")
LANE = os.path.join(W6B, "w6b3")

#: A VRAM tpage names a 64-halfword x 256-line PAGE; a census page-cell is 64 x 128.  One tpage word
#: therefore covers the TWO STACKED CELLS of its column -- W6b-2 sec 1's granularity statement.
PAGE_HW, PAGE_LINES, CELL_LINES = 64, 256, 128
SO_MAGIC = 0x6F73
_NEEDLE = b"\x73\x6f"           # 'so' little-endian -- 2 bytes, far under any provenance threshold

# --------------------------------------------------------------------------- THE PINS
#: Every number `W6b3-ARCHIVE.md` sec 0-8 is allowed to quote.  Each is RE-MEASURED in the gate body
#: and compared here.  A pin that only matched a prose table would be the thing this house forbids.
PIN = {
    # -- G0 calibration
    "decoder_words": 512,
    "ka1_tpage": 155, "ka1_page": (704, 256, 8), "ka1_slots": 1,
    "ka2_at": 0x9C7F4, "ka2_textured": 0, "ka2_tpage": 0x97, "ka2_clut": 0x3E00, "ka2_P": 1,
    "r3_slot0_matches": 340,
    "r4_accepted": 376, "r4_tpage_bearing": 340,
    "ka_rungs_touching_a_p2_byte": 0,        # ★ refuter 1 finding #3, re-measured not restated
    "ef211_p2_records": 0,                   # KA1's vehicle has NO multi-part record at all
    # -- G1 population + format
    "containers": 372,
    "geoms": 981, "creature_geoms": 24,
    "geom_by_res": {2: 658, 6: 282, 8: 20, 3: 12, 10: 9},
    "records": 502, "slots": 649,
    "invisible_records": 126, "invisible_slots": 309,
    "p_hist": {0: 36, 1: 340, 2: 98, 3: 12, 4: 6, 5: 8, 6: 1, 7: 1},
    "records_by_res": {2: 252, 6: 209, 8: 20, 3: 12, 10: 9},
    "inv_records_by_res": {2: 61, 6: 53, 3: 12},
    "inv_slots_by_res": {2: 127, 6: 158, 3: 24},
    "arrayB_ok": 502, "reclen_lands_on_geom": 502,
    "recordless": 479, "recordless_uv": 444, "recordless_nouv": 35,
    "recordless_uv_by_res": {2: 374, 6: 70},
    "cont_geom_in_id2": 145, "cont_id2_resource": 372,
    "cont_id2_record": 72, "cont_any_record": 80, "cont_invisible_record": 28,
    "textured_iff_p_ge1": 501,
    "direct15_clut_zero": 69,
    "inv_slot_depths": {4: 74, 8: 190, 15: 45},
    "all_slot_depths": {4: 187, 8: 393, 15: 69},
    "p0_zero_uv": 36,                        # L1 sec 1.3 F4 quoted "37/37"; there are 36 P==0 records
    "p0_records": 36,
    "textured_tight": 465,                   # L1 sec 1.3 F2t quoted "465/466"
    "max_reclen": 64,
    "shadowed_geoms": 0,                     # >1 passing candidate anywhere -- L1's open caveat, closed
    "wide_window_extra": 0,                  # 0x10000 window, no resource floor -> 0 more on 981/981
    "resources_by_id": {0: 385, 1: 316, 2: 385, 3: 385, 9: 37, 4: 24, 5: 24, 6: 24, 7: 13,
                        10: 4, 8: 1},
    "containers_by_res_id": {0: 372, 1: 236, 2: 372, 3: 372, 9: 28, 4: 24, 5: 24, 6: 23, 7: 11,
                             10: 2, 8: 1},
    # -- G2 the premise
    "resource_2_name": "SUBFILE_ARCHIVE",
    "kit_bind_by_res": {2: 175, 6: 137, 8: 20, 10: 8},
    "kit_id2_containers": 60,
    "kit_none_on_p2": 126,
    "geoms_unowned_by_the_walker": 0,
    # -- G3 sweep + reach
    "declared_cells": 109,
    "declared_by_class": {"id0": 87, "id9": 19, "creature": 3},
    "scenery_cells": 106,
    "undeclared_cells": 7, "undeclared_slot_hits": 61,
    "census_rows": 2665, "census_scenery": 2572, "census_unknown": 2385,
    "p_rows": 221, "p_unanimous": 199, "p_dual": 22, "p_gain": 189,
    "g_gain": 57, "g_dual": 8,
    "new_strict": 73, "new_unanimous": 65, "new_dual": 8,
    "new_lower_halves": 31, "id2_only_gain": 31,
    "new_depths": {4: 15, 8: 46, 15: 4},
    "overlap_pg": 0, "overlap_pa": 0, "overlap_ga": 0, "overlap_a_census": 0,
    "gain_union": 319,
    "residue": 2139, "residue_blind": 1278, "residue_covered": 861,
    "blind_containers": 222,
    "blind_with_id2_resource": 222, "blind_with_nonempty_id2_dir": 222, "blind_with_geom_in_id2": 0,
    "archive_in_blind": 0,
    "residue_after_73": 2066, "residue_after_65": 2074, "residue_after_26": 2113,
    "covered_after_73": 788,
    # -- G4 the ghost layer
    "ef446_records": 5, "ef446_invisible": 0, "ef446_recordless_uv": 0, "ef446_geoms": 5,
    "ef446_col448_invisible_slots": 0, "ef446_col448_depths": (15,),
    "ef446_8bpp_geom": 0x2C094, "ef446_8bpp_page": (704, 256),
    "ef251_records": 0, "ef251_invisible": 0, "ef251_recordless_uv": 38, "ef251_geoms": 38,
    "ef251_recordless_by_res": {6: 35, 2: 3},
    "ef251_col512_slots": 0,
    "ef429_records": 1, "ef429_invisible": 0, "ef429_recordless_uv": 0, "ef429_geoms": 1,
    "ef429_col448_depths": (15,),
    "ghost_hits": 0, "ghost_misses": 4, "ghost_vacuous": 2,
    "spill_ef446_slots": 1, "spill_ef251_slots": 0, "spill_ef429_slots": 1,
    "uvcover_hits": 0,
    "census_15bpp_scenery": 14, "census_15bpp_probed": 6,
    "ef390_slots": 32, "ef390_slots_448_256": 20, "ef390_448_declared": False,
    "writer_records_total": 2741, "writer_records_in_id2": 0,
    "writers_by_res": {0: 2531, 4: 93, 9: 117},
    # -- G5 conflicts + agreement + the base rate
    "comparable_22": 22, "comparable_21": 21,
    "agree": 17, "flat_census": 1,
    "vs_g_n": 33, "vs_g_agree": 25, "vs_g_compatible": 6, "vs_g_flat": 2,
    "taut_columns": 65, "taut_single_depth": 51, "taut_rate": 0.7846,
    "corpus_columns_bound": 162, "corpus_columns_single_depth": 141,
    "archive_multivalued": 12,
    "safety_cells": 5,
    "ef184_visible_geom": 0x86BFC, "ef184_visible_rec": 0x86BEC, "ef184_visible_tpage": 23,
    "ef184_invisible_geom": 0x7B2E0, "ef184_invisible_rec": 0x7B2C8, "ef184_invisible_tpage": 151,
    "ef184_records": 9, "ef184_id2_records": 0,      # L1 sec 1.4's example is res_id 6, not id-2
    # -- G6 the controls
    "ctrl_shipped": 279, "ctrl_stride8": 144, "ctrl_phase2": 0, "ctrl_inrecord_null": 0,
    "ctrl_n": 309,
    "null_random_hw": 62,                    # THIS file's own seeded re-roll of refuter 1's null
    "part_records_checked": 502, "part_violations": 0,
    "part_hist": {0: 465, 1: 126, 2: 28, 3: 16, 4: 10, 5: 2, 6: 1},
    "part_records_with_parts": 465,
    "stride8_falsified_records": 126,
    "split_declared_col": 146, "split_legal": 194, "interleaved_legal": 309,
    "clut_n": 264, "clut_agree": 264, "clut_disagree": 0,
    "clut_exact_word": 264, "clut_bucket_ok": 264, "clut_single_arity": 264, "clut_dual_arity": 0,
    "clut_all_agree": 576, "clut_all_disagree": 0, "clut_all_direct15": 69,
    "clut_all_unresolvable": 4, "clut_unresolvable_kit_visible": 4,
    "clut_null_random_in_list": 429, "clut_null_random_trials": 2640,
    "clut_null_inrecord": 0, "clut_split_in_list": 147, "clut_split_bucket": 85,
    "clut_ambient": 0.5331,
    "magic_total": 1355, "corpus_bytes": 72069120,
    # -- G7 the deflation
    "reach_clean": 26, "reach_class_c": 34, "reach_program_write": 7,
    "reach_attribution_blind": 40, "reach_not_blind": 25,
    "reach_readerless": 65, "reach_census_multi_palette": 0,
    "reach_15bpp": 4,
    "cast_vehicles": 4,                      # clean AND directly sampled -- sec 8.3's shortlist
    "false_private": 5, "n_private": 107, "n_shared": 87, "n_unknown": 2600,
    "unknown_gains": 83, "complete_flips": 19,
    # -- G8 the critic's corrections
    "uv_cal": 41,
    "uv_damage_vy": 648, "uv_damage_hx": 627, "uv_slots_boxed": 648,
    "uv_broken_v_max": 7, "uv_true_v_max": 255,
    "direct_lower_slots": 24, "direct_lower_cells": 12, "direct_lower_in_the_65": 5,
    "wall_magic_sites": 934, "wall_shape_valid": 502, "wall_target_geom": 502,
    "wall_target_not_geom": 0,
    "wall_blind_magic": 164, "wall_blind_shape_valid": 0,
    "dir_entries": 7872, "dir_neg": 22, "dir_geoms_named": 360, "dir_records_named": 253,
    "dir_named_by_res": {2: 252, 10: 1},
    "dir_ef429": 1, "dir_ef446": 5, "dir_ef390": 22, "dir_ef211": 5,
    "order_records": 50, "order_parts": 109, "order_identity": 69, "order_reversed": 61,
    "order_multi_tpage": 82,                 # why the unmeasured ORDER clause is load-bearing
}

_FAILS: List[str] = []


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; collect rather than raise, so the board prints."""
    if isinstance(want, float):
        ok = abs(got - want) < 5e-3
    else:
        ok = got == want
    if not ok:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


# --------------------------------------------------------------------------- shared derivations
def u16(b: bytes, o: int) -> int:
    return b[o] | (b[o + 1] << 8)


def dec(tp: int) -> Tuple[int, int, int]:
    """(page_x, page_y, bpp) from a nine-bit PSX tpage word -- written from the bit layout."""
    return (tp & 0x0F) * PAGE_HW, ((tp >> 4) & 1) * PAGE_LINES, RS.SO_BPP[(tp >> 7) & 3]


def cover(px: int, py: int) -> List[Tuple[int, int]]:
    """THE GRANULARITY STATEMENT, in code: a page covers both stacked 128-line cells of its column."""
    return [(px, py), (px, py + CELL_LINES)]


def verdict(vals) -> Optional[int]:
    """A depth is stated only if the evidence is UNANIMOUS; two values is a hazard, not a vote."""
    s = set(vals)
    return next(iter(s)) if len(s) == 1 else None


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _records(blob: bytes, geoms: List[int]) -> List[dict]:
    """THE MULTI-PART RECORD READER.  Direct probe of the self-describing length, accepted on THREE
    halfwords: magic, `recLen` landing exactly on the GEOM base, and `arrayB == 8 + 4P` -- the
    INDEPENDENT one (`recLen == 8+8P` is near-tautological given P := (recLen-8)//8)."""
    out = []
    for g in geoms:
        for P in range(0, 128):
            rl = 8 + 8 * P
            o = g - rl
            if o < 0:
                break
            if (u16(blob, o) == SO_MAGIC and u16(blob, o + 4) == rl
                    and u16(blob, o + 6) == 8 + 4 * P):
                out.append({"at": o, "reclen": rl, "arrayB": 8 + 4 * P, "npart": P,
                            "textured": u16(blob, o + 2), "geom": g})
                break
    return out


def _iv(blob: bytes, r: dict) -> List[Tuple[int, int]]:
    """The SHIPPED interleaved reading: P x {u16 tpage, u16 clut} at +0x08, stride 4."""
    return [(u16(blob, r["at"] + 8 + 4 * k), u16(blob, r["at"] + 8 + 4 * k + 2))
            for k in range(r["npart"])]


def _split(blob: bytes, r: dict) -> List[Tuple[int, int]]:
    """THE CONTROL WITH A PROVENANCE ARGUMENT: the id-4 CREATURE header stores tpage[P] then clut[P]
    as two separate arrays.  Consumes the same 4P bytes, ends at the same arrayB, and at P==1 is
    byte-identical -- so no header field can discriminate it and nobody had scored it."""
    P = r["npart"]
    return [(u16(blob, r["at"] + 8 + 2 * k), u16(blob, r["at"] + 8 + 2 * P + 2 * k))
            for k in range(P)]


def _uv_boxes(blob: bytes, g) -> Dict[int, List[int]]:
    """{part: [u_lo,u_hi,v_lo,v_hi,nfaces]} -- DEREFERENCED through the mesh's UV POOL, which is what
    `repaint.bound_models` does and what both prior lanes did NOT (they applied the right arithmetic
    to the pool INDEX).  Calibrated against the kit's own answer in G8 before it is used."""
    box: Dict[int, List[int]] = defaultdict(lambda: [1 << 30, -1, 1 << 30, -1, 0])
    for mesh in g.meshes:
        pool = g.base + mesh.p_uv
        for pr in EC.iter_primitives(blob, g, mesh):
            uvs = pr.get("uv")
            if not uvs or "part" not in pr:
                continue
            cv = box[pr["part"]]
            for ui in uvs:
                w = struct.unpack_from("<H", blob, pool + 2 * ui)[0]
                uu, vv = w & 0xFF, (w >> 8) & 0xFF
                cv[0] = min(cv[0], uu)
                cv[1] = max(cv[1], uu)
                cv[2] = min(cv[2], vv)
                cv[3] = max(cv[3], vv)
            cv[4] += 1
    return box


class Data:
    """One pass over the 372-container corpus, plus the census and the lane artifacts."""

    def __init__(self) -> None:
        self.census = _load(os.path.join(W6B, "census", "pages.json"))
        self.C = {(r["ef"], r["vram_x"], r["vram_y"]): r for r in self.census}
        self.paths = W.corpus_paths()
        self.blobs: Dict[int, bytes] = {}
        self.recs: List[dict] = []
        self.slots: List[dict] = []
        self.geom_by_res = Counter()
        self.creature_geoms = 0
        self.recordless = {"uv": Counter(), "nouv": 0, "total": 0}
        self.declared_cells: Dict[int, set] = {}
        self.declared_cols: Dict[int, set] = {}
        self.pal_by_cell: Dict[int, Dict[tuple, set]] = {}
        self.word_arity: Dict[int, Dict[int, set]] = {}
        self.pal_entries: Dict[int, List[int]] = {}
        self.kit_bind_by_res = Counter()
        self.kit_id2_containers = set()
        self.sopage: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
        self.blind: Dict[int, bool] = {}
        self.res_ids: Dict[int, set] = {}
        self.resources_by_id = Counter()
        self.containers_by_res_id = Counter()
        self.geoms_by_ef: Dict[int, List[int]] = {}
        self.uvbox: Dict[Tuple[int, int], Dict[int, List[int]]] = {}
        self.dir_targets: Dict[int, set] = {}
        self.dir_entries = 0
        self.dir_neg = 0
        self.wall = Counter()
        self._walk()
        self._roll_archive()

    # ------------------------------------------------------------------ the single corpus pass
    def _walk(self) -> None:
        for p in self.paths:
            ef = int(os.path.basename(p)[2:5])
            with open(p, "rb") as fh:
                blob = fh.read()
            self.blobs[ef] = blob
            mp = EC.creature_package(blob)
            cg = mp.geom_offset if mp is not None else None
            gobjs = [g for g in EC.scan_geom(blob) if g.base != cg]
            if cg is not None:
                self.creature_geoms += 1
            geoms = [g.base for g in gobjs]
            gmap = {g.base: g for g in gobjs}
            self.geoms_by_ef[ef] = geoms
            self.blind[ef] = (len(geoms) == 0)

            c = EC.parse_header(blob, strict=False)
            spans = []
            ids = set()
            for ch in c.chunks:
                for r in ch.resources:
                    n = r.nbytes + ((r.extra_sectors or 0) << 11)
                    spans.append((r.offset, r.offset + n, r.id))
                    ids.add(r.id)
                    self.resources_by_id[r.id] += 1
            for i in ids:
                self.containers_by_res_id[i] += 1
            self.res_ids[ef] = ids

            def rid(off: int) -> int:
                for lo, hi, i in spans:
                    if lo <= off < hi:
                        return i
                return -1

            for g in geoms:
                self.geom_by_res[rid(g)] += 1

            # -- the id-2 sub-file directories (G3's blind-wall table and G8's reference probe)
            targets = set()
            for ch in c.chunks:
                for r2 in ch.resources:
                    if r2.id != 2:
                        continue
                    try:
                        ents = EC.parse_directory(blob, r2.offset)
                    except Exception:                                          # noqa: BLE001
                        continue
                    for e in ents:
                        self.dir_entries += 1
                        if e < 0:
                            self.dir_neg += 1
                            continue
                        targets.add(r2.offset + e)
            self.dir_targets[ef] = targets

            # -- the declared page-cell map and the container's own palettes
            try:
                pcs = RS.page_cells(blob)
            except Exception:                                                  # noqa: BLE001
                pcs = {}
            self.declared_cells[ef] = {pc.cell for pc in pcs.values()}
            self.declared_cols[ef] = {pc.cell[0] for pc in pcs.values()}
            pals = []
            for ch in c.chunks:
                try:
                    _t, pl = RS.id0_palettes(blob, ch, RS.chunk_tag(ch))
                except Exception:                                              # noqa: BLE001
                    pl = []
                pals += pl
            by_cell: Dict[tuple, set] = defaultdict(set)
            for pl in pals:
                by_cell[pl.vram].add(pl.entries)
            self.pal_by_cell[ef] = by_cell
            self.pal_entries[ef] = [pl.entries for pl in pals]
            wa: Dict[int, set] = defaultdict(set)
            for ch in c.chunks:
                r0 = [r for r in ch.resources if r.id == 0]
                if len(r0) != 1:
                    continue
                p0 = r0[0].offset
                n4, n8 = u16(blob, p0 + 0x0C), u16(blob, p0 + 0x0E)
                for i in range(n4 + n8):
                    wa[u16(blob, p0 + 0x10 + 2 * i)].add(16 if i < n4 else 256)
            self.word_arity[ef] = wa

            # -- CHANNEL G: the kit's own bindings, at PAGE granularity, and their owning resource
            try:
                a = RS.attribution(blob, include_direct=True)
            except Exception:                                                  # noqa: BLE001
                a = None
            if a is not None:
                for b in a.bindings:
                    self.kit_bind_by_res[rid(int(b.geom))] += 1
                    if rid(int(b.geom)) == 2:
                        self.kit_id2_containers.add(ef)
                    px, py, bpp = dec(b.tpage)
                    for cell in cover(px, py):
                        k = (ef, cell[0], cell[1])
                        if k in self.C:
                            self.sopage[k][bpp] += 1

            # -- THE MULTI-PART RECORDS
            recs = _records(blob, geoms)
            rset = {r["at"] for r in recs}
            with_rec = set()
            for r in recs:
                r["ef"] = ef
                r["res_id"] = rid(r["geom"])
                r["kit_blind"] = RS.so_record(blob, r["geom"]) is None
                with_rec.add(r["geom"])
                self.recs.append(r)
                for k, (tp, cw) in enumerate(_iv(blob, r)):
                    px, py, bpp = dec(tp)
                    self.slots.append({
                        "ef": ef, "geom": r["geom"], "at": r["at"], "part": k,
                        "tpage": tp, "clut": cw, "bpp": bpp, "page": (px, py),
                        "res_id": r["res_id"], "npart": r["npart"],
                        "invisible": r["kit_blind"] or k > 0,
                    })
                self.uvbox[(ef, r["geom"])] = _uv_boxes(blob, gmap[r["geom"]])

            # -- the recordless residue: a GEOM block with no record at all
            for g in geoms:
                if g in with_rec:
                    continue
                self.recordless["total"] += 1
                has_uv = False
                go = gmap[g]
                for mesh in go.meshes:
                    for pr in EC.iter_primitives(blob, go, mesh):
                        if pr.get("uv"):
                            has_uv = True
                            break
                    if has_uv:
                        break
                if has_uv:
                    self.recordless["uv"][rid(g)] += 1
                else:
                    self.recordless["nouv"] += 1

            # -- THE WALL FROM THE OTHER SIDE: every halfword-aligned `so` magic in the whole blob
            gset = set(geoms) | ({cg} if cg is not None else set())
            pos = 0
            while True:
                k = blob.find(_NEEDLE, pos)
                if k < 0:
                    break
                pos = k + 1
                if k % 2 or k + 8 > len(blob):
                    continue
                self.wall["magic"] += 1
                if self.blind[ef]:
                    self.wall["blind_magic"] += 1
                rl, ab = u16(blob, k + 4), u16(blob, k + 6)
                if rl < 8 or rl % 8 or ab != 8 + 4 * ((rl - 8) // 8) or k + rl > len(blob):
                    continue
                self.wall["shape_valid"] += 1
                if self.blind[ef]:
                    self.wall["blind_shape_valid"] += 1
                self.wall["target_geom" if (k + rl) in gset else "target_not_geom"] += 1

    # ------------------------------------------------------------------ derived views
    def _roll_archive(self) -> None:
        """CHANNEL A: every binding slot's page, attributed to both stacked cells of its column."""
        self.arch: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
        self.arch_inv: Dict[Tuple[int, int, int], Counter] = defaultdict(Counter)
        self.undeclared: Counter = Counter()
        for s in self.slots:
            if not s["invisible"]:
                continue
            px, py = s["page"]
            for c in cover(px, py):
                k = (s["ef"], c[0], c[1])
                if k in self.C:
                    self.arch[k][s["bpp"]] += 1
                    self.arch_inv[k][s["bpp"]] += 1
                else:
                    #: a cell the slot's column names that the container never uploads at all --
                    #: counted PER CELL, which is what makes this 7/61 and not L1's 10/64.
                    self.undeclared[k] += 1

    def unknown(self) -> List[Tuple[int, int, int]]:
        return [k for k, r in self.C.items()
                if "creature" not in r["classes"] and r["hz_depth_unknown"]]

    def gv(self) -> Dict[Tuple[int, int, int], Optional[int]]:
        return {k: verdict(v.elements()) for k, v in self.sopage.items()}

    def scenery_arch(self) -> Dict[Tuple[int, int, int], Counter]:
        return {k: v for k, v in self.arch.items()
                if "creature" not in self.C[k]["classes"]}


# --------------------------------------------------------------------------- G0
def g0_calibrate(D: Data) -> None:
    print("[G0] CALIBRATE the instrument before judging with it")
    bad = [tp for tp in range(512)
           if dec(tp) != ((tp & 0x0F) * 64, ((tp >> 4) & 1) * 256, RS.SO_BPP[(tp >> 7) & 3])]
    chk("decoder", 512 - len(bad), PIN["decoder_words"])
    print("   this file's tpage decoder == reskin's field extraction over %d/512 nine-bit words"
          % (512 - len(bad)))

    # KNOWN ANSWER 1 -- THE DOME's own column, re-found through THIS walker's slots.
    k1 = [s for s in D.slots if s["ef"] == 211 and s["page"][0] == 704]
    chk("KA1 slot count", len(k1), PIN["ka1_slots"])
    chk("KA1 tpage", k1[0]["tpage"], PIN["ka1_tpage"])
    chk("KA1 page", (k1[0]["page"][0], k1[0]["page"][1], k1[0]["bpp"]), PIN["ka1_page"])
    print("   KNOWN ANSWER 1  ef211 column-704: %d binding, tpage %d -> page (%d,%d) %dbpp -- THE"
          " DOME's column and w6b2_gates H0's own first known answer"
          % (len(k1), k1[0]["tpage"], k1[0]["page"][0], k1[0]["page"][1], k1[0]["bpp"]))

    # KNOWN ANSWER 2 -- the one outlier `reskin.so_record`'s docstring names by offset AND value.
    k2 = [r for r in D.recs if r["ef"] == 226 and r["geom"] == 0x9C804]
    chk("KA2 record found", len(k2), 1)
    chk("KA2 at", k2[0]["at"], PIN["ka2_at"])
    chk("KA2 textured", k2[0]["textured"], PIN["ka2_textured"])
    chk("KA2 P", k2[0]["npart"], PIN["ka2_P"])
    s2 = _iv(D.blobs[226], k2[0])[0]
    chk("KA2 tpage", s2[0], PIN["ka2_tpage"])
    chk("KA2 clut", s2[1], PIN["ka2_clut"])
    print("   KNOWN ANSWER 2  ef226 GEOM %#x: record @%#x textured=%d P=%d tpage=%#x clut=%#x --"
          " reskin.so_record's OWN documented outlier, re-found exactly"
          % (0x9C804, k2[0]["at"], k2[0]["textured"], k2[0]["npart"], s2[0], s2[1]))
    print("   ** THE SUBSTITUTION, DECLARED (L1 declared it; L2 inherited it; it is re-declared"
          " here rather than slipped in): w6b2_gates H0's KA2 is L1's ef001 PROGRAM chain, which is"
          " not an `so` record and lies outside this walker's domain -- it was tried first, FAILED"
          " with 0 records, and was REPLACED rather than rescued.")

    # R3/R4 -- the incumbent reader reproduced on every record it accepts.
    ok = n = 0
    for r in D.recs:
        kit = RS.so_record(D.blobs[r["ef"]], r["geom"])
        if kit is None or "tpage" not in kit:
            continue
        n += 1
        s0 = _iv(D.blobs[r["ef"]], r)[0]
        if kit["at"] == r["at"] and kit["tpage"] == s0[0] and kit["clut"] == s0[1]:
            ok += 1
    chk("R3 slot 0 reproduces reskin.so_record", ok, PIN["r3_slot0_matches"])
    chk("R3 denominator", n, PIN["r3_slot0_matches"])
    acc = tp_bear = 0
    for ef, blob in D.blobs.items():
        for g in D.geoms_by_ef[ef]:
            rec = RS.so_record(blob, g)
            if rec is None:
                continue
            acc += 1
            if "tpage" in rec:
                tp_bear += 1
    chk("R4 accepted records", acc, PIN["r4_accepted"])
    chk("R4 tpage-bearing", tp_bear, PIN["r4_tpage_bearing"])
    print("   R3 slot 0 reproduces reskin.so_record's (at, tpage, clut): %d/%d" % (ok, n))
    print("   R4 the population reskin.attribution publishes: %d accepted / %d tpage-bearing"
          " (so_record's own docstring: 376 / 340)" % (acc, tp_bear))

    # ★ AND THE LIMIT OF ALL FOUR, MEASURED RATHER THAN CONCEDED.
    ef211_p2 = len([r for r in D.recs if r["ef"] == 211 and r["npart"] >= 2])
    chk("KA1's vehicle has no multi-part record", ef211_p2, PIN["ef211_p2_records"])
    ka2_p2 = 1 if k2[0]["npart"] >= 2 else 0
    touching = ef211_p2 + ka2_p2
    chk("calibration rungs evaluating a P>=2 byte", touching, PIN["ka_rungs_touching_a_p2_byte"])
    print("   ** THE LIMIT OF THIS CALIBRATION, PRINTED (refuter 1 finding #3): ef211 holds %d"
          " multi-part records and KA2's chosen block is P=%d, so %d of these rungs evaluates a byte"
          " only the NEW reading reaches.  R3 runs only on records the kit accepts (P<=1 by"
          " construction) and R4 compares the kit's own published population.  The rung with power"
          " over a P>=2 byte is G6's CLUT-arity test."
          % (ef211_p2, k2[0]["npart"], touching))


# --------------------------------------------------------------------------- G1
def g1_population(D: Data) -> None:
    print("[G1] THE POPULATION AND THE FORMAT -- a RECORD-LENGTH channel, not an id-2 channel")
    chk("containers", len(D.blobs), PIN["containers"])
    chk("non-creature GEOM blocks", sum(len(v) for v in D.geoms_by_ef.values()), PIN["geoms"])
    chk("creature GEOM blocks", D.creature_geoms, PIN["creature_geoms"])
    chk("GEOM by resource", dict(D.geom_by_res), PIN["geom_by_res"])
    chk("records", len(D.recs), PIN["records"])
    chk("slots", len(D.slots), PIN["slots"])
    inv_r = [r for r in D.recs if r["kit_blind"]]
    inv_s = [s for s in D.slots if s["invisible"]]
    chk("invisible records", len(inv_r), PIN["invisible_records"])
    chk("invisible slots", len(inv_s), PIN["invisible_slots"])
    ph = dict(Counter(r["npart"] for r in D.recs))
    chk("part-count histogram", ph, PIN["p_hist"])
    chk("records by resource", dict(Counter(r["res_id"] for r in D.recs)), PIN["records_by_res"])
    chk("invisible records by resource", dict(Counter(r["res_id"] for r in inv_r)),
        PIN["inv_records_by_res"])
    chk("invisible slots by resource", dict(Counter(s["res_id"] for s in inv_s)),
        PIN["inv_slots_by_res"])

    # F1 -- and the honest half of it.
    ab_ok = sum(1 for r in D.recs if r["arrayB"] == 8 + 4 * r["npart"])
    geom_ok = sum(1 for r in D.recs if r["at"] + r["reclen"] == r["geom"])
    chk("arrayB == 8+4P", ab_ok, PIN["arrayB_ok"])
    chk("recordBase + recLen == geomBase", geom_ok, PIN["reclen_lands_on_geom"])
    ab_hist = Counter((r["npart"], r["arrayB"]) for r in D.recs)
    informative = sum(n for (p, _a), n in ab_hist.items() if p >= 2)
    chk("arrayB values outside a P<=1 corpus's two constants", informative,
        PIN["invisible_records"])
    print("   %d records / %d binding slots over %d non-creature GEOM blocks; %d records and %d"
          " slots are INVISIBLE to reskin.so_record" % (len(D.recs), len(D.slots), PIN["geoms"],
                                                        len(inv_r), len(inv_s)))
    print("   GEOM blocks by resource %s -- plus %d id-5 creature blocks = %d, which is the total"
          " L1's headline quotes and which container.py's own source comment above _GEOM_NEEDLE"
          " already prints verbatim (a re-derivation, not a discovery)"
          % (dict(sorted(D.geom_by_res.items())), D.creature_geoms,
             PIN["geoms"] + D.creature_geoms))
    print("   P histogram %s ; records by res %s ; invisible by res %s"
          % (dict(sorted(ph.items())), dict(sorted(Counter(r["res_id"] for r in D.recs).items())),
             dict(sorted(Counter(r["res_id"] for r in inv_r).items()))))
    print("   ** F1's FIRST HALF IS NEAR-TAUTOLOGICAL AND IS FLAGGED AS SUCH: with P defined as"
          " (recLen-8)//8, 'recLen == 8+8P' asserts only recLen == 0 mod 8.  THE LOAD IS CARRIED BY"
          " arrayB, an INDEPENDENT halfword agreeing %d/%d -- and %d records take a value outside"
          " the two constants {8,12} a P<=1 corpus could supply, so the informative population is"
          " exactly the novel one." % (ab_ok, len(D.recs), informative))
    print("   recordBase + recLen == geomBase on %d/%d -- the record is SELF-DESCRIBING"
          % (geom_ok, len(D.recs)))

    # the residue closes
    chk("recordless GEOM blocks", D.recordless["total"], PIN["recordless"])
    chk("recordless UV-BEARING", sum(D.recordless["uv"].values()), PIN["recordless_uv"])
    chk("recordless UV-bearing by resource", dict(D.recordless["uv"]), PIN["recordless_uv_by_res"])
    chk("recordless with no UV faces", D.recordless["nouv"], PIN["recordless_nouv"])
    chk("the residue CLOSES", len(D.recs) + sum(D.recordless["uv"].values())
        + D.recordless["nouv"], PIN["geoms"])
    print("   THE RESIDUE CLOSES EXACTLY: %d with a record + %d recordless-but-UV-BEARING (id-2 %d /"
          " id-6 %d) + %d with no UV faces = %d"
          % (len(D.recs), sum(D.recordless["uv"].values()), D.recordless["uv"][2],
             D.recordless["uv"][6], D.recordless["nouv"], PIN["geoms"]))

    # container counts -- the disambiguation L1's own caveat asked for
    id2_geom = set()
    for r in D.recs:
        pass
    geom_res = {}
    for ef, geoms in D.geoms_by_ef.items():
        blob = D.blobs[ef]
        c = EC.parse_header(blob, strict=False)
        spans = [(x.offset, x.offset + x.nbytes + ((x.extra_sectors or 0) << 11), x.id)
                 for ch in c.chunks for x in ch.resources]
        for g in geoms:
            for lo, hi, i in spans:
                if lo <= g < hi:
                    geom_res[(ef, g)] = i
                    break
        if any(geom_res.get((ef, g)) == 2 for g in geoms):
            id2_geom.add(ef)
    chk("containers with a non-creature GEOM inside an id-2 archive", len(id2_geom),
        PIN["cont_geom_in_id2"])
    chk("containers carrying an id-2 resource", sum(1 for v in D.res_ids.values() if 2 in v),
        PIN["cont_id2_resource"])
    chk("containers with a decodable id-2 record",
        len(set(r["ef"] for r in D.recs if r["res_id"] == 2)), PIN["cont_id2_record"])
    chk("containers with ANY record", len(set(r["ef"] for r in D.recs)), PIN["cont_any_record"])
    chk("containers with an INVISIBLE record", len(set(r["ef"] for r in inv_r)),
        PIN["cont_invisible_record"])
    chk("resources by id", dict(D.resources_by_id), PIN["resources_by_id"])
    chk("containers by resource id", dict(D.containers_by_res_id), PIN["containers_by_res_id"])
    print("   COUNT DISAMBIGUATION: %d containers hold a non-creature GEOM in an id-2 archive; ALL"
          " %d carry an id-2 RESOURCE; %d have a decodable id-2 record; %d have any record; %d have"
          " an INVISIBLE one"
          % (len(id2_geom), sum(1 for v in D.res_ids.values() if 2 in v),
             len(set(r["ef"] for r in D.recs if r["res_id"] == 2)),
             len(set(r["ef"] for r in D.recs)), len(set(r["ef"] for r in inv_r))))

    # the `textured` halfword, and the depth split
    pt = Counter((r["npart"], r["textured"]) for r in D.recs)
    tex_iff = sum(n for (p, t), n in pt.items() if (t == 1) == (p >= 1))
    chk("textured == 1 iff P >= 1", tex_iff, PIN["textured_iff_p_ge1"])
    chk("invisible slot depths", dict(Counter(s["bpp"] for s in inv_s)), PIN["inv_slot_depths"])
    chk("all slot depths", dict(Counter(s["bpp"] for s in D.slots)), PIN["all_slot_depths"])
    d15 = [s for s in D.slots if s["bpp"] == 15]
    chk("15bpp slots carry clut == 0", sum(1 for s in d15 if s["clut"] == 0),
        PIN["direct15_clut_zero"])
    print("   the `textured` halfword: textured==1 iff P>=1 on %d/%d -- the ONE exception is KA2's"
          " own ef226 outlier, and it reads 1 at P=7, so the 'part count' reading is REFUTED"
          % (tex_iff, len(D.recs)))
    print("   invisible slot depths %s (45 direct-15bpp) ; all slots %s ; 15bpp slots with clut==0"
          " %d/%d" % (dict(sorted(Counter(s["bpp"] for s in inv_s).items())),
                      dict(sorted(Counter(s["bpp"] for s in D.slots).items())),
                      sum(1 for s in d15 if s["clut"] == 0), len(d15)))

    # ★ TWO OF L1's PUBLISHED NUMBERS, CORRECTED BY MEASUREMENT
    p0 = [r for r in D.recs if r["npart"] == 0]
    p0_zero = 0
    for r in p0:
        box = D.uvbox[(r["ef"], r["geom"])]
        if not any(b[4] for b in box.values()):
            p0_zero += 1
    chk("P==0 records", len(p0), PIN["p0_records"])
    chk("... with zero UV-bearing faces", p0_zero, PIN["p0_zero_uv"])
    tex_recs = [r for r in D.recs if r["textured"] == 1]
    tight = sum(1 for r in tex_recs if r["at"] + r["reclen"] == r["geom"])
    chk("textured records", len(tex_recs), PIN["textured_tight"])
    chk("... tight against their GEOM", tight, PIN["textured_tight"])
    print("   ** L1 sec 1.3 F4 QUOTED '37/37'.  MEASURED %d/%d -- there are %d P==0 records, as"
          " L1's own sec 1.2 table says.  The denominator 37 is in no artifact."
          % (p0_zero, len(p0), len(p0)))
    print("   ** L1 sec 1.3 F2t QUOTED '465/466'.  MEASURED %d/%d -- the one exception the row"
          " names (ef226 0x9c804) declares textured==0 BY L1'S OWN SENTENCE, so it cannot be in the"
          " denominator it is scored against." % (tight, len(tex_recs)))

    # THE WINDOW AND THE SHADOWING CAVEAT, both CLOSED by measurement
    multi = extra = 0
    maxrl = 0
    for ef, geoms in D.geoms_by_ef.items():
        blob = D.blobs[ef]
        for g in geoms:
            lo = max(0, g - 0x10000)
            win = blob[lo:g]
            cands = []
            pos = 0
            while True:
                k = win.find(_NEEDLE, pos)
                if k < 0:
                    break
                pos = k + 1
                if k % 2 != (lo % 2):
                    continue
                o = lo + k
                if o + 8 > len(blob):
                    continue
                rl = u16(blob, o + 4)
                if rl < 8 or rl % 8 or u16(blob, o + 6) != 8 + 4 * ((rl - 8) // 8):
                    continue
                if o + rl == g:
                    cands.append((o, rl))
            if len(cands) > 1:
                multi += 1
            for o, rl in cands:
                maxrl = max(maxrl, rl)
                if g - o > 0x400:
                    extra += 1
    chk("GEOM blocks with MORE THAN ONE passing candidate", multi, PIN["shadowed_geoms"])
    chk("records beyond the 0x400 window at a 0x10000 window", extra, PIN["wide_window_extra"])
    chk("longest recLen in the corpus", maxrl, PIN["max_reclen"])
    print("   ** TWO OF L1's STANDING CAVEATS, RETIRED BY MEASUREMENT: keeping EVERY candidate that"
          " passes the length test, %d of %d GEOM blocks has more than one -- so 'nearest' and"
          " 'farthest' are the same record everywhere and the tie-break was never load-bearing; and"
          " a %#x window with NO resource floor finds %d additional records on %d/%d.  The longest"
          " recLen anywhere is %d (P=7)." % (multi, PIN["geoms"], 0x10000, extra, PIN["geoms"],
                                             PIN["geoms"], maxrl))


# --------------------------------------------------------------------------- G2
def g2_premise(D: Data) -> None:
    print("[G2] THE HYPOTHESIS'S PREMISE, FALSIFIED -- the census walker ALREADY descends")
    chk("resource id 2's kit name", EC.RESOURCE_IDS[2], PIN["resource_2_name"])
    chk("kit bindings by owning resource", dict(D.kit_bind_by_res), PIN["kit_bind_by_res"])
    chk("containers where the KIT itself binds an id-2-resident model",
        len(D.kit_id2_containers), PIN["kit_id2_containers"])
    p2 = [r for r in D.recs if r["npart"] >= 2]
    none_on = sum(1 for r in p2 if RS.so_record(D.blobs[r["ef"]], r["geom"]) is None)
    chk("reskin.so_record returns None on every P>=2 record", none_on, PIN["kit_none_on_p2"])
    chk("... and that is the whole invisible population", len(p2), PIN["invisible_records"])
    print("   EC.RESOURCE_IDS[2] = %r, read by EC.parse_directory (fn 0x3d800's tail) -- id 2 IS the"
          " sub-file archive, and %d of the corpus's %d non-creature GEOM blocks live in it"
          % (EC.RESOURCE_IDS[2], D.geom_by_res[2], PIN["geoms"]))
    print("   BUT THE ARCHIVE IS NOT THE CHANNEL: EC.scan_geom(blob) is a WHOLE-BLOB needle scan"
          " with no resource filter and reskin.attribution iterates it unfiltered, so the kit's own"
          " bindings resolve to resources %s -- it binds id-2-resident models in %d containers"
          % (dict(sorted(D.kit_bind_by_res.items())), len(D.kit_id2_containers)))
    print("   THE BLINDNESS IS IN THE RECORD READER: reskin.so_record hard-probes recLen in"
          " (0x10, 0x08) only, so all %d P>=2 records return None -- record, slot 0 and every"
          " part>=1 slot" % none_on)
    print("   ** FOLLOW-THE-EVIDENCE CORRECTION, STATED LOUDLY: this is a RECORD-LENGTH channel,"
          " NOT an id-2 channel.  The %d invisible records split id-2 %d / id-6 %d / id-3 %d, so"
          " naming it 'the id-2 archive channel' would be wrong on %d of %d."
          % (len(p2), Counter(r["res_id"] for r in p2)[2], Counter(r["res_id"] for r in p2)[6],
             Counter(r["res_id"] for r in p2)[3],
             len(p2) - Counter(r["res_id"] for r in p2)[2], len(p2)))
    # the walker owns every block: nothing is unreachable to it
    chk("GEOM blocks no instrument in this round owns", 0, PIN["geoms_unowned_by_the_walker"])


# --------------------------------------------------------------------------- G3
def _channels(D: Data):
    unk = set(D.unknown())
    p_rows = {(k[0], k[1], k[2]): v for k, v in DA.PROGRAM_DEPTH.items()}
    p_keys = set(p_rows) & unk
    p_gain = set(k for k in p_keys if p_rows[k].bpp is not None)
    p_dual = p_keys - p_gain
    gv = D.gv()
    g_keys = set(gv) & unk
    g_gain = set(k for k in g_keys if gv[k] is not None)
    g_dual = g_keys - g_gain
    arch = D.scenery_arch()
    a_keys = set(arch) & unk
    new = a_keys - p_keys - g_keys
    return unk, p_rows, p_keys, p_gain, p_dual, g_keys, g_gain, g_dual, arch, a_keys, new


def g3_reach(D: Data) -> None:
    print("[G3] THE SWEEP AND THE REACH -- 73 new cells, and what they do to the residue")
    unk, p_rows, p_keys, p_gain, p_dual, g_keys, g_gain, g_dual, arch, a_keys, new = _channels(D)

    # the declared-cell pivot: 109, not 106 -- and 3 of them are CREATURE pages
    all_arch = set(D.arch)
    cls = Counter()
    for k in all_arch:
        c = D.C[k]["classes"]
        cls["creature" if "creature" in c else ("id9" if "id9" in c else "id0")] += 1
    chk("declared cells named by the 309 invisible slots", len(all_arch), PIN["declared_cells"])
    chk("... by class", dict(cls), PIN["declared_by_class"])
    chk("... scenery-class", len(arch), PIN["scenery_cells"])
    chk("undeclared cells", len(D.undeclared), PIN["undeclared_cells"])
    chk("undeclared slot hits", sum(D.undeclared.values()), PIN["undeclared_slot_hits"])
    print("   the %d invisible slots name %d DECLARED page-cells: %d id0 + %d id9 + %d CREATURE ->"
          " %d scenery.  ** L1 published '64 slot->column hits name 10 cells the container NEVER"
          " UPLOADS'.  MEASURED %d hits over %d cells -- the missing 3 (ef179/ef186/ef276 at"
          " 320,384) ARE uploaded, as CREATURE pages.  Same pivot, both counts."
          % (PIN["invisible_slots"], len(all_arch), cls["id0"], cls["id9"], cls["creature"],
             len(arch), sum(D.undeclared.values()), len(D.undeclared)))
    print("      the %d undeclared cells, by name: %s"
          % (len(D.undeclared),
             ", ".join(sorted("ef%03d.x%d_y%d" % k for k in D.undeclared))))
    print("      the %d CREATURE-class cells, by name: %s"
          % (cls["creature"], ", ".join(sorted(D.C[k]["id"] for k in all_arch
                                               if "creature" in D.C[k]["classes"]))))

    # the census populations and the two incumbent channels, re-derived LIVE
    creature = sum(1 for r in D.census if "creature" in r["classes"])
    chk("census rows", len(D.census), PIN["census_rows"])
    chk("census scenery", len(D.census) - creature, PIN["census_scenery"])
    chk("census depth-unknown", len(unk), PIN["census_unknown"])
    chk("channel P rows", len(DA.PROGRAM_DEPTH), PIN["p_rows"])
    chk("channel P unanimous", sum(1 for v in DA.PROGRAM_DEPTH.values() if v.bpp is not None),
        PIN["p_unanimous"])
    chk("channel P dual", sum(1 for v in DA.PROGRAM_DEPTH.values() if v.bpp is None), PIN["p_dual"])
    chk("channel P gains", len(p_gain), PIN["p_gain"])
    chk("channel G gains", len(g_gain), PIN["g_gain"])
    chk("channel G duals", len(g_dual), PIN["g_dual"])
    print("   census %d rows = %d scenery + %d creature ; %d scenery cells are DEPTH-UNKNOWN"
          % (len(D.census), len(D.census) - creature, creature, len(unk)))
    print("   channel P (shipped table) %d rows = %d unanimous + %d dual -> %d gains ;"
          " channel G re-derived LIVE from the containers -> %d gains + %d dual"
          % (len(DA.PROGRAM_DEPTH), PIN["p_unanimous"], PIN["p_dual"], len(p_gain),
             len(g_gain), len(g_dual)))

    # THE REACH
    new_una = set(k for k in new if verdict(arch[k].elements()) is not None)
    new_dual = new - new_una
    chk("new vs ALL channels (strict)", len(new), PIN["new_strict"])
    chk("... unanimous", len(new_una), PIN["new_unanimous"])
    chk("... dual", len(new_dual), PIN["new_dual"])
    chk("... lower halves", sum(1 for k in new_una if k[2] == 384), PIN["new_lower_halves"])
    chk("... by depth", dict(Counter(verdict(arch[k].elements()) for k in new_una)),
        PIN["new_depths"])
    # the CONSERVATIVE subtraction predicate, which must give the same 73
    g_cover_all = set(D.sopage)
    new_cons = a_keys - p_keys - (g_cover_all & unk)
    chk("the 73 is stable under the conservative predicate too", len(new_cons), PIN["new_strict"])
    # id-2 framing cost
    id2_slots = set()
    for s in D.slots:
        if not s["invisible"] or s["res_id"] != 2:
            continue
        for c in cover(*s["page"]):
            id2_slots.add((s["ef"], c[0], c[1]))
    chk("the reach under an id-2-ONLY framing", len(new_una & id2_slots), PIN["id2_only_gain"])
    print("   THE REACH: %d cells new vs EVERY channel = %d unanimous + %d DUAL-DEPTH (a hazard,"
          " not a vote).  Depths %s.  %d of the %d are LOWER halves."
          % (len(new), len(new_una), len(new_dual),
             dict(sorted(Counter(verdict(arch[k].elements()) for k in new_una).items())),
             sum(1 for k in new_una if k[2] == 384), len(new_una)))
    print("   ** THE id-2 FRAMING COSTS 52 %% OF THE REACH, MEASURED: restricted to id-2-resident"
          " records the gain falls %d -> %d, and the invisible SLOTS split id-6 %d / id-2 %d /"
          " id-3 %d -- id-6 carries MORE than id-2."
          % (len(new_una), len(new_una & id2_slots),
             Counter(s["res_id"] for s in D.slots if s["invisible"])[6],
             Counter(s["res_id"] for s in D.slots if s["invisible"])[2],
             Counter(s["res_id"] for s in D.slots if s["invisible"])[3]))

    # double-count checks -- the totals must ADD
    chk("P n G", len(p_gain & g_gain), PIN["overlap_pg"])
    chk("P n A", len(p_gain & new), PIN["overlap_pa"])
    chk("G n A", len(g_gain & new), PIN["overlap_ga"])
    chk("A n census-known", len(new - unk), PIN["overlap_a_census"])
    chk("the union ADDS", len(p_gain | g_gain | new), PIN["gain_union"])
    print("   DOUBLE-COUNT CHECKS ALL EMPTY: P&G %d, P&A %d, G&A %d, A&census-known %d -- so"
          " %d + %d + %d = %d and the totals ADD"
          % (len(p_gain & g_gain), len(p_gain & new), len(g_gain & new), len(new - unk),
             len(p_gain), len(g_gain), len(new), len(p_gain | g_gain | new)))

    # THE RESIDUE, and the reach's ACTUAL movement on it
    blind = set(ef for ef, b in D.blind.items() if b)
    chk("geom-blind containers", len(blind), PIN["blind_containers"])
    bu = [k for k in unk if k[0] in blind]
    residue = unk - p_gain - g_gain
    covered = residue - set(bu)
    chk("residue", len(residue), PIN["residue"])
    chk("residue behind the wall", len(bu), PIN["residue_blind"])
    chk("residue in model-BEARING containers", len(covered), PIN["residue_covered"])
    chk("the archive reaches NOTHING behind the wall", len(new & set(bu)), PIN["archive_in_blind"])
    chk("the 73 come entirely out of the 861", len(new & covered), PIN["new_strict"])
    chk("the covered class after adopting the 73", len(covered) - len(new), PIN["covered_after_73"])
    chk("residue after the 73", len(residue) - len(new), PIN["residue_after_73"])
    chk("residue after the 65", len(residue) - len(new_una), PIN["residue_after_65"])
    chk("residue after the 26 genuinely clean", len(residue) - PIN["reach_clean"],
        PIN["residue_after_26"])
    print("   THE RESIDUE CLOSES: %d unknown - %d P - %d G = %d = %d behind the wall + %d in"
          " model-BEARING containers" % (len(unk), len(p_gain), len(g_gain), len(residue),
                                         len(bu), len(covered)))
    print("   ** THE REACH'S ACTUAL MOVEMENT, WHICH NEITHER LANE STATED: all %d are drawn from the"
          " %d covered class (intersection with the %d blind cells = %d), so the residue moves"
          " %d -> %d if the 73 were adopted, %d for the 65 unanimous, and %d after the deflation"
          " to %d genuinely clean cells."
          % (len(new), len(covered), len(bu), len(new & set(bu)), len(residue),
             len(residue) - len(new), len(residue) - len(new_una),
             len(residue) - PIN["reach_clean"], PIN["reach_clean"]))
    print("      the covered-but-uncovered class itself goes %d -> %d under the 73."
          % (len(covered), len(covered) - len(new)))

    # THE WALL, three predicates -- and the identity named as an identity
    with_r = sum(1 for ef in blind if 2 in D.res_ids[ef])
    nonempty = sum(1 for ef in blind if D.dir_targets[ef])
    with_geom = 0
    for ef in blind:
        blob = D.blobs[ef]
        c = EC.parse_header(blob, strict=False)
        spans = [(x.offset, x.offset + x.nbytes + ((x.extra_sectors or 0) << 11), x.id)
                 for ch in c.chunks for x in ch.resources]
        if any(any(lo <= g < hi and i == 2 for lo, hi, i in spans) for g in D.geoms_by_ef[ef]):
            with_geom += 1
    chk("blind containers carrying an id-2 resource", with_r, PIN["blind_with_id2_resource"])
    chk("blind containers with a NON-EMPTY id-2 directory", nonempty,
        PIN["blind_with_nonempty_id2_dir"])
    chk("blind containers holding a GEOM block inside one", with_geom, PIN["blind_with_geom_in_id2"])
    print("   ** THE STRUCTURAL WALL IS UNMOVED, and its 0 is an IDENTITY not a measurement (a"
          " blind container has no GEOM block, so no record, so no cell).  The informative table"
          " beside it: of the %d blind containers, %d carry an id-2 RESOURCE, %d have a NON-EMPTY"
          " id-2 sub-file DIRECTORY, and %d hold a single GEOM block inside one.  The %d cells"
          " behind the wall gain NOTHING.  Do not project %d forward onto %d."
          % (len(blind), with_r, nonempty, with_geom, len(bu), len(new_una), len(residue)))


# --------------------------------------------------------------------------- G4
#: THE THREE VEHICLES, with the in-game fact each was chosen for (W6b-SCENERY.md sec 5's cast
#: ladder) and the prediction the hypothesis makes.  Predictions were written before the numbers.
_GHOST = {
    446: {"cols": [448], "screen": 8, "spill": [448, 512],
          "fact": "census 15bpp; DREW at 8bpp (the salmon checker; THE DEPTH COROLLARY)",
          "predict": "an invisible archive binding names this column at 8bpp"},
    251: {"cols": [512], "screen": 4, "spill": [448, 512, 576],
          "fact": "channel P registered tpage 312 = 15bpp; DREW indexed / 4bpp (the bumper strip)",
          "predict": "an invisible archive binding names x512 at 4bpp"},
    429: {"cols": [448], "screen": None, "spill": [384, 448, 512],
          "fact": "census 15bpp; BOUND-NEVER-DRAWN on both covers",
          "predict": "nothing -- a channel that 'explained' this would be over-fitting"},
}


def g4_ghost(D: Data) -> None:
    print("[G4] THE GHOST-LAYER VERDICT -- scored prediction by prediction")
    hits = misses = vacuous = 0
    for ef in (446, 251, 429):
        spec = _GHOST[ef]
        recs = [r for r in D.recs if r["ef"] == ef]
        inv = [r for r in recs if r["kit_blind"]]
        slots = [s for s in D.slots if s["ef"] == ef]
        col_inv = [s for s in slots if s["invisible"] and s["page"][0] in spec["cols"]]
        col_any = [s for s in slots if s["page"][0] in spec["cols"]]
        # PREDICATE 2 -- UV COVER, on the CORRECTED (dereferenced) UVs
        uvhit = 0
        for s in slots:
            box = D.uvbox[(ef, s["geom"])].get(s["part"])
            if not box or not box[4]:
                continue
            per = KT.TEXELS_PER_HW[s["bpp"]]
            hx_lo = s["page"][0] + box[0] // per
            hx_hi = s["page"][0] + box[1] // per
            for c in spec["cols"]:
                if hx_lo <= c + 63 and hx_hi >= c and s["invisible"]:
                    uvhit += 1
        # PREDICATE 3 -- SPILL TARGET (ef446's own cast proved a 112-halfword band crosses a seam)
        sp = [s for s in slots if s["page"][0] in spec["spill"]]
        rl_uv = sum(1 for g in D.geoms_by_ef[ef] if g not in set(r["geom"] for r in recs))
        chk("ef%03d records" % ef, len(recs), PIN["ef%d_records" % ef])
        chk("ef%03d invisible records" % ef, len(inv), PIN["ef%d_invisible" % ef])
        chk("ef%03d recordless GEOM blocks" % ef, rl_uv, PIN["ef%d_recordless_uv" % ef])
        chk("ef%03d non-creature GEOM blocks" % ef, len(D.geoms_by_ef[ef]), PIN["ef%d_geoms" % ef])
        chk("ef%03d spill-target slots" % ef, len(sp), PIN["spill_ef%d_slots" % ef])
        hit = bool(col_inv) and spec["screen"] in set(s["bpp"] for s in col_inv)
        if spec["screen"] is None:
            vacuous += 2                    # both stacked cells of the vehicle's column
            tag = "VACUOUS PASS -- it passes by predicting nothing"
        elif hit:
            hits += 2
            tag = "HIT"
        else:
            misses += 2
            tag = "MISS"
        print("   ef%03d  %s" % (ef, spec["fact"]))
        print("          PREDICTED: %s" % spec["predict"])
        print("          declared column %s: %d invisible slot(s), %d of any kind, depths %s"
              % (spec["cols"], len(col_inv), len(col_any),
                 sorted(set(s["bpp"] for s in col_any)) or "none"))
        print("          UV-COVER (corrected UVs) invisible hits %d ; SPILL-TARGET %s -> %d slot(s)"
              " depths %s" % (uvhit, spec["spill"], len(sp),
                              sorted(set(s["bpp"] for s in sp)) or "none"))
        print("          records %d (invisible %d) ; recordless GEOM blocks %d ; -> %s"
              % (len(recs), len(inv), rl_uv, tag))
        chk("ef%03d UV-cover widening finds nothing either" % ef, uvhit, PIN["uvcover_hits"])
    # both cells of each vehicle, so the score is over 6 named cells
    chk("ef446 column-448 invisible slots", len([s for s in D.slots if s["ef"] == 446
                                                 and s["invisible"] and s["page"][0] == 448]),
        PIN["ef446_col448_invisible_slots"])
    chk("ef446 column-448 depths", tuple(sorted(set(s["bpp"] for s in D.slots if s["ef"] == 446
                                                    and s["page"][0] == 448))),
        PIN["ef446_col448_depths"])
    chk("ef251 column-512 slots of ANY kind",
        len([s for s in D.slots if s["ef"] == 251 and s["page"][0] == 512]), PIN["ef251_col512_slots"])
    chk("ef429 column-448 depths", tuple(sorted(set(s["bpp"] for s in D.slots if s["ef"] == 429
                                                    and s["page"][0] == 448))),
        PIN["ef429_col448_depths"])
    chk("ef251 recordless UV-bearing by resource",
        dict(Counter(rid for rid in _recordless_res(D, 251))), PIN["ef251_recordless_by_res"])
    chk("ghost HITS", hits, PIN["ghost_hits"])
    chk("ghost MISSES", misses, PIN["ghost_misses"])
    chk("ghost VACUOUS passes", vacuous, PIN["ghost_vacuous"])
    print("   FULL SCORE ACROSS THE THREE VEHICLES AND SIX NAMED CELLS: %d hits, %d misses,"
          " %d vacuous passes.  The archive channel says NOTHING about any of them."
          % (hits, misses, vacuous))

    # ef446 DOES bind 8bpp -- on a DIFFERENT column, through a record the kit already reads
    e446 = [s for s in D.slots if s["ef"] == 446 and s["bpp"] == 8]
    chk("ef446 binds 8bpp exactly once", len(e446), 1)
    chk("ef446's 8bpp geom", e446[0]["geom"], PIN["ef446_8bpp_geom"])
    chk("ef446's 8bpp page", e446[0]["page"], PIN["ef446_8bpp_page"])
    print("   SHARPENING L1's TABLE DID NOT HAVE: ef446 DOES bind 8bpp -- GEOM %#x at page (%d,%d),"
          " a DIFFERENT column, through a record the kit ALREADY reads.  With 0 recordless blocks"
          " there is no unexamined model of any record length left in the container, so whatever"
          " draws the nucleus at 8bpp is NOT a GEOM model in ef446 at all."
          % (e446[0]["geom"], e446[0]["page"][0], e446[0]["page"][1]))

    # WHERE THE GHOST COULD STILL BE
    print("   WHERE THE GHOST COULD STILL BE: %d UV-bearing GEOM blocks corpus-wide carry NO record"
          " (id-2 %d / id-6 %d) -- but ef446 and ef429 have ZERO of them, so for those two the"
          " ghost is not a model at any length in any sub-file.  ef251 holds %d."
          % (sum(D.recordless["uv"].values()), D.recordless["uv"][2], D.recordless["uv"][6],
             PIN["ef251_recordless_uv"]))

    # the 15bpp prior this lane inherits
    f15 = [r for r in D.census
           if "creature" not in r["classes"] and r["bpp"] == 15]
    chk("census-15bpp scenery cells corpus-wide", len(f15), PIN["census_15bpp_scenery"])
    print("   THE GHOST-LAYER OBSERVATION's OWN SAMPLE: %d scenery page-cells carry a census 15bpp"
          " and %d have been probed in-game -- a %.0f %% sample, every one of which was"
          " bound-never-drawn or drawn at another depth."
          % (len(f15), PIN["census_15bpp_probed"],
             100.0 * PIN["census_15bpp_probed"] / len(f15)))

    # ef390 Q4 -- the channel boundary, re-measured
    e390 = [s for s in D.slots if s["ef"] == 390]
    n448 = [s for s in e390 if s["page"] == (448, 256)]
    chk("ef390 slots", len(e390), PIN["ef390_slots"])
    chk("ef390 slots naming (448,256)", len(n448), PIN["ef390_slots_448_256"])
    chk("ef390 declares (448,256)", (390, 448, 256) in D.C, PIN["ef390_448_declared"])
    wr = Counter()
    for r in D.census:
        for w in r["writers"]:
            wr[w["res_id"]] += 1
    chk("census page-cell WRITER records by resource", dict(wr), PIN["writers_by_res"])
    chk("writer records total", sum(wr.values()), PIN["writer_records_total"])
    chk("writer records living in an id-2 resource", wr[2], PIN["writer_records_in_id2"])
    print("   W6b-2 sec 3 probe 1 / W6b-1 Q4, SHARPENED: %d of ef390's %d slots name page (448,256)"
          " at 15bpp, not the 10 W6b-2 recorded -- and %d of the corpus's %d census page-cell"
          " WRITER records lives in an id-2 resource %s, so NO archive uploads a page in any"
          " container and the residual-VRAM refusal stands."
          % (len(n448), len(e390), wr[2], sum(wr.values()), dict(sorted(wr.items()))))


def _recordless_res(D: Data, ef: int) -> List[int]:
    blob = D.blobs[ef]
    c = EC.parse_header(blob, strict=False)
    spans = [(x.offset, x.offset + x.nbytes + ((x.extra_sectors or 0) << 11), x.id)
             for ch in c.chunks for x in ch.resources]
    have = set(r["geom"] for r in D.recs if r["ef"] == ef)
    out = []
    for g in D.geoms_by_ef[ef]:
        if g in have:
            continue
        for lo, hi, i in spans:
            if lo <= g < hi:
                out.append(i)
                break
    return out


# --------------------------------------------------------------------------- G5
def g5_conflicts(D: Data) -> None:
    print("[G5] CONFLICTS, AGREEMENT, AND THE BASE RATE THE AGREEMENT DOES NOT BEAT")
    arch = D.scenery_arch()
    gv = D.gv()

    comp22 = [k for k in arch
              if D.C[k]["bpp"] is not None or D.C[k]["hz_dual_depth"]]
    comp21 = [k for k in arch if D.C[k]["bpp"] is not None]
    agree = [k for k in comp21 if verdict(arch[k].elements()) == D.C[k]["bpp"]]
    flat = [k for k in comp21
            if verdict(arch[k].elements()) is not None
            and verdict(arch[k].elements()) != D.C[k]["bpp"]]
    chk("comparable rows (census attribution of any kind)", len(comp22), PIN["comparable_22"])
    chk("comparable rows (a single census depth) -- L2's 21", len(comp21), PIN["comparable_21"])
    chk("AGREE", len(agree), PIN["agree"])
    chk("FLAT contradictions against the census", len(flat), PIN["flat_census"])
    chk("the flat cell, by name", sorted(D.C[k]["id"] for k in flat), ["ef184.x448_y256"])
    print("   vs the `so` CENSUS: %d/%d = %.1f %% under L2's predicate, %d/%d = %.1f %% including"
          " the census-DUAL row (ef381:576,256) L2 silently drops.  FLAT contradictions: %s"
          % (len(agree), len(comp21), 100.0 * len(agree) / len(comp21), len(agree), len(comp22),
             100.0 * len(agree) / len(comp22), [D.C[k]["id"] for k in flat]))

    # vs the LICENSED channel G
    rows = [(k, sorted(gv[k].elements() and set(gv_ := None) or set()) if False else None)
            for k in []]
    vg = []
    for k in arch:
        if k not in D.sopage:
            continue
        gset = set(D.sopage[k])
        aset = set(arch[k])
        if gset == aset:
            v = "AGREE"
        elif gset & aset:
            v = "COMPATIBLE"
        else:
            v = "FLAT"
        vg.append((k, v))
    hist = Counter(v for _k, v in vg)
    chk("vs channel G, n", len(vg), PIN["vs_g_n"])
    chk("vs channel G, AGREE", hist["AGREE"], PIN["vs_g_agree"])
    chk("vs channel G, COMPATIBLE", hist["COMPATIBLE"], PIN["vs_g_compatible"])
    chk("vs channel G, FLAT", hist["FLAT"], PIN["vs_g_flat"])
    chk("the two flat cells, by name", sorted(D.C[k]["id"] for k, v in vg if v == "FLAT"),
        ["ef184.x448_y256", "ef184.x448_y384"])
    print("   vs CHANNEL G, which the kit LICENSES: n=%d -> %d AGREE / %d COMPATIBLE / %d FLAT, and"
          " the two FLAT rows are %s.  So the flat contradiction is TWO cells against a licensed"
          " channel, not one cell against a disclosure."
          % (len(vg), hist["AGREE"], hist["COMPATIBLE"], hist["FLAT"],
             sorted(D.C[k]["id"] for k, v in vg if v == "FLAT")))

    # ★ THE TAUTOLOGY CONTROL the agreement statistic must beat, run inside the census's OWN
    # instrument: two records naming ONE column agree unless the container draws it at two depths.
    col_depths: Dict[Tuple[int, int], set] = defaultdict(set)
    col_models: Dict[Tuple[int, int], set] = defaultdict(set)
    for ef, blob in D.blobs.items():
        try:
            a = RS.attribution(blob, include_direct=True)
        except Exception:                                                      # noqa: BLE001
            continue
        for b in a.bindings:
            px, _py, bpp = dec(b.tpage)
            col_depths[(ef, px)].add(bpp)
            col_models[(ef, px)].add(int(b.geom))
    multi = [c for c in col_models if len(col_models[c]) >= 2]
    single = [c for c in multi if len(col_depths[c]) == 1]
    chk("columns bound by >=2 kit-VISIBLE models", len(multi), PIN["taut_columns"])
    chk("... of which SINGLE-depth", len(single), PIN["taut_single_depth"])
    chk("the tautology rate", round(len(single) / len(multi), 4), PIN["taut_rate"])
    allcol: Dict[Tuple[int, int, int], set] = defaultdict(set)
    for s in D.slots:
        allcol[(s["ef"], s["page"][0], s["page"][1])].add(s["bpp"])
    chk("corpus columns bound at all", len(allcol), PIN["corpus_columns_bound"])
    chk("... single-depth", sum(1 for c in allcol if len(allcol[c]) == 1),
        PIN["corpus_columns_single_depth"])
    print("   ** THE TAUTOLOGY CONTROL (refuter 2, run inside the CENSUS's OWN instrument): over the"
          " %d columns bound by >=2 kit-VISIBLE models, %d are single-depth = %.1f %%.  The"
          " archive-vs-census agreement on the identical structure is %.1f %%.  OBSERVED AND"
          " CONTROL ARE WITHIN NOISE.  Corpus-wide %d/%d bound columns = %.1f %% single-depth."
          % (len(multi), len(single), 100.0 * len(single) / len(multi),
             100.0 * len(agree) / len(comp22), sum(1 for c in allcol if len(allcol[c]) == 1),
             len(allcol),
             100.0 * sum(1 for c in allcol if len(allcol[c]) == 1) / len(allcol)))

    # the multi-valued hazard class -- 12 cells, not the 8 that are ALSO new
    mv = sorted("%s %s" % (D.C[k]["id"], sorted(arch[k])) for k in arch if len(arch[k]) > 1)
    chk("archive MULTI-VALUED cells", len(mv), PIN["archive_multivalued"])
    print("   ** THE ARCHIVE's MULTI-VALUED HAZARD CLASS IS %d CELLS, NOT 8 -- L1 counted only the"
          " ones that are also NEW.  Full list: %s" % (len(mv), ", ".join(mv)))

    # THE SAFETY POPULATION -- five census-attributed cells, one of which is the class's control
    safety = []
    for k in comp21:
        a = set(arch[k])
        cb = D.C[k]["bpp"]
        if len(a) > 1 and cb in a:
            safety.append((D.C[k]["id"], "DUAL", sorted(a), cb))
        elif len(a) == 1 and cb not in a:
            safety.append((D.C[k]["id"], "FLAT", sorted(a), cb))
    ctrl = [k for k in comp21 if len(arch[k]) == 1 and D.C[k]["bpp"] in arch[k]
            and D.C[k]["id"] == "ef381.x576_y384"]
    chk("safety population (dual or flat against a census depth)", len(safety) + len(ctrl),
        PIN["safety_cells"])
    print("   ** THE SAFETY POPULATION IS %d CENSUS-ATTRIBUTED CELLS, and the fifth is the class's"
          " own CONTROL: %s ; plus ef381.x576_y384 (census 8, archive [8]) which AGREES."
          % (len(safety) + len(ctrl),
             " ; ".join("%s census %s archive %s -> %s" % (n, c, a, t) for n, t, a, c in safety)))

    # ef184, both predicates on the same bytes
    r_vis = [r for r in D.recs if r["ef"] == 184 and r["geom"] == PIN["ef184_visible_geom"]]
    r_inv = [r for r in D.recs if r["ef"] == 184 and r["geom"] == PIN["ef184_invisible_geom"]]
    chk("ef184 kit-visible record at", r_vis[0]["at"], PIN["ef184_visible_rec"])
    chk("ef184 invisible record at", r_inv[0]["at"], PIN["ef184_invisible_rec"])
    chk("ef184 invisible record is P=2", r_inv[0]["npart"], 2)
    v0 = _iv(D.blobs[184], r_vis[0])[0]
    i1 = _iv(D.blobs[184], r_inv[0])[1]
    chk("ef184 visible tpage", v0[0], PIN["ef184_visible_tpage"])
    chk("ef184 invisible part-1 tpage", i1[0], PIN["ef184_invisible_tpage"])
    chk("ef184 visible depth", dec(v0[0])[2], 4)
    chk("ef184 invisible part-1 depth", dec(i1[0])[2], 8)
    chk("ef184 records", len([r for r in D.recs if r["ef"] == 184]), PIN["ef184_records"])
    chk("ef184 records in an id-2 archive",
        len([r for r in D.recs if r["ef"] == 184 and r["res_id"] == 2]), PIN["ef184_id2_records"])
    print("   THE FLAT CONTRADICTION, BOTH PREDICATES ON THE SAME BYTES: ef184 kit-visible GEOM %#x"
          " (record %#x, P=1, tpage %d -> %dbpp) vs INVISIBLE GEOM %#x (record %#x, P=2, part 1,"
          " tpage %d -> %dbpp).  Both true; adjudicated, not explained."
          % (PIN["ef184_visible_geom"], r_vis[0]["at"], v0[0], dec(v0[0])[2],
             PIN["ef184_invisible_geom"], r_inv[0]["at"], i1[0], dec(i1[0])[2]))
    print("   ** AND L1 sec 1.4 OFFERS THAT SAME GEOM AS 'the measured example ... inside an id-2"
          " archive'.  MEASURED: ef184 has %d records, %d in an id-2 archive; every one is res_id"
          " %s.  The conclusion is untouched; the example does not exercise the case."
          % (len([r for r in D.recs if r["ef"] == 184]),
             len([r for r in D.recs if r["ef"] == 184 and r["res_id"] == 2]),
             sorted(set(r["res_id"] for r in D.recs if r["ef"] == 184))))


# --------------------------------------------------------------------------- G6
def g6_controls(D: Data) -> None:
    print("[G6] THE CONTROLS -- a reading never contrasted with a wrong one is an assertion")
    rng = random.Random(20260729)
    inv = [s for s in D.slots if s["invisible"]]
    dcol = D.declared_cols

    shipped = sum(1 for s in inv if s["page"][0] in dcol[s["ef"]])
    st8 = ph2 = ph2_legal = nul = 0
    n_rand = hit_rand = 0
    for r in D.recs:
        blob, ef, P = D.blobs[r["ef"]], r["ef"], r["npart"]
        at, rl = r["at"], r["reclen"]
        for k in range(P):
            if not (r["kit_blind"] or k > 0):
                continue
            if at + 8 + 8 * k + 4 <= at + rl:
                if dec(u16(blob, at + 8 + 8 * k))[0] in dcol[ef]:
                    st8 += 1
            if at + 8 + 4 * k + 4 <= at + rl:
                w2 = u16(blob, at + 8 + 4 * k + 2)
                if w2 <= 0x1FF:
                    ph2_legal += 1
                    if dec(w2)[0] in dcol[ef]:
                        ph2 += 1
            o = at + r["arrayB"] + 4 * k
            if o + 2 <= at + rl and dec(u16(blob, o))[0] in dcol[ef]:
                nul += 1
            n_rand += 1
            if dec(u16(blob, at + 2 * rng.randrange(rl // 2)))[0] in dcol[ef]:
                hit_rand += 1
    chk("SHIPPED +0x08 stride 4, declared column", shipped, PIN["ctrl_shipped"])
    chk("WRONG stride 8", st8, PIN["ctrl_stride8"])
    chk("phase +2 (the CLUT halfword read AS a tpage)", ph2, PIN["ctrl_phase2"])
    chk("the IN-RECORD NULL (the second array at +arrayB)", nul, PIN["ctrl_inrecord_null"])
    chk("null: a random halfword from the record's own bytes", hit_rand, PIN["null_random_hw"])
    chk("control denominator", len(inv), PIN["ctrl_n"])
    print("   scored on the DECLARED-COLUMN predicate over the %d invisible slots:" % len(inv))
    print("      SHIPPED  +0x08 stride 4 : %3d/%d = %.1f %%" % (shipped, len(inv),
                                                                100.0 * shipped / len(inv)))
    print("      WRONG    stride 8       : %3d/%d = %.1f %%   (the first reading tried, discarded)"
          % (st8, len(inv), 100.0 * st8 / len(inv)))
    print("      phase +2 (CLUT as tpage): %3d/%d   -- only %d of the %d yield a LEGAL 9-bit page"
          " word at all" % (ph2, len(inv), ph2_legal, len(inv)))
    print("      IN-RECORD NULL @+arrayB : %3d/%d   -- its 'legal tpage 309/309' is VACUOUS (values"
          " all in {0,16,32,64,80,128}) and is printed rather than quoted" % (nul, len(inv)))
    print("      random halfword, SAME record: %d/%d = %.1f %% -- the honest floor the shipped"
          " reading clears by ~5x" % (hit_rand, n_rand, 100.0 * hit_rand / max(n_rand, 1)))

    # ★ refuter 2's PART-BYTE RANGE TEST -- the first check from OUTSIDE the record's own header
    viol = 0
    withparts = 0
    hist = Counter()
    p2_multi = 0
    for r in D.recs:
        box = D.uvbox[(r["ef"], r["geom"])]
        parts = sorted(k for k, b in box.items() if b[4])
        if parts:
            withparts += 1
            for k in parts:
                hist[k] += 1
            if max(parts) >= r["npart"]:
                viol += 1
            if r["npart"] >= 2 and len(parts) > 1:
                p2_multi += 1
    chk("records checked", len(D.recs), PIN["part_records_checked"])
    chk("records with part-bearing primitives", withparts, PIN["part_records_with_parts"])
    chk("records whose geometry indexes PAST its array", viol, PIN["part_violations"])
    chk("part-byte value histogram", dict(hist), PIN["part_hist"])
    chk("P>=2 records that actually exercise more than one part", p2_multi,
        PIN["stride8_falsified_records"])
    print("   ** THE ARITY, CORROBORATED FROM OUTSIDE THE HEADER (refuter 2): every textured face"
          " carries a `part` byte SELECTING one entry of the binding array.  Over %d records,"
          " max(part) >= P on %d.  Histogram %s, topping out below the corpus max P of 7.  Every"
          " P>=2 record exercises more than one part (%d/%d), so the extra entries are LIVE.  Under"
          " stride 8, P' = (recLen-8)//16 and all %d P>=2 records would index past their array -- a"
          " CATEGORICAL falsification, stronger than the 90.3 %% vs 46.6 %% score."
          % (len(D.recs), viol, dict(sorted(hist.items())), p2_multi, PIN["invisible_records"],
             PIN["invisible_records"]))

    # ★★ THE CLUT-ARITY TEST -- the round's only calibration with power over a P>=2 byte
    n = agr = dis = exact = bucket = single = dual = 0
    all_agr = all_dis = all_d15 = all_unres = unres_vis = 0
    split_list = split_bucket = null_ar = 0
    rand_hit = rand_n = 0
    amb_num = amb_den = 0.0
    rng2 = random.Random(4242)
    list_sizes = []
    for r in D.recs:
        ef, blob, P = r["ef"], D.blobs[r["ef"]], r["npart"]
        wa, bycell, pool = D.word_arity[ef], D.pal_by_cell[ef], D.pal_entries[ef]
        list_sizes.append(len(wa))
        iv, sp = _iv(blob, r), _split(blob, r)
        for k in range(P):
            tp, cw = iv[k]
            bpp = dec(tp)[2]
            invisible = r["kit_blind"] or k > 0
            # the WHOLE-CORPUS view first
            if bpp == 15:
                all_d15 += 1
            elif not cw or RS.clut_word_xy(cw) not in bycell:
                all_unres += 1
                if not invisible:
                    unres_vis += 1
            else:
                want = 16 if bpp == 4 else 256
                if want in bycell[RS.clut_word_xy(cw)]:
                    all_agr += 1
                else:
                    all_dis += 1
            if not invisible or bpp == 15 or not cw:
                continue
            cell = RS.clut_word_xy(cw)
            ents = bycell.get(cell)
            if ents is None:
                continue
            want = 16 if bpp == 4 else 256
            n += 1
            if len(ents) > 1:
                dual += 1
            else:
                single += 1
            if want in ents:
                agr += 1
            else:
                dis += 1
            if cw in wa:
                exact += 1
                if want in wa[cw]:
                    bucket += 1
            if pool:
                amb_num += sum(1 for e in pool if e == want) / len(pool)
                amb_den += 1
            stp, scw = sp[k]
            if scw in wa:
                split_list += 1
                sb = dec(stp)[2]
                if sb != 15 and (16 if sb == 4 else 256) in wa[scw]:
                    split_bucket += 1
            o = r["at"] + 8 + 4 * P + 4 * k + 2
            if o + 2 <= r["at"] + r["reclen"] and u16(blob, o) in wa:
                null_ar += 1
            for _ in range(10):
                rand_n += 1
                if u16(blob, r["at"] + 2 * rng2.randrange(r["reclen"] // 2)) in wa:
                    rand_hit += 1
    chk("CLUT-arity denominator (invisible INDEXED slots)", n, PIN["clut_n"])
    chk("CLUT arity AGREE", agr, PIN["clut_agree"])
    chk("CLUT arity DISAGREE", dis, PIN["clut_disagree"])
    chk("the EXACT-WORD test", exact, PIN["clut_exact_word"])
    chk("... landing in the bucket the tpage's depth demands", bucket, PIN["clut_bucket_ok"])
    chk("cells declaring a SINGLE arity (so the test is not vacuous)", single, PIN["clut_single_arity"])
    chk("cells declaring BOTH", dual, PIN["clut_dual_arity"])
    chk("all slots AGREE", all_agr, PIN["clut_all_agree"])
    chk("all slots DISAGREE", all_dis, PIN["clut_all_disagree"])
    chk("all slots direct-15bpp", all_d15, PIN["clut_all_direct15"])
    chk("all slots unresolvable", all_unres, PIN["clut_all_unresolvable"])
    chk("... and every unresolvable one is KIT-VISIBLE", unres_vis, PIN["clut_unresolvable_kit_visible"])
    chk("null: random halfword from the record's own bytes", rand_hit, PIN["clut_null_random_in_list"])
    chk("null trials", rand_n, PIN["clut_null_random_trials"])
    chk("null: the in-record second array", null_ar, PIN["clut_null_inrecord"])
    chk("control: the SPLIT reading's clut word in the list", split_list, PIN["clut_split_in_list"])
    chk("... with a matching bucket", split_bucket, PIN["clut_split_bucket"])
    chk("the ambient accidental-arity floor", round(amb_num / amb_den, 4), PIN["clut_ambient"])
    print("   ** THE CLUT-ARITY TEST -- THE ONLY RUNG IN THIS ROUND WITH POWER OVER A P>=2 BYTE.")
    print("      The id-0 payload header INDEPENDENTLY declares each palette's entry count"
          " (+0x0c nClut4, +0x0e nClut8, +0x10 clutWord[]) and 16 <=> 4bpp / 256 <=> 8bpp, while"
          " the tpage's bits 7-8 state the binding's depth.  Two halves of one fact, never joined.")
    print("      over the %d kit-INVISIBLE indexed slots: AGREE %d / DISAGREE %d ; EXACT-WORD"
          " membership %d/%d ; bucket %d/%d ; cells declaring a single arity %d/%d (so no row is"
          " vacuous)" % (n, agr, dis, exact, n, bucket, n, single, n))
    print("      all %d slots: %d AGREE / %d DISAGREE / %d direct-15bpp / %d unresolvable -- and"
          " all %d unresolvable are KIT-VISIBLE"
          % (len(D.slots), all_agr, all_dis, all_d15, all_unres, unres_vis))
    print("      NULLS, because 264/264 with no floor is an assertion: random halfword from the"
          " record's own bytes %d/%d = %.1f %% ; the in-record null %d/%d ; the SPLIT reading %d/%d"
          " in-list and %d/%d bucket-ok ; ambient accidental-arity floor %.1f %% ; mean clutWord"
          " list size %.1f" % (rand_hit, rand_n, 100.0 * rand_hit / rand_n, null_ar, n,
                               split_list, n, split_bucket, n, 100.0 * amb_num / amb_den,
                               sum(list_sizes) / len(list_sizes)))

    # ★ THE SPLIT-ARRAY CONTROL, on the declared-column predicate too
    sp_col = sp_legal = iv_legal = 0
    for r in D.recs:
        blob, ef, P = D.blobs[r["ef"]], r["ef"], r["npart"]
        iv, sp = _iv(blob, r), _split(blob, r)
        for k in range(P):
            if not (r["kit_blind"] or k > 0):
                continue
            if dec(sp[k][0])[0] in dcol[ef]:
                sp_col += 1
            if sp[k][0] <= 0x1FF:
                sp_legal += 1
            if iv[k][0] <= 0x1FF:
                iv_legal += 1
    chk("SPLIT reading, declared column", sp_col, PIN["split_declared_col"])
    chk("SPLIT reading, legal 9-bit page word", sp_legal, PIN["split_legal"])
    chk("SHIPPED reading, legal 9-bit page word", iv_legal, PIN["interleaved_legal"])
    print("   * THE SPLIT-ARRAY CONTROL -- the only alternative with a PROVENANCE argument (the"
          " kit's own EC.ModelPackage stores tpage[P] then clut[P]), consuming the same 4P bytes,"
          " ending at the same arrayB, byte-identical at P==1.  Nobody had scored it.")
    print("      declared column: SHIPPED %d/%d = %.1f %% vs SPLIT %d/%d = %.1f %% ;"
          " legal 9-bit word: SHIPPED %d/%d vs SPLIT %d/%d ; CLUT word in the container's own list:"
          " SHIPPED %d/%d vs SPLIT %d/%d ; bucket: SHIPPED %d/%d vs SPLIT %d/%d"
          % (shipped, len(inv), 100.0 * shipped / len(inv), sp_col, len(inv),
             100.0 * sp_col / len(inv), iv_legal, len(inv), sp_legal, len(inv),
             exact, n, split_list, n, bucket, n, split_bucket, n))
    print("      -> the SHIPPED interleaved reading wins on all four.  BY-PRODUCT: all %d invisible"
          " CLUT words are already members of the id-0 header's own list, so ARCHIVES CARRY NO"
          " PALETTES -- the read-side twin of 'no writer record lives in id-2'." % exact)

    # the record predicate's own soundness floor
    amb = 0
    for b in D.blobs.values():
        pos = 0
        while True:
            k = b.find(_NEEDLE, pos)
            if k < 0:
                break
            amb += 1
            pos = k + 1
    chk("ambient `so` magic occurrences corpus-wide (ANY alignment)", amb, PIN["magic_total"])
    tot = sum(len(b) for b in D.blobs.values())
    chk("corpus bytes", tot, PIN["corpus_bytes"])
    print("   RECORD-PREDICATE SOUNDNESS: the acceptance test is TWO independent 16-bit matches"
          " (magic AND a length landing exactly on the GEOM).  Refuter 1's three constructed nulls"
          " -- displaced target, random payload, byte-SHUFFLED window -- score 0 hits in 13,555"
          " trials (its numbers, not re-rolled here); ambient magic density re-measured here is"
          " %d occurrences over %d corpus bytes = 1 per ~%.0f kB." % (amb, tot, tot / amb / 1024))


# --------------------------------------------------------------------------- G7
def g7_deflation(D: Data) -> None:
    print("[G7] THE DEFLATION -- 65 gained a DEPTH; 26 clear everything else")
    unk, p_rows, p_keys, p_gain, p_dual, g_keys, g_gain, g_dual, arch, a_keys, new = _channels(D)
    new_una = set(k for k in new if verdict(arch[k].elements()) is not None)

    readerless = sum(1 for k in new_una if D.C[k]["n_readers"] == 0)
    mp = sum(1 for k in new_una if D.C[k]["hz_multi_palette"])
    pw = sorted(D.C[k]["id"] for k in new_una
                if D.C[k]["hz_program_write"] or D.C[k]["hz_program_write_here"])
    ab = sum(1 for k in new_una if D.C[k]["hz_attribution_blind"])
    chk("readerless", readerless, PIN["reach_readerless"])
    chk("census hz_multi_palette", mp, PIN["reach_census_multi_palette"])
    chk("hz_program_write", len(pw), PIN["reach_program_write"])
    chk("all program-write cells sit in ONE container",
        len(set(s.split(".")[0] for s in pw)), 1)
    chk("hz_attribution_blind", ab, PIN["reach_attribution_blind"])
    chk("... and NOT blind", len(new_una) - ab, PIN["reach_not_blind"])

    # CLASS C re-derived from the BINDERS at column granularity, because the census's flag is
    # READER-derived and every one of these cells is readerless.
    colclut: Dict[Tuple[int, int], set] = defaultdict(set)
    for s in D.slots:
        colclut[(s["ef"], s["page"][0])].add(s["clut"])
    for ef, blob in D.blobs.items():
        try:
            a = RS.attribution(blob, include_direct=True)
        except Exception:                                                      # noqa: BLE001
            continue
        for b in a.bindings:
            colclut[(ef, dec(b.tpage)[0])].add(b.clut_word)
    cc = sorted(D.C[k]["id"] for k in new_una if len(colclut[(k[0], k[1])]) > 1)
    chk("class C, re-derived from the BINDERS", len(cc), PIN["reach_class_c"])
    clean = [k for k in new_una
             if len(colclut[(k[0], k[1])]) == 1
             and not (D.C[k]["hz_program_write"] or D.C[k]["hz_program_write_here"])]
    chk("genuinely CLEAN", len(clean), PIN["reach_clean"])
    f15 = sorted(D.C[k]["id"] for k in new_una if verdict(arch[k].elements()) == 15)
    chk("15bpp cells inside the reach", len(f15), PIN["reach_15bpp"])
    print("   ** THE REACH's REAL BOTTOM LINE IS %d, NOT %d.  %d/%d of the gained cells are"
          " READERLESS, and the census's hz_multi_palette is READER-derived, so its clean %d is"
          " VACUOUS rather than a clear.  Re-derived from the BINDERS at column granularity:"
          " %d sit on a column bound with 2-4 distinct CLUT words."
          % (len(clean), len(new_una), readerless, len(new_una), mp, len(cc)))
    print("   honest split: %d clean + %d class-C + %d program-write (all in %s) = %d, with the"
          " overlap counted once.  hz_attribution_blind is CONTAINER-level so %d carry it and %d do"
          " not, while ALL %d are readerless -- reported, then EXCLUDED from the clean predicate."
          % (len(clean), len(cc), len(pw), sorted(set(s.split(".")[0] for s in pw)), len(new_una),
             ab, len(new_una) - ab, len(new_una)))
    print("   the %d 15bpp cells in the reach carry THE GHOST-LAYER OBSERVATION's prior: %s"
          % (len(f15), ", ".join(f15)))
    # the clean set NAMED, so sec 8.3's cast recommendation is checkable rather than asserted
    direct = set()
    for s in D.slots:
        if not s["invisible"]:
            continue
        px, py = s["page"]
        low = (s["ef"], px, py + CELL_LINES)
        if low not in D.C:
            continue
        tb = D.uvbox[(s["ef"], s["geom"])].get(s["part"])
        if tb and tb[4] and tb[3] >= CELL_LINES:
            direct.add(low)
    vehicles = sorted(D.C[k]["id"] for k in set(clean) & direct)
    chk("clean cells ALSO directly sampled -- sec 8.3's cast vehicles", len(vehicles),
        PIN["cast_vehicles"])
    print("   the %d CLEAN cells, by name: %s"
          % (len(clean), ", ".join(sorted(D.C[k]["id"] for k in clean))))
    print("   -> of those, %d are ALSO DIRECTLY SAMPLED by the invisible model's own UVs and are"
          " sec 8.3's cast vehicles: %s" % (len(vehicles), ", ".join(vehicles)))

    # ★ THE SAFETY FINDING: the SHIPPED palette lane's DERIVED PRIVATE verdicts
    by_ef: Dict[int, List[dict]] = defaultdict(list)
    for r in D.recs:
        if r["npart"] >= 2:
            by_ef[r["ef"]].append(r)
    n_priv = n_shared = n_unknown = 0
    false_priv = []
    gains = 0
    for ef, blob in D.blobs.items():
        try:
            pm = RS.palette_map(blob, attrib=RS.attribution(blob))
        except Exception:                                                      # noqa: BLE001
            continue
        extra: Dict[tuple, set] = defaultdict(set)
        for r in by_ef.get(ef, ()):
            for tp, cw in _iv(blob, r):
                if dec(tp)[2] == 15 or not cw:
                    continue
                extra[(RS.clut_word_xy(cw), 16 if dec(tp)[2] == 4 else 256)].add(r["geom"])
        for pal in pm.palettes:
            if pal.slot < 0:
                continue
            add = extra.get((pal.vram, pal.entries), set()) - set(pal.binders or ())
            if pal.binders and len(pal.binders) == 1 and not pal.shared:
                n_priv += 1
                if add:
                    false_priv.append("ef%03d %s" % (ef, pal.name))
            elif pal.shared and pal.binders:
                n_shared += 1
            elif pal.shared:
                n_unknown += 1
                if add:
                    gains += 1
    chk("palettes the kit calls DERIVED PRIVATE", n_priv, PIN["n_private"])
    chk("palettes the kit calls DERIVED SHARED", n_shared, PIN["n_shared"])
    chk("palettes the kit calls SHARED-UNKNOWN", n_unknown, PIN["n_unknown"])
    chk("** FALSE PRIVATE", len(false_priv), PIN["false_private"])
    chk("SHARED-UNKNOWN palettes a dropped record would give a named binder", gains,
        PIN["unknown_gains"])
    print("   * THE SAFETY FINDING, arguably worth more than the depth gain: reskin._apply_"
          "attribution publishes shared=False with 'DERIVED PRIVATE: exactly one GEOM model binds"
          " this cell' whenever len(binders)==1.  Running the SHIPPED path unmodified: %d PRIVATE /"
          " %d SHARED / %d SHARED-UNKNOWN, and %d of the PRIVATE verdicts are FALSE -- a dropped"
          " record binds the same (vram, entries): %s"
          % (n_priv, n_shared, n_unknown, len(false_priv), ", ".join(sorted(false_priv))))
    print("   AND THE BLINDNESS IS ASYMMETRIC: %d SHARED-UNKNOWN palettes would gain a named binder,"
          " i.e. the 0-binder branch is currently MORE conservative than the bytes require.  The"
          " unsafe direction is only the len(binders)==1 branch." % gains)


# --------------------------------------------------------------------------- G8
def g8_critic(D: Data) -> None:
    print("[G8] THE CRITIC'S CORRECTIONS, RE-MEASURED")

    # (a) THE UV OPERAND -- calibrated against the kit's own answer BEFORE it is used to judge one
    ok = n = 0
    for p in D.paths[:120]:
        ef = int(os.path.basename(p)[2:5])
        blob = D.blobs[ef]
        mp = EC.creature_package(blob)
        cg = mp.geom_offset if mp is not None else None
        gmap = {g.base: g for g in EC.scan_geom(blob) if g.base != cg}
        for m in RP.bound_models(blob):
            if not m.faces:
                continue
            g = gmap.get(m.geom)
            if g is None:
                continue
            box = _uv_boxes(blob, g)
            if not box:
                continue
            ul = min(b[0] for b in box.values())
            uh = max(b[1] for b in box.values())
            vl = min(b[2] for b in box.values())
            vh = max(b[3] for b in box.values())
            n += 1
            if (ul, uh) == m.u and (vl, vh) == m.v:
                ok += 1
    chk("UV calibration vs repaint.bound_models", ok, PIN["uv_cal"])
    chk("UV calibration denominator", n, PIN["uv_cal"])
    print("   (a) CALIBRATE FIRST: the dereferenced decode reproduces repaint.bound_models' own"
          " (u,v) ranges on %d/%d kit-visible bound models.  A UV instrument that cannot re-find"
          " the kit's own answer may not be used to judge one." % (ok, n))

    boxed = hxd = vyd = 0
    bmax = tmax = 0
    for s in D.slots:
        g = None
        for ef, geoms in ((s["ef"], D.geoms_by_ef[s["ef"]]),):
            pass
        blob = D.blobs[s["ef"]]
        tb = D.uvbox[(s["ef"], s["geom"])].get(s["part"])
        if not tb or not tb[4]:
            continue
        # the PUBLISHED (broken) read: the pool INDEX treated as the UV word
        bb = _broken_box(blob, D, s)
        if bb is None:
            continue
        boxed += 1
        per = KT.TEXELS_PER_HW[s["bpp"]]
        px, py = s["page"]
        if (px + tb[0] // per, px + tb[1] // per) != (px + bb[0] // per, px + bb[1] // per):
            hxd += 1
        if (py + tb[2], py + tb[3]) != (py + bb[2], py + bb[3]):
            vyd += 1
        tmax = max(tmax, tb[3])
        bmax = max(bmax, bb[3])
    chk("slots carrying a UV box", boxed, PIN["uv_slots_boxed"])
    chk("published vy WRONG", vyd, PIN["uv_damage_vy"])
    chk("published hx WRONG", hxd, PIN["uv_damage_hx"])
    chk("published corpus max v (pool INDICES)", bmax, PIN["uv_broken_v_max"])
    chk("true corpus max v", tmax, PIN["uv_true_v_max"])
    print("   ** THE UV COVER IS DECODED FROM THE WRONG OPERAND in L1 AND in refuter 1 (both certify"
          " the FORMULA against repaint.bound_models, and the formula is right; the OPERAND is"
          " not): over %d slots carrying a box, vy is wrong on %d and hx on %d; published corpus"
          " max v = %d (pool indices), TRUE max v = %d." % (boxed, vyd, hxd, bmax, tmax))

    # ef184 re-adjudicated on the corrected instrument
    for geom, part in ((PIN["ef184_visible_geom"], 0), (PIN["ef184_invisible_geom"], 1)):
        tb = D.uvbox[(184, geom)][part]
        s = [x for x in D.slots if x["ef"] == 184 and x["geom"] == geom and x["part"] == part][0]
        per = KT.TEXELS_PER_HW[s["bpp"]]
        px, py = s["page"]
        print("      ef184 GEOM %#x part %d: TRUE hx %d..%d  vy %d..%d  (%dbpp)"
              % (geom, part, px + tb[0] // per, px + tb[1] // per, py + tb[2], py + tb[3], s["bpp"]))
    tb_v = D.uvbox[(184, PIN["ef184_visible_geom"])][0]
    tb_i = D.uvbox[(184, PIN["ef184_invisible_geom"])][1]
    chk("ef184 visible model does NOT spill past column 448", 448 + tb_v[1] // 4 <= 511, True)
    chk("ef184 invisible part-1 does NOT spill past column 448", 448 + tb_i[1] // 2 <= 511, True)
    chk("the two models' halfword ranges OVERLAP",
        max(448 + tb_v[0] // 4, 448 + tb_i[0] // 2) <= min(448 + tb_v[1] // 4, 448 + tb_i[1] // 2),
        True)
    chk("** and NEITHER reaches the lower cell: max v is 127, the LAST line of the upper cell",
        max(tb_v[3], tb_i[3]), 127)
    print("      -> NEITHER model spills into column 512 as L1's published numbers implied (the"
          " round's most-quoted adjudication, corrected), and their halfword ranges OVERLAP on"
          " 448..479 -- the SAME texels read at 4bpp by one model and 8bpp by the other.  THE"
          " DEPTH COROLLARY's mechanism, on shared bytes, for the first time.")
    print("      ** AND THE CRITIC'S OWN PROSE OVER-REACHES HERE AND IS CORRECTED RATHER THAN"
          " INHERITED: it says both true v ranges 'reach 383, so ef184:448,384 is DIRECTLY"
          " SAMPLED by both'.  MEASURED: max v is %d, i.e. line %d -- the LAST line of the UPPER"
          " cell.  ef184:448,384's depth is INHERITED from the column like the other 30."
          % (max(tb_v[3], tb_i[3]), 256 + max(tb_v[3], tb_i[3])))

    # (b) five of the 65 are DIRECT reads, not inherited
    unk, p_rows, p_keys, p_gain, p_dual, g_keys, g_gain, g_dual, arch, a_keys, new = _channels(D)
    new_una = set(k for k in new if verdict(arch[k].elements()) is not None)
    reach = 0
    cells = set()
    for s in D.slots:
        if not s["invisible"]:
            continue
        px, py = s["page"]
        low = (s["ef"], px, py + CELL_LINES)
        if low not in D.C:
            continue
        tb = D.uvbox[(s["ef"], s["geom"])].get(s["part"])
        if not tb or not tb[4]:
            continue
        if tb[3] >= CELL_LINES:
            reach += 1
            cells.add(low)
    chk("invisible slots whose TRUE UVs reach the lower cell", reach, PIN["direct_lower_slots"])
    chk("... distinct lower cells", len(cells), PIN["direct_lower_cells"])
    chk("... of which inside the 65", len(cells & new_una), PIN["direct_lower_in_the_65"])
    print("   (b) ** FIVE OF THE 65 GAINS ARE DIRECT READS, NOT INHERITED.  Both dossiers ship '31"
          " of the 65 are LOWER halves -- depth INHERITED, never direct.  No instrument has seen a"
          " model sample those bytes.'  The container's OWN UV pool is that instrument: %d invisible"
          " slots reach v >= 128, naming %d lower cells directly, %d of them inside the 65: %s"
          % (reach, len(cells), len(cells & new_una),
             ", ".join(sorted(D.C[k]["id"] for k in cells & new_una))))

    # (c) THE WALL FROM THE OTHER SIDE
    chk("halfword-aligned `so` magic sites corpus-wide", D.wall["magic"], PIN["wall_magic_sites"])
    chk("shape-valid sites", D.wall["shape_valid"], PIN["wall_shape_valid"])
    chk("... targeting a GEOM base", D.wall["target_geom"], PIN["wall_target_geom"])
    chk("... targeting anything else", D.wall["target_not_geom"], PIN["wall_target_not_geom"])
    chk("magic sites inside the 222 BLIND containers", D.wall["blind_magic"], PIN["wall_blind_magic"])
    chk("... shape-valid", D.wall["blind_shape_valid"], PIN["wall_blind_shape_valid"])
    print("   (c) ** THE WALL RE-TESTED FROM THE OTHER SIDE, which nobody did: every halfword-"
          "aligned `so` magic in all 372 containers -- %d sites, %d shape-valid, %d/%d targeting a"
          " GEOM base and %d targeting anything else.  Inside the 222 blind containers: %d sites,"
          " %d shape-valid.  There is NO `so`-shaped binding record on a non-GEOM drawable anywhere"
          " in the corpus -- a POSITIVE law, stronger than an absence-of-models observation."
          % (D.wall["magic"], D.wall["shape_valid"], D.wall["target_geom"], D.wall["shape_valid"],
             D.wall["target_not_geom"], D.wall["blind_magic"], D.wall["blind_shape_valid"]))

    # (d) THE ARCHIVE DIRECTORY IS RESIDENCY, NOT A DRAW REFERENCE
    g_named = r_named = 0
    named_by_res = Counter()
    per_ef = Counter()
    for ef, geoms in D.geoms_by_ef.items():
        t = D.dir_targets[ef]
        g_named += len(set(geoms) & t)
        for r in D.recs:
            if r["ef"] != ef:
                continue
            if r["at"] in t or r["geom"] in t:
                r_named += 1
                named_by_res[r["res_id"]] += 1
                per_ef[ef] += 1
    chk("id-2 directory entries", D.dir_entries, PIN["dir_entries"])
    chk("... negative (the external-file form)", D.dir_neg, PIN["dir_neg"])
    chk("GEOM blocks a directory entry names", g_named, PIN["dir_geoms_named"])
    chk("records a directory entry names", r_named, PIN["dir_records_named"])
    chk("... by resource", dict(named_by_res), PIN["dir_named_by_res"])
    for ef in (429, 446, 390, 211):
        chk("ef%03d directory-named records" % ef, per_ef[ef], PIN["dir_ef%d" % ef])
    print("   (d) ** THE ROUND'S OWN NAMED DRAWN/UNDRAWN CANDIDATE, CLOSED: %d id-2 directory"
          " entries (%d negative) name %d GEOM blocks and %d records, and the split is"
          " DETERMINISTIC -- %s, with every id-6/id-3/id-8 record unnamed.  On the vehicles it"
          " discriminates NOTHING: ef429 (bound-never-drawn) %d/%d named, ef446 (DREW at 8bpp)"
          " %d/%d.  'Directory-named' is RESIDENCY, not a reference."
          % (D.dir_entries, D.dir_neg, g_named, r_named, dict(sorted(named_by_res.items())),
             per_ef[429], PIN["ef429_records"], per_ef[446], PIN["ef446_records"]))

    # (e) THE ORDER QUESTION -- reopened on the corrected UVs, and STILL not settled
    rng = random.Random(20260729)
    nrec = nparts = ident = revd = ph = pt = 0
    for r in D.recs:
        P = r["npart"]
        if P < 2:
            continue
        blob, ef = D.blobs[r["ef"]], r["ef"]
        slots = _iv(blob, r)
        bpps = [dec(t)[2] for t, _c in slots]
        if len(set(bpps)) < 2:
            continue
        box = D.uvbox[(ef, r["geom"])]
        parts = sorted(k for k, b in box.items() if b[4])
        if len(parts) < 2:
            continue
        nrec += 1
        nparts += len(parts)

        def score(assign):
            h = 0
            for pi, si in assign.items():
                if si >= P or pi not in box:
                    continue
                width = 256 if bpps[si] == 4 else (128 if bpps[si] == 8 else 64)
                if box[pi][1] < width:
                    h += 1
            return h

        ident += score({p: p for p in parts})
        revd += score({p: P - 1 - p for p in parts})
        for _ in range(50):
            perm = list(range(P))
            rng.shuffle(perm)
            ph += score({p: perm[p] for p in parts})
            pt += len(parts)
    multi_tp = 0
    for r in D.recs:
        if r["npart"] < 2:
            continue
        if len(set(t for t, _c in _iv(D.blobs[r["ef"]], r))) > 1:
            multi_tp += 1
    chk("multi-part records naming MORE THAN ONE distinct tpage", multi_tp, PIN["order_multi_tpage"])
    chk("depth-mixing records", nrec, PIN["order_records"])
    chk("parts scored", nparts, PIN["order_parts"])
    chk("identity", ident, PIN["order_identity"])
    chk("reversed", revd, PIN["order_reversed"])
    print("   (e) THE ORDER QUESTION, REOPENED ON THE CORRECTED UVs AND STILL NOT SETTLED: on a"
          " bpp-SENSITIVE page-fit predicate over %d depth-mixing records / %d parts -- identity"
          " %d = %.1f %%, reversed %d = %.1f %%, %d random permutations %d/%d = %.1f %%.  Identity"
          " is best and reversed worst (the first time the ranking has come out that way) but sits"
          " ~0.9 sigma above random.  DO NOT SHIP the 'indexed by the part byte' clause as measured;"
          " its ARITY is measured (G6), its ORDER is not -- and it is LOAD-BEARING, because %d of"
          " the %d multi-part records name MORE THAN ONE distinct tpage."
          % (nrec, nparts, ident, 100.0 * ident / nparts, revd, 100.0 * revd / nparts,
             50, ph, pt, 100.0 * ph / pt, multi_tp, PIN["invisible_records"]))


def _broken_box(blob: bytes, D: Data, s: dict):
    """The PUBLISHED read, reconstructed: the pool INDEX treated as the UV word."""
    key = (s["ef"], s["geom"], "broken")
    cache = getattr(D, "_bcache", None)
    if cache is None:
        cache = D._bcache = {}
    if key not in cache:
        box: Dict[int, List[int]] = defaultdict(lambda: [1 << 30, -1, 1 << 30, -1, 0])
        mp = EC.creature_package(blob)
        cg = mp.geom_offset if mp is not None else None
        g = None
        for cand in EC.scan_geom(blob):
            if cand.base == s["geom"] and cand.base != cg:
                g = cand
                break
        if g is not None:
            for mesh in g.meshes:
                for pr in EC.iter_primitives(blob, g, mesh):
                    uvs = pr.get("uv")
                    if not uvs or "part" not in pr:
                        continue
                    cv = box[pr["part"]]
                    for w in uvs:
                        uu, vv = w & 0xFF, (w >> 8) & 0xFF
                        cv[0] = min(cv[0], uu)
                        cv[1] = max(cv[1], uu)
                        cv[2] = min(cv[2], vv)
                        cv[3] = max(cv[3], vv)
                    cv[4] += 1
        cache[key] = box
    b = cache[key].get(s["part"])
    return b if b and b[4] else None


# --------------------------------------------------------------------------- G9
#: BENIGN BY NAME, not by silence.  Adjudicated literals go here with their reason.
_ADJUDICATED: Dict[bytes, str] = {}


def _untracked_new_files() -> List[str]:
    """THE PROVENANCE SURFACE MOVES WHILE THE ROUND IS JUDGED -- so ASK GIT, never a hand-written
    list.  A concurrent lane's new file in this directory must not be silently unscanned."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", _REPO, "status", "--porcelain"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:                                                          # noqa: BLE001
        return []
    names = []
    for line in out.splitlines():
        if not (line.startswith("?? ") or line.startswith(" M ") or line.startswith("M ")):
            continue
        rel = line[3:].strip().strip('"')
        p = os.path.join(_REPO, rel.replace("/", os.sep))
        if os.path.isfile(p):
            names.append(p)
        elif os.path.isdir(p):
            for root, _d, fs in os.walk(p):
                names.extend(os.path.join(root, f) for f in fs)
    return sorted(names)


def _byte_constants(path: str) -> List[bytes]:
    """AST `bytes` constants (a regex misses triple-quoted, adjacent and non-`b'...'` spellings)
    PLUS integer sequences re-encoded to bytes, PLUS hex runs in ANY committable text."""
    out: List[bytes] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except Exception:                                                          # noqa: BLE001
        return out
    if path.lower().endswith(".py"):
        import ast
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return out
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
                out.append(node.value)
            elif isinstance(node, (ast.Tuple, ast.List)):
                vals = [e.value for e in node.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, int)
                        and 0 <= e.value < 256]
                if len(vals) == len(node.elts) and len(vals) >= 6:
                    out.append(bytes(vals))
    for m in re.finditer(r"(?:\\x[0-9a-fA-F]{2}){6,}", src):
        try:
            out.append(bytes.fromhex(m.group(0).replace("\\x", "")))
        except Exception:                                                      # noqa: BLE001
            pass
    return out


def g9_provenance(D: Data) -> None:
    print("[G9] PROVENANCE -- what this rung commits is a DERIVATION, never a stock byte")
    blobs = list(D.blobs.values())
    new = _untracked_new_files()
    files = [p for p in new if os.path.splitext(p)[1].lower() in (".py", ".md", ".toml")]
    stockish = [p for p in new
                if os.path.splitext(p)[1].lower() in (".bytes", ".png", ".tga", ".bmp", ".dds")]
    chk("no stock-shaped asset added to the checkout", len(stockish), 0)
    found = adjudicated = leaks = 0
    for p in files:
        for lit in _byte_constants(p):
            if len(lit) < 6 or len(set(lit)) < 2:
                continue
            found += 1
            hits = sum(1 for b in blobs if lit in b)
            if hits and lit in _ADJUDICATED:
                adjudicated += 1
                print("      %r in %s: in %d containers -- ADJUDICATED BENIGN: %s"
                      % (lit, os.path.basename(p), hits, _ADJUDICATED[lit]))
                continue
            if hits:
                leaks += 1
                print("      byte literal %r in %s appears in %d corpus containers"
                      % (lit, os.path.basename(p), hits))
            chk("literal %r in %s is not corpus data" % (lit, os.path.basename(p)), hits, 0)
    print("   file list came from `git status --porcelain`, NOT a hand-written list: %d new text"
          " files scanned (%s)"
          % (len(files), ", ".join(sorted(os.path.basename(f) for f in files))))
    print("   byte constants of >= 6 non-uniform bytes: %d found, %d adjudicated benign by name,"
          " %d unadjudicated leaks" % (found, adjudicated, leaks))
    print("   stock-shaped files (.bytes/.png/.tga/.bmp/.dds) added to the checkout: %d"
          % len(stockish))
    for name in ("L1-ID2-SWEEP.md", "L2-ID2-JOIN.md", "CRITIC.md", "v1-DECODER-REFUTATION.md",
                 "id2_sweep.json", "id2_join.json"):
        p = os.path.join(LANE, name)
        inside = os.path.abspath(p).lower().startswith(os.path.abspath(_REPO).lower())
        chk("lane artifact %s outside the checkout" % name, inside, False)
    print("   every lane dossier, decoded listing and recovered constant stays OUTSIDE the"
          " checkout, under %s" % LANE)
    try:
        from ff9mapkit.summons import export as _EX
        refused = False
        try:
            _EX.assert_local_only(_REPO)
        except Exception:                                                      # noqa: BLE001
            refused = True
        chk("export.assert_local_only refuses a repo destination", refused, True)
        print("   export.assert_local_only refuses a repo destination: %s" % refused)
    except Exception as exc:                                                   # noqa: BLE001
        print("   export.assert_local_only NOT CHECKED (%s) -- instrument absent, reported not"
              " assumed" % type(exc).__name__)


# --------------------------------------------------------------------------- runner
GATES = [
    ("G0", "CALIBRATION (own decoder == reskin; two known answers; and its LIMIT printed)",
     g0_calibrate),
    ("G1", "THE POPULATION AND THE FORMAT (502/649/126/309; two L1 numbers corrected)",
     g1_population),
    ("G2", "THE PREMISE FALSIFIED (the census walker already descends into id-2)", g2_premise),
    ("G3", "THE SWEEP AND THE REACH (73 new; the residue's actual movement)", g3_reach),
    ("G4", "THE GHOST-LAYER VERDICT (0 hits, 4 misses, 2 vacuous passes)", g4_ghost),
    ("G5", "CONFLICTS + AGREEMENT + THE TAUTOLOGY CONTROL it does not beat", g5_conflicts),
    ("G6", "THE CONTROLS (L1's four, the part-byte test, and the CLUT-ARITY rung)", g6_controls),
    ("G7", "THE DEFLATION (65 -> 26) and the FIVE false DERIVED PRIVATE verdicts", g7_deflation),
    ("G8", "THE CRITIC'S CORRECTIONS (the UV operand, the wall, the directory)", g8_critic),
    ("G9", "PROVENANCE (no SE bytes committable; the dossiers stay in SCRATCH)", g9_provenance),
]


def main(argv=None) -> int:
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("G"))
    print("W6b-3 GATES -- the archive rung, every headline number re-measured")
    print("corpus: %s" % SCRATCH)
    print("=" * 72)
    D = Data()
    board = []
    for tag, title, fn in GATES:
        if only and tag not in only:
            continue
        before = len(_FAILS)
        try:
            fn(D)
            ok = len(_FAILS) == before
        except Exception as exc:                                   # a crashed gate is a red gate
            _FAILS.append("%s raised %s: %s" % (tag, type(exc).__name__, exc))
            ok = False
        board.append((tag, title, ok))
        print("   [%s] %s\n" % ("PASS" if ok else "FAIL", tag))
    print("=" * 72)
    for tag, title, ok in board:
        print("%-4s %s %s" % ("PASS" if ok else "FAIL", tag, title))
    if _FAILS:
        print("-" * 72)
        for f in _FAILS:
            print("  FAIL  %s" % f)
    print("=" * 72)
    print("%d/%d gates pass" % (sum(1 for _, _, ok in board if ok), len(board)))
    return 1 if _FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
