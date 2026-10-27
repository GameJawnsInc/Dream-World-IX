"""The press-closure classifier (``ff9mapkit.eb.pressclosure``) and the guest-traversal ship filter
(``guest_traversal.derive_field``), INSTALL-FREE: tiny kit-authored fields assembled through ``eb.ebsrc`` in the
decoded stock idiom (a region whose tag 3 brackets a ``RunScriptSync(2, 250, 17)``, a player whose tag 17 climbs on
the direction keys), each mutated ONE way, each mutant with the verdict it must give. No game bytes.

Every synthetic field is also classified by the frozen study census
(``studies/field-coop/guest-traversal/interaction_census.py``) and must get the same tier and kind -- the install-free
half of the faithfulness pin (the install-gated half runs every real QUAD root).
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import pathlib
import re
import zlib

import pytest

from ff9mapkit import guest_traversal as G
from ff9mapkit.eb import EbScript
from ff9mapkit.eb import pressclosure as P
from ff9mapkit.eb.ebsrc import assemble_source

REPO = pathlib.Path(__file__).resolve().parents[2]
CENSUS = REPO / "studies" / "field-coop" / "guest-traversal" / "interaction_census.py"

REGION_ZONE = "SetRegion(58719976, 56491967, 87162787, 84147866)"
CALL_BODY = "RunScriptSync(2, 250, 17)"
CLIMB = [
    "AddCharacterAttribute(4)",
    "Ltop:",
    "SET({const(16) B_KEY B_EXPR_END})",
    "JMP_IFNOT(Lskip)",
    "SET({Map.Int16[2] obj(uid=255).f[1] const(20) B_MINUS B_LET B_EXPR_END})",
    "Lskip:",
    "MoveInstantXZY({const(100) B_EXPR_END}, {Map.Int16[2] B_EXPR_END}, {const(200) B_EXPR_END})",
    "SET({Map.Int16[2] const(64807) B_GT B_EXPR_END})",
    "JMP_IF(Ltop)",
    "RemoveCharacterAttribute(4)",
]


def region3(*calls) -> list:
    """The stock bracket around the given body calls (usercontrol gate, DisableMove .. EnableMove)."""
    return ["SET({B_SYSVAR[2] B_EXPR_END})", "JMP_IF(Lgo)", "RET()", "Lgo:", "SET({Map.Bit[158] const(0) B_LET B_EXPR_END})",
            "DisableMove()", "SetTriangleFlagMask(127)", *calls, "SET({Map.Bit[158] const(1) B_LET B_EXPR_END})",
            "EnableMove()", "SetTriangleFlagMask(255)"]


def base() -> dict:
    """{entry: (type, {tag: [lines]})} -- main inits region 1 + player 2; the region's press climbs the player."""
    return {
        0: (0, {0: ["InitRegion(1, 0)", "InitObject(2, 0)"], 1: []}),
        1: (1, {0: [REGION_ZONE], 3: region3(CALL_BODY)}),
        2: (2, {0: ["SetModel(8, 61)", "DefinePlayerCharacter()"], 17: list(CLIMB)}),
    }


def build(ents: dict, dup: "dict | None" = None) -> bytes:
    """Assemble ``ents`` (+ ``dup``: {entry: [(tag, lines)]} listed AFTER the entry's own functions) to ``.eb`` bytes."""
    n = max(ents) + 1
    out = [".ebs 1", ".name " + "00" * 124]
    for i in range(n):
        if i not in ents:
            out.append(f".entry {i} EMPTY")
            continue
        typ, funcs = ents[i]
        out.append(f".entry {i} type={typ} loc=0 flags=0")
        for tag, lines in list(funcs.items()) + list((dup or {}).get(i, [])):
            out.append(f".func {tag}")
            out += [*lines, "RET()"]
    return assemble_source("\n".join(out) + "\n")


def derive(data: bytes, langs=("us",), by_lang=None, **kw):
    """The ship filter on one synthetic field: ``(candidates, rows, refused, quad_roots)`` (``walkmesh=`` is R15's
    provider; without one R15 is not evaluated)."""
    return G.derive_field(30999, by_lang or {lang: data for lang in langs}, langs, **kw)


@pytest.fixture(scope="module")
def census():
    spec = importlib.util.spec_from_file_location("_census_guest_traversal_under_test", CENSUS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verdict_of(data: bytes, census, region: int = 1) -> P.PressVerdict:
    """pressclosure's verdict for ``region`` -- asserted equal to the census's (tier, kind, gate) on the same bytes."""
    v = next(x for x in P.analyze_regions(data) if x.region == region)
    fld = census.Field(30999, census.EbScript.from_bytes(data))
    assert region in [ei for (rk, ei, _t, _s) in census.roots_of(fld) if rk == "QUAD"]
    c = census.Closure(fld, region)
    c.walk(region, 3, None)
    c.finish()
    assert (census.classify(c)[0], census.loco_kind(c), sorted(census.root_gate(fld, region, 3, None))) == \
        (v.tier, v.kind, list(v.gate)), "pressclosure and the census disagree"
    return v


# ================================================================================================ the positive control
def test_the_stock_idiom_ships_one_ladder_row(census):
    data = build(base())
    v = verdict_of(data, census)
    assert (v.tier, v.kind, v.gate) == ("LOCO-ONLY", "ladder-navigable", ("usercontrol",))
    assert v.funcs == ((1, 3), (2, 17)) and v.candidate and not v.truncated
    assert [(e.kind, e.uid, e.tag, e.targets) for e in v.edges] == [("ctrl", 250, 17, (2,))]
    cands, rows, refused, quads = derive(data)
    assert (cands, len(rows), refused, quads) == (1, 1, [], 1)
    r = rows[0]
    assert (r["entry"], r["kind"], r["async"], r["census_kind"], r["player_entries"]) == (1, "ladder", False,
                                                                                        "ladder-navigable", [2])
    eb = EbScript.from_bytes(data)
    for f, (role, ent, tag, uid) in zip(r["funcs"], [("region", 1, 3, 0), ("ctrl", 2, 17, 250)]):
        assert (f["role"], f["entry"], f["tag"], f["uid"]) == (role, ent, tag, uid)
        e = eb.entry(ent)
        fn = e.func_by_tag(tag)                              # the kit model's slice == the twin's (R10)
        body = eb.data[fn.abs_start:fn.abs_end]
        assert (f["len"], f["crc"]) == (fn.length, "0x%08x" % zlib.crc32(body))
        assert G.func_slice(eb.data[e.abs_start:e.abs_end], tag) == (fn.abs_start - e.abs_start, fn.length)
    assert (r["funcs"][1]["call"], r["funcs"][1]["level"]) == ("RunScriptSync", 2)


def test_fixed_uid_dispatch_ships_as_fixed_ctrl(census):
    ents = base()
    ents[1][1][3] = region3("RunScriptSync(2, 2, 17)")       # uid 2 == the player entry (InitObject uid 0 -> sid)
    v = verdict_of(build(ents), census)
    assert [(e.kind, e.uid) for e in v.edges] == [("fixed_ctrl", 2)]
    _, rows, refused, _ = derive(build(ents))
    assert not refused and [(f["role"], f["uid"]) for f in rows[0]["funcs"]] == [("region", 0), ("fixed_ctrl", 2)]


def test_an_async_body_marks_the_row_async(census):
    ents = base()
    ents[1][1][3] = region3("RunScriptAsync(4, 250, 17)")
    verdict_of(build(ents), census)
    _, rows, _, _ = derive(build(ents))
    assert rows[0]["async"] is True and rows[0]["funcs"][1]["call"] == "RunScriptAsync"


def test_a_seq_helper_ships_as_its_tag_zero(census):
    ents = base()
    ents[2][1][17] = ["RunSharedScript(3)"] + CLIMB
    ents[3] = (0, {0: ["op_22(1)", "op_22(1)", "op_22(1)"]})
    v = verdict_of(build(ents), census)
    assert ("seq", 0, (3,)) in [(e.kind, e.tag, e.targets) for e in v.edges]
    _, rows, refused, _ = derive(build(ents))
    assert not refused
    assert [(f["role"], f["entry"], f["tag"], f["uid"]) for f in rows[0]["funcs"]] == \
        [("region", 1, 3, 0), ("ctrl", 2, 17, 250), ("seq", 3, 0, 0)]


def test_jump_and_carry_kinds_map_to_the_table_kinds(census):
    ents = base()
    ents[2][1][17] = ["SetupJump(100, 0, 200, 4)", "Jump()"]
    assert verdict_of(build(ents), census).kind == "jump"
    assert derive(build(ents))[1][0]["kind"] == "jump"
    ents[2][1][17] = ["Lc:", "MoveInstantXZY(100, 0, 200)", "SET({Map.Int16[2] const(1) B_GT B_EXPR_END})", "JMP_IF(Lc)"]
    assert verdict_of(build(ents), census).kind == "carry-loop"
    assert derive(build(ents))[1][0]["kind"] == "carry"


# ================================================================================================ the tier mutants
@pytest.mark.parametrize("line, tier", [
    ("WindowSync(0, 128, 7)", "FLAVOR-TALK"),                 # a window anywhere in the closure
    ("SET({Global.Byte[13] const(9) B_LET B_EXPR_END})", "STATEFUL"),   # a GLOB write
    ("SET({Global.Byte[2] const(9) B_LET B_EXPR_END})", "STATEFUL"),    # the entrance index's bytes, by Byte width
    ("AddItem(236, 1)", "STATEFUL"),                          # an item
    ("Field(355)", "LOCO+EXIT"),                              # a warp after the climb
    ("Battle(0, 4)", "STATEFUL"),                             # a battle
    ("InitCode(3, 0)", "STATEFUL"),                           # a spawn: a scene op, so never a candidate at all
])
def test_a_non_local_op_in_the_closure_is_not_a_candidate(census, line, tier):
    ents = base()
    ents[2][1][17] = CLIMB + [line]
    if line.startswith("InitCode"):
        ents[3] = (0, {0: []})
    v = verdict_of(build(ents), census)
    assert v.tier == tier and not v.candidate
    assert derive(build(ents))[:3] == (0, [], [])


def test_a_teleport_candidate_is_a_generator_error(census):
    """The table has no walk/teleport kind: a LOCO-ONLY candidate of one is a hard error, never a silent row."""
    ents = base()
    ents[2][1][17] = ["MoveInstantXZY(100, 0, 200)"]
    assert verdict_of(build(ents), census).kind == "teleport"
    with pytest.raises(G.TableError, match="no table kind"):
        derive(build(ents))


# ================================================================================================ the refusals
def _refusal(ents, dup=None, **kw) -> str:
    cands, rows, refused, _ = derive(build(ents, dup), **kw)
    assert cands == 1 and rows == [] and len(refused) == 1, (rows, refused)
    return refused[0]["refusal"]


@pytest.mark.parametrize("call, kind", [
    ("RunScriptSync(2, 255, 5)", "self"),                     # uid 255: the region itself
])
def test_r2_a_self_edge_refuses(census, call, kind):
    ents = base()
    ents[1][1][3] = region3(CALL_BODY, call)
    ents[1][1][5] = []
    v = verdict_of(build(ents), census)
    assert v.candidate and kind in [e.kind for e in v.edges]
    assert _refusal(ents).startswith("R2 edge: ") and f"is a {kind} edge" in _refusal(ents)


def test_r2_a_sender_edge_refuses(census):
    ents = base()
    ents[2][1][17] = CLIMB + ["RunScriptObjectSync(2, 18)"]
    v = verdict_of(build(ents), census)
    assert v.candidate and "sender" in [e.kind for e in v.edges]
    assert _refusal(ents).startswith("R2 edge: ")


def test_r1_a_truncated_closure_refuses(census):
    """Nine chained calls: the census's walk stops at depth 8 SILENTLY; here it refuses (an unvisited function could
    hold a window)."""
    ents = base()
    ents[2][1][17] = CLIMB + ["RunScriptSync(2, 250, 18)"]
    for t in range(18, 28):
        ents[2][1][t] = [f"RunScriptSync(2, 250, {t + 1})"]
    ents[2][1][28] = []
    v = verdict_of(build(ents), census)
    assert v.candidate and v.truncated
    assert _refusal(ents).startswith("R1 closure: the walk was truncated")


def test_r3_one_function_in_two_roles_refuses(census):
    ents = base()
    ents[1][1][3] = region3(CALL_BODY, "RunScriptSync(2, 2, 17)")
    verdict_of(build(ents), census)
    assert _refusal(ents).startswith("R3 roles: 2:17 is reached as ctrl/fixed_ctrl")


def test_r4_a_duplicated_closure_tag_refuses(census):
    ents = base()
    data = build(ents, dup={2: [(17, ["op_22(1)"])]})
    assert [f.tag for f in EbScript.from_bytes(data).entry(2).funcs].count(17) == 2
    verdict_of(data, census)
    assert _refusal(ents, dup={2: [(17, ["op_22(1)"])]}) == "R4 table: entry 2 lists tag 17 twice"


def test_r5_a_card_handler_on_the_region_refuses(census):
    ents = base()
    ents[1][1][8] = ["op_22(1)"]
    verdict_of(build(ents), census)
    assert _refusal(ents).startswith("R5 card: ")


def test_r6_a_seq_target_with_two_functions_refuses(census):
    ents = base()
    ents[2][1][17] = ["RunSharedScript(3)"] + CLIMB
    ents[3] = (0, {0: ["op_22(1)", "op_22(1)", "op_22(1)"], 1: []})
    verdict_of(build(ents), census)
    assert _refusal(ents).startswith("R6 seq: RunSharedScript(3) targets an entry with functions [0, 1]")


def test_r7_mixed_ctrl_and_fixed_bodies_refuse(census):
    ents = base()
    ents[1][1][3] = region3(CALL_BODY, "RunScriptSync(2, 2, 18)")
    ents[2][1][18] = list(CLIMB)
    verdict_of(build(ents), census)
    assert _refusal(ents) == "R7 body: ctrl and fixed_ctrl bodies are mixed"


def test_r7_two_fixed_uids_refuse(census):
    ents = base()
    ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)", "InitObject(3, 0)"]
    ents[3] = (2, {0: ["SetModel(8, 61)", "DefinePlayerCharacter()"], 17: list(CLIMB)})
    ents[1][1][3] = region3("RunScriptSync(2, 2, 17)", "RunScriptSync(2, 3, 17)")
    verdict_of(build(ents), census)
    assert _refusal(ents) == "R7 body: two fixed uids [2, 3]"


def test_r8_a_function_under_eight_bytes_refuses(census):
    ents = base()
    ents[2][1][17] = ["RunSharedScript(3)"] + CLIMB
    ents[3] = (0, {0: ["op_22(1)"]})                          # 3 + 1 bytes
    verdict_of(build(ents), census)
    assert _refusal(ents) == "R8 short: 3:0 is 4 bytes (< 8)"


def test_r9_a_different_or_missing_language_refuses():
    us = build(base())
    other = base()
    other[2][1][17] = CLIMB + ["op_22(1)"]                    # same tier and kind, different bytes
    fr = build(other)
    assert _refusal(base(), langs=("us", "fr"), by_lang={"us": us, "fr": fr}).startswith("R9 language: fr differs")
    assert _refusal(base(), langs=("us", "fr"), by_lang={"us": us, "fr": None}) == "R9 language: fr has no .eb"
    assert derive(us, langs=("us", "fr"))[2] == []           # identical bytes in both languages ship


def _with_object_3(ents):
    """Entry 3 an object created at field init, with a looping tag 1 (what a ReturnEntryFunctions(3) restarts)."""
    ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)", "InitObject(3, 0)"]
    ents[3] = (2, {0: ["op_22(1)"], 1: ["Lt:", "op_22(1)", "JMP(Lt)"]})


def _seq_tail(ents, line):
    """The climb opens a Seq on entry 3 whose tag 0 runs ``line`` between two waits (the 207 Seq-tail shape)."""
    ents[2][1][17] = ["RunSharedScript(3)"] + CLIMB
    ents[3] = (0, {0: ["op_22(1)", line, "op_22(1)"]})


def _body_then(ents, line):
    ents[2][1][17] = CLIMB + [line]


R12_SHAPES = {
    "dret_other": (lambda e: (_body_then(e, "ReturnEntryFunctions(3)"), _with_object_3(e)),
                   r"R12 op: 2:17 \+\d+ ReturnEntryFunctions\(3\) restarts an entry's tag 1 "),
    "dret_self": (lambda e: _body_then(e, "ReturnEntryFunctions(255)"),
                  r"R12 op: 2:17 \+\d+ ReturnEntryFunctions\(255\) restarts an entry's tag 1 "),
    "seq_ends_the_player": (lambda e: _seq_tail(e, "op_1C(2)"),
                            r"R12 op: 3:0 \+3 TerminateEntry\(2\) is not the constant self-end 255 "),
    "seq_ends_another": (lambda e: _seq_tail(e, "op_1C(3)"),
                         r"R12 op: 3:0 \+3 TerminateEntry\(3\) is not the constant self-end 255 "),
    "seq_ends_computed": (lambda e: _seq_tail(e, "op_1C({const(255) B_EXPR_END})"),
                          r"R12 op: 3:0 \+3 TerminateEntry\(an expression\) is not the constant self-end 255 "),
}


@pytest.mark.parametrize("how", sorted(R12_SHAPES))
def test_r12_an_op_that_reaches_outside_the_closure_refuses(census, how):
    """R12 'op': the census keeps both shapes LOCO-ONLY (ReturnEntryFunctions is a neutral 'call'; any Seq-run
    TerminateEntry is 'flow'), so each is a candidate the old filter shipped -- DRET restarts code no CRC covers, and a
    Seq's TerminateEntry(X) disposes X (the player, here). The refusal comes from the ship filter, not the tier."""
    setup, want = R12_SHAPES[how]
    ents = base()
    setup(ents)
    v = verdict_of(build(ents), census)
    assert v.tier == "LOCO-ONLY" and v.candidate, how
    assert re.match(want, _refusal(ents)), _refusal(ents)


def test_r12_the_constant_self_end_seq_tail_still_ships(census):
    """The control: TerminateEntry(255) (1c 00 ff) is a Seq ending ITSELF -- every shipped Seq tail on the install."""
    ents = base()
    _seq_tail(ents, "op_1C(255)")
    data = build(ents)
    assert verdict_of(data, census).candidate
    _, rows, refused, _ = derive(data)
    assert refused == [] and [(f["role"], f["entry"]) for f in rows[0]["funcs"]][-1] == ("seq", 3)


@pytest.mark.parametrize("line, var, what", [
    ("SET({Null.Int16[0] const(1) B_LET B_EXPR_END})", "Null.Int16[0]", "a Null Memoria-custom / save-data var"),
    ("SET({Global.Int16[2] const(9) B_LET B_EXPR_END})", "Global.Int16[2]", "a GLOB gEventGlobal var"),
    ("SET({Global.UInt16[2] const(9) B_LET B_EXPR_END})", "Global.UInt16[2]", "a GLOB gEventGlobal var"),
])
def test_r13_a_global_or_null_write_refuses(census, line, var, what):
    """R13 'write': the census buckets no Null write at all and calls the saved entrance index (Global.Int16[2] /
    UInt16[2], no exit near) 'entrance_write', outside the tier -- both stay LOCO-ONLY candidates the old filter
    shipped. The closure may write only Map and Instance vars, which R11 audits."""
    ents = base()
    ents[2][1][17] = CLIMB + [line]
    v = verdict_of(build(ents), census)
    assert v.tier == "LOCO-ONLY" and v.candidate
    assert _refusal(ents) == f"R13 write: the closure writes {var} ({what}; only Map and Instance vars may be written)"


def test_r13_is_keyed_to_the_source_not_the_entrance_index():
    """Any Global write refuses, not only idx 2: a closure write the census would call STATEFUL (so never a candidate
    on stock bytes) is planted on a shipping verdict, and the filter alone refuses it."""
    fld = P.FieldModel.from_bytes(build(base()))
    v = P.analyze_regions(fld)[0]
    assert G._derive_one(fld, v)["pre"] is None
    v.closure.writes.append((0, 0, 77, 2))
    assert G._derive_one(fld, v)["pre"].startswith("R13 write: the closure writes Global.SBit[77] (a GLOB")


