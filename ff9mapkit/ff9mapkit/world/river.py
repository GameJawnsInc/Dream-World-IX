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
    ``seaward`` is the seaward boundary's points, W join base to E join base. ``join_side`` holds, per join, what
    the kit's wall must continue: the stock UVs at the column (``uv``, from the carried lip tri; None without UVs)
    and the home coast (``home``: the next stock base along the lip the kit replaces, and its ``home_uv``)."""
    donor: RiverDonor
    tris: list
    boundary: dict
    joins: dict
    seaward: list
    report: dict = field(default_factory=dict)
    join_side: dict = field(default_factory=dict)


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
                    seaward=[M.exact[k] for k in path], report=report,
                    join_side={n: _join_side(M, frag, n, c, b) for n, (c, b) in joins.items()})


def _join_side(M: _Mesh, frag, name, ck, bk) -> dict:
    """A join column's two stock lip tris: the carried one's UVs at crest and base, and the home coast -- the next
    stock base vertex along the lip the kit's wall replaces (in the home tri when it has one, else the nearest)."""
    walls = [i for i in M.by_edge[_ek(ck, bk)] if M.cls[i] == "lip"]
    fi, hi = [i for i in walls if i in frag], [i for i in walls if i not in frag]
    if len(fi) != 1 or len(hi) != 1:
        raise RiverRefused("J0", f"join {name}'s column does not part a carried lip tri from a home one",
                           [(bk[0], bk[2])])

    def uv_at(i, k):
        t = M.tris[i]
        return None if t["uv"] is None else tuple(float(c) for c in t["uv"][M.keys[i].index(k)])
    cands = []
    for i in M.by_vert[bk]:
        if i in frag or M.cls[i] != "lip":
            continue
        for k in M.keys[i]:
            if k not in (bk, ck) and abs(k[1] - bk[1]) < 0.05:
                cands.append((i not in hi, math.dist(k, bk), k, i))
    if not cands:
        raise RiverRefused("J0", f"join {name} has no home coast: no stock lip base beside it outside the fragment",
                           [(bk[0], bk[2])])
    _, _, hk, h_i = min(cands)
    return {"uv": None if uv_at(fi[0], bk) is None else {"crest": uv_at(fi[0], ck), "base": uv_at(fi[0], bk)},
            "home": M.exact[hk], "home_uv": uv_at(h_i, hk), "home_base_uv": uv_at(h_i, bk)}


# ==== rung 1: the island's outline and the join columns ============================================================
#
# The kit mints the island with a CUSTOM OUTLINE (island.build_landmass(outline=, rim_at=, shore_origin=)): the kit
# ARC runs from one join base round the fragment's land side to the other, at least ``margin`` from the fragment's
# land ring away from the joins, and the seaward boundary closes the ring through the cove (everything on that side is
# the fragment's, dropped by the opening in rung 2). At each join the arc leaves along the HOME coast -- the stock lip
# the kit's wall replaces -- because the column parts the carried lip from the home one: a kit wall arriving from any
# other side would lie over the carried lip. The rock band's U is continuous across both columns: ``shore_origin``
# lands the first join's U, and the arc's LENGTH lands the second's (the band repeats every strip_w / density, 19.84u).

STUB = 0.5                    # x margin: the straight stub each end of the arc runs along the home coast
WRAP_GUARD = 0.85             # a join's arc segment stays this far inside the strip's wrap (rock_uvs translates there)


@dataclass
class Outline:
    """The island's coast ring for ``island.build_landmass(outline=ring, rim_at=rim_at, shore_origin=...)``.

    ``ring[0]`` is the FIRST join's base, ``ring[arc_end]`` the LAST's; the kit arc is ``ring[0..arc_end]`` (U
    increasing along it, as the stock band runs) and the rest is the seaward boundary back. ``rim_at`` pins both
    join crests to the stock crests; ``targets`` holds the stock UVs the kit's wall must meet at each column."""
    ring: list
    arc_end: int
    first: str
    last: str
    rim_at: dict
    shore_origin: float
    targets: dict
    report: dict = field(default_factory=dict)


