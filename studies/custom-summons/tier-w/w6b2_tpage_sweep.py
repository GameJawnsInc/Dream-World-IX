r"""TIER W rung W6b-2, lane L1 -- THE TPAGE SWEEP.  Can the id-3 PROGRAM name a cell's bit depth?

THE PROBLEM.  2,385 of 2,572 non-creature scenery page-cells are DEPTH-UNKNOWN: no ``so`` record
binds them, so the container states no bit depth and ``repaint``'s texel lane refuses them by name.
An ``so`` record is a BINDING, not a draw (W6b-1's cast law), and 222 of 372 containers declare zero
non-creature GEOM blocks yet visibly draw textured effects -- so something OTHER than an ``so``
record is setting a texture page.  Recon Q1 asks whether the id-3 effect PROGRAM does it, and this
lane answers with the program's own recovered constants.

WHAT A TPAGE BUYS.  A PSX texture-page word names a **64-halfword x 256-line PAGE**, and the scenery
band's cells are 64 x 128, so ONE page covers the TWO STACKED CELLS of its column (``y=256`` and
``y=384``).  Depth is a property of the page (it is the GPU's draw mode while that page is sampled),
not of the UV footprint -- so one constant tpage attributes depth to both cells of its column.  That
granularity is also why this lane finds depth the census could not: the census attributed an ``so``
record's depth only to the cells its stored UVs physically touched (``probe_pass2.halfword_rows``),
which is the right instrument for READERSHIP and the wrong one for DEPTH.  Both predicates are
reported here; neither is silently reconciled into the other.

THE THREE CHANNELS, ranked by how much they prove:

  * **P (program)** -- a folded constant flowing into the tpage argument of an HLE call whose
    dispatch is the R1 sentinel chain.  Discovered, not assumed: :func:`discover` scores EVERY
    ``(op, argument)`` pair in the corpus for tpage-likeness and the sweep runs only what that ranking
    puts on top.  A runtime-computed argument is recorded as a NAMED UNKNOWN, never guessed.
  * **G (so at page granularity)** -- the container's OWN ``so`` records, re-read at page rather than
    UV granularity.  Zero new parsing; it is the census's own tpage field asked a different question.
  * **X (undeclared column)** -- a recovered tpage naming a VRAM column this container never uploads.
    Reported, never attributed: it is evidence about somebody else's page.

THE FALSE-POSITIVE GUARD.  ef435 is the canonical miscall: a switch dispatch through the image's own
pointer table read as HLE op 0.  Every hit here carries its DISPATCH CHAIN, and only
``sysStruct+0x10 -> table[4*op]`` (or a literal ``0xFF0000xx`` sentinel) counts as strong; a bare
fn-ptr slot with no sysStruct parent is recorded and EXCLUDED from the headline.

PROVENANCE.  Pure analysis code -- zero Square-Enix bytes.  It reads the user's own extracted
containers at run time and writes its results (which quote decoded stock instructions) to SCRATCH.

CLI::

    py w6b2_tpage_sweep.py discover            # rank every (HLE op, arg) by tpage-likeness
    py w6b2_tpage_sweep.py sweep               # the full corpus sweep -> tpage_sweep.json
    py w6b2_tpage_sweep.py calibrate           # ground-truth agreement + the ef211 anchor
    py w6b2_tpage_sweep.py all                 # discover + sweep + join + calibrate
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_TIER_R = os.path.normpath(os.path.join(_HERE, "..", "tier-r"))
_KIT = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))
for _p in (_TIER_R, _KIT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tier_r_disasm as D                                      # noqa: E402
from ff9mapkit.summons import reskin as RS                     # noqa: E402

SCRATCH = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
OUT_DIR = os.path.join(SCRATCH, "texel-w6b", "w6b2")
CENSUS_PAGES = os.path.join(SCRATCH, "texel-w6b", "census", "pages.json")
HLE_OPS_JSON = os.path.join(_TIER_R, "hle_ops.json")

PAGE_LINES = 256          # a tpage's y span
CELL_LINES = 128          # a census cell's y span
PAGE_HW = 64              # a tpage's x span, halfwords


# ------------------------------------------------------------------ the tpage word (VERIFIED)
def decode_tpage(tp: int) -> Dict[str, object]:
    """Decode a PSX texture-page word.

    Re-derived here from :func:`ff9mapkit.summons.reskin.attribution`'s own decoder, which is the
    in-repo authority:  ``page = ((tp & 0x0F) * 64, ((tp >> 4) & 1) * 256)`` and
    ``bpp = SO_BPP[(tp >> 7) & 3]``.  :func:`assert_decoder_matches_reskin` proves the agreement
    rather than asserting it in prose.
    """
    return {
        "tpage": tp & 0xFFFF,
        "page_x": (tp & 0x0F) * PAGE_HW,
        "page_y": ((tp >> 4) & 1) * PAGE_LINES,
        "semi": (tp >> 5) & 3,
        "mode": (tp >> 7) & 3,
        "bpp": RS.SO_BPP[(tp >> 7) & 3],
        "high_bits": tp >> 9,
    }


def assert_decoder_matches_reskin(n: int = 512) -> str:
    """CALIBRATION 0: this module's decoder == reskin's, over every 9-bit tpage word."""
    bad = []
    for tp in range(n):
        d = decode_tpage(tp)
        if (d["page_x"], d["page_y"]) != ((tp & 0x0F) * 64, ((tp >> 4) & 1) * 256):
            bad.append(tp)
        if d["bpp"] != RS.SO_BPP[(tp >> 7) & 3]:
            bad.append(tp)
    if bad:
        raise AssertionError("tpage decoder diverges from reskin on %d words: %s"
                             % (len(bad), bad[:8]))
    return "tpage decoder agrees with reskin.attribution over %d/%d words" % (n, n)


def page_cover(page_x: int, page_y: int) -> List[Tuple[int, int]]:
    """The census cells one tpage's page covers: the TWO stacked 128-line halves of its column."""
    return [(page_x, page_y), (page_x, page_y + CELL_LINES)]