# ================================================================================================ R11: the latch audit
#: an outside region that reads the climb's Map.Int16[2] FIRST and then writes it -- the census's order-blind scratch
#: rule calls it another scratch user (so the tier stays LOCO-ONLY); the order-aware audit sees a latch consumer
READ_FIRST = ["SET({Map.Int16[2] const(5) B_GT B_EXPR_END})", "JMP_IFNOT(Lr)", "SetupJump(100, 0, 200, 4)", "Lr:",
              "SET({Map.Int16[2] const(0) B_LET B_EXPR_END})"]
WRITE_FIRST = ["SET({Map.Int16[2] const(0) B_LET B_EXPR_END})", "SET({Map.Int16[2] const(5) B_GT B_EXPR_END})"]


def with_reader(where: str, lines) -> dict:
    ents = base()
    if where == "region":
        ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)", "InitRegion(3, 0)"]
        ents[3] = (1, {0: [REGION_ZONE], 3: list(lines)})
    else:                                                     # the player's own tag (1 = its loop function)
        ents[2][1][int(where)] = list(lines)
    return ents


def test_r11_a_read_first_reader_refuses(census):
    ents = with_reader("region", READ_FIRST)
    v = verdict_of(build(ents), census)
    assert v.tier == "LOCO-ONLY", "the census's order-blind rule keeps it LOCO-ONLY -- the audit is what refuses"
    readers = P.latch_consumers(build(ents), v)
    assert [(r.label, r.first, r.consumer) for r in readers] == [("3:3", "read", True)]
    assert _refusal(ents) == "R11 latch: Map.Int16[2] is read before it is written by 3:3"


def test_r11_a_write_first_reader_is_scratch(census):
    ents = with_reader("region", WRITE_FIRST)
    verdict_of(build(ents), census)
    assert [(r.label, r.first) for r in P.latch_consumers(build(ents), P.analyze_regions(build(ents))[0])] == \
        [("3:3", "write")]
    assert derive(build(ents))[2] == []


_W = "SET({Map.Int16[2] const(0) B_LET B_EXPR_END})"
_R = "SET({Map.Int16[2] const(5) B_GT B_EXPR_END})"
_USERCONTROL = "SET({B_SYSVAR[2] B_EXPR_END})"

#: outside region bodies that READ the climb's Map.Int16[2] on some path before a plain write covers it. Each one
#: SHIPPED under the old byte-order rule (its first access in instruction order was a write, or the reader had no
#: census read site at all) -- the path-aware audit must refuse every one
R11_READ_ON_SOME_PATH = {
    "conditional_write_then_read": [_USERCONTROL, "JMP_IFNOT(Lc)", _W, "Lc:", _R],
    "plus_let_alone": ["SET({Map.Int16[2] const(1) B_PLUS_LET B_EXPR_END})"],
    "plus_let_then_read": ["SET({Map.Int16[2] const(1) B_PLUS_LET B_EXPR_END})", _R],
    "x_is_x_plus_1": ["SET({Map.Int16[2] Map.Int16[2] const(1) B_PLUS B_LET B_EXPR_END})"],
    "post_plus_then_read": ["SET({Map.Int16[2] B_POST_PLUS B_EXPR_END})", _R],
    "byte_write_then_int16_read": ["SET({Map.Byte[2] const(0) B_LET B_EXPR_END})", _R],
    "terminate_other_falls_through": [_USERCONTROL, "JMP_IF(Lw)", "op_1C(2)", "JMP(Lr)", "Lw:", _W, "Lr:", _R],
}

#: ... and the controls a path-aware rule must still SHIP: every path to the read is covered by a plain write
R11_COVERED_ON_EVERY_PATH = {
    "write_first": list(WRITE_FIRST),
    "both_arms_write_then_join": [_USERCONTROL, "JMP_IFNOT(Le)", _W, "JMP(Lj)", "Le:",
                                  "SET({Map.Int16[2] const(1) B_LET B_EXPR_END})", "Lj:", _R],
    "self_end_ends_the_uncovered_path": [_USERCONTROL, "JMP_IF(Lw)", "op_1C(255)", "JMP(Lr)", "Lw:", _W, "Lr:", _R],
}


@pytest.mark.parametrize("how", sorted(R11_READ_ON_SOME_PATH))
def test_r11_a_read_on_some_path_before_a_covering_write_refuses(census, how):
    """The path-aware audit: a conditional write does not cover the path that skips it; ``+=`` / ``++`` and the RHS of
    ``x = x + 1`` READ; a Byte write covers only its own byte of an Int16; TerminateEntry of another object does not
    end the path. The census's order-blind scratch rule keeps every one LOCO-ONLY."""
    ents = with_reader("region", R11_READ_ON_SOME_PATH[how])
    v = verdict_of(build(ents), census)
    assert v.tier == "LOCO-ONLY" and v.candidate
    assert [(r.label, r.first, r.consumer) for r in P.latch_consumers(build(ents), v)] == [("3:3", "read", True)], how
    assert _refusal(ents) == "R11 latch: Map.Int16[2] is read before it is written by 3:3"


@pytest.mark.parametrize("how", sorted(R11_COVERED_ON_EVERY_PATH))
def test_r11_a_write_covering_every_path_is_scratch(census, how):
    """The precision controls: a write on BOTH arms covers the join (a single-dominator rule would refuse it), and a
    constant self-end 255 ends the path that skipped the write."""
    ents = with_reader("region", R11_COVERED_ON_EVERY_PATH[how])
    v = verdict_of(build(ents), census)
    assert [(r.label, r.first, r.consumer) for r in P.latch_consumers(build(ents), v)] == [("3:3", "write", False)]
    _, rows, refused, _ = derive(build(ents))
    assert (len(rows), refused) == (1, []), how


def test_r11_the_load_once_reader_is_exempt(census):
    """The 2507 / 2918 shape: the player's tag 1 reads the climb var at field init (no caller, no loop before the
    read, the entry created only by Main_Init) -- it can never see a press's leftover, so the row ships."""
    ents = with_reader("1", READ_FIRST)
    v = verdict_of(build(ents), census)
    (r,) = P.latch_consumers(build(ents), v)
    assert (r.label, r.first, r.consumer) == ("2:1", "read", False) and "load-once" in r.exempt_why
    assert derive(build(ents))[1] and derive(build(ents))[2] == []


@pytest.mark.parametrize("how", ["loop_before_read", "read_again_in_a_loop", "spawned_again", "called", "tag_two",
                                 "seq_of_it", "returned", "returned_through_ctrl", "returned_by_itself",
                                 "returned_computed"])
def test_r11_each_load_once_condition_is_load_bearing(census, how):
    """Break ONE condition of the exemption at a time (critique G5's tighter rule): each turns the reader back into
    a consumer and refuses the row. 'returned*': a ReturnEntryFunctions (DRET) that can name the reader's entry --
    by its uid, through the control uid 250, as 255 from the entry itself, or computed -- restarts its tag 1."""
    lines = list(READ_FIRST)
    ents = with_reader("1", lines)
    if how == "loop_before_read":
        ents[2][1][1] = ["Lloop:", "op_22(1)", *lines, "SET({Map.Int16[4] const(1) B_GT B_EXPR_END})", "JMP_IF(Lloop)"]
    elif how == "read_again_in_a_loop":                       # the first read is before the loop, a later one inside
        ents[2][1][1] = [_R, "Lloop:", "op_22(1)", _R, "JMP_IF(Lloop)", _W]
    elif how == "spawned_again":
        ents[0][1][1] = ["InitObject(2, 0)"]                  # Main_Loop re-creates the player: tag 0/1 re-run
    elif how == "called":
        ents[0][1][1] = ["RunScriptAsync(2, 2, 1)"]
    elif how == "tag_two":
        ents = with_reader("2", lines)
    elif how == "seq_of_it":
        ents[0][1][1] = ["RunSharedScript(2)"]
    elif how == "returned":
        ents[0][1][1] = ["ReturnEntryFunctions(2)"]
    elif how == "returned_through_ctrl":
        ents[0][1][1] = ["ReturnEntryFunctions(250)"]
    elif how == "returned_by_itself":
        ents[2][1][5] = ["ReturnEntryFunctions(255)"]
    elif how == "returned_computed":
        ents[0][1][1] = ["ReturnEntryFunctions({const(1) B_EXPR_END})"]
    data = build(ents)
    v = verdict_of(data, census)
    assert v.candidate
    assert [r.consumer for r in P.latch_consumers(data, v) if r.first == "read"] == [True], how
    assert _refusal(ents).startswith("R11 latch: Map.Int16[2] is read before it is written by 2:")


@pytest.mark.parametrize("how", ["tag_zero_returned", "tag_one_another_entry_returned"])
def test_r11_a_return_that_cannot_restart_the_reader_keeps_it_load_once(census, how):
    """DRET restarts its target's TAG 1 only (Return: sx 0, stateInit -> GetIP(sid, 1)): a tag-0 reader keeps its
    exemption under a ReturnEntryFunctions of its own entry, and a tag-1 reader under one of ANOTHER entry."""
    if how == "tag_zero_returned":
        ents = with_reader("0", ["SetModel(8, 61)", "DefinePlayerCharacter()", *READ_FIRST])
        ents[0][1][1] = ["ReturnEntryFunctions(2)"]
        label = "2:0"
    else:
        ents = with_reader("1", READ_FIRST)
        ents[0][1][1] = ["ReturnEntryFunctions(1)"]
        label = "2:1"
    data = build(ents)
    v = verdict_of(data, census)
    (r,) = P.latch_consumers(data, v)
    assert (r.label, r.first, r.consumer) == (label, "read", False) and "load-once" in r.exempt_why
    _, rows, refused, _ = derive(data)
    assert (len(rows), refused) == (1, [])


# ================================================================================================ R14: the key polls
HOST_TAIL = " -- a host-owned key a live guest's climb cannot see"


@pytest.mark.parametrize("line, want", [
    ("SET({const(8192) B_KEY B_EXPR_END})", "R14 key: 2:17 polls KEY(0x2000)" + HOST_TAIL),          # Circle
    ("SET({const(1) B_KEYON B_EXPR_END})", "R14 key: 2:17 polls KEYON(0x1)" + HOST_TAIL),            # Select
    ("SET({const(8208) B_KEY B_EXPR_END})", "R14 key: 2:17 polls KEY(0x2010)" + HOST_TAIL),          # up + Circle
    ("SET({Map.Int16[8] B_KEY B_EXPR_END})", "R14 key: 2:17 polls KEY(a computed mask)" + HOST_TAIL),
    ("SET({const(256) B_KEY B_EXPR_END})", "R14 key: 2:17 polls KEY(0x100) -- no direction bit (a live guest's "
                                           "climb answers only its own direction keys)"),
])
def test_r14_a_poll_that_is_not_directions_only_refuses(census, line, want):
    """R14 'key': the census buckets a host-owned mask key_press and a computed / no-direction one key_other, both
    NEUTRAL, so each stays a LOCO-ONLY candidate the old filter shipped -- and on a live guest FilterScriptButtons masks
    exactly the host-owned bits during the control-off climb, so the loop would wait forever."""
    ents = base()
    ents[2][1][17] = CLIMB + [line]
    v = verdict_of(build(ents), census)
    assert v.tier == "LOCO-ONLY" and v.candidate
    assert _refusal(ents) == want


def test_r14_a_poll_in_the_region_function_refuses_too(census):
    ents = base()
    ents[1][1][3] = region3(CALL_BODY, "SET({const(16384) B_KEY B_EXPR_END})")       # Cross, in the press itself
    assert verdict_of(build(ents), census).candidate
    assert _refusal(ents) == "R14 key: 1:3 polls KEY(0x4000)" + HOST_TAIL


@pytest.mark.parametrize("mask", [16, 96, 192, 272])            # up; down; down-left; up + a non-host, non-direction bit
def test_r14_a_directions_only_poll_ships(census, mask):
    ents = base()
    ents[2][1][17] = CLIMB + [f"SET({{const({mask}) B_KEY B_EXPR_END}})"]
    v = verdict_of(build(ents), census)
    assert {b for (_k, _m, b, _n, _o) in v.closure.key_sites} == {"key_dir"}
    _, rows, refused, _ = derive(build(ents))
    assert (len(rows), refused) == (1, [])


# ================================================================================================ R15: the walk-ins
def _u16(v: int) -> int:
    return v & 0xFFFF


def zone(*pts) -> str:
    """A SetRegion of the given (x, z) points, packed as stock packs them (x low, z high)."""
    return "SetRegion(" + ", ".join(str((x & 0xFFFF) | ((z & 0xFFFF) << 16)) for (x, z) in pts) + ")"


#: two walkable floors, apart (no shared vertex -- two components): A where the player spawns, B where the jump lands
GROUND_A = [(-1000, 0, -1000), (-500, 0, -1000), (-500, 0, -500), (-1000, 0, -500)]
GROUND_B = [(0, 0, 0), (400, 0, 0), (400, 0, 400), (0, 0, 400)]
POLY_A = [(-900, -900), (-600, -900), (-600, -600), (-900, -600)]
POLY_B = [(50, 50), (350, 50), (350, 350), (50, 350)]
SPAWN_A = [f"CreateObject({_u16(-750)}, {_u16(-750)})"]
JUMP_B = ["SetupJump(100, 0, 200, 4)", "Jump()"]
STATEFUL_TREAD = ["AddItem(236, 1)"]


def ground():
    """The kit-built walkmesh: GROUND_A (tris 0-1) and GROUND_B (tris 2-3), each its own component."""
    from ff9mapkit.scene import bgi
    return bgi.build(GROUND_A + GROUND_B, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)])


def comp(gr, which) -> int:
    return gr.comp_of[0 if which == "A" else 2]


def r15_field(tread=None, poly=POLY_B, body=JUMP_B, spawn=SPAWN_A) -> dict:
    """base() with a spawn in the player's tag 0, a jump body, and (optionally) a tread region 3 over ``poly``."""
    ents = base()
    ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)"] + (["InitRegion(3, 0)"] if tread is not None else [])
    ents[2][1][0] = [*spawn, "SetModel(8, 61)", "DefinePlayerCharacter()"]
    ents[2][1][17] = list(body)
    if tread is not None:
        ents[3] = (1, {0: [zone(*poly)], 2: list(tread)})
    return ents


def test_the_r15_ground_is_two_components():
    gr = G.Ground(ground())
    assert comp(gr, "A") != comp(gr, "B") and gr.comp_of[0] == gr.comp_of[1] and gr.comp_of[2] == gr.comp_of[3]
    assert gr.placed(-750, None, -750) == comp(gr, "A") and gr.landed(100, 0, 200) == {comp(gr, "B")}
    assert gr.landed(100, -800, 200) == set() and gr.landed(5000, 0, 5000) == set()    # mid-air; off the mesh
    assert gr.touched(POLY_B) == {comp(gr, "B")} and gr.touched(POLY_A) == {comp(gr, "A")}


def test_r15_a_region_that_only_crosses_a_component_touches_it():
    """The area test is the engine's (IsInQuad: the triangles of every three consecutive points), not a probe: a
    sliver whose centre and corners all miss B still fires on B where it crosses it."""
    gr = G.Ground(ground())
    sliver = [(-450, 195), (2000, 195), (2000, 205), (-450, 205)]                    # centre (775, 200): off B
    assert all(gr.wm.tris_at(x, z) == [] for (x, z) in sliver + [(775, 200)])
    assert gr.touched(sliver) == {comp(gr, "B")}


def test_r15_a_stateful_walk_in_on_a_non_arrival_landing_refuses(census):
    ents = r15_field(STATEFUL_TREAD)
    data = build(ents)
    v = verdict_of(data, census)
    assert v.candidate and v.kind == "jump"
    assert P.analyze_root(P.FieldModel.from_bytes(data), 3, 2).tier == "STATEFUL"
    gr = G.Ground(ground())
    assert _refusal(ents, walkmesh=ground) == (f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival) "
                                               "carries walk-in 3:2 (item)")


def test_r15_the_same_walk_in_on_an_arrival_component_ships(census):
    """The 207 shape: the climb lands where the field itself stands the player on SOME entrance branch (a
    Global.Int16[2] switch: one branch spawns on A, the other on B) -- nothing is newly reachable."""
    spawn = ["SET({Global.Int16[2] B_EXPR_END})", "SWITCH(1, Ld, La)",
             "La:", f"SET({{Map.Int16[0] const({_u16(-750)}) B_LET B_EXPR_END}})",
             f"SET({{Map.Int16[4] const({_u16(-750)}) B_LET B_EXPR_END}})", "JMP(Lm)",
             "Ld:", "SET({Map.Int16[0] const(300) B_LET B_EXPR_END})", "SET({Map.Int16[4] const(300) B_LET B_EXPR_END})",
             "Lm:", "CreateObject({Map.Int16[0] B_EXPR_END}, {Map.Int16[4] B_EXPR_END})"]
    ents = r15_field(STATEFUL_TREAD, spawn=spawn)
    data = build(ents)
    verdict_of(data, census)
    gr = G.Ground(ground())
    fld = P.FieldModel.from_bytes(data)
    assert sorted((x, z) for (_e, _o, _op, x, _y, z) in G.spawn_points(fld)) == [(-750, -750), (300, 300)]
    assert G.field_arrival(fld, gr) == {comp(gr, "A"), comp(gr, "B")}
    _, rows, refused, _ = derive(data, walkmesh=ground)
    assert (len(rows), refused) == (1, []) and "r15" not in rows[0]


def test_r15_the_last_placement_on_a_path_is_the_arrival(census):
    """A CreateObject that a later MoveInstantXZY moves (stock lifts its spawn to a floor this way, through
    obj(uid=255).f[0] / f[2]) arrives where the MoveInstantXZY puts it, not where CreateObject did."""
    spawn = ["CreateObject(300, 300)",
             f"MoveInstantXZY({_u16(-750)}, 0, {_u16(-750)})", "SetPathing(1)"]       # B, then moved to A
    ents = r15_field(STATEFUL_TREAD, spawn=spawn)
    data = build(ents)
    gr = G.Ground(ground())
    assert G.field_arrival(P.FieldModel.from_bytes(data), gr) == {comp(gr, "A")}
    assert _refusal(ents, walkmesh=ground).startswith("R15 walk-in: landing component")
    lift = ["CreateObject(300, 300)", "MoveInstantXZY({obj(uid=255).f[0] B_EXPR_END}, 0, {obj(uid=255).f[2] B_EXPR_END})",
            "SetPathing(1)"]
    fld = P.FieldModel.from_bytes(build(r15_field(STATEFUL_TREAD, spawn=lift)))
    assert [(op, x, y, z) for (_e, _o, op, x, y, z) in G.spawn_points(fld)] == [(0xA1, 300, 0, 300)]


def test_r15_an_unresolved_spawn_counts_no_arrival(census):
    """FAIL CLOSED: a spawn the walk cannot resolve (a saved position) arrives nowhere, so B -- even where a real
    entrance might stand the player -- is newly reachable."""
    spawn = ["CreateObject({Global.Int16[243] B_EXPR_END}, {Global.Int16[247] B_EXPR_END})"]
    ents = r15_field(STATEFUL_TREAD, spawn=spawn)
    data = build(ents)
    assert G.spawn_points(P.FieldModel.from_bytes(data)) == []
    assert _refusal(ents, walkmesh=ground).startswith("R15 walk-in: landing component")


@pytest.mark.parametrize("tread, tier", [(["Field(355)"], "EXIT-ONLY"), ([], "TRIVIAL"), (["op_22(1)"], "TRIVIAL")])
def test_r15_an_exit_only_or_trivial_walk_in_on_new_ground_ships(census, tread, tier):
    ents = r15_field(tread)
    data = build(ents)
    verdict_of(data, census)
    assert P.analyze_root(P.FieldModel.from_bytes(data), 3, 2).tier == tier
    _, rows, refused, _ = derive(data, walkmesh=ground)
    assert (len(rows), refused) == (1, [])


def test_r15_a_stateful_walk_in_off_the_new_ground_ships(census):
    _, rows, refused, _ = derive(build(r15_field(STATEFUL_TREAD, poly=POLY_A)), walkmesh=ground)
    assert (len(rows), refused) == (1, [])


