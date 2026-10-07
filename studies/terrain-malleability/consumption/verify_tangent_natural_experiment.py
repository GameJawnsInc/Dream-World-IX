"""VERIFY C11's natural experiment: "1337 live files carry tangent.w=1 and 48 carry y=1, and they render + walk fine".

The trap: the live stack holds 939 DEAD 1-tri blanks (bind_oracle.py). If the nonzero-tangent files are mostly dead
blanks, the "natural experiment" proves nothing about the engine reading .y/.z/.w. This script splits the nonzero
files into BOUND (the effective prefab has that child) vs DEAD, and further into bound files whose block appears in
the Memoria.log receipts (engine-confirmed loaded), using out/bind_oracle.json for the bound/dead split.

Read-only on the install. Rerun:  py studies/terrain-malleability/consumption/verify_tangent_natural_experiment.py
"""
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
FILE_RE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (.+?)\.ff9mesh$")


def tangent_flags(p):
    b = p.read_bytes()
    ver, vc, ic, fl = struct.unpack_from("<iiii", b, 4)
    if not fl & 4:
        return None
    off = 20 + vc * 12 + (vc * 12 if fl & 1 else 0) + (vc * 8 if fl & 2 else 0)
    t = struct.unpack_from(f"<{vc * 4}f", b, off)
    ys = any(t[i * 4 + 1] != 0 for i in range(vc))
    zs = any(t[i * 4 + 2] != 0 for i in range(vc))
    ws = any(t[i * 4 + 3] != 0 for i in range(vc))
    # corner-1/2 tangent.x differing from corner 0 (the other "free" claim) -- needs the index buffer
    idx = struct.unpack_from(f"<{ic}i", b, off + vc * 16)
    diff12 = any(t[idx[3 * k + 1] * 4] != t[idx[3 * k] * 4] or t[idx[3 * k + 2] * 4] != t[idx[3 * k] * 4] for k in range(ic // 3))
    return ys, zs, ws, diff12


def main():
    O = json.loads((HERE / "out" / "bind_oracle.json").read_text(encoding="utf-8"))
    logged = set()
    logp = Path(O["calibration"]["log"])
    for ln in logp.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"loaded 'WorldMap/Disc(\d+)/0_1/r\d+/Block\[(\d+)\]\[(\d+)\] ([^']+)'", ln)
        if m:
            logged.add((m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)))
    tally = Counter()
    seen = set()
    for f in O["folders"]:
        root = GAME / f / "FF9_Data" / "WorldMap"
        if not root.is_dir():
            continue
        for dd in root.iterdir():
            m = re.match(r"Disc(\d+)$", dd.name)
            if not m or not (dd / "0_1").is_dir():
                continue
            ns = m.group(1)
            for rdir in (dd / "0_1").iterdir():
                for p in rdir.iterdir():
                    fm = FILE_RE.match(p.name)
                    if not fm:
                        continue
                    x, y, part = int(fm.group(1)), int(fm.group(2)), fm.group(3)
                    if (ns, x, y, part) in seen:
                        continue                                   # shadowed by a higher-priority folder
                    seen.add((ns, x, y, part))
                    tf = tangent_flags(p)
                    if tf is None:
                        tally["no-tangent-array"] += 1
                        continue
                    ys, zs, ws, d12 = tf
                    cell = O["cells"].get(f"{ns}:{x},{y}", {})
                    state = "bound" if part in cell.get("bound", []) else "dead"
                    if state == "bound" and (ns, x, y, part) in logged:
                        state = "bound+logged"
                    for nm, flag in (("y", ys), ("z", zs), ("w", ws), ("x12", d12)):
                        if flag:
                            tally[f"{nm}!=0 [{state}]"] += 1
                    if ys or zs or ws:
                        tally[f"any yzw!=0 [{state}]"] += 1
                    tally[f"files [{state}]"] += 1
    for k in sorted(tally):
        print(f"  {k:<28} {tally[k]}")
    (HERE / "out" / "verify_tangent_natural_experiment.json").write_text(json.dumps(dict(tally), indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
