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
(:func:`~ff9mapkit.world.transplant.wang_carry_gate`, ``_mod_overwrite_gate``) reaches them either;
for CLASS C below, the single-family mints pick their ground family ONCE, structurally immune to a
per-tri selector slip, while the junction generator -- the class's one proving site -- reaches this
gate through ``transplant_region`` and its own Stage-12 kit-orphangate advisory).
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

THE MAINS-RECT ORPHAN (CLASS C -- the batch-1 grow-9013 forensics,
``studies/path-d-new-world/grow/batch1-junction/TRIANGLE.md``): a tri whose uv bbox sits inside ONE
ground family's MAINS rect (``grassland.FAM_REGION["main"]`` translated by ``GROUNDS[family]``'s
delta -- :func:`~ff9mapkit.world.grassland.ground_main_region`) while its own IDALL topograph
belongs to a DIFFERENT family (``grassland.TOPO_FAMILY``). The proving defect: tri 521 of
Block[2][17] on the Path-D landmass -- a grass-topo wedge wearing a byte-LAWFUL desert mains
evaluation (right cell, right quadrant, right rotation, wrong GROUND FAMILY: a one-tri
family-selector slip in the junction generator, reproducing across tile seeds) -- invisible to the
STRIPS-only census above, which never looks at a plain-mains uv at all. The census judges only tris
whose topo family is KNOWN (an unfamilied topo -- walls, murals -- can never be said to "belong to
a different family") and skips the degenerate sliver that fits more than one family rect at
tolerance.

⚠ A raw family mismatch is NOT the defect. Productizing the forensics' one-liner verbatim
("family-A rect on family-B topo, landmass-wide, one hit") re-censused the SAME ratified landmass
at 151 hits, because the tile language wears cross-family mains ON PURPOSE in two grammars the
one-tri run never had to adjudicate: the ~100-tri dunes sand-patch dressing on grass topo (the
meadow-patch grammar with a catalogued ``cls="interior"`` tile set) and stock's scrub
(``cls="transition"``) texture-substitution idiom. The shipped predicate therefore carries THE
SPARING LAWS (island-class worn rects only; THE ISOLATED-STRAY LAW -- size-1 same-worn-family
visual component, the forensics' own discriminant; THE MIXED-CELL PAIR LAW), byte-validated on the
live vs pre-fix trees: {} vs exactly the filed tri. Detail: :func:`mains_orphan_defects`.

CLASS C's ``redress=True`` shape is THE TRANSLATION LAW in reverse (the applied fix,
``fix_triangle.py`` beside the forensics -- :func:`compute_mains_translate`):
``uv - GROUNDS[worn].delta + GROUNDS[own].delta``, recovering exactly the tile the generator would
have emitted for the tri's own family; UV ONLY, the whole tangent/IDALL is NEVER touched (the
incident's event arming survived precisely because of this). REFUSED -- the tri stays flagged --
unless the worn uv is a genuine per-vert mains evaluation of the worn family (THE CUT-VERT LAW's
witness, :func:`mains_evaluation_witness` -- a smear translated is still a smear) AND the
translated uv stays inside the destination rect.
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

#: CLASS C (mains-rect orphan): uv-bbox containment slack against a family's mains rect --
#: ``fix_triangle.py``'s own src-rect precondition bound. Real stock bytes are 5dp-rounded and a
#: lawful evaluation bleeds only INWARD (never outside the 2x2), so this covers float noise without
#: reaching a neighbouring family's rect: the closest rect pair (scrub|dunes) still leaves only a
#: <0.0012-wide degenerate sliver that could fit BOTH at this tol, and a multi-rect fit is skipped,
#: never judged (:func:`mains_rect_family`).
MAINS_RECT_TOL = 4e-3
#: CLASS C translate-redress: the per-corner tolerance for THE CUT-VERT LAW's witness
#: (``fix_triangle.py``'s own ``realises`` bound) -- and for the post-translate destination-rect
#: containment (the witness already grants +-3e-4 of float noise on the SOURCE side, so demanding
#: tighter containment on the translated result would refuse legitimate fixes; 3e-4 uv = ~0.3 texel
#: of the 1024 atlas, inside the measured 1-2px bleed gutter).
MAINS_WITNESS_TOL = 3e-4

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


def mains_rect_family(uvs, *, eps: float = MAINS_RECT_TOL):
    """Which ground family's MAINS rect (:data:`~ff9mapkit.world.grassland.FAM_REGION`'s ``"main"``
    translated by ``GROUNDS[family]``'s delta -- :func:`~ff9mapkit.world.grassland.ground_main_region`)
    contains this tri's WHOLE uv bbox? Returns the single matching family name, or ``None`` when no
    catalogued rect contains it (a STRIPS decal, the meadow set, a wall band, a mural, the
    uncatalogued desert SECONDARY rect -- all legitimately non-mains vocabularies) or when more than
    one does (a degenerate sliver squeezed into the inter-rect gutter -- undecidable, never judged;
    see :data:`MAINS_RECT_TOL`)."""
    lo_u = min(u for u, _ in uvs)
    hi_u = max(u for u, _ in uvs)
    lo_v = min(v for _, v in uvs)
    hi_v = max(v for _, v in uvs)
    hits = [fam for fam in GL.GROUNDS
            for r in (GL.ground_main_region(fam),)
            if r[0] - eps <= lo_u and hi_u <= r[2] + eps
            and r[1] - eps <= lo_v and hi_v <= r[3] + eps]
    return hits[0] if len(hits) == 1 else None


def mains_orphan_defects(records: list, *, report_blocks=None) -> tuple:
    """CLASS C -- THE MAINS-RECT ORPHAN census (see the module docstring: the batch-1 grow-9013
    family-selector slip, ``studies/path-d-new-world/grow/batch1-junction/TRIANGLE.md``): a tri
    wearing family A's mains rect (:func:`mains_rect_family`) while its own topo family
    (``record["fam"]``, the ``TOPO_FAMILY`` lookup) is a DIFFERENT known family. A tri whose topo
    family is unknown (``fam is None`` -- walls, murals, families outside ``TOPO_FAMILY``) is
    counted but never flagged: it cannot be said to "belong to a different family".

    A raw family mismatch is NOT the defect -- re-censusing the ratified batch-1 landmass found 150
    playtest-approved mismatch tris beside the one filed stray, all deliberate cross-family wear.
    THE SPARING LAWS (each byte-validated on the live vs pre-fix trees, which census {} vs exactly
    the filed tri 521 under all three):

    * **island-worn only**: the family-selector composes ``cls="island"`` ground fills, so only an
      island-class worn rect can indict a slip. A non-island rect on foreign topo is DRESSING/SEAM
      grammar, measured live: the ~100-tri dunes (``cls="interior"``) sand-patch dressing on
      grass topo -- the meadow-patch grammar with a catalogued tile set -- and stock's scrub
      (``cls="transition"``) texture-substitution idiom.
    * **THE ISOLATED-STRAY LAW**: the tri's same-worn-family VISUAL component (edge-connected via
      position-welded edges, ring context included) must have size 1 -- the forensics' own
      discriminant ("the ONLY size-1 desert-visual component on the entire landmass"). A multi-tri
      same-family cluster is a deliberate arrangement (a patch, a whole-cell tile); a selector slip
      is per-tri. Known recall bound: a hypothetical whole-cell slip reads as a patch and is spared
      -- refuse-to-guess beats flagging every ratified patch.
    * **THE MIXED-CELL PAIR LAW** (``fix_triangle.py``'s own runtime gate, coastmorph.py:826): a
      same-cell tri sharing the uv bbox is the lawful diagonal-pair partner, not a stray -- spared
      even when the pair's verts are not position-welded (the edge-component test then misses it).

    Ring records feed the component/pair CONTEXT but are never judged or reported (a ring defect is
    deployed/stock content -- not ours). Returns ``(defects: {cell: [hit, ...]}, stats:
    dict(n_mains_tris, n_mains_tris_ring, mains_spared))`` -- ``n_mains_tris`` counts CORE tris
    wearing ANY catalogued mains rect (the census denominator, matching ``n_strip_tris``'s own
    core-only headline convention); ``mains_spared`` tallies core mismatch tris each law excused
    (the re-adjudication trail: a spared count is DATA, not a verdict)."""
    report_set = None if report_blocks is None else {tuple(b) for b in report_blocks}
    island = {f for f, g in GL.GROUNDS.items() if g["cls"] == "island"}

    worn = []                                     # (record index, worn family) for rect-wearing tris
    n_mains = n_mains_ring = 0
    for ti, t in enumerate(records):
        uv_fam = mains_rect_family(t["uv"])
        if uv_fam is None:
            continue
        worn.append((ti, uv_fam))
        if report_set is not None and tuple(t["block"]) not in report_set:
            n_mains_ring += 1
        else:
            n_mains += 1

    # THE ISOLATED-STRAY LAW's components: union-find over same-worn-family tris sharing a
    # position-welded edge (3dp world coords -- the codebase's weld precision, smooth_normals).
    def _pk(p):
        return (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    parent = {ti: ti for ti, _f in worn}

    def _find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    edge_owner = collections.defaultdict(list)
    for ti, fam in worn:
        pts = [_pk(p) for p in records[ti]["world_pts"]]
        for a in range(3):
            edge_owner[(fam, tuple(sorted((pts[a], pts[(a + 1) % 3]))))].append(ti)
    for owners in edge_owner.values():
        for o in owners[1:]:
            ra, rb = _find(owners[0]), _find(o)
            if ra != rb:
                parent[rb] = ra
    comp_size = collections.Counter(_find(ti) for ti, _f in worn)

    def _bbox(uvs):
        return (min(u for u, _ in uvs), min(v for _, v in uvs),
                max(u for u, _ in uvs), max(v for _, v in uvs))
    by_cell = collections.defaultdict(list)
    for ti, t in enumerate(records):
        by_cell[t["cell"]].append(ti)

    defects = collections.defaultdict(list)
    spared = dict(non_island_worn=0, in_a_patch=0, mixed_cell_pair=0)
    for ti, uv_fam in worn:
        t = records[ti]
        if report_set is not None and tuple(t["block"]) not in report_set:
            continue                              # ring: context only, never judged
        if t["fam"] is None or t["fam"] == uv_fam:
            continue
        if uv_fam not in island:
            spared["non_island_worn"] += 1
            continue
        if comp_size[_find(ti)] != 1:
            spared["in_a_patch"] += 1
            continue
        bb = _bbox(t["uv"])
        if any(o != ti and all(abs(c - d) < 6e-3 for c, d in zip(_bbox(records[o]["uv"]), bb))
               for o in by_cell[t["cell"]]):
            spared["mixed_cell_pair"] += 1
            continue
        defects[t["cell"]].append(dict(
            cell=t["cell"], block=t["block"], tri_idx=t["tri_idx"], topo=t["topo"], fam=t["fam"],
            uv_family=uv_fam, uv=[list(u) for u in t["uv"]], klass="C",
            missing_context=(f"mains-rect orphan: an ISOLATED stray wearing {uv_fam!r}'s mains "
                            f"rect while its own topograph {t['topo']} belongs to family "
                            f"{t['fam']!r} (the family-selector slip class)")))
    return dict(defects), dict(n_mains_tris=n_mains, n_mains_tris_ring=n_mains_ring,
                               mains_spared=spared)


def orphan_decal_census(records: list, *, report_blocks=None) -> tuple:
    """THE FULL rule set over an already-flattened tri record list (see
    :func:`flatten_terrain_records`): CLASS A (:func:`row_lawfulness`, any row) union CLASS B
    (:func:`topo_consistency_defects`, fringe rows only) -- the same two-class reconciliation
    ``comp1_orphan_redress.round3_census`` proved over the live comp[1] region (7 cells: 6 Class A +
    1 Class B) -- union CLASS C (:func:`mains_orphan_defects`, the mains-rect orphan: the batch-1
    grow-9013 family-selector slip the STRIPS-only classes structurally cannot see). Class C is
    tri-disjoint from A/B by construction (every family's mains rect is disjoint from every
    translated STRIPS column, so no tri classifies as both), and it does NOT participate in the
    AMBIGUOUS overlap verdict below -- that verdict models the A/B fix-shape conflict on one decal
    group; a Class-C hit sharing a CELL with an A/B hit is a different tri with an independent fix.

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

    class_c, mains_stats = mains_orphan_defects(records, report_blocks=report_blocks)

    # AMBIGUOUS OVERLAP (see docstring): a cell claimed by BOTH the A and B classes is an unmodelled
    # shape -- never auto-fixed, always surfaced distinctly. Class C stays OUT of this verdict: its
    # hits are tri-disjoint from A/B and its fix shape conflicts with neither.
    ambiguous_cells = sorted(set(class_a) & set(class_b))
    ambiguous_set = set(ambiguous_cells)

    defects: dict = {}
    seen_tri = set()
    for cell, hits in list(class_a.items()) + list(class_b.items()) + list(class_c.items()):
        for h in hits:
            key = (tuple(h["block"]), tuple(h["tri_idx"]))
            if key in seen_tri:
                continue
            seen_tri.add(key)
            if cell in ambiguous_set and h["klass"] in ("A", "B"):
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
                n_class_b=sum(len(v) for v in class_b.values()),
                n_class_c=sum(len(v) for v in class_c.values()), n_defect_cells=len(defects),
                n_ambiguous_cells=len(ambiguous_cells),
                ambiguous_cells=[list(c) for c in ambiguous_cells],
                class_b_group_stats=class_b_stats, **mains_stats)
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


def mains_evaluation_witness(xz_pts, uvs, family: str, *, eps: float = MAINS_WITNESS_TOL) -> list:
    """Every ``(cell, quad, ori)`` whose :func:`~ff9mapkit.world.grassland.ground_uv` under
    ``family`` reproduces these uvs at these world ``(x, z)`` points -- a genuine per-vert linear
    evaluation has >=1 hit; a corner-snap smear or a constant fill has none. THE CUT-VERT LAW's own
    witness (``fix_triangle.py``'s ``realises``, ported verbatim: the tile map is EVALUATED AT THE
    VERT, never corner-snapped, so only a real evaluation reproduces bit-for-bit)."""
    out = []
    ci = range(int(min(p[0] for p in xz_pts) // 4) - 1, int(max(p[0] for p in xz_pts) // 4) + 2)
    cj = range(int(min(p[1] for p in xz_pts) // 4) - 1, int(max(p[1] for p in xz_pts) // 4) + 2)
    for i in ci:
        for j in cj:
            for quad in ((0, 0), (0, 1), (1, 0), (1, 1)):
                for ori in GL.ORIS:
                    if all(abs(GL.ground_uv(p[0], p[1], (i, j), quad, ori, family)[k] - u[k]) < eps
                           for p, u in zip(xz_pts, uvs) for k in (0, 1)):
                        out.append(((i, j), quad, ori))
    return out


def compute_mains_translate(bm, ox: float, oz: float, tri_idx: list, src_family: str,
                            dst_family: str):
    """CLASS C's redress -- THE TRANSLATION LAW in reverse (the applied batch-1 fix,
    ``fix_triangle.py`` mode "translate"): ``uv_new = uv_old - GROUNDS[src].delta +
    GROUNDS[dst].delta``, recovering EXACTLY the ``dst_family`` tile the generator would have
    emitted had the family selector been right -- same cell, same quadrant, same rotation, same
    per-vert fractional positions; nothing re-rolled (contrast :func:`compute_orphan_redress`,
    whose ``assign_mains`` re-roll is seed-keyed and unrelated to the generator's own choice).
    UV ONLY: geometry, normals and the WHOLE tangent (IDALL event/area/topo/flags) are never
    touched -- the incident's event arming survived precisely because of this.

    REFUSES (returns ``None``, mutating nothing -- the tri stays flagged) unless BOTH hold:
    the worn uv is a genuine per-vert ``src_family`` mains evaluation
    (:func:`mains_evaluation_witness` -- a smear translated is still a smear, an unmodelled state
    never auto-fixed blind), and the translated uv stays inside the destination rect at
    :data:`MAINS_WITNESS_TOL` (outside the 2x2 lies the transparent gutter that renders WHITE).
    MUTATES ``bm`` in place on success; returns the applied translation for reporting."""
    xz = [(bm.verts[j][0] + ox, bm.verts[j][2] + oz) for j in tri_idx]
    old_uv = [list(bm.uvs[j]) for j in tri_idx]
    witness = mains_evaluation_witness(xz, old_uv, src_family)
    if not witness:
        return None
    gs, gd = GL.GROUNDS[src_family], GL.GROUNDS[dst_family]
    du = gd["mains_du"] - gs["mains_du"]
    dv = gd["mains_dv"] - gs["mains_dv"]
    new_uv = [[u + du, v + dv] for u, v in old_uv]
    lo_u, lo_v, hi_u, hi_v = GL.ground_main_region(dst_family)
    if not all(lo_u - MAINS_WITNESS_TOL <= u <= hi_u + MAINS_WITNESS_TOL
               and lo_v - MAINS_WITNESS_TOL <= v <= hi_v + MAINS_WITNESS_TOL
               for (u, v) in new_uv):
        return None
    for j, uv in zip(tri_idx, new_uv):
        bm.uvs[j] = uv
    return dict(du=du, dv=dv, new_uv=new_uv, witness=witness[0])


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
    BlockMeshes directly, before any write the caller performs) -- Class A/B via
    :func:`compute_orphan_redress` (the FIX-G shape), Class C (the mains-rect orphan) via
    :func:`compute_mains_translate` (THE TRANSLATION LAW in reverse, uv-only, IDALL untouched;
    it REFUSES a uv that is not a genuine worn-family evaluation, and a refused hit stays flagged) --
    then the census RE-RUNS over the mutated meshes + the SAME (unchanged, read-only) ring records
    (never trust a fix blind) -- ``ok``/``warn``/``n_orphans`` all reflect the POST-redress state,
    so a fully successful auto-fix makes the gate clean even when ``enforce=True`` UNLESS an
    ambiguous cell (or a refused Class-C hit) remains, which keeps it dirty by design."""
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
                if h.get("klass") == "C":
                    src_family = h.get("uv_family")
                    if not src_family or src_family not in GL.GROUNDS:
                        continue                  # can't translate blind -- stays flagged
                    if compute_mains_translate(bm, ox, oz, h["tri_idx"], src_family,
                                               dst_family) is None:
                        continue                  # refused: worn uv is no lawful evaluation (a
                                                  # smear) or the translation escapes the rect --
                                                  # an unmodelled state stays flagged, never guessed
                    n_redressed += 1
                    continue
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
        if "pair" in h0:                          # a STRIPS-vocabulary hit (Class A/B/AMBIGUOUS)
            label = f"{h0['pair'][0]}|{h0['pair'][1]} row{h0['row']}"
        else:                                     # a Class-C mains-rect orphan carries no pair/row
            label = f"{h0['uv_family']} mains on {h0['fam']} topo"
        ctx_bits.append(f"{cell}[{label}]: {h0.get('missing_context') or h0['klass']}")
    ok = allow or (not enforce) or not incoherent
    warn = bool(incoherent) and not enforce and not allow
    return {
        "gate": "orphan-decals", "checked": stats["n_strip_tris"],
        "checked_mains": stats.get("n_mains_tris", 0), "n_orphans": incoherent,
        "cells": [list(c) for c in cells_sorted], "redress": bool(redress),
        "n_redressed": n_redressed, "detail": "; ".join(ctx_bits) if ctx_bits else 0,
        "enforced": bool(enforce), "warn": warn, "ok": ok,
        "n_ambiguous": stats.get("n_ambiguous_cells", 0),
        "ambiguous_cells": stats.get("ambiguous_cells", []),
        "ring_blocks": [list(b) for b in sorted(ring_meshes)],
    }
