"""``summons.build`` -- the Model-struct adapter (a decoded summon ``Geom`` + motion clips -> the kit's own
Model/clip dict shapes, TRANSPLANT.md section 3.3).

Two lanes (the suite's game-gated pattern, cf. test_summons_container.py / test_summons_motion.py):
  * OFFLINE (always runs) -- a hand-built, byte-exact synthetic 3-node/1-mesh/1-face ``Geom`` (verified
    against ``container.geom_checks`` first) and a hand-built synthetic motion-clip blob (all axes
    LITERAL, no track bytes needed). Every expected number below is worked out by hand from the forward-
    kinematics formula the adapter documents, not just shape-checked.
  * GAME-GATED -- the full real-bytes adapt of Bahamut (``ef227.bytes``, 93 bones / 2 meshes / 1439 verts
    / 8 clips), cross-checked against the frame counts + node-0 signature already proven in
    test_summons_motion.py. Skips cleanly when the local ``C:/gd/SCRATCH/summon-format/`` blob is absent.
"""
from __future__ import annotations

import math
import os
import struct

import pytest

from ff9mapkit.summons import build as B
from ff9mapkit.summons import container as C
from ff9mapkit.summons import motion as M

_SCRATCH = r"C:/gd/SCRATCH/summon-format"


def _ef(effid: int) -> str:
    return os.path.join(_SCRATCH, f"ef{effid:03d}.bytes")


def _have(effid: int) -> bool:
    return os.path.exists(_ef(effid))


def _blob(effid: int) -> bytes:
    with open(_ef(effid), "rb") as fh:
        return fh.read()


