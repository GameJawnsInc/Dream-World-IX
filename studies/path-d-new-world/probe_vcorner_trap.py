"""THE V-CORNER TRAP PROBE — offline reproduction of the stuck-only-turn walk trap.

Registration: VSHORE-SEAL-PREDICTION.md "THE V-CORNER TRAP REPRODUCTION" (P-A..P-E).
Runs walk_sim's engine-exact query (the decoded fan + two-probe commit) against the
LIVE tuck-build bytes and the pre-deploy pristine control. The trap signature: a
grounded point where EVERY heading (32-step circle) rejects at a commit probe —
turning re-aims the fan, so an all-headings failure is exactly "could only TURN".

Per failing probe the ANSWERING surface is decoded: a mask-reject names the tri that
won the scan (part, buffer index, mapid, topo, cache-vs-scan); a miss is classed
void / step-up / filtered-only / veto-shadow from the raw geometry on the line.

READ-ONLY: no deploy, no bench mutation.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

PIN = (376.5, -509.5)                                       # the owner's trap locus
GC_STALL = (377.2, -502.7)                                  # gC's accepted "open_lawn" stall
TUCK_WEST = (382.1, -508.0)                                 # the tuck chain's west vert
WINDOW = (368.0, 388.0, -516.0, -496.0)                     # x0, x1, z0, z1
GRID = 0.25
HEADINGS = [math.radians(11.25 * k) for k in range(32)]
PREWALL = Path(r"C:\gd\Dream-World-IX\backups\terrace-strip-prewall.20260802-010535")
OUTD = HERE / "out" / "vcorner_trap"


def ring_copy(r):
    if r is None:
        return None
    n = W.Ring()
    n.blocks = list(r.blocks)
    n.mesh_i = list(r.mesh_i)
    n.tri_i = list(r.tri_i)
    n.number = r.number
    return n


def raw_sheets(world, x, z):
    """EVERY geometric intersection on the vertical line — no skip/ny/veto filter.
    (y, topo, mesh_i, ti, mapid, ny), top-down. The miss decoder's evidence."""
    bk = W.block_key(x, z)
    if bk not in world:
        return []
    cell = (int(x // 4), int(z // 4))
    out = []
    for mi, mesh in enumerate(world[bk]):
        for ti in mesh["grid"].get(cell, ()):
            tri = mesh["tris"][ti]
            hy = W.bary_y(x, z, tri)
            if hy is None:
                continue
            out.append((hy, tri[4], mi, ti, tri[3], tri[5]))
    out.sort(key=lambda s: -s[0])
    return out


def check(world, ring, px, py, pz, heading, speed):
    """round_check with the failure decoded. ring is mutated (write-back), pass a copy."""
    nx = px + math.sin(heading) * speed
    nz = pz + math.cos(heading) * speed
    q = W.ground_query(world, ring, nx, nz, py)
    if q is None:
        origin = py + W.OFFSET
        sheets = W.all_sheets(world, nx, nz)
        raw = raw_sheets(world, nx, nz)
        if not raw:
            reason = "miss:void"
        elif any(s[0] <= origin for s in sheets):
            reason = "miss:veto-shadow"                     # passing sheet below origin yet no hit
        elif sheets:
            reason = "miss:step-up"                         # passing sheets exist, all above origin
        else:
            reason = "miss:filtered-only"                   # only skip-mapid/steep sheets cover it
        return dict(ok=False, reason=reason, nx=round(nx, 2), nz=round(nz, 2),
                    raw=[(round(s[0], 2), s[1], world[W.block_key(nx, nz)][s[2]]["name"],
                          s[3], s[4], round(s[5], 3)) for s in raw[:5]])
    if q[4] not in W.WALK_OK:
        bk = W.block_key(nx, nz)
        return dict(ok=False, reason="mask", nx=round(nx, 2), nz=round(nz, 2),
                    surf=dict(part=world[bk][q[0]]["name"], ti=q[1], y=round(q[2], 2),
                              mapid=q[3], topo=q[4], src=q[5]))
    return dict(ok=True, nx=nx, y=q[2], nz=nz)


def probe_heading(world, x, y, z, h, ring):
    """One heading's walk_step branch (two-probe commit), decoded."""
    r = ring_copy(ring)
    r1 = check(world, r, x, y, z, h, W.SPEED)
    if not r1["ok"]:
        r1["stage"] = "p1"
        return r1
    dx, dy, dz = r1["nx"] - x, r1["y"] - y, r1["nz"] - z
    num8 = math.sqrt(dx * dx + dy * dy + dz * dz)
    num9 = W.SPEED * W.SPEED / num8 if num8 > 1e-9 else W.SPEED
    r2 = check(world, r, x, y, z, h, num9)
    if not r2["ok"]:
        r2["stage"] = "p2"
        return r2
    return dict(ok=True, stage="commit")


def fan_test(world, x, z, ring=None, y=None):
    """All 32 headings from a grounded stance; None if not standable."""
    if y is None:
        walk = [s for s in W.all_sheets(world, x, z) if s[1] in W.WALK_OK]
        if not walk:
            return None
        y = max(s[0] for s in walk)                         # top walkable (declared freedom)
    det = []
    n_ok = 0
    for h in HEADINGS:
        r = probe_heading(world, x, y, z, h, ring)
        if r.get("ok"):
            n_ok += 1
        det.append(r)
    return dict(x=round(x, 2), z=round(z, 2), y=round(y, 3), n_ok=n_ok, det=det)


def reason_key(d):
    if d.get("ok"):
        return None
    if d["reason"] == "mask":
        s = d["surf"]
        return f"mask({s['part']}#{s['ti']} mapid={s['mapid']} topo={s['topo']} {s['src']})"
    return d["reason"]


def static_map(world, title):
    """P-A: the fan map over the window. Cold query (ring=None) — the static picture."""
    x0, x1, z0, z1 = WINDOW
    ni = int(round((x1 - x0) / GRID)) + 1
    nj = int(round((z1 - z0) / GRID)) + 1
    traps, cramped, cells = [], [], {}
    reasons = Counter()
    for i in range(ni):
        x = x0 + i * GRID
        for j in range(nj):
            z = z0 + j * GRID
            ft = fan_test(world, x, z)
            if ft is None:
                continue
            cells[(i, j)] = ft["n_ok"]
            if ft["n_ok"] == 0:
                traps.append(ft)
                for d in ft["det"]:
                    reasons[reason_key(d)] += 1
            elif ft["n_ok"] <= 8:
                cramped.append(dict(x=ft["x"], z=ft["z"], y=ft["y"], n_ok=ft["n_ok"]))
    print(f"\n=== STATIC FAN MAP [{title}]: {len(cells)} standable pts, "
          f"{len(traps)} ALL-STALL (trap), {len(cramped)} cramped (<=8 ok) ===")
    if traps:
        dmin = min(math.hypot(t["x"] - PIN[0], t["z"] - PIN[1]) for t in traps)
        xs = [t["x"] for t in traps]; zs = [t["z"] for t in traps]
        print(f"   trap set bbox x [{min(xs)},{max(xs)}] z [{min(zs)},{max(zs)}], "
              f"pin_dmin={dmin:.2f}u")
        print("   trap-probe failure histogram:")
        for k, n in reasons.most_common(12):
            print(f"      {n:5d}  {k}")
    # ASCII map, north (z max) at top; markers: P pin, G gC, T tuck vert
    marks = {}
    for (mx, mz, ch) in (PIN + ("P",), GC_STALL + ("G",), TUCK_WEST + ("T",)):
        marks[(int(round((mx - x0) / GRID)), int(round((mz - z0) / GRID)))] = ch
    print(f"   map ({GRID}u/char, x {x0}->{x1} left->right, z {z1} top -> {z0} bottom;")
    print("        '#'=trap 'x'=cramped '.'=free ' '=not standable; P=pin G=gC T=tuck)")
    for j in range(nj - 1, -1, -1):
        row = []
        for i in range(ni):
            if (i, j) in marks:
                row.append(marks[(i, j)])
            elif (i, j) not in cells:
                row.append(" ")
            else:
                n = cells[(i, j)]
                row.append("#" if n == 0 else ("x" if n <= 8 else "."))
        print("   |" + "".join(row) + "|")
    return traps, cramped, cells


def decode_traps(world, traps, title, limit=4):
    """P-C: at representative trap points, the full stack + every heading's answer."""
    print(f"\n=== TRAP DECODE [{title}] ({min(len(traps), limit)} of {len(traps)}) ===")
    offenders = Counter()
    for t in traps:
        for d in t["det"]:
            k = reason_key(d)
            if k and k.startswith("mask"):
                offenders[(d["surf"]["part"], d["surf"]["ti"], d["surf"]["mapid"],
                           d["surf"]["topo"])] += 1
    # representative points: nearest to the pin first
    traps = sorted(traps, key=lambda t: math.hypot(t["x"] - PIN[0], t["z"] - PIN[1]))
    for t in traps[:limit]:
        print(f"   trap at ({t['x']},{t['z']}) standing y={t['y']}:")
        for s in raw_sheets(world, t["x"], t["z"])[:6]:
            bk = W.block_key(t["x"], t["z"])
            print(f"      line: y={s[0]:7.2f} topo={s[1]:3d} {world[bk][s[2]]['name']:8s}"
                  f"#{s[3]:<5d} mapid={s[4]:5d} ny={s[5]: .3f}")
        per = Counter(reason_key(d) for d in t["det"])
        for k, n in per.most_common(6):
            print(f"      fan: {n:2d}/32 {k}")
    if offenders:
        print("   mask offender tris (tri verts in world frame):")
        bk = W.block_key(PIN[0], PIN[1])
        for (part, ti, mapid, topo), n in offenders.most_common(6):
            mi = next(i for i, m in enumerate(world[bk]) if m["name"] == part)
            tri = world[bk][mi]["tris"][ti]
            vs = " ".join(f"({v[0]:.1f},{v[1]:.2f},{v[2]:.1f})" for v in (tri[0], tri[1], tri[2]))
            print(f"      {n:5d}x {part}#{ti} mapid={mapid} topo={topo} ny={tri[5]:.3f} {vs}")
    return offenders


def drive_walkers(world, title):
    """P-B: walkers driven at the pin (seek + fixed crossings); on stall, the escape
    test with the walker's OWN poisoned ring vs a COLD query."""
    events = []
    for mode in ("seek", "fixed"):
        for hk in range(16):
            th = 2 * math.pi * hk / 16
            for r0 in (8.0, 14.0, 20.0):
                sx, sz = PIN[0] - r0 * math.sin(th), PIN[1] - r0 * math.cos(th)
                walk = [s for s in W.all_sheets(world, sx, sz) if s[1] in W.WALK_OK]
                if len(walk) != 1:
                    continue
                st = dict(x=sx, y=walk[0][0], z=sz, heading=th)
                ring = W.Ring()
                for k in range(200):
                    if mode == "seek":
                        st["heading"] = math.atan2(PIN[0] - st["x"], PIN[1] - st["z"])
                    ev = W.walk_step(world, ring, st)
                    if ev == "stall":
                        own = fan_test(world, st["x"], st["z"], ring=ring, y=st["y"])
                        cold = fan_test(world, st["x"], st["z"], ring=None, y=st["y"])
                        events.append(dict(mode=mode, hd=hk, r0=r0, step=k,
                                           x=round(st["x"], 2), z=round(st["z"], 2),
                                           y=round(st["y"], 2),
                                           own=own["n_ok"], cold=cold["n_ok"]))
                        break
                    if mode == "seek" and math.hypot(PIN[0] - st["x"], PIN[1] - st["z"]) < 0.4:
                        break
                    if mode == "fixed" and math.hypot(st["x"] - sx, st["z"] - sz) > r0 + 12.0:
                        break
    hard = [e for e in events if e["own"] == 0 and e["cold"] == 0]
    ringy = [e for e in events if e["own"] == 0 and e["cold"] > 0]
    print(f"\n=== WALKERS [{title}]: {len(events)} stalls, {len(hard)} HARD-TRAPPED "
          f"(0 escape headings, own AND cold ring), {len(ringy)} ring-poisoned ===")
    for e in events[:14]:
        print(f"   {e['mode']:5s} hd={e['hd']:2d} r0={e['r0']:4.1f} step={e['step']:3d} "
              f"at ({e['x']:6.2f},{e['z']:7.2f}) y={e['y']:5.2f} "
              f"escape own={e['own']:2d} cold={e['cold']:2d}")
    return events, hard, ringy


def gc_reexam(world):
    """P-E: gC's open_lawn classifier vs the commit test at its accepted stall."""
    x, z = GC_STALL
    walk = [s for s in W.all_sheets(world, x, z) if s[1] in W.WALK_OK]
    if not walk:
        print(f"\n=== gC RE-EXAM: ({x},{z}) not standable on these bytes ===")
        return dict(standable=False)
    y = max(s[0] for s in walk)
    open_lawn = True                                        # walk_gate_fix's classifier verbatim
    for aa in range(8):
        ax = x + math.sin(math.pi * aa / 4)
        az = z + math.cos(math.pi * aa / 4)
        sh2 = W.all_sheets(world, ax, az)
        w2 = [s for s in sh2 if s[1] in W.WALK_OK]
        if len(w2) != 1 or abs(w2[0][0] - y) > 2.0 or len(sh2) != len(w2):
            open_lawn = False
            break
    ft = fan_test(world, x, z, y=y)
    per = Counter(reason_key(d) for d in ft["det"] if not d.get("ok"))
    print(f"\n=== gC RE-EXAM at ({x},{z}) y={y:.2f}: open_lawn={open_lawn}, "
          f"commit-test n_ok={ft['n_ok']}/32 ===")
    for k, n in per.most_common(6):
        print(f"   {n:2d}/32 {k}")
    return dict(standable=True, open_lawn=open_lawn, n_ok=ft["n_ok"],
                reasons={k: n for k, n in per.items()})


def main():
    OUTD.mkdir(parents=True, exist_ok=True)
    print("loading LIVE world (the tuck build) ...")
    live = W.load_world()
    for bk in sorted(live):
        print(f"   block {bk}: " + ", ".join(f"{m['name']}({len(m['tris'])})" for m in live[bk]))

    traps, cramped, cells = static_map(live, "LIVE tuck build")
    offenders = decode_traps(live, traps, "LIVE") if traps else Counter()
    events, hard, ringy = drive_walkers(live, "LIVE")
    gc = gc_reexam(live)

    print("\nloading PRE-TUCK pristine control (terrace-strip-prewall.20260802-010535) ...")
    tsrc = {}
    for (bx, by) in W.CELLS:
        p = PREWALL / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            tsrc[(bx, by)] = p
    print(f"   pristine Terrain files: {len(tsrc)}/6")
    pris = W.load_world(terrain_src=tsrc)
    p_traps, p_cramped, _ = static_map(pris, "PRE-TUCK pristine")
    p_offenders = decode_traps(pris, p_traps, "PRE-TUCK") if p_traps else Counter()
    p_events, p_hard, p_ringy = drive_walkers(pris, "PRE-TUCK")

    print("\n=== VERDICT (scored against the registration) ===")
    pa = len(traps) > 0 and min(math.hypot(t["x"] - PIN[0], t["z"] - PIN[1])
                                for t in traps) <= 2.0
    pb = len(hard) > 0
    pd_clean = len(p_traps) == 0 and len(p_hard) == 0
    print(f"   P-A static trap set within 2u of the pin: {'PASS' if pa else 'FAIL'}")
    print(f"   P-B walkers hard-trapped (static class):  {'PASS' if pb else 'FAIL'}"
          f"   (ring-poisoned stalls: {len(ringy)})")
    print(f"   P-D pre-tuck pristine clean:              "
          f"{'CLEAN -> this round authored it' if pd_clean else 'TRAPPED -> older authorship'}"
          f"   (pre-tuck traps={len(p_traps)}, hard={len(p_hard)})")

    json.dump(dict(
        traps=[dict(x=t["x"], z=t["z"], y=t["y"],
                    reasons={k: n for k, n in
                             Counter(reason_key(d) for d in t["det"]).items()})
               for t in traps],
        cramped_n=len(cramped), events=events,
        hard_n=len(hard), ringy_n=len(ringy), gc=gc,
        pretuck=dict(traps_n=len(p_traps), hard_n=len(p_hard),
                     traps=[dict(x=t["x"], z=t["z"], y=t["y"]) for t in p_traps[:50]]),
        offenders={f"{k[0]}#{k[1]} mapid={k[2]} topo={k[3]}": n
                   for k, n in offenders.most_common(12)},
    ), open(OUTD / "report.json", "w"), indent=1)
    print(f"\nreport: {OUTD / 'report.json'}")


if __name__ == "__main__":
    main()
