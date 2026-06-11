"""``fork-report`` -- preview, OFFLINE, what a fork of a real FF9 field will and won't reproduce.

The north star is fork FIDELITY (``docs/FORK_FIDELITY.md``): "fork a real field -> does it play identically?"
Before you fork, this answers it. For any real field it reads the compiled ``.eb`` (no game running) and reports:

  * **Roster fidelity** -- how many persistent objects a fork carries, how many are ``Field()``-warp **directors**
    (cutscene actors carried as NPCs -> the rotating-cast mess), and whether content rotates by story beat.
  * **Interaction fidelity** -- per carried NPC, whether its talk handler PORTS (`graft_safety`): ``clean`` = fully
    interactive on the fork, ``init_only`` = renders but its talk is dropped (re-author it), ``refuse`` = a stub.
  * **Story gating** -- story-gated doors + the ScenarioCounter beats the field gates content on.
  * **Home beat** -- a suggested ``[startup] scenario`` (the author picks the beat -- they have the game knowledge).

It is **read-only** and reuses the existing scanners (``eventscan.scan_objects_verbatim`` for the carry
classification, ``eventscan.scan_gateway_entries`` for gated doors, ``flags`` for the beat table) -- it adds
no carry/scanner logic of its own. Two axes are reported SEPARATELY because they are independent: Daguerreo
is a clean *roster* (0 directors, renders faithfully) yet degrades *interactions* (half its NPCs go render-only).
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field as _dc_field

from . import flags as _flags
from .eb.model import EbScript

# --- bytecode signals -------------------------------------------------------------------------------
FIELD_OP = 0x2B            # Field(target) -- a warp; in an object's tag-1 LOOP => a cutscene director/actor
PHASE_SWITCH_OP = 0x06     # op_06 -- a phase/state jump-table (the other director tell)
LOOP_TAG = 1               # object LOOP function (where cutscene warps live)
TALK_TAG = 3               # press-action talk handler

# A ScenarioCounter gate in an expression: push GLOB_UINT16[0] (DC 00), a constant (7D lo hi), then a
# COMPARISON op (a write would use 2C/3F instead, so comparisons alone are the field's story gates).
_SC_GATE = re.compile(rb"\xDC\x00\x7D(..)(.)", re.DOTALL)
_CMP_OPS = frozenset({0x18, 0x19, 0x1A, 0x1B, 0x20})   # < > <= >= ==
# Many distinct gate values => the field rotates its content/cast by story progress (the Dali shop gates
# at 11 values, Dali through Pandemonium; a static room gates at <=1).
_ROTATING_GATE_COUNT = 3


@dataclass
class ForkReport:
    field_id: int
    fbg_name: str = ""
    event_name: str = ""
    has_script: bool = True
    n_objects: int = 0
    n_props: int = 0                          # non-talkable set-dressing
    n_talkable: int = 0
    directors: list = _dc_field(default_factory=list)     # donor_idx of carried objects that warp/switch in LOOP
    stacked: list = _dc_field(default_factory=list)       # donor_idx of multi-instance (one-spot stacking) objects
    safety: dict = _dc_field(default_factory=dict)        # {clean: n, init_only: n, refuse: n}
    gated_doors: int = 0
    sc_gates: list = _dc_field(default_factory=list)      # [(value, (milestone_value, beat))] sorted
    suggested_scenario: int | None = None
    roster_class: str = "static-roster"        # "static-roster" | "story-event"
    notes: list = _dc_field(default_factory=list)


def _is_director(eb: EbScript, donor_idx: int) -> bool:
    """True if the object's LOOP (tag 1) warps (``Field()``) or runs a phase-switch -- a cutscene
    director/actor carried as an NPC (the rotating-cast / stacked-spawn failure mode)."""
    try:
        loop = eb.entry(donor_idx).func_by_tag(LOOP_TAG)
    except (IndexError, AttributeError):
        return False
    if loop is None:
        return False
    return any(ins.op in (FIELD_OP, PHASE_SWITCH_OP) for ins in eb.instrs(loop))


def scenario_gates(eb_bytes) -> list[int]:
    """Distinct ScenarioCounter values the field COMPARES against (the beats it gates content on), sorted.
    A field with many of these rotates its cast/content by story progress; one (or none) is static."""
    out = set()
    for m in _SC_GATE.finditer(bytes(eb_bytes)):
        if m.group(2)[0] in _CMP_OPS:
            out.add(struct.unpack("<H", m.group(1))[0])
    return sorted(out)


def resolve_field_id(token, *, game=None) -> int:
    """A field id (digit) or an FBG/event-name substring -> the numeric field id. Raises ValueError on no
    match or an ambiguous substring (unless one candidate is an exact FBG/mapid match)."""
    from .extract import ID_TO_FBG, ID_TO_EVT
    s = str(token).strip()
    if s.isdigit():
        fid = int(s)
        if fid in ID_TO_FBG:           # a real, forkable field id (vs a typo that would silently read empty)
            return fid
        raise ValueError(f"no field with id {fid} -- pass a real field id or an FBG substring (see "
                         f"`list-fields`). Note: a bare number here is a FIELD ID, not a map number.")
    sl = s.lower()
    hits = [fid for fid, fbg in ID_TO_FBG.items() if sl in (fbg or "").lower()]
    hits += [fid for fid, evt in ID_TO_EVT.items() if sl in (evt or "").lower() and fid not in hits]
    if not hits:
        raise ValueError(f"no field matches {token!r} -- pass a field id or an FBG substring (see `list-fields`)")
    if len(hits) > 1:
        exact = [fid for fid in hits if sl == (ID_TO_FBG.get(fid, "") or "").lower()
                 or ("_map" + sl) in (ID_TO_FBG.get(fid, "") or "").lower()]
        if len(exact) == 1:
            return exact[0]
        ex = ", ".join(ID_TO_FBG.get(f, str(f)) for f in hits[:4])
        raise ValueError(f"{token!r} matches {len(hits)} fields ({ex}{'...' if len(hits) > 4 else ''}) "
                         f"-- be more specific or use the field id")
    return hits[0]


def analyze(field_id: int, *, game=None, bundle=None) -> ForkReport:
    """Build the fidelity preview for a real field id. ``bundle`` (an ``extract.EventBundle``) is reused
    across calls when given; otherwise one is created. Read-only -- never touches the install's bytes."""
    from .extract import EventBundle, ID_TO_FBG, ID_TO_EVT   # lazy: extraction deps (UnityPy) only when used
    b = bundle or EventBundle(game)
    data = b.eb_for_id(field_id)
    return analyze_eb(data, field_id=field_id,
                      fbg_name=ID_TO_FBG.get(field_id, ""), event_name=ID_TO_EVT.get(field_id, ""))


