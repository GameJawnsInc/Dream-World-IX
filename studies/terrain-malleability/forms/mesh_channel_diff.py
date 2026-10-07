"""forms lane CENSUS 4 -- channel-level (RENDER) diff of each switchable block's form-1 vs form-2 sub-meshes, and
the cross-disc question "is disc 4's form 2 just disc 1's form 2?".

diff_forms.py measures the WALK surface (up-facing first-hit). A form change can also be render-only: vertical
walls (n.y <= 0.1, never walked), UV/atlas swaps (a "destroyed" texture on the same geometry) or a moved object.
Here every part is compared as a multiset of per-triangle records at three strengths:
   geo  = sorted 3 corner positions (3 dp)
   uv   = geo + the 3 corner UVs (4 dp)
   full = uv + IDALL (tangent.x of corner 0)
so "geo equal but uv differs" == a pure texture swap, etc.  Also counts vertical (n.y<=0.1) triangles.
CALIBRATION: a part compared with itself must be equal at every strength; a copy with ONE uv nudged must differ
at uv/full and not at geo.  Output out/mesh_channel_diff.json.  Rerun:  py mesh_channel_diff.py
"""
import sys, json, re, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X

HERE = Path(__file__).parent
CENSUS = json.loads((HERE / "out" / "prefab_census.json").read_text())
PAIRS = [("TerrainForm1", "TerrainForm2"), ("ObjectForm1", "ObjectForm2"), ("VolcanoCrater1", "VolcanoCrater2"),
         ("VolcanoLava1", "VolcanoLava2"), ("Sea3", "Sea3_2"), ("Sea4", "Sea4_2"), ("Sea5", "Sea5_2")]


def parse(mesh_path):
    m = re.match(r"worldmap/disc(\d)/(0_\d)/r(\d+)/block\[(\d+)\]\[(\d+)\] (\w+)\.asset", mesh_path)
    return int(m.group(1)), m.group(2), int(m.group(4)), int(m.group(5)), m.group(6)


_c = {}


def recs(mesh_path):
    if mesh_path in _c:
        return _c[mesh_path]
    d, lod, x, y, part = parse(mesh_path)
    bm = X.read_block(x, y, disc=d, lod=lod, part=part)
    V = bm.verts
    UV = bm.uvs or [[0.0, 0.0]] * len(V)
    TA = bm.tangents or [[0.0] * 4] * len(V)
    out = {"geo": collections.Counter(), "uv": collections.Counter(), "full": collections.Counter(),
           "ntri": len(bm.tris), "vertical": 0, "y": [min(v[1] for v in V), max(v[1] for v in V)] if V else [0, 0]}
    for t in bm.tris:
        corners = sorted((tuple(round(c, 3) for c in V[k]), tuple(round(c, 4) for c in UV[k])) for k in t)
        g = tuple(c[0] for c in corners)
        u = tuple(corners)
        out["geo"][g] += 1
        out["uv"][u] += 1
        out["full"][(u, int(TA[t[0]][0]))] += 1
        a, b, c = (np.array(V[k]) for k in t)
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln == 0 or n[1] / ln <= 0.1:
            out["vertical"] += 1
    _c[mesh_path] = out
    return out


def cmp(ra, rb):
    o = {}
    for k in ("geo", "uv", "full"):
        o[k + "_equal"] = ra[k] == rb[k]
        o[k + "_only_a"] = int(sum((ra[k] - rb[k]).values()))
        o[k + "_only_b"] = int(sum((rb[k] - ra[k]).values()))
    return o


def calibrate():
    row = [r for r in CENSUS["1"] if (r["x"], r["y"]) == (20, 10)][0]
    p = row["slots"]["ObjectForm1"]["mesh"]
    r = recs(p)
    c0 = cmp(r, r)
    assert c0["geo_equal"] and c0["uv_equal"] and c0["full_equal"], c0
    # nudge one uv record: take one uv key, re-key it with a shifted uv
    r2 = {k: collections.Counter(v) if isinstance(v, collections.Counter) else v for k, v in r.items()}
    key = next(iter(r2["uv"]))
    r2["uv"][key] -= 1
    r2["uv"][tuple((g, (uv[0] + 0.25, uv[1])) for g, uv in key)] += 1
    fk = next(k for k in r2["full"] if k[0] == key)
    r2["full"][fk] -= 1
    r2["full"][(tuple((g, (uv[0] + 0.25, uv[1])) for g, uv in key), fk[1])] += 1
    r2 = {k: (+v if isinstance(v, collections.Counter) else v) for k, v in r2.items()}
    c1 = cmp(r, r2)
    assert c1["geo_equal"] and not c1["uv_equal"] and not c1["full_equal"], c1
    print("CALIBRATION OK: self equal at geo/uv/full; one-uv nudge -> geo equal, uv+full differ")


