"""ff9mapkit.newgame -- the New-Game entry wiring extracted from tools/wire_newgame_from_stock.py +
tools/retarget_newgame_warp.py (now thin shims). Pure-logic coverage + an install-gated faithfulness check."""
from __future__ import annotations

import runpy
import struct
from pathlib import Path

import pytest

from ff9mapkit import newgame
from ff9mapkit.config import ModLayout
from ff9mapkit.content import ambient
from ff9mapkit.eb import EbScript
from ff9mapkit.eb import edit as eb_edit
from ff9mapkit.eb.model import pack_entry

from ._ebengine import Engine


def test_live_overrides_globs_only_customfolders(tmp_path):
    game = tmp_path / "FF9"
    a = game / "FF9CustomMap" / "x" / "us" / "evt_alex1_ts_opening.eb.bytes"
    b = game / "FF9CustomMap-bb" / "y" / "evt_alex1_ts_opening.eb.bytes"
    other = game / "SomeOtherMod" / "evt_alex1_ts_opening.eb.bytes"   # not FF9CustomMap* -> ignored
    for p in (a, b, other):
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
    found = newgame.live_overrides(game)
    assert a in found and b in found
    assert other not in found


def test_retarget_no_override_is_not_ok(tmp_path):
    res = newgame.retarget(tmp_path / "FF9", 4100, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv",
                           verbose=False)
    assert res["found"] == 0 and res["ok"] is False and res["revert"] is None


def test_emit_revert_writes_runnable_script(tmp_path):
    p = newgame._emit_revert(tmp_path / "rv", "revert_x.py", ['print("reverted")'])
    assert p.is_file() and p.name == "revert_x.py"
    assert 'print("reverted")' in p.read_text(encoding="utf-8")


def test_cli_registers_newgame():
    from ff9mapkit import cli
    ns = cli.build_parser().parse_args(["newgame", "6000"])
    assert ns.func.__name__ == "_cmd_newgame" and ns.field_id == 6000 and ns.mod_folder == "FF9CustomMap"


def test_global_game_and_modfolder_survive_subcommand_redeclare():
    """A subcommand redeclaring --game/--mod-folder (needed so `ff9mapkit newgame 6000 --mod-folder X` still
    works) must NOT silently reset a value the user gave BEFORE the subcommand name back to the subcommand's
    own default -- argparse copies the sub-namespace's declared defaults over the parent's on every parse."""
    from ff9mapkit import cli
    p = cli.build_parser()
    ns = p.parse_args(["--game", "C:/MyCustomFF9Install", "model-export", "GEO_MAIN_F0_VIV"])
    assert ns.game == "C:/MyCustomFF9Install"
    ns2 = p.parse_args(["--mod-folder", "FF9CustomMap-bb", "newgame", "6000"])
    assert ns2.mod_folder == "FF9CustomMap-bb"
    # the sub-level flag, given explicitly, still wins over the global one
    ns3 = p.parse_args(["newgame", "6000", "--mod-folder", "FF9CustomMap-ih"])
    assert ns3.mod_folder == "FF9CustomMap-ih"
    # neither given anywhere -> each level's own documented default holds
    ns4 = p.parse_args(["model-export", "GEO_MAIN_F0_VIV"])
    assert ns4.game is None
    ns5 = p.parse_args(["newgame", "6000"])
    assert ns5.mod_folder == "FF9CustomMap"
    # the world verbs whose --mod-folder is optional inherit the global value the same way
    ns6 = p.parse_args(["--mod-folder", "FF9CustomMap-world", "world-coast", "--cells", "1,1", "--donor", "18,15"])
    assert ns6.mod_folder == "FF9CustomMap-world"
    ns7 = p.parse_args(["--mod-folder", "FF9CustomMap-world", "world-encounters", "--config", "x.toml"])
    assert ns7.mod_folder == "FF9CustomMap-world"
    ns8 = p.parse_args(["--mod-folder", "FF9CustomMap-world", "world-morphs"])
    assert ns8.mod_folder == "FF9CustomMap-world"


def _install_game():
    try:
        from ff9mapkit.config import find_game_path
        g = find_game_path()
        return g if (g and Path(g).is_dir()) else None
    except Exception:
        return None


