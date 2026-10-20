"""``world-river``: carry a stock river and its cove onto a kit island (``studies/terrain-malleability/watercarry/``,
PLAN.md -- the owner-signed build plan; RECON.md holds the evidence).

This module is RUNG 0: the FRAGMENT -- exactly what is carried verbatim -- and the two topology gates that decide it
is lawful. Nothing here writes; the composition (mint, opening, zip, joins, water knit, binding) is later rungs.

The fragment, built only from the stock bytes:

* THE UNIT -- the river's water parts (Stream / River / RiverJoint / Falls) in the donor's unit blocks, plus every
  Terrain tri of the channel's topographs (62 banks, 48/50/51 the Terrain's own water markers -- one closes the source)
  and every Object tri, welded to them transitively (THE ENSEMBLE IS WIDER THAN THE PARTS: cluster C's 40-tri bridge).
* THE COVE -- the sea and beach the river empties into, flooded edge to edge from the river's mouth and closed by the
  SEAWARD BOUNDARY: the cheapest path between the two join bases along edges with deep water (Sea3/4/5) on both
  sides, through vertices touching only deep water (THE STRICT SHORE LAW -- shallows are shore-bound). Every island
  standing in the bay is TETHERED to the mouth by a water corridor the path may not touch, so the path must go round
  it seaward (RECON R1 round 4: the straight chord cut cluster C's island in half).
* THE COASTAL ASSEMBLY -- the cliff lip (topo 58) welded to the cove, grown along the coast edge to edge and stopped
  at the two JOIN COLUMNS (the stock wall edges where the kit's minted cliff will meet the stock lips), plus the one
  row of sand (topo 31) backing it.
* THE ISLANDS -- every land component whose shore touches the cove, taken WHOLE.

The gates (each refusal names its gate and the points where it fails -- the overworld-editor habit):

* F1 COMPONENT CLOSURE -- no forest, rock, Object, building, beach or island component is partly inside; a lip strip
  is cut only at a join column.
* F2 SHORE SCOPE -- the seaward boundary has deep water on both sides of every edge and touches no shallow or beach.
"""
from __future__ import annotations

import heapq
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np

from . import extract as X
from .interior import kk3

RIVER_PARTS = ("stream", "riverjoint", "river", "falls")
SEA_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5")
DEEP = frozenset(("sea3", "sea4", "sea5"))
BEACH = "beach1"
WATER = frozenset(SEA_PARTS + (BEACH,))                   # what the cove floods
LAND_PARTS = frozenset(("terrain", "object", BEACH))      # what a land component is made of
READ_PARTS = ("terrain", "object", BEACH) + SEA_PARTS + RIVER_PARTS
CHANNEL_TOPOS = frozenset((62, 48, 50, 51))               # the banks + the Terrain's own channel markers
LIP, SAND = 58, 31
FOREST, ROCK, BUILDING = frozenset((36, 37)), frozenset((49, 7)), frozenset((59,))
JOIN_TOL = 0.05                                           # a donor join point -> its stock vertex


@dataclass(frozen=True)
class RiverDonor:
    """A catalogued river donor (``world/data/donors.toml`` class ``river``; the drift test pins these literals).

    ``window`` is the stock read, ``((bx0, bx1), (by0, by1))`` inclusive; ``unit_blocks`` seed the river's parts;
    ``joins`` names each join column as ``(name, crest, base)`` stock points (2 dp; resolved to the exact vertex)."""
    name: str
    blocks: str
    window: tuple
    unit_blocks: tuple
    joins: tuple
    disc: int = 1


# The lowland river at (16,14)-(17,15) and its beached cove (RECON.md R1). The join columns sit at the kit's 3.2 crest
# (lips.py): E on the headland tip, W on the cove's south-west shore.
CLUSTER_C = RiverDonor(
    name="cluster-c", blocks="16-17,14-15", window=((13, 19), (12, 17)),
    unit_blocks=((16, 14), (16, 15), (17, 14)),
    joins=(("W", (1039.77, 3.29, -1084.39), (1040.0, 0.0, -1083.34)),
           ("E", (1140.46, 3.11, -1028.0), (1141.11, 0.0, -1028.0))))

RIVER_DONORS = {CLUSTER_C.name: CLUSTER_C}


