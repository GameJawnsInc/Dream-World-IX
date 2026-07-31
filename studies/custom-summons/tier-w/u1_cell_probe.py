r"""TIER W rung W6b-3iii -- THE U1 SECOND-ARRAY CAST.  ef038 (Stock Shiva), the two halves of
column 640, marked with two DIFFERENT gratings so the screen says which half the engine sampled.

    py u1_cell_probe.py                    # stage only; the install is untouched
    py u1_cell_probe.py --deploy           # snapshot the live override and write the probe over it
    py u1_cell_probe.py --deploy --mod-folder <temp>\FF9CustomMap --root <temp>\probe-root
                                           # REHEARSE the whole ledger against a folder the game
                                           # never reads.  Do this first -- it is how the Odin
                                           # probe's `\U`-in-a-docstring revert defect was found, at
                                           # zero cost, instead of at the cast.

THE QUESTION THIS PROBE ASKS -- U1: DOES THE ENGINE APPLY SECOND-ARRAY HALFWORD A AT ALL?
-----------------------------------------------------------------------------------------
`second-array-lead/REPORT.md` refuted H_V (A as a universal per-slot texture V-offset) at 0.85 and
left the positive reading R_FLAGS (A is a depth-keyed render-state bit).  Two things it could NOT
close from data: **U1** -- whether the engine reads A at all -- and one unexplained regularity, C3
(A = 0x0080 appears only on columns that physically have a lower half, 73/73).

The cast is the report's own §5 sketch, re-derived and re-sized at the machine:

  * pick a column whose readers are 8bpp with **v confined to 1..127** -- then OFFSET and SELECT are
    the same prediction, and the cast tests *applied vs not applied* cleanly;
  * mark the column's UPPER half-cell with one grating and its LOWER half-cell with a DIFFERENT one;
  * a reader's surface then NAMES the half it sampled, by COUNT and by THICKNESS.

    A APPLIED (v -> v + 128, or a page-half select)  ->  the surface shows the LOWER cell's mark
    A a FLAG, or never read                          ->  the surface shows the UPPER cell's mark
    nothing bands on any surface                     ->  BINDING-IS-NOT-A-DRAW; a RESULT, not a
                                                         failure -- fall to the next vehicle (§5 of
                                                         the study doc)

WHY ef038 AND WHY THIS COLUMN.  The vehicle is not the record the sketch named; it is the COLUMN,
and the column is far richer than the sketch assumed.  **27 of ef038's 28 non-creature `so` records
bind column 640**, and they split into TWO FAMILIES that this file re-derives on every run:

    A = 0x0080, clut 0x3dc0 -- 20 slots   THE ANSWER-CARRYING CLASS
    A = 0x0000, clut 0x3d40 --  7 slots   THE IN-CAST NEGATIVE CONTROL (0 + anything = identity, so
                                          these read the UPPER cell under EVERY live reading of A)

That control is the whole reason this vehicle was chosen over the three relaunch-class alternatives:
**the negative control rides in the same cast, on the same column, in the same frame**, so no
cross-cast comparison is needed and "the override never loaded" cannot be confused with "A is not
applied".  Seven of the pairs are even bbox-identical twins with opposite A, which puts both families
on the same shard at the same place -- superposition, not memory.

THE INSTRUMENT.  Zero-writing, unchanged from `phoenix_cell_probe.py` / `odin_cell_probe.py`: a
`0x00` byte is index 0 twice at 4bpp, index 0 once at 8bpp, and half of the cutout word `0x0000` at
15bpp -- at every depth a zeroed texel is the palette-entry-0 / transparent value.  Not load-bearing
here (all 27 readers derive 8bpp, and the probe REFUSES if that ever stops being true) but kept,
because VRAM is shared and it is the one value whose meaning does not depend on the answer measured.

★ THE COUNTS DEPART FROM THE SKETCH'S k=10 / k=2, AND THE REASON IS MEASURED, NOT AESTHETIC.  The
established encoding is *k evenly-spaced stripes*, not *period k*.  At k=2 the lower cell's stripes
sit 64 rows apart while the readers' UV patches are small (median per-face v-span 22 texels on the
headline disc), so **only 71 of that disc's 140 faces would be crossed by any band** -- half the
answer-carrying surface would show no mark, which is indistinguishable from "not drawn".  This file
uses **12 thin stripes of 4 rows upstairs, 4 fat bands of 8 rows downstairs**, and PRINTS the exact
per-reader face-crossing counts it achieves so the claim is auditable rather than asserted.  The
discriminator stays threshold-free and two-dimensional: COUNT 12 vs 4 (3:1) and THICKNESS 4 vs 8
rows (1:2), at near-equal duty (37.5 % vs 25 %) so the read is never "it got darker".

★ THE READ DIFFERS BY FAMILY, AND THAT IS DERIVED HERE EVERY RUN.  The two CLUTs decode entry 0
oppositely -- 0x3dc0's is opaque dark navy and the darkest entry in the palette, 0x3d40's is fully
transparent.  So the same grating reads as **DARK BANDS on the A=0x0080 family and as HOLES on the
A=0x0000 control family**.  An operator told only to "count dark bands" would score the entire
control family as blank.  Both readings are printed into `PROTOCOL.txt`.

THE LEDGER.  `--deploy` snapshots whatever the live override holds into THIS probe's own SCRATCH
root -- never the kit's -- verifies the readback sha, and emits a `compile()`-checked, idempotent
`revert_probe.py`.  **THE LEDGER TRAP:** revert this probe BEFORE any `summon-reskin deploy` touches
this root.  The kit takes its own first-deploy snapshot per root and never overwrites it, so a kit
deploy on top of a live probe records THE PROBE as the pre-state -- permanently.

PROVENANCE.  Every number is derived from the user's own container at run time; zero Square-Enix
bytes live in this file.  The marked container stays in SCRATCH and the install.  `pin_source`
refuses a foreign `--from` by NAME *and* by STRUCTURE (both cells' page geometry, plus the whole
column-640 reader census and its A histogram), so no other container can be staged as `ef038` and
written over the ef038 override.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------------------------
# WHERE THE KIT AND THE SIBLING INSTRUMENT LIVE.
#
# This file is written to live in `studies/custom-summons/tier-w/`, where `../../../ff9mapkit` is
# the package root and `odin_band_stamp.py` is a sibling.  It is DEVELOPED under SCRATCH, where
# neither is true.  Rather than let an import silently resolve against some other checkout, both
# roots are resolved by PROBING for a file that must exist and refusing loudly if none does -- so
# the same source regenerates byte-identically from either location, which is the property that
# makes "the parent moves it into the repo and re-runs it" checkable instead of hoped over.
# ---------------------------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
# Fallback only -- never reached when this file sits in tier-w or under the U1 SCRATCH root
# (verified both), but STALE once the worktree is gone; the _pick probing resolves first.
REPO = r"C:\gd\Dream-World-IX\.claude\worktrees\gracious-pike-9ebbb8"
_TIERW_HOME = os.path.join(REPO, "studies", "custom-summons", "tier-w")


def _pick(cands, probe_file: str, what: str) -> str:
    for c in cands:
        if os.path.exists(os.path.join(c, probe_file)):
            return os.path.abspath(c)
    raise SystemExit("REFUSED: cannot locate %s -- none of %r holds %s.  This script pins the "
                     "worktree %s; re-point REPO if it moved."
                     % (what, [os.path.abspath(c) for c in cands], probe_file, REPO))


KIT_ROOT = _pick([os.path.join(_HERE, "..", "..", "..", "ff9mapkit"),
                  os.path.join(REPO, "ff9mapkit")],
                 os.path.join("ff9mapkit", "summons", "reskin.py"), "the ff9mapkit package root")
TIERW = _pick([_HERE, _TIERW_HOME], "odin_band_stamp.py", "the tier-w instrument directory")
sys.path.insert(0, KIT_ROOT)
sys.path.insert(0, TIERW)

from ff9mapkit.summons import container as EC                     # noqa: E402
from ff9mapkit.summons import repaint as RP                       # noqa: E402
from ff9mapkit.summons import reskin as RS                        # noqa: E402
from ff9mapkit.summons import texture as TX                       # noqa: E402
# THE PLACEMENT RULE COMES FROM THE OTHER INSTRUMENT, never from a second copy of it.  A restated
# placement rule is how one instrument ends up marking lines another instrument's read assumes are
# marked -- and an offline restatement of `evenly_spaced_tops` written during the design of THIS
# cast already differed from the real one by +-1 row, which is exactly the class of error a probe
# whose whole content is a COUNT cannot survive.
from odin_band_stamp import cover_span, evenly_spaced_tops        # noqa: E402
# The ef424 cast's marks, imported for the SIGNATURE-COLLISION check.  Different container, but the
# two instruments share a screen in the operator's memory; a collision is printed LOUD, not assumed
# away.  `pin_source` is deliberately NOT imported: odin_band_stamp's is pinned to ef424's cells.
from odin_band_stamp import BANDS as CAST_B_BANDS                 # noqa: E402
from odin_band_stamp import BAND_ROWS as CAST_B_BAND_ROWS         # noqa: E402

# ============================================================================ MODULE CONSTANTS
EFFECT = 38
SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
U1_ROOT = os.path.join(SCRATCH, "repaint-w6b", "u1-second-array")
DEFAULT_ROOT = os.path.join(U1_ROOT, "cellprobe")
DEFAULT_CORPUS = os.path.join(SCRATCH, "ef%03d.bytes" % EFFECT)
MOD_ROOT = (r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
            r"\FF9CustomMap")
GAME_OVERRIDE = os.path.join(MOD_ROOT, "FF9_Data", "SpecialEffects", "ef%03d" % EFFECT)

ROW_BYTES = 128                      # 8bpp, 64 halfwords wide -> 128 texels == 128 bytes per line
CELL_ROWS = 128
CELL_BYTES = ROW_BYTES * CELL_ROWS   # 0x4000

#: THE COLUMN IS THE VEHICLE.  Not a record -- 27 of ef038's 28 non-creature `so` records bind it.
COLUMN = 640
UPPER_CELL = "cell.s0.x%d_y256" % COLUMN
LOWER_CELL = "cell.s0.x%d_y384" % COLUMN

#: THE MARKS.  ``cell -> (stripe count, byte-rows per stripe)``.  The COUNT ratio (12:4 = 3:1) and
#: the THICKNESS ratio (4:8 = 1:2) are the two independent axes of the read; the near-equal duty
#: (37.5 % vs 25 %) is deliberate, so no reader can score this by "how much got darker".
MARKS = {UPPER_CELL: (12, 4), LOWER_CELL: (4, 8)}

#: WHAT EACH MARK MEANS, once, so the protocol cannot drift from the code that writes it.
MEANING = {UPPER_CELL: "A is NOT applied to the sample (R_FLAGS, or declared-and-ignored)",
           LOWER_CELL: "A IS applied (V-offset by 128, or a page-half select -- they agree here)"}

#: ---- THE SOURCE PIN -------------------------------------------------------------------------
#: `EFFECT`, `MARKS` and `GAME_OVERRIDE` are module constants pinned to ef038 while `--from` is a
#: free path.  Point `--from` at another container and every one of them keeps pointing at ef038:
#: the probe would stage another container's bytes as `ef038.cellprobe` and `--deploy` would write
#: them over `.../SpecialEffects/ef038`.  So the pin is by NAME *and* by STRUCTURE, and the
#: structure checked is exactly what the cast rests on.
SOURCE_PIN_CELLS = {UPPER_CELL: ("so-uv", 8, 0x1946c), LOWER_CELL: ("so-uv", 8, 0x1d46c)}
#: the placement spans the marks are sized against.  If a container's declared cover moved, the
#: stripe rows move with it and every face-crossing number in the study is stale -- refuse instead.
SOURCE_PIN_COVER = {UPPER_CELL: (1, 127), LOWER_CELL: (0, 127)}
#: the column census: total binding slots on COLUMN, the A histogram, and the ONE wrap reader whose
#: v runs to 255 (record 0x79168 -- the in-cast positive control for the LOWER mark, C3).
SOURCE_PIN_COLUMN = {"slots": 27, "A": {0x0080: 20, 0x0000: 7}, "wrap_recs": (0x79168,)}
#: sha256 of the stock ef038 container, measured off the user's own install
#: (`x64/FF9_Data/resources.assets`) and equal to the corpus copy.  A pin, not documentation.
EXPECT_STOCK_SHA256 = "8f71a91b5ea8761cb072d0c5aa53fdd6cd926ec03a77634a99bf582fec4eb2a2"

SO_MAGIC = 0x6F73                    # reskin.py:309
SO_BPP = {0: 4, 1: 8, 2: 15, 3: 15}  # reskin.py:311
MAX_SO_PARTS = 15                    # reskin.py:344


def _fail(msg: str) -> "SystemExit":
    return SystemExit("REFUSED: " + msg)


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


# ============================================================================ THE COLUMN CENSUS
def column_readers(blob: bytes, column: int = COLUMN) -> list:
    """Every `so` binding slot in the container that names ``column`` -- walked from the bytes.

    Independent of `reskin.so_record`: the record walk, the tpage decode and the second-array read
    are done here from the layout the format states (magic 'so', ``recLen == 8 + 8P``,
    ``arrayB == 8 + 4P``, ``rec + recLen == geom_base``), and the self-describing law is ASSERTED on
    every record rather than trusted.  The creature GEOM is excluded -- its texture lane is the
    id-4 ModelPackage path, not the scenery page rects this cast marks.

    Per slot it also measures the reader's own faces: count, u/v range, how many faces touch
    v >= 128, and -- the number the read is scored on -- how many faces cross at least one row of
    each mark.  Those crossing counts are what make "nothing is starved" checkable instead of
    claimed.
    """
    mp = EC.creature_package(blob)
    cg = EC.creature_geom(blob, mp).base if mp is not None else None
    out = []
    for g in EC.scan_geom(blob):
        if cg is not None and g.base == cg:
            continue
        rec = None
        for P in range(0, MAX_SO_PARTS + 1):
            rec_len = 8 + 8 * P
            o = g.base - rec_len
            if o < 0:
                break
            if (u16(blob, o) == SO_MAGIC and u16(blob, o + 4) == rec_len
                    and u16(blob, o + 6) == 8 + 4 * P):
                rec = (o, rec_len, P, u16(blob, o + 6))
                break
        if rec is None:
            continue
        o, rec_len, P, arrayB = rec
        if o + rec_len != g.base:
            raise _fail("the self-describing law is broken at geom %#x (record %#x + %d != %#x)"
                        % (g.base, o, rec_len, g.base))
        for k in range(P):
            tp = u16(blob, o + 8 + 4 * k)
            if (tp & 0x0F) * 64 != column:
                continue
            faces = []
            for mesh in g.meshes:
                pool = g.base + mesh.p_uv
                for prim in EC.iter_primitives(blob, g, mesh):
                    uvs = prim.get("uv")
                    if not uvs or prim.get("part", -1) != k:
                        continue
                    vs, us = [], []
                    for i in uvs:
                        w = u16(blob, pool + 2 * i)
                        us.append(w & 0xFF)
                        vs.append((w >> 8) & 0xFF)
                    faces.append((min(vs), max(vs), min(us), max(us)))
            vs = [f[0] for f in faces] + [f[1] for f in faces]
            us = [f[2] for f in faces] + [f[3] for f in faces]
            out.append({
                "rec": o, "geom": g.base, "P": P, "slot": k, "tpage": tp,
                "clut": u16(blob, o + 10 + 4 * k), "column": column,
                "page_y": ((tp >> 4) & 1) * 256, "bpp": SO_BPP[(tp >> 7) & 3],
                "semi": (tp >> 5) & 3,
                "A": u16(blob, o + arrayB + 4 * k), "B": u16(blob, o + arrayB + 2 + 4 * k),
                "sec_off": o + arrayB + 4 * k,
                "faces": len(faces), "vmin": min(vs) if vs else None,
                "vmax": max(vs) if vs else None, "umin": min(us) if us else None,
                "umax": max(us) if us else None,
                "v_ge128_faces": sum(1 for f in faces if f[1] >= 128),
                "_faces": faces,
            })
    return sorted(out, key=lambda r: r["rec"])


def crossing_counts(reader: dict, rowset: set) -> int:
    """How many of a reader's faces touch at least one marked row, taking v modulo the 128-line cell.

    The modulo matters for exactly one reader -- the wrap record, whose v runs to 255 -- and it is
    the honest reading for it: whichever half that face lands in, its v-span reduced mod 128 is the
    set of cell lines it covers.  For the other 26 readers (v <= 127) it is the identity.
    """
    n = 0
    for (vlo, vhi, _ulo, _uhi) in reader["_faces"]:
        if any((v % CELL_ROWS) in rowset for v in range(vlo, vhi + 1)):
            n += 1
    return n


# ============================================================================ THE SOURCE PIN
def pin_source(blob: bytes, path: str) -> dict:
    """REFUSE a container that is not the effect these constants were measured on.

    Four independent pins, because a name is a convention and a derivation is a fact:

    * the source's FILE NAME must name this module's ``EFFECT``;
    * its sha256 must be the stock sha this cast was designed against (drift in the user's install
      -- a Steam or Moguri patch -- must stop the cast, not silently re-aim it);
    * both marked cells must resolve at the depth, channel and FILE OFFSET measured here, and their
      declared cover spans must be the ones the marks were sized against;
    * the whole column-640 reader census must reproduce: 27 binding slots, the A histogram
      {0x0080: 20, 0x0000: 7}, and the one wrap reader.  **This is the pin that matters.**  The
      cast's negative control IS that histogram; a container that does not reproduce it has no
      in-cast control, so running this instrument on it would produce a read nobody could score.
    """
    base = os.path.basename(path).lower()
    tag = "ef%03d" % EFFECT
    if tag not in base:
        raise _fail("--from names %r, which does not name this module's EFFECT (%s).  EFFECT, "
                    "MARKS, the cell names and GAME_OVERRIDE all pin ef%03d; --from re-points the "
                    "SOURCE and nothing else, so a probe built from another container would be "
                    "staged as `%s.cellprobe` and DEPLOYED over the ef%03d override.  To run a "
                    "FALLBACK VEHICLE, re-pin EFFECT, COLUMN, the cells, MARKS and every SOURCE_PIN "
                    "entry -- not just --from." % (base, tag, EFFECT, tag, EFFECT))
    sha = hashlib.sha256(blob).hexdigest()
    if sha != EXPECT_STOCK_SHA256:
        raise _fail("%s sha256 %s != this cast's pinned stock sha %s.  Every offset, span and "
                    "face-crossing count in the study was measured on those bytes."
                    % (path, sha[:16], EXPECT_STOCK_SHA256[:16]))
    notes = []
    for cell, (want_src, want_bpp, want_off) in sorted(SOURCE_PIN_CELLS.items()):
        try:
            page = RP.texel_page(blob, cell, EFFECT)
        except Exception as exc:                                    # noqa: BLE001
            raise _fail("%s does not resolve %s at all (%s: %s)."
                        % (path, cell, type(exc).__name__, str(exc).splitlines()[0][:160]))
        got = (page.depth_source, page.bpp, page.page_offset)
        if got != (want_src, want_bpp, want_off):
            raise _fail("%s resolves %s as %s/%dbpp @%#x, but this cast was measured on "
                        "%s/%dbpp @%#x." % (path, cell, got[0], got[1], got[2],
                                            want_src, want_bpp, want_off))
        cov = cover_span(blob, page.cell)
        if cov != SOURCE_PIN_COVER[cell]:
            raise _fail("%s's declared `so` cover on %s is %r, but the marks were sized against "
                        "%r.  The stripe rows move with the cover, so every face-crossing number "
                        "in the study would be stale." % (path, cell, cov, SOURCE_PIN_COVER[cell]))
        notes.append("%s %s/%dbpp @%#x cover %r" % (cell, want_src, want_bpp, want_off, cov))
    readers = column_readers(blob)
    hist = dict(Counter(r["A"] for r in readers))
    if len(readers) != SOURCE_PIN_COLUMN["slots"] or hist != SOURCE_PIN_COLUMN["A"]:
        raise _fail("%s binds column %d with %d slot(s), A histogram %r -- this cast was measured "
                    "on %d slots, %r.  THE NEGATIVE CONTROL *IS* THAT HISTOGRAM: without the "
                    "A=0x0000 family riding in the same cast there is nothing to prove the upload "
                    "landed, and a null would be unscoreable."
                    % (path, COLUMN, len(readers), hist, SOURCE_PIN_COLUMN["slots"],
                       SOURCE_PIN_COLUMN["A"]))
    bad = [r for r in readers if r["bpp"] != 8]
    if bad:
        raise _fail("%d column-%d reader(s) are not 8bpp (%s).  The mark is a whole BYTE ROW, which "
                    "is a texel row at every depth, but the per-CLUT read printed by this probe "
                    "assumes a byte IS an index." % (len(bad), COLUMN,
                                                     ", ".join("%#x@%dbpp" % (r["rec"], r["bpp"])
                                                               for r in bad)))
    wraps = tuple(sorted(r["rec"] for r in readers if r["vmax"] is not None and r["vmax"] >= 128))
    if wraps != tuple(sorted(SOURCE_PIN_COLUMN["wrap_recs"])):
        raise _fail("%s's column-%d wrap readers are %s, not %s.  Record 0x79168 is THE IN-CAST "
                    "POSITIVE CONTROL for the lower mark (C3); without it a null on the lower cell "
                    "cannot be told from a failed upload."
                    % (path, COLUMN, [hex(w) for w in wraps],
                       [hex(w) for w in SOURCE_PIN_COLUMN["wrap_recs"]]))
    return {"ok": True, "sha256": sha, "name": base, "cells": notes,
            "column_slots": len(readers), "A_histogram": {hex(k): v for k, v in sorted(hist.items())},
            "wrap_recs": [hex(w) for w in wraps],
            "text": "source pin OK: %s names ef%03d, sha %s, %s; column %d = %d slots, A %s, wrap %s"
                    % (base, EFFECT, sha[:16], "; ".join(notes), COLUMN, len(readers),
                       {hex(k): v for k, v in sorted(hist.items())}, [hex(w) for w in wraps])}


# ============================================================================ THE MARK
def stripe_tops(k: int, rows: int, lo: int, hi: int):
    """The TOP row of each of ``k`` evenly-spaced ``rows``-row stripes inside ``lo..hi``.

    A one-line wrapper over `odin_band_stamp.evenly_spaced_tops` and NOT a reimplementation of it:
    both instruments must place their marks by one rule, and a count-only read cannot survive a
    +-1-row divergence between the rule that writes and the rule that predicts.
    """
    return evenly_spaced_tops(k, rows, lo, hi)


def marked_rows(k: int, rows: int, lo: int, hi: int) -> list:
    out = set()
    for t in stripe_tops(k, rows, lo, hi):
        for r in range(t, min(CELL_ROWS, t + rows)):
            out.add(r)
    return sorted(out)


def authored_offsets(cell_off: int, rowset) -> range:
    """(generator) every FILE offset this mark writes -- whole 128-byte rows inside one 0x4000 cell."""
    for r in rowset:
        base = cell_off + r * ROW_BYTES
        for o in range(base, base + ROW_BYTES):
            yield o


def byte_proof(stock: bytes, probe: bytes, authored: set) -> dict:
    """THE PROOF: the changed-vs-stock byte set is EXACTLY the authored stripe set, by code.

    Four claims, each checked and each able to fail loudly:

    1. the container's LENGTH is unchanged (an `so` container is offset-addressed; a length change
       is a different file, not a marked one);
    2. every authored offset holds `0x00` in the probe -- the mark is a zero-write, wholly;
    3. NO offset outside the authored set differs -- nothing else moved;
    4. the CHANGED set is exactly the authored offsets whose stock byte was non-zero.  It is a
       SUBSET of the authored set by arithmetic (zeroing a zero changes nothing), so the honest
       statement is `changed == {o in authored : stock[o] != 0}` and both directions are asserted:
       0 extra, 0 missing, 0 wrong-value.
    """
    if len(probe) != len(stock):
        raise _fail("the probe changed the container's LENGTH (%d -> %d)" % (len(stock), len(probe)))
    nonzero_ink = [o for o in authored if probe[o] != 0]
    if nonzero_ink:
        raise _fail("%d authored offset(s) are not 0x00 in the probe (first %#x = %#04x)"
                    % (len(nonzero_ink), nonzero_ink[0], probe[nonzero_ink[0]]))
    changed = {o for o in range(len(stock)) if stock[o] != probe[o]}
    extra = sorted(changed - authored)
    if extra:
        raise _fail("%d byte(s) changed OUTSIDE the authored stripe set (first %#x: %#04x -> %#04x)"
                    % (len(extra), extra[0], stock[extra[0]], probe[extra[0]]))
    want_changed = {o for o in authored if stock[o] != 0}
    missing = sorted(want_changed - changed)
    if missing:
        raise _fail("%d authored non-zero byte(s) did NOT change (first %#x)"
                    % (len(missing), missing[0]))
    spurious = sorted(changed - want_changed)
    if spurious:                                                    # unreachable by arithmetic
        raise _fail("%d changed byte(s) were already 0x00 in stock -- impossible; the walk is wrong"
                    % len(spurious))
    return {"authored_bytes": len(authored), "changed_bytes": len(changed),
            "already_zero_in_stock": len(authored) - len(changed),
            "outside_authored": 0, "missing": 0, "wrong_value": 0,
            "length_stock": len(stock), "length_probe": len(probe),
            "claim": "changed-vs-stock == {o in authored : stock[o] != 0}  (0 extra / 0 missing / "
                     "0 wrong-value), and every authored offset is 0x00 in the probe"}


# ============================================================================ PALETTE READ
def palette_read(blob: bytes) -> list:
    """How a zeroed texel LOOKS to each CLUT on this column -- derived, because the read differs.

    The A=0x0080 family draws through a palette whose entry 0 is OPAQUE and the darkest entry it
    has; the A=0x0000 control family draws through one whose entry 0 is the hardware CUTOUT.  Same
    grating, two appearances.  A runbook that says only "count dark bands" scores the control family
    as blank, which is the failure this function exists to prevent.
    """
    hdr = EC.parse_header(blob, strict=True)
    pals = {}
    for ch in hdr.chunks:
        for p in RS.id0_palettes(blob, ch, RS.chunk_tag(ch))[1]:
            pals[p.vram] = p
    out = []
    for cw in sorted({r["clut"] for r in column_readers(blob)}):
        xy = RS.clut_word_xy(cw)
        p = pals.get(xy)
        if p is None:
            out.append({"clut": cw, "error": "no id-0 palette at vram %r" % (xy,)})
            continue
        w = struct.unpack_from("<%dH" % 256, blob, p.off)
        r, g, b, a = TX.bgr555_rgba(w[0])
        lums = [0 if not q else (TX.bgr555_rgba(q)[0] * 299 + TX.bgr555_rgba(q)[1] * 587
                                 + TX.bgr555_rgba(q)[2] * 114) // 1000 for q in w]
        out.append({"clut": cw, "vram": list(xy), "offset": p.off, "entry0": w[0],
                    "rgba": [r, g, b, a], "transparent": a == 0,
                    "zeros": sum(1 for q in w if q == 0),
                    "stp_blacks": sum(1 for q in w if q == 0x8000),
                    "entry0_luma": lums[0], "min_opaque_luma": min(l for l, q in zip(lums, w) if q),
                    "reads_as": ("TRANSPARENT HOLES in the surface" if a == 0
                                 else "OPAQUE DARK BANDS (entry 0 luma %d)" % lums[0])})
    return out


def cell_contrast(blob: bytes, cell_off: int, clut_words) -> dict:
    d = blob[cell_off:cell_off + CELL_BYTES]
    lums, opq = [], 0
    for byte in d:
        q = clut_words[byte]
        if q:
            opq += 1
            rr, gg, bb, _a = TX.bgr555_rgba(q)
            lums.append((rr * 299 + gg * 587 + bb * 114) // 1000)
        else:
            lums.append(0)
    return {"mean_luma": sum(lums) / len(lums), "opaque_pct": 100.0 * opq / len(d),
            "min": min(lums), "max": max(lums)}


# ============================================================================ GENERATE
def generate(from_path: str, root: str, cells=None) -> dict:
    stock = Path(from_path).read_bytes()
    # THE SOURCE PIN RUNS INSIDE generate(), not in main(): no caller -- and no import of this
    # module -- can reach the striping, or the deploy that consumes its output, with a container
    # these constants were not measured on.  A guard at the CLI edge is a guard one call site wide.
    pin = pin_source(stock, from_path)

    census = RS.page_cells(stock)
    by_name = {pc.name: pc for pc in census.values()}
    want = list(cells) if cells else list(MARKS)
    unknown = [c for c in want if c not in by_name]
    if unknown:
        raise _fail("no such cell(s) %r; this container declares:\n%s"
                    % (unknown, "\n".join("  " + n for n in sorted(by_name))))
    unmarked = [c for c in want if c not in MARKS]
    if unmarked:
        raise _fail("%r has no entry in MARKS.  This instrument writes exactly the two halves of "
                    "column %d; marking a third cell would add a mark the read has no meaning for."
                    % (unmarked, COLUMN))

    readers = column_readers(stock)
    blob = bytearray(stock)
    authored, legend = set(), []
    for cell in sorted(MARKS):
        pc = by_name[cell]
        k, rows = MARKS[cell]
        cov = cover_span(stock, (pc.x, pc.y))
        lo, hi = cov if cov else (0, CELL_ROWS - 1)
        rowset = marked_rows(k, rows, lo, hi)
        written = cell in want
        offs = set(authored_offsets(pc.off, rowset)) if written else set()
        if written:
            if pc.nbytes != CELL_BYTES:
                raise _fail("%s is %#x bytes, not the %#x this instrument's row arithmetic assumes"
                            % (cell, pc.nbytes, CELL_BYTES))
            for r in rowset:
                b = pc.off + r * ROW_BYTES
                blob[b:b + ROW_BYTES] = b"\x00" * ROW_BYTES
            authored |= offs
        legend.append({
            "cell": cell, "written": written, "k": k, "stripe_rows": rows,
            "offset": pc.off, "xy": [pc.x, pc.y], "nbytes": pc.nbytes,
            "cover_span": list(cov) if cov else None,
            "placement": "so-cover" if cov else "whole-cell", "span": [lo, hi],
            "tops": stripe_tops(k, rows, lo, hi), "rows": rowset,
            "duty_rows": len(rowset), "duty_pct": 100.0 * len(rowset) / CELL_ROWS,
            "bytes": len(offs), "meaning": MEANING[cell],
            "byte_ranges": [[pc.off + t * ROW_BYTES,
                             pc.off + min(CELL_ROWS, t + rows) * ROW_BYTES]
                            for t in stripe_tops(k, rows, lo, hi)],
            "rowset": set(rowset),
        })

    probe = bytes(blob)
    EC.parse_header(probe, strict=True)                          # the probe must still parse
    proof = byte_proof(stock, probe, authored)

    # per-reader crossing counts, for BOTH marks -- the "nothing is starved" claim, measured
    for rec in readers:
        for L in legend:
            rec.setdefault("crossed", {})[L["cell"]] = crossing_counts(rec, L["rowset"])
    for L in legend:
        L.pop("rowset")

    pal = palette_read(stock)
    hdr = EC.parse_header(stock, strict=True)
    pals = {}
    for ch in hdr.chunks:
        for p in RS.id0_palettes(stock, ch, RS.chunk_tag(ch))[1]:
            pals[p.vram] = p
    contrast = {}
    for L in legend:
        for entry in pal:
            if "error" in entry:
                continue
            words = struct.unpack_from("<256H", stock, pals[tuple(entry["vram"])].off)
            contrast.setdefault(L["cell"], {})["%#06x" % entry["clut"]] = cell_contrast(
                stock, L["offset"], words)

    root_p = Path(root)
    root_p.mkdir(parents=True, exist_ok=True)
    out = root_p / ("ef%03d.cellprobe" % EFFECT)
    out.write_bytes(probe)
    d = {"effect": EFFECT, "column": COLUMN, "source": from_path, "root": str(root_p),
         "container": str(out), "sha256": hashlib.sha256(probe).hexdigest(),
         "stock_sha256": pin["sha256"], "bytes": len(probe),
         "marks": {c: list(MARKS[c]) for c in sorted(MARKS)}, "legend": legend,
         "byte_proof": proof, "source_pin": pin,
         "readers": [{k: v for k, v in r.items() if k != "_faces"} for r in readers],
         "palette_read": pal, "cell_contrast": contrast,
         "cast_b_bands": dict(CAST_B_BANDS), "cast_b_band_rows": CAST_B_BAND_ROWS,
         "notes": contamination_notes()}
    (root_p / "probe.derivation.json").write_text(
        json.dumps(d, indent=1, default=str), encoding="utf-8")
    d["_readers_full"] = readers
    return d


def contamination_notes() -> list:
    """Every way this cast's signature could be MISTAKEN for an earlier one, checked not asserted."""
    L = []
    ks = {c: MARKS[c][0] for c in MARKS}
    if len(set(ks.values())) != len(ks):
        L.append("*** LOUD: the two marks share a COUNT (%r) -- the read has no discriminator." % ks)
    if len({MARKS[c][1] for c in MARKS}) != len(MARKS):
        L.append("*** LOUD: the two marks share a THICKNESS -- one of the two read axes is gone.")
    for c, (k, rows) in sorted(MARKS.items()):
        for bc, bk in sorted(CAST_B_BANDS.items()):
            if k == bk and rows == CAST_B_BAND_ROWS:
                L.append("*** LOUD: %s's mark (%d x %d rows) is IDENTICAL to the ef424 cast's on %s."
                         % (c, k, rows, bc))
            elif k == bk:
                L.append("note: %s's COUNT (%d) equals the ef424 cast's on %s, but the thickness "
                         "differs (%d vs %d rows) and the container differs (ef%03d vs ef424) -- no "
                         "screen shows both." % (c, k, bc, rows, CAST_B_BAND_ROWS, EFFECT))
    duties = {c: MARKS[c][0] * MARKS[c][1] for c in MARKS}
    if len(set(duties.values())) != len(duties):
        L.append("*** LOUD, DISCLOSED: the two marks have EQUAL aggregate duty (%r rows).  COUNT "
                 "and THICKNESS still differ, which are the two axes the read uses -- but never "
                 "infer the mark from how much of the surface changed." % duties)
    else:
        L.append("duty differs by design but NEARLY: %s.  The read is still structural -- 'many "
                 "thin' vs 'few fat' -- and must never be scored as 'it got darker'."
                 % ", ".join("%s %d/%d rows (%.1f%%)" % (c.split(".")[-1], v, CELL_ROWS,
                                                         100.0 * v / CELL_ROWS)
                             for c, v in sorted(duties.items())))
    if not any(x.startswith("***") for x in L):
        L.insert(0, "no collision: the two marks differ in COUNT (%d vs %d) and THICKNESS (%d vs %d "
                    "rows), and the ef424 cast's marks (%r at %d rows) are on a different container."
                    % (MARKS[UPPER_CELL][0], MARKS[LOWER_CELL][0], MARKS[UPPER_CELL][1],
                       MARKS[LOWER_CELL][1], dict(CAST_B_BANDS), CAST_B_BAND_ROWS))
    return L


