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

# The controlled PLAYER character (DefinePlayerCharacter's SetModel id). Most fields are Zidane; a
# non-Zidane primary means "you play as someone else" -- which forks faithfully ONLY via --verbatim (it
# ships the donor player rig + anim packs + the field's own party/cutscene setup whole). The graft path
# refuses non-Zidane player funcs ("model" graft-safety -- another rig's clip ids). Proven on Vivi/field 100.
# (memory project-ff9-non-zidane-donors). Names for the playable cast; others fall back to the GEO model name.
PLAYABLE_NAMES = {98: "Zidane", 532: "Zidane(ZDD)", 8: "Vivi", 5489: "Steiner", 526: "Steiner(STD)",
                  192: "Freya", 443: "Eiko", 185: "Garnet", 509: "Amarant", 273: "Kuja"}


def player_name(model_id) -> str:
    """A friendly name for a player model id (the playable cast), else its GEO model name, else 'none'."""
    if model_id is None:
        return "none"
    if model_id in PLAYABLE_NAMES:
        return PLAYABLE_NAMES[model_id]
    from ._modeldb import MODELS
    return MODELS.get(model_id, f"model {model_id}")


# Which entry the engine BINDS CONTROL to when a field defines >1 DefinePlayerCharacter (0x2C). The engine
# sets controlUID = the uid of each 0x2C as it EXECUTES (last-write-wins; Memoria EventEngine.DoEventCode.cs),
# and entries run their Init in InitObject (0x09 in Main_Init) order -- so control binds to the entry whose
# 0x2C runs LAST: among entries whose tag-0 Init runs a 0x2C UNCONDITIONALLY, the one InitObject'd latest.
# In-game PROVEN on the Treno Dagger+Steiner room (-> Garnet, the last-executed 0x2C, NOT the first-spawned
# Steiner nor the warp-in Zidane). memory project-ff9-non-zidane-donors. Reliable for FIXED-SID character
# fields (the non-Zidane lane); a normal party field can route control through a party slot to the LIVE
# leader, which this doesn't model -- so trust it only when no Zidane is among the PCs (the lane).
_BRANCH_OPS = frozenset({0x02, 0x03, 0x04})   # conditional-branch family (empirically gates a following 0x2C)
INITOBJ_OP = 0x09
DEFINE_PC_OP = 0x2C


def _init_0x2c_status(eb, entry_index) -> str:
    """A player entry's load-time Init (tag 0) DefinePlayerCharacter: 'uncond' (binds at spawn), 'cond'
    (behind a conditional branch -> story-dependent), or 'absent' (its 0x2C is in a cutscene func, not Init)."""
    try:
        f = eb.entry(entry_index).func_by_tag(0)
    except (IndexError, AttributeError):
        return "absent"
    if f is None:
        return "absent"
    ins = list(eb.instrs(f))
    idx = next((k for k, i in enumerate(ins) if i.op == DEFINE_PC_OP), None)
    if idx is None:
        return "absent"
    return "cond" if any(i.op in _BRANCH_OPS for i in ins[:idx]) else "uncond"


def controlled_player(eb):
    """Best-effort (entry_index | None, confidence in {'high','low','none'}) for the player entry the engine
    binds control to at field load (see the module note above). Single-PC -> that entry. Multi-PC -> among
    the entries whose Init runs a 0x2C unconditionally (else any 0x2C-in-Init), the one InitObject'd latest in
    Main_Init; 'low' confidence when that entry is multi-spawned or only gated (the binder is then ambiguous)."""
    from . import eventscan as _es  # lazy (extraction-free, but keeps import cost off the core path)
    pents = _es.resolve_player_entries(eb)
    if not pents:
        return (None, "none")
    if len(pents) == 1:
        return (pents[0], "high")
    mi = eb.entry(0).func_by_tag(0) if eb.entry_count > 0 else None
    order = [i.imm(0) for i in eb.instrs(mi) if i.op == INITOBJ_OP] if mi is not None else []

    def last_pos(p):
        occ = [k for k, v in enumerate(order) if v == p]
        return max(occ) if occ else -1

    status = {p: _init_0x2c_status(eb, p) for p in pents}
    pool = ([p for p in pents if status[p] == "uncond"]
            or [p for p in pents if status[p] == "cond"] or list(pents))
    binder = max(pool, key=last_pos)
    multi_spawn = sum(1 for v in order if v == binder) > 1
    conf = "high" if (status[binder] == "uncond" and not multi_spawn) else "low"
    return (binder, conf)


