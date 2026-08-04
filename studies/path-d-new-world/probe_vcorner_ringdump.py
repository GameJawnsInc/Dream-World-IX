"""THE V-CORNER RING DUMP — P-C: name the surface answering the poisoned probes.

Replays one deterministically trapped walker (fixed heading due south, spawn 8u north
of the pin — probe_vcorner_trap's fixed hd=8 r0=8 case), then at the stall dumps:
the 10-slot ring's contents, the answering slot per heading (cache introspection),
the permanence check (does a full scan EVER fire again = can the ring refresh), and
the poisoning tris' full geometry so the authored element can be named. Runs on the
LIVE tuck build and the PRE-TUCK pristine. READ-ONLY.
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from probe_vcorner_trap import PIN, PREWALL, ring_copy      # noqa: E402

HEADINGS = [math.radians(11.25 * k) for k in range(32)]


def ring_dump(world, ring, tag):
    print(f"   ring [{tag}] (slot order newest={ring.number}):")
    for s in range(10):
        bk = ring.blocks[s]
        if bk is None:
            print(f"      slot {s}: empty")
            continue
        mesh = world[bk][ring.mesh_i[s]]
        tri = mesh["tris"][ring.tri_i[s]]
        vs = " ".join(f"({v[0]:.2f},{v[1]:.2f},{v[2]:.2f})" for v in (tri[0], tri[1], tri[2]))
        walkable = "WALK" if tri[4] in W.WALK_OK else "BLOCK"
        print(f"      slot {s}: blk{bk} {mesh['name']}#{ring.tri_i[s]} mapid={tri[3]} "
              f"topo={tri[4]} [{walkable}] ny={tri[5]:.3f} {vs}")


def cache_probe(world, ring, x, z, origin_y):
    """ground_query's cache pass with introspection: (probe_i, slot, name, ti, hy, mapid, topo)."""
    bk = W.block_key(x, z)
    for i in range(10):
        s = (ring.number + i) % 10
        if ring.blocks[s] != bk:
            continue
        mesh = world[bk][ring.mesh_i[s]]
        tri = mesh["tris"][ring.tri_i[s]]
        hy = W.bary_y(x, z, tri)
        if hy is None or hy > origin_y:
            continue
        if tri[3] == W.VETO:
            continue
        return (i, s, mesh["name"], ring.tri_i[s], hy, tri[3], tri[4])
    return None


def heading_decode(world, ring, st):
    """Per heading: who answers p1 (cache slot or scan), verdict. Poison census."""
    poison = Counter()
    n_commit = 0
    print("   per-heading answers (p1 at speed 0.4375):")
    rows = []
    for k, h in enumerate(HEADINGS):
        nx = st["x"] + math.sin(h) * W.SPEED
        nz = st["z"] + math.cos(h) * W.SPEED
        origin = st["y"] + W.OFFSET
        cp = cache_probe(world, ring_copy(ring), nx, nz, origin)
        if cp is not None:
            i, s, name, ti, hy, mapid, topo = cp
            ok = topo in W.WALK_OK
            rows.append((k, f"cache slot {s} {name}#{ti} topo={topo} y={hy:.2f} "
                            f"{'-> WALKABLE' if ok else '-> MASK-REJECT'}"))
            if not ok:
                poison[(name, ti, mapid, topo)] += 1
            else:
                n_commit += 1                               # would proceed to p2
            continue
        fs = W.full_scan(world, W.block_key(nx, nz), nx, nz, origin)
        if fs is None:
            rows.append((k, "scan MISS"))
        else:
            mi, ti, hy, mapid, topo = fs
            ok = topo in W.WALK_OK
            name = world[W.block_key(nx, nz)][mi]["name"]
            rows.append((k, f"scan {name}#{ti} topo={topo} y={hy:.2f} "
                            f"{'-> WALKABLE' if ok else '-> MASK-REJECT'}"))
            if ok:
                n_commit += 1
    for k, msg in rows:
        print(f"      h{k:2d} ({11.25 * k:6.2f}deg): {msg}")
    print(f"   headings that would pass p1: {n_commit}/32")
    if poison:
        print("   POISONING TRIS (cache answers that mask-reject):")
        bk = W.block_key(st["x"], st["z"])
        for (name, ti, mapid, topo), n in poison.most_common():
            mi = next(i for i, m in enumerate(world[bk]) if m["name"] == name)
            tri = world[bk][mi]["tris"][ti]
            vs = " ".join(f"({v[0]:.2f},{v[1]:.2f},{v[2]:.2f})" for v in (tri[0], tri[1], tri[2]))
            print(f"      {n:2d}/32 {name}#{ti} mapid={mapid} topo={topo} ny={tri[5]:.3f} {vs}")
    return poison


