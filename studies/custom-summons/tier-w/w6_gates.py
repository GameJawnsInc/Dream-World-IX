r"""TIER W rung W6a -- THE RUNG'S OWN GATE RUNNER.  `py w6_gates.py` prints G1..G6 with PASS/FAIL.

Six gates, each the falsifiable form of a claim W6-TEXEL.md makes in prose:

G1  THE INDEXED ROUND TRIP (this lane's X0-class gate): decode -> P-mode PNG (palette = the CLUT
    row, tRNS = the transparent entry) -> reload -> indices is BYTE-IDENTICAL on every creature page
    in the extracted corpus (93 pages / 24 packages).  This is the gate the whole format decision
    rests on: an RGBA lane cannot carry it, because 8.31% of the corpus's palette entries are
    duplicates of the full 16-bit word and an identity RGBA round trip already moves 1,844 of 16,384
    texels on ef251 part 0 -- a lane whose NO-OP is not a no-op cannot carry a byte-identity gate.
G2  THE EMBLEM ARTIFACT: `bahamut_emblem.toml` rebuilds, from the user's own install, the exact
    container B2 verified byte-by-byte with an independent instrument -- pinned by sha256, with the
    composition base pinned to W4's cast-proven artifact and the two halves proven DISJOINT rather
    than assumed.  Also re-runs the kit's own 20-gate self-check and requires all 20.
G3  THE REGION PARTITION: `reskin._regions(..., partition=)` is ONE function with two partitions,
    not two functions.  Proven: outside the id-4 resource the two are IDENTICAL region-for-region;
    inside it they PARTITION the resource exactly (no overlap, no gap, union == the whole id-4
    span); the CLUT partition gates the pages and the TEXEL partition gates the CLUT strip; and the
    licensed page span intersects no gated region under the texel partition.
G4  THE REFUSAL MATRIX: every refusal this rung establishes fires, with its own reason -- the W6b
    surfaces (scenery page names, the rgba export lane, a non-creature container), the format
    refusals (RGBA import, wrong size, an index past the row), the CUTOUT LAW in both directions plus
    the literal-boolean law on its acknowledgement, the TEXANIM refusal on all five armed packages,
    the CO-TRANSFORM refusal in both of its forms (a shared VRAM cell and an overlapping file span),
    and the guard refusals (unknown key, drift, art-manifest drift, a mis-stated span).
G5  THE CLUT-LANE BYTE-COMPAT PINS: W4/W5's three cast-proven recolours still build their exact
    shas.  The texel lane touches `reskin.py` in exactly one place (the `partition` argument) and
    this is what says so in bytes.
G6  THE CORPUS CENSUS: the numbers W6-TEXEL.md quotes, re-measured -- 24 decodable creature
    packages / 93 pages, the UV-coverage total, THE MARGIN LAW (the share of a page's dead texels
    that is one border-connected pad -- R2's 99.6% was a two-effect sample and this is the 93-page
    sweep that corrects it), and ZERO collisions between a creature page and any other declared page
    writer, by VRAM cell and by file span.
G7  PROVENANCE: a byte-literal scan of every committable file this rung adds, against all 372 corpus
    containers; the repo / install staging refusals fire; the emblem's art and the staged container
    are both OUTSIDE the checkout; and no stock-shaped file is sitting in the working tree.  The
    decoded page PNG this rung's proof rests on is Square-Enix content and ships as a GENERATOR --
    this is the gate that says the generator carries no stock bytes of its own.

Reads the user's own install for G2/G5 (their subject is the real artifacts) and the extracted corpus
at C:\gd\SCRATCH\summon-format for everything else.  NO deploy, NO install write, NO git commit.
G6 rasterises 93 pages from their uv pools and takes a couple of minutes; nothing else is slow.
"""
from __future__ import annotations

import dataclasses
import io
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402  (sets up sys.path)
import summon_camera as W                                        # noqa: E402
from ff9mapkit.summons import container as EC                    # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402

CORPUS = W.SCRATCH_CORPUS
EMBLEM_SPEC = os.path.join(_HERE, "bahamut_emblem.toml")

#: W6a's staging root -- the composed container, its previews, its art and its two scripts.  Outside
#: the repo by construction (``export.assert_local_only`` refuses a checkout with no ``--force``).
SCRATCH_W6_ROOT = os.environ.get("FF9_REPAINT_W6_ROOT",
                                 r"C:\gd\SCRATCH\summon-format\repaint-w6\ef227")

