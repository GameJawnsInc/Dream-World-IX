"""The NATIVE-FLOW nameplate SURGERY: repoint a DEAD overworld AREA-switch case to a custom-name entrance.

The surgery makes the whole overworld entrance run the game's REAL native flow (so the approach nameplate can
show a genuine CUSTOM location name) by:
  * writing the STOCK trigger (``Byte[39]=<case>`` + ``RunScriptAsync``) into object-0, and
  * repointing a dead high AREA-switch case (default 53) to ``[set explored bit] + Field(<custom id>)`` in every
    free-roam dispatcher, in every language -- a length-preserving 2-byte reloffset patch + an appended handler.

The offline pieces (the handler bytes, the explored word/bit, the name-text splice) are game-free; the whole-
surgery round-trip + correctness is gated on the FF9 install (it needs the real dispatcher bytes).
"""
from __future__ import annotations

import pytest

from ff9mapkit import dialogue
from ff9mapkit.world import entrance as EN, navimap


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


needs_game = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")

CASE = 53
FIELD = 6500
# The PIN's proven handler: gEventGlobal[98] |= (1<<4) [read-OR-write, opDC(98)=dc 62, 0x26=B_OR], then Field(6500).
EXPLORED_EXPR = bytes([0x05, 0xDC, 98, 0xDC, 98, 0x7D, 0x10, 0x00, 0x26, 0x2C, 0x7F])
FIELD_6500 = bytes([0x2B, 0x00, 0x64, 0x19])          # Field(6500): 6500 == 0x1964 -> 64 19 LE


# --------------------------------------------------------------------------- offline: the handler + explored bit

def test_explored_word_bit_ranges():
    assert EN.explored_word_bit(53) == (98, 4)         # 49-64 -> word 98, bit case-49
    assert EN.explored_word_bit(1) == (92, 0)          # 1-16  -> word 92
    assert EN.explored_word_bit(17) == (94, 0)         # 17-32 -> word 94
    assert EN.explored_word_bit(33) == (96, 0)         # 33-48 -> word 96
    assert EN.explored_word_bit(64) == (98, 15)
    assert EN.explored_word_bit(65) == (2006, 0)       # THE EXTENDED BAND (test_nameplate_band.py)
    for bad in (0, -1, 91, 156):
        with pytest.raises(ValueError):
            EN.explored_word_bit(bad)


def test_explored_bit_is_the_navi_marker_bit():
    # the explored bit that shows the nameplate NAME is the SAME save flag as navi marker discovery for locId case-1
    word, bit = EN.explored_word_bit(CASE)
    assert word * 8 + bit == navimap.marker_bit(CASE - 1) == 788


def test_explored_set_expr_is_the_pin_bytes():
    assert EN.explored_set_expr(CASE) == EXPLORED_EXPR
    # bit 6 variant (case 55) matches the task's other worked example: 1<<6 = 0x40
    assert EN.explored_set_expr(55) == bytes([0x05, 0xDC, 98, 0xDC, 98, 0x7D, 0x40, 0x00, 0x26, 0x2C, 0x7F])


def test_nameplate_handler_shape():
    h = EN.nameplate_handler(FIELD, CASE)
    assert h == EXPLORED_EXPR + FIELD_6500             # [set explored bit] + Field(6500); Field terminates (no RET)
    assert h.hex() == "05dc62dc627d1000262c7f2b006419"
    with pytest.raises(ValueError):
        EN.nameplate_handler(0x8000, CASE)             # past the engine Int16 range


def test_name_text_splice_sets_the_case_slot():
    # a block-68-shaped .mes (txid-0 = [TBLE=...]<64 names>): renaming locId 52 must land at split[53] (= the case)
    synth = ("[STRT=0,0][TBLE=1,2,3,]" + "\n".join("slot%d" % i for i in range(64)) + "[ENDN]"
             "[STRT=1,0]unrelated[ENDN]")
    out = navimap.apply_marker_renames(synth, {CASE - 1: "Waystation"})
    t0 = dialogue.parse_mes(out)[0].text
    split = t0[t0.find("]") + 1:].split("\n")
    assert split[CASE] == "Waystation"                 # nameplate reads GetTableText(0)[Byte[24]] with Byte[24]=case
    assert split[CASE - 1] == "slot%d" % (CASE - 1)    # neighbour untouched (splice is surgical)
    assert dialogue.parse_mes(out)[1].text == "unrelated"