# ============================================================================ THE PROTOCOL
def protocol(d: dict) -> list:
    up = next(L for L in d["legend"] if L["cell"] == UPPER_CELL)
    lo = next(L for L in d["legend"] if L["cell"] == LOWER_CELL)
    readers = d["_readers_full"]
    fam80 = [r for r in readers if r["A"] == 0x0080]
    fam00 = [r for r in readers if r["A"] == 0x0000]
    wrap = [r for r in readers if r["vmax"] >= 128]
    L = [
        "THE U1 SECOND-ARRAY CAST -- ef%03d, both halves of column %d" % (d["effect"], d["column"]),
        "  QUESTION         U1: does the engine APPLY second-array halfword A at all?",
        "  source           %s" % d["source"],
        "  stock sha256     %s" % d["stock_sha256"],
        "  %s" % d["source_pin"]["text"],
        "",
        "  THE TWO MARKS -- placement imported from odin_band_stamp.evenly_spaced_tops, spans from",
        "  odin_band_stamp.cover_span; neither is restated here.",
        "",
        "  cell                      mark        duty        placement  span     tops",
    ]
    for r in (up, lo):
        L.append("  %-25s %-11s %2d/%-3d %4.1f%% %-10s %3d..%-3d %s"
                 % (r["cell"], "%d x %d rows" % (r["k"], r["stripe_rows"]),
                    r["duty_rows"], CELL_ROWS, r["duty_pct"], r["placement"],
                    r["span"][0], r["span"][1], r["tops"]))
        L.append("      -> a surface showing THIS mark says: %s" % r["meaning"])
        L.append("      rows %s" % r["rows"])
        L.append("      cell %#x..%#x; %d byte(s) written in %d range(s): %s"
                 % (r["offset"], r["offset"] + r["nbytes"], r["bytes"], len(r["byte_ranges"]),
                    ", ".join("%#x-%#x" % (a, b) for a, b in r["byte_ranges"])))
        if not r["written"]:
            L.append("      *** NOT WRITTEN THIS RUN (--cells narrowed the mark set)")
    p = d["byte_proof"]
    L += ["",
          "  probe container  %d B  sha256 %s" % (d["bytes"], d["sha256"]),
          "  BYTE PROOF       authored %d B; changed vs stock %d B; %d authored byte(s) were "
          "ALREADY 0x00" % (p["authored_bytes"], p["changed_bytes"], p["already_zero_in_stock"]),
          "                   %d outside the authored set, %d missing, %d wrong-value"
          % (p["outside_authored"], p["missing"], p["wrong_value"]),
          "                   %s" % p["claim"],
          "                   %.3f%% of the container; everything else is untouched and is its own "
          "control" % (100.0 * p["changed_bytes"] / d["bytes"]),
          "  staged           %s" % d["container"],
          ""]

    L += ["  ---- HOW A ZEROED TEXEL LOOKS, PER CLUT (derived; the read DIFFERS by family) ----"]
    for e in d["palette_read"]:
        if "error" in e:
            L.append("  clut %#06x  *** %s" % (e["clut"], e["error"]))
            continue
        L.append("  clut %#06x  entry0 %#06x rgba%r  %s"
                 % (e["clut"], e["entry0"], tuple(e["rgba"]), e["reads_as"]))
        L.append("              %d/256 entries are 0x0000, %d are 0x8000; entry-0 luma %d, dimmest "
                 "opaque entry %d" % (e["zeros"], e["stp_blacks"], e["entry0_luma"],
                                      e["min_opaque_luma"]))
    for cell in (UPPER_CELL, LOWER_CELL):
        for cw, c in sorted(d["cell_contrast"].get(cell, {}).items()):
            L.append("  stock %-25s under %s: mean luma %5.1f, %5.1f%% opaque (min %d max %d)"
                     % (cell, cw, c["mean_luma"], c["opaque_pct"], c["min"], c["max"]))

    L += ["",
          "  ---- EVERY READER OF COLUMN %d (%d slots, all P=1 slot 0, all 8bpp, page_y 256) ----"
          % (d["column"], len(readers)),
          "  rec       clut    A      B      faces  v        u        v>=128  cross(UP) cross(LO)"]
    for r in readers:
        L.append("  %#08x %#06x %#06x %#06x %5d  %3d..%-3d %3d..%-3d %6d  %4d/%-4d %4d/%-4d"
                 % (r["rec"], r["clut"], r["A"], r["B"], r["faces"], r["vmin"], r["vmax"],
                    r["umin"], r["umax"], r["v_ge128_faces"],
                    r["crossed"][UPPER_CELL], r["faces"], r["crossed"][LOWER_CELL], r["faces"]))
    L += ["",
          "  FAMILY A=0x0080 (%d slots, clut %s) -- THE ANSWER-CARRYING CLASS."
          % (len(fam80), ", ".join(sorted({"%#06x" % r["clut"] for r in fam80}))),
          "  FAMILY A=0x0000 (%d slots, clut %s) -- THE IN-CAST NEGATIVE CONTROL.  0 + anything is"
          % (len(fam00), ", ".join(sorted({"%#06x" % r["clut"] for r in fam00}))),
          "                  the identity, so these read the UPPER cell under EVERY live reading of",
          "                  A.  They MUST show the %d-count mark.  If they do, the override "
          "loaded," % up["k"],
          "                  the upload landed, and column-%d surfaces DRAW -- the "
          "BINDING-IS-NOT-A-DRAW" % d["column"],
          "                  gate passed IN-CAST.  If they show the %d-count mark instead, the "
          "prediction" % lo["k"],
          "                  table is wrong somewhere: DISCARD the cast, do not interpret it.",
          "  WRAP READER%s     %s -- v runs past 127, so under the no-offset reading it samples BOTH"
          % ("" if len(wrap) == 1 else "S", ", ".join("%#x" % r["rec"] for r in wrap)),
          "                  halves at once: the LOWER mark rendered on screen with the question "
          "still open.",
          "",
          "  ---- HOW TO SCORE THE VIDEO ----",
          "  #### DO NOT SCORE THIS BY COUNTING BANDS ON SCREEN. ####  The marks are %d and %d"
          % (up["k"], lo["k"]),
          "  stripes ACROSS THE TEXTURE CELL, and no surface in this cast maps that cell to one",
          "  continuous chart: on the headline disc the median face spans only ~23 of the 128 texel",
          "  rows, so a face shows ~2 thin lines or ~1 fat line -- never 12 or 4.  MEASURED per",
          "  face on the disc: under the upper mark 125/140 faces cross >=2 stripes (median 2);",
          "  under the lower mark 122/140 cross exactly ONE (median 1).  The read is PITCH and",
          "  THICKNESS, not a count:",
          "",
          "        FINE / DENSE banding, thin lines   -> A is NOT applied (R_FLAGS / never read)",
          "        COARSE banding, lines ~2x thicker  -> A IS APPLIED",
          "",
          "  The two marks differ 1:2 in stripe thickness and ~3:1 in stripes per unit of texture,",
          "  at near-equal duty (%.1f%% vs %.1f%%) -- so it is never 'it got darker'.  SCORE AGAINST"
          % (100.0 * len(up["rows"]) / CELL_ROWS, 100.0 * len(lo["rows"]) / CELL_ROWS),
          "  THE OFFLINE PANELS in ..\\predict\\, which render every surface from its own GEOM UV",
          "  stream under both hypotheses.  NOTE they are ORTHOGRAPHIC model-space views (the disc",
          "  top-down); the battle camera foreshortens all of them, so expect the on-screen pitch",
          "  to be COMPRESSED relative to the panel.",
          "",
          "  1. THE BIG FLAT SNOWFLAKE DISC (record 0x29dbc, %d faces, the ONLY wide-flat surface in"
          % next(r["faces"] for r in readers if r["rec"] == 0x29dbc),
          "     the container -- everything else is a tall shard, an icicle or a small orb).  Singly",
          "     attributable, and an A=0x0080 surface.  Fine -> not applied; coarse -> applied.",
          "     This one surface decides U1 and needs no other.",
          "  2. CROSS-CHECK ON A TWINNED SHARD.  SIX pairs are the same mesh drawn twice with",
          "     OPPOSITE A -- byte-identical positions AND byte-identical UV pools, differing only",
          "     in the per-face flag byte: 0x3114c/0x7b150, 0x31a48/0x7c838, 0x32344/0x7df20,",
          "     0x32c40/0x7f778, 0x3353c/0x80bc4, 0x33e38/0x85de0.  (0x79168/0x79ae8 is bbox-twinned",
          "     but its UV POOLS DIFFER in 94 of 102 entries -- NOT a coincident-grating pair; do",
          "     not use it here.)  Same read: fine -> not applied, coarse -> applied.  In principle",
          "     the applied case superimposes the faint A=0x0000 fine grating on the coarse one, but",
          "     that cut-out additive layer is dim: do NOT require seeing two gratings -- the pitch",
          "     of the BRIGHT layer is the read.",
          "     ! Caveat: those six pairs straddle container resources id-2 and id-6.  Whether both",
          "     ! resources are drawn in the SAME cast is UNVERIFIED offline.  If only one is, this",
          "     ! question has no instance -- fall back to question 1, which needs only id-2.",
          "  3. THE WRAP READER'S BASE END (near end of the orb-and-tail).  Coarse -> applied; fine",
          "     -> not applied.  CORROBORATION ONLY -- the smallest surface in the cast.",
          "",
          "  ---- RECORD TWO THINGS SEPARATELY, PER SURFACE CLASS ----",
          "  (a) is the surface VISIBLE at all?    (b) does it BAND?",
          "  Different observations; conflating them is how a cast gets mis-read.",
          "    visible AND banded      -> score it (fine vs coarse)",
          "    NOT VISIBLE anywhere    -> BOUND-NEVER-DRAWN for that class.  A RESULT, not a",
          "                               failure: report it, retry ONCE after a relaunch, then fall",
          "                               to the next vehicle (the study's fallback ladder).  With",
          "                               %d readers a genuine total null is itself a substantial"
          % len(readers),
          "                               finding.",
          "    VISIBLE but UNBANDED    -> *** NEITHER MARKED CELL WAS SAMPLED. ***  NOT",
          "                               bound-never-drawn and NOT a null -- a THIRD outcome (the",
          "                               texels came from somewhere else: a displaced upload, a",
          "                               different page, a cached decode).  Record it as its own",
          "                               finding; do not file it under either hypothesis.",
          "",
          "  A FINE (upper-mark) RESULT CLOSES U1 IN THE NEGATIVE DIRECTION ONLY.  Per the report's "
          "own caveat it is",
          "  consistent with BOTH 'A is a render-state flag' and 'A is declared and ignored'; only "
          "the",
          "  second leg (flip A on one record, look for a BLEND-STATE change) or a disassembly "
          "separates",
          "  those.  A COARSE (lower-mark) result closes U1 positively -- but A is perfectly "
          "confounded with CLUT and",
          "  with blend mode in this container, so report it as 'something in the second array "
          "moves the",
          "  sampled cell', NOT as 'H_V confirmed'.",
          ""]
    L += ["  " + n for n in d["notes"]]
    return L


