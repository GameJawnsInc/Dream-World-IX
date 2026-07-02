"""Blender round-trip for overworld block meshes -- the "mesh surgery" path.

Export a block's **Terrain** or **Object** (building) sub-mesh to a Wavefront **OBJ** (world-positioned, UVs +
normals preserved) for editing in Blender -- splice a multi-block structure into one, reshape, or model new -- then
rebuild the edited OBJ into a loose ``.ff9mesh`` override and deploy it via the s34 hook
(:func:`ff9mapkit.world.mesh.deploy_override`, ``part="Object"``).

The engine's per-triangle **IDALL** (in ``tangent.x``) does NOT ride OBJ. For **buildings it is uniform**
(``topograph 59`` = impassable), so :func:`build_from_obj` STAMPS it on build. (Per-triangle terrain IDALL is a
separate follow-up -- it needs a spatial re-derive or a face sidecar.)

Frame: block-LOCAL verts -> WORLD is ``worldX = x*64 + localX``, ``worldZ = -y*64 + localZ`` (Y up;
:func:`ff9mapkit.world.extract.block_world_origin`). The OBJ is written in WORLD coords so several blocks line up in
Blender; :func:`build_from_obj` converts back to the TARGET block's local frame. Use Blender's default OBJ axes
(Y-up) both ways so the round-trip is an identity.
"""
from __future__ import annotations

from pathlib import Path

from . import extract as W, mesh as M

_TOPO_IMPASSABLE = 59          # the stock "structure/wall" topograph (Alexandria's castle uses it): blocks on-foot


def export_obj(blocks, *, disc: int = 1, part: str = "object", lod: str = "0_1", out, game=None) -> dict:
    """Write each block in ``blocks`` (a list of ``(x, y)``) ``part`` sub-mesh to one OBJ at ``out``, in WORLD coords
    (per-block ``o`` groups; ``v``/``vt``/``vn``/``f``). ``part`` = ``"object"`` (buildings) or ``"terrain"``. Returns
    a summary. Open it in Blender, splice/reshape, export back to OBJ, then :func:`build_from_obj`."""
    out = Path(out)
    lines = [f"# ff9mapkit world-mesh export -- disc{disc} {part} lod {lod}  (WORLD coords, Y up)",
             "# edit in Blender (default OBJ axes), then: ff9mapkit world-mesh-build"]
    vbase, total_v, total_t = 0, 0, 0
    for (x, y) in blocks:
        bm = W.read_block(x, y, disc=disc, lod=lod, part=part, game=game)
        ox, oz = W.block_world_origin(x, y)
        verts, normals, uvs = bm.verts, bm.normals, bm.uvs
        lines.append(f"o Block_{x}_{y}_{part}")
        for v in verts:
            lines.append(f"v {v[0] + ox:.6f} {v[1]:.6f} {v[2] + oz:.6f}")
        for u in (uvs or []):
            lines.append(f"vt {u[0]:.6f} {u[1]:.6f}")
        for n in (normals or []):
            lines.append(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}")
        for (a, b, c) in bm.tris:
            A, B, C = a + vbase + 1, b + vbase + 1, c + vbase + 1   # OBJ 1-based, global; v==vt==vn per vertex
            if uvs and normals:
                lines.append(f"f {A}/{A}/{A} {B}/{B}/{B} {C}/{C}/{C}")
            elif uvs:
                lines.append(f"f {A}/{A} {B}/{B} {C}/{C}")
            elif normals:
                lines.append(f"f {A}//{A} {B}//{B} {C}//{C}")
            else:
                lines.append(f"f {A} {B} {C}")
        vbase += bm.vcount
        total_v += bm.vcount
        total_t += len(bm.tris)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"path": str(out), "blocks": list(blocks), "verts": total_v, "tris": total_t}


def read_obj(path) -> dict:
    """Parse a Wavefront OBJ into ``{V, VT, VN, faces}`` where ``faces`` is a list of triangles (polygons are
    fan-triangulated), each a 3-tuple of ``(v_idx, vt_idx, vn_idx)`` 1-based ints (0 = absent)."""
    V, VT, VN, faces = [], [], [], []
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == "v":
            V.append((float(t[1]), float(t[2]), float(t[3])))
        elif t[0] == "vt":
            VT.append((float(t[1]), float(t[2])))
        elif t[0] == "vn":
            VN.append((float(t[1]), float(t[2]), float(t[3])))
        elif t[0] == "f":
            corners = []
            for tok in t[1:]:
                p = (tok.split("/") + ["", ""])[:3]
                corners.append((int(p[0]), int(p[1]) if p[1] else 0, int(p[2]) if p[2] else 0))
            for k in range(1, len(corners) - 1):                   # fan-triangulate n-gons
                faces.append((corners[0], corners[k], corners[k + 1]))
    return {"V": V, "VT": VT, "VN": VN, "faces": faces}


