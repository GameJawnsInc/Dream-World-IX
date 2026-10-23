r"""THE SCROLL-BLIT FOLD-IN -- `py scroll_blit_gates.py` prints S1..S6 with PASS/FAIL.

tier-r's DR_MOVE check (`tier-r/drmove_cells.py`, `CALLBACK-OPS.md` addendum 10) found that HLE op 144
-- a VRAM scroll blit -- rewrites 88 editable scenery cells in 20 containers every frame it runs, so a
repaint there is byte-correct on disk, deploys, verifies and never reaches the screen.  The kit now
carries the op-144 sites as a table (`ff9mapkit/summons/scroll_blit.py`), refuses at build an edit that
changes a texel inside a destination band, and discloses a source hit.  The table is a CACHE OF A
MEASUREMENT, so this runner re-derives it rather than trusting it:

S1  THE RE-DERIVATION PIN.  Every annotated listing under the SCRATCH `annot-r2` corpus is re-parsed
    through `drmove_cells.blit_rects` and compared with the shipped `_SITE_ROWS`, SITE FOR SITE.
S2  THE CORPUS VERDICT, TWO INSTRUMENTS.  The instrument's own `drmove_cells.analyse` and the kit's
    per-cell join (`scenery_texel_pages` -> `hazards.scroll_dst` / `scroll_src`) must name the SAME
    cells in the SAME containers, and both must equal the module's pins.
S3  THE PENDING CAST (ef407).  `x704_y384` -- the cell PLAN.md used to name as the gain-half vehicle
    -- refuses BY NAME with the measurement and the remedy `x704_y256`; the literal-boolean key lifts
    it and a truthy string does not; `x704_y256` builds and discloses where it propagates;
    `x640_y256` refuses and says its source is not editable here.
S4  THE PARTIAL BAND (ef211 `x640_y256`, the pool-wheel cell).  op 144 rewrites its left half from
    its right half: an edit confined to the right half builds with both disclosures, and ONE changed
    texel in the left half refuses, counted.
S5  THE ef211 CAST RECORD, READ BOTH WAYS.  The study's own cast specs, rebuilt from their SCRATCH
    art: the ink and punch wheels on `(704,256)` -- both INVISIBLE in game -- lie wholly in a FULL
    destination and refuse; the dome bands on `(704,384)` -- which showed -- are their SOURCE and build;
    the pool wheel on `(640,256)` -- which showed -- is PARTLY in a band; and cast 2b's bold wheel on
    `(576,384)` lies WHOLLY in a band and still showed -- the counter-witness that makes the key
    necessary.  With the key, each rebuilds the exact bytes it was cast with: the key moves no byte.
S6  PROVENANCE.  `scroll_blit.py` carries coordinates and counts only -- no bytes constant, no hex
    run, no integer outside the VRAM/coordinate range.
S7  THE EXECUTED-BLIT CROSS-CHECK.  The headless host's census (`headless/sfx_host.py`, SCRATCH only:
    the blits the user's own plugin actually EXECUTES) against the static table.  Every static
    destination cell on the edit surface must be observed executing, and the executed destinations
    the table does NOT hold must be exactly the pinned OPEN GAP -- so the gap cannot grow silently.
    The census is a cross-check and never the refusal's authority: the host stands actors at the
    origin with no battle camera, so a cell it never saw is "not observed", not "safe".

Reads `C:\gd\SCRATCH\summon-format` ONLY (S7 its `headless/census.json`) -- no install read, no
deploy, no install write, no commit.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import struct
import sys
import tempfile
import tomllib
from typing import List

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import scroll_blit as SB                  # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "tier-r")))
import drmove_cells as DM                                        # noqa: E402

_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
# THE WORKTREE PIN: a study script that silently imported the MAIN checkout's kit would grade the
# wrong code and pass.  Assert the module under test is THIS tree's.
assert os.path.normcase(os.path.abspath(SB.__file__)).startswith(
    os.path.normcase(os.path.join(_REPO, "ff9mapkit"))), SB.__file__

CORPUS = DM.A.SCRATCH_CORPUS
REPAINT_W6B = os.path.join(CORPUS, "repaint-w6b")
_FAILS: List[str] = []
_TMP = tempfile.mkdtemp(prefix="scrollblit-gates-")


def chk(name: str, got, want) -> None:
    """Compare a re-measured value against its pin; collect rather than raise, so the board prints."""
    if got != want:
        _FAILS.append("%s: measured %r, pinned %r" % (name, got, want))


def _load(ef: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % ef), "rb") as fh:
        return fh.read()


def _refuses(fn, *a, **kw):
    """``(fired, message)`` -- did the lane raise its OWN error class, and what did it say?"""
    try:
        fn(*a, **kw)
    except RP.RepaintError as e:
        return True, str(e)
    return False, ""


def _page(blob: bytes, ef: int, name: str):
    return next(p for p in RP.scenery_texel_pages(blob, ef) if p.name == name)


def _png(blob: bytes, page, raw: bytes, tag: str) -> str:
    """One cell's art at ITS OWN depth -- the dispatch the build itself uses."""
    path = os.path.join(_TMP, "%s.%s.png" % (page.name, tag))
    if page.direct:
        RP.write_direct_png(raw, page.w, page.h, path)
    elif page.bpp == 4:
        RP.write_indexed4_png(raw, RP.palette_words(blob, page), page.w, page.h, path)
    else:
        RP.write_indexed_png(raw, RP.palette_words(blob, page), page.w, page.h, path)
    return path


