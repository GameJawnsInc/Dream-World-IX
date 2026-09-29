"""THE AMBIENT CLEAR (``content/ambient.py``) -- every synthesized Main_Init restores stock's report/clear tail,
minus the window, at stock's position, and nothing else moves.

The claims are pinned on BUILD OUTPUT, never on bytes the test made itself: nine real builds (the seven bundled
examples that build from templates alone, a gen-hub hub, an ``ff9mapkit new`` scaffold), each run through
``tests/_ebengine`` (what Main_Init leaves in ``Byte[13]``/``Byte[14]``) and ``eb/cfg.FuncFlow`` (no path skips
the tail). The TAIL constant itself is pinned against stock's own bytes (the blank's prologue, and field 1357's
tail read from the install).

Twenty-five tests, and none of them may skip on a provisioned machine (AMB-COUNT). The module never reads the blank
at import time: the top-level conftest would ignore-collect it on an unprovisioned checkout (``_MODULE_LEVEL_IO``),
and a silently uncollected file is a check that cannot fail.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from ff9mapkit import build as B
from ff9mapkit import data, hub, pack, provision
from ff9mapkit.config import LANGS
from ff9mapkit.content import ambient
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.cfg import FuncFlow
from ff9mapkit.eb.disasm import iter_code
from ff9mapkit.eb.edit import insert_in_function

from ._ebengine import Engine

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
FIX = Path(__file__).parent / "fixtures"

# The seven bundled examples that build from templates alone (their tomls name no cache, .bgx or fbx).
EXAMPLE_TOMLS = {
    "vivi-hut": "vivi-hut/hut_int.field.toml",
    "SHOWCASE": "SHOWCASE/showcase.field.toml",
    "capstone": "capstone/capstone.field.toml",
    "items-equipment": "items-equipment/items_equipment.field.toml",
    "scroll-demo": "scroll-demo/scroll_demo.field.toml",
    "siege": "siege/siege.field.toml",
    "thirteenth-character": "thirteenth-character/iviv.field.toml",
}
BUILDS = (*EXAMPLE_TOMLS, "gen-hub", "new")

HUT_PRE = "2c6f18b9fae1d7c9cdf79acba2d9587d2a01159464a3639c2a64001c34bdba1d"    # the hut golden before the fix
HUT_POST = "55d9b7b8b74bff743aa0d70477e1eceac769c9de0cc238752006545645fbfe16"   # PRE-REGISTERED (F5c design)
HUT_TAIL_REL = 246                  # the blank's `set MAP159 = 1`, Main_Init-relative (after the two Wait(2))

I16_9_NONE = bytes([0x05, 0xD8, 0x09, 0x7D, 0xFF, 0xFF, 0x2C, 0x7F])    # the prologue's Int16[9] := 65535
LET1_14 = bytes([0x05, 0xD4, 0x0E, 0x7D, 0x01, 0x00, 0x2C, 0x7F])       # the prologue's last store, Byte[14] := 1
MAIN_READY = bytes([0x05, 0xC5, 159, 0x7D, 0x01, 0x00, 0x2C, 0x7F])     # set MAP159 = 1
ARRIVALS = (0, 1, 2, 3, 9)


def _game_ready() -> bool:
    """True if the FF9 install + UnityPy are readable (gates the two tests that read stock fields)."""
    try:
        from ff9mapkit.extract import EventBundle
        EventBundle()
        return True
    except Exception:
        return False


def _main(b: bytes):
    """``(func, body)`` of entry 0 / function tag 0 (Main_Init)."""
    f = EbScript.from_bytes(b).entry(0).func_by_tag(0)
    return f, b[f.abs_start:f.abs_end]


def _stmts(b: bytes) -> list:
    """Main_Init's decoded instructions: ``[(Main_Init-relative offset, instruction bytes)]``."""
    eb = EbScript.from_bytes(b)
    f = eb.entry(0).func_by_tag(0)
    return [(i.off - f.abs_start, bytes(b[i.off:i.end])) for i in eb.instrs(f)]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------------------------------------ the builds
