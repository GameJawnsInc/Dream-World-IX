"""The press-closure classifier (``ff9mapkit.eb.pressclosure``) and the guest-traversal ship filter
(``guest_traversal.derive_field``), INSTALL-FREE: tiny kit-authored fields assembled through ``eb.ebsrc`` in the
decoded stock idiom (a region whose tag 3 brackets a ``RunScriptSync(2, 250, 17)``, a player whose tag 17 climbs on
the direction keys), each mutated ONE way, each mutant with the verdict it must give. No game bytes.

Every synthetic field is also classified by the frozen study census
(``studies/field-coop/guest-traversal/interaction_census.py``) and must get the same tier and kind -- the install-free
half of the faithfulness pin (the install-gated half runs every real QUAD root).
"""
from __future__ import annotations

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


def derive(data: bytes, langs=("us",), by_lang=None):
    """The ship filter on one synthetic field: ``(candidates, rows, refused, quad_roots)``."""
    return G.derive_field(30999, by_lang or {lang: data for lang in langs}, langs)


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
