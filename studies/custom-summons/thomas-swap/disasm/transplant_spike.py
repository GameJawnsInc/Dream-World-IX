"""transplant_spike -- the D3 REAL-BYTES VALIDATION SPIKE for the summon-model transplant.

A design that hasn't touched real bytes is a hypothesis. This spike PARSES a stock creature's
geometry + skeleton + motion far enough to answer the load-bearing questions the "put our model where
the real creature renders" transplant depends on, and cross-checks the offline decode against the live
s53 BONES probe:

  1. bone count + hierarchy (parent indices), vs the ~93 the s53 BONES probe reads;
  2. skinning: is each vertex hard-bound to exactly ONE bone (run-length rigid)? vertex->bone samples;
  3. motion: decode per-frame Euler tracks for a few bones/frames, confirm sane (continuous), frame
     counts match the clip headers;
  4. sanity cross-check: do the decoded bind/pose bone positions relate to the s53 BONES AABB?

PROVENANCE (hard rule). This is COMMITTABLE format-parser code. It reads a caller-supplied LOCAL blob
(a stock ``ef###.bytes`` the user extracted from their own install, kept only under C:/gd/SCRATCH/...)
and prints COUNTS / OFFSETS / SAMPLE VALUES only. NO stock bytes are embedded here or emitted anywhere.
The geometry decode is delegated to the committable ``ef_container.py`` (native-grounded parser); this
file adds the MOTION-clip decoder (M5) and the forward-kinematics pose composition (M4/M5), both of
which are logic, not content. Cross-check against the live probe reads only the caller's own
``sfxmeshprobe.log`` (also local, not committed).

Motion format authority: ``M5-motion-payload.md`` (fn 0x7820 branch M, x64/x86 cross-checked).
Geometry authority: ``M4-mesh-payload.md`` / ``D3-container-validate.md`` (fn 0x7120 / 0x4eb0).

USAGE:
    py transplant_spike.py [EF_BYTES] [--log SFXMESHPROBE_LOG] [--clip N] [--frame F]
    (defaults: EF_BYTES = C:/gd/SCRATCH/summon-format/ef227.bytes = Bahamut__Full;
               --log = the FF9 install's sfxmeshprobe.log if present)
"""
from __future__ import annotations

import math
import struct
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import ef_container as efc

DEFAULT_EF = r"C:/gd/SCRATCH/summon-format/ef227.bytes"
DEFAULT_LOG = r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"

PSX_ONE = 4096.0            # 4096 == 2*pi (PSX fixed-point angle) and == 1.0 (fixed-point scalar)


# ======================================================================= MOTION CLIP DECODE (M5)
@dataclass
class Clip:
    """One decoded motion-clip header (M5 §2). All offsets are motion-relative BYTE offsets, exactly
    as on disk (pre-relocation)."""
    index: int
    file_off: int
    frame_count: int
    flags: int                 # bits 0..2 = "root translation axis i is a CONSTANT"
    t_raw: Tuple[int, int, int]  # per axis: constant s16 value (flag set) OR track byte-offset (clear)
    rot_key_off: int           # -> RotKey[nodeCount]  (coarse)
    fine_key_off: int          # -> RotKey[nodeCount]  (fine nibble), or 0
    max_touched: int           # highest motion-relative byte offset any decode of any frame reads


def _u16(b, o): return struct.unpack_from("<H", b, o)[0]
def _s16(b, o): return struct.unpack_from("<h", b, o)[0]
def _u32(b, o): return struct.unpack_from("<I", b, o)[0]


def read_clip_header(blob: bytes, idx: int, file_off: int) -> Clip:
    fc = _u16(blob, file_off + 2)
    tx, ty, tz = _u16(blob, file_off + 4), _u16(blob, file_off + 6), _u16(blob, file_off + 8)
    flags = blob[file_off + 0x0A]
    rko = _u32(blob, file_off + 0x0C)
    fko = _u32(blob, file_off + 0x10)
    return Clip(idx, file_off, fc, flags, (tx, ty, tz), rko, fko, max_touched=0)


def decode_root_translation(blob: bytes, clip: Clip, frame: int) -> Tuple[int, int, int, int]:
    """Root translation for one frame (M5 §2.2). Returns (tx,ty,tz,maxTouched)."""
    base = clip.file_off
    out = []
    touched = 0
    for i in range(3):
        v = clip.t_raw[i]
        if clip.flags & (1 << i):
            out.append(struct.unpack("<h", struct.pack("<H", v))[0])         # constant s16
        else:
            rel = v + frame * 2
            out.append(_s16(blob, base + rel))                                # per-frame s16 track
            touched = max(touched, rel + 2)
    return out[0], out[1], out[2], touched


