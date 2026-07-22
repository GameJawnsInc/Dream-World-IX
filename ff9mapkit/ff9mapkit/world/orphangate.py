"""THE ORPHAN-DECAL GATE -- a carry-time productization of the comp[1] fringe-arc's proven rule set
(``studies/overworld-topography/comp1_orphan_redress.py`` --census3 / ``classify_tri_any_pair`` +
``_row_lawfulness`` + ``topo_consistency_defects``, in-game proven across 3 redress rounds / 15
cells on the deployed comp[1] region, 2026-07-22). Read that study file's module docstring first --
it is this module's contract; ``GROUND-FAMILY-DECODE-2026-07-19.md`` Round 10 earmarked exactly this
productization.

THE DEFECT CLASS: a transition-vocabulary tri (:data:`~ff9mapkit.world.grassland.STRIPS` -- today
``('grass','desert')`` or ``('desert','dunes')``, any row, any orientation) is an ORPHAN unless its
justifying neighbourhood context holds:

* **straddle rows** (1/3) need a genuine SAME-CELL straddle of the pair's two families (the decal's
  two halves exist to union into one rect across exactly two different-family tris sharing one
  cell) -- unconditional; no neighbour search rescues a straddle-row decal on a pure-family cell.
* **fringe rows** (0/2) need the partner family within the calibrated accept radius (2 cells; the
  observed curvature bound is 4) -- Law 4's modal-1 dressing band, generously re-verified.
* **topo-consistency** (orthogonal to context): within the loaded region, a (pair,row) fringe
  group's topo is measured LIVE (never hardcoded); a tri breaking an overwhelming majority is a
  topo/UV mismatch even with lawful context nearby (this axis is what the original colour-band
  filter lacked, and what let a misassigned tile slip past it).

THE REDRESS (opt-in, ``redress=True``): the arc's own proven FIX-G shape -- UV always, topo only
when the tri still carries the STRIPS decal's own dedicated fringe topo (not yet the family's own
plain-mains topo) -- via the SAME ``grassland.assign_mains`` -> ``grassland.ground_uv`` call the
shipped ``GroundRetile`` "recovered" path already uses. Zero geometry; vertex positions, normals and
tangent[1:] (y/z/w) are never touched. IN-MEMORY only, at build time, before any write -- never
touches an already-deployed file.

SCOPE: hooked at :func:`~ff9mapkit.world.transplant.transplant` /
:func:`~ff9mapkit.world.transplant.transplant_region` (the only carry paths where STRIPS-vocabulary
terrain content can appear -- ``world-island``/``world-mountain``/``world-forest`` never touch the
STRIPS vocabulary at all, confirmed by grep, and neither existing carry-time gate
(:func:`~ff9mapkit.world.transplant.wang_carry_gate`, ``_mod_overwrite_gate``) reaches them either).
:func:`~ff9mapkit.world.transplant.morph_in_place` has no donor mapping and is likewise outside both
precedent gates' scope -- excluded here too, for the same reason. :func:`~ff9mapkit.world.fuse.fuse_layout`
reaches :func:`~ff9mapkit.world.transplant.transplant_region` without a dedicated top-level
``enforce_orphan_decals``/``allow_orphan_decals``/``redress_orphans`` parameter of its own -- a
placement dict MAY still set them (``fuse_layout``'s ``_kw`` forwards a placement's own kwargs
verbatim), but absent that they default ``False``, i.e. WARN-only through a fuse layout. That is
safe (WARN mode never mutates a byte) and deliberate, not an oversight -- ported flags stay off by
default everywhere until a caller opts in.

Follows :func:`~ff9mapkit.world.transplant.wang_carry_gate`'s exact shape: WARN by default (``ok``
stays ``True``, a ``warn`` flag surfaces the finding), ``enforce=True`` hard-fails, ``allow=True``
waives even when enforced. In WARN mode (the default -- ``redress=False``) this gate is PURELY
READ-ONLY: it never mutates a single byte of the meshes it inspects, so wiring it into an existing
carry/retile path changes zero output bytes unless ``--redress-orphans`` is explicitly passed.

THE RING-CONTEXT FIX (2026-07-22, RULE-FIDELITY re-pass against ``--census3``'s
``round3_generalized_census``): the first port scoped BOTH Class A's fringe-row radius search and
Class B's topo-consistency group statistics to ``cell_meshes`` alone (the just-carried region) --
``--census3`` always reads a 1-block Moore RING of REAL bordering terrain (an already-deployed mod
override where one exists, else real stock bytes) alongside the carried core, for both checks. A
carried region is small (often a single block); a fringe group can be too thin to judge, or a
legitimately-dressed edge decal's partner family can sit one cell outside the carry, without that
ring. :func:`orphan_decal_gate` now takes an injectable ``context_provider`` (default
:func:`default_context_provider`, matching ``--census3``'s own deployed-override-else-stock,
READ-ONLY reader) and feeds its ring records into BOTH checks alongside ``cell_meshes``'s own,
exactly as ``round3_generalized_census``/``topo_consistency_defects`` do. The ring is READ-ONLY --
this changes zero output bytes on the default (WARN, ``redress=False``) path; a caller may inject a
synthetic provider (a plain callable, no game install / SE bytes needed) for hermetic tests.

THE AMBIGUOUS VERDICT: ``--census3``'s own ``round3_build_and_gate`` hard-refuses (assert) when
Class A and Class B claim the SAME cell -- an unmodelled 3rd shape neither class's fix mechanism
was designed for. A gate must degrade gracefully rather than crash a caller's build, so this is
ported as its own verdict (``klass="AMBIGUOUS"``) rather than an assertion: it still counts toward
``n_orphans``/``warn``/``ok`` exactly like Class A/B (WARN loudly, fail under ``enforce=True``), but
:func:`orphan_decal_gate`'s ``redress=True`` path REFUSES to touch it -- an unmodelled state is never
auto-fixed blind. Surfaced on the gate result as ``n_ambiguous``/``ambiguous_cells``.
"""
from __future__ import annotations

