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

import bisect as _bisect
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
# control-flow opcodes for the beat-roster walk: an EXPR (0x05) ScenarioCounter comparison drives a
# conditional jump -- 0x02 skips its body when the condition is FALSE, 0x03 skips when TRUE. 0x01 is the
# undocumented UNCONDITIONAL jump (CLAUDE.md §7); it does NOT gate its body, so the walk FOLLOWS it (which
# is what correctly steps over an if/else's else-branch) rather than treating it as a guard.
JMP_UNCOND = 0x01
JMP_FALSE = 0x02
JMP_TRUE = 0x03


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
    n_interactive: int = 0                     # talkable NPCs whose talk grafts CLEAN (keep interactions; props excluded)
    n_speaking: int = 0                        # carried NPCs whose tag-3 talk SHOWS dialogue (need --carry-text)
    n_dialogue_lines: int = 0                  # total distinct talk txids those NPCs show
    directors: list = _dc_field(default_factory=list)     # donor_idx of carried objects that warp/switch in LOOP
    stacked: list = _dc_field(default_factory=list)       # donor_idx of multi-instance (one-spot stacking) objects
    safety: dict = _dc_field(default_factory=dict)        # {clean: n, init_only: n, refuse: n}
    gated_doors: int = 0
    sc_gates: list = _dc_field(default_factory=list)      # [(value, (milestone_value, beat))] sorted
    suggested_scenario: int | None = None
    roster_class: str = "static-roster"        # "static-roster" | "story-event"
    beat_roster: list = _dc_field(default_factory=list)   # [(beat, milestone, [(slot, model_name, is_director)])]
    #   per ScenarioCounter beat (incl. 0), which carried objects the director actually spawns -- the
    #   #13 "rotating cast" preview (empty unless the roster genuinely VARIES across beats)
    player_models: list = _dc_field(default_factory=list)  # [(entry_index, model_id, name)] -- the defined PC(s)
    multi_pc: bool = False                                # the field defines >1 DefinePlayerCharacter
    non_zidane: bool = False                              # the controlled player isn't Zidane -> --verbatim is the faithful mode
    controlled_entry: int | None = None                  # the entry the engine BINDS control to (multi-PC; controlled_player)
    controlled_name: str = ""                            # its character name
    control_confidence: str = "none"                     # 'high' | 'low' | 'none' (binder ambiguity)
    swap_gesture_count: int = 0                           # scripted player GESTURES that would glitch on a --swap-player
    arrival_spots: int = 0                                # distinct per-ENTRANCE player spawn points (#9); >1 = a synth
    #   fork collapses them to one [player] spawn (loses per-door arrival) -- --verbatim ships the real table
    cam_pitch: float | None = None                       # camera downward pitch (deg); None = not read (.eb-only / no install)
    cam_fov: float | None = None                         # horizontal FOV (deg) -> close/medium/wide feel
    cam_scrolling: bool = False                           # a wide/scrolling field (range past one 384x448 screen)
    cam_count: int = 0                                    # number of cameras (> 1 = a multi-camera field)
    cam_range_h: int = 0                                  # camera visible height (screen units); the "how far back" signal
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
    lost_on_mint: list = _dc_field(default_factory=list)  # [(label, detail)] -- USER-VISIBLE engine behaviors
    #   keyed on the real fldMapNo that a fork loses on its custom id (walkmesh hotfix / narrow-map letterbox /
    #   Chocobo HUD / intro FMV). The "impossible" axis of the taxonomy, per field (idgated.lost_on_mint).
    area_title: tuple = None                              # (startOvr, endOvr) if the field has an area-title
    #   CARD -- donor identity SHOWN on --verbatim, dropped/auto-hidden on a synth (BG-borrow/native) fork
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


# --- roster by beat (#13): which carried objects the director actually spawns at each ScenarioCounter beat -
# A story-event field gates its InitObject calls on ScenarioCounter (the "rotating cast"). To preview the cast
# at a given beat WITHOUT deploying, we symbolically walk Main_Init at that beat: evaluate only the
# ScenarioCounter comparisons that drive conditional jumps (fall through every OTHER conditional -- flag gates
# are assumed satisfied), follow unconditional jumps, and collect the InitObject slots actually reached. This
# correctly handles if/else, nesting, and the `if(SC==BEAT){spawn}` dispatch chain (vs naive range-containment).

def _sc_cond(data, off):
    """If the EXPR statement at ``off`` is a SIMPLE ScenarioCounter comparison (``05 DC 00 7D <u16> <cmp> 7F``),
    return ``(cmp_op, const)``; else ``None`` (compound/other exprs are treated as non-SC -> fall through)."""
    if off + 7 >= len(data) or data[off] != EXPR_STMT_OP:
        return None
    if data[off + 1] != 0xDC or data[off + 2] != 0x00 or data[off + 3] != 0x7D:
        return None
    cmp = data[off + 6]
    if cmp not in _CMP_OPS or data[off + 7] != 0x7F:
        return None
    return (cmp, data[off + 4] | (data[off + 5] << 8))


def _eval_cmp(sc, cond) -> bool:
    """Does ``ScenarioCounter == sc`` satisfy the comparison ``cond = (cmp_op, const)``?"""
    cmp, const = cond
    return {0x20: sc == const, 0x18: sc < const, 0x19: sc > const,
            0x1A: sc <= const, 0x1B: sc >= const}.get(cmp, False)