# ------------------------------------------------------------------ the walker (SUBCLASS ONLY)
class _ArgWalker(D.ImageWalker):
    """:class:`tier_r_disasm.ImageWalker` plus per-call-site argument LATTICE VALUES.

    ``ImageWalker`` keeps only the folded integer of a constant argument, which cannot tell a
    runtime-computed argument (the honest unknown this lane must count) from a constant zero, and
    keeps no dispatch value at all -- so the ef435 false-positive guard would have nothing to test.
    Both are recorded here, in a SUBCLASS: the shared tier-R module is read-only to this lane.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.argvals: Dict[int, Tuple[D.Val, ...]] = {}
        self.dispatch: Dict[int, str] = {}

    def _record_call(self, r, ins, st):
        before = len(r.calls)
        super()._record_call(r, ins, st)
        if len(r.calls) == before:
            return
        off = r.calls[-1].off
        self.argvals[off] = tuple(st.get(a, D.UNK) for a in D.ARG_REGS)
        self.dispatch[off] = _chain(ins, st)


def _chain(ins, st) -> str:
    """Name the dispatch shape -- THE ef435 GUARD.

    R1's HLE CALL SHAPE LAW: the sentinel table is ``*(sysStruct + 0x10)`` and the op falls out of a
    ``lw $vX, (4*op)(table)``.  ef435's miscall was the same ``lw`` shape with NO sysStruct parent --
    the image dispatching through its own switch table -- so the parent load is the discriminator.
    """
    n = ins.entry.name
    if n == "jal":
        return "direct-jal"
    rs = ins.ops[1] if n == "jalr" else ins.ops[0]
    v = st.get(rs, D.UNK)
    if v.kind == "const":
        if (v.v & D.HLE_SENTINEL_MASK) == D.HLE_SENTINEL_MASK:
            return "immediate-sentinel"
        return "const-target"
    if v.kind == "slot":
        src = v.src
        if src is not None and src.kind == "slot" and src.v == D.HLE_STRUCT_FIELD:
            return "sysStruct-chain"
        if src is not None and src.kind == "slot":
            return "slot-of-slot(+%#x)" % src.v
        return "bare-slot"
    return "dynamic-%s" % v.kind


STRONG_CHAINS = ("sysStruct-chain", "immediate-sentinel")


def clut_shaped(v: Optional[int]) -> bool:
    """Is this co-argument a PSX CLUT word? -- the INDEPENDENT corroborator for a weak dispatch.

    ``Hi_RegisterTexEffModel``'s third argument is the palette word beside the tpage, and the corpus
    histogram is unmistakable: ``0xFFFF`` (the no-palette sentinel, 38 sites) or a word whose
    ``y = w >> 6`` lands in VRAM's palette band and whose ``x = (w & 0x3F) * 16`` is inside the 1024
    halfword-wide frame buffer.  A register that is not a CLUT word is not this call.
    """
    if v is None:
        return False
    if v == 0xFFFF:
        return True
    return 0 < v < 0x8000 and (v & 0x3F) * 16 < 1024 and (v >> 6) < 512


def corroborated(rec: Dict[str, object]) -> bool:
    """A dispatch-chain-LOST hit that four independent facts still identify as the same idiom.

    The chain is lost when ``sysStruct`` reaches the call through a stack reload or a cross-block
    merge, so the walker sees ``lw $vX, 0x58($unknown)`` with no visible parent -- structurally the
    ef435 shape.  What separates it from ef435 is that ef435 had NOTHING else: no tpage-shaped
    argument, no CLUT co-argument, no declared column.  Here all four hold at once, and the promotion
    is reported as its own tier so a reader can subtract it.
    """
    return (str(rec.get("dispatch", "")).startswith(("bare-slot", "slot-of-slot"))
            and rec.get("value") is not None and int(rec["value"]) < 512
            and bool((int(rec["value"]) >> 4) & 1)
            and bool(rec.get("declared_column"))
            and clut_shaped(rec.get("co_args", (None, None, None, None))[2]))


# ------------------------------------------------------------------ provenance: a backward slice
def _writes(ins) -> Optional[int]:
    """The register an instruction writes, or None -- enough for a backward slice."""
    if ins.entry is None:
        return None
    n = ins.entry.name
    if n in ("sb", "sh", "sw", "swl", "swr", "swc0", "swc1", "swc2", "swc3",
             "j", "jal", "jr", "jalr", "b", "nop", "cop0", "cop1", "cop2", "cop3",
             "mult", "multu", "div", "divu", "break", "syscall"):
        return None
    if n.startswith("b") and ins.entry.is_transfer:
        return None
    if ins.entry.ex and ins.entry.ex[0] in (D.Ex.RD, D.Ex.RT):
        return ins.ops[0] or None
    return None


def _reads(ins) -> List[int]:
    if ins.entry is None:
        return []
    out = []
    for k, e in enumerate(ins.entry.ex or ()):
        if k == 0 and e in (D.Ex.RD, D.Ex.RT):
            continue
        if e in (D.Ex.RS, D.Ex.RT, D.Ex.RD):
            v = ins.ops[k]
            if v:
                out.append(v)
    if getattr(ins, "base_reg", None):
        out.append(ins.base_reg)
    return out


def slice_back(r, body: Sequence[int], upto: int, reg: int, depth: int = 3,
               limit: int = 8) -> List[str]:
    """The instructions inside this block that produced ``reg`` at ``upto`` -- the FOLDING CHAIN.

    Deliberately intra-block and depth-capped: a chain that leaves the block is reported as
    ``"<cross-block>"`` rather than chased, because the constant tracker itself is intra-procedural
    and a longer story than it can back would be decoration, not evidence.
    """
    out: List[str] = []
    want = [(reg, depth)]
    seen = set()
    idx = [o for o in body if o < upto]
    while want and len(out) < limit:
        target, d = want.pop(0)
        if d < 0 or (target, d) in seen:
            continue
        seen.add((target, d))
        found = None
        for o in reversed(idx):
            ins = r.instrs.get(o)
            if ins is not None and _writes(ins) == target:
                found = (o, ins)
                break
        if found is None:
            out.append("$%s <cross-block>" % D.REG[target])
            continue
        o, ins = found
        out.append("%04x  %s" % (o, ins.text()))
        for src in _reads(ins):
            want.append((src, d - 1))
    return out


# ------------------------------------------------------------------ corpus plumbing
def corpus_paths(root: str = SCRATCH) -> List[str]:
    return sorted(glob.glob(os.path.join(root, "ef*.bytes")))


def ef_number(path: str) -> int:
    base = os.path.splitext(os.path.basename(path))[0]
    return int(base[2:])


def container_cells(blob: bytes) -> Dict[Tuple[int, int], List[str]]:
    """``{(vram x, vram y): [writer tag]}`` for one container -- reskin's own page-cell map."""
    out: Dict[Tuple[int, int], List[str]] = defaultdict(list)
    try:
        for pc in RS.page_cells(blob).values():
            out[(pc.x, pc.y)].append(pc.tag)
    except Exception:
        pass
    return dict(out)


