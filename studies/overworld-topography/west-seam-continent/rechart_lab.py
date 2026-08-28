"""The re-chart lab: load the R4 massif, build the exterior foot chain, classify the
knoll facade's chart, and render the flank -- textured or false-colored by chart class,
with optional candidate UV shifts applied in memory (nothing is written to the install)."""
import math
import struct
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
G = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
ATLAS = GAME / "MoguriMain" / "StreamingAssets" / "Assets" / "Resources" / "worldmap" \
    / "textures" / "res(1_24)_terrain.png"
OUT = Path(__file__).parent
BLOCKS = [(22, 6), (22, 7), (23, 6), (23, 7)]
TILE_U, TILE_V = 0.0625, 0.03125
PU, PV = 0.015625, 0.01953125
GRASS = {0, 1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 42}

# the site camera frame (from home_flank_render's fit)
CENTER = (1429.0, 8.3, -473.0)
TAN = (0.637490006226303, -0.7704586244319601)
NRM = (-0.7704586244319601, -0.637490006226303)
PITCH = math.radians(32)
SC = 14
HALF_W, SY_LO, SY_HI = 34.0, -16.0, 22.0


def read_loose(path, bx, by):
    data = path.read_bytes()
    _, vcount, _, flags = struct.unpack_from("<iiii", data, 4)
    off = 20
    verts = [struct.unpack_from("<fff", data, off + i * 12) for i in range(vcount)]
    off += vcount * 12
    if flags & 1:
        off += vcount * 12
    uvs = [struct.unpack_from("<ff", data, off + i * 8) for i in range(vcount)]
    off += vcount * 8
    topos = [(int(round(struct.unpack_from("<f", data, off + i * 16)[0])) >> 2) & 0x3F
             for i in range(vcount)]
    tris = []
    for t in range(vcount // 3):
        i = t * 3
        w = [[bx * 64 + verts[i + k][0], verts[i + k][1], verts[i + k][2] - by * 64]
             for k in range(3)]
        tris.append({"w": w, "uv": [list(uvs[i + k]) for k in range(3)], "topo": topos[i],
                     "blk": (bx, by), "tri": t})
    return tris


def load_all():
    tris = []
    for bx, by in BLOCKS:
        p = G / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        tris += read_loose(p, bx, by)
    return tris


def foot_chain(tris):
    kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    eo = defaultdict(list)
    for t in tris:
        ps = [kk(v) for v in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eo[tuple(sorted((ps[a], ps[b])))].append(t["topo"])
    edges = []
    for e, tps in eo.items():
        if len(tps) == 2 and 49 in tps and any(tp in GRASS for tp in tps):
            my = (e[0][1] + e[1][1]) / 2
            mx = (e[0][0] + e[1][0]) / 2
            mz = (e[0][2] + e[1][2]) / 2
            if my < 8 and 1390 <= mx <= 1466 and -512 <= mz <= -434:
                edges.append(e)
    adj = defaultdict(list)
    for e in edges:
        adj[e[0]].append(e[1])
        adj[e[1]].append(e[0])
    seen, chains = set(), []
    for start in list(adj):
        if start in seen or len(adj[start]) != 1:
            continue
        ch = [start]
        seen.add(start)
        while True:
            nxt = [n for n in adj[ch[-1]] if n not in seen]
            if not nxt:
                break
            ch.append(nxt[0])
            seen.add(nxt[0])
        chains.append(ch)
    chains.sort(key=len, reverse=True)
    merged = chains[0]
    rest = chains[1:]
    while rest:
        best = None
        for ci, ch in enumerate(rest):
            for fm in (0, 1):
                for fc in (0, 1):
                    a = merged[0] if fm else merged[-1]
                    b = ch[-1] if fc else ch[0]
                    d = math.dist((a[0], a[2]), (b[0], b[2]))
                    if best is None or d < best[0]:
                        best = (d, ci, fm, fc)
        d, ci, fm, fc = best
        if d > 8:
            break
        ch = rest.pop(ci)
        if fc:
            ch = ch[::-1]
        merged = (ch[::-1] + merged) if fm else (merged + ch)
    S = [0.0]
    for i in range(1, len(merged)):
        S.append(S[-1] + math.dist((merged[i - 1][0], merged[i - 1][2]),
                                   (merged[i][0], merged[i][2])))
    return merged, S


def classify(tris, chain, S):
    """Tag every rock tri near the exterior foot with (s, h, row, col)."""
    def foot_at(px, pz):
        best, bs, by_ = 1e9, 0, 0
        for i in range(len(chain)):
            dd = (chain[i][0] - px) ** 2 + (chain[i][2] - pz) ** 2
            if dd < best:
                best, bs, by_ = dd, S[i], chain[i][1]
        return math.sqrt(best), bs, by_

    for t in tris:
        t["cls"] = None
        if t["topo"] != 49:
            continue
        cx = sum(v[0] for v in t["w"]) / 3
        cy = sum(v[1] for v in t["w"]) / 3
        cz = sum(v[2] for v in t["w"]) / 3
        d, s, fy = foot_at(cx, cz)
        if d > 15:
            continue
        uc = sum(u[0] for u in t["uv"]) / 3
        vc = sum(u[1] for u in t["uv"]) / 3
        row = int((vc - PV) / TILE_V)
        col = int((uc - PU) / TILE_U)
        t["cls"] = dict(s=s, h=cy - fy, row=row, col=col, d=d)


atlas = Image.open(ATLAS).convert("RGB")
AW, AH = atlas.size
APX = atlas.load()


def at_b(u_, v_):
    fx = (u_ % 1.0) * AW - 0.5
    fy = (1.0 - v_ % 1.0) * AH - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = [0.0, 0.0, 0.0]
    for dx, dy, wg in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                       (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        qx, qy = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
        c = APX[qx, qy]
        acc[0] += c[0] * wg
        acc[1] += c[1] * wg
        acc[2] += c[2] * wg
    return int(acc[0]), int(acc[1]), int(acc[2])


def render(tris, tag, color_fn=None):
    """color_fn(tri) -> flat rgb or None for textured."""
    d = (-NRM[0] * math.cos(PITCH), -math.sin(PITCH), -NRM[1] * math.cos(PITCH))
    r3 = (TAN[0], 0.0, TAN[1])
    u3 = (r3[1] * d[2] - r3[2] * d[1], r3[2] * d[0] - r3[0] * d[2],
          r3[0] * d[1] - r3[1] * d[0])
    if u3[1] < 0:
        u3 = (-u3[0], -u3[1], -u3[2])
    W = int(2 * HALF_W * SC)
    H = int((SY_HI - SY_LO) * SC)
    img = Image.new("RGB", (W, H), (204, 217, 228))
    px = img.load()

    def proj(p):
        vx, vy, vz = p[0] - CENTER[0], p[1] - CENTER[1], p[2] - CENTER[2]
        return (vx * r3[0] + vy * r3[1] + vz * r3[2],
                vx * u3[0] + vy * u3[1] + vz * u3[2],
                vx * d[0] + vy * d[1] + vz * d[2])

    draw = []
    for t in tris:
        ps = [proj(v) for v in t["w"]]
        if all(abs(p[0]) > HALF_W for p in ps) or all(not (SY_LO < p[1] < SY_HI) for p in ps):
            continue
        a, b, c = t["w"]
        gn = ((b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
              (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
              (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        if gn[0] * d[0] + gn[1] * d[1] + gn[2] * d[2] > 0:
            continue
        depth = sum(p[2] for p in ps) / 3
        draw.append((depth, ps, t))
    draw.sort(key=lambda e: -e[0])
    for _, ps, t in draw:
        flat = color_fn(t) if color_fn else None
        xs = [(p[0] + HALF_W) * SC for p in ps]
        ys = [(SY_HI - p[1]) * SC for p in ps]
        x0, x1 = max(0, int(min(xs))), min(W - 1, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys))), min(H - 1, int(max(ys)) + 1)
        ax, ay = xs[0], ys[0]
        bx_, by_ = xs[1], ys[1]
        cx_, cy_ = xs[2], ys[2]
        den = (by_ - cy_) * (ax - cx_) + (cx_ - bx_) * (ay - cy_)
        if abs(den) < 1e-9:
            continue
        us = t["uv"]
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                w0 = ((by_ - cy_) * (xx + 0.5 - cx_) + (cx_ - bx_) * (yy + 0.5 - cy_)) / den
                w1 = ((cy_ - ay) * (xx + 0.5 - cx_) + (ax - cx_) * (yy + 0.5 - cy_)) / den
                w2 = 1 - w0 - w1
                if w0 < -0.001 or w1 < -0.001 or w2 < -0.001:
                    continue
                if flat:
                    px[xx, yy] = flat
                else:
                    uu = w0 * us[0][0] + w1 * us[1][0] + w2 * us[2][0]
                    vv = w0 * us[0][1] + w1 * us[1][1] + w2 * us[2][1]
                    px[xx, yy] = at_b(uu, vv)
    img.save(OUT / f"lab_{tag}.png")
    return img


if __name__ == "__main__":
    tris = load_all()
    chain, S = foot_chain(tris)
    classify(tris, chain, S)
    print(f"chain {len(chain)} pts, {S[-1]:.0f}u; classified "
          f"{sum(1 for t in tris if t['cls'])} facade rock tris")

    PAL = {11: (60, 220, 60), 10: (220, 50, 50), 9: (240, 150, 40), 8: (60, 200, 220),
           7: (70, 90, 230), 6: (235, 225, 60), 5: (180, 120, 200)}

    def fc(t):
        if t["topo"] in GRASS:
            return (200, 230, 200)
        c = t.get("cls")
        if not c:
            return (150, 150, 150)
        if c["col"] in (4, 5):
            return (230, 60, 200)                          # fringe-column / accessory
        return PAL.get(c["row"], (120, 120, 120))

    cnt = Counter()
    for t in tris:
        if t.get("cls") and 30 <= t["cls"]["s"]:
            cnt[(t["cls"]["row"], t["cls"]["col"])] += 1
    print("window (s>=30) row/col census:", dict(sorted(cnt.items())))
    render(tris, "false", fc)
    render(tris, "base")
    print("wrote lab_false.png / lab_base.png")
