r"""TIER W rung W6q -- THE RUNG'S OWN GATE RUNNER.  `py w6q_gates.py` prints G1..G18 with PASS/FAIL.

W6q ships `--quantize` as a new **`paint`** art lane plus THREE keys on `[[reskin.texel]]`
(`source_paint`, `acknowledge_quantize`, `acknowledge_recoloured_palette`).  It writes INDICES ONLY
and ZERO CLUT bytes, so `_regions`, `_orthogonality`, `_gate_spans`, the cutout law, the region
invariant and the page-cell derivation identity all run UNCHANGED and unrouted-around.
`--mint-clut` stays DEFERRED, now with a shipped `MINT_CLUT_REASON` that has a real call site.

The one sentence the record changes: the deferral said *"a lane whose no-op is not a no-op cannot
carry a byte-identity gate."*  That is true of a STATELESS quantizer and false of one holding the
container -- THE INCUMBENT LOCK, which makes the container's own index the first term of the
selection order.  G1 is that claim in its falsifiable form.

G1  ★ THE NO-OP, AT CORPUS SCALE.  export -> paint-lane import -> 0 changed bytes on every lawful
    surface.  THE TAMPER IS THE CALIBRATION: delete the incumbent clause from the sort key and the
    naive rule moves 767,531 texels across 191 of 240 surfaces -- and exactly 1,844 of 16,384 on
    `ef251 tex.part0`, the published figure the shipped `rgba` refusal quotes.
G2  THE RENDER/READ IDENTITY, exhaustive over BOTH renderings, plus `(v*255//31)>>3 == v` for all 32.
G3  DETERMINISM: 4 separate processes with different PYTHONHASHSEED, the alternate rows permuted,
    and -- because the seed sweep provably CANNOT catch a set-iterating tie-break (small ints hash to
    themselves) -- an AST check that no set/dict is iterated anywhere in the decision path.
G4  THE ALPHA-GOVERNS RULE: 502 accidental holes without it, 0 with it, on `ef227 tex.part0`.
G5  ★ THE ALTERNATE-SPLIT REFUSAL fires by name on `ef226 cell.s0.x448_y256` (42 of 43 groups split).
G6  ...AND IT DOES NOT OVER-FIRE on `ef211 cell.s0.x576_y256` (class C, 1 alternate, 0 split) -- and
    the PASS PATH itself runs: a NON-split group on ef226 is checked, passes, and BUILDS.
G6b ★ OPEN RISK 1 MEASURED: the share of the exportable class-C surface R7 blocks at 4/8/40 degrees,
    with an unedited control that must be byte-exact and refusal-free.  Control asserted, sweep
    DISCLOSED -- pricing it is the owner's call, not this rung's.
G7  THE COMPOSED-PALETTE REFUSAL (R9) fires, naming N of M and the target.
G8  ...AND IT DOES NOT OVER-FIRE when the CLUT target is on a different palette.
G9  ZERO CLUT BYTES on every paint build, composed ones included.
G10 THE REGION INVARIANT + THE PAGE-CELL DERIVATION IDENTITY under a paint splice, at the existing
    call site, against PRISTINE stock -- and the perturbed-rect-table tamper still fires by name.
G11 THE FOUR CAST-PROVEN ARTIFACTS still rebuild byte-exact.
G12 THE KEY-SET PINS, all three tables: the three new keys are known; `quantize` / `mint_clut` are
    STILL unknown keys, on `[[reskin.texel]]`, on `[[reskin.target]]` and under `[reskin]`.
G13 EVERY SHIPPED SPEC STILL LOADS under W6q-0's new gates, ENUMERATED FROM THE TREE, never listed.
G14 `_SUMMON_ART_LANES == repaint.ART_LANES`.
G15 THE REFUSAL-STRING PINS: `INDEXED_RGBA_REASON` verbatim at all three shipped sites, `1,844` /
    `8.31%` / `93/93` verbatim, the `rgba` lane still refuses, `MINT_CLUT_REASON` quoted by R12.
G16 ★ THE RE-DERIVATION PIN.  Every headline number this rung quotes is RE-MEASURED here, not
    restated: a constant that is a cache of a measurement has to be re-measured somewhere.
G17 THE FAIL-SAFES ARE LABELLED, NOT CLAIMED -- each with its population and the words FAIL-SAFE /
    structurally unreachable.
G18 PROVENANCE: a byte-literal scan of every committable file this rung adds, against all 372 corpus
    containers; every decoded page goes through `export.assert_local_only`.

Reads the extracted corpus at C:\gd\SCRATCH\summon-format ONLY -- no install read except G11's
(which rebuilds from the corpus), NO deploy, no install write, no git commit.  Every number is
measured in the gate body.  G1 and G16 share ONE corpus pass; nothing else is slow.
"""
from __future__ import annotations

import colorsys
import json
import os
import struct
import subprocess
import sys
import tempfile
from typing import Dict, List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

# A gate runner that CRASHES on its own report is a gate runner nobody can read: Windows consoles
# default to cp1252 and this file's report uses the study's own marks.  Never silently -- errors are
# replaced, so a lost character is visible rather than fatal.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                            # pragma: no cover - non-tty
        pass

import reskin as RS_STUDY                                        # noqa: E402,F401 (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit import cli                                        # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import export as KE                       # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import reskin as RS                       # noqa: E402
from ff9mapkit.summons import texture as KT                      # noqa: E402

CORPUS = W.SCRATCH_CORPUS
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # <repo>

# --------------------------------------------------------------------------- THE FIXTURES
#: ★ THE ALTERNATE-SPLIT FIXTURE.  Chosen for the co-transform fixture's own reason: its only
#: quantize-class hazard is this one, so a refusal there can only be THIS refusal.
SPLIT_EF, SPLIT_CELL = 226, "cell.s0.x448_y256"
#: its clean counterpart -- class C, 1 alternate, 0 duplicate groups, 0 split.
CLEAN_EF, CLEAN_CELL = 211, "cell.s0.x576_y256"
#: the calibration page: the `rgba` refusal's own published 1,844 / 16,384.
CAL_EF, CAL_PAGE = 251, "tex.part0"
#: the alpha-governs page, and the census page §1.8 measured.
HUE_EF, HUE_PAGE = 227, "tex.part0"

#: THE FOUR CAST-PROVEN ARTIFACTS, as HASHES.  Not data -- no container byte is committed anywhere.
CLUT_PINS = {
    "bahamut_reskin.toml": (227, "7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a"),
    "phoenix_reskin.toml": (211, "4daab8ade69315e6452a96e5af1092c1bb943e1cec78968f3d9dc20e4d276790"),
    "madeen_reskin.toml": (251, "78b395f89e6114f0639e4463819460eafe9952b4707769ca6ea5b92d474a373b"),
}
W6A_COMPOSED_SHA256 = "813a7ea4c461a06beec6bfe62ec47b61f7e81589d6d94cc17bad5489e18a8682"
W4_PATCHED_SHA256 = CLUT_PINS["bahamut_reskin.toml"][1]
W6A_TEXEL_BYTES = 1032

#: the files THIS rung adds to the checkout.  G18 scans every one of them for a literal run of stock
#: bytes against all 372 corpus containers.
COMMITTABLE = ("w6q_gates.py", "w6q_QUANTIZE.md")

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


def _effects():
    for n in sorted(os.listdir(CORPUS)):
        if n.startswith("ef") and n.endswith(".bytes") and len(n) == 11:
            yield int(n[2:5]), os.path.join(CORPUS, n)


def _tmp() -> str:
    global _TMP
    if _TMP is None:
        _TMP = tempfile.mkdtemp(prefix="w6qgates-")
    return _TMP


def _refuses(fn, *a, **kw):
    """``(fired, message)`` -- did this raise one of the LANE's OWN error classes, and what did it say?

    A refusal that raised the wrong exception type is not a refusal: it is a crash that happened to
    stop the build, and it stops being one the day the call site grows a ``try``.
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


def _paint_row(name: str, src: str, **extra) -> dict:
    d = {"name": name, "source_paint": src, "enabled": True, "acknowledge_quantize": True}
    d.update(extra)
    return d


def _lawful_surfaces(blob: bytes, ef: int):
    """EXACTLY what ``export_art(lane="paint")`` emits: the id-4 creature pages plus every 4/8bpp
    scenery cell the derivation does not refuse by name.

    ⚠ OPEN RISK 3: the study's page-scope-safe count (76) and the export predicate's own emitted
    count are DIFFERENT QUESTIONS and neither sharpens the other.  This gate ships against the
    predicate's own verdict and REPORTS the number rather than hard-coding either.
    """
    pages = RP.creature_texel_pages(blob)
    try:
        scen, refused = RP.scenery_surface(blob, ef)
    except Exception:
        scen, refused = [], []
    bad = {r.name for r in refused}
    return list(pages), [p for p in scen if p.bpp in (4, 8) and p.name not in bad]


#: ★ W6b-3 SPLIT THE CENSUS SURFACE FROM THE AUTHOR-FACING ONE, AND THIS BOARD STRADDLES BOTH.
#:
#: :func:`_lawful_surfaces` rolls the CENSUS scope (``scenery_surface``'s own default) -- that is the
#: population every number in this file is about, and W6b-3 leaves it BYTE-IDENTICAL (0 census cells
#: gained or lost, pinned by `w6b3i_gates` I4).  But :func:`~ff9mapkit.summons.repaint.texel_page`
#: resolves at ``LICENSED_CHANNELS``, which since W6b-3 consults CHANNEL A -- and channel A's two
#: hazard classes hold **VETO** power: they can WITHDRAW a page an earlier channel emitted.  So a
#: census cell can now be REFUSED on the author-facing path, and a bare ``texel_page`` sweep over the
#: census aborts this whole board on the first one.
#:
#: The board therefore SKIPS what an author can no longer reach and **states the difference instead
#: of absorbing it**: :func:`_author_surface_withdrawals` re-derives the set from the shipped
#: predicate every run and G6b pins it BY NAME, so a withdrawal of a DIFFERENT cell -- or one under a
#: class that is not channel A's -- turns this board RED rather than disappearing into a ``try``.
CHANNEL_A_VETO = ("array-dual-depth", "array-vs-column-depth")

#: the census class-C cells the AUTHOR-FACING surface withdraws.  MEASURED through the shipped
#: predicate (never a hand list -- the list is here so a CHANGE is visible, and G6b re-derives it).
W6B3_WITHDRAWN = ((179, "cell.s0.x448_y256"),)

_WITHDRAWN = None


def _author_surface_withdrawals(records) -> List[Tuple[int, str, str]]:
    """``[(effect, cell name, refusal class)]`` for every census cell the AUTHOR-FACING surface
    refuses -- rolled from ``scenery_surface(..., LICENSED_CHANNELS)`` so the class is the
    predicate's own name rather than a substring scraped off a ``RepaintError``."""
    global _WITHDRAWN
    if _WITHDRAWN is not None:
        return _WITHDRAWN
    by_ef: Dict[int, set] = {}
    for rec in records:
        by_ef.setdefault(rec["ef"], set()).add(rec["name"])
    out: List[Tuple[int, str, str]] = []
    for ef, names in sorted(by_ef.items()):
        blob = _load(ef)
        try:
            pages, refused = RP.scenery_surface(blob, ef, channels=RP.LICENSED_CHANNELS)
        except Exception:                                        # pragma: no cover - derivation refusal
            continue
        served = {p.name for p in pages}
        for r in refused:
            if r.name in names and r.name not in served:
                out.append((ef, r.name, r.klass))
    _WITHDRAWN = sorted(set(out))
    return _WITHDRAWN


def _paint_source(blob: bytes, page, out_dir: str) -> str:
    """Render this page's paint file exactly as ``export_art`` would, without an export."""
    words = RP.palette_words(blob, page)
    raw = blob[page.page_offset:page.page_offset + page.page_bytes]
    dst = os.path.join(out_dir, "%s.paint.png" % page.name.replace(".", "_"))
    RP.write_paint_png(RP.texel_view(page, raw), words, page.w, page.h, dst)
    return dst


def _naive_moved(words, idx, zset, c_op, c_z) -> int:
    """★ THE TAMPER, computed rather than executed: nearest-colour with the INCUMBENT CLAUSE DELETED,
    tie -> lowest index.

    On an unedited page the painted colour is the incumbent's own colour, so the exact class is
    non-empty and 'nearest' collapses to 'the members carrying that word'.  A texel therefore moves
    exactly when its index is not the LOWEST member of its own colour's group.  That is what the
    no-op costs without the lock, and it is the shape the published 1,844 was measured in.
    """
    low = {}
    for i in c_op:
        key = words[i] & 0x7FFF
        if key not in low:
            low[key] = i
    zlow = c_z[0] if c_z else None
    moved = 0
    for s in idx:
        if s >= len(words):
            continue
        if s in zset:
            moved += 1 if (zlow is not None and zlow != s) else 0
            continue
        want = low.get(words[s] & 0x7FFF)
        moved += 1 if (want is not None and want != s) else 0
    return moved