def _built_ebs(out: Path) -> dict:
    """``{lang: the one field .eb}`` of a single-field build."""
    got = {}
    for lang in LANGS:
        ebs = sorted(out.rglob(f"eventbinary/field/{lang}/*.eb.bytes"))
        assert len(ebs) == 1, (out, lang, ebs)
        got[lang] = ebs[0].read_bytes()
    return got


def _build_toml(toml: Path, out: Path) -> dict:
    B.build_mod([B.FieldProject.load(toml)], out, mod_name="FF9CustomMap")
    return _built_ebs(out)


def _hub_toml(d: Path) -> Path:
    """A gen-hub hub (rendered like test_hub_gen's), its ``[camera] borrow`` swapped for the ``new`` scaffold's
    declarative camera -- no game-derived camera file; ``entry_settle`` kept."""
    spec = hub.HubSpec(name="AMB_HUB", id=30997, area=21, borrow_bg="GRGR_MAP420_GR_CEN_0",
                       camera="camera_hub.bgx", text_block=None, player_spawn=[404, 127], narrator_pos=[480, 127],
                       journeys=[hub.Journey("j1", "Journey One", 4501, 2600)])
    text, n = re.subn(r'(?m)^borrow = ".*$',
                      "pitch = 48.0\ndistance = 4500\nfov = 42.2\nframe = { back = 205, front = 432 }",
                      hub.render_hub_field_toml(spec))
    assert n == 1, "the rendered hub no longer carries one [camera] borrow line"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "hub.field.toml"
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def _new_toml(d: Path) -> Path:
    """An ``ff9mapkit new`` scaffold, as the CLI makes it (placeholder art, template camera + quad)."""
    proj = pack.new_project("AMB_NEW", d, field_id=30998, area=11)
    return proj / "amb_new.field.toml"


def _build(key: str, d: Path) -> dict:
    if key in EXAMPLE_TOMLS:
        return _build_toml(EXAMPLES / EXAMPLE_TOMLS[key], d / "out")
    if key == "gen-hub":
        return _build_toml(_hub_toml(d / "src"), d / "out")
    if key == "new":
        return _build_toml(_new_toml(d / "src"), d / "out")
    raise KeyError(key)


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    """``built(key) -> {lang: .eb}`` -- each of the nine builds made once per session (per worker), into tmp."""
    cache: dict = {}

    def get(key: str) -> dict:
        if key not in cache:
            cache[key] = _build(key, tmp_path_factory.mktemp(f"amb_{re.sub(r'[^A-Za-z0-9]', '_', key)}"))
        return cache[key]
    return get


# ------------------------------------------------------------------------------------------------ T-AMB-1
def _exits(body: bytes, n: int) -> dict:
    """``{arriving Byte[n]: what Main_Init leaves}``, running the span from the prologue's Int16[9] store to the
    TAIL's end (to the prologue's end when the TAIL is absent, so an unfixed build shows its 9s)."""
    start = body.index(I16_9_NONE)
    t = body.find(ambient.TAIL)
    end = t + len(ambient.TAIL) if t >= 0 else body.index(LET1_14) + len(LET1_14)
    span = body[start:end]
    out = {}
    for v in ARRIVALS:
        eng = Engine()
        eng.scalars[f"Global.Byte[{n}]"] = v
        eng.run(span)
        out[v] = eng.scalars.get(f"Global.Byte[{n}]")
    return out


@pytest.mark.parametrize("key", BUILDS)
def test_amb1_every_exit_clears(built, key):
    """T-AMB-1: whatever Byte[13]/Byte[14] arrive with (0/1/2/3/9), the synthesized Main_Init leaves 0 -- all 7
    languages. Unfixed, an arriving 2 or 9 leaves 9. (Blind to windows: the Engine no-ops them -- T-AMB-2 (iii).)
    The slots are the literal pair, never ``ambient.SLOTS``: a module that dropped one would shrink its own test."""
    for lang, b in built(key).items():
        _f, body = _main(b)
        for n in (13, 14):
            got = _exits(body, n)
            assert got == {v: 0 for v in ARRIVALS}, f"{key} {lang} Byte[{n}]: arriving -> left {got}"