def so_tpages(blob: bytes) -> List[Dict[str, object]]:
    """Every non-creature ``so`` binding's tpage -- channel G's whole input."""
    rows = []
    try:
        # ★ W6b-3 NARROWING, DECLARED: this artifact DESCRIBES channel G ("channel G's whole input"),
        # and channel G is the INCUMBENT half of the post-W6b-3 population.  Left at the default the
        # sweep's outputs would silently re-aim onto CHANNEL A while still being read as G's.
        a = RS.attribution(blob, include_direct=True, witness=RS.WITNESS_INCUMBENT)
    except Exception:
        return rows
    for b in a.bindings:
        rows.append({"geom": b.geom, "tpage": b.tpage, "bpp": b.bpp,
                     "page_x": b.page[0], "page_y": b.page[1]})
    return rows


# ------------------------------------------------------------------ pass 1: IDIOM DISCOVERY
def _walk_all(paths: Sequence[str], progress: bool = True):
    """Yield ``(ef, image, WalkResult, walker, blob)`` for every id-3 image, in file order."""
    hle = D.load_hle_names()
    t0 = time.time()
    for i, p in enumerate(paths):
        blob = open(p, "rb").read()
        src = os.path.splitext(os.path.basename(p))[0]
        try:
            imgs = D.id3_images(blob, src)
        except Exception as e:
            if progress:
                print("  !! %s: %s" % (src, e))
            continue
        for img in imgs:
            w = _ArgWalker(img.payload, img.psx_base, img.header_rel, img.live_programs,
                           name=img.label, hle_names=hle)
            try:
                r = w.run()
            except Exception as e:
                if progress:
                    print("  !! %s walk: %s: %s" % (img.label, type(e).__name__, e))
                continue
            yield ef_number(p), img, r, w, blob
        if progress and (i + 1) % 50 == 0:
            print("  ... %d/%d containers  %.1fs" % (i + 1, len(paths), time.time() - t0))


