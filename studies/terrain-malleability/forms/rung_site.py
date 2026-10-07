"""forms lane -- numbers for the registered predictions of the two proof rungs (offline, read-only).

F0 (no-DLL, stock art): Water Shrine (3,9) form 1 vs form 2 -- terrain/object/sea y-ranges and tri counts, and the
   cell-local XZ bbox of the form-2 ENTRANCE tiles (IDALL event bits != 0), i.e. what the switch should visibly add.
F1 (s34 Terrain2 override on a stock-NO-OP cell): Black Mage Village's three cells (14,6), (21,10), (22,14) -- for each,
   the first-hit topograph histogram, terrain y-range and entrance-tile count of FORM 1 (== form 2 on disc 1), so a
   plateau can be planted on plain walkable ground away from any entrance tile.
Reuses diff_forms.py's instrument (surface()).  Rerun:  py rung_site.py
"""
import collections
import numpy as np
import diff_forms as D

census = {(r["x"], r["y"]): r for r in D.CENSUS["1"]}


def lists(cell):
    r = census[cell]
    f1, f2 = D.form_lists(r)
    return r, [(k, *D.load_mesh(r["slots"][k]["mesh"])) for k in f1], [(k, *D.load_mesh(r["slots"][k]["mesh"])) for k in f2]


r, m1, m2 = lists((3, 9))
print("F0  Water Shrine (3,9):")
for tag, ms in (("form1", m1), ("form2", m2)):
    for k, V, T, ids in ms:
        print(f"   {tag} {k:<13} tris={len(T):>4} y=[{V[:, 1].min():+.2f},{V[:, 1].max():+.2f}]")
Y2, I2, P2 = D.surface(m2)
ev = (I2 >= 0) & (D.event(np.where(I2 < 0, 0, I2)) != 0)
if ev.any():
    print(f"   form2 entrance tiles: {int(ev.sum())} samples, local x[{D.PX[ev].min() - .5:.0f},{D.PX[ev].max() + .5:.0f}] "
          f"z[{D.PZ[ev].min() - .5:.0f},{D.PZ[ev].max() + .5:.0f}] -> world x[{3 * 64 + D.PX[ev].min() - .5:.0f},"
          f"{3 * 64 + D.PX[ev].max() + .5:.0f}] z[{-9 * 64 + D.PZ[ev].min() - .5:.0f},{-9 * 64 + D.PZ[ev].max() + .5:.0f}]; "
          f"topographs {dict(collections.Counter(int(t) for t in D.topo(I2[ev])))}")
print("\nF1  Black Mage Village cells (form 1 == form 2 on disc 1):")
for cell in ((14, 6), (21, 10), (22, 14)):
    r, m1, _ = lists(cell)
    Y, I, P = D.surface(m1)
    hit = I >= 0
    top = collections.Counter(int(t) for t in D.topo(I[hit]))
    parts = collections.Counter(m1[int(p)][0] for p in P[hit])
    ev = hit & (D.event(np.where(I < 0, 0, I)) != 0)
    terr = [m for m in m1 if m[0] == "TerrainForm1"][0]
    print(f"   {cell}: first-hit parts {dict(parts)}; topo top5 {top.most_common(5)}; "
          f"terrain y=[{terr[1][:, 1].min():+.2f},{terr[1][:, 1].max():+.2f}] tris={len(terr[2])}; entrance samples={int(ev.sum())}")
    # the largest all-terrain, single-topograph, no-entrance 16x16 window -> a plateau site
    best = None
    for j0 in range(0, 49, 4):
        for i0 in range(0, 49, 4):
            idx = np.array([(j0 + j) * 64 + (i0 + i) for j in range(16) for i in range(16)])
            if not (P[idx] == [k for k, (n, *_) in enumerate(m1) if n == "TerrainForm1"][0]).all():
                continue
            if (D.event(np.where(I[idx] < 0, 0, I[idx])) != 0).any():
                continue
            tt = collections.Counter(int(t) for t in D.topo(I[idx]))
            t0, n0 = tt.most_common(1)[0]
            rough = float(np.nanmax(Y[idx]) - np.nanmin(Y[idx]))
            score = (n0 >= 240, -rough)          # >=94% one topograph, then the FLATTEST window
            if best is None or score > best[0]:
                best = (score, i0, j0, t0, rough, float(np.nanmean(Y[idx])))
    if best:
        _, i0, j0, t0, rough, ym = best
        print(f"      plateau site: local x[{i0},{i0 + 16}] z[{-j0},{-j0 - 16}] -> world x[{cell[0] * 64 + i0},{cell[0] * 64 + i0 + 16}] "
              f"z[{-cell[1] * 64 - j0},{-cell[1] * 64 - j0 - 16}], dominant topograph {t0}, relief {rough:.2f}u, mean y {ym:+.2f}")

# F1 dome-centre readout: the stock (form 1 == form 2) surface at the centre of (22,14) and a ring of 8 points r=12
r, m1, _ = lists((22, 14))
Y, I, P = D.surface(m1)
for (lx, lz) in ((31.5, -31.5), (43.5, -31.5), (19.5, -31.5), (31.5, -43.5), (31.5, -19.5)):
    k = int((-lz - 0.5) * 64 + (lx - 0.5))
    print(f"   (22,14) local ({lx},{lz}) world ({22 * 64 + lx},{-14 * 64 + lz}): y={Y[k]:+.2f} topograph={int(D.topo(I[k]))} "
          f"event={int(D.event(I[k]))} part={m1[int(P[k])][0]}")