def _jump_target(ins) -> int:
    """Absolute byte target of a jump instr (operand is a signed i16 skip distance from the instr end)."""
    raw = ins.imm(0)
    if raw is None:
        return -1
    return ins.end + (raw - 0x10000 if raw >= 0x8000 else raw)


def _spawned_slots(instrs, sc_conds, sc) -> list:
    """Symbolically execute the Main_Init instr list at ``ScenarioCounter == sc``: take a conditional jump
    only when its driving ScenarioCounter comparison is known (else fall through = run the guarded body),
    follow forward jumps (incl. the unconditional 0x01 that steps over an if's else-branch), and return the
    ordered InitObject slots reached. A FORWARD jump lands on the first instr at-or-after the target (so a
    jump to the function end correctly terminates); a BACKWARD jump is not followed (loop guard). Bounded by
    a visited set + step cap."""
    offs = [ins.off for ins in instrs]             # ascending (Main_Init in order)
    n = len(instrs)

    def _forward(i, ins):                           # next index for a jump from instr i, or fall-through
        tgt = _jump_target(ins)
        k = _bisect.bisect_left(offs, tgt) if tgt >= 0 else i + 1
        return k if k > i else i + 1               # forward only; backward/unknown -> fall through

    out, visited, last, i, steps = [], set(), None, 0, 0
    while 0 <= i < n and steps < 20000:
        steps += 1
        if i in visited:
            break
        visited.add(i)
        ins = instrs[i]
        op = ins.op
        if op == EXPR_STMT_OP:
            last = sc_conds.get(ins.off)           # the SC condition for an immediately-following jump (or None)
            i += 1
            continue
        if op in (JMP_FALSE, JMP_TRUE):
            take = None
            if last is not None:                   # known SC condition -> decide the jump deterministically
                base = _eval_cmp(sc, last)
                take = (not base) if op == JMP_FALSE else base
            last = None
            i = _forward(i, ins) if take else i + 1   # take -> skip guarded body; else/unknown -> run it
            continue
        if op == JMP_UNCOND:                        # follow forward (steps over an if's else-branch)
            last = None
            i = _forward(i, ins)
            continue
        last = None
        if op == INITOBJ_OP:
            s = ins.imm(0)
            if s is not None:
                out.append(int(s))
        i += 1
    return out


def _roster_entry_name(eb, slot):
    """The model name for an InitObject slot (incl. cutscene actors ``scan_objects`` skips), or ``None`` for
    the player / party (excluded from the roster table -- the cast of interest is the NPCs/actors)."""
    from . import eventscan as _eventscan
    from ._modeldb import MODELS
    try:
        e = eb.entry(slot)
    except (IndexError, AttributeError):
        return None
    if e is None or e.empty:
        return None
    fi = e.func_by_tag(0)
    if fi is None:
        return None
    try:
        rd = _eventscan._read_object_init(eb, fi)
    except Exception:
        return None
    m = rd.get("model")
    if m is None or rd.get("player"):
        return None
    name = MODELS.get(m)
    if name and name.startswith("GEO_MAIN"):       # the party rig, not set-dressing
        return None
    return name or f"model {m}"


def roster_by_beat(eb, data, director_slots) -> list:
    """For each ScenarioCounter beat the field gates on (plus 0 = the scenario-zero baseline), the set of
    carried objects the director SPAWNS at that beat. Returns ``[(beat, milestone, [(slot, name, is_dir)])]``,
    or ``[]`` when the field has no gates OR the roster does not actually vary across beats (then the flat
    ``sc_gates`` line already says it all).

    APPROXIMATE (a guide, confirm in-game): it evaluates only SIMPLE ScenarioCounter comparisons that drive a
    jump; flag gates are assumed satisfied (so flag-gated actors are over-included), compound/looping
    ScenarioCounter logic is run once (backward jumps fall through rather than iterate), and a director's OWN
    per-beat model swap inside its LOOP is not traced (only WHICH objects spawn in Main_Init)."""
    try:
        mi = eb.entry(0).func_by_tag(0)
    except (IndexError, AttributeError):
        return []
    if mi is None:
        return []
    instrs = list(eb.instrs(mi))
    sc_conds = {ins.off: c for ins in instrs if ins.op == EXPR_STMT_OP
                for c in (_sc_cond(data, ins.off),) if c is not None}
    gates = scenario_gates(data)
    if not gates:
        return []
    table = []
    for beat in sorted(set(gates) | {0}):
        seen, entries = set(), []
        for s in _spawned_slots(instrs, sc_conds, beat):
            if s in seen:
                continue
            nm = _roster_entry_name(eb, s)
            if nm is None:
                continue
            seen.add(s)
            entries.append((s, nm, s in director_slots))
        table.append((beat, _flags.nearest_milestone(beat), entries))
    # only meaningful if the cast genuinely rotates -- else the flat sc_gates line suffices. Compare by
    # (slot, model) so a same-slot model swap also counts as variation (not just add/remove of slots).
    rosters = {frozenset((s, n) for s, n, _d in row[2]) for row in table}
    return table if len(rosters) >= 2 else []


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
        # several fields can SHARE one FBG folder (the same room at different story beats), so listing folders
        # would just repeat -- list the field IDS, which is exactly what disambiguates them.
        ex = ", ".join(str(f) for f in hits[:8])
        raise ValueError(f"{token!r} matches {len(hits)} fields (ids {ex}{'...' if len(hits) > 8 else ''}) "
                         f"-- pass the field id (a shared FBG folder maps to several fields)")
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
        rep.cam_range_h = ci.get("range_h", 0)
    # the area-title CARD is keyed on the scene name (manifest in resources.assets), so it needs the install too.
    # ID_TO_FBG is lowercase; the manifest keys are the real (UPPER) scene names -> match on upper.
    if fbg:
        from . import areatitle as _at
        rep.area_title = _at.title_range(fbg.upper(), game=game)
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
            if o.get("graft_safety") == "clean":
                rep.n_interactive += 1            # clean-graft NPCs (those that KEEP their talk) -- props excluded
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
    # #9 per-door spawn: a field that positions the player by ENTRANCE (reads D8:2, branches to N spots). A
    # synth fork re-authors a single [player] spawn -> collapses the table; --verbatim ships the real Init.
    try:
        rep.arrival_spots = _eventscan.scan_player_arrivals(eb)["distinct"]
    except Exception:                                    # a preview must never crash on an odd field
        rep.arrival_spots = 0
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
    # #13 rotating-cast preview: which carried objects the director spawns at each beat (empty unless it varies)
    try:
        rep.beat_roster = roster_by_beat(eb, data, set(rep.directors))
    except Exception:                          # a preview must never crash on an odd field
        rep.beat_roster = []

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
    # LOST ON A MINT: every user-visible engine behavior keyed on the real fldMapNo a fork loses on its custom
    # id (walkmesh hotfix / narrow-map letterbox / Chocobo HUD / intro FMV) -- the taxonomy's "impossible" axis,
    # per field. Pure baked data (no install), so it's fine on the install-free analyze_eb path.
    from . import idgated as _idg
    rep.lost_on_mint = _idg.lost_on_mint(field_id)
    return rep


