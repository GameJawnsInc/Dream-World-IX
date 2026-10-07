"""CAPACITY lane, step 3 -- census of the LIVE deployed .ff9mesh overrides (READ-ONLY on the install):
per-namespace/part counts, header vcount/icount (the 65535 ceiling + the unindexed contract), and the
intersection with the 26 FORM-SWITCHABLE blocks (ff9.cs w_worldChangeBlockSet / the bundle's 0_2 dir),
where a "Terrain" override is NOT read while the block is in Form 2 (the Form-2 child is named "Terrain2",
and the s34 key is `transform.name` -- WMWorld.cs:823-825; prefab names from out/prefab_children.json).

Writes out/live_overrides.json.  Run:  py studies/terrain-malleability/capacity/live_overrides.py
"""
import json
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
PAT = re.compile(r"Disc(\d+)[/\\]0_(\d)[/\\]r(\d+)[/\\]Block\[(\d+)\]\[(\d+)\] ([A-Za-z0-9_]+)\.ff9mesh$", re.I)

# ff9.cs w_worldChangeBlockSet (stock Memoria): the 26 blocks mw_worldSetFormBit can flip to Form 2.
SWITCHABLE = {(18, 14), (17, 12), (19, 10), (19, 11), (20, 10), (20, 11), (7, 1), (8, 1), (14, 15),
              (13, 16), (13, 17), (14, 16), (14, 17), (13, 12), (14, 12), (14, 6), (21, 10), (22, 14),
              (3, 9), (9, 1), (16, 1), (13, 4), (14, 5), (0, 0), (16, 14), (9, 17)}


def main():
    folders = [p for p in GAME.iterdir() if p.is_dir() and p.name.startswith("FF9CustomMap")]
    rows = []
    for f in folders:
        for p in f.rglob("*.ff9mesh"):
            m = PAT.search(str(p))
            if not m:
                rows.append({"folder": f.name, "path": str(p), "unparsed": True})
                continue
            data = p.read_bytes()[:20]
            magic = data[:4]
            ver, vc, ic, flags = struct.unpack_from("<iiii", data, 4) if magic == b"F9WM" else (None,) * 4
            rows.append({"folder": f.name, "disc": int(m.group(1)), "dir": "0_" + m.group(2),
                         "x": int(m.group(4)), "y": int(m.group(5)), "part": m.group(6),
                         "vcount": vc, "icount": ic, "flags": flags, "bytes": p.stat().st_size})
    parsed = [r for r in rows if not r.get("unparsed")]
    by_ns = Counter((r["folder"], r["disc"], r["dir"]) for r in parsed)
    by_part = Counter(r["part"] for r in parsed)
    vmax = max(parsed, key=lambda r: r["vcount"] or 0) if parsed else None
    viol = [r for r in parsed if r["vcount"] != r["icount"]]
    over = [r for r in parsed if (r["vcount"] or 0) > 65535]
    sw = [r for r in parsed if r["disc"] in (1, 4) and (r["x"], r["y"]) in SWITCHABLE]
    sw_parts = Counter((r["disc"], r["x"], r["y"], r["part"]) for r in sw)
    form2_overrides = [r for r in parsed if r["part"].lower() in ("terrain2", "object2")]
    res = {"n_files": len(rows), "unparsed": [r for r in rows if r.get("unparsed")][:20],
           "by_namespace": {f"{a}|Disc{b}|{c}": n for (a, b, c), n in sorted(by_ns.items())},
           "by_part": dict(by_part.most_common()),
           "vcount_max": vmax, "unindexed_violations": viol[:20], "over_65535": over,
           "on_switchable_blocks": sorted(f"disc{d} ({x},{y}) {p}" for (d, x, y, p) in sw_parts),
           "form2_named_overrides": form2_overrides,
           "vcount_hist_terrain": _hist([r["vcount"] for r in parsed if r["part"].lower() == "terrain"])}
    (OUT / "live_overrides.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k in ("n_files", "by_namespace", "by_part", "vcount_max", "unindexed_violations", "over_65535",
              "on_switchable_blocks", "form2_named_overrides", "vcount_hist_terrain"):
        print(k, "=", res[k])


def _hist(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return {}
    q = lambda f: vals[min(len(vals) - 1, int(f * (len(vals) - 1) + 0.5))]
    return {"n": len(vals), "min": vals[0], "median": q(0.5), "p99": q(0.99), "max": vals[-1]}


if __name__ == "__main__":
    main()