def _wall_band(ground: str = "grass"):
    """The kit wall's U band as island.rock_uvs computes it: (ru0, strip_w, density)."""
    from . import grassland as G, island as I
    du = G.GROUNDS[ground]["wall_du"]
    ru0, ru1 = I.ROCK_U[0] + du, I.ROCK_U[1] + du
    return ru0, ru1 - ru0, I.ROCK_DENSITY


def land_chain(frag: Fragment, first: str, last: str) -> list:
    """The fragment's land ring as one ordered chain of exact points, ``first`` join base -> its crest -> the lawn /
    source edges -> the ``last`` crest -> its base. Refuses when the land-side boundary is not a single chain."""
    adj = defaultdict(list)
    for c in ("lawn", "source", "join"):
        for a, b in frag.boundary.get(c, ()):
            ka, kb = kk3(a), kk3(b)
            adj[ka].append((kb, b))
            adj[kb].append((ka, a))
    start, goal = kk3(frag.joins[first][1]), kk3(frag.joins[last][1])
    chain, prev, cur = [frag.joins[first][1]], None, start
    while cur != goal:
        nxt = [(k, p) for k, p in adj[cur] if k != prev]
        if len(nxt) != 1:
            raise RiverRefused("O0", f"the fragment's land ring branches or ends ({len(nxt)} ways on)",
                               [(cur[0], cur[2])])
        prev, (cur, p) = cur, nxt[0]
        chain.append(p)
        if len(chain) > 100000:
            raise RiverRefused("O0", "the fragment's land ring does not reach the other join")
    return chain


def _seg_arrays(pts):
    P = np.asarray([(p[0], p[-1]) for p in pts], dtype=float)
    return P[:-1], P[1:]


def _dist_to_segs(X, A, B):
    """Distances (N, M) from points X (N, 2) to segments A->B (M, 2)."""
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(axis=1), 1e-18)
    t = np.clip(((X[:, None, :] - A[None]) * AB[None]).sum(axis=2) / L2[None], 0.0, 1.0)
    Q = A[None] + t[..., None] * AB[None]
    return np.sqrt(((X[:, None, :] - Q) ** 2).sum(axis=2))


def _pip_many(X, poly):
    """Even-odd point-in-polygon for X (N, 2) against a closed ``poly`` (M, 2)."""
    A, B = poly, np.roll(poly, -1, axis=0)
    inside = np.zeros(len(X), dtype=bool)
    for (x1, z1), (x2, z2) in zip(A, B):
        if z1 == z2:
            continue
        cross = (z1 > X[:, 1]) != (z2 > X[:, 1])
        xi = x1 + (X[:, 1] - z1) / (z2 - z1) * (x2 - x1)
        inside ^= cross & (X[:, 0] < xi)
    return inside