# --------------------------------------------------------------------------- the shared corpus pass
_CENSUS = None


def census() -> dict:
    """ONE pass over all 372 containers, feeding G1 and G16.  Every number is measured here."""
    global _CENSUS
    if _CENSUS is not None:
        return _CENSUS
    td = _tmp()
    c = {
        "surfaces": 0, "texels": 0, "noop_exact": 0, "noop_moved_total": 0,
        "naive_moved": 0, "naive_creature": 0, "naive_scenery": 0, "naive_surfaces": 0,
        "amb_creature": 0, "amb_scenery": 0, "tex_creature": 0, "tex_scenery": 0,
        "n_creature": 0, "n_scenery": 0,
        "dup_c": 0, "dup_c_tot": 0, "dup_c_rows": 0, "dup_c_worst": 0,
        "dup_s": 0, "dup_s_tot": 0, "dup_s_live": 0, "dup_s_live_tot": 0,
        "dup_s_rows": 0, "dup_s_worst": 0, "pal_rows_scen": 0,
        "stp_c": 0, "stp_c_rows": 0, "stp_s": 0, "stp_s_rows": 0, "stp_by_ef": {},
        "no_hole": 0, "hole_not_zero": 0, "creature_no_hole": 0,
        "rows4": 0, "rows4_full16": 0, "rows4_spend_all": 0,
        "budget_c": 0, "budget_s": 0, "tightest": ("", 0, 0),
        "distinct_live": [], "covered": [], "classC": [], "per_page": {},
    }
    for ef, path in _effects():
        with open(path, "rb") as fh:
            blob = fh.read()
        try:
            pmap = RS.palette_map(blob, effect=ef)
        except Exception:
            pmap = None
        if pmap is not None:
            for pal in pmap.palettes:
                w = struct.unpack_from("<%dH" % pal.entries, blob, pal.off)
                g, gl = {}, {}
                for x in w:
                    g[x] = g.get(x, 0) + 1
                    if x:
                        gl[x] = gl.get(x, 0) + 1
                rep = sum(n - 1 for n in g.values() if n > 1)
                repl = sum(n - 1 for n in gl.values() if n > 1)
                worst = max(g.values())
                # STP COLOUR GROUPS: 15-bit colour equal, bit 15 differing.  Colour 0 is EXCLUDED on
                # purpose -- 0x0000 is the CUTOUT and 0x8000 is an opaque black, so the two never sit
                # in one candidate set (alpha governs which set a texel draws from) and counting them
                # would report a pair the tie-break can never see.
                cg = {}
                for x in w:
                    cg.setdefault(x & 0x7FFF, set()).add(x >> 15)
                nstp = sum(1 for k, v in cg.items() if len(v) > 1 and k != 0)
                if pal.slot < 0:
                    c["dup_c"] += rep
                    c["dup_c_tot"] += len(w)
                    c["dup_c_rows"] += 1 if rep else 0
                    c["dup_c_worst"] = max(c["dup_c_worst"], worst)
                    c["stp_c"] += nstp
                    c["stp_c_rows"] += 1 if nstp else 0
                else:
                    c["pal_rows_scen"] += 1
                    c["dup_s"] += rep
                    c["dup_s_tot"] += len(w)
                    c["dup_s_live"] += repl
                    c["dup_s_live_tot"] += sum(1 for x in w if x)
                    c["dup_s_rows"] += 1 if rep else 0
                    c["dup_s_worst"] = max(c["dup_s_worst"], worst)
                    c["stp_s"] += nstp
                    c["stp_s_rows"] += 1 if nstp else 0
                    if nstp:
                        c["stp_by_ef"][ef] = c["stp_by_ef"].get(ef, 0) + nstp
        pages, cells = _lawful_surfaces(blob, ef)
        c["n_creature"] += len(pages)
        c["n_scenery"] += len(cells)
        for p in list(pages) + list(cells):
            words = RP.palette_words(blob, p)
            raw = blob[p.page_offset:p.page_offset + p.page_bytes]
            idx = RP.texel_view(p, raw)
            zset = set(RP.transparent_indices(words))
            c_op = [i for i in range(len(words)) if i not in zset]
            c_z = sorted(zset)
            n = len(idx)
            c["surfaces"] += 1
            c["texels"] += n
            # ---- G1: THE NO-OP, through the REAL codec on the REAL rendered file ----------------
            src = _paint_source(blob, p, td)
            back, cen = RP.read_paint_png(src, p, words, idx,
                                          RP.alternate_palette_rows(blob, p, pmap) if pmap else ())
            mv = sum(1 for i in range(len(raw)) if raw[i] != back[i])
            c["noop_moved_total"] += mv
            c["noop_exact"] += 1 if mv == 0 else 0
            os.remove(src)
            # ---- the TAMPER, computed ----------------------------------------------------------
            nv = _naive_moved(words, idx, zset, c_op, c_z)
            c["naive_moved"] += nv
            c["naive_surfaces"] += 1 if nv else 0
            grp = {}
            for x in words:
                grp[x] = grp.get(x, 0) + 1
            amb = sum(1 for s in idx if s < len(words) and grp[words[s]] > 1)
            c["per_page"]["ef%03d/%s" % (ef, p.name)] = (nv, amb, n)
            live = sum(1 for x in words if x)
            distinct = len({x & 0x7FFF for x in words if x})
            if p.kind == "creature":
                c["naive_creature"] += nv
                c["amb_creature"] += amb
                c["tex_creature"] += n
                c["distinct_live"].append(distinct)
                c["creature_no_hole"] += 0 if c_z else 1
                cov = RP.coverage(blob, p.index)
                if cov.available:
                    c["covered"].append(cov.covered / float(cov.total))
                    # THE ENTRY BUDGET, |H| <= B, over the UV-COVERED texels and the LIVE entries:
                    # the cutout is not a colour a fit could claim, on either side of the comparison.
                    need = len({idx[i] for i in range(n) if cov.mask[i]} - zset)
                    B = sum(1 for x in words if x)
                    c["budget_c"] += 1 if need <= B else 0
                    if need > c["tightest"][1]:
                        c["tightest"] = ("ef%03d %s" % (ef, p.name), need, B)
            else:
                c["naive_scenery"] += nv
                c["amb_scenery"] += amb
                c["tex_scenery"] += n
                if not c_z:
                    c["no_hole"] += 1
                elif c_z[0] != 0:
                    c["hole_not_zero"] += 1
                if p.bpp == 4:
                    c["rows4"] += 1
                    c["rows4_full16"] += 1 if distinct >= 16 else 0
                    c["rows4_spend_all"] += 1 if live >= 16 else 0
                c["budget_s"] += 1 if len({int(v) for v in idx} - zset) <= sum(
                    1 for x in words if x) else 0
                c["rows_spend_all"] = c.get("rows_spend_all", 0)
                if p.bpp == 4:
                    c["rows4_all_indices_used"] = c.get("rows4_all_indices_used", 0) + (
                        1 if len({int(v) for v in idx}) == len(words) else 0)
                    c["rows4_all_distinct_words"] = c.get("rows4_all_distinct_words", 0) + (
                        1 if len(set(words)) == len(words) else 0)
                alts = RP.alternate_palette_rows(blob, p, pmap) if pmap else ()
                if alts:
                    by = {}
                    for i, x in enumerate(words):
                        by.setdefault(x, []).append(i)
                    dupg = [m for m in by.values() if len(m) > 1]
                    split, sgm, worst_m = 0, set(), 0
                    for m in dupg:
                        for a in alts:
                            if len({a.words[i] if i < len(a.words) else 0 for i in m}) > 1:
                                split += 1
                                sgm.update(m)
                                worst_m = max(worst_m, len(m))
                                break
                    c["classC"].append({
                        "ef": ef, "name": p.name, "alts": len(alts), "groups": len(dupg),
                        "split": split, "on_split": sum(1 for s in idx if s in sgm),
                        "texels": n, "worst": worst_m})
    _CENSUS = c
    return c


# --------------------------------------------------------------------------- G1
def g1_the_no_op():
    if not _have_corpus():
        return gate("G1 the no-op at corpus scale", False, "no extracted corpus at %s" % CORPUS)
    c = census()
    lines, ok = [], True
    lines.append("%-52s %d surfaces (%d creature + %d scenery), %s texels"
                 % ("THE LAWFUL PAINT SURFACE (the export's own verdict)", c["surfaces"],
                    c["n_creature"], c["n_scenery"], "{:,}".format(c["texels"])))
    ok = ok and c["surfaces"] > 0
    good = c["noop_exact"] == c["surfaces"] and c["noop_moved_total"] == 0
    ok = ok and good
    lines.append("%-52s %d of %d surfaces, %d container byte(s) moved"
                 % ("★ THE NO-OP IS EXACT (export -> paint import)", c["noop_exact"],
                    c["surfaces"], c["noop_moved_total"]))
    # THE TAMPER IS THE CALIBRATION, not merely a non-zero: it must re-find the published figures.
    cal = c["per_page"].get("ef%03d/%s" % (CAL_EF, CAL_PAGE), (None, None, None))
    pins = [("naive texels moved", c["naive_moved"], 767531),
            ("   ...creature half", c["naive_creature"], 88631),
            ("   ...scenery half", c["naive_scenery"], 678900),
            ("   ...surfaces affected", c["naive_surfaces"], 191),
            ("★ ef251 tex.part0 (the rgba refusal's own figure)", cal[0], 1844)]
    for label, got, want in pins:
        hit = got == want
        ok = ok and hit
        lines.append("%-52s %s (published %s) %s"
                     % ("TAMPER -- delete the incumbent clause: " + label if label.startswith("naive")
                        else "TAMPER: " + label,
                        "{:,}".format(got) if isinstance(got, int) else got,
                        "{:,}".format(want), "" if hit else "*** MISMATCH ***"))
    return gate("G1 ★ THE NO-OP IS EXACT, and its tamper re-finds the published 1,844", ok, *lines)