UNNAMED = [
    (["SetupJump(5000, 0, 5000, 4)", "Jump()"],
     "2:17 +0 SetupJump(5000, 0, 5000) can end the climb on no walkable tri within 250 u"),          # off the mesh
    ([f"SetupJump(100, {_u16(-800)}, 200, 4)", "Jump()"],
     "2:17 +0 SetupJump(100, -800, 200) can end the climb on no walkable tri within 250 u"),         # 800 u above B
    (["SetupJump({Map.Int16[8] B_EXPR_END}, 0, 200, 4)", "Jump()"],
     "2:17 +0 SetupJump can end the climb at a computed point"),
]


@pytest.mark.parametrize("body, wild", UNNAMED)
def test_r15_a_final_landing_it_cannot_name_lands_everywhere(census, body, wild):
    """F1, FAIL CLOSED: a final landing R15 cannot name may leave the player on ANY walkable component -- so a STATEFUL
    walk-in off the arrival ground (B) refuses, and the refusal says it was the unnamed landing that reached it."""
    ents = r15_field(STATEFUL_TREAD, body=body)
    assert verdict_of(build(ents), census).candidate
    gr = G.Ground(ground())
    assert _refusal(ents, walkmesh=ground) == (f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival) "
                                               f"carries walk-in 3:2 (item) -- {wild}, so the climb may land on any "
                                               "walkable component")


@pytest.mark.parametrize("tread", [None, "on_arrival"])
@pytest.mark.parametrize("body, wild", UNNAMED)
def test_r15_an_unnamed_final_landing_with_nothing_exposed_off_arrival_ships(census, body, wild, tread):
    """F1's control: the unnamed landing alone refuses nothing -- with no walk-in, or a STATEFUL one only on the arrival
    ground A, there is nothing a landing anywhere could newly reach (the 2353 / 2456 / 2955 shape)."""
    ents = r15_field(STATEFUL_TREAD if tread else None, poly=POLY_A, body=body)
    data = build(ents)
    fld = P.FieldModel.from_bytes(data)
    gr = G.Ground(ground())
    w = G.walkin(fld, P.analyze_regions(fld)[0], gr, G.field_arrival(fld, gr), G.walk_ins(fld, gr))
    assert w["wild"] == [wild] and w["land"] == {comp(gr, "A"), comp(gr, "B")} and w["why"] is None
    _, rows, refused, _ = derive(data, walkmesh=ground)
    assert (len(rows), refused) == (1, [])


def test_r15_a_mid_air_mount_that_a_later_landing_follows_is_in_flight(census):
    """A ladder's mount hangs mid-air on the ladder; a later landing on every path makes it non-final, so it neither
    refuses nor names a component -- the climb lands on B only."""
    body = [f"SetupJump(100, {_u16(-800)}, 200, 4)", "Jump()", "SetupJump(100, 0, 200, 4)", "Jump()"]
    data = build(r15_field(None, body=body))
    fld = P.FieldModel.from_bytes(data)
    v = P.analyze_regions(fld)[0]
    assert [(x, y, z, final) for (_op, x, y, z, _n, _o, final) in G.landing_points(fld, v)] == \
        [(100, -800, 200, False), (100, 0, 200, True)]
    _, rows, refused, _ = derive(data, walkmesh=ground)
    assert (len(rows), refused) == (1, [])
    gr = G.Ground(ground())
    assert _refusal(r15_field(STATEFUL_TREAD, body=body), walkmesh=ground).startswith(
        f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival)")


def test_r15_a_computed_tread_region_touches_everything(census):
    """FAIL CLOSED: a walk-in whose SetRegion is computed may lie anywhere -- here even over the arrival A only."""
    ents = r15_field(STATEFUL_TREAD)
    ents[3][1][0] = [zone(*POLY_A), "SetRegion({Map.Int16[8] B_EXPR_END}, 0, 0, 0)"]
    assert G.region_polys(P.FieldModel.from_bytes(build(ents)), 3) is None
    gr = G.Ground(ground())
    assert _refusal(ents, walkmesh=ground) == (f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival) may "
                                               "carry walk-in 3:2 (item) -- its region is computed")


def test_r15_without_a_provider_is_not_evaluated_and_never_ships(census):
    """The install-free path with no walkmesh: the row comes back MARKED, never as a pass -- assemble refuses it."""
    data = build(r15_field(STATEFUL_TREAD))
    _, rows, refused, _ = derive(data)
    assert refused == [] and rows[0]["r15"] == G.R15_NOT_EVALUATED
    with pytest.raises(G.TableError, match="R15 was not evaluated for 30999:1"):
        G.assemble(rows, refused, {"fields_scanned": 1, "quad_roots": 1, "census_candidates": 1}, [])


def test_r15_the_provider_is_lazy_and_its_failure_refuses_the_table(census):
    """The walkmesh is read only when a row reaches R15 (an R14 refusal never asks), and a provider that fails is a
    TableError -- the install path never ships a row it could not judge."""
    calls = []

    def boom():
        calls.append(1)
        raise G.TableError("R15 walk-in needs field 30999's walkmesh: spy")
    ents = r15_field(STATEFUL_TREAD, body=JUMP_B + ["SET({const(8192) B_KEY B_EXPR_END})"])
    assert _refusal(ents, walkmesh=boom).startswith("R14 key: ") and calls == []
    with pytest.raises(G.TableError, match="spy"):
        derive(build(r15_field(STATEFUL_TREAD)), walkmesh=boom)
    assert calls == [1]
    with pytest.raises(G.TableError, match="field index"):
        G._r15_walkmesh(None, None, 30999)


# ============================================================================================ R15: the engine's own frames
#: two stacked floors over B's footprint (LOW at y 0, HIGH 1000 u above it -- y is DOWN in the script frame)
GROUND_LOW = [(0, 0, 0), (400, 0, 0), (400, 0, 400), (0, 0, 400)]
GROUND_HIGH = [(0, -1000, 0), (400, -1000, 0), (400, -1000, 400), (0, -1000, 400)]


def stacked():
    """A, LOW (tris 2-3) and HIGH (tris 4-5): three components, LOW and HIGH over the same XZ."""
    from ff9mapkit.scene import bgi
    return bgi.build(GROUND_A + GROUND_LOW + GROUND_HIGH, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (8, 9, 10),
                                                            (8, 10, 11)])


def test_r15_createobject_stands_on_the_topmost_floor():
    """F4a: CreateObject carries no y -- the engine places at Unity y = POS_COMMAND_DEFAULTY (+32768) and the walkmesh
    negates y, so in the kit's y-down frame the pick is the TOPMOST tri. A spawn over LOW / HIGH arrives on HIGH, so a
    jump down to LOW opens LOW and its STATEFUL tread refuses (with the old +32768 the spawn read as LOW: it shipped)."""
    gr = G.Ground(stacked())
    low, high = gr.comp_of[2], gr.comp_of[4]
    assert G.ENGINE_DEFAULT_Y == -32768 and low != high
    assert gr.placed(200, None, 200) == high and gr.placed(200, 0, 200) == low
    ents = r15_field(STATEFUL_TREAD, spawn=["CreateObject(200, 200)"])
    fld = P.FieldModel.from_bytes(build(ents))
    assert G.field_arrival(fld, gr) == {high}
    assert _refusal(ents, walkmesh=stacked) == (f"R15 walk-in: landing component {low} (not an arrival) carries walk-in "
                                                "3:2 (item)")


_LIFT_A = [f"CreateObject({_u16(-750)}, {_u16(-750)})", f"MoveInstantXZY({_u16(-750)}, 0, {_u16(-750)})"]


@pytest.mark.parametrize("spawn, kept", [
    (_LIFT_A, False),                                                          # MoveInstantXZY turns pathing off
    (_LIFT_A + ["SetPathing(1)"], True),                                       # the stock lift: back on
    (_LIFT_A + ["SetPathing(1)", "AddCharacterAttribute(4)"], False),          # left on a ladder
    (_LIFT_A + ["SetPathing(1)", "AddCharacterAttribute(4)", "RemoveCharacterAttribute(4)"], True),
    (_LIFT_A + ["SetPathing(1)", "AddCharacterAttribute(1)"], True),           # not the ladder bit
    (_LIFT_A[:1] + ["SetPathing(0)"], False),
    (_LIFT_A[:1] + ["SetPathing({Map.Int16[8] B_EXPR_END})"], False),          # unknown: no arrival
    (_LIFT_A[:1] + ["SetupJump(100, 0, 200, 4)", "Jump()"], False),            # SetupJump turns pathing off
    (_LIFT_A[:1] + ["WalkTowardObject(3)"], False),                            # a move the walk cannot place
])
def test_r15_a_spawn_path_that_hands_no_walk_control_is_no_arrival(spawn, kept):
    """F4b: a path through the player's tag 0 counts its last placement as an ARRIVAL only when it ends with pathing on
    (FieldMapActorController.charFlags bit 0 -- off, ServiceChar never runs) and no ladder attribute -- the player's
    tag 1 carries such a player on, so the point is no control position. Fewer arrivals, never more."""
    fld = P.FieldModel.from_bytes(build(r15_field(STATEFUL_TREAD, spawn=spawn)))
    assert bool(G.spawn_points(fld)) == kept, G._place_walk(fld, 2, fld.player)


def test_r15_the_entrance_switch_is_followed_into_a_later_test_of_the_same_index():
    """F4b on the 2505 shape: the entrance switch's arm value is LEARNED, so a later `if Global.Int16[2] == 122` that
    puts the player on a ladder follows only arm 122 -- the B spawn (entrance 122) is dropped and A (the default) kept.
    A walk that took both successors of every branch would keep B through the infeasible "122 but not 122" path."""
    spawn = ["SET({Global.Int16[2] B_EXPR_END})", "SWITCHEX(Ld, 122, Lb)",
             "Lb:", "CreateObject(300, 300)", "JMP(Lj)",
             "Ld:", f"CreateObject({_u16(-750)}, {_u16(-750)})",
             "Lj:", "SET({Global.Int16[2] const(122) B_EQ B_EXPR_END})", "JMP_IFNOT(Le)", "AddCharacterAttribute(4)",
             "Le:"]
    fld = P.FieldModel.from_bytes(build(r15_field(STATEFUL_TREAD, spawn=spawn)))
    assert [(x, z) for (_e, _o, _op, x, _y, z) in G.spawn_points(fld)] == [(-750, -750)]
    gr = G.Ground(ground())
    assert G.field_arrival(fld, gr) == {comp(gr, "A")}


#: A, a BRIDGE and B in a row (floors 0, 1, 2), sharing their edges: ONE component until the bridge is disabled
STRIP = [(-1000, 0, 0), (-1000, 0, 400), (-500, 0, 0), (-500, 0, 400), (0, 0, 0), (0, 0, 400), (400, 0, 0), (400, 0, 400)]
STRIP_FACES = [(0, 2, 3), (0, 3, 1), (2, 4, 5), (2, 5, 3), (4, 6, 7), (4, 7, 5)]
SPAWN_STRIP_A = [f"CreateObject({_u16(-750)}, 200)"]


def strip():
    from ff9mapkit.scene import bgi
    return bgi.build(STRIP, STRIP_FACES, floor_ids=[0, 0, 1, 1, 2, 2])


@pytest.mark.parametrize("disable", ["EnablePathTriangle(2, 0)\nEnablePathTriangle(3, 0)", "EnablePath(1, 0)"])
def test_r15_main_inits_constant_disables_split_the_ground(census, disable):
    """F4c: Main_Init's constant EnablePathTriangle(tri, 0) / EnablePath(floor, 0) take the bridge off the walkmesh
    before R15 names components, so A (the arrival) and B (the landing) are apart and B's STATEFUL tread refuses --
    with the bridge left on, B was A's own component and the row shipped."""
    ents = r15_field(STATEFUL_TREAD, spawn=SPAWN_STRIP_A)
    _, rows, refused, _ = derive(build(ents), walkmesh=strip)
    assert (len(rows), refused) == (1, [])                                   # the bridge on: one component
    ents[0][1][0] = ents[0][1][0] + disable.split("\n")
    data = build(ents)
    assert G.main_init_disables(P.FieldModel.from_bytes(data), strip()) == {2, 3}
    gr = G.Ground(strip(), {2, 3})
    assert _refusal(ents, walkmesh=strip) == (f"R15 walk-in: landing component {gr.comp_of[4]} (not an arrival) carries "
                                              "walk-in 3:2 (item)")


def test_r15_a_disable_counts_on_any_branch_and_only_as_a_constant():
    """The union over Main_Init's branches (the conservative direction); a computed operand, an enable, or a disable
    outside Main_Init is not applied."""
    ents = r15_field(STATEFUL_TREAD, spawn=SPAWN_STRIP_A)
    ents[0][1][0] = ents[0][1][0] + ["SET({Global.Bit[9000] B_EXPR_END})", "JMP_IFNOT(Lq)", "EnablePathTriangle(2, 0)",
                                     "Lq:", "EnablePathTriangle({Map.Int16[8] B_EXPR_END}, 0)", "EnablePath(2, 1)"]
    ents[0][1][1] = ["EnablePathTriangle(5, 0)"]
    fld = P.FieldModel.from_bytes(build(ents))
    assert G.main_init_disables(fld, strip()) == {2}


def test_r15_a_disabled_tri_stands_for_what_it_borders():
    """A tread only over the disabled bridge can fire once a script re-enables it: it touches the components the
    bridge joins (both A and B), never nothing."""
    gr = G.Ground(strip(), {2, 3})
    assert gr.touched([(-400, 100), (-100, 100), (-100, 300), (-400, 300)]) == {gr.comp_of[0], gr.comp_of[4]}


def test_r15_a_quadcircle_hot_fix_region_touches_everything():
    """F4d: a tread whose fldMapNo * 1000 + sid is a QuadCircleData key is tested against the engine's own circle, not
    its SetRegion -- so even one drawn over the arrival ground only may carry its walk-in onto B."""
    ents = r15_field(STATEFUL_TREAD, poly=POLY_A)
    ents[6] = ents.pop(3)
    ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)", "InitRegion(6, 0)"]
    data = build(ents)
    assert 1553006 in G.QUAD_CIRCLE_KEYS
    _, rows, refused, _ = G.derive_field(30999, {"us": data}, ("us",), walkmesh=ground)
    assert (len(rows), refused) == (1, [])
    _, rows, refused, _ = G.derive_field(1553, {"us": data}, ("us",), walkmesh=ground)
    gr = G.Ground(ground())
    assert rows == [] and refused[0]["refusal"] == (
        f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival) may carry walk-in 6:2 (item) -- the engine's "
        "QuadCircleData hot-fix tests it against its own circle")


# ================================================================================================ R15: the bumps
#: the stock chest template: a user-control test, then a constant Confirm | Special poll, dominating every effect
CHEST = ["SET({B_SYSVAR[2] B_EXPR_END})", "JMP_IF(Lc)", "RET()", "Lc:", "Bubble(1)",
         "SET({const4(655360) B_KEYON B_EXPR_END})", "JMP_IFNOT(Lx)", "AddItem(236, 1)", "WindowSync(7, 0, 4)", "Lx:"]
#: ... and its Japanese twin: Cancel | Special, which F1's control-on mask does NOT strip
JP_CHEST = [ln.replace("655360", "589824") for ln in CHEST]


def bump_field(tag2, at=(200, 200), place=None, extra0=(), tag1=None) -> dict:
    """r15_field (spawn on A, a jump to B, no tread) plus object 4 -- created by Main_Init, placed by its own tag 0 --
    whose tag 2 is ``tag2``: the bump a player walking into it runs (CheckNPCPush)."""
    ents = r15_field(None)
    ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)", "InitObject(4, 0)"]
    funcs = {0: [place or f"CreateObject({_u16(at[0])}, {_u16(at[1])})", *extra0], 2: list(tag2)}
    if tag1 is not None:
        funcs[1] = list(tag1)
    ents[4] = (2, funcs)
    return ents


def test_r15_a_stateful_bump_on_new_ground_refuses(census):
    """F3: an object's tag 2 runs on the guest's own copy exactly as a tread region's does -- R15's walk-in set holds
    it too, placed where its tag 0 leaves it."""
    ents = bump_field(STATEFUL_TREAD)
    data = build(ents)
    assert verdict_of(data, census).candidate
    fld = P.FieldModel.from_bytes(data)
    assert [e for (e, _tv) in G.bump_objects(fld)] == [4] and G.tread_regions(fld) == []
    gr = G.Ground(ground())
    assert _refusal(ents, walkmesh=ground) == (f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival) carries "
                                               "bump 4:2 (item)")


def test_r15_the_chest_template_bump_ships_and_needs_both_halves(census):
    """The hidden-item exemption (pressclosure.WatchScan.exempt_why): every effect op dominated by a
    user-control test AND a constant Confirm / Special / Select poll. Dropping either half, or polling the Japanese
    Cancel | Special (F1 strips Confirm, Special, Select only -- NetSyncField.ControlOnScriptKeys), exposes it."""
    _, rows, refused, _ = derive(build(bump_field(CHEST)), walkmesh=ground)
    assert (len(rows), refused) == (1, [])
    no_control = CHEST[4:]
    no_key = CHEST[:5] + ["AddItem(236, 1)", "WindowSync(7, 0, 4)"]
    gr = G.Ground(ground())
    for tag2 in (no_control, no_key, JP_CHEST):
        fld = P.FieldModel.from_bytes(build(bump_field(tag2)))
        assert P.watch_scan(fld, 4, 2).exempt_why(P.analyze_root(fld, 4, 2)) is not None
        assert _refusal(bump_field(tag2), walkmesh=ground) == (
            f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival) carries bump 4:2 (window, item)")


def test_r15_a_bump_reaches_as_far_as_its_collision_radius():
    """The footprint is WalkMesh.Collision's mode-2 reach (4 * collRad of the player and of the object + speed + 60),
    not only the tri under the point: an object on A near B touches B once its SetObjectLogicalSize radius spans the
    gap (A ends at x -500, B starts at 0)."""
    at = (-520, -520)                                               # 735 u from B's corner (0, 0)
    _, rows, refused, _ = derive(build(bump_field(STATEFUL_TREAD, at=at)), walkmesh=ground)
    assert (len(rows), refused) == (1, [])                          # 4*16 + 4*16 + 255 + 60 = 443 u
    big = bump_field(STATEFUL_TREAD, at=at, extra0=["SetObjectLogicalSize(20, 100, 40)"])
    assert G.bump_reach(P.FieldModel.from_bytes(build(big)), 4) == 779
    assert _refusal(big, walkmesh=ground).startswith("R15 walk-in: landing component")


@pytest.mark.parametrize("how, why", [
    ("computed", "4:0 leaves it at no known point on some path"),
    ("walks_unbound", "its 4:1 runs Walk"),
    ("moved_ex", "0:1 runs MoveInstantXZYEx on it"),
    ("created_at_a_computed_point", "its 4:1 runs CreateObject"),
    ("walks_from_an_unknown_start", "its 4:1 runs Walk"),
    ("walks_to_the_exit", "its 4:1 runs WalkToExit"),
])
def test_r15_a_bump_that_is_not_where_its_tag_0_left_it_touches_everything(how, why):
    """FAIL CLOSED: a computed placement, or a move outside the object's tag 0 (its own walk, anyone's Ex op naming it),
    may put it anywhere -- even one placed on the arrival ground A. A walker is no walker when a CreateObject outside its
    tag 0 has a computed point, when its tag 0 placed it at an unknown point before its walk (that start is a seed), or
    when it runs WalkToExit (MOVJ walks gCur to a computed exit point, EventEngine.DoEventCode.cs:872-876)."""
    a = (-750, -750)
    if how == "computed":
        ents = bump_field(STATEFUL_TREAD, place="CreateObject({Map.Int16[8] B_EXPR_END}, 0)")
    elif how == "walks_unbound":                              # a walker the V1 bound cannot hold: its pathing may go off
        ents = bump_field(STATEFUL_TREAD, at=a, tag1=["SetPathing(0)", "Walk(200, 200)"])
    elif how == "created_at_a_computed_point":
        ents = bump_field(STATEFUL_TREAD, at=a, tag1=["CreateObject({Map.Int16[8] B_EXPR_END}, 0)"] + CHASER)
    elif how == "walks_from_an_unknown_start":
        ents = bump_field(STATEFUL_TREAD, place="CreateObject({Map.Int16[8] B_EXPR_END}, 0)", tag1=CHASER,
                          extra0=[f"Walk({_u16(a[0])}, {_u16(a[1])})"])
    elif how == "walks_to_the_exit":
        ents = bump_field(STATEFUL_TREAD, at=a, tag1=["WalkToExit()"])
    else:
        ents = bump_field(STATEFUL_TREAD, at=a)
        ents[0][1][1] = ["MoveInstantXZYEx(4, 200, 0, 200)"]
    gr = G.Ground(ground())
    assert _refusal(ents, walkmesh=ground) == (f"R15 walk-in: landing component {comp(gr, 'B')} (not an arrival) may "
                                               f"carry bump 4:2 (item) -- {why}")


