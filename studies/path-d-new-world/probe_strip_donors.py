"""STRIP-CARRY DONOR INVENTORY -- the read-only probe before the registration.

The profile-carry rung scored FAIL-on-form 2026-07-30 (PROFILE-CARRY-PREDICTION.md): the
carried massing improved the shape verdict, but course-depth sampling flattened the ledge
relief the fringe tiles advertise. The pre-declared FAIL branch names the next lane:
WHOLE-MESH STRIP CARRY -- carry real wall geometry verbatim (verts+uvs+tangents) as strips
seated on a minted plan. Before registering that rung, this probe answers, from the massing
artifact (out/rock_wall_massing.json, per-column world centroids + profiles):

  1. CHAINS: per component, columns ordered by nearest-neighbour chaining in plan (step
     <= 9u). Does any chain CLOSE (a full stock ring -- the zero-seam jackpot)?
  2. BEND: per chain, arc length, per-column signed turn distribution, total signed bend --
     the intrinsic curvature a rigid carry brings with it.
  3. OUTWARDNESS: walls batter outward going down (foot offsets exceed crest offsets along
     the outward normal), so the artifact's arbitrary-sign nrm is recoverable; a strip is
     traversable in only ONE direction once the ring's handedness is fixed.
  4. BURIAL FEASIBILITY: per column H >= SHELF_BAND[0]-LOWLAND+0.3 = 12.8u (the amendment's
     seat); maximal feasible sub-runs per chain.
  5. COMPOSITION: combos of 2-5 feasible runs whose summed length lands a plateau radius
     R = L/2pi in [10, 24]u (fits the 40u bench island) and whose total intrinsic bend
     leaves a per-seam kink within stock's own per-column turn distribution.

Read-only; artifact -> out/strip_donors.json. Run: py -X utf8 probe_strip_donors.py
"""
import itertools
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MASSING = HERE.parents[1] / "studies" / "overworld-topography" / "out" / "rock_wall_massing.json"
OUT = HERE / "out" / "strip_donors.json"

SHELF_BAND = (15.7, 18.3)
LOWLAND = 3.2
NEED_H = SHELF_BAND[0] - LOWLAND + 0.3                      # 12.8u -- burial-seat feasibility
STEP_MAX = 9.0                                              # ~2x station: same-wall gate
R_BAND = (10.0, 24.0)                                       # plateau radius that fits the bench


def signed_turn(a, b, c):
    """Turn angle at b (deg) in plan, +ve = left turn while travelling a->b->c."""
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    L1, L2 = math.hypot(*v1), math.hypot(*v2)
    if L1 < 1e-9 or L2 < 1e-9:
        return 0.0
    cr = v1[0] * v2[1] - v1[1] * v2[0]
    dt = v1[0] * v2[0] + v1[1] * v2[1]
    return math.degrees(math.atan2(cr, dt))