def _contour_loops(g, x0, z0, h):
    """Marching squares at level 0 over ``g`` (nz, nx), ``g > 0`` inside -> closed loops [(x, z), ...]. Edge points
    are computed once per grid edge, so neighbouring cells share them exactly."""
    nz, nx = g.shape
    pos = g > 0
    cache = {}

    def ep(kind, iz, ix):
        key = (kind, iz, ix)
        if key not in cache:
            if kind == "h":                                  # (iz, ix) -> (iz, ix + 1)
                a, b = g[iz, ix], g[iz, ix + 1]
                t = a / (a - b)
                cache[key] = (x0 + (ix + t) * h, z0 + iz * h)
            else:                                            # (iz, ix) -> (iz + 1, ix)
                a, b = g[iz, ix], g[iz + 1, ix]
                t = a / (a - b)
                cache[key] = (x0 + ix * h, z0 + (iz + t) * h)
        return key
    links = defaultdict(list)
    for iz in range(nz - 1):
        for ix in range(nx - 1):
            c = (pos[iz, ix], pos[iz, ix + 1], pos[iz + 1, ix + 1], pos[iz + 1, ix])
            if all(c) or not any(c):
                continue
            e = {0: ("h", iz, ix), 1: ("v", iz, ix + 1), 2: ("h", iz + 1, ix), 3: ("v", iz, ix)}
            sides = [k for k, (a, b) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0))) if c[a] != c[b]]
            if len(sides) == 2:
                pairs = [tuple(sides)]
            else:                                            # a saddle: the centre decides
                centre = (g[iz, ix] + g[iz, ix + 1] + g[iz + 1, ix + 1] + g[iz + 1, ix]) > 0
                pairs = [(0, 1), (2, 3)] if centre == c[0] else [(3, 0), (1, 2)]
            for a, b in pairs:
                ka, kb = ep(*e[a]), ep(*e[b])
                links[ka].append(kb)
                links[kb].append(ka)
    loops, seen = [], set()
    for k0 in links:
        if k0 in seen:
            continue
        loop, prev, cur = [k0], None, k0
        seen.add(k0)
        while True:
            nxt = [k for k in links[cur] if k != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur == k0 or cur in seen:
                break
            seen.add(cur)
            loop.append(cur)
        loops.append([cache[k] for k in loop])
    return loops


def _edt_1d(f):
    """Felzenszwalb-Huttenlocher: the squared distance transform of one sampled row ``f`` (0 on the set, inf off)."""
    n = len(f)
    d = np.empty(n)
    v = np.zeros(n, dtype=int)
    z = np.empty(n + 1)
    k = 0
    v[0], z[0], z[1] = 0, -np.inf, np.inf
    for q in range(1, n):
        if not np.isfinite(f[q]):
            continue
        while True:
            if not np.isfinite(f[v[k]]):
                v[k], z[k], z[k + 1] = q, -np.inf, np.inf
                break
            sq = ((f[q] + q * q) - (f[v[k]] + v[k] * v[k])) / (2 * q - 2 * v[k])
            if sq <= z[k]:
                if k == 0:
                    v[0], z[0], z[1] = q, -np.inf, np.inf
                    break
                k -= 1
                continue
            k += 1
            v[k], z[k], z[k + 1] = q, sq, np.inf
            break
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        d[q] = (q - v[k]) ** 2 + f[v[k]] if np.isfinite(f[v[k]]) else np.inf
    return d


def _edt(mask, h):
    """Euclidean distance (world units, cell size ``h``) from every cell to the nearest ``mask`` cell -- exact,
    separable (rows, then columns)."""
    f = np.where(mask, 0.0, np.inf)
    f = np.stack([_edt_1d(r) for r in f])
    f = np.stack([_edt_1d(c) for c in f.T]).T
    return np.sqrt(f) * h


def _chaikin(P, fixed_head: int, fixed_tail: int, rounds: int):
    """Chaikin corner cutting on an open polyline, the first ``fixed_head`` and last ``fixed_tail`` points kept."""
    P = [tuple(p) for p in P]
    for _ in range(rounds):
        head, tail = P[:fixed_head], P[len(P) - fixed_tail:]
        mid = P[fixed_head - 1:len(P) - fixed_tail + 1]
        cut = []
        for (ax, az), (bx, bz) in zip(mid, mid[1:]):
            cut += [(0.75 * ax + 0.25 * bx, 0.75 * az + 0.25 * bz), (0.25 * ax + 0.75 * bx, 0.25 * az + 0.75 * bz)]
        P = head + cut + tail
    return P


def _resample(P, spacing):
    """An open polyline re-spaced evenly at about ``spacing`` (ends kept)."""
    P = np.asarray(P, dtype=float)
    seg = np.hypot(*(P[1:] - P[:-1]).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(1, int(math.ceil(cum[-1] / spacing)))
    s = np.linspace(0.0, cum[-1], n + 1)
    Q = np.stack([np.interp(s, cum, P[:, 0]), np.interp(s, cum, P[:, 1])], 1)
    return [tuple(map(float, q)) for q in Q]


def _poly_len(P):
    return float(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(P, P[1:])))


def land_phase(arc, *, ph_first, ph_last, density, period, outward, fixed=2):
    """THE U PHASE: bump the arc's middle outward (a sin^2 window; the ends and ``fixed`` points at each end stay)
    until its length L satisfies ``ph_first + L * density = ph_last (mod strip)`` -- in arc-length units, L lands
    on its target modulo ``period``, the smallest such L at or above today's. Returns ``(arc, added, bump)``."""
    P = np.asarray(arc, dtype=float)
    n = len(P)
    seg = np.hypot(*(P[1:] - P[:-1]).T)
    t = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    w = np.where((t > 0.1) & (t < 0.9), np.sin(np.pi * (t - 0.1) / 0.8) ** 2, 0.0)
    w[:fixed] = 0.0
    w[n - fixed:] = 0.0
    T = np.zeros_like(P)
    T[1:-1] = P[2:] - P[:-2]
    T[0], T[-1] = P[1] - P[0], P[-1] - P[-2]
    T /= np.maximum(np.hypot(*T.T), 1e-12)[:, None]
    N = np.stack([T[:, 1], -T[:, 0]], 1) * outward       # the right normal; ``outward`` = +1 / -1 by winding
    L0 = float(seg.sum())
    need = ((ph_last - ph_first) / density - L0) % period
    target = L0 + need

    def length(d):
        Q = P + d * w[:, None] * N
        return float(np.hypot(*(Q[1:] - Q[:-1]).T).sum())
    if need < 1e-12:
        return [tuple(map(float, p)) for p in P], 0.0, 0.0
    hi = 1.0
    while length(hi) < target:
        hi *= 2.0
        if hi > 256.0:
            raise RiverRefused("J2", "no outward bump lands the U phase on the second join (the arc will not "
                               "lengthen)", [tuple(P[n // 2])])
    lo = 0.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if length(mid) < target:
            lo = mid
        else:
            hi = mid
    d = 0.5 * (lo + hi)
    Q = P + d * w[:, None] * N
    Q[0], Q[-1] = P[0], P[-1]
    return [tuple(map(float, q)) for q in Q], need, d


def outline(frag: Fragment, *, margin: float = 16.0, taper=None, closing=None, spacing: float = 6.0,
            grid: float = 1.0, smooth: int = 3, ground: str = "grass") -> Outline:
    """The kit island's coast ring round a fragment (rung 1; studies/terrain-malleability/watercarry/PLAN.md step 2).

    THE BAND: the island must hold the fragment plus a one-sided band ``margin`` wide on the LAND side of its land
    ring (tapered to 0 within ``taper`` of the joins), plus, at each join, a band ``margin`` wide on the land side of
    the HOME coast's continuation -- so the coast leaves each join along the stock lip it replaces. The band's outer
    contour from join to join round the land, smoothed and re-spaced, is the kit arc; the seaward boundary closes
    the ring. THE CLOSING fills what the band leaves open between parts of the land ring (the river's inner bank
    and the cove's back are one lowland in stock, not an inlet): a morphological closing of radius ``closing``
    (default 1.5 x margin), keeping only what lies nearer the land ring than the seaward boundary, so the cove's
    mouth stays open. Then THE U PHASE: ``shore_origin`` lands the first join's stock U, and an outward bump of the
    arc's middle lands its length so that the second join's U matches too."""
    if any(js.get("uv") is None for js in frag.join_side.values()):
        raise RiverRefused("J2", "the fragment carries no UVs at its join columns: the U phase has nothing to land on")
    taper = 2.0 * margin if taper is None else taper
    closing = 1.5 * margin if closing is None else closing
    ru0, strip_w, dens = _wall_band(ground)
    period = strip_w / dens

    def wrapd(du):
        return (du + strip_w / 2) % strip_w - strip_w / 2
    # which way the stock band runs: U must grow from the first join's column out along its home coast, and run
    # into the last join's column along its home coast
    dirs = {n: wrapd(js["home_uv"][0] - js["home_base_uv"][0]) for n, js in frag.join_side.items()}
    if dirs["E"] > 0 > dirs["W"]:
        first, last = "E", "W"
    elif dirs["W"] > 0 > dirs["E"]:
        first, last = "W", "E"
    else:
        raise RiverRefused("J2", "the stock band runs the same way out of both joins: no kit arc continues both",
                           [(frag.joins[n][1][0], frag.joins[n][1][2]) for n in ("E", "W")])
    base = {n: np.array([frag.joins[n][1][0], frag.joins[n][1][2]]) for n in (first, last)}
    crest = {n: np.array([frag.joins[n][0][0], frag.joins[n][0][2]]) for n in (first, last)}
    tang = {}
    for n in (first, last):
        hx, _, hz = frag.join_side[n]["home"]
        v = np.array([hx, hz]) - base[n]
        tang[n] = v / np.linalg.norm(v)

    chain = land_chain(frag, first, last)
    sea = list(frag.seaward) if first == "E" else list(reversed(frag.seaward))   # the last base -> the first base
    A, B = _seg_arrays(chain)
    SA, SB = _seg_arrays(sea)
    poly = np.asarray([(p[0], p[2]) for p in chain] + [(p[0], p[2]) for p in sea[1:-1]], dtype=float)
    mid = (A + B) / 2
    dj = np.minimum(np.hypot(*(mid - base[first]).T), np.hypot(*(mid - base[last]).T))
    u = np.clip(dj / taper, 0.0, 1.0)
    m_seg = margin * u * u * (3 - 2 * u)                   # a smoothstep taper to 0 at the joins
    ext = {n: (base[n], base[n] + margin * tang[n]) for n in (first, last)}
    def side(t, d):                                       # the z-component of t x d, per row of d
        return np.sign(t[0] * d[..., 1] - t[1] * d[..., 0])
    ext_side = {n: side(tang[n], crest[n] - base[n]) for n in (first, last)}   # the side the crest stands on

    pad = margin + closing + 4 * grid
    ends = np.asarray([e[1] for e in ext.values()])
    lo = np.minimum(poly.min(axis=0), ends.min(axis=0)) - pad
    hi = np.maximum(poly.max(axis=0), ends.max(axis=0)) + pad
    xs = np.arange(lo[0], hi[0] + grid, grid)
    zs = np.arange(lo[1], hi[1] + grid, grid)
    GX, GZ = np.meshgrid(xs, zs)
    X = np.stack([GX.ravel(), GZ.ravel()], 1)
    g = np.full(len(X), -1.0)
    landward = np.zeros(len(X), dtype=bool)               # nearer the land ring than the seaward boundary
    for s0 in range(0, len(X), 4000):
        Xc = X[s0:s0 + 4000]
        inside = _pip_many(Xc, poly)
        D = _dist_to_segs(Xc, A, B)
        j = D.argmin(axis=1)
        d_chain = D[np.arange(len(Xc)), j]
        d_sea = _dist_to_segs(Xc, SA, SB).min(axis=1)
        landward[s0:s0 + 4000] = d_chain < d_sea
        val = np.where(d_chain < d_sea, (m_seg[j] - d_chain) / margin, -1.0)
        for n in (first, last):
            a, b = ext[n]
            de = _dist_to_segs(Xc, a[None], b[None])[:, 0]
            land = side(tang[n], Xc - a[None]) == ext_side[n]
            val = np.maximum(val, np.where(land, (margin - de) / margin, -1.0))
        g[s0:s0 + 4000] = np.where(inside, 1.0, np.clip(val, -1.0, 1.0))
    g = g.reshape(GZ.shape)
    g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = -1.0
    if closing > 0:                                      # THE CLOSING: dilate, then erode, by ``closing``
        dil = _edt(g > 0, grid) <= closing
        d_in = _edt(~dil, grid)
        add = (d_in > closing) & (g <= 0) & landward.reshape(GZ.shape)
        g = np.where(add, np.clip((d_in - closing) / margin, 1e-6, 1.0), g)
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = -1.0
    g = np.where(g == 0.0, -1e-9, g)
    loop = max(_contour_loops(g, float(xs[0]), float(zs[0]), grid), key=_poly_len)
    L = np.asarray(loop)
    i0 = int(np.hypot(*(L - base[first]).T).argmin())
    i1 = int(np.hypot(*(L - base[last]).T).argmin())
    for n, i in ((first, i0), (last, i1)):
        if math.hypot(*(L[i] - base[n])) > 2.5 * grid:
            raise RiverRefused("O1", f"the band's contour misses join {n}'s base", [tuple(base[n])])
    k = len(loop)
    fwd = [loop[(i0 + q) % k] for q in range(((i1 - i0) % k) + 1)]
    bwd = [loop[(i0 - q) % k] for q in range(((i0 - i1) % k) + 1)]
    sea_mid = np.asarray([(p[0], p[2]) for p in sea]).mean(axis=0)
    sec = max((fwd, bwd), key=lambda S: max(math.hypot(x - sea_mid[0], z - sea_mid[1]) for x, z in S))
    # THE WRAP GUARD: each join's arc segment stays inside the rock strip (rock_uvs window-translates a tri that
    # straddles the band's wrap, which would move the join's U)
    ph = {n: frag.join_side[n]["uv"]["base"][0] - ru0 for n in (first, last)}
    d_first = min(spacing, WRAP_GUARD * (strip_w - ph[first]) / dens)
    d_last = min(spacing, WRAP_GUARD * ph[last] / dens)
    if min(d_first, d_last) < 2.0:
        raise RiverRefused("J2", f"a join's stock U sits within {min(d_first, d_last) / WRAP_GUARD:.2f}u of the "
                           "band's wrap: the kit's first wall segment cannot stay inside the strip",
                           [tuple(base[first]), tuple(base[last])])
    # the stubs: the arc leaves each join exactly along its home coast, then the band's contour, smoothed + re-spaced
    stub = STUB * margin
    keep = [p for p in sec if min(math.hypot(*(np.array(p) - base[first])),
                                  math.hypot(*(np.array(p) - base[last]))) > 0.8 * margin]
    s_first = tuple(map(float, base[first] + d_first * tang[first]))
    s_last = tuple(map(float, base[last] + d_last * tang[last]))
    raw = ([s_first, tuple(base[first] + max(stub, d_first + 1.0) * tang[first])] + keep
           + [tuple(base[last] + max(stub, d_last + 1.0) * tang[last]), s_last])
    arc = ([(frag.joins[first][1][0], frag.joins[first][1][2])] + _resample(_chaikin(raw, 2, 2, smooth), spacing)
           + [(frag.joins[last][1][0], frag.joins[last][1][2])])
    ring0 = arc + [(p[0], p[2]) for p in sea[1:-1]]
    nr = len(ring0)
    area2 = sum(ring0[i][0] * ring0[(i + 1) % nr][1] - ring0[(i + 1) % nr][0] * ring0[i][1] for i in range(nr))
    outward = 1.0 if area2 > 0 else -1.0                   # counter-clockwise: the outside is on the right
    arc, added, bump = land_phase(arc, ph_first=ph[first], ph_last=ph[last], density=dens, period=period,
                                  outward=outward)
    ring = arc + [(p[0], p[2]) for p in sea[1:-1]]
    arc_end = len(arc) - 1
    nr = len(ring)
    segs = [math.hypot(ring[(i + 1) % nr][0] - ring[i][0], ring[(i + 1) % nr][1] - ring[i][1]) for i in range(nr)]
    if max(segs) > 8.0:
        i = int(np.argmax(segs))
        raise RiverRefused("G2", f"a coast segment is {max(segs):.2f}u, over the mint's 8u grain", [ring[i]])
    _refuse_self_crossing(ring)
    dmin = float(_dist_to_segs(np.asarray(arc[2:-2]), A, B).min()) if len(arc) > 4 else 0.0
    rep = {"first": first, "last": last, "arc_points": len(arc), "ring_points": nr,
           "arc_len": round(_poly_len(arc), 3), "phase_added": round(added, 3), "bump": round(bump, 3),
           "seg_max": round(max(segs), 3), "seg_min": round(min(segs), 3), "arc_to_land_min": round(dmin, 2),
           "stub": {first: round(d_first, 3), last: round(d_last, 3)}}
    return Outline(ring=ring, arc_end=arc_end, first=first, last=last,
                   rim_at={0: tuple(frag.joins[first][0]), arc_end: tuple(frag.joins[last][0])},
                   shore_origin=ph[first] / dens,
                   targets={first: frag.join_side[first]["uv"], last: frag.join_side[last]["uv"]}, report=rep)


def _refuse_self_crossing(ring):
    """G0: the ring is a simple polygon (a crossing coast mints a folded island)."""
    from .island import _seg_cross
    n = len(ring)
    P = np.asarray(ring)
    Q = np.roll(P, -1, axis=0)
    lo, hi = np.minimum(P, Q), np.maximum(P, Q)
    for i in range(n):
        cand = np.where((lo[:, 0] <= hi[i, 0]) & (hi[:, 0] >= lo[i, 0]) & (lo[:, 1] <= hi[i, 1])
                        & (hi[:, 1] >= lo[i, 1]))[0]
        for j in cand:
            if j <= i + 1 or (i == 0 and j == n - 1):
                continue
            if _seg_cross(ring[i], ring[(i + 1) % n], ring[j], ring[(j + 1) % n]):
                raise RiverRefused("G0", "the island's coast crosses itself", [ring[i], ring[j]])


def mint(ol: Outline, *, center=None, **kw) -> dict:
    """``island.build_landmass`` on the outline: the custom ring, the join crests pinned, the U origin set."""
    from .island import build_landmass
    if center is None:
        P = np.asarray(ol.ring)
        center = (float(P[:, 0].mean()), float(P[:, 1].mean()))
    kw.setdefault("n_patches", 0)
    return build_landmass(center=center, outline=ol.ring, rim_at=ol.rim_at, shore_origin=ol.shore_origin, **kw)


def join_gates(built: dict, ol: Outline, joins: dict, *, tol_u: float = 1e-4, tol_v: float = 1e-3,
               slope=(60.0, 80.0)) -> dict:
    """J1-J4 at both join columns, on the minted island (PLAN.md's gate table). ``joins`` = ``{name: (crest, base)}``
    -- the STOCK points, exact (``Fragment.joins``):

    * J1 -- the kit wall has a tri on the ARC side holding the column, its base and crest the stock floats exactly;
    * J2 -- its U at the crest and the base within ``tol_u`` of the carried stock lip's;
    * J3 -- its V rows within ``tol_v`` of the stock's (the kit's language rows against the stock's own);
    * J4 -- every such tri leans ``slope`` degrees from level, as the stock walls do.
    Returns the per-join report; raises :class:`RiverRefused` naming the first gate that fails."""
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    ring, n = ol.ring, len(ol.ring)
    rep = {}
    for name, idx, arc_nb, sea_nb in ((ol.first, 0, 1, n - 1),
                                      (ol.last, ol.arc_end, ol.arc_end - 1, (ol.arc_end + 1) % n)):
        crest, base = (tuple(map(float, p)) for p in joins[name])
        where = [(base[0], base[2])]
        hits = []
        for tri, (_blk, _idall, fam, uvv) in zip(gtris, gmeta):
            if fam != "rock":
                continue
            P = [tuple(map(float, gpos[v])) for v in tri]
            if base not in P or crest not in P:
                continue
            c = np.mean(np.asarray(P)[:, [0, 2]], axis=0)

            def dseg(a, b):
                a, b = np.asarray(ring[a]), np.asarray(ring[b])
                t = np.clip(np.dot(c - a, b - a) / max(float(np.dot(b - a, b - a)), 1e-18), 0.0, 1.0)
                return float(np.hypot(*(c - (a + t * (b - a)))))
            if dseg(idx, arc_nb) < dseg(idx, sea_nb):
                hits.append((P, uvv))
        if not hits:
            raise RiverRefused("J1", f"no kit wall tri on the arc side holds join {name}'s stock column exactly "
                               "(crest and base, bit for bit)", where)
        tgt = ol.targets[name]
        du, dv, slopes = 0.0, 0.0, []
        for P, uvv in hits:
            for p, (uu, vv) in zip(P, uvv):
                role = "base" if p == base else "crest" if p == crest else None
                if role:
                    du = max(du, abs(uu - tgt[role][0]))
                    dv = max(dv, abs(vv - tgt[role][1]))
            a, b, c = (np.asarray(p) for p in P)
            nrm = np.cross(b - a, c - a)
            slopes.append(math.degrees(math.acos(min(1.0, abs(nrm[1]) / max(float(np.linalg.norm(nrm)), 1e-18)))))
        rep[name] = {"tris": len(hits), "du": du, "dv": dv, "slope": [round(x, 2) for x in slopes]}
        if du >= tol_u:
            raise RiverRefused("J2", f"join {name}: the kit wall's U is {du:.6f} off the stock lip's", where)
        if dv > tol_v:
            raise RiverRefused("J3", f"join {name}: the kit wall's V row is {dv:.6f} off the stock lip's", where)
        if not all(slope[0] <= x <= slope[1] for x in slopes):
            raise RiverRefused("J4", f"join {name}: the kit wall beside the column leans {rep[name]['slope']} deg, "
                               f"outside the stock {slope[0]:g}-{slope[1]:g}", where)
    return rep
