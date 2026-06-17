"""FF9 reference-arc scaffold -- the north-star planning + fork-and-test harness.

A "reference arc" lays out a span of FF9's REAL story as a chain of forkable arcs: each arc is one campaign
you produce with ``import-chain <seed> --verbatim``, and the arcs chain together as a multi-campaign JOURNEY
(:mod:`.journey`). This module reads the curated arc->seed table (``data/reference_arcs.toml`` -- the disc-1
spine, drafted from the field manifest + the in-game-proven import-chain seeds; EDIT to taste) and renders:

  * a ``journeys.toml`` laying the arcs out as a multi-campaign journey (campaigns / entry / links / seed), and
  * a fork PLAYBOOK -- one ``import-chain`` command per arc, with a disjoint id band + a unique FBG/EVT
    name-prefix each -- so you fork each arc, fill the entry/links from the forked member names, deploy the
    journey, and fidelity-test the seams incrementally toward "fork a real field -> does it play identically?".

It is NOT a one-click rebuild of FF9 (the world map is unmoddable + the narrative layer is the weak axis --
docs/FORK_FIDELITY.md): it's a PLAN you execute arc-by-arc. Pure + tk-free (mirrors :mod:`.journey` /
:mod:`.hub`) -- unit-testable with no game install.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import flags as _flags

_DATA = Path(__file__).resolve().parent / "data" / "reference_arcs.toml"

# Each arc forks into its own disjoint id band so the campaigns never collide in the GLOBAL EventDB namespace
# (the sec 8 id-disjointness guarantee the journey assembler lints). A --whole-zone fork can be large -- the
# biggest FF9 zone is Lindblum (ldbm = 124 forkable fields once shared-FBG-folder fields are counted) -- so the
# band must clear that; 200 ids/arc covers every zone with margin. 12 arcs x 200 = 6000..8400, inside the
# shipped-custom range (4000-9899, CLAUDE.md sec 3).
DEFAULT_ID_BASE = 6000
ARC_ID_SPAN = 200

# The journey assembler lays every campaign's GLOB flag window end-to-end inside ONE safe band (8512..16320 =
# 7808 bits). At import-chain's defaults (25 members x 64 flags/field) a 12-arc chain needs 19200 bits and
# OVERFLOWS -> the deploy lint hard-errors. So the fork playbook emits a SMALLER `--flags-per-field` sized so
# all arcs fit; arcs keep their full member count (the lever is the per-field reservation, not --max-fields).
SAFE_FLAG_BUDGET = _flags.CHOICE_SCRATCH_FLOOR - _flags.FIRST_SAFE_FLAG     # bits the journey band has for campaigns
# A --whole-zone fork can be bigger than the 25-field default cap (Alexandria's zone = 38 screens across discs);
# size the per-arc flag budget for that so the chain still fits the safe band end-to-end (the deploy lint is the
# real backstop). Stays well under ARC_ID_SPAN (100) -- no FF9 zone has that many forkable fields.
MAX_FIELDS_PER_ARC = 40

# Default hub backdrop = MOGNET CENTRAL (real field 3100, FBG fbg_n56_mgnt_map810_mn_mog_0): FF9's Moogle
# journey nexus -- the thematic home for a journey selector (it's the room the project's World Hub borrows),
# and supplying the real `borrow_field` lets `deploy_journey --apply` auto-extract the hub camera. Override
# `borrow_bg`/`area`/`borrow_field` to theme the hub on any other real room (`ff9mapkit list-fields`).
HUB_BORROW_BG = "MGNT_MAP810_MN_MOG_0"
HUB_BORROW_AREA = 56
HUB_BORROW_FIELD = 3100


class RefArcError(ValueError):
    """A malformed reference-arc table (missing key, duplicate key, no arcs)."""


@dataclass
class ReferenceArc:
    key: str                       # the arc slug = the campaign FOLDER name = the --out dir = the journey member
    name: str                      # the human label (the journey-menu / overview name)
    seed: int                      # the REAL FF9 field id to import-chain from
    zone: "str | None" = None      # optional FBG token for `import-chain --zones` (default: the seed's own zone)
    beat: "int | None" = None      # optional ScenarioCounter to seed this arc's story state on entry
    note: str = ""


@dataclass
class ReferenceArcSet:
    title: str
    arcs: list = field(default_factory=list)   # list[ReferenceArc], in story order


# --------------------------------------------------------------------------- load
def load_reference_arcs(path=None) -> ReferenceArcSet:
    """Parse a reference-arc table (default = the packaged disc-1 ``data/reference_arcs.toml``). Raises
    :class:`RefArcError` on a missing/duplicate ``key`` or an empty table."""
    p = Path(path) if path else _DATA
    with open(p, "rb") as fh:
        data = tomllib.load(fh)
    arcs: list = []
    seen: set = set()
    for i, a in enumerate(data.get("arc", [])):
        for req in ("key", "name", "seed"):
            if req not in a:
                raise RefArcError(f"[[arc]] #{i}: missing required key {req!r}")
        key = str(a["key"]).strip()
        if not key:
            raise RefArcError(f"[[arc]] #{i}: empty 'key'")
        if key in seen:
            raise RefArcError(f"duplicate arc key {key!r} (each arc = a distinct campaign folder)")
        seen.add(key)
        arcs.append(ReferenceArc(
            key=key, name=str(a["name"]), seed=int(a["seed"]),
            zone=(str(a["zone"]).strip() or None) if a.get("zone") else None,
            beat=(int(a["beat"]) if a.get("beat") is not None else None),
            note=str(a.get("note", ""))))
    if not arcs:
        raise RefArcError(f"{p}: no [[arc]] rows")
    return ReferenceArcSet(title=str(data.get("title") or "FF9 reference arc"), arcs=arcs)


# --------------------------------------------------------------------------- per-arc fork parameters
def arc_id_base(index: int, *, base: int = DEFAULT_ID_BASE, span: int = ARC_ID_SPAN) -> int:
    """The disjoint ``--id-base`` for arc ``index`` (0-based) so no two arcs share an EventDB id band."""
    return base + index * span


def arc_name_prefixes(arcset: ReferenceArcSet) -> dict:
    """A unique short FBG/EVT ``--name-prefix`` per arc (so two arcs forking related fields don't collide on
    the by-name, highest-folder-wins scene/.eb resolution). Derived from the key, de-duplicated."""
    out: dict = {}
    used: set = set()
    for arc in arcset.arcs:
        base = "".join(c for c in arc.key if c.isalnum()).upper()[:4] or "ARC"
        tag, n = base, 1
        while tag in used:
            n += 1
            tag = f"{base[:3]}{n}"
        used.add(tag)
        out[arc.key] = tag
    return out


def arc_mod_folder(tag: str) -> str:
    """The stacked Memoria mod folder a forked arc deploys into. Each arc needs its OWN folder -- the journey
    assembler ABORTS if two campaigns share a ``mod_folder`` (it wholesale-replaces a folder per campaign).
    Derived from the arc's unique ``tag`` so the 12 folders are disjoint."""
    return f"FF9CustomMap-{tag.lower()}"


