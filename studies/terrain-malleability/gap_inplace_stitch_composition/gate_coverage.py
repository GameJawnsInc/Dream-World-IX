"""METHOD D (static half) -- which safety gates does each IN-PLACE writer's code reach? Cross-checks the dynamic
sys.setprofile trace in composition_probe.py (out/composition_probe.json) against an AST walk of the source.

For each writer function, collect every called name reachable through same-package calls up to depth 3
(`ff9mapkit/ff9mapkit/world/*.py` + `cli.py`; attribute calls `M.x`, `TR.x`, `DM.x` resolved by name), then
intersect with the gate-name sets. Control: transplant.transplant must reach weld_audit, _tjunc_gate, census and
_mod_overwrite_gate (it does at runtime -- the dynamic control); island.landmass must reach the island gates.
Writes out/gate_coverage.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/gate_coverage.py
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402

PKG = Path(r"C:\gd\Dream-World-IX\ff9mapkit\ff9mapkit")
FILES = sorted((PKG / "world").glob("*.py")) + [PKG / "cli.py"]
GATES = {
    "MOD-OVERWRITE": {"mod_overwrite_gate", "_mod_overwrite_gate", "existing_overrides"},
    "MOD-OVERWRITE (warn row, --fresh only)": {"fresh_discard_note"},
    "weld_audit": {"weld_audit"},
    "T-junction": {"_tjunc_gate"},
    "placement census": {"census"},
    "entrance guard": {"block_mapids"},          # world-deploy's inline refusal reads the block's event mapids
    "auto_mirror": {"auto_mirror"},
    "one-way-wall": {"_walk_gate"},
    "in-place-frame": {"_frame_set"},
    "stacked read": {"read_block_stacked", "blockmesh_from_ff9mesh", "read_deployed_blocks"},
}
WRITERS = {
    "world-terrain (terrain.reshape)": ("world/terrain.py", "reshape"),
    "world-deploy (cli._cmd_world_deploy)": ("cli.py", "_cmd_world_deploy"),
    "world-retarget (cli._cmd_world_retarget)": ("cli.py", "_cmd_world_retarget"),
    "world-transplant --in-place (transplant.morph_in_place)": ("world/transplant.py", "morph_in_place"),
    "world-entrance (entrance.author_entrance)": ("world/entrance.py", "author_entrance"),
    "CONTROL world-transplant (transplant.transplant)": ("world/transplant.py", "transplant"),
    "CONTROL world-island (island.landmass)": ("world/island.py", "landmass"),
}

defs = {}                                              # name -> [(file, FunctionDef)]
for f in FILES:
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(node.name, []).append((str(f.relative_to(PKG)).replace("\\", "/"), node))


def called(fn):
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                out.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                out.add(n.func.attr)
        # nested defs (closures) are walked too by ast.walk -- they count as reachable
    return out


def reach(file, name, depth=3):
    roots = [fn for (f, fn) in defs.get(name, []) if f == file]
    assert roots, (file, name)
    seen, frontier = set(), set(called(roots[0]))
    allc = set(frontier)
    for _ in range(depth - 1):
        nxt = set()
        for c in frontier:
            if c in seen or c not in defs:
                continue
            seen.add(c)
            for (_f, fn) in defs[c]:
                nxt |= called(fn)
        allc |= nxt
        frontier = nxt
    return allc


res = {}
for label, (file, name) in WRITERS.items():
    r = reach(file, name)
    res[label] = {g: sorted(r & names) for g, names in GATES.items() if r & names}
    print(f"{label:58s} {sorted(res[label])}")
dyn = json.loads((S.OUT / "composition_probe.json").read_text(encoding="utf-8"))
res["_dynamic_note"] = ("cross-check against composition_probe.json traces: static reach is an UPPER bound "
                        "(a reachable call may be gated off at runtime, e.g. fresh_discard_note only under fresh=True)")
p = S.save_json("gate_coverage.json", res)
print("->", p)