import collections
import functools
import math

from . import grassland as GL
from . import mesh as _mesh
from .. import config as _config
from .extract import block_world_origin, decode_id, encode_id, read_block

#: the fringe-row (0/2) partner-family accept radius (Law 4's modal 1 + Round 2's own generosity,
#: ``comp1_orphan_redress.py`` ``ROUND3_ACCEPT_RADIUS``) and the observed outer curvature-exception
#: search bound (a zigzag reentrant reached depth 3-4) beyond which a partner never rescues a hit.
ACCEPT_RADIUS = 2
MAX_BAND_RADIUS = 4

#: topo-consistency (Class B): refuse to judge a (pair,row) group thinner than this, or without an
#: overwhelming majority topo -- too small a sample to call any topo value "the norm" with confidence.
FRINGE_MODE_MIN_GROUP = 5
FRINGE_MODE_MIN_SHARE = 0.8

#: the FIX-G precedent's own seed (``dunes_true_carry.py`` / the shipped ``GroundRetile`` "recovered"
#: path) -- kept identical so a redressed cell's mains assignment matches what an ADJACENT recovered
#: cell in the SAME build would pick (the neighbour-avoid quadrant/rotation policy is seed-keyed).
DEFAULT_REDRESS_SEED = 0xF93

#: below this Y, a tri is a below-world BLANKING STUB (``mesh.hidden_block_mesh`` ``y_depth=-80``,
#: ``mesh.stub_terrain_mesh`` ``y=-100``), never real carried terrain (real overworld relief never
#: reaches anywhere close) -- excluded from the census so a blanked "Terrain" part's degenerate
#: placeholder tri can never spuriously register a family at its (block-local origin) cell.
STUB_Y_FLOOR = -50.0


def _strip_uv_for_pair(pair, x: float, z: float, cell, row: int, ori: int):
    """One corner's UV under ``grassland.STRIPS[pair]``'s row/orientation decode (the same rect
    :func:`~ff9mapkit.world.grassland.ground_uv` uses for plain mains, generalized to the
    transition-strip band + the pair's own translation)."""
    spec = GL.STRIPS[pair]
    du, dv = spec["du"], spec["dv"]
    (i, j) = cell
    fx = (x - 4.0 * i) / 4.0
    fz = (z - 4.0 * j) / 4.0
    a, b = GL.rot_ab(fx, fz, ori)
    a, b = max(0.0, min(1.0, a)), max(0.0, min(1.0, b))
    u0, u1 = GL.STRIP_U
    v0, v1 = GL.STRIPS_V[row]
    return (u0 + a * (u1 - u0) + du, v0 + b * (v1 - v0) + dv)