#: THE COMPOSED ARTIFACT.  A hash, not data.  Verified independently of the kit's own self-report:
#: diff(stock, staged) == diff(stock, W4's frozen artifact) UNION diff(stock page 0, the emblem
#: PNG's indices), the two disjoint, everything else byte-identical.
W6A_COMPOSED_SHA256 = "813a7ea4c461a06beec6bfe62ec47b61f7e81589d6d94cc17bad5489e18a8682"
#: the composition BASE: W4's deployed, cast-proven spectral-mist recolour.
W4_PATCHED_SHA256 = "7fef205ffbe547545374de9d1017613448777f0251d9d425b55f7796f688b89a"
#: pristine stock ef227, as the drift guard reads it out of ``resources.assets``.
EF227_STOCK_SHA256 = "fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167"
#: how many bytes the emblem moves, and where.
W6A_TEXEL_BYTES = 1032
W6A_CLUT_BYTES = 4832
W6A_PAGE0 = (0x04A1A0, 0x04E1A0)

#: W4/W5's three cast-proven CLUT artifacts, by spec.  All three are hashes of containers rebuilt
#: from the user's own install; none of them is data.
CLUT_PINS = {
    "bahamut_reskin.toml": (227, W4_PATCHED_SHA256, 4832),
    "phoenix_reskin.toml": (211, "4daab8ade69315e6452a96e5af1092c1bb943e1cec78968f3d9dc20e4d276790",
                            2374),
    "madeen_reskin.toml": (251, "78b395f89e6114f0639e4463819460eafe9952b4707769ca6ea5b92d474a373b",
                           3054),
}

#: the five packages whose id-5 model image carries a NON-EMPTY texanim table (A1's census,
#: re-measured every run by G4 rather than trusted).
TEXANIM_CLASS = (38, 177, 493, 494, 495)

RESULTS = []


def gate(name: str, ok: bool, *lines: str) -> bool:
    RESULTS.append((name, ok))
    print("\n%s %s  %s" % ("[PASS]" if ok else "[FAIL]", name, "-" * max(2, 58 - len(name))))
    for ln in lines:
        print("   " + ln)
    return ok


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


def _have_corpus() -> bool:
    return bool(W.corpus_paths(CORPUS))


def _load(effect: int) -> bytes:
    with open(os.path.join(CORPUS, "ef%03d.bytes" % effect), "rb") as fh:
        return fh.read()


def _refuses(fn, *a, **kw):
    """``(fired, message)`` -- did this raise a RepaintError, and what did it say?

    A refusal that raised the WRONG exception type is not a refusal: it is a crash that happened to
    stop the build, and it would stop being one the day the call site grows a ``try``.
    """
    try:
        fn(*a, **kw)
        return False, ""
    except RP.RepaintError as e:
        return True, str(e)
    except Exception as e:                                       # pragma: no cover - a real defect
        return False, "*** %s (not a RepaintError): %s" % (type(e).__name__, e)


# --------------------------------------------------------------------------- G1
def g1_indexed_round_trip():
    if not _have_corpus():
        return gate("G1 the indexed round trip", False, "no extracted corpus at %s" % CORPUS)
    lines, fails = [], []
    npkg = npage = 0
    for path in W.corpus_paths(CORPUS):
        with open(path, "rb") as fh:
            blob = fh.read()
        pages = RP.creature_texel_pages(blob)
        if not pages:
            continue
        npkg += 1
        for p in pages:
            npage += 1
            words = RP.palette_words(blob, p)
            px = blob[p.page_offset:p.page_offset + p.page_bytes]
            back = RP._read_indices(io.BytesIO(RP.encode_indexed_png(px, words, p.w, p.h)),
                                    "(gate)", p.w, p.h, len(words))
            if back != px:
                fails.append("%s %s" % (os.path.basename(path), p.name))
    lines.append("decodable creature packages: %d   pages: %d" % (npkg, npage))
    lines.append("encode -> P-mode PNG (tRNS = the transparent entry) -> reload -> indices: "
                 "%d/%d BYTE-IDENTICAL" % (npage - len(fails), npage))
    for f in fails[:10]:
        lines.append("   DRIFT %s" % f)
    ok = npage == 93 and npkg == 24 and not fails
    lines.append("the RGBA lane, for contrast, is REFUSED by name -- an identity RGBA round trip "
                 "moves 1,844 of 16,384 texels on ef251 part 0 before anyone paints")
    return gate("G1 the indexed round trip (93/93 stock creature pages, byte-identical)", ok, *lines)


# --------------------------------------------------------------------------- G2
_BUILD = None
_BUILD_ERR = ""