def test_r15_a_bump_on_the_arrival_ground_ships():
    _, rows, refused, _ = derive(build(bump_field(STATEFUL_TREAD, at=(-750, -750))), walkmesh=ground)
    assert (len(rows), refused) == (1, [])


# ================================================================================================ R15: the exemption, FAIL CLOSED
CTRL_GATE = ["SET({B_SYSVAR[2] B_EXPR_END})", "JMP_IF(Lc)", "RET()", "Lc:"]
CONFIRM_GATE = ["SET({const4(655360) B_KEYON B_EXPR_END})", "JMP_IFNOT(Lx)"]
NOT_BOTH = "is not under both a user-control test and a stripped poll"


def tread_r15(tag2, more=None) -> dict:
    """r15_field (spawn on A, a jump to B) with tread region 3 over B whose tag 2 is ``tag2``; ``more``: extra entries."""
    ents = r15_field(list(tag2))
    ents.update(more or {})
    return ents


def judged(ents, ei=3, root_tag=2):
    """(tier, exempt_why) of entry ``ei``'s tag-2 closure: the walk-in exemption's own view (the scan follows Init*)."""
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    tv = P.analyze_root(fld, ei, root_tag)
    return tv.tier, P.watch_scan(fld, ei, root_tag, spawn=True).exempt_why(tv)


def ships(ents, gr=ground) -> bool:
    _, rows, refused, _ = derive(build(ents), walkmesh=gr)
    return (len(rows), refused) == (1, [])


def on_b(what) -> str:
    return f"R15 walk-in: landing component {comp(G.Ground(ground()), 'B')} (not an arrival) {what}"


def test_r15_a_spawned_objects_code_is_scanned():
    """V2 D1: the tread's tag 2 only creates object 7, whose tag 0 gives the item. The closure walk follows Init*, so
    the exemption's scan must too (the created object runs its tag 0 on the guest's copy): ungated it refuses; under
    both halves the spawn itself is out of a guest's reach, so the child is entered holding them and ships."""
    child = {7: (2, {0: ["AddItem(236, 1)"]})}
    ents = tread_r15(["InitObject(7, 0)"], child)
    assert judged(ents) == ("STATEFUL", f"item at 7:0 {NOT_BOTH}")
    assert _refusal(ents, walkmesh=ground) == on_b("carries walk-in 3:2 (item)")
    gated = tread_r15(CTRL_GATE + CONFIRM_GATE + ["InitObject(7, 0)", "Lx:"], child)
    assert judged(gated) == ("STATEFUL", None) and ships(gated)


@pytest.mark.parametrize("line, bucket", [("RunTimer(1)", "timer"), ("ChangeTimerTime(60)", "timer"),
                                          ("ShowTimer(1)", "timer"), ("DefinePlayerCharacter()", "control_swap")])
def test_r15_a_stateful_bucket_with_no_effect_op_still_needs_both_halves(line, bucket):
    """V2 D2: a timer op (the HARD 'timer' bucket) or DefinePlayerCharacter (control_swap) makes a closure STATEFUL but
    is no effect R16 names -- the exemption sees every STATEFUL bucket's site (pressclosure.STATEFUL_BUCKETS) and needs
    both halves over each (the stock 1650 treads 7-11 and 2510 tread 14 were exempt with zero effects)."""
    assert judged(tread_r15([line])) == ("STATEFUL", f"{bucket} at 3:2 {NOT_BOTH}")
    assert judged(tread_r15(CTRL_GATE + CONFIRM_GATE + [line, "Lx:"])) == ("STATEFUL", None)
    if bucket == "timer":                                     # (a DefinePlayerCharacter makes entry 3 a player entry)
        assert _refusal(tread_r15([line]), walkmesh=ground) == on_b("carries walk-in 3:2 (timer)")
        assert ships(tread_r15(CTRL_GATE + CONFIRM_GATE + [line, "Lx:"]))


_GATED_ITEM = CTRL_GATE + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"]


@pytest.mark.parametrize("ungated, more, bucket", [
    (["SET({Map.Int16[8] B_SYSVAR[9] B_LET B_EXPR_END})"], {}, "read_choice"),        # the choice result, read
    (["op_1C(5)"], {5: (2, {0: []})}, "spawn"),                                       # TerminateEntry(5) disposes 5
])
@pytest.mark.parametrize("beside", [(), ("InitObject(6, 0)",)])
def test_r15_an_ungated_stateful_site_beside_a_gated_effect_refuses(ungated, more, bucket, beside):
    """Every STATEFUL bucket's every SITE needs both halves, not just one site of each bucket: an ungated read of the
    choice result (read_choice) or a TerminateEntry of another object (the spawn bucket -- R12 ships only the constant
    self-end as flow) before the gated chest refuses, and so it does beside a gated InitObject that gives the spawn
    bucket a covered site too."""
    gated = _GATED_ITEM[:-2] + list(beside) + _GATED_ITEM[-2:]
    six = {6: (2, {0: []})} if beside else {}
    ents = tread_r15(list(ungated) + gated, {**more, **six})
    assert judged(ents) == ("STATEFUL", f"{bucket} at 3:2 {NOT_BOTH}")
    assert not ships(ents)
    assert ships(tread_r15(gated, six))


def test_the_exemption_fails_closed_on_what_its_scan_did_not_see():
    """WatchScan.exempt_why, condition by condition, on the stock chest template (exempt): (a) an open scan, (b) a
    closure function the scan never visited, (c) a STATEFUL bucket with no site in the scan -- each refuses it."""
    fld = P.FieldModel.from_bytes(build(bump_field(CHEST)), 30999)
    tv = P.analyze_root(fld, 4, 2)
    ws = P.watch_scan(fld, 4, 2, spawn=True)
    assert ws.exempt_why(tv) is None and set(tv.funcs) <= ws.nodes
    assert ws.exempt_why(dataclasses.replace(tv, funcs=tv.funcs + ((9, 9),))) == "the scan never visited 9:9"
    assert ws.exempt_why(dataclasses.replace(tv, buckets=tv.buckets + ("timer",))) == \
        "its closure's timer has no site the scan saw"
    ws.open.append("a probe")
    assert ws.exempt_why(tv) == "its scan is open (a probe)"


@pytest.mark.parametrize("body, bucket", [
    (["AddItem(236, 1)", "Lx:", "RET()", "WindowSync(7, 0, 4)"], "window"),
    (["AddItem(236, 1)", "Lx:", "RET()", "Field(355)"], "exit"),
    (["WindowSync(7, 0, 4)", "Lx:", "RET()", "AddItem(236, 1)"], "item_party"),
    (["AddItem(236, 1)", "JMP(Lf)", "SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})", "Lf:", "Field(355)", "Lx:"],
     "exit_glob"),                                    # jumped over, but within the census's 12 ops of the exit
])
def test_r15_a_stateful_bucket_whose_site_the_scan_never_sees_refuses(body, bucket):
    """Condition (c) on real code, one STATEFUL class at a time: the closure walk reads every instruction in byte order,
    the scan only the reachable ones, so a bucket whose only site is dead code has no site the scan saw -- the chest
    template around the rest stays refused (FAIL CLOSED: the scan and the tier must agree on what is there)."""
    ents = tread_r15(CTRL_GATE + CONFIRM_GATE + body)
    assert judged(ents) == ("STATEFUL", f"its closure's {bucket} has no site the scan saw")
    assert not ships(ents)


def test_r15_a_global_write_beside_the_exit_is_its_exit_glob_site():
    """The control: a Global write within the census's 12 ops of the exit is the closure's exit_glob bucket, and the
    scan names its site the same way (site_buckets' near-exit rule) -- under both halves the template ships."""
    ents = tread_r15(CTRL_GATE + CONFIRM_GATE + ["AddItem(236, 1)", "SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})",
                                                 "Field(355)", "Lx:"])
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert "exit_glob" in P.analyze_root(fld, 3, 2).buckets
    assert judged(ents) == ("STATEFUL", None) and ships(ents)


def test_r15_a_walk_in_it_cannot_judge_whole_is_exposed_whatever_its_tier():
    """V4: a tread whose tag 2 calls through a computed uid tiers from what its walk saw (TRIVIAL) and the AddItem
    behind it never counts -- an incomplete closure (pressclosure.closure_gaps) or an open scan (here a sender call,
    which the closure walk guesses) is EXPOSED whatever the tier."""
    child = {7: (2, {0: [], 5: ["AddItem(236, 1)"]})}
    ents = tread_r15(["RunScriptSync(2, {Map.Int16[8] B_EXPR_END}, 5)"], child)
    ents[0][1][0].append("InitObject(7, 0)")
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    tv = P.analyze_root(fld, 3, 2)
    assert tv.tier == "TRIVIAL" and G.walk_judgement(fld, 3, tv)[1].startswith("unresolved expr-uid x1; 3:2 RunScriptSync "
                                                                                 "has a expr target")
    assert _refusal(ents, walkmesh=ground).startswith(on_b("carries walk-in 3:2 (TRIVIAL) -- its tag-2 closure cannot be "
                                                           "judged whole (unresolved expr-uid x1"))
    sender = tread_r15(["RunScriptObjectSync(2, 18)"])
    fld = P.FieldModel.from_bytes(build(sender), 30999)
    tv = P.analyze_root(fld, 3, 2)
    assert P.closure_gaps(tv) == [] and G.walk_judgement(fld, 3, tv) == (
        False, "its scan is open: 3:2 +0 RunScriptObjectSync runs its sender's code (unknown to a root)")
    assert _refusal(sender, walkmesh=ground).startswith(on_b(f"carries walk-in 3:2 ({tv.tier}) -- its tag-2 closure "
                                                             "cannot be judged whole (its scan is open"))


def test_r15_a_party_slot_spawn_opens_the_scan():
    """The closure walk follows no Init* of a party slot (it creates whoever is in the party): the scan cannot see
    what that object runs, so the walk-in -- SCENE-LOCAL by its tier -- is EXPOSED."""
    assert _refusal(tread_r15(["InitObject(251, 0)"]), walkmesh=ground) == on_b(
        "carries walk-in 3:2 (spawn) -- its tag-2 closure cannot be judged whole (its scan is open: 3:2 +0 InitObject "
        "creates a computed or party-slot entry)")


def test_r15_a_covered_move_of_another_object_keeps_the_exemption():
    """A SCENE bucket is a STATEFUL site too (loco_other: the chest's closure moves object 4) -- under both halves it
    is covered, so the template stays exempt (its site is seen, condition (c))."""
    ents = tread_r15(CTRL_GATE + CONFIRM_GATE + ["MoveInstantXZYEx(4, 200, 0, 200)", "AddItem(236, 1)", "Lx:"])
    ents[4] = (2, {0: [f"CreateObject({_u16(-900)}, {_u16(-900)})"]})
    ents[0][1][0].append("InitObject(4, 0)")
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert "loco_other" in P.analyze_root(fld, 3, 2).buckets
    assert judged(ents) == ("STATEFUL", None) and ships(ents)


def test_closure_gaps_names_every_gap_of_the_walk():
    fld = P.FieldModel.from_bytes(build(tread_r15(["op_22(1)"])), 30999)
    tv = P.analyze_root(fld, 3, 2)
    assert P.closure_gaps(tv) == []
    edge = P.Edge((3, 2), 0, 0x14, "RunScriptSync", "party", 2, 251, 5, (), ())
    for kw, want in (({"truncated": True}, "the walk was truncated"),
                     ({"decode_fail": True}, "an instruction or expression failed to decode"),
                     ({"unresolved": (("uid-unknown", 2),)}, "unresolved uid-unknown x2"),
                     ({"edges": (edge,)}, "3:2 RunScriptSync has a party target"),
                     ({"edges": (dataclasses.replace(edge, kind="unknown", uid=200),)},
                      "3:2 RunScriptSync has a unknown target"),
                     ({"edges": (dataclasses.replace(edge, kind="expr", uid=None),)}, "3:2 RunScriptSync has a expr target")):
        assert P.closure_gaps(dataclasses.replace(tv, **kw)) == [want], kw


#: HOLE 2's shapes: a tag 1 a walked op starts, which the closure walk never follows -- (tag 2, entry 7, created by
#: Main_Init too, what the refusal names the walk-in by, the gap)
TAG1_GAPS = {
    "spawned_object": (["InitObject(7, 0)"], (2, {0: [], 1: ["AddItem(236, 1)"]}), False, "spawn",
                       "3:2 InitObject creates 7, whose tag 1 runs when its tag 0 returns"),
    "spawned_code": (["InitCode(7, 0)"], (0, {0: [], 1: ["Battle(1, 2)"]}), False, "spawn",
                     "3:2 InitCode creates 7, whose tag 1 runs when its tag 0 returns"),
    "spawned_with_no_tag_0": (["InitObject(7, 0)"], (2, {1: ["AddItem(236, 1)"]}), False, "spawn",
                              "3:2 InitObject creates 7, whose tag 1 runs when its tag 0 returns"),
    "returned": (["ReturnEntryFunctions(7)"], (2, {0: [], 1: ["AddItem(236, 1)", "Lw:", "op_22(1)", "JMP(Lw)"]}), True,
                 "TRIVIAL", "3:2 ReturnEntryFunctions restarts an entry's tag 1"),
    "returned_in_a_seq": (["RunSharedScript(8)"], (2, {0: [], 1: ["AddItem(236, 1)"]}), True, "TRIVIAL",
                          "8:0 ReturnEntryFunctions restarts an entry's tag 1"),
}


@pytest.mark.parametrize("how", sorted(TAG1_GAPS))
def test_r15_a_tag_1_the_walk_never_follows_is_a_gap(how):
    """HOLE 2, FAIL CLOSED: an Init*-created object runs its tag 1 when its tag 0 returns (EventEngine.Return, stateInit
    -> GetIP(sid, 1), EventEngine.cs:1278-1283) and ReturnEntryFunctions restarts its target's (DoEventCode.cs DRET
    :2172-2181) -- code the closure walk never reaches, so whatever its tier (SCENE-LOCAL, TRIVIAL) the walk-in cannot
    be judged whole: EXPOSED, even under both halves."""
    tag2, seven, at_init, named, gap = TAG1_GAPS[how]
    for lines in (tag2, CTRL_GATE + CONFIRM_GATE + tag2 + ["Lx:"]):
        ents = tread_r15(lines, {7: seven, 8: (0, {0: ["ReturnEntryFunctions(7)"]})})
        if at_init:
            ents[0][1][0].append("InitObject(7, 0)")
        fld = P.FieldModel.from_bytes(build(ents), 30999)
        tv = P.analyze_root(fld, 3, 2)
        assert tv.tier != "STATEFUL" and P.closure_gaps(tv) == [gap] and G.walk_judgement(fld, 3, tv)[1] == gap
        assert _refusal(ents, walkmesh=ground) == on_b(f"carries walk-in 3:2 ({named}) -- its tag-2 closure cannot be "
                                                       f"judged whole ({gap})")


def test_r15_a_spawned_entry_with_no_tag_1_is_no_gap():
    """The control: the same spawn of an entry with no tag 1 leaves nothing unwalked -- under both halves it ships."""
    ents = tread_r15(CTRL_GATE + CONFIRM_GATE + ["InitObject(7, 0)", "Lx:"], {7: (2, {0: ["AddItem(236, 1)"]})})
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert P.closure_gaps(P.analyze_root(fld, 3, 2)) == [] and ships(ents)


#: S1 / S2's shapes: a Seq entry that is not ONE tag 0 -- RunSharedScript builds new Seq(entry, uid) at GetIP(sid, 0),
#: found by TAG id whatever the listed order (EventEngine.cs:1116-1137), and when that tag 0 returns EventEngine.Return
#: (stateInit, :1278-1283) runs GetIP(sid, 1): its tag 1, as the Seq -- while the census walk (verbatim) takes the entry's
#: FIRST listed function. "empty" (an EMPTY entry 8 below a code entry 9) and "out_of_range" (no entry 8 at all) are
#: the closure walk's 'missing' Seq targets -- failed closed with them
SEQ_NOT_ONE_TAG_0 = {
    "tag_1_after_tag_0": (0, {0: [], 1: ["AddItem(236, 1)"]}),
    "tag_1_listed_first": (0, {1: [], 0: ["AddItem(236, 1)"]}),
    "tag_1_only": (0, {1: ["AddItem(236, 1)"]}),
    "empty": "EMPTY",
    "out_of_range": None,
}


def _with_seq8(ents, how) -> dict:
    seq = SEQ_NOT_ONE_TAG_0[how]
    if seq == "EMPTY":
        ents[9] = (0, {0: []})
    elif seq:
        ents[8] = seq
    return ents


def _seq_gap(src) -> str:
    return f"{src} RunSharedScript(8) runs a Seq whose entry is not one tag 0 (its tag 1 runs when its tag 0 returns)"


@pytest.mark.parametrize("how", sorted(SEQ_NOT_ONE_TAG_0))
@pytest.mark.parametrize("gated", [False, True])
def test_r15_a_walk_in_whose_seq_is_not_one_tag_0_is_a_gap(how, gated):
    """S1, FAIL CLOSED: whatever the census tier says (the walk took the entry's first listed function), the Seq runs
    code the walk never saw -- the walk-in cannot be judged whole: EXPOSED, even under both halves."""
    lines = (CTRL_GATE + CONFIRM_GATE + ["RunSharedScript(8)", "Lx:"]) if gated else ["RunSharedScript(8)"]
    ents = _with_seq8(tread_r15(lines), how)
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    tv = P.analyze_root(fld, 3, 2)
    assert P.closure_gaps(tv) == [_seq_gap("3:2")]
    assert (tv.tier == "STATEFUL") is (how == "tag_1_only")          # only there does the census walk reach the item
    assert _refusal(ents, walkmesh=ground) == on_b(f"carries walk-in 3:2 ({G._walkin_effects(tv)}) -- its tag-2 closure "
                                                   f"cannot be judged whole ({_seq_gap('3:2')})")


@pytest.mark.parametrize("how", sorted(SEQ_NOT_ONE_TAG_0))
def test_r15_a_bump_whose_seq_is_not_one_tag_0_is_a_gap_and_touches_everything(how):
    """S1 + S2 on a bump: object 4's tag 2 runs the Seq -- a gap in its closure, and (its own code runs it on its body)
    the object may stand anywhere."""
    ents = _with_seq8(bump_field(["RunSharedScript(8)"]), how)
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    tv = P.analyze_root(fld, 4, 2)
    assert P.closure_gaps(tv) == [_seq_gap("4:2")]
    assert _refusal(ents, walkmesh=ground) == on_b(
        f"may carry bump 4:2 ({G._walkin_effects(tv)}) -- its tag-2 closure cannot be judged whole ({_seq_gap('4:2')}) "
        "-- it runs a "
        "Seq whose entry is not one tag 0 (4:2 RunSharedScript(8))")


def test_r15_a_seq_of_one_tag_0_is_no_gap():
    """The controls: a Seq entry of exactly one tag 0 is walked whole -- a TRIVIAL one ships as a tread and as a bump on
    B, and the gated item inside one is the template (the Seq is entered holding both halves)."""
    one = {8: (0, {0: ["op_22(1)"]})}
    ents = tread_r15(["RunSharedScript(8)"], one)
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert P.closure_gaps(P.analyze_root(fld, 3, 2)) == [] and ships(ents)
    bump = bump_field(["RunSharedScript(8)"])
    bump.update(one)
    assert G._own_code(P.FieldModel.from_bytes(build(bump), 30999), 4)[1] is None and ships(bump)
    gated = tread_r15(CTRL_GATE + CONFIRM_GATE + ["RunSharedScript(8)", "Lx:"], {8: (0, {0: ["AddItem(236, 1)"]})})
    assert judged(gated) == ("STATEFUL", None) and ships(gated)