d = json.loads(MASSING.read_text())
chains = []
chain_geo = []                                              # (P, turns_by_vertex, steps, feas, blk)
for comp in d["profiles"]:
    cols = comp["profiles"]
    pts = [(c["cen"][0], c["cen"][2]) for c in cols]
    H = [c["prof"][-1][1] for c in cols]
    # outwardness per column: along nrm, does the foot stick OUT past the crest?
    outward_ok = []
    for c in cols:
        prof = c["prof"]                                    # [(off, h)], h=0 base .. H crest
        off_crest, off_foot = prof[-1][0], prof[0][0]
        outward_ok.append(off_foot > off_crest)             # nrm as stored points outward
    n = len(cols)
    used = [False] * n
    for s in range(n):
        if used[s]:
            continue
        chain = [s]
        used[s] = True
        for _dirn in (1, -1):                               # grow both ends
            while True:
                tail = chain[-1] if _dirn == 1 else chain[0]
                cand = [(math.dist(pts[tail], pts[j]), j) for j in range(n) if not used[j]]
                cand = [c for c in cand if c[0] <= STEP_MAX]
                if not cand:
                    break
                _, j = min(cand)
                used[j] = True
                (chain.append if _dirn == 1 else lambda x: chain.insert(0, x))(j)
        if len(chain) < 6:
            continue
        P = [pts[i] for i in chain]
        # outward side vs travel: cross2d(travel, nrm) per column; force nrm-ON-RIGHT
        # traversal (ring interior = plateau on the left), reversing the chain if needed
        sides = []
        for ci in range(len(chain) - 1):
            t = (P[ci + 1][0] - P[ci][0], P[ci + 1][1] - P[ci][1])
            nr = cols[chain[ci]]["nrm"]
            sides.append(t[0] * nr[1] - t[1] * nr[0])
        if sides and float(np.median(sides)) > 0:           # nrm on the left -> reverse
            chain.reverse()
            P.reverse()
        closes = math.dist(P[0], P[-1]) <= STEP_MAX and len(chain) >= 8
        loopP = P + [P[0]] if closes else P
        length = sum(math.dist(loopP[i], loopP[i + 1]) for i in range(len(loopP) - 1))
        turns = [signed_turn(loopP[i - 1], loopP[i], loopP[i + 1])
                 for i in range(1, len(loopP) - 1)]
        if closes:                                          # wrap turns at both weld points
            turns.append(signed_turn(P[-2], P[-1], P[0]))
            turns.append(signed_turn(P[-1], P[0], P[1]))
        feas = [H[i] >= NEED_H for i in chain]
        t_open = [signed_turn(P[i - 1], P[i], P[i + 1]) for i in range(1, len(P) - 1)]
        # THE TIER GATE (instrument calibration, found by the strip builder's mesh dump):
        # nearest-neighbour chaining stitches wall runs from DIFFERENT tiers into one chain
        # -- blk [22,14]'s n=14 chain has a 15.8u crest spread, so its bend was tier-noise,
        # not wall-line curvature. Stock's own law (the round-4 amendment): crests are
        # LEVEL per run. Split chains at crest jumps > 2.5u; window-search level sub-chains.
        crest_abs = [cols[i]["cen"][1] + cols[i]["prof"][-1][1] for i in chain]
        sub = [0]
        for ci in range(1, len(chain)):
            if abs(crest_abs[ci] - crest_abs[ci - 1]) > 2.5:
                sub.append(ci)
        sub.append(len(chain))
        for q0, q1 in zip(sub, sub[1:]):
            if q1 - q0 < 8:
                continue
            Ps = P[q0:q1]
            ts_ = [signed_turn(Ps[i - 1], Ps[i], Ps[i + 1]) for i in range(1, len(Ps) - 1)]
            if ts_ and float(np.median(np.abs(ts_))) > 60.0:
                continue                                    # plan zigzag: not a wall line
            chain_geo.append((Ps, [0.0] + ts_ + [0.0],
                              [math.dist(Ps[i], Ps[i + 1]) for i in range(len(Ps) - 1)],
                              feas[q0:q1], comp["blk"], (q0, q1),
                              round(max(crest_abs[q0:q1]) - min(crest_abs[q0:q1]), 1),
                              len(chain)))
        # maximal contiguous feasible sub-runs (in-chain, no wrap)
        runs, cur = [], 0
        for f in feas + [False]:
            cur = cur + 1 if f else (runs.append(cur) or 0 if cur else 0)
        chains.append(dict(
            blk=comp["blk"], n=len(chain), closes=closes,
            length=round(length, 1), bend=round(sum(turns), 1),
            turn_med=round(float(np.median(np.abs(turns))), 1) if turns else 0.0,
            turn_p95=round(float(np.percentile(np.abs(turns), 95)), 1) if turns else 0.0,
            step_med=round(float(np.median([math.dist(P[i], P[i + 1])
                                            for i in range(len(P) - 1)])), 2),
            H_min=round(min(H[i] for i in chain), 1),
            H_med=round(float(np.median([H[i] for i in chain])), 1),
            n_feasible=sum(feas), max_run=max(runs) if runs else 0,
            outward_frac=round(sum(outward_ok[i] for i in chain) / len(chain), 2),
            all_feasible=all(feas)))

