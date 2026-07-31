r"""TIER W rung W6b-3iii -- THE U1 SECOND-ARRAY CAST.  ef038 (Stock Shiva), the PAGE of tpage 0x9a.

    py u1_cell_probe.py                    # CAST 2 (default): stage only; the install is untouched
    py u1_cell_probe.py --deploy           # snapshot the live override and write the probe over it
    py u1_cell_probe.py --cast 1 --root <dir>
                                           # regenerate CAST 1's container byte-for-byte (sha
                                           # 1f20d798...).  Kept live, not deleted: an instrument
                                           # that can no longer reproduce the cast it was read on
                                           # cannot be audited against it.
    py u1_cell_probe.py --deploy --mod-folder <temp>\FF9CustomMap --root <temp>\probe-root
                                           # REHEARSE the whole ledger against a folder the game
                                           # never reads.  Do this first -- it is how the Odin
                                           # probe's `\U`-in-a-docstring revert defect was found, at
                                           # zero cost, instead of at the cast.

THE QUESTION -- U1: DOES THE ENGINE APPLY THE SECOND ARRAY AT ALL?  NOW ASKED ON BOTH AXES AT ONCE.
---------------------------------------------------------------------------------------------------
CAST 1 ran and read `VISIBLE_UNBANDED` at 0.88 -- the study's own THIRD outcome.  The column DREW
(61-69 % of the whole column-640 prim pool per frame) and NOTHING banded, on either family.  The s76
control cast then adjudicated WHY, and the answer is **G1, THE PAGE-SPAN GATE**, which is container
arithmetic and needed no engine at all:

    `GetTexture` builds every page as 256x256 texels (`PSXTextureMgr.cs:179`) and
    `CreateBufferColor32` steps `w>>1` halfwords per row at 8 bpp from base `TX<<6, TY<<8`
    (`PSXTexture.cs:44-45, :71`).  So tpage `tx=10, ty=1, tp=1` is VRAM **x 640..767**, y 256..511 =
    **ALL FOUR** declared 32 KB cells: (640,256) (640,384) (704,256) (704,384).  The MESH key names
    the PAGE; only `u,v` choose the cell.  **Cast 1 marked two of the four.**  A reader at `u >= 128`
    samples column 704 -- uploaded, blitted 252x per cast, and UNMARKED -- which is indistinguishable
    from "not sampled".  ef038 declares B = 0x0080 on 19 of its 27 column-640 slots, and 0x0080
    texels is exactly the shift onto column 704.

THE REPAIR IS THE SAME CAST WITH FOUR MARKS, AND IT UPGRADES THE READ FROM 2-WAY TO 4-WAY.  Two
independent screen properties carry two independent halfwords:

    ORIENTATION  answers **B** (the u axis, hypothesis H_U)     VERTICAL stripes -> column 640
                                                                HORIZONTAL bands -> column 704
    PITCH        answers **A** (the v axis, the original U1)    COARSE (few, fat) -> the UPPER cell
                                                                FINE (many, thin) -> the LOWER cell

    cell            (A applied?, B applied?)   mark                      what it says
    (640,256)       (no,  no )                 COARSE VERTICAL           neither halfword moves it
    (640,384)       (yes, no )                 FINE   VERTICAL           A moves it, B does not
    (704,256)       (no,  yes)                 COARSE HORIZONTAL         B moves it, A does not
    (704,384)       (yes, yes)                 FINE   HORIZONTAL         both move it

All four marks carry **EXACTLY EQUAL DUTY** -- 48 of 128 texels, 37.5 % -- so neither axis can be
scored as "it got darker", which is the threshold this arc keeps paying for.  COUNT 12 vs 4 is 3:1
and THICKNESS 4 vs 12 is 1:3, and the read is still PITCH and ORIENTATION, never a count (see the
DO-NOT-COUNT clause in the emitted PROTOCOL.txt).

WHY ORIENTATION IS THE COLUMN AXIS AND NOT THE OTHER WAY ROUND -- THE BARREL-ROLL CONFOUND.
The s76 control cast reconstructed block 2 of ef038's `DR_MOVE` stream as **two phase-locked vertical
barrel rolls** (`s76-read\verify\roll.reconstruction.json`, `model_ok: true`, every frame tiling its
destination exactly):

    column 640   f237..379   master = the LOWER cell, read-only  ->  copy = the UPPER cell, +1 row/frame
    column 704   f254..380   master = the UPPER cell, read-only  ->  copy = the LOWER cell, +2 rows/frame

A vertical roll TRANSLATES a horizontal-band grating (same pitch, moving phase -- it CRAWLS) and
leaves a vertical-stripe grating PIXEL-IDENTICAL (each row is copied whole, and a full-height stripe
is the same in every row).  So:

  * whichever cell of a column is sampled, the column's ORIENTATION is on screen for the entire cast
    -- the roll cannot change it.  **B is answerable in every frame.**
  * the PITCH of a COPY cell is its own only until the roll starts, then it becomes the MASTER's.
    **A is answerable cleanly in the pre-roll window f214..236** (both CLUT families draw there:
    67/67 meshes, 24,917 tris in the marked cast -- `s76-read\adjudicate\adj.preroll.json`), and
    after that on column 704 by MOTION, because a crawling coarse band is a copy cell and a static
    one is the master.
  * column 704 is given the HORIZONTAL (roll-visible) orientation on purpose: it is where the answer
    family lands if H_U holds, it rolls twice as fast, and its pre-roll window is the longer of the
    two (f214..253 vs f214..236).

THE CONTROL, REBUILT.  Cast 1's control was the 7 A=0x0000 readers on the faint cut-out CLUT
`0x3d40`, whose cell is ALREADY 28.8 % transparent -- a ~1.9x instrument with no stock reference.
Cast 2 keeps it and adds two things it did not have:

  1. **A BRIGHT-FAMILY COLUMN CONTROL.**  The B histogram on column 640 is {0x0000: 8, 0x0080: 19},
     and the joint is {(A,B) = (0,0): 7, (0x80,0): **1**, (0x80,0x80): 19}.  That single
     (0x80, 0x00) slot is the wrap reader `0x79168`, on the OPAQUE `0x3dc0` palette: under every live
     reading of B it reads column 640, so it must show a VERTICAL grating in the bright family.  Cast
     1 had no bright-family control at all.
  2. **A MEASURED, THRESHOLD-FREE HOLE STATISTIC.**  The control cell's mark is VERTICAL because the
     stock cell under `0x3d40` contains **0 fully-transparent COLUMNS** and **4 fully-transparent
     ROWS** -- so vertical stripes start from a population of zero and horizontal bands do not.  The
     COARSE (12-wide) class is chosen over the FINE for the same cell because a 12-texel feature is
     ~37.5 screen px at the derived scale and survives the capture's blur (`build\blurprice.
     derivation.json`) where a 4-texel one does not.

THE RESIDENCY CANARY -- §9.3's honest limit 3, closed.  Neither s76 log proves the U1 override was
RESIDENT during the marked cast, because a zero-writing probe is invisible to row counts by design.
Cast 2 therefore writes ONE non-zero block per cell: a 12x12 patch of the palette index that is
opaque and brightest under BOTH of the column's CLUTs, derived here and never typed, placed at a
per-cell corner and guaranteed disjoint from every stripe.  It is 0.88 % of a cell and it moves a
BRIGHT-tail statistic, which is orthogonal to the near-black statistic the marks move.  **It is NOT
part of the read** and the protocol says so in capitals.

THE INSTRUMENT.  The stripes stay a ZERO-WRITE: a `0x00` byte is index 0 twice at 4bpp, once at 8bpp
and half of the cutout word `0x0000` at 15bpp -- at every depth a zeroed texel is the palette-entry-0
value.  All 27 readers derive 8bpp and the probe REFUSES if that stops being true.

WHERE THE FOUR CELLS' GEOMETRY COMES FROM.  The 640 pair resolves through the kit
(`repaint.texel_page` -> `so-uv`, 8 bpp).  The 704 pair **is refused by the kit as DEPTH-UNKNOWN, and
that refusal is pinned as a FACT rather than routed around**: nothing in ef038 binds column 704, so
the container never states those cells' depth.  What states it is the READER's own page word, whose
span covers them -- which is G1 and is re-derived here on every run, including the byte<->texel map
(page texel `u` -> halfword `tx*64 + u//2` -> byte `u mod 128` of that column's own 128-byte row,
checked for all 256 texels of the page).

THE LEDGER.  `--deploy` snapshots whatever the live override holds into THIS probe's own SCRATCH
root -- never the kit's -- verifies the readback sha, and emits a `compile()`-checked, idempotent
`revert_probe.py`.  The `pre` / `pre.ABSENT` markers are MUTUALLY EXCLUSIVE by construction.  **THE
LEDGER TRAP:** revert this probe BEFORE any `summon-reskin deploy` touches this root.

PROVENANCE.  Every number is derived from the user's own container at run time; zero Square-Enix
bytes live in this file.  `pin_source` refuses a foreign `--from` by NAME *and* by STRUCTURE (all
four cells' geometry, the kit's own refusal on the 704 pair, the column-640 census with its A **and**
B histograms, the G1 page span, and the stock sha), so no other container can be staged as `ef038`
and written over the ef038 override.
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
# whose whole content is a COUNT cannot survive.  It is a 1-D rule, so cast 2 uses it unchanged for
# the U axis too: a vertical stripe's left edge is placed by the same arithmetic as a band's top.
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
#: per-CAST staging roots.  THEY MUST DIFFER: the ledger markers (`pre` / `pre.ABSENT`) and the
#: emitted revert live in the root, so two casts sharing one root would consume each other's
#: snapshot -- the same class of defect §8.2 already had to fix once inside a single root.
DEFAULT_ROOT = {1: os.path.join(U1_ROOT, "cellprobe"),
                2: os.path.join(U1_ROOT, "cast2", "cellprobe")}
DEFAULT_CORPUS = os.path.join(SCRATCH, "ef%03d.bytes" % EFFECT)
MOD_ROOT = (r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"
            r"\FF9CustomMap")
GAME_OVERRIDE = os.path.join(MOD_ROOT, "FF9_Data", "SpecialEffects", "ef%03d" % EFFECT)

ROW_BYTES = 128                      # 8bpp, 64 halfwords wide -> 128 texels == 128 bytes per line
CELL_ROWS = 128
CELL_COLS = 128
CELL_BYTES = ROW_BYTES * CELL_ROWS   # 0x4000

#: THE COLUMN IS THE VEHICLE.  Not a record -- 27 of ef038's 28 non-creature `so` records bind it.
COLUMN = 640
#: ...AND THE PAGE IS BOTH COLUMNS.  G1: at 8 bpp a tpage spans TWO 64-halfword columns, so the page
#: word every one of those 27 readers carries addresses column 704 as well, at texel u >= 128.
COLUMN_HI = 704
UPPER_CELL = "cell.s0.x%d_y256" % COLUMN
LOWER_CELL = "cell.s0.x%d_y384" % COLUMN
UPPER_CELL_HI = "cell.s0.x%d_y256" % COLUMN_HI
LOWER_CELL_HI = "cell.s0.x%d_y384" % COLUMN_HI
QUAD = (UPPER_CELL, LOWER_CELL, UPPER_CELL_HI, LOWER_CELL_HI)

#: THE MARKS.  ``cell -> (axis, feature count, feature thickness in texels)``.
#:   axis "H" = horizontal bands, placed down the ROW span, each band a whole 128-byte row;
#:   axis "V" = vertical stripes, placed across the U span, each stripe a full-height byte column.
#: FINE is 12 x 4 and COARSE is 4 x 12: COUNT 3:1, THICKNESS 1:3, and duty EXACTLY EQUAL at
#: 48/128 = 37.5 %, so no mark in this cast can be told from another by how dark it got.
FINE = (12, 4)
COARSE = (4, 12)
MARKS_BY_CAST = {
    # CAST 1, as it ran and as it was read -- regenerable byte-for-byte, never re-tuned.
    1: {UPPER_CELL: ("H", 12, 4), LOWER_CELL: ("H", 4, 8)},
    # CAST 2, the G1 repair: all four cells of the page, two axes, one cast.
    2: {UPPER_CELL:    ("V",) + COARSE,
        LOWER_CELL:    ("V",) + FINE,
        UPPER_CELL_HI: ("H",) + COARSE,
        LOWER_CELL_HI: ("H",) + FINE},
}

#: WHAT EACH MARK MEANS, once, so the protocol cannot drift from the code that writes it.
MEANING_BY_CAST = {
    1: {UPPER_CELL: "A is NOT applied to the sample (R_FLAGS, or declared-and-ignored)",
        LOWER_CELL: "A IS applied (V-offset by 128, or a page-half select -- they agree here)"},
    2: {UPPER_CELL:    "NEITHER halfword moves the sample  (A not applied, B not applied)",
        LOWER_CELL:    "A IS applied, B is NOT            (the v axis moves, the u axis does not)",
        UPPER_CELL_HI: "B IS applied, A is NOT            (H_U holds; the v axis does not move)",
        LOWER_CELL_HI: "BOTH halfwords are applied        (A on v and B on u)"},
}

#: ---- THE ROLL, FROM THE s76 CONTROL CAST -----------------------------------------------------
#: These four facts are LOG-DERIVED, not container-derived, so they are stated here with their
#: provenance and re-checked by `build\roll_check.py` against the saved reconstruction rather than
#: being quietly trusted.  Source: `...\u1-second-array\s76-read\verify\roll.reconstruction.json`
#: (`model_ok: true`, `every_frame_tiles_..._exactly: true`) and study §9.3.
ROLL = {
    COLUMN:    {"master": LOWER_CELL,    "copy": UPPER_CELL,    "rows_per_frame": 1,
                "first_frame": 237, "last_frame": 379},
    COLUMN_HI: {"master": UPPER_CELL_HI, "copy": LOWER_CELL_HI, "rows_per_frame": 2,
                "first_frame": 254, "last_frame": 380},
}
#: the first effect frame on which the marked page is sampled at all (§9.3).  f214..236 is the
#: PRE-ROLL WINDOW in which all four cells still hold their own marks.
FIRST_SAMPLED_FRAME = 214

#: ---- THE RESIDENCY CANARY --------------------------------------------------------------------
#: One non-zero block per cell, 12x12 texels, at a per-cell corner, disjoint from every stripe.
#: The INK INDEX IS DERIVED (brightest index that is opaque under BOTH of the column's CLUTs) --
#: cast B of the Odin ladder was refuted precisely because its ink byte was chosen for brightness on
#: one decode and rendered identically on the others.
CANARY_SIZE = 12
CANARY_AREA = 144
CANARY_CORNER = {UPPER_CELL: ("left", "top"), LOWER_CELL: ("right", "top"),
                 UPPER_CELL_HI: ("left", "bottom"), LOWER_CELL_HI: ("right", "bottom")}

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
#: THE 704 PAIR.  `(file offset, byte length)` plus the fact that the KIT REFUSES them: no `so`
#: record binds column 704 anywhere in ef038, so the container states no depth for these cells and
#: `repaint.texel_page` says DEPTH-UNKNOWN.  That refusal is pinned POSITIVELY -- a container in
#: which those cells suddenly resolve is a container whose second column has a binder, and every
#: word of the G1 argument would have to be re-derived for it.
SOURCE_PIN_CELLS_HI = {UPPER_CELL_HI: (0x2146c, 0x4000), LOWER_CELL_HI: (0x2546c, 0x4000)}
#: the column census: total binding slots on COLUMN, the A histogram, the B histogram, the JOINT
#: (A,B) histogram -- the joint is what makes the 4-way read scoreable, and the lone (0x80, 0x00)
#: slot is the bright-family column control -- and the ONE wrap reader whose v runs to 255.
SOURCE_PIN_COLUMN = {"slots": 27, "A": {0x0080: 20, 0x0000: 7},
                     "B": {0x0080: 19, 0x0000: 8},
                     "AB": {(0x0000, 0x0000): 7, (0x0080, 0x0000): 1, (0x0080, 0x0080): 19},
                     "wrap_recs": (0x79168,)}
#: and the SECOND column of the same page has NO binder at all -- which is G1's whole point.
SOURCE_PIN_COLUMN_HI_SLOTS = 0
#: G1, as arithmetic: the readers' shared page word, its decoded page, and the columns it spans.
SOURCE_PIN_PAGE = {"tpage": 0x009a, "tx": 10, "ty": 1, "bpp": 8, "columns": (640, 704)}
#: sha256 of the stock ef038 container, measured off the user's own install
#: (`x64/FF9_Data/resources.assets`) and equal to the corpus copy.  A pin, not documentation.
EXPECT_STOCK_SHA256 = "8f71a91b5ea8761cb072d0c5aa53fdd6cd926ec03a77634a99bf582fec4eb2a2"
#: what CAST 1 produced, so `--cast 1` is a REGRESSION TEST and not just a code path.
CAST1_CONTAINER_SHA256 = "1f20d79810d1123e90461ee8493223e7361acba7f5971ad784e15d0d386cc168"

SO_MAGIC = 0x6F73                    # reskin.py:309
SO_BPP = {0: 4, 1: 8, 2: 15, 3: 15}  # reskin.py:311
MAX_SO_PARTS = 15                    # reskin.py:344
SPAN_COLS = {4: 1, 8: 2, 15: 4}      # PSXTexture.cs:51/:71/:91 -- halfword step per row, /64


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


def crossing_counts(reader: dict, marked: set, axis: str) -> int:
    """How many of a reader's faces touch at least one marked LINE of a mark, taken modulo the cell.

    ``axis`` picks which of the face's two spans is tested: "H" marks are row sets and are crossed
    by a face's v span; "V" marks are column sets and are crossed by its u span.  The modulo matters
    for exactly one reader -- the wrap record, whose v runs to 255 -- and it is the honest reading
    for it: whichever half that face lands in, its span reduced mod 128 is the set of cell lines it
    covers.  For the other 26 readers (v <= 127) it is the identity.
    """
    n = 0
    for (vlo, vhi, ulo, uhi) in reader["_faces"]:
        lo, hi, mod = ((vlo, vhi, CELL_ROWS) if axis == "H" else (ulo, uhi, CELL_COLS))
        if any((x % mod) in marked for x in range(lo, hi + 1)):
            n += 1
    return n


def page_span(tpage: int) -> dict:
    """G1, from the page word alone: which VRAM columns a tpage covers, and the byte<->texel map.

    `GetTexture` builds a page as 256x256 texels; `CreateBufferColor32` steps ``w >> 1`` halfwords
    per row at 8 bpp from base ``TX << 6`` -- so an 8 bpp page is 128 halfwords = TWO 64-halfword
    columns wide.  Page texel ``u`` therefore lives at halfword ``tx*64 + u//2``, in the column
    ``u // 128``, at BYTE ``u % 128`` of that column's own 128-byte cell row.  The map is asserted
    over every texel of the page rather than argued.
    """
    tx, ty, bpp = tpage & 0x0F, (tpage >> 4) & 1, SO_BPP[(tpage >> 7) & 3]
    n = SPAN_COLS[bpp]
    cols = [tx * 64 + 64 * i for i in range(n)]
    ok = True
    for u in range(n * 128):
        hx = tx * 64 + u // 2
        col = (hx - tx * 64) // 64
        if 2 * (hx - (tx * 64 + 64 * col)) + (u & 1) != u - 128 * col or col != u // 128:
            ok = False
            break
    return {"tpage": tpage, "tx": tx, "ty": ty, "bpp": bpp, "span_cols": n, "columns": cols,
            "vram_x": [tx * 64, tx * 64 + n * 64 - 1], "vram_y": [ty * 256, ty * 256 + 255],
            "byte_map_verified": ok}


# ============================================================================ THE SOURCE PIN
def pin_source(blob: bytes, path: str, cast: int) -> dict:
    """REFUSE a container that is not the effect these constants were measured on.

    Independent pins, because a name is a convention and a derivation is a fact:

    * the source's FILE NAME must name this module's ``EFFECT``;
    * its sha256 must be the stock sha this cast was designed against (drift in the user's install
      -- a Steam or Moguri patch -- must stop the cast, not silently re-aim it);
    * both column-640 cells must resolve at the depth, channel and FILE OFFSET measured here, and
      their declared cover spans must be the ones the marks were sized against;
    * the whole column-640 reader census must reproduce: 27 binding slots, the A histogram
      {0x0080: 20, 0x0000: 7}, and the one wrap reader.  **This is the pin that matters.**  The
      cast's negative control IS that histogram; a container that does not reproduce it has no
      in-cast control, so running this instrument on it would produce a read nobody could score.

    ★ CAST 2 ADDS FOUR MORE, and every one of them is a G1 fact:

    * the B histogram and the JOINT (A,B) histogram -- the 4-way read is only scoreable if the
      three joint classes are the ones the prediction table was written for;
    * the 704 pair's file offsets and lengths, taken from `reskin.page_cells`;
    * the KIT'S OWN REFUSAL on that pair (DEPTH-UNKNOWN, no binder).  If those cells ever resolve,
      column 704 has a binder and it is no longer the unmarked second half of somebody else's page;
    * the page span itself: the readers' shared page word must decode to tx=10, 8 bpp, columns
      {640, 704}, and the byte<->texel map must hold for all 256 texels.
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

    out = {"ok": True, "sha256": sha, "name": base, "cells": notes,
           "column_slots": len(readers),
           "A_histogram": {hex(k): v for k, v in sorted(hist.items())},
           "wrap_recs": [hex(w) for w in wraps],
           "text": "source pin OK: %s names ef%03d, sha %s, %s; column %d = %d slots, A %s, wrap %s"
                   % (base, EFFECT, sha[:16], "; ".join(notes), COLUMN, len(readers),
                      {hex(k): v for k, v in sorted(hist.items())}, [hex(w) for w in wraps])}
    if cast == 1:
        return out

    # ---- CAST 2 ONLY: the G1 pins ------------------------------------------------------------
    bhist = dict(Counter(r["B"] for r in readers))
    if bhist != SOURCE_PIN_COLUMN["B"]:
        raise _fail("%s's column-%d B histogram is %r, not %r.  The 4-way read needs B to split "
                    "the column, and the single (A=0x0080, B=0x0000) slot is the BRIGHT-FAMILY "
                    "column control -- cast 1 had none."
                    % (path, COLUMN, {hex(k): v for k, v in sorted(bhist.items())},
                       {hex(k): v for k, v in sorted(SOURCE_PIN_COLUMN["B"].items())}))
    ab = dict(Counter((r["A"], r["B"]) for r in readers))
    if ab != SOURCE_PIN_COLUMN["AB"]:
        raise _fail("%s's column-%d joint (A,B) histogram is %r, not %r.  The prediction table is "
                    "written per JOINT class; a different joint is a different cast."
                    % (path, COLUMN, {"%#x/%#x" % k: v for k, v in sorted(ab.items())},
                       {"%#x/%#x" % k: v for k, v in sorted(SOURCE_PIN_COLUMN["AB"].items())}))
    hi = column_readers(blob, COLUMN_HI)
    if len(hi) != SOURCE_PIN_COLUMN_HI_SLOTS:
        raise _fail("%s binds column %d with %d slot(s), not %d.  G1's whole content is that the "
                    "second column of this page has NO binder of its own, so the only page word "
                    "that can address it is the one the column-%d readers already carry."
                    % (path, COLUMN_HI, len(hi), SOURCE_PIN_COLUMN_HI_SLOTS, COLUMN))
    census = {pc.name: pc for pc in RS.page_cells(blob).values()}
    for cell, (want_off, want_len) in sorted(SOURCE_PIN_CELLS_HI.items()):
        pc = census.get(cell)
        if pc is None:
            raise _fail("%s does not declare %s at all -- G2 (cell completeness) fails and the "
                        "repair has nothing to mark on the second column." % (path, cell))
        if (pc.off, pc.nbytes) != (want_off, want_len):
            raise _fail("%s declares %s at %#x/%#x, not the %#x/%#x this cast was measured on."
                        % (path, cell, pc.off, pc.nbytes, want_off, want_len))
        try:
            RP.texel_page(blob, cell, EFFECT)
        except Exception as exc:                                    # noqa: BLE001
            if "DEPTH-UNKNOWN" not in str(exc):
                raise _fail("%s refuses %s for a reason that is NOT depth-unknown (%s: %s)."
                            % (path, cell, type(exc).__name__, str(exc).splitlines()[0][:120]))
        else:
            raise _fail("%s RESOLVES %s through the kit.  This cast's whole argument is that column "
                        "%d has no binder, so the container states no depth for its cells and the "
                        "only page word that reaches them is the column-%d readers' own.  A "
                        "container where they resolve needs the G1 argument re-derived."
                        % (path, cell, COLUMN_HI, COLUMN))
    tps = {r["tpage"] for r in readers}
    if len(tps) != 1:
        raise _fail("the column-%d readers carry %d distinct page words (%s); the page-span "
                    "argument is written for one." % (COLUMN, len(tps),
                                                      ", ".join("%#06x" % t for t in sorted(tps))))
    span = page_span(next(iter(tps)))
    want = SOURCE_PIN_PAGE
    if (span["tpage"], span["tx"], span["ty"], span["bpp"],
            tuple(span["columns"])) != (want["tpage"], want["tx"], want["ty"], want["bpp"],
                                        want["columns"]):
        raise _fail("the shared page word decodes to %r, not the pinned %r." % (span, want))
    if not span["byte_map_verified"]:
        raise _fail("the page's texel<->byte map does not hold over all %d texels -- every "
                    "placement in this cast assumes it does." % (span["span_cols"] * 128))
    out["B_histogram"] = {hex(k): v for k, v in sorted(bhist.items())}
    out["AB_histogram"] = {"%#x/%#x" % k: v for k, v in sorted(ab.items())}
    out["column_hi_slots"] = len(hi)
    out["page_span"] = span
    out["cells_hi"] = ["%s @%#x/%#x, kit REFUSES (depth-unknown, no binder)"
                       % (c, SOURCE_PIN_CELLS_HI[c][0], SOURCE_PIN_CELLS_HI[c][1])
                       for c in sorted(SOURCE_PIN_CELLS_HI)]
    out["text"] += ("; B %s, joint %s; column %d = %d slots; page %#06x = tx%d/%dbpp spanning %r, "
                    "byte map verified"
                    % (out["B_histogram"], out["AB_histogram"], COLUMN_HI, len(hi),
                       span["tpage"], span["tx"], span["bpp"], span["columns"]))
    return out


