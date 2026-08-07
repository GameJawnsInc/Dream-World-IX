"""Tests for the TIER R rung-2 annotator.

Runs WITHOUT the extracted corpus and WITHOUT the game install: the unit tests synthesise tiny id-3
images with R1's own MIPS encoder, and drive the classifier / data-ref / segmentation / confidence
logic on those.  Corpus and DLL tests skip when their inputs are absent -- the same convention R1's
tests use, so the committed artifact stays verifiable by anyone.

    py -m pytest studies/custom-summons/tier-r/test_tier_r_annot.py -q
"""
from __future__ import annotations

import collections
import json
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tier_r_disasm as T        # noqa: E402
import tier_r_annot as A         # noqa: E402
from test_tier_r_disasm import (  # noqa: E402  -- one MIPS encoder, not two
    PSX, ORIGIN, ZERO, V0, V1, A0, A1, A2, A3, S0, SP, RA,
    addiu, ori, lui, lw, sw, sltiu, sll, addu, jr, jalr, cop2, nop, beq, bne, j, jal, image,
)

CORPUS = T.SCRATCH_CORPUS
have_corpus = (os.path.isdir(CORPUS)
               and bool([f for f in os.listdir(CORPUS) if f.startswith("ef")]))
try:
    import refkit                                     # noqa: F401
    have_dll = os.path.isfile(refkit.DLL_X64)
except Exception:                                     # pragma: no cover
    have_dll = False
have_ops = os.path.isfile(A.HLE_OPS_JSON)

needs_corpus = pytest.mark.skipif(not have_corpus, reason="needs the extracted ef###.bytes corpus")
needs_dll = pytest.mark.skipif(not have_dll, reason="needs the installed FF9SpecialEffectPlugin.dll")
needs_ops = pytest.mark.skipif(not have_ops, reason="needs a built hle_ops.json")

HEADER_REL_OF = None      # image() derives it; tests read img.header_rel


def annot(img):
    w, r = A.walk(img)
    return w, r


# =========================================================================== the PSX address space
def test_image_code_address_resolves_to_a_code_offset():
    kind, rel, _d = A.classify_psx(PSX + 0x40, PSX, 0x100, 0x400)
    assert (kind, rel) == ("image_code", 0x40)


def test_image_data_address_lands_past_header_rel():
    kind, rel, detail = A.classify_psx(PSX + 0x180, PSX, 0x100, 0x400)
    assert kind == "image_data" and rel == 0x180 and detail == "image.bss"


def test_the_program_table_and_sysstruct_slot_are_named():
    hdr = 0x100
    assert A.classify_psx(PSX + hdr + 0x10, PSX, hdr, 0x400)[2] == "header.programTable"
    assert A.classify_psx(PSX + hdr + 0x48, PSX, hdr, 0x400)[2] == "header.sysStructPtr"


def test_the_sibling_chunk_image_is_recognised():
    kind, rel, _d = A.classify_psx(PSX + A.CHUNK_STRIDE + 0x20, PSX, 0x100, 0x400)
    assert (kind, rel) == ("sibling_image", 0x20)


def test_main_ram_outside_the_container_is_psx_ram():
    assert A.classify_psx(0x80000010, PSX, 0x100, 0x400)[0] == "psx_ram"


def test_the_scratchpad_arm_matches_the_dlls_translator():
    kind, rel, _d = A.classify_psx(0x1F800020, PSX, 0x100, 0x400)
    assert (kind, rel) == ("scratchpad", 0x20)


def test_a_negative_integer_constant_is_not_a_pointer():
    """`lui 0xffff` + `addiu` makes 0xFFFF####, which satisfies the DLL's bank mask.  Admitting it
    would relabel ordinary negative constants as 'host bank 255' pointers."""
    assert A.classify_psx(0xFFFFFF00, PSX, 0x100, 0x400)[0] == "host_bank"   # the DLL's own arm
    assert not A.looks_like_psx_pointer(0xFFFFFF00)                          # ... but never a CONST
    assert not A.looks_like_psx_pointer(0x0000FFFF)
    assert A.looks_like_psx_pointer(PSX + 0x40)


def test_a0000000_mirror_is_main_ram_too():
    assert A.classify_psx(0xA01E7740, PSX, 0x100, 0x400)[:2] == ("image_code", 0x40)