class RiverRefused(ValueError):
    """A gate refused the carry. ``gate`` names it; ``where`` lists the plan points ``(x, z)`` where it fails."""

    def __init__(self, gate: str, msg: str, where=()):
        self.gate, self.where = gate, [(round(float(x), 2), round(float(z), 2)) for x, z in where]
        at = "; at " + ", ".join(f"({x}, {z})" for x, z in self.where[:6]) if self.where else ""
        more = f" (+{len(self.where) - 6} more)" if len(self.where) > 6 else ""
        super().__init__(f"{gate}: {msg}{at}{more}")


@dataclass
class Fragment:
    """What ``world-river`` carries, verbatim, and how its edge meets the world it leaves.

    ``tris`` are the stock tri dicts (part, P world, uv, nrm, tan, idall, topo, blk), untouched. ``boundary`` maps
    each class -- ``join`` (the two column edges), ``water`` (the seaward boundary: the knit), ``source`` (where the
    channel meets rock), ``lawn`` (the zip), ``open`` (nothing across) -- to its edges as exact point pairs.
    ``seaward`` is the seaward boundary's points, W join base to E join base."""
    donor: RiverDonor
    tris: list
    boundary: dict
    joins: dict
    seaward: list
    report: dict = field(default_factory=dict)


# ---- reading ------------------------------------------------------------------------------------------------------

def block_tris(bm, bx: int, by: int, part: str) -> list:
    """One decoded block part -> world-frame tri dicts, every channel verbatim (float64 of the float32 bytes, plus
    the block's integer origin -- exact, so the bytes are recoverable)."""
    V = np.asarray(bm.verts, dtype=float) + np.array([64.0 * bx, 0.0, -64.0 * by])
    ch = bm.chan_arrays
    U = np.asarray(ch[X.CH_UV], dtype=float) if X.CH_UV in ch else None
    N = np.asarray(ch[X.CH_NRM], dtype=float) if X.CH_NRM in ch else None
    T = np.asarray(ch[X.CH_TAN], dtype=float) if X.CH_TAN in ch else None
    out = []
    for t in bm.tris:
        t = list(t)
        idall = int(round(T[t[0]][0])) if T is not None else 0
        out.append({"blk": (bx, by), "part": part, "P": V[t], "uv": None if U is None else U[t],
                    "nrm": None if N is None else N[t], "tan": None if T is None else T[t],
                    "idall": idall, "topo": X.decode_id(idall)["topograph"]})
    return out


def read_window(donor: RiverDonor, *, game=None) -> list:
    """Every tri of the donor's window, in the parts the fragment and its gates look at."""
    bp = X.block_parts(disc=donor.disc, game=game)
    (bx0, bx1), (by0, by1) = donor.window
    out = []
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            for part in READ_PARTS:
                if part in bp.get((bx, by), ()):
                    out += block_tris(X.read_block(bx, by, disc=donor.disc, part=part, game=game), bx, by, part)
    return out


def fragment(donor: RiverDonor = CLUSTER_C, *, game=None) -> Fragment:
    """The donor's fragment from the user's install, gated (F1, F2). Raises :class:`RiverRefused`."""
    return build_fragment(read_window(donor, game=game), donor)


# ---- the mesh index -----------------------------------------------------------------------------------------------

def _ek(a, b):
    return (a, b) if a <= b else (b, a)


def tri_class(t) -> str:
    part = t["part"]
    if part in RIVER_PARTS:
        return "river"
    if part in SEA_PARTS:
        return "water"
    if part == BEACH:
        return "beach"
    if part == "object":
        return "object"
    topo = t["topo"]
    if topo in CHANNEL_TOPOS:
        return "channel"
    if topo == LIP:
        return "lip"
    if topo == SAND:
        return "sand"
    if topo in FOREST:
        return "forest"
    if topo in ROCK:
        return "rock"
    if topo in BUILDING:
        return "building"
    return "ground"


class _Mesh:
    """Shared-vertex / shared-edge adjacency over a tri soup, keyed by ``kk3`` (the kit's 1e-3 weld key)."""

    def __init__(self, tris):
        self.tris = tris
        self.cls = [tri_class(t) for t in tris]
        self.keys = [tuple(kk3(p) for p in t["P"]) for t in tris]
        self.exact = {}
        self.by_vert = defaultdict(list)
        self.by_edge = defaultdict(list)
        for i, (t, ks) in enumerate(zip(tris, self.keys)):
            for p, k in zip(t["P"], ks):
                self.exact.setdefault(k, tuple(float(c) for c in p))
                self.by_vert[k].append(i)
            for e in self.edges(i):
                self.by_edge[e].append(i)

    def edges(self, i):
        ks = self.keys[i]
        return [_ek(ks[a], ks[b]) for a, b in ((0, 1), (1, 2), (2, 0)) if ks[a] != ks[b]]

    def across(self, i):
        """``(edge, j)`` for every tri ``j`` sharing an edge with tri ``i``."""
        for e in self.edges(i):
            for j in self.by_edge[e]:
                if j != i:
                    yield e, j

    def centroid(self, idx):
        P = np.concatenate([self.tris[i]["P"] for i in idx])
        return float(P[:, 0].mean()), float(P[:, 2].mean())