def arc_flags_per_field(n_arcs: int, *, max_fields: int = MAX_FIELDS_PER_ARC, budget: int = SAFE_FLAG_BUDGET) -> int:
    """A per-field GLOB flag-block width small enough that ALL ``n_arcs`` arcs' flag windows fit the safe band
    (the assembler lays them end-to-end; the default 64 overflows past ~2 arcs). The largest power-of-two in
    [8, 64] that fits ``n_arcs * max_fields * fpf <= budget``; floors at 8 for a very long table (the header
    note warns + the deploy lint still catches a true overflow)."""
    for fpf in (64, 32, 16, 8):
        if max(n_arcs, 1) * max_fields * fpf <= budget:
            return fpf
    return 8


def fork_command(arc: ReferenceArc, *, id_base: int, tag: str, flags_per_field: int, verbatim: bool = True) -> str:
    """The ``ff9mapkit import-chain`` line that forks ONE arc into its own campaign folder: ``--out <key>``, a
    disjoint ``--id-base`` (EventDB id band), a unique ``--name-prefix`` (by-name FBG/.eb resolution across the
    stacked folders), a unique ``--mod-folder`` (the assembler needs one folder per campaign), a
    ``--flags-per-field`` sized so the chain's flag windows fit the safe band, and ``--verbatim`` for the
    truest fork. ``tag`` is the arc's unique short slug driving the prefix + folder."""
    parts = [f"py -m ff9mapkit import-chain {arc.seed}", f"--out {arc.key}"]
    if arc.zone:
        parts.append(f"--zones {arc.zone}")
    parts.append("--whole-zone")                 # fork the WHOLE zone, not just the seed's door-reachable slice
    #                                              (cutscene zones don't door-connect -- the bytes are there)
    if verbatim:
        parts.append("--verbatim")
    parts.append(f"--id-base {id_base}")
    parts.append(f"--name-prefix {tag}")
    parts.append(f"--mod-folder {arc_mod_folder(tag)}")
    parts.append(f"--flags-per-field {flags_per_field}")
    return " ".join(parts)


