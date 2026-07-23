"""ef_geom_writer -- a NATIVE-GROUNDED *writer* for FF9's summon/eff GEOM block (the id-5 model image).

Companion to ``ef_container.py`` (the reader). This module PARSES a GEOM block into a fully-typed
``GeomModel`` and RE-EMITS it. The acceptance test is **byte-identity round-trip** against stock model
images: parse -> serialize -> ``out == original``. That is the format's own checksum for a writer -- if a
single field, pointer, alignment pad, or pool value were misunderstood, the bytes would diverge.

Committable: pure format code. It reads a caller-supplied blob and emits offsets/bytes for a
caller-supplied model. It NEVER embeds or writes game bytes into the repo. The round-trip harness reads
the user's own locally-extracted ``C:/gd/SCRATCH/summon-format/`` corpus and prints only MATCH/counts.

Provenance of every rule: the disassembly of the user's own ``FF9SpecialEffectPlugin.dll`` as recorded in
``M4-mesh-payload.md`` / ``D3-container-validate.md`` and re-validated in ``ef_container.py``.

THE WRITABILITY MODEL (what is typed vs carried):
  * TYPED (regenerated from semantic values): every header field, the bone-link table, every mesh
    descriptor's 8 bucket counts + otBias + the FIVE sub-block pointers (RECOMPUTED from layout), the
    vertsPerBone runs, the vertex pool (s16 x,y,z,w), the UV pool (u16), the colour pool (u32), and every
    DECODED primitive field (vertex idx, uv idx, colour idx, inline rgb, part, flag).
  * CARRIED VERBATIM (genuinely opaque, per the M4/D3 "opaque ledger"): geom+0x04, geom+0x08, listHead
    (+0x14), MeshDesc+0x00 (unknown0), and the per-record "junk" bytes M4 could not attribute. These are a
    short, NAMED list; carrying them is the roadmap's explicit W1/W5 guidance, not a gap in the writer.

LAYOUT: sub-blocks are 4-BYTE ALIGNED, in the fixed per-mesh order
``vertsPerBone -> positions -> primitives -> uv -> colors``; the whole run of meshes is laid out in
mesh-table order (the stock creatures store table order == layout order). The block ends at the header's
``firstBlock`` (== the last colour pool's 4-aligned end).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import ef_container as efc
from ef_container import PRIM_TYPES, PRIM_FIELDS, Geom, Mesh


def _a4(v: int) -> int:
    return (v + 3) & ~3


# --------------------------------------------------------------------------- typed primitive
@dataclass
class Prim:
    """One face. ``fields`` holds every DECODED field by name (v, uv, col, rgb, part, flg). ``raw`` is the
    record's full ``stride`` bytes as read; re-emission overwrites the decoded fields into ``raw`` so the
    genuinely-unattributed "junk" bytes are preserved bit-exact. For a NOVEL face pass ``raw=zeros`` and set
    the decoded fields -- the junk defaults to 0 (inert: no builder in fn 0x56c0 reads it)."""
    type_index: int
    fields: Dict[str, object]
    raw: bytes

    @property
    def name(self) -> str:
        return PRIM_TYPES[self.type_index][0]


@dataclass
class MeshModel:
    unknown0: int                     # MeshDesc+0x00 -- carried verbatim
    ot_bias: int                      # MeshDesc+0x13 (signed)
    verts_per_bone: List[int]         # u16[boneCount]
    vertices: List[tuple]             # (x,y,z,w) s16 quads
    prims: List[Prim]                 # every face, in the fixed 8-bucket emission order
    colors: List[int]                 # u32 colour pool (empty for FT4/FT3-only creatures)
    uv: List[int]                     # u16 uv pool

    @property
    def counts(self) -> List[int]:
        c = [0] * 8
        for p in self.prims:
            c[p.type_index] += 1
        return c


@dataclass
class GeomModel:
    flags: int
    zero1: int
    bone_count: int
    unknown_a: int                    # geom+0x04 -- carried
    unknown_b: int                    # geom+0x08 -- carried
    list_head: int                    # geom+0x14 -- carried
    bones: List[tuple]                # (len, zero, parent) per BoneLink, len == boneCount-1
    meshes: List[MeshModel]
    mesh_layout_order: List[int]      # indices into meshes, giving on-disk pool order (usually 0,1,..)


# --------------------------------------------------------------------------- parse -> GeomModel
def model_from_geom(blob: bytes, g: Geom) -> GeomModel:
    """Lift a parsed ``Geom`` (from ``ef_container``) into the fully-typed writer model, capturing the
    opaque header fields, each primitive's raw bytes, and the observed pool layout order."""
    meshes: List[MeshModel] = []
    for m in g.meshes:
        verts = list(efc.vertices(blob, g, m))
        # UV pool: u16 * uv_count
        uv = [struct.unpack_from("<H", blob, g.base + m.p_uv + 2 * i)[0] for i in range(m.uv_count)]
        # colour pool: u32 * col_count (col_count resolved by chain closure)
        ncol = m.col_count or 0
        colors = [struct.unpack_from("<I", blob, g.base + m.p_colors + 4 * i)[0] for i in range(ncol)]
        prims: List[Prim] = []
        off = g.base + m.p_primitives
        for k, (name, code, stride, cnt_off, nv, nuv, ncolf, has_rgb) in enumerate(PRIM_TYPES):
            f = PRIM_FIELDS[name]
            for _ in range(m.counts[k]):
                raw = blob[off:off + stride]
                fields: Dict[str, object] = {
                    "v": [struct.unpack_from("<H", raw, o)[0] for o in f["v"]],
                    "flg": raw[f["flg"]],
                }
                if "uv" in f:
                    fields["uv"] = [struct.unpack_from("<H", raw, o)[0] for o in f["uv"]]
                if "col" in f:
                    fields["col"] = [struct.unpack_from("<H", raw, o)[0] for o in f["col"]]
                if "rgb" in f:
                    fields["rgb"] = tuple(raw[f["rgb"] + i] for i in range(3))
                if "part" in f:
                    fields["part"] = raw[f["part"]]
                prims.append(Prim(k, fields, raw))
                off += stride
        meshes.append(MeshModel(m.unknown0, m.ot_bias, list(m.verts_per_bone),
                                verts, prims, colors, uv))
    bones = [(b.length, b.zero, b.parent) for b in g.bones]
    # observed layout order = meshes sorted by their vertsPerBone pointer
    order = sorted(range(len(g.meshes)), key=lambda i: g.meshes[i].p_verts_per_bone)
    return GeomModel(g.flags, g.zero1, g.bone_count, g.unknown_a, g.unknown_b, g.list_head,
                     bones, meshes, order)


