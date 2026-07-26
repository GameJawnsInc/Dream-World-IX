"""THE EXTENDED NAMEPLATE BAND (virgin cases 65-155) -- the func-0xB range-arm splice.

Stock func-0xB's last arm (`w98 >> (case-49)`) dies above case 64, capping named entrances at 5 per
world. The kit replaces the arm SECTION (the stock body's first 114 bytes) with a chain whose new
arms read the kit-reserved explored words (flags.NAMEPLATE_EXPLORED_FLOOR, gEventGlobal bytes
2006-2017), keeping every stock-reachable case byte-equivalent. These tests pin:
  * the ORACLE -- the composed stock section reproduces the real dispatcher bytes exactly (both the
    Byte[38] form and WORLD02's Byte[35] form);
  * the SEMANTICS -- a byte-walking interpreter (EBin rules: Int32 ops, C# >> masks count&31) runs
    all 256 Byte[39] values through both chains: stock-domain equivalence + new-band correctness;
  * the maps and validations around it (explored_word_bit, the reserved trio, navimap's extended
    locid space, the flags reservation).
"""
from __future__ import annotations

import pytest

from ff9mapkit import flags
from ff9mapkit.world import navimap
from ff9mapkit.world.entrance import (EXTENDED_EXPLORED_RANGES, RESERVED_VIRGIN_CASES,
                                      VIRGIN_CASE_MAX, explored_word_bit, f0xb_arm_section,
                                      load_world_dispatchers)


def _run_chain(chain, b39, words):
    """Interpret the arm-chain BYTES exactly (never a re-model of them)."""
    pc = 0
    while pc < len(chain):
        if chain[pc] == 0x05 and chain[pc + 1] == 0xD5 and chain[pc + 2] == 0x27:   # test B39 <= k
            assert chain[pc + 3] == 0x7D and chain[pc + 6] == 0x1A and chain[pc + 7] == 0x7F
            k = chain[pc + 4] | (chain[pc + 5] << 8)
            cond = b39 <= k
            pc += 8
            assert chain[pc] == 0x02
            dist = chain[pc + 1] | (chain[pc + 2] << 8)
            pc += 3
            if not cond:
                pc += dist
            continue
        if chain[pc] == 0x05 and chain[pc + 1] == 0xD5:                             # the assign
            var = chain[pc + 2]; i = pc + 3
            if chain[i] == 0xDC:
                word = chain[i + 1]; i += 2
            elif chain[i] == 0xFC:
                word = chain[i + 1] | (chain[i + 2] << 8); i += 3
            else:
                raise AssertionError(f"bad var token at {i}")
            assert chain[i:i + 3] == bytes([0xD5, 0x27, 0x7D])
            base = chain[i + 3] | (chain[i + 4] << 8)
            assert chain[i + 5:i + 13] == bytes([0x15, 0x17, 0x7D, 0x01, 0x00, 0x24, 0x2C, 0x7F])
            val = (words.get(word, 0) >> ((b39 - base) & 31)) & 1                    # C# >> masks count
            return (var, val, word, (b39 - base) & 31)
        raise AssertionError(f"unexpected op {chain[pc]:#x} at {pc}")
    raise AssertionError("fell off the chain")


WORDS = {92: 0xAAAA, 94: 0x5555, 96: 0xF0F0, 98: 0x0F0F,
         2006: 0x1234, 2008: 0x4321, 2010: 0x9999, 2012: 0x6666, 2014: 0xCCCC, 2016: 0x3333}


def test_stock_arm_section_is_the_oracle():
    """The composed stock section must equal the LIVE dispatcher bytes -- both var forms."""
    from ff9mapkit.eb.model import EbScript
    disp = load_world_dispatchers()
    for name, var_b in (("evt_world_world00", 0x26), ("evt_world_world02", 0x23)):
        d = disp[name]
        s = EbScript(d)
        fn = s.entry(1).func_by_tag(11)
        assert d[fn.abs_start:fn.abs_start + 114] == f0xb_arm_section(var_b, extended=False), name


def test_extended_chain_semantics_all_256_cases():
    stock = f0xb_arm_section(0x26, extended=False)
    ext = f0xb_arm_section(0x26, extended=True)
    for b39 in range(256):
        rs, re_ = _run_chain(stock, b39, WORDS), _run_chain(ext, b39, WORDS)
        band = next(((lo, hi, w) for lo, hi, w in EXTENDED_EXPLORED_RANGES if lo <= b39 <= hi), None)
        if band:
            lo, _hi, word = band
            assert re_ == (0x26, (WORDS[word] >> (b39 - lo)) & 1, word, b39 - lo), b39
        else:
            assert rs == re_, f"stock-domain drift at case {b39}"           # 1-64, 91-93, 156-255


def test_extended_chain_var_form_follows_the_dispatcher():
    """WORLD02's chain must write Byte[35] (0x23) everywhere the others write Byte[38]."""
    a, b = f0xb_arm_section(0x26, extended=True), f0xb_arm_section(0x23, extended=True)
    assert len(a) == len(b)
    diffs = {(x, y) for x, y in zip(a, b) if x != y}
    assert diffs == {(0x26, 0x23)}


def test_explored_word_bit_extended_ranges():
    assert explored_word_bit(64) == (98, 15)                 # the stock band's last case
    assert explored_word_bit(65) == (2006, 0)                # the extended band's first
    assert explored_word_bit(90) == (2008, 9)
    assert explored_word_bit(94) == (2010, 0)
    assert explored_word_bit(155) == (2016, 13)
    for c in RESERVED_VIRGIN_CASES:                          # the vehicle trio refuses
        with pytest.raises(ValueError):
            explored_word_bit(c)
    with pytest.raises(ValueError):
        explored_word_bit(VIRGIN_CASE_MAX + 1)               # Byte[24] would wrap


def test_explored_words_live_in_the_reserved_flag_region():
    """Every extended explored bit sits inside flags' nameplate_explored_words reservation --
    and the [[flag]] validator refuses user flags there (the enforcement, not just the wish)."""
    for lo, hi, word in EXTENDED_EXPLORED_RANGES:
        for case in (lo, hi):
            w, bit = explored_word_bit(case)
            abs_bit = w * 8 + bit
            assert flags.NAMEPLATE_EXPLORED_FLOOR <= abs_bit < flags.QTE_SCRATCH_FLOOR
            assert flags.is_reserved(abs_bit)
            assert not flags.is_safe_custom(abs_bit)
    with pytest.raises(ValueError, match="nameplate_explored_words"):
        flags.collect_flag_defs({"flag": [{"name": "oops", "index": flags.NAMEPLATE_EXPLORED_FLOOR}]})


def test_navimap_extended_locids():
    assert navimap.resolve_renames([{"locid": 154, "to": "Far Light"}]) == {154: "Far Light"}
    with pytest.raises(ValueError):
        navimap.resolve_renames([{"locid": 155, "to": "x"}])             # past the case-155 cap
    for loc in (90, 91, 92):                                             # the vehicle trio's labels
        with pytest.raises(ValueError):
            navimap.resolve_renames([{"locid": loc, "to": "x"}])
    # the dot-table path (names / reveal_markers) stays capped at the real navi table
    with pytest.raises(ValueError):
        navimap.resolve_markers([100])