def analyze_eb(eb_bytes, *, field_id: int = 0, fbg_name: str = "", event_name: str = "") -> ForkReport:
    """The pure analysis: a fidelity preview from a field's ``.eb`` bytes (no install needed -- so it is
    unit-testable against a fixture). :func:`analyze` is the thin id->bytes loader over this."""
    rep = ForkReport(field_id=field_id, fbg_name=fbg_name, event_name=event_name)
    if not eb_bytes:
        rep.has_script = False
        rep.notes.append("no field event script (a world/special/unmapped field) -- nothing to fork")
        return rep
    data = bytes(eb_bytes)

    from . import eventscan as _eventscan      # lazy (keeps import cost off the core path)
    try:
        eb = EbScript.from_bytes(data)         # raises on bad magic -> report gracefully, don't crash a preview
    except ValueError as e:
        rep.has_script = False
        rep.notes.append(f"not a parseable field script ({e})")
        return rep
    # Classify carry at the FULL faithful-fork setting -- the recommended `import --native
    # --graft-player-funcs --carry-text` recipe + the default STARTSEQ-helper closure -- so the portability
    # numbers match what the author actually gets (else an object only blocked by a benign Seq helper or a
    # graftable player gesture reads as render-only here but carries clean in a real fork).
    objs = _eventscan.scan_objects_verbatim(data, graft_player_funcs=True, carry_text=True,
                                            graft_seq_helpers=True)
    rep.n_objects = len(objs)
    for o in objs:
        di = o.get("donor_idx")
        rep.safety[o.get("graft_safety", "?")] = rep.safety.get(o.get("graft_safety", "?"), 0) + 1
        if o.get("kind") == "npc":
            rep.n_talkable += 1
        else:
            rep.n_props += 1
        if di is not None and _is_director(eb, di):
            rep.directors.append(di)
        if len(o.get("instances", []) or []) > 1:
            rep.stacked.append(di)

    try:
        gw = _eventscan.scan_gateway_entries(data)
        rep.gated_doors = sum(1 for g in gw if g.get("story_gated"))
    except (ValueError, IndexError, KeyError, struct.error):   # a malformed gateway region -> just omit the count
        rep.gated_doors = 0

    gates = scenario_gates(data)
    rep.sc_gates = [(v, _flags.nearest_milestone(v)) for v in gates]
    # earliest gate ~= when the field's story content first appears = its natural "home" beat. (A rotating
    # field also gates at later beats; the author picks which one -- the list shows them all.)
    rep.suggested_scenario = gates[0] if gates else None

    rotating = len(gates) >= _ROTATING_GATE_COUNT
    rep.roster_class = "story-event" if (rep.directors or rotating) else "static-roster"
    if rep.directors:
        rep.notes.append(f"{len(rep.directors)} carried object(s) are cutscene DIRECTORS (Field()/phase-switch "
                         f"in their LOOP) -- forking runs that logic against the asserted beat (gap #13)")
    if rotating:
        rep.notes.append(f"content gates on {len(gates)} story beats -- this field ROTATES its cast/content; "
                         f"a fork shows one beat (pick it with [startup] scenario)")
    if rep.stacked:
        rep.notes.append(f"{len(rep.stacked)} object(s) are multi-instanced -- watch for one-spot stacking")
    return rep


