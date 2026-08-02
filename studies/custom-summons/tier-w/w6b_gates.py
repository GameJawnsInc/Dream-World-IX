r"""TIER W rung W6b-1 -- THE RUNG'S OWN GATE RUNNER.  `py w6b_gates.py` prints G1..G7 with PASS/FAIL.

W6b-1 opens the SCENERY texel surface: the per-VRAM-cell page map, the 4bpp nibble pack, the 15bpp
direct codec, the co-transform and name-every-column remedies, the program-VRAM DIRECTION law, and a
refusal set that covers 93 % of the surface by name.  These are the falsifiable forms of the claims
`SYNTHESIS.md` sec 4.3 lists, in its own order:

G1  THE FORMAT IDENTITY, PER CLASS (sec 2.1-2.3).  8bpp and 4bpp round-trip byte-identical over
    EVERY writer cell in the 372-container corpus, and over every cell x binding view at that
    binding's own depth and CLUT; 15bpp round-trips EXHAUSTIVELY over all 65,536 halfwords plus every
    real writer-backed cell; and the NIBBLE ORDER is re-measured with its own discriminator (a
    within-row-invariant vertical control) against the cast-proven 8bpp answer.
G2  THE CAST ARTIFACT (sec 5).  The rung's cast vehicle -- ef211 `(704,256)`, the Phoenix fire field
    -- built from the corpus: the no-op delta is 0, every changed byte is inside that cell's own
    0x4000 span, the container length and its strict re-parse are unchanged, the region invariant and
    the page-cell derivation both hold, and the kit's own self-check passes whole.
G3  THE REGION PARTITION, and its NEW id-0 half (sec 4.2, and sec 6 Q7's cheapest experiment).  The
    texel partition gates the id-0 page-block header + rect table and licenses the pixel stream; the
    CLUT partition does the opposite; and the fail-safe is proven NON-VACUOUS -- a synthetically
    perturbed rect table is CAUGHT by name while a write inside the pixel stream is LICENSED.
G4  THE REFUSAL MATRIX (sec 3.2) -- every refusal this rung establishes, each carrying its own
    measurement, plus the REMEDIES that make three of them lawful, plus sec 4.4's MOVED PINS.
G5  CLUT-LANE BYTE COMPATIBILITY.  A scenery TEXEL build and a scenery CLUT recolour of the SAME
    container touch DISJOINT byte sets -- the composition proof the two levers already have on
    creature pages, re-run on the scenery surface where they share a container and a palette.
G6  THE CORPUS CENSUS -- the numbers this rung is allowed to quote, re-measured every run, plus
    **THE RE-DERIVATION PIN**: the program-VRAM id lists are the one corpus constant `repaint.py`
    carries, so this gate re-walks all 385 id-3 program images with the study's own const-folding
    walker and compares the sets it derives against the shipped ones, including the ef435 REFUTATION.
G7  PROVENANCE: a byte-literal scan of every committable file this rung adds, against all 372 corpus
    containers; the SE-derived lane dossiers all sit outside the checkout.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format ONLY -- no install read, NO deploy, no
install write, no git commit.  Every number is measured in the gate body.  G1/G6 share ONE corpus
pass (about two minutes); nothing else is slow.
"""
from __future__ import annotations

import ast
import io
import os
import struct
import sys
import tempfile
from statistics import mean

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402

CORPUS = W.SCRATCH_CORPUS
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # <repo>

# --------------------------------------------------------------------------- THE CAST VEHICLE
#: ef211 (Phoenix), VRAM cell (704, 256) -- the full-screen roiling fire field.  Chosen because its
#: upload path is ALREADY CAST-PROVEN live (W5's magenta probe: "magenta showed up in the flames"),
#: which is the one property no other candidate has.  Every field below is RE-DERIVED by G2; they are
#: written down so a drift is a visible diff rather than a silently different verdict.
CAST_EF = 211
CAST_CELL = (704, 256)
CAST_NAME = "cell.s0.x704_y256"
CAST_SPAN = (0x11678, 0x15678)             # the cell's own 0x4000 file span
CAST_BPP = 8
CAST_COVER = 8128                          # halfwords of this 8,192-halfword cell that a model reads

#: sec 3.3's cast 2 -- the same container, the same bench row, and the cell the per-cell map exists
#: for: `(576, 384)` is the LOWER half of a tall rect whose UPPER half is a two-palette refusal.
CAST2_NAME = "cell.s0.x576_y384"

#: THE SHIPPED DELIVERABLE, PINNED (V1 F3).  `cast_build()` below proves the LANE with its own
#: synthetic stamp; these two pins prove the FILES the owner actually runs -- the committed
#: generator's PNG and the container `phoenix_field.toml` builds -- regenerated from the corpus
#: every run and compared by hash.  Hashes, not data; a drift in `RING_R`, the ink tie-break or the
#: cover expansion turns G2 red instead of shipping a different artifact under a green board.
PHOENIX_STAMP_PNG_SHA256 = "3444c97833f946c688dac8102e04297ee317d182626e7da3d477a5284104dc17"
PHOENIX_STAGED_SHA256 = "d09f8c78e1d412c6072373a8ae30b6e9921ed410609491ad5bcdb149abd0d5a7"

# --------------------------------------------------------------------------- THE CENSUS PINS
#: The numbers sec 4.3 G6 says this rung may quote.  Every one of them is RE-MEASURED in `census()`
#: and compared here; a pin that only matched a prose table would be the thing this house forbids.
PIN = {
    "page_cells": 2665,          # 2,572 scenery cells + 93 id-4 creature pages
    "writer_records": 2648,      # a co-transform cell is several writer records
    "creature_pages": 93,
    "scenery_cells": 2572,
    "lawful_rect": 56,           # A1's predicate: addressable through the RECT view
    "lawful_page_safe": 50,      # ... of which page-scope-safe
    "lawful_model_scope": 6,     # ... of which the reader spills out of the cell
    "lower_half_lawful": 20,     # class B2: otherwise-lawful, reachable ONLY via the per-cell map
    "unaddressable": 1179,       # cells the (tag, x) rect key can never name
    "depth_unknown": 2385,
    "co_transform": 34,
    "co_expressible": 16,
    "co_two_depth": 8,
    "co_unread": 10,
    "co_pairs": 156,
    "co_identical": 0,
    "dual_depth": 17,
    "multi_palette": 42,         # class E2, A1's predicate: >1 palette KEY, "no CLUT" counting as one
    "multi_clut_cell": 38,       # ... counting only DECLARED CLUT cells (the kit's own predicate)
    "class_c": 25,               # ... of which single-depth -- the display-palette rule's own set
    "shared_read": 93,
    "spill_bindings": 58,
    "spill_8bpp": 41,
    "spill_15bpp": 17,
    "spill_4bpp": 0,
    "spill_uv_exact": 70,        # UV-exact AND written -- the name-every-column gate's set
    "spill_unwritten": 8,        # UV-exact but nothing uploads them (all ef390)
    #: A1's rect-conservative superset is 83 in the dossier's own probe.  It is NOT pinned here,
    #: because it is CONSTRUCTION-DEPENDENT rather than a fact about what a model reads: this gate's
    #: own rect expansion (every stacked cell of every writer rect of a spill-touched cell) measures
    #: 94.  The load-bearing property survives either construction and IS pinned -- the UV-exact set
    #: is a strict SUBSET with zero contradictions -- and the gate uses the UV-exact one, because
    #: naming a cell the model does not read would be a false obligation.
    "program_write_cells": 175,
    "program_read_cells": 113,
    "program_cells_by_name": 3,
    "direct15_lawful": 4,        # + 1 more once the per-cell map lands (ef429 x448_y384)
    "views_4": 125, "views_8": 298, "views_15": 26,
}

#: THE PROGRAM-VRAM RE-DERIVATION, expressed as the walker's OWN four op families so G6 can state
#: where each shipped id came from rather than restating the shipped list back to itself.
WALK_LOADIMAGE = frozenset((149, 435))
WALK_MOVEIMAGE = frozenset((1, 142, 144, 149, 274))
WALK_STOREIMAGE = frozenset((7, 72, 149, 211, 214, 276, 390))
WALK_SEQ07 = frozenset((87, 125, 134, 143, 223, 224, 308, 381, 415))
WALK_TEXANIM_ARM = frozenset((38,))
#: the six the reachability walk never reached and the linear HLE-call-shape scan found, all
#: StoreImage -- a READ, so they DISCLOSE.  Re-derived by the same scan in G6.
LINEAR_ONLY_STORE = frozenset((151, 152, 225, 445, 460, 510))

#: the committable files THIS rung adds or rewrites.  The KIT modules are scanned as well as the
#: study's own, for w6_gates' reason: the engine is where stock texels are read and rewritten, and a
#: scan covering only the study would report green over the half of the rung that touches bytes.
COMMITTABLE = ("w6b_gates.py", "W6b-SCENERY.md", "W6-TEXEL.md",
               "ff9mapkit/ff9mapkit/summons/repaint.py",
               "ff9mapkit/ff9mapkit/summons/reskin.py",
               "ff9mapkit/ff9mapkit/summons/texture.py",
               "ff9mapkit/tests/test_summon_repaint.py",
               "ff9mapkit/tests/test_summon_reskin.py")

#: the CAST lane's own committable files -- scanned when they are in the tree, reported as absent when
#: they are not.  OPTIONAL rather than required, for w7_gates' reason: the cast artifacts land in a
#: sibling lane, and a gate that FAILED on their absence would be asserting another agent's schedule
#: rather than provenance.  Scanned at all because a generator that stamps art onto a decoded stock
#: page is exactly where a run of stock bytes would hide.
COMMITTABLE_CAST = ("phoenix_field_stamp.py", "phoenix_field.toml")