# --- rendering --------------------------------------------------------------------------------------
def _verdict_line(rep: ForkReport) -> str:
    if rep.roster_class == "static-roster":
        head = "a CLEAN static-roster field -- a native fork renders the cast faithfully"
    else:
        head = "a STORY-EVENT field -- a fork is a high-fidelity diorama, not a faithful slice (rotating cast / cutscene actors)"
    if rep.n_talkable:
        # numerator = CLEAN NPCs only (n_interactive), never the props-inclusive safety['clean']; the
        # "render-only" tail only when there's a real render-only NPC remainder (not a refused prop).
        inter = f"{rep.n_interactive} of {rep.n_talkable} NPC(s) keep their interactions"
        if rep.n_talkable > rep.n_interactive:
            inter += "; the rest render-only (re-author their dialogue)"
    else:
        inter = "no talkable NPCs"
    parts = [f"{head}; {inter}."]
    # The synthesized BOTTOM LINE across every axis: which fork MODE, and why. --verbatim is the faithful mode
    # whenever the field has story-bound state a synth rebuild drops (gated cast/logic, a non-Zidane player,
    # party/item grants, per-door arrival); otherwise --native is a clean diorama.
    why = []
    if rep.roster_class != "static-roster" or rep.sc_gates:
        why.append("story-gated cast/logic")
    if rep.non_zidane:
        why.append("non-Zidane player")
    if rep.party_adds or rep.party_removes or rep.party_reset or rep.party_recruit:
        why.append("party changes")
    if rep.item_gives or rep.item_var_give or rep.item_gil_any or rep.item_shops or rep.item_var_shop:
        why.append("item/shop grants")
    if rep.arrival_spots > 1:
        why.append("per-door arrival")
    if why:
        reco = f"--verbatim (carries {', '.join(why[:3])}{'...' if len(why) > 3 else ''})"
        if rep.sc_gates or rep.roster_class != "static-roster":
            reco += " + a [startup] beat (else it boots scenario-zero)"
    else:
        reco = "--native (a faithful diorama; nothing story-bound to carry)"
    parts.append(f"Recommended: {reco}.")
    # The lost-on-a-mint steer -- only the NON-reproduced losses are fork-in-place-worthy ("auto-reproduced on
    # fork" via a toggle prepend, or "reproduced by the engine fork-donor remap", both mean it's NOT lost).
    losses = [lbl for lbl, det in rep.lost_on_mint if "reproduced" not in det]
    if losses:
        parts.append(f"Loses {', '.join(losses)} on a custom id -- fork IN-PLACE on the real id to keep (see Lost on mint).")
    return " ".join(parts)


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
    elif fov < 10:
        feel = "distant"             # a sub-10 "FOV" is a far telephoto (FF9 projection is orthographic-like,
                                     # so a tiny FOV = zoomed FAR OUT, model is a speck) -- NOT an intimate room
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