@pytest.mark.parametrize("order, item_at", [({1: ["op_22(1)"], 0: ["AddItem(236, 1)"]}, "8:0"),
                                            ({0: ["op_22(1)"], 1: ["AddItem(236, 1)"]}, "8:1")])
def test_the_scan_runs_a_seqs_tag_0_by_id_and_then_its_tag_1(order, item_at):
    """S1: watch_scan follows the engine, not the listing -- the Seq's tag 0 found by id, then its tag 1 -- so the item
    the census walk never reaches is a site the exemption sees (and refuses, unguarded)."""
    ents = tread_r15(["RunSharedScript(8)"], {8: (0, dict(order))})
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    tv = P.analyze_root(fld, 3, 2)
    ws = P.watch_scan(fld, 3, 2, spawn=True)
    assert ws.nodes == {(3, 2), (8, 0), (8, 1)} and tv.tier != "STATEFUL"
    assert ws.exempt_why(tv) == f"item at {item_at} {NOT_BOTH}"


@pytest.mark.parametrize("seq, why", [
    ((0, {0: [], 1: ["MoveInstantXZY(200, 0, 200)"]}), "its tag 1 teleports"),
    ((0, {0: [], 1: ["MoveInstantEx(255, 200, 200)"]}), "its tag 1 moves 255: the body"),
    ((0, {0: [], 1: ["MoveInstantXZYEx(255, 200, 0, 200)"]}), "its tag 1 moves 255: the body"),
    ((0, {0: [], 1: ["SetupJump(200, 0, 200, 4)", "Jump()"]}), "its tag 1 jumps"),
    ((0, {1: [], 0: ["MoveInstantXZY(200, 0, 200)"]}), "its tag 0, listed second, teleports"),
    ((0, {0: ["op_1C(255)"], 1: ["MoveInstantXZY(200, 0, 200)"]}), "failed closed: its tag 0 self-ends first"),
])
def test_r15_an_objects_seq_that_is_not_one_tag_0_moves_it_anywhere(seq, why):
    """S2, FAIL CLOSED: _own_code follows a Seq's tag 0 by id, and a Seq entry that is not one tag 0 (its tag 1 runs as
    the Seq on object 4's body when its tag 0 returns) may move the object where its tag-0 walk never says -- its bump
    touches every component, even placed on the arrival ground A."""
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=["RunSharedScript(7)"])
    ents[7] = seq
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    want = "it runs a Seq whose entry is not one tag 0 (4:1 RunSharedScript(7))"
    assert G._own_code(fld, 4)[1] == want and G._moved_elsewhere(fld, 4) == want, why
    assert G._walk_bound(fld, 4) == (set(), want)
    assert _refusal(ents, walkmesh=ground) == on_b(f"may carry bump 4:2 (item) -- {want}")


def test_r15_an_objects_seq_of_one_tag_0_is_followed_by_id():
    """The controls: a one-tag-0 Seq that does not move the object leaves its bump on A (ships); one whose tag 0 moves it
    is a move of its own (refuses with that op), followed into the Seq's tag 0 by id."""
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=["RunSharedScript(7)"])
    ents[7] = (0, {0: ["op_22(1)"]})
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert G._own_code(fld, 4) == ([(4, 0), (4, 2), (4, 1), (7, 0)], None) and ships(ents)
    ents[7] = (0, {0: ["MoveInstantXZY(200, 0, 200)"]})
    assert _refusal(ents, walkmesh=ground) == on_b("may carry bump 4:2 (item) -- its 7:0 runs MoveInstantXZY")


#: V3's same-frame law: each of these breaks the pair between the control test and the poll -- a yield (Wait) either
#: way round, DisableMove after the test, EnableMove after the poll
SPLIT_PAIRS = {
    "control_wait_poll": CTRL_GATE + ["op_22(30)"] + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"],
    "poll_wait_control": CONFIRM_GATE + ["op_22(30)", "SET({B_SYSVAR[2] B_EXPR_END})", "JMP_IFNOT(Lx)",
                                         "AddItem(236, 1)", "Lx:"],
    "control_disablemove_poll": CTRL_GATE + ["DisableMove()"] + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"],
    "poll_enablemove_control": CONFIRM_GATE + ["EnableMove()", "SET({B_SYSVAR[2] B_EXPR_END})", "JMP_IFNOT(Lx)",
                                               "AddItem(236, 1)", "Lx:"],
    # the non-wait yields: RunScript stays until its target accepts (:154-186), WalkEx until the walk ends (:806)
    "control_runscript_poll": CTRL_GATE + ["RunScript(2, 250, 13)"] + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"],
    "control_walkex_poll": CTRL_GATE + ["WalkEx(250, 30, 100, 0, 200, 0)"] + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"],
    # a code past the engine's enum (disasm decodes 0xFF 0x20 as 0x120; DoEventCode's default: return 1)
    "control_op120_poll": CTRL_GATE + ["op_120()"] + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"],
}

#: YIELD_OPS as DERIVED from the engine (EventEngine.DoEventCode.cs split into its case blocks): every case whose block
#: can return non-zero or stay() -- 0x00 0x12 0x14 0x18 0x1A 0x1F 0x20 0x21 0x23 0x24 0x2A 0x2B 0x41 0x44 0x4F
#: 0x50 0x54 0x75 0x8C 0x8F 0x95 0x96 0x97 0xA0 0xA2 0xA5 0xAB 0xAC 0xAE 0xB2 0xB6 0xBC 0xBE 0xDC 0xE8 0xF5 0x117 (its
#: 0x4C hit is a comment's ')': ATTACH returns 0) -- plus EBin's own Wait (jumpToCommand case 34 -> EBin.wait), every
#: opcode with no case (default: return 1, :3387-3390 -- 0x0A 0x0C 0x0E 0x0F 0x11 0x13 0x15 0x17 0x19 0x6E and 0x11F, past
#: the enum), and RunScriptAsync 0x10 (a self-call runs inline and its RET ends the run: Request -> Call,
#: EventEngine.cs:340-372; EBin.jumpToCommand case 4). EVERY code past the enum (EBin.event_code_binary ends at
#: REMOVE_STATUS 0x11E) is the default case too: disasm.read_code decodes 0xFF XX as 0x100 | XX for any XX, so a decoded
#: op can be anything up to 0x1FF -- pressclosure.is_yield counts 0x11F..0x1FF whatever YIELD_OPS lists
ENGINE_YIELD_OPS = frozenset({
    0x00, 0x12, 0x14, 0x18, 0x1A, 0x1F, 0x20, 0x21, 0x23, 0x24, 0x2A, 0x2B, 0x41, 0x44, 0x4F, 0x50, 0x54, 0x75, 0x8C, 0x8F,
    0x95, 0x96, 0x97, 0xA0, 0xA2, 0xA5, 0xAB, 0xAC, 0xAE, 0xB2, 0xB6, 0xBC, 0xBE, 0xDC, 0xE8, 0xF5, 0x117,
    0x22,
    0x0A, 0x0C, 0x0E, 0x0F, 0x11, 0x13, 0x15, 0x17, 0x19, 0x6E, 0x11F,
    0x10})


def test_yield_ops_is_the_engines_derived_set():
    """EXACT, not a subset: a yield dropped lets one half survive into another frame (a guest's control can change
    there), a yield added refuses more than the engine needs -- either is a change to argue against the derivation
    above (ENGINE_YIELD_OPS), not to make quietly."""
    assert P.YIELD_OPS == ENGINE_YIELD_OPS, sorted(hex(o) for o in P.YIELD_OPS ^ ENGINE_YIELD_OPS)
    from ff9mapkit.eb._optables import OP_ARG_COUNT
    assert P.OP_PAST_ENUM == len(OP_ARG_COUNT) == 0x11F
    assert {op for op in range(0x200) if P.is_yield(op)} == ENGINE_YIELD_OPS | set(range(0x11F, 0x200))


@pytest.mark.parametrize("how", sorted(SPLIT_PAIRS))
def test_r15_the_two_halves_must_be_proved_in_one_frame(how):
    """V3: FilterScriptButtons decides the mask at the KEYON read (NetSyncField.cs:858), so a user-control test proves
    nothing about a poll another frame (or a control write) away -- the D3 shape and its mirror images refuse."""
    ents = tread_r15(SPLIT_PAIRS[how])
    assert judged(ents) == ("STATEFUL", f"item at 3:2 {NOT_BOTH}")
    assert _refusal(ents, walkmesh=ground) == on_b("carries walk-in 3:2 (item)")


def test_r15_the_pair_once_proved_survives_the_chests_own_waits():
    """The controls: Bubble does not yield (EventEngine.DoEventCode.cs FICON :1889-1902 returns 0), so the chest
    template keeps its pair across it; and once BOTH hold the path is out of every guest's reach, so the stock chest's
    own tail -- DisableMove, Wait, a RunScriptSync to the player (entered holding the pair), WaitAnimation -- stays
    covered."""
    assert 0x68 not in P.YIELD_OPS and {0x00, 0x14, 0x1F, 0x22, 0x41, 0x54, 0x23, 0xDC} <= P.YIELD_OPS
    tail = CTRL_GATE + ["Bubble(1)"] + CONFIRM_GATE + ["DisableMove()", "op_22(1)", "RunScriptSync(2, 250, 13)",
                                                       "WaitAnimation()", "op_22(2)", "AddItem(236, 1)",
                                                       "WindowSync(7, 0, 4)", "Lx:"]
    ents = tread_r15(tail)
    ents[2][1][13] = ["AddItem(237, 1)", "WindowSync(7, 0, 5)"]
    assert judged(ents) == ("STATEFUL", None) and ships(ents)


@pytest.mark.parametrize("call, callee", [
    ("RunScriptSync(2, 250, 13)", {2: [(13, CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"])]}),
    ("RunSharedScript(7)", {7: (0, {0: CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"]})}),
])
def test_r15_one_half_does_not_carry_into_a_callee(call, callee):
    """A callee runs in a later segment (EventEngine.Request -> Call only sets its ip), so a user-control test before
    the call and the poll inside it are never one frame: only the proved PAIR carries (pressclosure.carried)."""
    ents = tread_r15(CTRL_GATE + [call])
    for e, spec in callee.items():
        if isinstance(spec, list):
            for tag, lines in spec:
                ents[e][1][tag] = list(lines)
        else:
            ents[e] = spec
    tier, why = judged(ents)
    assert tier == "STATEFUL" and why.startswith("item at ") and why.endswith(NOT_BOTH)
    assert _refusal(ents, walkmesh=ground).startswith(on_b("carries walk-in 3:2 (item)"))


#: a self-call's callee: control off, then a 30-frame wait -- it runs INLINE, on the caller's own run
SELF_CALLEE = ["DisableMove()", "op_22(30)"]


@pytest.mark.parametrize("tag2, callee", [
    (CTRL_GATE + ["RunScriptAsync(0, 255, 5)"] + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"], SELF_CALLEE),
    (CTRL_GATE + ["RunScriptAsync(0, 3, 5)"] + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:"], SELF_CALLEE),   # its own uid
    (CONFIRM_GATE + ["RunScriptAsync(0, 255, 5)", "SET({B_SYSVAR[2] B_EXPR_END})", "JMP_IFNOT(Lx)", "AddItem(236, 1)",
                     "Lx:"], ["EnableMove()", "op_22(30)"]),                                             # the mirror
])
def test_r15_a_self_runscriptasync_between_the_halves_is_a_yield(tag2, callee):
    """V3 / HOLE 1: RunScriptAsync returns 0, but when its uid names the executing object Request -> Call points the
    CURRENT object's ip at the callee (EventEngine.cs:340-372): it runs inline and its RET ends the run (EBin case 4:
    Return + adfr), so the caller resumes in a later frame -- a yield between the test and the poll (YIELD_OPS)."""
    ents = tread_r15(tag2)
    ents[3][1][5] = list(callee)
    assert 0x10 in P.YIELD_OPS
    assert judged(ents) == ("STATEFUL", f"item at 3:2 {NOT_BOTH}")
    assert _refusal(ents, walkmesh=ground) == on_b("carries walk-in 3:2 (item)")


def test_r15_a_self_runscriptasync_after_the_pair_keeps_it():
    """The control: once both halves are proved the path is out of every guest's reach, so the same self-call after
    them (callee and all) stays covered and the template ships."""
    ents = tread_r15(CTRL_GATE + CONFIRM_GATE + ["RunScriptAsync(0, 255, 5)", "AddItem(236, 1)", "Lx:"])
    ents[3][1][5] = list(SELF_CALLEE)
    assert judged(ents) == ("STATEFUL", None) and ships(ents)


def test_r15_a_keyoff_poll_is_no_half():
    """B_KEYOFF never passes through FilterScriptButtons (EBin.cs:1125-1129): a guest's own release reaches it at
    control-on, so a chest polling it is not the hidden-item template."""
    keyoff = [ln.replace("B_KEYON", "B_KEYOFF") for ln in CHEST]
    assert judged(bump_field(keyoff), 4) == ("STATEFUL", f"item at 4:2 {NOT_BOTH}")
    assert _refusal(bump_field(keyoff), walkmesh=ground) == on_b("carries bump 4:2 (window, item)")


def test_r15_a_key_poll_is_a_half_as_keyon_is():
    """B_KEY goes through FilterScriptButtons as B_KEYON does (EBin.cs:1131-1140, FILTERED_KEY_OPS): F1 strips its
    constant Confirm | Special at control-on, so the chest polling it is the template and ships."""
    held = [ln.replace("B_KEYON", "B_KEY") for ln in CHEST]
    assert judged(bump_field(held), 4) == ("STATEFUL", None) and ships(bump_field(held))


# ================================================================================================ R15: the placements
def test_r15_a_landing_in_a_function_whose_cfg_does_not_build_is_final():
    fld = P.FieldModel.from_bytes(build(r15_field(None, body=["SetupJump(5000, 0, 5000, 4)", "Jump()",
                                                              "SetupJump(100, 0, 200, 4)", "Jump()"])))
    v = P.analyze_regions(fld)[0]
    assert [final for (*_, final) in G.landing_points(fld, v)] == [False, True]
    fld._flows[(2, 17)] = None
    assert [final for (*_, final) in G.landing_points(fld, v)] == [True, True]


@pytest.mark.parametrize("line, why", [
    ("AttachObject(4, 2, 5)", "0:1 runs AttachObject on it"),
    ("MoveInstantXZYEx({Map.Int16[8] B_EXPR_END}, 200, 0, 200)", "0:1 runs MoveInstantXZYEx on it"),
])
def test_r15_an_ex_or_attach_op_that_can_name_a_bump_touches_everything(line, why):
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750))
    ents[0][1][1] = [line]
    assert _refusal(ents, walkmesh=ground) == on_b(f"may carry bump 4:2 (item) -- {why}")


def test_r15_a_move_its_tag_0_walk_cannot_place_loses_the_point():
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750), extra0=["WalkTowardObject(2)"])
    assert _refusal(ents, walkmesh=ground) == on_b("may carry bump 4:2 (item) -- 4:0 leaves it at no known point on "
                                                   "some path")


def test_r15_a_placement_walk_past_its_cap_touches_everything(monkeypatch):
    two = bump_field(STATEFUL_TREAD)
    two[4][1][0] = ["SET({Global.Bit[9000] B_EXPR_END})", "JMP_IFNOT(Lq)", f"CreateObject({_u16(-750)}, {_u16(-750)})",
                    "JMP(Lj)", "Lq:", f"CreateObject({_u16(-700)}, {_u16(-700)})", "Lj:"]
    assert ships(two)                                          # both branches stand it on A
    monkeypatch.setattr(G, "_ENV_CAP", 1)
    assert _refusal(two, walkmesh=ground) == on_b("may carry bump 4:2 (item) -- 4:0 has more paths than the placement "
                                                  "walk follows")


def test_r15_a_bump_whose_tag_0_cfg_does_not_build_touches_everything():
    fld = P.FieldModel.from_bytes(build(bump_field(STATEFUL_TREAD, at=(-750, -750))), 30999)
    gr = G.Ground(ground())
    assert G.bump_touched(fld, 4, gr) == ({comp(gr, "A")}, None)
    fld._flows[(4, 0)] = None
    assert G.bump_touched(fld, 4, gr) == (set(gr.walkable), "4:0's CFG does not build")


# ================================================================================================ R15: the walker bound (V1)
#: a floor 50 u off A's +x edge, at height ``y`` (1000 u above A at -1000: y is DOWN in the script frame)
NEAR_B = [(-450, 0, -1000), (0, 0, -1000), (0, 0, -500), (-450, 0, -500)]
CHASER = ["Lw:", "Walk({obj(uid=250).f[0] B_EXPR_END}, {obj(uid=250).f[2] B_EXPR_END})", "op_22(1)", "JMP(Lw)"]


def near(y):
    from ff9mapkit.scene import bgi
    return lambda: bgi.build(GROUND_A + [(x, y, z) for (x, _y, z) in NEAR_B], [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)])


def chaser_field(y, tag1=CHASER, extra0=()) -> dict:
    """bump_field: object 4 created on A, chasing the player in its tag 1; the row's jump lands on NEAR_B at ``y``."""
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=list(tag1), extra0=extra0)
    ents[2][1][17] = [f"SetupJump({_u16(-200)}, {_u16(y)}, {_u16(-750)}, 4)", "Jump()"]
    return ents


def test_r15_a_chaser_is_held_to_its_region_reach_and_height_window():
    """V1: a walker moved only by its own pathing-on Walk stays on the tris its placement reaches (A); its bump fires
    within its reach AND WalkMesh.Collision's -400 < dy < 400 window -- B 50 u off A's edge but 1000 u above it is out of
    it (the 1209 shape), the same B at A's height is not; a pathing-off op in its code lifts the bound."""
    assert ships(chaser_field(-1000), near(-1000))
    assert _refusal(chaser_field(0), walkmesh=near(0)) == \
        f"R15 walk-in: landing component {G.Ground(near(0)()).comp_of[2]} (not an arrival) carries bump 4:2 (item)"
    # the window's edge, exactly: WalkMesh.cs:919-920 bumps only for -400 < dy < 400 (BUMP_DY), so a floor 400 u above
    # A is out of it and one 399 u above is in
    assert G.BUMP_DY == 400 and ships(chaser_field(-400), near(-400))
    assert _refusal(chaser_field(-399), walkmesh=near(-399)) == \
        f"R15 walk-in: landing component {G.Ground(near(-399)()).comp_of[2]} (not an arrival) carries bump 4:2 (item)"
    for off in (["SetPathing(0)"] + CHASER, CHASER + ["SetupJump(100, 0, 200, 4)", "Jump()"]):
        assert _refusal(chaser_field(-1000, off), walkmesh=near(-1000)) == (
            f"R15 walk-in: landing component {G.Ground(near(-1000)()).comp_of[2]} (not an arrival) may carry bump 4:2 "
            "(item) -- its 4:1 runs Walk")
    replaced = chaser_field(-1000, CHASER[:1] + [f"CreateObject({_u16(-150)}, {_u16(-750)})"] + CHASER[1:])
    assert not ships(replaced, near(-1000))                    # a constant CreateObject on B is a placement point too
    assert ships(bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=CHASER))  # B 500 u off: past its 443 u reach
    from ff9mapkit.scene import bgi
    diag = [(-150, 0, -150), (250, 0, -150), (250, 0, 250), (-150, 0, 250)]   # 350 u off A in x AND z: 495 u away
    corner = bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=CHASER)
    corner[2][1][17] = ["SetupJump(100, 0, 100, 4)", "Jump()"]
    assert ships(corner, lambda: bgi.build(GROUND_A + diag, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)]))
    idiom = bump_field(STATEFUL_TREAD, place="CreateObject({Map.Int16[0] B_EXPR_END}, {Map.Int16[4] B_EXPR_END})",
                       tag1=CHASER)                           # 1209's own placement: constants through Map vars
    idiom[4][1][0] = [f"SET({{Map.Int16[0] const({_u16(-750)}) B_LET B_EXPR_END}})",
                      f"SET({{Map.Int16[4] const({_u16(-750)}) B_LET B_EXPR_END}})"] + idiom[4][1][0]
    assert ships(idiom)
    for unbounded in (bump_field(STATEFUL_TREAD, at=(5000, 5000), tag1=CHASER),           # created off the walkmesh
                      bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=CHASER,            # pathing off in its tag 0
                                 extra0=[f"MoveInstantXZY({_u16(-750)}, 0, {_u16(-750)})"])):
        assert _refusal(unbounded, walkmesh=ground) == on_b("may carry bump 4:2 (item) -- its 4:1 runs Walk")