def classify_strip_tri(world_pts, uvs, cell, eps: float = 0.004):
    """Is this tri a STRIPS transition-vocabulary decal, and if so which ``(pair, row, ori)``?
    Brute-force UV/row decode over every catalogued :data:`~ff9mapkit.world.grassland.STRIPS` pair,
    every row, every orientation (generalized from
    ``studies/overworld-topography/dunes_grazing_eye.py``'s single-pair hardcoded decoder /
    ``comp1_orphan_redress.classify_tri_any_pair``). Returns ``(pair, row, ori)`` or ``None``.

    Unlike the study's own diagnostic ``classify_tri_any_pair``, a plain MAINS/ground classification
    is intentionally NOT attempted here: no orphan-decal rule below ever consumes it (a non-decal
    tri simply isn't one, whatever plain family it wears) -- and skipping that branch keeps this the
    hot inner loop of a gate that runs on every carry, not just a diagnostic tool."""
    def match(fn):
        return all(abs(fn(p)[0] - uv[0]) < eps and abs(fn(p)[1] - uv[1]) < eps
                   for p, uv in zip(world_pts, uvs))
    for pair, spec in GL.STRIPS.items():
        for ori in GL.ORIS:
            for row in range(spec.get("rows", 4)):
                if match(lambda p, pr=pair, r=row, o=ori: _strip_uv_for_pair(pr, p[0], p[2], cell, r, o)):
                    return (pair, row, ori)
    return None


def flatten_terrain_records(cell_meshes: dict) -> list:
    """Flatten every 'terrain' :class:`~ff9mapkit.world.extract.BlockMesh` in ``cell_meshes`` (``{(bx,by):
    [(part_name, BlockMesh), ...]}`` -- exactly :func:`~ff9mapkit.world.transplant.transplant`'s /
    :func:`~ff9mapkit.world.transplant.transplant_region`'s just-built, pre-write, POST-tweak tri set,
    one absolute-block key per target cell) into one record per triangle: ``block`` (the owning
    world-map block), ``cell`` (the 4u lattice cell), ``tri_idx`` (the LOCAL vertex-index triple into
    that block's own BlockMesh -- these are unindexed 'soup' meshes, so each vertex belongs to
    exactly one tri and is safe to redress independently), ``topo``, ``fam`` (``grassland.TOPO_FAMILY``
    lookup, or ``None`` for a family the STRIPS vocabulary doesn't key off), ``world_pts``, ``uv``.
    Below-:data:`STUB_Y_FLOOR` blanking-stub tris are skipped (see the module docstring)."""
    out = []
    for block, parts in cell_meshes.items():
        (bx, by) = block
        ox, oz = block_world_origin(bx, by)
        for pn, bm in parts:
            if pn.lower() != "terrain":
                continue
            verts, uvs, tans = bm.verts, bm.uvs, bm.tangents
            for tri in bm.tris:
                wpts = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
                if all(p[1] <= STUB_Y_FLOOR for p in wpts):
                    continue
                uv3 = [tuple(uvs[j]) for j in tri]
                topo = decode_id(int(round(tans[tri[0]][0])))["topograph"]
                cx = sum(p[0] for p in wpts) / 3.0
                cz = sum(p[2] for p in wpts) / 3.0
                cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
                out.append(dict(block=(bx, by), tri_idx=list(tri), topo=topo,
                                fam=GL.TOPO_FAMILY.get(topo), world_pts=wpts, uv=uv3, cell=cell))
    return out