# --------------------------------------------------------------------------- G2
def g2_render_read_identity():
    lines, ok = [], True
    bad32 = [v for v in range(32) if ((v * 255 // 31) >> 3) != v]
    ok = ok and not bad32
    lines.append("%-52s %d of 32 failures" % ("(v * 255 // 31) >> 3 == v", len(bad32)))
    bad_shift = [w for w in range(0x10000)
                 if KT.direct15_word(*KT.direct15_split(w)) != w]
    ok = ok and not bad_shift
    lines.append("%-52s %d of 65,536 failures" % ("the SHIFT rendering, inverted", len(bad_shift)))
    bad_scale = leak = 0
    for w in range(0x8000):
        if w == 0:
            continue                                  # the cutout renders alpha 0 -- ALPHA carries it
        r, g, b, a = KT.bgr555_rgba(w)
        if KT.direct15_word(r, g, b, 0) != w:
            bad_scale += 1
        if a != 255:
            leak += 1
    ok = ok and not bad_scale and not leak
    lines.append("%-52s %d of 32,767 failures, %d STP leak"
                 % ("the SCALE rendering, inverted by the SHIFT", bad_scale, leak))
    # THE TAMPER: a ROUNDING inverse of the scale form fails on the values direct15_split names.
    tamper = sum(1 for v in range(32) if int(round((v * 255 / 31.0) * 31 / 255.0)) != v)
    flooring = sum(1 for v in range(32) if int((v * 255 // 31) * 31 / 255.0) != v)
    lines.append("%-52s a FLOORING inverse of the scale fails %d of 32 channel values"
                 % ("TAMPER: replace the reader with round(c8*31/255)", flooring))
    ok = ok and flooring >= 30
    lines.append("%-52s %d (the rounding inverse is lossless, which is why the SHIFT is the codec "
                 "of record and the SCALE is only the RENDER)" % ("   (rounding inverse)", tamper))
    return gate("G2 the render/read identity, exhaustive over BOTH renderings", ok, *lines)


# --------------------------------------------------------------------------- G3
_DET_PROBE = r'''
import os, sys, struct
sys.path.insert(0, r"%s")
from ff9mapkit.summons import repaint as RP, reskin as RS, texture as KT
blob = open(r"%s", "rb").read()
p = RP.texel_page(blob, "%s", %d)
words = list(RP.palette_words(blob, p))
raw = blob[p.page_offset:p.page_offset+p.page_bytes]
idx = list(RP.texel_view(p, raw))
src = r"%s"
out, cen = RP.read_paint_png(src, p, tuple(words), idx)
import hashlib
print(hashlib.sha256(out).hexdigest())
'''


def g3_determinism():
    if not _have_corpus():
        return gate("G3 determinism", False, "no extracted corpus at %s" % CORPUS)
    td = _tmp()
    lines, ok = [], True
    # a 57-way creature tie and a 239-way scenery tie -- the corpus's own worst cases
    for ef, name, why in ((276, "tex.part3", "the 57-way creature tie"),
                          (HUE_EF, HUE_PAGE, "the census page")):
        blob = _load(ef)
        p = RP.texel_page(blob, name, ef)
        words = RP.palette_words(blob, p)
        raw = blob[p.page_offset:p.page_offset + p.page_bytes]
        idx = list(RP.texel_view(p, raw))
        src = _paint_source(blob, p, td)
        # repaint a band onto a colour the row carries more than once, so the tie is REAL
        from PIL import Image
        by = {}
        for i, x in enumerate(words):
            by.setdefault(x, []).append(i)
        multi = sorted((m for m in by.values() if len(m) > 1 and words[m[0]]), key=len, reverse=True)
        with Image.open(src) as im:
            px = list(im.convert("RGBA").tobytes())
        if multi:
            col = KT.bgr555_rgba(words[multi[0][0]])[:3] + (255,)
            for k in range(2000, 4000):
                if px[4 * k + 3] == 255:
                    px[4 * k:4 * k + 4] = list(col)
        im2 = Image.new("RGBA", (p.w, p.h))
        im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
        im2.save(src)
        shas = []
        for seed in ("0", "1", "12345", "987654"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            code = _DET_PROBE % (os.path.join(_REPO, "ff9mapkit"),
                                 os.path.join(CORPUS, "ef%03d.bytes" % ef), name, ef, src)
            r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
            shas.append(r.stdout.strip() or ("*** %s" % r.stderr.strip()[-120:]))
        same = len(set(shas)) == 1 and shas[0] and not shas[0].startswith("***")
        ok = ok and same
        lines.append("%-52s %s across 4 SEPARATE PROCESSES, PYTHONHASHSEED 0/1/12345/987654 (%s)"
                     % ("%s ef%03d %s" % (why, ef, name),
                        "IDENTICAL" if same else "*** DIVERGED: %s ***" % shas, shas[0][:16]))
    # ⚠ HONESTY ABOUT WHAT THE SEED SWEEP CAN AND CANNOT CATCH, stated because the design's own
    # tamper for this gate ("make the tie-break iterate a set -> the seeded runs diverge") DOES NOT
    # WORK: CPython hashes small ints to themselves, so `list({200,5,3,77,129,4})` is identical under
    # every seed.  A set-iterating tie-break would sail through the sweep above.  So the seed sweep is
    # kept for what it does prove (process/platform independence end to end) and the structural claim
    # is proven STRUCTURALLY, below, where it can actually go red.
    lines.append("%-52s a set of small ints iterates identically under every seed, so THIS sweep "
                 "cannot catch a set-iterating tie-break -- the AST check below is what does"
                 % "⚠ WHAT THE SEED SWEEP CANNOT CATCH:")
    hits = _iterated_containers(("read_paint_png", "_nearest", "_alt_split_check"))
    ok = ok and not hits
    lines.append("%-52s %s"
                 % ("STRUCTURAL: set/dict iteration in the decision path",
                    "NONE in read_paint_png / _nearest / _alt_split_check" if not hits
                    else "*** %s ***" % "; ".join(hits)))
    lines.append("%-52s add `for i in set(cand):` to the tie-break and this check goes RED"
                 % "   THE TAMPER:")
    # ★ A GENUINELY PERMUTED INPUT.  The only ORDER-BEARING input the codec takes is `alt_rows`
    # (`words` order IS the index space, so permuting it changes the question).  Reversing the
    # derivation order must not move a byte -- the previous spelling of this check passed the SAME
    # enumeration twice and permuted nothing.
    perm = _permuted_alt_rows_probe(td)
    ok = ok and perm[0]
    lines.append("%-52s %s" % ("PERMUTED: the alternate rows in reverse order", perm[1]))
    return gate("G3 determinism, across processes and enumeration order", ok, *lines)


def _iterated_containers(fn_names) -> list:
    """Every ``for``/comprehension in the named functions that iterates a SET or a DICT.

    An AST check rather than a sentence, because *a law in a docstring is a wish*: the claim
    "no set or dict iteration in any decision path" is the whole basis of the determinism argument,
    and the seed sweep provably cannot falsify it (small ints hash to themselves). This can: add one
    ``for i in set(...)`` to the tie-break and it goes red by name.
    """
    import ast
    src = open(RP.__file__, "r", encoding="utf-8").read()
    tree = ast.parse(src)
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in fn_names:
            continue
        # names bound to a set/dict anywhere in the function -- `zset`, `memo`, `alt_memo`, ...
        setish = set()
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Assign, ast.AnnAssign)):
                val = sub.value
                tgts = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                if val is None:
                    continue
                is_set = isinstance(val, (ast.Set, ast.SetComp, ast.Dict, ast.DictComp)) or (
                    isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                    and val.func.id in ("set", "frozenset", "dict"))
                if is_set:
                    setish.update(t.id for t in tgts if isinstance(t, ast.Name))
        iters = [s.iter for s in ast.walk(node) if isinstance(s, ast.For)]
        iters += [g.iter for s in ast.walk(node)
                  if isinstance(s, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
                  for g in s.generators]
        for it in iters:
            why = ""
            if isinstance(it, (ast.Set, ast.SetComp, ast.Dict, ast.DictComp)):
                why = "a set/dict literal or comprehension"
            elif isinstance(it, ast.Call) and isinstance(it.func, ast.Name) \
                    and it.func.id in ("set", "frozenset", "dict"):
                why = "a %s() call" % it.func.id
            elif isinstance(it, ast.Name) and it.id in setish:
                why = "%r, which is bound to a set/dict" % it.id
            if why:
                bad.append("%s line %d iterates %s" % (node.name, getattr(it, "lineno", 0), why))
    return bad


def _permuted_alt_rows_probe(td):
    """The alternate rows handed over in REVERSE derivation order must give the same verdict.

    ``alt_rows`` is the codec's ONLY order-bearing input (``words`` order IS the index space, so
    permuting it asks a different question), and the fixture is chosen from the corpus rather than
    named: a cell with >= 2 alternate keys, preferring one that also carries a NON-SPLIT duplicate
    group so the check RUNS in both orders and still emits bytes to compare.
    """
    from PIL import Image
    best = None
    # W6b-3: the same channel-A veto G6b names -- a cell the author-facing surface withdraws is not a
    # fixture this probe may pick, and reaching one through `texel_page` would abort the board.
    _lost = {(ef, n) for ef, n, _k in _author_surface_withdrawals(census()["classC"])}
    for rec in sorted(census()["classC"], key=lambda r: -r["alts"]):
        if rec["alts"] < 2:
            break
        if (rec["ef"], rec["name"]) in _lost:
            continue
        blob = _load(rec["ef"])
        p = RP.texel_page(blob, rec["name"], rec["ef"])
        words = RP.palette_words(blob, p)
        alts = RP.alternate_palette_rows(blob, p, RS.palette_map(blob, effect=rec["ef"]))
        zset = set(RP.transparent_indices(words))
        by_colour = {}
        for i in range(len(words)):
            if i not in zset:
                by_colour.setdefault(words[i] & 0x7FFF, []).append(i)
        # a group the check RUNS on: clean (it passes in both orders and emits bytes to compare) or,
        # failing that, split (it must REFUSE in both orders).  Either way `alt_rows` is iterated.
        groups = [g for c, g in sorted(by_colour.items()) if len(g) > 1 and c]
        clean = [g for g in groups if all(len({a.words[i] for i in g}) == 1 for a in alts)]
        pick = clean or groups
        best = best or (rec, blob, p, words, alts, pick)
        if pick:
            best = (rec, blob, p, words, alts, pick)
            if clean:
                break
    if best is None:
        return True, "SKIPPED: no class-C cell declares >= 2 alternate keys in this corpus"
    rec, blob, p, words, alts, pick = best
    raw = blob[p.page_offset:p.page_offset + p.page_bytes]
    idx = list(RP.texel_view(p, raw))
    src = _paint_source(blob, p, td)
    G = pick[0] if pick else None
    colour = words[G[0]] if G else next(x for x in words if x)
    with Image.open(src) as im:
        px = list(im.convert("RGBA").tobytes())
    n = 0
    for k in range(len(idx)):
        if px[4 * k + 3] == 255 and n < 200 and (G is None or idx[k] not in G):
            px[4 * k:4 * k + 4] = list(KT.bgr555_rgba(colour)[:3] + (255,))
            n += 1
    im2 = Image.new("RGBA", (p.w, p.h))
    im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
    im2.save(src)
    where = "ef%03d %s, %d alternates, %d texels edited" % (rec["ef"], rec["name"], len(alts), n)
    try:
        a, cen = RP.read_paint_png(src, p, words, idx, alts)
    except RP.RepaintError:                                      # both orders must refuse alike
        try:
            RP.read_paint_png(src, p, words, idx, tuple(reversed(alts)))
            return False, "*** forward order REFUSED and reverse order BUILT (%s) ***" % where
        except RP.RepaintError:
            return True, "both orders REFUSE identically (%s)" % where
    b, _ = RP.read_paint_png(src, p, words, idx, tuple(reversed(alts)))
    return a == b, ("byte-equal (%s, %d split check(s) ran in each order)"
                    % (where, cen["alt_checked"]) if a == b else "*** DIVERGED (%s) ***" % where)


# --------------------------------------------------------------------------- G4
def _hue_rotate_paint(src, deg: float):
    from PIL import Image
    with Image.open(src) as im:
        raw = im.convert("RGBA").tobytes()
        w, h = im.size
    out = []
    for i in range(w * h):
        r, g, b, a = raw[4 * i], raw[4 * i + 1], raw[4 * i + 2], raw[4 * i + 3]
        if a == 0:
            out.append((r, g, b, 0))
            continue
        hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        r2, g2, b2 = colorsys.hsv_to_rgb((hh + deg / 360.0) % 1.0, ss, vv)
        out.append((round(r2 * 255), round(g2 * 255), round(b2 * 255), 255))
    im2 = Image.new("RGBA", (w, h))
    im2.putdata(out)
    im2.save(src)
    return out


def _nearest_in(words, c15, cand):
    cr, cg, cb = c15 & 0x1F, (c15 >> 5) & 0x1F, (c15 >> 10) & 0x1F
    best, hits = 1 << 30, []
    for i in cand:
        wd = words[i]
        d = ((wd & 0x1F) - cr) ** 2 + (((wd >> 5) & 0x1F) - cg) ** 2 + (((wd >> 10) & 0x1F) - cb) ** 2
        if d < best:
            best, hits = d, [i]
        elif d == best:
            hits.append(i)
    return hits, best


def g4_alpha_governs():
    if not _have_corpus():
        return gate("G4 the alpha-governs rule", False, "no extracted corpus at %s" % CORPUS)
    td = _tmp()
    lines, ok = [], True
    holes_t = holes_g = 0
    for ef, name in ((HUE_EF, "tex.part0"), (HUE_EF, "tex.part1"), (HUE_EF, "tex.part2"),
                     (HUE_EF, "tex.part3"), (HUE_EF, "tex.part4"), (HUE_EF, "tex.part5"),
                     (CLEAN_EF, "cell.s0.x704_y256"), (CLEAN_EF, CLEAN_CELL)):
        blob = _load(ef)
        p = RP.texel_page(blob, name, ef)
        words = RP.palette_words(blob, p)
        raw = blob[p.page_offset:p.page_offset + p.page_bytes]
        idx = list(RP.texel_view(p, raw))
        src = _paint_source(blob, p, td)
        painted = _hue_rotate_paint(src, 40.0)
        zset = set(RP.transparent_indices(words))
        c_all = list(range(len(words)))
        c_op = [i for i in c_all if i not in zset]
        memo = {}
        ht = hg = opaque = 0
        for i, (r, g, b, a) in enumerate(painted):
            if a == 0:
                continue
            opaque += 1
            c15 = KT.direct15_word(r, g, b, 0)
            if c15 not in memo:
                memo[c15] = (min(_nearest_in(words, c15, c_all)[0]),
                             min(_nearest_in(words, c15, c_op)[0]) if c_op else -1)
            t, gsel = memo[c15]
            ht += 1 if t in zset else 0
            hg += 1 if gsel in zset else 0
        # ...and the SHIPPED codec agrees with the governed column
        out, cen = RP.read_paint_png(src, p, words, idx)
        nv = RP.texel_view(p, out)
        real = sum(1 for i in range(len(idx)) if idx[i] not in zset and nv[i] in zset)
        ok = ok and hg == 0 and real == 0
        holes_t += ht
        holes_g += hg
        lines.append("%-52s TAMPER %d hole(s) / GOVERNED %d / SHIPPED CODEC %d  (%d opaque)"
                     % ("ef%03d %s under a 40 degree hue slider" % (ef, name), ht, hg, real, opaque)
                     + ("" if hg == 0 and real == 0 else "  *** LEAK ***"))
        os.remove(src)
    # ★ THE CALIBRATION: the published 502 on ef227 tex.part0
    cal = lines[0]
    pinned = "TAMPER 502 " in cal
    ok = ok and pinned
    lines.append("%-52s %s (published 502 of 15,931 opaque = 3.15%%)"
                 % ("★ the ef227 tex.part0 calibration", "RE-FOUND" if pinned else "*** MISSED ***"))
    lines.append("%-52s %d without the rule, %d with it, over 8 pages"
                 % ("TOTAL", holes_t, holes_g))
    lines.append("%-52s the shipped CUTOUT gate then refuses the build -- the tamper fires through "
                 "TWO independent mechanisms" % "and:")
    return gate("G4 ALPHA GOVERNS the cutout, in both directions", ok, *lines)


# --------------------------------------------------------------------------- G5 / G6
def _split_fixture(ef: int, cell: str):
    blob = _load(ef)
    p = RP.texel_page(blob, cell, ef)
    pmap = RS.palette_map(blob, effect=ef)
    words = RP.palette_words(blob, p)
    alts = RP.alternate_palette_rows(blob, p, pmap)
    raw = blob[p.page_offset:p.page_offset + p.page_bytes]
    idx = list(RP.texel_view(p, raw))
    return blob, p, words, alts, raw, idx


def g5_alternate_split_fires():
    if not _have_corpus():
        return gate("G5 the alternate-split refusal", False, "no extracted corpus at %s" % CORPUS)
    from PIL import Image
    td = _tmp()
    lines, ok = [], True
    blob, p, words, alts, raw, idx = _split_fixture(SPLIT_EF, SPLIT_CELL)
    by = {}
    for i, x in enumerate(words):
        by.setdefault(x, []).append(i)
    dupg = [m for m in by.values() if len(m) > 1]
    split = [m for m in dupg
             if any(len({a.words[i] for i in m}) > 1 for a in alts)]
    lines.append("%-52s %d alternate key(s), %d duplicate group(s), %d SPLIT (%.1f%%)"
                 % ("FIXTURE ef%03d %s (class C)" % (SPLIT_EF, SPLIT_CELL),
                    len(alts), len(dupg), len(split), 100.0 * len(split) / max(1, len(dupg))))
    ok = ok and len(alts) >= 1 and split
    G = split[0]
    src = _paint_source(blob, p, td)
    with Image.open(src) as im:
        px = list(im.convert("RGBA").tobytes())
    victim = next(k for k in range(len(idx)) if idx[k] not in G and words[idx[k]])
    px[4 * victim:4 * victim + 4] = list(KT.bgr555_rgba(words[G[0]])[:3] + (255,))
    im2 = Image.new("RGBA", (p.w, p.h))
    im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
    im2.save(src)
    fired, msg = _refuses(RP.read_paint_png, src, p, words, idx, alts)
    for want in ("ALTERNATE-SPLIT TIE", "298 of 365", "11 of 16", "no acknowledge key",
                 "THAT THE CONTAINER DECLARES", "the swatch marks them"):
        hit = fired and want in msg
        ok = ok and hit
        lines.append("%-52s %s" % ("   refuses, quoting %r" % want,
                                   "YES" if hit else ("WRONG REASON: %s" % msg[:60] if fired
                                                      else "*** DID NOT REFUSE ***")))
    # THE TAMPER: remove the alternate loop and the build succeeds -- and the alternate view moves.
    out, _cen = RP.read_paint_png(src, p, words, idx, ())
    nv = RP.texel_view(p, out)
    moved_alt = sum(1 for k in range(len(idx)) if alts[0].words[nv[k]] != alts[0].words[idx[k]])
    ok = ok and moved_alt > 0
    lines.append("%-52s builds, and the OTHER reader's picture moves %d texel(s)"
                 % ("TAMPER: the alternate loop removed", moved_alt))
    # EDIT-SCOPED: the unedited page is structurally exempt
    src2 = _paint_source(blob, p, td)
    back, _c = RP.read_paint_png(src2, p, words, idx, alts)
    ok = ok and back == raw
    lines.append("%-52s %s (the incumbent survives, so the check never runs)"
                 % ("EDIT-SCOPED: the same page unedited", "0 bytes moved" if back == raw
                    else "*** MOVED ***"))
    return gate("G5 ★ the alternate-split refusal fires BY NAME on a real split group", ok, *lines)


def g6_alternate_split_does_not_over_fire():
    if not _have_corpus():
        return gate("G6 ...and it does not over-fire", False, "no corpus")
    from PIL import Image
    td = _tmp()
    lines, ok = [], True
    blob, p, words, alts, raw, idx = _split_fixture(CLEAN_EF, CLEAN_CELL)
    by = {}
    for i, x in enumerate(words):
        by.setdefault(x, []).append(i)
    dupg = [m for m in by.values() if len(m) > 1]
    lines.append("%-52s %d alternate key(s), %d duplicate group(s), 0 split"
                 % ("FIXTURE ef%03d %s (class C, clean)" % (CLEAN_EF, CLEAN_CELL),
                    len(alts), len(dupg)))
    ok = ok and len(alts) >= 1 and not dupg
    src = _paint_source(blob, p, td)
    with Image.open(src) as im:
        px = list(im.convert("RGBA").tobytes())
    live = [i for i, x in enumerate(words) if x]
    n = 0
    for k in range(len(idx)):
        if px[4 * k + 3] == 255 and n < 400:
            px[4 * k:4 * k + 4] = list(KT.bgr555_rgba(words[live[(k + 3) % len(live)]])[:3] + (255,))
            n += 1
    im2 = Image.new("RGBA", (p.w, p.h))
    im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
    im2.save(src)
    try:
        out, cen = RP.read_paint_png(src, p, words, idx, alts)
        built, why = out != raw, "%d texel(s) edited, %d alternate-split check(s) ran and PASSED" % (
            n, cen["alt_checked"])
    except RP.RepaintError as e:                                 # pragma: no cover - a real defect
        built, why = False, "*** REFUSED: %s ***" % str(e)[:80]
    ok = ok and built
    lines.append("%-52s %s" % ("a genuine edit on the CLEAN class-C cell", why))
    lines.append("%-52s the gate is CANDIDATE-SET-scoped, not group-scoped -- it asks about the "
                 "entries in contention for THIS texel" % "why it cannot over-fire here:")
    # ...and it is structurally unreachable on 93 of 240 surfaces
    b227 = _load(HUE_EF)
    pm = RS.palette_map(b227, effect=HUE_EF)
    creature_alts = sum(len(RP.alternate_palette_rows(b227, q, pm))
                        for q in RP.creature_texel_pages(b227))
    ok = ok and creature_alts == 0
    lines.append("%-52s %d (an id-4 page is uploaded by PART index and owns its own CLUT row)"
                 % ("CREATURE-UNREACHABLE: alternate keys on ef227's 6 pages", creature_alts))
    # ★ THE PASS PATH ITSELF -- the half both non-over-fire proofs above leave untouched.  On the
    # CLEAN cell and on a creature page the check NEVER RUNS, so they prove the refusal cannot fire
    # rather than that it DISCRIMINATES.  This half runs it and passes, on the SAME cell G5 refuses
    # on: one duplicate group there splits (G5), another does not (here).  `alt_checked >= 1` is the
    # instrument OPEN RISK 1 asked for, measured on real corpus bytes rather than asserted to be 0.
    pass_ok, pass_why = _alt_split_pass_path(td)
    ok = ok and pass_ok
    lines.append("%-52s %s" % ("★ THE CHECK RAN AND PASSED (ef%03d %s)" % (SPLIT_EF, SPLIT_CELL),
                               pass_why))
    return gate("G6 ...AND IT DOES NOT OVER-FIRE (the non-over-fire twin)", ok, *lines)


def _alt_split_pass_path(td):
    """Drive a genuine edit onto a duplicate group that does NOT split, and prove the check RAN."""
    from PIL import Image
    blob, p, words, alts, raw, idx = _split_fixture(SPLIT_EF, SPLIT_CELL)
    if not alts:                                                 # pragma: no cover - fixture drift
        return False, "*** the fixture declares no alternate key ***"
    zset = set(RP.transparent_indices(words))
    c_op = [i for i in range(len(words)) if i not in zset]
    by_colour = {}
    for i in c_op:
        by_colour.setdefault(words[i] & 0x7FFF, []).append(i)
    # a group whose members carry ONE word in EVERY alternate: the check runs and finds no split
    groups = [g for c, g in sorted(by_colour.items())
              if len(g) > 1 and c and all(len({a.words[i] for i in g}) == 1 for a in alts)]
    if not groups:                                               # pragma: no cover - fixture drift
        return False, "*** no NON-SPLIT duplicate group on this cell -- pick another fixture ***"
    G = groups[0]
    victim = next((k for k in range(len(idx)) if idx[k] not in G and idx[k] in c_op), -1)
    if victim < 0:                                               # pragma: no cover
        return False, "*** every texel already sits inside the group ***"
    src = _paint_source(blob, p, td)
    with Image.open(src) as im:
        px = list(im.convert("RGBA").tobytes())
    px[4 * victim:4 * victim + 4] = list(KT.bgr555_rgba(words[G[0]])[:3] + (255,))
    im2 = Image.new("RGBA", (p.w, p.h))
    im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
    im2.save(src)
    try:
        out, cen = RP.read_paint_png(src, p, words, idx, alts)
    except RP.RepaintError as e:
        return False, "*** REFUSED on a NON-SPLIT group: %s ***" % str(e)[:80]
    nv = RP.texel_view(p, out)
    ok = cen["alt_checked"] >= 1 and out != raw and nv[victim] in G
    return ok, ("group %s (word %#06x, %d-way) -- %d check(s) RAN and PASSED, the texel BUILT onto "
                "index %d, and every alternate renders the group as ONE word"
                % (G, words[G[0]], len(G), cen["alt_checked"], nv[victim]))


# --------------------------------------------------------------------------- G6b
def g6b_over_fire_measurement():
    """★ OPEN RISK 1's OWN INSTRUMENT, run: HOW MUCH of the class-C surface does R7 block?

    The judges' one real disagreement is whether a no-key refusal under a NEAREST lane fires on
    ordinary anti-aliased work. This spec shipped the safer posture (no key) and filed the ack as an
    open risk *with the measurement that would open it*. Filing a measurement and not taking it is how
    an open risk becomes a forgotten one, so it is taken here, on the real codec and the real cells.

    **IT ASSERTS THE CONTROL AND DISCLOSES THE SWEEP.** The control -- an UNEDITED re-quantize of
    every exportable class-C cell -- must be byte-exact with ZERO refusals, because that is law 1 on
    exactly the surface R7 lives on, and it is what makes a non-zero refusal rate at 4 degrees a
    statement about EDITS rather than about the gate being on. The hue rates themselves are a
    DISCLOSURE: they are the owner's decision to price, not a threshold this rung may invent.

    ★ **AND SINCE W6b-3 THE SWEEP STATES ITS OWN SURFACE.** ``texel_page`` resolves at
    ``LICENSED_CHANNELS``, which consults CHANNEL A, whose hazards can WITHDRAW a census cell from
    the author-facing path (:data:`CHANNEL_A_VETO`). The sweep runs over what an author can still
    reach and the withdrawal is **named, counted and pinned** rather than skipped quietly -- a
    control that silently shrinks is not a control.
    """
    if not _have_corpus():
        return gate("G6b the R7 over-fire measurement", False, "no corpus")
    td = _tmp()
    cc = census()["classC"]
    lines, ok = [], True
    # ★ THE AUTHOR-FACING SURFACE, RE-DERIVED, AND ITS DIFFERENCE FROM THE CENSUS PINNED BY NAME.
    withdrawn = _author_surface_withdrawals(cc)
    lost = {(ef, n) for ef, n, _k in withdrawn}
    cc = [rec for rec in cc if (rec["ef"], rec["name"]) not in lost]
    ok = ok and tuple(sorted(lost)) == tuple(sorted(W6B3_WITHDRAWN))
    ok = ok and all(k in CHANNEL_A_VETO for _e, _n, k in withdrawn)
    noop_exact = noop_refused = 0
    rates = {}
    for deg in (0.0, 4.0, 8.0, 40.0):
        refused = built = 0
        for rec in cc:
            blob = _load(rec["ef"])
            p = RP.texel_page(blob, rec["name"], rec["ef"])
            words = RP.palette_words(blob, p)
            alts = RP.alternate_palette_rows(blob, p, RS.palette_map(blob, effect=rec["ef"]))
            raw = blob[p.page_offset:p.page_offset + p.page_bytes]
            idx = list(RP.texel_view(p, raw))
            src = _paint_source(blob, p, td)
            if deg:
                _hue_rotate_paint(src, deg)
            try:
                out, _cen = RP.read_paint_png(src, p, words, idx, alts)
                built += 1
                if not deg:
                    noop_exact += 1 if out == raw else 0
            except RP.RepaintError:
                refused += 1
                if not deg:
                    noop_refused += 1
            os.remove(src)
        rates[deg] = (refused, refused + built)
    ok = ok and noop_refused == 0 and noop_exact == len(cc) and len(cc) > 0
    lines.append("%-52s %d of %d byte-EXACT, %d refusal(s) -- law 1 on R7's OWN surface"
                 % ("THE CONTROL: an unedited re-quantize (0 degrees)", noop_exact, len(cc),
                    noop_refused))
    lines.append("%-52s %s"
                 % ("★ W6b-3: THE AUTHOR-FACING SURFACE IS SMALLER THAN THE CENSUS",
                    ("; ".join("ef%03d %s (%s)" % w for w in withdrawn) +
                     " -- CHANNEL A holds VETO power, so these census cell(s) resolve no page on the "
                     "path an author walks.  The census itself is UNMOVED (0 cells gained or lost) "
                     "and every §1.4 pin above is measured there.")
                    if withdrawn else
                    "none -- no census class-C cell is withdrawn on the licensed path"))
    lines.append("%-52s the set is RE-DERIVED from `scenery_surface(LICENSED_CHANNELS)` every run "
                 "and pinned by NAME: a different cell, or a class that is not channel A's, is RED "
                 "here rather than a silently shorter sweep" % "   (and it is pinned, not skipped:)")
    for deg in (4.0, 8.0, 40.0):
        r, n = rates[deg]
        lines.append("%-52s R7 REFUSED %d of %d exportable class-C cells (%.1f%%)"
                     % ("a %g degree hue nudge over the WHOLE cell" % deg, r, n,
                        100.0 * r / max(1, n)))
    lines.append("%-52s a whole-cell hue slider is the WORST case for this gate (every texel is an "
                 "edit); a local brush stroke touches far fewer candidate sets"
                 % "SCOPE OF THE NUMBER:")
    lines.append("%-52s if the first real class-C paint cast trips R7 on work the OWNER calls "
                 "ordinary, open a follow-on rung for `acknowledge_alternate_split` -- `_ack_bool`"
                 % "★ OPEN RISK 1, AND IT IS AN OWNER CALL:")
    lines.append("%-52s guarded, quoting the texel count, the split candidate set, both decoded "
                 "words and 298/365, and PAIRED with the re-rendered alternate.  Not pre-emptively."
                 % "")
    return gate("G6b ★ OPEN RISK 1 MEASURED: how much surface R7 blocks (control asserted, "
                "sweep disclosed)", ok, *lines)


# --------------------------------------------------------------------------- G7 / G8 / G9
def _composed_paint(ef: int, page: str, clut_target: str, ack: bool):
    """A one-spec composition: a CLUT recolour of ``clut_target`` + a paint row on ``page``."""
    td = _tmp()
    blob = _load(ef)
    p = RP.texel_page(blob, page, ef)
    src = _paint_source(blob, p, td)
    row = _paint_row(page, src)
    if ack:
        row["acknowledge_recoloured_palette"] = True
    spec = {"reskin": {"effect": ef, "allow_unguarded": True,
                       "target": [{"name": clut_target, "hue_rotate": 40.0,
                                   "acknowledge_shared": True}],
                       "texel": [row]}}
    b0 = RS.build(spec, "?", blob=blob)
    return spec, blob, b0


def g7_composed_palette_refusal():
    if not _have_corpus():
        return gate("G7 the composed-palette refusal", False, "no corpus")
    lines, ok = [], True
    spec, blob, b0 = _composed_paint(HUE_EF, "tex.part0", "creature.part0", ack=False)
    moved = sum(1 for i in range(len(blob)) if blob[i] != b0.patched[i])
    ok = ok and moved > 0
    lines.append("%-52s %d CLUT byte(s) moved -- the target ACTUALLY recolours, so the gate cannot "
                 "look green for the wrong reason" % ("FIXTURE ef227 creature.part0 hue_rotate 40",
                                                      moved))
    fired, msg = _refuses(RP.build, spec, "?", blob=blob, base=b0.patched)
    for want in ("THE RECOLOURED-PALETTE REFUSAL", "creature.part0", "IN THIS SPEC",
                 "acknowledge_recoloured_palette = true"):
        hit = fired and want in msg
        ok = ok and hit
        lines.append("%-52s %s" % ("   refuses, quoting %r" % want,
                                   "YES" if hit else ("WRONG REASON: %s" % msg[:60] if fired
                                                      else "*** DID NOT REFUSE ***")))
    spec2, blob2, b02 = _composed_paint(HUE_EF, "tex.part0", "creature.part0", ack=True)
    try:
        b = RP.build(spec2, "?", blob=blob2, base=b02.patched)
        lines.append("%-52s BUILDS, note: %s"
                     % ("   ...and the acknowledgement lets it through",
                        next((n for n in b.enabled[0].hazard_notes if "acknowledge" in n),
                             "(none)")[:70]))
    except RP.RepaintError as e:                                # pragma: no cover
        ok = False
        lines.append("%-52s *** STILL REFUSED: %s ***" % ("   acknowledged", str(e)[:70]))
    return gate("G7 the COMPOSED-PALETTE refusal (R9) fires, naming N of M", ok, *lines)


def g8_composed_palette_does_not_over_fire():
    if not _have_corpus():
        return gate("G8 ...and it does not over-fire", False, "no corpus")
    lines, ok = [], True
    spec, blob, b0 = _composed_paint(HUE_EF, "tex.part0", "creature.part3", ack=False)
    moved = sum(1 for i in range(len(blob)) if blob[i] != b0.patched[i])
    ok = ok and moved > 0
    lines.append("%-52s %d CLUT byte(s) moved on ANOTHER palette" % ("FIXTURE recolour part3, paint "
                                                                     "part0", moved))
    try:
        b = RP.build(spec, "?", blob=blob, base=b0.patched)
        b.check = RP.self_check(b)
        bad = [g.name for g in b.check.gates if not g.ok]
        ok = ok and not bad and not b.enabled[0].changed
        lines.append("%-52s BUILDS, %d texel byte(s) moved, %d/%d gates"
                     % ("   the lawful composed build", len(b.enabled[0].changed),
                        sum(1 for g in b.check.gates if g.ok), len(b.check.gates)))
        if bad:
            lines.append("   *** RED: %s ***" % "; ".join(bad))
        z = next(g for g in b.check.rules if "ZERO CLUT bytes" in g.name)
        ok = ok and z.ok
        lines.append("%-52s %s" % ("   and the shipped ZERO-CLUT gate", z.detail[:74]))
    except RP.RepaintError as e:                                # pragma: no cover
        ok = False
        lines.append("%-52s *** REFUSED: %s ***" % ("   the lawful composed build", str(e)[:70]))
    lines.append("%-52s a BYTE comparison of THIS page's own row, never \"any CLUT target exists\""
                 % "why it cannot over-fire:")
    return gate("G8 ...AND IT DOES NOT OVER-FIRE on a different palette", ok, *lines)


def g9_zero_clut_bytes():
    if not _have_corpus():
        return gate("G9 zero CLUT bytes", False, "no corpus")
    lines, ok = [], True
    # SELF-CONTAINED on purpose: a gate that reads another gate's global is a gate that passes or
    # fails depending on the order somebody ran them in.
    spec, cblob, b0 = _composed_paint(HUE_EF, "tex.part0", "creature.part3", ack=False)
    bc = RP.build(spec, "?", blob=cblob, base=b0.patched)
    bc.check = RP.self_check(bc)
    zc = next(g for g in bc.check.rules if "ZERO CLUT bytes" in g.name)
    ok = ok and zc.ok
    lines.append("%-52s %s" % ("on a COMPOSED paint build (CLUT + paint, one artifact)",
                               zc.detail[:74]))
    # ...and on a plain paint build, with a real edit
    td = _tmp()
    blob = _load(HUE_EF)
    p = RP.texel_page(blob, "tex.part0", HUE_EF)
    words = RP.palette_words(blob, p)
    src = _paint_source(blob, p, td)
    _hue_rotate_paint(src, 8.0)
    b = RP.build(_texel_spec(HUE_EF, [_paint_row("tex.part0", src,
                                                 acknowledge_cutout_reshape=True)]), "?", blob=blob)
    b.check = RP.self_check(b)
    z = next(g for g in b.check.rules if "ZERO CLUT bytes" in g.name)
    clut_lo, clut_hi = p.clut_offset, p.clut_offset + 2 * p.clut_entries
    hits = sum(1 for o in b.check.changed if clut_lo <= o < clut_hi)
    ok = ok and z.ok and hits == 0
    lines.append("%-52s %d texel byte(s) moved, %d CLUT byte(s) -- gate %s"
                 % ("on a plain paint build (an 8 degree hue nudge)", len(b.check.changed), hits,
                    "green" if z.ok else "*** RED ***"))
    lines.append("%-52s the lane writes INDICES; the CLUT lever is `[[reskin.target]]`"
                 % "STRUCTURAL:")
    globals()["_G10_BUILD"] = b
    return gate("G9 the paint lane writes ZERO CLUT bytes", ok, *lines)


# --------------------------------------------------------------------------- G10
def _id0_rect_table(blob: bytes, tag: str = "s0"):
    """``(rect table offset, rect count)`` for one chunk -- derived exactly as ``scenery_pages`` does.

    Lifted verbatim from ``w6b_gates.py``'s own G3 so the tamper this gate fires is THE SAME tamper
    that rung proved non-vacuous, rather than a second one that might land somewhere harmless.
    """
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


def g10_region_invariant():
    if not _have_corpus():
        return gate("G10 the region invariant", False, "no corpus")
    lines, ok = [], True
    b = globals().get("_G10_BUILD")
    if b is None:                                                # pragma: no cover
        return gate("G10 the region invariant", False, "G9 did not produce a build")
    ok = ok and "re-derive identically" in b.region_invariant.lower().replace("re-derives", "re-derive")
    lines.append("%-52s %s" % ("at the BUILD call site, against PRISTINE stock",
                               b.region_invariant[:74]))
    reg = [g for g in b.check.regions if not g.ok]
    ok = ok and not reg
    lines.append("%-52s %d/%d green" % ("the TEXEL partition's region gates",
                                        sum(1 for g in b.check.regions if g.ok),
                                        len(b.check.regions)))
    # THE TAMPER, the w6b_gates G3 precedent re-run on THIS lane's own container: move rect 0's VRAM
    # y by one page-cell and the derivation identity CATCHES it by name.  A splice that moved the
    # rect table would re-aim the whole page map while the container still parsed, the length still
    # matched and every palette still re-derived -- so this is the only instrument that sees it.
    blob = _load(HUE_EF)
    off, nrects = _id0_rect_table(blob)
    tampered = bytearray(blob)
    struct.pack_into("<H", tampered, off + 2,
                     struct.unpack_from("<H", tampered, off + 2)[0] + RS.PAGE_CELL_LINES)
    fired, msg = _refuses(RS.assert_page_cells_identical, blob, bytes(tampered),
                          "a perturbed ef%03d" % HUE_EF)
    ok = ok and fired and "DERIVATION MOVED" in msg
    lines.append("%-52s %s" % ("TAMPER: rect 0's VRAM y + 128 (%d rects @%#x)" % (nrects, off),
                               "REFUSED -- %s" % msg.split(":")[0] if fired
                               else "*** NOT CAUGHT -- the gate is a comment ***"))
    # ...and a write INSIDE the licensed pixel stream is NOT caught: the gate is not a blanket
    licensed = bytearray(blob)
    p0 = RP.texel_page(blob, "cell.s0.x704_y256", HUE_EF) if any(
        q.name == "cell.s0.x704_y256" for q in RP.scenery_texel_pages(blob, HUE_EF)) else None
    if p0 is not None:
        licensed[p0.page_offset + 100] ^= 0xFF
        fired2, msg2 = _refuses(RS.assert_page_cells_identical, blob, bytes(licensed), "a pixel write")
        ok = ok and not fired2
        lines.append("%-52s %s" % ("...and a write INSIDE the pixel stream is LICENSED",
                                   "yes (the map re-derives)" if not fired2
                                   else "*** REFUSED: %s ***" % msg2[:50]))
    lines.append("%-52s the paint branch goes through the SAME call site -- it adds one branch in "
                 "front of the art READ, and touches no splice, no gate and no region"
                 % "UNROUTED-AROUND:")
    return gate("G10 the region invariant + page-cell identity under a paint splice", ok, *lines)


# --------------------------------------------------------------------------- G11
def g11_cast_proven_shas():
    if not _have_corpus():
        return gate("G11 the four cast-proven artifacts", False, "no corpus")
    import hashlib
    lines, ok = [], True
    for spec_name, (ef, want) in sorted(CLUT_PINS.items()):
        path = os.path.join(_HERE, spec_name)
        if not os.path.isfile(path):                             # pragma: no cover
            ok = False
            lines.append("%-52s *** MISSING ***" % spec_name)
            continue
        try:
            b = RS.build(RS.load_spec(path), path, blob=_load(ef))
            got = hashlib.sha256(b.patched).hexdigest()
        except Exception as e:                                   # pragma: no cover
            ok = False
            lines.append("%-52s *** BUILD FAILED: %s ***" % (spec_name, str(e)[:60]))
            continue
        hit = got == want
        ok = ok and hit
        lines.append("%-52s %s %s" % ("ef%03d  %s" % (ef, spec_name), got[:16],
                                      "== the cast-proven sha" if hit else "*** MOVED (want %s) ***"
                                      % want[:16]))
    # THE COMPOSED W6a ARTIFACT: the texel lane on top of W4's recolour.
    emblem = os.path.join(_HERE, "bahamut_emblem.toml")
    art = os.path.join(CORPUS, "repaint-w6", "ef227", "art", "tex.part0.png")
    if os.path.isfile(emblem) and os.path.isfile(art):
        blob = _load(227)
        base = RS.build(RS.load_spec(os.path.join(_HERE, "bahamut_reskin.toml")),
                        os.path.join(_HERE, "bahamut_reskin.toml"), blob=blob)
        spec = RP.load_spec(emblem)
        spec["reskin"].pop("orthogonality", None)      # its sibling paths point at another worktree
        spec["reskin"]["texel"][0]["source"] = art
        b = RP.build(spec, emblem, blob=blob, base=base.patched, compose=False)
        got = hashlib.sha256(b.patched).hexdigest()
        hit = got == W6A_COMPOSED_SHA256
        nbytes = sum(len(t.changed) for t in b.enabled)
        ok = ok and hit and nbytes == W6A_TEXEL_BYTES
        # ★ THE HALVES, EACH DERIVED FROM ITS OWN PAIR OF CONTAINERS.  The previous spelling
        # intersected `base_changed` with a comprehension that EXCLUDED every member of
        # `base_changed`, so the intersection was empty by construction and the line proved nothing.
        # The CLUT half is stock -> base; the texel half is base -> patched; disjointness is the
        # claim that no byte is in both.
        clut_half = set(b.base_changed)
        texel_half = {i for i in range(len(blob)) if b.orig[i] != b.patched[i]}
        inter = clut_half & texel_half
        disjoint = not inter
        ok = ok and disjoint and clut_half and texel_half
        lines.append("%-52s %s %s (%d texel bytes, want %d)"
                     % ("the COMPOSED W6a artifact on base %s" % W4_PATCHED_SHA256[:8], got[:16],
                        "== the cast-proven sha" if hit else "*** MOVED ***", nbytes,
                        W6A_TEXEL_BYTES))
        lines.append("%-52s CLUT half %d B, texel half %d B, intersection %d -- %s"
                     % ("   the two halves, each from its OWN container pair", len(clut_half),
                        len(texel_half), len(inter),
                        "DISJOINT" if disjoint else "*** THEY OVERLAP ***"))
    else:                                                        # pragma: no cover
        ok = False
        lines.append("%-52s *** the emblem spec or its SCRATCH art is absent ***"
                     % "the COMPOSED W6a artifact")
    lines.append("%-52s W6q adds ONE branch IN FRONT of the existing dispatch and modifies none of "
                 "it -- if a sha moves, the change went into the wrong branch" % "WHY THIS HOLDS:")
    return gate("G11 the FOUR cast-proven artifacts still rebuild BYTE-EXACT", ok, *lines)


# --------------------------------------------------------------------------- G12 / G13 / G14
def g12_key_set_pins():
    lines, ok = [], True
    td = _tmp()
    for key in ("source_paint", "acknowledge_quantize", "acknowledge_recoloured_palette"):
        hit = key in RP._TEXEL_KEYS
        ok = ok and hit
        lines.append("%-52s %s" % ("`%s` is a KNOWN [[reskin.texel]] key" % key,
                                   "yes" if hit else "*** MISSING ***"))
    blob = _load(CLEAN_EF)
    for key in ("quantize", "mint_clut"):
        # (1) on [[reskin.texel]] -- the EXISTING w6b_gates fixture, unchanged
        row = {"name": "cell.s0.x704_y256", "source": "x.png", "enabled": True, key: True}
        fired, msg = _refuses(RP.build, _texel_spec(CLEAN_EF, [row]), "?", blob=blob)
        hit = fired and "unknown key" in msg
        ok = ok and hit
        lines.append("%-52s %s" % ("`%s = true` on [[reskin.texel]]" % key,
                                   "STILL an unknown key" if hit else "*** ACCEPTED ***"))
        # (2) on [[reskin.target]] -- NEW in W6q-0
        spec = {"reskin": {"effect": CLEAN_EF, "allow_unguarded": True,
                           "target": [{"name": "creature.part0", key: True}]}}
        fired2, msg2 = _refuses(RS.build, spec, "?", blob=blob)
        hit2 = fired2 and "unknown key" in msg2
        ok = ok and hit2
        lines.append("%-52s %s" % ("`%s = true` on [[reskin.target]]" % key,
                                   "unknown key (W6q-0)" if hit2 else "*** SILENTLY IGNORED ***"))
        # (3) under [reskin] -- NEW in W6q-0
        p = os.path.join(td, "k_%s_reskin.toml" % key)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write('[reskin]\neffect = %d\n%s = true\n\n[[reskin.target]]\nname = "x"\n'
                     % (CLEAN_EF, key))
        fired3, msg3 = _refuses(RS.load_spec, p)
        fired4, msg4 = _refuses(RP.load_spec, p)
        hit3 = fired3 and "unknown key" in msg3 and fired4 and "unknown key" in msg4
        ok = ok and hit3
        lines.append("%-52s %s" % ("`%s = true` under [reskin] (both loaders)" % key,
                                   "unknown key (W6q-0)" if hit3 else "*** SILENTLY IGNORED ***"))
    return gate("G12 the key-set pins, all three tables", ok, *lines)


def g13_every_shipped_spec_still_loads():
    """ENUMERATED FROM THE TREE, never hand-listed: this rung's only real regression risk."""
    import tomllib
    lines, ok = [], True
    seen = bad = 0
    for root, dirs, files in os.walk(_REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for f in files:
            if not f.endswith(".toml"):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "rb") as fh:
                    doc = tomllib.load(fh)
            except Exception:
                continue
            r = doc.get("reskin")
            if not isinstance(r, dict):
                continue
            seen += 1
            probs = []
            if set(r) - RS._RESKIN_KEYS:
                probs.append("[reskin] %s" % sorted(set(r) - RS._RESKIN_KEYS))
            for i, row in enumerate(r.get("target") or []):
                if set(row) - RS._TARGET_KEYS:
                    probs.append("target #%d %s" % (i, sorted(set(row) - RS._TARGET_KEYS)))
            for i, row in enumerate(r.get("texel") or []):
                if set(row) - RP._TEXEL_KEYS:
                    probs.append("texel #%d %s" % (i, sorted(set(row) - RP._TEXEL_KEYS)))
            if probs:
                bad += 1
                ok = False
                lines.append("*** %s: %s" % (os.path.relpath(path, _REPO), "; ".join(probs)))
    ok = ok and seen > 0
    lines.append("%-52s %d spec(s) found by glob, %d refused" % ("every [reskin] spec in the tree",
                                                                 seen, bad))
    # every EMITTED scaffold, both lanes -- a scaffold emitting a key its own loader refuses is the
    # worst possible shape, so they are GENERATED here rather than trusted.
    td = _tmp()
    blob = _load(HUE_EF)
    text, _pm = RS.scaffold(HUE_EF, blob=blob)
    doc = tomllib.loads(text)
    p1 = set(doc["reskin"]) - RS._RESKIN_KEYS
    p2 = set().union(*[set(r) for r in doc["reskin"]["target"]]) - RS._TARGET_KEYS
    ok = ok and not p1 and not p2
    lines.append("%-52s %d row(s), unknown keys %s / %s"
                 % ("the CLUT scaffold (`summon-reskin scaffold`)", len(doc["reskin"]["target"]),
                    sorted(p1) or "none", sorted(p2) or "none"))
    for lane in ("indexed", "paint"):
        out = os.path.join(td, "sc_%s" % lane)
        RP.export_art(blob, HUE_EF, out, lane=lane, overlays=False)
        with open(os.path.join(out, RP.SCAFFOLD_NAME), "rb") as fh:
            doc2 = tomllib.load(fh)
        p3 = set(doc2["reskin"]) - RS._RESKIN_KEYS
        p4 = set().union(*[set(r) for r in doc2["reskin"]["texel"]]) - RP._TEXEL_KEYS
        ok = ok and not p3 and not p4
        lines.append("%-52s %d row(s), unknown keys %s / %s"
                     % ("the TEXEL scaffold, lane=%s" % lane, len(doc2["reskin"]["texel"]),
                        sorted(p3) or "none", sorted(p4) or "none"))
    # ...and the DEPRECATED key that would break the largest population if it were omitted
    hit = "acknowledge_texanim" in RS._TARGET_KEYS and "acknowledge_texanim" in RS._RESKIN_KEYS
    ok = ok and hit
    lines.append("%-52s %s" % ("the DEPRECATED `acknowledge_texanim` is still known",
                               "yes" if hit else "*** OMITTED -- every spec carrying it refuses ***"))
    return gate("G13 every shipped spec + every emitted scaffold still loads", ok, *lines)


def g14_lane_tuple_pin():
    ok = tuple(cli._SUMMON_ART_LANES) == RP.ART_LANES
    return gate("G14 `_SUMMON_ART_LANES == repaint.ART_LANES`", ok,
                "%-52s %s" % ("cli", list(cli._SUMMON_ART_LANES)),
                "%-52s %s" % ("repaint", list(RP.ART_LANES)),
                "%-52s the parser is built before any summon module imports, so the choices= list is "
                "stated literally and PINNED" % "why:")


# --------------------------------------------------------------------------- G15
def g15_refusal_string_pins():
    if not _have_corpus():
        return gate("G15 the refusal-string pins", False, "no corpus")
    td = _tmp()
    lines, ok = [], True
    verbatim = ("RGBA / quantize / mint-CLUT stay refused on the INDEXED lane and W6b-1 does "
                "not touch that: the refusal is about EXACT RECOVERY, not about scope -- a "
                "lane whose no-op is not a no-op cannot carry a byte-identity gate")
    hit = RP.INDEXED_RGBA_REASON == verbatim
    ok = ok and hit
    lines.append("%-52s %s" % ("INDEXED_RGBA_REASON is BYTE-FOR-BYTE unchanged",
                               "yes" if hit else "*** EDITED ***"))
    blob = _load(HUE_EF)
    fired, msg = _refuses(RP.export_art, blob, HUE_EF, td, lane="rgba")
    for pin in ("93/93", "1,844", "8.31%", "88.75%..99.24%", verbatim):
        h = fired and pin in msg
        ok = ok and h
        lines.append("%-52s %s" % ("the `rgba` EXPORT refusal quotes %r" % pin[:28],
                                   "yes" if h else "*** MISSING ***"))
    h = fired and "`paint`" not in msg and "source_paint" not in msg
    ok = ok and h
    lines.append("%-52s %s" % ("   ...and does NOT advertise the new lane",
                               "yes" if h else "*** SOFTENED ***"))
    # site A: an RGBA file handed to a `source =` row
    p = RP.texel_page(blob, "tex.part0", HUE_EF)
    src = _paint_source(blob, p, td)
    fired2, msg2 = _refuses(RP.read_indexed_png, src, p.w, p.h, p.clut_entries)
    h2 = fired2 and verbatim in msg2 and 'not "P"' in msg2
    ok = ok and h2
    lines.append("%-52s %s" % ("the INDEXED IMPORT refusal (site A) is verbatim",
                               "yes" if h2 else "*** CHANGED ***"))
    # MINT_CLUT_REASON, quoted verbatim by R12
    b = bytearray(blob)
    struct.pack_into("<H", b, p.clut_offset, 0x1234)
    p2 = RP.texel_page(bytes(b), "tex.part0", HUE_EF)
    words2 = RP.palette_words(bytes(b), p2)
    from PIL import Image
    with Image.open(src) as im:
        px = list(im.convert("RGBA").tobytes())
    px[4 * 900:4 * 900 + 4] = [0, 0, 0, 0]
    im2 = Image.new("RGBA", (p.w, p.h))
    im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
    im2.save(src)
    raw = blob[p.page_offset:p.page_offset + p.page_bytes]
    fired3, msg3 = _refuses(RP.read_paint_png, src, p2, words2, RP.texel_view(p2, raw))
    h3 = fired3 and RP.MINT_CLUT_REASON in msg3 and "45 of 147" in msg3 and "0 of 93" in msg3
    ok = ok and h3
    lines.append("%-52s %s" % ("MINT_CLUT_REASON is quoted VERBATIM by R12",
                               "yes -- a real call site" if h3 else "*** NOT QUOTED ***"))
    lines.append("%-52s softening either string reddens THREE tests and TWO call sites at once"
                 % "THE TRIPWIRE:")
    return gate("G15 the refusal-string pins (the tripwire)", ok, *lines)


# --------------------------------------------------------------------------- G16
def g16_re_derivation_pin():
    """★ Every headline number this rung quotes, RE-MEASURED.  A constant that is a cache of a
    measurement has to be re-measured somewhere -- and quoting the design document instead is exactly
    the failure this gate exists to catch."""
    if not _have_corpus():
        return gate("G16 the re-derivation pin", False, "no corpus")
    c = census()
    lines, ok = [], True
    COMMA = lambda v: "{:,}".format(v)
    PCT2 = lambda v: "%.2f%%" % v
    PCT1 = lambda v: "%.1f%%" % v
    F1 = lambda v: "%.1f" % v
    F3 = lambda v: "%.3f" % v

    def pin(label, got, want, fmt=None):
        """RE-MEASURED == PUBLISHED, or the gate goes red naming both. ``fmt`` is a CALLABLE, so a
        thousands separator and a percent are the same mechanism."""
        nonlocal ok
        f = fmt or (lambda v: "%s" % (v,))
        hit = got == want
        ok = ok and hit
        lines.append("%-52s %s (published %s)%s"
                     % (label, f(got), f(want), "" if hit else "   *** MISMATCH ***"))

    def near(label, got, want, tol, fmt=None):
        nonlocal ok
        f = fmt or (lambda v: "%.4f" % v)
        hit = abs(got - want) <= tol
        ok = ok and hit
        lines.append("%-52s %s (published %s +/- %s)%s"
                     % (label, f(got), f(want), f(tol), "" if hit else "   *** MISMATCH ***"))

    pin("§1.1 texels moved by a NAIVE re-quantize", c["naive_moved"], 767531, COMMA)
    pin("§1.1    creature half", c["naive_creature"], 88631, COMMA)
    pin("§1.1    scenery half", c["naive_scenery"], 678900, COMMA)
    pin("§1.1    surfaces affected", c["naive_surfaces"], 191)
    pin("§1.1 texels moved WITH the incumbent lock", c["noop_moved_total"], 0)
    pin("§1.1    surfaces exact", c["noop_exact"], c["surfaces"])
    pin("§1.1 ★ the ef251 tex.part0 calibration",
        c["per_page"]["ef251/tex.part0"][0], 1844, COMMA)
    pin("§1.1 worst creature page (ef184 tex.part4)",
        c["per_page"]["ef184/tex.part4"][0], 6187, COMMA)
    pin("§1.1 worst scenery cell (ef447 cell.s1.x448_y256)",
        c["per_page"]["ef447/cell.s1.x448_y256"][0], 14428, COMMA)
    near("§1.1    ...as a share of its cell",
         100.0 * c["per_page"]["ef447/cell.s1.x448_y256"][0]
         / c["per_page"]["ef447/cell.s1.x448_y256"][2], 88.06, 0.01, PCT2)
    near("§1.1 the ef211 bench cell would move",
         100.0 * c["per_page"]["ef211/cell.s0.x704_y256"][0]
         / c["per_page"]["ef211/cell.s0.x704_y256"][2], 78.56, 0.01, PCT2)
    pin("§1.2 ambiguous creature texels", c["amb_creature"], 156254, COMMA)
    near("§1.2    ...share", 100.0 * c["amb_creature"] / c["tex_creature"], 10.25, 0.005, PCT2)
    pin("§1.2 ambiguous scenery texels", c["amb_scenery"], 1217754, COMMA)
    near("§1.2    ...share", 100.0 * c["amb_scenery"] / c["tex_scenery"], 39.75, 0.005, PCT2)
    near("§1.2 ef184 tex.part4 ambiguity",
         100.0 * c["per_page"]["ef184/tex.part4"][1] / c["per_page"]["ef184/tex.part4"][2],
         54.8, 0.05, PCT1)
    pin("§1.2 creature duplicate ENTRIES", c["dup_c"], 1979, COMMA)
    near("§1.2    ...share", 100.0 * c["dup_c"] / c["dup_c_tot"], 8.31, 0.005, PCT2)
    pin("§1.2    rows carrying >= 1 duplicate", c["dup_c_rows"], 75)
    pin("§1.2    worst multiplicity", c["dup_c_worst"], 57)
    pin("§1.2 scenery duplicate ENTRIES", c["dup_s"], 151328, COMMA)
    near("§1.2    ...share", 100.0 * c["dup_s"] / c["dup_s_tot"], 47.79, 0.005, PCT2)
    pin("§1.2    ...live entries only", c["dup_s_live"], 100102, COMMA)
    near("§1.2    ...that share", 100.0 * c["dup_s_live"] / c["dup_s_live_tot"], 38.12, 0.05, PCT2)
    pin("§1.2    rows carrying >= 1 duplicate", c["dup_s_rows"], 1528)
    pin("§1.2    of derived scenery rows", c["pal_rows_scen"], 3095)
    pin("§1.2    worst multiplicity", c["dup_s_worst"], 239)
    cc = c["classC"]
    # ⚠ MEASURED AT THE CENSUS SCOPE, which W6b-3 leaves byte-identical -- so this dossier number
    # still re-measures what §1.4 measured.  One of the 16 is withdrawn from the AUTHOR-FACING
    # surface by CHANNEL A's veto; G6b names it, and re-pinning it here would be re-aiming a control.
    pin("§1.4 exportable class-C cells", len(cc), 16)
    pin("§1.4    ...carrying >= 1 split group", sum(1 for x in cc if x["split"]), 11)
    pin("§1.4 duplicate groups in the editable rows", sum(x["groups"] for x in cc), 365)
    pin("§1.4 ★ ...that SPLIT under some alternate", sum(x["split"] for x in cc), 298)
    pin("§1.4 stock texels sitting on a split group", sum(x["on_split"] for x in cc), 119369,
        COMMA)
    worst = max(cc, key=lambda x: x["on_split"] / max(1, x["texels"]))
    near("§1.4 worst exposure (ef%d %s)" % (worst["ef"], worst["name"]),
         100.0 * worst["on_split"] / worst["texels"], 97.09, 0.01, PCT2)
    pin("§1.4    ...groups split there", (worst["split"], worst["groups"]), (42, 43))
    pin("§1.4 worst split multiplicity", max(x["worst"] for x in cc), 176)
    clean = [x for x in cc if x["ef"] == CLEAN_EF and x["name"] == CLEAN_CELL]
    pin("§1.4 the clean counterpart (ef211 x576_y256)",
        (clean[0]["alts"], clean[0]["groups"], clean[0]["split"]) if clean else None, (1, 0, 0))
    pin("§1.6 STP colour groups, creature", (c["stp_c"], c["stp_c_rows"]), (0, 0))
    pin("§1.6 STP colour groups, scenery", (c["stp_s"], c["stp_s_rows"]), (38, 4))
    pin("§1.6    ...by effect", sorted(c["stp_by_ef"].items()),
        [(11, 1), (235, 31), (286, 5), (498, 1)])
    pin("§1.9 lawful scenery rows with NO transparent entry", c["no_hole"], 45)
    pin("§1.9    ...of lawful scenery cells", c["n_scenery"], 147)
    pin("§1.9 creature rows with no transparent entry", c["creature_no_hole"], 0)
    pin("§1.9    ...of creature pages", c["n_creature"], 93)
    pin("§1.9 rows whose hole is NOT at index 0", c["hole_not_zero"], 26)
    pin("§1.9 4bpp rows already carrying 16 distinct colours",
        (c["rows4_full16"], c["rows4"]), (15, 40))
    # ⚠ REPORTED, NOT PINNED.  §1.9's "39 of 40 spend all 16" does not state WHICH reading of "spend"
    # it measured, and the two available ones give different answers on the same corpus.  A pin whose
    # predicate is a guess is a pin that will be satisfied by editing the gate.  Both are measured
    # here and neither is asserted; whoever owns the study record should settle the predicate.
    lines.append("%-52s %d (all 16 INDICES used by the picture -- re-finds the published 39) / %d "
                 "(16 DISTINCT words in the row) of %d.  REPORTED, not pinned: §1.9 does not state "
                 "which reading it measured, and choosing the one that agrees is not evidence."
                 % ("§1.9    ...4bpp rows that \"spend all 16\"",
                    c.get("rows4_all_indices_used", 0), c.get("rows4_all_distinct_words", 0),
                    c["rows4"]))
    near("§1.9 creature mean distinct live colours",
         sum(c["distinct_live"]) / len(c["distinct_live"]), 233.7, 0.05, F1)
    # ⚠ RE-PINNED 0.640 → 0.6443: the design's §1.9 measured the PERIMETER quad fan; the QUAD-ORDER
    # fix (kit 6ed66133, Z fan) landed on master after this board was authored on the recon lane and
    # rode the a3c16bcd merge, so the pin was a cache of a pre-fix measurement.  A/B at the re-pin:
    # the old fan monkeypatched back re-measures 0.640017 -- the pin's own source -- and the Z fan
    # 0.644309 (37/93 pages gain, 0 lose, +6,539 texels: bowtie wedges that had read as dead).
    # Provenance: w6q_QUANTIZE.md §4 item 3, QUAD-ORDER-DELTA.md §6.
    near("§1.9 creature mean covered fraction",
         sum(c["covered"]) / len(c["covered"]), 0.6443, 0.0005, F3)
    pin("§1.9 entry budget |H| <= B, creature", (c["budget_c"], c["n_creature"]), (93, 93))
    pin("§1.9    ...scenery", (c["budget_s"], c["n_scenery"]), (147, 147))
    pin("§1.9    tightest", c["tightest"][:1] + c["tightest"][1:],
        ("ef179 tex.part1", 255, 255))
    lines.append("%-52s %s texels over %d surfaces"
                 % ("§1.1 the population all of it is measured over",
                    "{:,}".format(c["texels"]), c["surfaces"]))
    ok = ok and c["texels"] == 4587520 and c["surfaces"] == 240
    return gate("G16 ★ THE RE-DERIVATION PIN -- every headline number RE-MEASURED", ok, *lines)


# --------------------------------------------------------------------------- G16b
def g16b_separation_sweep():
    """§1.3: NO THRESHOLD SEPARATES a legitimate fixed-palette edit from an unrepresentable one.

    9 thresholds x 6 creature pages x 3 edits.  This is the measurement that DEMOTES any
    quantization-error refusal to a disclosure, and any successor proposing one owes a sweep of this
    shape first -- so it is re-run here rather than cited.
    """
    if not _have_corpus():
        return gate("G16b the separation sweep", False, "no corpus")
    td = _tmp()
    blob = _load(HUE_EF)
    pages = RP.creature_texel_pages(blob)[:6]
    stats = {"hue8": [], "hue40": [], "unrep": []}
    THRESH = (1, 2, 4, 8, 16, 32, 64, 128, 256)
    for p in pages:
        words = RP.palette_words(blob, p)
        raw = blob[p.page_offset:p.page_offset + p.page_bytes]
        idx = list(RP.texel_view(p, raw))
        for label, mode in (("hue8", 8.0), ("hue40", 40.0), ("unrep", None)):
            src = _paint_source(blob, p, td)
            if mode is None:
                # a deliberately unrepresentable HARD MAGENTA repaint of every opaque texel
                from PIL import Image
                with Image.open(src) as im:
                    px = list(im.convert("RGBA").tobytes())
                for k in range(p.w * p.h):
                    if px[4 * k + 3] == 255:
                        px[4 * k:4 * k + 4] = [255, 0, 255, 255]
                im2 = Image.new("RGBA", (p.w, p.h))
                im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
                im2.save(src)
            else:
                _hue_rotate_paint(src, mode)
            _out, cen = RP.read_paint_png(src, p, words, idx)
            # the UNCLAMPED distribution -- the preview's per-texel map is clamped for display, and a
            # sweep run on a clamped map would see every large error as one value.
            hist = {int(k): v for k, v in cen["d_hist"].items()}
            op = max(1, cen["opaque"])
            stats[label].append(tuple(sum(v for d2, v in hist.items() if d2 > t) / float(op)
                                      for t in THRESH))
            os.remove(src)
    lines, ok = [], True
    lines.append("%-31s %s" % ("share of opaque texels with d^2 >",
                               "  ".join("%7d" % t for t in THRESH)))
    for label, title in (("hue8", "8 deg hue nudge"), ("hue40", "40 deg hue rotation"),
                         ("unrep", "hard-magenta (unrepresentable)")):
        hi = [max(s[k] for s in stats[label]) for k in range(len(THRESH))]
        lo = [min(s[k] for s in stats[label]) for k in range(len(THRESH))]
        lines.append("%-31s %s   (worst page)" % (title,
                                                  "  ".join("%6.2f%%" % (100 * v) for v in hi)))
        lines.append("%-31s %s   (best page)" % ("", "  ".join("%6.2f%%" % (100 * v) for v in lo)))
    overlap = sum(1 for k in range(len(THRESH))
                  if max(s[k] for s in stats["hue40"]) >= min(s[k] for s in stats["unrep"]))
    lines.append("%-31s worst(hue40) >= min(unrepresentable) at %d of %d thresholds"
                 % ("MEASURED SEPARATION:", overlap, len(THRESH)))
    if overlap < len(THRESH):
        lines.append("⚠ THIS DISAGREES WITH D1's 9-of-9 ON THIS FIXTURE SET (6 pages of ONE effect,")
        lines.append("  and a whole-page hard-magenta repaint).  It is REPORTED rather than tuned")
        lines.append("  into agreement: a sweep edited until it produces the expected answer is not")
        lines.append("  a measurement.  It changes NOTHING that ships -- see the assertion below.")
    # ★ WHAT THIS GATE ACTUALLY ASSERTS, and it is the SAFER half of the claim either way.
    # The sweep's CONSEQUENCE is that the census is a DISCLOSURE and never a refusal.  A sweep that
    # found separation would still not license a threshold -- it would only be the FIRST of the two
    # things a threshold owes (the second being that the separation survives the whole surface).  So
    # what is gated here is the shipped posture: no error statistic is compared against any constant
    # anywhere in the lane, and a build whose every texel is maximally wrong still passes every gate.
    blob = _load(HUE_EF)
    p = RP.creature_texel_pages(blob)[0]
    src = _paint_source(blob, p, td)
    from PIL import Image
    with Image.open(src) as im:
        px = list(im.convert("RGBA").tobytes())
    for k in range(p.w * p.h):
        if px[4 * k + 3] == 255:
            px[4 * k:4 * k + 4] = [255, 0, 255, 255]
    im2 = Image.new("RGBA", (p.w, p.h))
    im2.putdata([tuple(px[4 * k:4 * k + 4]) for k in range(p.w * p.h)])
    im2.save(src)
    b = RP.build(_texel_spec(HUE_EF, [_paint_row("tex.part0", src,
                                                 acknowledge_cutout_reshape=True)]), "?", blob=blob)
    b.check = RP.self_check(b)
    bad = [g.name for g in b.check.gates if not g.ok]
    cen = b.enabled[0].census
    ok = not bad
    lines.append("%-31s mean d^2 %.1f, worst %d of %d -- %d/%d gates GREEN, 0 refusals"
                 % ("A MAXIMALLY WRONG PAINT BUILD:", cen["mean_d2"], cen["worst_d2"],
                    cen["cube_diagonal_sq"], sum(1 for g in b.check.gates if g.ok),
                    len(b.check.gates)))
    if bad:
        lines.append("   *** a census statistic REFUSED: %s ***" % "; ".join(bad))
    src2 = _paint_source(blob, p, td)
    _o2, cen2 = RP.read_paint_png(src2, p, RP.palette_words(blob, p),
                                  RP.texel_view(p, blob[p.page_offset:p.page_offset + p.page_bytes]))
    ok = ok and cen2["worst_d2"] == 0
    lines.append("%-31s worst d^2 %d -- and the SAME lane is byte-exact on the no-op, so the census "
                 "is not a gate that happens to be off" % ("...while the no-op through it:",
                                                           cen2["worst_d2"]))
    lines.append("THE CONSEQUENCE, BINDING ON THIS SPEC AND ANY SUCCESSOR: a fixed CLUT is a small")
    lines.append("subset of the 32,768-colour cube, so ANY hue move leaves it -- and a hue move is")
    lines.append("this lane's own primary use case.  The quantization-error census therefore ships as")
    lines.append("a DISCLOSURE, never a refusal, and any successor proposing an error-threshold")
    lines.append("constant owes a separation sweep of this shape run on ITS OWN distribution first.")
    return gate("G16b §1.3 the error census is a DISCLOSURE, never a refusal (+ the sweep)",
                ok, *lines)


# --------------------------------------------------------------------------- G17
def g17_fail_safes_labelled():
    if not _have_corpus():
        return gate("G17 the fail-safes are labelled", False, "no corpus")
    td = _tmp()
    lines, ok = [], True
    blob = _load(HUE_EF)
    p = RP.texel_page(blob, "tex.part0", HUE_EF)
    words = RP.palette_words(blob, p)
    raw = blob[p.page_offset:p.page_offset + p.page_bytes]
    src = _paint_source(blob, p, td)
    _out, cen = RP.read_paint_png(src, p, words, RP.texel_view(p, raw))
    text = "\n".join(RP.census_lines(cen))
    for want, why in (("FAIL-SAFE: ", "the alternate-split census line"),
                      ("structurally unreachable", "...and its population on a creature page"),
                      ("the STP TERM decided the pick", "the STP tie-break component, on its OWN "
                                                        "line"),
                      ("0 on 93/93 creature rows and 38 groups on 4 of 3,095",
                       "...with the population that is actually its own"),
                      ("0x0000 is the container's cutout word BY VALUE", "the opaque-black line"),
                      ("incumbent NOT NAMEABLE by the row",
                       "the unnameable-incumbent class -- the one way a texel can move that THE "
                       "INCUMBENT LOCK cannot hold"),
                      ("FAIL-SAFE, corpus population 0", "...with its own population"),
                      ("DISCLOSURE", "the quantization-error census itself")):
        hit = want in text
        ok = ok and hit
        lines.append("%-52s %s" % (why, "LABELLED" if hit else "*** CLAIMED, not labelled ***"))
    # R5's own label
    b = bytearray(blob)
    struct.pack_into("<%dH" % p.clut_entries, b, p.clut_offset, *([0] * p.clut_entries))
    fired, msg = _refuses(RP.read_paint_png, src, RP.texel_page(bytes(b), "tex.part0", HUE_EF),
                          RP.palette_words(bytes(b), p), RP.texel_view(p, raw))
    hit = fired and "LABELLED A FAIL-SAFE" in msg and "population of this class is 0" in msg
    ok = ok and hit
    lines.append("%-52s %s" % ("R5 (a row with no opaque entry)",
                               "LABELLED with population 0" if hit else "*** CLAIMED ***"))
    # the codec's own docstring, whitespace-normalised (a wrapped line is still one sentence)
    doc = " ".join((RP.read_paint_png.__doc__ or "").split())
    hit = ("LABELLED FAIL-SAFE with a named population" in doc
           and "93/93 creature rows by construction" in doc)
    ok = ok and hit
    lines.append("%-52s %s" % ("the codec's own docstring labels the STP term",
                               "yes" if hit else "*** unlabelled ***"))
    # ...and pack4's index > 15 belt is labelled structurally unreachable at its own call site
    doc2 = " ".join((RP.read_paint_png.__doc__ or "").split())
    belt = "pack4" in (RP.pack4.__doc__ or "") or "REFUSES any index > 15" in (RP.pack4.__doc__ or "")
    ok = ok and belt
    lines.append("%-52s %s" % ("pack4's index > 15 belt states its own rule",
                               "yes (refuses rather than masking)" if belt else "*** silent ***"))
    return gate("G17 the FAIL-SAFES are LABELLED, not claimed as proofs", ok, *lines)


# --------------------------------------------------------------------------- G18
def _byte_literals(path: str, minlen: int = 6):
    """Every candidate stock-byte run in a committable file.

    TWO extractors, because one of them cannot see the other's spelling: the AST finds ``bytes``
    constants in a ``.py``, and a `\\xNN` run scan finds them in ANY committable text -- which is how a
    literal transcribed into a MARKDOWN table (a real occurrence in this rung's own doc) gets scanned
    at all. A provenance gate that only reads Python is a provenance gate with a documentation-shaped
    hole in it.
    """
    import ast
    import re
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    if path.lower().endswith(".py"):
        try:
            tree = ast.parse(src)
        except SyntaxError:                                      # pragma: no cover
            tree = None
        for node in (ast.walk(tree) if tree is not None else ()):
            if isinstance(node, ast.Constant) and isinstance(node.value, (bytes, bytearray)):
                if len(node.value) >= minlen:
                    out.append(bytes(node.value))
    for m in re.finditer(r"(?:\\x[0-9a-fA-F]{2}){%d,}" % minlen, src):
        try:
            out.append(bytes.fromhex(m.group(0).replace("\\x", "")))
        except ValueError:                                       # pragma: no cover
            pass
    return out


def g18_provenance():
    if not _have_corpus():
        return gate("G18 provenance", False, "no corpus")
    lines, ok = [], True
    lits = []
    for name in COMMITTABLE:
        path = os.path.join(_HERE, name)
        if not os.path.isfile(path):                             # pragma: no cover
            ok = False
            lines.append("*** missing committable file %s" % name)
            continue
        lits += [(name, b) for b in _byte_literals(path)]
    hits = 0
    if lits:
        for _ef, path in _effects():
            with open(path, "rb") as fh:
                blob = fh.read()
            for name, lit in lits:
                if lit in blob:
                    hits += 1
                    ok = False
                    lines.append("*** %s carries a %d-byte run present in %s"
                                 % (name, len(lit), os.path.basename(path)))
    lines.append("%-52s %d literal(s) >= 6 bytes, %d present in any of the 372 containers"
                 % ("byte-literal scan of every file this rung adds", len(lits), hits))
    # every decoded page goes through the provenance guard, with no --force
    fired, msg = _refuses(RP.export_art, _load(HUE_EF), HUE_EF,
                          os.path.join(_REPO, "_never_written"))
    hit = fired or "git repo" in msg
    try:
        KE.assert_local_only(os.path.join(_REPO, "_never_written"))
        guard = False
    except Exception as e:
        guard = "git repo" in str(e)
    ok = ok and guard and not os.path.exists(os.path.join(_REPO, "_never_written"))
    lines.append("%-52s %s" % ("export.assert_local_only refuses a repo destination",
                               "yes (no --force)" if guard else "*** ACCEPTED ***"))
    lines.append("%-52s %s" % ("this gate's own scratch root", _tmp()))
    inside = os.path.abspath(_tmp()).startswith(os.path.abspath(_REPO))
    ok = ok and not inside
    lines.append("%-52s %s" % ("   ...is outside the checkout", "yes" if not inside else "*** NO ***"))
    lines.append("%-52s every SE-derived artifact of this rung lives under "
                 r"C:\gd\SCRATCH\summon-format\quantize-w6q\ " % "AND:")
    return gate("G18 provenance: zero SE bytes committable", ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not _have_corpus():
        print("\nNOTE: no extracted corpus at %s -- every gate will FAIL loudly rather than skip."
              % CORPUS)
    try:
        g1_the_no_op()
        g2_render_read_identity()
        g3_determinism()
        g4_alpha_governs()
        g5_alternate_split_fires()
        g6_alternate_split_does_not_over_fire()
        g6b_over_fire_measurement()
        g7_composed_palette_refusal()
        g8_composed_palette_does_not_over_fire()
        g9_zero_clut_bytes()
        g10_region_invariant()
        g11_cast_proven_shas()
        g12_key_set_pins()
        g13_every_shipped_spec_still_loads()
        g14_lane_tuple_pin()
        g15_refusal_string_pins()
        g16_re_derivation_pin()
        g16b_separation_sweep()
        g17_fail_safes_labelled()
        g18_provenance()
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
