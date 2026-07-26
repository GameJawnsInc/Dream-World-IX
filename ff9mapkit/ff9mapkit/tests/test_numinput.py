"""``[[numeric_input]]`` -- the Treno-stepper substrate (:mod:`ff9mapkit.content.numinput`).

Golden provenance: field 909 ``Code10_31`` + its ``.mes`` entries 203-206 (the 3-digit
x100 bid stepper nine shipping fields carry byte-for-byte -- studies/minigame-ui/SURVEY.md
substrate #2). The text tests below pin the kit's cursor lines to the STOCK bytes."""
from __future__ import annotations

import pytest

from ff9mapkit import build as BLD
from ff9mapkit.content import numinput as NI
from ff9mapkit.eb import disasm as D, opcodes
from ff9mapkit.eb.model import EbScript

BID_RAW = {"name": "bid", "result": 2000, "digits": 3, "multiplier": 100,
           "gil_ceiling": True, "label": "Bid", "suffix": " Gil",
           "echo": "You bid [NUMB=0] Gil.", "start": 1}
TX = {"value": 500, "cur0": 501, "cur1": 502, "cur2": 503, "help": 504, "echo": 505}


def _spec(**over):
    return NI.from_raw({**BID_RAW, **over}, 0)


def _verify_body(body: bytes) -> int:
    """The behavior suite's structural invariant: walk the stream, every jump lands on
    an instruction start (or one-past-the-end)."""
    starts, count = set(), 0
    for ins in D.iter_code(body, 0, len(body)):
        starts.add(ins.off)
        count += 1
        assert ins.end <= len(body)
    ends = starts | {len(body)}
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op in (0x01, 0x02, 0x03):
            t = D.jump_target(ins)
            assert t is None or t in ends, f"jump at {ins.off} -> {t} misses a boundary"
    return count


# ------------------------------------------------------------------------ the .mes texts
def test_cursor_texts_are_stock_bytes():
    """The kit's default-position cursor overlays reproduce field 909's entries 204-206
    BYTE-FOR-BYTE (MPOS run 33/40/47, the Pink pair, the WDTH shape) -- the strongest
    verbatim claim the emitter can make offline."""
    texts = dict((p, t) for p, t, _ in NI.mes_texts(_spec()))
    assert texts["cur2"] == ("[MPOS=33,80][WDTH=0,0,64,5,-1][NFOC][B880E0][HSHD][IMME]"
                            "[NUMB=5][TIME=-1]")                       # stock 204
    assert texts["cur1"] == ("[MPOS=40,80][WDTH=0,0,64,6,-1][NFOC][B880E0][HSHD][IMME]"
                            "[NUMB=6][TIME=-1]")                       # stock 205
    assert texts["cur0"] == ("[MPOS=47,80][WDTH=0,0,64,7,-1][NFOC][B880E0][HSHD][IMME]"
                            "[NUMB=7][TIME=-1]")                       # stock 206


def test_value_text_shape():
    parts = {p: (t, s) for p, t, s in NI.mes_texts(_spec())}
    vt, strt = parts["value"]
    assert vt == ("[MPOS=33,80][WDTH=0,0,64,5,64,6,64,7,-1][NFOC][IMME]"
                  "[NUMB=5][NUMB=6][NUMB=7]00 Gil[TIME=-1]")
    assert strt == (0, 1)                                # stock's frameless [STRT=0,1]
    ht, hstrt = parts["help"]
    assert ht.startswith("[MPOS=8,96][NANI][NFOC][IMME]Bid\n[DBTN=UP]")
    assert hstrt == (NI.HELP_STRT_WIDTH, 5)              # label line + 4 button lines
    et, estrt = parts["echo"]
    assert et == "[IMME]You bid [NUMB=0] Gil." and estrt is None


def test_mes_texts_no_multiplier_no_help():
    parts = {p: (t, s) for p, t, s in
             NI.mes_texts(_spec(multiplier=1, digits=2, suffix="", help=False,
                                echo=None, label="", max=20))}
    assert parts["value"][0] == ("[MPOS=33,80][WDTH=0,0,64,6,64,7,-1][NFOC][IMME]"
                                 "[NUMB=6][NUMB=7][TIME=-1]")          # no zeros, no suffix
    assert "help" not in parts and "echo" not in parts
    assert set(parts) == {"value", "cur0", "cur1"}


