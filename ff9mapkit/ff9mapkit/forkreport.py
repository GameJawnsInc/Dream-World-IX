"""``fork-report`` -- preview, OFFLINE, what a fork of a real FF9 field will and won't reproduce.

The north star is fork FIDELITY (``docs/FORK_FIDELITY.md``): "fork a real field -> does it play identically?"
Before you fork, this answers it. For any real field it reads the compiled ``.eb`` (no game running) and reports:

  * **Roster fidelity** -- how many persistent objects a fork carries, how many are ``Field()``-warp **directors**
    (cutscene actors carried as NPCs -> the rotating-cast mess), and whether content rotates by story beat.
  * **Interaction fidelity** -- per carried NPC, whether its talk handler PORTS (`graft_safety`): ``clean`` = fully
    interactive on the fork, ``init_only`` = renders but its talk is dropped (re-author it), ``refuse`` = a stub.
  * **Story gating** -- story-gated doors + the ScenarioCounter beats the field gates content on.
  * **Items / treasure** -- the item/gil grants + shops the field's ``.eb`` performs (``AddItem`` / ``AddGil``
    / ``Menu(2, id)``). A ``--verbatim`` fork RUNS these (carries them byte-identically); a plain/synthesize
    fork has no item scanner, so it DROPS every treasure + shop. (memory ``project-ff9-items-equipment``.)
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
    # Zidane-present hedge: if a Zidane model is defined among the PCs but the crowned binder is NOT Zidane,
    # control likely routes through the party slot to the Zidane leader (the last-0x2C binder is unreliable
    # here -- the Cargo Ship mispredicts) -> downgrade so no caller treats the pick as certain.
    if conf == "high" and _es._player_model(eb, binder) not in _es.ZIDANE_MODELS \
            and any(_es._player_model(eb, p) in _es.ZIDANE_MODELS for p in pents):
        conf = "low"
    return (binder, conf)


# --- party-membership ops (a verbatim fork RUNS these -> the fork can change your party) ----------------
# CharacterOldIndex (the .eb id space the party ops take; project-ff9-pc-party-system). NOT the GEO model id.
CHAR_OLD_INDEX = {0: "Zidane", 1: "Vivi", 2: "Garnet", 3: "Steiner", 4: "Freya", 5: "Quina", 6: "Eiko",
                  7: "Amarant", 8: "Beatrix", 9: "Cinna", 10: "Marcus", 11: "Blank"}
PARTY_NONE = 0xFFFF                         # the NONE sentinel (slot-clear / add terminator) -- not a real member
REMOVE_PARTY_OP = 0xDD                      # RemoveParty(charIndex)
SET_PARTY_RESERVE_OP = 0xB4                 # SetPartyReserve(mask) -- rebuilds the recruitable roster
JOIN_OP = 0xFE                              # SetCharacterData / JOIN -- a formal recruit (battle+menu init)
PARTY_MENU_OP = 0xB2                        # Party() -- the change-members menu UI
EXPR_STMT_OP = 0x05                         # an expression statement (holds the B_PARTYADD call)
# literal single-char ADD inside an expression: B_CONST(0x7D) <2-byte CharacterOldIndex> B_PARTYADD(0x6D)
_PARTYADD_RE = re.compile(rb"\x7d(..)\x6d", re.DOTALL)


def party_char_name(idx) -> str:
    return CHAR_OLD_INDEX.get(int(idx), "#%d" % int(idx))


def scan_party_ops(eb_bytes) -> dict:
    """The party-membership operations a field performs -- a ``--verbatim`` fork RUNS these, so they preview
    how a fork will change your party. Returns ``{adds, removes}`` (sorted distinct CharacterOldIndex, NONE
    filtered) + the flags ``reset`` (``SetPartyReserve`` -> rebuilds the recruitable roster), ``recruit``
    (``SetCharacterData``/JOIN), ``menu`` (the change-members UI). Heuristic: the literal single-char ADD
    (``B_CONST <id> B_PARTYADD``) is decoded inside expression statements; the statement ops by their arg.
    A field that drives membership from a variable (the common reserve-mask form) is captured by ``reset``."""
    data = bytes(eb_bytes)
    eb = EbScript.from_bytes(data)
    adds, removes = set(), set()
    reset = recruit = menu = False
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == REMOVE_PARTY_OP:
                    if ins.args and not any(ins.arg_is_expr):
                        removes.add(int(ins.args[0]))
                elif ins.op == SET_PARTY_RESERVE_OP:
                    reset = True
                elif ins.op == JOIN_OP:
                    recruit = True
                elif ins.op == PARTY_MENU_OP:
                    menu = True
                elif ins.op == EXPR_STMT_OP:
                    for h in _PARTYADD_RE.findall(data[ins.off:ins.end]):
                        adds.add(struct.unpack("<H", h)[0])
    adds.discard(PARTY_NONE)
    removes.discard(PARTY_NONE)
    return {"adds": sorted(adds), "removes": sorted(removes), "reset": reset, "recruit": recruit, "menu": menu}


# --- item / treasure / shop ops -----------------------------------------------------------------------
# These live WHOLLY in the field `.eb`, so a `--verbatim` fork RUNS them (carries them byte-identically) but
# a plain/synthesize fork DROPS them -- eventscan has no AddItem scanner, and there is no shop authoring. A
# shop's `Menu(2, id)` carries too, but its STOCK comes from the base `ShopItems.csv` (a fork is parasitic on
# it -- it can't change the inventory). The kit catalogs only the regular 0-255 item space, so a key/card id
# gets a generic label. (memory project-ff9-items-equipment; opcodes AddItem/AddGil/Menu in eb/opcodes.py.)
ADD_ITEM_OP = 0x48         # AddItem(item_id, count) -- the real-chest / reward opcode (item_id 2B, count 1B)
REMOVE_ITEM_OP = 0x49      # RemoveItem(item_id, count)
ADD_GIL_OP = 0xCE          # AddGil(amount) -- treasure gil (amount 3B, unsigned)
REMOVE_GIL_OP = 0xCF       # RemoveGil(amount)
MENU_OP = 0x75             # Menu(menu_id, sub_id); menu_id 2 = SHOP (sub_id = shop id). 1=name 4=save 5=chocograph
SHOP_MENU_ID = 2
NO_ITEM = 255              # the RegularItem empty sentinel -- not a real grant (filtered, like PARTY_NONE)
GIL_CAP = 9_999_999        # the FF9 party-gil ceiling; a larger literal AddGil is a scripted sentinel, not treasure
# The event `AddItem` operand is a POOL-ENCODED item id, classified by `id % 1000` (ff9item.FF9Item_Add_Generic):
# 0-255 = regular item, 256-511 = important/key item, 512-611 = Tetra Master card, >= 612 = engine NO-OP (inert).
# A plain regular item (the normal chest/reward) has raw id 0-255 (pool 0), so `items.name_of` names it directly;
# higher pools (e.g. 31000, %1000=0) reference extended/modded regular ids the kit doesn't name. (project-ff9-items-equipment.)
POOL = 1000
REGULAR_MAX = 256          # id % 1000 < 256          -> regular item
IMPORTANT_MAX = 512        # 256 <= id % 1000 < 512   -> important/key item
CARD_MAX = 612             # 512 <= id % 1000 < 612   -> card;  id % 1000 >= 612 -> inert (no grant)


def item_inert(item_id) -> bool:
    """True if the engine treats this ``AddItem`` id as a NO-OP (``id % 1000 >= 612`` falls in no item pool, so
    ``FF9Item_Add_Generic`` returns 0). Such ids grant nothing -> excluded from the preview's give list."""
    return int(item_id) % POOL >= CARD_MAX