# ------------------------------------------------------------------------------------------------ T-AMB-2
def _hits(b: bytes, blk) -> list:
    """The RET / Field / `set MAP159 = 1` instructions of a CFG block (off, what)."""
    out = []
    for ins in blk.instrs:
        if ins.op == 0x04:
            out.append((ins.off, "RET"))
        elif ins.op == 0x2B:
            out.append((ins.off, "Field"))
        elif b[ins.off:ins.end] == MAIN_READY:
            out.append((ins.off, "MAP159"))
    return out


@pytest.mark.parametrize("key", BUILDS)
def test_amb2_stock_position_and_shape(built, key):
    """T-AMB-2: the TAIL sits where stock's tail sits, has stock's shape minus the window, and no path skips it."""
    for lang, b in built(key).items():
        f, body = _main(b)
        # (i) exactly once in e0 t0, after the prologue's Byte[14] := 1
        assert body.count(ambient.TAIL) == 1, f"{key} {lang}: TAIL x{body.count(ambient.TAIL)} in Main_Init"
        t = body.index(ambient.TAIL)
        end1 = body.index(LET1_14) + len(LET1_14)
        assert t >= end1, f"{key} {lang}: TAIL at rel {t}, before the prologue ends ({end1})"
        # (ii) only nothing, or the entry_settle hold `2d 22 00 NN`, between it and `set MAP159 = 1`
        after = body[t + len(ambient.TAIL):]
        hold = after[:3] == b"\x2d\x22\x00" and after[4:12] == MAIN_READY
        assert after.startswith(MAIN_READY) or hold, \
            f"{key} {lang}: after the TAIL comes {after[:12].hex(' ')}, not [2d 22 00 NN] + set MAP159 = 1"
        # (ii') and no settle hold BEFORE it: the pass runs FIRST on the blank, so entry_settle's DisableMove ;
        # Wait(NN) lands after the TAIL -- stock's order. (Wired last, the TAIL would follow the hold, and (ii)
        # alone reads both orders as fine.)
        pre = [raw for off, raw in _stmts(b) if end1 <= off < t]
        held = [f"{x.hex(' ')} {y.hex(' ')}" for x, y in zip(pre, pre[1:]) if x == b"\x2d" and y[:1] == b"\x22"]
        assert not held, f"{key} {lang}: a settle hold ({held}) runs between the prologue and the TAIL"
        # (iii) the span decodes to 0x05 / 0x02 only: no window, no wait, no yield
        a0, a1 = f.abs_start + t, f.abs_start + t + len(ambient.TAIL)
        span = list(iter_code(b, a0, a1))
        assert span and span[-1].end == a1, f"{key} {lang}: the TAIL span does not decode to its own end"
        assert {i.op for i in span} <= {0x05, 0x02}, \
            f"{key} {lang}: TAIL span ops {sorted(hex(i.op) for i in span)}"
        # (iv) its block dominates every reachable block holding RET, Field or `set MAP159 = 1`, and nothing of
        # those three runs before it inside its own block
        ff = FuncFlow.build(b, f.abs_start, f.abs_end)
        tb = ff.block_at(a0)
        assert tb is not None, f"{key} {lang}: the TAIL does not start on an instruction"
        reach = ff._fwd_reach()[ff.entry]
        dom = set(ff.dominated_by(tb))
        bad = []
        for blk in ff.blocks:
            if not (reach >> blk.index) & 1:
                continue
            hits = _hits(b, blk)
            if blk.index == tb:
                bad += [(off - f.abs_start, w, "before the TAIL in its block") for off, w in hits if off < a0]
            elif hits and blk.index not in dom:
                bad += [(off - f.abs_start, w, "not dominated") for off, w in hits]
        assert not bad, f"{key} {lang}: a path skips the TAIL: {bad}"


