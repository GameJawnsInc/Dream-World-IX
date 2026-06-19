"""import-chain (P1, read-only): walk FF9's walkable-door graph out from a seed field, across zones.

Single-field ``import`` extracts one field's gateway edges but leaves each ``to`` pointing back into the
live game. ``import-chain`` follows those edges: from a seed it walks the connected region of real fields,
classifies every connection (walk-in gateway / scripted teleport / overworld exit -- see
:func:`ff9mapkit.eventscan.scan_all_warps`), bounds the walk (zones, hops, a hard field cap), and renders
the graph for scoping. Emitting ``campaign.toml`` + the per-field forks (with edges retargeted among the
chain's own new ids) is P2; this module is P1: discovery + ``--dry-run``.

The walk is PURE: it takes ``scan_fn(id)`` and ``zone_fn(id)`` callbacks, so it unit-tests on a synthetic
graph with no game install. The CLI wires the real :class:`ff9mapkit.extract.EventBundle`-backed scan.

Grounded in a live byte-survey (2026-06-09): ~41% of real connectivity is scripted (not walk-in), every
warp target is a literal (FF9 never computes a warp id), WorldMap operands are overworld LOCATION ids
(9000-9012) not fields, and only ~2.9% of region exits are story-conditional (stacked same-zone doors)."""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass

WALK_IN = "walk_in"
SCRIPTED = "scripted"
OVERWORLD = "overworld_exit"

DEFAULT_DENYLIST = frozenset({100})     # field 100 (Alexandria) crashes in this setup -- CLAUDE.md §5
DEFAULT_MAX_FIELDS = 25
# Generous: within a --zones scope, zones + max_fields are the real bound; a tight hop cap would sever a
# long linear dungeon (Ice Cavern is 13 screens deep). Lower it for an unscoped --cross-zones sweep.
DEFAULT_MAX_HOPS = 20


def zone_label(folder) -> str:
    """Zone token of an FBG folder: ``'fbg_n05_iccv_map085_ic_ent_0'`` -> ``'iccv'``. None/odd -> ``'?'``."""
    if not folder:
        return "?"
    parts = str(folder).split("_")
    return parts[2] if len(parts) >= 3 else str(folder)


# --------------------------------------------------------------------------- field-id clustering / ranges
# FF9 stores "same place, different story state" as SEPARATE field ids that share the background art -- a
# revisited zone's ids cluster by visit, separated by big id gaps (Alexandria town: 100-117 opening, 1850-1865
# return, 2450-2457 ruined, 3000 ending). These helpers split a zone by those gaps (so a region fork can scope
# to ONE visit instead of the whole 48-screen zone) and parse/format the compact id-range string the catalog
# stores in `members` and import-chain reads from `--ids`.
DEFAULT_CLUSTER_GAP = 120   # sits in the dead band (98, 135) measured from ID_TO_FBG: the largest WITHIN-visit
#                             gap is 98 (evft 152->250, an orphaned cutscene screen) and the smallest BETWEEN-
#                             visit gap is 135 (alxc 1866->2001) -- so 120 keeps each visit whole AND splits all
#                             distinct visits (margins ~22/15 ids; widen/narrow via --gap if fields are added)


def id_clusters(ids, gap: int = DEFAULT_CLUSTER_GAP) -> list:
    """Split a sorted-unique list of field ids into clusters wherever consecutive ids jump by more than
    ``gap`` -- each cluster is one story-state visit of a revisited zone. ``[]`` for no ids. PURE."""
    seq = sorted({int(x) for x in ids})
    if not seq:
        return []
    out, cur = [], [seq[0]]
    for a, b in zip(seq, seq[1:]):
        if b - a > gap:
            out.append(cur)
            cur = [b]
        else:
            cur.append(b)
    out.append(cur)
    return out


def format_id_ranges(ids) -> str:
    """Render a set of ids as a compact, sorted range string: ``[100..117, 150, 200..202]`` ->
    ``'100-117,150,200-202'``. ``''`` for empty. The inverse of :func:`parse_id_ranges`."""
    seq = sorted({int(x) for x in ids})
    if not seq:
        return ""
    spans, start, prev = [], seq[0], seq[0]
    for n in seq[1:]:
        if n == prev + 1:
            prev = n
            continue
        spans.append((start, prev))
        start = prev = n
    spans.append((start, prev))
    return ",".join(f"{a}-{b}" if a != b else f"{a}" for a, b in spans)