# --------------------------------------------------------------------------- offline: the generic switch helper

def test_repoint_switch_case_guards_a_synthetic_switch():
    # a hand-built .eb whose entry-1/tag-1 has a base-2 contiguous switch (cases 2,3; both DEAD -> default) is enough
    # to exercise the length-preserving reloffset patch + the live-case guard, install-free.
    from ff9mapkit.eb import edit as E
    from ff9mapkit.eb.model import EbScript
    import struct
    # func body: EXPR pushing selector, then 0x0B switch [count=2, base=2, default->arm0, case2->arm0, case3->arm0],
    # arm0 = a bare RETURN. Build with placeholder reloffsets then let decode confirm all three point to the default.
    switch = bytes([0x0B, 0x02]) + struct.pack("<H", 2)        # op, count, base=2
    # anchor = off+1; we want default + both cases to point at the RETURN right after the table. Fill after sizing.
    body_pre = bytes([0x05, 0x7A, 0x02, 0x7F])                 # EXPR{ B_SYSVAR(2) } -- a selector on the stack
    sw_off = len(body_pre)
    table = switch + struct.pack("<H", 0) * 3                  # default + 2 case reloffsets (patched below)
    ret_off = sw_off + len(table)                              # the shared RETURN sits right after the table
    anchor = sw_off + 1
    reloff = ret_off - anchor
    table = switch + struct.pack("<H", reloff) * 3
    func = body_pre + table + bytes([0x04])                    # ... + RETURN
    # assemble a 2-entry .eb: entry0 (Main_Init stub), entry1 carrying this func as tag 1
    eb = EbScript.from_bytes(_min_eb(entries={0: {0: bytes([0x04])}, 1: {1: func}}))
    handler = EXPLORED_EXPR + FIELD_6500
    out, info = E.repoint_switch_case(eb.to_bytes(), 1, 1, 2, handler, switch_base=2)
    assert EbScript.from_bytes(out).to_bytes() == out          # round-trip identity
    # case 2 now decodes to the appended handler
    from ff9mapkit.eb import disasm as D
    s = EbScript(out)
    f1 = s.entry(1).func_by_tag(1)
    si = next(D.decode_switch(i) for i in D.iter_code(s.data, f1.abs_start, f1.abs_end)
              if i.is_switch and D.decode_switch(i))
    e2 = next(e for e in si.edges if e.value == 2)
    assert out[e2.target:e2.target + len(handler)] == handler
    # repointing case 2 again is now a LIVE case -> raises. match= matters: "case not in the switch"
    # and "handler reloffset out of range" are ValueErrors from the same helper, so a bare raises()
    # here would go green on a parse failure that never reached the dead-case guard at all.
    with pytest.raises(ValueError, match="case 2 is LIVE"):
        E.repoint_switch_case(out, 1, 1, 2, handler, switch_base=2)


def _min_eb(entries: dict) -> bytes:
    """A minimal valid .eb carrying ``{entry_index: {func_tag: body}}`` -- header + name + entry table + packed
    entry bodies. Enough for the structural-edit helpers (magic, count byte, 8-byte slots, per-entry func table)."""
    from ff9mapkit.eb.model import ENTRY_TABLE_OFF, ENTRY_SLOT_SIZE, MAGIC
    import struct
    n = max(entries) + 1
    header = bytearray(ENTRY_TABLE_OFF)
    header[:2] = MAGIC
    header[3] = n
    table = bytearray(ENTRY_SLOT_SIZE * n)
    bodies = bytearray()
    for i in range(n):
        funcs = entries.get(i, {})
        if not funcs:
            continue
        items = list(funcs.items())
        etype = 0
        fc = len(items)
        code = bytearray()
        ftable = bytearray()
        fpos = fc * 4
        for tag, fb in items:
            ftable += struct.pack("<HH", tag, fpos)
            code += fb
            fpos += len(fb)
        entry_body = bytes([etype, fc]) + bytes(ftable) + bytes(code)
        off = n * ENTRY_SLOT_SIZE + len(bodies)        # relative to ENTRY_TABLE_OFF, PAST the entry table
        struct.pack_into("<HH", table, i * ENTRY_SLOT_SIZE, off, len(entry_body))
        bodies += entry_body
    return bytes(header) + bytes(table) + bytes(bodies)