# ============================================================================ THE MARK
def stripe_tops(k: int, rows: int, lo: int, hi: int):
    """The TOP (or LEFT) line of each of ``k`` evenly-spaced ``rows``-line features inside ``lo..hi``.

    A one-line wrapper over `odin_band_stamp.evenly_spaced_tops` and NOT a reimplementation of it:
    both instruments must place their marks by one rule, and a count-only read cannot survive a
    +-1-row divergence between the rule that writes and the rule that predicts.  The rule is 1-D, so
    cast 2's VERTICAL stripes are placed with the identical call on the U axis.
    """
    return evenly_spaced_tops(k, rows, lo, hi)


def marked_lines(k: int, rows: int, lo: int, hi: int, limit: int) -> list:
    out = set()
    for t in stripe_tops(k, rows, lo, hi):
        for r in range(t, min(limit, t + rows)):
            out.add(r)
    return sorted(out)


def marked_rows(k: int, rows: int, lo: int, hi: int) -> list:
    return marked_lines(k, rows, lo, hi, CELL_ROWS)


def authored_offsets(cell_off: int, lines, axis: str) -> range:
    """(generator) every FILE offset one mark writes, inside one 0x4000 cell.

    "H" -- whole 128-byte rows, exactly as cast 1 wrote them.
    "V" -- one byte per row at each marked column, over the cell's FULL height.  Full height is not
           a convenience: a vertical stripe is roll-INVARIANT only because every row carries it, and
           roll invariance is what makes ORIENTATION readable after f237.
    """
    if axis == "H":
        for r in lines:
            base = cell_off + r * ROW_BYTES
            for o in range(base, base + ROW_BYTES):
                yield o
    elif axis == "V":
        for r in range(CELL_ROWS):
            base = cell_off + r * ROW_BYTES
            for c in lines:
                yield base + c
    else:
        raise _fail("unknown mark axis %r" % axis)