def write_obj(obj: dict, path) -> Path:
    """Write a parsed OBJ dict (from :func:`read_obj`) back to a Wavefront OBJ. Preserves the ``v``/``vt``/``vn``
    pools verbatim and re-emits ``f`` lines with their original 1-based indices (an unreferenced vertex left by a
    face filter is harmless -- :func:`obj_to_blockmesh` only walks faces)."""
    out = ["# ff9mapkit mesh edit"]
    out += [f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}" for v in obj["V"]]
    out += [f"vt {u[0]:.6f} {u[1]:.6f}" for u in obj.get("VT", [])]
    out += [f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}" for n in obj.get("VN", [])]
    for face in obj["faces"]:
        toks = []
        for (vi, ti, ni) in face:
            s = str(vi)
            if ni:
                s += f"/{ti if ti else ''}/{ni}"
            elif ti:
                s += f"/{ti}"
            toks.append(s)
        out.append("f " + " ".join(toks))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def _face_normal_y_and_cy(V, face):
    """The unit normal's Y component + the centroid Y of a triangle ``face`` ((v,vt,vn) 1-based)."""
    import math
    p = [V[c[0] - 1] if c[0] > 0 else V[c[0]] for c in face]
    ux, uy, uz = p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2]
    wx, wy, wz = p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2]
    nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return ny / length, (p[0][1] + p[1][1] + p[2][1]) / 3.0


def trim_floor(obj: dict, *, base_height: float = 6.0, up_threshold: float = 0.5) -> dict:
    """Return a copy of ``obj`` with the LOW, UP-FACING triangles dropped -- a building's base courtyard-floor /
    ground apron, the flat faces that read as a brown "dirt" patch under the top-down overworld camera. Keeps walls
    (near-vertical), towers, and roofs (up-facing but HIGH). A face is "floor" iff its unit normal points up
    (``ny > up_threshold``) AND its centroid sits within ``base_height`` of the mesh's lowest vertex. Only ``faces``
    is filtered; verts are kept (an unreferenced vert is harmless). Adds ``dropped``/``kept`` counts to the result."""
    V = obj["V"]
    if not V:
        return {**obj, "dropped": 0, "kept": len(obj["faces"])}
    ymin = min(v[1] for v in V)
    kept = []
    for f in obj["faces"]:
        ny, cy = _face_normal_y_and_cy(V, f)
        if ny > up_threshold and cy < ymin + base_height:
            continue                                   # low + up-facing = base floor/apron -> drop
        kept.append(f)
    return {**obj, "faces": kept, "dropped": len(obj["faces"]) - len(kept), "kept": len(kept)}