# --------------------------------------------------------------------------- game-gated: the real 9x7 surgery

@needs_game
def test_reloff_pos_matches_the_live_world09_switch():
    """The reloffset byte position is computed (op+count header, then 2-byte operands), NOT the PIN prose formula.
    Live WORLD09 base-2 switch @4033: case-53 reloffset at byte 4141 (== off+6+2*(53-2)), value 784 == the default
    reloffset (so case 53 is DEAD)."""
    from ff9mapkit.eb import edit as E
    from ff9mapkit.eb.model import EbScript
    import struct
    b = EN.load_world_dispatchers()["evt_world_world09"]
    eb = EbScript(b)
    f, ins, si = E.find_switch(eb, 1, 1, switch_base=2)
    assert ins.off == 4033 and si.base == 2
    pos = E.switch_case_reloff_pos(ins, si, 53)
    assert pos == 4141 == ins.off + 6 + 2 * (53 - 2)
    default_reloff = next(e.target for e in si.edges if e.is_default) - (ins.off + 1)
    assert struct.unpack_from("<H", b, pos)[0] == default_reloff       # dead: the arm's reloffset == the default's


@needs_game
def test_surgery_roundtrips_on_all_dispatchers_and_langs():
    """Trigger (stock template, Byte[39]=53) + repoint (case 53 -> handler) on every free-roam dispatcher, in every
    language: byte-exact round-trip, the repointed case decodes to the handler, and the op is idempotent."""
    from ff9mapkit.eb import edit as E, disasm as D
    from ff9mapkit.eb.model import EbScript
    alld = EN.load_all_dispatchers()
    us = {n: L["us"] for n, L in alld.items() if "us" in L}
    handler = EN.nameplate_handler(FIELD, CASE)
    trigger = EN.entrance_func_body(CASE, dispatchers=us)
    tag = EN.pack_cell_tag(7, 36, 1)
    targets = sorted(n for n, L in alld.items()
                     if "us" in L and (cs := EN.dispatcher_cases(L["us"])) is not None and CASE in cs)
    assert len(targets) == 9                                             # every free-roam dispatcher carries case 53
    combos = 0
    for name in targets:
        for lang in EN.LANGS:
            base = alld[name].get(lang, alld[name]["us"])
            ex = EbScript.from_bytes(base).entry(0).func_by_tag(tag)
            out = E.add_function(base, 0, tag, trigger) if ex is None \
                else E.replace_function_body(base, 0, tag, trigger)
            out = EN._repoint_dead_case(out, CASE, handler)
            # (a) round-trip identity holds after BOTH edits
            assert EbScript.from_bytes(out).to_bytes() == out, (name, lang)
            s = EbScript(out)
            # (b) the trigger is the stock template with Byte[39] = 53
            tf = s.entry(0).func_by_tag(tag)
            tb = out[tf.abs_start:tf.abs_end]
            assert tb == trigger and EN.byte39_value(tb) == CASE, (name, lang)
            # (c) the repointed case decodes to exactly the handler = [explored-bit set] + Field(6500)
            f1 = s.entry(1).func_by_tag(1)
            si = next(D.decode_switch(i) for i in D.iter_code(s.data, f1.abs_start, f1.abs_end)
                      if i.is_switch and D.decode_switch(i) and D.decode_switch(i).base == 2)
            e = next(x for x in si.edges if x.value == CASE)
            assert out[e.target:e.target + len(handler)] == handler, (name, lang)
            # (d) idempotent: a second surgery pass is a no-op
            assert EN._repoint_dead_case(out, CASE, handler) == out, (name, lang)
            combos += 1
    assert combos == 63                                                 # 9 dispatchers x 7 languages


