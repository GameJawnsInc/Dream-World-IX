"""The COAST WINDOW SCANNER -- the coast-morph pillar's catalog builder.

Walks a real block's shore structures -- BEACH waterline runs and CLIFF base runs -- and
emits the lawful morph windows with per-verb depth CEILINGS. The builders are the oracle:
each verb is probed down a depth ladder by calling the real morph function (the offline
gates ARE the law; the scanner re-implements none of it), and a ceiling only counts if
the built tweak set also passes a :func:`transplant.morph_in_place` DRY-RUN (the
in-place frame + bounds gates) -- so every cataloged window deploys as listed via
``world-transplant --in-place``. A verb that refuses at every rung reports its BINDING
refusal (the law that stops the shallowest attempt) instead of a ceiling.

Discovery rules (each the in-game-proven decode):
- beach runs: beach1 boundary verts that are sea2-welded and terrain-free, chained;
  endpoints stepped inward off the block frame; class by THE DEFINITIVE SEAWARD RULE
  (minus the mean per-vert wl->nearest-seam direction -- global centroids flip on
  multi-beach islands, midpoint tests on curved runs).
- cliff runs: the CliffWindow base-edge recipe (topo-58 boundary edges, land- and
  frame-edge-free, Y under the base cap), chained into maximal runs. A maximal run can
  overshoot a lawful window (e.g. into the sea5 shallow ladder), so each verb retries a
  few end-trimmed variants before reporting the refusal.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

from . import transplant as TR
from . import coastmorph as CM
from .coastmorph import _pk
from .extract import decode_id

#: probe ladders, deepest first -- the first rung that builds AND certifies in-place
#: is the verb's ceiling for that window
BEACH_LADDER = (2.5, 2.0, 1.5, 1.0, 0.5)
CLIFF_LADDERS = {
    "cliff-bump": (2.5, 2.0, 1.5, 1.0),
    "cliff-headland": (8.0, 6.0, 4.0, 3.0),
    "cliff-bay": (6.0, 4.0, 3.0, 2.0),
}


def _chain_runs(adj, min_verts=3):
    runs, seen = [], set()
    for k0 in sorted(adj):
        if k0 in seen:
            continue
        run = [k0]
        seen.add(k0)
        for end in (0, -1):
            while True:
                nxts = [nb for nb in adj[run[end]] if nb not in seen]
                if not nxts:
                    break
                seen.add(nxts[0])
                if end == 0:
                    run.insert(0, nxts[0])
                else:
                    run.append(nxts[0])
        if len(run) >= min_verts:
            runs.append(run)
    return runs


def beach_windows(bx, by, *, disc=1, lod="0_1", game=None):
    """The block's beach waterline runs as candidate windows, classified."""
    beach = TR.world_tris(bx, by, "beach1", disc=disc, lod=lod, game=game)
    if not beach:
        return []
    sea2 = TR.world_tris(bx, by, "sea2", disc=disc, lod=lod, game=game)
    terr = TR.world_tris(bx, by, "terrain", disc=disc, lod=lod, game=game)
    r2 = {_pk(v[0]) for t3 in sea2 for v in t3}
    rt = {_pk(v[0]) for t3 in terr for v in t3}
    ec = defaultdict(int)
    pos = {}
    for t3 in beach:
        ps = [v[0] for v in t3]
        for v in t3:
            pos.setdefault(_pk(v[0]), v[0])
        for i in range(3):
            ec[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
    adj_all = defaultdict(list)
    for e, c in ec.items():
        if c == 1:
            a, b = tuple(e)
            adj_all[a].append(b)
            adj_all[b].append(a)
    wk = {k for k in adj_all if k in r2 and k not in rt}
    adj = defaultdict(list)
    for k in wk:
        adj[k] = [nb for nb in adj_all[k] if nb in wk]
    seam = [pos[k] for k in adj_all if k in rt]
    fx0, fx1 = 64.0 * bx, 64.0 * bx + 64.0
    fz0, fz1 = -64.0 * by - 64.0, -64.0 * by
    out = []
    for runk in _chain_runs(adj, min_verts=5):
        run = [pos[k] for k in runk]
        # an ON-frame endpoint cannot anchor a window: step inward
        while len(run) > 4 and min(run[0][0] - fx0, fx1 - run[0][0],
                                   run[0][2] - fz0, fz1 - run[0][2]) < 0.05:
            run = run[1:]
        while len(run) > 4 and min(run[-1][0] - fx0, fx1 - run[-1][0],
                                   run[-1][2] - fz0, fz1 - run[-1][2]) < 0.05:
            run = run[:-1]
        a, b = run[0], run[-1]
        L = math.hypot(b[0] - a[0], b[2] - a[2])
        if L < 14.0 or not seam:
            continue
        sx = sz = 0.0                               # the definitive seaward rule
        for p in run:
            q = min(seam, key=lambda q: math.hypot(p[0] - q[0], p[2] - q[2]))
            d = math.hypot(p[0] - q[0], p[2] - q[2]) or 1.0
            sx += (q[0] - p[0]) / d
            sz += (q[2] - p[2]) / d
        nx, nz = -(b[2] - a[2]) / L, (b[0] - a[0]) / L
        if nx * sx + nz * sz > 0:
            nx, nz = -nx, -nz
        devs = [(q[0] - a[0]) * nx + (q[2] - a[2]) * nz for q in run[1:-1]]
        klass = ("nose" if max(devs) > 0.5 and min(devs) > -0.5 else
                 "pocket" if min(devs) < -0.5 and max(devs) < 0.5 else
                 "mixed" if max(devs) > 0.5 else "straight")
        out.append({"kind": "beach", "cell": (bx, by), "class": klass,
                    "start": (a[0], a[2]), "end": (b[0], b[2]),
                    "L": L, "n": len(run), "devs": (min(devs), max(devs))})
    return out


def cliff_windows(bx, by, *, disc=1, lod="0_1", game=None):
    """The block's cliff base runs as candidate windows (the CliffWindow edge recipe)."""
    terr = TR.world_tris(bx, by, "terrain", disc=disc, lod=lod, game=game)
    topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]
    cliff = [t for t in terr if topo(t) == 58]
    if not cliff:
        return []
    cnt = defaultdict(int)
    pos = {}
    for t3 in cliff:
        ps = [v[0] for v in t3]
        for v in t3:
            pos.setdefault(_pk(v[0]), v[0])
        for i in range(3):
            cnt[frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3])))] += 1
    land_edges = set()
    for t3 in terr:
        if topo(t3) == 58:
            continue
        ps = [v[0] for v in t3]
        for i in range(3):
            land_edges.add(frozenset((_pk(ps[i]), _pk(ps[(i + 1) % 3]))))
    x0, x1 = 64.0 * bx, 64.0 * bx + 64.0
    z0, z1 = -64.0 * by - 64.0, -64.0 * by

    def on_frame(a, b, eps=0.02):
        for ax, lo, hi in ((0, x0, x1), (2, z0, z1)):
            for plane in (lo, hi):
                if abs(a[ax] - plane) < eps and abs(b[ax] - plane) < eps:
                    return True
        return False
    adj = defaultdict(list)
    for e, c in cnt.items():
        if (c == 1 and e not in land_edges and not on_frame(*tuple(e))
                and max(k[1] for k in e) < CM.BASE_Y_MAX):
            a, b = tuple(e)
            adj[a].append(b)
            adj[b].append(a)
    out = []
    for runk in _chain_runs(adj, min_verts=3):
        run = [pos[k] for k in runk]
        L = sum(math.dist(p, q) for p, q in zip(run, run[1:]))
        if L < 12.0:
            continue
        out.append({"kind": "cliff", "cell": (bx, by),
                    "run": [(p[0], p[2]) for p in run],
                    "start": (run[0][0], run[0][2]), "end": (run[-1][0], run[-1][2]),
                    "L": L, "n": len(run)})
    return out