def fork_playbook(arcset: ReferenceArcSet, *, id_base: int = DEFAULT_ID_BASE) -> list:
    """``[(arc, command), ...]`` -- the ordered ``import-chain`` commands that fork every arc into its OWN
    id band + name-prefix + mod folder + a chain-sized flag budget (so the chain deploys with no EventDB /
    by-name / folder / flag-window collisions). Run them from the folder that holds the journeys.toml so each
    ``--out <key>`` lands beside it."""
    tags = arc_name_prefixes(arcset)
    fpf = arc_flags_per_field(len(arcset.arcs))
    return [(arc, fork_command(arc, id_base=arc_id_base(i, base=id_base), tag=tags[arc.key], flags_per_field=fpf))
            for i, arc in enumerate(arcset.arcs)]


# --------------------------------------------------------------------------- render the journeys.toml
def _commented_block(lines: list) -> list:
    return [("# " + ln).rstrip() for ln in lines]


def render_arc_journey_toml(arcset: ReferenceArcSet, *, hub_name: str = "FF9 Disc 1", hub_id: int = 4600,
                            borrow_bg: "str | None" = None, hub_area: "int | None" = None,
                            borrow_field: "int | None" = None, journey_id: str = "ff9_disc1",
                            journey_name: "str | None" = None, id_base: int = DEFAULT_ID_BASE) -> str:
    """Render a multi-campaign ``journeys.toml`` laying the arcs out as one chained journey, with the fork
    PLAYBOOK in the header and the entry/links/seed left as fill-in templates (the member names come from the
    forked campaigns). The hub defaults to MOGNET CENTRAL (field 3100 -- FF9's journey nexus + a real
    ``borrow_field`` so ``deploy_journey --apply`` auto-extracts the camera); pass ``borrow_bg`` to theme it on
    another room (``hub_area``/``borrow_field`` then describe that room, else only the bg is emitted). Always
    loads structurally; the not-yet-forked campaign folders surface as a 'fork first' note -- onboarding."""
    if borrow_bg is None:                          # default the hub to Mognet Central (thematic + --apply-ready)
        borrow_bg, hub_area, borrow_field = HUB_BORROW_BG, HUB_BORROW_AREA, HUB_BORROW_FIELD
    journey_name = journey_name or arcset.title
    plays = fork_playbook(arcset, id_base=id_base)
    keys = [a.key for a in arcset.arcs]
    fpf = arc_flags_per_field(len(arcset.arcs))

    L: list = []
    L += _commented_block([
        f"{arcset.title} -- an FF9 reference arc (the north-star fork-and-test harness).",
        "",
        "Each arc below is ONE campaign you fork from a REAL FF9 field, chained as a multi-campaign journey.",
        "This is a PLAN, not a one-click rebuild -- fork an arc, fill its entry/links, deploy, walk it, ask",
        '"does it play identically?", then move to the next arc (CLAUDE.md: fork FIDELITY, not a release).',
        "",
        "STEP 1 -- fork every arc (run these FROM this folder, so each --out <key> lands beside this file).",
        f"         Each gets its OWN id band + name-prefix + mod folder + a {fpf}-bit flag block, so the {len(keys)}",
        "         arcs deploy with no EventDB / by-name / folder / flag-window collisions (don't drop those flags):",
    ])
    for i, (arc, cmd) in enumerate(plays, 1):
        L.append(f"#   {i:>2}. {cmd}")
        if arc.note:
            L.append(f"#       -- {arc.name}: {arc.note}")
    L += _commented_block([
        "",
        "STEP 2 -- in each forked campaign.toml, note its ENTRY member name + the BOUNDARY member that exits",
        "         to the next arc; fill them into `entry` and the `[[journey.link]]` rows below.",
        "STEP 3 -- deploy + playtest:  Build & Deploy -> (this journeys.toml) -> Preview playbook, then Deploy.",
        "         Or:  py tools/deploy_journey.py journeys.toml --apply   (one-shot, reverse-order revert).",
        "         The one-shot AUTO-EXTRACTS the hub camera, which needs a real source field: set [hub]",
        "         borrow_field = <real field id> below, or supply [hub] camera = \"<your>.bgx\" yourself.",
    ])
    L.append("")

    from . import hub as _hub
    L.append("[hub]")
    L.append(f'name = "{_hub.name_token(hub_name)}"          # an EVT_/FBG_ token (no spaces -- the field name)')
    L.append(f"id = {int(hub_id)}                  # the hub field id (custom band, >= 4000; NOT in an arc band)")
    if hub_area is not None:
        L.append(f"area = {int(hub_area)}                  # the borrowed room's FBG area (FBG_N<area>_...)")
    else:                                              # custom borrow_bg with no area -> the default 21 is likely wrong
        L.append("# area = 21          # SET ME: must equal the borrowed room's real FBG area (the default 21 is "
                 "usually WRONG for a custom room -> black screen)")
    L.append(f'borrow_bg = "{_toml_str(borrow_bg)}"   # a real field whose art the hub reuses (`list-fields`)')
    if borrow_field is not None:
        L.append(f"borrow_field = {int(borrow_field)}              # the real field -> `deploy_journey --apply` "
                 "auto-extracts its camera")
    else:
        L.append("# borrow_field = <real field id>   # uncomment so `deploy_journey --apply` auto-extracts the camera")
    L.append("")

    L.append("[[journey]]")
    L.append(f'id = "{_toml_str(journey_id)}"        # the stable journey slug')
    L.append(f'name = "{_toml_str(journey_name)}"   # shown on the hub menu')
    clist = ", ".join(f'"{_toml_str(k)}"' for k in keys)
    L.append(f"campaigns = [{clist}]")
    L.append(f'#   ^ the {len(keys)} arc folders (fork them in STEP 1 above; order = story order).')
    first = arcset.arcs[0]
    L.append(f'entry = {{ campaign = "{_toml_str(first.key)}", field = "ENTRY_MEMBER" }}'
             f"   # CHANGE: the start member of {first.name} (real field {first.seed})")
    L.append("")

    L += _commented_block([
        f"One link per arc boundary ({len(keys)} arcs -> {max(len(keys) - 1, 0)} links). Uncomment + fill the",
        "member names (the boundary member that walks OUT of arc i, and the arrival member of arc i+1):",
    ])
    for a, b in zip(arcset.arcs, arcset.arcs[1:]):
        L.append("# [[journey.link]]")
        L.append(f'# from = {{ campaign = "{_toml_str(a.key)}", field = "BOUNDARY_MEMBER" }}'
                 f"   # {a.name} (real {a.seed})")
        L.append(f'# to = {{ campaign = "{_toml_str(b.key)}", field = "ARRIVAL_MEMBER", entrance = 0 }}'
                 f"   # {b.name} (real {b.seed})")
    L.append("")

    L += _commented_block([
        "The New-Game starting state for this journey (the story_flags capstone). Uncomment + edit:",
    ])
    if first.beat is not None:
        L.append("[journey.seed]")
        L.append(f"scenario = {int(first.beat)}        # {first.name}'s opening beat")
    else:
        L.append("# [journey.seed]")
        L.append(f"# scenario = 0          # the ScenarioCounter for {first.name}'s start (your game knowledge)")
        L.append('# party = ["Zidane"]')
    return "\n".join(L) + "\n"