def _components(M: _Mesh, members) -> dict:
    """Union-find over ``members`` (tri indices) by shared vertex -> ``{tri: root}``."""
    members = set(members)
    par = {i: i for i in members}

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in members:
        for k in M.keys[i]:
            for j in M.by_vert[k]:
                if j in members:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        par[rj] = ri
    return {i: find(i) for i in members}


def _groups(comp: dict) -> dict:
    g = defaultdict(set)
    for i, r in comp.items():
        g[r].add(i)
    return g


def _once_edges(M: _Mesh, frag) -> dict:
    """The fragment's boundary: ``{edge: inside tri}`` for every edge exactly one fragment tri has."""
    seen = defaultdict(list)
    for i in frag:
        for e in M.edges(i):
            seen[e].append(i)
    return {e: v[0] for e, v in seen.items() if len(v) == 1}


def _mid(e):
    return ((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2)


# ---- the pieces ---------------------------------------------------------------------------------------------------

def river_unit(M: _Mesh, unit_blocks) -> set:
    """THE UNIT: the water parts in ``unit_blocks`` plus the channel Terrain and Object tris welded to them,
    transitively (``seat_dryrun.unit`` promoted)."""
    blocks = {tuple(b) for b in unit_blocks}
    unit = {i for i, t in enumerate(M.tris) if t["part"] in RIVER_PARTS and t["blk"] in blocks}
    keys = {k for i in unit for k in M.keys[i]}
    left = {i for i, t in enumerate(M.tris) if t["blk"] in blocks
            and ((t["part"] == "terrain" and t["topo"] in CHANNEL_TOPOS) or t["part"] == "object")}
    changed = True
    while changed:
        changed = False
        for i in sorted(left):
            if any(k in keys for k in M.keys[i]):
                unit.add(i)
                left.discard(i)
                keys.update(M.keys[i])
                changed = True
    return unit


def resolve_join(M: _Mesh, name, crest, base):
    """A donor join (2-dp points) -> its exact stock column edge ``(crest_key, base_key)``: both points must name a
    stock vertex within ``JOIN_TOL``; the two must share an edge of two lip tris (a wall column); the base must touch
    water and the crest must not."""
    def vert(p, what):
        hits = [k for k in M.by_vert if abs(k[0] - p[0]) <= JOIN_TOL and abs(k[1] - p[1]) <= JOIN_TOL
                and abs(k[2] - p[2]) <= JOIN_TOL]
        if len(hits) != 1:
            raise RiverRefused("J0", f"join {name}'s {what} names {len(hits)} stock vertices, not one",
                               [(p[0], p[2])])
        return hits[0]
    c, b = vert(crest, "crest"), vert(base, "base")
    walls = [i for i in M.by_edge.get(_ek(c, b), ()) if M.cls[i] == "lip"]
    if len(walls) != 2:
        raise RiverRefused("J0", f"join {name} is not a stock wall column ({len(walls)} lip tris share it)",
                           [(base[0], base[2])])
    wet = lambda k: any(M.tris[j]["part"] in WATER for j in M.by_vert[k])   # noqa: E731
    if not wet(b) or wet(c):
        raise RiverRefused("J0", f"join {name}'s base must touch water and its crest must not (base wet: {wet(b)}, "
                           f"crest wet: {wet(c)})", [(base[0], base[2])])
    return c, b


def mouth_tris(M: _Mesh, unit) -> set:
    """The sea / beach tris across the unit's boundary: where the river empties."""
    return {j for e, i in _once_edges(M, unit).items() for j in M.by_edge[e]
            if j not in unit and M.tris[j]["part"] in WATER}


def _frame(M: _Mesh):
    xs = [k[0] for k in M.by_vert]
    zs = [k[2] for k in M.by_vert]
    return min(xs), max(xs), min(zs), max(zs)


def _on_frame(k, fr, tol=1e-3):
    return abs(k[0] - fr[0]) < tol or abs(k[0] - fr[1]) < tol or abs(k[2] - fr[2]) < tol or abs(k[2] - fr[3]) < tol


def land_islands(M: _Mesh, unit):
    """The land components (terrain / object / beach by shared vertex): ``(comp, mainland_roots, islands)`` --
    the mainland is every component the river runs through or the window cuts; an island is any other."""
    comp = _components(M, [i for i, t in enumerate(M.tris) if t["part"] in LAND_PARTS])
    fr = _frame(M)
    mainland = {comp[i] for i in unit if i in comp}
    for i, r in comp.items():
        if r not in mainland and any(_on_frame(k, fr) for k in M.keys[i]):
            mainland.add(r)
    islands = {r: g for r, g in _groups(comp).items() if r not in mainland}
    return comp, mainland, islands


def _tether(M: _Mesh, island, mouth):
    """The cheapest water corridor (tris, edge-adjacent, centroid distance) from the island's shore to the mouth,
    or None when the island stands in another water body."""
    keys = {k for i in island for k in M.keys[i]}
    src = {j for k in keys for j in M.by_vert[k] if M.tris[j]["part"] in WATER and j not in island}
    if not src:
        return None
    cen = {}

    def c(i):
        if i not in cen:
            cen[i] = M.tris[i]["P"].mean(axis=0)
        return cen[i]
    dist, prev, pq = {}, {}, []
    for s in src:
        dist[s] = 0.0
        heapq.heappush(pq, (0.0, s))
    while pq:
        d, i = heapq.heappop(pq)
        if d > dist.get(i, math.inf):
            continue
        if i in mouth:
            path = [i]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return path
        for _e, j in M.across(i):
            if M.tris[j]["part"] not in WATER or j in island:
                continue
            nd = d + float(np.linalg.norm(c(i)[[0, 2]] - c(j)[[0, 2]]))
            if nd < dist.get(j, math.inf):
                dist[j], prev[j] = nd, i
                heapq.heappush(pq, (nd, j))
    return None


def seaward_boundary(M: _Mesh, w_base, e_base, forbidden=frozenset()):
    """THE SEAWARD BOUNDARY: the cheapest vertex path W base -> E base along edges with exactly two tris, both deep,
    through vertices every tri of which is deep (the bases excepted) and none ``forbidden`` (the tethers). F2 refuses
    when no such route exists -- the mouth is barred by shallows."""
    def ok_vert(k):
        if k in (w_base, e_base):
            return True
        return k not in forbidden and all(M.tris[j]["part"] in DEEP for j in M.by_vert[k])
    nbr = defaultdict(list)
    for e, ts in M.by_edge.items():
        if len(ts) == 2 and all(M.tris[j]["part"] in DEEP for j in ts) and ok_vert(e[0]) and ok_vert(e[1]):
            L = math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])
            nbr[e[0]].append((e[1], L))
            nbr[e[1]].append((e[0], L))
    dist, prev, pq = {w_base: 0.0}, {}, [(0.0, w_base)]
    while pq:
        d, k = heapq.heappop(pq)
        if d > dist.get(k, math.inf):
            continue
        if k == e_base:
            path = [k]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return path[::-1], d
        for n, L in nbr[k]:
            if d + L < dist.get(n, math.inf):
                dist[n], prev[n] = d + L, k
                heapq.heappush(pq, (d + L, n))
    near = min(dist, key=lambda k: math.hypot(k[0] - e_base[0], k[2] - e_base[2]))
    raise RiverRefused("F2", "no deep-water route closes the cove: shallows bar its mouth (the reachable deep water "
                       "from the W join base ends at the point named)",
                       [(w_base[0], w_base[2]), (near[0], near[2]), (e_base[0], e_base[2])])