@pytest.mark.skipif(_install_game() is None, reason="needs the FF9 install (BYO p0data)")
def test_wire_from_stock_dryrun_matches_tool(tmp_path):
    """The package dry-run reproduces the in-game-proven tool: stock field 70 warps Field(50); the override
    repoints it to the target across 7 langs; dry-run writes nothing."""
    g = _install_game()
    try:
        res = newgame.wire_from_stock(g, 6000, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv",
                                      dry_run=True, verbose=False)
    except Exception as e:                                   # UnityPy missing / bundle unreadable
        pytest.skip(f"needs install + UnityPy: {e}")
    assert res["ok"] is True
    assert res["stock_dest"] == 50 and res["new_dest"] == 6000
    assert len(res["files"]) == 7
    assert res["revert"] is None                            # dry-run: nothing written
    assert not (tmp_path / "rv").exists()
    # the handoff follows 6000's own script: kept only when it owns 643 (the faithful opening's fork of 50)
    assert res["handoff"] == ("keep" if res["target_ambient"] == 643 else "stop")


# ================================================================================ F-NG: the ambient handoff
# Stock 70 marks Byte[13] := 2, plays 643 and sets the keep flag right before Field(50) -- a same-id handoff (50
# owns 643). Anywhere else the override must stop 643 first, in stock's own form (70's disc-change branch).
# The pure tests run on a kit-encoded stand-in for 70's warp shape; the install tests pin it to the real bytes.

STOP643 = bytes.fromhex("05d40d7d0900187f" "020800" "05d40d7d03002c7f" "c60080518302000000")   # 28 bytes
LT9_13 = bytes.fromhex("05d40d7d0900187f")          # Byte[13] < 9
LET2_13 = bytes.fromhex("05d40d7d02002c7f")         # Byte[13] := 2
KEEP162 = bytes.fromhex("05c5a27d01002c7f")         # Map.Bit[162] := 1 -- the keep-playing flag
ENT0 = bytes.fromhex("05d8027d00002c7f")            # Int16[2] := 0 -- the entrance var, right before Field()
BIT162_0 = bytes.fromhex("05c5a27d0000207f")        # Map.Bit[162] == 0
WAIT25 = bytes.fromhex("220019")


def _i16_9(k: int) -> bytes:
    """``Int16[9] := k`` -- the prologue's own-ambient statement (stock's one 8-byte form)."""
    return bytes([0x05, 0xD8, 0x09, 0x7D]) + struct.pack("<H", k) + b"\x2c\x7f"