@dataclass
class ForkReport:
    field_id: int
    fbg_name: str = ""
    event_name: str = ""
    has_script: bool = True
    n_objects: int = 0
    n_props: int = 0                          # non-talkable set-dressing
    n_talkable: int = 0
    n_speaking: int = 0                        # carried NPCs whose tag-3 talk SHOWS dialogue (need --carry-text)
    n_dialogue_lines: int = 0                  # total distinct talk txids those NPCs show
    directors: list = _dc_field(default_factory=list)     # donor_idx of carried objects that warp/switch in LOOP
    stacked: list = _dc_field(default_factory=list)       # donor_idx of multi-instance (one-spot stacking) objects
    safety: dict = _dc_field(default_factory=dict)        # {clean: n, init_only: n, refuse: n}
    gated_doors: int = 0
    sc_gates: list = _dc_field(default_factory=list)      # [(value, (milestone_value, beat))] sorted
    suggested_scenario: int | None = None
    roster_class: str = "static-roster"        # "static-roster" | "story-event"
    player_models: list = _dc_field(default_factory=list)  # [(entry_index, model_id, name)] -- the defined PC(s)
    multi_pc: bool = False                                # the field defines >1 DefinePlayerCharacter
    non_zidane: bool = False                              # the controlled player isn't Zidane -> --verbatim is the faithful mode
    controlled_entry: int | None = None                  # the entry the engine BINDS control to (multi-PC; controlled_player)
    controlled_name: str = ""                            # its character name
    control_confidence: str = "none"                     # 'high' | 'low' | 'none' (binder ambiguity)
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

    # #5 preview (the TEXT axis, orthogonal to the interaction safety above): which carried NPCs SPEAK. A
    # talk handler's WindowSync shows a donor txid that renders WRONG/missing unless the fork carries the
    # words -- `--carry-text` remaps them, `--verbatim` ships the whole donor `.mes`. Mirrors the build-side
    # lint (`build._entry_window_txids`) as a BEFORE-you-fork preview, via the dialogue reader (analysis layer).
    try:
        from . import dialogue as _dialogue
        obj_idxs = {o.get("donor_idx") for o in objs}
        speaking: dict = {}
        for c in _dialogue.scan_dialogue(eb):
            if c.func_tag == TALK_TAG and c.entry_idx in obj_idxs and c.txid is not None:
                speaking.setdefault(c.entry_idx, set()).add(c.txid)
        rep.n_speaking = len(speaking)
        rep.n_dialogue_lines = sum(len(v) for v in speaking.values())
    except Exception:                          # a preview must never crash on an odd field
        pass

    try:
        gw = _eventscan.scan_gateway_entries(data)
        rep.gated_doors = sum(1 for g in gw if g.get("story_gated"))
    except (ValueError, IndexError, KeyError, struct.error):   # a malformed gateway region -> just omit the count
        rep.gated_doors = 0

    # The controlled player character(s). resolve_player_entries returns EVERY DefinePlayerCharacter entry
    # (182 fields define >1). CAUTION: in a multi-PC field the FIRST entry is NOT reliably who you control --
    # the Cargo Ship lists Blank first but you play Zidane; co-actors are also "player characters". So we crown
    # a single-PC field confidently, but for multi-PC we only enumerate + infer: if ANY pc is Zidane you most
    # likely control the Zidane party-leader (the rest are co-actors); ONLY when NO Zidane is defined is the
    # controlled character genuinely non-Zidane (the Treno Dagger/Steiner split). The exact bind is the frontier.
    pents = _eventscan.resolve_player_entries(eb)
    rep.player_models = [(pe, _eventscan._player_model(eb, pe),
                          player_name(_eventscan._player_model(eb, pe))) for pe in pents]
    rep.multi_pc = len(pents) > 1
    models = [m for _, m, _ in rep.player_models if m is not None]
    zidane_present = any(m in _eventscan.ZIDANE_MODELS for m in models)
    if not rep.multi_pc:
        rep.non_zidane = bool(models) and models[0] not in _eventscan.ZIDANE_MODELS
        if rep.non_zidane:
            nm = rep.player_models[0][2]
            rep.notes.append(f"you play as {nm} (non-Zidane) -- fork with --verbatim: it ships the donor player "
                             f"rig + anim packs + the field's own party/cutscene setup whole (proven faithful on "
                             f"Vivi/field 100). --graft-player-funcs would drop {nm}'s funcs (wrong-rig clips)")
    elif models:
        names = ", ".join(n for _, _, n in rep.player_models)
        rep.non_zidane = not zidane_present                  # no Zidane among the PCs -> genuinely non-Zidane control
        if rep.non_zidane:
            # compute WHICH non-Zidane PC binds control (the last DefinePlayerCharacter executed). This is
            # in-game proven for fixed-SID fields (the lane); see controlled_player. A Zidane-present field is
            # NOT computed -- control may route through a party slot to the live leader (left as the hedge below).
            ce, conf = controlled_player(eb)
            rep.controlled_entry, rep.control_confidence = ce, conf
            if ce is not None:
                rep.controlled_name = player_name(_eventscan._player_model(eb, ce))
            hedge = "" if conf == "high" else " (likely -- ambiguous spawn/gating)"
            who = rep.controlled_name or "a non-Zidane character"
            rep.notes.append(f"you control {who}{hedge} -- the last DefinePlayerCharacter executed of the "
                             f"{len(models)} PCs ({names}); the rest are co-defined companions. Fork --verbatim "
                             f"(the player rig + anim packs ship whole). In-game proven on the Treno Dagger/Steiner room.")
        else:
            rep.notes.append(f"the field defines {len(models)} player characters ({names}) -- you most likely "
                             f"control the Zidane party-leader; the rest are co-actors. The exact bind in a fork "
                             f"is untested")

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

    if rep.player_models:
        if rep.multi_pc:
            names = ", ".join(n for _, _, n in rep.player_models)
            if rep.non_zidane and rep.controlled_name:
                q = "" if rep.control_confidence == "high" else "?"
                pc = f"controls {rep.controlled_name}{q} of [{names}]  [MULTI-PC non-Zidane -> --verbatim]"
            else:
                pc = f"{len(rep.player_models)} PCs: {names}  [MULTI-PC; likely Zidane party-leader]"
        else:
            pc = rep.player_models[0][2] + ("  [non-Zidane -> --verbatim]" if rep.non_zidane else "")
        lines.append(f"  Player        : {pc}")
    s = rep.safety
    dirs = f"{len(rep.directors)} director(s)" if rep.directors else "0 directors"
    stack = f", {len(rep.stacked)} multi-instance" if rep.stacked else ""
    lines.append(f"  Roster        : {rep.n_objects} carried object(s) ({rep.n_talkable} NPC, {rep.n_props} prop) "
                 f"- {dirs}{stack}  -> {rep.roster_class.upper()}")
    lines.append(f"  Interactions  : {s.get('clean', 0)} fully interactive, {s.get('init_only', 0)} render-only, "
                 f"{s.get('refuse', 0)} stub  (faithful carry = --graft-player-funcs --carry-text)")
    if rep.n_speaking:
        lines.append(f"  Dialogue      : {rep.n_speaking} NPC(s) speak {rep.n_dialogue_lines} line(s) -- "
                     f"--carry-text (or --verbatim) ships them; else they render WRONG text (lint #5)")
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
    # suggested authoring -- a non-Zidane player forks faithfully only via --verbatim (it ships the donor
    # player rig + anim packs + the field's own party/cutscene setup whole; the graft path drops them).
    fbg = rep.fbg_name or str(rep.field_id)
    lines += ["", "  Suggested authoring:"]
    if rep.non_zidane:
        who = "the non-Zidane PC(s)" if rep.multi_pc else rep.player_models[0][2]
        lines.append(f"    ff9mapkit import {fbg} --verbatim"
                     f"   # ships {who} + rig/anim/party-setup whole (non-Zidane)")
    else:
        lines.append(f"    ff9mapkit import {fbg} --native --graft-player-funcs --carry-text")
    if rep.suggested_scenario is not None:
        nm = _flags.nearest_milestone(rep.suggested_scenario)
        lines += ["    [startup]",
                  f"    scenario = {rep.suggested_scenario}" + (f"   # {nm[1]}" if nm else "")]
    return "\n".join(lines)