# ------------------------------------------------------------------------ the .eb body
def test_body_structure_and_census():
    spec = _spec()
    body = NI.stepper_body(spec, TX)
    n = _verify_body(body)
    assert n > 80                                        # a real loop, not a stub
    names = [ins.name for ins in D.iter_code(body, 0, len(body))]
    d = spec.digits
    # publish runs twice (seed + per-tick) x d digits, + 1 echo slot-0 load
    assert names.count("SetTextVariable") == 2 * d + 1
    # opens: value + help + initial cursor + (d-1) right-swaps + (d-1) left-swaps
    assert names.count("WindowAsync") == 3 + 2 * (d - 1)
    # closes: the swaps (2*(d-1)) + the exit sweep (d cursors + value + help)
    assert names.count("CloseWindow") == 2 * (d - 1) + d + 2
    assert names.count("WindowSync") == 1                # the echo ack


def test_body_key_masks():
    body = NI.stepper_body(_spec(), TX)
    exprs = []
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op == 0x05:
            exprs.append(D.pretty_expr(body, ins.off + 1)[0])
    keyon = [e for e in exprs if "B_KEYON" in e]
    keyheld = [e for e in exprs if "B_KEY " in e or e.rstrip().endswith("B_KEY")]
    # edges: exit-mask, right, left, down-step, up-step, the cancel re-test
    assert len(keyon) == 6
    # held: the two ramp reads (up / down)
    assert len(keyheld) == 2
    # the exit mask is Confirm|Cancel
    assert any(str(NI.KEY_CONFIRM | NI.KEY_CANCEL) in e or "196608" in e for e in keyon)
    # the gil ceiling reads B_SYSVAR[6] (GetGil)
    assert any("B_SYSVAR" in e and "B_DIV" in e for e in exprs)


def test_body_no_gil_ceiling_drops_sysvar():
    body = NI.stepper_body(_spec(gil_ceiling=False), TX)
    _verify_body(body)
    for ins in D.iter_code(body, 0, len(body)):
        if ins.op == 0x05:
            assert "B_SYSVAR" not in D.pretty_expr(body, ins.off + 1)[0]


def test_body_deterministic():
    assert NI.stepper_body(_spec(), TX) == NI.stepper_body(_spec(), TX)


def test_entry_bytes_two_funcs():
    eb = NI.entry_bytes(_spec(), TX)
    assert eb[0] == 0x00 and eb[1] == 0x02               # type 0, two functions
    import struct
    t0, f0, t3, f3 = struct.unpack_from("<HHHH", eb, 2)
    assert (t0, t3) == (0, NI.INPUT_TAG)
    assert eb[2 + f0:2 + f3] == bytes(opcodes.RETURN)    # tag 0 = a bare return


def test_call_bytes():
    assert NI.call_bytes(12) == opcodes.run_script_sync(NI.DISPATCH_LEVEL, 12, NI.INPUT_TAG)


# ------------------------------------------------------------------------ validation
@pytest.mark.parametrize("over,frag", [
    ({"digits": 5}, "digits"),
    ({"digits": 0}, "digits"),
    ({"multiplier": 30}, "multiplier"),
    ({"max": 1000}, "max"),
    ({"start": 998, "max": 20}, "start"),
    ({"result": 2041}, "result"),
    ({"result": None}, "result"),
    ({"window": 4}, "window"),                            # 4 - 3 digits < 2
    ({"label": "a\nb"}, "label"),
    ({"pos": [400, 80]}, "pos"),
    ({"bogus": 1}, "unknown"),
])
def test_from_raw_rejects(over, frag):
    with pytest.raises(NI.NumericInputError) as ei:
        _spec(**over)
    assert frag in str(ei.value)