def bridged(flags=0x8001):
    """STRIP, its bridge (floor 1, tris 2-3) re-flagged: 0x8001 blocks the PLAYER only (high-byte bit 0x80) -- an NPC
    walks across; 0 is inactive for both."""
    def wm():
        m = strip()
        for t in (2, 3):
            m.tris[t].tri_flags = flags
        return m
    return wm


def strip_walker(init=(), more=None) -> dict:
    """bump_field on the strip: the player spawned on A, object 4 created on A chasing it (CHASER), Main_Init's tag 0
    extended by ``init`` and other functions set from ``more`` -- a key ``tag`` is entry 0's, ``(entry, tag)`` any
    entry's (the walker's own 4, the player's 2, the press region's 1)."""
    ents = bump_field(STATEFUL_TREAD, place=f"CreateObject({_u16(-900)}, 200)", tag1=CHASER)
    ents[2][1][0] = [*SPAWN_STRIP_A, "SetModel(8, 61)", "DefinePlayerCharacter()"]
    ents[0][1][0] = ents[0][1][0] + list(init)
    for key, lines in (more or {}).items():
        e, tag = key if isinstance(key, tuple) else (0, key)
        ents[e][1][tag] = list(lines)
    return ents


#: Main_Init's disable on one branch only: the arm a JMP_IFNOT falls into, the arm a JMP_IF takes (the work list reaches
#: it before the join), and an arm that ends the function -- the MUST dataflow keeps none of them
_ON_ONE_ARM = {
    "fall": ["SET({Global.Bit[9000] B_EXPR_END})", "JMP_IFNOT(Lq)", "EnablePath(1, 0)", "Lq:"],
    "taken": ["SET({Global.Bit[9000] B_EXPR_END})", "JMP_IF(Lq)", "JMP(Lj)", "Lq:", "EnablePath(1, 0)", "Lj:"],
    "ended": ["SET({Global.Bit[9000] B_EXPR_END})", "JMP_IFNOT(Lq)", "EnablePath(1, 0)", "RET()", "Lq:"],
}


@pytest.mark.parametrize("init, more, ok", [
    ([], {}, False),                                          # the bridge is open to a walker: B is in its region
    (["EnablePath(1, 0)"], {}, True),                         # Main_Init takes it off before any object has run
    (["op_22(1)", "EnablePath(1, 0)"], {}, False),            # ... after a yield: a walker may already be on it
    (["EnablePath(1, 0)"], {1: ["EnablePath(1, 1)"]}, False),  # ... and some code can put it back
    (["EnablePath(1, 0)"], {1: ["EnablePathTriangle({Map.Int16[8] B_EXPR_END}, 1)"]}, False),
    (["EnablePath(1, 0)"], {1: ["EnablePath(1, {Map.Int16[8] B_EXPR_END})"]}, False),   # a computed flag may be 1
    (["EnablePath(1, 0)"], {1: ["op_10A(0, 0)"]}, False),     # BAFRAME turns an animation frame's tris on
    (["EnablePath(1, 0)"], {10: ["op_22(1)"]}, False),        # Main_Reinit restarts the room and never takes it off
    (["EnablePath(1, 0)"], {10: ["EnablePath(1, 0)"]}, True),
    (_ON_ONE_ARM["fall"], {}, False),
    (_ON_ONE_ARM["taken"], {}, False),
    (_ON_ONE_ARM["ended"], {}, False),
    (["op_1C(255)", "EnablePath(1, 0)"], {}, False),         # Main_Init ends itself first: the disable never runs
    (["op_120()", "EnablePath(1, 0)"], {}, False),            # ... after a code past the enum (default: return 1)
    # the re-enable in a function OTHER than entry 0's: activatable sweeps every function of the field
    (["EnablePath(1, 0)"], {(4, 7): ["EnablePath(1, 1)"]}, False),                             # the walker's own
    (["EnablePath(1, 0)"], {(2, 9): ["EnablePathTriangle(2, 1)", "EnablePathTriangle(3, 1)"]}, False),   # the player's
    (["EnablePath(1, 0)"], {(1, 9): ["EnablePath(1, {Map.Int16[8] B_EXPR_END})"]}, False),     # a region's
    (["EnablePath(1, 0)"], {(4, 7): ["op_10A(0, 0)"]}, False),
])
def test_r15_a_walker_crosses_what_only_the_player_cannot(init, more, ok):
    """An NPC is blocked by high-byte bit 0x40 only (WalkMesh.BGI_findAccessibleTriangle, WalkMesh.cs:1155-1169): a
    player-blocked bridge joins two player components for a walker. Only a tri Main_Init (and Main_Reinit, after a
    battle) takes off before its first yield on every path, and that nothing can turn back on (walker_blocks), holds
    it -- the 1209 question. An inactive bridge holds it on its own."""
    ents = strip_walker(init, more)
    assert G.Ground(bridged()()).comp_of[0] != G.Ground(bridged()()).comp_of[4]
    assert ships(ents, bridged()) is ok
    if not init and not more:
        assert ships(ents, bridged(0))


@pytest.mark.parametrize("init, more, ok", [
    ([], {}, True),                                           # nothing turns the bridge on: the walker stays on A
    (["EnablePath(1, 0)"], {}, True),
    ([], {1: ["EnablePath(1, 1)"]}, False),                   # some code turns it on: a walker crosses
    (["EnablePath(1, 1)"], {}, False),
    ([], {1: ["EnablePathTriangle(2, 1)", "EnablePathTriangle(3, 1)"]}, False),
    ([], {1: ["EnablePath(1, {Map.Int16[8] B_EXPR_END})"]}, False),
    ([], {1: ["EnablePathTriangle({Map.Int16[8] B_EXPR_END}, 1)"]}, False),
    ([], {1: ["op_10A(0, 0)"]}, False),
    # the source in a function OTHER than entry 0's (the walker's own tag, the player's, a region's)
    ([], {(4, 7): ["EnablePath(1, 1)"]}, False),
    ([], {(2, 9): ["EnablePathTriangle(2, 1)", "EnablePathTriangle(3, 1)"]}, False),
    ([], {(1, 9): ["EnablePath(1, {Map.Int16[8] B_EXPR_END})"]}, False),
    ([], {(1, 9): ["EnablePathTriangle({Map.Int16[8] B_EXPR_END}, 1)"]}, False),
    ([], {(4, 7): ["op_10A(0, 0)"]}, False),
    ([], {(2, 9): ["op_10A(0, 0)"]}, False),
])
@pytest.mark.parametrize("flags", [0x8000, 0])
def test_r15_a_walker_steps_onto_what_code_can_turn_on(init, more, ok, flags):
    """HOLE 4: a bridge INACTIVE in the walkmesh (0x8000: player-blocked as well; 0: not) still joins A and B for a walker
    once code can turn it on (guest_traversal.activatable) -- an EnablePath / EnablePathTriangle whose flag is not the
    constant 0 (DoEventCode.cs:2661-2678), a computed tri or floor, any BAFRAME (0x10A -> WalkMesh.BGI_animShowFrame,
    :3184-3187, WalkMesh.cs:1081-1121), in ANY function of the field. Ground.region steps onto it, and walker_blocks never
    blocks it; activatable itself names the bridge exactly when code can turn it on (a BAFRAME field is refused whole,
    ground_unnamed, so the sweep is pinned here too)."""
    ents = strip_walker(init, more)
    assert ships(ents, bridged(flags)) is ok
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert ({2, 3} <= G.activatable(fld, bridged(flags)())) is not ok


def test_r15_the_engines_own_tri_switches_count(monkeypatch):
    """The engine's per-field hot-fixes turn tris on whatever the script says (HOTFIX_ON_TRIS, each cited where it is
    defined): on a field they name, the walker crosses a bridge no script turns on, and walker_blocks lets Main_Init's
    disable of it go."""
    assert G.HOTFIX_ON_TRIS == {900: {62}, 2803: {105, 106}, 1421: {109, 110}, 1606: {107}, 1753: {208}}
    ents, blocked = strip_walker(), strip_walker(["EnablePath(1, 0)"])
    assert ships(ents, bridged(0x8000)) and ships(blocked, bridged())
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert G.activatable(fld, bridged(0x8000)()) == frozenset()
    monkeypatch.setitem(G.HOTFIX_ON_TRIS, 30999, frozenset({2, 3}))
    assert G.activatable(fld, bridged(0x8000)()) == {2, 3}
    assert not ships(ents, bridged(0x8000)) and not ships(blocked, bridged())


def test_r15_a_function_that_does_not_decode_may_turn_any_tri_on():
    """FAIL CLOSED: an undecodable function could hold any EnablePath, so activatable is every tri."""
    fld = P.FieldModel.from_bytes(build(strip_walker()), 30999)
    assert G.activatable(fld, bridged(0x8000)()) == frozenset()
    fld._instrs[(0, 1)] = None
    assert fld.decode_failed(0, 1) and G.activatable(fld, bridged(0x8000)()) == frozenset(range(6))


@pytest.mark.parametrize("seq, why", [
    ({7: (0, {0: ["MoveInstantXZY(200, 0, 200)"]})}, "its 7:0 runs MoveInstantXZY"),
    (None, "it runs a Seq of a computed entry"),
    ({7: (0, {0: ["MoveInstantEx(255, 200, 200)"]})}, "7:0 runs MoveInstantEx on it"),
    ({7: (0, {0: ["MoveInstantXZYEx(255, 200, 0, 200)"]})}, "7:0 runs MoveInstantXZYEx on it"),
])
def test_r15_a_seq_an_object_runs_moves_the_object_itself(seq, why):
    """RunSharedScript keeps its caller's body (EBin.ProcessCode objV0): a Seq object 4 runs teleports object 4, which
    its tag-0 walk never sees -- and a Seq of a computed entry may run anything on it. Inside the Seq uid 255 is that
    body too (GetObjUID returns gCur = objV0, EventEngine.cs:959-962), so its Ex op on 255 moves object 4."""
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=["RunSharedScript(7)" if seq else
                                                             "RunSharedScript({Map.Int16[8] B_EXPR_END})"])
    ents.update(seq or {})
    assert _refusal(ents, walkmesh=ground) == on_b(f"may carry bump 4:2 (item) -- {why}")


@pytest.mark.parametrize("op", ["MoveInstantEx(255, 200, 200)", "MoveInstantXZYEx(255, 200, 0, 200)", "WalkToExit()"])
def test_r15_a_move_of_255_in_someone_elses_seq_leaves_the_bump_where_it_is(op):
    """The control: the same Seq run by ANOTHER entry (5) moves entry 5's body, not object 4's -- its bump stays on A."""
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750))
    ents[5] = (0, {0: [], 1: ["RunSharedScript(7)"]})
    ents[7] = (0, {0: [op]})
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert G._moved_elsewhere(fld, 4) is None and ships(ents)


def test_r15_a_walker_that_moves_another_object_is_still_a_walker():
    """An Ex op in a walker's own code is judged by the uid it moves (_ex_named), not as a move of the walker: the
    chaser that also teleports object 5 is still held to A (and the same op on 255 is not)."""
    ents = bump_field(STATEFUL_TREAD, at=(-750, -750), tag1=CHASER[:1] + ["MoveInstantEx(5, 200, 200)"] + CHASER[1:])
    ents[5] = (2, {0: [f"CreateObject({_u16(-900)}, {_u16(-900)})"]})
    ents[0][1][0].append("InitObject(5, 0)")
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert G._walk_bound(fld, 4) == (set(), None) and ships(ents)
    ents[4][1][1] = CHASER[:1] + ["MoveInstantEx(255, 200, 200)"] + CHASER[1:]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert G._walk_bound(fld, 4) == (set(), "4:1 runs MoveInstantEx on it")
    assert _refusal(ents, walkmesh=ground) == on_b("may carry bump 4:2 (item) -- its 4:1 runs Walk")


# ================================================================================================ R15: ground code can turn on (S3)
#: over the strip's bridge (floor 1, tris 2-3) only; ... and over its tri 3 only (A's side of its diagonal): a footprint
#: whose one tri borders A alone, and reaches C only through the bridge's other tri
BRIDGE_POLY = [(-450, 100), (-50, 100), (-50, 300), (-450, 300)]
BRIDGE_CORNER = [(-480, 300), (-400, 300), (-400, 380), (-480, 380)]
#: A, a LONG bridge (floor 1: 1500 u, past a bump's 443 u reach from its middle) and C, sharing their edges
LONG_STRIP = [(-2000, 0, 0), (-2000, 0, 400), (-1500, 0, 0), (-1500, 0, 400), (0, 0, 0), (0, 0, 400), (400, 0, 0),
              (400, 0, 400)]
#: A, then 50 u apart an island I (floor 1) that shares its far edge with C (floor 2): I is no neighbour of A
GAP_ISLAND = [(-1000, 0, 0), (-1000, 0, 400), (-500, 0, 0), (-500, 0, 400), (-450, 0, 0), (-450, 0, 400), (-50, 0, 0),
              (-50, 0, 400), (350, 0, 0), (350, 0, 400)]
GAP_ISLAND_FACES = [(0, 2, 3), (0, 3, 1), (4, 6, 7), (4, 7, 5), (6, 8, 9), (6, 9, 7)]


def _off_floor_1(verts, faces):
    """A walkmesh of ``verts`` / ``faces`` on floors 0, 1, 2 whose floor 1 (tris 2-3) is INACTIVE (triFlags 0)."""
    def wm():
        from ff9mapkit.scene import bgi
        m = bgi.build(verts, faces, floor_ids=[0, 0, 1, 1, 2, 2])
        for t in (2, 3):
            m.tris[t].tri_flags = 0
        return m
    return wm


@pytest.mark.parametrize("poly", [BRIDGE_POLY, BRIDGE_CORNER], ids=["bridge", "corner"])
@pytest.mark.parametrize("where", [(0, 1), (2, 9), (3, 9)])       # Main_Init's tag 1, the player's, the tread's own
def test_r15_a_tread_over_a_tri_code_can_turn_on_touches_what_it_borders(where, poly):
    """S3, the player-side HOLE 4: a tread whose area lies only on a statically INACTIVE tri fires once code turns that
    tri on (activatable) -- it touches the walkable components its run of such tris borders (Ground.foot / _comps), here
    A and the landing C (the corner footprint through the bridge's other tri). With nothing turning the bridge on it is
    over no ground at all and ships."""
    ents = r15_field(STATEFUL_TREAD, poly=poly, spawn=SPAWN_STRIP_A, body=["SetupJump(200, 0, 200, 4)", "Jump()"])
    assert ships(ents, bridged(0))
    ents[where[0]][1][where[1]] = ["EnablePath(1, 1)"]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    gr = G.field_ground(fld, bridged(0)())
    assert gr.enabled == {2, 3} and not any(gr.static_walk[t] for t in (2, 3)) and gr.foot[2] and gr.foot[3]
    assert gr.touched(poly) == {gr.comp_of[0], gr.comp_of[4]}
    assert _refusal(ents, walkmesh=bridged(0)) == (f"R15 walk-in: landing component {gr.comp_of[4]} (not an arrival) "
                                                   "carries walk-in 3:2 (item)")


@pytest.mark.parametrize("where", [(0, 1), (4, 7), (2, 9)])       # Main_Init's tag 1, the object's own, the player's
def test_r15_a_bump_on_a_tri_code_can_turn_on_reaches_what_it_borders(where):
    """S3 for a bump (Ground.near): object 4 stands in the middle of a long inactive bridge, 750 u from A and from C --
    beyond its 443 u reach of both. Once code can turn the bridge on, the bridge stands for A and C."""
    ents = bump_field(STATEFUL_TREAD, at=(-750, 200))
    ents[2][1][0] = [f"CreateObject({_u16(-1750)}, 200)", "SetModel(8, 61)", "DefinePlayerCharacter()"]
    wm = _off_floor_1(LONG_STRIP, STRIP_FACES)
    assert ships(ents, wm)
    ents[where[0]][1][where[1]] = ["EnablePath(1, 1)"]
    gr = G.field_ground(P.FieldModel.from_bytes(build(ents), 30999), wm())
    assert gr.near(-750, 200, 443) == {gr.comp_of[0], gr.comp_of[4]}
    assert _refusal(ents, walkmesh=wm) == (f"R15 walk-in: landing component {gr.comp_of[4]} (not an arrival) carries "
                                           "bump 4:2 (item)")


#: A, a bridge (floor 1), B, a second strip (floor 3, NPC-only: 0x8001) and C (floor 4) in a row, sharing their edges
FAR_XS = [-1000, -500, 0, 400, 900, 1300]