def _toml_str(s) -> str:
    """Escape a value for a double-quoted TOML string (backslash + quote)."""
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


# --------------------------------------------------------------------------- parse the playbook back out
@dataclass
class ParsedFork:
    key: str                       # the arc folder (the --out value) = the journeys.toml campaign name
    seed: int                      # the real field id (the import-chain seed)
    command: str                   # the canonical `import-chain <seed> --out <key> ...` (no launcher prefix)


_FORK_RE = re.compile(r"(import-chain\s+(\d+)\b.*?--out\s+(\S+).*?)\s*$")


def parse_fork_commands(text: str) -> list:
    """Recover the fork PLAYBOOK from a journeys.toml's header comments: every commented
    ``# .. py -m ff9mapkit import-chain <seed> ... --out <key> ...`` line -> a :class:`ParsedFork` (in file
    order, de-duplicated by key). Returns ``[]`` for a file with no playbook (a hand-written journey). The
    GUI uses this to offer a per-arc Fork button; ``command`` is the launcher-free tail (run it via
    ``editor.jobs.fork_command_argv``)."""
    out: list = []
    seen: set = set()
    for raw in text.splitlines():
        s = raw.strip()
        if not s.startswith("#") or "import-chain" not in s:
            continue
        m = _FORK_RE.search(s)
        if not m:
            continue
        key = m.group(3)
        if key in seen:
            continue
        seen.add(key)
        out.append(ParsedFork(key=key, seed=int(m.group(2)), command=m.group(1).strip()))
    return out