#: the SE-derived recon dossiers this rung was written from.  Never in the checkout, by construction.
DOSSIERS = (r"C:\gd\SCRATCH\summon-format\texel-w6b\SYNTHESIS.md",
            r"C:\gd\SCRATCH\summon-format\texel-w6b\census\A1-SCENERY-SURFACE-CENSUS.md",
            r"C:\gd\SCRATCH\summon-format\texel-w6b\formats\A2-FORMATS.md",
            r"C:\gd\SCRATCH\summon-format\texel-w6b\prior\A3-PRIOR.md")

RESULTS = []
_TMP = None


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def _have_corpus() -> bool:
    return bool(W.corpus_paths(CORPUS))


def _load(effect: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % effect), "rb") as fh:
        return fh.read()


def _tmp() -> str:
    global _TMP
    if _TMP is None:
        _TMP = tempfile.mkdtemp(prefix="w6bgates-")
    return _TMP


def _refuses(fn, *a, **kw):
    """``(fired, message)`` -- did this raise one of the LANE's OWN error classes, and what did it say?

    A refusal that raised the wrong exception type is not a refusal: it is a crash that happened to
    stop the build, and it stops being one the day the call site grows a ``try`` (w6_gates' own rule).
    """
    try:
        fn(*a, **kw)
        return False, ""
    except (RP.RepaintError, RS.ReskinError) as e:
        return True, str(e)
    except Exception as e:                                       # pragma: no cover - a real defect
        return False, "*** %s (not a lane error): %s" % (type(e).__name__, e)


def _texel_spec(effect: int, rows) -> dict:
    return {"reskin": {"effect": effect, "allow_unguarded": True, "texel": list(rows)}}


def _row(name: str, src: str, **extra) -> dict:
    d = {"name": name, "source": src, "enabled": True}
    d.update(extra)
    return d


# --------------------------------------------------------------------------- the shared corpus pass
_CENSUS = None


def _rates(px, w: int, h: int):
    """``(H, V)`` -- horizontal and vertical neighbour DISAGREEMENT rates.

    ``V`` is invariant under any within-row permutation, so it is a FREE CONTROL for ``H``: the nibble
    order is exactly a within-row permutation, which is what makes this a discriminator rather than a
    preference.
    """
    hn = hd = vn = vd = 0
    for y in range(h):
        row = px[y * w:(y + 1) * w]
        hn += w - 1
        hd += sum(1 for i in range(w - 1) if row[i] != row[i + 1])
    for y in range(h - 1):
        a, b = px[y * w:(y + 1) * w], px[(y + 1) * w:(y + 2) * w]
        vn += w
        vd += sum(1 for i in range(w) if a[i] != b[i])
    return (hd / max(1, hn), vd / max(1, vn))


def _unpack4_swapped(raw: bytes) -> bytes:
    out = bytearray(2 * len(raw))
    out[0::2] = bytes(b >> 4 for b in raw)
    out[1::2] = bytes(b & 0x0F for b in raw)
    return bytes(out)


def _byteswap16(raw: bytes) -> bytes:
    out = bytearray(raw)
    out[0::2], out[1::2] = raw[1::2], raw[0::2]
    return bytes(out)


def census() -> dict:
    """ONE pass over all 372 containers, feeding G1 and G6.

    Cached for ``w6_gates.emblem_build``'s reason: these are real derivations over real bytes, and two
    gates that each re-ran them could in principle disagree, which is a report nobody could trust.
    """
    global _CENSUS
    if _CENSUS is not None:
        return _CENSUS
    RAMP8 = tuple(range(1, 257))                       # a 256-entry display key, distinct words
    RAMP4 = tuple(range(1, 17))
    d = dict(containers=0, writer_records=0, scenery_cells=0, creature_pages=0,
             rt8=0, rt8_fail=[], rt4=0, rt4_fail=[], depth_unknown=0, lower_half_records=0,
             unaddressable=set(), lawful_rect=set(), lawful_cell=set(), page_safe=set(),
             model_scope=set(), co_cells=0, co_pairs=0, co_identical=0, co_expressible=0,
             co_two_depth=0, co_unread=0, dual_depth=0, multi_palette=0, multi_clut_cell=0,
             class_c=0, shared_read=0,
             spill_bind={4: 0, 8: 0, 15: 0}, spill_uv=set(), spill_unwritten=set(), spill_rect=set(),
             spill_cross_writer=0, spill_unwritten_bindings=0,
             views={4: 0, 8: 0, 15: 0}, prog_write=set(), prog_read=set(), prog_named=set(),
             d15_lawful=[], d15_cells=[], nibble=[], control=[], dual_by_ef={}, exposed=0,
             creatureless_exposed=0)
    for path in W.corpus_paths(CORPUS):
        ef = int(os.path.basename(path)[2:5])
        with open(path, "rb") as fh:
            blob = fh.read()
        d["containers"] += 1
        cells = RS.page_cells(blob)
        by_cell = {}
        for c in cells.values():
            by_cell.setdefault(c.cell, []).append(c)
            if c.split and c.split_index > 0:
                d["lower_half_records"] += 1
                d["unaddressable"].add((ef, c.cell))
        d["writer_records"] += len(cells)
        d["scenery_cells"] += len(by_cell)
        creature = RP.creature_texel_pages(blob)
        d["creature_pages"] += len(creature)

        # ---- G1 pass A: EVERY writer record round-trips at BOTH indexed depths
        for c in sorted(cells.values(), key=lambda q: q.off):
            raw = blob[c.off:c.off + c.nbytes]
            back8 = RP._read_indices(io.BytesIO(RP.encode_indexed_png(raw, RAMP8, 128, 128)),
                                     "(gate)", 128, 128, 256)
            d["rt8"] += 1
            if back8 != raw:                                     # pragma: no cover - a real defect
                d["rt8_fail"].append("ef%03d %s" % (ef, c.name))
            idx = RP.unpack4(raw)
            back4 = RP.pack4(RP._read_indices(
                io.BytesIO(RP.encode_indexed_png(idx, RAMP4, 256, 128)), "(gate)", 256, 128, 16))
            d["rt4"] += 1
            if back4 != raw:                                     # pragma: no cover - a real defect
                d["rt4_fail"].append("ef%03d %s" % (ef, c.name))

        # ---- the hazard census, off the kit's own derivation
        pages, refused = RP.scenery_surface(blob, ef)
        if pages:
            d["exposed"] += 1
            if EC.creature_package(blob) is None:
                d["creatureless_exposed"] += 1
        d["depth_unknown"] += len({r.cell for r in refused if r.klass == "depth-unknown"})
        models = RP.bound_models(blob)
        readers = RP.cell_readers(blob, models)
        written = set(by_cell)
        for m in models:
            if not m.spills:
                continue
            d["spill_bind"][m.bpp] = d["spill_bind"].get(m.bpp, 0) + 1
            for c in m.cover:
                (d["spill_uv"] if c in written else d["spill_unwritten"]).add((ef, c))
            if any(c not in written for c in m.cover):
                d["spill_unwritten_bindings"] += 1
        for cell, ws in by_cell.items():
            if len(ws) > 1:
                d["co_cells"] += 1
                for i in range(len(ws)):
                    for j in range(i + 1, len(ws)):
                        d["co_pairs"] += 1
                        if blob[ws[i].off:ws[i].off + ws[i].nbytes] == \
                                blob[ws[j].off:ws[j].off + ws[j].nbytes]:
                            d["co_identical"] += 1
                if not readers.get(cell):
                    d["co_unread"] += 1
        per = {}
        for p in pages:
            per.setdefault(p.cell, p)
        for cell, p in sorted(per.items()):
            hz = p.hazards
            for r in hz.readers:
                d["views"][r.bpp] = d["views"].get(r.bpp, 0) + 1
            if hz.two_depths:
                d["dual_depth"] += 1
                d["dual_by_ef"][ef] = d["dual_by_ef"].get(ef, 0) + 1
            # TWO multi-palette predicates, because A1 and the kit count different things and BOTH
            # are right.  A1 counts distinct palette KEYS with "no CLUT at all" (a 15bpp binder)
            # counting as one of them -- 42 cells.  The kit's `palette_cells` counts only DECLARED
            # CLUT cells -- 38 -- because the display-palette rule has to name an alternate VIEW, and
            # a 15bpp binder has no key to render one in.  The 4-cell delta is exactly the cells that
            # are ALSO same-bytes-two-depths, which refuse earlier anyway.
            keys = {r.clut_cell for r in hz.readers}
            if len(keys) > 1:
                d["multi_palette"] += 1
            if len(hz.palette_cells) > 1:
                d["multi_clut_cell"] += 1
                if not hz.two_depths:
                    d["class_c"] += 1
            if hz.shared_read:
                d["shared_read"] += 1
            if hz.co_transform:
                d["co_two_depth" if hz.two_depths else "co_expressible"] += 1
            if hz.spill_in or hz.spill_out:
                # this gate's OWN rect-conservative construction: every stacked cell of every writer
                # rect that uploads a spill-touched cell.  Reported beside the UV-exact set so the
                # superset's construction-dependence is visible rather than argued about.
                for w in by_cell[cell]:
                    for y in range(w.rect_y, w.rect_y + w.rect_h, RS.PAGE_CELL_LINES):
                        d["spill_rect"].add((ef, (w.x, y)))
            # THE LAWFUL PREDICATE, in its two forms.  A1's `lawful` is addressability through the
            # RECT view, so it excludes every lower half by construction; the per-cell map is exactly
            # what makes those 20 reachable, and the difference between the two sets IS class B2.
            if (len(hz.writers) == 1 and not hz.two_depths and not hz.multi_palette
                    and not hz.spill_in and not hz.shared_read
                    and hz.program not in ("write", "unknown") and not hz.program_cell):
                d["lawful_cell"].add((ef, cell))
                if not hz.lower_half:
                    d["lawful_rect"].add((ef, cell))
                    (d["model_scope"] if hz.spill_out else d["page_safe"]).add((ef, cell))
                if p.bpp == 15:
                    d["d15_lawful"].append((ef, cell, bool(hz.spill_out), hz.lower_half))
            if p.bpp == 15:
                d["d15_cells"].append((ef, cell))
        cls, _why = RP.program_class(ef)
        if cls == "write":
            d["prog_write"] |= {(ef, c) for c in by_cell}
        elif cls == "read":
            d["prog_read"] |= {(ef, c) for c in by_cell}
        hard = RP.MOVEIMAGE_HARD_CELLS.get(ef)
        if hard is not None and hard in by_cell:
            d["prog_named"].add((ef, hard))

        # ---- THE NIBBLE-ORDER INSTRUMENT (A2's own population: one writer, >= 1 4bpp reader)
        for cell, ws in sorted(by_cell.items()):
            if len(ws) != 1 or ws[0].nbytes != RS.PAGE_CELL_BYTES:
                continue
            if not any(m.bpp == 4 for m in readers.get(cell, [])):
                continue
            raw = blob[ws[0].off:ws[0].off + ws[0].nbytes]
            hc, v = _rates(RP.unpack4(raw), 256, 128)
            hs, _ = _rates(_unpack4_swapped(raw), 256, 128)
            d["nibble"].append((ef, cell, hc, hs, v))
        for p in creature:                                        # the 8bpp CONTROL, cast-proven
            raw = blob[p.page_offset:p.page_offset + p.page_bytes]
            hc, v = _rates(raw, 128, 128)
            hs, _ = _rates(_byteswap16(raw), 128, 128)
            d["control"].append((ef, p.name, hc, hs, v))
    _CENSUS = d
    return d