def _entry_settle_line(rep: ForkReport) -> str:
    """The entry-camera-settle advisory (coarse flag). The engine's smooth-camera follower eases onto the
    spawn on a warp-in; a SYNTH fork (--native/BG-borrow) reveals immediately, so on a SCROLLING field that
    ease is VISIBLE as a drift (worst on an F6/hard warp; the bigger the spawn-to-centre delta, the longer it
    drifts). Empty for a fixed-camera field (no center-on-player motion) or when the camera wasn't read. A
    --verbatim fork carries the donor's real entry sequence, which hides it. (content/entry_settle.py.)"""
    if not rep.cam_scrolling:
        return ""
    return ("  Entry settle  : scrolling camera -> a SYNTH (--native/BG-borrow) fork may show the camera ease "
            "onto the spawn on warp-in (worst on an F6/hard warp; a big spawn-to-centre delta drifts longer). "
            "Add `[camera] entry_settle = 45` to hide it behind the load fade; a --verbatim fork carries the "
            "real entry sequence and doesn't need it.")


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
    if rep.arrival_spots > 1:
        lines.append(f"  Arrival       : {rep.arrival_spots} per-door spawn points (#9) -- a SYNTH fork uses one "
                     f"[player] spawn (you arrive at the same spot via every door); --verbatim ships the real table")
    cam_line = _camera_line(rep)
    if cam_line:
        lines.append(cam_line)
    settle_line = _entry_settle_line(rep)
    if settle_line:
        lines.append(settle_line)
    if rep.area_title:
        a, b = rep.area_title
        lines.append(f"  Area title    : this field shows an area-title CARD (overlays {a}-{b}) -- donor identity: "
                     f"kept on --verbatim (real show+fade), auto-hidden on a synth/BG-borrow fork (DROP on reuse)")
    if rep.lost_on_mint:
        lines.append("  Lost on mint  : engine behavior(s) keyed on the real field id a fork loses on a custom id "
                     "(fork IN-PLACE to keep, unless noted auto-reproduced):")
        for label, detail in rep.lost_on_mint:
            lines.append(f"      - {label}: {detail}")
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
    if rep.beat_roster:
        lines.append("  Roster by beat: which carried NPCs/actors the director spawns at each beat "
                     "(set [startup] scenario to one):")
        has_dir = False
        for bv, nm, entries in rep.beat_roster:
            label = (nm[1] if nm else "?")
            if entries:
                names = ", ".join((n[4:] if n.startswith("GEO_") else n) + ("*" if d else "")
                                  for _s, n, d in entries)
                has_dir = has_dir or any(d for _s, _n, d in entries)
            else:
                names = "(no carried cast)"
            base = "  <- scenario-zero baseline" if bv == 0 else ""
            lines.append(f"      {bv:>6}  {label:<20}: {names}{base}")
        lines.append("      (approximate -- a guide, confirm in-game: flag-gated content is assumed present; "
                     "compound/looping ScenarioCounter logic is run once)")
        if has_dir:
            lines.append("      (* = a director; its OWN model may further vary by beat inside its loop -- not traced)")
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


# ============================================================================================
# Room finder -- sweep ALL forkable fields for the best swap/demo TEST ROOMS.
#
# A "good room" = a place to walk as a swapped character (`--swap-player`) or stage a visual test
# where the model's DETAIL is actually visible. Grounded in a 676-field calibration sweep:
# FOV ALONE is not a detail proxy (FF9's projection is orthographic-like, k~0.93 -- a tiny "FOV" is
# zoomed FAR OUT, not close), so a room is the AND of (single-PC) + (swap-clean) + a CLOSE 3/4
# single-screen camera = bounded FOV AND a 3/4 pitch band AND a near-one-screen RANGE AND not a
# `_CS_` cutscene-staging field. Two-phase for speed (~45s): a cheap .eb-only prefilter, then the
# expensive per-field camera read only on the survivors. (memory project-ff9-non-zidane-donors.)
# ============================================================================================
_REAL_FBG = re.compile(r"^fbg_n\d+_")

# Calibration constants (validated against the sweep; the proven anchor is field 1200 ac_rst_x,
# FOV 29.5 / pitch 28.8 / range_h 336). Good rooms cluster FOV ~22-42, pitch ~8-48, range_h 224-368.
ROOM_MIN_FOV = 10.0       # below this is a degenerate telephoto/orthographic camera (model is a speck), not a room
ROOM_MAX_FOV = 45.0       # above this is a wide establishing lens
ROOM_MIN_PITCH = 6.0      # below this is a flat/side-on view (no 3/4 detail; the proven anchors sit >= 8.7)
ROOM_MAX_PITCH = 48.0     # above this is near-top-down -- you see the head, not the face/body
ROOM_MAX_RANGE_H = 420    # camera visible height; intimate rooms sit 224-368, distant/wide shots 448-592
ROOM_IDEAL_FOV = 30.0     # the proven anchor sits here
ROOM_IDEAL_PITCH = 28.0   # ...and pitch ~28 -- the classic 3/4 detail view
ROOM_SCROLL_DEMERIT = 15.0  # a wide-pan field is not a tight single-screen stage (rank down, don't exclude)


def _is_real_fbg(fbg: str) -> bool:
    """True for a genuine field background name (fbg_nNN_...) -- filters placeholders like 'invalidfieldmapid'."""
    return bool(_REAL_FBG.match(fbg or ""))


