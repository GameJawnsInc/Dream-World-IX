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
# (the sec 8 id-disjointness guarantee the journey assembler lints). 100 ids/arc easily covers import-chain's
# <=25 members; the band starts in the shipped-custom range (4000-9899, CLAUDE.md sec 3).
DEFAULT_ID_BASE = 6000
ARC_ID_SPAN = 100

# The journey assembler lays every campaign's GLOB flag window end-to-end inside ONE safe band (8512..16320 =
# 7808 bits). At import-chain's defaults (25 members x 64 flags/field) a 12-arc chain needs 19200 bits and
# OVERFLOWS -> the deploy lint hard-errors. So the fork playbook emits a SMALLER `--flags-per-field` sized so
# all arcs fit; arcs keep their full member count (the lever is the per-field reservation, not --max-fields).
SAFE_FLAG_BUDGET = _flags.CHOICE_SCRATCH_FLOOR - _flags.FIRST_SAFE_FLAG     # bits the journey band has for campaigns
MAX_FIELDS_PER_ARC = 25                                                     # import-chain's default --max-fields cap


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
                            borrow_bg: str = "N11_HUT", journey_id: str = "ff9_disc1",
                            journey_name: "str | None" = None, id_base: int = DEFAULT_ID_BASE) -> str:
    """Render a multi-campaign ``journeys.toml`` laying the arcs out as one chained journey, with the fork
    PLAYBOOK in the header and the entry/links/seed left as fill-in templates (the member names come from the
    forked campaigns). Always loads structurally (the schema is valid); the not-yet-forked campaign folders
    surface as a 'fork the campaigns first' note in the journey overview/lint -- onboarding, not a crash."""
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

    L.append("[hub]")
    L.append(f'name = "{_toml_str(hub_name)}"          # the World-Hub field that lists + warps into the arcs')
    L.append(f"id = {int(hub_id)}                  # the hub field id (custom band, >= 4000; NOT in an arc band)")
    L.append(f'borrow_bg = "{_toml_str(borrow_bg)}"   # a real field whose art the hub reuses (`list-fields`)')
    L.append("# borrow_field = <real field id>   # uncomment so `deploy_journey --apply` auto-extracts the hub camera")
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