#: refusal classes that are DEPTH-INDEPENDENT (window structure / seam laws) -- one rung
#: settles them; anything else (band/hug/fold/strain/reach envelopes) shrinks with depth
_STRUCTURAL = re.compile(
    r"window gap|outline vert|touches (sea|beach)|no grass mains|"
    r"not a waterline run|not on the waterline chain|uniform 4u lattice|"
    r"z-dominant|south-facing|no beach1|no topo-58|matched waterline/sand|"
    r"has no sand seam|sits on the block frame")


def _probe(builder, cell, start, end, ladder, *, game=None):
    """Walk the ladder deepest-first; the first rung that BUILDS and certifies through a
    morph_in_place dry-run is the ceiling. A STRUCTURAL refusal (window decode / seam
    law -- depth-independent) settles the whole ladder at one rung.
    Returns (ceiling, binding_refusal)."""
    binding = None
    for d in ladder:
        try:
            tweaks = builder(cell, start, end, d, game=game)
        except ValueError as e:
            msg = str(e).splitlines()[0]
            binding = f"D={d:g}: {msg[:110]}"
            if _STRUCTURAL.search(msg):
                break
            continue
        try:
            s = TR.morph_in_place("", cell=cell, tweaks=list(tweaks), game=game,
                                  dry_run=True)
        except ValueError as e:
            binding = f"D={d:g}: in-place: {str(e).splitlines()[0][:100]}"
            continue
        if not s["clean"]:
            bad = next(g for g in s["gates"] if not g.get("ok", True))
            binding = f"D={d:g}: in-place gate {bad['gate']}"
            continue
        return d, binding
    return None, binding