# --------------------------------------------------------------------------- emit a primitive record
def _emit_prim(p: Prim) -> bytes:
    """Rebuild a face record: start from the carried ``raw`` (or zeros for a novel face) and overwrite every
    DECODED field. Identity on round-trip proves every non-junk byte is located; on a novel face the junk is
    inert 0."""
    name, code, stride, cnt_off, nv, nuv, ncolf, has_rgb = PRIM_TYPES[p.type_index]
    f = PRIM_FIELDS[name]
    buf = bytearray(p.raw if len(p.raw) == stride else bytes(stride))
    for o, val in zip(f["v"], p.fields["v"]):
        struct.pack_into("<H", buf, o, val)
    buf[f["flg"]] = p.fields["flg"]
    if "uv" in f and "uv" in p.fields:
        for o, val in zip(f["uv"], p.fields["uv"]):
            struct.pack_into("<H", buf, o, val)
    if "col" in f and "col" in p.fields:
        for o, val in zip(f["col"], p.fields["col"]):
            struct.pack_into("<H", buf, o, val)
    if "rgb" in f and "rgb" in p.fields:
        for i, val in enumerate(p.fields["rgb"]):
            buf[f["rgb"] + i] = val
    if "part" in f and "part" in p.fields:
        buf[f["part"]] = p.fields["part"]
    return bytes(buf)