def _bump_halfwords(blob: bytes, page, raw: bytes, keep) -> bytes:
    """Move the texels of every halfword ``keep(col, row)`` selects, never across the DERIVED
    transparent boundary (a cutout crossing is a different law and would make the gate assert two
    things at once)."""
    stride = page.page_bytes // (2 * page.h)
    vals = list(RP.texel_view(page, raw))
    per = 1 if page.direct else KT.TEXELS_PER_HW[page.bpp]
    zeros = set(RP.transparent_values(blob, page)[0])
    top = 16 if page.bpp == 4 else 256
    opaque = [i for i in range(top) if i not in zeros]
    for i, v in enumerate(vals):
        hw = i // per
        if not keep(hw % stride, hw // stride):
            continue
        if page.direct:
            vals[i] = v if v == KT.DIRECT15_CUTOUT else ((v ^ 0x0421) | 0x0001)
        elif v not in zeros and len(opaque) > 1:
            vals[i] = opaque[(opaque.index(v) + 1) % len(opaque)]
    if page.direct:
        return struct.pack("<%dH" % len(vals), *vals)
    return RP.pack4(bytes(vals)) if page.bpp == 4 else bytes(vals)


def _spec(blob: bytes, ef: int, row: dict) -> dict:
    return {"reskin": {"effect": ef, "label": "scroll-blit-gate",
                       "expect_sha256": hashlib.sha256(blob).hexdigest(), "texel": [row]}}


def _row(page, src: str, **kw) -> dict:
    d = {"name": page.name, "source": src, "expect_cell": list(page.cell)}
    d.update(kw)
    return d


# --------------------------------------------------------------------------- S1
def s1_rederive() -> None:
    rows, unfolded = [], 0
    for f in sorted(os.listdir(DM.ANNOT)):
        m = re.match(r"ef(\d+)_c(\d+)\.asm$", f)
        if not m:
            continue
        for r in DM.blit_rects(os.path.join(DM.ANNOT, f)):
            if None in (r["x"], r["y"], r["w"], r["h"], r["sx"], r["sy"]):
                unfolded += 1
                continue
            rows.append((int(m.group(1)), int(m.group(2)), r["x"], r["y"], r["w"], r["h"],
                         r["sx"], r["sy"]))
    print("   re-parsed %d site(s) over %d container(s); %d excluded (a field did not fold)"
          % (len(rows), len({r[0] for r in rows}), unfolded))
    chk("S1 the sites, SITE FOR SITE, in listing order", tuple(rows), SB._SITE_ROWS)
    chk("S1 no site excluded", unfolded, 0)
    chk("S1 site count", len(rows), SB.SITES)
    chk("S1 container count", len({r[0] for r in rows}), SB.CONTAINERS)


# --------------------------------------------------------------------------- S2
def s2_two_instruments() -> None:
    dst, src, scanned, sites, unfolded, surfaced = DM.analyse()
    inst_d = {ef: set(v) for ef, v in dst.items()}
    inst_s = {ef: set(v) for ef, v in src.items()}
    kit_d, kit_s, surface = {}, {}, 0
    for ef in sorted(SB.SCROLL_BLITS):
        path = os.path.join(CORPUS, "ef%03d.bytes" % ef)
        if not os.path.isfile(path):
            continue
        for p in RP.scenery_texel_pages(_load(ef), ef):
            if not DM.cell_xy(p.name):
                continue
            surface += 1
            if p.hazards.scroll_dst:
                kit_d.setdefault(ef, set()).add(p.name)
            if p.hazards.scroll_src:
                kit_s.setdefault(ef, set()).add(p.name)
    print("   instrument: %d containers / %d sites / %d excluded / %d editable cells"
          % (scanned, sites, unfolded, surfaced))
    print("   kit join  : %d editable cells; DEST %d containers / %d cells; SOURCE %d / %d"
          % (surface, len(kit_d), sum(len(v) for v in kit_d.values()), len(kit_s),
             sum(len(v) for v in kit_s.values())))
    chk("S2 destination cells, kit vs instrument", kit_d, inst_d)
    chk("S2 source cells, kit vs instrument", kit_s, inst_s)
    chk("S2 edit surface", (surface, surfaced), (SB.EDIT_SURFACE_CELLS, SB.EDIT_SURFACE_CELLS))
    chk("S2 destination pins", (len(kit_d), sum(len(v) for v in kit_d.values())),
        (SB.DEST_CONTAINERS, SB.DEST_CELLS))
    chk("S2 source pins", (len(kit_s), sum(len(v) for v in kit_s.values())),
        (SB.SOURCE_CONTAINERS, SB.SOURCE_CELLS))


# --------------------------------------------------------------------------- S3
def s3_pending_cast() -> None:
    ef, blob = 407, _load(407)
    names = sorted(p.name for p in RP.scenery_texel_pages(blob, ef))
    print("   ef407 edit surface: %s" % ", ".join(names))
    chk("S3 ef407's whole edit surface", names,
        ["cell.s0.x640_y256", "cell.s0.x704_y256", "cell.s0.x704_y384"])
    every = lambda c, r: True                                    # noqa: E731

    dome = _page(blob, ef, "cell.s0.x704_y384")
    art = _png(blob, dome, _bump_halfwords(blob, dome, blob[dome.page_offset:dome.page_offset
                                                       + dome.page_bytes], every), "all")
    fired, msg = _refuses(RP.build, _spec(blob, ef, _row(dome, art)), "?", blob=blob)
    print("   x704_y384, unacknowledged: %s" % (msg[:240] + "..." if fired else "BUILT"))
    chk("S3 the named cast cell refuses", fired, True)
    for needle in ("SCROLL-BLIT DESTINATION", "cell.s0.x704_y384",
                   "paint the source cell `cell.s0.x704_y256`", "252 DR_MOVE blits",
                   SB.ACK_KEY):
        chk("S3 the refusal says %r" % needle, needle in msg, True)
    fired, msg = _refuses(RP.build, _spec(blob, ef, _row(dome, art, **{SB.ACK_KEY: "true"})), "?",
                          blob=blob)
    chk("S3 a truthy STRING refuses rather than arming", fired and "BOOLEAN" in msg, True)
    b = RP.build(_spec(blob, ef, _row(dome, art, **{SB.ACK_KEY: True})), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    chk("S3 the key lifts it and the build says what was lifted",
        "SCROLL-BLIT DESTINATION, acknowledged" in note and SB.ACK_KEY in note, True)

    src = _page(blob, ef, "cell.s0.x704_y256")
    art = _png(blob, src, _bump_halfwords(blob, src, blob[src.page_offset:src.page_offset
                                                     + src.page_bytes], every), "all")
    b = RP.build(_spec(blob, ef, _row(src, art)), "?", blob=blob)
    b.check = RP.self_check(b)
    note = "  ".join(b.enabled[0].hazard_notes)
    print("   x704_y256 (the SOURCE): built, self-check %d/%d"
          % (sum(1 for g in b.check.gates if g.ok), len(b.check.gates)))
    chk("S3 the source cell builds and its self-check passes", b.check.ok, True)
    chk("S3 the source cell discloses where it propagates",
        "SCROLL-BLIT SOURCE" in note and "(704,384)" in note, True)

    top = _page(blob, ef, "cell.s0.x640_y256")
    art = _png(blob, top, _bump_halfwords(blob, top, blob[top.page_offset:top.page_offset
                                                     + top.page_bytes], every), "all")
    fired, msg = _refuses(RP.build, _spec(blob, ef, _row(top, art)), "?", blob=blob)
    chk("S3 x640_y256 refuses too", fired and "SCROLL-BLIT DESTINATION" in msg, True)
    chk("S3 ...and says its source (640,384) is not an editable cell here",
        "(640,384)" in msg and "no cell to paint instead" in msg, True)


# --------------------------------------------------------------------------- S4
def s4_partial_band() -> None:
    ef, blob = 211, _load(211)
    pool = _page(blob, ef, "cell.s0.x640_y256")
    raw = blob[pool.page_offset:pool.page_offset + pool.page_bytes]
    bands = [b.describe() for b in pool.hazards.scroll_dst]
    print("   ef211 x640_y256 destination: %s" % "; ".join(bands))
    chk("S4 one destination blit, the left half, fed from the right half",
        [(b.dst, b.size, b.src) for b in pool.hazards.scroll_dst],
        [((640, 256), (32, 128), (672, 256))])
    chk("S4 the band is exactly half the cell", len(pool.hazards.scroll_rewritten), 32 * 128)
    right = _png(blob, pool, _bump_halfwords(blob, pool, raw, lambda c, r: c >= 32), "right")
    b = RP.build(_spec(blob, ef, _row(pool, right)), "?", blob=blob)
    note = "  ".join(b.enabled[0].hazard_notes)
    chk("S4 a right-half edit builds, clear of the band",
        "SCROLL-BLIT DESTINATION, clear" in note, True)
    chk("S4 ...and discloses that it is the band's SOURCE", "SCROLL-BLIT SOURCE" in note, True)
    one = _png(blob, pool, _bump_halfwords(blob, pool, raw, lambda c, r: c >= 32 or (c, r) == (5, 7)),
               "one")
    fired, msg = _refuses(RP.build, _spec(blob, ef, _row(pool, one)), "?", blob=blob)
    chk("S4 one changed halfword inside the band refuses, counted",
        fired and "1 of this edit's" in msg, True)
    chk("S4 ...and the remedy is the same cell's own source band",
        "in THIS cell" in msg and "(672,256)" in msg, True)


# --------------------------------------------------------------------------- S5
#: ``(spec, cell, kind, the sha the staged cast container carries)`` -- the shas are read off each
#: cast's own SCRATCH build manifest (`patched_sha256`), never typed from memory.
CASTS = (("phoenix_field.toml", "cell.s0.x704_y256", "full", "ef211"),           # invisible
         ("phoenix_field_punch.toml", "cell.s0.x704_y256", "full", "ef211-punch"),  # invisible
         ("phoenix_field_cast2.toml", "cell.s0.x576_y384", "in-band", "ef211-cast2"),  # SHOWED
         ("phoenix_field_cast3.toml", "cell.s0.x640_y256", "partial", "ef211-pool"),  # showed
         ("phoenix_dome.toml", "cell.s0.x704_y384", "source", None))               # showed


def s5_retrodiction() -> None:
    blob = _load(211)
    for spec_name, cell, kind, staged in CASTS:
        with open(os.path.join(_HERE, spec_name), "rb") as fh:
            spec = tomllib.load(fh)
        rows = spec["reskin"]["texel"]
        if not all(os.path.isfile(r["source"]) for r in rows if r.get("enabled", True)):
            _FAILS.append("S5 %s: its SCRATCH art is missing" % spec_name)
            continue
        bare = json.loads(json.dumps(spec))
        for r in bare["reskin"]["texel"]:
            r.pop(SB.ACK_KEY, None)
        fired, msg = _refuses(RP.build, bare, os.path.join(_HERE, spec_name), blob=blob)
        line = "%-26s %-18s %-7s " % (spec_name, cell, kind)
        if kind == "source":
            chk("S5 %s (the dome, a SOURCE) builds without the key" % spec_name, fired, False)
            b = RP.build(spec, os.path.join(_HERE, spec_name), blob=blob)
            chk("S5 %s discloses the propagation" % spec_name,
                "SCROLL-BLIT SOURCE" in "  ".join(b.enabled[0].hazard_notes), True)
            print("   " + line + "builds, discloses the scroll (no key, no refusal)")
            continue
        m = re.search(r"(\d+) of this edit's (\d+) changed halfword", msg)
        chk("S5 %s refuses as a scroll-blit destination without the key" % spec_name,
            fired and "SCROLL-BLIT DESTINATION" in msg, True)
        if m and kind in ("full", "in-band"):
            chk("S5 %s: EVERY changed halfword is in the band" % spec_name, m.group(1), m.group(2))
        if m and kind == "partial":
            chk("S5 %s: SOME but not all changed halfwords are in the band" % spec_name,
                0 < int(m.group(1)) < int(m.group(2)), True)
        chk("S5 %s carries the key, literally" % spec_name,
            all(r.get(SB.ACK_KEY) is True for r in rows if r.get("enabled", True)), True)
        b = RP.build(spec, os.path.join(_HERE, spec_name), blob=blob)
        want = None
        if staged:
            with open(os.path.join(REPAINT_W6B, staged, "build_manifest.json"),
                      encoding="utf-8") as fh:
                want = json.load(fh)["patched_sha256"]
        chk("S5 %s rebuilds the bytes it was cast with" % spec_name, b.sha_out, want)
        print("   " + line + "refuses (%s of %s changed halfwords in the band); with the key "
              "sha %s %s" % (m.group(1) if m else "?", m.group(2) if m else "?", b.sha_out[:12],
                             "== the cast" if b.sha_out == want else "!= the cast %s" % want))


# --------------------------------------------------------------------------- S6
def s6_provenance() -> None:
    path = SB.__file__
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src)
    blobs = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, bytes)]
    ints = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
            and isinstance(n.value, int) and not isinstance(n.value, bool)]
    hexrun = re.findall(r"(?:\\x[0-9a-fA-F]{2}){4,}|\b[0-9a-fA-F]{16,}\b", src)
    print("   %s: %d bytes constant(s), %d int literal(s) (max %d), %d hex run(s)"
          % (os.path.basename(path), len(blobs), len(ints), max(ints), len(hexrun)))
    chk("S6 no bytes constant", len(blobs), 0)
    chk("S6 no hex run", hexrun, [])
    chk("S6 every integer is a coordinate, a size, an id or a count", max(ints) <= 8192, True)