def room_score(rep: ForkReport, *, max_fov: float = ROOM_MAX_FOV) -> float | None:
    """A swap/demo test-room rank key (LOWER = tighter on the model), or None if ``rep`` fails a HARD
    filter. Assumes ``rep`` already passed the .eb prefilter (single-PC + swap-clean) and has its camera
    fields populated. FOV alone is not a detail proxy, so this ANDs FOV + pitch + the visible range + a
    cutscene-name guard -- the combination the calibration sweep validated."""
    fov, pitch, rh = rep.cam_fov, rep.cam_pitch, rep.cam_range_h
    if fov is None or pitch is None:
        return None                                       # no readable camera -> un-rankable
    if "_CS_" in (rep.event_name or "").upper():
        return None                                       # a cutscene-staging field, definitionally not a room
    if not (ROOM_MIN_FOV <= fov <= max_fov):
        return None                                       # degenerate telephoto / wide establishing lens
    if not (ROOM_MIN_PITCH <= pitch <= ROOM_MAX_PITCH):
        return None                                       # flat/side-on (no 3/4 detail) OR near-top-down
    if rh and rh > ROOM_MAX_RANGE_H:
        return None                                       # camera too far back (a distant/wide view)
    key = abs(fov - ROOM_IDEAL_FOV) + 0.3 * abs(pitch - ROOM_IDEAL_PITCH)
    if rep.cam_scrolling:
        key += ROOM_SCROLL_DEMERIT
    return key


@dataclass
class RoomSweep:
    rooms: list = _dc_field(default_factory=list)         # list[ForkReport], best-first
    scanned: int = 0                                      # real fields examined (cheap .eb pass)
    swap_clean: int = 0                                   # passed the single-PC + swap-clean prefilter


def find_rooms(*, game=None, limit: int = 20, max_fov: float = ROOM_MAX_FOV,
               ids=None, bundle=None) -> RoomSweep:
    """Sweep every forkable field and return the best swap/demo TEST ROOMS, best-first. Two-phase for
    speed: a cheap .eb-only prefilter (ONE EventBundle, no per-field scene load) keeps single-PC +
    swap-clean fields, then the expensive per-field camera read (``field_camera_info``) runs ONLY on those
    survivors and scores them (``room_score``). Pass ``ids`` to restrict the sweep to a candidate set (also
    keeps it fast). Read-only. Needs the install (reads the scene cameras)."""
    from .extract import EventBundle, ID_TO_FBG, ID_TO_EVT, field_camera_info  # lazy: UnityPy only when used
    b = bundle or EventBundle(game)
    items = [(i, ID_TO_FBG.get(i, "")) for i in ids] if ids is not None else list(ID_TO_FBG.items())
    # phase 1 (cheap, ~30s): the .eb-only filter -- a real field, a real single player, swap-clean.
    survivors = []
    scanned = 0
    for fid, fbg in items:
        if not _is_real_fbg(fbg):
            continue
        scanned += 1
        rep = analyze_eb(b.eb_for_id(fid), field_id=fid, fbg_name=fbg, event_name=ID_TO_EVT.get(fid, ""))
        # single-PC, swap-clean, a PLAYABLE controller (not a submarine/monster rig), and a STATIC roster
        # (a story-event field rotates its cast/spawns by beat -> forks as a diorama, not a clean room).
        if (rep.has_script and rep.player_models and not rep.multi_pc and rep.swap_gesture_count == 0
                and rep.roster_class == "static-roster"
                and rep.player_models[0][1] in PLAYABLE_NAMES):
            survivors.append(rep)
    # phase 2 (expensive, ~15s): read the camera ONLY for survivors, then hard-filter + score.
    scored = []
    for rep in survivors:
        ci = field_camera_info(rep.fbg_name, game=game)
        if not ci:
            continue                                      # no readable scene -> skip (never rank a None camera)
        rep.cam_pitch, rep.cam_fov = ci["pitch"], ci["fov"]
        rep.cam_scrolling, rep.cam_count = ci["scrolling"], ci["count"]
        rep.cam_range_h = ci.get("range_h", 0)
        key = room_score(rep, max_fov=max_fov)
        if key is not None:
            scored.append((key, rep))
    scored.sort(key=lambda kr: (kr[0], kr[1].field_id))
    n = limit if (limit and limit > 0) else len(scored)   # a non-positive limit -> show all (never the slice bug)
    return RoomSweep(rooms=[r for _, r in scored[:n]], scanned=scanned, swap_clean=len(survivors))


def format_room_table(sweep: RoomSweep) -> str:
    """Render a RoomSweep as a ranked ASCII table (cp1252-safe)."""
    lines = ["swap/demo test rooms -- single-PC, swap-clean, a close 3/4 single-screen camera",
             "(walk as a swapped character, or stage a visual test where the model's detail is visible)", ""]
    if not sweep.rooms:
        lines.append("  no rooms matched -- try a wider --max-fov, or --limit")
        return "\n".join(lines)
    lines.append(f"  {len(sweep.rooms)} room(s)  (swept {sweep.scanned} fields; "
                 f"{sweep.swap_clean} single-PC + swap-clean). best-first:")
    lines += ["", f"  {'#':>2}  {'field':>5}  {'fbg':<36}  {'player':<12}  camera"]
    for i, rep in enumerate(sweep.rooms, 1):
        fbg = (rep.fbg_name or "")[:36]
        who = (rep.controlled_name or (rep.player_models[0][2] if rep.player_models else "?"))[:11]
        if rep.non_zidane:
            who += "*"
        cam = (f"FOV {rep.cam_fov:g}, pitch {rep.cam_pitch:g}"
               if rep.cam_fov is not None and rep.cam_pitch is not None else "(no camera)")
        flags = (["scroll"] if rep.cam_scrolling else []) + ([f"{rep.cam_count}cam"] if rep.cam_count > 1 else [])
        tail = ("  " + " ".join(flags)) if flags else ""
        lines.append(f"  {i:>2}  {rep.field_id:>5}  {fbg:<36}  {who:<12}  {cam}{tail}")
    lines += ["", "  * = non-Zidane player (forks via --verbatim).  Fork a room:",
              "    ff9mapkit import <fbg> --verbatim --swap-player <char>"]
    return "\n".join(lines)