def far_strip(bridge_flags):
    """FAR_XS as a strip of five floors: the bridge (tris 2-3) flagged ``bridge_flags``, the second strip (tris 6-7)
    0x8001 -- a walker crosses it, the player does not -- so A, B and C (tris 8-9) are three player components."""
    def wm():
        from ff9mapkit.scene import bgi
        verts = [(x, 0, z) for x in FAR_XS for z in (0, 400)]
        faces = [f for k in range(5) for f in ((2 * k, 2 * k + 2, 2 * k + 3), (2 * k, 2 * k + 3, 2 * k + 1))]
        m = bgi.build(verts, faces, floor_ids=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
        for t in (2, 3):
            m.tris[t].tri_flags = bridge_flags
        for t in (6, 7):
            m.tris[t].tri_flags = 0x8001
        return m
    return wm


@pytest.mark.parametrize("init, more, flags", [
    (["EnablePath(1, 0)"], {1: ["EnablePath(1, 1)"]}, 0x8001),   # Main_Init's disable, put back: walker_blocks lets go
    ([], {1: ["EnablePath(1, 1)"]}, 0),                          # inactive, turned on: Ground.region steps onto it
])
def test_r15_a_walker_crosses_a_bridge_code_turns_on_and_goes_on_beyond_it(init, more, flags):
    """The bridge itself is a FOOTPRINT tri once code can turn it on (S3), so a walker on A already bumps into a player on
    it -- the bridge stands for A and B. What only the walker's REGION sees is the ground past B: across the NPC-only
    strip to C, 900 u off A (out of its reach) and the row's landing. With the bridge's switch on the walker gets there
    and the row refuses; without it (Main_Init's disable stands, or nothing turns the inactive bridge on) it ships."""
    ents = strip_walker(init, more)
    ents[2][1][17] = ["SetupJump(1100, 0, 200, 4)", "Jump()"]
    gr = G.Ground(far_strip(flags)())
    assert _refusal(ents, walkmesh=far_strip(flags)) == (f"R15 walk-in: landing component {gr.comp_of[8]} (not an "
                                                         "arrival) carries bump 4:2 (item)")
    control = strip_walker(init)
    control[2][1][17] = list(ents[2][1][17])
    assert ships(control, far_strip(flags))


@pytest.mark.parametrize("where", [(0, 1), (4, 7), (2, 9)])
def test_r15_a_walker_bumps_into_a_tri_code_can_turn_on(where):
    """S3 for a walker (Ground.walker_touched): the chaser stays on A (the island I is no neighbour), but a player
    standing on I -- 50 u off A, once code turns it on -- is within its reach, and I borders C (the landing), which is
    450 u off A: out of reach on its own."""
    ents = strip_walker()
    ents[2][1][17] = ["SetupJump(150, 0, 200, 4)", "Jump()"]
    wm = _off_floor_1(GAP_ISLAND, GAP_ISLAND_FACES)
    assert ships(ents, wm)
    ents[where[0]][1][where[1]] = ["EnablePath(1, 1)"]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    gr = G.field_ground(fld, wm())
    assert gr.region([0]) == {0, 1} and gr.walker_touched({0, 1}, G.bump_reach(fld, 4)) == {gr.comp_of[0], gr.comp_of[4]}
    assert _refusal(ents, walkmesh=wm) == (f"R15 walk-in: landing component {gr.comp_of[4]} (not an arrival) carries "
                                           "bump 4:2 (item)")


# ================================================================================================ R15: BAFRAME, field-wide (S4)
@pytest.mark.parametrize("where", [(0, 1), (2, 9), (1, 9)])       # Main_Init's tag 1, the player's, the press region's
@pytest.mark.parametrize("body", [JUMP_B, [f"SetupJump({_u16(-750)}, 0, {_u16(-750)}, 4)", "Jump()"]], ids=["to_b", "to_a"])
def test_r15_a_field_that_runs_baframe_refuses_every_row(where, body):
    """S4, FAIL CLOSED at FIELD level: BAFRAME carries every pathing-on actor on the old frame's tris to the new frame's
    (WalkMesh.BGI_animUpdateCharacters, WalkMesh.cs:1423-1455) and rewires the neighbour links (BGI_animUpdateNeighbors,
    :1457-1482) -- no component, placement or landing is the static walkmesh's -- so every row of such a field refuses,
    the one that lands on new ground and the one that lands on the arrival ground alike, with no walk-in at all."""
    ents = r15_field(None, body=body)
    assert ships(ents)
    ents[where[0]][1][where[1]] = ["op_10A(0, 1)"]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert G.ground_unnamed(fld) == f"{where[0]}:{where[1]} +0 runs BAFRAME (0x10A)"
    assert G.activatable(fld, ground()) == frozenset(range(4))
    assert _refusal(ents, walkmesh=ground) == G.UNNAMED_GROUND + f"{where[0]}:{where[1]} +0 runs BAFRAME (0x10A)"


def test_r15_a_function_that_does_not_decode_refuses_every_row():
    """S4's other half: a function that does not decode may run BAFRAME -- the field's ground is unnamed too."""
    fld = P.FieldModel.from_bytes(build(r15_field(None)), 30999)
    v = P.analyze_regions(fld)[0]
    gr = G.field_ground(fld, ground())
    assert gr.unnamed is None and G.walkin(fld, v, gr, G.field_arrival(fld, gr), G.walk_ins(fld, gr))["why"] is None
    fld._instrs[(0, 1)] = None
    gr = G.field_ground(fld, ground())
    assert gr.unnamed == G.ground_unnamed(fld) == "0:1 does not decode (it may run BAFRAME or a walkmesh sim)"
    w = G.walkin(fld, v, gr, G.field_arrival(fld, gr), G.walk_ins(fld, gr))
    assert w["why"] == G.UNNAMED_GROUND + "0:1 does not decode (it may run BAFRAME or a walkmesh sim)" and w["land"] == set(gr.walkable)


@pytest.mark.parametrize("op, args", [(0x102, "0, 1"), (0x103, "0, 13"), (0x104, "0, 1"), (0x105, "0, 256"),
                                      (0x106, "0, 0"), (0x107, "0, 0, 100"), (0x108, "0, 0")])
def test_r15_a_field_that_drives_a_walkmesh_sim_refuses_every_row(op, args):
    """S4 for the walkmesh SIM setters BSACTIVE .. BSAXIS: a sim starts inactive and only these ops drive it; once on,
    WalkMesh.BGI_simService slides its floor and the actors standing on it every frame, so a footprint or a landing
    height read from the static verts is wrong -- every row of the field refuses, as for BAFRAME."""
    ents = r15_field(None, body=JUMP_B)
    assert ships(ents)
    ents[0][1][1] = [f"op_{op:X}({args})"]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    why = f"0:1 +0 drives a walkmesh sim (0x{op:X})"
    assert G.ground_unnamed(fld) == why
    assert _refusal(ents, walkmesh=ground) == G.UNNAMED_GROUND + why


def test_r15_stacked_prefixes_are_a_function_that_does_not_decode():
    """``0xFF 0xFF XX`` is ONE engine op (DoEventCode.cs:35-42 loops over the prefixes; the default case runs, then
    commandDefault2 backs ip up one byte) where the disassembler reads 0x1FF and then decodes XX as an op of its own --
    here a RunScriptAsync the engine never runs, out of step with the bytes after it. The function counts as one that
    does not decode, so the field's rows refuse."""
    ents = r15_field(None, body=JUMP_B)
    ents[0][1][1] = ["op_1FF()", "op_10(0, 236, 0)"]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert fld.decode_failed(0, 1) and fld.instrs(0, 1) == []
    why = "0:1 does not decode (it may run BAFRAME or a walkmesh sim)"
    assert G.ground_unnamed(fld) == why
    assert _refusal(ents, walkmesh=ground) == G.UNNAMED_GROUND + why


# ================================================================================================ R15: the chase (S5)
GROUND_C = [(1000, 0, 0), (1400, 0, 0), (1400, 0, 400), (1000, 0, 400)]
GROUND_D = [(2000, 0, 0), (2400, 0, 0), (2400, 0, 400), (2000, 0, 400)]
POLY_C = [(1050, 50), (1350, 50), (1350, 350), (1050, 350)]
POLY_D = [(2050, 50), (2350, 50), (2350, 350), (2050, 350)]


def four():
    """GROUND_A .. GROUND_D, each its own component (tris 0-1, 2-3, 4-5, 6-7)."""
    from ff9mapkit.scene import bgi
    return bgi.build(GROUND_A + GROUND_B + GROUND_C + GROUND_D,
                     [(4 * k + a, 4 * k + b, 4 * k + c) for k in range(4) for (a, b, c) in ((0, 1, 2), (0, 2, 3))])


def chain_field(hops, item_poly, item_entry=7) -> dict:
    """r15_field (spawn on A, the row's jump lands on B), a tread per hop ``(entry, poly, player tag, (x, z))`` whose tag 2
    runs the player's jump to ``(x, 0, z)`` -- LOCO-ONLY, never exposed itself -- and a STATEFUL item tread over
    ``item_poly``."""
    ents = r15_field(None)
    inits = ["InitRegion(1, 0)", "InitObject(2, 0)"]
    for (e, poly, tag, (x, z)) in hops:
        ents[e] = (1, {0: [zone(*poly)], 2: [f"RunScriptSync(2, 250, {tag})"]})
        ents[2][1][tag] = [f"SetupJump({_u16(x)}, 0, {_u16(z)}, 4)", "Jump()"]
        inits.append(f"InitRegion({e}, 0)")
    ents[item_entry] = (1, {0: [zone(*item_poly)], 2: list(STATEFUL_TREAD)})
    ents[0][1][0] = inits + [f"InitRegion({item_entry}, 0)"]
    return ents


def test_r15_a_walk_in_that_lands_the_player_is_chased():
    """S5: a LOCO-ONLY tread on the climb's new ground B jumps the player (a spectator's tread runs its tag 2) to C,
    which is neither an arrival nor the row's landing -- C's STATEFUL tread is judged against the row too."""
    gr = G.Ground(four())
    c = gr.comp_of[4]
    ents = chain_field([(3, POLY_B, 18, (1200, 200))], POLY_C)
    assert _refusal(ents, walkmesh=four) == (f"R15 walk-in: component {c} (not an arrival; walk-in 3:2 on the climb's "
                                             "new ground lands the player there) carries walk-in 7:2 (item)")


def test_r15_a_hop_over_a_computed_region_is_chased_from_anywhere():
    """A hop whose SetRegion is computed may fire on ANY component -- the climb's new ground B among them -- so its
    landing is chased as one that meets B (and C's item refuses)."""
    gr = G.Ground(four())
    ents = chain_field([(3, POLY_B, 18, (1200, 200))], POLY_C)
    ents[3][1][0] = ["SetRegion({Map.Int16[8] B_EXPR_END}, 0, 0, 0)"]
    assert _refusal(ents, walkmesh=four) == (f"R15 walk-in: component {gr.comp_of[4]} (not an arrival; walk-in 3:2 on "
                                             "the climb's new ground lands the player there) carries walk-in 7:2 (item)")


def test_r15_the_chase_runs_to_a_fixpoint():
    """Two hops, the later one listed FIRST (entry 3 hops C -> D, entry 5 hops B -> C): one pass over the walk-ins
    reaches C only; the fixpoint reaches D, whose item refuses."""
    gr = G.Ground(four())
    ents = chain_field([(3, POLY_C, 19, (2200, 200)), (5, POLY_B, 18, (1200, 200))], POLY_D)
    assert _refusal(ents, walkmesh=four) == (f"R15 walk-in: component {gr.comp_of[6]} (not an arrival; walk-in 3:2 on "
                                             "the climb's new ground lands the player there) carries walk-in 7:2 (item)")


@pytest.mark.parametrize("hops, item", [
    ([], POLY_C),                                             # nothing reaches C
    ([(3, POLY_B, 18, (-750, -750))], POLY_A),               # the hop lands on A, an arrival: no new ground
    ([(3, POLY_C, 19, (2200, 200))], POLY_D),                 # a hop on ground the climb never reaches
])
def test_r15_the_chase_stops_where_nothing_new_is_reached(hops, item):
    assert ships(chain_field(hops, item), four)


def test_r15_a_chased_landing_it_cannot_name_lands_everywhere():
    """FAIL CLOSED: the hop's jump goes to a computed point, so it may land the player on ANY walkable component."""
    gr = G.Ground(four())
    ents = chain_field([(3, POLY_B, 18, (1200, 200))], POLY_C)
    ents[2][1][18] = ["SetupJump({Map.Int16[8] B_EXPR_END}, 0, 200, 4)", "Jump()"]
    assert _refusal(ents, walkmesh=four) == (
        f"R15 walk-in: component {gr.comp_of[4]} (not an arrival; walk-in 3:2 on the climb's new ground lands the "
        "player there) carries walk-in 7:2 (item) -- 2:18 +0 SetupJump can end the climb at a computed point, so that "
        "walk-in may land the player on any walkable component")


def test_r15_only_a_walk_in_that_lands_the_player_is_chased():
    """The chase follows a walk-in's own landing points: a hop with NO landing adds nothing, even one that cannot be
    judged whole (it is exposed itself, and refuses as itself -- named, not the item tread far away that only an
    everywhere-landing would reach)."""
    ents = chain_field([], POLY_D, item_entry=3)
    ents[5] = (1, {0: [zone(*POLY_B)], 2: ["InitObject(8, 0)"]})
    ents[8] = (2, {0: [], 1: ["op_22(1)"]})
    ents[0][1][0].append("InitRegion(5, 0)")
    assert _refusal(ents, walkmesh=four) == (f"R15 walk-in: landing component {G.Ground(four()).comp_of[2]} (not an "
                                             "arrival) carries walk-in 5:2 (spawn) -- its tag-2 closure cannot be judged "
                                             "whole (5:2 InitObject creates 8, whose tag 1 runs when its tag 0 returns)")


def test_r15_a_refusal_names_the_climbs_own_new_ground_first():
    """The refusal text names a NEW component (the row's own landing) before a chased one, whatever their numbers: the
    row lands on D, a hop on D lands the player on B, and a walk-in over a computed region (it may fire anywhere) is
    exposed on both."""
    gr = G.Ground(four())
    ents = chain_field([(3, POLY_D, 18, (200, 200))], POLY_C)
    ents[2][1][17] = ["SetupJump(2200, 0, 200, 4)", "Jump()"]
    ents[7] = (1, {0: ["SetRegion({Map.Int16[8] B_EXPR_END}, 0, 0, 0)"], 2: list(STATEFUL_TREAD)})
    assert _refusal(ents, walkmesh=four) == (f"R15 walk-in: landing component {gr.comp_of[6]} (not an arrival) may "
                                             "carry walk-in 7:2 (item) -- its region is computed")


def test_r15_a_chased_walk_in_it_cannot_judge_whole_lands_everywhere():
    """FAIL CLOSED: a hop whose closure has a gap (an object it creates runs a tag 1 the walk never follows) may land the
    player anywhere -- the chase grows to every non-arrival component (it refuses as itself too: it is exposed)."""
    ents = chain_field([(3, POLY_B, 18, (1200, 200))], POLY_C)
    ents[3][1][2].append("InitObject(8, 0)")
    ents[8] = (2, {0: [], 1: ["op_22(1)"]})
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    gr = G.field_ground(fld, four())
    arrival = G.field_arrival(fld, gr)
    w = G.walkin(fld, P.analyze_regions(fld)[0], gr, arrival, G.walk_ins(fld, gr))
    assert w["new"] == {gr.comp_of[2]} and w["reach"] == set(gr.walkable) - arrival and w["why"] is not None


# ================================================================================================ R15: THE JP WAIVER (V6)
def _two_langs(us, jp, **kw):
    return G.derive_field(30999, {"us": us, "jp": jp}, ("us", "jp"), walkmesh=ground, **kw)


def test_the_jp_waiver_ships_a_row_only_japanese_r15_refuses_and_the_engine_never_sees_it():
    """THE JP WAIVER: the chest template is exempt in US and polls KEYON(Cancel | Special) in Japanese (refused there:
    F1 strips Confirm / Special / Select only); exempt once the key fact also accepts Cancel, the row SHIPS, recorded
    as waived -- and assemble moves the record to the top-level "waivers", so the rows, table_crc and render_cs are
    those of the same row unwaived."""
    _, rows, refused, _ = _two_langs(build(bump_field(CHEST)), build(bump_field(JP_CHEST)))
    assert refused == [] and rows[0]["waived"] == f"R15 walk-in waived: jp F1 hole -- bump 4:2 {G.WAIVER_WHY}"
    counts = {"fields_scanned": 1, "quad_roots": 1, "census_candidates": 1}
    obj = G.assemble(rows, refused, counts, [])
    assert obj["waivers"] == [{"field": 30999, "entry": 1, "waiver": rows[0]["waived"]}]
    bare = [{k: x for k, x in rows[0].items() if k != "waived"}]
    plain = G.assemble(bare, refused, counts, [])
    assert obj["rows"] == bare and obj["table_crc"] == plain["table_crc"] and G.render_cs(obj) == G.render_cs(plain)
    assert list(obj).index("waivers") == list(obj).index("refused") + 1 and plain["waivers"] == []


def test_the_jp_waiver_is_scoped_exactly():
    """Nothing a western language refuses (the US script itself polls Cancel | Special), nothing Japanese refuses for
    any other reason (a bump that gives the item with no poll at all), and no waiver past R16 (a watcher refuses the
    waived row, and the record goes with it)."""
    jp = build(bump_field(JP_CHEST))
    _, rows, refused, _ = _two_langs(jp, jp)
    assert rows == [] and refused[0]["refusal"] == on_b("carries bump 4:2 (window, item)")
    _, rows, refused, _ = _two_langs(build(bump_field(CHEST)), build(bump_field(STATEFUL_TREAD)))
    assert rows == [] and refused[0]["refusal"] == on_b("carries bump 4:2 (item) [jp]")
    circle = [ln.replace("655360", "532480") for ln in CHEST]                    # Circle | Special: no JP-mapped bit
    _, rows, refused, _ = _two_langs(build(bump_field(CHEST)), build(bump_field(circle)))
    assert rows == [] and refused[0]["refusal"] == on_b("carries bump 4:2 (window, item) [jp]")
    watched = []
    for tag2 in (CHEST, JP_CHEST):
        ents = bump_field(tag2)
        ents[0][1][0] = ents[0][1][0] + ["InitCode(5, 0)"]
        ents[5] = (0, {0: [], 1: ["Lw:", *POS_TEST, *KEY_TEST, *GIVE, "op_22(1)", "JMP(Lw)"]})
        watched.append(build(ents))
    _, rows, refused, _ = _two_langs(*watched, r16=True)
    assert rows == [] and refused[0]["refusal"].startswith("R16 watcher: (a) 5:1 item")
    assert _two_langs(*watched)[1][0]["waived"].startswith("R15 walk-in waived: jp F1 hole -- bump 4:2 ")


def test_the_jp_waiver_holds_for_a_tread_too():
    """The waiver is R15's, not the bump's: the chest template as a TREAD region over B (exempt in US, Cancel | Special
    in Japanese) ships waived, naming the walk-in; a Japanese tread that gives the item with no poll is still refused."""
    us = build(tread_r15(CHEST))
    _, rows, refused, _ = _two_langs(us, build(tread_r15(JP_CHEST)))
    assert refused == [] and rows[0]["waived"] == f"R15 walk-in waived: jp F1 hole -- walk-in 3:2 {G.WAIVER_WHY}"
    _, rows, refused, _ = _two_langs(us, build(tread_r15(STATEFUL_TREAD)))
    assert rows == [] and refused[0]["refusal"] == on_b("carries walk-in 3:2 (item) [jp]")


# ================================================================================================ R16: the watchers
POS_TEST = ["SET({obj(uid=250).f[1] const(65136) B_LE B_EXPR_END})", "JMP_IFNOT(Ln)"]      # y <= -400: a ladder top
KEY_TEST = ["SET({const4(655360) B_KEYON B_EXPR_END})", "JMP_IFNOT(Ln)"]                   # Confirm | Special
CTRL_TEST = ["SET({B_SYSVAR[2] B_EXPR_END})", "JMP_IFNOT(Ln)"]
GIVE = ["AddItem(238, 1)", "Ln:"]


def watcher_field(loop, more=None) -> dict:
    """base() plus code entry 5 (Main_Init's InitCode) whose tag 1 loops over ``loop`` -- a watcher the engine runs on
    its own on the guest's copy, never pressed; ``more``: {entry: (type, funcs)} besides."""
    ents = base()
    ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)", "InitCode(5, 0)"] + \
        [f"InitCode({e}, 0)" for e in sorted(more or ())]
    ents[5] = (0, {0: [], 1: ["Lw:", *loop, "op_22(1)", "JMP(Lw)"]})
    ents.update(more or {})
    return ents


def _r16(ents) -> list:
    return [(root, why) for (root, why) in G.watchers(P.FieldModel.from_bytes(build(ents), 30999))]


@pytest.mark.parametrize("loop, want", [
    (CTRL_TEST + POS_TEST + KEY_TEST + GIVE, None),                                          # the hidden-item template
    (CTRL_TEST + KEY_TEST + GIVE, None),
    (POS_TEST + KEY_TEST + GIVE,                                                             # 1952 / 2853: no control test
     "(a) 5:1 item at 5:1 +23 fires on a host-owned key poll (KEYON(0xA0000)) with no user-control test"),
    (KEY_TEST + GIVE, "(a) 5:1 item at 5:1 +11 fires on a host-owned key poll (KEYON(0xA0000)) with no user-control test"),
    (CTRL_TEST + POS_TEST + GIVE,                                                            # a position auto-trigger
     "(b) 5:1 item at 5:1 +19 fires on the player's whereabouts (obj(uid=250).f[1]) with no constant Confirm / "
     "Special / Select poll before it"),
    (CTRL_TEST + POS_TEST + ["SET({const(8192) B_KEYON B_EXPR_END})", "JMP_IFNOT(Ln)"] + GIVE,   # Circle: not stripped
     "(b) 5:1 item at 5:1 +28 fires on the player's whereabouts (obj(uid=250).f[1]) with no constant Confirm / "
     "Special / Select poll before it"),
    (CTRL_TEST + POS_TEST + ["SET({const4(589824) B_KEYON B_EXPR_END})", "JMP_IFNOT(Ln)"] + GIVE,  # JP: Cancel | Special
     "(b) 5:1 item at 5:1 +30 fires on the player's whereabouts (obj(uid=250).f[1]) with no constant Confirm / "
     "Special / Select poll before it"),
    (["SET({B_SYSVAR[2] const(0) B_EQ B_EXPR_END})", "JMP_IFNOT(Ln)"] + KEY_TEST + GIVE,     # control OFF is no test
     "(a) 5:1 item at 5:1 +22 fires on a host-owned key poll (KEYON(0xA0000)) with no user-control test"),
])
def test_r16_a_watcher_trips_on_what_its_effects_fire_on(loop, want):
    """R16 (a) / (b) and their shared exemption on a synthetic watcher: the facts are proved by the branch, not read off
    it (`usercontrol == 0` proves nothing), and only a constant poll inside F1's mask exempts (b)."""
    got = _r16(watcher_field(loop))
    assert got == ([] if want is None else [((5, 1), want)]), got