def item_label(item_id) -> str:
    """A friendly label for an ``AddItem`` id, faithful to the engine's ``id % 1000`` pool decode: the
    ``RegularItem`` name for a plain 0-255 id (the normal treasure case), else a classified-but-unnamed
    ``item #N`` (extended/modded regular) / ``key item #N`` / ``card #N`` (the kit catalogs only the regular
    0-255 space -- project-ff9-items-equipment)."""
    iid = int(item_id)
    if 0 <= iid < REGULAR_MAX:                    # pool 0: the raw id IS the RegularItem id (names directly)
        from . import items as _items
        nm = _items.name_of(iid)
        if nm is not None:
            return nm
    m = iid % POOL
    if m < REGULAR_MAX:
        return "item #%d" % iid                   # a regular item in a higher pool (extended / modded id space)
    if m < IMPORTANT_MAX:
        return "key item #%d" % (m - REGULAR_MAX)  # important/key item (a separate space the kit doesn't name)
    if m < CARD_MAX:
        return "card #%d" % (m - IMPORTANT_MAX)    # Tetra Master card
    return "item #%d (inert)" % iid               # id % 1000 >= 612 -> engine no-op (shouldn't reach gives)


def scan_item_ops(eb_bytes) -> dict:
    """The item / gil / shop operations a field performs -- a ``--verbatim`` fork RUNS these, so they preview
    the treasure + shops a fork reproduces (a plain/synthesize fork has NO item scanner, so it DROPS them all).
    Returns ``{gives, gil_max, gil_any, shops, removes, var_give}``: ``gives`` = sorted distinct
    ``(item_id, count)`` literal ``AddItem`` grants (NoItem filtered; ``count`` = the MAX single-grant amount,
    ``None`` when computed); ``gil_max`` = the largest single PLAUSIBLE literal ``AddGil`` (<= ``GIL_CAP``);
    ``gil_any`` = any ``AddGil`` at all (literal or computed); ``shops`` = sorted distinct ``Menu(2, id)`` shop
    ids; ``removes`` = ``RemoveItem`` op count; ``var_give`` = any ``AddItem`` with a COMPUTED id; ``var_shop`` =
    any ``Menu(2, <computed>)`` (a story-gated shop whose id is picked at runtime) -- both un-previewable.

    IMPORTANT -- DON'T SUM across paths: a field's ``.eb`` runs many MUTUALLY-EXCLUSIVE story-gated branches,
    so the same chest's ``AddItem``/``AddGil`` recurs across them. We report DISTINCT items (max single-grant
    count, not a sum) and gil as a per-grant max -- summing wildly overcounts (field 854 grants Ether x1 on two
    parallel paths, not x2; its ~16.7M-gil literal is a scripted sentinel above the 9,999,999 cap, so it is
    suppressed from ``gil_max`` but still flips ``gil_any``)."""
    data = bytes(eb_bytes)
    eb = EbScript.from_bytes(data)
    gives: dict = {}           # item_id -> max single-AddItem count (None once any occurrence has a computed count)
    gil_max = 0                # largest single PLAUSIBLE literal AddGil (<= GIL_CAP)
    gil_any = False            # any AddGil at all (literal or computed)
    shops: set = set()
    removes = 0
    var_give = False
    var_shop = False
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == ADD_ITEM_OP:
                    iid = ins.imm(0)
                    if iid is None:                       # a computed item id -> can't say which item
                        var_give = True
                        continue
                    if iid == NO_ITEM or item_inert(iid):  # NoItem / engine no-op (id % 1000 >= 612) -> no grant
                        continue
                    cnt = ins.imm(1)
                    prev = gives.get(iid, 0)
                    gives[iid] = None if (prev is None or cnt is None) else max(prev, cnt)
                elif ins.op == REMOVE_ITEM_OP:
                    removes += 1
                elif ins.op == ADD_GIL_OP:
                    gil_any = True
                    amt = ins.imm(0)
                    if amt is not None and amt <= GIL_CAP:
                        gil_max = max(gil_max, amt)
                elif ins.op == MENU_OP and ins.imm(0) == SHOP_MENU_ID:
                    sid = ins.imm(1)
                    if sid is not None:
                        shops.add(sid)
                    else:                                 # a story-gated shop (computed sub_id) -> can't name the id
                        var_shop = True
    return {"gives": sorted(gives.items()), "gil_max": gil_max, "gil_any": gil_any,
            "shops": sorted(shops), "removes": removes, "var_give": var_give, "var_shop": var_shop}


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
    swap_gesture_count: int = 0                           # scripted player GESTURES that would glitch on a --swap-player
    cam_pitch: float | None = None                       # camera downward pitch (deg); None = not read (.eb-only / no install)
    cam_fov: float | None = None                         # horizontal FOV (deg) -> close/medium/wide feel
    cam_scrolling: bool = False                           # a wide/scrolling field (range past one 384x448 screen)
    cam_count: int = 0                                    # number of cameras (> 1 = a multi-camera field)
    party_adds: list = _dc_field(default_factory=list)    # distinct CharacterOldIndex names the field ADDS (B_PARTYADD)
    party_removes: list = _dc_field(default_factory=list)  # distinct names it REMOVES (RemoveParty)
    party_reset: bool = False                            # SetPartyReserve -- rebuilds the recruitable roster (story reset)
    party_recruit: bool = False                          # SetCharacterData/JOIN -- a formal recruit (battle+menu init)
    party_menu: bool = False                             # opens the change-members MENU (moogle/save-point UI)
    item_gives: list = _dc_field(default_factory=list)    # [(item_id, count)] distinct AddItem grants (count = max single)
    item_gil_max: int = 0                                # largest single PLAUSIBLE literal AddGil (<= GIL_CAP)
    item_gil_any: bool = False                           # any AddGil at all (literal or computed) -> treasure gil
    item_shops: list = _dc_field(default_factory=list)    # distinct Menu(2, id) shop ids the field opens
    item_removes: int = 0                                # RemoveItem op count
    item_var_give: bool = False                          # an AddItem with a COMPUTED id (un-previewable)
    item_var_shop: bool = False                          # a Menu(2, <computed>) -- a story-gated shop (id un-previewable)
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
    from .extract import EventBundle, ID_TO_FBG, ID_TO_EVT, field_camera_info  # lazy: UnityPy only when used
    b = bundle or EventBundle(game)
    data = b.eb_for_id(field_id)
    fbg = ID_TO_FBG.get(field_id, "")
    rep = analyze_eb(data, field_id=field_id, fbg_name=fbg, event_name=ID_TO_EVT.get(field_id, ""))
    # the Camera axis lives in the scene .bgs (not the .eb), so it needs the install -- populate it here,
    # NOT in the pure analyze_eb (which stays .eb-only + fixture-testable). None -> the line is omitted.
    ci = field_camera_info(fbg, game=game) if fbg else None
    if ci:
        rep.cam_pitch, rep.cam_fov = ci["pitch"], ci["fov"]
        rep.cam_scrolling, rep.cam_count = ci["scrolling"], ci["count"]
    return rep


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
    # swap-friendliness: how a `--swap-player` fares -- the scripted gestures on the entr(ies) the swap targets
    # (the controlled-leader model). 0 = a clean free-roam swap; >0 = a cutscene field where those gestures
    # glitch on the new rig (only movement clips are swapped). Reuses the same logic the swap + CLI WARN use.
    from . import playerswap as _playerswap
    try:
        rep.swap_gesture_count = _playerswap.scripted_gesture_ops(data)
    except Exception:                                    # never let the preview crash on a swap-edge field
        rep.swap_gesture_count = 0
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

    # Party-membership ops the field runs (a verbatim fork executes them -> the fork changes your party).
    party = scan_party_ops(data)
    rep.party_adds = [party_char_name(i) for i in party["adds"]]
    rep.party_removes = [party_char_name(i) for i in party["removes"]]
    rep.party_reset, rep.party_recruit, rep.party_menu = party["reset"], party["recruit"], party["menu"]

    # Item / treasure / shop ops the field runs (a verbatim fork carries them; a plain/synthesize fork DROPS
    # them -- no item scanner). The shop STOCK is parasitic on the base ShopItems.csv (a fork can't change it).
    itm = scan_item_ops(data)
    rep.item_gives = itm["gives"]
    rep.item_gil_max = itm["gil_max"]
    rep.item_gil_any = itm["gil_any"]
    rep.item_shops = itm["shops"]
    rep.item_removes = itm["removes"]
    rep.item_var_give = itm["var_give"]
    rep.item_var_shop = itm["var_shop"]

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


