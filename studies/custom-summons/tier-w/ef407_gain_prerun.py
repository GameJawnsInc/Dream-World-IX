r"""TIER W -- THE GAIN-HALF CAST, RUN OFFLINE FIRST.  ef407, ``cell.s0.x704_y256``.

    py ef407_gain_prerun.py                    # stamp both marks, build, render stock + both, report
    py ef407_gain_prerun.py --frames 70-215    # the drawn window (default: every frame of the reads)
    py ef407_gain_prerun.py --variants ink     # one mark only

THE QUESTION
------------
The U2 adoption (``linear-add-v1``) licenses ``cell.s0.x704_y256`` on ef407 although no reader is BOUND
there: one record's second array displaces it onto column 704, and op 144 copies (704,256) into
(704,384) every frame it runs.  ``tier-w/PLAN.md`` names this cell as the owner cast that closes the
gain half's silent-failure mode, with a three-way reading:

    a mark that SCROLLS vertically   the readers on the blitted band (704,384) -- the gain half working
    a STATIC mark only               the one reader arriving on (704,256) itself
    nothing at all                   refutes the derivation on this container

``headless/raster.py`` reproduces the in-game command buffer exactly (``rx_gates`` RX2), and the
texture coordinates it samples with are the ones the user's own plugin computes, including the
displacement.  So the cast can be run here first: if the mark never reaches the screen offline there
is no cast to ask for, and if it does, the owner gets a pictured prediction instead of a guess.

WHAT THIS RUNS
--------------
For each mark variant (``ink`` = the brightest live entry of the cell's palette, ``dark`` = the
darkest; the readers blend ADDITIVELY, so one adds and the other fails to add):

1. stamp four horizontal bars, 8 rows each at a 32-row pitch, full width, into the cell's INDEX bytes
   (horizontal, because the op-144 band is a vertical roll: a horizontal bar crawls under it, a
   vertical stripe would come out pixel-identical);
2. build through the kit's own ``repaint.build`` and ``self_check`` -- the cast path, not a shortcut;
3. render stock and the build in separate processes (the plugin is process-global) with
   ``raster.run(watch=...)``, which maps each frame's screen pixels to the cells their fragments read;
4. charge every changed pixel to (704,384), to (704,256), or to neither -- NEITHER must be zero, or
   the attribution is wrong and the verdict is void -- and replay the frame's ``DR_MOVE`` commands on
   a row-label copy of column 704 to say where the bars sit inside (704,384) on each frame.

Everything it writes goes to ``C:\gd\SCRATCH\summon-format\headless\raster\ef407-gain`` (the stamped
page is decoded Square-Enix art; the frames are rendered from it).  Nothing is deployed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import reskin as RS                                              # noqa: E402,F401  (sets up sys.path)
from ff9mapkit.summons import repaint as RP                      # noqa: E402

_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
assert os.path.normcase(os.path.abspath(RP.__file__)).startswith(
    os.path.normcase(os.path.join(_REPO, "ff9mapkit"))), RP.__file__

HEADLESS = os.path.normpath(os.path.join(_HERE, "..", "headless"))
sys.path.insert(0, HEADLESS)
import sfx_host as H                                             # noqa: E402

EF = 407
CELL = "cell.s0.x704_y256"
UPPER, LOWER = "x704_y256@8", "x704_y384@8"
CORPUS_FILE = Path(r"C:\gd\SCRATCH\summon-format") / ("ef%03d.bytes" % EF)
OUT = H.OUT_DIR / "raster" / "ef407-gain"
DEFAULT_FRAMES = "70-215"                       # the reads run f71-192, the op-144 blits f85-211
BAR_ROWS = tuple(r for r in range(128) if r % 32 < 8)
VARIANTS = ("ink", "dark")
#: THE STATIC-SURFACE WINDOW: the ice spire's shaft (screen x 150-175, y 0-129) over f92-105, chosen by
#: eye from the stock frames and then CHECKED by the run itself -- the (704,384) footprint inside it must
#: hold still (IoU near 1) while the mark moves, or "it scrolls" is geometry motion and proves nothing.
STRIP = (slice(0, 130), slice(150, 176))
STRIP_FRAMES = range(92, 106)
STRONG = (85, 125)                              # the window the mark reads in (measured, see the report)


def _lum(word: int) -> float:
    r, g, b = (word & 31) * 255 / 31, (word >> 5 & 31) * 255 / 31, (word >> 10 & 31) * 255 / 31
    return 0.299 * r + 0.587 * g + 0.114 * b


# ============================================================ 1-2: stamp and build
def stamp(blob: bytes, variant: str) -> dict:
    page = next(p for p in RP.scenery_texel_pages(blob, EF) if p.name == CELL)
    assert (page.bpp, page.w, page.h, page.page_bytes) == (8, 128, 128, 16384), page
    raw = bytearray(blob[page.page_offset:page.page_offset + page.page_bytes])
    words = RP.palette_words(blob, page)
    zeros = set(RP.transparent_values(blob, page)[0])
    live = sorted(set(raw) - zeros)
    pick = max if variant == "ink" else min
    ink = pick(live, key=lambda i: (_lum(words[i]), -i if variant == "ink" else i))
    moved = 0
    for r in BAR_ROWS:
        for c in range(page.w):
            i = r * page.w + c
            if raw[i] in zeros:
                continue                                         # never cross the cutout boundary
            moved += raw[i] != ink
            raw[i] = ink
    d = OUT / variant
    d.mkdir(parents=True, exist_ok=True)
    png = str(H._refuse_repo_path(d / ("%s.png" % CELL)))
    RP.write_indexed_png(bytes(raw), words, page.w, page.h, png)
    spec = {"reskin": {"effect": EF, "label": "ef407-gain-prerun-%s" % variant,
                       "expect_sha256": hashlib.sha256(blob).hexdigest(),
                       "texel": [{"name": CELL, "source": png, "expect_cell": list(page.cell)}]}}
    b = RP.build(spec, str(d / "spec"), blob=blob)
    b.check = RP.self_check(b)
    cont = H._refuse_repo_path(d / ("ef%03d.bytes" % EF))
    cont.write_bytes(b.patched)
    changed = sum(1 for i in range(len(blob)) if blob[i] != b.patched[i])
    toml = "\n".join([
        "# ef407 gain-half cast, %s bars -- written by ef407_gain_prerun.py (SCRATCH art)" % variant,
        "[reskin]", "effect = %d" % EF, 'label = "ef407-gain-%s"' % variant,
        'expect_sha256 = "%s"' % hashlib.sha256(blob).hexdigest(), "",
        "[[reskin.texel]]", 'name = "%s"' % CELL, 'source = "%s"' % png.replace("\\", "/"),
        "expect_cell = [%d, %d]" % page.cell, ""])
    (d / ("ef407_gain_%s.toml" % variant)).write_text(toml, encoding="utf-8")
    return {"variant": variant, "ink": ink, "ink_rgb15": words[ink], "ink_luminance": round(_lum(words[ink]), 1),
            "texels_set": moved, "container_bytes_changed": changed,
            "self_check": "%d/%d" % (sum(1 for g in b.check.gates if g.ok), len(b.check.gates)),
            "self_check_ok": bool(b.check.ok), "hazard_notes": list(b.enabled[0].hazard_notes),
            "container": str(cont), "patched_sha256": hashlib.sha256(b.patched).hexdigest()}


# ============================================================ 3: one render, in its own process
def child(container: str, out: str, frames_spec: str) -> int:
    import numpy as np
    import raster as R
    blob, source, _ = H.load_container(EF, None if container == "stock" else container, False, None)
    bdir, sha = H.resolve_bin(None, None)
    frames = R.parse_frames(frames_spec)
    order = sorted(frames)
    screens, up, lo, moves = {}, {}, {}, {}

    def on_frame(f, screen, cmds, stats):
        mv = [list(c.args) for c in cmds if c.kind == "move"]
        if mv:
            moves[f] = mv
        if screen is not None:
            screens[f] = np.round(np.clip(screen.color, 0, 1) * 255).astype(np.uint8)
            up[f] = stats.watch_masks[UPPER].copy()
            lo[f] = stats.watch_masks[LOWER].copy()

    res = R.run(bdir, blob, EF, frames=frames, on_frame=on_frame, watch=(UPPER, LOWER))
    drawn = [f for f in order if f in screens]
    o = H._refuse_repo_path(Path(out))
    o.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(o / "frames.npz", frames=np.array(drawn),
                        screen=np.stack([screens[f] for f in drawn]),
                        upper=np.stack([up[f] for f in drawn]), lower=np.stack([lo[f] for f in drawn]))
    (o / "moves.json").write_text(json.dumps({str(k): v for k, v in moves.items()}), encoding="utf-8")
    (o / "run.json").write_text(json.dumps({"source": source, "plugin_sha256": sha, "frames": res["frames"],
                                            "faults": res["faults"], "drawn": drawn}), encoding="utf-8")
    return 0


# ============================================================ 4: the roll, replayed on row labels
def roll_phases(moves: dict) -> dict:
    """Replay every ``DR_MOVE`` that touches column 704 on a 256-row label array (VRAM y 256..511).
    Returns frame -> the upper-cell row now sitting at (704,384) row 0, plus any move that does not
    fit the model (another width, another column) -- a non-empty ``foreign`` voids the replay."""
    lab = list(range(256))
    phase, foreign = {}, []
    for f in sorted(moves, key=int):
        for rx, ry, rw, rh, x, y in moves[f]:
            if not (x < 768 and x + rw > 704 and y + rh > 256):
                continue
            if (rx, x, rw) != (704, 704, 64) or ry < 256 or y < 256 or ry + rh > 512 or y + rh > 512:
                foreign.append([int(f), rx, ry, rw, rh, x, y])
                continue
            src = lab[ry - 256:ry - 256 + rh]
            lab[y - 256:y - 256 + rh] = src
        phase[int(f)] = lab[128:256]
    return {"rows": phase, "foreign": foreign}


def analyse(variant: str, info: dict) -> dict:
    import numpy as np
    S = np.load(OUT / "stock" / "frames.npz")
    P = np.load(OUT / variant / "render" / "frames.npz")
    assert list(S["frames"]) == list(P["frames"])
    fr = [int(f) for f in P["frames"]]
    moves = json.loads((OUT / variant / "render" / "moves.json").read_text(encoding="utf-8"))
    roll = roll_phases(moves)
    rows = {}
    prev = None
    for k, f in enumerate(fr):
        d = np.abs(S["screen"][k].astype(np.int16) - P["screen"][k].astype(np.int16)).max(axis=-1)
        D = d > 1
        # both runs' footprints: a dark mark that adds nothing leaves no "changed" fragment in the paint
        U, L = P["upper"][k] | S["upper"][k], P["lower"][k] | S["lower"][k]
        lab = roll["rows"].get(f)
        in_lower = sorted({r for r in range(128) if lab and lab[r] < 128 and lab[r] in BAR_ROWS}) if lab else []
        row = {"changed": int(D.sum()), "lower_only": int((D & L & ~U).sum()), "both": int((D & L & U).sum()),
               "upper_only": int((D & U & ~L).sum()), "neither": int((D & ~U & ~L).sum()), "max_diff": int(d.max()),
               "mean_diff": round(float(d[D].mean()), 1) if D.any() else 0.0,
               "lower_footprint": int(L.sum()), "upper_footprint": int(U.sum()),
               "bar_rows_in_lower": len(in_lower),
               "phase": (lab[0] if lab else None)}
        DL = D & L
        if prev is not None and prev.any() and DL.any():
            best = max(range(-12, 13), key=lambda dy: int((np.roll(prev, dy, axis=0) & DL).sum()))
            row["screen_dy"] = best
            row["overlap_dy0"] = int((prev & DL).sum())
            row["overlap_best"] = int((np.roll(prev, best, axis=0) & DL).sum())
        prev = DL
        rows[f] = row
    # the scroll, on a surface that holds still
    strip = {}
    for f in STRIP_FRAMES:
        if f - 1 not in fr or f not in fr:
            continue
        a, b = fr.index(f - 1), fr.index(f)
        La = (S["lower"][a] | P["lower"][a])[STRIP]
        Lb = (S["lower"][b] | P["lower"][b])[STRIP]
        da = (np.abs(S["screen"][a].astype(np.int16) - P["screen"][a].astype(np.int16)).max(-1) > 20)[STRIP]
        db = (np.abs(S["screen"][b].astype(np.int16) - P["screen"][b].astype(np.int16)).max(-1) > 20)[STRIP]
        best = max(range(-15, 16), key=lambda dy: int((np.roll(da, dy, 0) & db).sum()))
        strip[f] = {"footprint_iou": round(float((La & Lb).sum() / max(1, (La | Lb).sum())), 3),
                    "mark_iou": round(float((da & db).sum() / max(1, (da | db).sum())), 3), "mark_dy": best}
    a, b = fr.index(STRONG[0]), fr.index(STRONG[1])
    d = np.abs(S["screen"][a:b + 1].astype(np.int16) - P["screen"][a:b + 1].astype(np.int16)).max(-1)
    n = d.shape[0]
    strength = {"over_16": round(float((d > 16).sum()) / n), "over_48": round(float((d > 48).sum()) / n),
                "over_96": round(float((d > 96).sum()) / n)}
    return {"variant": variant, "build": info, "frames": rows, "roll_foreign": roll["foreign"],
            "strip": strip, "strength_per_frame": strength}


def sheets(variant: str, picks) -> None:
    import numpy as np
    from PIL import Image
    S = np.load(OUT / "stock" / "frames.npz")
    P = np.load(OUT / variant / "render" / "frames.npz")
    fr = [int(f) for f in P["frames"]]
    ks = [fr.index(f) for f in picks if f in fr]
    h, w = P["screen"].shape[1:3]
    sheet = Image.new("RGB", (w * len(ks), h * 3))
    for j, k in enumerate(ks):
        d = np.abs(S["screen"][k].astype(np.int16) - P["screen"][k].astype(np.int16))
        sheet.paste(Image.fromarray(S["screen"][k]), (j * w, 0))
        sheet.paste(Image.fromarray(P["screen"][k]), (j * w, h))
        sheet.paste(Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8)), (j * w, 2 * h))
    sheet.save(H._refuse_repo_path(OUT / variant / ("sheet_%s.png" % "_".join(str(f) for f in picks))))
    frames = [Image.fromarray(np.concatenate([S["screen"][k], P["screen"][k]], axis=1)) for k in range(len(fr))]
    frames[0].save(H._refuse_repo_path(OUT / variant / "stock_vs_paint.gif"), save_all=True,
                   append_images=frames[1:], duration=33, loop=0)
    # the kymograph: the strip's mean difference per screen row (y) against frame (x) -- a scroll is a
    # family of parallel diagonals
    a, b = fr.index(82), fr.index(130)
    d = np.abs(S["screen"][a:b + 1].astype(np.int16) - P["screen"][a:b + 1].astype(np.int16)).max(-1)
    kymo = np.clip(d[:, STRIP[0], STRIP[1]].mean(axis=2).T * 3, 0, 255).astype(np.uint8)
    Image.fromarray(kymo).resize((kymo.shape[1] * 6, kymo.shape[0] * 3), Image.NEAREST).save(
        H._refuse_repo_path(OUT / variant / "kymograph_f82_130.png"))


# ============================================================ CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--frames", default=DEFAULT_FRAMES)
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--no-render", action="store_true", help="re-analyse the renders already in SCRATCH")
    ap.add_argument("--child", nargs=2, metavar=("CONTAINER", "OUT"), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.child:
        return child(a.child[0], a.child[1], a.frames)
    variants = [v for v in a.variants.split(",") if v]
    blob = CORPUS_FILE.read_bytes()
    builds = {v: stamp(blob, v) for v in variants}
    for v, b in builds.items():
        print("%-5s ink %3d (lum %5.1f)  %d texels set, %d container bytes, self-check %s" % (
            v, b["ink"], b["ink_luminance"], b["texels_set"], b["container_bytes_changed"], b["self_check"]))
        for n in b["hazard_notes"]:
            print("        %s" % n[:200])
    jobs = [("stock", str(OUT / "stock"))] + [(builds[v]["container"], str(OUT / v / "render")) for v in variants]
    procs = [] if a.no_render else [subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "--frames", a.frames, "--child", c, o],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=_HERE)
             for c, o in jobs]
    for (c, o), p in zip(jobs, procs):
        out, _ = p.communicate()
        if p.returncode:
            print("render %s failed:\n%s" % (c, out[-3000:]))
            return 1
    report = {"effect": EF, "cell": CELL, "bar_rows": BAR_ROWS, "frames": a.frames, "variants": {}}
    for v in variants:
        r = analyse(v, builds[v])
        report["variants"][v] = r
        fr = r["frames"]
        lit = [f for f, x in fr.items() if x["changed"]]
        print("\n%s: %d of %d drawn frames differ from stock (%s)" % (
            v, len(lit), len(fr), "%d-%d" % (min(lit), max(lit)) if lit else "none"))
        tot = {k: sum(x[k] for x in fr.values()) for k in ("changed", "lower_only", "both", "upper_only", "neither")}
        print("   changed px %(changed)d = via (704,384) only %(lower_only)d + both %(both)d"
              " + via (704,256) only %(upper_only)d + via neither %(neither)d" % tot)
        up = sorted(f for f, x in fr.items() if x["upper_only"] or x["both"])
        print("   the static reader on (704,256) shows on frames %s" % up)
        ph = [fr[f]["phase"] for f in range(85, 96)]
        print("   roll replay: %d foreign moves; (704,384) row 0 holds source row %s over f85-95"
              % (len(r["roll_foreign"]), ph))
        st = r["strip"]
        print("   spire f%d-%d: footprint IoU %.3f-%.3f, mark IoU %.3f-%.3f, mark shift %s px/frame" % (
            min(st), max(st), min(x["footprint_iou"] for x in st.values()), max(x["footprint_iou"] for x in st.values()),
            min(x["mark_iou"] for x in st.values()), max(x["mark_iou"] for x in st.values()),
            [x["mark_dy"] for x in st.values()]))
        print("   strength f%d-%d, px per frame off by >16/>48/>96 levels: %s" % (
            STRONG[0], STRONG[1], "/".join(str(v_) for v_ in r["strength_per_frame"].values())))
        sheets(v, [76, 90, 91, 92, 93, 120, 150])
    (OUT / "report.json").write_text(json.dumps(report, indent=1, default=list), encoding="utf-8")
    print("\n-> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