# ------------------------------------------------------------------------------------------------ T-AMB-3
def test_amb3_tail_is_stocks_own_ops():
    """T-AMB-3: each 8-byte statement of the TAIL is one the blank's own prologue carries (exactly once, in stock's
    order: slot 13's test, its clear, slot 14's test, its clear), and each JMP_IFNOT skips exactly the clear."""
    tail = ambient.TAIL
    assert len(tail) == 38
    pieces = [tail[0:8], tail[11:19], tail[19:27], tail[30:38]]
    for skip, clear in ((tail[8:11], tail[11:19]), (tail[27:30], tail[30:38])):
        assert skip[0] == 0x02 and int.from_bytes(skip[1:3], "little") == len(clear) == 8, skip.hex(" ")
    for lang in LANGS:
        _f, body = _main(data.blank_field_bytes(lang))
        pos = []
        for p in pieces:
            assert body.count(p) == 1, f"{lang}: {p.hex(' ')} x{body.count(p)} in the blank's Main_Init"
            pos.append(body.index(p))
        assert pos == sorted(pos), f"{lang}: the TAIL's statements out of stock's order: {pos}"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_amb3_tail_is_1357_minus_the_window():
    """T-AMB-3: field 1357 (the blank's donor) src[464:532] -- the two tail blocks the provenance patch skips -- with
    each 15-byte window block cut and its JMP_IFNOT shortened by it, IS the TAIL, in all 7 languages. (Read from the
    install into memory; nothing is written.)"""
    from ff9mapkit import extract
    blank = provision.load_manifest()["blank"]
    for lang in LANGS:
        src = extract.extract_event_script(blank["source_fbg"], lang=lang)
        patch = json.loads((provision.PROVENANCE / blank["patch"].format(lang=lang)).read_text(encoding="utf-8"))
        assert provision.sha256(src) == patch["src_sha256"], f"{lang}: not the patch's source field"
        assert [["c", 435, 29], ["c", 532, 105]] == [op for op in patch["ops"] if op[:2] in (["c", 435], ["c", 532])]
        blk = src[464:532]
        cut = b""
        for k in (0, 34):
            test, jmp, window, clear = blk[k:k + 8], blk[k + 8:k + 11], blk[k + 11:k + 26], blk[k + 26:k + 34]
            assert jmp[0] == 0x02 and jmp[1] == len(window) + len(clear) and jmp[2] == 0, f"{lang}: {jmp.hex(' ')}"
            cut += test + bytes([jmp[0], jmp[1] - len(window), jmp[2]]) + clear
        assert cut == ambient.TAIL, f"{lang}: {cut.hex(' ')} != {ambient.TAIL.hex(' ')}"


# ------------------------------------------------------------------------------------------------ T-AMB-4
def test_amb4_idempotent():
    """T-AMB-4: the blank classifies 'missing'; once restored it classifies 'restored' and a second pass is a no-op."""
    for lang in LANGS:
        blank = data.blank_field_bytes(lang)
        assert ambient.classify(blank) == "missing", lang
        once = ambient.restore_clear(blank)
        assert len(once) == len(blank) + len(ambient.TAIL), lang
        assert ambient.classify(once) == "restored", lang
        assert ambient.restore_clear(once) == once, lang


def test_amb4_stock_tail_left_alone():
    """T-AMB-4: a stock script with its own tail (field 100, the alex100 fixture) comes back byte-identical."""
    stock = (FIX / "alex100-us.eb.bytes").read_bytes()
    assert ambient.classify(stock) == "stock-tail"
    assert ambient.restore_clear(stock) == stock


