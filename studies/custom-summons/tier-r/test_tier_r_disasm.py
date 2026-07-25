"""Tests for the TIER R rung-1 disassembler.

Runs WITHOUT the extracted corpus and WITHOUT the game install: the unit tests synthesise tiny id-3
images with a small MIPS encoder below.  Corpus and DLL tests are skipped when their inputs are
absent (the kit's own convention -- see ff9mapkit/tests/test_battlecsv.py).

    py -m pytest studies/custom-summons/tier-r/test_tier_r_disasm.py -q
"""
from __future__ import annotations

import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tier_r_disasm as T   # noqa: E402

CORPUS = T.SCRATCH_CORPUS
have_corpus = os.path.isdir(CORPUS) and bool(
    [f for f in os.listdir(CORPUS) if f.startswith("ef")]) if os.path.isdir(CORPUS) else False
try:
    import refkit                                    # noqa: F401
    have_dll = os.path.isfile(refkit.DLL_X64)
except Exception:                                     # pragma: no cover
    have_dll = False

needs_corpus = pytest.mark.skipif(not have_corpus, reason="needs the extracted ef###.bytes corpus")
needs_dll = pytest.mark.skipif(not have_dll, reason="needs the installed FF9SpecialEffectPlugin.dll")

PSX = 0x801E7700
ZERO, AT, V0, V1, A0, A1, A2, A3 = 0, 1, 2, 3, 4, 5, 6, 7
S0, S1, SP, RA = 16, 17, 29, 31


# --------------------------------------------------------------------------- a tiny MIPS encoder
def addiu(rt, rs, imm): return 0x24000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)
def ori(rt, rs, imm):   return 0x34000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)
def lui(rt, imm):       return 0x3C000000 | rt << 16 | (imm & 0xFFFF)
def lw(rt, off, base):  return 0x8C000000 | base << 21 | rt << 16 | (off & 0xFFFF)
def sw(rt, off, base):  return 0xAC000000 | base << 21 | rt << 16 | (off & 0xFFFF)
def sltiu(rt, rs, imm): return 0x2C000000 | rs << 21 | rt << 16 | (imm & 0xFFFF)
def sll(rd, rt, sa):    return rt << 16 | rd << 11 | sa << 6
def addu(rd, rs, rt):   return rs << 21 | rt << 16 | rd << 11 | 0x21
def jr(rs):             return rs << 21 | 0x08
def jalr(rs, rd=RA):    return rs << 21 | rd << 11 | 0x09
def cop2(cofun):        return 0x4A000000 | (cofun & 0x1FFFFFF)
def nop():              return 0