def replay(world, title):
    th = math.pi                                            # due south, the hd=8 case
    sx, sz = PIN[0], PIN[1] + 8.0
    walk = [s for s in W.all_sheets(world, sx, sz) if s[1] in W.WALK_OK]
    assert len(walk) == 1, f"spawn not clean lawn: {walk}"
    st = dict(x=sx, y=walk[0][0], z=sz, heading=th)
    ring = W.Ring()
    print(f"\n=== REPLAY [{title}]: spawn ({sx},{sz}) y={st['y']:.2f}, heading south ===")
    stalled = None
    for k in range(200):
        before = (list(ring.blocks), list(ring.mesh_i), list(ring.tri_i), ring.number)
        ev = W.walk_step(world, ring, st)
        after = (list(ring.blocks), list(ring.mesh_i), list(ring.tri_i), ring.number)
        if before != after:
            s = ring.number
            mesh = world[ring.blocks[s]][ring.mesh_i[s]]
            tri = mesh["tris"][ring.tri_i[s]]
            walkable = "WALK" if tri[4] in W.WALK_OK else "BLOCK"
            print(f"   step {k:3d} {ev:7s} at ({st['x']:6.2f},{st['z']:7.2f}) y={st['y']:.2f} "
                  f"| ring+= slot {s}: {mesh['name']}#{ring.tri_i[s]} topo={tri[4]} [{walkable}]")
        if ev == "stall":
            stalled = k
            print(f"   step {k:3d} STALL at ({st['x']:6.2f},{st['z']:7.2f}) y={st['y']:.2f}")
            break
    if stalled is None:
        print("   NO STALL in 200 steps -- replay failed")
        return
    ring_dump(world, ring, f"at stall, step {stalled}")
    poison = heading_decode(world, ring, st)

    # permanence: does any full scan ever fire again? (a full scan would change the
    # ring on a hit; also spin the fan another 100 ticks and watch for movement)
    moved = False
    before = (list(ring.blocks), list(ring.mesh_i), list(ring.tri_i), ring.number)
    for k in range(100):
        st["heading"] = HEADINGS[k % 32]                    # the player turning in place
        ev = W.walk_step(world, ring, st)
        if ev != "stall":
            moved = True
            print(f"   ESCAPED after {k} extra ticks heading {math.degrees(st['heading']):.1f}")
            break
    after = (list(ring.blocks), list(ring.mesh_i), list(ring.tri_i), ring.number)
    print(f"   PERMANENCE: 100 turning ticks -> {'ESCAPED' if moved else 'still stuck'}; "
          f"ring {'CHANGED (a full scan fired)' if before != after else 'FROZEN (cache answered everything)'}")
    return poison


def main():
    print("loading LIVE world (the tuck build) ...")
    live = W.load_world()
    replay(live, "LIVE tuck build")

    print("\nloading PRE-TUCK pristine control ...")
    tsrc = {}
    for (bx, by) in W.CELLS:
        p = PREWALL / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            tsrc[(bx, by)] = p
    pris = W.load_world(terrain_src=tsrc)
    replay(pris, "PRE-TUCK pristine")


if __name__ == "__main__":
    main()