def _party_line(rep: ForkReport) -> str:
    """The 'Party' axis: what a verbatim fork will do to your party. Empty when the field is party-neutral."""
    if not (rep.party_adds or rep.party_removes or rep.party_reset or rep.party_recruit or rep.party_menu):
        return ""
    bits = []
    if rep.party_adds:
        shown = ", ".join(rep.party_adds[:6]) + (f" +{len(rep.party_adds) - 6}" if len(rep.party_adds) > 6 else "")
        bits.append(f"adds {shown}")
    if rep.party_reset:
        bits.append("rebuilds the roster (story reset)" if rep.party_removes else "sets the recruitable roster")
    elif rep.party_removes:
        shown = ", ".join(rep.party_removes[:6]) + (f" +{len(rep.party_removes) - 6}" if len(rep.party_removes) > 6 else "")
        bits.append(f"removes {shown}")
    if rep.party_menu:
        bits.append("opens the change-members menu")
    tail = "  (a --verbatim fork RUNS this; a plain fork inherits your current party)"
    return f"  Party         : {'; '.join(bits)}{tail}"


def _items_line(rep: ForkReport) -> str:
    """The 'Items' axis: the treasure / gil / shops the field grants. A --verbatim fork RUNS these (carries
    them byte-identically); a plain/synthesize fork DROPS them (no item scanner). Empty when nothing is granted."""
    if not (rep.item_gives or rep.item_var_give or rep.item_gil_any or rep.item_shops or rep.item_var_shop):
        return ""
    bits = []
    if rep.item_gives:
        shown = ", ".join(item_label(i) + (" x%d" % c if c not in (None, 1) else "")
                          for i, c in rep.item_gives[:6])
        more = f" +{len(rep.item_gives) - 6}" if len(rep.item_gives) > 6 else ""
        bits.append(f"grants {shown}{more}")
    if rep.item_var_give:
        bits.append("computed-id item(s)")
    if rep.item_gil_max:
        bits.append(f"up to {rep.item_gil_max} gil")
    elif rep.item_gil_any:
        bits.append("gil (scripted)")
    if rep.item_shops:
        ids = ", ".join("#%d" % s for s in rep.item_shops[:6])
        more = f" +{len(rep.item_shops) - 6}" if len(rep.item_shops) > 6 else ""
        bits.append(f"opens shop(s) {ids}{more}" + (" + a story-gated shop" if rep.item_var_shop else ""))
    elif rep.item_var_shop:
        bits.append("opens a story-gated shop")
    tail = "  (--verbatim carries these; a plain/synthesize fork DROPS them"
    tail += "; shop stock = base ShopItems.csv)" if (rep.item_shops or rep.item_var_shop) else ")"
    return f"  Items         : {'; '.join(bits)}{tail}"