def _approx(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


# ------------------------------------------------------------------ OFFLINE: a byte-exact synthetic Geom
# A hand-built 3-node skeleton (node0 root; node1 child of 0, length=100; node2 child of 1, length=50) with
# ONE mesh: a single FT3 face, vertex i rigidly owned by bone i (verts_per_bone=[1,1,1]) -- exercising
# multi-bone run-length skinning, not just a single-bone degenerate case. Offsets follow container.py's
# documented layout (FORMAT.md section 2.3) exactly; geom_checks() below is the format's own linter, so a
# layout mistake here fails LOUD rather than silently mis-adapting.
_P_MESH = 0x18 + 2 * 4          # 0x20 -- bonelink rows (2 * 4B) end exactly here
_P_VPB, _P_POS, _P_PRIM, _P_UV, _P_COL = 0x48, 0x50, 0x68, 0x7C, 0x84


def _synthetic_geom_blob():
    header = struct.pack("<BBBB", 0, 0, 3, 1)              # flags,zero1,boneCount=3,meshCount=1
    header += struct.pack("<II", 0, 0)                     # unknown_a, unknown_b
    header += struct.pack("<I", 0x14)                       # p_bone_table (the structural law's value)
    header += struct.pack("<I", _P_MESH)                    # p_mesh_table
    header += struct.pack("<I", 0)                          # list_head (not an invariant)
    assert len(header) == 0x18
    bonelink = struct.pack("<HBB", 100, 0, 0)               # node1: length=100, parent=bone0
    bonelink += struct.pack("<HBB", 50, 0, 1)               # node2: length=50, parent=bone1

    counts = [0, 1, 0, 0, 0, 0, 0, 0]                        # ONE FT3 face (PRIM_TYPES order)
    meshdesc = struct.pack("<H", 0)
    for c in counts:
        meshdesc += struct.pack("<H", c)
    meshdesc += struct.pack("<Bb", 0, 0)                    # zero, ot_bias
    meshdesc += struct.pack("<IIIII", _P_VPB, _P_POS, _P_PRIM, _P_UV, _P_COL)
    assert len(meshdesc) == 0x28

    vpb = struct.pack("<HHH", 1, 1, 1)                       # each bone owns exactly 1 vertex
    positions = struct.pack("<4h", 100, 0, 0, 1)             # bone0-local vertex
    positions += struct.pack("<4h", 0, 50, 0, 1)             # bone1-local vertex
    positions += struct.pack("<4h", 0, 0, 25, 1)             # bone2-local vertex
    prim = struct.pack("<HHH", 0, 1, 2)                      # v0,v1,v2
    prim += struct.pack("<BB", 0, 0)                         # part, pad
    prim += struct.pack("<BBBB", 128, 128, 128, 0)           # rgb, pad
    prim += struct.pack("<HHH", 0, 1, 2)                     # uv0,uv1,uv2 (pool indices)
    prim += struct.pack("<BB", 0, 0)                         # flag, pad
    assert len(prim) == 0x14
    uvpool = struct.pack("<HHH", 10 | (20 << 8), 30 | (40 << 8), 50 | (60 << 8))

    blob = bytearray(_P_COL)                                 # colors pool is empty -> block ends at P_COL
    blob[0:len(header)] = header
    blob[0x18:0x18 + len(bonelink)] = bonelink
    blob[_P_MESH:_P_MESH + len(meshdesc)] = meshdesc
    blob[_P_VPB:_P_VPB + len(vpb)] = vpb
    blob[_P_POS:_P_POS + len(positions)] = positions
    blob[_P_PRIM:_P_PRIM + len(prim)] = prim
    blob[_P_UV:_P_UV + len(uvpool)] = uvpool
    return bytes(blob)


def _synthetic_geom():
    blob = _synthetic_geom_blob()
    g = C.parse_geom(blob, base=0, block_end=_P_COL)
    chk = C.geom_checks(blob, g, limit=_P_COL)
    assert all(chk[k] for k in (
        "pBoneTable_is_0x14", "pMeshTable_law", "mesh_byte0x12_zero",
        "chain_vertsPerBone_to_positions", "chain_positions_to_primitives",
        "chain_primitives_to_uv", "chain_uv_to_colors", "in_bounds")), chk
    return blob, g


def test_synthetic_geom_is_well_formed():
    blob, g = _synthetic_geom()
    assert g.bone_count == 3 and g.mesh_count == 1
    assert g.parents() == [0, 0, 1] and g.lengths() == [0, 100, 50]
    assert C.bone_of_vertex(g.meshes[0]) == [0, 1, 2]


def test_adapt_model_identity_rest_pose():
    blob, g = _synthetic_geom()
    model = B.adapt_model(blob, g, geo="TESTCREATURE", geo_id=99999)

    assert model["geo"] == "TESTCREATURE" and model["geo_id"] == 99999
    assert model["root_bone"] == "bone000"
    assert [b["name"] for b in model["bones"]] == ["bone000", "bone001", "bone002"]
    assert model["bones"][0]["parent"] is None
    assert model["bones"][1]["parent"] == "bone000"
    assert model["bones"][2]["parent"] == "bone001"
    # rest local pos == (0,0,length[b]); identity rest rotation -> unit quaternion on every node
    assert model["bones"][1]["pos"] == [0.0, 0.0, 100.0]
    assert model["bones"][2]["pos"] == [0.0, 0.0, 50.0]
    for b in model["bones"]:
        assert _approx(b["rot"], (0.0, 0.0, 0.0, 1.0))
        assert b["scale"] == [1.0, 1.0, 1.0]

    assert len(model["meshes"]) == 1
    mesh = model["meshes"][0]
    assert mesh["weights"] == [[(0, 1.0)], [(1, 1.0)], [(2, 1.0)]]          # one bone per vertex, rigid
    assert mesh["submeshes"][0]["tris"] == [[0, 1, 2]]                      # one FT3 -> one triangle
    assert mesh["normals"] is None
    # bind-pose verts = W[b]*pool_vertex; identity rest -> W[b] = pure translation by chain length
    assert _approx(mesh["verts"][0], [100.0, 0.0, 0.0])     # bone0 local vertex, W0 = identity
    assert _approx(mesh["verts"][1], [0.0, 50.0, 100.0])    # bone1 local vertex + t1=(0,0,100)
    assert _approx(mesh["verts"][2], [0.0, 0.0, 175.0])     # bone2 local vertex + t2=(0,0,150)
    # UV pool decode: u16 == (u | v<<8), normalized /255
    assert _approx(mesh["uvs"][0], [10 / 255.0, 20 / 255.0])
    assert _approx(mesh["uvs"][1], [30 / 255.0, 40 / 255.0])
    assert _approx(mesh["uvs"][2], [50 / 255.0, 60 / 255.0])
    assert len(model["materials"]) == 1 and model["materials"][0]["texture"] is None
    assert model["textures"] == {}


def test_adapt_model_rotated_rest_pose_exercises_forward_kinematics():
    # bone1's rest rotation = Rx(90deg) (PSX units 1024 == 90deg); bone0/bone2 stay identity. Composition
    # must be R[parent] @ local (not local @ R[parent], not a transpose) or these numbers diverge.
    blob, g = _synthetic_geom()
    model = B.adapt_model(blob, g, geo="T2", geo_id=1, rest_angles=[(0, 0, 0), (1024, 0, 0), (0, 0, 0)])
    mesh = model["meshes"][0]
    assert _approx(mesh["verts"][0], [100.0, 0.0, 0.0])      # bone0 unaffected (still identity)
    assert _approx(mesh["verts"][1], [0.0, 0.0, 150.0])      # Rx90 rotates the bone1-local vertex's Y->Z
    assert _approx(mesh["verts"][2], [0.0, -75.0, 100.0])
    # bone1's quaternion == a 90-degree rotation about X
    expect_q = (math.sin(math.pi / 4), 0.0, 0.0, math.cos(math.pi / 4))
    assert _approx(model["bones"][1]["rot"], expect_q)


# ------------------------------------------------------------------ OFFLINE: a synthetic motion clip
def _synthetic_clip_blob():
    # ALL axes LITERAL (cflags bits 0-2 set on every RotKey, root-translation flags bits 0-2 set) so no
    # per-frame track bytes are needed at all -- the smallest possible well-formed clip. fine_key_off=0 ->
    # decoded angle == coarse<<4 exactly, so an integer coarse of N*16 decodes to exactly N PSX units.
    frame_count, tx, ty, tz, flags = 2, 1000, 2000, 3000, 0b111
    rot_key_off, fine_key_off = 0x14, 0
    header = struct.pack("<HHHHHBxII", 0, frame_count, tx, ty, tz, flags, rot_key_off, fine_key_off)
    assert len(header) == 0x14
    node_axes = [(0, 0, 0), (64, 0, 0), (0, 0, 0)]           # bone1 coarse=64 -> angle 1024 (90 deg)
    rotkeys = b"".join(struct.pack("<HHHh", cx, cy, cz, 0b111) for cx, cy, cz in node_axes)
    return header + rotkeys


def test_adapt_clip_matches_gltf_animation_loop_contract():
    blob = _synthetic_clip_blob()
    clip = M.read_clip_header(blob, 0, 0)
    assert clip.frame_count == 2 and clip.rot_key_off == 0x14 and clip.fine_key_off == 0

    out = B.adapt_clip(blob, 3, clip, fps=10.0)
    assert out["name"] == "clip0" and out["sample_rate"] == 10.0
    assert set(out["bones"]) == {"bone000", "bone001", "bone002"}       # gltf.py keys clip["bones"] by path

    # only the ROOT gets a translation curve (FORMAT.md 2.4)
    assert "pos" in out["bones"]["bone000"] and len(out["bones"]["bone000"]["pos"]) == 2
    assert "pos" not in out["bones"]["bone001"]
    assert "pos" not in out["bones"]["bone002"]
    # EVERY node gets a dense rotation curve, one sample per frame, (t, (x,y,z,w))
    for name in out["bones"]:
        rot = out["bones"][name]["rot"]
        assert len(rot) == 2
        t0, q0 = rot[0]
        assert isinstance(t0, float) and len(q0) == 4

    t0, q0 = out["bones"]["bone000"]["rot"][0]
    assert t0 == 0.0 and _approx(q0, (0.0, 0.0, 0.0, 1.0))              # identity axis -> unit quaternion
    t0p, p0 = out["bones"]["bone000"]["pos"][0]
    assert p0 == (1000.0, 2000.0, 3000.0)                                # literal root translation, every frame
    t1, q1 = out["bones"]["bone001"]["rot"][1]
    assert abs(t1 - 0.1) < 1e-9                                          # frame 1 / fps 10 == 0.1s
    assert _approx(q1, (math.sin(math.pi / 4), 0.0, 0.0, math.cos(math.pi / 4)))


def test_adapt_all_clips_reads_the_model_package_table():
    # a creature package with the ONE synthetic clip above at the id-5 payload's own offset 0
    clip_bytes = _synthetic_clip_blob()
    mp = C.ModelPackage(
        tex_offset=0, motion_count=1, part_count=0, clut_rows=0, tex_bytes=0, clut_bytes=0,
        model_bytes=0, first_block=0, motion_offsets=[0], tpage=[], clut=[], v_offset=[],
        header_offset=0, tex_file_offset=0, model_file_offset=0, model_bytes_total=0)
    clips = B.adapt_all_clips(clip_bytes, mp, bone_count=3)
    assert len(clips) == 1
    assert clips[0]["name"] == "clip0"
    assert len(clips[0]["bones"]["bone000"]["rot"]) == 2


# ------------------------------------------------------------------ GAME-GATED (local stock blob)
@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_adapt_model_shape_and_invariants():
    blob = _blob(227)
    mp = C.creature_package(blob)
    g = C.creature_geom(blob, mp)
    model = B.adapt_model(blob, g, geo="BAHAMUT", geo_id=227)

    assert len(model["bones"]) == 93
    assert model["root_bone"] == "bone000" and model["bones"][0]["parent"] is None
    assert len(model["meshes"]) == 2
    assert sum(len(m["verts"]) for m in model["meshes"]) == 1439           # 797 + 642, known total

    for m in model["meshes"]:
        n = len(m["verts"])
        assert len(m["uvs"]) == n and len(m["normals"] or []) == 0
        for w in m["weights"]:                                             # rigid: exactly ONE weight
            assert len(w) == 1 and w[0][1] == 1.0 and 0 <= w[0][0] < 93
        for u, v in m["uvs"]:
            assert 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0
        for tri in m["submeshes"][0]["tris"]:
            assert all(0 <= idx < n for idx in tri)


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_adapt_all_clips_matches_known_frame_counts_and_signature():
    blob = _blob(227)
    mp = C.creature_package(blob)
    g = C.creature_geom(blob, mp)
    clips = B.adapt_all_clips(blob, mp, g.bone_count)

    assert len(clips) == 8
    # test_summons_motion.py's test_ef227_all_clips_tile_and_roundtrip already proves these frame counts
    assert [len(c["bones"]["bone000"]["rot"]) for c in clips] == [24, 30, 26, 48, 40, 68, 82, 28]
    for c in clips:
        assert set(c["bones"]) == {f"bone{k:03d}" for k in range(93)}      # matches gltf.py's by-path lookup
        for name, ch in c["bones"].items():
            assert ("pos" in ch) == (name == "bone000")                    # only the root carries translation

    # test_summons_motion.py's test_ef227_node0_signature_matches_study: clip0/node0 == literal -90deg X
    expect_q = B.mat3_to_quat(M.build_rotation(-1024, 0, 0))
    for _t, q in clips[0]["bones"]["bone000"]["rot"]:
        assert _approx(q, expect_q)


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_rest_angles_from_clip_gives_a_non_identity_rest_pose():
    blob = _blob(227)
    mp = C.creature_package(blob)
    g = C.creature_geom(blob, mp)
    clip0 = M.read_clip_header(blob, 0, mp.motion_file_offsets[0])

    identity_model = B.adapt_model(blob, g, geo="BAHAMUT", geo_id=227)
    angles0 = B.rest_angles_from_clip(blob, g.bone_count, clip0, frame=0)
    posed_model = B.adapt_model(blob, g, geo="BAHAMUT", geo_id=227, rest_angles=angles0)

    expect_q = B.mat3_to_quat(M.build_rotation(-1024, 0, 0))                # the known node0 signature
    assert _approx(posed_model["bones"][0]["rot"], expect_q)
    assert not _approx(identity_model["bones"][0]["rot"], expect_q)