def test_amb4_template_drift_raises():
    """T-AMB-4: template drift fails loudly -- no prologue, two `:= 9` sites, no `set MAP159 = 1` anchor, or a
    stock tail on ONE slot only (``classify``'s 'stock-tail' needs both slots' second `== 9`, never any one)."""
    stock = (FIX / "alex100-us.eb.bytes").read_bytes()
    sf, stmts = ambient._main_init(stock)
    tests14 = [off for off, raw in stmts if raw == ambient._eq9(14)]
    assert len(tests14) == 2, tests14                        # the prologue's test, then stock's own tail's
    at = sf.abs_start + tests14[1] + 4                       # its literal 9 -> 8: slot 14 keeps no stock tail
    one_slot = stock[:at] + b"\x08" + stock[at + 1:]
    for fn in (ambient.classify, ambient.restore_clear):
        with pytest.raises(ValueError, match="template drift"):
            fn(one_slot)
    blank = data.blank_field_bytes("us")
    f, body = _main(blank)

    def with_body(new: bytes) -> bytes:
        assert len(new) == len(body)
        return blank[:f.abs_start] + new + blank[f.abs_end:]

    # no prologue: every Byte[13]/Byte[14] statement of Main_Init pointed at other bytes (same length, still parses)
    no_prologue = with_body(body.replace(b"\x05\xd4\x0d\x7d", b"\x05\xd4\x20\x7d")
                            .replace(b"\x05\xd4\x0e\x7d", b"\x05\xd4\x21\x7d"))
    # two `:= 9` sites: the 8-byte `Bit[191] := 0` turned into a second `Byte[13] := 9`
    bit191 = bytes([0x05, 0xC4, 0xBF, 0x7D, 0x00, 0x00, 0x2C, 0x7F])
    assert body.count(bit191) == 1
    two_nines = with_body(body.replace(bit191, ambient._let9(13)))
    # no anchor: `set MAP159 = 1` turned into `set MAP159 = 2`
    assert body.count(MAIN_READY) == 1
    no_anchor = with_body(body.replace(MAIN_READY, MAIN_READY[:4] + b"\x02" + MAIN_READY[5:]))
    for bad in (no_prologue, two_nines, no_anchor):
        with pytest.raises(ValueError, match="template drift"):
            ambient.classify(bad)
        with pytest.raises(ValueError, match="template drift"):
            ambient.restore_clear(bad)


# ------------------------------------------------------------------------------------------------ T-AMB-5
def test_amb5_hut_golden_moves_by_exactly_the_tail(built, tmp_path, monkeypatch):
    """T-AMB-5: the vivi-hut golden moves by exactly the 38-byte TAIL, to the pre-registered sha. With the pass as
    identity the build is the old golden; with it, the new golden, and new == old + TAIL at rel 246 in 7 languages."""
    new = built("vivi-hut")                                  # before the patch below (the session cache)
    monkeypatch.setattr(ambient, "restore_clear", lambda eb: bytes(eb))
    old = _build("vivi-hut", tmp_path)
    assert _sha(old["us"]) == HUT_PRE, "with the pass as identity the hut is not the pre-fix golden"
    assert provision.load_manifest()["goldens"]["EVT_HUT_INT.eb.bytes/us"] == HUT_POST
    assert _sha(new["us"]) == HUT_POST
    for lang in LANGS:
        assert new[lang] == insert_in_function(old[lang], 0, 0, HUT_TAIL_REL, ambient.TAIL), lang


# ------------------------------------------------------------------------------------------------ T-AMB-6
class _PassReached(Exception):
    pass


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_amb6_verbatim_never_calls_the_pass(tmp_path, monkeypatch):
    """T-AMB-6: with ``ambient.restore_clear`` patched to raise, a ``new`` scaffold build RAISES (the positive
    control: the patch site is live, so the build reads the module attribute) and the Dali Inn verbatim build
    (test_verbatim's end-to-end one) succeeds -- a verbatim fork keeps its donor's own tail and never meets the pass."""
    def reached(eb):
        raise _PassReached("ambient.restore_clear reached")
    monkeypatch.setattr(ambient, "restore_clear", reached)
    with pytest.raises(_PassReached):
        _build("new", tmp_path / "new")
    from ff9mapkit import extract
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path / "dv", name="DV",
                                               verbatim=True)
    project = B.FieldProject.load(toml)
    assert "verbatim_eb" in project.raw
    out = tmp_path / "mod"
    B.build_mod([project], out, mod_name="FF9CustomMap")
    ebs = _built_ebs(out)
    assert ambient.classify(ebs["us"]) == "stock-tail"