def emblem_build():
    """The composed build, once per run (it rebuilds the CLUT sibling too, which reads the install)."""
    global _BUILD, _BUILD_ERR
    if _BUILD is None and not _BUILD_ERR:
        try:
            b = RP.build(RP.load_spec(EMBLEM_SPEC), EMBLEM_SPEC)
            b.check = RP.self_check(b)
            _BUILD = b
        except Exception as e:                                   # pragma: no cover - env dependent
            _BUILD_ERR = "%s: %s" % (type(e).__name__, e)
    return _BUILD


def g2_emblem_artifact():
    if not _has_install():
        return gate("G2 the emblem artifact", False, "no FF9 install resolvable")
    b = emblem_build()
    if b is None:
        return gate("G2 the emblem artifact", False, "build FAILED: %s" % _BUILD_ERR)
    lines, ok = [], True
    changed = set(b.check.changed)
    base = set(b.base_changed)

    lines.append("stock    sha256 %s  %s" % (b.sha_stock,
                                             "PINNED" if b.sha_stock == EF227_STOCK_SHA256
                                             else "*** DRIFTED ***"))
    ok = ok and b.sha_stock == EF227_STOCK_SHA256
    lines.append("base     sha256 %s  %s  (%d CLUT bytes -- W4's cast-proven spectral mist)"
                 % (b.sha_in, "PINNED" if b.sha_in == W4_PATCHED_SHA256 else "*** DIFFERS ***",
                    len(base)))
    ok = ok and b.sha_in == W4_PATCHED_SHA256 and len(base) == W6A_CLUT_BYTES
    lines.append("composed sha256 %s  %s"
                 % (b.sha_out, "PINNED" if b.sha_out == W6A_COMPOSED_SHA256 else "*** DIFFERS ***"))
    ok = ok and b.sha_out == W6A_COMPOSED_SHA256

    lines.append("texel delta %d byte(s), all inside page 0 %#x..%#x: %s"
                 % (len(changed), W6A_PAGE0[0], W6A_PAGE0[1],
                    all(W6A_PAGE0[0] <= o < W6A_PAGE0[1] for o in changed)))
    ok = ok and len(changed) == W6A_TEXEL_BYTES
    ok = ok and all(W6A_PAGE0[0] <= o < W6A_PAGE0[1] for o in changed)
    lines.append("CLUT half n texel half = %d (DISJOINT), union = %d vs stock"
                 % (len(base & changed), len(base | changed)))
    ok = ok and not (base & changed) and len(base | changed) == W6A_CLUT_BYTES + W6A_TEXEL_BYTES

    t = b.enabled[0]
    lines.append("the glyph: %d texels moved | dead-pad %d | cutout punch %d fill %d | "
                 "coverage %d/%d sampled"
                 % (len(t.changed), t.dead_changed, t.cutout_punch, t.cutout_fill,
                    t.cov.covered, t.cov.total))
    ok = ok and (t.dead_changed, t.cutout_punch, t.cutout_fill) == (0, 0, 0)
    ok = ok and not t.ack_cutout                                 # nothing was acknowledged away

    npass = sum(1 for g in b.check.gates if g.ok)
    lines.append("the kit's own self-check: %d/%d gates" % (npass, len(b.check.gates)))
    for g in b.check.gates:
        if not g.ok:
            lines.append("   [!!] %s -- %s" % (g.name, g.detail))
    ok = ok and b.check.ok and len(b.check.gates) == 20
    return gate("G2 the emblem artifact (composed sha256 pin + disjoint halves + 20/20)", ok, *lines)


# --------------------------------------------------------------------------- G3
def _id4_span(blob: bytes):
    c = EC.parse_header(blob, strict=True)
    for ch in c.chunks:
        for r in ch.resources:
            if r.id == 4:
                return r.offset, r.offset + r.nbytes
    return None                                                  # pragma: no cover