# =========================================================================== data refs
def test_a_lui_addiu_pair_is_recorded_as_a_pointer():
    img = image([lui(V0, (PSX + 0x200) >> 16), addiu(V0, V0, (PSX + 0x200) & 0xFFFF),
                 jr(RA), nop()])
    w, r = annot(img)
    refs = A.image_data_refs(img, w, r)
    assert any(d.how == "pointer" and d.addr == PSX + 0x200 for d in refs)


def test_a_lui_ori_pair_is_recorded_too():
    img = image([lui(V0, PSX >> 16), ori(V0, V0, 0x300), jr(RA), nop()])
    w, r = annot(img)
    assert any(d.addr == (PSX & 0xFFFF0000) | 0x300 for d in A.image_data_refs(img, w, r))


def test_a_load_off_a_constant_base_records_its_effective_address():
    img = image([lui(V0, 0x801F), lw(V1, -0x1000, V0), jr(RA), nop()])
    w, r = annot(img)
    refs = [d for d in A.image_data_refs(img, w, r) if d.how == "load"]
    assert refs and refs[0].addr == (0x801F0000 - 0x1000) & 0xFFFFFFFF


def test_a_store_is_distinguished_from_a_load():
    img = image([lui(V0, 0x801F), sw(V1, -0x1000, V0), jr(RA), nop()])
    w, r = annot(img)
    assert [d.how for d in A.image_data_refs(img, w, r) if d.how in ("load", "store")] == ["store"]


def test_small_integer_constants_never_enter_the_map():
    img = image([addiu(V0, ZERO, 12), ori(V1, ZERO, 0x40), jr(RA), nop()])
    w, r = annot(img)
    assert not [d for d in A.image_data_refs(img, w, r) if d.how == "pointer"]


def test_a_clobbered_base_register_stops_producing_addresses():
    """After `lw $v0, ...` the base register's constant is gone; a later load off it must not be
    reported against a stale value."""
    img = image([lui(V0, 0x801F), lw(V0, 0, V0), lw(V1, 0x20, V0), jr(RA), nop()])
    w, r = annot(img)
    addrs = [d.addr for d in A.image_data_refs(img, w, r) if d.how == "load"]
    assert addrs == [0x801F0000]


def test_data_ref_summary_counts_by_region():
    img = image([lui(V0, (PSX + 0x200) >> 16), addiu(V0, V0, (PSX + 0x200) & 0xFFFF),
                 jr(RA), nop()])
    w, r = annot(img)
    assert sum(A.data_ref_summary(A.image_data_refs(img, w, r)).values()) >= 1


# =========================================================================== observed arity
def _hle_image(op, argsetup):
    """A tiny program that sets up `argsetup` then makes one HLE call to `op`."""
    words = [lw(V0, 0x10, S0), lw(V1, 4 * op, V0)] + argsetup + [jalr(V1), nop(), jr(RA), nop()]
    return image(words)


def test_observed_arity_counts_the_argument_registers_a_site_sets():
    img = _hle_image(26, [addiu(A0, ZERO, 1), addiu(A1, ZERO, 2)])
    w, r = annot(img)
    obs = A.observed_arities(w, r)
    assert set(obs.values()) == {2}


def test_observed_arity_is_zero_when_no_argument_register_is_touched():
    img = _hle_image(30, [])
    w, r = annot(img)
    assert set(A.observed_arities(w, r).values()) == {0}


def test_observed_arity_uses_the_highest_register_not_the_count():
    """$a0 and $a2 set, $a1 not: O32 arity is 3, not 2."""
    img = _hle_image(9, [addiu(A0, ZERO, 1), addiu(A2, ZERO, 3)])
    w, r = annot(img)
    assert set(A.observed_arities(w, r).values()) == {3}


# =========================================================================== the confidence contract
def _row(**kw):
    base = dict(op=0, name="x", confidence="high", corpus_support="arity-mode", arity=1,
                arg_kinds="i", returns="void", native_fn="0x1000",
                native_fn_confirmed_by_stub=True, touches=[], touches_deep=[],
                evidence="stub 0x1: arity 1; corpus: 5 call sites ... AGREES", call_sites=5,
                effects=1, creature_effects=0)
    base.update(kw)
    return base