# --------------------------------------------------------------------------- G1
def g1_format_identity():
    if not _have_corpus():
        return gate("G1 the format identity", False, "no extracted corpus at %s" % CORPUS)
    c = census()
    lines, ok = [], True

    lines.append("8bpp  indexed round trip over EVERY writer cell: %d/%d byte-identical "
                 "(%d distinct cells, %d writer records -- a co-transform cell is several records)"
                 % (c["rt8"] - len(c["rt8_fail"]), c["rt8"], c["scenery_cells"],
                    c["writer_records"]))
    lines.append("4bpp  unpack4 -> 1 byte/texel PNG -> pack4, same cells: %d/%d byte-identical"
                 % (c["rt4"] - len(c["rt4_fail"]), c["rt4"]))
    ok = ok and not c["rt8_fail"] and not c["rt4_fail"]
    ok = ok and c["rt8"] == c["rt4"] == PIN["writer_records"]
    for f in (c["rt8_fail"] + c["rt4_fail"])[:6]:
        lines.append("   *** DRIFT %s" % f)
    lines.append("cell x binding VIEWS, at each binding's OWN depth: 4bpp %d, 8bpp %d, 15bpp %d "
                 "(sec 2.1-2.3's pass B: %d / %d / %d)"
                 % (c["views"][4], c["views"][8], c["views"][15],
                    PIN["views_4"], PIN["views_8"], PIN["views_15"]))
    ok = ok and (c["views"][4], c["views"][8], c["views"][15]) == \
        (PIN["views_4"], PIN["views_8"], PIN["views_15"])

    # ---- 15bpp: EXHAUSTIVE, not by corpus.  65,536 halfwords is the whole domain.
    bad = miss = sidecar = 0
    for w in range(0x10000):
        r, g, b, s = KT.direct15_split(w)
        if KT.direct15_word(r, g, b, s) != w:                    # pragma: no cover - a real defect
            bad += 1
        if ((r, g, b, s) == (0, 0, 0, 0)) != (w == 0):
            miss += 1
        if s != ((w >> 15) & 1):                                 # pragma: no cover
            sidecar += 1
    lines.append("15bpp word -> (rgb8, stp) -> word, EXHAUSTIVE: %d/65536 identical; "
                 "`alpha == 0 <=> word == 0x0000` violations %d; `sidecar == bit15` violations %d"
                 % (0x10000 - bad, miss, sidecar))
    ok = ok and not bad and not miss and not sidecar

    n15 = ident15 = 0
    td = _tmp()
    for ef, cell in c["d15_cells"]:
        blob = _load(ef)
        page = next((p for p in RP.scenery_texel_pages(blob, ef) if p.cell == cell), None)
        if page is None or page.bpp != 15:                       # pragma: no cover - census drift
            continue
        raw = blob[page.page_offset:page.page_offset + page.page_bytes]
        dst = os.path.join(td, "d15_%03d_%d_%d.png" % (ef, cell[0], cell[1]))
        RP.write_direct_png(raw, page.w, page.h, dst)
        n15 += 1
        ident15 += 1 if RP.read_direct_png(dst, page.w, page.h) == raw else 0
    lines.append("15bpp REAL writer-backed cells, RGBA + STP sidecar -> raw: %d/%d byte-identical "
                 "(%d cell x binding views)" % (ident15, n15, c["views"][15]))
    ok = ok and n15 and ident15 == n15

    # ---- THE NIBBLE ORDER.  Byte identity is BLIND to it (pack4(unpack4(b)) == b under either
    # convention), so this is the discriminator, calibrated first on the answer the cast already knows.
    ctl = c["control"]
    ctl_win = sum(1 for r in ctl if r[2] < r[3])
    lines.append("nibble-order CALIBRATION on the cast-proven 8bpp answer (byte i = texel i vs the "
                 "halfword byte-swap): %d/%d creature pages agree   H %.4f vs %.4f, V %.4f"
                 % (ctl_win, len(ctl), mean(r[2] for r in ctl), mean(r[3] for r in ctl),
                    mean(r[4] for r in ctl)))
    ok = ok and len(ctl) == PIN["creature_pages"] and ctl_win == len(ctl)
    nb = c["nibble"]
    win = sum(1 for r in nb if r[2] < r[3])
    sig = [r for r in nb if abs(r[2] - r[3]) > 0.003]
    sig_win = sum(1 for r in sig if r[2] < r[3])
    lines.append("the 4bpp QUESTION (low nibble = even u): %d/%d cells agree; with a signal floor of "
                 "|dH| > 0.003, %d/%d -- NO dissent   H %.4f vs %.4f, V %.4f (mean winning margin "
                 "%.4f)" % (win, len(nb), sig_win, len(sig), mean(r[2] for r in nb),
                            mean(r[3] for r in nb), mean(r[4] for r in nb),
                            mean(abs(r[2] - r[3]) for r in sig)))
    ok = ok and len(nb) == 48 and win == 44 and len(sig) == 36 and sig_win == 36
    for r in nb:
        if r[2] >= r[3]:
            lines.append("   dissenter ef%03d %s  H_can %.5f  H_swp %.5f  V %.4f -- separates by "
                         "%.5f, below the floor: DIAGNOSED, not averaged away"
                         % (r[0], str(r[1]), r[2], r[3], r[4], abs(r[2] - r[3])))
    lines.append("the load-bearing argument is not statistical: the PSX rule is ONE rule at every "
                 "depth -- lower-order bits hold the lower u -- and its 8bpp instance is cast-proven "
                 "on screen (W6a's emblem read correctly with byte i = texel i)")
    return gate("G1 the format identity per class (8bpp / 4bpp / 15bpp exhaustive / nibble order)",
                ok, *lines)


# --------------------------------------------------------------------------- G2
_CAST = None


def cast_build():
    """The rung's cast artifact, built once from the corpus: a stamp on ef211's fire field.

    Built HERE rather than loaded from a spec file so the gate proves the LANE, not one agent's toml:
    the shape is the cast's (a hard-edged figure stock fire never forms), the ink is chosen the way
    sec 5.3 requires -- the live palette entry with the HIGHEST luminance, measured at build time,
    never picked by eye -- and everything else is the kit's own path.
    """
    global _CAST
    if _CAST is not None:
        return _CAST
    blob = _load(CAST_EF)
    page = RP.texel_page(blob, CAST_NAME, CAST_EF)
    words = RP.palette_words(blob, page)
    zeros = set(RP.transparent_indices(words))
    stock = blob[page.page_offset:page.page_offset + page.page_bytes]
    td = _tmp()

    def _lum(i):
        r, g, b, _a = KT.bgr555_rgba(words[i])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    live = [i for i in range(len(words)) if i not in zeros]
    ink = max(live, key=_lum)
    # the no-op first: the identity edit must move ZERO bytes, or nothing below means anything
    noop = os.path.join(td, "cast_noop.png")
    RP.write_indexed_png(stock, words, page.w, page.h, noop)
    b_noop = RP.build(_texel_spec(CAST_EF, [_row(CAST_NAME, noop, expect_bpp=CAST_BPP,
                                                 expect_cell=list(CAST_CELL))]), td, blob=blob)
    # the stamp: a thick stroked ring cut into three sectors by radial spokes -- W6a's precedent shape
    px = bytearray(stock)
    cx = cy = page.w // 2
    import math
    for y in range(page.h):
        for x in range(page.w):
            dx, dy = x - cx, y - cy
            rr = math.hypot(dx, dy)
            ang = math.degrees(math.atan2(dy, dx)) % 120.0
            if 40.0 <= rr <= 48.0 or (rr < 48.0 and ang < 6.0):
                px[y * page.w + x] = ink
    art = os.path.join(td, "cast_ring.png")
    RP.write_indexed_png(bytes(px), words, page.w, page.h, art)
    # NO `acknowledge_cutout_reshape`, deliberately.  sec 5.3 ANTICIPATED the cutout gate firing on a
    # solid stamp over a flame texture's holes; at this radius it does not, and the honest way to say
    # so is to build with nothing acknowledged and let the gate refuse if a texel ever crosses.
    b = RP.build(_texel_spec(CAST_EF, [_row(CAST_NAME, art, expect_bpp=CAST_BPP,
                                            expect_cell=list(CAST_CELL))]), td, blob=blob)
    b.check = RP.self_check(b)
    _CAST = {"blob": blob, "page": page, "ink": ink, "noop": b_noop, "build": b,
             "lum": _lum(ink), "live": len(live)}
    return _CAST