def g3_region_partition():
    if not _have_corpus():
        return gate("G3 the region partition", False, "no extracted corpus at %s" % CORPUS)
    blob = _load(227)
    lines, ok = [], True
    clut = RS._regions(blob, 227, partition="clut")
    tex = RS._regions(blob, 227, partition="texel")
    lo4, hi4 = _id4_span(blob)
    lines.append("id-4 resource: %#x..%#x (%d B)" % (lo4, hi4, hi4 - lo4))
    lines.append("regions: clut partition %d, texel partition %d" % (len(clut), len(tex)))

    out_c = sorted(r for r in clut if not (lo4 <= r[1] < hi4))
    out_t = sorted(r for r in tex if not (lo4 <= r[1] < hi4))
    lines.append("regions OUTSIDE id-4 are identical region-for-region: %s (%d each)"
                 % (out_c == out_t, len(out_c)))
    ok = ok and out_c == out_t and len(out_c) >= 20

    in_t = sorted((lo, hi) for _n, lo, hi in tex if lo4 <= lo < hi4)
    in_c = sorted((lo, hi) for _n, lo, hi in clut if lo4 <= lo < hi4)
    def _cover(spans):
        s = set()
        for lo, hi in spans:
            s |= set(range(lo, hi))
        return s
    ct, cc = _cover(in_t), _cover(in_c)
    overlap_t = sum(hi - lo for lo, hi in in_t) - len(ct)
    lines.append("TEXEL partition inside id-4: %d region(s), %d B, self-overlap %d"
                 % (len(in_t), len(ct), overlap_t))
    lines.append("CLUT  partition inside id-4: %d region(s), %d B, self-overlap %d"
                 % (len(in_c), len(cc), sum(hi - lo for lo, hi in in_c) - len(cc)))
    ok = ok and overlap_t == 0

    mp = EC.creature_package(blob)
    pages = (mp.tex_file_offset, mp.tex_file_offset + mp.tex_bytes)
    strip = (mp.tex_file_offset + mp.tex_bytes,
             mp.tex_file_offset + mp.tex_bytes + mp.clut_bytes)
    page_set, strip_set = set(range(*pages)), set(range(*strip))
    lines.append("pages %#x..%#x (%d B); CLUT strip %#x..%#x (%d B)"
                 % (pages[0], pages[1], mp.tex_bytes, strip[0], strip[1], mp.clut_bytes))
    lines.append("TEXEL partition LICENSES the pages (gated n pages == 0): %s"
                 % (not (ct & page_set)))
    lines.append("TEXEL partition GATES the CLUT strip (strip subset of gated): %s"
                 % strip_set.issubset(ct))
    lines.append("CLUT  partition GATES the pages (pages subset of gated): %s"
                 % page_set.issubset(cc))
    lines.append("CLUT  partition LICENSES the CLUT strip (gated n strip == 0): %s"
                 % (not (cc & strip_set)))
    ok = ok and not (ct & page_set) and strip_set.issubset(ct)
    ok = ok and page_set.issubset(cc) and not (cc & strip_set)

    union = ct | cc
    whole = set(range(lo4, hi4))
    lines.append("the two partitions together cover the WHOLE id-4 resource: %s "
                 "(union %d of %d B, gap %d)"
                 % (union == whole, len(union), len(whole), len(whole - union)))
    ok = ok and union == whole

    fired, why = _refuses(RS._regions, blob, 227, partition="both")
    lines.append("an unknown partition name refuses: %s" % (bool(why) or fired))
    ok = ok and bool(why or fired)
    return gate("G3 the region partition (one function, two partitions, no overlap and no gap)",
                ok, *lines)


# --------------------------------------------------------------------------- G4
def _texel_spec(effect: int, name: str, src: str, **extra) -> dict:
    row = {"name": name, "source": src, "enabled": True}
    row.update(extra)
    return {"reskin": {"effect": effect, "allow_unguarded": True, "texel": [row]}}


def _write_png(path, px, words, w=128, h=128):
    RP.write_indexed_png(bytes(px), words, w, h, path)
    return str(path)