def _s12(raw: int) -> int:
    """Reduce a raw (coarse<<4)|fine result to a signed 12-bit angle in [-2048, 2047] (the value
    PSX RotMatrix effectively uses: 4096 == one turn, high bits are periodic)."""
    v = raw & 0xFFF
    return v - 4096 if v >= 2048 else v


def decode_rotation(blob: bytes, clip: Clip, frame: int, node_count: int
                    ) -> Tuple[List[Tuple[int, int, int]], List[Tuple[bool, bool, bool]], int]:
    """Decode the 12-bit Euler angles for EVERY node at ``frame`` (M5 §2.3). Angles are returned RAW
    (u16 (coarse<<4)|fine); apply ``_s12``/mod-4096 for a canonical angle. Also returns, per node, a
    (isTrackX, isTrackY, isTrackZ) tuple so the caller can measure continuity over ANIMATED channels
    only (a literal channel is constant by construction).

    Per node k, per axis i:
        coarse = coarseKey[k].field[i]
        if !(coarseKey[k].flags & (1<<i)):  coarse = motion[coarse + frame]        # u8 track
        fine = 0
        if fineKeyOff:
            f = fineKey[k].field[i]
            if !(fineKey[k].flags & (1<<i)):  b = motion[f + (frame>>1)]            # nibble track
                                              f = (frame&1) ? (b>>4) : b
            fine = f & 0xF
        angle[i] = ((coarse<<4) | fine) & 0xFFFF        # interpret as s16, reduce mod 4096
    A LITERAL field stores angle/16 signed (e.g. 0xffc0 = -64 -> -1024 = -90deg); a TRACK coarse is a
    u8 (0..255) -> 0..4080 before the fine nibble. Returns (angles, isTrack, maxTouched).
    """
    base = clip.file_off
    touched = 0
    angles: List[Tuple[int, int, int]] = []
    is_track: List[Tuple[bool, bool, bool]] = []
    for k in range(node_count):
        ckey = base + clip.rot_key_off + 8 * k
        cflags = _s16(blob, ckey + 6)
        fkey = base + clip.fine_key_off + 8 * k if clip.fine_key_off else 0
        fflags = _s16(blob, fkey + 6) if fkey else 0
        axis = []
        trk = []
        for i in range(3):
            tracked = not (cflags & (1 << i))
            coarse = _u16(blob, ckey + 2 * i)          # field i (u16): literal coarse OR track offset
            if tracked:
                rel = coarse + frame
                coarse = blob[base + rel]              # u8 coarse track, 1 byte/frame
                touched = max(touched, rel + 1)
            fine = 0
            if clip.fine_key_off:
                f = _u16(blob, fkey + 2 * i)
                if not (fflags & (1 << i)):
                    rel = f + (frame >> 1)
                    bval = blob[base + rel]            # nibble track, 2 frames/byte
                    f = (bval >> 4) if (frame & 1) else bval
                    touched = max(touched, rel + 1)
                fine = f & 0xF
            axis.append(((coarse << 4) | fine) & 0xFFFF)
            trk.append(tracked)
        angles.append((axis[0], axis[1], axis[2]))
        is_track.append((trk[0], trk[1], trk[2]))
    # account for the key tables themselves in the tiling bound
    touched = max(touched, clip.rot_key_off + 8 * node_count)
    if clip.fine_key_off:
        touched = max(touched, clip.fine_key_off + 8 * node_count)
    return angles, is_track, touched


# ======================================================================= FORWARD KINEMATICS (M4/M5 §4/§5)
def _rotmat(ax: int, ay: int, az: int):
    """PSX-style Euler(3x12-bit) -> 3x3, built by three RotMatrix calls (axis order x,y,z; M5 §2.3).
    The exact psyq composition ORDER is not fully re-derived here (flagged in the findings); this
    uses R = Rz @ Ry @ Rx. Rotation ORDER affects the posed skeleton's SHAPE but NOT any root-to-leaf
    chain LENGTH, which is the rotation-invariant number the cross-check leans on."""
    def rc(a):  # angle in PSX units -> radians
        return math.cos(a / PSX_ONE * 2 * math.pi), math.sin(a / PSX_ONE * 2 * math.pi)
    cx, sx = rc(ax); cy, sy = rc(ay); cz, sz = rc(az)
    Rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    Ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    Rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    def mul(A, B):
        return tuple(tuple(sum(A[r][k] * B[k][c] for k in range(3)) for c in range(3)) for r in range(3))
    return mul(mul(Rz, Ry), Rx)