@needs_game
def test_dead_case_guard_raises_on_a_mapped_case():
    """Repointing a LIVE case (17 -> a real Ice-Cavern-band Field) must refuse, so the surgery can never clobber a
    real entrance."""
    b = EN.load_world_dispatchers()["evt_world_world09"]
    handler = EN.nameplate_handler(FIELD, CASE)
    # against REAL dispatcher bytes, so the sibling failures ("has no case 17", a template-shape
    # refusal) are live possibilities -- match= is what makes this the DEAD-CASE guard's test.
    with pytest.raises(ValueError, match="case 17 is already mapped"):
        EN._repoint_dead_case(b, 17, handler)
    # the generic helper guards it too
    from ff9mapkit.eb import edit as E
    with pytest.raises(ValueError, match="case 17 is LIVE"):
        E.repoint_switch_case(b, 1, 1, 17, handler, switch_base=2)


@needs_game
def test_author_entrance_surgery_summary():
    """The one-shot author (dry-run, trigger-only) reports the surgery plan: 9 dispatchers, case 53 -> Field(6500),
    name 'Waystation' at locId 52, explored word 98 bit 4 (== gEventGlobal bit 788).

    The mod folder is a deliberately-ABSENT name: author_entrance stacks on ``<mod_folder>``'s deployed ``.eb``
    when one exists, and the SHARED install's real folders may legitimately carry case 53 already (a shipped
    surgery entrance maps it to ITS OWN handler), which would trip the -- correct, load-bearing -- already-mapped
    guard. An absent folder makes every base fall back to pristine p0data bytes, where case 53 is dead (stock)."""
    from ff9mapkit import config
    mod = "FF9MK-PYTEST-NO-SUCH-MOD"
    assert not (config.find_game_path(None) / mod).exists(), \
        f"{mod!r} exists in the install -- this test needs an absent mod folder so the bases stay pristine"
    info = EN.author_entrance(cell=(7, 36), mod_folder=mod, direct_field=FIELD,
                              nameplate_name="Waystation", trigger_only=True, dry_run=True)
    assert info["surgery"] is True
    assert info["case"] == CASE and info["field"] == FIELD
    assert info["name_locid"] == CASE - 1 == 52
    assert (info["explored_word"], info["explored_bit"]) == (98, 4)
    assert info["explored_bit_index"] == 788 == navimap.marker_bit(52)
    assert info["name_rename"] == {"locid": 52, "to": "Waystation", "text_block": 68}
    # pristine bases -> the surgery is a FRESH plan in every free-roam dispatcher (nothing already-present to skip)
    assert len(info["dispatchers_written"]) == 9 and info["dispatchers_skipped"] == []


@needs_game
def test_author_entrance_surgery_rejects_bad_combinations():
    # each combination has its OWN refusal; without match= an unrelated early raise (a missing
    # dispatcher, an OBJ path check) would satisfy all five and the combination guards could be gone.
    for kw, why in (({"field": 300}, "drop field/case"),
                    ({"case": 4}, "drop field/case"),
                    ({"prompt": True}, "drop prompt/nameplate"),
                    ({"nameplate": True}, "drop prompt/nameplate")):
        with pytest.raises(ValueError, match=why):
            EN.author_entrance(cell=(7, 36), mod_folder="X", direct_field=FIELD, nameplate_name="W",
                               trigger_only=True, dry_run=True, **kw)
    # nameplate_name needs a custom destination
    with pytest.raises(ValueError, match="nameplate_name requires direct_field"):
        EN.author_entrance(cell=(7, 36), mod_folder="X", nameplate_name="W", trigger_only=True, dry_run=True)