# --------------------------------------------------------------------------- STEP 2: reconcile after Fork-All
# The scaffold ships `entry = {.. field = "ENTRY_MEMBER"}` + COMMENTED `[[journey.link]]` templates (STEP 2 =
# "fill the member names from the forked campaigns"). Until filled, the journey hard-errors on the placeholder
# + warns 0-of-(N-1) links. This automates STEP 2: once the campaigns are forked beside the journeys.toml, we
# read each campaign.toml's REAL entry member + boundary seams and rewrite the placeholders in place.
@dataclass
class ReconcileNote:
    level: str    # "filled" (an exact fill) | "verify" (a best-guess that needs a human eyeball) | "skip"
    text: str


def _mk_link(src_c, src_f, dst_c, dst_f, *, comment=None):
    return {"src_campaign": src_c, "src_field": src_f, "dst_campaign": dst_c, "dst_field": dst_f,
            "comment": comment}


def _pick_boundary(cur_plan, nxt_plan, cur, nxt, notes):
    """Pick the boundary member of ``cur`` that hands off to ``nxt`` + the arrival member, the SAME way the
    deploy step classifies a link (:func:`journey._seam_remap`, fed the next arc's real ids): a member with a
    ``Field()`` door straight INTO ``nxt`` (PRECISE field_remap, exact arrival) wins; else a world-map exit
    (worldmap_inject, arrival = ``nxt``'s entry -- NOT shadowed by the member's in-zone doors); else a lone
    out-of-chain door repurposed to ``nxt`` (a VERIFY note). Returns a link dict (always -- a `fill`/`verify`
    link still scaffolds the row so the journey lints + the human only edits one field)."""
    from . import journey as _journey
    nxt_sources = {m.real_id: m.name for m in nxt_plan.members}     # real field id -> the next arc's member name
    nxt_reals = frozenset(nxt_sources)                             # the next arc's donor ids (precise-door test)
    nxt_entry = nxt_plan.entry_name
    precise, overworld, other_fr = [], [], []
    for m in cur_plan.members:
        sr = _journey._seam_remap(cur_plan, m.name, 0, dst_reals=nxt_reals)   # dst_id dummy; read mode/remap
        if sr["mode"] == "field_remap":
            target = next(iter(sr["remap"]), None)                 # the chosen int seam target
            (precise.append((m.name, nxt_sources[target])) if target in nxt_sources else other_fr.append(m.name))
        elif sr["mode"] == "worldmap_inject":
            overworld.append(m.name)
    if precise:
        nm, dst = precise[0]
        if len(precise) > 1:                                       # a tie -> mark it inline so it's not silently picked
            notes.append(ReconcileNote("verify", f"{cur} -> {nxt}: {len(precise)} members exit into {nxt}; "
                                       f"picked {nm!r}"))
            return _mk_link(cur, nm, nxt, dst,
                            comment=f"VERIFY: {len(precise)} members of {cur} exit into {nxt}; "
                                    f"picked {nm} -> {dst}")
        return _mk_link(cur, nm, nxt, dst)
    if len(overworld) == 1:
        return _mk_link(cur, overworld[0], nxt, nxt_entry)
    if len(overworld) > 1:
        notes.append(ReconcileNote("verify", f"{cur} -> {nxt}: {len(overworld)} world-map exits {overworld}; "
                                   f"picked {overworld[0]!r} -- confirm it's the one toward {nxt}"))
        return _mk_link(cur, overworld[0], nxt, nxt_entry,
                        comment=f"VERIFY: {cur} has {len(overworld)} world-map exits; confirm this is toward {nxt}")
    if len(other_fr) == 1:
        notes.append(ReconcileNote("verify", f"{cur} -> {nxt}: boundary {other_fr[0]!r} exits to a field "
                                   f"outside {nxt} -- confirm the hand-off target"))
        return _mk_link(cur, other_fr[0], nxt, nxt_entry,
                        comment=f"VERIFY: {other_fr[0]} exits to a field outside {nxt}; confirm to.field")
    notes.append(ReconcileNote("verify", f"{cur} -> {nxt}: no single clear boundary seam -- set from.field by "
                               f"hand (the member that leaves {cur} toward {nxt})"))
    return _mk_link(cur, "BOUNDARY_MEMBER", nxt, nxt_entry,
                    comment=f"FILL: the member that leaves {cur} toward {nxt} (no boundary seam auto-found)")


