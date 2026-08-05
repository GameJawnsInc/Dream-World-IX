"""world-readback: GROUND TRUTH from the engine's own mesh dump (audit rec 10 step 3).

The s22 debug menu ships a block dumper (~ -> World -> Dump: writes ``ff9mk_dumps/
block_<x>_<y>/`` next to the game data) that records what the RUNTIME actually built --
every child mesh in local coords, the walkmeshes the movement Raycast reads, and the
material/shader/texture actually bound. It shipped with ZERO consumers: every offline gate
scored the kit's INTENT while the one instrument measuring the engine went unread. This
module is the reader. Human-in-the-loop by design (the game must be running and the block
loaded; the owner presses Dump), exactly like ``tools/game_snap.ps1`` -- it can never be a
build step.

What it answers, per part:
* did the engine build OUR bytes? (vert-for-vert at float32 width -- the dump's ``R``
  format round-trips float32 exactly, so equality is byte-equality after a float32 pack)
* does the Form1 walkmesh the Raycast reads match a render child, and whose IDALL does it
  carry? (the ``# tan i x y z w`` trailer lines; tangent.x is the per-tri idall)
* which material/shader/texture is actually bound -- the empirical answer the
  EFFECTIVE-PREFAB and DIVERT-ARM laws were guessing at from offline models.

Only DEPLOYED overrides are compared (a stock-backed child reports "stock -- no override
to compare"): the verb verifies OUR deploys against engine actuals, not stock against
itself.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

from .. import config
from . import mesh as M
from .extract import CH_POS, CH_TAN

_DIR_RE = re.compile(r"block_(\d+)_(\d+)$")
_CHILD_RE = re.compile(r"^child\[(\d+)\] '([^']*)'\s+activeInHierarchy=(\w+)\s+rendererEnabled=(\w+)")
_MAT_RE = re.compile(r"^\s+material=(.*?)\s+shader=(.*?)\s+tex=(.*)$")
_OBJ_RE = re.compile(r"^(\d\d)_(.+)\.obj$")
_WALK_RE = re.compile(r"^walk_form(\d+)_(\d\d)\.obj$")


def _f32(x: float) -> bytes:
    return struct.pack("<f", x)


def parse_dump_obj(path) -> dict:
    """One dump OBJ -> ``{"verts": [(x,y,z)...], "tris": [(a,b,c)...] 0-based,
    "tan": {vert_index: (x,y,z,w)}}``. The dump's floats are C# ``ToString("R")`` --
    they round-trip float32, so verts are kept as parsed (compare via :func:`_f32`)."""
    verts, tris, tan = [], [], {}
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == "v":
            verts.append((float(t[1]), float(t[2]), float(t[3])))
        elif t[0] == "f":
            idx = [int(p.split("/")[0]) - 1 for p in t[1:4]]
            tris.append(tuple(idx))
        elif t[0] == "#" and len(t) >= 7 and t[1] == "tan":
            tan[int(t[2])] = (float(t[3]), float(t[4]), float(t[5]), float(t[6]))
    return {"verts": verts, "tris": tris, "tan": tan}


def parse_manifest(text: str) -> dict:
    """manifest.txt -> ``{"header": [first two lines], "children": [{n, name, active,
    renderer, material, shader, tex}...]}``."""
    lines = text.splitlines()
    children = []
    for i, ln in enumerate(lines):
        m = _CHILD_RE.match(ln)
        if m:
            child = {"n": int(m.group(1)), "name": m.group(2),
                     "active": m.group(3) == "True", "renderer": m.group(4),
                     "material": None, "shader": None, "tex": None}
            if i + 1 < len(lines):
                mm = _MAT_RE.match(lines[i + 1])
                if mm:
                    child["material"], child["shader"], child["tex"] = \
                        (mm.group(1), mm.group(2), mm.group(3))
            children.append(child)
    return {"header": lines[:2], "children": children}


def _mesh_verts_f32(bm) -> list:
    return [(_f32(v[0]), _f32(v[1]), _f32(v[2])) for v in bm.chan_arrays[CH_POS]]


def _obj_verts_f32(dump) -> list:
    return [(_f32(x), _f32(y), _f32(z)) for (x, y, z) in dump["verts"]]


def _compare(dump, bm) -> dict:
    """Engine-actual OBJ vs a deployed BlockMesh: vert-for-vert at float32 width, plus the
    walk-relevant IDALL set from the tan trailer vs the deployed tangent channel."""
    ev, dv = _obj_verts_f32(dump), _mesh_verts_f32(bm)
    out = {"engine_verts": len(ev), "deployed_verts": len(dv), "match": False,
           "first_mismatch": None}
    if len(ev) != len(dv):
        return out
    for i, (a, b) in enumerate(zip(ev, dv)):
        if a != b:
            out["first_mismatch"] = {"index": i, "engine": dump["verts"][i],
                                     "deployed": tuple(bm.chan_arrays[CH_POS][i])}
            return out
    out["match"] = True
    eng_id = {int(round(t[0])) for t in dump["tan"].values()} if dump["tan"] else set()
    dep_id = {int(round(t[0])) for t in bm.chan_arrays.get(CH_TAN, [])}
    out["idall_engine"], out["idall_deployed"] = sorted(eng_id), sorted(dep_id)
    out["idall_match"] = (not eng_id) or eng_id == dep_id
    return out


def readback(dump_dir, *, mod_folder: str, disc: int, lod: str = "0_1", game=None) -> dict:
    """Ingest one ``block_<x>_<y>`` dump dir and reconcile it against the deployed tree."""
    dump_dir = Path(dump_dir)
    m = _DIR_RE.search(dump_dir.name)
    if not m:
        raise ValueError(f"{dump_dir.name!r} is not a block_<x>_<y> dump dir")
    bx, by = int(m.group(1)), int(m.group(2))
    man_p = dump_dir / "manifest.txt"
    if not man_p.is_file():
        raise ValueError(f"no manifest.txt in {dump_dir} -- not an s22 dump")
    man = parse_manifest(man_p.read_text(encoding="utf-8", errors="replace"))

    mod_root = Path(config.find_game_path(game)) / mod_folder
    report = {"block": (bx, by), "disc": disc, "children": [], "walk": [],
              "materials": [{k: c[k] for k in ("name", "material", "shader", "tex",
                                               "active", "renderer")}
                            for c in man["children"]]}

    objs = {}
    for p in sorted(dump_dir.iterdir()):
        mo = _OBJ_RE.match(p.name)
        if mo:
            objs[mo.group(2)] = p

    for name, p in objs.items():
        dump = parse_dump_obj(p)
        dep = mod_root / M.override_relpath(disc, bx, by, lod, name)
        entry = {"child": name, "deployed": dep.is_file()}
        if dep.is_file():
            bm = M.blockmesh_from_ff9mesh(dep, disc=disc, x=bx, y=by, part=name.lower())
            entry.update(_compare(dump, bm))
        else:
            entry["note"] = "stock -- no deployed override to compare"
        report["children"].append(entry)

    dep_meshes = {}
    for name, p in objs.items():
        dep = mod_root / M.override_relpath(disc, bx, by, lod, name)
        if dep.is_file():
            dep_meshes[name] = M.blockmesh_from_ff9mesh(dep, disc=disc, x=bx, y=by,
                                                        part=name.lower())
    for p in sorted(dump_dir.iterdir()):
        mw = _WALK_RE.match(p.name)
        if not mw:
            continue
        dump = parse_dump_obj(p)
        wentry = {"walkmesh": p.name, "form": int(mw.group(1)), "verts": len(dump["verts"]),
                  "tris": len(dump["tris"]), "matches_child": None, "idall": sorted(
                      {int(round(t[0])) for t in dump["tan"].values()})}
        wv = _obj_verts_f32(dump)
        for name, bm in dep_meshes.items():
            if wv == _mesh_verts_f32(bm):
                wentry["matches_child"] = name
                break
        report["walk"].append(wentry)
    return report