def _ring_blocks(region_cells) -> list:
    """The 1-block Moore ring of ``(bx,by)`` BLOCKS around ``region_cells`` (the just-carried
    target rect), clipped to the engine's real 24x20 grid (``mesh.block_in_grid`` -- THE
    GRID-BOUNDS GATE) and EXCLUDING ``region_cells`` themselves (those are ours to read from
    ``cell_meshes``, in-memory and pre-write -- never from disk). Matches
    ``comp1_orphan_redress.ROUND2_RING``'s own Moore-neighbourhood construction, minus its core."""
    region_set = {tuple(c) for c in region_cells}
    ring = {(bx + dx, by + dy) for (bx, by) in region_set
           for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - region_set
    return sorted((bx, by) for (bx, by) in ring if _mesh.block_in_grid(bx, by))


def default_context_provider(region_cells, *, mod_folder: str, disc: int = 1, lod: str = "0_1",
                             game=None) -> dict:
    """THE DEFAULT RING-CONTEXT PROVIDER -- matches ``comp1_orphan_redress._region_blockmeshes``'s
    own ring-read semantics exactly: for every block in the 1-block Moore ring around
    ``region_cells`` (:func:`_ring_blocks`), prefer an already-DEPLOYED mod override (``mod_folder``'s
    own ``Terrain.ff9mesh``) and fall back to real STOCK bytes (:func:`~ff9mapkit.world.extract.read_block`)
    when none is deployed there. A ring block with neither (off the catalogued mesh index -- e.g.
    open ocean, or off the grid) is silently skipped: it only narrows the neighbour-lookup evidence
    available near that block, exactly as the study's own reader does -- never fatal.

    READ-ONLY: this function only ever opens files / decodes bytes to build in-memory
    :class:`~ff9mapkit.world.extract.BlockMesh` objects for the census; it never writes a byte. If
    the game install cannot be resolved at all (:class:`~ff9mapkit.config.ConfigError` -- no FF9
    install found, e.g. a bare CI checkout), this degrades to "no ring" (returns ``{}``) rather than
    raising -- the ring is an ACCURACY improvement to a WARN-by-default gate, never a hard
    requirement to run a carry offline.

    Returns ``{(bx,by): [("Terrain", BlockMesh)], ...}`` -- the same shape
    :func:`flatten_terrain_records` (and ``cell_meshes`` itself) already consume, so a caller's
    ``context_provider`` can return a hand-built dict of the identical shape for a hermetic test."""
    ring = _ring_blocks(region_cells)
    if not ring:
        return {}
    try:
        game_root = _config.find_game_path(game)
    except _config.ConfigError:
        return {}
    out = {}
    for (bx, by) in ring:
        path = game_root / mod_folder / _mesh.override_relpath(disc, bx, by, lod, "Terrain")
        if path.is_file():
            # A DEPLOYED override that exists but cannot decode is a REAL bug in the deploy --
            # raise loudly, exactly like the proven instrument (comp1_orphan_redress's
            # _region_blockmeshes leaves this read unprotected). Never swallow it: a silently
            # skipped corrupt override would weaken the ring evidence AND mask the corruption.
            bm = _mesh.blockmesh_from_ff9mesh(path, disc=disc, x=bx, y=by, lod=lod, part="terrain")
        else:
            try:
                bm = read_block(bx, by, disc=disc, lod=lod, part="terrain", game=game)
            except Exception:                 # noqa: BLE001 -- no STOCK data / a stubbed asset reader
                continue                      # (test doubles included) at this ring block -- narrower
                                              # evidence, not fatal (the codebase's degrade-on-read-
                                              # failure idiom applies to the OPTIONAL stock fallback
                                              # only, matching the instrument's own narrow catch)
        out[(bx, by)] = [("Terrain", bm)]
    return out


def row_lawfulness(cell, pair, row: int, fam_t, cell_fams: dict, *,
                   accept_radius: int = ACCEPT_RADIUS, max_band_radius: int = MAX_BAND_RADIUS):
    """The Round-10 justifying-context rule for ONE ``(cell, pair, row, fam_t)`` hit
    (``comp1_orphan_redress._row_lawfulness``, ported verbatim). ``cell_fams``: ``{cell: {family,
    ...}}`` -- family PRESENCE per cell, from a plain ``TOPO_FAMILY`` lookup (never a UV re-decode:
    a real stock sub-cell-conforming vertex's UV stays pinned to its quadrant corner, which a linear
    fx/fz re-interpolation does not reproduce -- cell-family presence sidesteps that gap entirely).
    Returns ``(lawful: bool | None, detail: dict)`` -- ``None`` = ambiguous (row/family don't fit
    the model at all, needs eyes, never auto-flagged as an orphan)."""
    fams_here = cell_fams.get(cell, set())
    if row in (1, 3):
        lawful = fams_here == set(pair)
        detail = dict(kind="straddle-row", fams_present=sorted(fams_here))
        if not lawful:
            detail["missing_context"] = (f"no same-cell straddle: cell holds families "
                                         f"{sorted(fams_here)}, needs BOTH {sorted(pair)}")
        return lawful, detail
    if row in (0, 2):
        partner = pair[1] if fam_t == pair[0] else pair[0] if fam_t == pair[1] else None
        if partner is None:
            return None, dict(kind="fringe-row", partner_family=None,
                              missing_context=f"ambiguous: tri's own family {fam_t!r} not in pair {pair}")
        radius_needed = None
        for r in range(1, max_band_radius + 1):
            found = any(
                (cell[0] + di, cell[1] + dj) in cell_fams
                and partner in cell_fams[(cell[0] + di, cell[1] + dj)]
                for di in range(-r, r + 1) for dj in range(-r, r + 1)
                if max(abs(di), abs(dj)) == r)
            if found:
                radius_needed = r
                break
        lawful = radius_needed is not None and radius_needed <= accept_radius
        detail = dict(kind="fringe-row", partner_family=partner, radius_needed=radius_needed)
        if not lawful:
            detail["missing_context"] = (
                f"partner family {partner!r} first found at radius {radius_needed} "
                f"(> accept radius {accept_radius})" if radius_needed is not None
                else f"partner family {partner!r} not found within {max_band_radius} cells at all")
        return lawful, detail
    return None, dict(kind=f"row{row}", missing_context="row index outside 0..3")


def topo_consistency_defects(records: list, *, report_blocks=None,
                              min_group: int = FRINGE_MODE_MIN_GROUP,
                              min_share: float = FRINGE_MODE_MIN_SHARE):
    """CLASS B (``comp1_orphan_redress.topo_consistency_defects``, ported): a SECOND, independent
    lawfulness test for FRINGE-row (0/2) STRIPS decals, orthogonal to :func:`row_lawfulness`'s
    context-radius test. Within ``records``, every ``(pair, row)`` fringe group's topo is measured
    LIVE (never hardcoded); if one topo value holds an overwhelming majority (>= ``min_share`` of a
    >= ``min_group`` sample), any tri breaking that majority is a topo/UV mismatch -- independent of
    whether its neighbourhood otherwise reads as lawful. STRADDLE rows (1/3) are out of scope on
    purpose: a genuine straddle legitimately wears two different topos across its two tris, so "the
    group's mode" is not a meaningful single number there.

    ``report_blocks`` (``None`` = every record) restricts which tris are REPORTED -- the group
    STATISTICS are always measured over every record passed in (a larger, more trustworthy sample).

    Returns ``(defects: {cell: [hit, ...]}, group_stats: {(pair, row): {mode_topo, mode_n, total_n,
    counts}})``."""
    report_set = None if report_blocks is None else {tuple(b) for b in report_blocks}
    by_group = collections.defaultdict(list)
    for t in records:
        cls = classify_strip_tri(t["world_pts"], t["uv"], t["cell"])
        if cls is None:
            continue
        pair, row, ori = cls
        if row not in (0, 2):
            continue
        by_group[(pair, row)].append(dict(cell=t["cell"], block=t["block"], tri_idx=t["tri_idx"],
                                          pair=pair, row=row, ori=ori, topo=t["topo"], fam=t["fam"],
                                          uv=[list(u) for u in t["uv"]]))
    defects = collections.defaultdict(list)
    group_stats = {}
    for key, group in by_group.items():
        ct = collections.Counter(r["topo"] for r in group)
        mode_topo, mode_n = ct.most_common(1)[0]
        group_stats[key] = dict(mode_topo=mode_topo, mode_n=mode_n, total_n=len(group), counts=dict(ct))
        if len(group) < min_group or mode_n / len(group) < min_share:
            continue                              # too thin / no clear majority: refuse to judge
        for r in group:
            if r["topo"] != mode_topo and (report_set is None or tuple(r["block"]) in report_set):
                defects[r["cell"]].append(r)
    return dict(defects), group_stats


def orphan_decal_census(records: list, *, report_blocks=None) -> tuple:
    """THE FULL rule set over an already-flattened tri record list (see
    :func:`flatten_terrain_records`): CLASS A (:func:`row_lawfulness`, any row) union CLASS B
    (:func:`topo_consistency_defects`, fringe rows only) -- the same two-class reconciliation
    ``comp1_orphan_redress.round3_census`` proved over the live comp[1] region (7 cells: 6 Class A +
    1 Class B).

    AMBIGUOUS OVERLAP: if Class A and Class B independently claim the SAME CELL,
    ``comp1_orphan_redress.round3_build_and_gate`` hard-refuses (an assert -- "the two fix SHAPES
    are mutually exclusive... an unmodelled 3rd shape, refuse rather than guess"). A gate cannot
    raise blind through a caller's build, so every hit on such a cell is relabelled
    ``klass="AMBIGUOUS"`` here instead (never silently folded into whichever class happened to be
    inserted first) -- it still counts as a defect (``n_orphans``/``warn``/``ok``), but
    :func:`orphan_decal_gate`'s ``redress=True`` path refuses to auto-fix it. A tri flagged by BOTH
    classes AT ONCE is still de-duplicated to one hit, keyed on ``(block, tri_idx)``.

    ``report_blocks`` (``None`` = every record) restricts which tris are candidates for reporting;
    every record still feeds the CONTEXT (``cell_fams``, the Class-B group statistics) regardless --
    callers wanting ``--census3``'s own ring semantics pass a RING-EXTENDED ``records`` (core +
    1-block Moore ring) with ``report_blocks`` naming only the core (:func:`orphan_decal_gate` does
    this automatically).

    Returns ``(defects: {cell: [hit, ...]}, stats: dict)`` -- ``stats`` also carries
    ``n_ambiguous_cells``/``ambiguous_cells``."""
    cell_fams = collections.defaultdict(set)
    for t in records:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])

    report_set = None if report_blocks is None else {tuple(b) for b in report_blocks}
    class_a = collections.defaultdict(list)
    n_strip = 0                               # CORE-scoped only -- the instrument's headline metric
    n_strip_ring = 0                          # ring strips tracked separately, never in the headline
    for t in records:
        cls = classify_strip_tri(t["world_pts"], t["uv"], t["cell"])
        if cls is None:
            continue
        if report_set is not None and tuple(t["block"]) not in report_set:
            n_strip_ring += 1
            continue
        n_strip += 1
        pair, row, ori = cls
        lawful, detail = row_lawfulness(t["cell"], pair, row, t["fam"], cell_fams)
        if lawful is False:
            class_a[t["cell"]].append(dict(cell=t["cell"], block=t["block"], tri_idx=t["tri_idx"],
                                           pair=pair, row=row, ori=ori, topo=t["topo"], fam=t["fam"],
                                           uv=[list(u) for u in t["uv"]], klass="A",
                                           missing_context=detail.get("missing_context")))

    class_b, class_b_stats = topo_consistency_defects(records, report_blocks=report_blocks)
    for hits in class_b.values():
        for h in hits:
            h["klass"] = "B"
            h["missing_context"] = (f"topo {h['topo']} breaks its own {h['pair']} row-{h['row']} "
                                    f"decal group's measured norm")

    # AMBIGUOUS OVERLAP (see docstring): a cell claimed by BOTH classes is an unmodelled shape --
    # never auto-fixed, always surfaced distinctly.
    ambiguous_cells = sorted(set(class_a) & set(class_b))
    ambiguous_set = set(ambiguous_cells)

    defects: dict = {}
    seen_tri = set()
    for cell, hits in list(class_a.items()) + list(class_b.items()):
        for h in hits:
            key = (tuple(h["block"]), tuple(h["tri_idx"]))
            if key in seen_tri:
                continue
            seen_tri.add(key)
            if cell in ambiguous_set:
                h = dict(h)
                h["klass"] = "AMBIGUOUS"
                h["missing_context"] = (
                    f"AMBIGUOUS: cell {cell} is claimed by BOTH Class A (context-radius) and Class "
                    f"B (topo-consistency) -- an unmodelled overlap state "
                    f"(comp1_orphan_redress.round3_build_and_gate hard-refuses on this exact shape); "
                    f"never auto-fixed by --redress-orphans")
            defects.setdefault(cell, []).append(h)

    stats = dict(n_strip_tris=n_strip, n_strip_tris_ring=n_strip_ring,
                 n_class_a=sum(len(v) for v in class_a.values()),
                n_class_b=sum(len(v) for v in class_b.values()), n_defect_cells=len(defects),
                n_ambiguous_cells=len(ambiguous_cells),
                ambiguous_cells=[list(c) for c in ambiguous_cells],
                class_b_group_stats=class_b_stats)
    return defects, stats


