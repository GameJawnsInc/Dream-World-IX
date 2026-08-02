"""THE COAST LINT — score the WHOLE walkable boundary for catch risk, then test it.

Registration: COAST-LINT-PREDICTION.md. Flow has only ever been tested at five
spawn points, all beside the corner — and flow is the axis that produced the
V-corner catch. This walks the entire boundary, scores every vertex under the
quantised-fan law, and then HUG-TESTS the flagged sites, because a static score
is a hypothesis and the simulator is the oracle.

  py coast_lint.py [live|staged]        scan + hug-test the flagged sites
  py coast_lint.py live --scan-only     scan only
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from vcorner_crest import hug                               # noqa: E402

FAN = 67.5                      # one hold's quantised deflection budget
HOLDS = [0.0, 22.5, -22.5, 45.0, -45.0]   # plausible player hold headings
CORNER_BBOX = (370.0, 390.0, -532.0, -503.0)
RUNUP = 5.0                     # how far back the traverse test starts


def boundary_adjacency(world):
    """The walkable-boundary graph: vertex -> its boundary neighbours."""
    edge = defaultdict(int)
    for bk in sorted(world):
        for mesh in world[bk]:
            if mesh["name"] != "Terrain":
                continue
            for t in mesh["tris"]:
                if t[4] not in W.WALK_OK:
                    continue
                k = [(round(p[0], 3), round(p[2], 3)) for p in t[:3]]
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    edge[tuple(sorted((k[a], k[b])))] += 1
    adj = defaultdict(set)
    for (a, b), c in edge.items():
        if c == 1:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def boundary_chains(world):
    """Every walkable-boundary chain in the world, as ordered plan polylines."""
    edge = defaultdict(int)
    for bk in sorted(world):
        for mesh in world[bk]:
            if mesh["name"] != "Terrain":
                continue
            for t in mesh["tris"]:
                if t[4] not in W.WALK_OK:
                    continue
                k = [(round(p[0], 3), round(p[2], 3)) for p in t[:3]]
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    edge[tuple(sorted((k[a], k[b])))] += 1
    nxt = defaultdict(set)
    for (a, b), c in edge.items():
        if c == 1:
            nxt[a].add(b)
            nxt[b].add(a)
    seen, chains = set(), []
    for start in sorted(nxt):
        if start in seen:
            continue
        chain, cur, prev = [start], start, None
        seen.add(start)
        while True:
            cand = [q for q in nxt[cur] if q != prev and q not in seen]
            if not cand:
                # allow closing the loop
                if len(chain) > 3 and chain[0] in nxt[cur]:
                    chain.append(chain[0])
                break
            if len(cand) > 1 and prev is not None:           # straightest continuation
                a0 = math.atan2(cur[0] - prev[0], cur[1] - prev[1])
                cand.sort(key=lambda q: abs((math.atan2(q[0] - cur[0], q[1] - cur[1])
                                             - a0 + math.pi) % (2 * math.pi) - math.pi))
            prev, cur = cur, cand[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) > 3:
            chains.append(chain)
    chains.sort(key=len, reverse=True)
    return chains


def score(adj):
    """Per-vertex catch risk, computed from the ADJACENCY, not from a walk.

    The first version scored a walked chain and reported a crop of -180 turns —
    the walk doubling back at forks, not geometry. It condemned shore the owner
    had already accepted, which by the round's own stop rule means the
    instrument is wrong. Scoring each vertex against its own incident boundary
    edges has no walk to go wrong.
    """
    out = []
    for v, ns in adj.items():
        if len(ns) != 2:
            out.append(dict(p=v, turn=None, worst=None, risk=False,
                            fork=len(ns)))
            continue
        p, q = sorted(ns)
        # a traveller arriving p->v and leaving v->q
        h_in = math.degrees(math.atan2(v[0] - p[0], v[1] - p[1])) % 360
        h_out = math.degrees(math.atan2(q[0] - v[0], q[1] - v[1])) % 360
        turn = (h_out - h_in + 180) % 360 - 180
        # MIN, not max: a walker needs only ONE hold that can follow the turn.
        # Scoring the max asks "does some hold fail here", which is true almost
        # everywhere -- it flagged 117 vertices including shore the owner had
        # already accepted, i.e. it was measuring nothing.
        worst = min(abs((h_out - (h_in + hold) + 180) % 360 - 180) for hold in HOLDS)
        out.append(dict(p=v, turn=round(turn, 1), worst=round(worst, 1),
                        risk=worst > FAN, fork=0))
    return out


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "live"
    scan_only = "--scan-only" in sys.argv
    src = {}
    if tag == "staged":
        import vcorner_transplant as VT
        src = dict(VT.staged_src())
    world = W.load_world(part_src=src)
    chains = boundary_chains(world)
    tot = sum(sum(math.dist(c[i], c[i + 1]) for i in range(len(c) - 1)) for c in chains)
    print(f"[{tag}] {len(chains)} boundary chain(s), {sum(len(c) for c in chains)} "
          f"verts, {tot:.0f}u total length")
    for ci, ch in enumerate(chains[:4]):
        L = sum(math.dist(ch[i], ch[i + 1]) for i in range(len(ch) - 1))
        closed = ch[0] == ch[-1]
        print(f"   chain {ci}: {len(ch)} verts, {L:.0f}u, {'CLOSED' if closed else 'open'}")

    adj = boundary_adjacency(world)
    scored = score(adj)
    forks = [s for s in scored if s["fork"] not in (0, 2)]
    print(f"   boundary graph: {len(adj)} verts, {len(forks)} fork/dead-end verts")
    flagged = sorted([s for s in scored if s["risk"]], key=lambda s: -s["worst"])
    print(f"\nSTATIC SCORE: {len(flagged)} vertices at catch risk "
          f"(worst-hold mismatch > {FAN} deg)")
    x0, x1, z0, z1 = CORNER_BBOX
    for s in flagged[:20]:
        where = "CORNER" if (x0 <= s["p"][0] <= x1 and z0 <= s["p"][1] <= z1) else "coast"
        print(f"   {where:6s} ({s['p'][0]:7.2f},{s['p'][1]:8.2f})  turn {s['turn']:+6.1f} "
              f"worst-hold {s['worst']:5.1f}")
    n_corner = sum(1 for s in flagged
                   if x0 <= s["p"][0] <= x1 and z0 <= s["p"][1] <= z1)
    print(f"   ({n_corner} inside the accepted corner, {len(flagged) - n_corner} elsewhere)")
    if scan_only or not flagged:
        return flagged

    print("\nSIMULATOR (the oracle — the static score is only a screen):")
    seen_sites = []
    for s in flagged[:12]:
        px, pz = s["p"]
        # spawn a little inland of the vertex and hold toward it
        best = None
        # A RUN-UP, not a drop-in. Spawning 1.2u from the site caught walkers
        # essentially at the spawn, which measures "is this spot cramped", not
        # "can the coast be traversed". The corner gate that actually predicted
        # a playtest spawns several units back and walks THROUGH.
        #
        # And test the SHORE-FOLLOWING holds, not the compass: a fixed-heading
        # walker stalling inside a concave inlet is expected behaviour, not a
        # defect. What matters is whether the route ALONG the coast is blocked,
        # which is the route a player actually takes -- and it is exactly what
        # the V-corner catch broke.
        ns = sorted(adj.get(s["p"], ()))
        tangents = []
        for q in ns:
            tangents.append(math.atan2(q[0] - px, q[1] - pz))
        holds = [t + d for t in tangents for d in
                 (0.0, math.radians(22.5), math.radians(-22.5))] or \
                [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
        for hold in holds:
            sx = px - RUNUP * math.sin(hold)
            sz = pz - RUNUP * math.cos(hold)
            if not any(t[1] in W.WALK_OK for t in W.all_sheets(world, sx, sz)):
                continue
            r = hug(world, [(sx, sz)], hold, math.radians(22.5),
                    lambda x, z: math.hypot(x - px, z - pz) > 8.0)
            res = r[0][2] if r else "NO-SPAWN"
            if best is None or res.startswith("CAUGHT"):
                best = (hold, res)
            if res.startswith("CAUGHT"):
                break
        if best is None:
            print(f"   ({px:7.2f},{pz:8.2f}): no standable spawn nearby")
            continue
        mark = "  <== CAUGHT" if best[1].startswith("CAUGHT") else ""
        print(f"   ({px:7.2f},{pz:8.2f}) hold {math.degrees(best[0]):5.1f}: "
              f"{best[1]}{mark}")
        seen_sites.append((s["p"], best[1]))
    caught = [s for s in seen_sites if s[1].startswith("CAUGHT")]
    print(f"\nVERDICT: {len(caught)} of {len(seen_sites)} flagged sites actually catch")
    return flagged


if __name__ == "__main__":
    main()