# ============================================================================================
# "Who do you play as" listing -- enrich a field list with the controlled player, so the
# non-Zidane donors are discoverable WITHOUT forking each. Id-centric (a player is a property of
# the .eb, so an alternate event script on a shared background is its OWN row -- more complete than
# the folder-centric `list-fields`). Reuses analyze_eb's in-game-proven player resolution.
# ============================================================================================
@dataclass
class FieldPlayer:
    field_id: int
    fbg: str
    event_name: str
    player: str                 # the compact "who you control" label
    non_zidane: bool
    multi_pc: bool
    playable: bool = True        # the controlled model is a named cast member (vs a GEO_SUB cutscene-driver)


def _player_is_playable(rep: ForkReport) -> bool:
    """True if you control a named playable cast member (not a GEO_SUB/GEO_ACC cutscene-driver model).
    Mirrors player_label's character choice so the flag matches the displayed name."""
    if not rep.player_models:
        return False
    if rep.multi_pc:
        if not rep.non_zidane:
            return True                          # Zidane-present multi-PC -> you control Zidane (playable)
        m = None
        if rep.controlled_entry is not None:
            m = next((mm for pe, mm, _ in rep.player_models if pe == rep.controlled_entry), None)
        return (m if m is not None else rep.player_models[0][1]) in PLAYABLE_NAMES
    return rep.player_models[0][1] in PLAYABLE_NAMES


def player_label(rep: ForkReport) -> tuple:
    """(compact 'who you control' label, is_non_zidane) for a browse/list view. For a Zidane-PRESENT
    multi-PC field control most likely routes to the Zidane party-leader (not the first entry), so it
    labels 'Zidane'; a no-Zidane multi-PC field names the computed binder (`controlled_name`)."""
    if not rep.player_models:
        return ("(no player)", False)
    if rep.multi_pc:
        co = len(rep.player_models) - 1
        if rep.non_zidane:                                       # keep the flag even if the binder name is blank
            name = rep.controlled_name or rep.player_models[0][2]
            return (f"{name} +{co}", True)                       # the non-Zidane control binder
        return (f"Zidane +{co}", False)                          # Zidane-present multi-PC: likely the leader
    return (rep.player_models[0][2], rep.non_zidane)


def field_players(*, game=None, pattern=None, non_zidane_only=False, bundle=None):
    """Sweep fields and resolve WHO you control in each (the model behind ``DefinePlayerCharacter``).
    Filter by an FBG substring (``pattern``) and/or ``non_zidane_only``. Returns ``(rows, scanned)``
    (rows = FieldPlayer, sorted by fbg then id). Reuses analyze_eb (eb-only, ONE EventBundle). A full
    no-pattern sweep reads ~675 scripts (~30s); a pattern narrows it. Read-only. Needs UnityPy."""
    from .extract import EventBundle, ID_TO_FBG, ID_TO_EVT      # lazy: UnityPy only when used
    b = bundle or EventBundle(game)
    pat = pattern.lower() if pattern else None
    rows = []
    scanned = 0
    for fid, fbg in sorted(ID_TO_FBG.items(), key=lambda kv: (kv[1], kv[0])):
        if not _is_real_fbg(fbg):
            continue
        if pat and pat not in fbg.lower():
            continue
        scanned += 1
        rep = analyze_eb(b.eb_for_id(fid), field_id=fid, fbg_name=fbg, event_name=ID_TO_EVT.get(fid, ""))
        label, nz = player_label(rep)
        if non_zidane_only and not nz:
            continue
        rows.append(FieldPlayer(fid, fbg, ID_TO_EVT.get(fid, "") or "", label, nz, rep.multi_pc,
                                _player_is_playable(rep)))
    return rows, scanned


# --- fork-report --explain: decode a field's NPC interactions into readable English -------------------
# The antidote to "staring at bits": for every carried NPC, trace its tag-3 talk handler into plain
# steps (real dialogue text + items/gil/menus + cross-refs), INLINING the funcs it RunScripts -- the
# Main_Init shared logic (uid 0), the player sequences (uid 250 / a player entry), a sibling object --
# so a multi-NPC sidequest reads as one quest. This is also WHY a render-only NPC is render-only: you
# SEE that its talk routine is the field's own quest logic, not a graftable gesture (-> use --verbatim).
# Pure structure is .eb-only; dialogue TEXT enriches it when the install's .mes is available. Read-only;
# reuses the disassembler + item-pool decode + dialogue.parse_mes (no carry/graft logic of its own).
_EXPLAIN_WIN = {0x1F: 2, 0x95: 3, 0x20: 2, 0x96: 3}    # window op -> txid arg index (mirrors dialogue.WINDOW_OPS)
_RUNSCRIPT_OPS = (0x10, 0x12, 0x14)                    # RunScript[Async|Sync](level, uid, tag)
SAVE_MENU_ID = 4                                        # Menu(4, 0) = the save point (memory project-ff9-savepoint)
_VERDICT = {"clean": "interactive", "init_only": "render-only", "refuse": "not carried"}


