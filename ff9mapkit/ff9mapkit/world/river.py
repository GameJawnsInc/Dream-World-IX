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
import re
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
#: THE CELL-ALIGNED SEAM (rung 3): the seaward boundary runs along lattice edges wherever it can. A diagonal splits a
#: 4u water cell between the carried band and the kit's Sea4 -- a shallow|deep contact INSIDE one cell, which the
#: cell-binned rim retile (rimretile.plan_rim) can neither see nor re-band. Measured on cluster C: 10 of 34 edges.
SEAM_DIAGONAL_COST = 100.0
#: THE SHORE-CLEAR SEAM (rung 3): the rim retile re-bands a seam cell only AWAY from shore (rimretile.plan_rim's shore
#: scope: no shallow, beach or land in its 3x3), so the boundary keeps this many 4u cells clear of every shore except
#: within SEAM_JOIN_RELAX of a join base (on the coast by definition). Measured on cluster C: hugging the island's
#: shallow ring, 9 sea3|sea4 contacts survived the knit.
SEAM_SHORE_CLEAR = 2
SEAM_JOIN_RELAX = 12.0


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


def _shore_cells(M: _Mesh, island) -> set:
    """The 4u cells of an island and its shallow ring: every non-deep tri (land, beach, sea1/sea2) joined to the
    island through non-deep tris."""
    seen, stack = set(island), list(island)
    while stack:
        i = stack.pop()
        for k in M.keys[i]:
            for j in M.by_vert[k]:
                if j not in seen and M.tris[j]["part"] not in DEEP and M.tris[j]["part"] not in RIVER_PARTS:
                    seen.add(j)
                    stack.append(j)
    return {(math.floor(c[0] / 4.0), math.floor(c[2] / 4.0)) for i in seen for c in [M.tris[i]["P"].mean(axis=0)]}


def seaward_boundary(M: _Mesh, w_base, e_base, forbidden=frozenset(), shore=frozenset()):
    """THE SEAWARD BOUNDARY: the cheapest vertex path W base -> E base along edges with exactly two tris, both deep,
    through vertices every tri of which is deep (the bases excepted) and none ``forbidden`` (the tethers); a diagonal
    edge costs :data:`SEAM_DIAGONAL_COST` more (THE CELL-ALIGNED SEAM), and every vertex keeps :data:`SEAM_SHORE_CLEAR`
    cells clear of the ``shore`` cells away from the joins (THE SHORE-CLEAR SEAM) -- the shores the COMPOSED island
    will have there: the bay's islands and their shallow rings, never home's land beyond the cove, which the kit's
    deep sheet replaces. F2 refuses when no such route exists. Returns ``(path, plan length)``."""
    def shore_clear(k):
        if min(math.hypot(k[0] - b[0], k[2] - b[2]) for b in (w_base, e_base)) <= SEAM_JOIN_RELAX:
            return True
        ci, cj = math.floor(k[0] / 4.0 + 1e-9), math.floor(k[2] / 4.0 + 1e-9)
        r = SEAM_SHORE_CLEAR
        return not any((ci + a, cj + b) in shore for a in range(-r, r) for b in range(-r, r))

    def ok_vert(k):
        if k in (w_base, e_base):
            return True
        return k not in forbidden and all(M.tris[j]["part"] in DEEP for j in M.by_vert[k]) and shore_clear(k)
    nbr = defaultdict(list)
    for e, ts in M.by_edge.items():
        if len(ts) == 2 and all(M.tris[j]["part"] in DEEP for j in ts) and ok_vert(e[0]) and ok_vert(e[1]):
            L = math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])
            if abs(e[0][0] - e[1][0]) > 1e-6 and abs(e[0][2] - e[1][2]) > 1e-6:
                L += SEAM_DIAGONAL_COST                  # THE CELL-ALIGNED SEAM: a diagonal splits a 4u cell
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
            path = path[::-1]
            return path, sum(math.hypot(a[0] - b[0], a[2] - b[2]) for a, b in zip(path, path[1:]))
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


def notch_closure(M: _Mesh, frag) -> set:
    """THE NOTCH CLOSURE: a stock lattice-ground tri (grass or sand) that the fragment holds on two sides is carried
    too, until none is left. Its three corners all sit on the land ring, so no zip strip can fill it -- every strip
    tri has a corner on each side of the seam, and over a one-tri notch it folds across the fragment (rung 2, the
    cove's NE corner: two squared sand cells meeting at a point). Carried, it is stock bytes, not authored ones."""
    frag = set(frag)
    added, grow = set(), True
    while grow:
        grow = False
        cnt = defaultdict(int)
        for e, i in _once_edges(M, frag).items():
            for j in M.by_edge[e]:
                if j not in frag and M.tris[j]["part"] == "terrain" and M.cls[j] in ("ground", "sand"):
                    cnt[j] += 1
        for j, n in cnt.items():
            if n >= 2:
                frag.add(j)
                added.add(j)
                grow = True
    return added


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
    forbidden, tethered, shore = set(), 0, set()
    for g in islands.values():
        in_bay = any(side(k[0], k[2]) * s_mouth > 0 and 0 < ((k[0] - ax) * (bx - ax) + (k[2] - az) * (bz - az)) < cl2
                     for i in g for k in M.keys[i])
        if not in_bay:
            continue
        corridor = _tether(M, g, mouth)
        if corridor:
            forbidden.update(k for i in corridor for k in M.keys[i])
            tethered += 1
        shore |= _shore_cells(M, g)
    path, path_len = seaward_boundary(M, w_base, e_base, frozenset(forbidden), frozenset(shore))
    cut = {_ek(a, b) for a, b in zip(path, path[1:])}

    cove = cove_flood(M, mouth, cut)
    coast = coastal_assembly(M, cove, join_edges)
    touch = {k for i in cove for k in M.keys[i]}
    isl_in = {r: g for r, g in islands.items() if any(k in touch for i in g for k in M.keys[i])}
    frag = unit | cove | coast
    for g in isl_in.values():
        frag |= g
    notches = notch_closure(M, frag)
    frag |= notches

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
        "tris": len(frag), "unit": len(unit), "cove": len(cove), "coast": len(coast), "notches": len(notches),
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


# ==== rung 2: the composition, offline end to end (nothing writes) ================================================
#
# The fragment, translated onto open ocean, seated in the island minted round it:
#   THE OPENING   every kit lawn tri over the fragment or within ``clear`` of its land ring drops, and every kit wall
#                 tri on the seaward chain (inside the footprint); the arc's walls stay, join columns included;
#   THE APRON     the kit lawn near the land ring is lifted (or lowered) toward the ring's own heights by POSITION --
#                 world-mountain's ground lift, faded before the coast walls -- because a stock lowland is not level;
#   THE OPEN ZIP  the hole's arc and the fragment's land ring are two chains from the E crest to the W crest (the
#                 columns weld them at both ends), strip-triangulated by a minimal-chord DP, the kit side on its own
#                 exact floats (THE EXACT-WELD LAW);
#   THE STAMP     decision 1: carried ground (Terrain, Beach1, the bridge) takes the island's area, except the IDALLs
#                 the ground query skips (THE BANK SKIP LAW); every event bit is stripped; the water parts keep their
#                 stock areas (stock sea is area 0, as the island lane's is).
# Then the gates (PLAN.md's table) and the binding plan, every failure with its location.

COMPOSE_CLEAR = 2.5           # the opening's clearance round the land ring (world-mountain's MTN_CLEAR)
DIVERT_PREFAB = (16, 15)      # the one stock prefab hosting every part the composition emits (PLAN.md step 7)
ZIP_RISE = 2.34               # a zip tri's vertical span ceiling (the engine's climb step 2.34375)
ZIP_NY_FLOOR = 0.5            # the per-tri slope floor (~60 deg)
ZIP_MAX_EDGE = 9.0            # G2: a zip edge's plan length ceiling
ZIP_SPLIT = 6.0               # the zip refinement splits interior edges longer than this (the kit's own grain)
RIVER_GBLEND = 24.0           # the apron's reach: twice the mountain's, because a stock lowland falls 2-3u to its
#                               beach behind the sand row, where a massif's foot meets a level bench
PART_BUDGET = 5000            # C1: tris per walkable part per block (the cost law)
GROUND_PARTS = ("terrain", "beach1", "object")
PART_NAME = {"terrain": "Terrain", "object": "Object", "beach1": "Beach1", "stream": "Stream", "river": "River",
             "riverjoint": "RiverJoint", "falls": "Falls", "sea1": "Sea1", "sea2": "Sea2", "sea3": "Sea3",
             "sea4": "Sea4", "sea5": "Sea5"}


@dataclass
class Composition:
    """The composed island, in world coordinates, before any write. ``tris`` are dicts (part, P, uv, nrm, tan,
    idall, topo, src) -- ``src`` is ``stock`` (the fragment, verbatim bar the stamp), ``kit`` (the mint, kept) or
    ``zip``. ``plan`` is the binding plan (per target block: emitted parts, blanks, the divert); ``report`` holds every
    gate's verdict."""
    offset: tuple
    tris: list
    outline: Outline
    plan: dict
    report: dict = field(default_factory=dict)
    footprint: list = field(default_factory=list)


def translate(frag: Fragment, offset) -> Fragment:
    """The fragment moved by ``offset = (dx, dz)`` (multiples of 4u: the water's lattice). Every float stays exact."""
    dx, dz = (float(v) for v in offset)
    if dx % 4.0 or dz % 4.0:
        raise RiverRefused("T0", f"a translation of ({dx:g}, {dz:g}) leaves the 4u water lattice")
    T = np.array([dx, 0.0, dz])

    def mv(p):
        return (p[0] + dx, p[1], p[2] + dz)
    tris = [dict(t, P=t["P"] + T) for t in frag.tris]
    js = {n: dict(v, home=mv(v["home"])) for n, v in frag.join_side.items()}
    return Fragment(donor=frag.donor, tris=tris,
                    boundary={c: [(mv(a), mv(b)) for a, b in es] for c, es in frag.boundary.items()},
                    joins={n: (mv(c), mv(b)) for n, (c, b) in frag.joins.items()},
                    seaward=[mv(p) for p in frag.seaward], report=dict(frag.report), join_side=js)


def translate_outline(ol: Outline, offset) -> Outline:
    dx, dz = (float(v) for v in offset)
    return Outline(ring=[(x + dx, z + dz) for x, z in ol.ring], arc_end=ol.arc_end, first=ol.first, last=ol.last,
                   rim_at={i: (p[0] + dx, p[1], p[2] + dz) for i, p in ol.rim_at.items()},
                   shore_origin=ol.shore_origin, targets=ol.targets, report=dict(ol.report))