def parse_id_ranges(spec) -> list:
    """Parse a compact id-range string (``'100-117,150,200-202'``) -> a sorted-unique ``list[int]``. Accepts
    spaces, an already-list/tuple of ints, or an empty value (-> ``[]``). Raises ``ValueError`` on a malformed
    token or a reversed range. The inverse of :func:`format_id_ranges`."""
    if spec is None or spec == "":
        return []
    if isinstance(spec, (list, tuple, set)):
        return sorted({int(x) for x in spec})
    out: set = set()
    for tok in str(spec).replace(" ", "").split(","):
        if not tok:
            continue
        if "-" in tok.lstrip("-"):                 # a range 'A-B' (lstrip guards a leading '-' that isn't a sep)
            a, _, b = tok.partition("-")
            lo, hi = int(a), int(b)
            if hi < lo:
                raise ValueError(f"reversed id range {tok!r} (low-high)")
            out.update(range(lo, hi + 1))
        else:
            out.add(int(tok))
    return sorted(out)


@dataclass
class GraphResult:
    """Outcome of a walk. ``nodes`` is an insertion-ordered (BFS discovery order) id -> info map; that
    order is also the id-assignment order P2 will use (``campaign_id_base + i``)."""

    nodes: "OrderedDict"     # id -> {zone, found, edges, overworld_exits, encounter, music, hop}
    portals: list            # edges NOT followed (zone boundary / stop-at / denylist / max-hops)
    seams: list              # scripted teleport edges not followed (author by hand)
    unforkable: list         # edges to targets with no FBG/background (shop/menu, variant, cutscene-only)
    seeds: list
    allowed_zones: object    # set | None (None = any zone)
    truncated: bool          # hit max_fields with more queued
    remaining: int           # fields still queued when truncated
    bounds: dict


def walk(seed_ids, scan_fn, zone_fn, *, forkable_fn=None, max_hops=DEFAULT_MAX_HOPS, zones=None,
         stop_at=None, max_fields=DEFAULT_MAX_FIELDS, follow_scripted=False, denylist=DEFAULT_DENYLIST,
         stop_at_zone_boundary=True, restrict_ids=None) -> GraphResult:
    """Bounded BFS over the door graph.

    ``scan_fn(field_id)`` -> ``{found: bool, edges: [{to, kind, entrance?, zone?, story_conditional?,
    trigger?}], overworld_exits: [...], encounter, music}`` (``found=False`` for an id with no scannable
    ``.eb`` -- world/special field -- terminating that branch). ``zone_fn(field_id)`` -> zone label.
    ``forkable_fn(field_id)`` -> True if the target is a real WALKABLE field (has a background in the
    FBG table); False for a shop/menu / variant / cutscene-only id that has no room to fork. A non-forkable
    target is recorded in ``unforkable`` and not followed -- BEFORE the zone test, so a shop door reads as
    'menu/no-bg', not a bogus zone-boundary portal. Defaults to always-forkable (pure-graph unit tests).

    Scope: if ``zones`` is given, only targets in those zones are followed; otherwise, with
    ``stop_at_zone_boundary`` (default) the walk stays within the seed's own zone(s). ``restrict_ids`` (an
    EXPLICIT id set, e.g. import-chain ``--ids``) bounds the walk to exactly those fields regardless of zone --
    an edge to a field OUTSIDE the set is recorded as a portal, never followed (so one story-state cluster
    doesn't leak its same-zone sibling visits). Either way an edge rejected SOLELY for being out of scope is
    recorded as a PORTAL (so you see where the region connects). Scripted edges are recorded as SEAMS and not
    followed unless ``follow_scripted``. ``max_fields`` is a hard cap with a loud ``truncated`` flag rather
    than silently forking the whole game."""
    forkable_fn = forkable_fn or (lambda fid: True)
    seeds = [int(s) for s in (seed_ids if isinstance(seed_ids, (list, tuple, set)) else [seed_ids])]
    stop_at = {int(x) for x in (stop_at or ())}
    deny = {int(x) for x in (denylist or ())}
    restrict = {int(x) for x in restrict_ids} if restrict_ids is not None else None
    if zones is not None:
        allowed = set(zones)
    elif stop_at_zone_boundary:
        allowed = {zone_fn(s) for s in seeds}
    else:
        allowed = None

    nodes: "OrderedDict" = OrderedDict()
    portals: list = []
    seams: list = []
    unforkable: list = []
    visited: set = set()
    q: deque = deque()
    for s in seeds:
        if s not in visited:
            visited.add(s)
            q.append((s, 0))

    truncated = False
    while q:
        fid, hop = q.popleft()
        if len(nodes) >= max_fields:
            truncated = True
            break
        node = scan_fn(fid)
        info = {
            "zone": zone_fn(fid), "found": bool(node.get("found")),
            "edges": node.get("edges", []), "overworld_exits": node.get("overworld_exits", []),
            "encounter": node.get("encounter"), "music": node.get("music"), "hop": hop,
        }
        nodes[fid] = info
        if not info["found"]:
            continue
        walkin_targets = {int(e["to"]) for e in info["edges"] if e["kind"] == WALK_IN}
        for e in info["edges"]:
            to = int(e["to"])
            kind = e["kind"]
            if kind == OVERWORLD:
                continue                                   # never a graph edge (it's an overworld loc id)
            tzone = zone_fn(to)
            if kind == SCRIPTED and not follow_scripted:
                if to not in walkin_targets:               # don't double-report a connection that's
                    seams.append({"from": fid, "to": to, "entrance": e.get("entrance"),  # also a real door
                                  "trigger": e.get("trigger"), "to_zone": tzone})
                continue
            if to in visited:
                continue
            if not forkable_fn(to):                        # shop/menu / variant / no-background id:
                unforkable.append({"from": fid, "to": to})  # can't fork a room -- classify before zone test
                continue
            reason = None
            if restrict is not None and to not in restrict:
                reason = "not-in-set"                       # --ids: outside the explicit cluster -> a portal
            elif to in stop_at:
                reason = "stop-at"
            elif allowed is not None and tzone not in allowed:
                reason = f"zone:{tzone}"
            elif to in deny:
                reason = "denylist"
            elif hop + 1 > max_hops:
                reason = "max-hops"
            if reason:
                portals.append({"from": fid, "to": to, "kind": kind, "to_zone": tzone, "reason": reason})
                continue
            visited.add(to)
            q.append((to, hop + 1))

    # when truncated we broke right after popping an unprocessed field, so it counts as unexplored too
    return GraphResult(
        nodes=nodes, portals=portals, seams=seams, unforkable=unforkable, seeds=seeds,
        allowed_zones=allowed, truncated=truncated, remaining=(len(q) + 1 if truncated else 0),
        bounds={"max_hops": max_hops, "max_fields": max_fields, "zones": list(zones) if zones else None,
                "follow_scripted": follow_scripted, "stop_at_zone_boundary": stop_at_zone_boundary,
                "restrict_ids": sorted(restrict) if restrict is not None else None},
    )