def compute_orphan_redress(bm, ox: float, oz: float, cell, tri_idx: list, dst_family: str, *,
                           seed: int = DEFAULT_REDRESS_SEED) -> dict:
    """THE PROVEN FIX-G SHAPE (``comp1_orphan_redress.compute_redress`` /
    ``compute_redress_round2``, unified): re-point ``tri_idx``'s corners on BlockMesh ``bm`` (world
    origin ``(ox, oz)``) to lawful ``grassland.GROUNDS[dst_family]`` mains, via
    ``grassland.assign_mains({cell}, seed=seed)`` -> ``grassland.ground_uv(...)`` -- the SAME
    per-cell call the shipped ``GroundRetile`` "recovered" path already uses. UV always changes;
    topo (``tangent.x``'s topograph field) changes ONLY when the tri's OWN topo is not already
    ``GROUNDS[dst_family]``'s plain-mains topo (event/area/flags preserved bit-for-bit when it
    does -- Round 1's shape); when the topo already matches, only the UV moves (Round 2's shape,
    idall left untouched). Vertex positions, normals and tangent[1:] (y/z/w) are never touched.
    MUTATES ``bm`` in place; returns the applied redress for reporting."""
    cq, co = GL.assign_mains({cell}, seed=seed)
    quad, ori = cq[cell], co[cell]
    dst_topo = GL.GROUNDS[dst_family]["topo"]
    new_uv, new_idall = [], []
    idall_changed = False
    for j in tri_idx:
        wx = bm.verts[j][0] + ox
        wz = bm.verts[j][2] + oz
        uv = list(GL.ground_uv(wx, wz, cell, quad, ori, dst_family))
        old_idall = int(round(bm.tangents[j][0]))
        d = decode_id(old_idall)
        if d["topograph"] == dst_topo:
            nid = old_idall
        else:
            nid = encode_id(d["event"], d["area"], dst_topo, d["flags"])
            idall_changed = True
        bm.uvs[j] = uv
        old_tan = bm.tangents[j]
        bm.tangents[j] = [float(nid)] + list(old_tan[1:])
        new_uv.append(uv)
        new_idall.append(nid)
    return dict(quad=quad, ori=ori, new_uv=new_uv, new_idall=new_idall, idall_changed=idall_changed)