def canary_shape(axis: str, lines) -> tuple:
    """``(width, height)`` of a canary that FITS BETWEEN this cell's stripes and keeps its AREA.

    A canary may never punch a hole in the grating, so its extent ACROSS the mark cannot exceed the
    widest gap the mark leaves -- 20 texels on a COARSE cell but only 7 on a FINE one.  Rather than
    shrink the FINE cells' canary to a seventh of the area (and with it the bright-tail statistic
    that proves residency), the block is made a RECTANGLE: as thick as the widest gap allows, up to
    ``CANARY_SIZE``, and as long as it needs to be to keep ~``CANARY_AREA`` texels.  Both numbers
    are derived from the mark that was actually placed.
    """
    limit = CELL_ROWS if axis == "H" else CELL_COLS
    marked = set(lines)
    best = run = 0
    for i in range(limit):
        run = 0 if i in marked else run + 1
        best = max(best, run)
    t = max(1, min(CANARY_SIZE, best))
    e = min(limit, -(-CANARY_AREA // t))
    return (e, t) if axis == "H" else (t, e)      # (width, height)


def canary_block(cell_off: int, authored: set, corner, row_span, shape) -> dict:
    """The first ``shape`` block at ``corner`` that touches no authored stripe byte.

    Deterministic: the scan order is fixed by the corner, so the block is a function of the marks
    and not of the order anything ran in.  It is also constrained to the cell's SAMPLED row span,
    because a canary nothing reads proves nothing about residency.
    """
    w, h = shape
    hside, vside = corner
    rlo, rhi = row_span
    rows = list(range(rlo, max(rlo, rhi - h + 2)))
    cols = list(range(0, CELL_COLS - w + 1))
    for v0 in (rows if vside == "top" else rows[::-1]):
        for u0 in (cols if hside == "left" else cols[::-1]):
            offs = {cell_off + (v0 + dv) * ROW_BYTES + (u0 + du)
                    for dv in range(h) for du in range(w)}
            if not (offs & authored):
                return {"u0": u0, "v0": v0, "w": w, "h": h, "offsets": offs,
                        "corner": "%s-%s" % (vside, hside)}
    raise _fail("no %dx%d canary block fits clear of the stripes in this cell" % (w, h))


def canary_ink(blob: bytes, cluts) -> dict:
    """The brightest palette index that is OPAQUE under EVERY CLUT the column's readers use.

    DERIVED, never chosen.  Cast B of the Odin ladder was refuted because its ink byte rendered
    identically under the decodes it was supposed to separate; here the requirement is weaker and
    checkable -- the canary only has to be visibly BRIGHT on both families, and "both" is measured.
    """
    words = {}
    hdr = EC.parse_header(blob, strict=True)
    pals = {}
    for ch in hdr.chunks:
        for p in RS.id0_palettes(blob, ch, RS.chunk_tag(ch))[1]:
            pals[p.vram] = p
    for cw in cluts:
        words[cw] = struct.unpack_from("<256H", blob, pals[RS.clut_word_xy(cw)].off)

    def luma(w):
        if not w:
            return 0
        r, g, b, _a = TX.bgr555_rgba(w)
        return (r * 299 + g * 587 + b * 114) // 1000

    best = None
    for i in range(1, 256):
        if any(TX.bgr555_rgba(words[cw][i])[3] == 0 for cw in cluts):
            continue
        score = min(luma(words[cw][i]) for cw in cluts)
        if best is None or score > best[0]:
            best = (score, i)
    if best is None:
        raise _fail("no palette index is opaque under all of %s -- the canary has no ink"
                    % ", ".join("%#06x" % c for c in cluts))
    score, idx = best
    return {"index": idx, "byte": "0x%02x" % idx, "min_luma_over_cluts": score,
            "per_clut": {"%#06x" % cw: {"word": words[cw][idx],
                                        "rgba": list(TX.bgr555_rgba(words[cw][idx])),
                                        "luma": luma(words[cw][idx])} for cw in cluts}}


def byte_proof(stock: bytes, probe: bytes, authored: set, canary: set, ink: int) -> dict:
    """THE PROOF: the changed-vs-stock byte set is EXACTLY the authored set, by code.

    Claims, each checked and each able to fail loudly:

    1. the container's LENGTH is unchanged (an `so` container is offset-addressed; a length change
       is a different file, not a marked one);
    2. the stripe set and the canary set are DISJOINT (a canary inside a stripe would be a hole in
       the mark and a lie in the proof);
    3. every authored stripe offset holds `0x00` in the probe -- the mark is a zero-write, wholly;
    4. every canary offset holds the DERIVED ink index -- the one deliberate non-zero write;
    5. NO offset outside those two sets differs -- nothing else moved;
    6. the CHANGED set is exactly the offsets whose stock byte already differed from what was
       written.  It is a SUBSET by arithmetic (writing 0x00 over 0x00 changes nothing), so the
       honest statement is `changed == {o in stripes : stock[o] != 0} | {o in canary : stock[o] !=
       ink}` and both directions are asserted: 0 extra, 0 missing, 0 wrong-value.
    """
    if len(probe) != len(stock):
        raise _fail("the probe changed the container's LENGTH (%d -> %d)" % (len(stock), len(probe)))
    clash = authored & canary
    if clash:
        raise _fail("%d canary byte(s) sit INSIDE a stripe (first %#x)"
                    % (len(clash), sorted(clash)[0]))
    nonzero_ink = [o for o in authored if probe[o] != 0]
    if nonzero_ink:
        raise _fail("%d authored offset(s) are not 0x00 in the probe (first %#x = %#04x)"
                    % (len(nonzero_ink), nonzero_ink[0], probe[nonzero_ink[0]]))
    wrong_canary = [o for o in canary if probe[o] != ink]
    if wrong_canary:
        raise _fail("%d canary offset(s) do not hold the derived ink %#04x (first %#x = %#04x)"
                    % (len(wrong_canary), ink, wrong_canary[0], probe[wrong_canary[0]]))
    changed = {o for o in range(len(stock)) if stock[o] != probe[o]}
    extra = sorted(changed - authored - canary)
    if extra:
        raise _fail("%d byte(s) changed OUTSIDE the authored set (first %#x: %#04x -> %#04x)"
                    % (len(extra), extra[0], stock[extra[0]], probe[extra[0]]))
    want_changed = ({o for o in authored if stock[o] != 0}
                    | {o for o in canary if stock[o] != ink})
    missing = sorted(want_changed - changed)
    if missing:
        raise _fail("%d authored byte(s) did NOT change (first %#x)" % (len(missing), missing[0]))
    spurious = sorted(changed - want_changed)
    if spurious:                                                    # unreachable by arithmetic
        raise _fail("%d changed byte(s) already held the written value -- impossible; the walk is "
                    "wrong" % len(spurious))
    return {"authored_bytes": len(authored) + len(canary),
            "stripe_bytes": len(authored), "canary_bytes": len(canary),
            "changed_bytes": len(changed),
            "already_zero_in_stock": len(authored) - len({o for o in authored if stock[o] != 0}),
            "canary_already_ink_in_stock": len(canary) - len({o for o in canary
                                                              if stock[o] != ink}),
            "outside_authored": 0, "missing": 0, "wrong_value": 0,
            "length_stock": len(stock), "length_probe": len(probe),
            # the claim is stated over the sets that EXIST.  With no canary (cast 1) it is the
            # sentence cast 1 was read with, verbatim, so `--cast 1` reproduces its PROTOCOL.txt
            # body and not merely its bytes.
            "claim": ("changed-vs-stock == {o in authored : stock[o] != 0}  (0 extra / 0 missing / "
                      "0 wrong-value), and every authored offset is 0x00 in the probe"
                      if not canary else
                      "changed-vs-stock == {o in stripes : stock[o] != 0} | {o in canary : "
                      "stock[o] != ink}  (0 extra / 0 missing / 0 wrong-value); every stripe byte "
                      "is 0x00 and every canary byte is the derived ink in the probe")}


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
    mean = sum(lums) / len(lums)
    thr = 0.35 * mean
    return {"mean_luma": mean, "opaque_pct": 100.0 * opq / len(d),
            "min": min(lums), "max": max(lums),
            # the a19-class statistic the cast-1 read was decided on: the near-black area fraction
            # of the surface's own light (castread/REPORT-U1.md 3.2-3.3).
            "near_black_pct": 100.0 * sum(1 for x in lums if x < thr) / len(lums)}


def full_extent_runs(blob: bytes, cell_off: int, clut_words) -> dict:
    """How many WHOLE rows / WHOLE columns of a cell are transparent end to end.

    This is the control family's threshold-free statistic.  A mark's stripe is transparent over the
    cell's entire extent; stock lace is not, and how not is measured here rather than assumed --
    which is what picks VERTICAL for the control cell (stock: 0 full columns, 4 full rows).
    """
    tr = [[clut_words[blob[cell_off + r * ROW_BYTES + c]] == 0 for c in range(CELL_COLS)]
          for r in range(CELL_ROWS)]
    return {"full_transparent_rows": sum(1 for r in range(CELL_ROWS) if all(tr[r])),
            "full_transparent_cols": sum(1 for c in range(CELL_COLS)
                                         if all(tr[r][c] for r in range(CELL_ROWS)))}


# ============================================================================ GENERATE
def generate(from_path: str, root: str, cells=None, cast: int = 2) -> dict:
    stock = Path(from_path).read_bytes()
    # THE SOURCE PIN RUNS INSIDE generate(), not in main(): no caller -- and no import of this
    # module -- can reach the striping, or the deploy that consumes its output, with a container
    # these constants were not measured on.  A guard at the CLI edge is a guard one call site wide.
    pin = pin_source(stock, from_path, cast)
    marks = MARKS_BY_CAST[cast]
    meaning = MEANING_BY_CAST[cast]

    census = RS.page_cells(stock)
    by_name = {pc.name: pc for pc in census.values()}
    want = list(cells) if cells else list(marks)
    unknown = [c for c in want if c not in by_name]
    if unknown:
        raise _fail("no such cell(s) %r; this container declares:\n%s"
                    % (unknown, "\n".join("  " + n for n in sorted(by_name))))
    unmarked = [c for c in want if c not in marks]
    if unmarked:
        raise _fail("%r has no entry in cast %d's MARKS.  This instrument writes exactly the cells "
                    "of the tpage %#06x page; marking another would add a mark the read has no "
                    "meaning for." % (unmarked, cast, SOURCE_PIN_PAGE["tpage"]))

    readers = column_readers(stock)
    cluts = sorted({r["clut"] for r in readers})
    blob = bytearray(stock)
    authored, canary_offs, legend = set(), set(), []
    ink = canary_ink(stock, cluts) if cast == 2 else None

    for cell in sorted(marks):
        pc = by_name[cell]
        axis, k, rows = marks[cell]
        cov = cover_span(stock, (pc.x, pc.y))
        # THE TWO PLACEMENT SPANS, each derived.  "H" marks are placed down the declared `so` row
        # cover; "V" marks are placed across the U span the column's own readers declare.  Both
        # fall back to the whole cell when nothing declares one -- which is the 704 pair's case, by
        # construction: nothing binds that column, which is exactly why cast 1 left it blank.
        if axis == "H":
            lo, hi = cov if cov else (0, CELL_ROWS - 1)
            rule = "so-cover" if cov else "whole-cell"
            limit = CELL_ROWS
        else:
            col_readers = column_readers(stock, pc.x)
            if col_readers:
                lo = min(r["umin"] for r in col_readers)
                hi = max(r["umax"] for r in col_readers)
                rule = "reader-u-cover"
            else:
                lo, hi, rule = 0, CELL_COLS - 1, "whole-cell"
            limit = CELL_COLS
        lines = marked_lines(k, rows, lo, hi, limit)
        written = cell in want
        offs = set(authored_offsets(pc.off, lines, axis)) if written else set()
        if written:
            if pc.nbytes != CELL_BYTES:
                raise _fail("%s is %#x bytes, not the %#x this instrument's row arithmetic assumes"
                            % (cell, pc.nbytes, CELL_BYTES))
            for o in offs:
                blob[o] = 0
            authored |= offs
        legend.append({
            "cell": cell, "written": written, "axis": axis, "k": k, "stripe_rows": rows,
            "class": "FINE" if (k, rows) == FINE else ("COARSE" if (k, rows) == COARSE else "-"),
            "offset": pc.off, "xy": [pc.x, pc.y], "nbytes": pc.nbytes,
            "cover_span": list(cov) if cov else None,
            "placement": rule, "span": [lo, hi],
            "tops": stripe_tops(k, rows, lo, hi), "rows": lines,
            "duty_rows": len(lines), "duty_pct": 100.0 * len(lines) / limit,
            "bytes": len(offs), "meaning": meaning[cell],
            "byte_ranges": ([[pc.off + t * ROW_BYTES,
                              pc.off + min(CELL_ROWS, t + rows) * ROW_BYTES]
                             for t in stripe_tops(k, rows, lo, hi)] if axis == "H" else
                            [[t, min(CELL_COLS, t + rows)]
                             for t in stripe_tops(k, rows, lo, hi)]),
            "lineset": set(lines),
        })

    # ---- THE RESIDENCY CANARY.  After every stripe is placed, so "disjoint" is a fact. ---------
    if cast == 2:
        for L in legend:
            if not L["written"]:
                continue
            pc = by_name[L["cell"]]
            rcov = cover_span(stock, (pc.x, pc.y)) or (0, CELL_ROWS - 1)
            blk = canary_block(pc.off, authored, CANARY_CORNER[L["cell"]], rcov,
                               canary_shape(L["axis"], L["rows"]))
            for o in blk["offsets"]:
                blob[o] = ink["index"]
            canary_offs |= blk["offsets"]
            L["canary"] = {k2: v for k2, v in blk.items() if k2 != "offsets"}
            L["canary"]["bytes"] = len(blk["offsets"])
            L["canary"]["ink"] = ink["byte"]

    probe = bytes(blob)
    EC.parse_header(probe, strict=True)                          # the probe must still parse
    proof = byte_proof(stock, probe, authored, canary_offs, ink["index"] if ink else 0)

    # per-reader crossing counts, for EVERY mark -- the "nothing is starved" claim, measured
    for rec in readers:
        for L in legend:
            rec.setdefault("crossed", {})[L["cell"]] = crossing_counts(rec, L["lineset"], L["axis"])
    for L in legend:
        L.pop("lineset")

    pal = palette_read(stock)
    hdr = EC.parse_header(stock, strict=True)
    pals = {}
    for ch in hdr.chunks:
        for p in RS.id0_palettes(stock, ch, RS.chunk_tag(ch))[1]:
            pals[p.vram] = p
    contrast, contrast_marked, runs = {}, {}, {}
    for L in legend:
        for entry in pal:
            if "error" in entry:
                continue
            words = struct.unpack_from("<256H", stock, pals[tuple(entry["vram"])].off)
            cw = "%#06x" % entry["clut"]
            contrast.setdefault(L["cell"], {})[cw] = cell_contrast(stock, L["offset"], words)
            if cast == 2:
                contrast_marked.setdefault(L["cell"], {})[cw] = cell_contrast(
                    probe, L["offset"], words)
                runs.setdefault(L["cell"], {})[cw] = {
                    "stock": full_extent_runs(stock, L["offset"], words),
                    "marked": full_extent_runs(probe, L["offset"], words)}

    root_p = Path(root)
    root_p.mkdir(parents=True, exist_ok=True)
    out = root_p / ("ef%03d.cellprobe" % EFFECT if cast == 1
                    else "ef%03d.cellprobe.cast%d" % (EFFECT, cast))
    out.write_bytes(probe)
    d = {"cast": cast, "effect": EFFECT, "column": COLUMN, "source": from_path, "root": str(root_p),
         "container": str(out), "sha256": hashlib.sha256(probe).hexdigest(),
         "stock_sha256": pin["sha256"], "bytes": len(probe),
         "marks": {c: list(marks[c]) for c in sorted(marks)}, "legend": legend,
         "byte_proof": proof, "source_pin": pin,
         "readers": [{k: v for k, v in r.items() if k != "_faces"} for r in readers],
         "palette_read": pal, "cell_contrast": contrast,
         "cast_b_bands": dict(CAST_B_BANDS), "cast_b_band_rows": CAST_B_BAND_ROWS,
         "notes": contamination_notes(cast)}
    if cast == 2:
        d.update({"canary_ink": ink, "cell_contrast_marked": contrast_marked,
                  "full_extent_runs": runs, "roll": ROLL,
                  "first_sampled_frame": FIRST_SAMPLED_FRAME,
                  "outcome_table": outcome_table(marks)})
    (root_p / "probe.derivation.json").write_text(
        json.dumps(d, indent=1, default=str), encoding="utf-8")
    d["_readers_full"] = readers
    return d


def outcome_table(marks) -> list:
    """The 4-way (A applied?, B applied?) -> cell -> screen class map, built from MARKS itself.

    Derived from the same dict the writer uses, so the table in PROTOCOL.txt cannot disagree with
    the bytes on disk.  ORIENTATION is the B answer; PITCH CLASS is the A answer.
    """
    axis_word = {"V": "VERTICAL stripes", "H": "HORIZONTAL bands"}
    cls = {FINE: "FINE", COARSE: "COARSE"}

    def klass(cell):
        _ax, k, th = marks[cell]
        return cls.get((k, th), "?")

    rows = []
    for (A_on, B_on, cell) in ((False, False, UPPER_CELL), (True, False, LOWER_CELL),
                               (False, True, UPPER_CELL_HI), (True, True, LOWER_CELL_HI)):
        axis, k, th = marks[cell]
        col = COLUMN_HI if B_on else COLUMN
        r = ROLL[col]
        is_master = cell == r["master"]
        # AFTER THE ROLL a COPY cell holds the MASTER's content, vertically rotated.  A vertical
        # roll preserves a vertical grating exactly and translates a horizontal one, so the copy's
        # PITCH becomes the master's either way and only a horizontal mark also MOVES.
        if is_master:
            post = "%s %s, STATIC" % (klass(cell), axis_word[axis])
        else:
            post = "%s %s, %s" % (
                klass(r["master"]), axis_word[axis],
                "CRAWLING %+d row/frame" % r["rows_per_frame"] if axis == "H"
                else "static (a full-height vertical stripe is roll-INVARIANT)")
        rows.append({
            "A_applied": A_on, "B_applied": B_on, "cell": cell, "column": col,
            "mark": "%s %d x %d texels" % (klass(cell), k, th),
            "screen": "%s, %s" % (klass(cell), axis_word[axis]),
            "role": "MASTER (read-only, never rewritten)" if is_master else
                    "COPY (rewritten from f%d at %+d row/frame)" % (r["first_frame"],
                                                                    r["rows_per_frame"]),
            "pre_roll": "%s %s" % (klass(cell), axis_word[axis]),
            "post_roll": post,
        })
    return rows


def contamination_notes(cast: int = 2) -> list:
    """Every way this cast's signature could be MISTAKEN for an earlier one, checked not asserted."""
    marks = MARKS_BY_CAST[cast]
    L = []
    if cast == 1:
        ks = {c: marks[c][1] for c in marks}
        if len(set(ks.values())) != len(ks):
            L.append("*** LOUD: the two marks share a COUNT (%r) -- the read has no discriminator."
                     % ks)
        if len({marks[c][2] for c in marks}) != len(marks):
            L.append("*** LOUD: the two marks share a THICKNESS -- one of the two read axes is "
                     "gone.")
        for c, (_ax, k, rows) in sorted(marks.items()):
            for bc, bk in sorted(CAST_B_BANDS.items()):
                if k == bk and rows == CAST_B_BAND_ROWS:
                    L.append("*** LOUD: %s's mark (%d x %d rows) is IDENTICAL to the ef424 cast's "
                             "on %s." % (c, k, rows, bc))
                elif k == bk:
                    L.append("note: %s's COUNT (%d) equals the ef424 cast's on %s, but the "
                             "thickness differs (%d vs %d rows) and the container differs (ef%03d "
                             "vs ef424) -- no screen shows both."
                             % (c, k, bc, rows, CAST_B_BAND_ROWS, EFFECT))
        duties = {c: marks[c][1] * marks[c][2] for c in marks}
        if len(set(duties.values())) != len(duties):
            L.append("*** LOUD, DISCLOSED: the two marks have EQUAL aggregate duty (%r rows).  "
                     "COUNT and THICKNESS still differ, which are the two axes the read uses -- but "
                     "never infer the mark from how much of the surface changed." % duties)
        else:
            L.append("duty differs by design but NEARLY: %s.  The read is still structural -- 'many "
                     "thin' vs 'few fat' -- and must never be scored as 'it got darker'."
                     % ", ".join("%s %d/%d rows (%.1f%%)" % (c.split(".")[-1], v, CELL_ROWS,
                                                             100.0 * v / CELL_ROWS)
                                 for c, v in sorted(duties.items())))
        if not any(x.startswith("***") for x in L):
            L.insert(0, "no collision: the two marks differ in COUNT (%d vs %d) and THICKNESS (%d "
                        "vs %d rows), and the ef424 cast's marks (%r at %d rows) are on a different "
                        "container." % (marks[UPPER_CELL][1], marks[LOWER_CELL][1],
                                        marks[UPPER_CELL][2], marks[LOWER_CELL][2],
                                        dict(CAST_B_BANDS), CAST_B_BAND_ROWS))
        return L

    # ---- CAST 2: FOUR marks, so the check is PAIRWISE over all six pairs ----------------------
    names = sorted(marks)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if marks[a] == marks[b]:
                L.append("*** LOUD: %s and %s carry the IDENTICAL mark %r -- that pair is "
                         "indistinguishable and the 4-way read is a 3-way." % (a, b, marks[a]))
    duties = {c: marks[c][1] * marks[c][2] for c in marks}
    if len(set(duties.values())) == 1:
        L.append("DUTY IS EQUAL ACROSS ALL FOUR MARKS (%d/%d texels = %.1f%%) -- ON PURPOSE.  "
                 "Neither axis can be scored as 'it got darker'; the read is ORIENTATION and PITCH "
                 "CLASS." % (next(iter(duties.values())), CELL_ROWS,
                             100.0 * next(iter(duties.values())) / CELL_ROWS))
    else:
        L.append("*** LOUD, DISCLOSED: the four marks do NOT share a duty (%r).  Brightness is then "
                 "a covariate of the read and the DO-NOT-COUNT clause is weaker than designed."
                 % duties)
    axes = Counter(marks[c][0] for c in marks)
    if sorted(axes.values()) != [2, 2]:
        L.append("*** LOUD: the orientation split is %r, not 2 and 2 -- ORIENTATION cannot be the "
                 "column axis." % dict(axes))
    for col, r in ROLL.items():
        ax = marks[r["master"]][0]
        if ax != marks[r["copy"]][0]:
            L.append("*** LOUD: column %d's master and copy carry DIFFERENT orientations, so the "
                     "roll would change the orientation on screen and B would stop being readable "
                     "after f%d." % (col, r["first_frame"]))
    for c, (_ax, k, rows) in sorted(marks.items()):
        for bc, bk in sorted(CAST_B_BANDS.items()):
            if k == bk and rows == CAST_B_BAND_ROWS:
                L.append("*** LOUD: %s's mark (%d x %d) is IDENTICAL to the ef424 cast's on %s."
                         % (c, k, rows, bc))
            elif rows == CAST_B_BAND_ROWS:
                L.append("note: %s's THICKNESS (%d texels) equals the ef424 cast's on %s, but the "
                         "COUNT differs (%d vs %d), the AXIS is stated per cell here, and the "
                         "container differs (ef%03d vs ef424) -- no screen shows both."
                         % (c, rows, bc, k, bk, EFFECT))
    if not any(x.startswith("***") for x in L):
        L.insert(0, "no collision: the four marks are pairwise distinct on ORIENTATION x PITCH "
                    "CLASS (%s), and the ef424 cast's marks (%r at %d rows) are on a different "
                    "container." % (", ".join("%s=%s%d x %d" % (c.split(".")[-1], marks[c][0],
                                                                marks[c][1], marks[c][2])
                                              for c in names),
                                    dict(CAST_B_BANDS), CAST_B_BAND_ROWS))
    L.append("THE CANARY IS NOT A MARK.  One ~%d-texel bright block per cell, at a per-cell corner, "
             "shaped to fit BETWEEN that cell's stripes and disjoint from every one of them -- it "
             "exists to prove the override was RESIDENT (the study's honest limit 3) and must never "
             "be scored as part of the grating." % CANARY_AREA)
    return L


# ============================================================================ THE PROTOCOL
def protocol(d: dict) -> list:
    return protocol_cast1(d) if d["cast"] == 1 else protocol_cast2(d)


def protocol_cast1(d: dict) -> list:
    """CAST 1's protocol body, unchanged, so `--cast 1` reproduces the file that was read."""
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


def protocol_cast2(d: dict) -> list:
    readers = d["_readers_full"]
    leg = {L["cell"]: L for L in d["legend"]}
    fam = lambda A, B: [r for r in readers if r["A"] == A and r["B"] == B]        # noqa: E731
    ink = d["canary_ink"]
    L = [
        "THE U1 SECOND-ARRAY CAST -- CAST 2, THE G1 REPAIR.  ef%03d, ALL FOUR CELLS of tpage %#06x"
        % (d["effect"], d["source_pin"]["page_span"]["tpage"]),
        "  QUESTION         U1, on BOTH axes at once: does the engine apply second-array halfword",
        "                   A (the v axis) and/or halfword B (the u axis, hypothesis H_U)?",
        "  WHY CAST 1 READ NOTHING   G1, the PAGE-SPAN GATE: an 8bpp tpage spans TWO 64-halfword",
        "                   columns, so this page is VRAM x %d..%d, y %d..%d = ALL FOUR declared"
        % (d["source_pin"]["page_span"]["vram_x"][0], d["source_pin"]["page_span"]["vram_x"][1],
           d["source_pin"]["page_span"]["vram_y"][0], d["source_pin"]["page_span"]["vram_y"][1]),
        "                   cells.  Cast 1 marked TWO.  A reader at u >= 128 samples column %d,"
        % COLUMN_HI,
        "                   which was uploaded, blitted, and UNMARKED.",
        "  source           %s" % d["source"],
        "  stock sha256     %s" % d["stock_sha256"],
        "  %s" % d["source_pin"]["text"],
        "",
        "  ================ THE READ, IN ONE BOX ================",
        "     ORIENTATION answers B :   VERTICAL stripes -> column %d (B NOT applied)" % COLUMN,
        "                               HORIZONTAL bands -> column %d (B IS applied)" % COLUMN_HI,
        "     PITCH CLASS answers A :   COARSE (few, fat) -> the UPPER cell (A NOT applied)",
        "                               FINE   (many, thin) -> the LOWER cell (A IS applied)",
        "     They are INDEPENDENT.  Read orientation first; it survives the barrel roll, and it is",
        "     the axis cast 1 could not ask at all.",
        "  ======================================================",
        "",
        "  !! 'VERTICAL' AND 'HORIZONTAL' ARE IN TEXTURE SPACE.  Each surface's own UV mapping decides",
        "  where that lands on screen, and on a shard or an orb it is nowhere near screen-vertical --",
        "  which is exactly why the prediction panels exist and why the read is scored against them",
        "  and not against the words.  WHAT IS PROJECTION-INDEPENDENT, and is the actual claim: the",
        "  two orientation classes differ by NINETY DEGREES ON THE SAME SURFACE, under any camera,",
        "  because a projection maps both by the same transform.  So the question is never 'is it",
        "  vertical on my screen' -- it is 'is it the panel's %s pane or the panel's %s pane'."
        % (UPPER_CELL.split(".")[-1], UPPER_CELL_HI.split(".")[-1]),
        "",
        "  THE FOUR MARKS -- placement imported from odin_band_stamp.evenly_spaced_tops (a 1-D rule,",
        "  used unchanged on the U axis for the vertical marks); row spans from",
        "  odin_band_stamp.cover_span, u spans from the column's own readers.  Nothing is restated.",
        "",
        "  cell                      class  axis  mark          duty        placement       span",
    ]
    for cell in (UPPER_CELL, LOWER_CELL, UPPER_CELL_HI, LOWER_CELL_HI):
        r = leg[cell]
        L.append("  %-25s %-6s %-5s %-13s %2d/%-3d %4.1f%% %-15s %3d..%-3d"
                 % (r["cell"], r["class"], r["axis"], "%d x %d texels" % (r["k"], r["stripe_rows"]),
                    r["duty_rows"], CELL_ROWS, r["duty_pct"], r["placement"],
                    r["span"][0], r["span"][1]))
        L.append("      -> a surface showing THIS mark says: %s" % r["meaning"])
        L.append("      %s %s" % ("rows" if r["axis"] == "H" else "cols", r["rows"]))
        L.append("      cell %#x..%#x; %d stripe byte(s); canary %dx%d = %d B at the %s corner "
                 "(u %d, v %d)"
                 % (r["offset"], r["offset"] + r["nbytes"], r["bytes"],
                    r["canary"]["w"], r["canary"]["h"], r["canary"]["bytes"],
                    r["canary"]["corner"], r["canary"]["u0"], r["canary"]["v0"]))
        if not r["written"]:
            L.append("      *** NOT WRITTEN THIS RUN (--cells narrowed the mark set)")
    p = d["byte_proof"]
    L += ["",
          "  probe container  %d B  sha256 %s" % (d["bytes"], d["sha256"]),
          "  BYTE PROOF       authored %d B (%d stripe + %d canary); changed vs stock %d B"
          % (p["authored_bytes"], p["stripe_bytes"], p["canary_bytes"], p["changed_bytes"]),
          "                   %d stripe byte(s) were ALREADY 0x00; %d canary byte(s) already held "
          "the ink" % (p["already_zero_in_stock"], p["canary_already_ink_in_stock"]),
          "                   %d outside the authored set, %d missing, %d wrong-value"
          % (p["outside_authored"], p["missing"], p["wrong_value"]),
          "                   %s" % p["claim"],
          "                   %.3f%% of the container; everything else is untouched and is its own "
          "control" % (100.0 * p["changed_bytes"] / d["bytes"]),
          "  staged           %s" % d["container"],
          "",
          "  ---- THE 4-WAY OUTCOME TABLE (built from MARKS, so it cannot disagree with the bytes) "
          "----",
          "  A?   B?   cell                      SCREEN CLASS                 role in the roll"]
    for row in d["outcome_table"]:
        L.append("  %-4s %-4s %-25s %-28s %s"
                 % ("YES" if row["A_applied"] else "no", "YES" if row["B_applied"] else "no",
                    row["cell"], row["screen"], row["role"]))
    L += ["",
          "  ---- THE BARREL ROLL, AND WHAT IT DOES TO EACH READ ----",
          "  From the s76 control cast (s76-read\\verify\\roll.reconstruction.json, model_ok true,",
          "  every frame tiling its destination exactly).  The marked page is first sampled on",
          "  effect frame %d." % d["first_sampled_frame"]]
    for col, r in sorted(d["roll"].items()):
        L.append("    column %s  f%s..%s  %s -> %s at %+d row/frame"
                 % (col, r["first_frame"], r["last_frame"], r["master"].split(".")[-1],
                    r["copy"].split(".")[-1], r["rows_per_frame"]))
    L += [
        "  A vertical roll TRANSLATES a horizontal grating and leaves a vertical one PIXEL-",
        "  IDENTICAL, so:",
        "    f%d..%-3d  THE CLEAN WINDOW.  All four cells hold their own marks; the full 4-way read"
        % (d["first_sampled_frame"], ROLL[COLUMN]["first_frame"] - 1),
        "               is available.  Both CLUT families draw here (67/67 meshes, 24,917 tris in",
        "               the marked cast -- s76-read\\adjudicate\\adj.preroll.json).",
        "    f%d..%-3d  column %d's copy has taken the master's PITCH.  Orientation unchanged."
        % (ROLL[COLUMN]["first_frame"], ROLL[COLUMN_HI]["first_frame"] - 1, COLUMN),
        "    f%d+      column %d's copy has taken the master's pitch too, and CRAWLS at %+d"
        % (ROLL[COLUMN_HI]["first_frame"], COLUMN_HI, ROLL[COLUMN_HI]["rows_per_frame"]),
        "               row/frame.  On column %d a CRAWLING coarse band is the LOWER cell and a"
        % COLUMN_HI,
        "               STATIC one is the UPPER -- so A stays readable there, by MOTION.",
        "  >>> ORIENTATION IS VALID IN EVERY FRAME.  PITCH IS VALID IN THE CLEAN WINDOW, and after",
        "  >>> it only on column %d and only via motion.  If the capture opens late, B is still" % COLUMN_HI,
        "  >>> answered and A may not be -- which is still a strict gain over cast 1.",
        "",
        "  ---- HOW A ZEROED TEXEL LOOKS, PER CLUT (derived; the read DIFFERS by family) ----"]
    for e in d["palette_read"]:
        if "error" in e:
            L.append("  clut %#06x  *** %s" % (e["clut"], e["error"]))
            continue
        L.append("  clut %#06x  entry0 %#06x rgba%r  %s"
                 % (e["clut"], e["entry0"], tuple(e["rgba"]), e["reads_as"]))
        L.append("              %d/256 entries are 0x0000, %d are 0x8000; entry-0 luma %d, dimmest "
                 "opaque entry %d" % (e["zeros"], e["stp_blacks"], e["entry0_luma"],
                                      e["min_opaque_luma"]))
    L += ["",
          "  ---- THE PREDICTED READ PER CELL, MEASURED ON THE MARKED BYTES ----",
          "  'near-black %' is the a19-class area fraction the cast-1 verdict was decided on (the",
          "  share of the cell below 35 % of its own mean luma); 'full-transp' is the number of",
          "  WHOLE rows / WHOLE columns that are transparent end to end -- the control family's",
          "  threshold-free statistic.",
          "  cell                      clut     opaque% (stock->marked)  near-black stock -> marked"
          "   full-transp rows/cols stock -> marked"]
    for cell in (UPPER_CELL, LOWER_CELL, UPPER_CELL_HI, LOWER_CELL_HI):
        for cw in sorted(d["cell_contrast"][cell]):
            s, m = d["cell_contrast"][cell][cw], d["cell_contrast_marked"][cell][cw]
            fr = d["full_extent_runs"][cell][cw]
            L.append("  %-25s %-8s %5.1f -> %5.1f   %6.2f%% -> %6.2f%% (%4.1fx)   %d/%d -> %d/%d"
                     % (cell, cw, s["opaque_pct"], m["opaque_pct"],
                        s["near_black_pct"], m["near_black_pct"],
                        (m["near_black_pct"] / s["near_black_pct"]) if s["near_black_pct"] else 0.0,
                        fr["stock"]["full_transparent_rows"], fr["stock"]["full_transparent_cols"],
                        fr["marked"]["full_transparent_rows"],
                        fr["marked"]["full_transparent_cols"]))
    L += ["",
          "  ---- THE RESIDENCY CANARY (NOT PART OF THE READ) ----",
          "  ink index %d (%s), derived as the brightest index OPAQUE under every CLUT the column's"
          % (ink["index"], ink["byte"]),
          "  readers use; %s"
          % ", ".join("%s -> rgba%r luma %d" % (cw, tuple(v["rgba"]), v["luma"])
                      for cw, v in sorted(ink["per_clut"].items())),
          "  One ~%d-texel block per cell at a per-cell corner, shaped to fit BETWEEN that cell's "
          "stripes" % CANARY_AREA,
          "  (a FINE cell leaves only 7-texel gaps, so its block is a bar, not a square) and "
          "disjoint from every stripe by construction.",
          "  IT PROVES RESIDENCY, NOT A HYPOTHESIS: a bright patch anywhere on an ef%03d scenery"
          % EFFECT,
          "  surface means the override was live in the process.  DO NOT score it as a mark; DO",
          "  report whether you saw one, because §9.3's honest limit 3 is exactly this.",
          "",
          "  ---- EVERY READER OF COLUMN %d (%d slots, all P=1 slot 0, all 8bpp, page_y 256) ----"
          % (d["column"], len(readers)),
          "  rec       clut    A      B      faces  v        u        cross: 640up 640lo 704up "
          "704lo"]
    for r in readers:
        L.append("  %#08x %#06x %#06x %#06x %5d  %3d..%-3d %3d..%-3d  %4d %4d %4d %4d  /%d"
                 % (r["rec"], r["clut"], r["A"], r["B"], r["faces"], r["vmin"], r["vmax"],
                    r["umin"], r["umax"],
                    r["crossed"][UPPER_CELL], r["crossed"][LOWER_CELL],
                    r["crossed"][UPPER_CELL_HI], r["crossed"][LOWER_CELL_HI], r["faces"]))
    f00, f80_0, f80_80 = fam(0, 0), fam(0x80, 0), fam(0x80, 0x80)
    L += ["",
          "  ---- THE THREE JOINT CLASSES, AND WHAT EACH ONE CONTROLS ----",
          "  (A=0x0000, B=0x0000)  %2d slots, clut %s" % (len(f00), ", ".join(sorted(
              {"%#06x" % r["clut"] for r in f00}))),
          "      THE FULL CONTROL.  Zero is the identity on BOTH axes, so these read %s under" % UPPER_CELL,
          "      every live reading of A and B.  They MUST show COARSE VERTICAL in the clean window",
          "      -- as HOLES, not as dark bands (their palette's entry 0 is the hardware cutout).",
          "      QUANTITATIVELY: %d of 128 columns of that cell are transparent end-to-end in stock,"
          % d["full_extent_runs"][UPPER_CELL]["0x3d40"]["stock"]["full_transparent_cols"],
          "      %d in the marked container -- a statistic with a stock floor of zero, which is what"
          % d["full_extent_runs"][UPPER_CELL]["0x3d40"]["marked"]["full_transparent_cols"],
          "      cast 1's control did not have.  (Cast 1's mark moved a 28.8%-transparent baseline",
          "      by ~1.9x; this one moves a count from %d to %d.)"
          % (d["full_extent_runs"][UPPER_CELL]["0x3d40"]["stock"]["full_transparent_cols"],
             d["full_extent_runs"][UPPER_CELL]["0x3d40"]["marked"]["full_transparent_cols"]),
          "      From f%d that cell is overwritten by the roll and shows the LOWER cell's FINE"
          % ROLL[COLUMN]["first_frame"],
          "      vertical stripes instead -- STILL VERTICAL.  A pitch change at exactly f%d on the"
          % ROLL[COLUMN]["first_frame"],
          "      control family is itself proof the marked page is what is on screen.",
          "  (A=0x0080, B=0x0000)  %2d slot%s, clut %s -- THE BRIGHT-FAMILY COLUMN CONTROL."
          % (len(f80_0), "" if len(f80_0) == 1 else "s",
             ", ".join(sorted({"%#06x" % r["clut"] for r in f80_0}))),
          "      %s.  B cannot move it, so it reads column %d whatever B does: it MUST show a"
          % (", ".join("%#x" % r["rec"] for r in f80_0), COLUMN),
          "      VERTICAL grating on the OPAQUE palette.  Cast 1 had no bright-family control at",
          "      all.  Its v runs to %d, so it samples both cells of the column and its PITCH is"
          % max(r["vmax"] for r in f80_0),
          "      mixed -- score its ORIENTATION only.",
          "  (A=0x0080, B=0x0080)  %2d slots, clut %s -- THE ANSWER-CARRYING CLASS."
          % (len(f80_80), ", ".join(sorted({"%#06x" % r["clut"] for r in f80_80}))),
          "      Everything the cast is for.  Under H_U these move to column %d and read" % COLUMN_HI,
          "      HORIZONTAL; if B is inert they stay VERTICAL.",
          "",
          "  ---- HOW TO SCORE THE VIDEO ----",
          "  #### DO NOT SCORE THIS BY COUNTING STRIPES ON SCREEN. ####  The marks are %d and %d"
          % (FINE[0], COARSE[0]),
          "  features ACROSS THE TEXTURE CELL and no surface maps that cell to one continuous",
          "  chart: on the headline disc the median face spans ~23 of the 128 texel lines, so a face",
          "  shows ~2 fine features or ~1 coarse one -- never 12 or 4.  THE READ IS:",
          "",
          "        which WAY do the lines run?      VERTICAL -> column %d   HORIZONTAL -> column %d"
          % (COLUMN, COLUMN_HI),
          "        how FINE are they?               FINE (many, thin) -> LOWER cell (A applied)",
          "                                         COARSE (few, ~3x thicker) -> UPPER cell",
          "        do they CRAWL?  (column %d only)  crawling -> the LOWER cell, from f%d"
          % (COLUMN_HI, ROLL[COLUMN_HI]["first_frame"]),
          "",
          "  All four marks carry EXACTLY THE SAME DUTY (48/128 = 37.5%), so 'it got darker' is not",
          "  a reading of anything.  At the derived on-screen scale (~3.1 px per texel from cast 1's",
          "  own disc extent) a FINE feature is ~12 px with a ~33 px period and a COARSE one ~37 px",
          "  with a ~100 px period -- both inside the range cast 1's own sweep could resolve, and",
          "  the coarse class survives blur that erases the fine one (build\\blurprice.derivation",
          "  .json).  SCORE AGAINST THE OFFLINE PANELS in ..\\predict-cast2\\.",
          "",
          "  Three questions, in order:",
          "  1. THE BIG FLAT SNOWFLAKE DISC (record 0x29dbc, %d faces, the only wide-flat surface"
          % next(r["faces"] for r in readers if r["rec"] == 0x29dbc),
          "     in the container).  A=0x0080, B=0x0080 -- the answer class.  Its ORIENTATION decides",
          "     B; its PITCH, in the clean window, decides A.",
          "  2. THE CONTROL FAMILY (the %d A=0x0000 readers).  COARSE VERTICAL HOLES.  If they show" % len(f00),
          "     nothing, the cast is NOT interpretable -- discard it, exactly as in cast 1.",
          "  3. THE WRAP READER %s.  VERTICAL, on the bright palette, in every frame."
          % ", ".join("%#x" % r["rec"] for r in f80_0),
          "     Orientation only; its pitch is mixed by construction.",
          "",
          "  ---- RECORD THREE THINGS SEPARATELY, PER SURFACE CLASS ----",
          "  (a) VISIBLE at all?   (b) does it carry a GRATING?   (c) which ORIENTATION, which PITCH?",
          "    visible + grating       -> score orientation, then pitch",
          "    NOT VISIBLE anywhere    -> BOUND-NEVER-DRAWN for that class.  A RESULT, not a failure.",
          "    VISIBLE but UNGRATED    -> *** NONE OF THE FOUR CELLS WAS SAMPLED. ***  Cast 1's third",
          "                               outcome, now with all four cells of the page marked, so",
          "                               G1 can no longer explain it: the remaining branches are a",
          "                               displaced upload, a cached decode, or a cells->VRAM",
          "                               mapping that is not what the container declares.  File it",
          "                               as its own finding; do not file it under any hypothesis.",
          "    ORIENTATION clear, PITCH ambiguous -> B is answered, A is not.  Report it that way;",
          "                               do NOT round it to a hypothesis.",
          "",
          "  WHAT EACH RESULT BUYS, STATED HONESTLY.  A HORIZONTAL read closes H_U positively and",
          "  makes R_UOFF live again (second-array-lead\\REPORT.md §3, whose closure rests on a claim",
          "  §9.3 shows is false under the texel convention).  A VERTICAL read on the answer class",
          "  refutes H_U on this container and leaves A alone to answer.  A and B are each perfectly",
          "  confounded with CLUT and blend mode here (20/20 and 7/7, 19/19 and 8/8), so the",
          "  reportable claim is always 'something in the second array moves the sampled CELL' and",
          "  never 'H_V confirmed' or 'H_U confirmed'.",
          ""]
    L += ["  " + n for n in d["notes"]]
    return L


# ============================================================================ MAIN
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cast", type=int, choices=(1, 2), default=2,
                    help="2 (default) = the G1 repair, all four cells of the page, orientation x "
                         "pitch.  1 = regenerate the container cast 1 actually ran, byte for byte; "
                         "it is kept so the instrument can still reproduce the artefact it was "
                         "read on")
    ap.add_argument("--from", dest="from_path", default=DEFAULT_CORPUS,
                    help="the STOCK container to mark (default the corpus ef%03d)" % EFFECT)
    ap.add_argument("--root", default=None,
                    help="staging root (LOCAL-ONLY).  Defaults to this CAST's own root -- the two "
                         "casts must never share one, because the ledger markers live in it")
    ap.add_argument("--cells", default=None, metavar="CELL[,CELL...]",
                    help="which of the page's cells to mark, each at its OWN pinned mark.  Default: "
                         "all of this cast's -- which is the cast.  Narrow it only for a surgical "
                         "follow-up; a cell left out stays stock and is its own control, and the "
                         "DISCRIMINATOR it carries is gone")
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

    # ⚠ `--cast 1` IS A REGRESSION TEST, NOT A DEPLOY MODE, and it may not write into the root that
    # holds the artefacts cast 1 was READ from.  Regenerating over them would silently replace the
    # PROTOCOL.txt and derivation the study cites -- the same class of loss as re-polishing a golden
    # oracle in place, and just as invisible afterwards.
    if a.cast == 1:
        if a.deploy:
            raise SystemExit("REFUSED: --cast 1 --deploy.  Cast 1 ran, was read, and was reverted; "
                             "re-deploying its two-mark container would spend a cast on the "
                             "question G1 already showed it cannot answer.  Deploy cast 2.")
        if a.root is None:
            raise SystemExit("REFUSED: --cast 1 needs an explicit --root.  Its default root (%s) "
                             "holds the container, PROTOCOL.txt and derivation the study's §9 read "
                             "was scored against; regenerating over them would replace the "
                             "artefact with a reproduction of it.  Point --root at a scratch dir "
                             "and compare the sha." % DEFAULT_ROOT[1])
    root = a.root or DEFAULT_ROOT[a.cast]
    cells = ([s.strip() for s in a.cells.split(",") if s.strip()] if a.cells
             else list(MARKS_BY_CAST[a.cast]))
    d = generate(a.from_path, root, cells, a.cast)
    lines = protocol(d)
    print("\n".join(lines))
    Path(root, "PROTOCOL.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n  protocol         %s" % Path(root, "PROTOCOL.txt"))
    print("  derivation       %s" % Path(root, "probe.derivation.json"))
    if a.cast == 1:
        ok = d["sha256"] == CAST1_CONTAINER_SHA256
        print("  cast-1 regen     %s  (%s the container cast 1 ran)"
              % (d["sha256"][:32], "MATCHES" if ok else "*** DIFFERS FROM ***"))
        if not ok:
            raise SystemExit("FAIL: --cast 1 no longer reproduces the container that was read.  "
                             "The instrument has drifted from its own artefact.")

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

    rootp = Path(root)
    pre = rootp / ("ef%03d" % EFFECT)
    absent_flag = rootp / "pre.ABSENT"
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

    rv = rootp / "revert_probe.py"
    # NO PATH IS EVER INTERPOLATED INTO THE DOCSTRING.  A Windows path inside a triple-quoted string
    # turns `...\Users\...` into an invalid `\U` escape and the emitted script does not even PARSE --
    # which the first rehearsal of the Odin deploy path caught, and which would have failed at the
    # one moment the revert matters (immediately before a kit deploy, THE LEDGER TRAP).  Paths go
    # through %r into CODE lines only, where the repr escapes the backslashes.
    rv.write_text(
        '"""Auto-generated REVERT for the ef%03d U1 SECOND-ARRAY probe (cast %d) -- stdlib only.\n\n'
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
        % (EFFECT, d["cast"], str(live), str(pre)), encoding="utf-8")
    # AND IT IS COMPILED HERE, not hoped over: a revert script that does not parse is worse than none.
    compile(rv.read_text(encoding="utf-8"), str(rv), "exec")
    (rootp / "deploy.ledger.json").write_text(
        json.dumps({"cast": d["cast"], "effect": EFFECT, "live": str(live), "mod_folder": str(mod),
                    "rehearsal": rehearsal, "pre": state,
                    "probe_sha256": d["sha256"], "readback_sha256": rb,
                    "stock_sha256": d["stock_sha256"], "revert": str(rv)}, indent=1),
        encoding="utf-8")
    print("  ledger           %s" % (rootp / "deploy.ledger.json"))
    print("  revert with      py %s" % rv)
    print("\n  *** REVERT THE PROBE BEFORE ANY KIT DEPLOY ON THIS ROOT.  SFX.Play re-reads the "
          "container on")
    print("      every cast, so the probe is live on the NEXT cast with no relaunch -- and so is "
          "its removal.")
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