def test_a_high_row_with_both_evidence_streams_passes():
    assert A.check_confidence_rule({0: _row()}) == []


def test_a_high_row_without_a_corpus_line_is_rejected():
    assert A.check_confidence_rule({0: _row(evidence="stub 0x1: arity 1")})


def test_a_high_row_without_a_handler_stub_is_rejected():
    assert A.check_confidence_rule({0: _row(evidence="corpus: 5 call sites")})


def test_a_high_row_whose_corpus_disagrees_is_rejected():
    assert A.check_confidence_rule({0: _row(evidence="stub 0x1; corpus: ... DISAGREES")})


def test_a_high_row_with_no_stub_terminator_is_rejected():
    assert A.check_confidence_rule({0: _row(returns=None)})


def test_an_unknown_corpus_support_kind_is_rejected():
    assert A.check_confidence_rule({0: _row(corpus_support="vibes")})


def test_medium_and_low_rows_are_not_policed_by_the_high_contract():
    assert A.check_confidence_rule({0: _row(confidence="medium", evidence="")}) == []


def test_confidence_histogram_counts_unnamed_as_a_bucket():
    hist = A.confidence_histogram({0: _row(), 1: _row(confidence=None, name=None)})
    assert hist["high"] == 1 and hist["unnamed"] == 1


# =========================================================================== the global rule ladder
def test_a_single_global_rule_must_match_the_touch_set_exactly():
    """Touching the translation AND the vertex bank must not be labelled a bare
    `set_gte_translation` -- a wrong confident name is the defect this guards."""
    assert A.global_semantics(["gteTranslation"])[0] == "set_gte_translation"
    assert A.global_semantics(["gteTranslation", "gteVertexBank"]) is None


def test_a_broad_rule_may_match_as_a_subset():
    got = A.global_semantics(["gteRotationMatrix", "gteTranslation", "gteVertexBank", "gteH"])
    assert got[0] == "gte_transform_vertices"


def test_the_most_specific_rule_wins():
    assert A.global_semantics(["otzArray", "screenXYArray", "gteRotationMatrix"])[0] == \
        "emit_primitive_to_ordering_table"


def test_an_unmapped_touch_set_yields_no_name():
    assert A.global_semantics(["psxBankTable"]) is None


# =========================================================================== function segmentation
def test_a_single_entry_program_is_one_function():
    img = image([addiu(SP, SP, -16), addiu(V0, ZERO, 1), jr(RA), addiu(SP, SP, 16)])
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    assert len(seg.functions) == 1 and seg.functions[0].role == "program-entry"
    assert seg.clean and not seg.midbody_targets