def orphan_decal_gate(cell_meshes: dict, region_cells, *, enforce: bool = False, allow: bool = False,
                      redress: bool = False, seed: int = DEFAULT_REDRESS_SEED,
                      mod_folder: str | None = None, disc: int = 1, lod: str = "0_1", game=None,
                      context_provider=None) -> dict:
    """THE ORPHAN-DECAL GATE -- follows :func:`~ff9mapkit.world.transplant.wang_carry_gate`'s exact
    shape (see the module docstring). ``cell_meshes``: ``{(bx,by): [(part_name, BlockMesh), ...]}``,
    the just-built carried region (transplant()'s single ``{(bx,by): meshes}`` or
    transplant_region()'s per-cell ``deploy_meshes``, keyed by ABSOLUTE target block). ``region_cells``:
    the set of ``(bx,by)`` blocks that are OURS to report (matches ``wang_carry_gate``'s parameter).

    RING CONTEXT (matches ``--census3``'s ``round3_generalized_census`` exactly): before censusing,
    a 1-block Moore ring of REAL bordering terrain around ``region_cells`` is fetched via
    ``context_provider(region_cells)`` (default :func:`default_context_provider` -- deployed mod
    override where one exists, else real stock bytes, READ-ONLY) and its flattened records are
    merged alongside ``cell_meshes``'s own for BOTH the Class-A fringe-row radius search and the
    Class-B topo-consistency group statistics -- only blocks inside ``region_cells`` are ever
    REPORTED as candidate defects (``report_blocks``), the ring is context-only. Pass ``mod_folder``
    (the deploying carry already has one) to enable the real reader; leave it ``None`` (the default)
    to skip ring reads entirely -- exactly the pre-ring behaviour, zero disk access. Pass
    ``context_provider`` directly (any callable ``region_cells -> {(bx,by): [(part_name,
    BlockMesh)], ...}``) to inject a synthetic ring for a hermetic test, bypassing the real reader
    (and ``mod_folder``) entirely.

    In WARN mode (``redress=False``, the default) this is PURELY READ-ONLY -- it never mutates a
    byte of any BlockMesh it inspects (ring reads included), so wiring it into an existing carry
    path changes zero output bytes. With ``redress=True``, every located orphan EXCEPT an
    ``AMBIGUOUS`` one (see the module docstring -- a cell Class A and Class B both claim is an
    unmodelled state, never auto-fixed) is fixed IN MEMORY (mutating the ``cell_meshes``
    BlockMeshes directly, before any write the caller performs) via :func:`compute_orphan_redress`,
    then the census RE-RUNS over the mutated meshes + the SAME (unchanged, read-only) ring records
    (never trust a fix blind) -- ``ok``/``warn``/``n_orphans`` all reflect the POST-redress state,
    so a fully successful auto-fix makes the gate clean even when ``enforce=True`` UNLESS an
    ambiguous cell remains, which keeps it dirty by design."""
    region = sorted({tuple(c) for c in region_cells})
    region_set = set(region)

    if context_provider is None:
        if mod_folder is not None:
            context_provider = functools.partial(default_context_provider, mod_folder=mod_folder,
                                                  disc=disc, lod=lod, game=game)
        else:
            context_provider = lambda _region: {}          # no mod_folder -- pre-ring behaviour: no ring
    ring_meshes = context_provider(region) or {}
    # defensive: a ring block that coincides with the just-carried region is OURS (in-memory,
    # pre-write) -- never let an injected/real ring silently shadow cell_meshes's own content.
    ring_meshes = {tuple(k): v for k, v in ring_meshes.items() if tuple(k) not in region_set}
    ring_records = flatten_terrain_records(ring_meshes)

    records = flatten_terrain_records(cell_meshes) + ring_records
    defects, stats = orphan_decal_census(records, report_blocks=region)

    n_redressed = 0
    if redress and defects:
        bm_by_block = {}
        for blk, parts in cell_meshes.items():
            for pn, bm in parts:
                if pn.lower() == "terrain":
                    bm_by_block[tuple(blk)] = bm
        seen = set()
        for hits in defects.values():
            for h in hits:
                if h.get("klass") == "AMBIGUOUS":
                    continue                      # never auto-fix an unmodelled overlap state
                key = (tuple(h["block"]), tuple(h["tri_idx"]))
                if key in seen:
                    continue
                seen.add(key)
                bm = bm_by_block.get(tuple(h["block"]))
                dst_family = h.get("fam")
                if bm is None or not dst_family or dst_family not in GL.GROUNDS:
                    continue                      # can't redress blind -- stays flagged
                ox, oz = block_world_origin(*h["block"])
                compute_orphan_redress(bm, ox, oz, h["cell"], h["tri_idx"], dst_family, seed=seed)
                n_redressed += 1
        # POST-STATE reclassify (in-memory, pre-write): never trust the fix blind -- re-run the
        # SAME census over the just-mutated meshes + the SAME (never re-read, never mutated) ring.
        records = flatten_terrain_records(cell_meshes) + ring_records
        defects, stats = orphan_decal_census(records, report_blocks=region)

    incoherent = sum(len(v) for v in defects.values())
    cells_sorted = sorted(defects)
    ctx_bits = []
    for cell in cells_sorted[:4]:
        h0 = defects[cell][0]
        ctx_bits.append(f"{cell}[{h0['pair'][0]}|{h0['pair'][1]} row{h0['row']}]: "
                        f"{h0.get('missing_context') or h0['klass']}")
    ok = allow or (not enforce) or not incoherent
    warn = bool(incoherent) and not enforce and not allow
    return {
        "gate": "orphan-decals", "checked": stats["n_strip_tris"], "n_orphans": incoherent,
        "cells": [list(c) for c in cells_sorted], "redress": bool(redress),
        "n_redressed": n_redressed, "detail": "; ".join(ctx_bits) if ctx_bits else 0,
        "enforced": bool(enforce), "warn": warn, "ok": ok,
        "n_ambiguous": stats.get("n_ambiguous_cells", 0),
        "ambiguous_cells": stats.get("ambiguous_cells", []),
        "ring_blocks": [list(b) for b in sorted(ring_meshes)],
    }