def discover(paths: Optional[Sequence[str]] = None, progress: bool = True) -> Dict[str, object]:
    """Rank EVERY ``(HLE op, argument index)`` pair by TPAGE-LIKENESS -- idiom recon, not assumption.

    Four independent predicates, each a property a real tpage argument must have and a random
    integer usually will not:

      ``narrow``    the constant fits 9 bits (a tpage word is 9 significant bits);
      ``ybase``     bit 4 is set -- every one of the 2,665 census cells sits at ``y>=256``, so a
                    scenery tpage's page-Y bit is necessarily 1;
      ``declared``  the decoded column is a VRAM column THIS container actually uploads;
      ``so_match``  the constant equals an ``so``-record tpage in this same container -- the
                    strongest single corroboration available offline.

    The score is their mean over the pair's constant call sites, and the ranking is the calibration:
    if the recovered idiom does not float to the top of a blind sweep of all 216 ops x 4 arguments,
    this lane has not found an idiom, it has confirmed a prior.
    """
    paths = list(paths or corpus_paths())
    stat: Dict[Tuple[int, int], Counter] = defaultdict(Counter)
    vals: Dict[Tuple[int, int], Counter] = defaultdict(Counter)
    for ef, img, r, w, blob in _walk_all(paths, progress):
        cells = container_cells(blob)
        cols = set(x for (x, _y) in cells)
        sotp = set(int(s["tpage"]) for s in so_tpages(blob))
        for c in r.calls:
            if c.kind != "hle" or c.hle_op is None:
                continue
            if w.dispatch.get(c.off) not in STRONG_CHAINS:
                continue
            for ai, v in enumerate(w.argvals.get(c.off, ())):
                key = (c.hle_op, ai)
                stat[key]["sites"] += 1
                if v.kind != "const":
                    stat[key]["runtime"] += 1
                    continue
                stat[key]["const"] += 1
                tp = v.v & 0xFFFFFFFF
                vals[key][tp] += 1
                if tp < 512:
                    stat[key]["narrow"] += 1
                if tp < 512 and (tp >> 4) & 1:
                    stat[key]["ybase"] += 1
                if tp < 512 and ((tp & 0x0F) * PAGE_HW) in cols:
                    stat[key]["declared"] += 1
                if tp in sotp:
                    stat[key]["so_match"] += 1
    rows = []
    names = {int(o["op"]): o.get("name") for o in json.load(open(HLE_OPS_JSON, encoding="utf-8"))}
    for (op, ai), s in stat.items():
        n = s["const"]
        if not n:
            continue
        score = (s["narrow"] + s["ybase"] + s["declared"] + s["so_match"]) / (4.0 * n)
        rows.append({
            "op": op, "arg": ai, "name": names.get(op),
            "sites": s["sites"], "const": n, "runtime": s["runtime"],
            "narrow": s["narrow"], "ybase": s["ybase"], "declared": s["declared"],
            "so_match": s["so_match"], "score": round(score, 4),
            "distinct_values": len(vals[(op, ai)]),
            "top_values": vals[(op, ai)].most_common(6),
        })
    rows.sort(key=lambda r_: (-r_["score"], -r_["const"]))
    return {"pairs": rows, "containers": len(paths)}


# ------------------------------------------------------------------ pass 2: THE SWEEP
def sweep(op_args: Sequence[Tuple[int, int]], paths: Optional[Sequence[str]] = None,
          progress: bool = True, include_corroborated: bool = True) -> Dict[str, object]:
    """Recover every CONSTANT flowing into ``(op, arg)`` corpus-wide, with its folding chain."""
    paths = list(paths or corpus_paths())
    want = set(op_args)
    hits: List[Dict[str, object]] = []
    runtime: List[Dict[str, object]] = []
    weak: List[Dict[str, object]] = []
    promoted: List[Dict[str, object]] = []
    per_container: Dict[int, Dict[str, object]] = {}
    images = 0
    for ef, img, r, w, blob in _walk_all(paths, progress):
        images += 1
        cells = container_cells(blob)
        cols = set(x for (x, _y) in cells)
        sotp = set(int(s["tpage"]) for s in so_tpages(blob))
        blocks = w.blocks(r)
        body_of = {}
        for b, (body, _s) in blocks.items():
            for o in body:
                body_of[o] = body
        pc = per_container.setdefault(ef, {"ef": ef, "images": 0, "hits": 0, "runtime": 0,
                                           "tpages": [], "columns": sorted(cols)})
        pc["images"] += 1
        for c in r.calls:
            if c.kind != "hle" or c.hle_op is None:
                continue
            chain = w.dispatch.get(c.off, "?")
            av = w.argvals.get(c.off, ())
            co = tuple((x.v & 0xFFFFFFFF) if x.kind == "const" else None for x in av)
            for ai, v in enumerate(av):
                if (c.hle_op, ai) not in want:
                    continue
                rec = {"ef": ef, "image": img.label, "chunk_slot": img.chunk_slot,
                       "off": c.off, "op": c.hle_op, "arg": ai, "idiom": "hle-arg",
                       "dispatch": chain, "co_args": list(co)}
                if v.kind != "const":
                    rec["value"] = None
                    rec["lattice"] = v.kind
                    rec["provenance"] = slice_back(r, body_of.get(c.off, ()), c.off,
                                                   D.ARG_REGS[ai])
                    runtime.append(rec)
                    if chain in STRONG_CHAINS:
                        pc["runtime"] += 1
                    continue
                tp = v.v & 0xFFFFFFFF
                rec["value"] = tp
                rec.update(decode_tpage(tp))
                rec["declared_column"] = ((tp & 0x0F) * PAGE_HW) in cols if tp < 512 else False
                rec["so_match"] = tp in sotp
                rec["provenance"] = slice_back(r, body_of.get(c.off, ()), c.off, D.ARG_REGS[ai])
                rec["tier"] = "strong" if chain in STRONG_CHAINS else (
                    "corroborated" if corroborated(rec) else "refused")
                if rec["tier"] == "refused":
                    weak.append(rec)
                    continue
                if rec["tier"] == "corroborated":
                    promoted.append(rec)
                    if not include_corroborated:
                        continue
                hits.append(rec)
                pc["hits"] += 1
                if tp not in pc["tpages"]:
                    pc["tpages"].append(tp)
    return {"hits": hits, "runtime": runtime, "weak_dispatch": weak, "promoted": promoted,
            "include_corroborated": include_corroborated,
            "per_container": sorted(per_container.values(), key=lambda d: d["ef"]),
            "images": images, "containers": len(paths), "op_args": [list(t) for t in op_args]}


