"""``tools/ambient_splice.py`` -- F-REDEPLOY by splice: a deployed synthesized field gains exactly the ambient TAIL.

Pinned on the kit's own build, never on bytes the test made itself: the vivi-hut built with the ambient pass as
identity (the pre-fix bytes a field deployed before d98ca2a4 carries) against the same build with it (the fixed
golden). The checker must accept that pair in all 7 languages and refuse each mutation; the whole tool is then run
against a FAKE install and main repo (both swapped in by name on the loaded tool module -- the real install, backups
and ledger are never touched): the dry run writes nothing, ``--apply`` writes restore_clear + backups + a revert
script, a second apply is a no-op, the revert restores the old bytes, and a revert over a changed file refuses.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from ff9mapkit import build as B
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.content import ambient
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.edit import insert_in_function

REPO = Path(__file__).resolve().parents[2]
HUT = Path(__file__).resolve().parents[1] / "examples" / "vivi-hut" / "hut_int.field.toml"
FOLDER = "FF9CustomMap-test"


def _load():
    spec = importlib.util.spec_from_file_location("ambient_splice_under_test", REPO / "tools" / "ambient_splice.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hut(out: Path) -> dict:
    B.build_mod([B.FieldProject.load(HUT)], out, mod_name="FF9CustomMap")
    return {L: next(out.rglob(f"eventbinary/field/{L}/*.eb.bytes")).read_bytes() for L in LANGS}


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    """``(old, new)``: the hut built without the ambient pass, and with it."""
    new = _hut(tmp_path_factory.mktemp("new"))
    real = ambient.restore_clear
    ambient.restore_clear = lambda eb: bytes(eb)             # build_script calls it through the module attribute
    try:
        old = _hut(tmp_path_factory.mktemp("old"))
    finally:
        ambient.restore_clear = real
    return old, new


def test_checker_accepts_the_kit_build(pair):
    S = _load()
    old, new = pair
    for L in LANGS:
        assert ambient.classify(old[L]) == "missing" and new[L] == ambient.restore_clear(old[L]), L
        S.check_splice(old[L], new[L])


def test_checker_refuses_mutations(pair):
    S = _load()
    old = pair[0]["us"]
    good = ambient.restore_clear(old)
    _f, stmts = ambient._main_init(old)
    anc = ambient._anchor(stmts)
    prev = max(o for o, _ in stmts if o < anc)
    flip = EbScript.from_bytes(good).entry(1).funcs[0].abs_start + 1       # inside a function other than Main_Init
    bad = {
        "unchanged": old,
        "tail one instruction early": insert_in_function(old, 0, 0, prev, ambient.TAIL),
        "another function changed": good[:flip] + bytes([good[flip] ^ 0x01]) + good[flip + 1:],
        "tail twice": insert_in_function(good, 0, 0, anc, ambient.TAIL),
    }
    for what, b in bad.items():
        with pytest.raises((AssertionError, ValueError)):
            S.check_splice(old, b)
            pytest.fail(what)


def test_tool_end_to_end_on_a_fake_install(pair, tmp_path, monkeypatch, capsys):
    S = _load()
    old = pair[0]
    game, main = tmp_path / "game", tmp_path / "main"
    live = ModLayout(game / FOLDER)
    live.root.mkdir(parents=True)
    live.dictionary_patch.write_text("MessageFile 30999 MES_X\nFieldScene 30999 11 SOME_MAP HUTX 30999\n",
                                     encoding="utf-8")
    for L in LANGS:
        p = live.eb_path(L, "EVT_HUTX.eb.bytes")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(old[L])
    dp_before = live.dictionary_patch.read_bytes()
    monkeypatch.setattr(S, "find_game_path", lambda: game)
    monkeypatch.setattr(S, "_MAIN", main)
    monkeypatch.setattr(S, "_ff9_running", lambda: False)
    eb = lambda L: live.eb_path(L, "EVT_HUTX.eb.bytes").read_bytes()

    assert S.main(["30999", "--mod-folder", FOLDER]) == 0                       # dry run
    assert all(eb(L) == old[L] for L in LANGS) and not (main / "backups").exists()

    assert S.main(["30999", "--mod-folder", FOLDER, "--apply"]) == 0
    assert all(eb(L) == ambient.restore_clear(old[L]) for L in LANGS)
    assert live.dictionary_patch.read_bytes() == dp_before
    assert len(list((main / "backups").iterdir())) == len(LANGS)
    assert "HUTX <- ambient_splice" in (game / "ff9mapkit-deploys.log").read_text(encoding="utf-8")
    capsys.readouterr()
    assert S.main(["30999", "--mod-folder", FOLDER, "--apply"]) == 0                # idempotent
    assert "nothing to do" in capsys.readouterr().out

    revert = main / "tools" / "scroll_out" / "revert_ambient_30999.py"
    assert subprocess.run([sys.executable, str(revert)]).returncode == 0
    assert all(eb(L) == old[L] for L in LANGS)
    assert subprocess.run([sys.executable, str(revert)], capture_output=True).returncode == 1   # changed: refuse
    assert all(eb(L) == old[L] for L in LANGS)


def test_apply_refuses_while_the_game_runs(pair, tmp_path, monkeypatch):
    S = _load()
    game = tmp_path / "game"
    live = ModLayout(game / FOLDER)
    live.root.mkdir(parents=True)
    live.dictionary_patch.write_text("FieldScene 30999 11 SOME_MAP HUTX 30999\n", encoding="utf-8")
    for L in LANGS:
        p = live.eb_path(L, "EVT_HUTX.eb.bytes")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pair[0][L])
    monkeypatch.setattr(S, "find_game_path", lambda: game)
    monkeypatch.setattr(S, "_MAIN", tmp_path / "main")
    monkeypatch.setattr(S, "_ff9_running", lambda: True)
    with pytest.raises(SystemExit, match="FF9.exe is running"):
        S.main(["30999", "--mod-folder", FOLDER, "--apply"])
    assert all(live.eb_path(L, "EVT_HUTX.eb.bytes").read_bytes() == pair[0][L] for L in LANGS)
