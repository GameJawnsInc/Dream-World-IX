"""THE CELL-CLIPPED FILL in game (coastmorph `_grass_fill_region`, master 7f063922): the lab, built outside the install.

Two variants of ONE scratch mod folder, FF9CustomMap-lab, each holding the same four in-place cliff morphs on disc 1
(Terrain + Sea4 overrides, no disc-4 mirror) plus world-environment's mist = false (the mist hides texture):
  out/old/FF9CustomMap-lab  built by the PRE-FIX coastmorph (master 9b99d78c, exported to out/pristine)
  out/new/FF9CustomMap-lab  built by this tree's coastmorph
The four windows are world-morphs' own certified deploy lines that carried a streaked fill tri before the fix (one
each, 1.25-1.91 u^2); each sits on its own cell and no live mod folder overrides any of them.
out/stations.json: per window, the OLD build's streak tri and a camera HOME on stock lawn inland of it -- inside a
kept stock tri (>= 0.08 barycentric), off the 4u lines, with WORLD_PROBE_REACH + 2u of foot-legal ground toward it
(world_face's probes walk ~10u from home) -- and the bearing from home to the tri.
RUN:  py studies/coast-shape-language/cellclip-fill/lab_build.py      (then lab_install.py install old)
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tarfile
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "out"
LAB_NAME = "FF9CustomMap-lab"
PRE_FIX = "9b99d78c"
#: (name, verb, cell, start, end, depth)
WINDOWS = [
    ("A", "cliff_headland", (13, 17), (867.71484375, -1108.0), (872.0, -1151.078125), 3.0),
    ("B", "cliff_headland", (12, 12), (789.0234375, -827.54296875), (768.0, -820.24609375), 4.0),
    ("C", "cliff_bay", (12, 13), (776.4375, -862.62890625), (793.1015625, -832.0), 6.0),
    ("D", "cliff_bay", (5, 16), (380.0, -1081.4140625), (356.0, -1055.09375), 6.0),
]
FOOT_LEGAL = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} \
    | set(range(32, 39)) | {41, 42, 45, 46, 52}
PROBE_CLEAR = 12.0              # WORLD_PROBE_REACH (10u) + 2u
HOME_RANGE = (12.0, 22.0)       # home this far inland of the streak tri


def child(pkg: str, lab: str, out_json: str) -> None:
    """Run in a fresh process with ``pkg`` first on sys.path: build the four morphs, deploy them into ``lab``."""
    sys.path.insert(0, pkg)
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(Path(pkg).resolve()), ff9mapkit.__file__
    from ff9mapkit.world import coastmorph as CM, island as IS, transplant as TR
    rep = {"pkg": pkg, "has_cell_clip": hasattr(CM, "_edge_cuts"), "windows": {}}
    for name, verb, cell, s, e, d in WINDOWS:
        tw = getattr(CM, verb)(cell, s, e, d)
        emit = next(t for t in tw if getattr(t, "part", None) == "terrain" and hasattr(t, "tris"))
        streaks = []
        for t3 in emit.tris:
            r = IS.uv_streak([v[0] for v in t3], [v[2] for v in t3])
            if r is not None:
                streaks.append({"ratio": None if math.isinf(r) else round(r, 2),
                                "pts": [list(v[0]) for v in t3]})
        summ = TR.morph_in_place(lab, cell=cell, tweaks=list(tw), skip_mirror=True)
        if not summ["clean"]:
            raise SystemExit(f"{name}: in-place gates not clean: {[g for g in summ['gates'] if not g.get('ok', True)]}")
        rep["windows"][name] = {"cell": list(cell), "streaks": streaks, "deployed": summ["deployed"],
                                "emit_terrain": len(emit.tris),
                                "emit_pts": [[list(v[0]) for v in t3] for t3 in emit.tris],
                                "emit_topo": [int(round(t3[0][3][0])) for t3 in emit.tris],
                                "drop_keys": sorted(sorted(k) for t in tw if getattr(t, "part", None) == "terrain"
                                                    and hasattr(t, "keys") for k in t.keys)}
    Path(out_json).write_text(json.dumps(rep, indent=1), encoding="utf-8")


def export_pristine() -> Path:
    dst = OUT / "pristine"
    if not (dst / "ff9mapkit" / "__init__.py").exists():
        dst.mkdir(parents=True, exist_ok=True)
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", PRE_FIX, "ff9mapkit/ff9mapkit"],
                             capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
            tf.extractall(OUT / "pristine_tmp")
        shutil.move(str(OUT / "pristine_tmp" / "ff9mapkit" / "ff9mapkit"), str(dst / "ff9mapkit"))
        shutil.rmtree(OUT / "pristine_tmp")
    return dst


def stations(reps: dict) -> dict:
    old_rep = reps["old"]
    sys.path.insert(0, str(ROOT / "ff9mapkit"))
    from ff9mapkit.world import coastmorph as CM, transplant as TR
    from ff9mapkit.world.extract import decode_id
    out = {}
    for name, verb, cell, s, e, d in WINDOWS:
        st = old_rep["windows"][name]["streaks"]
        if len(st) != 1:
            raise SystemExit(f"{name}: the OLD build carries {len(st)} streak tris, want exactly 1")
        pts = st[0]["pts"]
        hx, hz = sum(p[0] for p in pts) / 3.0, sum(p[2] for p in pts) / 3.0
        tw = getattr(CM, verb)(cell, s, e, d)
        dropped, emitted = set(), []
        for t in tw:
            if getattr(t, "part", None) == "terrain" and hasattr(t, "keys"):
                dropped |= t.keys
            elif getattr(t, "part", None) == "terrain" and hasattr(t, "tris"):
                emitted += t.tris
        terr = [t3 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                for t3 in TR.world_tris(cell[0] + dx, cell[1] + dy, "terrain")]
        # the morphed ground: kept stock + the NEW build's emission (the refilled grass is the same surface in both
        # variants -- pieces on the uncut tris' planes -- so a home or a probe line may cross it)
        kept = [t3 for t3 in terr if frozenset(CM._pk(v[0]) for v in t3) not in dropped] + emitted
        win = CM.CliffWindow(cell, s, e)
        inland0 = math.atan2(-win.nhat[1], -win.nhat[0])

        def locate(x, z, tris):
            for t3 in tris:
                (ax, ay, az), (bx, by, bz), (cx, cy, cz) = (v[0] for v in t3)
                det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
                if abs(det) < 1e-9:
                    continue
                w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
                w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
                w2 = 1.0 - w0 - w1
                if min(w0, w1, w2) >= 0.0:
                    return t3, (w0, w1, w2), w0 * ay + w1 * by + w2 * cy
            return None, None, None

        def topo(t3):
            return decode_id(int(round(t3[0][3][0])))["topograph"]
        best = None
        why = {}
        for ang in (0, 15, -15, 30, -30, 45, -45, 60, -60):              # the approach, off straight inland
            a = inland0 + math.radians(ang)
            inland = (math.cos(a), math.sin(a))
            for t in [HOME_RANGE[0] + 0.5 * k for k in range(int((HOME_RANGE[1] - HOME_RANGE[0]) * 2) + 1)]:
                x = hx + t * inland[0]
                z = hz + t * inland[1]
                if min(abs(x / 4.0 - round(x / 4.0)), abs(z / 4.0 - round(z / 4.0))) * 4.0 < 0.3:
                    why["on a 4u line"] = why.get("on a 4u line", 0) + 1
                    continue
                t3, bary, y = locate(x, z, kept)
                if t3 is None or min(bary) < 0.08 or topo(t3) not in FOOT_LEGAL:
                    k_ = "no tri" if t3 is None else ("edge" if min(bary) < 0.08 else f"topo {topo(t3)}")
                    why[k_] = why.get(k_, 0) + 1
                    continue
                L = math.hypot(hx - x, hz - z)
                ok = True
                for k in range(1, int(PROBE_CLEAR * 4) + 1):          # the probe line, every 0.25u
                    f = 0.25 * k / L
                    q, _b, _y = locate(x + f * (hx - x), z + f * (hz - z), kept)
                    if q is None or topo(q) not in FOOT_LEGAL:
                        k_ = "probe: no tri" if q is None else f"probe: topo {topo(q)}"
                        why[k_] = why.get(k_, 0) + 1
                        ok = False
                        break
                if ok:
                    best = {"home": [round(x, 3), round(z, 3)], "ground_y": round(y, 3),
                            "bearing": round(math.degrees(math.atan2(hz - z, hx - x)) % 360.0, 2),
                            "distance": round(L, 2), "streak": [round(hx, 3), round(hz, 3)],
                            "home_topo": topo(t3), "approach_off_inland": ang}
                    break
            if best:
                break
        if best is None:
            raise SystemExit(f"{name}: no lawful home {HOME_RANGE[0]}-{HOME_RANGE[1]}u from the streak tri "
                             f"within 60 deg of inland: {why}")
        # THE CLOSE-UPS: after facing at home (the camera's yaw survives a teleport), stand 3u short of the streak
        # tri on the same line ("near"), then ON it ("on") -- each point castable in BOTH variants' ground
        stock = [[v[0] for v in t3] for t3 in terr]

        def ground(variant):
            w = reps[variant]["windows"][name]
            drop = {frozenset(tuple(k) for k in ks) for ks in w["drop_keys"]}
            g = [(pts, decode_id(int(round(t3[0][3][0])))["topograph"]) for pts, t3 in zip(stock, terr)
                 if frozenset(CM._pk(p) for p in pts) not in drop]
            return g + [(pts, decode_id(tp)["topograph"]) for pts, tp in zip(w["emit_pts"], w["emit_topo"])]

        def castable(x, z, g_):
            for pts, tp in g_:
                (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts
                det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
                if abs(det) < 1e-9:
                    continue
                w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
                w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
                if min(w0, w1, 1.0 - w0 - w1) >= 0.08 and tp in FOOT_LEGAL:
                    return round(w0 * ay + w1 * by + (1.0 - w0 - w1) * cy, 3)
            return None
        g_old, g_new = ground("old"), ground("new")
        hx_, hz_ = best["streak"]
        x0, z0 = best["home"]
        L = math.hypot(hx_ - x0, hz_ - z0)
        for key, cands in (("near", [(x0 + (hx_ - x0) * (L - s) / L, z0 + (hz_ - z0) * (L - s) / L)
                                     for s in (3.0, 2.5, 3.5, 2.0, 4.0)]),
                           ("on", [(hx_ + dx, hz_ + dz) for dx, dz in ((0, 0), (0.2, 0), (-0.2, 0), (0, 0.2),
                                                                       (0, -0.2), (0.3, 0.3), (-0.3, -0.3))])):
            for (x, z) in cands:
                yo, yn = castable(x, z, g_old), castable(x, z, g_new)
                if yo is not None and yn is not None and abs(yo - yn) < 0.01:
                    best[key] = {"at": [round(x, 3), round(z, 3)], "ground_y": yn}
                    break
            else:
                raise SystemExit(f"{name}: no {key} point castable in both variants")
        out[name] = dict(best, cell=list(cell), verb=verb, depth=d, ratio=st[0]["ratio"])
    return out


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(*sys.argv[2:5])
        return
    pristine = export_pristine()
    reps = {}
    for variant, pkg in (("old", pristine), ("new", ROOT / "ff9mapkit")):
        lab = OUT / variant / LAB_NAME
        if lab.parent.exists():
            shutil.rmtree(lab.parent)
        lab.mkdir(parents=True)
        rj = OUT / f"{variant}.json"
        subprocess.run([sys.executable, __file__, "--child", str(pkg), str(lab), str(rj)], check=True,
                       cwd=str(OUT))
        env = OUT / "mist_off.toml"
        env.write_text("[world_environment]\nmist = false\n", encoding="utf-8")
        r = subprocess.run([sys.executable, "-m", "ff9mapkit", "world-environment", "--mod-folder", str(lab),
                            str(env)], cwd=str(ROOT / "ff9mapkit"), capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"world-environment failed: {r.stdout[-400:]} {r.stderr[-400:]}")
        reps[variant] = json.loads(rj.read_text(encoding="utf-8"))
    if reps["old"]["has_cell_clip"] or not reps["new"]["has_cell_clip"]:
        raise SystemExit("the variants did not build from the code they claim (old must predate the fix)")
    for name in reps["new"]["windows"]:
        if reps["new"]["windows"][name]["streaks"]:
            raise SystemExit(f"{name}: the NEW build still carries a streak tri")
    st = stations(reps)
    (OUT / "stations.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
    for variant in ("old", "new"):
        files = sorted(p.relative_to(OUT / variant).as_posix() for p in (OUT / variant).rglob("*") if p.is_file())
        print(f"{variant}: {len(files)} files")
        for f in files:
            print("   ", f)
    for name, s in st.items():
        print(f"{name} {s['cell']} {s['verb']} D={s['depth']}: streak {s['streak']} (ratio {s['ratio']}) "
              f"home {s['home']} y {s['ground_y']} bearing {s['bearing']} at {s['distance']}u")


if __name__ == "__main__":
    main()