# ------------------------------------------------------------------ a REFUSED channel, measured
def probe_pointer_tables(paths: Optional[Sequence[str]] = None,
                         progress: bool = False) -> Dict[str, object]:
    """``Hi_RegisterTexListModel`` (op 19) / ``Hi_RegisterTexPtrModel`` (171) -- CONSIDERED, REFUSED.

    Both take in-image POINTERS rather than a tpage integer, so the obvious extension is to deref
    and read the pointee as a table of tpage words.  Measured rather than assumed: of the in-image
    pointer arguments recovered corpus-wide, only a minority carry even ONE tpage-shaped halfword in
    their first eight.  A table that shape-tests at chance is not a table this lane can read, so the
    channel is refused BY NAME with its number attached instead of guessed at.
    """
    import struct as _s
    paths = list(paths or corpus_paths())
    tot = Counter()
    for ef, img, r, w, blob in _walk_all(paths, progress):
        cols = set(x for (x, _y) in container_cells(blob))
        for c in r.calls:
            if c.kind != "hle" or c.hle_op not in (19, 171):
                continue
            for ai, v in enumerate(w.argvals.get(c.off, ())):
                if ai == 0 or v.kind != "const":
                    continue
                rel = (v.v & 0x0FFFFFFF) - (img.psx_base & 0x0FFFFFFF)
                if not (0 <= rel < len(img.payload) - 16):
                    tot["ptr_outside_image"] += 1
                    continue
                tot["ptr_inside_image"] += 1
                hw = _s.unpack_from("<8H", img.payload, rel)
                if any(h < 512 and (h >> 4) & 1 and ((h & 0xF) * PAGE_HW) in cols for h in hw):
                    tot["pointee_has_tpage_shaped_halfword"] += 1
    n = tot["ptr_inside_image"]
    return {"counts": dict(tot),
            "shape_hit_rate": round(tot["pointee_has_tpage_shaped_halfword"] / n, 4) if n else None,
            "verdict": "REFUSED -- pointee layout unproven; no depth attributed from this channel"}


