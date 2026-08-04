"""THE GUARDED PALETTE CENSUS -- ask what each rect CARRIES, not whether a mass fits.

The first census asked "does a landmass sit whole inside this rect", trusted the gate
stack, and published 10 carryable masses. Six of them shipped a crumb or nothing: the
sinuous island carried `terrain:0`, Daguerreo 25 tris of a 9264u2 island. Every one passed
every gate, because the gates score the carry that HAPPENED and none asks whether the
subject is still in it.

So this census asks the only question that matters -- **how much of the target landmass
actually survives the carry** -- and it asks it per RECT, trying several per mass rather
than committing to one (the other bug: a mass whose best-by-excise rect fails was reported
unavailable even when another rect carried it).

Offline and exact: `kept = rect terrain - excise-dropped terrain` reproduces the deploy's
own `carried: terrain:N` line exactly, verified on the four real carries.

  py studies/coast-shape-language/palette_census2.py [--disc 1]

Read-only. Writes out/palette2_d1.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit.world import transplant as TR                 # noqa: E402

CELL, BLK = 4.0, 16
NX, NY = 24, 20
#: a mass is only worth carrying if a real share of it survives
#: (KEEP_FRAC removed -- it was dead: `usable` keys off carried tris, not a fraction)


def label_wrapped(land):
    nz, nx = land.shape
    lab = np.zeros((nz, nx), np.int32)
    cur = 0
    for z0 in range(nz):
        for x0 in range(nx):
            if not land[z0, x0] or lab[z0, x0]:
                continue
            cur += 1
            stack = [(z0, x0)]
            lab[z0, x0] = cur
            while stack:
                z, x = stack.pop()
                for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = z + dz, (x + dx) % nx
                    if 0 <= a < nz and land[a, b] and not lab[a, b]:
                        lab[a, b] = cur
                        stack.append((a, b))
    return lab, cur


def rect_terrain(bx, by, nx, ny, disc):
    return sum(len(TR.world_tris(bx + i, by + j, "terrain", disc=disc))
               for j in range(ny) for i in range(nx))


def _mass_terrain(bx, by, nx, ny, mass_id, lab, disc):
    """Terrain tris inside the rect that belong to ``mass_id`` in the label mask.

    Excise drops whole assemblies, so a surviving assembly is either wholly kept or
    wholly gone; what this measures is how much of THE TARGET is in the rect at all,
    which is the ceiling on what a carry can deliver. Attribution is by plan position
    into the same 4u mask the masses were labelled from.
    """
    # world_tris ALREADY returns world coordinates (it folds in 64*bx / -64*by). Adding the
    # block origin again double-offsets every tri, which lands them on the wrong mass -- and
    # the failure is invisible except at block (0,0), where the offset is zero. That is
    # exactly how the first run reported "1 mass carries real land", and the one survivor
    # was the mass at (0,0).
    nz, nxc = lab.shape
    n = 0
    for j in range(ny):
        for i in range(nx):
            for t in TR.world_tris(bx + i, by + j, "terrain", disc=disc):
                cx = sum(v[0][0] for v in t) / 3.0
                cz = sum(v[0][2] for v in t) / 3.0
                gx, gz = int(cx // CELL) % nxc, int((-cz) // CELL)
                if 0 <= gz < nz and lab[gz, gx] == mass_id:
                    n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    ap.add_argument("--min-area", type=float, default=400.0)
    args = ap.parse_args()

    d = np.load(HERE / "out" / f"landmask_d{args.disc}.npz")
    land, foot, hgt = d["land"], d["foot"], d["hgt"]
    lab, n = label_wrapped(land)

    masses = []
    for i in range(1, n + 1):
        zz, xx = np.nonzero(lab == i)
        area = len(zz) * CELL * CELL
        if area < args.min_area:
            continue
        h = hgt[zz, xx]
        h = h[~np.isnan(h)]
        masses.append(dict(
            id=i, area=area, relief=round(float(np.percentile(h, 95)), 1) if len(h) else 0.0,
            walk=round(float(foot[zz, xx].mean()), 2),
            bx0=int(xx.min()) // BLK, bx1=int(xx.max()) // BLK,
            by0=int(zz.min()) // BLK, by1=int(zz.max()) // BLK))
    masses.sort(key=lambda m: -m["area"])
    print(f"[disc {args.disc}] {len(masses)} landmasses >= {args.min_area:.0f}u2 to test\n")

    out = []
    for m in masses:
        w, h = m["bx1"] - m["bx0"] + 1, m["by1"] - m["by0"] + 1
        if w > 4 or h > 4:
            print(f"  mass {m['id']:>3} {m['area']:>7.0f}u2  spans {w}x{h} blocks -- "
                  f"too big for any rect")
            continue
        best = None
        # the mass's own block bbox first, then pad outward: more room can help (the ring
        # ends inside) or hurt (the assembly re-touches the new frame) -- measured, not guessed
        cands = []
        for pad_x in (0, 1):
            for pad_y in (0, 1):
                bx, by = m["bx0"] - pad_x, m["by0"] - pad_y
                nx, ny = w + 2 * pad_x, h + 2 * pad_y
                if bx < 0 or by < 0 or bx + nx > NX or by + ny > NY or nx > 4 or ny > 4:
                    continue
                cands.append((bx, by, nx, ny))
        for (bx, by, nx, ny) in cands:
            try:
                _tw, rep = TR.excise_plan((bx, by), (nx, ny), disc=args.disc)
            except Exception:
                continue
            why = rep.get("refused")
            # ATTRIBUTE THE SURVIVING LAND TO A MASS. Rect-wide carried terrain credits
            # the target with whatever ELSE the rect happens to hold: padding the rect
            # around mass 9 (544u2) swept in the reef and reported "carries 798" -- the
            # reef's own number, for a mass a fifth its size. Count only tris whose plan
            # position falls on THIS mass in the label mask.
            kept = 0 if why else _mass_terrain(bx, by, nx, ny, m["id"], lab, args.disc)
            if best is None or kept > best["carried"]:
                best = dict(donor=[bx, by], size=[nx, ny], carried=kept,
                            refused=why[:70] if why else None)
        if best is None:
            continue
        row = dict(m, **best, usable=bool(best["carried"] > 0))
        out.append(row)
        mark = "CARRIES" if row["usable"] else "no      "
        print(f"  mass {m['id']:>3} {m['area']:>7.0f}u2 relief {m['relief']:>5.1f} "
              f"walk {m['walk']:.2f}  {mark} {best['carried']:>5} tris via "
              f"{tuple(best['donor'])} {best['size'][0]}x{best['size'][1]}"
              + (f"  ({best['refused']})" if best["refused"] and not row["usable"] else ""))

    usable = [r for r in out if r["usable"]]
    print(f"\nGUARDED PALETTE: {len(usable)} masses carry real land")
    for r in sorted(usable, key=lambda r: -r["carried"]):
        print(f"   {str(tuple(r['donor'])):>9} {r['size'][0]}x{r['size'][1]}  "
              f"{r['area']:>7.0f}u2  relief {r['relief']:>5.1f}  walk {r['walk']:.2f}  "
              f"carries {r['carried']} tris")
    (HERE / "out" / f"palette2_d{args.disc}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