def _script(main: bytes, *more) -> bytes:
    """A one-entry .eb: Main_Init (tag 0) = ``main``, then ``more`` as (tag, body) functions."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    return eb_edit.append_entry(bytes(head), 0, pack_entry(0, [(0, main), *more]))


def _opening(dest: int = 50, own: int = 643, *, entrance: bool = True) -> bytes:
    """Stock 70's warp shape, kit-encoded: the prologue's own ambient, a 0x0B switch whose default and second
    case lie PAST the warp (as 70's do, so an insert or remove there must re-aim them), case 0 = mark 2 + keep
    flag + Wait(25) + ``Int16[2] := 0`` + ``Field(dest)`` + JMP to RET, and a Main_Loop after Main_Init."""
    case0 = LT9_13 + b"\x02\x08\x00" + LET2_13 + KEEP162 + WAIT25 + (ENT0 if entrance else b"") + \
        bytes([0x2B, 0x00]) + struct.pack("<H", dest)
    case1 = BIT162_0 + b"\x02\x00\x00"
    jmp = b"\x01" + struct.pack("<h", len(case1))                    # case 0 ends by jumping over case 1
    anchor, c0 = 9, 18                                              # the 10-byte 0x0B sits at 8; anchor +1
    c1 = c0 + len(case0) + len(jmp)
    ret = c1 + len(case1)
    sw = bytes([0x0B, 0x02]) + struct.pack("<HHHH", 0, ret - anchor, c0 - anchor, c1 - anchor)
    main = _i16_9(own) + sw + case0 + jmp + case1 + b"\x04"
    loop = WAIT25[:2] + b"\x01" + b"\x01\xfa\xff"                    # L0: Wait(1); JMP L0
    return _script(main, (1, loop))


def _field(own: int) -> bytes:
    """A target field's script: just the prologue's own-ambient statement."""
    return _script(_i16_9(own) + b"\x04")


def _main(b: bytes) -> bytes:
    f = EbScript.from_bytes(b).entry(0).func_by_tag(0)
    return b[f.abs_start:f.abs_end]


def _byte13_at_warp(b: bytes, arriving: int = 1) -> int:
    """Run Main_Init's case 0 (``Byte[13] < 9`` .. the ``Field()``) and read the Byte[13] the warp hands on."""
    eb = EbScript.from_bytes(b)
    f = eb.entry(0).func_by_tag(0)
    body = b[f.abs_start:f.abs_end]
    start = body.index(LT9_13)                                      # case 0's first statement
    end = next(i.off for i in eb.instrs(f) if i.op == 0x2B) - f.abs_start
    eng = Engine()
    eng.scalars["Global.Byte[13]"] = arriving
    eng.run(body[start:end])
    return eng.scalars["Global.Byte[13]"]


def _switch_landing(b: bytes) -> list:
    """The instruction bytes each of Main_Init's 0x0B edges lands on (default, case 0, case 1)."""
    eb = EbScript.from_bytes(b)
    f = eb.entry(0).func_by_tag(0)
    ins = list(eb.instrs(f))
    sw = next(i for i in ins if i.op == 0x0B)
    at = {i.off: bytes(b[i.off:i.end]) for i in ins}
    return [at[sw.off + 1 + sw.args[k]] for k in (1, 2, 3)]


def _game(tmp_path, *, target: int, own: int, overrides: dict | None = None, folder: str = "FF9CustomMap-t"):
    """A tmp install: Memoria.ini stacking ``folder``, which registers field ``target`` (named HUB, its script
    owning ambient ``own``) and ships ``overrides`` ({lang: override bytes}) as the field-70 override."""
    game = tmp_path / "FF9"
    root = game / folder
    (root / "DictionaryPatch.txt").parent.mkdir(parents=True)
    (game / "Memoria.ini").write_text(f'[Mod]\nFolderNames = "{folder}"\n', encoding="utf-8")
    (root / "DictionaryPatch.txt").write_text(f"FieldScene {target} 21 GRGR HUB {target}\n", encoding="utf-8")
    hub = ModLayout(root).eb_path("us", "EVT_HUB.eb.bytes")
    hub.parent.mkdir(parents=True)
    hub.write_bytes(_field(own))
    for lang, data in (overrides or {}).items():
        p = root / newgame.OVERRIDE_REL.format(lang=lang)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return game, root


def test_exit_stop_is_stocks_form():
    """``ambient.exit_stop`` encodes stock's exit stop byte for byte (pinned against 70 itself in the install
    test below): ``if Byte[13] < 9 { Byte[13] := 3 }; RunSoundCode1(20864, k, 0)``."""
    assert ambient.exit_stop(643) == STOP643
    assert ambient.exit_stop(1483) == STOP643[:-5] + struct.pack("<H", 1483) + bytes(3)
    assert ambient.ambient_id(_opening()) == 643 and ambient.ambient_id(_field(65535)) == 65535


def test_set_handoff_seats_the_stop_before_the_warp():
    """stop=True puts the 28 bytes right before ``Int16[2] := 0; Field()`` -- where stock exits seat it -- and
    nothing else changes meaning: the warp, the switch's three edges and the Main_Loop all land where they did.
    Executed, the warp now hands on Byte[13] = 3 (stopped) instead of 2 (playing). stop=False undoes it exactly."""
    s0 = _opening(4600)
    s1 = newgame.set_handoff(s0, stop=True)
    assert newgame.handoff(s0) == "keep" and newgame.handoff(s1) == "stop"
    assert len(s1) == len(s0) + 28
    assert WAIT25 + STOP643 + ENT0 + b"\x2b\x00" + struct.pack("<H", 4600) in _main(s1)
    assert newgame.newgame_target(s1) == 4600
    assert _switch_landing(s1) == _switch_landing(s0)
    loop = lambda b: (lambda f: b[f.abs_start:f.abs_end])(EbScript.from_bytes(b).entry(0).func_by_tag(1))  # noqa: E731
    assert loop(s1) == loop(s0)
    assert _byte13_at_warp(s0) == 2 and _byte13_at_warp(s1) == 3
    assert newgame.set_handoff(s1, stop=True) == s1                 # idempotent
    assert newgame.set_handoff(s1, stop=False) == s0                # the exact inverse
    assert newgame.set_handoff(s0, stop=False) == s0


def test_set_handoff_refuses_a_reshaped_warp():
    """Drift fails loudly: no ``Int16[2] := N`` right before the Field(), or no own ambient to stop."""
    with pytest.raises(ValueError, match="warp shape"):
        newgame.set_handoff(_opening(4600, entrance=False), stop=True)
    with pytest.raises(ValueError, match="no slot-0 ambient"):
        newgame.set_handoff(_opening(4600, own=65535), stop=True)


def test_retarget_stops_643_for_a_target_that_owns_none(tmp_path):
    """The live shape: a plain 2-byte-swap override, retargeted to a field that owns no ambient (a hub). Every
    copy gets 70's stop before its Field(); the revert restores the pre-retarget bytes exactly."""
    old = _opening(4600)
    game, root = _game(tmp_path, target=4700, own=65535, overrides={"us": old, "jp": old})
    res = newgame.retarget(game, 4700, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv", verbose=False)
    for lang in ("us", "jp"):
        got = (root / newgame.OVERRIDE_REL.format(lang=lang)).read_bytes()
        assert STOP643 + ENT0 + b"\x2b\x00" + struct.pack("<H", 4700) in got
        assert _byte13_at_warp(got) == 3
    assert res["ok"] and res["changed"] == 2 and res["confirmed"] == 2 and res["target_ambient"] == 65535
    runpy.run_path(str(res["revert"]), run_name="__main__")
    for lang in ("us", "jp"):
        assert (root / newgame.OVERRIDE_REL.format(lang=lang)).read_bytes() == old


def test_retarget_upgrades_an_override_already_on_its_target(tmp_path):
    """An override already warping the target but still handing 643 on (the live FF9CustomMap-world copy) is
    NOT 'nothing to do': it gets the stop."""
    game, root = _game(tmp_path, target=4600, own=65535, overrides={"us": _opening(4600)})
    res = newgame.retarget(game, 4600, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv", verbose=False)
    assert res["ok"] and res["changed"] == 1
    assert STOP643 in (root / newgame.OVERRIDE_REL.format(lang="us")).read_bytes()


def test_retarget_keeps_stocks_handoff_for_a_643_owner(tmp_path):
    """Retargeted to a field that owns 643 (a fork of 50, e.g. the faithful opening's 6000), a stop-carrying
    override loses the stop: the result is exactly the 2-byte swap of the no-stop original -- stock's handoff."""
    stopped = newgame.set_handoff(_opening(4700), stop=True)
    game, root = _game(tmp_path, target=6000, own=643, overrides={"us": stopped})
    res = newgame.retarget(game, 6000, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv", verbose=False)
    assert res["ok"] and res["changed"] == 1 and res["target_ambient"] == 643
    got = (root / newgame.OVERRIDE_REL.format(lang="us")).read_bytes()
    assert got == _opening(6000)
    assert _byte13_at_warp(got) == 2


def test_retarget_skips_an_override_reshaped_away_from_70(tmp_path):
    """No ``Int16[2] := N`` before the warp: the handoff cannot be set, so the copy is left untouched and New
    Game reports NOT wired rather than half-wired."""
    odd = _opening(4600, entrance=False)
    game, root = _game(tmp_path, target=4700, own=65535, overrides={"us": odd})
    res = newgame.retarget(game, 4700, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv", verbose=False)
    assert res["found"] == 1 and res["confirmed"] == 0 and res["ok"] is False and res["revert"] is None
    assert (root / newgame.OVERRIDE_REL.format(lang="us")).read_bytes() == odd


class _FakeBundle:
    """Stands in for the install's p0data: stock field 70 is the kit-encoded opening warping Field(50)."""

    def __init__(self, *_a, **_k):
        pass

    def eb_for_id(self, fid):
        return _opening(50) if fid == 70 else None


@pytest.mark.parametrize("own, stop", [(65535, True), (1483, True), (643, False)])
def test_wire_from_stock_sets_the_handoff_by_target(tmp_path, monkeypatch, own, stop):
    """From stock: the stop is inserted unless the registered target owns 643; all 7 langs carry the same
    bytes, and the revert removes what was created."""
    monkeypatch.setattr(newgame.extract, "EventBundle", _FakeBundle)
    game, root = _game(tmp_path, target=4700, own=own)
    res = newgame.wire_from_stock(game, 4700, mod_folder="FF9CustomMap-t", backups_dir=tmp_path / "bk",
                                  reverts_dir=tmp_path / "rv", verbose=False)
    paths = [root / newgame.OVERRIDE_REL.format(lang=L) for L in newgame.LANGS]
    assert all((STOP643 + ENT0 in p.read_bytes()) is stop for p in paths)
    want = newgame.set_handoff(_opening(4700), stop=stop)
    assert all(p.read_bytes() == want for p in paths)
    assert res["ok"] and res["target_ambient"] == own and res["handoff"] == ("stop" if stop else "keep")
    runpy.run_path(str(res["revert"]), run_name="__main__")
    assert not any(p.exists() for p in paths)


def test_target_script_follows_the_folder_stack(tmp_path):
    """The target's script is read the way the engine resolves it: the id's name from the first FolderNames
    folder registering it, the file from the first folder shipping it; an unlisted ``mod_folder`` (a journey
    hub folder not stacked yet) is searched last; an unregistered custom id is unknown."""
    game = tmp_path / "FF9"
    (game / "A").mkdir(parents=True)
    (game / "Memoria.ini").write_text('FolderNames = "A", "B"\n', encoding="utf-8")
    (game / "A" / "DictionaryPatch.txt").write_text("FieldScene 4700 21 GRGR HUB 4700\n", encoding="utf-8")
    (game / "B").mkdir()
    (game / "B" / "DictionaryPatch.txt").write_text("FieldScene 4700 21 GRGR OTHER 4700\n", encoding="utf-8")
    for folder, name, own in (("B", "EVT_HUB", 1483), ("B", "EVT_OTHER", 643), ("C", "EVT_LATE", 643)):
        p = ModLayout(game / folder).eb_path("us", f"{name}.eb.bytes")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_field(own))
    (game / "C" / "DictionaryPatch.txt").write_text("FieldScene 4800 21 GRGR LATE 4800\n", encoding="utf-8")
    assert newgame.target_ambient(game, 4700) == 1483               # A's name wins, B serves the file
    assert newgame.target_ambient(game, 4800) is None               # C is not stacked ...
    assert newgame.target_ambient(game, 4800, mod_folder="C") == 643   # ... unless it is the folder being wired
    assert newgame.target_ambient(game, 31999) is None              # registered nowhere, not a stock id


def _stock70():
    g = _install_game()
    try:
        from ff9mapkit import extract
        return extract.EventBundle(game=str(g)).eb_for_id(70) if g else None
    except Exception:                                        # UnityPy missing / bundle unreadable
        return None


@pytest.mark.skipif(_install_game() is None, reason="needs the FF9 install (BYO p0data)")
def test_the_stop_is_field_70s_own_and_seats_where_its_exits_do():
    """Grounding in the real bytes: 70's disc-change branch (Main_Init rel 812-839) IS ``exit_stop(643)``; 70
    owns 643; and its New-Game warp is ``Wait(25); Int16[2] := 0; Field(50)`` (rel 538/541/549) -- the seat."""
    s = _stock70()
    if s is None:
        pytest.skip("needs install + UnityPy")
    body = _main(s)
    assert ambient.ambient_id(s) == 643
    assert body[812:840] == ambient.exit_stop(643) == STOP643
    assert body[538:549] == WAIT25 + ENT0 and body[549:553] == b"\x2b\x00\x32\x00"
    assert newgame.handoff(s) == "keep"


@pytest.mark.skipif(_install_game() is None, reason="needs the FF9 install (BYO p0data)")
def test_real_override_stops_643_before_its_warp():
    """On stock 70 itself: the override for a target that owns none is the literal swap plus exactly one
    insert (70's stop at rel 541); run, its warp hands on Byte[13] = 3, the swap alone 2; the play of 643
    precedes its stop, which precedes the Field(); the scenario switch's three edges land where they did; the
    kit's own eb-src round-trips it; and a 643-owning target gets the bare swap (stock verbatim for 50)."""
    s = _stock70()
    if s is None:
        pytest.skip("needs install + UnityPy")
    from ff9mapkit.content.verbatim import remap_fields
    from ff9mapkit.eb import ebsrc
    swap = remap_fields(s, {50: 4600})
    o = newgame.build_override(s, 4600, 65535)
    assert o == eb_edit.insert_in_function(swap, 0, 0, 541, STOP643)
    assert newgame.newgame_target(o) == 4600 and newgame.handoff(o) == "stop"
    assert _byte13_at_warp(swap) == 2 and _byte13_at_warp(o) == 3
    body = _main(o)
    play = body.index(bytes.fromhex("c80080d08302"))                 # RunSoundCode3(53376 = RES_PLAY, 643, ..)
    assert play < body.index(STOP643) < body.index(b"\x2b\x00" + struct.pack("<H", 4600))   # < stop < Field()
    assert _switch_landing(o) == _switch_landing(swap)
    assert ebsrc.assemble_source(ebsrc.write_source(o, enrich=False)) == o
    assert newgame.set_handoff(o, stop=False) == swap
    assert newgame.build_override(s, 6000, 643) == remap_fields(s, {50: 6000})
    assert newgame.build_override(s, 50, 643) == s