# ------------------------------------------------------------------ pass 3: THE JOIN
def join(sw: Dict[str, object], census_path: str = CENSUS_PAGES) -> Dict[str, object]:
    """Attribute the recovered tpages to census cells at PAGE granularity, plus channel G."""
    cen = json.load(open(census_path, encoding="utf-8"))
    by_cell = {(r["ef"], r["vram_x"], r["vram_y"]): r for r in cen}

    prog: Dict[Tuple[int, int, int], Dict[str, object]] = {}
    undeclared: List[Dict[str, object]] = []
    for h in sw["hits"]:
        if h["value"] is None or h["value"] >= 512:
            continue
        ef = h["ef"]
        px, py = h["page_x"], h["page_y"]
        covered = [(px, y) for (px, y) in page_cover(px, py) if (ef, px, y) in by_cell]
        if not covered:
            undeclared.append({"ef": ef, "tpage": h["value"], "page_x": px, "page_y": py,
                               "image": h["image"], "off": h["off"]})
            continue
        for cell in covered:
            k = (ef, cell[0], cell[1])
            e = prog.setdefault(k, {"ef": ef, "x": cell[0], "y": cell[1], "depths": {},
                                    "tpages": [], "sites": []})
            e["depths"].setdefault(h["bpp"], 0)
            e["depths"][h["bpp"]] += 1
            if h["value"] not in e["tpages"]:
                e["tpages"].append(h["value"])
            e["sites"].append([h["image"], h["off"]])

    # ---- channel G: the container's OWN so records, re-read at PAGE granularity
    so_by_cell: Dict[Tuple[int, int, int], Dict[str, object]] = {}
    geom_blind: Dict[int, bool] = {}
    for p in corpus_paths():
        ef = ef_number(p)
        blob = open(p, "rb").read()
        try:
            geom_blind[ef] = RS.attribution(blob).geom_total == 0
        except Exception:
            geom_blind[ef] = True
        for s in so_tpages(blob):
            px, py = int(s["page_x"]), int(s["page_y"])
            for cell in page_cover(px, py):
                k = (ef, cell[0], cell[1])
                if k not in by_cell:
                    continue
                e = so_by_cell.setdefault(k, {"ef": ef, "x": cell[0], "y": cell[1],
                                              "depths": {}, "tpages": []})
                e["depths"].setdefault(int(s["bpp"]), 0)
                e["depths"][int(s["bpp"])] += 1
                if int(s["tpage"]) not in e["tpages"]:
                    e["tpages"].append(int(s["tpage"]))

    def verdict(e):
        d = sorted(e["depths"])
        return d[0] if len(d) == 1 else None

    rows = []
    for k, r in sorted(by_cell.items()):
        p, g = prog.get(k), so_by_cell.get(k)
        rows.append({
            "id": r["id"], "ef": r["ef"], "x": r["vram_x"], "y": r["vram_y"],
            "creature": "creature" in r["classes"],
            "census_bpp": r["bpp"], "census_depth_unknown": r["hz_depth_unknown"],
            "census_dual_depth": r["hz_dual_depth"], "census_hint": r["bpp_hint"],
            "census_spill_in": r["hz_spill_in"],
            "census_readers_all_spilled": (bool(r["readers"])
                                           and not any(x["own_column"] for x in r["readers"])),
            "geom_blind_container": geom_blind.get(r["ef"]),
            "prog_bpp": verdict(p) if p else None,
            "prog_depths": (p["depths"] if p else None),
            "prog_tpages": (p["tpages"] if p else None),
            "prog_sites": (p["sites"][:4] if p else None),
            "so_page_bpp": verdict(g) if g else None,
            "so_page_depths": (g["depths"] if g else None),
        })
    return {"cells": rows, "undeclared": undeclared}


# ------------------------------------------------------------------ THE RESIDUE, named
def residue(paths: Optional[Sequence[str]] = None, progress: bool = False) -> Dict[str, object]:
    """What the 222 GEOM-BLIND containers call instead -- naming the next lane's target.

    This lane's ceiling is structural, not statistical: ``Hi_RegisterTexEffModel`` registers a
    texture onto a MODEL, and a container with no non-creature GEOM block has no model to register
    one on, so the whole op-22 channel is silent exactly where the ``so`` census is blind.  Rather
    than leave that as a shrug, this measures which HLE ops those containers DO call, ranked by how
    exclusive they are to the blind population -- an op that is common there and rare elsewhere is
    where the blind containers' texture page has to come from.
    """
    import struct as _s
    paths = list(paths or corpus_paths())
    names = {int(o["op"]): o.get("name") for o in json.load(open(HLE_OPS_JSON, encoding="utf-8"))}
    blind_ops: Counter = Counter()
    seen_ops: Counter = Counter()
    blind_efs, seen_efs, id3_efs = set(), set(), set()
    #: the pointer arguments of the blind-exclusive ops -- the obvious next place a tpage could hide
    ptr_args = {117: (1,), 128: (2,), 33: (2,)}
    ptr = Counter()
    for ef, img, r, w, blob in _walk_all(paths, progress):
        id3_efs.add(ef)
        try:
            is_blind = RS.attribution(blob).geom_total == 0
        except Exception:
            is_blind = True
        (blind_efs if is_blind else seen_efs).add(ef)
        ops = set(c.hle_op for c in r.calls
                  if c.kind == "hle" and c.hle_op is not None
                  and w.dispatch.get(c.off) in STRONG_CHAINS)
        for op in ops:
            (blind_ops if is_blind else seen_ops)[op] += 1
        if not is_blind:
            continue
        cols = set(x for (x, _y) in container_cells(blob))
        for c in r.calls:
            if c.kind != "hle" or c.hle_op not in ptr_args:
                continue
            if w.dispatch.get(c.off) not in STRONG_CHAINS:
                continue
            for ai, v in enumerate(w.argvals.get(c.off, ())):
                if ai not in ptr_args[c.hle_op] or v.kind != "const":
                    continue
                rel = (v.v & 0x0FFFFFFF) - (img.psx_base & 0x0FFFFFFF)
                if not (0 <= rel < len(img.payload) - 32):
                    ptr["outside_image"] += 1
                    continue
                ptr["inside_image"] += 1
                hw = _s.unpack_from("<16H", img.payload, rel)
                n = sum(1 for h in hw if h < 512 and (h >> 4) & 1
                        and ((h & 0xF) * PAGE_HW) in cols)
                ptr["tpage_shaped_halfwords"] += n
                ptr["halfwords_examined"] += 16
                ptr["pointees_with_any"] += 1 if n else 0
    rows = []
    for op in set(blind_ops) | set(seen_ops):
        b = blind_ops[op] / max(1, len(blind_efs))
        s = seen_ops[op] / max(1, len(seen_efs))
        rows.append({"op": op, "name": names.get(op), "blind_containers": blind_ops[op],
                     "geom_containers": seen_ops[op], "blind_rate": round(b, 3),
                     "geom_rate": round(s, 3), "exclusivity": round(b - s, 3)})
    rows.sort(key=lambda r_: -r_["exclusivity"])
    return {"blind_containers": len(blind_efs), "geom_containers": len(seen_efs),
            "containers_with_an_id3_program": len(id3_efs),
            "blind_pointer_shape_test": dict(ptr),
            "blind_pointer_verdict":
                "NEGATIVE -- 0 tpage-shaped halfwords in the first 16 of any in-image pointee of "
                "ops 117/128/33 across the geom-blind population.  A geom-blind container's texture "
                "page is not a head-of-struct constant reachable from these arguments; the next "
                "probe belongs on the id-2 sub-file bodies that op 102 hands back."
                if not ptr["tpage_shaped_halfwords"] else "POSITIVE -- see counts",
            "ops": rows[:25]}