def _matvec(M, v):
    return tuple(sum(M[r][c] * v[c] for c in range(3)) for r in range(3))


def compose_skeleton(angles: List[Tuple[int, int, int]], root_t: Tuple[float, float, float],
                     lengths: List[int], parents: List[int]) -> List[Tuple[float, float, float]]:
    """World node TRANSLATIONS via the hierarchy pass (M5 §4/§5), with root R = identity, S = 1
    (the runtime .seq R_root/S/T are omitted -- see findings). node0.t = root translation;
    child.t = R[parent] @ (0,0,length) + t[parent]."""
    n = len(angles)
    R: List[tuple] = [None] * n
    t: List[Tuple[float, float, float]] = [None] * n
    R[0] = _rotmat(*angles[0])
    t[0] = (float(root_t[0]), float(root_t[1]), float(root_t[2]))
    for k in range(1, n):
        p = parents[k]
        local = _rotmat(*angles[k])
        R[k] = tuple(tuple(sum(R[p][r][j] * local[j][c] for j in range(3)) for c in range(3))
                     for r in range(3))
        off = _matvec(R[p], (0.0, 0.0, float(lengths[k])))
        t[k] = (t[p][0] + off[0], t[p][1] + off[1], t[p][2] + off[2])
    return t


def max_chain_length(lengths: List[int], parents: List[int]) -> float:
    """Rotation-INVARIANT upper bound on the skeleton's radius from node 0: the longest root->leaf
    accumulated |bone length|. Independent of Euler order / pose -- the robust magnitude datum."""
    n = len(lengths)
    acc = [0.0] * n
    for k in range(1, n):
        acc[k] = acc[parents[k]] + abs(lengths[k])
    return max(acc)


def aabb(points: List[Tuple[float, float, float]]):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]; zs = [p[2] for p in points]
    lo = (min(xs), min(ys), min(zs)); hi = (max(xs), max(ys), max(zs))
    span = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    return lo, hi, span


# ======================================================================= LIVE PROBE CROSS-CHECK
@dataclass
class BonesRow:
    frame: int
    n: int
    centroid: Tuple[int, int, int]
    lo: Tuple[int, int, int]
    hi: Tuple[int, int, int]

    @property
    def span(self):
        return (self.hi[0] - self.lo[0], self.hi[1] - self.lo[1], self.hi[2] - self.lo[2])


def read_bones_log(path: str, effect_id: int = 227) -> List[BonesRow]:
    """Parse the s53 BONES rows: BONES,effectId,frame,n,cx,cy,cz,minX,minY,minZ,maxX,maxY,maxZ."""
    rows: List[BonesRow] = []
    seen = set()
    try:
        with open(path, "r", errors="ignore") as fh:
            for line in fh:
                if not line.startswith("BONES,"):
                    continue
                p = line.strip().split(",")
                if len(p) < 13 or int(p[1]) != effect_id:
                    continue
                fr = int(p[2])
                if fr in seen:
                    continue
                seen.add(fr)
                rows.append(BonesRow(fr, int(p[3]),
                                     (int(p[4]), int(p[5]), int(p[6])),
                                     (int(p[7]), int(p[8]), int(p[9])),
                                     (int(p[10]), int(p[11]), int(p[12]))))
    except FileNotFoundError:
        return []
    rows.sort(key=lambda r: r.frame)
    return rows