def g2_cast_artifact():
    if not _have_corpus():
        return gate("G2 the cast artifact", False, "no extracted corpus at %s" % CORPUS)
    try:
        d = cast_build()
    except Exception as e:                                       # pragma: no cover - a real defect
        return gate("G2 the cast artifact", False, "the build FAILED: %s: %s" % (type(e).__name__, e))
    lines, ok = [], True
    page, b, noop = d["page"], d["build"], d["noop"]
    lines.append("vehicle ef%03d %s -- writer %s @%#x, %d B; reader GEOM %#x %dbpp CLUT %s = %s"
                 % (CAST_EF, page.name, page.hazards.writers[0].tag, page.page_offset,
                    page.page_bytes, page.hazards.readers[0].geom, page.bpp,
                    str(page.hazards.readers[0].clut_cell), page.palette_name))
    lines.append("its derived span %#x..%#x  %s the stated cast span %#x..%#x; depth %d %s; "
                 "cover %d of %d halfwords"
                 % (page.page_offset, page.page_offset + page.page_bytes,
                    "MATCHES" if (page.page_offset, page.page_offset + page.page_bytes) == CAST_SPAN
                    else "*** DIFFERS FROM ***", CAST_SPAN[0], CAST_SPAN[1], page.bpp,
                    "as stated" if page.bpp == CAST_BPP else "*** DIFFERS ***",
                    page.hazards.covered_halfwords, RS.PAGE_CELL_W * RP.CELL_LINES))
    ok = ok and (page.page_offset, page.page_offset + page.page_bytes) == CAST_SPAN
    ok = ok and page.bpp == CAST_BPP and page.hazards.covered_halfwords == CAST_COVER
    lines.append("hazards on this cell: %s -- co-transform %s, dual-depth %s, multi-palette %s, "
                 "shared-read %s, spill %s, lower-half %s"
                 % (page.hazards.names or "(none)", page.hazards.co_transform,
                    page.hazards.two_depths, page.hazards.multi_palette, page.hazards.shared_read,
                    page.hazards.spills, page.hazards.lower_half))
    ok = ok and not page.hazards.names
    lines.append("the program verdict: %s" % (b.enabled[0].hazard_notes[0] if
                                              b.enabled[0].hazard_notes else "(none)"))
    ok = ok and any("program-VRAM READ" in n for n in b.enabled[0].hazard_notes)

    lines.append("THE NO-OP: the identity edit moves %d byte(s)" % len(noop.enabled[0].changed))
    ok = ok and not noop.enabled[0].changed and noop.patched == noop.orig

    t = b.enabled[0]
    inside = all(CAST_SPAN[0] <= page.page_offset + o < CAST_SPAN[1] for o in t.changed)
    lines.append("THE STAMP: ink index %d (the LIVE entry of %d with the highest luminance, %.1f -- "
                 "measured at build time, never chosen by eye); %d byte(s) moved, all inside the "
                 "cell's own span: %s" % (d["ink"], d["live"], d["lum"], len(t.changed), inside))
    ok = ok and inside and len(t.changed) > 0
    lines.append("   live/dead split %d live, %d outside any model's UV cover; cutout punch %d / "
                 "fill %d -- NOTHING was acknowledged away, so the silhouette is provably untouched.  "
                 "(sec 5.3 anticipated a FILL here; at this radius the ring lands entirely on live "
                 "texels, which is a measurement the cast's own stamp must re-take, not inherit.)"
                 % (t.live_changed, t.dead_changed, t.cutout_punch, t.cutout_fill))
    ok = ok and not t.ack_cutout and not t.cutout_flips and t.round_trip
    lines.append("container length %d -> %d, strict re-parse: %s" % (
        len(b.orig), len(b.patched), "OK" if EC.parse_header(b.patched, strict=True) else "?"))
    lines.append("the invariants, at the BUILD call site: %s" % b.region_invariant)
    ok = ok and len(b.orig) == len(b.patched)
    ok = ok and "unchanged" in b.region_invariant and "re-derive identically" in b.region_invariant
    outside = [o for o in range(len(b.orig)) if b.orig[o] != b.patched[o]
               and not (CAST_SPAN[0] <= o < CAST_SPAN[1])]
    lines.append("bytes changed ANYWHERE outside %#x..%#x: %d" % (CAST_SPAN[0], CAST_SPAN[1],
                                                                  len(outside)))
    ok = ok and not outside
    npass = sum(1 for g in b.check.gates if g.ok)
    lines.append("the kit's own self-check: %d/%d gates" % (npass, len(b.check.gates)))
    for g in b.check.gates:
        if not g.ok:
            lines.append("   [!!] %s -- %s" % (g.name, g.detail))
    ok = ok and b.check.ok
    lines.append("sha256 stock %s -> staged %s" % (b.sha_stock, b.sha_out))
    lines.append("CAST 2 (%s) is the SAME container, the SAME bench row: %s"
                 % (CAST2_NAME, "resolvable today" if any(
                     p.name == CAST2_NAME for p in RP.scenery_texel_pages(d["blob"], CAST_EF))
                     else "*** NOT RESOLVABLE ***"))
    ok = ok and any(p.name == CAST2_NAME for p in RP.scenery_texel_pages(d["blob"], CAST_EF))

    # THE SHIPPED DELIVERABLE (V1 F3).  Everything above proves the lane on a stamp this gate drew
    # itself; the owner will run `phoenix_field_stamp.py` + `phoenix_field.toml`, so THOSE are
    # regenerated from the corpus here and pinned by hash.
    import hashlib
    import subprocess
    import tomllib
    sroot = os.path.join(_tmp(), "shipped")
    r = subprocess.run([sys.executable, os.path.join(_HERE, "phoenix_field_stamp.py"),
                        "--from", os.path.join(CORPUS, "ef%03d.bytes" % CAST_EF),
                        "--root", sroot, "--no-export"],
                       capture_output=True, text=True, timeout=600)
    png = os.path.join(sroot, "art", "%s.png" % CAST_NAME)
    gen_ok = r.returncode == 0 and os.path.exists(png)
    sha_png = hashlib.sha256(open(png, "rb").read()).hexdigest() if gen_ok else "(generator failed)"
    lines.append("THE SHIPPED GENERATOR: exit %d, PNG sha %s -- %s" % (
        r.returncode, sha_png[:16],
        "PINNED" if sha_png == PHOENIX_STAMP_PNG_SHA256 else "*** DRIFTED from the pin ***"))
    ok = ok and gen_ok and sha_png == PHOENIX_STAMP_PNG_SHA256
    if gen_ok:
        with open(os.path.join(_HERE, "phoenix_field.toml"), "rb") as fh:
            spec = tomllib.load(fh)
        spec["reskin"]["texel"][0]["source"] = png       # the corpus regeneration, not stale SCRATCH
        sb = RP.build(spec, sroot, blob=d["blob"])
        sb.check = RP.self_check(sb)
        lines.append("THE SHIPPED SPEC: sha_out %s -- %s; self-check %d/%d; %d byte(s), all in the "
                     "cell span: %s" % (
                         sb.sha_out[:16],
                         "PINNED" if sb.sha_out == PHOENIX_STAGED_SHA256 else "*** DRIFTED ***",
                         sum(1 for g in sb.check.gates if g.ok), len(sb.check.gates),
                         len(sb.enabled[0].changed),
                         all(CAST_SPAN[0] <= sb.enabled[0].page.page_offset + o < CAST_SPAN[1]
                             for o in sb.enabled[0].changed)))
        ok = (ok and sb.sha_out == PHOENIX_STAGED_SHA256 and sb.check.ok
              and all(CAST_SPAN[0] <= sb.enabled[0].page.page_offset + o < CAST_SPAN[1]
                      for o in sb.enabled[0].changed))
    return gate("G2 the cast artifact (ef211's fire field: no-op 0, delta inside the cell, self-check)",
                ok, *lines)


# --------------------------------------------------------------------------- G3
def _id0_rect_table(blob: bytes, tag: str = "s0"):
    """``(rect table offset, rect count)`` for one chunk -- derived exactly as ``scenery_pages`` does."""
    c = EC.parse_header(blob, strict=True)
    for ch in c.chunks:
        if RS.chunk_tag(ch) != tag:
            continue
        res = [r for r in ch.resources if r.id == 0]
        if not res:
            continue                                             # pragma: no cover
        P = res[0].offset
        pb = P + struct.unpack_from("<i", blob, P)[0]
        return (pb + 8, struct.unpack_from("<i", blob, pb + 4)[0])
    return (None, 0)                                             # pragma: no cover