def cove_flood(M: _Mesh, mouth, cut_edges) -> set:
    """THE COVE: water and beach flooded edge to edge from the mouth, never across a seaward-boundary edge. The cove
    must be CLOSED: a flooded tri with nothing across one of its edges (the window's frame, or a prefab-less open-sea
    block) means the boundary leaks."""
    cove, stack = set(mouth), list(mouth)
    while stack:
        i = stack.pop()
        for e in M.edges(i):
            if e in cut_edges:
                continue
            if len(M.by_edge[e]) == 1:
                raise RiverRefused("F2", "the cove leaks: its water runs past the seaward boundary to an edge with "
                                   "nothing across", [_mid(e)])
            for j in M.by_edge[e]:
                if j not in cove and M.tris[j]["part"] in WATER:
                    cove.add(j)
                    stack.append(j)
    return cove


def coastal_assembly(M: _Mesh, cove, join_edges) -> set:
    """THE COASTAL ASSEMBLY: lip tris welded edge to edge to the cove, grown along the coast and stopped at the join
    columns, plus the one row of sand cells backing the lip or the beach."""
    lips, stack = set(), list(cove)
    while stack:
        i = stack.pop()
        for e, j in M.across(i):
            if e in join_edges or j in lips or j in cove or M.cls[j] != "lip":
                continue
            lips.add(j)
            stack.append(j)
    sand = {j for i in cove | lips for e, j in M.across(i) if e not in join_edges and M.cls[j] == "sand"}
    # square the row into whole cells: each sand tri's quad partner (the sand tri across its longest edge, the cell's
    # diagonal) -- a row of lone tris is a sawtooth against the zip
    for i in list(sand):
        e = max(M.edges(i), key=lambda e: math.dist(e[0], e[1]))
        sand.update(j for j in M.by_edge[e] if j != i and M.cls[j] == "sand")
    return lips | sand


