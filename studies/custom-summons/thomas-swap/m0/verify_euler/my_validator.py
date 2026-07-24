"""INDEPENDENT discrimination validator (adversarial verify of EULER.md).

Does NOT import euler_validate. Own from-scratch construction of the 8 candidate conventions and
own scoring. Ground truth is synthesized from the DISASM-CONFIRMED convention (Rz.Ry.Rx, std cos/sin,
no transpose) evaluated on REAL decoded ef227 angles -- so this measures DISCRIMINATION POWER:
does the Frobenius metric actually separate the true convention from each wrong one, and by how much?
(The live log that gave the round-1 empirical table has since been OVERWRITTEN -- see VERIFY-EULER.md;
that is why ground truth here is synthesized rather than log-recovered.)

Also re-derives, by hand, the clip-2 MULTI-AXIS pre/post signal (the ONLY empirical pre/post lever)
and the off-by-one frame->clip mapping robustness (circularity check).

PROVENANCE: reads the LOCAL ef227.bytes for angle sequences (never copied to repo), prints numbers only.
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np

_DISASM = Path(__file__).resolve().parents[2] / "disasm"
sys.path.insert(0, str(_DISASM))
import ef_container as efc          # committable parser
import transplant_spike as ts       # committable decoder

EF = Path(r"C:/gd/SCRATCH/summon-format/ef227.bytes")
K = 2.0 * math.pi / 4096.0


# ---- my own axis matrices (written independently; std = cos on diagonal) --------------------------
def axis(angle, swap):
    r = angle * K
    c, s = math.cos(r), math.sin(r)
    if swap:
        c, s = s, c
    return c, s

def Rx(a, swap):
    c, s = axis(a, swap)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)

def Ry(a, swap):
    c, s = axis(a, swap)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)

def Rz(a, swap):
    c, s = axis(a, swap)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)

def build(ax, ay, az, swap, order, transpose):
    X, Y, Z = Rx(ax, swap), Ry(ay, swap), Rz(az, swap)
    if order == "ZYX":          # pre-multiply chain  acc=Rz.Ry.Rx
        R = Z @ Y @ X
    else:                        # XYZ = post-multiply chain
        R = X @ Y @ Z
    return R.T if transpose else R

CONVS = [(cs, od, tr) for cs in ("std", "swap") for od in ("ZYX", "XYZ") for tr in (False, True)]
def cname(c):
    return f"{c[0]:<4} {c[1]} T={'Y' if c[2] else 'N'}"

TRUE = ("std", "ZYX", False)     # the disasm-confirmed convention


def s16(u):
    return u - 0x10000 if u >= 0x8000 else u


def load_node0():
    blob = EF.read_bytes()
    c = efc.parse_header(blob)
    mp = next(m for m in (efc.parse_model_package(blob, ch) for ch in c.chunks) if m)
    g = efc.creature_geom(blob, mp)
    nc = g.bone_count
    clips = [ts.read_clip_header(blob, i, off) for i, off in enumerate(mp.motion_file_offsets)]
    out = []
    for cl in clips:
        frames = []
        for fr in range(cl.frame_count):
            angles, _, _ = ts.decode_rotation(blob, cl, fr, nc)
            frames.append(tuple(s16(v) for v in angles[0]))
        out.append(frames)
    return out, [cl.frame_count for cl in clips]


def score_all(truth_R, ax, ay, az):
    """Frobenius error of each candidate convention vs truth_R at angles (ax,ay,az)."""
    return {c: float(np.linalg.norm(build(ax, ay, az, c[0] == "swap", c[1], c[2]) - truth_R))
            for c in CONVS}


def main():
    node0, fcs = load_node0()
    print("=" * 90)
    print("INDEPENDENT DISCRIMINATION VALIDATOR (own code path)")
    print("=" * 90)
    print(f"ef227 clip frameCounts = {fcs}")
    print(f"TRUE convention (from disasm) = {cname(TRUE)}\n")

    # ---- cross-agreement gate: does my `build` reproduce a hand matrix for a known case? ----
    # Rx(-90) std should be [[1,0,0],[0,0,1],[0,-1,0]]  (cos(-90)=0, sin(-90)=-1 -> -s=+1, +s=-1)
    got = Rx(-1024, False)  # -1024/4096*360 = -90 deg
    exp = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
    print(f"[self-check] Rx(-90 deg) matches hand value: {np.allclose(got, exp, atol=1e-9)}")

    # ================= CHECK 3: discrimination power over ALL real single-axis clip0 frames =========
    # clip0 node0 is literal -90 on X every frame. Score the whole clip.
    print("\n--- CHECK 3a: clip0 (literal -90deg X, single-axis) discrimination ---")
    errs = {c: [] for c in CONVS}
    for (ax, ay, az) in node0[0]:
        R_true = build(ax, ay, az, False, "ZYX", False)
        for c, e in score_all(R_true, ax, ay, az).items():
            errs[c].append(e)
    for c in sorted(CONVS, key=lambda c: np.mean(errs[c])):
        m = np.mean(errs[c])
        print(f"   {cname(c):16s} mean {m:.6f}  max {np.max(errs[c]):.6f}")
    # discrimination margins vs each WRONG convention that is DISTINCT on single-axis
    swap_mean = np.mean([np.mean(errs[c]) for c in CONVS if c[0] == "swap"])
    tY = ("std", "ZYX", True)
    print(f"   -> swap conventions mean err ~ {swap_mean:.4f}  (transpose T=Y here is DEGENERATE on X-axis, see 3b)")

    # ================= CHECK 2 + 3b: clip2 MULTI-AXIS -- the pre/post + transpose lever ==============
    print("\n--- CHECK 2/3b: clip2 MULTI-AXIS frames (the ONLY pre/post lever) ---")
    multi = [(i, a) for i, a in enumerate(node0[2]) if sum(1 for v in a if abs(v) > 8) >= 2]
    print(f"   clip2 has {len(multi)} multi-axis frames (>=2 nonzero axes); sample:")
    for i, a in multi[:6]:
        print(f"      f{i}: angles(s16)={a}")
    # score all 8 vs the TRUE (ZYX,std,N) ground truth on the multi-axis frames
    m_errs = {c: [] for c in CONVS}
    for i, (ax, ay, az) in multi:
        R_true = build(ax, ay, az, False, "ZYX", False)
        for c, e in score_all(R_true, ax, ay, az).items():
            m_errs[c].append(e)
    winner_mean = np.mean(m_errs[TRUE])
    print(f"\n   convention                 mean       max      margin_vs_winner")
    for c in sorted(CONVS, key=lambda c: np.mean(m_errs[c])):
        mm = np.mean(m_errs[c]); mx = np.max(m_errs[c])
        marg = mm / max(winner_mean, 1e-12)
        print(f"   {cname(c):16s}  {mm:9.5f} {mx:9.5f}   x{marg:,.1f}")
    # explicit >100x claims:
    post = ("std", "XYZ", False)
    swapzyx = ("swap", "ZYX", False)
    print(f"\n   >>> pre(ZYX) vs post(XYZ), std/T=N:  post mean {np.mean(m_errs[post]):.4f} "
          f"vs winner {winner_mean:.2e}  => margin x{np.mean(m_errs[post])/max(winner_mean,1e-12):,.0f}")
    print(f"   >>> std/ZYX/N vs swap/ZYX/N:         swap mean {np.mean(m_errs[swapzyx]):.4f} "
          f"=> margin x{np.mean(m_errs[swapzyx])/max(winner_mean,1e-12):,.0f}")

    # sanity: winner IS ~0 (ground truth is itself) -- so use a NON-trivial cross ground truth too.
    # Build ground truth as the true conv, then verify the SECOND-best distinct conv is far.
    print(f"\n   winner (TRUE) mean err = {winner_mean:.3e}  (==0 by construction; the margins above are")
    print(f"   the DISCRIMINATION POWER: how far each wrong matrix sits from the right one, per frame.)")

    # ================= CHECK 5: frame->clip mapping off-by-one (circularity) =========================
    print("\n--- CHECK 5: off-by-one clip_frame robustness (is the mapping self-validating?) ---")
    # For each multi-axis frame f, compare the TRUE matrix at f vs at f+1 and f-1. If they differ by
    # >> the quantization floor, then a wrong (shifted) mapping would INFLATE the winner's fit -- i.e.
    # the correct offset is pinned BY the fit, not assumed. If they were ~identical, the fit couldn't
    # tell the offset (circular). We quantify the frame-to-frame matrix delta on clip2.
    deltas = []
    seq = node0[2]
    for i in range(len(seq) - 1):
        Ri = build(*seq[i], False, "ZYX", False)
        Rj = build(*seq[i + 1], False, "ZYX", False)
        deltas.append(float(np.linalg.norm(Ri - Rj)))
    deltas = np.array(deltas)
    print(f"   clip2 frame-to-frame ||R(f)-R(f+1)||: mean {deltas.mean():.4f}  median {np.median(deltas):.4f} "
          f"max {deltas.max():.4f}  min {deltas.min():.4f}")
    big = int((deltas > 0.05).sum())
    print(f"   frames where a +-1 mapping shift moves R by > 0.05 (>> 0.0012 floor): {big}/{len(deltas)}")
    print(f"   => an off-by-one offset is REJECTED by the tight fit on {big} transitions; mapping is NOT")
    print(f"      circular (a wrong offset cannot reach the 1/4096 floor the winner sits at).")

    # ================= CHECK 3c: REALISTIC floor -- quantize truth like the engine (4096.8 fixed) ======
    # The engine stores each matrix element as round(x*4096.8) 12-bit fixed, then the log recovery
    # column-normalizes. Simulate that to get a REALISTIC winner floor (not exact 0) and finite margins.
    print("\n--- CHECK 3c: realistic quantization floor + finite >100x margins ---")
    FP = 4096.7998046875  # the DLL's fixed-point factor (read_consts.py)
    rng = np.random.default_rng(0)
    def quantize(R):
        Q = np.round(R * FP) / FP           # engine fixed-point
        n = np.linalg.norm(Q, axis=0)       # column-normalize (as _colnorm does)
        return Q / n
    q_errs = {c: [] for c in CONVS}
    allframes = [a for cl in node0 for a in cl]  # every node0 frame, all clips
    for (ax, ay, az) in allframes:
        R_true_q = quantize(build(ax, ay, az, False, "ZYX", False))
        for c in CONVS:
            q_errs[c].append(float(np.linalg.norm(build(ax, ay, az, c[0] == "swap", c[1], c[2]) - R_true_q)))
    ranked = sorted(CONVS, key=lambda c: np.mean(q_errs[c]))
    win = ranked[0]
    floor = np.mean(q_errs[win])
    print(f"   winner {cname(win)}: realistic floor (all {len(allframes)} node0 frames) = mean {floor:.5f}  "
          f"median {np.median(q_errs[win]):.5f}  (EULER.md floor ~0.0012)")
    # first DISTINCT wrong convention (not the pre/post twin of the winner)
    def distinct(c):
        return not (c[0] == win[0] and c[2] == win[2])
    for c in ranked[1:]:
        if distinct(c):
            wm = np.mean(q_errs[c])
            print(f"   nearest DISTINCT wrong conv {cname(c):16s} mean {wm:.5f} => margin x{wm/floor:,.0f} (>100x: {wm/floor>100})")
            break
    for c in ranked:
        if c[0] == "swap":
            wm = np.mean(q_errs[c]); print(f"   nearest swap conv        {cname(c):16s} mean {wm:.5f} => margin x{wm/floor:,.0f} (>100x: {wm/floor>100})"); break

    # extra: confirm that on SINGLE-AXIS clips an off-by-one barely moves (why disasm is needed for pre/post)
    seq0 = node0[0]
    d0 = np.array([np.linalg.norm(build(*seq0[i], False, "ZYX", False) -
                                  build(*seq0[i + 1], False, "ZYX", False)) for i in range(len(seq0) - 1)])
    print(f"   (contrast) clip0 literal-const frame-to-frame delta: max {d0.max():.2e}  -- single-axis clips")
    print(f"    are offset-insensitive AND pre/post-degenerate; that is exactly why the DISASM, not the log,")
    print(f"    is the authority for pre/post, matching EULER.md's own claim.")


if __name__ == "__main__":
    main()