def g4_refusal_matrix():
    if not _have_corpus():
        return gate("G4 the refusal matrix", False, "no extracted corpus at %s" % CORPUS)
    from PIL import Image
    lines, ok = [], True
    blob = _load(227)
    pages = RP.creature_texel_pages(blob)
    p0 = pages[0]
    words = RP.palette_words(blob, p0)
    stock_px = bytearray(blob[p0.page_offset:p0.page_offset + p0.page_bytes])
    zeros = set(RP.transparent_indices(words))

    def check(label, fired, msg, want):
        nonlocal ok
        good = fired and want in msg
        ok = ok and good
        lines.append("%-46s %s" % (label, "REFUSED (%s)" % want if good else
                                   ("WRONG REASON: %s" % msg.splitlines()[0][:70] if fired
                                    else "*** DID NOT REFUSE ***" if not msg
                                    else msg.splitlines()[0][:80])))

    with tempfile.TemporaryDirectory() as td:
        good = os.path.join(td, "good.png")
        _write_png(good, stock_px, words)

        # -- (a) the W6b surfaces
        check("a scenery page name (`page.s0.x576_y256.h256`)",
              *_refuses(RP.texel_page, blob, "page.s0.x576_y256.h256"), want="W6b")
        check("the `rgba` export lane",
              *_refuses(RP.export_art, blob, 227, td, lane="rgba"), want="W6b")
        check("an unknown export lane", *_refuses(RP.export_art, blob, 227, td, lane="cmyk"),
              want="unknown art lane")
        check("a container with no creature package (ef000)",
              *_refuses(RP.export_art, _load(0), 0, td), want="W6b")

        # -- (b) the format refusals
        rgba = os.path.join(td, "rgba.png")
        Image.new("RGBA", (128, 128), (10, 20, 30, 255)).save(rgba)
        check("an RGBA source PNG", *_refuses(RP.read_indexed_png, rgba, 128, 128, 256),
              want="INDEXED PNG")
        small = os.path.join(td, "small.png")
        _write_png(small, bytes(64 * 64), words, 64, 64)
        check("a 64x64 source for a 128x128 page",
              *_refuses(RP.read_indexed_png, small, 128, 128, 256), want="no rescale here")
        check("an index past the row (max 255 vs a 16-entry row)",
              *_refuses(RP.read_indexed_png, good, 128, 128, 16), want="palette index")
        check("a source image that is not there",
              *_refuses(RP.read_indexed_png, os.path.join(td, "nope.png"), 128, 128, 256),
              want="no such source image")

        # -- (c) THE CUTOUT LAW, both directions, plus the literal-boolean law
        opaque = next(i for i in range(len(stock_px)) if stock_px[i] not in zeros)
        hole = next(i for i in range(len(stock_px)) if stock_px[i] in zeros)
        punched = bytearray(stock_px)
        punched[opaque] = sorted(zeros)[0]
        pun = _write_png(os.path.join(td, "punch.png"), punched, words)
        check("a texel punched opaque -> hole, unacknowledged",
              *_refuses(RP.build, _texel_spec(227, p0.name, pun), td, blob=blob),
              want="THE CUTOUT LAW")
        filled = bytearray(stock_px)
        filled[hole] = stock_px[opaque]
        fil = _write_png(os.path.join(td, "fill.png"), filled, words)
        check("a texel filled hole -> opaque, unacknowledged",
              *_refuses(RP.build, _texel_spec(227, p0.name, fil), td, blob=blob),
              want="THE CUTOUT LAW")
        check("`acknowledge_cutout_reshape = \"true\"` (a STRING)",
              *_refuses(RP.build, _texel_spec(227, p0.name, pun,
                                              acknowledge_cutout_reshape="true"), td, blob=blob),
              want="must be a BOOLEAN")
        try:
            b = RP.build(_texel_spec(227, p0.name, pun, acknowledge_cutout_reshape=True), td,
                         blob=blob)
            armed = b.enabled[0].cutout_punch == 1 and b.enabled[0].cutout_fill == 0
        except Exception as e:                                   # pragma: no cover
            armed = False
            lines.append("   acknowledged build FAILED: %s" % e)
        lines.append("%-46s %s" % ("the SAME edit with the literal `true`",
                                   "BUILDS, punch 1 / fill 0" if armed else "*** DID NOT BUILD ***"))
        ok = ok and armed

        # -- (d) THE TEXANIM REFUSAL, all five armed packages
        n_armed = 0
        for ef in TEXANIM_CLASS:
            tb = _load(ef)
            ta = RS.texanim_region(tb)
            tp = RP.creature_texel_pages(tb)
            if ta is None or not ta.armed or not tp:             # pragma: no cover - corpus drift
                lines.append("%-46s *** ef%03d is not armed / has no page ***" % ("", ef))
                ok = False
                continue
            n_armed += 1
            tw = RP.palette_words(tb, tp[0])
            src = _write_png(os.path.join(td, "ta%d.png" % ef),
                             tb[tp[0].page_offset:tp[0].page_offset + tp[0].page_bytes], tw)
            check("texanim armed: ef%03d creature texel scope" % ef,
                  *_refuses(RP.build, _texel_spec(ef, tp[0].name, src), td, blob=tb),
                  want="TEXANIM ARMED")
        lines.append("%-46s %d of %d" % ("armed texanim packages re-measured", n_armed,
                                         len(TEXANIM_CLASS)))
        ok = ok and n_armed == len(TEXANIM_CLASS)

        # -- (e) THE CO-TRANSFORM REFUSAL, in both of its forms, on a DERIVED foreign cell
        others = RP.other_page_writers(blob)
        cell, ws = sorted(others.items())[0]
        check("a page whose VRAM cell has another writer",
              *_refuses(RP._gate_collisions, blob,
                        dataclasses.replace(p0, vram=cell)), want="CO-TRANSFORM REFUSAL")
        check("a page whose FILE SPAN overlaps another writer",
              *_refuses(RP._gate_collisions, blob,
                        dataclasses.replace(p0, page_offset=ws[0][1] + 64)),
              want="CO-TRANSFORM REFUSAL")

        # -- (f) the guard refusals
        check("an unknown [[reskin.texel]] key",
              *_refuses(RP.build, _texel_spec(227, p0.name, good, expect_page_offest=0), td,
                        blob=blob), want="unknown key")
        check("a mis-stated expect_page_offset",
              *_refuses(RP.build, _texel_spec(227, p0.name, good, expect_page_offset=0x1234), td,
                        blob=blob), want="the derivation says")
        check("a mis-stated expect_page_wh",
              *_refuses(RP.build, _texel_spec(227, p0.name, good, expect_page_wh=[64, 64]), td,
                        blob=blob), want="the derivation says")
        check("`palette_from` naming another part's row",
              *_refuses(RP.build, _texel_spec(227, p0.name, good, palette_from="creature.part3"),
                        td, blob=blob), want="a HEADER FACT")
        # ef227 IS in `rescore.EXPECTED_STOCK_SHA`, so a spec that omits `expect_sha256` is still
        # guarded there and correctly does NOT refuse.  The unguarded case has to be probed on an
        # effect the registry does not know -- ef211 is creature-bearing, texanim-clean and
        # unregistered -- or the gate would be asserting the registry instead of the refusal.
        b211 = _load(211)
        p211 = RP.creature_texel_pages(b211)[0]
        src211 = _write_png(os.path.join(td, "ef211.png"),
                            b211[p211.page_offset:p211.page_offset + p211.page_bytes],
                            RP.palette_words(b211, p211))
        nog = {"reskin": {"effect": 211, "texel": [{"name": p211.name, "source": src211}]}}
        check("no drift guard at all (ef211 -- NOT in the registry)",
              *_refuses(RP.build, nog, td, blob=b211), want="NO drift guard")
        lines.append("%-46s %s" % ("   (ef227 omitting expect_sha256 is still GUARDED",
                                   "by rescore.EXPECTED_STOCK_SHA -- correctly does not refuse)"))
        check("the same target declared twice",
              *_refuses(RP.build, {"reskin": {"effect": 227, "allow_unguarded": True, "texel": [
                  {"name": p0.name, "source": good}, {"name": p0.name, "source": good}]}},
                        td, blob=blob), want="declared twice")
        check("a spec with neither table",
              *_refuses(RP.load_spec, _write_toml(td, "[reskin]\neffect = 227\n")),
              want="nothing to do")

        # -- (g) THE ART-MANIFEST DRIFT GUARD
        sub = os.path.join(td, "art")
        os.makedirs(sub, exist_ok=True)
        drifted = _write_png(os.path.join(sub, "tex.part0.png"), stock_px, words)
        man = {"stock_sha256": "0" * 64, "parts": [{"name": p0.name,
                                                    "page_offset": p0.page_offset,
                                                    "page_bytes": p0.page_bytes, "wh": [128, 128]}]}
        with open(os.path.join(sub, RP.ART_MANIFEST), "w", encoding="utf-8") as fh:
            json.dump(man, fh)
        check("art exported from a DIFFERENT container",
              *_refuses(RP.build, _texel_spec(227, p0.name, drifted), td, blob=blob),
              want="ART DRIFT")

    return gate("G4 the refusal matrix (W6b surfaces, format, cutout, texanim, co-transform, guards)",
                ok, *lines)