chains.sort(key=lambda c: (-c["closes"], -c["max_run"]))
allturn = [abs(t) for c in chains for t in [c["turn_med"]]]  # summary only; full dist below

print(f"chains >= 6 columns: {len(chains)} across {len({tuple(c['blk']) for c in chains})} "
      f"blocks; feasibility bar H >= {NEED_H:.1f}u\n")
print("== CLOSED RINGS (the zero-seam jackpot, if any) ==")
closed = [c for c in chains if c["closes"]]
for c in closed:
    print(f"  blk {c['blk']}: n={c['n']} len={c['length']}u R~{c['length'] / (2 * math.pi):.1f}u "
          f"bend={c['bend']} H_min={c['H_min']} feas={c['n_feasible']}/{c['n']} "
          f"ALL_FEAS={c['all_feasible']}")
if not closed:
    print("  none")

print("\n== TOP OPEN RUNS by max contiguous feasible sub-run ==")
for c in [c for c in chains if not c["closes"]][:14]:
    print(f"  blk {c['blk']}: n={c['n']} max_run={c['max_run']} len={c['length']}u "
          f"bend={c['bend']} turn_med={c['turn_med']} p95={c['turn_p95']} "
          f"step={c['step_med']}u H_med={c['H_med']} outward={c['outward_frac']}")

# ---- stock per-column turn distribution (the seam-kink legality reference) -----------------
turn_all = []
for comp in d["profiles"]:
    cols = comp["profiles"]
    pts = [(c["cen"][0], c["cen"][2]) for c in cols]
    # reuse the chain walk cheaply: consecutive |turn| over every chain of this comp
for c in chains:
    pass
print(f"\nstock per-column |turn| context: med-of-chain-medians "
      f"{np.median([c['turn_med'] for c in chains]):.1f} deg, "
      f"p95-of-chain-p95s {np.percentile([c['turn_p95'] for c in chains], 50):.1f} deg (med)")
strong = [c for c in chains if abs(c["bend"]) > 45]
print(f"handedness check (nrm-on-right traversal, strongly-bent chains |bend|>45): "
      f"{sum(1 for c in strong if c['bend'] > 0)} positive vs "
      f"{sum(1 for c in strong if c['bend'] < 0)} negative of {len(strong)} -- "
      f"convex plateau walls should share ONE sign")

# ---- window-level composition search -------------------------------------------------------
# The maximal-run combos above are the coarse view; the atomic carriable unit is a WINDOW
# (a contiguous feasible column stretch inside one chain). Burial-seat geometry on the
# radius-40 bench caps the crest radius: reach = R + drop/tan(50deg) (~11.7u foot flare)
# + ~6u ground annulus <= ~36u  =>  R <= ~17u. Positive net bend is required (plateau
# handedness); basin-negative chains may still donate positive-bend corner windows.
print("\n== WINDOW COMPOSITIONS (burial seat, kink <= 25 deg/seam, TIER-GATED chains) ==")
# R cap: a radius-48 island occupies the SAME 6 bench blocks -- reach = R + ~11.7 flare
# + ~6 annulus + margin => R <= ~26. S up to 5 (the level pool carries less bend/strip).
WIN_R = (12.0, 26.0)
KINK_MAX = 25.0
wins = []
for ci, c in enumerate(chain_geo):
    P, turns, steps, feas, blk, qrange, cspread, nchain = c
    n = len(P)
    for i in range(n):
        if not feas[i]:
            continue
        j = i + 1
        while j < n and feas[j] and math.dist(P[j - 1], P[j]) <= STEP_MAX:
            j += 1
        # [i, j) all feasible & contiguous; enumerate sub-windows ending anywhere
        for a in range(i, j - 7):
            for b in range(a + 7, j):
                L = sum(steps[t] for t in range(a, b))
                if L > 2 * math.pi * WIN_R[1]:
                    break
                B = sum(turns[t] for t in range(a + 1, b))
                wins.append((round(B, 1), round(L, 1), ci, a + qrange[0], b + qrange[0],
                             blk, cspread, nchain))
        break                                               # windows of the FIRST feasible
                                                            # stretch only (greedy, plenty)