def obj_to_blockmesh(obj: dict, *, into_block, disc: int = 1, part: str = "object", lod: str = "0_1",
                     topograph: int = _TOPO_IMPASSABLE):
    """Build a :class:`~ff9mapkit.world.extract.BlockMesh` (flat/unindexed, in the TARGET block's local frame) from a
    parsed OBJ. Each face corner becomes one vertex (pos/uv/normal); ``tangent.x`` is STAMPED with the IDALL
    ``encode_id(event=0, area=0, topograph=topograph)`` -- uniform, the right model for a solid building."""
    from .extract import BlockMesh, encode_id, block_world_origin
    tx, ty = into_block
    ox, oz = block_world_origin(tx, ty)
    idall = float(encode_id(event=0, area=0, topograph=topograph))
    V, VT, VN, faces = obj["V"], obj["VT"], obj["VN"], obj["faces"]

    def rez(i, arr):                                               # 1-based, negative = from end
        return (i - 1) if i > 0 else (len(arr) + i)

    verts, normals, uvs, tans, flat, tris = [], [], [], [], [], []
    vi = 0
    for face in faces:
        tri = []
        for (vidx, tidx, nidx) in face:
            p = V[rez(vidx, V)]
            verts.append([p[0] - ox, p[1], p[2] - oz])            # WORLD -> target block LOCAL
            uvs.append(list(VT[rez(tidx, VT)]) if (tidx and VT) else [0.0, 0.0])
            normals.append(list(VN[rez(nidx, VN)]) if (nidx and VN) else [0.0, 1.0, 0.0])
            tans.append([idall, 0.0, 0.0, 1.0])
            tri.append(vi); flat.append(vi); vi += 1
        tris.append(tri)
    chan = {W.CH_POS: verts, W.CH_NRM: normals, W.CH_UV: uvs, W.CH_TAN: tans}
    channels = {W.CH_POS: (0, 3), W.CH_NRM: (12, 3), W.CH_UV: (24, 2), W.CH_TAN: (32, 4)}
    return BlockMesh(name=f"Block[{tx}][{ty}] {part.capitalize()}", disc=disc, x=tx, y=ty, lod=lod, vcount=vi,
                     stride=48, channels=channels, chan_arrays=chan, flat_index=flat, tris=tris,
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def build_from_obj(obj_path, *, into_block, mod_folder: str, disc: int = 1, part: str = "object", lod: str = "0_1",
                   topograph: int = _TOPO_IMPASSABLE, at=None, seat: bool = False, keep_block: bool = False,
                   solid_base: bool = False, texture: bool = False, tile=None, stock_bm=None, terrain_bm=None,
                   game=None) -> dict:
    """Read an edited OBJ, rebuild it as the TARGET block's ``part`` ``.ff9mesh``, and deploy the loose override.
    ``into_block=(x, y)`` picks the block whose local frame + override path the result is written into.

    Placement (so you can MODEL AT THE ORIGIN in Blender and drop it where you want): ``at=(worldX, worldZ)`` shifts
    the mesh so its XZ centroid lands at that world spot; ``seat=True`` then drops it so its lowest point rests on the
    terrain surface there (samples the block's Terrain mesh). Omit both to treat the OBJ as already world-positioned
    (e.g. a `world-mesh-export` file).

    ``terrain_bm`` / ``stock_bm`` let a caller supply the seat-reference terrain and the ``keep_block`` merge base
    explicitly (e.g. an already-deployed override so a placement STACKS on a prior edit / seats on a flattened pad,
    rather than re-reading pristine p0data). Both default to a fresh pristine read of ``into_block``. Returns a
    summary."""
    obj = read_obj(obj_path)
    V = obj["V"]
    if not V:
        raise ValueError("OBJ has no vertices")
    if at is not None or seat:
        xs = [v[0] for v in V]; zs = [v[2] for v in V]; ys = [v[1] for v in V]
        # anchor by the XZ BOUNDING-BOX centre, not the vertex centroid: an asymmetric/vertex-dense model (e.g. a
        # castle with detailed towers on one side) has its centroid pulled off-centre, so a centroid anchor bulges
        # the model ~15u to one side of the target cell. The bbox centre seats it symmetrically on the cell.
        cx, cz, ymin = (min(xs) + max(xs)) / 2.0, (min(zs) + max(zs)) / 2.0, min(ys)
        wx, wz = at if at is not None else (cx, cz)
        dx, dz = (wx - cx, wz - cz) if at is not None else (0.0, 0.0)
        dy = 0.0
        if seat:
            tx, ty = into_block
            ox, oz = W.block_world_origin(tx, ty)
            ter = terrain_bm if terrain_bm is not None else W.read_block(tx, ty, disc=disc, lod=lod,
                                                                         part="terrain", game=game)
            dy = M.sample_ground_y(ter, wx - ox, wz - oz) - ymin      # lowest point -> ground
        obj["V"] = [(v[0] + dx, v[1] + dy, v[2] + dz) for v in V]
    bm = obj_to_blockmesh(obj, into_block=into_block, disc=disc, part=part, lod=lod, topograph=topograph)
    if solid_base:                                                 # fill the footprint so a hollow model can't box you
        bm = M.add_solid_base(bm, topograph=topograph)
    merged_with_stock = False
    if keep_block:                                                  # keep the block's stock structures (e.g. a town)
        try:
            stock = stock_bm
            if stock is None:
                stock = W.read_block(into_block[0], into_block[1], disc=disc, lod=lod, part=part, game=game)
            bm = M.place_building(stock, bm, translate=(0.0, 0.0, 0.0))   # append the new mesh onto the stock
            merged_with_stock = True
        except (ValueError, FileNotFoundError):
            pass                                                   # no stock mesh / channel mismatch -> just the new one
    textured = 0
    if texture or tile is not None:                                # stamp real atlas tiles onto UV-less new faces
        from . import palette as PAL
        before = bm
        topo = tile[0] if tile is not None else None               # --tile TOPO:VARIANT forces one picked tile
        variant = tile[1] if tile is not None else 0
        bm = PAL.apply_palette_uvs(bm, disc=disc, part=part, topograph=topo, variant=variant, game=game)
        textured = 1 if bm is not before else 0
    dest = M.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part=part.capitalize())
    return {"dest": str(dest), "into_block": list(into_block), "verts": bm.vcount, "tris": len(bm.tris),
            "kept_stock": merged_with_stock, "textured": bool(textured)}