# ---- the gates ----------------------------------------------------------------------------------------------------

def gate_f1(M: _Mesh, frag, *, islands, join_edges) -> dict:
    """F1 COMPONENT CLOSURE: every whole-carry component is wholly in or wholly out, and a lip strip is cut only at
    a join column. Returns the report; raises :class:`RiverRefused` naming each cut."""
    frag = set(frag)
    cuts, where, report = [], [], {}
    for name, members in (("forest", [i for i, c in enumerate(M.cls) if c == "forest"]),
                          ("rock", [i for i, c in enumerate(M.cls) if c == "rock"]),
                          ("object", [i for i, c in enumerate(M.cls) if c == "object"]),
                          ("building", [i for i, c in enumerate(M.cls) if c == "building"]),
                          ("beach", [i for i, c in enumerate(M.cls) if c == "beach"])):
        groups = _groups(_components(M, members)).values()
        whole = 0
        for g in groups:
            n_in = len(g & frag)
            if n_in == len(g):
                whole += 1
            elif n_in:
                cuts.append(f"{name} component of {len(g)} tris cut ({n_in} inside)")
                where.append(M.centroid(g & frag))
        report[name] = whole
    n_isl = 0
    for g in islands.values():
        n_in = len(g & frag)
        if n_in == len(g):
            n_isl += 1
        elif n_in:
            cuts.append(f"island component of {len(g)} tris cut ({n_in} inside)")
            where.append(M.centroid(g & frag))
    report["islands"] = n_isl
    for e, i in _once_edges(M, frag).items():
        if e not in join_edges and any(M.cls[j] == "lip" for j in M.by_edge[e] if j not in frag):
            cuts.append("lip strip cut away from a join column")
            where.append(_mid(e))
    if cuts:
        kinds = Counter(c.split(" cut")[0].split(" component")[0] for c in cuts)
        raise RiverRefused("F1", "the fragment cuts a component that carries whole or not at all: "
                           + ", ".join(f"{n} x {k}" for k, n in kinds.most_common()), where)
    return report


def gate_f2(M: _Mesh, frag, *, seaward, bases) -> dict:
    """F2 SHORE SCOPE: every fragment edge with water across has deep water on both sides, and every seaward-boundary
    vertex but the two join bases touches deep water only. Returns the report; raises :class:`RiverRefused`."""
    frag = set(frag)
    where, n = [], 0
    for e, i in _once_edges(M, frag).items():
        out = [j for j in M.by_edge[e] if j not in frag and M.tris[j]["part"] in WATER]
        if not out:
            continue
        n += 1
        if M.tris[i]["part"] not in DEEP or any(M.tris[j]["part"] not in DEEP for j in out):
            where.append(_mid(e))
    for k in seaward:
        if k not in bases and any(M.tris[j]["part"] not in DEEP for j in M.by_vert[k]):
            where.append((k[0], k[2]))
    if where:
        raise RiverRefused("F2", "the seaward boundary touches a shallow or a beach (THE STRICT SHORE LAW)", where)
    return {"water_edges": n}


# ---- the fragment -------------------------------------------------------------------------------------------------