@pytest.mark.parametrize("between, want", [
    ([], None),
    (["op_22(1)"], "(a) 5:1 item at 5:1 +19 fires on a host-owned key poll (KEYON(0x2000)) with no user-control test"),
    (["DisableMove()"], "(a) 5:1 item at 5:1 +17 fires on a host-owned key poll (KEYON(0x2000)) with no user-control "
                        "test"),
    (["ExitField()"], "(a) 5:1 item at 5:1 +17 fires on a host-owned key poll (KEYON(0x2000)) with no user-control "
                      "test"),                                       # ExitField sets usercontrol 0 too (:859-866)
])
def test_r16_a_user_control_test_holds_only_until_a_yield_or_a_control_write(between, want):
    """V3 inside one block: a Circle poll picks the effect, a user-control test guards it -- until a Wait (another frame:
    control may have gone) or a DisableMove between the test and the effect, which leaves (a) unguarded."""
    loop = ["SET({const(8192) B_KEYON B_EXPR_END})", "JMP_IFNOT(Ln)"] + CTRL_TEST + between + GIVE
    assert _r16(watcher_field(loop)) == ([] if want is None else [((5, 1), want)])


def test_r16_a_global_write_is_an_effect():
    assert _r16(watcher_field(KEY_TEST + ["SET({Global.Bit[9000] const(1) B_LET B_EXPR_END})", "Ln:"])) == [
        ((5, 1), "(a) 5:1 GLOB write at 5:1 +11 fires on a host-owned key poll (KEYON(0xA0000)) with no user-control test")]


def test_r16_an_effect_after_the_join_does_not_fire_on_the_test():
    """Control dependence, not 'somewhere after': an effect every arm of a position test reaches is not triggered by
    it (the 114 3:1 direction pick is two arms that both write -- this is the single-effect form)."""
    assert _r16(watcher_field(["SET({obj(uid=250).f[1] const(65136) B_LE B_EXPR_END})", "JMP_IFNOT(Lj)", "op_22(1)",
                               "Lj:", "AddItem(238, 1)"])) == []


def test_r16_a_position_test_reaches_an_effect_through_a_map_var():
    """The taint: one watcher latches the ladder-top test into Map.Bit[200], another pays out on the latch -- the
    second's effect fires on the player's whereabouts. A latch written only under a constant F1-stripped poll is not
    guest-triggerable and taints nothing."""
    latch = (0, {0: [], 1: ["Lw:", "SET({Map.Bit[200] B_EXPR_END})", "JMP_IFNOT(Ln)", "AddItem(238, 1)", "Ln:",
                            "op_22(1)", "JMP(Lw)"]})
    got = _r16(watcher_field(POS_TEST + ["SET({Map.Bit[200] const(1) B_LET B_EXPR_END})", "Ln:"], {6: latch}))
    assert got == [((6, 1), "(b) 6:1 item at 6:1 +7 fires on the player's whereabouts (a position-tainted var) with no "
                            "constant Confirm / Special / Select poll before it")], got
    gated = CTRL_TEST + POS_TEST + KEY_TEST + ["SET({Map.Bit[200] const(1) B_LET B_EXPR_END})", "Ln:"]
    assert _r16(watcher_field(gated, {6: latch})) == []


def test_r16_a_scan_that_cannot_see_everything_trips():
    """FAIL CLOSED: a sender call (RunScriptObject*) runs code a root cannot name; a CFG that does not build hides
    everything."""
    got = _r16(watcher_field(["RunScriptObjectSync(2, 18)"]))
    assert got == [((5, 1), "5:1 cannot be fully scanned (5:1 +0 RunScriptObjectSync runs its sender's code (unknown "
                            "to a root))")], got
    fld = P.FieldModel.from_bytes(build(watcher_field(KEY_TEST + GIVE)), 30999)
    fld._flows[(5, 1)] = None
    assert G.watchers(fld) == [((5, 1), "5:1 cannot be fully scanned (5:1's CFG does not build)")]


@pytest.mark.parametrize("loop, why", [
    (["RunScriptSync(2, {Map.Int16[8] B_EXPR_END}, 5)"], "5:1 +0 RunScriptSync has a computed uid or tag"),
    (["RunScriptSync(2, 200, 5)"], "5:1 +0 RunScriptSync(uid 200) does not resolve (uid-unknown)"),
    (["RunScriptSync(2, 250, {Map.Int16[8] B_EXPR_END})"], "5:1 +0 RunScriptSync has a computed uid or tag"),
    (["RunSharedScript({Map.Int16[8] B_EXPR_END})"], "5:1 +0 RunSharedScript has a computed entry"),
])
def test_r16_a_call_the_scan_cannot_name_trips(loop, why):
    """FAIL CLOSED: a call whose uid or tag is computed, or whose uid resolves to nothing, could run any code."""
    assert _r16(watcher_field(loop)) == [((5, 1), f"5:1 cannot be fully scanned ({why})")]


def test_r16_a_scan_past_its_depth_trips():
    """Nine chained calls: past the scan's depth an unvisited function could hold anything."""
    ents = watcher_field(["RunScriptSync(2, 250, 18)"])
    for t in range(18, 28):
        ents[2][1][t] = [f"RunScriptSync(2, 250, {t + 1})"]
    ents[2][1][28] = []
    got = _r16(ents)
    assert len(got) == 1 and got[0][0] == (5, 1) and "is past the walk's depth / node budget" in got[0][1], got


def test_r16_an_operand_that_does_not_decode_trips(monkeypatch):
    """An operand the scan cannot decode hides its reads, polls and writes."""
    fld = P.FieldModel.from_bytes(build(watcher_field(["AddItem({Map.Int16[8] B_EXPR_END}, 1)"])), 30999)
    real = P.instr_expr_tokens

    def undecodable(data, ins):
        if ins.op == 0x48:
            raise ValueError("probe")
        return real(data, ins)
    monkeypatch.setattr(P, "instr_expr_tokens", undecodable)
    assert G.watchers(fld) == [((5, 1), "5:1 cannot be fully scanned (5:1 +0 does not decode)")]


def test_r16_roots_are_the_functions_the_engine_starts_on_its_own():
    """Tags 0 / 1 (and Main_Reinit) are watched; a press (tag 3) or a walk-in (tag 2) is not a root -- a following guest
    never starts the first, R15 judges the second."""
    talk = (2, {0: [], 3: list(POS_TEST + ["WindowSync(1, 0, 1)", "Ln:"]), 2: list(POS_TEST + GIVE)})
    ents = watcher_field(["op_22(1)"], {6: talk})
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    assert (6, 3) not in P.watch_roots(fld) and (6, 2) not in P.watch_roots(fld) and (5, 1) in P.watch_roots(fld)
    assert G.watchers(fld) == []


def test_r16_is_measured_not_enforced():
    """R16 refuses through derive_field(r16=True) with its own text; the install's derive() passes R16_ENFORCED, which
    is False -- on the stock install R16 refuses bench rows (test_guest_traversal_install.py pins the set), so the
    table does not carry it until the lead rules on the measurement."""
    data = build(watcher_field(POS_TEST + KEY_TEST + GIVE))
    _, rows, refused, _ = derive(data, r16=True)
    assert rows == [] and refused[0]["refusal"] == ("R16 watcher: (a) 5:1 item at 5:1 +23 fires on a host-owned key "
                                                    "poll (KEYON(0xA0000)) with no user-control test")
    _, rows, refused, _ = derive(data)
    assert len(rows) == 1 and refused == []
    assert G.R16_ENFORCED is False and "NOT ENFORCED" in G.RULE["refusals"]


# ================================================================================================ the far-tread report
class _FakeEvents:
    """An install stand-in for the report: a game folder with NO field index, one synthetic field."""

    def __init__(self, game, data):
        self.game, self._data = game, data

    def eb(self, fid, lang="us"):
        return self._data


def _report_field():
    ents = base()
    ents[0][1][0] = ["InitRegion(1, 0)", "InitObject(2, 0)", "InitRegion(3, 0)"]
    ents[3] = (1, {0: [REGION_ZONE], 2: ["Field(355)"]})        # a tread region that warps
    data = build(ents)
    _, rows, _, _ = derive(data)
    return data, rows


def _loader_spies(monkeypatch) -> dict:
    """RECORDING spies on every extract entry point that can build or rescan the field index. They record, then
    raise -- the report's ``except Exception`` swallows the raise, so the test reads the RECORD, never the raise --
    and never pass through (a pass-through could rescan a real install)."""
    from ff9mapkit import extract
    calls = {}
    for name in ("build_field_index", "resolve_field", "stock_walkmesh", "find_field"):
        calls[name] = []

        def spy(*a, _name=name, **k):
            calls[_name].append((a, k))
            raise FileNotFoundError(f"spy: {_name}")
        monkeypatch.setattr(extract, name, spy)
    return calls


def _snapshot(sa):
    return sorted((p.name, p.read_bytes(), p.stat().st_mtime_ns) for p in sa.iterdir())


def test_the_far_tread_report_never_builds_a_missing_index(tmp_path, monkeypatch):
    """D5: the report is informational and names a walkmesh component only when the field index ALREADY exists.
    With no index it says so in its fixed words and never reaches a walkmesh loader (which could build one)."""
    (tmp_path / "StreamingAssets").mkdir()
    data, rows = _report_field()
    monkeypatch.setattr(G, "_study_verdicts", lambda: {(30999, 1): "LINKS-COMPONENTS"})
    calls = _loader_spies(monkeypatch)
    text = G.far_tread_report(obj={"rows": rows}, events=_FakeEvents(tmp_path, data))
    assert G.UNKNOWN_COMPONENT == "component: unknown (field index not built; this report never builds it)"
    assert G.UNKNOWN_COMPONENT in text
    assert "tread 30999:3  effects: exit" in text and "row 30999:1 ladder" in text
    assert calls == {name: [] for name in calls}
    assert sorted(p.name for p in (tmp_path / "StreamingAssets").iterdir()) == []


@pytest.mark.parametrize("content", [b"", b"{", b"\xff", b"[]"], ids=["empty", "truncated", "not_utf8", "not_object"])
def test_the_far_tread_report_reads_a_corrupt_index_as_absent(tmp_path, monkeypatch, content):
    """An index that EXISTS but does not parse as an object is the no-index branch: is_file() alone would send the
    walkmesh lookup into resolve_field -> build_field_index, which rescans every bundle and rewrites the index inside
    the install. Nothing may be called, and the index's bytes and mtime stay as they were."""
    from ff9mapkit import extract
    sa = tmp_path / "StreamingAssets"
    sa.mkdir()
    (sa / extract.INDEX_NAME).write_bytes(content)
    before = _snapshot(sa)
    data, rows = _report_field()
    monkeypatch.setattr(G, "_study_verdicts", lambda: {(30999, 1): "LINKS-COMPONENTS"})
    calls = _loader_spies(monkeypatch)
    text = G.far_tread_report(obj={"rows": rows}, events=_FakeEvents(tmp_path, data))
    assert calls == {name: [] for name in calls}
    assert _snapshot(sa) == before
    assert G.UNKNOWN_COMPONENT in text


def test_the_far_tread_report_loads_a_walkmesh_only_through_the_parsed_index(tmp_path, monkeypatch):
    """The control: with an index that parses, the walkmesh lookup goes to find_field with the index's OWN bundle
    (the read-only explicit-bundle branch) -- never resolve_field / build_field_index -- and the index is not written."""
    from ff9mapkit import extract
    sa = tmp_path / "StreamingAssets"
    sa.mkdir()
    monkeypatch.setitem(extract.ID_TO_FBG, 30999, "fbg_n99_test_map999_tt_tst_0")
    (sa / extract.INDEX_NAME).write_text(json.dumps({"fbg_n99_test_map999_tt_tst_0": "p0data99.bin"}), encoding="utf-8")
    before = _snapshot(sa)
    data, rows = _report_field()
    monkeypatch.setattr(G, "_study_verdicts", lambda: {(30999, 1): "LINKS-COMPONENTS"})
    calls = _loader_spies(monkeypatch)
    text = G.far_tread_report(obj={"rows": rows}, events=_FakeEvents(tmp_path, data))
    assert [(a, k.get("bundle")) for (a, k) in calls["find_field"]] == [(("fbg_n99_test_map999_tt_tst_0",), "p0data99.bin")]
    assert (calls["build_field_index"], calls["resolve_field"], calls["stock_walkmesh"]) == ([], [], [])
    assert "field 30999: walkmesh unreadable (FileNotFoundError)" in text and G.UNKNOWN_COMPONENT not in text
    assert _snapshot(sa) == before


# ================================================================================================ R15: round 5's controls
def test_r15_a_seq_entry_listing_another_tag_first_is_a_gap():
    """S1's rule is EXACTLY [tag 0], not "no tag 1": a Seq entry whose FIRST listed function is tag 2 and whose tag 0
    (listed second) holds the item. The census walk takes the first listed function (op_22: not STATEFUL); the engine
    runs tag 0 by id. It is a closure gap, and the tread refuses on B."""
    ents = tread_r15(["RunSharedScript(8)"], {8: (0, {2: ["op_22(1)"], 0: ["AddItem(236, 1)"]})})
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    tv = P.analyze_root(fld, 3, 2)
    assert tv.tier != "STATEFUL"                                   # the census walk saw tag 2's op_22 only
    assert P.closure_gaps(tv) == [_seq_gap("3:2")]
    assert not ships(ents)


def _four_floor_strip():
    """A (tris 0-1), D (floor 1, tris 2-3: statically walkable, Main_Init disables it), X (floor 2, tris 4-5: INACTIVE,
    no code turns it on), C (floor 3, tris 6-7) -- in a row, sharing edges."""
    from ff9mapkit.scene import bgi
    xs = [-1000, -500, 0, 400, 900]
    verts = [(x, 0, z) for x in xs for z in (0, 400)]
    faces = [f for k in range(4) for f in ((2 * k, 2 * k + 2, 2 * k + 3), (2 * k, 2 * k + 3, 2 * k + 1))]
    m = bgi.build(verts, faces, floor_ids=[0, 0, 1, 1, 2, 2, 3, 3])
    for t in (4, 5):
        m.tris[t].tri_flags = 0
    return m


def test_r15_a_disabled_tris_run_stops_at_a_tri_nothing_turns_on():
    """S3's run of foot tris stops at a tri no code turns on: a tread only over D (Main_Init's constant disable) stands
    for what D's run borders -- A. X is inactive and nothing turns it on, so it is no foot tri; C beyond X (the row's
    landing, new ground) is not the tread's, and the row ships."""
    ents = r15_field(STATEFUL_TREAD, poly=BRIDGE_POLY, spawn=SPAWN_STRIP_A, body=["SetupJump(600, 0, 200, 4)", "Jump()"])
    ents[0][1][0] = ents[0][1][0] + ["EnablePath(1, 0)"]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    gr = G.field_ground(fld, _four_floor_strip())
    assert gr.disabled == {2, 3} and gr.enabled == frozenset() and not gr.foot[4] and not gr.foot[5]
    assert gr.touched(BRIDGE_POLY) == {gr.comp_of[0]}
    assert ships(ents, _four_floor_strip)


def test_r15_the_height_window_holds_below_as_well_as_above():
    """WalkMesh.Collision's -400 < dy < 400 is symmetric: B 1000 u BELOW A (y +1000, y is down) is out of the window
    exactly as B 1000 u above is, so the chaser on A never bumps a player there and the row ships."""
    assert ships(chaser_field(1000), near(1000))
    assert ships(chaser_field(400), near(400))
    assert not ships(chaser_field(399), near(399))


def test_r15_baframe_in_main_init_itself_refuses_every_row():
    """S4 with the BAFRAME appended to Main_Init (0, 0) itself -- the BAFRAME test replaces other functions' bodies,
    never Main_Init's (that would drop the field's InitRegion / InitObject)."""
    for body in (JUMP_B, [f"SetupJump({_u16(-750)}, 0, {_u16(-750)}, 4)", "Jump()"]):
        ents = r15_field(None, body=body)
        assert ships(ents)
        ents[0][1][0] = ents[0][1][0] + ["op_10A(0, 1)"]
        fld = P.FieldModel.from_bytes(build(ents), 30999)
        why = G.ground_unnamed(fld)
        assert why is not None and why.startswith("0:0 +") and why.endswith(" runs BAFRAME (0x10A)"), why
        assert _refusal(ents, walkmesh=ground) == G.UNNAMED_GROUND + why


def test_r15_a_gap_chased_component_names_its_gap():
    """S5's text: the item tread (entry 3, over C) is listed BEFORE the hop that reaches C (entry 5, B -> C, whose
    closure has a gap), so the item is named first, on the chased C, and the refusal carries the hop's gap as the reason
    C is reached."""
    ents = chain_field([(5, POLY_B, 18, (1200, 200))], POLY_C, item_entry=3)
    ents[5][1][2].append("InitObject(8, 0)")
    ents[8] = (2, {0: [], 1: ["op_22(1)"]})
    gr = G.Ground(four())
    gap = "5:2 InitObject creates 8, whose tag 1 runs when its tag 0 returns"
    assert _refusal(ents, walkmesh=four) == (
        f"R15 walk-in: component {gr.comp_of[4]} (not an arrival; walk-in 5:2 on the climb's new ground lands the "
        f"player there) carries walk-in 3:2 (item) -- {gap}, so that walk-in may land the player on any walkable component")


def test_r15_a_seq_terminateentry_is_flow_in_the_scan():
    """The scan visits a Seq AS a Seq: the gated chest-template tread, then -- outside the gate -- a Seq whose one tag 0
    runs TerminateEntry(5). The census walk counts a Seq-run TerminateEntry as FLOW and the scan agrees, so the template
    stays exempt and ships (visited as a plain call it would be an ungated 'spawn' site)."""
    ents = tread_r15(CTRL_GATE + CONFIRM_GATE + ["AddItem(236, 1)", "Lx:", "RunSharedScript(8)"],
                     {8: (0, {0: ["op_1C(5)"]}), 5: (0, {0: []})})
    assert judged(ents) == ("STATEFUL", None)
    assert ships(ents)


def test_r15_a_nonfinal_landing_in_flight_is_not_wild():
    """Only a FINAL unnamed landing lands everywhere: the climb's first jump peaks 3000 u above A (no walkable tri within
    LAND_TOL: in flight), its last lands back on A, so the row lands on A (arrival) and ships beside a STATEFUL tread on
    B."""
    body = [f"SetupJump({_u16(-750)}, {_u16(-3000)}, {_u16(-750)}, 4)", "Jump()",
            f"SetupJump({_u16(-750)}, 0, {_u16(-750)}, 4)", "Jump()"]
    ents = r15_field(STATEFUL_TREAD, body=body)
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    pts = G.landing_points(fld, P.analyze_regions(fld)[0])
    assert [(x, y, z, final) for (_op, x, y, z, _n, _o, final) in pts] == [(-750, -3000, -750, False),
                                                                          (-750, 0, -750, True)], pts
    assert ships(ents)


@pytest.mark.parametrize("flags", [0x8000, 0x8001], ids=["inactive_restricted", "active_restricted"])
def test_r15_a_restricted_tri_code_turns_on_is_foot(flags):
    """S3's foot counts EVERY tri code can turn on, the player-restricted ones included (SetTriangleFlagMask / BGIMASK
    can mask bit 0x80 off, WalkMesh.cs:1155-1163): on a player-restricted bridge that code turns on, the tread touches A
    and C and refuses."""
    ents = r15_field(STATEFUL_TREAD, poly=BRIDGE_POLY, spawn=SPAWN_STRIP_A, body=["SetupJump(200, 0, 200, 4)", "Jump()"])
    assert ships(ents, bridged(flags))
    ents[0][1][1] = ["EnablePath(1, 1)"]
    fld = P.FieldModel.from_bytes(build(ents), 30999)
    gr = G.field_ground(fld, bridged(flags)())
    assert gr.foot[2] and gr.foot[3] and gr.touched(BRIDGE_POLY) == {gr.comp_of[0], gr.comp_of[4]}
    assert not ships(ents, bridged(flags))