def main():
    calibrate()
    out = {"form": {}, "cross_disc": {}}
    for d in ("1", "4"):
        out["form"][d] = {}
        print(f"\n=== disc {d}: form1 vs form2, per part (only_f1/only_f2 at geo | uv | full; vertical tris f1/f2) ===")
        for r in sorted((r for r in CENSUS[d] if r["IsSwitchable"]), key=lambda r: r["Number"]):
            s = r["slots"]
            line, rec = [], {}
            for a, b in PAIRS:
                if a.startswith("Sea") and r["Number"] != 219:
                    continue          # SeaN is SHARED (form1+form2) on every block but 219 (WMWorld.cs:778-807)
                if a not in s and b not in s:
                    continue
                ra = recs(s[a]["mesh"]) if a in s else None
                rb = recs(s[b]["mesh"]) if b in s else None
                if ra is None or rb is None:
                    rec[a + "|" + b] = {"present": [a in s, b in s], "ntri": [ra["ntri"] if ra else 0, rb["ntri"] if rb else 0]}
                    line.append(f"{a[:-1] if a.endswith('1') else a}: {'ADDED' if ra is None else 'REMOVED'}({(rb or ra)['ntri']})")
                    continue
                c = cmp(ra, rb)
                c.update(ntri=[ra["ntri"], rb["ntri"]], vertical=[ra["vertical"], rb["vertical"]], y_f1=ra["y"], y_f2=rb["y"])
                rec[a + "|" + b] = c
                tag = "SAME" if c["full_equal"] else ("UV/ID-only" if c["geo_equal"] else "GEO")
                line.append(f"{a.replace('Form1', '')}: {tag} {c['geo_only_a']}/{c['geo_only_b']}|{c['uv_only_a']}/{c['uv_only_b']}|"
                            f"{c['full_only_a']}/{c['full_only_b']} v{ra['vertical']}/{rb['vertical']}")
            out["form"][d][f"{r['x']},{r['y']}"] = rec
            print(f"  {str((r['x'], r['y'])):>8} {r['Number']:>4}  " + " ; ".join(line))
    # cross-disc: is disc4 form-N == disc1 form-N ?
    print("\n=== cross-disc: disc1 vs disc4, same slot (SAME = full-record equal) ===")
    c1 = {(r["x"], r["y"]): r for r in CENSUS["1"] if r["IsSwitchable"]}
    c4 = {(r["x"], r["y"]): r for r in CENSUS["4"] if r["IsSwitchable"]}
    tally = collections.Counter()
    for cell in sorted(c1, key=lambda c: c1[c]["Number"]):
        r1, r4 = c1[cell], c4[cell]
        line, rec = [], {}
        for slot in ("TerrainForm1", "TerrainForm2", "ObjectForm1", "ObjectForm2"):
            if slot not in r1["slots"] or slot not in r4["slots"]:
                line.append(f"{slot}: n/a({slot in r1['slots']},{slot in r4['slots']})")
                continue
            c = cmp(recs(r1["slots"][slot]["mesh"]), recs(r4["slots"][slot]["mesh"]))
            rec[slot] = c
            same = c["full_equal"]
            tally[(slot, same)] += 1
            line.append(f"{slot}: {'SAME' if same else 'diff'}")
        out["cross_disc"][f"{cell[0]},{cell[1]}"] = rec
        print(f"  {str(cell):>8}  " + " ; ".join(line))
    print("tally (slot, disc1==disc4):", dict(tally))
    (HERE / "out" / "mesh_channel_diff.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", HERE / "out" / "mesh_channel_diff.json")


if __name__ == "__main__":
    main()