def _journey_block_range(lines, target_jidx):
    """The [start, end) line span of the ``target_jidx``-th ``[[journey]]`` block (a row runs to the next
    ``[[journey]]`` header or EOF; its ``[[journey.link]]`` / ``[journey.seed]`` subtables belong to it).
    ``(None, None)`` if there's no such block."""
    idxs = [i for i, ln in enumerate(lines) if ln.strip() == "[[journey]]"]
    if target_jidx >= len(idxs):
        return None, None
    start = idxs[target_jidx]
    end = idxs[target_jidx + 1] if target_jidx + 1 < len(idxs) else len(lines)
    return start, end


_ENTRY_FIELD_RE = re.compile(r'field\s*=\s*"([^"]*)"')
_TMPL_PREFIXES = ("# [[journey.link]]", "# from = {", "# to = {", "# One link per arc boundary",
                  "# member names (")


def _is_link_template(stripped: str) -> bool:
    return any(stripped.startswith(p) for p in _TMPL_PREFIXES)


def _render_links(links):
    out: list = []
    for lk in links:
        if lk.get("comment"):
            out.append(f"# {lk['comment']}")
        out.append("[[journey.link]]")
        out.append(f'from = {{ campaign = "{_toml_str(lk["src_campaign"])}", '
                   f'field = "{_toml_str(lk["src_field"])}" }}')
        out.append(f'to = {{ campaign = "{_toml_str(lk["dst_campaign"])}", '
                   f'field = "{_toml_str(lk["dst_field"])}", entrance = 0 }}')
        out.append("")                                             # a blank line between adjacent link blocks
    return out