def _zip_dp_open(H, Rr, *, ny_floor: float = ZIP_NY_FLOOR):
    """THE OPEN ZIP: the minimal-total-chord strip between two chains that share both ends (``H[0] == Rr[0]``,
    ``H[-1] == Rr[-1]``) -- :func:`interior._zip_dp` without the wrap. A step whose tri would repeat a shared end is
    free and emits nothing, so the strip may FAN round a shared end (a crest where the two chains leave in opposite
    directions: one tri cannot span that 180 deg). A tri steeper than ``ny_floor`` costs
    :data:`interior.ZIP_STEEP_PENALTY` more, so the strip routes round plan-flat slivers (an arc point on the line
    of the other arc's edge: the 4u lattice and the block borders line both arcs up). A strip cannot fill a notch
    of the land ring one tri deep (its three corners all on one arc) -- it folds there; :func:`notch_closure` carries
    those tris with the fragment instead, and G4 catches any fold left. Returns point triples."""
    from .interior import ZIP_STEEP_PENALTY

    def d(p, q):
        return math.hypot(p[0] - q[0], p[2] - q[2])

    def tri_cost(a, b, c):
        if a == b or b == c or a == c:
            return 0.0, False
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        return (ZIP_STEEP_PENALTY if ln < 1e-12 or abs(ny) / ln < ny_floor else 0.0), True
    NH, NR = len(H), len(Rr)
    INF = float("inf")
    cost = [[INF] * NR for _ in range(NH)]
    back = [[None] * NR for _ in range(NH)]
    cost[0][0] = 0.0
    for i in range(NH):
        for j in range(NR):
            c0 = cost[i][j]
            if c0 == INF:
                continue
            if i + 1 < NH:
                pen, _ = tri_cost(H[i], H[i + 1], Rr[j])
                nc = c0 + d(H[i + 1], Rr[j]) + pen
                if nc < cost[i + 1][j]:
                    cost[i + 1][j], back[i + 1][j] = nc, "h"
            if j + 1 < NR:
                pen, _ = tri_cost(H[i], Rr[j], Rr[j + 1])
                nc = c0 + d(H[i], Rr[j + 1]) + pen
                if nc < cost[i][j + 1]:
                    cost[i][j + 1], back[i][j + 1] = nc, "r"
    tris = []
    i, j = NH - 1, NR - 1
    while i > 0 or j > 0:
        if back[i][j] == "h":
            t = (H[i - 1], H[i], Rr[j])
            i -= 1
        else:
            t = (H[i], Rr[j], Rr[j - 1])
            j -= 1
        if tri_cost(*t)[1]:
            tris.append(t)
    return tris[::-1]


