r"""CHANNEL D, RUN OFFLINE -- does a repaint of a cell the render target is DRAWN from reach the screen?

    py drawn_feed_prerun.py                 # ef150 cell.s0.x448_y256: stamp, build, diff headless
    py drawn_feed_prerun.py --ef 203 --cell cell.s0.x448_y256
    py drawn_feed_prerun.py --noop          # the falsifier: the unedited art moves nothing
    py drawn_feed_prerun.py --screen --ef N --cell C    # THE SCREEN HALF: a cell only the screen reads

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

Everything it writes goes to ``C:\gd\SCRATCH\summon-format\headless\raster\drawn-<ef>`` (decoded and
repainted Square-Enix art, and frames rendered from it).  Nothing is deployed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS_STUDY                                        # noqa: E402,F401  (sets up sys.path)
from ff9mapkit.summons import render_target as RT                # noqa: E402
from ff9mapkit.summons import repaint as RP                      # noqa: E402

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
    rep = {"effect": ef, "cell": cell, "half": census, "bpp": page.bpp, "depth_source": page.depth_source,
           "palette": page.palette_name, "build_sha256": b.sha_out, "self_check": "%d/%d" % (
               sum(1 for g in b.check.gates if g.ok), len(b.check.gates)),
           "bytes_moved": len(b.check.changed), "frames": [f0, f1], "frames_drawn": len(d["frames"]),
           "frames_changed": len(changed), "screen_px_changed": sum(changed.values()),
           "feeder_into_target_px": tgt, "feeder_direct_to_screen_px": scr, "verdict": verdict}
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
    a = ap.parse_args(argv)
    out = Path(CORPUS) / "headless" / "raster" / ("drawn-%03d%s%s" % (
        a.ef, "-screen" if a.screen else "", "-noop" if a.noop else ""))
    rep = run(a.ef, a.cell, out, noop=a.noop, screen=a.screen)
    print(json.dumps(rep, indent=1))
    return 0 if rep["verdict"] == ("NOTHING" if a.noop else "DIRECT" if a.screen else "REACHES") else 1


if __name__ == "__main__":
    raise SystemExit(main())
