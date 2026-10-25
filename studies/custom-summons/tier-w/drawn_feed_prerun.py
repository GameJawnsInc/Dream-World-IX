r"""CHANNEL D, RUN OFFLINE -- does a repaint of a cell the render target is DRAWN from reach the screen?

    py drawn_feed_prerun.py                 # ef150 cell.s0.x448_y256: stamp, build, diff headless
    py drawn_feed_prerun.py --ef 203 --cell cell.s0.x448_y256
    py drawn_feed_prerun.py --noop          # the falsifier: the unedited art moves nothing
    py drawn_feed_prerun.py --screen --ef N --cell C    # THE SCREEN HALF: a cell only the screen reads
    py drawn_feed_prerun.py --conflict --ef 179 --cell cell.s0.x704_y384   # THE CONFLICT GATE'S PREMISE
    py drawn_feed_prerun.py --screen --ef 406 --cell cell.s0.x448_y384 --art DIR   # stamp a cast's art

THE QUESTION
------------
Every 15bpp read in a target-rendering effect samples the render target, never VRAM, so a ``direct15``
repaint there shows nothing (``render_target.py``).  The remedy names what the target is DRAWN from --
and most of those cells are ones no ``so`` record gives a depth to, so until CHANNEL D the remedy named
nothing paintable.  Channel D hands such a cell out at the depth the target's draw reads it at, behind
``acknowledge_drawn_depth``.  This runs the claim the remedy makes: paint the feeder, and the target --
and through it the screen -- changes.

WHAT THIS RUNS
--------------
1. ``export_art(drawn_depth=True)`` hands out the feeder's PNG in the draw's own key;
2. ZEBRA: every OPAQUE texel of the cell is set to the key's brightest or darkest opaque entry in
   16-row bands (transparent texels are left alone, so the cutout law has nothing to say);
3. ``repaint.build`` with ``acknowledge_drawn_depth = true`` + ``expect_bpp`` -- the cast path;
4. ``raster.py diff`` renders stock and the build in separate processes over the frames the census saw
   the feeder drawn on, and the run's own books say where the change came from: the feeder's fragments
   INTO THE TARGET (``render_target_cells``) and straight TO THE SCREEN (``visible_cells``).

The verdict is ``REACHES`` when screen frames change and the feeder drew the target on both sides with
no direct screen read of it -- the change can then only have travelled through the target.

``--screen`` runs the same claim for the draw census's other half: a cell no `so` record gives a depth
and no draw into the target reads, that the screen's own draws read at one depth.  Its frames are the
ones the draw census saw it read on, and the verdict it wants is ``DIRECT``: screen frames change and
the cell's own fragments drew the screen on both sides.

``--conflict`` runs THE DRAWN-CONFLICT GATE's premise on an 8bpp page every draw reads at 4bpp only:
an edit painted at the page's own depth reaches the screen as a SECOND picture, its indices repacked
as nibbles.  The mark is built so the two readings disagree on sight -- PARITY ZEBRA: 16-row bands of
two bytes that are each other's nibbles swapped (``a = hl``, ``b = lh``).  At 8bpp they are two
different palette entries (the export PNG shows bands); at 4bpp they are the same two texels in the
other order, so the bands vanish into one uniform comb.  Four renders measure it on the effect's own
geometry, at BAND scale (a 5-pixel box: pixel for pixel the two inks are complementary combs):
``a`` on every opaque texel against ``b`` on every opaque texel must be nearly the same picture
(``parity_residual``), while the plain zebra's two inks must not (``plain_residual``, the control that
proves the residual can fail).  The verdict it wants is ``SECOND-PICTURE``: screen frames change, only
through reads at the other depth, and the parity residual under a quarter of the plain one.  What the
eye gets is a fine VERTICAL HATCH -- each byte drawn as a lit and a clear texel -- where an 8bpp read
would draw plain horizontal bands.

``--art DIR`` stamps the cast mark (zebra; parity zebra with ``--conflict``) into an ``export-art``
directory's own PNG for the cast spec to read, and stops.

Everything it writes goes to ``C:\gd\SCRATCH\summon-format\headless\raster\drawn-<ef>`` (decoded and
repainted Square-Enix art, and frames rendered from it).  Nothing is deployed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS_STUDY                                        # noqa: E402,F401  (sets up sys.path)
from ff9mapkit.summons import render_target as RT                # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402
from ff9mapkit.summons import reskin as RSK                      # noqa: E402

_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
assert os.path.normcase(os.path.abspath(RP.__file__)).startswith(
    os.path.normcase(os.path.join(_REPO, "ff9mapkit"))), RP.__file__

CORPUS = r"C:\gd\SCRATCH\summon-format"
RASTER = os.path.join(_REPO, "studies", "custom-summons", "headless", "raster.py")


def _lum(word: int) -> float:
    return 0.299 * (word & 31) + 0.587 * ((word >> 5) & 31) + 0.114 * ((word >> 10) & 31)


def zebra(blob: bytes, page) -> bytes:
    """The page's index bytes with every OPAQUE texel banded brightest / darkest, 16 rows a band."""
    words = RP.palette_words(blob, page)
    zeros, _why = RP.transparent_values(blob, page)
    live = [i for i, w in enumerate(words) if i not in zeros and w]
    hi, lo = max(live, key=lambda i: _lum(words[i])), min(live, key=lambda i: _lum(words[i]))
    raw = blob[page.page_offset:page.page_offset + page.page_bytes]
    vals = list(RP.texel_view(page, raw))
    out = [v if v in zeros else (hi if (i // page.w) // 16 % 2 == 0 else lo) for i, v in enumerate(vals)]
    return RP.pack4(out) if page.bpp == 4 else bytes(out)


# --------------------------------------------------------------------------- the conflict half
def other_clut(blob: bytes, ef: int, page) -> Tuple[Tuple[int, int], Tuple[int, ...]]:
    """The CLUT the draws read an 8bpp page's bytes through at 4bpp, and its 16 words.

    Channel D's lowest-addressed CLUT (the class-C display rule), found among the container's own
    palette records -- a CLUT the container does not upload is no prediction this run can make.
    """
    dd = RT.drawn_depth(ef, page.cell, page.page_offset)
    assert dd is not None and set(dd.depths) == {4} and page.bpp == 8, (
        "the parity mark is built for an 8bpp page read at 4bpp only", page.name, dd and dd.depths)
    clut = dd.clut_cells[0]
    pals = [q for q in RSK.palette_map(blob, ef).palettes if q.vram == clut and q.entries == 16]
    assert len(pals) == 1, ("no single 16-entry palette record at the draw's CLUT", clut, pals)
    return clut, struct.unpack_from("<16H", blob, pals[0].off)


def parity_pair(blob: bytes, ef: int, page) -> Tuple[int, int]:
    """Two bytes ``a = hl`` and ``b = lh``: far apart in the page's own 8bpp palette, and one picture at 4bpp.

    Scored as the 8bpp luminance gap times the brighter nibble's 4bpp luminance (a pair the 4bpp read
    shows as nothing would test nothing); both bytes must be opaque at 8bpp, or the export's own
    picture would carry a cutout the 4bpp read does not.
    """
    w8 = RP.palette_words(blob, page)
    zeros8, _why = RP.transparent_values(blob, page)
    _clut, w4 = other_clut(blob, ef, page)
    best, pair = -1.0, None
    for h in range(16):
        for lo in range(h):
            a, b = (h << 4) | lo, (lo << 4) | h
            if a in zeros8 or b in zeros8 or not w8[a] or not w8[b]:
                continue
            score = abs(_lum(w8[a]) - _lum(w8[b])) * max(_lum(w4[h]) if w4[h] else 0.0,
                                                        _lum(w4[lo]) if w4[lo] else 0.0)
            if score > best:
                best, pair = score, (a, b)
    assert pair is not None, "no opaque nibble-swapped pair in this page's palette"
    return pair


def paint8(blob: bytes, page, even: Optional[int], odd: Optional[int]) -> bytes:
    """The page's 8bpp bytes with every OPAQUE texel set to ``even`` / ``odd`` in alternate 16-row bands
    (``None`` leaves that band stock)."""
    zeros, _why = RP.transparent_values(blob, page)
    raw = blob[page.page_offset:page.page_offset + page.page_bytes]
    out = bytearray(raw)
    for i, v in enumerate(raw):
        ink = even if (i // page.w) // 16 % 2 == 0 else odd
        if v not in zeros and ink is not None:
            out[i] = ink
    return bytes(out)


def _rgb(word: int) -> List[int]:
    return [(word & 31) * 8, ((word >> 5) & 31) * 8, ((word >> 10) & 31) * 8]


def _build(blob: bytes, ef: int, page, raw: bytes, art: Path, tag: str, row_keys: dict) -> Tuple[object, Path]:
    """Write ``raw`` as the page's PNG and build it through the kit -- the cast path, not a shortcut."""
    words = RP.palette_words(blob, page)
    png = art / ("%s.%s.png" % (page.name, tag))
    if page.bpp == 4:
        RP.write_indexed4_png(raw, words, page.w, page.h, png)
    else:
        RP.write_indexed_png(raw, words, page.w, page.h, png)
    spec = {"reskin": {"effect": ef, "label": "drawn-prerun-%s" % tag,
                       "expect_sha256": hashlib.sha256(blob).hexdigest(),
                       "texel": [dict({"name": page.name, "source": str(png), "expect_bpp": page.bpp},
                                      **row_keys)]}}
    b = RP.build(spec, str(art / ("prerun.%s.toml" % tag)), blob=blob)
    b.check = RP.self_check(b)
    patched = art.parent / ("ef%03d.%s.bytes" % (ef, tag))
    patched.write_bytes(b.patched)
    return b, patched


def _render(ef: int, container: Optional[Path], frames: str, dest: Path) -> subprocess.Popen:
    cmd = [sys.executable, "-I", RASTER, "run", "--ef", str(ef), "--frames", frames, "--out", str(dest)]
    if container is not None:
        cmd += ["--container", str(container)]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            cwd=os.path.dirname(RASTER))


def _frames_of(d: Path) -> Dict[int, "object"]:
    import numpy as np
    from PIL import Image
    return {int(p.stem[1:]): np.asarray(Image.open(p).convert("RGB"), np.int16) for p in sorted(d.glob("f*.png"))}


#: the band scale: a box this many screen pixels wide averages away the comb a 4bpp read makes of each byte
#: (one texel lit, one clear) but not a 16-row band.  Pixel for pixel the two parity inks are COMPLEMENTARY
#: combs, so an unblurred residual calls them as different as the plain zebra's inks (measured: 1.32 vs 1.84
#: on ef226) although no eye sees a band.
BAND_BOX = 5


def _box(a, k: int):
    import numpy as np
    c = np.cumsum(np.cumsum(np.pad(a, ((k, 0), (k, 0))), 0), 1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def run_conflict(ef: int, cell: str, out: Path, reuse: bool = False) -> dict:
    """THE DRAWN-CONFLICT GATE'S PREMISE, offline: see the module docstring (``--conflict``).

    ``reuse`` keeps renders already on disk (each one is a full process over the page's frames); the
    builds always run, so a changed kit still changes the report.
    """
    import numpy as np
    blob = (Path(CORPUS) / ("ef%03d.bytes" % ef)).read_bytes()
    if out.exists() and not reuse:
        shutil.rmtree(out)
    art = out / "art"
    if art.exists():
        shutil.rmtree(art)
    RP.export_art(blob, ef, art, overlays=False, scaffold=True)
    page = RP.texel_page(blob, cell, ef)
    assert RP.drawn_conflict(page), (cell, "the drawn-conflict gate does not fire on this page")
    other = RT.drawn_depth(ef, page.cell, page.page_offset)
    clut, w4 = other_clut(blob, ef, page)
    a, b = parity_pair(blob, ef, page)
    w8 = RP.palette_words(blob, page)
    zeros8, _why = RP.transparent_values(blob, page)
    live = [i for i, w in enumerate(w8) if w and i not in zeros8]
    hi, lo = max(live, key=lambda i: _lum(w8[i])), min(live, key=lambda i: _lum(w8[i]))
    # the cast mark, its two inks apart, the plain zebra (what bands look like on this element), and the
    # plain zebra's two inks apart -- the control the parity residual is judged against
    marks = {"parity": (a, b), "a_all": (a, a), "b_all": (b, b),
             "plain": (hi, lo), "hi_all": (hi, hi), "lo_all": (lo, lo)}
    ack = {RT.DRAWN_CONFLICT_KEY: True}
    # the gate itself, first: the cast mark must refuse without the key
    try:
        _build(blob, ef, page, paint8(blob, page, a, b), art, "unacked", {})
        refused = ""
    except RP.RepaintError as e:
        refused = str(e)
    assert refused.startswith("DRAWN AT ANOTHER DEPTH"), refused or "built without the key"
    builds = {t: _build(blob, ef, page, paint8(blob, page, *m), art, t, ack) for t, m in marks.items()}
    stats = json.loads((Path(CORPUS) / "headless" / "raster" / "screen" / ("ef%03d" % ef)
                        / "summary.json").read_text(encoding="utf-8"))
    key_other = "x%d_y%d@4" % page.cell
    key_own = "x%d_y%d@8" % page.cell
    f0, f1 = stats["read_cells"][key_other]["frames"]
    spec = "%d-%d" % (f0, f1)
    tags = ["stock"] + list(builds)
    procs = {t: _render(ef, None if t == "stock" else builds[t][1], spec, out / t) for t in tags
             if not (reuse and (out / t / "summary.json").exists())}
    for t, p in procs.items():
        log, _ = p.communicate()
        if p.returncode != 0:
            raise SystemExit("render %s failed:\n%s" % (t, log[-3000:]))
    fr = {t: _frames_of(out / t) for t in tags}
    summ = {t: json.loads((out / t / "summary.json").read_text(encoding="utf-8")) for t in tags}
    lum = {t: {f: _box(v.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32), BAND_BOX)
               for f, v in fr[t].items()} for t in ("stock", "a_all", "b_all", "hi_all", "lo_all")}

    def absdiff(x, y, src):
        return sum(float(np.abs(src[x][f] - src[y][f]).sum()) for f in src[x] if f in src[y])

    def residual(x, y, src):
        """How different two one-ink renders are, as a share of how much each moves the screen."""
        return absdiff(x, y, src) / max(1.0, (absdiff(x, "stock", src) + absdiff(y, "stock", src)) / 2)

    moved = {f: n for f, n in ((f, int((np.abs(fr["parity"][f] - fr["stock"][f]).max(-1) > 1).sum()))
                               for f in fr["parity"]) if n}
    vis = {t: {"other": summ[t]["visible_cells"].get(key_other, {}).get("pixels", 0),
               "own": summ[t]["visible_cells"].get(key_own, {}).get("pixels", 0)} for t in tags}
    par, ctl = residual("a_all", "b_all", lum), residual("hi_all", "lo_all", lum)
    par_px, ctl_px = residual("a_all", "b_all", fr), residual("hi_all", "lo_all", fr)
    sheet = _sheet(fr, ("stock", "parity", "plain"), moved, out / "sheet.png")
    verdict = ("SECOND-PICTURE" if moved and vis["parity"]["other"] and not any(v["own"] for v in vis.values())
               and par < 0.25 * ctl else "NOTHING" if not moved else "UNDECIDED")
    rep = {"effect": ef, "cell": cell, "half": "conflict", "bpp": page.bpp, "depth_source": page.depth_source,
           "palette": page.palette_name, "drawn": other.evidence(),
           "draw_clut": "x%d_y%d" % clut,
           "mark": {"a": a, "b": b,
                    "at_8bpp": {"a": _rgb(w8[a]), "b": _rgb(w8[b])},
                    "at_4bpp": {"a": [_rgb(w4[a & 15]) if w4[a & 15] else "clear",
                                      _rgb(w4[a >> 4]) if w4[a >> 4] else "clear"],
                                "b": [_rgb(w4[b & 15]) if w4[b & 15] else "clear",
                                      _rgb(w4[b >> 4]) if w4[b >> 4] else "clear"]},
                    "plain": {"hi": hi, "lo": lo}},
           "refused_without_key": refused[:200],
           "build_sha256": {t: bb.sha_out for t, (bb, _p) in builds.items()},
           "self_check": {t: "%d/%d" % (sum(1 for g in bb.check.gates if g.ok), len(bb.check.gates))
                          for t, (bb, _p) in builds.items()},
           "frames": [f0, f1], "frames_drawn": len(fr["parity"]), "frames_changed": len(moved),
           "screen_px_changed": sum(moved.values()), "reads": vis,
           "band_box": BAND_BOX, "parity_residual": round(par, 4), "plain_residual": round(ctl, 4),
           "pixel_residuals": {"parity": round(par_px, 4), "plain": round(ctl_px, 4)},
           "sheet": str(sheet), "verdict": verdict}
    (out / "prerun.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def _sheet(fr: dict, rows: Sequence[str], moved: Dict[int, int], path: Path, n: int = 4) -> Path:
    """Stock / edits / amplified difference at the ``n`` frames the edit moves most, side by side."""
    import numpy as np
    from PIL import Image
    picks = sorted(sorted(moved, key=lambda f: -moved[f])[:n])
    h, w = fr[rows[0]][picks[0]].shape[:2]
    img = Image.new("RGB", (w * len(picks), h * (len(rows) + 1)))
    for j, f in enumerate(picks):
        for i, t in enumerate(rows):
            img.paste(Image.fromarray(fr[t][f].astype(np.uint8)), (j * w, i * h))
        d = np.clip(np.abs(fr[rows[1]][f] - fr[rows[0]][f]) * 4, 0, 255).astype(np.uint8)
        img.paste(Image.fromarray(d), (j * w, len(rows) * h))
    img.save(path)
    (path.parent / (path.stem + ".frames.txt")).write_text(
        "columns: frames %s\nrows: %s, then |%s - %s| x4\n" % (picks, ", ".join(rows), rows[1], rows[0]),
        encoding="utf-8")
    return path


def stamp_art(blob: bytes, ef: int, cell: str, art_dir: str, conflict: bool) -> dict:
    """THE CAST'S ART: overwrite an ``export-art`` directory's own PNG of ``cell`` with the cast mark.

    Refuses a PNG that is not the stock page (the export is the source of truth for the guards), so a
    stamp cannot land twice or on someone else's art.
    """
    if conflict:
        page = RP.texel_page(blob, cell, ef)
        a, b = parity_pair(blob, ef, page)
        raw = paint8(blob, page, a, b)
    else:
        page = RP.texel_page(blob, cell, ef, allow_drawn_depth=True)
        assert page.depth_source == "drawn", (cell, page.depth_source)
        raw = zebra(blob, page)
    png = Path(art_dir) / ("%s.png" % cell)
    stock = blob[page.page_offset:page.page_offset + page.page_bytes]
    read = (RP.read_indexed4_png(png, page.w, page.h) if page.bpp == 4
            else RP.read_indexed_png(png, page.w, page.h, 256))
    assert read == stock, "%s is not the stock page -- re-export first" % png
    words = RP.palette_words(blob, page)
    if page.bpp == 4:
        RP.write_indexed4_png(raw, words, page.w, page.h, png)
    else:
        RP.write_indexed_png(raw, words, page.w, page.h, png)
    return {"png": str(png), "sha256": hashlib.sha256(png.read_bytes()).hexdigest(), "bpp": page.bpp,
            "page_offset": hex(page.page_offset)}


def run(ef: int, cell: str, out: Path, noop: bool = False, screen: bool = False) -> dict:
    blob = (Path(CORPUS) / ("ef%03d.bytes" % ef)).read_bytes()
    if out.exists():
        shutil.rmtree(out)
    art = out / "art"
    RP.export_art(blob, ef, art, overlays=False, scaffold=True, drawn_depth=True)
    page = RP.texel_page(blob, cell, ef, allow_drawn_depth=True)
    assert page.depth_source == "drawn", (cell, page.depth_source)
    png = art / ("%s.png" % cell)
    raw = (blob[page.page_offset:page.page_offset + page.page_bytes] if noop else zebra(blob, page))
    words = RP.palette_words(blob, page)
    if page.bpp == 4:
        RP.write_indexed4_png(raw, words, page.w, page.h, png)
    else:
        RP.write_indexed_png(raw, words, page.w, page.h, png)
    spec = {"reskin": {"effect": ef, "label": "drawn-feed-prerun",
                       "expect_sha256": hashlib.sha256(blob).hexdigest(),
                       "texel": [{"name": cell, "source": str(png), "expect_bpp": page.bpp,
                                  RT.DRAWN_ACK_KEY: True}]}}
    b = RP.build(spec, str(art / "prerun.toml"), blob=blob)
    b.check = RP.self_check(b)
    patched = out / ("ef%03d.patched.bytes" % ef)
    patched.write_bytes(b.patched)
    census = "screen" if screen else "feeds"
    stats = json.loads((Path(CORPUS) / "headless" / "raster" / census / ("ef%03d" % ef)
                        / "summary.json").read_text(encoding="utf-8"))
    book = "read_cells" if screen else "render_target_cells"
    f0, f1 = stats[book]["x%d_y%d@%d" % (page.cell + (page.bpp,))]["frames"]
    cp = subprocess.run([sys.executable, "-I", RASTER, "diff", "--ef", str(ef), "--b", str(patched),
                         "--frames", "%d-%d" % (f0, f1), "--out", str(out / "diff")],
                        capture_output=True, text=True, cwd=os.path.dirname(RASTER))
    if cp.returncode != 0:
        raise SystemExit(cp.stdout[-2000:] + cp.stderr[-2000:])
    d = json.loads((out / "diff" / "diff.json").read_text(encoding="utf-8"))
    sides = {t: json.loads((out / "diff" / t / "summary.json").read_text(encoding="utf-8")) for t in "ab"}
    key = "x%d_y%d@%d" % (page.cell + (page.bpp,))
    tgt = {t: sides[t]["render_target_cells"].get(key, {}).get("pixels", 0) for t in "ab"}
    scr = {t: sides[t]["visible_cells"].get(key, {}).get("pixels", 0) for t in "ab"}
    changed = {f: r["changed_px"] for f, r in d["frames"].items() if r["changed_px"]}
    verdict = ("REACHES" if changed and tgt["a"] and tgt["b"] and not scr["a"] and not scr["b"]
               else "DIRECT" if changed and (scr["a"] or scr["b"]) else "NOTHING")
    sheet = (_sheet({"stock": _frames_of(out / "diff" / "a"), "zebra": _frames_of(out / "diff" / "b")},
                    ("stock", "zebra"), {int(f): n for f, n in changed.items()}, out / "sheet.png")
             if changed else None)
    rep = {"effect": ef, "cell": cell, "half": census, "bpp": page.bpp, "depth_source": page.depth_source,
           "palette": page.palette_name, "build_sha256": b.sha_out, "self_check": "%d/%d" % (
               sum(1 for g in b.check.gates if g.ok), len(b.check.gates)),
           "bytes_moved": len(b.check.changed), "frames": [f0, f1], "frames_drawn": len(d["frames"]),
           "frames_changed": len(changed), "screen_px_changed": sum(changed.values()),
           "feeder_into_target_px": tgt, "feeder_direct_to_screen_px": scr,
           "sheet": str(sheet) if sheet else None, "verdict": verdict}
    (out / "prerun.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ef", type=int, default=150)
    ap.add_argument("--cell", default="cell.s0.x448_y256")
    ap.add_argument("--noop", action="store_true",
                    help="THE FALSIFIER: build the UNEDITED art -- no byte may move and no frame differ")
    ap.add_argument("--screen", action="store_true",
                    help="the draw census's SCREEN half: frames from the screen census, verdict DIRECT")
    ap.add_argument("--conflict", action="store_true",
                    help="THE DRAWN-CONFLICT GATE's premise: parity zebra, verdict SECOND-PICTURE")
    ap.add_argument("--reuse", action="store_true",
                    help="with --conflict: keep the renders already on disk (the builds still run)")
    ap.add_argument("--art", metavar="DIR",
                    help="stamp the cast mark into this export-art directory's own PNG and stop")
    a = ap.parse_args(argv)
    if a.art:
        blob = (Path(CORPUS) / ("ef%03d.bytes" % a.ef)).read_bytes()
        print(json.dumps(stamp_art(blob, a.ef, a.cell, a.art, a.conflict), indent=1))
        return 0
    out = Path(CORPUS) / "headless" / "raster" / ("drawn-%03d%s%s" % (
        a.ef, "-conflict" if a.conflict else "-screen" if a.screen else "", "-noop" if a.noop else ""))
    if a.conflict:
        rep = run_conflict(a.ef, a.cell, out, reuse=a.reuse)
        print(json.dumps(rep, indent=1))
        return 0 if rep["verdict"] == "SECOND-PICTURE" else 1
    rep = run(a.ef, a.cell, out, noop=a.noop, screen=a.screen)
    print(json.dumps(rep, indent=1))
    return 0 if rep["verdict"] == ("NOTHING" if a.noop else "DIRECT" if a.screen else "REACHES") else 1


if __name__ == "__main__":
    raise SystemExit(main())