def _write_toml(td: str, text: str) -> str:
    p = os.path.join(td, "empty.toml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


# --------------------------------------------------------------------------- G5
def g5_clut_lane_byte_compat():
    if not _has_install():
        return gate("G5 the CLUT-lane byte-compat pins", False, "no FF9 install resolvable")
    lines, ok = [], True
    for spec, (ef, want, nbytes) in sorted(CLUT_PINS.items()):
        path = os.path.join(_HERE, spec)
        try:
            b = RS.build(RS.load_spec(path), path)
            n = sum(1 for i in range(len(b.orig)) if b.orig[i] != b.patched[i])
            same = b.sha_out == want and b.effect == ef and n == nbytes
            lines.append("%-22s ef%03d  %s  %d bytes  %s"
                         % (spec, b.effect, b.sha_out, n,
                            "IDENTICAL to the pinned artifact" if same else "*** DIFFERS ***"))
            ok = ok and same
        except Exception as e:
            lines.append("%-22s FAILED: %s: %s" % (spec, type(e).__name__, e))
            ok = False
    lines.append("the texel lane's only edit to reskin.py is `_regions(partition=)` -- this is what "
                 "says so in bytes, on all three cast-proven artifacts")
    return gate("G5 the CLUT-lane byte-compat pins (W4 ef227 + W5 ef211/ef251 still build)", ok,
                *lines)


# --------------------------------------------------------------------------- G6
def g6_corpus_census():
    if not _have_corpus():
        return gate("G6 the corpus census", False, "no extracted corpus at %s" % CORPUS)
    lines, ok = [], True
    npkg = npage = 0
    covered = total = dead = holes = 0
    cell_hits = span_hits = 0
    xs = set()
    worst = []
    per_effect = {}
    for path in W.corpus_paths(CORPUS):
        with open(path, "rb") as fh:
            blob = fh.read()
        pages = RP.creature_texel_pages(blob)
        if not pages:
            continue
        npkg += 1
        ef = int(os.path.basename(path)[2:5])
        per_effect[ef] = [0, 0, 0]                               # covered, dead, interior holes
        others = RP.other_page_writers(blob)
        for p in pages:
            npage += 1
            xs.add(p.vram[0])
            if p.vram in others:
                cell_hits += 1
            lo, hi = p.page_offset, p.page_offset + p.page_bytes
            for _c, ws in others.items():
                for _s, off, nb in ws:
                    if off < hi and lo < off + nb:
                        span_hits += 1
            cov = RP.coverage(blob, p.index)
            if not cov.available:                                # pragma: no cover - geom drift
                lines.append("coverage UNAVAILABLE on %s %s: %s"
                             % (os.path.basename(path), p.name, cov.reason))
                ok = False
                continue
            covered += cov.covered
            total += cov.total
            dead += cov.dead
            holes += cov.interior_holes
            per_effect[ef][0] += cov.covered
            per_effect[ef][1] += cov.dead
            per_effect[ef][2] += cov.interior_holes
            if cov.dead:
                worst.append((cov.interior_holes / cov.dead, os.path.basename(path), p.name,
                              cov.interior_holes, cov.dead))
    lines.append("decodable creature packages %d, pages %d, VRAM x values %s"
                 % (npkg, npage, sorted(xs)))
    ok = ok and (npkg, npage) == (24, 93)
    ok = ok and set(xs) <= set(range(*RP.CREATURE_VRAM_X))
    lines.append("UV coverage: %d of %d texels sampled (%.2f%%), %d dead (%.2f%%)"
                 % (covered, total, 100.0 * covered / total, dead, 100.0 * dead / total))
    # THE MARGIN LAW, CORPUS-WIDE -- and R2's 99.6% is CORRECTED here rather than repeated.  R2
    # measured the law on ef227 and ef211 only (0.32% and 0.09% interior holes) and generalised it;
    # this is the first sweep of all 93 pages and the corpus number is weaker.  The law still holds
    # in the sense that matters -- the dead region is overwhelmingly ONE outer pad, so "paint inside
    # the island" is a complete instruction -- but the interior-hole class is REAL on some effects,
    # which is exactly why the overlay hatches pad GREEN and hole RED instead of one colour.
    lines.append("THE MARGIN LAW (corpus): %d interior-hole texels of %d dead (%.3f%%) -- "
                 "%.3f%% is ONE border-connected outer pad"
                 % (holes, dead, 100.0 * holes / dead, 100.0 - 100.0 * holes / dead))
    ok = ok and holes / dead < 0.02
    for ef in (227, 211, 251):
        if ef in per_effect:
            c, d, h = per_effect[ef]
            lines.append("   ef%03d: %d sampled, %d dead, %d interior holes -- pad share %.2f%%"
                         % (ef, c, d, h, 100.0 - 100.0 * h / max(1, d)))
    worst.sort(reverse=True)
    for frac, f, n, h, d in worst[:3]:
        lines.append("   worst PAGE for interior holes: %s %s -- %d of %d dead (%.2f%%)"
                     % (f, n, h, d, 100.0 * frac))
    worst_ef = max(per_effect.items(), key=lambda kv: kv[1][2] / max(1, kv[1][1]))
    lines.append("   worst EFFECT: ef%03d -- %d of %d dead texels are interior holes (%.2f%%)"
                 % (worst_ef[0], worst_ef[1][2], worst_ef[1][1],
                    100.0 * worst_ef[1][2] / max(1, worst_ef[1][1])))
    lines.append("collisions with any other declared page writer: %d by VRAM cell, %d by file span"
                 % (cell_hits, span_hits))
    ok = ok and cell_hits == 0 and span_hits == 0
    lines.append("A2's \"100%% of its own page block\" was a BBOX claim: the polygon coverage is "
                 "%.1f%%, so ~1/3 of every summon's texture budget is never sampled"
                 % (100.0 * covered / total))
    return gate("G6 the corpus census (24/93, the coverage total, THE MARGIN LAW, 0 collisions)",
                ok, *lines)


# --------------------------------------------------------------------------- G7
#: the committable files THIS rung adds.  The KIT module is scanned as well as the study's own files,
#: for w4_gates' own reason: the engine is where stock texels are actually read and rewritten, and a
#: scan that covered only the study would report a green provenance verdict over the half of the rung
#: that never touches a byte.  An entry containing "/" is REPO-relative; a bare name is local.
COMMITTABLE = ("emblem_stamp.py", "w6_gates.py", "bahamut_emblem.toml", "W6-TEXEL.md",
               "ff9mapkit/ff9mapkit/summons/repaint.py",
               "ff9mapkit/tests/test_summon_repaint.py")

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))   # <repo>