def zone_coverage(result: GraphResult, zone_members_fn) -> dict:
    """How much of each touched zone the walk actually forked: ``{zone: (reached, total, [unreached_ids])}``.
    ``zone_members_fn(zone)`` -> the set of ALL forkable field ids in that zone (the static FBG table). A low
    ratio flags an ISOLATED seed -- e.g. Evil Forest seeded at 152 forks 1 of 13 (the rest aren't door-reachable
    from that screen). PURE: the membership comes from a callback so :mod:`chain` stays game-free. Only zones the
    walk forked at least one field in are reported (the seed's own zone(s) + any followed neighbour)."""
    forked_by_zone: dict = {}
    for fid, info in result.nodes.items():
        if info.get("found"):
            forked_by_zone.setdefault(info["zone"], set()).add(int(fid))
    out: dict = {}
    for zone, forked in forked_by_zone.items():
        total = {int(x) for x in (zone_members_fn(zone) or ())}
        unreached = sorted(total - forked)
        out[zone] = (len(forked & total) if total else len(forked), len(total), unreached)
    return out


def render_coverage(coverage: dict) -> list:
    """Lines flagging under-forked zones (reached < total) -- the 'isolated seed' hint. ``[]`` if every touched
    zone is fully covered (e.g. a --whole-zone fork)."""
    lines: list = []
    for zone, (reached, total, unreached) in sorted(coverage.items()):
        if total and reached < total:
            shown = ", ".join(map(str, unreached[:12])) + (" ..." if len(unreached) > 12 else "")
            lines.append(f"  zone {zone}: forked {reached} of {total} forkable fields -- {len(unreached)} "
                         f"NOT door-reachable from the seed ({shown}). Try --whole-zone (or a connected seed).")
    return lines


def _walkin_summary(info):
    """('->' destinations with x{n} stacking, story_conditional?) for a node's walk-in edges."""
    counts: "OrderedDict" = OrderedDict()
    cond = False
    for e in info["edges"]:
        if e["kind"] != WALK_IN:
            continue
        counts[e["to"]] = counts.get(e["to"], 0) + 1
        cond = cond or bool(e.get("story_conditional"))
    parts = [f"{to}(x{n})" if n > 1 else str(to) for to, n in counts.items()]
    return parts, cond