# --------------------------------------------------------------------------- S7
CENSUS = os.path.join(CORPUS, "headless", "census.json")
#: THE OPEN GAP, by name: editable cells (not already refused as a program-VRAM write) the plugin
#: executes a DR_MOVE into while the static op-144 table names no rect over them.  The kit licenses
#: these today; folding them in is its own task.
KNOWN_GAP = frozenset({(226, "cell.s0.x448_y384"), (226, "cell.s0.x512_y384"),
                       (509, "cell.s0.x448_y384"), (509, "cell.s0.x512_y384")})


def s7_executed_crosscheck() -> None:
    if not os.path.isfile(CENSUS):
        _FAILS.append("S7: no headless census at %s -- run studies/custom-summons/headless/ first"
                      % CENSUS)
        return
    with open(CENSUS, encoding="utf-8") as fh:
        rows = {int(r["effect"]): r for r in json.load(fh)["rows"].values()}
    ex = {ef: (r.get("dr_move_dst_cells") or {}) for ef, r in rows.items()}
    executing = {ef for ef, v in ex.items() if v}
    seen, unseen, gap = 0, [], set()
    for ef in sorted(executing | set(SB.SCROLL_BLITS)):
        if not os.path.isfile(os.path.join(CORPUS, "ef%03d.bytes" % ef)):
            continue
        for p in RP.scenery_texel_pages(_load(ef), ef):
            key = "x%d_y%d" % p.cell
            if p.hazards.scroll_dst:
                if key in ex.get(ef, {}):
                    seen += 1
                else:
                    unseen.append((ef, p.name))
            elif key in ex.get(ef, {}) and p.hazards.program not in ("write", "unknown"):
                gap.add((ef, p.name))
    print("   census: %d containers execute DR_MOVE, %d (container, destination cell) pairs"
          % (len(executing), sum(len(v) for v in ex.values())))
    print("   static destination cells on the edit surface observed executing: %d / %d"
          % (seen, seen + len(unseen)))
    print("   OPEN GAP -- executed, editable, unpinned: %s"
          % ", ".join("ef%03d %s" % g for g in sorted(gap)))
    chk("S7 every static container executes", sorted(set(SB.SCROLL_BLITS) - executing), [])
    chk("S7 every static destination cell is observed executing", unseen, [])
    chk("S7 the static destination count", seen, SB.DEST_CELLS)
    chk("S7 the open gap is exactly the pinned one", sorted(gap), sorted(KNOWN_GAP))