def beq(rs, rt, here, there): return 0x10000000 | rs << 21 | rt << 16 | (((there - here) // 4 - 1) & 0xFFFF)
def bne(rs, rt, here, there): return 0x14000000 | rs << 21 | rt << 16 | (((there - here) // 4 - 1) & 0xFFFF)
def j(target, psx=PSX):       return 0x08000000 | (((psx + target) >> 2) & 0x3FFFFFF)
def jal(target, psx=PSX):     return 0x0C000000 | (((psx + target) >> 2) & 0x3FFFFFF)


ORIGIN = 4      # word 0 of a real image is its own header pointer, never an instruction


def image(words, progs=(ORIGIN,), tail=b"", psx=PSX, source="synth"):
    """Assemble a synthetic id-3 image.

    ``words[i]`` lands at offset ``ORIGIN + 4*i``; word 0 holds the image's own header pointer, as
    in every stock image.  Then ``tail`` (embedded data, still below headerRel), the two-word header
    and the 16-entry program table.  An ABSENT program slot is encoded 0, which is exactly why no
    live program can sit at offset 0.
    """
    pay = bytearray(struct.pack("<I", 0))
    for w in words:
        pay += struct.pack("<I", w)
    pay += tail
    header_rel = len(pay)
    pay[0:4] = struct.pack("<I", psx + header_rel)
    pay += struct.pack("<II", 0, 0)
    tbl = [0] * 16
    for i, p in enumerate(progs):
        tbl[i] = psx + p
    for v in tbl:
        pay += struct.pack("<I", v)
    pay += b"\0" * ((-len(pay)) % 0x800)
    return T.Id3Image(source, 0, psx, header_rel, bytes(pay),
                      tuple((v & 0x0FFFFFFF) - (psx & 0x0FFFFFFF) if v else 0 for v in tbl))


def container(img: T.Id3Image) -> bytes:
    """Wrap one id-3 payload in the container format fn 0xd390 walks."""
    hdr = bytearray()
    hdr += struct.pack("<h", 1)                        # chunkCount
    hdr += struct.pack("<hh", 0, 1)                    # chunkIndex, resourceCount
    hdr += struct.pack("<bbh", 3, 0, len(img.payload) >> 11)
    hdr += b"\0" * (0x800 - len(hdr))
    return bytes(hdr) + img.payload


def walk(img):
    return T.walk_image(img)


# --------------------------------------------------------------------------- the ISA mirror
def test_isa_mirror_is_99_ordered_entries():
    assert len(T.ISA) == 99
    assert [e.idx for e in T.ISA] == list(range(99))
    assert T.ISA[0].name == "nop" and T.ISA[98].name == "syscall"


def test_greedy_first_match_order_is_load_bearing():
    d = T.DEFAULT_DECODER
    assert d.classify(0).name == "nop"                       # entry 0 beats sll
    assert d.classify(addu(S0, ZERO, V0)).name == "move"     # entry 4 beats addu
    assert d.classify(addiu(V0, ZERO, 5)).name == "addiu"    # entry 29 beats the `li` alias
    assert d.classify(ori(V0, ZERO, 5)).name == "ori"        # entry 33 beats the `li` alias
    assert d.classify(0x10000000).name == "beq"              # entry 52 beats `b`
    for shadowed in (35, 36, 60):
        e = T.ISA[shadowed]
        assert d.classify(e.match).idx != shadowed, "entry %d should be unreachable" % shadowed


def test_delay_slot_flags_are_exactly_the_transfers():
    flagged = {e.name for e in T.ISA if e.is_transfer}
    assert flagged == {"jalr", "jr", "j", "jal", "beq", "bne", "bgez", "bltz", "bltzal",
                       "bgezal", "blez", "bgtz", "b",
                       "bc0f", "bc1f", "bc2f", "bc3f", "bc0t", "bc1t", "bc2t", "bc3t"}


# --------------------------------------------------------------------------- operand extraction
def test_operands_follow_the_dll_thunks():
    d = T.DEFAULT_DECODER
    i = d.decode(addiu(SP, SP, -400), 0x9D4, PSX)
    assert (i.name, i.ops) == ("addiu", (SP, SP, -400))
    i = d.decode(lw(V0, 564, S1), 0x100, PSX)
    assert i.name == "lw" and i.ops == (V0, 564, S1) and i.base_reg == S1
    i = d.decode(lui(V0, 0x801E), 0, PSX)
    assert i.ops == (V0, 0x801E)
    i = d.decode(cop2(0x0180001), 0, PSX)
    assert i.name == "cop2" and i.ops == (0x0180001,)


def test_branch_target_is_pc_plus_4_plus_simm4():
    d = T.DEFAULT_DECODER
    w = beq(A0, ZERO, 0x100, 0x140)
    assert d.decode(w, 0x100, PSX).op(T.Ex.BTARGET) == 0x140
    w = bne(A0, ZERO, 0x200, 0x1C0)          # backwards
    assert d.decode(w, 0x200, PSX).op(T.Ex.BTARGET) == 0x1C0


def test_jump_target_is_relocated_off_the_psx_base():
    d = T.DEFAULT_DECODER
    assert d.decode(j(0x848), 0x10, PSX).ops[0] == 0x848
    assert d.decode(jal(0x9D4), 0x10, PSX).ops[0] == 0x9D4
    other = PSX + 0x5000                      # a chunk-1 image
    assert d.decode(j(0x100, psx=other), 0x10, other).ops[0] == 0x100


def test_invalid_word_is_rejected():
    assert T.DEFAULT_DECODER.classify(0xFFFFFFFF) is None


# --------------------------------------------------------------------------- delay slots (G5)
def test_taken_branch_executes_its_delay_slot():
    #  4: bne a0,zero,0x18   8: addiu (THE SLOT)   c,10: fall-through   14: never   18,1c: target
    words = [bne(A0, ZERO, 0x04, 0x18), addiu(A0, ZERO, 7),
             jr(RA), nop(),
             0xFFFFFFFF,
             jr(RA), nop()]
    r = walk(image(words))
    assert 0x08 in r.instrs and 0x08 in r.delay_slots       # the slot RAN
    assert r.instrs[0x08].name == "addiu"
    assert 0x18 in r.instrs and 0x1C in r.delay_slots       # the target and its own slot
    assert 0x14 not in r.instrs                             # nothing reaches the filler
    assert r.invalid == []                                  # so it is never decoded


def test_beq_zero_zero_is_not_constant_folded():
    """`beq $0,$0` is entry 52 (entry 60 `b` is shadowed by it), and the walk stays conservative:
    both arms are followed.  A disassembler that folded the condition would drop real code the
    moment a compiler emitted the same encoding for a computed-always branch."""
    words = [beq(ZERO, ZERO, 0x04, 0x14), nop(), jr(RA), nop(), jr(RA), nop()]
    r = walk(image(words))
    assert 0x0C in r.instrs and 0x14 in r.instrs


def test_conditional_branch_walks_both_arms():
    words = [addiu(A0, ZERO, 1), beq(A0, ZERO, 0x08, 0x18), nop(),
             addiu(A1, ZERO, 2), jr(RA), nop()]
    r = walk(image(words))
    assert 0x10 in r.instrs and 0x18 in r.instrs            # fall-through AND taken


def test_jr_ra_executes_its_slot_then_terminates():
    words = [jr(RA), addiu(SP, SP, 40), 0xFFFFFFFF, 0xFFFFFFFF]
    r = walk(image(words))
    assert 0x08 in r.instrs and 0x08 in r.delay_slots
    assert r.instrs[0x08].name == "addiu"
    assert 0x0C not in r.instrs and r.invalid == []


def test_unconditional_j_does_not_fall_through_past_its_slot():
    words = [j(0x14), nop(), 0xFFFFFFFF, 0xFFFFFFFF, jr(RA), nop()]
    r = walk(image(words))
    assert 0x08 in r.delay_slots
    assert 0x0C not in r.instrs and 0x14 in r.instrs and r.invalid == []


def test_jal_returns_to_the_instruction_after_the_slot():
    words = [jal(0x18), nop(), addiu(A0, ZERO, 1), jr(RA), nop(),
             addiu(A1, ZERO, 2), jr(RA), nop()]
    r = walk(image(words))
    assert 0x18 in r.instrs                                  # the callee
    assert 0x0C in r.instrs                                  # the return point (off+8)


def test_branch_in_a_delay_slot_is_flagged_not_crashed():
    words = [beq(ZERO, ZERO, 0x04, 0x14), j(0x1C), nop(), nop(),
             jr(RA), nop(), jr(RA), nop()]
    r = walk(image(words))
    assert any("branch in delay slot" in a for a in r.anomalies)
    assert 0x08 in r.instrs and r.invalid == []


def test_branch_INTO_a_delay_slot_is_walked_sanely():
    #  the target of the bne at 0x04 is 0x10, which is itself the delay slot of the j at 0x0c
    words = [bne(A0, ZERO, 0x04, 0x10), nop(), j(0x1C), addiu(A1, ZERO, 3),
             0xFFFFFFFF, 0xFFFFFFFF, jr(RA), nop()]
    r = walk(image(words))
    assert 0x10 in r.instrs and 0x10 in r.delay_slots
    assert 0x1C in r.instrs                                  # reached through the j
    assert r.invalid == []


# --------------------------------------------------------------------------- reachability vs data
def test_embedded_data_after_a_return_is_never_decoded():
    blob = struct.pack("<8I", *([0xDEADBEEF] * 8))           # not decodable as MIPS
    words = [addiu(SP, SP, -16), jr(RA), addiu(SP, SP, 16)]
    img = image(words, tail=blob)
    r = walk(img)
    assert r.invalid == []
    assert max(r.instrs) == 0x0C
    kinds = {k for _a, _b, k in T.region_runs(img, r)}
    assert "data" in kinds                                    # described, not swallowed
    assert T.linear_score(img) < 1.0                          # the ANTI-pattern would choke here


def test_coverage_is_reachable_bytes_over_header_rel():
    words = [addiu(SP, SP, -16), jr(RA), nop()]
    img = image(words)
    r = walk(img)
    # word 0 is the header pointer, not code: 12 of the 16 bytes below headerRel are reachable
    assert r.header_rel == 16 and r.reached_bytes == 12 and r.coverage == 0.75


# --------------------------------------------------------------------------- HLE recognition
def test_hle_call_is_named_from_the_load_offset():
    op = 164                                                  # Hi_GetSummonBoneMatrix
    words = [lw(V0, 4 * op, S1), nop(), jalr(V0), addiu(A0, ZERO, 3), jr(RA), nop()]
    r = walk(image(words))
    calls = [c for c in r.calls if c.kind == "hle"]
    assert len(calls) == 1
    assert calls[0].hle_op == op
    assert calls[0].args[0] == 3                              # $a0 set IN THE DELAY SLOT counts


def test_hle_args_track_lui_ori_and_addiu_chains():
    words = [lui(A0, 0x1234), ori(A0, A0, 0x5678), addiu(A1, ZERO, -2),
             lw(V0, 4 * 25, S1), jalr(V0), nop(), jr(RA), nop()]
    r = walk(image(words))
    c = [x for x in r.calls if x.kind == "hle"][0]
    assert c.hle_op == 25 and c.args[0] == 0x12345678
    assert c.args[1] == (-2 & 0xFFFFFFFF)


def test_in_image_jal_is_classified_in_image():
    words = [jal(0x14), nop(), jr(RA), nop(), addiu(SP, SP, -8), jr(RA), nop()]
    r = walk(image(words))
    c = [x for x in r.calls if x.via == "jal"]
    assert len(c) == 1 and c[0].kind == "in_image" and c[0].target == 0x14


def test_a_non_table_function_pointer_call_stays_unresolved():
    words = [lw(V0, 0x400, S1), nop(), jalr(V0), nop(), jr(RA), nop()]   # 0x400 > 216*4
    r = walk(image(words))
    assert [c.kind for c in r.calls if c.via == "jalr"] == ["unresolved"]


# --------------------------------------------------------------------------- switch tables
def test_switch_jump_table_is_recovered_and_walked():
    #     4 sltiu at,a0,2 / 8 beq at,zero,default / c lui v0 / 10 addiu v0 / 14 sll v1 /
    #    18 addu v1,v1,v0 / 1c lw v0,0(v1) / 20 nop / 24 jr v0 / 28 nop
    #    2c default: jr ra   34 case0: jr ra   3c case1: jr ra    44..4b the table
    tbl_off = 0x44
    words = [
        sltiu(AT, A0, 2),
        beq(AT, ZERO, 0x08, 0x2C),
        lui(V0, (PSX + tbl_off) >> 16),
        addiu(V0, V0, (PSX + tbl_off) & 0xFFFF),
        sll(V1, A0, 2),
        addu(V1, V1, V0),
        lw(V0, 0, V1),
        nop(),
        jr(V0),
        nop(),
        jr(RA), nop(),
        jr(RA), nop(),
        jr(RA), nop(),
        PSX + 0x34, PSX + 0x3C,
    ]
    img = image(words)
    r = walk(img)
    assert len(r.jump_tables) == 1
    jt = r.jump_tables[0]
    assert jt.bound == 2 and jt.targets == (0x34, 0x3C) and jt.off == tbl_off
    assert 0x34 in r.instrs and 0x3C in r.instrs              # both cases walked
    assert r.invalid == []


def test_switch_table_read_stops_at_a_non_pointer():
    tbl_off = 0x34
    words = [
        lui(V0, (PSX + tbl_off) >> 16), addiu(V0, V0, (PSX + tbl_off) & 0xFFFF),
        sll(V1, A0, 2), addu(V1, V1, V0), lw(V0, 0, V1), nop(), jr(V0), nop(),
        jr(RA), nop(), jr(RA), nop(),
        PSX + 0x24, 0x00000001, PSX + 0x24,                   # entry 1 is not a PSX pointer
    ]
    r = walk(image(words))
    assert r.jump_tables and r.jump_tables[0].targets == (0x24,)


# --------------------------------------------------------------------------- GTE
def test_gte_field_decode_names_the_canonical_commands():
    expect = {0x0180001: "RTPS", 0x0280030: "RTPT", 0x0480012: "MVMVA",
              0x0780010: "DPCS", 0x1400006: "NCLIP", 0x158002D: "AVSZ3"}
    for cofun, name in expect.items():
        assert T.gte_fields(cofun)["name"] == name


def test_gte_mvmva_modifier_fields():
    f = T.gte_fields(0x0480012)
    assert (f["sf"], f["mx"], f["v"], f["cv"], f["lm"]) == (1, 0, 0, 0, 0)
    assert "mx=Rot" in T.gte_text(0x0480012) and "v=V0" in T.gte_text(0x0480012)


def test_every_dll_implemented_cofun_is_named():
    for cofun, (name, _how) in T.DLL_GTE_COFUNS.items():
        assert T.gte_fields(cofun)["name"] == name
        assert T.gte_fields(cofun)["implemented"]


def test_an_unimplemented_gte_op_is_marked():
    assert not T.gte_fields(0x108041B)["implemented"]         # NCCS -- FF9 never uses it


def test_cop2_instruction_lands_in_the_histogram():
    words = [cop2(0x0180001), cop2(0x0480012), jr(RA), nop()]
    r = walk(image(words))
    assert r.cofun_hist == {0x0180001: 1, 0x0480012: 1}


# --------------------------------------------------------------------------- container glue
def test_id3_images_parses_a_synthetic_container():
    img = image([addiu(SP, SP, -16), jr(RA), nop()])
    got = T.id3_images(container(img), "synth")
    assert len(got) == 1
    assert got[0].header_rel == img.header_rel
    assert got[0].live_programs == (4,)
    assert got[0].psx_base == PSX
    r = T.walk_image(got[0])
    assert r.invalid == [] and set(r.instrs) == {4, 8, 12}


def test_listing_writer_emits_annotations(tmp_path):
    op = 149
    words = [lw(V0, 4 * op, S1), cop2(0x0180001), jalr(V0), addiu(A0, ZERO, 9), jr(RA), nop()]
    r = walk(image(words))
    p = tmp_path / "synth.asm"
    with open(p, "w", encoding="utf-8") as fh:
        T.write_listing(r, fh)
    txt = p.read_text(encoding="utf-8")
    assert "GTE RTPS" in txt
    assert "Hi_GetSummonBonePos" in txt and "$a0=0x9" in txt
    assert "[delay slot]" in txt


# --------------------------------------------------------------------------- the live DLL
@needs_dll
def test_isa_mirror_matches_the_shipping_table():
    assert T.isa_diff(T.load_isa_from_dll()) == []


@needs_dll
def test_cop2_handler_implements_exactly_our_six_cofuns():
    """The DLL's COP2 handler whole-word-matches its cofun constants; read them back."""
    pe = refkit.load()
    tab = struct.unpack("<90I", pe.get_data(0xED18, 0x168))
    handler = tab[64]                                          # decode index 65, jump index op-1
    base = refkit.image_base(pe)
    consts = set()
    for ins in refkit.disasm(pe, handler, 0xEBD5):
        if ins.mnemonic == "cmp" and ins.op_str.startswith("eax, 0x"):
            consts.add(int(ins.op_str.split("0x")[1], 16))
    assert consts == set(T.DLL_GTE_COFUNS), (sorted(consts), sorted(T.DLL_GTE_COFUNS))
    assert base == 0x180000000


@needs_dll
def test_hle_sentinel_base_is_published_to_0x21ff78():
    """The publisher pipeline in fn 0x30c20: store[i] carries call[i]'s result."""
    pe = refkit.load()
    base = refkit.image_base(pe)
    seen = []
    for ins in refkit.disasm(pe, 0x30CB5, 0x30D45):
        rva = ins.address - base
        if ins.mnemonic in ("lea", "call", "mov"):
            seen.append((rva, ins.mnemonic, ins.op_str))
    kinds = [k for _r, k, o in seen if k == "call" or (k == "mov" and o.endswith(", eax"))]
    assert kinds.count("call") == 5
    assert kinds[-1] == "mov"                                  # ends on a store: the phase is pinned
    rvas = {r: (k, o) for r, k, o in seen}
    assert rvas[0x30D07][0] == "lea" and "0x37542" in rvas[0x30D07][1]     # -> 0x68250
    assert rvas[0x30D1B][0] == "call"
    assert rvas[0x30D2E][0] == "mov" and "0x1ef244" in rvas[0x30D2E][1]    # -> 0x21FF78
    # 0x21FF78 - 0x21FF68 == the +0x10 field the effect programs load the table pointer from
    assert 0x21FF78 - 0x21FF68 == T.HLE_STRUCT_FIELD


@needs_dll
def test_sentinel_table_is_216_entries_of_ff000000_or_i():
    pe = refkit.load()
    words = struct.unpack("<217I", pe.get_data(T.DLL_HLE_SENTINEL_TABLE_RVA, 4 * 217))
    assert words[:T.HLE_OP_COUNT] == tuple(0xFF000000 | i for i in range(T.HLE_OP_COUNT))
    assert words[T.HLE_OP_COUNT] == 0


# --------------------------------------------------------------------------- the corpus
@needs_corpus
def test_corpus_shape_matches_the_format_round():
    imgs = list(T.corpus_images())
    assert len(imgs) == 385
    assert sum(len(i.live_programs) for i in imgs) == 599
    assert len({i.source for i in imgs}) == 372


@needs_corpus
def test_corpus_walk_has_no_invalid_reachable_instruction():
    bad = []
    for img in T.corpus_images():
        r = T.walk_image(img)
        bad += [(img.label, hex(o)) for o in r.invalid]
    assert bad == []


@needs_corpus
def test_corpus_prologue_census_is_589_of_599():
    n = good = 0
    for img in T.corpus_images():
        for o in img.live_programs:
            w = struct.unpack_from("<I", img.payload, o)[0]
            i = T.DEFAULT_DECODER.decode(w, o, img.psx_base)
            n += 1
            good += i.name == "addiu" and i.ops[:2] == (29, 29) and i.ops[2] < 0
    assert (good, n) == (589, 599)


@needs_corpus
def test_corpus_cofun_set_is_exactly_what_the_dll_implements():
    seen = set()
    for img in T.corpus_images():
        seen |= set(T.walk_image(img).cofun_hist)
    assert seen == set(T.DLL_GTE_COFUNS)


@needs_corpus
def test_corpus_has_no_unresolved_call_targets():
    unres = []
    for img in T.corpus_images():
        r = T.walk_image(img)
        unres += [(img.label, hex(c.off), c.detail) for c in r.calls if c.kind == "unresolved"]
    assert unres == []


@needs_corpus
def test_corpus_hle_ops_stay_inside_the_dispatcher_bound():
    ops = set()
    for img in T.corpus_images():
        for c in T.walk_image(img).calls:
            if c.kind == "hle":
                ops.add(c.hle_op)
    assert ops and min(ops) >= 0 and max(ops) < T.HLE_OP_COUNT


@needs_corpus
def test_the_embedded_data_canary_images_stay_low_on_a_linear_sweep():
    by = {i.label: i for i in T.corpus_images()}
    for label in ("ef508:c0", "ef210:c0"):
        img = by[label]
        r = T.walk_image(img)
        assert T.linear_score(img) < 0.70          # V-C8 measured 50.3% / 62.0%
        assert r.invalid == []                     # yet reachable code decodes perfectly
        runs = T.region_runs(img, r)
        data = sum(b - a for a, b, k in runs if k == "data")
        code = sum(b - a for a, b, k in runs if k == "unreached_code")
        assert data > code                          # the unreached mass really is data