def _refine_zip(tris, *, max_edge: float, rise: float = ZIP_RISE):
    """Split the zip's INTERIOR edges (two zip tris own them; an arc edge is shared with a kept or carried tri and
    never splits -- that would mint a T-junction) at their exact midpoints, both owners at once, longest first,
    until no interior edge that is the longest of a tri it bounds is longer than ``max_edge``, and none climbs more
    than ``rise``. Returns ``(tris, splits)``."""
    tris = [tuple(tuple(map(float, p)) for p in t) for t in tris]
    splits = 0
    for _ in range(4096):
        own = defaultdict(list)
        for ti, t in enumerate(tris):
            for a, b in ((0, 1), (1, 2), (2, 0)):
                own[_ek(kk3(t[a]), kk3(t[b]))].append((ti, a, b))
        def plan_len(t, a, b):
            return math.hypot(t[a][0] - t[b][0], t[a][2] - t[b][2])
        longest = [max(plan_len(t, a, b) for a, b in ((0, 1), (1, 2), (2, 0))) for t in tris]
        best = None
        for e, ow in own.items():
            if len(ow) != 2:
                continue
            ti, a, b = ow[0]
            L = plan_len(tris[ti], a, b)
            high = abs(tris[ti][a][1] - tris[ti][b][1]) > rise       # the edge's own climb: a split halves it
            # LONGEST-EDGE BISECTION (Rivara): split for length only an edge that is the longest of a tri it bounds
            # -- a tri on an arc edge longer than 2 x max_edge can never get both other edges under it, and
            # splitting those forever would never end
            long_ = L > max_edge and any(L >= longest[t_] - 1e-9 for t_, _, _ in ow)
            if (long_ or high) and (best is None or L > best[0]) and L > 0.5:
                best = (L, ow)
        if best is None:
            return tris, splits
        _, ow = best
        ti, a, b = ow[0]
        pa, pb = tris[ti][a], tris[ti][b]
        m = ((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0, (pa[2] + pb[2]) / 2.0)
        done = {t_ for t_, _, _ in ow}
        new = [t for k, t in enumerate(tris) if k not in done]
        for t_, a_, b_ in ow:
            t = tris[t_]
            c = [t[k] for k in range(3) if k not in (a_, b_)][0]
            new += [(t[a_], m, c), (m, t[b_], c)]
        tris = new
        splits += 1
    raise RiverRefused("G2", "the zip refinement did not converge")


def _up(tri):
    a, b, c = (np.asarray(p, dtype=float) for p in tri)
    n = np.cross(b - a, c - a)
    return tri if n[1] >= 0 else (tri[0], tri[2], tri[1])


def _stamp_carried(t, area):
    """Decision 1 on one carried tri -> its new IDALL."""
    from .placement import ground_query_skips
    idall = int(t["idall"])
    if ground_query_skips(idall):
        return idall                                     # THE BANK SKIP LAW: the area is the physics here
    d = X.decode_id(idall)
    keep_area = d["area"] if t["part"] not in GROUND_PARTS else area
    return int(X.encode_id(0, keep_area, d["topograph"], d["flags"]))


def _kit_tris(built, area):
    gpos, gtris, gmeta, gnrm = (built["world"][k] for k in ("pos", "tris", "meta", "nrm"))
    out = []
    for tri, (blk, idall, fam, uvv) in zip(gtris, gmeta):
        d = X.decode_id(int(round(idall)))
        stamped = int(X.encode_id(0, area, d["topograph"], d["flags"]))
        out.append({"part": "terrain", "P": np.asarray([gpos[v] for v in tri], dtype=float),
                    "uv": np.asarray(uvv, dtype=float), "nrm": np.asarray([gnrm[v] for v in tri], dtype=float),
                    "tan": None, "idall": stamped, "topo": d["topograph"], "fam": fam, "src": "kit"})
    return out


def _apron(kept, nodes, gblend):
    """world-mountain's ground lift (``interior.carve_mountain``'s apron, ported in seat_dryrun.py): every kit LAWN
    position within ``gblend`` of a land-ring node moves vertically toward the nodes' IDW height, faded by
    (1 - d/gblend)^2 and dying within 2.5-5.5u of the kit's walls (the coast rim never moves). By POSITION, so
    every coincident corner moves together (the weld holds). Returns ``{key: lift}``."""
    if not nodes:
        return {}
    N = np.asarray(nodes, dtype=float)                   # (x, z, y)
    walls = np.asarray([[p[0], p[2]] for t in kept if t["fam"] == "rock" for p in t["P"]] or [[1e9, 1e9]])
    lift, done = {}, set()
    for t in kept:
        if t["fam"] != "main":
            continue
        for p in t["P"]:
            k = kk3(p)
            if k in done:
                continue
            done.add(k)
            d2 = (N[:, 0] - p[0]) ** 2 + (N[:, 1] - p[2]) ** 2
            if d2.min() >= gblend * gblend:
                continue
            m = d2 <= gblend * gblend
            w = 1.0 / (d2[m] + 0.04)
            target = float((w * N[m, 2]).sum() / w.sum())
            W = (1.0 - math.sqrt(float(d2.min())) / gblend) ** 2
            dnp = math.sqrt(float(((walls - np.array([p[0], p[2]])) ** 2).sum(axis=1).min()))
            pt = max(0.0, min(1.0, (dnp - 2.5) / 3.0))
            lf = pt * W * (target - p[1])
            if abs(lf) > 1e-6:
                lift[k] = lf
    for t in kept:
        for i in range(3):
            k = kk3(t["P"][i])
            if k in lift:
                t["P"][i] = t["P"][i] + np.array([0.0, lift[k], 0.0])
    return lift


def _soup_once(tris):
    seen = Counter()
    for t in tris:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = kk3(t["P"][a]), kk3(t["P"][b])
            if ka != kb:
                seen[_ek(ka, kb)] += 1
    return {e for e, n in seen.items() if n == 1}


class _PM:
    """A world-frame part mesh in the shape :func:`placement.place` reads (verts, tangents, flat_index, tris)."""

    def __init__(self, tris):
        self.verts = [list(map(float, p)) for t in tris for p in t["P"]]
        self.tangents = [[float(t["idall"]), 0.0, 0.0, 0.0] for t in tris for _ in range(3)]
        self.flat_index = list(range(len(self.verts)))
        self.tris = [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(len(tris))]


def _meshlist(tris):
    from .placement import REGISTRATION_ORDER, build_meshlist_index
    by = defaultdict(list)
    for t in tris:
        by[PART_NAME[t["part"]]].append(t)
    ml = [(n, _PM(by[n])) for n in REGISTRATION_ORDER if by.get(n)]
    return ml, build_meshlist_index(ml)


def open_ocean_offsets(blocks, *, margin: int = 0, disc: int = 1, game=None, limit: int = 8):
    """Whole-block translations that land every block of ``blocks`` -- and a ``margin``-block ring round them -- on
    open ocean (no stock prefab: the divert binds only there), nearest first."""
    from . import mesh as M_
    taken = set(X.block_parts(disc=disc, game=game))
    bx0, bx1 = min(b[0] for b in blocks), max(b[0] for b in blocks)
    by0, by1 = min(b[1] for b in blocks), max(b[1] for b in blocks)
    out = []
    for dy in range(-by0 + margin, M_.GRID_ROWS - by1 - margin):
        for dx in range(-M_.GRID_COLS + 1, M_.GRID_COLS):
            cells = {(M_.wrap_block_col(x + dx), y + dy) for x in range(bx0 - margin, bx1 + margin + 1)
                     for y in range(by0 - margin, by1 + margin + 1)}
            if not cells & taken:
                out.append((abs(dx) + abs(dy), dx, dy))
    return [(dx, dy) for _, dx, dy in sorted(out)[:limit]]


def compose(frag: Fragment, *, offset=(0.0, 0.0), window=None, ol: Outline | None = None, area: int | None = None,
            apron: bool = True, clear: float = COMPOSE_CLEAR, gblend: float | None = None, mod_folder=None,
            disc: int = 1, game=None, census_step: float = 1.0) -> Composition:
    """Rung 2 end to end: the outline (donor frame) -> translate -> mint -> opening -> apron -> open zip -> stamp ->
    gates -> binding plan. ``window`` = the donor window's stock tris (for the census against home; without it G4/G6
    are skipped and say so). Raises :class:`RiverRefused` at the first structural failure; the gates' verdicts --
    green or failing, each with locations -- are in ``report``. Nothing is written."""
    from .terrain import minted_area
    gblend = RIVER_GBLEND if gblend is None else gblend
    stamp = minted_area(area)
    A = stamp["area"]
    ol = outline(frag) if ol is None else ol
    tf, tol_ = translate(frag, offset), translate_outline(ol, offset)
    built = mint(tol_)
    jr = join_gates(built, tol_, tf.joins)                 # J1-J4 on the minted island

    # THE OPENING
    first, last = tol_.first, tol_.last
    chain = land_chain(tf, first, last)
    sea = list(tf.seaward) if first == "E" else list(reversed(tf.seaward))
    poly = [(p[0], p[2]) for p in chain] + [(p[0], p[2]) for p in sea[1:-1]]
    land_segs = [(a, b) for c in ("lawn", "source") for a, b in tf.boundary.get(c, ())]
    LA = np.asarray([(a[0], a[2]) for a, _ in land_segs])
    LB = np.asarray([(b[0], b[2]) for _, b in land_segs])
    kit = _kit_tris(built, A)
    from .island import _pip
    P2 = np.asarray([[p[0], p[2]] for t in kit for p in t["P"]])
    near = (_dist_to_segs(P2, LA, LB).min(axis=1) < clear).reshape(-1, 3)
    polyA = np.asarray(poly, dtype=float)
    cin = _pip_many(np.asarray([t["P"].mean(axis=0)[[0, 2]] for t in kit]), polyA)
    kept, dropped = [], []
    for t, nr, inside in zip(kit, near, cin):
        if inside or (t["fam"] != "rock" and nr.any()):
            dropped.append(t)
        else:
            kept.append(t)
    bad = [t for t in dropped if t["fam"] not in ("main", "rock")]
    if bad:
        raise RiverRefused("O2", f"the opening reaches {len(bad)} kit tri(s) that are neither lawn nor wall",
                           [tuple(t["P"].mean(axis=0)[[0, 2]]) for t in bad])
    over = [t for t, inside in zip(kept, _pip_many(np.asarray([t["P"].mean(axis=0)[[0, 2]] for t in kept]), polyA))
            if inside]
    if over:
        raise RiverRefused("O2", f"{len(over)} kept kit tri(s) still lie over the fragment",
                           [tuple(t["P"].mean(axis=0)[[0, 2]]) for t in over])

    # THE HOLE ARC: the kept kit's edges that a dropped tri used to share, less the two join columns -- read on the
    # mint's own keys, BEFORE the apron moves any of them (a lifted key no longer matches its dropped neighbour)
    k_cnt, k_float = Counter(), {}
    for t in kept:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = kk3(t["P"][a]), kk3(t["P"][b])
            k_cnt[_ek(ka, kb)] += 1
        for p in t["P"]:
            k_float.setdefault(kk3(p), tuple(map(float, p)))
    d_edges = set()
    for t in dropped:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = kk3(t["P"][a]), kk3(t["P"][b])
            d_edges.add(_ek(ka, kb))
    cols = {_ek(kk3(c), kk3(b)) for c, b in tf.joins.values()}
    hole = [e for e, n in k_cnt.items() if n == 1 and e in d_edges and e not in cols]
    adj = defaultdict(list)
    for a, b in hole:
        adj[a].append(b)
        adj[b].append(a)
    cf, cl = kk3(tf.joins[first][0]), kk3(tf.joins[last][0])
    odd = [k for k, v in adj.items() if len(v) != 2 and k not in (cf, cl)]
    if odd or len(adj.get(cf, ())) != 1 or len(adj.get(cl, ())) != 1:
        raise RiverRefused("O3", "the opening's rim is not one arc from crest to crest",
                           [(k[0], k[2]) for k in odd] or [(cf[0], cf[2]), (cl[0], cl[2])])
    harc, prev = [cf], None
    while harc[-1] != cl:
        nxt = [k for k in adj[harc[-1]] if k != prev]
        prev = harc[-1]
        harc.append(nxt[0])

    # THE APRON: the kit lawn near the land ring moves toward the ring's heights; the zip then welds to the moved
    # lawn on its exact floats (a lifted position = the mint's float plus the one lift every coincident corner took)
    nodes = [(p[0], p[2], p[1]) for p in chain[1:-1]]
    lift = _apron(kept, nodes, gblend) if apron else {}
    H = [(k_float[k][0], k_float[k][1] + lift[k], k_float[k][2]) if k in lift else k_float[k] for k in harc]
    Rr = [tuple(map(float, p)) for p in chain[1:-1]]
    if (H[0], H[-1]) != (Rr[0], Rr[-1]):
        raise RiverRefused("J1", "the opening's arc and the land ring do not share both crests exactly",
                           [(H[0][0], H[0][2]), (H[-1][0], H[-1][2])])
    # THE REFINEMENT is margin, measured: unrefined, cluster C's longest zip chord is 8.95u, 0.05 under G2
    zt, zip_splits = _refine_zip(_zip_dp_open(H, Rr), max_edge=ZIP_SPLIT)
    zt = [_up(z) for z in zt]

    # zip attributes: the island's grass at its area, mains UVs from the mint's own field, normals smoothed
    from . import grassland as G
    field_ = built["mains_field"]
    ID_ZIP = int(X.encode_id(0, A, 0, 0))
    zips = []
    for z in zt:
        P = np.asarray(z, dtype=float)
        c = P.mean(axis=0)
        cell = (math.floor(c[0] / 4.0), math.floor(c[2] / 4.0))
        if cell in field_:
            quad, ori = field_[cell]
        else:                                            # a cell the mint never covered: the seeded policy
            qd, od = G.assign_mains([cell], seed=0xF91)
            quad, ori = qd[cell], od[cell]
        uv = np.asarray([G.ground_uv(p[0], p[2], cell, quad, ori, "grass") for p in P], dtype=float)
        zips.append({"part": "terrain", "P": P, "uv": uv, "nrm": None, "tan": None, "idall": ID_ZIP, "topo": 0,
                     "fam": "zip", "src": "zip"})
    stock = []
    skip_pairs = []
    for t in tf.tris:
        new = _stamp_carried(t, A)
        skip_pairs.append((t["idall"], new))
        stock.append(dict(t, idall=new, src="stock"))
    acc = defaultdict(lambda: np.zeros(3))
    for t in kept + zips + [t for t in stock if t["part"] == "terrain"]:
        a, b, c = t["P"]
        n = np.cross(b - a, c - a)
        n = n if n[1] >= 0 else -n
        for p in t["P"]:
            acc[kk3(p)] += n
    for t in zips:
        t["nrm"] = np.asarray([acc[kk3(p)] / (np.linalg.norm(acc[kk3(p)]) or 1.0) for p in t["P"]])
    for t in kept:
        if any(kk3(p) in lift for p in t["P"]):
            t["nrm"] = np.asarray([acc[kk3(p)] / (np.linalg.norm(acc[kk3(p)]) or 1.0) for p in t["P"]])
    tris = kept + zips + stock

    # ---- THE GATES ----------------------------------------------------------------------------------------------
    from .placement import skip_parity_gate
    gates = {"J": jr}
    # zip envelope + G2 grain
    stock_edges = {_ek(kk3(t["P"][a]), kk3(t["P"][b])) for t in stock for a, b in ((0, 1), (1, 2), (2, 0))}
    zbad, zmax, rise_max, ny_min, inherited_climb = [], 0.0, 0.0, 1.0, 0.0
    for z in zips:
        P = z["P"]
        own = [(a, b) for a, b in ((0, 1), (1, 2), (2, 0)) if _ek(kk3(P[a]), kk3(P[b])) not in stock_edges]
        rise = max((abs(float(P[a][1] - P[b][1])) for a, b in own), default=0.0)   # a carried edge's climb is stock's
        inherited_climb = max(inherited_climb, float(P[:, 1].max() - P[:, 1].min()))
        n = np.cross(P[1] - P[0], P[2] - P[0])
        ny = abs(float(n[1])) / (float(np.linalg.norm(n)) or 1.0)
        e = max(math.hypot(*(P[a] - P[b])[[0, 2]]) for a, b in ((0, 1), (1, 2), (2, 0)))
        zmax, rise_max, ny_min = max(zmax, e), max(rise_max, rise), min(ny_min, ny)
        if rise > ZIP_RISE or ny < ZIP_NY_FLOOR or e >= ZIP_MAX_EDGE:
            zbad.append((tuple(round(float(v), 2) for v in P.mean(axis=0)[[0, 2]]), round(rise, 2), round(ny, 3),
                         round(e, 2)))
    gates["zip"] = {"tris": len(zips), "max_edge": round(zmax, 2), "max_rise": round(rise_max, 2),
                    "max_rise_incl_stock_edges": round(inherited_climb, 2),
                    "ny_min": round(ny_min, 3), "fails": len(zbad), "where": zbad[:12], "ok": not zbad}
    # G1 crack: once-edges the parts did not already have, bar the arc's coast and the seaward boundary
    # (the minted island was closed, so its own once-edges are exactly the coast's base edges)
    once = _soup_once(tris)
    bnd = {_ek(kk3(a), kk3(b)) for es in tf.boundary.values() for a, b in es}
    inherited_open = _soup_once(tf.tris) - bnd             # the fragment's own internal once-edges
    seam = {_ek(kk3(a), kk3(b)) for a, b in tf.boundary.get("water", ())}
    coast = _soup_once(kit) & once
    cracks = sorted(once - inherited_open - seam - coast)
    gates["G1"] = {"cracks": len(cracks), "where": [tuple(round(v, 2) for v in _mid(e)) for e in cracks[:12]],
                   "ok": not cracks, "coast_edges": len(coast), "seam_edges": len(seam & once),
                   "inherited_open": len(inherited_open & once)}
    # G3 weld audit: near-miss pairs the composition minted (the fragment's own are inherited)
    from .mesh import near_miss_pairs
    pairs = set(near_miss_pairs(p for t in tris for p in t["P"]))
    inherited = set(near_miss_pairs(p for t in tf.tris for p in t["P"]))        # the fragment's own
    inherited |= set(near_miss_pairs(built["world"]["pos"]))                     # the mint's own (border cuts)
    minted = sorted(pairs - inherited)
    gates["G3"] = {"near_miss": len(minted), "inherited": len(inherited & pairs),
                   "where": [(round(a[0], 2), round(a[2], 2)) for a, _ in minted[:12]], "ok": not minted}
    # G5 skip parity
    sp = skip_parity_gate(skip_pairs, label="river")
    gates["G5"] = {"flipped": sp["flipped"], "ok": sp["ok"], "skipped_carried": sum(
        1 for a, _ in skip_pairs if int(a) in (4078, 4088, 2040))}
    # G4 / G6 census against home at the same relative points; MISS 0 over the kit's own land
    from .placement import place
    ml, idx = _meshlist(tris)
    dx, dz = float(offset[0]), float(offset[1])
    fx = [p[0] for p in poly]
    fz = [p[1] for p in poly]
    if window is not None:
        dml, didx = _meshlist(window)
        stats, where = Counter(), defaultdict(list)
        GX, GZ = np.meshgrid(np.arange(min(fx) + 0.25, max(fx), census_step),
                             np.arange(min(fz) + 0.25, max(fz), census_step))
        pts = np.stack([GX.ravel(), GZ.ravel()], 1)
        pts = pts[np.concatenate([_pip_many(pts[k:k + 20000], polyA) for k in range(0, len(pts), 20000)])]
        for x, z in pts:
            gy, nm, _i, tp = place(ml, x, z, 0.0, sky=True, index=idx)
            hy, hn, _j, hp = place(dml, x - dx, z - dz, 0.0, sky=True, index=didx)
            if nm == "MISS" and hn != "MISS":
                k = "introduced_miss"
            elif (nm, tp) == (hn, hp):
                k = "same"
            elif hn == "MISS":
                k = "home_miss"
            else:
                k = f"{hn}/{hp}->{nm}/{tp}"
            stats[k] += 1
            if k != "same" and len(where[k]) < 6:
                where[k].append((round(float(x), 1), round(float(z), 1)))
        # inside the footprint the composed island must ground EXACTLY as home does: a miss home never had is a
        # stranding hole, and any other change is a kit or zip tri lying over the fragment (a stacked sheet)
        gates["G4"] = {"points": sum(stats.values()), "by": dict(stats.most_common()), "where": dict(where),
                       "ok": set(stats) <= {"same", "home_miss"}}
        moved = {k: n for k, n in stats.items() if k != "same" and ("Stream" in k or "RiverJoint" in k)}
        gates["G6"] = {"ok": not moved, "river_points_moved": moved, "where": {k: where[k] for k in moved}}
    else:
        gates["G4"] = gates["G6"] = {"ok": None, "why": "no donor window given: the census against home was skipped"}
    rim = built["rim"]
    rx, rz = [p[0] for p in rim], [p[1] for p in rim]
    GX, GZ = np.meshgrid(np.arange(min(rx) + 0.37, max(rx), 2.0), np.arange(min(rz) + 0.37, max(rz), 2.0))
    pts = np.stack([GX.ravel(), GZ.ravel()], 1)
    pts = pts[_pip_many(pts, np.asarray(rim, dtype=float)) & ~_pip_many(pts, polyA)]
    n_kit = len(pts)
    miss = [(round(float(x), 1), round(float(z), 1)) for x, z in pts
            if place(ml, x, z, 0.0, sky=True, index=idx)[1] == "MISS"]
    gates["G4_kit"] = {"points": n_kit, "miss": len(miss), "where": miss[:12], "ok": not miss}

    plan = binding_plan(tris, disc=disc, game=game, mod_folder=mod_folder)
    gates["B1"], gates["C1"] = plan.pop("B1"), plan.pop("C1")
    report = {"offset": [dx, dz], "area": {k: stamp[k] for k in ("area", "source")},
              "opening": {"kit_tris": len(kit), "dropped": len(dropped), "dropped_fams": dict(Counter(
                  t["fam"] for t in dropped)), "kept": len(kept)},
              "apron": {"on": apron, "gblend": gblend, "lifted": len(lift), "max_up": round(max(lift.values(), default=0.0), 2),
                        "max_down": round(min(lift.values(), default=0.0), 2)},
              "zip": {"hole_arc": len(H), "land_arc": len(Rr), "tris": len(zips), "splits": zip_splits},
              "tris": dict(Counter(t["src"] for t in tris)), "gates": gates,
              "green": all(g.get("ok") is not False for k, g in gates.items() if isinstance(g, dict) and k != "J")}
    return Composition(offset=(dx, dz), tris=tris, outline=tol_, plan=plan, report=report, footprint=poly)


def binding_plan(tris, *, disc: int = 1, game=None, mod_folder=None) -> dict:
    """THE BINDING PLAN (PLAN.md step 7), computed, not written: each target block's parts after the 64u split,
    the divert (every cell -> :data:`DIVERT_PREFAB`), the hidden blanks (every prefab part a cell does not carry --
    its own would free-ride), and the gates B1 (every cell open ocean; the prefab hosts every emitted part) and C1
    (the per-part budget). Sea4 is emitted everywhere: the island lane's cut sheet (rung 3) fills it. With
    ``mod_folder``, B1 also refuses a target cell another deploy there already holds."""
    from pathlib import Path
    from . import mesh as M_
    from .interior import split_borders8
    per = defaultdict(Counter)
    for part in sorted({t["part"] for t in tris}):
        parents = []
        for t in (t for t in tris if t["part"] == part):
            uv = t["uv"] if t["uv"] is not None else np.zeros((3, 2))
            nr = t["nrm"] if t["nrm"] is not None else np.tile([0.0, 1.0, 0.0], (3, 1))
            parents.append((tuple((*t["P"][k], *uv[k], *nr[k]) for k in range(3)), t["idall"], part))
        for blk, items in split_borders8(parents).items():
            per[(M_.wrap_block_col(blk[0]), blk[1])][part] += len(items)
    stock_parts = X.block_parts(disc=disc, game=game)
    host = set(stock_parts.get(DIVERT_PREFAB, ()))
    cells, b1, c1 = {}, [], []
    for blk in sorted(per):
        emitted = set(per[blk]) | {"sea4"}
        if blk in stock_parts:
            b1.append(f"{blk} has its own stock prefab ({len(stock_parts[blk])} parts): the divert cannot bind")
        if not 0 <= blk[1] < M_.GRID_ROWS:
            b1.append(f"{blk} is off the grid")
        lacking = sorted(emitted - host)
        if lacking:
            b1.append(f"{blk} emits {lacking}, which the divert prefab {DIVERT_PREFAB} does not host")
        for part, n in per[blk].items():
            if n > PART_BUDGET:
                c1.append(f"{blk} {PART_NAME[part]}: {n} tris")
        cells[blk] = {"tris": {PART_NAME[p]: n for p, n in sorted(per[blk].items())},
                      "blanks": sorted(PART_NAME[p] for p in host - emitted if p in PART_NAME),
                      "divert": list(DIVERT_PREFAB)}
    # THE MOD-TREE OCCUPANCY READ: the stock tree says "open ocean", which is a different question from "free" -- a
    # prior deploy in the target folder (rung 4: the live overworld folder holds 54 files on cluster C's first seam
    # placement) would be shadowed cell by cell, its neighbours left rendering against ours
    occupied = []
    if mod_folder:
        occupied = M_.existing_overrides(sorted((M_.wrap_block_col(b[0]), b[1]) for b in cells), mod_folder,
                                         disc=disc, game=game)
        if occupied:
            b1.append(f"{len(occupied)} override file(s) already deployed on the target cells in {mod_folder}, "
                      f"e.g. {[Path(p).name for p in occupied[:3]]}")
    return {"cells": {f"{b[0]},{b[1]}": v for b, v in cells.items()}, "occupied": occupied,
            "B1": {"ok": not b1, "fails": b1[:12], "cells": len(cells)},
            "C1": {"ok": not c1, "fails": c1[:12], "max": max((n for c in per.values() for n in c.values()),
                                                                default=0)}}


# ==== rung 3: the composition written (a scratch folder, never the install) ========================================
#
# The composed tris become per-block part meshes (block-local, every carried byte verbatim bar the stamp), the island
# lane's deep Sea4 sheet is cut out under the island AND the fragment (THE SEA4-UNDER-LAND LAW, conservative: a plane
# tri drops only when all three corners lie under them), and THE KNIT re-bands the seaward seam with the rim retile
# (rimretile: carry the tiles, do not author them) until the seam is a series of Wang tiles. The blocks keep their
# UNWRAPPED keys until the write: the retile steps neighbours linearly, and the only open water this footprint fits
# spans the world seam. Then everything is written under a root OUTSIDE the install, and audited from the bytes.

SEA_PARTS_ALL = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1")
#: the crop-made sea pairs stock authors nowhere (transplant.sea_adjacent_lawful; the deep system's sea3|sea4)
UNLAWFUL_SEA = frozenset({frozenset(p) for p in (("sea3", "sea4"), ("sea1", "sea4"), ("sea2", "sea4"),
                                                ("sea2", "sea5"))})


def _blockmesh(items, blk, part, *, disc: int = 1, lod: str = "0_1"):
    """``[(corners8, idall, tan_yzw)]`` world-frame -> a block-local BlockMesh, unindexed (the kit's writer shape)."""
    bx, by = blk
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    for corners, idall, yzw in items:
        base = len(pos)
        for c in corners:
            pos.append([c[0] - BLOCK_U * bx, c[1], c[2] + BLOCK_U * by])
            uv.append([c[3], c[4]])
            nrm.append([c[5], c[6], c[7]])
            tan.append([float(idall), *yzw])
            flat.append(len(pos) - 1)
        tris.append([base, base + 1, base + 2])
    return X.BlockMesh(name=f"Block[{bx}][{by}] {PART_NAME[part]}", disc=disc, x=bx, y=by, lod=lod,
                       vcount=len(pos), stride=48,
                       channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
                       chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
                       flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


BLOCK_U = 64.0


def part_meshes(comp: Composition, *, disc: int = 1, lod: str = "0_1") -> dict:
    """``{(bx, by): {part: BlockMesh}}`` -- the composition split at the 64u borders (every corner channel lerped:
    ``interior.split_borders8``), block-local, keyed by UNWRAPPED block. A carried tri keeps its tangent's y/z/w; a
    kit or zip tri writes the island lane's (0, 0, 1)."""
    from .interior import split_borders8
    per = defaultdict(lambda: defaultdict(list))
    for part in sorted({t["part"] for t in comp.tris}):
        parents = []
        for t in comp.tris:
            if t["part"] != part:
                continue
            uv = t["uv"] if t["uv"] is not None else np.zeros((3, 2))
            nr = t["nrm"] if t["nrm"] is not None else np.tile([0.0, 1.0, 0.0], (3, 1))
            yzw = tuple(float(v) for v in t["tan"][0][1:]) if t.get("tan") is not None else (0.0, 0.0, 1.0)
            parents.append((tuple((*map(float, t["P"][k]), *map(float, uv[k]), *map(float, nr[k])) for k in range(3)),
                            int(t["idall"]), yzw))
        for blk, items in split_borders8(parents).items():
            per[blk][part].extend(items)
    return {blk: {p: _blockmesh(items, blk, p, disc=disc, lod=lod) for p, items in parts.items()}
            for blk, parts in sorted(per.items())}


def _empty_part(blk, part, *, disc: int = 1, lod: str = "0_1"):
    return _blockmesh([], blk, part, disc=disc, lod=lod)


def _concat(blk, part, meshes, *, disc: int = 1, lod: str = "0_1"):
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    for bm in meshes:
        if bm is None:
            continue
        for tri in bm.tris:
            base = len(pos)
            for k in tri:
                pos.append(list(bm.chan_arrays[X.CH_POS][k]))
                nrm.append(list(bm.chan_arrays[X.CH_NRM][k]))
                uv.append(list(bm.chan_arrays[X.CH_UV][k]))
                tan.append(list(bm.chan_arrays[X.CH_TAN][k]))
                flat.append(len(pos) - 1)
            tris.append([base, base + 1, base + 2])
    bx, by = blk
    return X.BlockMesh(name=f"Block[{bx}][{by}] {PART_NAME[part]}", disc=disc, x=bx, y=by, lod=lod,
                       vcount=len(pos), stride=48,
                       channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
                       chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
                       flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _sub_mesh(bm, tris):
    import dataclasses as _dc
    return _dc.replace(bm, tris=[list(t) for t in tris])


def kit_sea4(meshes: dict, *, disc: int = 1, game=None, lod: str = "0_1", plane=None) -> dict:
    """The island lane's deep sheet (the (12,0) plane, hole-patched) on every block, CUT under everything the
    composition puts there -- the island's land and the fragment's own water and beach -- by THE SEA4-UNDER-LAND
    LAW's conservative rule (under, everywhere sampled), then joined by the fragment's own carried Sea4. Returns the
    per-block cut counts."""
    from .island import _sea_plane, _xz_tri_cover, _xz_inside
    plane = _sea_plane(disc, game) if plane is None else plane
    out = {}
    for blk, parts in meshes.items():
        under = _concat(blk, "terrain", [bm for p, bm in parts.items()], disc=disc, lod=lod)
        cover = _xz_tri_cover(under)
        P = plane.chan_arrays[X.CH_POS]
        keep = []
        for tri in plane.tris:
            a, b, c = ((P[k][0], P[k][2]) for k in tri)
            # THE COVERED-TRI TEST: the island lane drops a plane tri when its three corners lie under land, which
            # holds while the cover is convex across the cell. At a join it is not -- the kit's wall and the carried
            # water meet there round a sliver of open sea -- so the corners AND four interior points must be under
            pts = [a, b, c] + [((wa * a[0] + wb * b[0] + wc * c[0]), (wa * a[1] + wb * b[1] + wc * c[1]))
                               for wa, wb, wc in ((1 / 3, 1 / 3, 1 / 3), (0.6, 0.2, 0.2), (0.2, 0.6, 0.2),
                                                  (0.2, 0.2, 0.6))]
            if not all(_xz_inside(cover, x, z) for x, z in pts):
                keep.append(tri)
        cut = _concat(blk, "sea4", [_sub_mesh(plane, keep)], disc=disc, lod=lod)
        out[blk] = {"plane": len(plane.tris), "kept": len(cut.tris), "carried": len(parts["sea4"].tris)
                    if "sea4" in parts else 0}
        parts["sea4"] = _concat(blk, "sea4", [cut, parts.get("sea4")], disc=disc, lod=lod)
    return out


def sea_contacts(meshes: dict) -> Counter:
    """Unlawful sea-band contacts (:data:`UNLAWFUL_SEA`) by shared tri EDGE, across parts and blocks -- finer than
    a 4u-cell shade grid, which cannot see a contact inside one cell."""
    owner = defaultdict(set)
    for (bx, by), parts in meshes.items():
        for p, bm in parts.items():
            if p not in SEA_PARTS_ALL or bm is None:
                continue
            V = bm.chan_arrays[X.CH_POS]
            for tri in bm.tris:
                P = [(V[k][0] + BLOCK_U * bx, V[k][1], V[k][2] - BLOCK_U * by) for k in tri]
                if all(q[1] < -50.0 for q in P):
                    continue                             # a hidden blank
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    owner[_ek(kk3(P[a]), kk3(P[b]))].add(p)
    out = Counter()
    for e, ps in owner.items():
        for a in ps:
            for b in ps:
                if a < b and frozenset((a, b)) in UNLAWFUL_SEA:
                    out[f"{a}|{b}"] += 1
    return out


def knit_variants(donors, *, disc: int = 1, game=None):
    """The knit's tile vocabulary: :func:`rimretile.harvest_variants` block by block, FIRST WINS, in ``donors``
    order (put the carried cove's own blocks first). Pooled, it is empty on cluster C's window: stock writes the
    same Wang tile in two dialects across blocks (a wrap corner at u 0.0 at (13,15), 0.0317 at (13,14)), and the
    harvest drops a variant whose instances disagree. Per block every instance agrees, so first-wins keeps each
    tile verbatim from ONE stock block -- the cove's own where it has one. Returns ``(variants, {key: block})``."""
    from . import rimretile as RT
    variants, source = {}, {}
    for blk in donors:
        for k, m in RT.harvest_variants([tuple(blk)], disc=disc, game=game).items():
            if k not in variants:
                variants[k], source[k] = m, tuple(blk)
    return variants, source


def _home_cells(blocks, shift, *, disc: int = 1, game=None) -> dict:
    """Home's own sea bands at the composition's blocks (``shift`` = the whole-block translation): the knit's
    baseline -- stock is not perfect either (cluster C's cove: one under tile, two contradicting edges)."""
    from . import mesh as M_
    bp = X.block_parts(disc=disc, game=game)
    out = {}
    for (bx, by) in blocks:
        d = (M_.wrap_block_col(bx - shift[0]), by - shift[1])
        parts = {p: X.read_block(*d, disc=disc, part=p, game=game) for p in SEA_PARTS_ALL if p in bp.get(d, ())}
        for p in ("sea3", "sea4", "sea5"):
            parts.setdefault(p, _empty_part(d, p, disc=disc))
        out[(bx, by)] = parts                          # keyed like the composition: the same relative cells
    return out


def knit(meshes: dict, *, donors, disc: int = 1, game=None, lod: str = "0_1", max_passes: int = 6,
         home_shift=None) -> dict:
    """THE KNIT: the rim retile run on the composition's sea bands in memory (unwrapped keys), iterated to its fixed
    point, then W1 -- the retile's own audits (no tile facing deep without its transition, no two tiles
    contradicting across an edge, no unpaintable sliver) plus the tri-level contact census. Mutates ``meshes``."""
    from . import rimretile as RT
    cells = {}
    for blk, parts in meshes.items():
        for p in ("sea3", "sea4", "sea5"):                # apply_rim rebuilds only the bands a block already has
            parts.setdefault(p, _empty_part(blk, p, disc=disc, lod=lod))
        cells[blk] = {p: parts[p] for p in SEA_PARTS_ALL if p in parts}
    variants, source = knit_variants(donors, disc=disc, game=game)
    if not variants:
        raise RiverRefused("W1", "no sea5 termination tile could be harvested from the donors")
    before = {"seam": RT.seam_report(cells), "edges": len(RT.edge_disagreements(cells)),
              "contacts": dict(sea_contacts(cells))}
    passes = []
    for k in range(max_passes):
        plan = RT.plan_rim(cells)
        miss = RT.uncovered(plan, variants)
        if miss:
            raise RiverRefused("W1", f"deep-set(s) {miss} have no verbatim donor tile (synthesizing one is what "
                               "produced the checkerboard)",
                               [(64 * b[0] + 4 * i + 2, -64 * b[1] - 4 * j - 2) for b, cs in plan.items()
                                for (i, j), (_p, ds) in cs.items() if "".join(sorted(ds)) in miss])
        post, n = RT.apply_rim(cells, plan, variants, disc=disc, lod=lod)
        if not RT.repartition_ok(cells, post):
            raise RiverRefused("W1", "the knit changed geometry: not a pure re-shade")
        passes.append(n)
        after = {c: dict(cells[c], **post.get(c, {})) for c in cells}
        fixed = RT.seam_report(after) == RT.seam_report(cells)
        cells = after
        if not n or (fixed and k) or (len(passes) >= 2 and passes[-1] == passes[-2]):
            break
    for blk, parts in cells.items():
        meshes[blk].update(parts)
    seam = RT.seam_report(cells)
    edges = RT.edge_disagreements(cells)
    slivers = RT.unpaintable_slivers(cells)
    contacts = sea_contacts(meshes)
    from .transplant import wang_carry_gate
    wang = wang_carry_gate(cells, list(cells), enforce=True)
    rep = {"variants": len(variants), "variant_blocks": sorted({tuple(b) for b in source.values()}),
           "passes": passes, "quads": sum(passes), "before": before,
           "after": {"seam": seam, "edges": len(edges), "contacts": dict(contacts)},
           "edges_where": [e[0] for e in edges[:8]], "unpaintable": slivers[:8],
           "wang": {k: wang[k] for k in ("incoherent", "incoherent_deep", "incoherent_shallow", "detail")}}
    home_edges = set()
    if home_shift is not None:
        hc = _home_cells(list(cells), home_shift, disc=disc, game=game)
        home_edges = {(e[0], e[1]) for e in RT.edge_disagreements(hc)}
        rep["home"] = {"seam": RT.seam_report(hc), "edges": len(home_edges), "contacts": dict(sea_contacts(hc))}
    new_edges = [e for e in edges if (e[0], e[1]) not in home_edges]
    rep["edges_introduced"] = len(new_edges)
    rep["edges_introduced_where"] = [e[0] for e in new_edges[:8]]
    # W1: no tile faces deep without its transition, no unpaintable sliver, no crop-made sea pair at any tri edge,
    # the frame coherent, and no contradicting edge home does not have itself
    rep["ok"] = (seam["under"] == 0 and not slivers and not contacts and wang["incoherent"] == 0 and not new_edges)
    return rep


def write(meshes: dict, root, *, disc: int = 1, lod: str = "0_1", game=None) -> list:
    """Every block's files under ``root`` (a folder laid out as a mod folder: ``FF9_Data/WorldMap/...``), at its
    WRAPPED label: each emitted part, a hidden blank for every other part the divert prefab carries (else its own
    would free-ride), and the ``Donor.txt`` divert. ``root`` must lie OUTSIDE the game install -- this rung never
    writes there."""
    import dataclasses as _dc
    from pathlib import Path
    from .. import config
    from . import mesh as M_
    root = Path(root).resolve()
    try:
        gp = Path(config.find_game_path(game)).resolve()
    except Exception:                                    # noqa: BLE001 -- no install: nothing to protect
        gp = None
    if gp is not None and (root == gp or gp in root.parents):
        raise RiverRefused("B0", f"{root} is inside the game install: rung 3 writes only to a scratch folder")
    host = set(X.block_parts(disc=disc, game=game).get(DIVERT_PREFAB, ()))
    written = []
    for (bx, by), parts in sorted(meshes.items()):
        wbx = M_.wrap_block_col(bx)
        for p in sorted(host | {"terrain", "sea4"}):
            bm = parts.get(p)
            name = f"Block[{wbx}][{by}] {PART_NAME[p]}"
            if bm is None or not bm.tris:
                bm = M_.hidden_block_mesh(name=name, disc=disc, x=wbx, y=by, lod=lod)
            else:
                bm = _dc.replace(bm, x=wbx, y=by, name=name)
            path = root / M_.override_relpath(disc, wbx, by, lod, PART_NAME[p])
            path.parent.mkdir(parents=True, exist_ok=True)
            M_.write_ff9mesh(bm, path)
            written.append(path)
        dt = root / M_.donor_sidecar_relpath(disc, wbx, by, lod)
        dt.write_bytes(f"{DIVERT_PREFAB[0]},{DIVERT_PREFAB[1]}".encode("utf-8"))
        written.append(dt)
    return written


def audit_written(root, blocks, *, disc: int = 1, lod: str = "0_1", game=None, meshes=None, home=None) -> dict:
    """B1 ON THE BYTES, read back from ``root``: every cell diverts to :data:`DIVERT_PREFAB`, carries a file for
    every part that prefab hosts (nothing free-rides) and none it lacks (an unbound file is a silent no-op), and its
    Terrain is real; every file round-trips to what was meant to be written; and the engine's ground query over the
    WRITTEN stack (placement.census, block-local, registration order) misses nowhere in the cell -- except where
    home misses too at the same relative point (``home = (window_tris, (dx, dz), footprint)``: inside the carried
    footprint stock's own skipped banks are holes by design, THE BANK SKIP LAW)."""
    from pathlib import Path
    from . import mesh as M_
    from . import placement as P_
    root = Path(root)
    host = set(X.block_parts(disc=disc, game=game).get(DIVERT_PREFAB, ()))
    fails, census = [], {}
    if home is not None:
        hml, hidx = _meshlist(home[0])
        hdx, hdz = home[1]
        hpoly = np.asarray(home[2], dtype=float)
    for (bx, by) in sorted(blocks):
        wbx = M_.wrap_block_col(bx)
        d = root / M_.donor_sidecar_relpath(disc, wbx, by, lod)
        if not d.is_file() or d.read_bytes() != f"{DIVERT_PREFAB[0]},{DIVERT_PREFAB[1]}".encode():
            fails.append(f"({wbx},{by}) Donor.txt does not divert to {DIVERT_PREFAB}")
        rdir = d.parent
        files = {f.name[len(f"Block[{wbx}][{by}] "):-len(".ff9mesh")]: f
                 for f in rdir.glob(f"Block[[]{wbx}[]][[]{by}[]] *.ff9mesh")}
        want = {PART_NAME[p] for p in host | {"terrain", "sea4"}}
        if set(files) != want:
            fails.append(f"({wbx},{by}) files {sorted(files)} != the prefab's parts {sorted(want)}")
        parts = {}
        for name, f in files.items():
            bm = M_.blockmesh_from_ff9mesh(f, disc=disc, x=wbx, y=by, lod=lod, part=name.lower())
            parts[name] = bm
            if meshes is not None:
                src = meshes[(bx, by)].get(name.lower())
                n_src = len(src.tris) if src is not None and src.tris else 1
                if len(bm.tris) != n_src:
                    fails.append(f"({wbx},{by}) {name}: {len(bm.tris)} tris read back, {n_src} meant")
        t = parts.get("Terrain")
        if t is None or all(v[1] < -50.0 for v in t.verts):
            fails.append(f"({wbx},{by}) has no real Terrain: the divert needs one")
        ml = P_.build_meshlist({n: bm for n, bm in parts.items()})
        c = P_.census(ml, samples=32, frame="block_local")
        miss = c["miss"]
        inherited = 0
        if home is not None and miss:
            W_ = np.asarray([(x + BLOCK_U * bx, z - BLOCK_U * by) for x, z in miss])
            inside = _pip_many(W_, hpoly)
            keep = []
            for (x, z), (wx, wz), ins in zip(miss, W_, inside):
                if ins and P_.place(hml, wx - hdx, wz - hdz, 0.0, sky=True, index=hidx)[1] == "MISS":
                    inherited += 1
                else:
                    keep.append((x, z))
            miss = keep
        census[f"{wbx},{by}"] = {"miss": len(miss), "home_miss": inherited, "stacked": len(c["stacked"])}
        if miss:
            fails.append(f"({wbx},{by}) the written stack MISSES at {len(miss)} sample(s) home grounds, e.g. "
                         f"{[(round(x, 1), round(z, 1)) for x, z in miss[:2]]}")
    return {"ok": not fails, "fails": fails[:16], "cells": len(blocks), "census": census}


def write_composition(comp: Composition, root, *, window, donors, disc: int = 1, game=None,
                      lod: str = "0_1") -> dict:
    """Rung 3 end to end: the composition's part meshes, the kit's Sea4 cut under it, THE KNIT (W1), the write to
    ``root`` (outside the install) and B1 read back from the bytes. ``donors`` = the knit's tile vocabulary, the
    carried cove's own blocks first (:func:`knit_variants`); ``window`` = the donor's stock tris (home, for the
    baselines). Returns the report; nothing here touches the game."""
    shift = block_shift(comp.offset)
    meshes = part_meshes(comp, disc=disc, lod=lod)
    sea4 = kit_sea4(meshes, disc=disc, game=game, lod=lod)
    w1 = knit(meshes, donors=donors, disc=disc, game=game, lod=lod, home_shift=shift)
    from .texgates import sea_plan_gate
    sp = sea_plan_gate({b: list(parts.items()) for b, parts in meshes.items()}, list(meshes))
    written = write(meshes, root, disc=disc, lod=lod, game=game)
    b1 = audit_written(root, list(meshes), disc=disc, lod=lod, game=game, meshes=meshes,
                       home=(window, comp.offset, comp.footprint))
    return {"root": str(root), "files": len(written), "blocks": [list(b) for b in sorted(meshes)],
            "sea4": {f"{b[0]},{b[1]}": v for b, v in sea4.items()}, "W1": w1,
            "sea_plan": {k: sp[k] for k in ("A_ok", "A_submerged_tris", "B_ok", "B_max_ratio", "B_violations",
                                            "C_ok", "C_overlap_frac", "status")},
            "B1": b1, "meshes": meshes}


# ==== the verb: `world-river` (PLAN.md "What the verb does") ======================================================
#
# The CLI composes, stages and promotes: :func:`compose` runs every geometry gate; :func:`write_composition` writes
# the island to a STAGE outside the install (B0 stays true) and audits it there (W1, the sea plan, B1 on the bytes);
# :func:`write_verdict` decides; :func:`promote` moves exactly the audited bytes into the mod folder through the kit's
# one write seam (``mesh.deploy_override`` / ``mesh.deploy_donor_sidecar``: the ledger, the backups, the ownership
# refusal); the disc-4 mirror runs after, as for every world writer.

#: THE CLIFF-CORNER BAND STEP (rung 3; owner-passed in rung 4): the contradicting sea-band edges a donor's composition
#: introduces and the owner's eye accepted -- cluster C's at the W join's corner cell, the carried cliff's sea3 against
#: the kit cliff's Sea4 (the step home ships at its own E headland). Donor frame: (block x, block y, cell i, cell j).
#: W1 stays strictly red on them; the verb accepts exactly these and refuses any other.
UNDERSTOOD_EDGES = {"cluster-c": frozenset({(16, 16, 3, 14)})}


def block_shift(offset) -> tuple:
    """A world translation ``(dx, dz)`` -> the whole-block shift ``(sx, sy)`` the writer takes (block x grows with x,
    block y with -z). T0 refuses one off the 4u water lattice; T1 one on the lattice but not a whole 64u block: the
    write splits per block and diverts every cell to one prefab, so it moves whole blocks only."""
    dx, dz = (float(v) for v in offset)
    if dx % 4.0 or dz % 4.0:
        raise RiverRefused("T0", f"a translation of ({dx:g}, {dz:g}) leaves the 4u water lattice")
    sx, sy = int(round(dx / BLOCK_U)), int(round(-dz / BLOCK_U))
    if (sx * BLOCK_U, -sy * BLOCK_U) != (dx, dz):
        raise RiverRefused("T1", f"the write moves whole 64u blocks only, not ({dx:g}, {dz:g})")
    return sx, sy


def knit_donors(frag: Fragment) -> list:
    """The knit's tile vocabulary for :func:`write_composition`, first wins (:func:`knit_variants`): the carried
    cove's own Sea5 blocks, most first, then every block of the donor window -- the order rung 3 and rung 4 wrote."""
    own = Counter(t["blk"] for t in frag.tris if t["part"] == "sea5")
    (bx0, bx1), (by0, by1) = frag.donor.window
    return [b for b, _ in own.most_common()] + [(x, y) for x in range(bx0, bx1 + 1) for y in range(by0, by1 + 1)]


def stack_folders(game=None) -> list:
    """Memoria.ini's ``FolderNames``, highest priority first; ``[]`` when no install or ini resolves."""
    from .. import config
    from ..deploystack import parse_folder_names
    try:
        ini = config.find_game_path(game) / "Memoria.ini"
    except config.ConfigError:
        return []
    return parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []


def stack_occupancy(cells, mod_folder: str, *, discs=(1, 4), game=None, lod: str = "0_1") -> dict:
    """THE STACK READ (rung 4's lab check, made the verb's): override files already deployed on ``cells`` in
    ``mod_folder`` AND in every folder ``FolderNames`` stacks, per disc. The engine resolves each part file through
    the stack on its own, so a cell two folders override renders a mix of two deploys' parts (or one hides the
    other). ``{(folder, disc): [paths]}``, non-empty entries only; ``cells`` are wrapped labels."""
    from . import mesh as M_
    out = {}
    for fo in [str(mod_folder)] + [f for f in stack_folders(game) if f != str(mod_folder)]:
        for d in discs:
            hits = M_.existing_overrides(cells, fo, disc=d, lod=lod, game=game)
            if hits:
                out[(fo, d)] = hits
    return out


def auto_offset(ol: Outline, mod_folder: str, *, discs=(1, 4), game=None, limit: int = 64):
    """``--at auto``: the nearest whole-block shift (:func:`open_ocean_offsets`) whose footprint no stacked folder
    overrides. The footprint is the minted island's block RECTANGLE, a superset of the cells the write touches, so a
    pick is free wherever the composition lands (B1 re-checks the exact cells). Returns ``((dx, dz), skipped)``:
    the world translation and the nearer shifts passed over, each with its occupancy count."""
    from . import mesh as M_
    blocks = sorted(mint(ol)["blocks"])
    bx0, bx1 = min(b[0] for b in blocks), max(b[0] for b in blocks)
    by0, by1 = min(b[1] for b in blocks), max(b[1] for b in blocks)
    skipped = []
    for sx, sy in open_ocean_offsets(blocks, limit=limit, game=game):
        cells = sorted({(M_.wrap_block_col(x + sx), y + sy) for x in range(bx0, bx1 + 1) for y in range(by0, by1 + 1)})
        occ = stack_occupancy(cells, mod_folder, discs=discs, game=game)
        if not occ:
            return (BLOCK_U * sx + 0.0, -BLOCK_U * sy + 0.0), skipped     # + 0.0: never a -0.0
        skipped.append(((sx, sy), sum(len(v) for v in occ.values())))
    raise RiverRefused("B1", f"none of the {len(skipped)} nearest open-ocean placements is free of other deploys "
                       "in the stack: pick one with --at")


def write_verdict(rep: dict, comp: Composition, donor: RiverDonor) -> list:
    """The verb's verdict on a staged write (:func:`write_composition`'s report): B1 on the bytes; the sea plan's A
    (no submerged land) and C (the overlap ceiling) -- B only warns, the island lane's continent-scale class; and W1,
    which may be red on exactly the band edges :data:`UNDERSTOOD_EDGES` names for this donor and nothing else.
    Returns the failures as ``(gate, message)``; empty = deploy."""
    out = []
    if not rep["B1"]["ok"]:
        out.append(("B1", "the written bytes do not bind: " + "; ".join(rep["B1"]["fails"][:4])))
    sp = rep["sea_plan"]
    if not sp["A_ok"]:
        out.append(("sea_plan", f"{sp['A_submerged_tris']} land tri(s) sit under the sea plane"))
    if not sp["C_ok"]:
        out.append(("sea_plan", f"the sea/land overlap is {sp['C_overlap_frac']:.1%}, over the ceiling"))
    w1 = rep["W1"]
    shift = block_shift(comp.offset)
    understood = {(x + shift[0], y + shift[1], i, j) for x, y, i, j in UNDERSTOOD_EDGES.get(donor.name, ())}
    where = [tuple(e) for e in w1["edges_introduced_where"]]
    stray = [e for e in where if e not in understood]
    seam = w1["after"]["seam"]
    if seam["under"]:
        out.append(("W1", f"{seam['under']} tile(s) face deep water without their transition"))
    if w1["after"]["contacts"]:
        out.append(("W1", f"crop-made sea pairs at tri edges: {w1['after']['contacts']}"))
    if w1["unpaintable"]:
        out.append(("W1", f"{len(w1['unpaintable'])} unpaintable sliver(s), e.g. {w1['unpaintable'][:2]}"))
    if w1["wang"]["incoherent"]:
        out.append(("W1", f"{w1['wang']['incoherent']} incoherent Wang frame(s)"))
    if stray or w1["edges_introduced"] > len(where):
        out.append(("W1", f"{w1['edges_introduced']} contradicting band edge(s) home lacks, not all THE "
                          f"CLIFF-CORNER BAND STEP: {stray[:4]}"))
    return out


_STAGED = re.compile(r"Block\[(\d+)\]\[(\d+)\] (\w+)\.(ff9mesh|txt)")


def promote(stage, mod_folder: str, *, disc: int = 1, lod: str = "0_1", game=None) -> list:
    """THE PROMOTION: every file :func:`write` staged under ``stage`` (outside the install, B0) deployed into
    ``mod_folder`` through the kit's one write seam -- :func:`mesh.deploy_override` per part mesh,
    :func:`mesh.deploy_donor_sidecar` per divert -- so the folder gets the ledger rows, the backups and the
    ownership refusal every world writer gets. P0 holds it to the audited bytes: before the first write every staged
    mesh must round-trip through the seam's serializer byte for byte, and after the last every deployed file must
    equal its staged one. Returns the deployed paths (meshes first, then the diverts), for the disc mirror."""
    from pathlib import Path
    from . import mesh as M_
    stage = Path(stage)
    meshes, diverts = [], []
    for f in sorted(p for p in stage.rglob("*") if p.is_file()):
        m = _STAGED.fullmatch(f.name)
        if not m:
            raise RiverRefused("P0", f"the stage holds a file the writer does not write: {f.relative_to(stage)}")
        x, y, part, ext = int(m[1]), int(m[2]), m[3], m[4]
        if ext == "txt":
            diverts.append((f, x, y, tuple(int(v) for v in f.read_text(encoding="utf-8").split(","))))
            continue
        bm = M_.blockmesh_from_ff9mesh(f, disc=disc, x=x, y=y, lod=lod, part=part.lower())
        if M_.ff9mesh_bytes(bm) != f.read_bytes():
            raise RiverRefused("P0", f"{f.name} does not round-trip through the deploy seam byte for byte")
        meshes.append((f, bm, part))
    pairs = [(f, M_.deploy_override(bm, mod_folder=mod_folder, game=game, lod=lod, part=part, disc=disc))
             for f, bm, part in meshes]
    pairs += [(f, M_.deploy_donor_sidecar(d[0], d[1], mod_folder=mod_folder, disc=disc, x=x, y=y, lod=lod,
                                          game=game)) for f, x, y, d in diverts]
    bad = [Path(dst).name for src, dst in pairs if Path(dst).read_bytes() != src.read_bytes()]
    if bad:
        raise RiverRefused("P0", f"{len(bad)} deployed file(s) differ from the audited stage, e.g. {bad[:3]}")
    return [dst for _, dst in pairs]


def red_gates(comp: Composition, stack: dict, mod_folder: str, donor: RiverDonor) -> list:
    """The composition's red gates plus THE STACK READ, as ``(gate, message)`` in report order. B1 names this verb's
    own earlier deploy (``--remove`` is the way out) apart from another's (none is offered)."""
    red = [(k, "; ".join(map(str, g["fails"][:4])) if g.get("fails") else f"red at {str(g.get('where'))[:240]}")
           for k, g in comp.report["gates"].items() if isinstance(g, dict) and g.get("ok") is False]
    if stack:
        more = {k: p for k, p in stack.items() if k != (str(mod_folder), donor.disc)}   # compose's B1 names that one
        held = ": " + "; ".join(f"{fo} disc {d} ({len(p)} file(s))" for (fo, d), p in sorted(more.items()))
        own = any(fo == str(mod_folder) for fo, _d in stack)                           # the target holds some of it
        red.append(("B1", "the stack already overrides these cells -- re-site with --at (or --at auto), or take that "
                          "deploy out first" + (" (this verb's own earlier one: `world-river --remove --at "
                                                f"{comp.offset[0]:g},{comp.offset[1]:g}`)" if own else "")
                    + (held if more else "")))
    return red


@dataclass
class RiverDeploy:
    """One :func:`deploy` run: everything the CLI reports from. ``red`` holds every refusing gate as
    ``(gate, message)`` in report order (empty = it deployed, or would have); ``written`` the promoted disc-1 paths
    (empty on a dry run or a refusal); ``mirror`` the disc-4 mirror's summary (``discmirror.auto_mirror``)."""
    donor: RiverDonor
    mod_folder: str
    frag: Fragment
    ol: Outline
    comp: Composition
    cells: list
    stack: dict
    skipped: list
    rep: dict | None = None
    fails: list = field(default_factory=list)
    red: list = field(default_factory=list)
    written: list = field(default_factory=list)
    mirror: dict | None = None


def deploy(mod_folder: str, *, donor: RiverDonor = None, offset=None, area=None, apron: bool = True,
           dry_run: bool = False, skip_mirror: bool = False, game=None, on_planned=None,
           on_gated=None) -> RiverDeploy:
    """THE VERB'S PIPELINE, one function for `world-river` and world-fuse's ``[[river]]`` row (RUNG5.md 5b: a recipe
    writes the CLI's bytes because both run this). Compose and gate (``offset=None`` is ``--at auto``); THE STACK
    READ; stage the write OUTSIDE the install and audit it there (:func:`write_composition`, :func:`write_verdict`);
    then, unless ``dry_run`` or any gate is red, :func:`promote` exactly the staged bytes and mirror disc 4 -- both
    under a :class:`mesh.ledger_pipeline` tag naming this verb and the placement, so ``--remove`` owns the rows
    whichever verb ran the pipeline.

    A red gate does not raise: it lands in ``red`` so the caller can report every gate. Raises :class:`RiverRefused`
    (T0/T1 before the first read, B1 when ``auto`` finds no free placement, P0 at the promotion) and the install's
    ``ValueError`` / ``FileNotFoundError``. ``on_planned(d)`` runs once the composition and the stack read exist;
    ``on_gated(d)`` once every gate has a verdict, before anything is promoted (the CLI prints from both)."""
    import shutil
    import tempfile
    from pathlib import Path
    from . import discmirror as DM
    from . import mesh as M_
    donor = donor or CLUSTER_C
    discs = (donor.disc,) if skip_mirror else (donor.disc, 4)
    if offset is not None:
        block_shift(offset)                                   # T0 / T1 before the first read
    win = read_window(donor, game=game)
    frag = build_fragment(win, donor)
    ol = outline(frag)
    skipped = []
    if offset is None:
        offset, skipped = auto_offset(ol, mod_folder, discs=discs, game=game)
    comp = compose(frag, offset=offset, window=win, ol=ol, area=area, apron=apron, mod_folder=mod_folder,
                   disc=donor.disc, game=game)
    cells = sorted(tuple(int(v) for v in k.split(",")) for k in comp.plan["cells"])
    d = RiverDeploy(donor=donor, mod_folder=str(mod_folder), frag=frag, ol=ol, comp=comp, cells=cells,
                    stack=stack_occupancy(cells, mod_folder, discs=discs, game=game), skipped=skipped)
    if on_planned:
        on_planned(d)
    d.red = red_gates(comp, d.stack, mod_folder, donor)
    stage_root = Path(tempfile.mkdtemp(prefix="ff9-world-river-"))
    try:
        if not d.red:
            try:
                d.rep = write_composition(comp, stage_root / "stage", window=win, donors=knit_donors(frag),
                                          disc=donor.disc, game=game)
            except RiverRefused as e:
                d.red.append((e.gate, str(e)))
            else:
                d.fails = write_verdict(d.rep, comp, donor)
                d.red += d.fails
        if on_gated:
            on_gated(d)
        if d.red or dry_run:
            return d
        tag = M_.ledger_pipeline(REMOVE_VERB, at=[float(comp.offset[0]), float(comp.offset[1])], donor=donor.name)
        with tag:
            d.written = list(promote(stage_root / "stage", mod_folder, disc=donor.disc, game=game))
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
    with tag:
        d.mirror = DM.auto_mirror(d.written, mod_folder=mod_folder, skip_mirror=skip_mirror)
    return d


# ---- taking a deploy back out: `world-river --remove` -------------------------------------------------------------
#
# B1 refuses ANY override on the target cells, this verb's own earlier deploy included, and it stays that way: a
# redeploy is a REMOVAL followed by an ordinary run, which re-reads the whole stack on clean cells. The removal deletes
# exactly the files the folder's ledger says this verb wrote at the placement's cells, on disc 1 and the disc-4 mirror,
# all or nothing. (Not an --allow-overwrite: that would leave the verb a waiver past B1, could not take a river out,
# and would orphan any cell an earlier kit's composition covered and this one does not.)

#: the verb a ledger row must have run (its argv, :func:`mesh.ledger_verb`) for :func:`remove_deploy` to delete its bytes
REMOVE_VERB = "world-river"


def ledger_shift(argv):
    """The whole-block shift a world-river ledger row's ``argv`` placed at (its last ``--at``), or ``None`` when the
    argv does not say: ``--at auto``, or no ``--at`` that parses."""
    toks = [str(t) for t in (argv or ())]
    val = None
    for i, tok in enumerate(toks):
        if tok == "--at" and i + 1 < len(toks):
            val = toks[i + 1]
        elif tok.startswith("--at="):
            val = tok[len("--at="):]
    if val is None or val.strip().lower() == "auto":
        return None
    try:
        dx, dz = (float(v) for v in val.split(","))
        return block_shift((dx, dz))
    except (ValueError, RiverRefused):
        return None


def _row_verb_shift(row) -> tuple:
    """``(verb, shift)`` a ledger row was written under: its ``pipeline`` tag when this verb's pipeline ran inside
    another (world-fuse's ``[[river]]`` row: the argv names world-fuse and a recipe, the tag names world-river and the
    placement; :class:`mesh.ledger_pipeline`), else its own argv. ``shift`` is ``None`` when the row does not say."""
    from . import mesh as M_
    tag = row.get("pipeline") or {}
    if tag.get("verb"):
        try:
            return tag["verb"], (None if tag.get("at") is None else block_shift(tag["at"]))
        except (ValueError, TypeError):
            return tag["verb"], None
    return M_.ledger_verb(row.get("argv")), ledger_shift(row.get("argv"))


def _same_shift(a, b) -> bool:
    from . import mesh as M_
    return a[1] == b[1] and (a[0] - b[0]) % M_.GRID_COLS == 0            # the x-torus: 24 columns is no shift


def _row_who(e) -> str:
    argv = " ".join(str(t) for t in (e.get("argv") or ())) or "(argv unrecorded)"
    if len(argv) > 100:                                  # elide the middle: a long absolute folder must not hide --at
        argv = argv[:40] + " ... " + argv[-55:]
    return f"`{argv}` at {e.get('utc')}"


def deploy_ownership(cells, mod_folder: str, *, shift, discs=(1, 4), game=None, lod: str = "0_1") -> dict:
    """THE OWNERSHIP READ (reads only): every override file in ``mod_folder`` on ``cells`` (wrapped labels) on each of
    ``discs``, judged against the folder's deploy ledger. A file is THIS deploy's when
      1. the LAST ledger row for its (disc, cell, part) records exactly its bytes now -- no hand edit, no later writer
         and no removal since; and
      2. some row for that target with those bytes ran :data:`REMOVE_VERB` at this placement: a row whose ``--at``
         names another whole-block shift is another deploy. ``--at auto`` does not say, and B1 never lets two of this
         verb's deploys share a cell in one folder.
    A later re-copy of the same bytes by another writer (a ``world-mirror`` run) keeps them ours: the content is.
    Returns ``{"owned": [{"path", "disc", "cell", "part", "sha256"}], "foreign": [(path, disc, why)]}``."""
    import hashlib
    from pathlib import Path
    from .. import config
    from . import mesh as M_
    rows = defaultdict(list)
    for e in M_.read_ledger(Path(config.find_game_path(game)) / mod_folder):
        try:
            rows[(int(e["write_disc"]), (int(e["cell"][0]), int(e["cell"][1])), str(e["part"]))].append(e)
        except (KeyError, TypeError, ValueError, IndexError):
            continue                                        # a row of another shape never claims a file
    owned, foreign = [], []
    for d in discs:
        for p in map(Path, M_.existing_overrides(cells, mod_folder, disc=d, lod=lod, game=game)):
            m = _STAGED.fullmatch(p.name)
            if not m:
                foreign.append((p, d, "not a file this verb writes"))
                continue
            cell, part = (int(m[1]), int(m[2])), m[3]
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            rs = rows.get((d, cell, part), [])
            if not rs:
                foreign.append((p, d, "no ledger row: a pre-ledger deploy, a hand copy or a tool outside the write "
                                      "seam"))
                continue
            last = rs[-1]
            if last.get("sha256") != sha:
                why = ("the ledger last REMOVED it; these bytes came back without a row" if last.get("op") == "remove"
                       else "its bytes are not the last ledgered write: a hand edit, or a writer outside the seam")
                foreign.append((p, d, f"{why} (last row: {_row_who(last)})"))
                continue
            mine = [r for r in rs if r.get("sha256") == sha and _row_verb_shift(r)[0] == REMOVE_VERB
                    and (_row_verb_shift(r)[1] is None or _same_shift(_row_verb_shift(r)[1], shift))]
            if not mine:
                foreign.append((p, d, f"another deploy's: last written by {_row_who(last)}"))
                continue
            owned.append({"path": p, "disc": d, "cell": cell, "part": part, "sha256": sha})
    return {"owned": owned, "foreign": foreign}


def remove_deploy(cells, mod_folder: str, *, shift, discs=(1, 4), game=None, lod: str = "0_1",
                  dry_run: bool = False) -> dict:
    """THE REMOVAL: :func:`deploy_ownership`, then delete exactly the files it owns. ALL OR NOTHING: R1 names every
    foreign file before the first delete, R0 refuses cells that hold nothing of ours. Per file it re-hashes first (a
    concurrent session writing between the read and the delete stops it, R1, naming what was already removed --
    re-run to finish, the rest are still ours), parks ``<name>.bak-<ts>`` beside it (:func:`mesh.park_backup`, a suffix
    the occupancy read and the mirror never see), deletes it and appends a removal row to the ledger. Only
    ``mod_folder`` is touched: the other stacked folders stay, and the next deploy's stack read still refuses them.
    Returns ``{"removed": [rows], "backups": [paths]}`` (``removed`` = what would go, on ``dry_run``)."""
    import hashlib
    from pathlib import Path
    from .. import config
    from . import mesh as M_
    own = deploy_ownership(cells, mod_folder, shift=shift, discs=discs, game=game, lod=lod)
    if own["foreign"]:
        raise RiverRefused("R1", f"{len(own['foreign'])} file(s) on the target cells are not this verb's deploy at this "
                                 "placement, so nothing was removed: " + "; ".join(
                                     f"Disc{d} {p.name}: {why}" for p, d, why in own["foreign"][:6])
                           + (" ..." if len(own["foreign"]) > 6 else ""))
    if not own["owned"]:
        raise RiverRefused("R0", f"nothing to remove: {mod_folder} holds no override on these cells on disc(s) "
                                 f"{list(discs)}")
    if dry_run:
        return {"removed": own["owned"], "backups": []}
    mod_root = Path(config.find_game_path(game)) / mod_folder
    removed, backups = [], []
    for f in own["owned"]:
        p = f["path"]
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
            raise RiverRefused("R1", f"Disc{f['disc']} {p.name} changed after the ownership read (another session?): "
                                     f"stopped after removing {len(removed)} of {len(own['owned'])} file(s). Re-run "
                                     "--remove to take out the rest of this deploy.")
        bak = M_.park_backup(p)
        p.unlink()
        M_.record_ledger_removal(mod_root, cell=f["cell"], part=f["part"], write_disc=f["disc"],
                                 removed_sha256=f["sha256"], backup=bak)
        removed.append(f)
        backups.append(bak)
    return {"removed": removed, "backups": backups}