# --------------------------------------------------------------------------- serialize a GeomModel
def serialize(model: GeomModel) -> bytes:
    """Emit an on-disk GEOM block (pre-relocation: all sub-block pointers are GEOM-relative offsets, exactly
    as fn 0x7120 expects to relocate them in place). Returns the block bytes; the block end is 4-aligned."""
    bc = model.bone_count
    mc = len(model.meshes)
    p_mesh = 0x18 + (bc - 1) * 4                       # the structural law
    # --- pass 1: lay out pools, compute each mesh's five pointers ---
    cursor = p_mesh + mc * 0x28
    ptrs: Dict[int, Dict[str, int]] = {}
    pool_bytes: List[tuple] = []                        # (offset, bytes)
    for mi in model.mesh_layout_order:
        m = model.meshes[mi]
        pd: Dict[str, int] = {}
        # vertsPerBone
        cursor = _a4(cursor); pd["vpb"] = cursor
        vpb = b"".join(struct.pack("<H", n) for n in m.verts_per_bone)
        pool_bytes.append((cursor, vpb)); cursor += len(vpb)
        # positions
        cursor = _a4(cursor); pd["pos"] = cursor
        pos = b"".join(struct.pack("<4h", *v) for v in m.vertices)
        pool_bytes.append((cursor, pos)); cursor += len(pos)
        # primitives
        cursor = _a4(cursor); pd["prim"] = cursor
        prim = b"".join(_emit_prim(p) for p in m.prims)
        pool_bytes.append((cursor, prim)); cursor += len(prim)
        # uv
        cursor = _a4(cursor); pd["uv"] = cursor
        uv = b"".join(struct.pack("<H", u) for u in m.uv)
        pool_bytes.append((cursor, uv)); cursor += len(uv)
        # colors
        cursor = _a4(cursor); pd["col"] = cursor
        col = b"".join(struct.pack("<I", c) for c in m.colors)
        pool_bytes.append((cursor, col)); cursor += len(col)
        ptrs[mi] = pd
    block_len = _a4(cursor)
    out = bytearray(block_len)
    # --- header (0x18) ---
    out[0x00] = model.flags
    out[0x01] = model.zero1
    out[0x02] = bc
    out[0x03] = mc
    struct.pack_into("<I", out, 0x04, model.unknown_a)
    struct.pack_into("<I", out, 0x08, model.unknown_b)
    struct.pack_into("<I", out, 0x0C, 0x14)            # pBoneTable, on disk always 0x14
    struct.pack_into("<I", out, 0x10, p_mesh)
    struct.pack_into("<I", out, 0x14, model.list_head)
    # --- bone links ---
    o = 0x18
    for (ln, zero, parent) in model.bones:
        struct.pack_into("<H", out, o, ln); out[o + 2] = zero; out[o + 3] = parent
        o += 4
    # --- mesh table (stride 0x28, in mesh-table order) ---
    for mi, m in enumerate(model.meshes):
        d = p_mesh + 0x28 * mi
        struct.pack_into("<H", out, d, m.unknown0)
        for k in range(8):
            struct.pack_into("<H", out, d + PRIM_TYPES[k][3], m.counts[k])
        out[d + 0x12] = 0
        struct.pack_into("<b", out, d + 0x13, m.ot_bias)
        pd = ptrs[mi]
        struct.pack_into("<I", out, d + 0x14, pd["vpb"])
        struct.pack_into("<I", out, d + 0x18, pd["pos"])
        struct.pack_into("<I", out, d + 0x1C, pd["prim"])
        struct.pack_into("<I", out, d + 0x20, pd["uv"])
        struct.pack_into("<I", out, d + 0x24, pd["col"])
    # --- pools ---
    for off, b in pool_bytes:
        out[off:off + len(b)] = b
    return bytes(out)


# --------------------------------------------------------------------------- round-trip harness
def roundtrip_geom(blob: bytes, g: Geom, block_end: int) -> Dict[str, object]:
    """Parse the GEOM block at ``g.base``, re-emit, and compare byte-for-byte against the original span
    ``blob[g.base:block_end]``."""
    original = blob[g.base:block_end]
    model = model_from_geom(blob, g)
    out = serialize(model)
    match = out == original
    diffs = []
    if not match:
        n = min(len(out), len(original))
        for i in range(n):
            if out[i] != original[i]:
                diffs.append(i)
                if len(diffs) >= 16:
                    break
    return {
        "base": g.base, "len_orig": len(original), "len_out": len(out),
        "match": match, "first_diffs": diffs,
        "bones": g.bone_count, "meshes": g.mesh_count,
        "verts": sum(len(m.vertices) for m in model.meshes),
        "faces": sum(len(m.prims) for m in model.meshes),
    }


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        blob = open(p, "rb").read()
        c = efc.parse_header(blob)
        any_pkg = False
        for ch in c.chunks:
            mp = efc.parse_model_package(blob, ch)
            if not mp:
                continue
            any_pkg = True
            g = efc.creature_geom(blob, mp)
            r = roundtrip_geom(blob, g, mp.geom_end)
            tag = "MATCH" if r["match"] else f"MISMATCH diffs@{[hex(d) for d in r['first_diffs']]}"
            print(f"{p}: creature geom @{r['base']:#x} "
                  f"bones={r['bones']} meshes={r['meshes']} verts={r['verts']} faces={r['faces']} "
                  f"len={r['len_out']:#x}/{r['len_orig']:#x} -> {tag}")
        if not any_pkg:
            print(f"{p}: no creature package")