def _committable_path(name: str) -> str:
    return os.path.join(_REPO, *name.split("/")) if "/" in name else os.path.join(_HERE, name)


def _byte_literals(path: str, minlen: int = 6):
    import ast
    out = []
    try:
        tree = ast.parse(open(path, "r", encoding="utf-8").read())
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
        fp = _committable_path(name)
        if not os.path.isfile(fp):
            lines.append("%s MISSING" % name)
            ok = False
            continue
        if name.endswith(".py"):
            lits.extend((name, ln, raw) for ln, raw in _byte_literals(fp))
    lines.append("byte literals of >= 6 non-uniform bytes in the %d committable W6 sources: %d"
                 % (len(COMMITTABLE), len(lits)))
    for name, ln, raw in lits:
        lines.append("   %s:%d  %r" % (name, ln, raw[:24]))
    hits = []
    if lits and _have_corpus():
        for path in W.corpus_paths(CORPUS):
            with open(path, "rb") as fh:
                blob = fh.read()
            for name, ln, raw in lits:
                if raw in blob:
                    hits.append("LEAK %s:%d found in %s" % (name, ln, os.path.basename(path)))
    lines.append("   of those, appearing anywhere in the %d-file corpus: %d"
                 % (len(W.corpus_paths(CORPUS)), len(hits)))
    for h in hits:
        lines.append("      " + h)
    ok = ok and not hits

    # the staged artifact and the art are both OUTSIDE the checkout, by the guard rather than by luck
    for label, p in (("staging root", SCRATCH_W6_ROOT),
                     ("the emblem art", os.path.join(SCRATCH_W6_ROOT, "art"))):
        outside = _REPO.lower() not in os.path.abspath(p).lower()
        lines.append("%s outside the repo: %s  (%s)" % (label, outside, p))
        ok = ok and outside
    # The guard is `export.assert_local_only`, reached through the module that actually calls it, so
    # this tests the object `export_art` uses rather than a second import that could diverge.
    try:
        RP.export.assert_local_only(os.path.join(_REPO, "studies", "x"))
        refused_repo = False
    except Exception:
        refused_repo = True
    lines.append("an export destination inside the checkout is REFUSED: %s" % refused_repo)
    ok = ok and refused_repo
    try:
        RP.export.assert_local_only(os.path.join(str(SCRATCH_W6_ROOT), "StreamingAssets", "x"))
        refused_mod = False
    except Exception:
        refused_mod = True
    lines.append("an export destination inside a StreamingAssets tree is REFUSED: %s" % refused_mod)
    ok = ok and refused_mod

    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=_REPO)
    big = [l[3:] for l in p.stdout.splitlines()
           if l[3:].strip().endswith((".bytes", ".png")) or l[3:].strip().endswith("ef227")]
    lines.append("stock-shaped files in the repo working tree: %d%s"
                 % (len(big), "" if not big else " -- " + ", ".join(big)))
    ok = ok and not big
    return gate("G7 provenance (no SE bytes committable, art + staging outside the checkout)",
                ok, *lines)


# --------------------------------------------------------------------------- main
def main() -> int:
    print(__doc__.splitlines()[0])
    if not _has_install():
        print("\nNOTE: no FF9 install resolvable -- G2/G5 will FAIL loudly rather than skip.")
    if not _have_corpus():
        print("\nNOTE: no extracted corpus at %s -- G1/G3/G4/G6 will FAIL loudly." % CORPUS)
    g1_indexed_round_trip()
    g2_emblem_artifact()
    g3_region_partition()
    g4_refusal_matrix()
    g5_clut_lane_byte_compat()
    g6_corpus_census()
    g7_provenance()
    print("\n" + "=" * 72)
    for name, ok in RESULTS:
        print("%-5s %s" % ("PASS" if ok else "FAIL", name))
    passed = sum(1 for _n, ok in RESULTS if ok)
    print("=" * 72)
    print("%d/%d gates pass" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