def build_fragment(tris, donor: RiverDonor) -> Fragment:
    """The fragment from a tri soup (the window's stock tris, or a synthetic fixture), gated F1 + F2."""
    M = _Mesh(tris)
    unit = river_unit(M, donor.unit_blocks)
    if not unit:
        raise RiverRefused("U0", "no river part in the unit blocks",
                           [(64 * bx + 32, -64 * by - 32) for bx, by in donor.unit_blocks])
    mouth = mouth_tris(M, unit)
    if not mouth:
        raise RiverRefused("U1", "the river has no mouth: no sea or beach tri welds to it", [M.centroid(unit)])
    joins = {name: resolve_join(M, name, crest, base) for name, crest, base in donor.joins}
    if set(joins) != {"W", "E"}:
        raise RiverRefused("J0", f"a river donor names joins W and E, not {sorted(joins)}")
    join_edges = {_ek(c, b) for c, b in joins.values()}
    w_base, e_base = joins["W"][1], joins["E"][1]

    # tether every island standing in the bay (a vertex on the mouth's side of the W-E chord, between the joins)
    comp, mainland, islands = land_islands(M, unit)
    mx, mz = M.centroid(mouth)
    ax, az, bx, bz = w_base[0], w_base[2], e_base[0], e_base[2]
    cl2 = (bx - ax) ** 2 + (bz - az) ** 2

    def side(x, z):
        return (bx - ax) * (z - az) - (bz - az) * (x - ax)
    s_mouth = side(mx, mz)
    forbidden, tethered = set(), 0
    for g in islands.values():
        in_bay = any(side(k[0], k[2]) * s_mouth > 0 and 0 < ((k[0] - ax) * (bx - ax) + (k[2] - az) * (bz - az)) < cl2
                     for i in g for k in M.keys[i])
        if not in_bay:
            continue
        corridor = _tether(M, g, mouth)
        if corridor:
            forbidden.update(k for i in corridor for k in M.keys[i])
            tethered += 1
    path, path_len = seaward_boundary(M, w_base, e_base, frozenset(forbidden))
    cut = {_ek(a, b) for a, b in zip(path, path[1:])}

    cove = cove_flood(M, mouth, cut)
    coast = coastal_assembly(M, cove, join_edges)
    touch = {k for i in cove for k in M.keys[i]}
    isl_in = {r: g for r, g in islands.items() if any(k in touch for i in g for k in M.keys[i])}
    frag = unit | cove | coast
    for g in isl_in.values():
        frag |= g

    f1 = gate_f1(M, frag, islands=islands, join_edges=join_edges)
    f2 = gate_f2(M, frag, seaward=path, bases=(w_base, e_base))

    boundary, lengths, lawn = defaultdict(list), Counter(), Counter()
    for e, i in _once_edges(M, frag).items():
        out = [j for j in M.by_edge[e] if j not in frag]
        if e in join_edges:
            c = "join"
        elif not out:
            c = "open"
        elif any(M.tris[j]["part"] in WATER for j in out):
            c = "water"
        elif any(M.cls[j] == "rock" for j in out):
            c = "source"
        else:
            c = "lawn"
            lawn[M.cls[out[0]] if M.cls[out[0]] != "ground" else f"topo{M.tris[out[0]]['topo']}"] += 1
        pts = (M.exact[e[0]], M.exact[e[1]])
        boundary[c].append(pts)
        lengths[c] += math.dist(pts[0], pts[1])
    order = sorted(frag)
    report = {
        "tris": len(frag), "unit": len(unit), "cove": len(cove), "coast": len(coast),
        "islands": [{"tris": len(g), "at": [round(c, 1) for c in M.centroid(g)]} for g in isl_in.values()],
        "tethered": tethered, "parts": dict(Counter(M.tris[i]["part"] for i in frag).most_common()),
        "seaward_len": round(path_len, 2), "seaward_verts": len(path),
        "boundary_len": {k: round(v, 1) for k, v in lengths.most_common()},
        "lawn_across": dict(lawn.most_common()), "F1": f1, "F2": f2,
        "mouth": [round(mx, 1), round(mz, 1)],
    }
    return Fragment(donor=donor, tris=[M.tris[i] for i in order], boundary=dict(boundary),
                    joins={n: (M.exact[c], M.exact[b]) for n, (c, b) in joins.items()},
                    seaward=[M.exact[k] for k in path], report=report)