# ------------------------------------------------------------------------ the full build
_TOML = (
    '[field]\nid = 30001\nname = "NUM"\narea = 11\n'
    "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    '\n[[npc]]\nname = "broker"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Well?"\n'
    '\n[[numeric_input]]\nname = "bid"\nresult = 2000\ndigits = 3\nmultiplier = 100\n'
    'gil_ceiling = true\nlabel = "Bid"\nsuffix = " Gil"\necho = "You bid [NUMB=0] Gil."\n'
    '\n[[choice]]\nnpc = "broker"\nprompt = "Place a bid?"\n'
    'options = [ { text = "Place a bid", input = "bid" }, { text = "Never mind" } ]\n'
)


def _build(tmp_path, toml=_TOML):
    f = tmp_path / "num.field.toml"
    f.write_text(toml, encoding="utf-8")
    p = BLD.FieldProject.load(f)
    assert BLD.validate(p) == []
    (mes, txids, ev, cs, ch, oe, ate, chest, gw, co, sp, bh, ni) = BLD.collect_text(p)
    eb = BLD.build_script(BLD.FieldProject.load(f), "us", txids, choice_txids=ch,
                          numinput_txids=ni)
    return mes, ni, eb


def test_full_build_seats_and_wires(tmp_path):
    mes, ni_txids, plain = _build(tmp_path)
    # every stepper window minted, tail-less, on the shared block
    assert {p for (_i, p) in ni_txids} == {"value", "cur0", "cur1", "cur2", "help", "echo"}
    assert "[B880E0]" in mes and "[MPOS=33,80]" in mes
    for line in mes.splitlines():
        if "[B880E0]" in line or "[MPOS=33,80]" in line:
            assert "[TAIL" not in line                   # pinned windows carry no tail
    eb = EbScript.from_bytes(plain)
    # exactly one seated input entry: tag 0 == bare RETURN, tag 3 == the stepper
    input_slots = []
    for i in range(1, eb.entry_count):
        e = eb.entry(i)
        if e.size <= 0 or e.func_by_tag(NI.INPUT_TAG) is None or e.func_by_tag(0) is None:
            continue
        fn0 = e.func_by_tag(0)
        if plain[fn0.abs_start:fn0.abs_end] == bytes(opcodes.RETURN):
            input_slots.append(i)
    assert len(input_slots) == 1
    slot = input_slots[0]
    # the choice option dispatches it synchronously
    assert NI.call_bytes(slot) in plain
    # the entry is armed from entry 0 (init_code 0x07)
    armed = set()
    for fn in eb.entry(0).funcs:
        for ins in D.iter_code(plain, fn.abs_start, fn.abs_end):
            if ins.op == 0x07:
                armed.add(int(ins.imm(0)))
    assert slot in armed
    # the stepper body inside the built field verifies structurally
    fn3 = eb.entry(slot).func_by_tag(NI.INPUT_TAG)
    _verify_body(plain[fn3.abs_start:fn3.abs_end])
    # determinism
    assert _build(tmp_path)[2] == plain


def test_build_without_input_has_no_stepper(tmp_path):
    toml = (
        '[field]\nid = 30001\nname = "NUM"\narea = 11\n'
        "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
        '\n[[npc]]\nname = "broker"\npreset = "vivi"\npos = [0, -300]\ndialogue = "Well?"\n'
    )
    mes, ni_txids, plain = _build(tmp_path, toml)
    assert ni_txids == {}
    assert b"".join([bytes([0x05, 0x7E])]) not in b""    # (shape guard only)
    assert "[B880E0]" not in mes


def test_validate_rejects_unknown_input_name(tmp_path):
    bad = _TOML.replace('input = "bid"', 'input = "nope"')
    f = tmp_path / "bad.field.toml"
    f.write_text(bad, encoding="utf-8")
    probs = BLD.validate(BLD.FieldProject.load(f))
    assert any("input" in p and "nope" in p for p in probs)


def test_validate_rejects_hud_collision(tmp_path):
    toml = _TOML + (
        '\n[behavior]\nwarmup = 30\n'
        '\n[[behavior.unit]]\nnpc = "broker"\nbranch = [{ do = { hold = [0, -300] } }]\n'
        '\n[[behavior.hud]]\ntext = "G [NUMB=0]"\nvalues = ["gil"]\n'
    )
    f = tmp_path / "hud.field.toml"
    f.write_text(toml, encoding="utf-8")
    probs = BLD.validate(BLD.FieldProject.load(f))
    assert any("gMesValue" in p for p in probs)