def g3_region_partition():
    if not _have_corpus():
        return gate("G3 the id-0 region partition", False, "no extracted corpus at %s" % CORPUS)
    blob = _load(CAST_EF)
    lines, ok = [], True
    clut = RS._regions(blob, CAST_EF, partition="clut")
    tex = RS._regions(blob, CAST_EF, partition="texel")
    splits = RS.id0_splits(blob)
    lines.append("ef%03d declares %d id-0 split(s): %s" % (
        CAST_EF, len(splits),
        "; ".join("%s header+CLUT %#x..%#x | PIXELS %#x..%#x (%d rects)"
                  % (s.tag, s.lo, s.boundary, s.boundary, s.hi, s.n_rects) for s in splits)))
    ok = ok and bool(splits)

    def _cover(regions, pred):
        s = set()
        for _n, lo, hi in regions:
            if pred(lo):
                s |= set(range(lo, hi))
        return s

    head = set()
    pixels = set()
    for s in splits:
        head |= set(range(s.lo, s.boundary))
        pixels |= set(range(s.boundary, s.hi))
    gt, gc = _cover(tex, lambda _l: True), _cover(clut, lambda _l: True)
    lines.append("TEXEL partition GATES the id-0 header + clutWord table + inline CLUT stream: %s "
                 "(%d B)" % (head.issubset(gt), len(head)))
    lines.append("TEXEL partition LICENSES the id-0 page PIXEL stream (gated n pixels == 0): %s"
                 % (not (gt & pixels)))
    lines.append("CLUT  partition GATES the PIXEL stream: %s" % pixels.issubset(gc))
    lines.append("CLUT  partition LICENSES the header + inline CLUT stream: %s" % (not (gc & head)))
    ok = ok and head.issubset(gt) and not (gt & pixels)
    ok = ok and pixels.issubset(gc) and not (gc & head)

    # ---- sec 6 Q7: "does the id-0 rect-table gate have anything to CATCH?"  It is a fail-safe with
    # ZERO known violations, so the only way to know it is not a comment is to manufacture one.
    off, n = _id0_rect_table(blob)
    lines.append("the s0 rect table: %d rect(s) of 8 B at %#x -- inside the gated half: %s"
                 % (n, off, off in head))
    ok = ok and off is not None and off in head
    perturbed = bytearray(blob)
    struct.pack_into("<H", perturbed, off + 2,
                     struct.unpack_from("<H", perturbed, off + 2)[0] + RS.PAGE_CELL_LINES)
    fired, msg = _refuses(RS.assert_page_cells_identical, blob, bytes(perturbed), "a perturbed ef211")
    lines.append("a SYNTHETICALLY perturbed rect table (rect 0's VRAM y + 128) is CAUGHT: %s"
                 % ("REFUSED -- %s" % msg.split(":")[0] if fired
                    else "*** NOT CAUGHT -- the gate is a comment ***"))
    ok = ok and fired and "DERIVATION MOVED" in msg
    lines.append("   ...and the refusal names the cells: %s"
                 % (msg.split("vanished (")[1].split(")")[0][:70] if fired and "vanished (" in msg
                    else "-"))
    licensed = bytearray(blob)
    pxo = sorted(pixels)[len(pixels) // 2]
    licensed[pxo] ^= 0xFF
    fired2, msg2 = _refuses(RS.assert_page_cells_identical, blob, bytes(licensed), "a pixel write")
    lines.append("a write INSIDE the pixel stream (%#x) is LICENSED (the map re-derives): %s"
                 % (pxo, "yes" if not fired2 else "*** REFUSED: %s ***" % msg2[:60]))
    ok = ok and not fired2
    lines.append("the two checks are different instruments on purpose: `_regions` compares BYTES, "
                 "`assert_page_cells_identical` RE-DERIVES the map -- a rect table edit that happened "
                 "to land outside a gated span would still be caught by the second")
    fired3, _m3 = _refuses(RS._regions, blob, CAST_EF, partition="both")
    lines.append("an unknown partition name still refuses: %s" % fired3)
    ok = ok and fired3
    return gate("G3 the id-0 region partition (both halves gated the right way; the fail-safe CATCHES)",
                ok, *lines)


# --------------------------------------------------------------------------- G4
def g4_refusal_matrix():
    if not _have_corpus():
        return gate("G4 the refusal matrix", False, "no extracted corpus at %s" % CORPUS)
    import dataclasses
    lines, ok = [], True

    def check(label, fired, msg, want):
        nonlocal ok
        good = fired and want in msg
        ok = ok and good
        lines.append("%-52s %s" % (label, "REFUSED (%s)" % want if good else
                                   ("WRONG REASON: %s" % msg.splitlines()[0][:60] if fired
                                    else "*** DID NOT REFUSE ***")))

    def builds(label, fn, *a, **kw):
        nonlocal ok
        try:
            b = fn(*a, **kw)
            lines.append("%-52s BUILDS -- %s" % (label, "%d target(s), %d byte(s)"
                                                 % (len(b.enabled),
                                                    sum(len(t.changed) for t in b.enabled))))
            return b
        except Exception as e:                                   # pragma: no cover - a real defect
            ok = False
            lines.append("%-52s *** DID NOT BUILD: %s: %s ***" % (label, type(e).__name__,
                                                                  str(e)[:70]))
            return None

    td = _tmp()
    b211 = _load(CAST_EF)

    # -- (a) sec 3.2's refusals, by name, each carrying its measurement
    check("DEPTH-UNKNOWN, by cell name (ef211 x448_y256)",
          *_refuses(RP.texel_page, b211, "cell.s0.x448_y256", CAST_EF), want="DEPTH-UNKNOWN")
    check("   ...and it quotes the FALSIFIED guessing probe",
          *_refuses(RP.texel_page, b211, "cell.s0.x448_y256", CAST_EF), want="54.5%")
    b227 = _load(227)
    # ★ THE FIXTURE CELL MOVED ONE STACKED CELL DOWN AT W6b-3 (iv), AND THAT IS A CORROBORATION OF
    # THE ADOPTION RATHER THAN A REGRESSION -- WRITTEN DOWN BECAUSE IT EXPLAINS AN OLD ANOMALY.
    # `cell.s0.x576_y256` used to refuse as a TRIPLE-depth conflict.  Its three bound readers are
    # 0x29e14 (8bpp, no pair), 0x2ba28 (4bpp, pair (0, 128)) and 0xbe030 (15bpp, pair (16, 128)) --
    # and record 0xbe020 IS ef227's ANSWER SLOT, the P = 1 record whose value test settled the
    # operation as ADD.  Under the measured displacement the 4bpp and the 15bpp readers both carry
    # dv = 128 and move to the LOWER stacked cell, so (576, 256) is left with the single 8bpp reader,
    # the depth set [4, 8, 15] collapses to [8], and the cell resolves cleanly.  The triple-depth
    # conflict was an ARTIFACT OF THE MIS-ATTRIBUTED JOIN: three depths were never stated about the
    # same bytes, they were two readers filed against the wrong cell.  The conflict did not vanish --
    # it followed the readers down to (576, 384), where 4 and 15 now disagree, and the class refuses
    # there.  SWEPT, NOT GUESSED: the replacement is a cell that still refuses through the SHIPPED
    # `texel_page` default.  Same container, same class, one token.
    check("SAME-BYTES-TWO-DEPTHS (ef227 x576_y384, where the displaced readers now collide)",
          *_refuses(RP.texel_page, b227, "cell.s0.x576_y384", 227), want="SAME-BYTES-TWO-DEPTHS")
    b381 = _load(381)
    check("PROGRAM-VRAM WRITE (ef381, loader op 0x07)",
          *_refuses(RP.build, _texel_spec(381, [_row("cell.s0.x448_y256", "x.png")]), td,
                    blob=b381), want="PROGRAM-VRAM WRITE")
    # THE BY-CELL VERDICT.  ef001/ef142/ef144 declare (704,256) and MoveImage's destination
    # const-folds to it -- but all 30 of their cells are ALSO depth-unknown, so no real spec can
    # reach the by-cell gate today.  It is therefore exercised on the gate function directly, with
    # ef211's real page wearing the hazard record those three containers carry.  Stating that is the
    # point: a refusal nothing can reach is a tripwire, and a tripwire nobody tested is a comment.
    p211 = RP.texel_page(b211, CAST_NAME, CAST_EF)
    hard = dataclasses.replace(p211, hazards=dataclasses.replace(
        p211.hazards, program="write", program_cell=True,
        program_evidence="MoveImage $a1/$a2 const-fold to (704, 256) on ef001 / ef142 / ef144"))
    check("PROGRAM-VRAM WRITE **BY CELL** (the MoveImage destination)",
          *_refuses(RP._gate_program_vram, hard, "the by-cell tripwire"),
          want="PROGRAM-VRAM WRITE, BY CELL")
    check("   ...and it says SHARPER, not narrower",
          *_refuses(RP._gate_program_vram, hard, "the by-cell tripwire"),
          want="SHARPER, NOT NARROWER")
    unk = dataclasses.replace(p211, hazards=dataclasses.replace(
        p211.hazards, program="unknown",
        program_evidence="no effect id was supplied with these bytes"))
    check("PROGRAM-VRAM UNKNOWN: silence is ignorance, not safety",
          *_refuses(RP._gate_program_vram, unk, "no id"), want="PROGRAM-VRAM UNKNOWN")
    # AN UNWRITTEN COLUMN.  Measured: the 10 bindings that read a cell nothing uploads are all
    # ef390's, and the cells they read have no writer -- so no cell of theirs is EMITTED and no real
    # spec can name one.  Like the by-cell MoveImage verdict it is a TRIPWIRE, and a tripwire nobody
    # fired is a comment, so it is fired here by giving a REAL spilling model a synthetic cover cell
    # that no writer uploads -- the same posture as G3's perturbed rect table.
    sky0 = next(p for p in RP.scenery_texel_pages(b227, 227)
                if p.cell == (704, 256) and p.hazards.spill_out)
    models227 = RP.bound_models(b227)
    spiller = next(m for m in models227 if m.geom == sky0.hazards.readers[0].geom and m.spills)
    ghost_cover = dict(spiller.cover)
    ghost_cover[(1216, 256)] = {0}
    # ⚠ BOTH COVERS, AND THE SECOND ONE IS LOAD-BEARING SINCE W6b-3 (iv).  THE NAME-EVERY-COLUMN gate
    # now takes its obligation on `effective_cover` -- the cell the hardware SAMPLES -- so a ghost
    # injected into `cover` alone is INVISIBLE to it and the gate fires its ordinary spill-out refusal
    # instead of the unwritten-column one.  A tripwire that fires for the WRONG reason is a tripwire
    # nobody has tested, which is exactly what this fixture exists to prevent.
    ghost = [dataclasses.replace(m, cover=ghost_cover, effective_cover=ghost_cover)
             if m is spiller else m for m in models227]
    tgt = RP.TexelTarget(name=sky0.name, enabled=True, source="x.png", page=sky0)
    check("an UNWRITTEN column (nothing uploads what the model reads)",
          *_refuses(RP._gate_spill_columns, b227, [tgt], ghost), want="NO WRITER in")
    b251 = _load(251)
    cells251 = {}
    for pc in RS.page_cells(b251).values():
        cells251.setdefault(pc.cell, []).append(pc)
    shared251 = [c for c, ws in cells251.items() if len(ws) > 1]
    unread251 = [c for c in shared251
                 if not any(p.cell == c for p in RP.scenery_texel_pages(b251, 251))]
    lines.append("%-52s %d of %d shared cells, %d of them UNREAD -- a Madeen shared-column repaint "
                 "is out of reach at ANY depth" % ("ef251 (Madeen): its multi-writer cells",
                                                   len(shared251), len(cells251), len(unread251)))
    ok = ok and len(shared251) == 6 and len(unread251) == 6
    check("   ...naming one of them",
          *_refuses(RP.texel_page, b251, "cell.%s.x%d_y%d"
                    % (cells251[shared251[0]][0].tag, shared251[0][0], shared251[0][1]), 251),
          want="DEPTH-UNKNOWN")
    check("the `rgba` lane on the INDEXED surface (unchanged by W6b)",
          *_refuses(RP.export_art, b227, 227, td, lane="rgba"), want="EXACT RECOVERY")
    check("an unknown art lane", *_refuses(RP.export_art, b227, 227, td, lane="cmyk"),
          want="unknown art lane")
    check("`--quantize` / `--mint-clut` are not a key at all",
          *_refuses(RP.build, _texel_spec(CAST_EF, [_row(CAST_NAME, "x.png", quantize=True)]), td,
                    blob=b211), want="unknown key")

    # -- (b) THE DEPTH GUARD, both directions
    check("expect_bpp mis-stated (4 where the `so` record says 8)",
          *_refuses(RP.build, _texel_spec(CAST_EF, [_row(CAST_NAME, "x.png", expect_bpp=4)]), td,
                    blob=b211), want="the container's own `so` record derives")
    check("expect_bpp on a cell with NO single depth",
          *_refuses(RP.assert_expect_bpp, b227,
                    [p for p in RP.scenery_texel_pages(b227, 227)
                     if p.depth_ambiguous][0], 4, "probe"), want="NO single depth to guard")
    check("expect_cell mis-stated",
          *_refuses(RP.build, _texel_spec(CAST_EF, [_row(CAST_NAME, "x.png",
                                                         expect_cell=[704, 384])]), td, blob=b211),
          want="the derivation says")
    check("expect_cell on a CREATURE page (its unit is the PART)",
          *_refuses(RP.build, _texel_spec(227, [_row("tex.part0", "x.png", expect_cell=[192, 0])]),
                    td, blob=b227), want="its addressable unit is the id-4 PART")

    # -- (c) THE CO-TRANSFORM REMEDY on ef227 x832_y384: sec 1.2's own remediable pair (writers `s1`
    # and `id9.s0`, one an id-0 page rect and one an id-9 ALTERNATE block), and the only shared cell
    # in the corpus carrying NO other hazard -- so a refusal here can only be the co-transform one.
    cells227 = {}
    for p in RP.scenery_texel_pages(b227, 227):
        cells227.setdefault(p.cell, []).append(p)
    pair = cells227[(832, 384)]
    arts = []
    for p in pair:
        words = RP.palette_words(b227, p)
        zeros = set(RP.transparent_indices(words))
        raw = bytearray(b227[p.page_offset:p.page_offset + p.page_bytes])
        # ONE index moved without ever crossing the transparent boundary, so a refusal in this block
        # is always THE CO-TRANSFORM REMEDY and never THE CUTOUT LAW wearing its coat.
        i = next(k for k in range(len(raw)) if raw[k] not in zeros)
        v = 1 + (raw[i] % 255)
        while v in zeros:
            v = 1 + (v % 255)
        raw[i] = v
        dst = os.path.join(td, "co_%s.png" % p.name.replace(".", "_"))
        RP.write_indexed_png(bytes(raw), words, p.w, p.h, dst)
        arts.append(dst)
    lines.append("%-52s %s (%d writers, hazards: %s)"
                 % ("CO-TRANSFORM fixture: ef227 VRAM cell (832, 384)",
                    " + ".join(p.name for p in pair), len(pair[0].hazards.writers),
                    pair[0].hazards.names or "co-transform ONLY"))
    check("CO-TRANSFORM: one writer of a 2-writer cell named",
          *_refuses(RP.build, _texel_spec(227, [_row(pair[0].name, arts[0])]), td, blob=b227),
          want="THE CO-TRANSFORM REMEDY")
    check("   ...and the refusal names what is LEFT STOCK",
          *_refuses(RP.build, _texel_spec(227, [_row(pair[0].name, arts[0])]), td, blob=b227),
          want="LEFT STOCK")
    check("   both writers named, neither acknowledged",
          *_refuses(RP.build, _texel_spec(227, [_row(pair[0].name, arts[0]),
                                                _row(pair[1].name, arts[1])]), td, blob=b227),
          want="does not say `acknowledge_cotransform = true`")
    check("   `acknowledge_cotransform = \"true\"` (a STRING)",
          *_refuses(RP.build, _texel_spec(227, [
              _row(pair[0].name, arts[0], acknowledge_cotransform="true"),
              _row(pair[1].name, arts[1], acknowledge_cotransform="true")]), td, blob=b227),
          want="must be a BOOLEAN")
    bco = builds("   both named + the literal `true`: THE REMEDY",
                 RP.build, _texel_spec(227, [
                     _row(pair[0].name, arts[0], acknowledge_cotransform=True),
                     _row(pair[1].name, arts[1], acknowledge_cotransform=True)]), td, blob=b227)
    if bco is not None:
        note = next((n for n in bco.enabled[0].hazard_notes if n.startswith("CO-TRANSFORM")), "")
        lines.append("      %s" % note[:150])
        ok = ok and "acknowledged" in note

    # -- (d) THE NAME-EVERY-COLUMN GATE, on ef227's sky dome (704 -> 768, CROSS-RESOURCE)
    sky = next(p for p in RP.scenery_texel_pages(b227, 227)
               if p.cell == (704, 256) and p.hazards.spill_out)
    check("SPILL: a spilling model's cell named alone",
          *_refuses(RP.build, _texel_spec(227, [_row(sky.name, "x.png")]), td, blob=b227),
          want="THE NAME-EVERY-COLUMN GATE")
    check("   ...and the refusal names the columns NOT NAMED",
          *_refuses(RP.build, _texel_spec(227, [_row(sky.name, "x.png")]), td, blob=b227),
          want="NOT NAMED")
    spill_in = next((p for p in RP.scenery_texel_pages(b227, 227) if p.hazards.spill_in), None)
    if spill_in is not None:
        check("SPILL-IN: a FOREIGN model reads this cell (page scope is wrong)",
              *_refuses(RP.build, _texel_spec(227, [_row(spill_in.name, "x.png")]), td, blob=b227),
              want="SPILLS IN here")

    # -- (e) sec 4.4's MOVED PINS
    fired, msg = _refuses(RP.texel_page, b211, "page.s0.x576_y256.h256", CAST_EF)
    named = fired and "cell.s0.x576_y256" in msg and "cell.s0.x576_y384" in msg
    lines.append("%-52s %s" % ("MOVED PIN: the h=256 RECT spelling still refuses",
                               "REFUSED, and NAMES both halves it splits into" if named
                               else "*** %s ***" % (msg.splitlines()[0][:60] or "DID NOT REFUSE")))
    ok = ok and named and "NOT an addressable unit" in msg
    b061 = _load(61)
    inverted = [p.name for p in RP.scenery_texel_pages(b061, 61)]
    lines.append("%-52s %s" % ("MOVED PIN: a CREATURE-LESS container (ef061)",
                               "now EXPOSES %d scenery cell(s): %s"
                               % (len(inverted), ", ".join(inverted[:3]))))
    ok = ok and bool(inverted) and EC.creature_package(b061) is None
    check("   ...while one with NO stated depth anywhere still refuses (ef000)",
          *_refuses(RP.export_art, _load(0), 0, td), want="W6b")
    others = RP.other_page_writers(b211)
    halves = sorted(c for c in others if c[0] == 576)
    lines.append("%-52s %s -> %s" % ("MOVED PIN: other_page_writers SPLITS an h=256 rect",
                                     [str(c) for c in halves],
                                     [others[c][0][0] for c in halves]))
    ok = ok and halves == [(576, 256), (576, 384)]
    check("   a w != 64 page rect REFUSES (a tripwire, 0 live instances)",
          *_refuses(RS._assert_cell_width, "a synthetic rect", 704, 256, 32, 128),
          want="PAGE-RECT WIDTH")
    return gate("G4 the refusal matrix (sec 3.2 by name + the three remedies + sec 4.4's moved pins)",
                ok, *lines)


# --------------------------------------------------------------------------- G5
def g5_clut_lane_compat():
    if not _have_corpus():
        return gate("G5 CLUT-lane byte compatibility", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    d = cast_build()
    blob, b = d["blob"], d["build"]
    texel_bytes = {i for i in range(len(blob)) if blob[i] != b.patched[i]}

    # the SIBLING lever, on the SAME container and the SAME palette this cell indexes into: W5's
    # cast-proven Phoenix recolour targets `pal.s0.x0_y247.e256`, which is exactly the fire field's
    # key.  If the two levers were ever going to collide, it would be here.
    text, _pmap = RS.scaffold(CAST_EF, blob)
    import tomllib
    spec = tomllib.loads(text)
    row = next(r for r in spec["reskin"]["target"] if r["name"] == d["page"].palette_name)
    row["enabled"] = True
    row["hue_rotate"] = 40.0
    if row.get("shared"):
        row["acknowledge_shared"] = True
    try:
        rb = RS.build(spec, "ef%03d-w6b-clut" % CAST_EF, blob=blob)
    except RS.ReskinError as e:                                  # pragma: no cover - a real defect
        return gate("G5 CLUT-lane byte compatibility", False, "the CLUT sibling refused: %s" % e)
    clut_bytes = {i for i in range(len(blob)) if blob[i] != rb.patched[i]}
    lines.append("the same container, the same palette (%s), two levers:"
                 % d["page"].palette_name)
    lines.append("   TEXEL lever: %d byte(s), all in %s's 0x4000 span %#x..%#x"
                 % (len(texel_bytes), d["page"].name, CAST_SPAN[0], CAST_SPAN[1]))
    lines.append("   CLUT  lever: %d byte(s), in the id-0 INLINE CLUT stream"
                 % len(clut_bytes))
    lines.append("   intersection: %d  (union %d)" % (len(texel_bytes & clut_bytes),
                                                      len(texel_bytes | clut_bytes)))
    ok = ok and not (texel_bytes & clut_bytes) and texel_bytes and clut_bytes

    splits = RS.id0_splits(blob)
    head = {o for o in clut_bytes if any(s.lo <= o < s.boundary for s in splits)}
    pix = {o for o in texel_bytes if any(s.boundary <= o < s.hi for s in splits)}
    lines.append("and the SPLIT explains it structurally, not coincidentally: every CLUT byte is "
                 "BELOW pixelDataRel (%d/%d) and every texel byte is ABOVE it (%d/%d)"
                 % (len(head), len(clut_bytes), len(pix), len(texel_bytes)))
    ok = ok and len(head) == len(clut_bytes) and len(pix) == len(texel_bytes)

    # ...and the sibling's own gate agrees, from the other side
    gates = [g for g in d["build"].check.orthogonality + d["build"].check.regions]
    named = [g for g in gates if "id-0" in g.name or "page-cell" in g.name]
    for g in named:
        lines.append("   [%s] %s" % ("ok" if g.ok else "!!", g.name))
        ok = ok and g.ok
    lines.append("the CLUT lane's own artifacts are pinned by w6_gates G5 (ef227 / ef211 / ef251 "
                 "shas); what THIS gate adds is the scenery surface, where the two levers finally "
                 "share a container AND a palette")
    return gate("G5 CLUT-lane byte compatibility (a scenery texel build and a scenery recolour: "
                "DISJOINT)", ok, *lines)


# --------------------------------------------------------------------------- G6
def _walk_program_vram():
    """RE-DERIVE the program-VRAM id sets from the corpus bytes with the study's own walker.

    ``repaint.PROGRAM_VRAM_WRITE_IDS`` / ``PROGRAM_VRAM_READ_IDS`` / ``MOVEIMAGE_HARD_CELLS`` are the
    ONE place the kit carries a corpus list rather than a derivation, because the derivation is a MIPS
    reachability walk over 385 program images that a build cannot afford per target. A constant that
    is a cache of a measurement has to be re-measured somewhere, and this is that somewhere.

    Two instruments, because the walk is a LOWER bound (384 of 385 images carry unreached code-shaped
    space): the const-folding reachability walk, and a LINEAR scan for the HLE call SHAPE the format
    guarantees (``lw $rX, (4*op)(base) ... jalr $rX``). Returns ``None`` when tier-r's disassembler is
    not importable, so the gate can report an ABSENT instrument rather than a passing one.
    """
    sys.path.insert(0, os.path.join(_REPO, "studies", "custom-summons", "tier-r"))
    sys.path.insert(0, os.path.join(_REPO, "studies", "custom-summons", "thomas-swap", "disasm"))
    try:
        import tier_r_disasm as D
    except Exception:                                            # pragma: no cover - env dependent
        return None
    VRAM_OPS = {0: "LoadImage", 1: "StoreImage", 166: "MoveImage", 12: "TexAnimArm"}
    LOOKBACK, BASE_BACK = 12, 40
    hle = D.load_hle_names()
    dec = D.DEFAULT_DECODER
    walk = {v: set() for v in VRAM_OPS.values()}
    linear = {v: set() for v in VRAM_OPS.values()}
    seq7, dest = set(), {}
    images = errors = 0
    for path in W.corpus_paths(CORPUS):
        ef = int(os.path.basename(path)[2:5])
        with open(path, "rb") as fh:
            blob = fh.read()
        try:
            for op in EC.parse_op_stream(blob):
                if op.code == 0x07:
                    seq7.add(ef)
        except Exception:                                        # pragma: no cover
            errors += 1
        try:
            imgs = D.id3_images(blob, "ef%03d" % ef)
        except Exception:                                        # pragma: no cover
            errors += 1
            continue
        for img in imgs:
            images += 1
            try:
                r = D.walk_image(img, hle_names=hle)
            except Exception:                                    # pragma: no cover
                errors += 1
                r = None
            if r is not None:
                for c in r.calls:
                    if c.kind == "hle" and c.hle_op in VRAM_OPS:
                        walk[VRAM_OPS[c.hle_op]].add(ef)
                        if c.hle_op == 166 and len(c.args) >= 3 and c.args[1] is not None \
                                and c.args[2] is not None:
                            dest.setdefault(ef, set()).add((c.args[1], c.args[2]))
            pay, n = img.payload, img.header_rel
            ins = [dec.decode(struct.unpack_from("<I", pay, o)[0], o, img.psx_base)
                   for o in range(0, min(n, len(pay)) - 3, 4)]
            for k, i in enumerate(ins):
                if not i.entry or i.entry.name != "jalr" or len(i.ops) < 2:
                    continue
                treg = i.ops[1]
                for j in range(k - 1, max(-1, k - 1 - LOOKBACK), -1):
                    p = ins[j]
                    if not p.entry or p.entry.name != "lw" or p.ops[0] != treg:
                        continue
                    imm = p.ops[1]
                    op = imm // 4 if imm % 4 == 0 else -1
                    if not (0 <= imm < D.HLE_MAX_OFFSET) or op not in VRAM_OPS:
                        break
                    linear[VRAM_OPS[op]].add(ef)
                    break
    return {"walk": walk, "linear": linear, "seq7": seq7, "dest": dest, "images": images,
            "errors": errors}


def g6_corpus_census():
    if not _have_corpus():
        return gate("G6 the corpus census", False, "no extracted corpus at %s" % CORPUS)
    c = census()
    lines, ok = [], True

    def row(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        lines.append("%-46s %6s   %s" % (label, got, "" if good else "*** STATED %s ***" % (want,)))

    row("containers", c["containers"], 372)
    row("page-cells, corpus-wide", c["scenery_cells"] + c["creature_pages"], PIN["page_cells"])
    row("   id-4 CREATURE pages (W6a's surface)", c["creature_pages"], PIN["creature_pages"])
    row("   SCENERY cells", c["scenery_cells"], PIN["scenery_cells"])
    row("   ...over cell-WRITER records", c["writer_records"], PIN["writer_records"])
    row("LAWFUL, rect-addressable", len(c["lawful_rect"]), PIN["lawful_rect"])
    row("   page-scope-safe", len(c["page_safe"]), PIN["lawful_page_safe"])
    row("   model-scope (the reader spills out)", len(c["model_scope"]), PIN["lawful_model_scope"])
    row("LOWER-HALF-ONLY, otherwise lawful (class B2)",
        len(c["lawful_cell"]) - len(c["lawful_rect"]), PIN["lower_half_lawful"])
    lines.append("%-46s %6d   = %d + %d: what the per-VRAM-cell map ADDS to the edit permission"
                 % ("LAWFUL under the per-cell map", len(c["lawful_cell"]),
                    len(c["lawful_rect"]), len(c["lawful_cell"]) - len(c["lawful_rect"])))
    row("unaddressable through the (tag, x) rect key", len(c["unaddressable"]), PIN["unaddressable"])
    row("DEPTH-UNKNOWN (no `so` reader)", c["depth_unknown"], PIN["depth_unknown"])
    row("CO-TRANSFORM cells", c["co_cells"], PIN["co_transform"])
    row("   expressible (single-depth, read)", c["co_expressible"], PIN["co_expressible"])
    row("   also SAME-BYTES-TWO-DEPTHS", c["co_two_depth"], PIN["co_two_depth"])
    row("   unread (nothing samples them)", c["co_unread"], PIN["co_unread"])
    row("   writer PAIRS", c["co_pairs"], PIN["co_pairs"])
    row("   ...byte-identical", c["co_identical"], PIN["co_identical"])
    row("SAME-BYTES-TWO-DEPTHS", c["dual_depth"], PIN["dual_depth"])
    lines.append("%-46s %6s" % ("   by effect",
                                ", ".join("ef%03d x%d" % (k, v)
                                          for k, v in sorted(c["dual_by_ef"].items()))))
    row("MULTI-PALETTE (class E2, > 1 palette KEY)", c["multi_palette"], PIN["multi_palette"])
    row("   ...counting DECLARED CLUT cells only", c["multi_clut_cell"], PIN["multi_clut_cell"])
    row("   ...of which single-depth (class C)", c["class_c"], PIN["class_c"])
    lines.append("%-46s %6s   the 4-cell delta is cells whose second reader is a 15bpp DIRECT binder "
                 "with no CLUT at all; all 4 are ALSO same-bytes-two-depths and refuse earlier"
                 % ("   the two predicates, reconciled", c["multi_palette"] - c["multi_clut_cell"]))
    row("SHARED-READ (class E3)", c["shared_read"], PIN["shared_read"])
    row("SPILLING bindings", sum(c["spill_bind"].values()), PIN["spill_bindings"])
    row("   at 8bpp", c["spill_bind"][8], PIN["spill_8bpp"])
    row("   at 15bpp", c["spill_bind"][15], PIN["spill_15bpp"])
    row("   at 4bpp (STRUCTURAL: u <= 255 / 4 = 63)", c["spill_bind"][4], PIN["spill_4bpp"])
    row("spill-touched cells, UV-exact AND written", len(c["spill_uv"]), PIN["spill_uv_exact"])
    row("   ...UV-exact but NOTHING uploads them", len(c["spill_unwritten"]),
        PIN["spill_unwritten"])
    lines.append("%-46s %6d   this gate's OWN rect expansion; A1's probe recorded 83.  The superset "
                 "is CONSTRUCTION-DEPENDENT and therefore not pinned -- what is pinned is that the "
                 "UV-exact set is a strict SUBSET of it, with %d contradictions"
                 % ("   rect-conservative superset", len(c["spill_rect"]),
                    len(c["spill_uv"] - c["spill_rect"])))
    ok = ok and not (c["spill_uv"] - c["spill_rect"])
    lines.append("%-46s %6s   the gate uses the UV-EXACT set, because naming a cell the model does "
                 "not read would be a FALSE obligation" % ("   the settlement", ""))
    row("PROGRAM-VRAM WRITE cells", len(c["prog_write"]), PIN["program_write_cells"])
    row("PROGRAM-VRAM READ cells (DISCLOSE, not refuse)", len(c["prog_read"]),
        PIN["program_read_cells"])
    row("   ...refused BY CELL NAME", len(c["prog_named"]), PIN["program_cells_by_name"])
    d15 = [x for x in c["d15_lawful"] if not x[3]]
    row("15bpp LAWFUL cells", len(d15), PIN["direct15_lawful"])
    lines.append("%-46s %6d   %s -- + %d more once the per-cell map lands"
                 % ("   ...incl. the lower halves", len(c["d15_lawful"]),
                    ", ".join("ef%03d %s%s" % (e, cell, " (spills)" if sp else "")
                              for e, cell, sp, _lh in c["d15_lawful"]),
                    len(c["d15_lawful"]) - len(d15)))
    lines.append("%-46s %6d   of which %d are CREATURE-LESS -- the inverted pin's real population"
                 % ("containers exposing >= 1 editable cell", c["exposed"],
                    c["creatureless_exposed"]))

    # ---- THE RE-DERIVATION PIN
    lines.append("")
    lines.append("THE RE-DERIVATION PIN -- the program-VRAM lists, re-walked from the bytes:")
    w = _walk_program_vram()
    if w is None:                                                # pragma: no cover - env dependent
        lines.append("   *** tier-r's disassembler is not importable -- the pin could not RUN, "
                     "which is a FAILED gate and not a skipped one ***")
        ok = False
    else:
        lines.append("   %d id-3 images walked, %d error(s)" % (w["images"], w["errors"]))
        for nm, got, want in (("walk LoadImage", w["walk"]["LoadImage"], WALK_LOADIMAGE),
                              ("walk MoveImage", w["walk"]["MoveImage"], WALK_MOVEIMAGE),
                              ("walk StoreImage", w["walk"]["StoreImage"], WALK_STOREIMAGE),
                              ("walk texanim arm (op 12)", w["walk"]["TexAnimArm"],
                               WALK_TEXANIM_ARM),
                              ("loader-script op 0x07", w["seq7"], WALK_SEQ07)):
            same = set(got) == set(want)
            ok = ok and same
            lines.append("   %-26s %2d  %s%s" % (nm, len(got),
                                                 ", ".join("ef%03d" % e for e in sorted(got)),
                                                 "" if same else "  *** DIFFERS FROM STATED ***"))
        mips_w = w["walk"]["LoadImage"] | w["walk"]["MoveImage"]
        lin_w = w["linear"]["LoadImage"] | w["linear"]["MoveImage"]
        refuted = mips_w - lin_w
        lines.append("   THE ef435 REFUTATION: the walk's MIPS writers are %s; the linear "
                     "call-SHAPE scan reproduces %s.  UNREPRODUCED: %s -- its @0x2dd8 has no "
                     "`lw (4*op)(base) ... jalr` shape at all, so the walker read a switch dispatch "
                     "through the image's own pointer table as HLE op 0"
                     % (sorted(mips_w), sorted(lin_w),
                        ", ".join("ef%03d" % e for e in sorted(refuted)) or "none"))
        ok = ok and refuted == {435}
        derived_write = (mips_w - refuted) | w["seq7"] | w["walk"]["TexAnimArm"]
        lines.append("   WRITE = (walk LoadImage u MoveImage - the refutation) u op-0x07 u the "
                     "texanim arm = %d ids  %s repaint.PROGRAM_VRAM_WRITE_IDS"
                     % (len(derived_write),
                        "==" if derived_write == set(RP.PROGRAM_VRAM_WRITE_IDS) else "*** != ***"))
        ok = ok and derived_write == set(RP.PROGRAM_VRAM_WRITE_IDS)
        store = w["walk"]["StoreImage"] | w["linear"]["StoreImage"]
        derived_read = store - derived_write
        extra = w["linear"]["StoreImage"] - w["walk"]["StoreImage"]
        lines.append("   READ  = (walk u linear StoreImage) - WRITE = %d ids  %s "
                     "repaint.PROGRAM_VRAM_READ_IDS   (the linear scan alone contributes %s -- the "
                     "six the reachability walk never reached)"
                     % (len(derived_read),
                        "==" if derived_read == set(RP.PROGRAM_VRAM_READ_IDS) else "*** != ***",
                        ", ".join("ef%03d" % e for e in sorted(extra))))
        ok = ok and derived_read == set(RP.PROGRAM_VRAM_READ_IDS)
        ok = ok and extra == set(LINEAR_ONLY_STORE)
        folded = {e: sorted(v)[0] for e, v in w["dest"].items() if len(v) == 1}
        lines.append("   MoveImage's DESTINATION const-folds on %d of the %d MoveImage containers: "
                     "%s  %s repaint.MOVEIMAGE_HARD_CELLS"
                     % (len(folded), len(w["walk"]["MoveImage"]),
                        ", ".join("ef%03d -> %s" % (e, str(v)) for e, v in sorted(folded.items())),
                        "==" if folded == dict(RP.MOVEIMAGE_HARD_CELLS) else "*** != ***"))
        ok = ok and folded == dict(RP.MOVEIMAGE_HARD_CELLS)
        allids = mips_w | w["walk"]["StoreImage"] | w["seq7"] | w["walk"]["TexAnimArm"]
        lines.append("   AND THE 15-vs-22 ARITHMETIC, settled: the WALK's union across all four op "
                     "families is %d ids -- the pre-W6b record's ENUMERATION; its writer union "
                     "alone is %d -- the record's HEADLINE.  Neither was wrong; they described "
                     "different sets.  The correction is that the corrected 15 is a DIFFERENT 15 "
                     "(ef435 out, ef038 in), and that the 7 ids the enumeration adds are READS."
                     % (len(allids), len(mips_w | w["seq7"])))
        ok = ok and len(allids) == 22 and len(mips_w | w["seq7"]) == 15
    return gate("G6 the corpus census (the numbers this rung may quote) + THE RE-DERIVATION PIN",
                ok, *lines)


# --------------------------------------------------------------------------- G7
def _byte_literals(path: str, minlen: int = 6):
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except SyntaxError:                                          # pragma: no cover
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
            if len(node.value) >= minlen and len(set(node.value)) > 1:
                out.append((node.lineno, node.value))
    return out


def g7_provenance():
    import subprocess
    lines, ok = [], True
    lits = []
    for name in COMMITTABLE:
        fp = os.path.join(_REPO, *name.split("/")) if "/" in name else os.path.join(_HERE, name)
        if not os.path.isfile(fp):
            lines.append("%s MISSING" % name)
            ok = False
            continue
        if name.endswith(".py"):
            lits.extend((name, ln, raw) for ln, raw in _byte_literals(fp))
    cast = []
    for name in COMMITTABLE_CAST:
        fp = os.path.join(_HERE, name)
        if os.path.isfile(fp):
            cast.append(name)
            if name.endswith(".py"):
                lits.extend((name, ln, raw) for ln, raw in _byte_literals(fp))
    lines.append("the cast lane's files, scanned when present: %s"
                 % (", ".join(cast) if cast else "none in this tree yet"))
    lines.append("byte literals of >= 6 non-uniform bytes in the %d committable W6b sources: %d"
                 % (len(COMMITTABLE) + len(cast), len(lits)))
    for name, ln, raw in lits:
        lines.append("   %s:%d  %r" % (name, ln, raw[:24]))
    hits = []
    if lits and _have_corpus():
        for path in W.corpus_paths(CORPUS):
            with open(path, "rb") as fh:
                blob = fh.read()
            for name, ln, raw in lits:
                if raw in blob:
                    hits.append("LEAK %s:%d in %s" % (name, ln, os.path.basename(path)))
    lines.append("   of those, appearing anywhere in the %d-file corpus: %d"
                 % (len(W.corpus_paths(CORPUS)), len(hits)))
    for h in hits:
        lines.append("      " + h)
    ok = ok and not hits
    for p in DOSSIERS:
        outside = _REPO.lower() not in os.path.abspath(p).lower()
        lines.append("dossier outside the checkout: %s  (%s)" % (outside, p))
        ok = ok and outside
    try:
        RP.export.assert_local_only(os.path.join(_REPO, "studies", "x"))
        refused_repo = False
    except Exception:
        refused_repo = True
    lines.append("an export destination inside the checkout is REFUSED: %s" % refused_repo)
    ok = ok and refused_repo
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=_REPO)
    big = [ln[3:] for ln in p.stdout.splitlines()
           if ln[3:].strip().endswith((".bytes", ".png"))]
    lines.append("stock-shaped files in the repo working tree: %d%s"
                 % (len(big), "" if not big else " -- " + ", ".join(big)))
    ok = ok and not big
    lines.append("what this rung commits is a DERIVATION, its gates, its tests and the study record "
                 "-- offsets, strides, depths, hazard predicates and effect ids, never a stock byte; "
                 "every decoded picture stays in SCRATCH by `export.assert_local_only`")
    return gate("G7 provenance (no SE bytes committable; the SE-derived dossiers stay in SCRATCH)",
                ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not _have_corpus():
        print("\nNOTE: no extracted corpus at %s -- every gate will FAIL loudly rather than skip."
              % CORPUS)
    try:
        g1_format_identity()
        g2_cast_artifact()
        g3_region_partition()
        g4_refusal_matrix()
        g5_clut_lane_compat()
        g6_corpus_census()
        g7_provenance()
    finally:
        if _TMP is not None:
            import shutil
            shutil.rmtree(_TMP, ignore_errors=True)
    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