@dataclass
class NpcExplain:
    slot: int
    model: str
    verdict: str                                       # interactive | render-only | not carried
    reason: str = ""                                   # why, in English (render-only / not-carried only)
    steps: list = _dc_field(default_factory=list)      # [(depth, kind, text)] -- kind: say|give|gil|menu|call


@dataclass
class ExplainReport:
    field_id: int
    fbg_name: str = ""
    event_name: str = ""
    npcs: list = _dc_field(default_factory=list)       # NpcExplain, in spawn order
    n_props: int = 0                                   # non-talkable set-dressing (carried, no interaction)
    has_text: bool = False                             # the .mes was resolved (dialogue is real text vs <line N>)


def _resolve_line(entries, txid, *, width=72) -> str:
    """A window's txid -> its (tag-stripped, one-line, truncated) text, or a ``<line N>`` placeholder when
    no ``.mes`` is loaded / the id is absent / the operand is computed."""
    if txid is None:
        return "(text chosen at runtime)"
    if not entries:
        return f"<line {txid}>"
    e = entries.get(int(txid))
    if e is None:
        return f"<line {txid}: not in this field's text>"
    from . import dialogue as _d
    s = _d.strip_tags(e.text).replace("\n", " / ").strip()
    s = " ".join(s.split())                            # collapse runs of whitespace from the join
    return (s[:width] + "...") if len(s) > width else (s or "(blank line)")


def _explain_call(eb, current_entry, uid, tag, pents):
    """Label a ``RunScript(uid, tag)`` in English + the entry index(es) to INLINE its body from.
    The uid->entry convention lives in :func:`eventscan.resolve_uid` (the single source of truth); this is
    the English-label layer over it."""
    from . import eventscan
    kind, targets = eventscan.resolve_uid(uid, current_entry, pents, eb.entry_count)
    label = {
        "self": f"runs its own routine #{tag}",
        "player": f"directs the player (sequence #{tag})",
        "party": f"calls a party member (routine #{tag})",
        "main": f"runs shared field logic (Main_Init routine #{tag})",
        "object": f"drives object #{uid} (routine #{tag})",
    }.get(kind, f"calls uid {uid} (routine #{tag})")
    return label, targets


def _trace_interaction(eb, entry_idx, tag, entries, *, depth, visited, steps, pents):
    """Walk one function into readable steps, recursing (depth-capped, cycle-guarded) into the player /
    Main_Init / sibling routines it RunScripts -- so a sidequest split across helpers reads as one flow."""
    key = (entry_idx, tag)
    if depth > 2 or key in visited:
        return
    visited.add(key)
    e = eb.entry(entry_idx) if 0 <= entry_idx < eb.entry_count else None
    f = e.func_by_tag(tag) if (e is not None and not e.empty) else None
    if f is None:
        return
    for ins in eb.instrs(f):
        op = ins.op
        if op in _EXPLAIN_WIN:
            steps.append((depth, "say", _resolve_line(entries, ins.imm(_EXPLAIN_WIN[op]))))
        elif op == ADD_ITEM_OP:
            iid = ins.imm(0)
            if iid is None:
                steps.append((depth, "give", "an item (chosen at runtime)"))
            elif iid != NO_ITEM and not item_inert(iid):
                cnt = ins.imm(1)
                steps.append((depth, "give", item_label(iid) + (f" x{cnt}" if cnt and cnt != 1 else "")))
        elif op == ADD_GIL_OP:
            steps.append((depth, "gil", "gil"))
        elif op == MENU_OP:
            mid = ins.imm(0)
            steps.append((depth, "menu", "a shop" if mid == SHOP_MENU_ID
                          else ("the save menu" if mid == SAVE_MENU_ID else f"menu #{mid}")))
        elif op in _RUNSCRIPT_OPS:
            uid, t = ins.imm(1), ins.imm(2)
            if uid is None or t is None:
                continue
            label, inline_from = _explain_call(eb, entry_idx, uid, t, pents)
            steps.append((depth, "call", label))
            for cand in inline_from:                   # inline the FIRST candidate that actually defines the tag
                ce = eb.entry(cand) if 0 <= cand < eb.entry_count else None
                if ce is not None and not ce.empty and ce.func_by_tag(t) is not None:
                    _trace_interaction(eb, cand, t, entries, depth=depth + 1,
                                       visited=visited, steps=steps, pents=pents)
                    break