def reconcile_arc_journey(text: str, base_dir) -> "tuple[str, list]":
    """Fill a reference-arc ``journeys.toml``'s ``entry`` placeholder + its commented ``[[journey.link]]`` rows
    from the REAL member names of the forked campaign folders beside it (STEP 2, automated). ``text`` is the
    file content; ``base_dir`` is the folder holding it (where each ``<campaign>/campaign.toml`` was forked).

    Returns ``(new_text, notes)`` -- ``notes`` is a list of :class:`ReconcileNote`. ``new_text == text`` (with a
    'skip' note) when there's nothing to do: no multi-campaign journey, the campaigns aren't forked yet, or the
    links are already filled. Targets the FIRST multi-campaign journey (the reference-arc scaffold has exactly
    one; a selector hub of BARE journeys needs no reconcile). Pure + tk-free -- the GUI writes the result so
    the edit is one undo step; a CLI/test can call it headless."""
    from . import campaign as _campaign
    base = Path(base_dir)
    notes: list = []
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        return text, [ReconcileNote("skip", f"not parseable TOML ({e})")]

    jrows = data.get("journey", [])
    midx = next((i for i, j in enumerate(jrows) if j.get("campaigns")), None)
    if midx is None:
        return text, [ReconcileNote("skip", "no multi-campaign [[journey]] to reconcile "
                                    "(bare journeys warp to a field id -- no entry member or links to fill)")]
    if sum(1 for j in jrows if j.get("campaigns")) > 1:
        notes.append(ReconcileNote("verify", "more than one multi-campaign journey -- reconciling only the first"))
    campaigns = [str(c) for c in jrows[midx].get("campaigns", [])]
    if not campaigns:
        return text, [ReconcileNote("skip", "the journey lists no campaigns")]

    plans: dict = {}
    for k in campaigns:
        cpath = base / k / "campaign.toml"
        if cpath.is_file():
            try:
                plans[k] = _campaign.load_campaign(cpath)
            except Exception as e:                                  # noqa: BLE001 -- a bad campaign.toml -> skip it
                notes.append(ReconcileNote("verify", f"campaign {k!r}: campaign.toml unreadable ({e})"))
    if campaigns[0] not in plans:
        notes.append(ReconcileNote("skip", f"fork the campaigns first (STEP 1) -- {campaigns[0]!r} has no "
                                   f"campaign.toml at {base / campaigns[0] / 'campaign.toml'}"))
        return text, notes

    entry_member = plans[campaigns[0]].entry_name                  # the entry arc's REAL start member (exact)
    pairs = list(zip(campaigns, campaigns[1:]))
    unforked = sorted({c for pair in pairs for c in pair if c not in plans})
    # Fill the link rows ATOMICALLY -- only once EVERY boundary's two campaigns are forked. A PARTIAL fill would
    # strip the still-commented templates for the not-yet-forkable boundaries (losing them), and a later re-run
    # would see the real rows it did write and bail (has_real_link) -- so those links could NEVER be filled. For
    # an incremental fork-by-arc workflow we therefore keep ALL templates until the chain is complete, then fill
    # them in one pass. (Entry only needs the first campaign, so it fills early regardless.)
    links_complete = not unforked
    links = [_pick_boundary(plans[c], plans[n], c, n, notes) for (c, n) in pairs] if links_complete else []

    # ---- text surgery on the target journey block (leave everything else, incl. the header playbook, intact)
    lines = text.split("\n")
    start, end = _journey_block_range(lines, midx)
    if start is None:
        notes.append(ReconcileNote("skip", "couldn't locate the [[journey]] block (file hand-edited?)"))
        return text, notes
    block = lines[start:end]

    # entry: replace ONLY the placeholder (respect a real member a human already set)
    changed = False
    for i, ln in enumerate(block):
        if ln.strip().startswith("entry ="):
            m = _ENTRY_FIELD_RE.search(ln)
            cur_field = m.group(1) if m else None
            if cur_field == "ENTRY_MEMBER" or cur_field is None:
                block[i] = f'entry = {{ campaign = "{_toml_str(campaigns[0])}", field = "{_toml_str(entry_member)}" }}'
                notes.append(ReconcileNote("filled", f"entry -> {campaigns[0]}/{entry_member}"))
                changed = True
            else:
                notes.append(ReconcileNote("skip", f"entry already set to {cur_field!r} -- left as-is"))
            break

    # links: fill the whole set in ONE pass, and only when the block has NO real [[journey.link]] yet AND every
    # boundary resolved (so an incremental fork keeps the templates intact + a re-run can complete the chain).
    has_real_link = any(ln.strip() == "[[journey.link]]" for ln in block)
    if has_real_link:
        notes.append(ReconcileNote("skip", "[[journey.link]] rows already present -- left as-is "
                                   "(delete them to re-fill)"))
    elif not links_complete:
        notes.append(ReconcileNote("verify", f"links NOT filled yet -- fork {unforked} first, then re-run; the "
                                   f"commented link templates are KEPT so a later run fills the whole chain"))
    elif links:
        kept, insert_at = [], None
        for ln in block:
            if _is_link_template(ln.strip()):
                if insert_at is None:
                    insert_at = len(kept)                          # splice the real rows where the template was
                continue
            kept.append(ln)
        rendered = _render_links(links)
        if insert_at is None:                                      # no template (hand-written) -> after `entry =`
            ei = next((i for i, ln in enumerate(kept) if ln.strip().startswith("entry =")), None)
            insert_at = (ei + 1) if ei is not None else len(kept)
            rendered = [""] + rendered
        block = kept[:insert_at] + rendered + kept[insert_at:]
        n_verify = sum(1 for lk in links if lk.get("comment"))
        notes.append(ReconcileNote("filled" if not n_verify else "verify",
                                   f"{len(links)} link(s) filled" + (f" ({n_verify} need a look)" if n_verify else "")))
        changed = True

    if not changed:
        notes.append(ReconcileNote("skip", "nothing to fill (entry + links already set)"))
        return text, notes
    return "\n".join(lines[:start] + block + lines[end:]), notes