def _probe_cliff(fn, cell, run, ladder, *, game=None, depth_limit=16):
    """Refusal-steered sub-window search over a maximal cliff base run -- the builders'
    POSITIONAL refusals drive the cuts: a ``window gap K`` refusal names the defective
    column gap (a corner, a non-column wall patch), a ``touches seaX ... first at (X,Z)``
    refusal names the vert riding the shallow ladder; split the run there and recurse on
    both halves. A residual non-positional refusal (reach / grass) gets a few end-trimmed
    retries. Returns ``(ceiling, binding, (start, end))``."""
    if len(run) < 3:
        return None, None, None
    best, binding = _probe(fn, cell, run[0], run[-1], ladder, game=game)
    if best is not None:
        return best, binding, (run[0], run[-1])
    cut = None
    m = re.search(r"window gap (\d+)", binding or "")
    if m:
        k = int(m.group(1))
        halves = (run[:k + 1], run[k + 1:])
        cut = True
    else:
        m = re.search(r"first at \((-?[\d.]+),(-?[\d.]+)\)", binding or "")
        if m:
            hx, hz = float(m.group(1)), float(m.group(2))
            i = min(range(len(run)),
                    key=lambda i: (run[i][0] - hx) ** 2 + (run[i][1] - hz) ** 2)
            halves = (run[:i], run[i + 1:])          # the offending vert itself is out
            cut = True
    if cut and depth_limit > 0:
        deep = None
        for half in halves:
            b2, r2, w2 = _probe_cliff(fn, cell, half, ladder, game=game,
                                      depth_limit=depth_limit - 1)
            if b2 is not None and (deep is None or b2 > deep[0]):
                deep = (b2, r2, w2)
        return deep if deep else (None, binding, None)
    for sub in (run[1:], run[:-1], run[1:-1]):
        if len(sub) >= 3:
            b2, r2 = _probe(fn, cell, sub[0], sub[-1], ladder, game=game)
            if b2 is not None:
                return b2, r2, (sub[0], sub[-1])
    return None, binding, None