def _dedup(rows, keys):
    seen, out = set(), []
    for r in rows:
        k = tuple(r.get(x) for x in keys)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def render(result: GraphResult, label_fn=None, coverage=None) -> str:
    """A human-readable scoping report for ``--dry-run``: per-zone node lists, inter-zone portals,
    scripted seams, overworld exits, and a blast-radius line. ``label_fn(id)`` -> a display name. ``coverage``
    (from :func:`zone_coverage`) adds an 'isolated seed' hint when a touched zone is under-forked."""
    label_fn = label_fn or (lambda i: "")
    b = result.bounds
    zstr = ",".join(b["zones"]) if b["zones"] else ("seed-zone" if b["stop_at_zone_boundary"] else "any")
    out = [f"import-chain from {', '.join(map(str, result.seeds))}   zones={zstr}  "
           f"max-hops={b['max_hops']}  max-fields={b['max_fields']}  follow-scripted={b['follow_scripted']}",
           ""]

    by_zone: "OrderedDict" = OrderedDict()
    for fid, info in result.nodes.items():
        by_zone.setdefault(info["zone"], []).append((fid, info))
    for z, items in by_zone.items():
        out.append(f"ZONE {z} - {len(items)} field(s)")
        for fid, info in items:
            lbl = label_fn(fid) or ""
            if not info["found"]:
                out.append(f"  {fid:<5} {lbl}  [no script / world field]")
                continue
            parts, cond = _walkin_summary(info)
            arrow = ("-> " + ", ".join(parts)) if parts else "(no walk-in exits)"
            tags = []
            if info.get("encounter"):
                tags.append(f"enc:{info['encounter']['scenes'][0]}")
            if info.get("music") is not None:
                tags.append(f"music:{info['music']}")
            if info.get("overworld_exits"):
                tags.append(f"wm:{len(info['overworld_exits'])}")
            if cond:
                tags.append("STORY-COND")
            out.append(f"  {fid:<5} {lbl:<30} {arrow}" + (("   " + " ".join(tags)) if tags else ""))
        out.append("")

    portals = _dedup(result.portals, ("from", "to", "reason"))
    if portals:
        out.append("PORTALS (edges out of scope -- where this region connects onward):")
        for p in portals:
            out.append(f"  {p['from']} -> {p['to']:<5} [{p.get('to_zone','?')}]  ({p['kind']}; {p['reason']})")
        out.append("")

    seams = _dedup(result.seams, ("from", "to"))
    if seams:
        out.append("SCRIPTED SEAMS (teleports -- not followed; author by hand):")
        for s in seams:
            ent = s.get("entrance")
            ent_str = str(ent) if isinstance(ent, int) and 0 <= ent <= 999 else "?"  # best-effort in cutscenes
            out.append(f"  {s['from']} -> {s['to']:<5} [{s.get('to_zone','?')}]  "
                       f"trigger:{s['trigger']} entrance:{ent_str}")
        out.append("")

    unfork = _dedup(result.unforkable, ("to",))
    if unfork:
        out.append("MENU / NON-FIELD TARGETS (no background in the FBG table -- shops/menus, variants, "
                   "cutscene-only; not forkable as rooms):")
        for u in unfork:
            out.append(f"  {u['from']} -> {u['to']:<5} {label_fn(u['to']) or ''}")
        out.append("")

    wm = [fid for fid, info in result.nodes.items() if info.get("overworld_exits")]
    if wm:
        out.append("OVERWORLD EXITS (screens that leave to the world map): " + ", ".join(map(str, wm)))
        out.append("")

    cov_lines = render_coverage(coverage) if coverage else []
    if cov_lines:
        out.append("UNDER-FORKED ZONES (fields in the zone the seed can't door-reach -- the bytes are there):")
        out.extend(cov_lines)
        out.append("")

    nwalk = sum(1 for info in result.nodes.values() for e in info["edges"] if e["kind"] == WALK_IN)
    status = (f"TRUNCATED at max-fields={b['max_fields']} ({result.remaining}+ more queued -- "
              f"raise --max-fields or narrow --zones)") if result.truncated else "complete"
    out.append(f"BLAST RADIUS: {len(result.nodes)} fields, {len(by_zone)} zone(s), {nwalk} walk-in edges, "
               f"{len(seams)} scripted seams, {len(unfork)} menu/non-field, {len(portals)} portals.  [{status}]")
    return "\n".join(out)