def test_a_jal_target_becomes_its_own_function():
    callee = ORIGIN + 0x40
    words = [addiu(SP, SP, -16), jal(callee), nop(), jr(RA), nop()]
    words += [nop()] * ((callee - ORIGIN) // 4 - len(words))
    words += [addiu(V0, ZERO, 7), jr(RA), nop()]
    img = image(words)
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    assert {f.start for f in seg.functions} == {ORIGIN, callee}
    assert seg.clean


def test_every_reachable_instruction_belongs_to_exactly_one_function():
    callee = ORIGIN + 0x40
    words = [addiu(SP, SP, -16), jal(callee), nop(), jr(RA), nop()]
    words += [nop()] * ((callee - ORIGIN) // 4 - len(words))
    words += [addiu(V0, ZERO, 7), jr(RA), nop()]
    img = image(words)
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    assert all(len(v) == 1 for v in seg.owners.values())
    assert set(seg.owners) == set(r.instrs)


def test_a_callee_reached_from_two_callers_is_still_one_function():
    callee = ORIGIN + 0x40
    words = [jal(callee), nop(), jal(callee), nop(), jr(RA), nop()]
    words += [nop()] * ((callee - ORIGIN) // 4 - len(words))
    words += [jr(RA), nop()]
    img = image(words)
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    assert len(seg.functions) == 2 and seg.clean


def test_a_branch_into_another_functions_body_is_reported_not_hidden():
    """A `jal` landing one instruction INSIDE the entry's own body: the target is a start AND is
    flooded from the entry, so it must surface as a shared instruction, never be silently split."""
    mid = ORIGIN + 8
    img = image([addiu(SP, SP, -16), jal(mid), nop(), addiu(V0, ZERO, 1), jr(RA), nop()])
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    assert seg.shared or seg.midbody_targets


def test_a_leaf_with_no_calls_is_labelled_leaf_helper():
    img = image([addiu(V0, ZERO, 1), jr(RA), nop()])
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    seg.functions[0].entry = False
    assert seg.functions[0].role == "leaf-helper"


def test_a_function_records_the_hle_ops_it_calls():
    img = _hle_image(164, [addiu(A0, ZERO, 1)])
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    assert 164 in seg.functions[0].hle_ops and seg.functions[0].hle_calls == 1


def test_a_gte_instruction_is_counted_and_tagged():
    img = image([cop2(0x0180001), jr(RA), nop()])
    w, r = annot(img)
    seg = A.segment_functions(img, w, r, {})
    assert seg.functions[0].gte == 1 and "gte-code" in seg.functions[0].tags


def test_role_tags_come_from_the_op_dictionary():
    ops = {164: {"op": 164, "name": "Hi_GetSummonBoneMatrix", "touches": ["summonModels"],
                 "touches_deep": []}}
    tags = A.role_tag_map(ops)
    assert 164 in tags["bone"] and 164 in tags["summon-slot"]


def test_role_tags_ignore_deep_touches():
    """Depth-2 touch sets make every Hi_Register* op a 'primitive emitter'; a tag that broad
    distinguishes nothing."""
    ops = {21: {"op": 21, "name": "Hi_RegisterSolidEffModel", "touches": [],
                "touches_deep": ["otzArray", "screenXYArray"]}}
    assert 21 not in A.role_tag_map(ops).get("primitive", set())


def test_switch_cases_are_attributed_to_the_dispatching_function():
    """The R1 switch idiom: sltiu / sll 2 / lui+addiu table / addu / lw / jr.  The cases belong to
    the function that dispatches them, not to new functions of their own."""
    base = ORIGIN + 0x40
    tbl = base + 0x20
    words = [
        sltiu(V1, A0, 2), beq(V1, ZERO, ORIGIN + 4, base), nop(),
        sll(V0, A0, 2), lui(V1, (PSX + tbl) >> 16), addiu(V1, V1, (PSX + tbl) & 0xFFFF),
        addu(V0, V0, V1), lw(V0, 0, V0), jr(V0), nop(),
    ]
    words += [nop()] * ((base - ORIGIN) // 4 - len(words))
    words += [jr(RA), nop()]                                  # base   = the default arm
    words += [nop()] * ((tbl - ORIGIN) // 4 - len(words))
    words += [PSX + base, PSX + base + 8]                     # the table
    words += [jr(RA), nop()]
    img = image(words)
    w, r = annot(img)
    if not r.jump_tables:
        pytest.skip("the synthetic switch did not reproduce the recovered idiom")
    seg = A.segment_functions(img, w, r, {})
    assert seg.clean
    assert any(f.switches for f in seg.functions)


# =========================================================================== the census
def test_ops_of_reads_a_polymorphic_call_site():
    c = T.CallSite(0, "hle_multi", "jalr", detail="merge of 2 paths: table[26,147]")
    assert A._ops_of(c) == [26, 147]


def test_ops_of_reads_a_plain_hle_site():
    assert A._ops_of(T.CallSite(0, "hle", "jalr", hle_op=25)) == [25]


def test_ops_of_ignores_an_in_image_call():
    assert A._ops_of(T.CallSite(0, "in_image", "jal", target=4)) == []


def test_phase_bins_split_the_code_region_in_thirds():
    assert A._phase_bin(0, 300) == "first-third"
    assert A._phase_bin(150, 300) == "middle-third"
    assert A._phase_bin(299, 300) == "last-third"


def test_op_census_index_hit_rate_is_zero_when_untested():
    assert A.OpCensus(op=1).index_hit_rate == 0.0


def test_op_census_index_hit_rate():
    st = A.OpCensus(op=102, index_in_range=98, index_out_of_range=2)
    assert abs(st.index_hit_rate - 0.98) < 1e-9


# =========================================================================== the memory map itself
def test_every_mapped_global_carries_a_citation():
    for rva, (name, src) in A.NAMED_GLOBALS.items():
        assert name and src, "%#x has no citation" % rva


def test_the_map_has_no_duplicate_names():
    names = [n for n, _ in A.NAMED_GLOBALS.values()]
    assert len(names) == len(set(names))


def test_the_calibration_set_is_exactly_the_twelve_named_ops():
    assert len(A.CALIBRATION_OPS) == 12
    known = T.load_hle_names()
    if known:
        assert set(A.CALIBRATION_OPS) == set(known)


def test_the_handler_abi_constants_match_r1s_op_count():
    assert len(A.CTX_ARG_SLOTS) == len(T.ARG_REGS)
    assert sorted(A.CTX_ARG_SLOTS.values()) == [0, 1, 2, 3]


# =========================================================================== DLL-backed
@needs_dll
def test_the_dispatcher_jump_table_is_216_entries():
    dll = A.DllView()
    assert len(dll.jt) == T.HLE_OP_COUNT


@needs_dll
def test_calibration_re_derives_all_twelve_known_ops():
    rows = A.calibration(A.DllView())
    misses = [(r["op"], r["derived_name"], r["arity"], r["expect_arity"])
              for r in rows if not (r["arity_ok"] and r["name_ok"])]
    assert not misses, "calibration misses: %s" % misses


@needs_dll
def test_the_inline_argument_idiom_is_required_for_calibration():
    """Ops 11/12/25/65 pass every argument through the INLINE `[ctx+0xca8..0xcb4]` form.  If the
    reader only knew `mov edx,i / call getArgInt`, these would come out with arity 0 or 1."""
    dll = A.DllView()
    for op, want in ((11, 2), (12, 3), (25, 5), (65, 4)):
        assert dll.handler(op).arity == want


@needs_dll
def test_the_two_return_tails_are_the_only_epilogues_used():
    dll = A.DllView()
    rets = collections.Counter(dll.handler(op).ret for op in range(T.HLE_OP_COUNT))
    assert set(rets) <= {"void", "int", "ptr", "none", None}
    assert rets["void"] + rets["int"] + rets["ptr"] > 200


@needs_dll
def test_a_noop_ops_jump_table_slot_is_the_return_tail_itself():
    dll = A.DllView()
    noops = [op for op in range(T.HLE_OP_COUNT) if dll.handler(op).noop]
    assert noops and all(dll.jt[op] in (A.TAIL_RETURN_INT_RVA, A.TAIL_RETURN_PTR_RVA)
                         for op in noops)


@needs_dll
def test_the_unwind_chain_gives_exact_function_boundaries():
    """Nearest-preceding-.pdata-begin instead puts two different Hi_ names on one op."""
    dll = A.DllView()
    fn = dll.function_of(0x18630)                       # Hi_GetSummonBoneMatrix
    assert fn is not None and dll.profile(fn).names == ("Hi_GetSummonBoneMatrix",)


@needs_dll
def test_an_import_thunk_is_transparent_so_trig_stays_depth_zero():
    dll = A.DllView()
    sig14, sig15 = dll.handler(14), dll.handler(15)
    p14, p15 = dll.profile_op(14, sig14), dll.profile_op(15, sig15)
    assert "cos" in p14.crt_direct and "sin" in p15.crt_direct


@needs_dll
def test_the_sentinel_table_base_is_still_where_r1_put_it():
    dll = A.DllView()
    words = struct.unpack("<%dI" % T.HLE_OP_COUNT,
                          dll.pe.get_data(T.DLL_HLE_SENTINEL_TABLE_RVA, 4 * T.HLE_OP_COUNT))
    assert all(w == (T.HLE_SENTINEL_MASK | i) for i, w in enumerate(words))


# =========================================================================== corpus-backed
@needs_corpus
def test_corpus_data_refs_all_resolve_inside_their_own_image():
    outside = collections.Counter()
    for img in T.corpus_images():
        w, r = A.walk(img)
        for d in A.image_data_refs(img, w, r):
            if not (d.kind.startswith("image") or d.kind == "scratchpad"):
                outside[d.kind] += 1
    assert not outside, "addresses leaving the id-3 image: %s" % dict(outside)


@needs_corpus
def test_corpus_segmentation_has_no_orphan_or_shared_instruction():
    bad = []
    for img in T.corpus_images():
        w, r = A.walk(img)
        seg = A.segment_functions(img, w, r, {})
        if seg.orphans or seg.shared or seg.midbody_targets:
            bad.append((img.label, len(seg.orphans), len(seg.shared), len(seg.midbody_targets)))
    assert not bad, "segmentation anomalies: %s" % bad[:10]


@needs_corpus
def test_ef227s_program_never_addresses_the_camera_sub_file():
    """The refutation-shaped gate: if a pointer into another resource existed, this would find it."""
    blob = open(os.path.join(CORPUS, "ef227.bytes"), "rb").read()
    for img in T.id3_images(blob, "ef227"):
        w, r = A.walk(img)
        refs = A.image_data_refs(img, w, r)
        assert refs, "no data references recovered at all -- the pass is broken, not the format"
        assert all(d.kind.startswith("image") or d.kind == "scratchpad" for d in refs)


@needs_corpus
def test_ef227s_subfile_indices_all_address_a_real_sub_file():
    import ef_container as ec
    blob = open(os.path.join(CORPUS, "ef227.bytes"), "rb").read()
    counts = {}
    for ch in ec.parse_header(blob).chunks:
        for res in ch.resources:
            if res.id == 2:
                counts[ch.slot] = len(ec.parse_directory(blob, res.offset))
    checked = 0
    for img in T.id3_images(blob, "ef227"):
        _w, r = A.walk(img)
        n = counts.get(img.chunk_slot)
        for c in r.calls:
            if c.kind == "hle" and c.hle_op == A.SUBFILE_OP and c.args[1] is not None and n:
                checked += 1
                assert (c.args[1] & A.SUBFILE_INDEX_MASK) < n
    assert checked > 10


@needs_corpus
def test_ef227s_two_entries_are_switch_driven_state_machines():
    blob = open(os.path.join(CORPUS, "ef227.bytes"), "rb").read()
    entries = []
    for img in T.id3_images(blob, "ef227"):
        w, r = A.walk(img)
        seg = A.segment_functions(img, w, r, {})
        entries += [f for f in seg.functions if f.entry]
    assert len(entries) == 2
    assert all(f.switches >= 1 and f.cases >= 5 for f in entries)


# =========================================================================== the built dictionary
@needs_ops
def test_the_committed_dictionary_covers_every_op_exactly_once():
    ops = A.load_hle_ops()
    assert sorted(ops) == list(range(T.HLE_OP_COUNT))


@needs_ops
def test_the_committed_dictionary_obeys_the_high_confidence_contract():
    assert A.check_confidence_rule(A.load_hle_ops()) == []


@needs_ops
def test_every_named_row_carries_evidence_and_a_confidence():
    for op, row in A.load_hle_ops().items():
        if row["name"]:
            assert row["confidence"] in ("high", "medium", "low"), op
            assert row["evidence"], op
        else:
            assert row["confidence"] is None, op


@needs_ops
def test_low_confidence_names_are_hedged():
    """A descriptive name at low confidence is fine; an unhedged one reads as a claim."""
    for op, row in A.load_hle_ops().items():
        if row["confidence"] == "low":
            assert row["name"].endswith("?") or row["name"].startswith(("touches_", "summon_")), \
                "op %d: %r" % (op, row["name"])


@needs_ops
def test_the_twelve_known_ops_keep_their_published_names():
    ops = A.load_hle_ops()
    for op, name in (T.load_hle_names() or {}).items():
        assert ops[op]["name"] == name, "op %d: %r != %r" % (op, ops[op]["name"], name)
        assert ops[op]["confidence"] == "high"


@needs_ops
def test_the_dictionary_is_valid_committable_json_with_no_byte_payload():
    with open(A.HLE_OPS_JSON, "r", encoding="utf-8") as fh:
        raw = fh.read()
    rows = json.loads(raw)
    assert isinstance(rows, list) and len(rows) == T.HLE_OP_COUNT
    allowed = {"op", "name", "confidence", "callback_command", "callback_code", "callback_submode",
               "corpus_support", "arity", "arg_kinds", "returns",
               "native_fn", "native_fn_confirmed_by_stub", "touches", "touches_deep", "evidence",
               "call_sites", "effects", "creature_effects"}
    for row in rows:
        assert set(row) == allowed, set(row) ^ allowed
