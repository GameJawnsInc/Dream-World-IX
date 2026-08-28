"""Take-8 Phase 1 — measure the SW window's base against THE PROFILE LAW (no writes).

For each foot station along the arc's rock-grass contact:
  - split the rock above into CARRIED donor tris vs MINTED (zip/contact-course) tris,
    by matching UV triples against the donor blocks and, for realigned tris, by the
    fitted rigid placement transform;
  - fit the local carried-face plane in the 6-18u uphill corridor -> face angle;
  - rim = the lowest carried-rock height in the corridor (where the donor face ends
    and my authored base begins);
  - THE LAWFUL CONTACT: extend the face plane from the rim down to lawn height;
    lawful horizontal run L = (rim_y - lawn_y) / tan(face_angle). Compare to the
    current run (contact -> rim footprint) -> per-station move.
Also: 13-sample profiles for every DONOR-HOME station and every owner-passed site
station, so a nearest-neighbor-profile gate can be calibrated for phase 3.
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from envelope_profile import (GAME, WM, WINDOW, SITE_BLOCKS, ROCK, GRASS,  # noqa: E402
                              STEPS, HeightField, read_loose, stations,
                              stock_tris, pct)

REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import extract as X                   # noqa: E402

DONOR_BLOCKS = [(5, 15), (5, 16), (6, 15), (6, 16)]


def uvkey(us):
    return frozenset((round(u, 5), round(v, 5)) for u, v in us)


def donor_data():
    """donor tris in donor-world coords + their uv triples."""
    tris, keys = [], []
    for bx, by in DONOR_BLOCKS:
        bm = X.read_block(bx, by, disc=1)
        wv = [(bx * 64.0 + v[0], v[1], v[2] - by * 64.0) for v in bm.verts]
        ids = [int(round(t[0])) for t in bm.tangents]
        for a, b, c in bm.tris:
            tris.append((wv[a], wv[b], wv[c], (ids[a] >> 2) & 0x3F))
            keys.append(uvkey((bm.uvs[a], bm.uvs[b], bm.uvs[c])))
    return tris, keys


def site_data():
    """site tris + uv triples, from the live loose meshes."""
    import struct
    tris, keys = [], []
    for bx, by in SITE_BLOCKS:
        p = WM / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not p.is_file():
            continue
        d = p.read_bytes()
        _, vc, _, fl = struct.unpack_from("<iiii", d, 4)
        off = 20
        verts = [struct.unpack_from("<fff", d, off + i * 12) for i in range(vc)]
        off += vc * 12 + (vc * 12 if fl & 1 else 0)
        uvs = [struct.unpack_from("<ff", d, off + i * 8) for i in range(vc)]
        off += vc * 8
        topos = [(int(round(struct.unpack_from("<f", d, off + i * 16)[0])) >> 2) & 0x3F
                 for i in range(vc)]
        for t in range(vc // 3):
            i = t * 3
            ws = [(bx * 64 + verts[i + k][0], verts[i + k][1],
                   verts[i + k][2] - by * 64) for k in range(3)]
            tris.append((ws[0], ws[1], ws[2], topos[i]))
            keys.append(uvkey((uvs[i], uvs[i + 1], uvs[i + 2])))
    return tris, keys


def fit_transform(site_tris, site_keys, dn_tris, dn_keys):
    """rigid xz transform donor->site from uniquely-matched uv triples (centroids)."""
    dcount = defaultdict(int)
    dref = {}
    for t, k in zip(dn_tris, dn_keys):
        dcount[k] += 1
        dref[k] = t
    scount = defaultdict(int)
    sref = {}
    for t, k in zip(site_tris, site_keys):
        scount[k] += 1
        sref[k] = t
    pairs = []
    for k in sref:
        if scount[k] == 1 and dcount.get(k) == 1:
            d = dref[k]
            s = sref[k]
            dc = [sum(v[j] for v in d[:3]) / 3 for j in range(3)]
            sc = [sum(v[j] for v in s[:3]) / 3 for j in range(3)]
            pairs.append((dc, sc))
    # Kabsch in xz
    n = len(pairs)
    dmx = sum(p[0][0] for p in pairs) / n
    dmz = sum(p[0][2] for p in pairs) / n
    smx = sum(p[1][0] for p in pairs) / n
    smz = sum(p[1][2] for p in pairs) / n
    sxx = sxz = szx = szz = 0.0
    for d, s in pairs:
        dx, dz = d[0] - dmx, d[2] - dmz
        sx, sz = s[0] - smx, s[2] - smz
        sxx += dx * sx
        sxz += dx * sz
        szx += dz * sx
        szz += dz * sz
    th = math.atan2(sxz - szx, sxx + szz)
    c, s_ = math.cos(th), math.sin(th)
    dy = sum(p[1][1] - p[0][1] for p in pairs) / n
    res = 0.0
    for d, sp in pairs:
        px = c * (d[0] - dmx) - s_ * (d[2] - dmz) + smx
        pz = s_ * (d[0] - dmx) + c * (d[2] - dmz) + smz
        res = max(res, math.hypot(px - sp[0], pz - sp[2]))
    print(f"transform: rot {math.degrees(th):.1f} deg, dy {dy:+.2f}, "
          f"{n} unique pairs, max plan residual {res:.3f}u")

    def xf(p):
        return (c * (p[0] - dmx) - s_ * (p[2] - dmz) + smx, p[1] + dy,
                s_ * (p[0] - dmx) + c * (p[2] - dmz) + smz)
    return xf


def classify(site_tris, site_keys, dn_keys, dn_tris, xf):
    """carried (donor geometry) vs minted, per site tri."""
    dset = set(dn_keys)
    vset = set()
    for t in dn_tris:
        for v in t[:3]:
            w = xf(v)
            vset.add((round(w[0], 1), round(w[1], 1), round(w[2], 1)))
    out = []
    for t, k in zip(site_tris, site_keys):
        if k in dset:
            out.append(True)
            continue
        hit = sum((round(v[0], 1), round(v[1], 1), round(v[2], 1)) in vset
                  for v in t[:3])
        out.append(hit == 3)
    return out


def face_plane(rock_pts, mx, mz, dx, dz):
    """LSQ plane over carried-rock verts in the 6-18u uphill corridor (half-width 5)."""
    sel = []
    for x, y, z in rock_pts:
        t = (x - mx) * dx + (z - mz) * dz
        w = abs(-(x - mx) * dz + (z - mz) * dx)
        if 6.0 <= t <= 18.0 and w <= 5.0:
            sel.append((x, y, z, t))
    if len(sel) < 4:
        return None, sel
    # slope along the uphill dir: fit y = a*t + b over the corridor
    n = len(sel)
    st = sum(p[3] for p in sel)
    sy = sum(p[1] for p in sel)
    stt = sum(p[3] * p[3] for p in sel)
    sty = sum(p[3] * p[1] for p in sel)
    den = n * stt - st * st
    if abs(den) < 1e-9:
        return None, sel
    a = (n * sty - st * sy) / den
    return math.degrees(math.atan(a)), sel


def main():
    dn_tris, dn_keys = donor_data()
    site_tris, site_keys = site_data()
    print(f"donor tris {len(dn_tris)}, site tris {len(site_tris)}")
    xf = fit_transform(site_tris, site_keys, dn_tris, dn_keys)
    carried = classify(site_tris, site_keys, dn_keys, dn_tris, xf)
    nc = sum(carried)
    print(f"carried {nc} / minted {len(site_tris) - nc} site tris")

    rock_carried_pts = []
    for t, isc in zip(site_tris, carried):
        if isc and t[3] == ROCK:
            rock_carried_pts.extend(t[:3])

    hf = HeightField(site_tris)
    print("\nWINDOW stations (every contact edge, incl. rise<4):")
    print("  (x, z)            lawnY  A1    face  rimY  rimT  curRun lawfulRun move")
    rows = []
    for mx, mz, dx, dz in stations(site_tris):
        if not (WINDOW[0] <= mx <= WINDOW[2] and WINDOW[1] <= mz <= WINDOW[3]):
            continue
        y0 = hf.h(mx, mz)
        ys = []
        for d in STEPS:
            y = hf.h(mx + dx * d, mz + dz * d)
            if y is None:
                break
            ys.append(y)
        a1 = math.degrees(math.atan2(ys[4] - ys[0], 8.0)) if len(ys) >= 5 else float("nan")
        ang, sel = face_plane(rock_carried_pts, mx, mz, dx, dz)
        if sel:
            rim = min(p[1] for p in sel)
            rimt = min(p[3] for p in sel if abs(p[1] - rim) < 0.75)
        else:
            rim, rimt = float("nan"), float("nan")
        if ang is not None and ang > 8.0 and not math.isnan(rim):
            lawful = (rim - y0) / math.tan(math.radians(ang))
            move = rimt - lawful       # >0: contact moves INWARD by this much
        else:
            lawful, move = float("nan"), float("nan")
        angs = f"{ang:5.1f}" if ang is not None else "  n/a"
        print(f"  ({mx:7.1f},{mz:7.1f})  {y0:5.1f}  {a1:5.1f} {angs} "
              f"{rim:5.1f} {rimt:5.1f}  {rimt - 0.0:5.1f}   {lawful:6.1f}  {move:+5.1f}")
        rows.append((mx, mz, y0, a1, ang, rim, rimt, lawful, move))

    # nearest-neighbor profile calibration corpus: donor home + site non-window
    def prof(tris, name, keep):
        hfl = HeightField(tris)
        out = []
        for mx, mz, dx, dz in stations(tris):
            if not keep(mx, mz):
                continue
            ys = []
            for d in STEPS:
                y = hfl.h(mx + dx * d, mz + dz * d)
                if y is None:
                    break
                ys.append(y)
            if len(ys) == len(STEPS):
                out.append([y - ys[0] for y in ys])
        print(f"{name}: {len(out)} full profiles")
        return out

    dprof = prof(dn_tris, "donor-home profiles", lambda x, z: True)
    sprof = prof(site_tris, "site passed-face profiles",
                 lambda x, z: not (WINDOW[0] <= x <= WINDOW[2]
                                   and WINDOW[1] <= z <= WINDOW[3]))

    def nn(p, corpus):
        return min(max(abs(a - b) for a, b in zip(p, q)) for q in corpus)

    d_pass = sorted(nn(p, dprof) for p in sprof)
    print("\npassed-face NN-to-donor-home (Linf, u): "
          f"p50 {pct(d_pass, 50):.2f}  p90 {pct(d_pass, 90):.2f}  max {d_pass[-1]:.2f}")
    wprof = prof(site_tris, "window profiles",
                 lambda x, z: (WINDOW[0] <= x <= WINDOW[2]
                               and WINDOW[1] <= z <= WINDOW[3]))
    for p in wprof:
        print(f"  window station NN {nn(p, dprof):5.2f}  profile "
              + " ".join(f"{v:5.1f}" for v in p))


if __name__ == "__main__":
    main()