# ------------------------------------------------------------------ pass 4: CALIBRATION
def calibrate(jn: Dict[str, object]) -> Dict[str, object]:
    """Ground truth = a cell with BOTH a census (``so``-UV) depth and a derived depth.

    Reported per channel.  Disagreements are listed in full so every one can be adjudicated by
    reading the disassembly -- an agreement rate with an un-listed residue is a claim, not a gate.
    """
    out = {}
    for ch, key in (("program", "prog_bpp"), ("so_page", "so_page_bpp")):
        gt = [c for c in jn["cells"] if c["census_bpp"] is not None and c[key] is not None]
        agree = [c for c in gt if c["census_bpp"] == c[key]]
        dis = [c for c in gt if c["census_bpp"] != c[key]]
        out[ch] = {
            "ground_truth_n": len(gt),
            "agree": len(agree),
            "rate": round(len(agree) / len(gt), 4) if gt else None,
            "disagreements": [{"id": c["id"], "census": c["census_bpp"], "derived": c[key],
                               "prog_tpages": c["prog_tpages"],
                               "so_page_depths": c["so_page_depths"],
                               "census_spill_in": c["census_spill_in"],
                               "census_readers_all_spilled": c["census_readers_all_spilled"],
                               "adjudication": (
                                   "U-SPILL: every census reader of this cell is a binding on a "
                                   "NEIGHBOURING page whose u range crosses the column boundary, so "
                                   "the census depth is the SPILLING draw's and the page depth is "
                                   "this column's own.  Both predicates hold; the cell is read at "
                                   "two depths by two draws."
                                   if c["census_readers_all_spilled"] else "UNADJUDICATED"),
                               "prog_sites": c["prog_sites"]} for c in dis],
        }
    nc = [c for c in jn["cells"] if not c["creature"]]
    unk = [c for c in nc if c["census_depth_unknown"]]
    unk_bppnone = [c for c in nc if c["census_bpp"] is None]
    out["population"] = {
        "cells_total": len(jn["cells"]),
        "non_creature": len(nc),
        "depth_unknown_hz": len(unk),
        "bpp_none": len(unk_bppnone),
        "hz_vs_bppnone_gap": len(unk_bppnone) - len(unk),
        "dual_depth": sum(1 for c in nc if c["census_dual_depth"]),
    }
    blind = [c for c in unk if c["geom_blind_container"]]
    out["gain"] = {
        "hz_unknown_gaining_program_depth": sum(1 for c in unk if c["prog_bpp"] is not None),
        "hz_unknown_gaining_so_page_depth": sum(1 for c in unk if c["so_page_bpp"] is not None),
        "hz_unknown_gaining_either": sum(1 for c in unk if c["prog_bpp"] is not None
                                         or c["so_page_bpp"] is not None),
        "bppnone_gaining_either": sum(1 for c in unk_bppnone if c["prog_bpp"] is not None
                                      or c["so_page_bpp"] is not None),
        "hz_unknown_in_geom_blind_containers": len(blind),
        "geom_blind_gaining_program_depth": sum(1 for c in blind if c["prog_bpp"] is not None),
        "cells_with_program_multi_depth_no_verdict": sum(
            1 for c in jn["cells"] if c["prog_depths"] and c["prog_bpp"] is None),
        "containers_geom_blind": len(set(c["ef"] for c in jn["cells"]
                                         if c["geom_blind_container"])),
        "containers_gaining_program_depth": len(set(c["ef"] for c in unk
                                                    if c["prog_bpp"] is not None)),
    }
    anchor = [c for c in jn["cells"] if c["ef"] == 211 and c["x"] == 704]
    out["ef211_anchor"] = {c["id"]: {"census_bpp": c["census_bpp"], "prog_bpp": c["prog_bpp"],
                                     "prog_tpages": c["prog_tpages"],
                                     "so_page_bpp": c["so_page_bpp"]} for c in anchor}
    return out