wins_u = {}
for w in wins:                                              # dedupe: best bend per (chain, L~)
    key = (w[2], round(w[1] / 4))
    if key not in wins_u or w[0] > wins_u[key][0]:
        wins_u[key] = w
wins = sorted(wins_u.values(), key=lambda w: -w[0])
print(f"windows (n>=8 cols, feasible, LEVEL, deduped): {len(wins)}; "
      f"best bend {wins[0][0]} deg over {wins[0][1]}u (blk {wins[0][5]})" if wins else "none")

best_c = []
pos = [w for w in wins if w[0] > 0]
for S in (3, 4, 5):
    pool = pos[:200] if S == 3 else pos[:26]
    for combo in itertools.combinations(range(len(pool)), S):
        ws = [pool[i] for i in combo]
        if len({w[2] for w in ws}) < S:
            continue
        L = sum(w[1] for w in ws)
        R = L / (2 * math.pi)
        if not (WIN_R[0] <= R <= WIN_R[1]):
            continue
        kink = (360.0 - sum(w[0] for w in ws)) / S
        if abs(kink) > KINK_MAX:
            continue
        best_c.append((abs(kink), kink, R, S, ws))
best_c.sort(key=lambda x: (x[0], x[3]))
for ak, kink, R, S, ws in best_c[:12]:
    desc = " + ".join(f"blk{w[5]}chain{w[7]}[{w[3]}:{w[4]}]({w[4] - w[3] + 1}c,{w[1]}u,"
                      f"{w[0]}deg,lvl{w[6]})" for w in ws)
    print(f"  S={S} R={R:.1f}u kink={kink:+.1f} deg/seam: {desc}")
if not best_c:
    print("  NO level-chain composition closes within the kink budget -- the level pool's "
          "positive bend cannot reach 360; the lane needs a design change, not a build")

print("\n== COMPOSITIONS (2-5 maximal runs -> closed ring, coarse view) ==")
cand = sorted([c for c in chains if c["max_run"] >= 8 and not c["closes"]],
              key=lambda c: -c["max_run"])[:16]
# per-run usable numbers: approximate the feasible sub-run's length/bend by scaling
runs = []
for c in cand:
    fr = c["max_run"] / c["n"]
    runs.append(dict(blk=c["blk"], n=c["max_run"], length=round(c["length"] * fr, 1),
                     bend=round(c["bend"] * fr, 1), src=c))
combos = []
for S in (2, 3, 4, 5):
    for combo in itertools.combinations(range(len(runs)), S):
        L = sum(runs[i]["length"] for i in combo)
        R = L / (2 * math.pi)
        if not (R_BAND[0] <= R <= R_BAND[1]):
            continue
        B = sum(runs[i]["bend"] for i in combo)             # SIGNED, traversal forced by
        kink = (360.0 - B) / S                              # nrm-on-right; convex -> +
        lens = sorted(runs[i]["length"] for i in combo)
        poly_ok = lens[-1] < sum(lens[:-1]) if S >= 3 else False
        combos.append(dict(S=S, runs=[runs[i]["blk"] + [runs[i]["n"]] for i in combo],
                           L=round(L, 1), R=round(R, 1), sum_bend=round(B, 1),
                           kink=round(kink, 1), poly_ok=poly_ok))
combos.sort(key=lambda c: abs(c["kink"]))
for c in combos[:12]:
    print(f"  S={c['S']} runs={c['runs']} L={c['L']}u R={c['R']}u sum_bend={c['sum_bend']} "
          f"per-seam kink={c['kink']} deg poly_ok={c['poly_ok']}")
if not combos:
    print("  none in the R band -- widen the run pool or the band")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(dict(chains=chains, combos=combos[:40]), indent=0))
print(f"\nartifact -> {OUT}")
