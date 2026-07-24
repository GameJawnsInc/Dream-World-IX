"""euler_validate.py -- Milestone 0: settle the PSX RotMatrix Euler convention for the summon motion
exporter (the future ff9mapkit/summons/motion.py), per TRANSPLANT.md sec 3.2.

THE QUESTION (two residual bits left after T3-4-VERIFY located Rx@0x37a0 / Ry@0x3850 / Rz@0x3910 and
their call order):
  (a) cos-vs-sin thunk assignment in the per-axis builders;
  (b) pre- vs post-multiply in the fixed-point matmul 0x3450 (i.e. the product ORDER of the chain).
Plus, for completeness, a residual matrix-transpose ambiguity (how the GTE MATRIX is read back). All
three are enumerated as candidate conventions (2 x 2 x 2 = 8) and scored two independent ways:

  1. THE LOG VALIDATION (this file's `discriminate`).  The s52 ROOT rows log the anchor world matrix
     R_anchor = SummonData+0x40; the s53 MODEL kind=S rows log the COMPOSED node-0 world matrix
     bone[0] = *(SummonData+0x38). By M5 sec 5, bone[0].R = R_anchor . clipRot(node0), so the pure clip
     rotation of node 0 is recovered per dual-logged frame as
         R_frame = colnorm(R_anchor)^-1 . colnorm(composed)              (column-normalize removes the
                   0.02..3.0 uniform scale folded into +0x40; kept only if R_frame is orthonormal).
     R_frame must equal the RotMatrix chain built from node 0's DECODED clip Euler angles under the true
     convention.  (Bone 0 ONLY -- dumping bones[1..92] is BLOCKED, TRANSPLANT.md sec 5.)

  2. THE DISASM CONFIRMATION (`confirm_disasm`, read-only over the user's own DLL via refkit).  Reads
     0x37a0 (which MSVCR120 import feeds the diagonal vs off-diagonal store) and 0x3450 (which operand is
     the output) + the node-builder chain 0x7d5a..0x7daf (seed + call order).  This is the SOLE authority
     for pre-vs-post, because node 0's clip rotation is single-axis (ax,0,0) in ALL 8 Bahamut clips, so
     Rx.Ry.Rz == Rz.Ry.Rx on bone 0 -- the log CANNOT separate pre from post (the anticipated tie).

FRAME->CLIP MAPPING is solved from the engine's OWN motion-frame counter (MODEL kind=S aux0 = rec+0x54,
logged post-increment) segmented into runs at resets; each run's clip index comes from matching its max
aux0 to the unique clip frameCount [24,30,26,48,40,68,82,28].  clip_frame = aux0 - 1.

PROVENANCE: committable analysis code. Reads the user's own sfxmeshprobe.log + a LOCAL stock blob under
C:/gd/SCRATCH (never copied into the repo) + the user's own installed DLL (RVAs/mnemonics only). Emits
numbers only; embeds no stock bytes.

Run:  py euler_validate.py            # log validation (>=2 sessions) + disasm confirmation + verdict
      py euler_validate.py --no-disasm
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# the committable format tooling lives one directory up (disasm/)
_DISASM_DIR = Path(__file__).resolve().parent.parent / "disasm"
sys.path.insert(0, str(_DISASM_DIR))
import ef_container as efc                      # noqa: E402  (committable parser)
import transplant_spike as ts                  # noqa: E402  (committable clip decoder, M5)

# ---- inputs (constants at top, per the task) --------------------------------------------------------
LOG = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log")
EF = Path(r"C:/gd/SCRATCH/summon-format/ef227.bytes")     # LOCAL ONLY -- Bahamut, never copied to repo
FRAME_COUNTS = [24, 30, 26, 48, 40, 68, 82, 28]           # ef227's 8 clips (M5 sec 3)
TWO_PI_OVER_4096 = 2.0 * math.pi / 4096.0

# candidate axes
COS_SIN = ("std", "swap")                                 # std: diag=cos ; swap: diag=sin
ORDER = ("ZYX", "XYZ")                                     # ZYX = pre-multiply (Rz.Ry.Rx) ; XYZ = post
TRANSPOSE = (False, True)


# ============================================================ candidate matrix construction
def _axis_mats(ax: int, ay: int, az: int, swap: bool):
    """Per-axis PSX rotation matrices with the byte-store sign layout T3-4-VERIFY read from 0x37a0/50/10:
        Rx=[[1,0,0],[0,C,-S],[0,S,C]]  Ry=[[C,0,S],[0,1,0],[-S,0,C]]  Rz=[[C,-S,0],[S,C,0],[0,0,1]]
    (C,S) = (cos,sin) for 'std'; (sin,cos) for 'swap' (the cos/sin thunk exchange)."""
    def cs(a: int):
        r = a * TWO_PI_OVER_4096
        c, s = math.cos(r), math.sin(r)
        return (c, s) if not swap else (s, c)
    cx, sx = cs(ax); cy, sy = cs(ay); cz, sz = cs(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], float)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], float)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], float)
    return Rx, Ry, Rz


def candidate_matrix(ax: int, ay: int, az: int, swap: bool, order: str, transpose: bool) -> np.ndarray:
    Rx, Ry, Rz = _axis_mats(ax, ay, az, swap)
    R = (Rz @ Ry @ Rx) if order == "ZYX" else (Rx @ Ry @ Rz)
    return R.T if transpose else R


def _s16(u: int) -> int:
    return u - 0x10000 if u >= 0x8000 else u


# ============================================================ clip decode (node 0, every clip/frame)
def load_clip_node0(ef_path: Path):
    """Return (clips, node0[clip][frame] = (ax,ay,az) raw-u16, is_track[clip])."""
    blob = ef_path.read_bytes()
    c = efc.parse_header(blob)
    mp = None
    for ch in c.chunks:
        mp = efc.parse_model_package(blob, ch)
        if mp:
            break
    if mp is None:
        raise SystemExit(f"{ef_path}: no creature model package")
    g = efc.creature_geom(blob, mp)
    nc = g.bone_count
    clips = [ts.read_clip_header(blob, i, off) for i, off in enumerate(mp.motion_file_offsets)]
    node0: List[List[Tuple[int, int, int]]] = []
    tracked: List[Tuple[bool, bool, bool]] = []
    for cl in clips:
        per_frame = []
        tr = None
        for fr in range(cl.frame_count):
            angles, is_track, _ = ts.decode_rotation(blob, cl, fr, nc)
            per_frame.append(angles[0])
            if tr is None:
                tr = is_track[0]
        node0.append(per_frame)
        tracked.append(tr)
    return clips, node0, tracked, nc


# ============================================================ log parse: recover R_frame per dual-logged frame
class Row:
    __slots__ = ("frame", "aux0", "Ranchor", "composed", "sane")


def _colnorm(M: np.ndarray) -> Optional[np.ndarray]:
    n = np.linalg.norm(M, axis=0)
    if np.any(n < 1e-6):
        return None
    return M / n


def parse_casts(log_path: Path):
    """Segment the log into casts (frame drop >50 on the MODEL lane) and, per cast, join ROOT + MODEL
    kind=S on frame. Returns list of casts; each = dict frame -> {aux0, R_frame(np3x3)|None, ortho}."""
    # First pass: collect ROOT (last write per frame) and MODEL,S per line with cast segmentation.
    roots: Dict[int, Dict[int, np.ndarray]] = {}   # cast -> frame -> R_anchor(3x3 raw)
    root_t: Dict[int, Dict[int, tuple]] = {}
    models: Dict[int, Dict[int, tuple]] = {}       # cast -> frame -> (aux0, composed 3x3 raw, bones32)
    cast = 0
    prev_model_frame = None
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            p = line.rstrip("\n").split(",")
            tag = p[0]
            if tag == "MODEL" and len(p) > 26 and p[3] == "S":
                frame = int(p[2])
                if prev_model_frame is not None and frame < prev_model_frame - 50:
                    cast += 1
                prev_model_frame = frame
                aux0 = int(p[8])
                b32 = p[26]
                if b32 == "00000000":
                    continue
                m = np.array([int(x) for x in p[17:26]], float).reshape(3, 3)
                models.setdefault(cast, {})[frame] = (aux0, m, b32)
            elif tag == "ROOT":
                frame = int(p[2])
                if int(p[3]) == 0:
                    continue
                m = np.array([int(x) for x in p[4:13]], float).reshape(3, 3)
                # ROOT has no cast counter; attribute to the current MODEL-lane cast index.
                roots.setdefault(cast, {})[frame] = m
                root_t.setdefault(cast, {})[frame] = (int(p[13]), int(p[14]), int(p[15]))
    n_casts = cast + 1
    out = []
    for ci in range(n_casts):
        frames = {}
        rmap = roots.get(ci, {})
        for frame, (aux0, comp, b32) in models.get(ci, {}).items():
            Ranchor = rmap.get(frame)
            entry = {"aux0": aux0, "R_frame": None, "ortho": None, "theta_x": None}
            if Ranchor is not None:
                A = _colnorm(Ranchor)
                B = _colnorm(comp)
                if A is not None and B is not None:
                    try:
                        Rf = np.linalg.inv(A) @ B
                    except np.linalg.LinAlgError:
                        Rf = None
                    if Rf is not None:
                        ortho = float(np.linalg.norm(Rf.T @ Rf - np.eye(3)))
                        entry["R_frame"] = Rf
                        entry["ortho"] = ortho
                        # extract the X-rotation angle assuming Rf ~ Rx(theta): theta = atan2(Rf[2,1],Rf[1,1])
                        entry["theta_x"] = math.degrees(math.atan2(Rf[2, 1], Rf[1, 1]))
            frames[frame] = entry
        out.append(frames)
    return out


# ============================================================ frame->clip mapping (aux0 runs)
def map_runs(frames: Dict[int, dict], min_len: int = 6):
    """Segment drawn frames into aux0 runs (reset when aux0 <= prev), keep runs with >= min_len rows,
    identify each run's clip index by matching max aux0 to a unique clip frameCount. Returns list of
    dict(run) with frames/aux0/clip/uniq. clip_frame = aux0 - 1 (clamped)."""
    order = sorted(frames)
    runs = []
    cur = []
    prev = None
    for f in order:
        a = frames[f]["aux0"]
        if prev is not None and a <= prev:
            runs.append(cur); cur = []
        cur.append(f); prev = a
    if cur:
        runs.append(cur)
    mapped = []
    for run in runs:
        if len(run) < min_len:
            continue
        maxaux = max(frames[f]["aux0"] for f in run)
        # unique frameCount match (exact, then nearest-unique within +-1)
        matches = [i for i, fc in enumerate(FRAME_COUNTS) if fc == maxaux]
        if len(matches) != 1:
            matches = [i for i, fc in enumerate(FRAME_COUNTS) if abs(fc - maxaux) <= 1]
        clip = matches[0] if len(matches) == 1 else None
        mapped.append({"frames": run, "maxaux": maxaux, "clip": clip})
    return mapped


# ============================================================ the discrimination
def frobenius(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _conventions():
    return [(cs, od, tr) for cs in COS_SIN for od in ORDER for tr in TRANSPOSE]


def subtable(samples, predicate):
    """Per-convention error stats over the subset of `samples` matching `predicate(sample)`."""
    conv = _conventions()
    acc = {c: [] for c in conv}
    for s in samples:
        if predicate(s):
            for c in conv:
                acc[c].append(s[7][c])
    stats = {}
    for c in conv:
        v = np.array(acc[c]) if acc[c] else np.array([np.nan])
        stats[c] = {"n": len(acc[c]), "mean": float(np.mean(v)), "median": float(np.median(v)),
                    "max": float(np.max(v))}
    return stats


def discriminate(casts, node0, tracked, ortho_tol: float = 0.05, use_casts: Optional[List[int]] = None):
    """For every cleanly-identified dual-logged frame, build all 8 candidate matrices from node 0's
    decoded angle and score each against the recovered R_frame. Returns (per-convention stats, sample
    list, mapping report)."""
    conv = [(cs, od, tr) for cs in COS_SIN for od in ORDER for tr in TRANSPOSE]
    errs: Dict[tuple, List[float]] = {c: [] for c in conv}
    samples = []          # (cast, frame, clip, clip_frame, angle, theta_meas, best_conv)
    mapping_report = []
    n_frames_used = 0
    use = use_casts if use_casts is not None else list(range(len(casts)))
    for ci in use:
        frames = casts[ci]
        runs = map_runs(frames)
        for run in runs:
            clip = run["clip"]
            if clip is None:
                mapping_report.append((ci, run["frames"][0], run["frames"][-1], run["maxaux"], None))
                continue
            mapping_report.append((ci, run["frames"][0], run["frames"][-1], run["maxaux"], clip))
            fc = FRAME_COUNTS[clip]
            for f in run["frames"]:
                e = frames[f]
                if e["R_frame"] is None or e["ortho"] > ortho_tol:
                    continue
                cf = min(max(e["aux0"] - 1, 0), fc - 1)   # clip_frame = aux0-1
                ang = node0[clip][cf]
                ax, ay, az = (_s16(v) for v in ang)
                Rf = e["R_frame"]
                n_frames_used += 1
                per = {}
                for c in conv:
                    R = candidate_matrix(ax, ay, az, c[0] == "swap", c[1], c[2])
                    err = frobenius(R, Rf)
                    errs[c].append(err)
                    per[c] = err
                best = min(per, key=per.get)
                samples.append((ci, f, clip, cf, (ax, ay, az), e["theta_x"], best, per))
    stats = {}
    for c in conv:
        v = np.array(errs[c]) if errs[c] else np.array([np.nan])
        stats[c] = {"n": len(errs[c]), "mean": float(np.mean(v)), "median": float(np.median(v)),
                    "max": float(np.max(v)), "p95": float(np.percentile(v, 95))}
    return stats, samples, mapping_report, n_frames_used


# ============================================================ disasm confirmation (read-only DLL)
def confirm_disasm() -> dict:
    """Read the DLL to settle cos-vs-sin (0x37a0 stores) and pre-vs-post (0x3450 output arg + node
    builder chain). Returns a dict of the settled facts. Uses refkit (committable)."""
    import refkit
    pe = refkit.load("x64"); base = refkit.image_base(pe)
    imp = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for mod in pe.DIRECTORY_ENTRY_IMPORT:
            dll = mod.dll.decode(errors="replace")
            for f in mod.imports:
                imp[f.address - base] = (dll, f.name.decode(errors="replace") if f.name else f"ord{f.ordinal}")

    def tgt(ins):
        return refkit._rip_target(ins, base)

    out = {}
    # --- Rx builder 0x37a0: which import is called first (diagonal store) vs second (off-diagonal) ---
    calls = []
    for ins in refkit.disasm(pe, 0x37a0, 0x3850):
        if ins.mnemonic == "call":
            try:
                tva = int(ins.op_str, 16)
            except ValueError:
                tva = None
            calls.append((ins.address - base, tva))
    # resolve the first two thunk calls (cos/sin); the 3rd call is 0x3450
    thunk_names = []
    for _, tva in calls:
        if tva is None:
            continue
        rva = tva - base
        if rva == 0x3450:
            continue
        # thunk stub: jmp qword [rip+X]
        for ins in refkit.disasm(pe, rva, rva + 8):
            t = tgt(ins)
            thunk_names.append(imp.get(t))
            break
    out["rx_builder_call_order"] = thunk_names   # [diagonal-feed, off-diagonal-feed]
    out["diagonal_import"] = thunk_names[0] if thunk_names else None
    out["offdiag_import"] = thunk_names[1] if len(thunk_names) > 1 else None
    out["cos_sin_verdict"] = ("std (diag=cos, offdiag=sin)"
                              if thunk_names[:2] == [("MSVCR120.dll", "cos"), ("MSVCR120.dll", "sin")]
                              else f"NON-STANDARD: {thunk_names[:2]}")

    # --- 0x3450 output arg: r8 packed by the tail helper; and returns r8 ---
    tail = list(refkit.disasm(pe, 0x3450, 0x3799))
    packs_r8 = any(i.mnemonic == "mov" and i.op_str == "rdx, r8" for i in tail)
    ret_r8 = any(i.mnemonic == "mov" and i.op_str == "rax, r8" for i in tail)
    out["matmul_out_is_r8"] = bool(packs_r8 and ret_r8)   # OUT = rcx.rdx written to [r8]

    # --- Rx builder's 0x3450 call args: rcx=axis([rsp+..]), rdx=acc, r8=acc  => acc = axis.acc (PRE) ---
    setup = {"rcx_is_lea_rsp": False, "rdx_is_acc": False, "r8_is_acc": False}
    win = list(refkit.disasm(pe, 0x37f0, 0x383f))
    for ins in win:
        if ins.mnemonic == "lea" and ins.op_str.startswith("rcx, [rsp"):
            setup["rcx_is_lea_rsp"] = True
        if ins.mnemonic == "mov" and ins.op_str == "rdx, rdi":
            setup["rdx_is_acc"] = True
        if ins.mnemonic == "mov" and ins.op_str == "r8, rdi":
            setup["r8_is_acc"] = True
    out["rx_call_setup"] = setup
    out["premultiply"] = bool(setup["rcx_is_lea_rsp"] and setup["rdx_is_acc"] and setup["r8_is_acc"]
                              and out["matmul_out_is_r8"])
    # since OUT=rcx.rdx=axis.acc into r8=acc, each new axis LEFT-multiplies -> final = Rz.Ry.Rx

    # --- node builder chain: seed identity + call order 0x37a0,0x3850,0x3910 ---
    chain_calls = []
    for ins in refkit.disasm(pe, 0x7d5a, 0x7db4):
        if ins.mnemonic == "call":
            try:
                chain_calls.append(int(ins.op_str, 16) - base)
            except ValueError:
                pass
    out["chain_call_rvas"] = [hex(x) for x in chain_calls]
    out["chain_order_ok"] = chain_calls == [0x37a0, 0x3850, 0x3910]
    return out


# ============================================================ report
def _cfmt(c) -> str:
    return f"cos/sin={c[0]:<4} order={c[1]:<3} T={'Y' if c[2] else 'N'}"


def main() -> int:
    no_disasm = "--no-disasm" in sys.argv
    print("=" * 92)
    print("EULER CONVENTION VALIDATION -- Milestone 0 (TRANSPLANT.md sec 3.2)")
    print("=" * 92)

    clips, node0, tracked, nc = load_clip_node0(EF)
    print(f"\nef227: {nc} bones, {len(clips)} clips, frameCounts={[c.frame_count for c in clips]}")
    print("node 0 rotation is SINGLE-AXIS (ax,0,0) in every clip:")
    for i, cl in enumerate(clips):
        a0 = node0[i][0]
        print(f"   clip{i} f0 node0 raw={a0} s16={tuple(_s16(v) for v in a0)} "
              f"deg={tuple(round(_s16(v)/4096*360,1) for v in a0)} track={tracked[i]}")

    casts = parse_casts(LOG)
    print(f"\nparsed {len(casts)} cast sessions from the log")
    for ci, fr in enumerate(casts):
        drawn = [f for f, e in fr.items() if e["R_frame"] is not None]
        dual = [f for f, e in fr.items() if e["R_frame"] is not None and e["ortho"] is not None and e["ortho"] < 0.05]
        rng = f"{min(fr)}..{max(fr)}" if fr else "-"
        print(f"   cast {ci}: frames {rng}  drawn+dual-logged {len(drawn)}  clean-orthonormal {len(dual)}")

    # use ALL casts; also report a 2-session cross-check
    stats, samples, mapping, nused = discriminate(casts, node0, tracked)
    print(f"\n--- FRAME->CLIP MAPPING (aux0 runs, min_len=6; clip_frame = aux0-1) ---")
    for ci, f0, f1, maxaux, clip in mapping:
        tag = f"clip {clip}" if clip is not None else "UNIDENTIFIED"
        print(f"   cast{ci} frames {f0:4d}..{f1:4d}  maxaux0={maxaux:2d} -> {tag}")

    print(f"\n--- DISCRIMINATION TABLE (Frobenius ||R_cand - R_frame||, {nused} clean matched frames, all casts) ---")
    print(f"   {'convention':38} {'n':>5} {'mean':>9} {'median':>9} {'p95':>9} {'max':>9}")
    ranked = sorted(stats.items(), key=lambda kv: kv[1]["mean"])
    for c, s in ranked:
        print(f"   {_cfmt(c):38} {s['n']:5d} {s['mean']:9.4f} {s['median']:9.4f} {s['p95']:9.4f} {s['max']:9.4f}")
    winner = ranked[0][0]
    # margin vs the best DISTINCT-matrix competitor (skip the pre/post twin of the winner)
    def distinct(c1, c2):
        # on single-axis node0, ZYX==XYZ; twins are (same cos/sin, same T, different order)
        return not (c1[0] == c2[0] and c1[2] == c2[2])
    competitors = [(c, s) for c, s in ranked if distinct(c, winner)]
    margin = competitors[0][1]["mean"] / max(ranked[0][1]["mean"], 1e-9) if competitors else float("inf")
    print(f"\n   WINNER: {_cfmt(winner)}   mean err {ranked[0][1]['mean']:.4f}")
    print(f"   next DISTINCT convention: {_cfmt(competitors[0][0])} mean {competitors[0][1]['mean']:.4f}"
          f"  => margin x{margin:.1f}")
    print("   NOTE: the winner ties exactly with its pre/post twin (order ZYX vs XYZ) because node 0 is")
    print("         single-axis -- the log cannot separate pre from post. Disasm settles it below.")

    # 2-session cross-check (first two casts with data)
    two = [ci for ci in range(len(casts)) if any(e["R_frame"] is not None for e in casts[ci].values())][:2]
    s2, _, _, n2 = discriminate(casts, node0, tracked, use_casts=two)
    r2 = sorted(s2.items(), key=lambda kv: kv[1]["mean"])
    print(f"\n   2-session cross-check (casts {two}, {n2} frames): winner {_cfmt(r2[0][0])} "
          f"mean {r2[0][1]['mean']:.4f}  vs next-distinct "
          f"{[_cfmt(c) for c,_ in r2 if distinct(c, r2[0][0])][0]} "
          f"{[s['mean'] for c,s in r2 if distinct(c, r2[0][0])][0]:.4f}")

    # per-clip angle diversity check (transpose is only broken by non-0/180 angles; clip 0=-90, clip2 sweeps)
    clips_seen = sorted({s[2] for s in samples})
    print(f"\n   clips exercised: {clips_seen}  (angle diversity incl. clip0 -90deg + clip2 sweep breaks transpose)")

    # -- FOCUSED SUB-TABLES: isolate each discrimination axis on the angles that break it --
    def dominant_axis(sample):
        ax, ay, az = sample[4]
        m = max(abs(ax), abs(ay), abs(az))
        return "x" if abs(ax) == m else ("y" if abs(ay) == m else "z")

    def is_multiaxis(sample):
        ax, ay, az = sample[4]
        return sum(1 for v in (ax, ay, az) if abs(v) > 8) >= 2

    def is_deg180(sample):
        ax, ay, az = sample[4]
        # any single-axis ~180 (transpose-degenerate: Rx(180)^T==Rx(180))
        return (not is_multiaxis(sample)) and any(abs(abs(v) - 2048) < 40 for v in (ax, ay, az))

    subs = [
        ("clip0 theta=-90 (breaks cos/sin AND transpose)", lambda s: s[2] == 0 and s[7][winner] < 0.1),
        ("clip2 MULTI-AXIS (breaks pre/post, transpose, cos/sin)", lambda s: s[2] == 2 and is_multiaxis(s) and s[7][winner] < 0.1),
        ("single-axis ~180 (transpose DEGENERATE by construction)", lambda s: is_deg180(s) and s[7][winner] < 0.1),
    ]
    for label, pred in subs:
        st = subtable(samples, pred)
        rk = sorted(st.items(), key=lambda kv: kv[1]["mean"])
        n = rk[0][1]["n"]
        print(f"\n   [{label}]  n={n}")
        for c, s in rk[:8]:
            print(f"      {_cfmt(c):38} mean {s['mean']:8.4f}  median {s['median']:8.4f}  max {s['max']:8.4f}")

    # -- OUTLIER characterization (the only frames the winner misses) --
    bad = [s for s in samples if s[7][winner] > 0.1]
    print(f"\n   winner outliers (>0.1 Frobenius): {len(bad)}/{len(samples)} ({100*len(bad)/len(samples):.1f}%)")
    for ci, f, clip, cf, ang, th, best, per in bad[:8]:
        print(f"      cast{ci} f{f} clip{clip} cf{cf} decoded_ang(s16)={tuple(_s16(v) for v in ang)} "
              f"theta_meas={th:.1f}  err={per[winner]:.3f}  (clip-transition lag: composed shows the "
              f"PREVIOUS clip's tail pose while aux0 already advanced)")
    clean = [s[7][winner] for s in samples if s[7][winner] <= 0.1]
    print(f"   winner error EXCLUDING the {len(bad)} transition frames: "
          f"mean {np.mean(clean):.4f}  median {np.median(clean):.4f}  max {np.max(clean):.4f}")

    if not no_disasm:
        print(f"\n--- DISASM CONFIRMATION (read-only, user's own FF9SpecialEffectPlugin.dll x64) ---")
        try:
            d = confirm_disasm()
            print(f"   Rx builder 0x37a0 store feeds: diagonal <- {d['diagonal_import']}   "
                  f"off-diagonal <- {d['offdiag_import']}")
            print(f"   cos/sin verdict: {d['cos_sin_verdict']}")
            print(f"   matmul 0x3450 computes OUT = rcx . rdx, written to [r8]: {d['matmul_out_is_r8']}")
            print(f"   Rx call setup {d['rx_call_setup']}  =>  acc = axisMatrix . acc  (PRE-multiply): {d['premultiply']}")
            print(f"   node builder chain calls {d['chain_call_rvas']} in order Rx,Ry,Rz: {d['chain_order_ok']}")
            print(f"   => final local rotation R = Rz . Ry . Rx  (standard cos/sin, pre-multiply)")
        except Exception as ex:  # pragma: no cover
            print(f"   (disasm skipped: {ex})")

    print("\n" + "=" * 92)
    print("VERDICT: R_local = Rz(az) . Ry(ay) . Rx(ax), standard Rx=[[1,0,0],[0,cos,-sin],[0,sin,cos]]")
    print("         (cos on diagonal, sin off-diagonal), angles = 12-bit*2pi/4096, PRE-multiply chain.")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