# ============================================================================ MAIN
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="from_path", default=DEFAULT_CORPUS,
                    help="the STOCK container to mark (default the corpus ef%03d)" % EFFECT)
    ap.add_argument("--root", default=DEFAULT_ROOT, help="staging root (LOCAL-ONLY)")
    ap.add_argument("--cells", default=",".join(sorted(MARKS)), metavar="CELL[,CELL...]",
                    help="which of the two column-%d half-cells to mark, each at its OWN pinned "
                         "(count, thickness).  Default: both -- which is the cast.  Narrow it only "
                         "for a surgical follow-up; a cell left out stays stock and is its own "
                         "control, and the DISCRIMINATOR is gone (both halves must be marked "
                         "differently for a surface to name the half it sampled)" % COLUMN)
    ap.add_argument("--deploy", action="store_true",
                    help="snapshot the live override and write the probe container over it")
    ap.add_argument("--mod-folder", default=MOD_ROOT,
                    help="the mod folder --deploy writes into.  Defaults to the live FF9CustomMap; "
                         "point it at a temp dir to REHEARSE the whole ledger + revert path without "
                         "touching the install.  The rehearsal prints REHEARSAL, so a real run can "
                         "never be mistaken for one")
    ap.add_argument("--skip-install-check", action="store_true",
                    help="skip the deploy-time check that the user's own resources.assets still "
                         "holds the SAME stock ef%03d these marks were measured on.  Only for a "
                         "machine without UnityPy; it removes the one guard that catches a "
                         "Steam/Moguri drift between the corpus copy and what the engine loads"
                         % EFFECT)
    a = ap.parse_args(argv)

    cells = [s.strip() for s in a.cells.split(",") if s.strip()]
    d = generate(a.from_path, a.root, cells)
    lines = protocol(d)
    print("\n".join(lines))
    Path(a.root, "PROTOCOL.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n  protocol         %s" % Path(a.root, "PROTOCOL.txt"))
    print("  derivation       %s" % Path(a.root, "probe.derivation.json"))

    if not a.deploy:
        print("\n  NOTHING WAS DEPLOYED.  The install is untouched.  Re-run with --deploy; bench row "
              "200 'Stock Shiva'")
        print("  (vfx %d/%d) is ALREADY LIVE in Actions.csv, so this container needs NO relaunch."
              % (EFFECT, EFFECT))
        return 0

    # ---- the live write, with the folder's state MEASURED rather than assumed --------------------
    mod = Path(a.mod_folder)
    live = mod / "FF9_Data" / "SpecialEffects" / ("ef%03d" % EFFECT)
    rehearsal = str(mod.resolve()).lower() != str(Path(MOD_ROOT).resolve()).lower()
    if not rehearsal and str(live) != GAME_OVERRIDE:
        # GAME_OVERRIDE is a PIN, not documentation: if the derived destination ever stops agreeing
        # with the constant this file names, the constant is a comment and the write is elsewhere.
        raise SystemExit("FAIL: the derived destination %s does not match this script's own "
                         "GAME_OVERRIDE pin %s -- refusing to write to a path the file does not "
                         "name." % (live, GAME_OVERRIDE))
    if rehearsal:
        print("\n  *** REHEARSAL -- --mod-folder is %s, NOT the live install.  Nothing the game "
              "reads will change." % mod)
        mod.mkdir(parents=True, exist_ok=True)
    if not mod.is_dir():
        raise SystemExit("FAIL: mod folder not found: %s" % mod)
    if (mod / "ModFileList.txt").exists():
        raise SystemExit(
            "REFUSING: %s has a ModFileList.txt.  THE SILENT-FALLBACK LAW -- "
            "TryFindAssetInModOnDisc TRUSTS that list and never calls File.Exists, so an unlisted "
            "override is INVISIBLE and this cast would read as a clean negative for a reason that "
            "has nothing to do with drawing.  Handle the list by hand, then re-run." % mod)

    # ---- the install-drift gate.  The corpus copy is a COPY; what the engine loads when no
    # override exists is resources.assets.  If those two ever diverge, every offset in this cast
    # was measured against bytes the engine does not have.
    if a.skip_install_check:
        print("\n  *** LOUD: --skip-install-check.  The stock bytes this probe was built from were "
              "NOT re-read")
        print("      from the install; a Steam/Moguri drift would be invisible.")
    else:
        from ff9mapkit.summons import rescore as RC
        blob, src = RC.read_stock_effect(EFFECT)
        sha = hashlib.sha256(blob).hexdigest()
        print("\n  install stock    %s" % src)
        print("  install sha256   %s  (%s the source)"
              % (sha[:32], "MATCHES" if sha == d["stock_sha256"] else "*** DIFFERS FROM ***"))
        if sha != d["stock_sha256"]:
            raise SystemExit("FAIL: the install's stock ef%03d is not the container this probe was "
                             "built from.  Every offset in this cast was measured on %s."
                             % (EFFECT, d["stock_sha256"][:16]))

    root = Path(a.root)
    pre = root / ("ef%03d" % EFFECT)
    absent_flag = root / "pre.ABSENT"
    print("\n  live override    %s" % live)
    # ⚠ THE STALE-SNAPSHOT DEFECT, found by rehearsing this path and fixed here.  The emitted revert
    # decides by `pre.exists()`.  A root that has ALREADY been deployed into once keeps whichever
    # marker that run left behind, so a PRESENT run followed by an ABSENT run would leave the old
    # `pre` snapshot lying beside the new `pre.ABSENT` -- and the revert would RESTORE somebody
    # else's container instead of deleting ours.  The two markers are mutually exclusive by
    # construction: whichever branch runs CLEARS the other one first, and says so.
    stale = [p for p in (pre, absent_flag) if p.exists()]
    if stale:
        print("  prior ledger     %s -- from an earlier deploy into this root; it is CLEARED below "
              "so the" % ", ".join(p.name for p in stale))
        print("                   emitted revert can never restore a stale snapshot.")
    if live.exists():
        absent_flag.unlink(missing_ok=True)
        pre.write_bytes(live.read_bytes())
        pre_sha = hashlib.sha256(pre.read_bytes()).hexdigest()
        print("  OBSERVED         PRESENT, %d B sha %s -- NOT the expected state.  Recon read this "
              "folder as ABSENT;" % (pre.stat().st_size, pre_sha[:16]))
        print("                   another session deployed an ef%03d override since.  The snapshot "
              "restores it byte for byte," % EFFECT)
        print("                   but say so in the ledger note before casting -- somebody else's "
              "cast is underneath this one.")
        state = {"existed": True, "sha256": pre_sha, "backup": str(pre)}
    else:
        pre.unlink(missing_ok=True)
        absent_flag.write_text(
            "no override existed before the probe; revert = delete\n", encoding="utf-8")
        print("  OBSERVED         ABSENT (as expected) -- revert DELETES; the resting state is "
              "stock.")
        state = {"existed": False, "sha256": None, "backup": None}

    probe = Path(d["container"]).read_bytes()
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_bytes(probe)
    rb = hashlib.sha256(live.read_bytes()).hexdigest()
    print("  DEPLOYED         %s  (readback sha %s: %s)"
          % (live, rb[:16], "OK" if rb == d["sha256"] else "*** MISMATCH ***"))
    if rb != d["sha256"]:
        raise SystemExit("FAIL: the readback does not match what we wrote -- do not cast.")

    rv = root / "revert_probe.py"
    # NO PATH IS EVER INTERPOLATED INTO THE DOCSTRING.  A Windows path inside a triple-quoted string
    # turns `...\Users\...` into an invalid `\U` escape and the emitted script does not even PARSE --
    # which the first rehearsal of the Odin deploy path caught, and which would have failed at the
    # one moment the revert matters (immediately before a kit deploy, THE LEDGER TRAP).  Paths go
    # through %r into CODE lines only, where the repr escapes the backslashes.
    rv.write_text(
        '"""Auto-generated REVERT for the ef%03d U1 SECOND-ARRAY probe -- stdlib only.\n\n'
        "Restores whatever the mod folder held before this probe first ran, byte for byte, or\n"
        "DELETES the override if there was none (the paths are the two literals below).  Idempotent:\n"
        "run it twice and the second run is a no-op that still exits 0.\n\n"
        "RUN THIS BEFORE any `summon-reskin deploy` touches this root: the kit's own first-deploy\n"
        "snapshot is taken once per root and never overwritten, so a kit deploy on top of a live\n"
        "probe records THE PROBE as the pre-state and its revert would then restore the probe\n"
        "forever, as the resting state of a mod folder nobody is looking at any more.\n"
        '"""\n'
        "import pathlib\n"
        "live = pathlib.Path(%r)\n"
        "pre = pathlib.Path(%r)\n"
        "if pre.exists():\n"
        "    live.parent.mkdir(parents=True, exist_ok=True)\n"
        "    live.write_bytes(pre.read_bytes()); print('restored', live)\n"
        "elif live.exists():\n"
        "    live.unlink(); print('deleted', live)\n"
        "else:\n"
        "    print('already reverted (absent):', live)\n"
        % (EFFECT, str(live), str(pre)), encoding="utf-8")
    # AND IT IS COMPILED HERE, not hoped over: a revert script that does not parse is worse than none.
    compile(rv.read_text(encoding="utf-8"), str(rv), "exec")
    (root / "deploy.ledger.json").write_text(
        json.dumps({"effect": EFFECT, "live": str(live), "mod_folder": str(mod),
                    "rehearsal": rehearsal, "pre": state,
                    "probe_sha256": d["sha256"], "readback_sha256": rb,
                    "stock_sha256": d["stock_sha256"], "revert": str(rv)}, indent=1),
        encoding="utf-8")
    print("  ledger           %s" % (root / "deploy.ledger.json"))
    print("  revert with      py %s" % rv)
    print("\n  *** REVERT THE PROBE BEFORE ANY KIT DEPLOY ON THIS ROOT.  SFX.Play re-reads the "
          "container on")
    print("      every cast, so the probe is live on the NEXT cast with no relaunch -- and so is "
          "its removal.")
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