# ======================================================================= THE SPIKE
def run(ef_path: str, log_path: Optional[str], want_clip: int, want_frame: int) -> dict:
    blob = open(ef_path, "rb").read()
    result: dict = {"ef_path": ef_path}
    c = efc.parse_header(blob)
    mp = None
    for ch in c.chunks:
        mp = efc.parse_model_package(blob, ch)
        if mp:
            break
    if mp is None:
        raise SystemExit(f"{ef_path}: no creature model package (id-4 + id-5 chunk)")
    g = efc.creature_geom(blob, mp)
    node_count = g.bone_count

    # ---------------- Q1: bones + hierarchy ----------------
    # BoneLink rows are nodes 1..N-1; node 0 is the implicit root. parents/lengths are 0-indexed by node.
    parents = [0] * node_count            # parents[0] unused
    lengths = [0] * node_count            # lengths[0] = 0 (root has the translation track, not a length)
    forward_ok = True
    for r, bl in enumerate(g.bones):      # r -> child node r+1
        child = r + 1
        parents[child] = bl.parent
        lengths[child] = struct.unpack("<h", struct.pack("<H", bl.length))[0]
        if not (bl.parent < child):       # a parent must have a LOWER index than its child (M5 §4)
            forward_ok = False
    middle_byte_zero = all(bl.zero == 0 for bl in g.bones)
    n_children = sum(1 for k in range(1, node_count))
    branch_points = len({parents[k] for k in range(1, node_count)})
    result["hierarchy"] = {
        "bone_count": node_count, "bonelink_rows": len(g.bones),
        "forward_referencing": forward_ok, "middle_byte_all_zero": middle_byte_zero,
        "distinct_parents": branch_points,
        "parent_sample_nodes_1_15": parents[1:16],
        "length_sample_nodes_1_15": lengths[1:16],
    }

    # ---------------- Q2: skinning (run-length rigid) ----------------
    meshes_info = []
    for m in g.meshes:
        bov = efc.bone_of_vertex(m)       # vertex index -> owning bone (run-length)
        # the D3 invariant: max vertex index used by any primitive == nVert-1
        max_vidx = -1
        for prim in efc.iter_primitives(blob, g, m):
            max_vidx = max(max_vidx, max(prim["v"]))
        nonzero_runs = sum(1 for n in m.verts_per_bone if n > 0)
        meshes_info.append({
            "n_vert": m.n_vert, "faces": m.face_count, "uv_count": m.uv_count,
            "max_vertex_index": max_vidx, "closure_ok": (max_vidx == m.n_vert - 1),
            "bones_with_verts": nonzero_runs,
            "vertex_to_bone_first10": bov[:10],
            "vertex_to_bone_at_mid": bov[len(bov) // 2: len(bov) // 2 + 6] if bov else [],
            "one_bone_per_vertex": len(bov) == m.n_vert,
        })
    result["skinning"] = {"meshes": meshes_info}

    # ---------------- Q3: motion decode ----------------
    clips = [read_clip_header(blob, i, off) for i, off in enumerate(mp.motion_file_offsets)]
    clip_reports = []
    clip_starts = sorted(cl.file_off for cl in clips)
    for cl in clips:
        # next clip start (or model-image end) bounds this clip's span
        nxt = next((s for s in clip_starts if s > cl.file_off), mp.to_file(mp.model_bytes))
        span_bytes = nxt - cl.file_off
        max_touched = 0
        node0_track = []                      # node 0's 3 angles (signed 12-bit) across frames
        probe_node = node_count // 2
        prev = None
        steps: List[int] = []                 # frame-to-frame circular steps over ANIMATED channels only
        animated_channels = 0
        for fr in range(cl.frame_count):
            angles, is_track, tch = decode_rotation(blob, cl, fr, node_count)
            _tx, _ty, _tz, tch2 = decode_root_translation(blob, cl, fr)
            max_touched = max(max_touched, tch, tch2)
            node0_track.append(tuple(_s12(a) for a in angles[0]))
            if fr == 0:
                animated_channels = sum(1 for trk in is_track for t in trk if t)
            if prev is not None:
                for k in range(node_count):
                    for i in range(3):
                        if is_track[k][i]:
                            d = (angles[k][i] - prev[k][i]) & 0xFFF
                            steps.append(min(d, 4096 - d))
            prev = angles
        steps.sort()
        p95 = steps[int(len(steps) * 0.95)] if steps else 0
        max_step = steps[-1] if steps else 0
        clip_reports.append({
            "index": cl.index, "file_off": hex(cl.file_off), "frame_count": cl.frame_count,
            "flags": cl.flags, "has_fine": cl.fine_key_off != 0,
            "span_bytes": span_bytes, "max_touched_offset": max_touched,
            "tiles_within_span": max_touched <= span_bytes,
            "animated_channels": animated_channels, "total_channels": node_count * 3,
            "track_step_p95": p95, "track_step_max": max_step,
            "continuous": p95 <= 128,                     # p95 <= ~11 deg/frame == smooth
            "node0_angles_f0..f4": node0_track[:5],
        })
    result["motion"] = {
        "clip_count": len(clips),
        "frame_counts": [cl.frame_count for cl in clips],
        "clips": clip_reports,
    }

    # ---------------- Q4: cross-check vs live BONES probe ----------------
    inv_radius = max_chain_length(lengths, parents)
    total_bone_len = sum(abs(l) for l in lengths)
    cl = clips[want_clip]
    frame = min(want_frame, cl.frame_count - 1)
    angles, _is_track, _ = decode_rotation(blob, cl, frame, node_count)
    rtx, rty, rtz, _ = decode_root_translation(blob, cl, frame)
    world = compose_skeleton(angles, (rtx, rty, rtz), lengths, parents)
    # express relative to node 0 so root translation offset doesn't dominate the extent
    rel = [(p[0] - world[0][0], p[1] - world[0][1], p[2] - world[0][2]) for p in world]
    lo, hi, span = aabb(rel)
    result["fk_pose"] = {
        "clip": want_clip, "frame": frame,
        "invariant_max_chain_length": round(inv_radius, 1),
        "total_bone_length": total_bone_len,
        "posed_span_rel_node0": tuple(round(s, 1) for s in span),
        "posed_half_diag_rel_node0": round(math.dist((0, 0, 0), span) / 2, 1),
        "note": "posed span uses an unverified Euler order; the invariant chain length does not",
    }

    bones = read_bones_log(log_path) if log_path else []
    xcheck = {"log_rows": len(bones)}
    if bones:
        ns = {b.n for b in bones}
        xcheck["live_n_values"] = sorted(ns)
        xcheck["live_n_matches_geom"] = (ns == {node_count})

        def hd(b):                                     # AABB half-diagonal (rotation+scale sensitive)
            return math.dist((0, 0, 0), b.span) / 2

        # Filter degenerate rows: scale~0 collapses the AABB to a point (half-diag ~0), and a few log
        # rows are corrupt (component >> any real world extent). Keep the physically-plausible band.
        clean = [b for b in bones if 1.0 < hd(b) < 100000.0]
        hds = sorted(hd(b) for b in clean)
        xcheck["clean_rows"] = len(clean)
        if hds:
            med = hds[len(hds) // 2]
            xcheck["live_halfdiag"] = {
                "min": round(hds[0], 1), "median": round(med, 1), "max": round(hds[-1], 1),
            }
            # posed half-diag (scale 1) should land inside the live band; invariant radius should
            # exceed the MEDIAN folded pose but the live MAX (scale ~3) can exceed it.
            posed_hd = math.dist((0, 0, 0), aabb(rel)[2]) / 2
            xcheck["posed_halfdiag_scale1"] = round(posed_hd, 1)
            xcheck["posed_within_live_band"] = hds[0] <= posed_hd <= hds[-1]
            xcheck["invariant_vs_live_median"] = {
                "invariant": round(inv_radius, 1), "live_median": round(med, 1),
                "invariant_exceeds_median": inv_radius >= med,
            }
            # nearest live frame to the posed half-diag (an at-scale-1 comparison point)
            near = min(clean, key=lambda b: abs(hd(b) - posed_hd))
            posed_span = aabb(rel)[2]
            # compare SORTED axis spans -- rotation of the world frame permutes axes but preserves the
            # sorted multiset. This is the sharpest falsifiable number: offline model-space extent vs live.
            ps = sorted(posed_span)
            ls = sorted(float(s) for s in near.span)
            ratios = [round(ps[i] / ls[i], 3) if ls[i] else None for i in range(3)]
            xcheck["nearest_live_frame"] = {"frame": near.frame, "span": near.span,
                                            "half_diag": round(hd(near), 1)}
            xcheck["sorted_axis_span_match"] = {
                "posed_sorted": [round(x, 0) for x in ps],
                "live_sorted": [round(x, 0) for x in ls],
                "posed_over_live_ratios": ratios,
            }
    result["cross_check"] = xcheck
    return result


def _fmt(result: dict) -> str:
    o = []
    o.append("=" * 78)
    o.append(f"TRANSPLANT VALIDATION SPIKE -- {result['ef_path']}")
    o.append("=" * 78)
    h = result["hierarchy"]
    o.append(f"\n[Q1] SKELETON  bones={h['bone_count']}  bonelink_rows={h['bonelink_rows']} "
             f"(node0 = implicit root)")
    o.append(f"     forward_referencing (parent<child): {h['forward_referencing']}   "
             f"middle_byte_all_zero: {h['middle_byte_all_zero']}   distinct_parents: {h['distinct_parents']}")
    o.append(f"     parent[1..15] = {h['parent_sample_nodes_1_15']}")
    o.append(f"     length[1..15] = {h['length_sample_nodes_1_15']}")
    o.append(f"\n[Q2] SKINNING (run-length rigid)")
    for i, m in enumerate(result["skinning"]["meshes"]):
        o.append(f"     mesh{i}: verts={m['n_vert']} faces={m['faces']} "
                 f"bones_with_verts={m['bones_with_verts']}  "
                 f"one_bone_per_vertex={m['one_bone_per_vertex']}  "
                 f"maxVtxIdx={m['max_vertex_index']}==nVert-1? {m['closure_ok']}")
        o.append(f"            vertex->bone [0..9]  = {m['vertex_to_bone_first10']}")
        o.append(f"            vertex->bone [mid..]  = {m['vertex_to_bone_at_mid']}")
    mo = result["motion"]
    o.append(f"\n[Q3] MOTION  clips={mo['clip_count']}  frame_counts={mo['frame_counts']}")
    for cr in mo["clips"]:
        o.append(f"     clip{cr['index']} @{cr['file_off']} frames={cr['frame_count']} "
                 f"flags={cr['flags']} fine={cr['has_fine']}  "
                 f"tiles_within_span={cr['tiles_within_span']} "
                 f"(touched {cr['max_touched_offset']:#x} <= span {cr['span_bytes']:#x})")
        o.append(f"            animated {cr['animated_channels']}/{cr['total_channels']} channels  "
                 f"continuous={cr['continuous']} (track step p95={cr['track_step_p95']}/4096, "
                 f"max={cr['track_step_max']})")
        o.append(f"            node0 angle(s12) f0..f4 = {cr['node0_angles_f0..f4']}")
    fk = result["fk_pose"]
    o.append(f"\n[Q4] POSE + CROSS-CHECK   (clip {fk['clip']} frame {fk['frame']})")
    o.append(f"     invariant max root->leaf chain length = {fk['invariant_max_chain_length']} "
             f"(rotation-INVARIANT)")
    o.append(f"     total bone length = {fk['total_bone_length']}")
    o.append(f"     posed skeleton span (rel node0) = {fk['posed_span_rel_node0']}  "
             f"half-diag = {fk['posed_half_diag_rel_node0']}")
    xc = result["cross_check"]
    if xc.get("log_rows"):
        o.append(f"     live BONES probe rows={xc['log_rows']} (clean={xc.get('clean_rows','?')})  "
                 f"live_n={xc['live_n_values']}  n matches geom bone_count? {xc['live_n_matches_geom']}")
        if xc.get("live_halfdiag"):
            lh = xc["live_halfdiag"]
            o.append(f"     live half-diag band: min={lh['min']} median={lh['median']} max={lh['max']} "
                     f"(scale sweeps ~0.02..3.0)")
            o.append(f"     posed half-diag (scale1) = {xc['posed_halfdiag_scale1']}  "
                     f"within live band? {xc['posed_within_live_band']}")
            nf = xc["nearest_live_frame"]
            o.append(f"     nearest live frame @f{nf['frame']}: span {nf['span']} half-diag {nf['half_diag']}")
            sm = xc["sorted_axis_span_match"]
            o.append(f"     SORTED axis span  posed={sm['posed_sorted']}  live={sm['live_sorted']}  "
                     f"ratios={sm['posed_over_live_ratios']}")
            iv = xc["invariant_vs_live_median"]
            o.append(f"     invariant radius {iv['invariant']} >= live median half-diag {iv['live_median']}? "
                     f"{iv['invariant_exceeds_median']}")
    else:
        o.append("     (no sfxmeshprobe.log found -- cross-check skipped)")
    return "\n".join(o)


if __name__ == "__main__":
    args = sys.argv[1:]
    ef = DEFAULT_EF
    log = DEFAULT_LOG
    clip = 0
    frame = 0
    i = 0
    positional = [a for a in args if not a.startswith("--")]
    if positional:
        ef = positional[0]
    if "--log" in args:
        log = args[args.index("--log") + 1]
    if "--clip" in args:
        clip = int(args[args.index("--clip") + 1])
    if "--frame" in args:
        frame = int(args[args.index("--frame") + 1])
    res = run(ef, log, clip, frame)
    print(_fmt(res))