# --- rendering --------------------------------------------------------------------------------------
def _verdict_line(rep: ForkReport) -> str:
    clean = rep.safety.get("clean", 0)
    if rep.roster_class == "static-roster":
        head = "a CLEAN static-roster field -- a native fork renders the cast faithfully"
    else:
        head = "a STORY-EVENT field -- a fork is a high-fidelity diorama, not a faithful slice (rotating cast / cutscene actors)"
    inter = (f"{clean} of {rep.n_talkable} NPC(s) keep their interactions; the rest render-only "
             f"(re-author their dialogue)") if rep.n_talkable else "no talkable NPCs"
    return f"{head}; {inter}."


def format_report(rep: ForkReport) -> str:
    title = rep.fbg_name or f"field {rep.field_id}"
    lines = [f"fork-report: {title}  (field {rep.field_id}{', ' + rep.event_name if rep.event_name else ''})", ""]
    if not rep.has_script:
        lines.append("  " + (rep.notes[0] if rep.notes else "no event script"))
        return "\n".join(lines)

    s = rep.safety
    dirs = f"{len(rep.directors)} director(s)" if rep.directors else "0 directors"
    stack = f", {len(rep.stacked)} multi-instance" if rep.stacked else ""
    lines.append(f"  Roster        : {rep.n_objects} carried object(s) ({rep.n_talkable} NPC, {rep.n_props} prop) "
                 f"- {dirs}{stack}  -> {rep.roster_class.upper()}")
    lines.append(f"  Interactions  : {s.get('clean', 0)} fully interactive, {s.get('init_only', 0)} render-only, "
                 f"{s.get('refuse', 0)} stub  (faithful carry = --graft-player-funcs --carry-text)")
    if rep.sc_gates:
        beats = ", ".join(f"{v} ({nm[1] if nm else '?'})" for v, nm in rep.sc_gates)
        lines.append(f"  Story gating  : {rep.gated_doors} gated door(s); ScenarioCounter gates at {beats}")
    else:
        lines.append(f"  Story gating  : {rep.gated_doors} gated door(s); no ScenarioCounter gates (beat-agnostic)")
    if rep.suggested_scenario is not None:
        nm = _flags.nearest_milestone(rep.suggested_scenario)
        beat = f' "{nm[1]}"' if nm else ""
        lines.append(f"  Home beat     : suggested [startup] scenario = {rep.suggested_scenario}{beat} "
                     f"(the earliest gate -- adjust to the beat you're forking)")
    lines += ["", "  Verdict: " + _verdict_line(rep)]
    if rep.notes:
        lines.append("")
        for n in rep.notes:
            lines.append(f"   - {n}")
    # suggested authoring
    fbg = rep.fbg_name or str(rep.field_id)
    lines += ["", "  Suggested authoring:",
              f"    ff9mapkit import {fbg} --native --graft-player-funcs --carry-text"]
    if rep.suggested_scenario is not None:
        nm = _flags.nearest_milestone(rep.suggested_scenario)
        lines += ["    [startup]",
                  f"    scenario = {rep.suggested_scenario}" + (f"   # {nm[1]}" if nm else "")]
    return "\n".join(lines)