def _explain_reason(spec) -> str:
    """Why a non-clean NPC's talk handler can't be carried as-is, in English (from its classified refs)."""
    cats = []
    for r in spec["refs"]:
        k = r["klass"]
        if k in ("self", "sibling"):
            continue
        if k == "player" and r.get("tag") is None:     # TurnTowardObject(player) etc. -- already safe
            continue
        if k == "player" and r.get("tag") is not None:
            cats.append("a scripted player sequence")
        elif r["op"] == 0x43:                          # RunSharedScript (STARTSEQ) -- a background script
            cats.append("a background script")
        elif k == "uncarried" and r.get("value") == 0 and r.get("tag") is not None:
            cats.append("shared field logic (Main_Init)")
        elif k == "uncarried" and r.get("tag") is not None:
            cats.append("another object that isn't carried")
        elif k == "expr":
            cats.append("a runtime-computed reference")
        elif k == "party":
            cats.append("a party member")
    seen = []
    for c in cats:
        if c not in seen:
            seen.append(c)
    if not seen:
        return "its talk routine references something the carry can't resolve"
    if len(seen) == 1:
        body = seen[0]
    else:
        body = ", ".join(seen[:-1]) + " and " + seen[-1]
    return "its talk routine depends on " + body


def explain_eb(eb_bytes, *, field_id: int = 0, fbg_name: str = "", event_name: str = "",
               entries=None) -> ExplainReport:
    """Decode a field's NPC interactions to an :class:`ExplainReport` from its ``.eb`` bytes (pure;
    ``entries`` = a parsed ``.mes`` ``{txid: MesEntry}`` enriches the windows with real text -- omit it
    for the structure-only view). Reuses ``scan_objects_verbatim`` with FULL grafting on, so a verdict of
    ``render-only`` means the NPC stays render-only even with every graft -- i.e. genuinely field logic."""
    from . import eventscan       # lazy (keeps import cost off the core path)
    rep = ExplainReport(field_id=field_id, fbg_name=fbg_name, event_name=event_name, has_text=bool(entries))
    if not eb_bytes:
        return rep
    eb = EbScript.from_bytes(bytes(eb_bytes))
    pents = set(eventscan.resolve_player_entries(eb))
    specs = eventscan.scan_objects_verbatim(bytes(eb_bytes), graft_player_funcs=True,
                                            carry_text=True, graft_seq_helpers=True)
    for s in specs:
        if s["kind"] != "npc":
            rep.n_props += 1
            continue
        steps: list = []
        _trace_interaction(eb, s["donor_idx"], 3, entries or {}, depth=0,
                           visited=set(), steps=steps, pents=pents)
        verdict = _VERDICT.get(s["graft_safety"], s["graft_safety"])
        reason = _explain_reason(s) if s["graft_safety"] != "clean" else ""
        rep.npcs.append(NpcExplain(s["donor_idx"], s["model"], verdict, reason, steps))
    return rep


def explain(field_id: int, *, game=None, bundle=None, lang: str = "us") -> ExplainReport:
    """The id->bytes loader over :func:`explain_eb` -- resolves the field's ``.mes`` (install needed for
    real dialogue text; degrades to ``<line N>`` placeholders without it). Read-only."""
    from .extract import EventBundle, ID_TO_FBG, ID_TO_EVT       # lazy: UnityPy only when used
    b = bundle or EventBundle(game)
    data = b.eb_for_id(field_id)
    entries = None
    try:
        from . import dialogue as _d
        mes = _d.extract_field_mes(str(field_id), lang=lang, game=game)
        if mes:
            entries = _d.parse_mes(mes)
    except Exception:                                  # no install / no UnityPy / no text block -> structure-only
        entries = None
    return explain_eb(data, field_id=field_id, fbg_name=ID_TO_FBG.get(field_id, ""),
                      event_name=ID_TO_EVT.get(field_id, ""), entries=entries)


_STEP_GLYPH = {"say": '"{}"', "give": "gives {}", "gil": "gives gil", "menu": "opens {}", "call": "-> {}"}


def format_explain(rep: ExplainReport) -> str:
    """Render an :class:`ExplainReport` as a readable cast-interaction transcript."""
    head = rep.fbg_name or f"field {rep.field_id}"
    suffix = f"  (field {rep.field_id}{', ' + rep.event_name if rep.event_name else ''})"
    out = [f"fork-report --explain: {head}{suffix}", ""]
    n_int = sum(1 for n in rep.npcs if n.verdict == "interactive")
    n_ro = sum(1 for n in rep.npcs if n.verdict == "render-only")
    out.append(f"  {len(rep.npcs)} NPC(s): {n_int} interactive, {n_ro} render-only"
               f"{f', {rep.n_props} prop(s)' if rep.n_props else ''}.")
    out.append("  Each NPC's talk routine is decoded below (dialogue + items + the funcs it runs).")
    if n_ro:
        out.append("  A render-only NPC's routine IS field logic (shared/player/quest), not a graftable")
        out.append("  gesture -- fork with --verbatim to keep it interactive (or re-author the interaction).")
    if not rep.has_text:
        out.append("  (no install / text block -> dialogue shown as <line N>; run with the game present for words.)")
    out.append("")
    if not rep.npcs:
        out.append("  (no carried NPCs -- nothing to explain.)")
        return "\n".join(out)
    for n in rep.npcs:
        glyph = "*" if n.verdict == "interactive" else "o"
        tag = f"[{n.verdict}{' -- ' + n.reason if n.reason else ''}]"
        out.append(f"  {glyph} {n.model}  (slot {n.slot})  {tag}")
        if not n.steps:
            out.append("        (no talk routine -- silent NPC)")
        for depth, kind, text in n.steps:
            pad = "        " + "    " * depth
            out.append(pad + _STEP_GLYPH.get(kind, "{}").format(text))
        out.append("")
    return "\n".join(out).rstrip()