def _camera_line(rep: ForkReport) -> str:
    """The Camera axis: a close/medium/wide feel + the raw pitch/FOV (the lens the fork plays through).
    Empty when the camera wasn't read (the pure .eb-only path / no install) -- so the report degrades."""
    if rep.cam_pitch is None:
        return ""
    fov = rep.cam_fov
    if fov is None:
        feel = "unknown-fov"
    elif fov < 35:
        feel = "close"               # an intimate room (e.g. ac_rst_x ~29.5) -- a good --swap/demo test room
    elif fov < 50:
        feel = "medium"
    else:
        feel = "wide"                # an establishing/scrolling shot (e.g. the Hangar ~61) -- details are tiny
    bits = ([f"FOV {fov:g} deg"] if fov is not None else []) + [f"pitch {rep.cam_pitch:g} deg"]
    extra = []
    if rep.cam_scrolling:
        extra.append("scrolling")
    if rep.cam_count > 1:
        extra.append(f"{rep.cam_count} cameras")
    tail = ("; " + ", ".join(extra)) if extra else ""
    return f"  Camera        : {feel} ({', '.join(bits)}){tail}"


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
        # swap-friendliness tag: is this a good `--swap-player` target? (the gestures glitch on a cutscene field)
        swap = ("swap-clean" if rep.swap_gesture_count == 0
                else f"swap: {rep.swap_gesture_count} gesture(s) glitch")
        lines.append(f"  Player        : {pc}  ({swap})")
    cam_line = _camera_line(rep)
    if cam_line:
        lines.append(cam_line)
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
    party_line = _party_line(rep)
    if party_line:
        lines.append(party_line)
    items_line = _items_line(rep)
    if items_line:
        lines.append(items_line)
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