def scan_block(bx, by, *, verbs=None, disc=1, lod="0_1", game=None):
    """Scan one real block: discovered windows, each with per-verb probed ceilings."""
    verbs = set(verbs or ("beach-bump", "beach-reshape",
                          "cliff-bump", "cliff-headland", "cliff-bay"))
    cell = (bx, by)
    windows = (beach_windows(bx, by, disc=disc, lod=lod, game=game)
               + cliff_windows(bx, by, disc=disc, lod=lod, game=game))
    for w in windows:
        w["probes"] = {}
        if w["kind"] == "beach":
            for verb, fn in (("beach-bump", CM.beach_bump),
                             ("beach-reshape", CM.beach_reshape)):
                if verb not in verbs:
                    continue
                sea, sea_r = _probe(fn, cell, w["start"], w["end"],
                                    BEACH_LADDER, game=game)
                land, land_r = _probe(fn, cell, w["start"], w["end"],
                                      tuple(-d for d in BEACH_LADDER), game=game)
                w["probes"][verb] = {"seaward": sea, "landward": land,
                                     "seaward_binding": sea_r, "landward_binding": land_r,
                                     "window": (w["start"], w["end"])}
        else:
            for verb, ladder in CLIFF_LADDERS.items():
                if verb not in verbs:
                    continue
                fn = {"cliff-bump": CM.cliff_bump, "cliff-headland": CM.cliff_headland,
                      "cliff-bay": CM.cliff_bay}[verb]
                best, binding, win = _probe_cliff(fn, cell, w["run"], ladder, game=game)
                w["probes"][verb] = {"depth": best, "binding": binding, "window": win}
    return windows


def format_catalog(windows, mod_folder="<MOD>"):
    """The human catalog: one block per window, ceilings + a ready-to-run deploy line."""
    lines = []
    for w in windows:
        bx, by = w["cell"]
        if w["kind"] == "beach":
            lines.append(f"({bx},{by}) BEACH  L={w['L']:.1f} n={w['n']} "
                         f"class={w['class']}  devs {w['devs'][0]:+.2f}..{w['devs'][1]:+.2f}")
        else:
            lines.append(f"({bx},{by}) CLIFF  L={w['L']:.1f} n={w['n']}")
        for verb, pr in w.get("probes", {}).items():
            if w["kind"] == "beach":
                parts = []
                for side in ("seaward", "landward"):
                    d = pr[side]
                    if d is not None:
                        parts.append(f"{side} {d:+g}")
                    else:
                        b = pr[f"{side}_binding"] or "no rung probed"
                        parts.append(f"{side} -- ({b})")
                lines.append(f"    {verb}: " + "  |  ".join(parts))
                d = pr["seaward"] if pr["seaward"] is not None else pr["landward"]
                if d is not None:
                    (sxz, exz) = pr["window"]
                    spec = f"{sxz[0]:.4f},{sxz[1]:.4f}:{exz[0]:.4f},{exz[1]:.4f}:{d:g}"
                    lines.append(f"      deploy: ff9mapkit world-transplant --mod-folder "
                                 f"\"{mod_folder}\" --cell {bx},{by} --donor {bx},{by} "
                                 f"--in-place --{verb} \"{spec}\"")
            else:
                if pr["depth"] is not None:
                    (sxz, exz) = pr["window"]
                    spec = (f"{sxz[0]:.4f},{sxz[1]:.4f}:{exz[0]:.4f},{exz[1]:.4f}"
                            f":{pr['depth']:g}")
                    lines.append(f"    {verb}: D={pr['depth']:g}")
                    lines.append(f"      deploy: ff9mapkit world-transplant --mod-folder "
                                 f"\"{mod_folder}\" --cell {bx},{by} --donor {bx},{by} "
                                 f"--in-place --{verb} \"{spec}\"")
                else:
                    lines.append(f"    {verb}: -- ({pr['binding'] or 'no window variant'})")
    return "\n".join(lines)
