"""Rung C18: the game's world fog, measured from C7's nine in-game stills (no game run).

    py studies/overworld-editor/c18_fog_fit.py

For each still: C7's decoded camera (its best eye / aim heights inside the settle bands, c7_compare.json), drawn by
render.raster WITH its depth buffer, beside the game's own frame. Render.py draws no fog and no lighting, so:
  1. THE LIGHT: near the eye the fog is nil, so there the game's colour is the render's under the game's lighting --
     a per-channel affine map fitted on the near pixels (robustly);
  2. THE FOG COLOUR: the game's colour where the render's land lies farthest (the haze it fades into);
  3. THE FOG FRACTION per pixel: how far the game's colour has gone from the lit render toward the fog colour;
     binned by distance, both radial (eye to point) and view depth, over all nine stills.
Then a linear ramp (start, end) and a capped one are fitted to each binning; the better binning names the metric.
Writes out/c18_fog_fit.json (gitignored with the frames; the numbers go to evidence/c18).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (pins the worktree package)
import c7_compare as CC                                                # noqa: E402

GAME = C1.GAME
OUT = HERE / "out" / "c18_fog_fit.json"
SCALE = 4


def _mask(h, w):
    m = np.ones((h, w), dtype=bool)
    cy, cx = int(h * 0.56), w // 2                                      # the party
    m[cy - int(h * 0.14):cy + int(h * 0.10), cx - int(w * 0.045):cx + int(w * 0.045)] = False
    m[:int(h * 0.12), int(w * 0.55):] = False                           # the co-op banner, top right
    m[int(h * 0.90):, int(w * 0.93):] = False                           # the corner glyph
    return m


def main(capture=None, compare=None, tag="c18"):
    from ff9mapkit.world import gamecam as G
    from ff9mapkit.world import render as R
    cap = json.loads(Path(capture or CC.CAPTURE).read_text(encoding="utf-8"))
    cmp_rows = {(r["spot"], r["turn"]): r for r in json.loads(Path(compare or CC.COMPARE).read_text(encoding="utf-8"))["rows"]}
    rows = [r for r in cap["rows"] if "error" not in r and r.get("shot")]
    S = G.Settings.from_game(GAME)
    table = G.transport_table(GAME)
    stack = R.game_stack(GAME)
    names = [p.name for p in stack]
    gsite = R.RenderSite(cells=(), disc=1, game=GAME, stack=stack)
    pool = []                                                            # (radial, depth, y, f, game rgb, lit rgb)
    checks = []
    spot_of = []
    per = []
    cache = {}
    for row in rows:
        gi = CC._load(row["shot"])
        H, W = gi.shape[:2]
        w, h = W // SCALE, H // SCALE
        gs = CC._small(gi, w, h)
        x, y, z = row["x"], row["y"], row["z"]
        bx, by = int(x // 64), int(-z // 64)
        if (bx, by) not in cache:
            cells = tuple((cx, cy) for cx in range(bx - 4, bx + 5) for cy in range(max(0, by - 4), min(20, by + 5)))
            site = R.RenderSite(cells=cells, disc=1, game=GAME, stack=stack, res=(w, h))
            cache[(bx, by)] = (site, R.load_batches(site, stock=True))
        site, batches = cache[(bx, by)]
        gq = C1._ground(gsite, x, z, names)

        def ground(px, pz):
            g = C1._ground(gsite, px % 1536.0, pz, names)
            return g.get("y")
        best = cmp_rows.get((row["spot"], row["turn"]), {})
        v = G.pose((x, y, z), row["cam_rot"], settings=S, area=int(gq.get("area", 14) or 0),
                   upper_counter=row["cam_upper"] or 0, ground=ground, mode=int(row.get("ctl") or 0), table=table,
                   topograph=gq.get("topograph"), eye_dy=best.get("eye_dy", 0.0) or 0.0,
                   aim_dy=best.get("aim_dy", 0.0) or 0.0)
        v["reach"] = 600.0
        ri, dep = R.raster(v, batches, "c18", site=site, out_dir=None, verbose=False, want_depth=True)
        ri = ri.astype(np.float32)
        f_px = (h / 2.0) / math.tan(math.radians(v["fov"]) / 2.0)
        yy, xx = np.mgrid[0:h, 0:w]
        radial = dep * np.sqrt(1.0 + ((xx + 0.5 - w / 2.0) / f_px) ** 2 + ((yy + 0.5 - h / 2.0) / f_px) ** 2)
        eye = np.asarray(v["eye"])
        fwd = np.asarray(v["at"]) - eye
        fwd /= np.linalg.norm(fwd)
        right = np.cross([0.0, 1.0, 0.0], fwd)
        right /= np.linalg.norm(right)
        up = np.cross(fwd, right)
        ray = (fwd[None, None, :] + ((xx + 0.5 - w / 2.0) / f_px)[..., None] * right
               - ((yy + 0.5 - h / 2.0) / f_px)[..., None] * up)
        wy = eye[1] + dep * ray[..., 1]                                  # each pixel's world height
        land = np.isfinite(dep) & _mask(h, w)
        near = land & (radial < 22.0)
        if int(near.sum()) < 50:                                          # a high camera sees no near land: its
            near = land & (radial <= np.percentile(radial[land], 15))     # nearest seen 15% stands in for it
        A = np.c_[ri[near], np.ones(int(near.sum()))]
        coef = []
        for c in range(3):                                             # the light: game = a * render + b, trimmed
            yv = gs[near][:, c]
            sol = np.linalg.lstsq(A, yv, rcond=None)[0]
            res = np.abs(A @ sol - yv)
            keep = res < np.percentile(res, 80)
            coef.append(np.linalg.lstsq(A[keep], yv[keep], rcond=None)[0])
        lit = np.stack([ri[..., 0] * coef[c][0] + ri[..., 1] * coef[c][1] + ri[..., 2] * coef[c][2] + coef[c][3]
                        for c in range(3)], axis=-1)
        sel = land & (radial > 0)
        pool.append(np.c_[radial[sel], dep[sel], wy[sel], gs[sel], lit[sel]])
        spot_of.append(np.full(int(sel.sum()), ["landing", "hill", "river"].index(row["spot"])
                               if row["spot"] in ("landing", "hill", "river") else 3))
        # THE CHECK: world.fog's model on the lit render, against the game, on the land past 25u
        from ff9mapkit.world import fog as FG
        fogm = FG.from_game(GAME)
        far_land = land & (dep > 25.0)
        with_fog = fogm.apply(lit, dep, wy)
        err_none = float(np.abs(lit[far_land] - gs[far_land]).mean())
        err_fog = float(np.abs(with_fog[far_land] - gs[far_land]).mean())
        sky = ~np.isfinite(dep) & _mask(h, w)
        sky_err = float(np.abs(gs[sky] - np.asarray(fogm.rgb, dtype=float)).mean()) if sky.any() else None
        checks.append({"spot": row["spot"], "turn": row["turn"], "err_no_fog": err_none, "err_fog": err_fog,
                       "sky_vs_fog_rgb": sky_err, "far_px": int(far_land.sum())})
        from PIL import Image
        view = FG.fog_still(ri.clip(0, 255).astype(np.uint8), dep, v, fogm).astype(np.float32)   # the editor's view
        Image.fromarray(np.concatenate([gs, ri, view], axis=1).clip(0, 255).astype(np.uint8)).save(
            HERE / "out" / f"{tag}-{row['spot']}-{row['turn']}.png")
        far = land & (radial >= np.percentile(radial[land], 97))
        per.append({"spot": row["spot"], "turn": row["turn"], "eye_y": float(eye[1]), "near_px": int(near.sum()),
                    "far_game_rgb": [float(v_) for v_ in np.median(gs[far], axis=0)],
                    "far_radial": float(np.median(radial[far]))})
    P = np.concatenate(pool)
    rad, dep, wy, game, lit = P[:, 0], P[:, 1], P[:, 2], P[:, 3:6], P[:, 6:9]
    C = np.median(np.array([p["far_game_rgb"] for p in per]), axis=0)  # the haze the far land fades into
    d = C[None, :] - lit
    f = np.clip(((game - lit) * d).sum(axis=1) / np.maximum((d * d).sum(axis=1), 1.0), -0.5, 1.5)
    ok = (d * d).sum(axis=1) > 400.0                                     # the lit colour differs from the haze
    out = {"fog_rgb": [float(c) for c in C], "stills": per, "n": int(ok.sum()), "fits": {}}
    for name, dist in (("radial", rad), ("depth", dep)):
        edges = np.arange(0, 260, 8.0)
        idx = np.digitize(dist[ok], edges)
        bins = [(float(edges[i - 1] + 4), float(np.median(f[ok][idx == i])), int((idx == i).sum()))
                for i in range(1, len(edges)) if (idx == i).sum() >= 40]
        xs = np.array([b[0] for b in bins])
        ys = np.array([b[1] for b in bins])
        ws = np.sqrt(np.array([b[2] for b in bins], dtype=float))
        best = None
        for s in np.arange(0, 120, 1.0):
            for e in np.arange(s + 4, 400, 2.0):
                for cap in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7):
                    pred = cap * np.clip((xs - s) / (e - s), 0, 1)
                    err = float(np.sqrt((ws * (pred - ys) ** 2).sum() / ws.sum()))
                    if best is None or err < best[0]:
                        best = (err, float(s), float(e), cap)
        out["fits"][name] = {"rmse": best[0], "start": best[1], "end": best[2], "cap": best[3], "bins": bins}
        print(f"{name}: linear fog {best[1]:.0f} -> {best[2]:.0f}u, cap {best[3]:.2f}, rmse {best[0]:.3f} over "
              f"{len(bins)} bins")
    lo, hi = wy[ok] < 4.0, wy[ok] >= 8.0                                # the height fog: low ground vs high
    for name, m in (("low ground (y < 4)", lo), ("high ground (y >= 8)", hi)):
        idx = np.digitize(rad[ok][m], np.arange(0, 260, 16.0))
        print(f"  {name}:", [(16 * i - 8, round(float(np.median(f[ok][m][idx == i])), 2)) for i in range(1, 17)
                             if (idx == i).sum() >= 40])
    # THE HEIGHT TERM: the Mist is a ground fog -- high ground stands out of it. f = ramp(depth; s, e(y)), the end
    # pushed out by height above a floor: e(y) = e0 + k * max(0, y - y0)
    dd, yy_, ff = dep[ok], wy[ok], f[ok]
    keep = np.isfinite(dd) & (dd < 240)
    dd, yy_, ff = dd[keep], yy_[keep], ff[keep]
    grid = {}
    for i in range(len(dd)):
        key = (int(dd[i] // 8), int(min(yy_[i], 39.9) // 4))
        grid.setdefault(key, []).append(ff[i])
    cells = [((k[0] + 0.5) * 8, (k[1] + 0.5) * 4, float(np.median(v)), len(v)) for k, v in grid.items() if len(v) >= 30]
    X = np.array([c[0] for c in cells]); Y = np.array([c[1] for c in cells]); F = np.array([c[2] for c in cells])
    Wt = np.sqrt(np.array([c[3] for c in cells], dtype=float))
    hb = None
    for s0 in np.arange(8, 30, 1.0):
        for e0 in np.arange(50, 90, 1.0):
            for k in np.arange(0, 6.01, 0.25):
                for y0 in (0.0, 2.0, 4.0, 6.0, 8.0):
                    e = e0 + k * np.maximum(0.0, Y - y0)
                    pred = np.clip((X - s0) / (e - s0), 0, 1)
                    err = float(np.sqrt((Wt * (pred - F) ** 2).sum() / Wt.sum()))
                    if hb is None or err < hb[0]:
                        hb = (err, float(s0), float(e0), float(k), float(y0))
    flat = None
    for s0 in np.arange(8, 30, 1.0):
        for e0 in np.arange(50, 120, 1.0):
            pred = np.clip((X - s0) / (e0 - s0), 0, 1)
            err = float(np.sqrt((Wt * (pred - F) ** 2).sum() / Wt.sum()))
            if flat is None or err < flat[0]:
                flat = (err, float(s0), float(e0))
    # LEAVE ONE SPOT OUT: fit the height model on two spots' cells, score it on the third's (out of sample)
    SP = np.concatenate(spot_of)[ok][keep]
    loso = {}
    for held in range(3):
        def cells_of(mask):
            g = {}
            for i in np.flatnonzero(mask):
                g.setdefault((int(dd[i] // 8), int(min(yy_[i], 39.9) // 4)), []).append(ff[i])
            c = [((k[0] + 0.5) * 8, (k[1] + 0.5) * 4, float(np.median(v)), len(v)) for k, v in g.items() if len(v) >= 30]
            return (np.array([q[0] for q in c]), np.array([q[1] for q in c]), np.array([q[2] for q in c]),
                    np.sqrt(np.array([q[3] for q in c], dtype=float)))
        Xa, Ya, Fa, Wa = cells_of(SP != held)
        Xb, Yb, Fb, Wb = cells_of(SP == held)
        bb = None
        for s0 in np.arange(8, 30, 1.0):
            for e0 in np.arange(50, 90, 1.0):
                for k in np.arange(0, 6.01, 0.25):
                    pred = np.clip((Xa - s0) / (e0 + k * Ya - s0), 0, 1)
                    err = float(np.sqrt((Wa * (pred - Fa) ** 2).sum() / Wa.sum()))
                    if bb is None or err < bb[0]:
                        bb = (err, s0, e0, k)
        test = float(np.sqrt((Wb * (np.clip((Xb - bb[1]) / (bb[2] + bb[3] * Yb - bb[1]), 0, 1) - Fb) ** 2).sum()
                             / Wb.sum()))
        none = float(np.sqrt((Wb * Fb ** 2).sum() / Wb.sum()))
        loso[["landing", "hill", "river"][held]] = {"fit": [float(bb[1]), float(bb[2]), float(bb[3])],
                                                    "train_rmse": bb[0], "test_rmse": test, "no_fog_rmse": none}
        print(f"  held out {['landing', 'hill', 'river'][held]}: fitted {bb[1]:.0f} -> {bb[2]:.0f}u + {bb[3]:.2f}/u; "
              f"its own rmse {test:.3f} (train {bb[0]:.3f}; no fog would be {none:.3f})")
    out["loso"] = loso
    out["height"] = {"rmse": hb[0], "start": hb[1], "end": hb[2], "per_u": hb[3], "floor": hb[4],
                     "flat_rmse": flat[0], "flat": [flat[1], flat[2]], "cells": len(cells)}
    print(f"by depth x height ({len(cells)} cells): flat {flat[1]:.0f} -> {flat[2]:.0f}u rmse {flat[0]:.3f}; with height "
          f"{hb[1]:.0f} -> {hb[2]:.0f}u + {hb[3]:.2f}u per unit above y {hb[4]:.0f}, rmse {hb[0]:.3f}")
    print("fog colour (the far land's median):", [round(c) for c in C], "per still:",
          [[round(c) for c in p["far_game_rgb"]] for p in per])
    out["checks"] = checks
    for c in checks:
        print(f"  {c['spot']}-{c['turn']}: far land error {c['err_no_fog']:.1f} without fog -> {c['err_fog']:.1f} "
              f"with it; sky vs the fog colour {c['sky_vs_fog_rgb'] if c['sky_vs_fog_rgb'] is None else round(c['sky_vs_fog_rgb'], 1)}")
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["c8"]:                      # out of sample: C8's vehicle stills, the model as fitted on C7's
        main(HERE / "out" / "c8_capture.json", HERE / "out" / "c8_compare.json", tag="c18-c8")
    else:
        main()