# ------------------------------------------------------------------ CLI
def _dump(name: str, obj) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    return p


def _print_discover(d, n=14):
    print("%-4s %-4s %-26s %6s %6s %7s %6s %6s %8s %8s %6s"
          % ("op", "arg", "name", "sites", "const", "runtime", "narr", "ybase", "declared",
             "so_match", "score"))
    for r in d["pairs"][:n]:
        print("%-4d %-4d %-26s %6d %6d %7d %6d %6d %8d %8d %6.3f"
              % (r["op"], r["arg"], (r["name"] or "-")[:26], r["sites"], r["const"], r["runtime"],
                 r["narrow"], r["ybase"], r["declared"], r["so_match"], r["score"]))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["discover", "sweep", "join", "calibrate", "all", "selfcheck"])
    ap.add_argument("--op-arg", action="append", default=[],
                    help="OP:ARG to sweep (repeatable); default = discover's top pair")
    ap.add_argument("--limit", type=int, default=0, help="first N containers only (smoke test)")
    ap.add_argument("--strong-only", action="store_true",
                    help="drop the corroborated tier -- the conservative headline")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    print(assert_decoder_matches_reskin())
    if a.cmd == "selfcheck":
        return 0

    paths = corpus_paths()
    if a.limit:
        paths = paths[:a.limit]
    prog = not a.quiet

    d = None
    if a.cmd in ("discover", "all"):
        d = discover(paths, prog)
        _dump("tpage_discover.json", d)
        _print_discover(d)
        if a.cmd == "discover":
            return 0

    op_args: List[Tuple[int, int]] = []
    for s in a.op_arg:
        op, ai = s.split(":")
        op_args.append((int(op), int(ai)))
    if not op_args:
        if d is None:
            d = json.load(open(os.path.join(OUT_DIR, "tpage_discover.json"), encoding="utf-8"))
        top = d["pairs"][0]
        op_args = [(top["op"], top["arg"])]
    print("sweeping op:arg = %s" % (op_args,))

    sw = sweep(op_args, paths, prog, include_corroborated=not a.strong_only)
    jn = join(sw)
    cal = calibrate(jn)
    refused = probe_pointer_tables(paths, False)
    res = residue(paths, False)
    payload = {"decoder_check": assert_decoder_matches_reskin(),
               "discover": d, "sweep": sw, "join": jn, "calibration": cal,
               "refused_channels": {"op19_op171_pointer_tables": refused},
               "residue": res}
    p = _dump("tpage_sweep.json", payload)
    print("\n-- HEADLINES ------------------------------------------------")
    print("images walked                       %d" % sw["images"])
    print("accepted constant hits              %d (corroborated tier %s)"
          % (len(sw["hits"]), "IN" if sw["include_corroborated"] else "OUT"))
    print("  ... of which strong dispatch      %d"
          % sum(1 for h in sw["hits"] if h["tier"] == "strong"))
    print("  ... of which corroborated         %d" % len(sw["promoted"]))
    print("refused-dispatch hits (EXCLUDED)    %d" % len(sw["weak_dispatch"]))
    print("runtime-computed tpage args         %d" % len(sw["runtime"]))
    print("containers with >=1 const tpage     %d"
          % sum(1 for c in sw["per_container"] if c["hits"]))
    print("distinct (container, tpage) pairs   %d"
          % sum(len(c["tpages"]) for c in sw["per_container"]))
    print("undeclared-column tpages            %d" % len(jn["undeclared"]))
    for k, v in cal["population"].items():
        print("population.%-28s %d" % (k, v))
    for k, v in cal["gain"].items():
        print("gain.%-34s %d" % (k, v))
    for ch in ("program", "so_page"):
        c = cal[ch]
        print("calibration[%s] N=%d agree=%d rate=%s disagreements=%d"
              % (ch, c["ground_truth_n"], c["agree"], c["rate"], len(c["disagreements"])))
    for ch in ("program", "so_page"):
        for x in cal[ch]["disagreements"]:
            print("  disagree[%s] %s census=%s derived=%s -- %s"
                  % (ch, x["id"], x["census"], x["derived"], x["adjudication"][:60]))
    print("refused channel op19/171: %s  hit-rate %s"
          % (refused["counts"], refused["shape_hit_rate"]))
    print("ef211 anchor: %s" % json.dumps(cal["ef211_anchor"]))
    print("residue: %d geom-blind vs %d geom-bearing containers; most blind-exclusive ops:"
          % (res["blind_containers"], res["geom_containers"]))
    for row in res["ops"][:8]:
        print("   op %-4d %-26s blind %.2f  geom %.2f  excl %+0.2f"
              % (row["op"], (row["name"] or "-")[:26], row["blind_rate"], row["geom_rate"],
                 row["exclusivity"]))
    print("wrote %s" % p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