GATES = [
    ("S1", "THE RE-DERIVATION PIN -- every site re-parsed and compared", s1_rederive),
    ("S2", "THE CORPUS VERDICT -- the kit's join == the instrument's, == the pins", s2_two_instruments),
    ("S3", "THE PENDING CAST -- ef407 x704_y384 refuses by name, the source builds", s3_pending_cast),
    ("S4", "THE PARTIAL BAND -- ef211 x640_y256, refused by the texel, not the cell", s4_partial_band),
    ("S5", "THE ef211 CAST RECORD, READ BOTH WAYS -- and the key moves no byte", s5_retrodiction),
    ("S6", "PROVENANCE -- coordinates and counts, never a stock byte", s6_provenance),
    ("S7", "THE EXECUTED-BLIT CROSS-CHECK -- 88/88 run headless; the open gap pinned",
     s7_executed_crosscheck),
]


def main(argv=None) -> int:
    only = set(a.upper() for a in (argv or sys.argv[1:]) if a.upper().startswith("S"))
    print("SCROLL-BLIT GATES -- op 144 folded into the texel lane, the table re-derived")
    print("corpus: %s" % CORPUS)
    print("=" * 72)
    board = []
    for tag, title, fn in GATES:
        if only and tag not in only:
            continue
        before = len(_FAILS)
        print("%s  %s" % (tag, title))
        try:
            fn()
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
