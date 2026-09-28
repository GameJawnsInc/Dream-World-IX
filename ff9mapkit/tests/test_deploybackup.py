"""Pre-deploy backups are never overwritten -- ``ff9mapkit.deploybackup``.

THE INCIDENT (story-trace rung 3): ``tools/deploy_field.py`` stamped ``backups/<file>.preDEPLOY.<STAMP>`` to the
second. A scripted batch landed two fork deploys in one second, the later one's backups replaced the earlier's --
which by then held the earlier id's OWN ``FieldScene`` line and ForkDonorPatch row -- and the earlier id's revert
deleted its ``.eb`` but RESTORED its registration: the null-.eb black screen, armed in six reverts. The wiring into
the script is pinned in ``test_deploy_field_script``; this file pins the helper and replays the incident end to
end through a real generated revert, against a throwaway game root (``FF9_GAME_PATH``), never the real install.
"""
from __future__ import annotations

import ast
import datetime
import os
import pathlib
import subprocess
import sys

import pytest

import ff9mapkit
from ff9mapkit import deploybackup as bkp
from ff9mapkit import forkdonor
from ff9mapkit.config import ModLayout
from ff9mapkit.reverttmpl import build_revert_script

FROZEN = datetime.datetime(2026, 9, 25, 21, 39, 49, 123456)     # both deploys of the incident, one instant
KIT = pathlib.Path(ff9mapkit.__file__).resolve().parents[1]
_DEPLOY_FIELD = pathlib.Path(__file__).resolve().parents[2] / "tools" / "deploy_field.py"


def _frozen():
    return FROZEN


# ---- the helper ---------------------------------------------------------------------------------------------
def test_backup_exclusive_copies_the_bytes(tmp_path):
    src = tmp_path / "live.txt"
    src.write_bytes(b"FieldScene 30831 11 A A 47\r\nx")
    dst = bkp.backup_exclusive(src, tmp_path / "live.txt.preDEPLOY.s")
    assert dst.read_bytes() == src.read_bytes()


def test_backup_exclusive_refuses_an_existing_backup_and_leaves_it_untouched(tmp_path):
    src, dst = tmp_path / "live.txt", tmp_path / "live.txt.preDEPLOY.s"
    src.write_bytes(b"the later deploy's state")
    dst.write_bytes(b"the earlier deploy's snapshot")
    with pytest.raises(bkp.BackupExists) as ei:
        bkp.backup_exclusive(src, dst)
    assert isinstance(ei.value, FileExistsError)           # an OSError a caller can still catch broadly
    assert dst.read_bytes() == b"the earlier deploy's snapshot", "an existing backup must never be replaced"


def test_backup_exclusive_with_a_missing_source_creates_nothing(tmp_path):
    with pytest.raises(FileNotFoundError):
        bkp.backup_exclusive(tmp_path / "absent.txt", tmp_path / "absent.txt.preDEPLOY.s")
    assert not (tmp_path / "absent.txt.preDEPLOY.s").exists()


def test_two_claims_in_one_instant_get_distinct_stamps_and_keep_both_snapshots(tmp_path):
    """The mechanism of the incident, at library level: the second deploy of the same instant must get its own
    stamp, and the first deploy's snapshot -- taken BEFORE it registered itself -- must survive untouched."""
    live, bk = tmp_path / "DictionaryPatch.txt", tmp_path / "bk"
    bk.mkdir()
    live.write_text("FieldScene 30831 11 A A 47\n", encoding="utf-8", newline="\n")
    s1 = bkp.claim_stamp(bk, live, "DictionaryPatch.txt", now=_frozen)
    live.write_text("FieldScene 30831 11 A A 47\nFieldScene 30832 11 B B 8\n", encoding="utf-8", newline="\n")   # deploy 1 lands
    s2 = bkp.claim_stamp(bk, live, "DictionaryPatch.txt", now=_frozen)
    assert s1 != s2
    assert (bk / bkp.backup_name("DictionaryPatch.txt", s1)).read_text(encoding="utf-8") == \
        "FieldScene 30831 11 A A 47\n", "the earlier deploy's pre-deploy snapshot was overwritten"
    assert "30832" in (bk / bkp.backup_name("DictionaryPatch.txt", s2)).read_text(encoding="utf-8")


def test_the_stamp_is_sub_second_and_sorts_in_claim_order(tmp_path):
    live, bk = tmp_path / "DictionaryPatch.txt", tmp_path / "bk"
    bk.mkdir()
    live.write_text("", encoding="utf-8", newline="\n")
    first = bkp.claim_stamp(bk, live, "DictionaryPatch.txt", now=lambda: FROZEN.replace(microsecond=0))
    assert first == "20260925-213949-000000"
    later = [bkp.claim_stamp(bk, live, "DictionaryPatch.txt", now=lambda: FROZEN.replace(microsecond=0))
             for _ in range(2)]
    assert later == ["20260925-213949-000000-1", "20260925-213949-000000-2"], "a frozen clock takes a suffix"
    nxt = bkp.claim_stamp(bk, live, "DictionaryPatch.txt", now=lambda: FROZEN.replace(microsecond=1))
    assert sorted([nxt, *later, first]) == [first, *later, nxt]
    assert "20260925-213949" < first, "and every new stamp sorts after the old one-second stamp of its second"


def test_a_claim_gives_up_loudly_instead_of_spinning(tmp_path, monkeypatch):
    live, bk = tmp_path / "DictionaryPatch.txt", tmp_path / "bk"
    bk.mkdir()
    live.write_text("", encoding="utf-8", newline="\n")
    monkeypatch.setattr(bkp, "MAX_CLAIM_TRIES", 3)
    for _ in range(3):
        bkp.claim_stamp(bk, live, "DictionaryPatch.txt", now=_frozen)
    with pytest.raises(bkp.BackupExists, match="could not claim"):
        bkp.claim_stamp(bk, live, "DictionaryPatch.txt", now=_frozen)


# ---- the incident, replayed through real generated reverts --------------------------------------------------
def _fork_fragment(fid):
    """deploy_field's REAL ForkDonorPatch revert fragment, evaluated out of the script's AST for this id."""
    tree = ast.parse(_DEPLOY_FIELD.read_text(encoding="utf-8"))
    expr = [n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
            for t in n.targets if isinstance(t, ast.Name) and t.id == "fork_revert_code"
            and not (isinstance(n.value, ast.Constant) and n.value.value == "")][-1]
    return eval(compile(ast.Expression(ast.fix_missing_locations(expr)), "<frag>", "eval"), {"FID": fid})  # noqa: S307


def _deploy(tmp_path, game, bk, fid, name, donor):
    """A fork deploy's steps that decide this bug, in deploy_field's order: claim the stamp with the
    DictionaryPatch snapshot, snapshot ForkDonorPatch under it, register the field + its donor row, ship the .eb,
    and write the revert."""
    live = ModLayout(game / "MF")
    stamp = bkp.claim_stamp(bk, live.dictionary_patch, "DictionaryPatch.txt", now=_frozen)
    fdp = live.root / "ForkDonorPatch.txt"
    if fdp.exists():
        bkp.backup_exclusive(fdp, bk / bkp.backup_name("ForkDonorPatch.txt", stamp))
    fdp.write_text(forkdonor.merge_row(fdp.read_text(encoding="utf-8") if fdp.exists() else "", fid, donor),
                   encoding="utf-8", newline="\n")
    dp = live.dictionary_patch.read_text(encoding="utf-8")
    live.dictionary_patch.write_text(dp + f"FieldScene {fid} 11 {name} {name} 47\n", encoding="utf-8", newline="\n")
    eb = live.eb_path("us", f"EVT_{name}.eb.bytes")
    eb.parent.mkdir(parents=True, exist_ok=True)
    eb.write_bytes(b"eb")
    script = tmp_path / f"revert_deploy_{fid}.py"
    script.write_text(build_revert_script(kit=KIT, backup_dir=bk, stamp=stamp, mod_folder="MF", fid=fid, name=name,
                                          fbg=f"FBG_{name}", text_block=47, repo="r",
                                          fork_revert_code=_fork_fragment(fid)), encoding="utf-8")
    return script, stamp


def test_two_fork_deploys_in_one_second_each_revert_removes_its_own_registration(tmp_path):
    """The incident end to end: 30832 then 30833 deploy in the SAME instant. Before the fix they shared one
    stamp, 30833's snapshots replaced 30832's, and 30832's revert deleted its .eb but restored `FieldScene 30832`
    and its `30832 312` donor row. Now each revert removes exactly its own registration."""
    game, bk = tmp_path / "game", tmp_path / "bk"
    bk.mkdir()
    live = ModLayout(game / "MF")
    live.root.mkdir(parents=True)
    live.dictionary_patch.write_text("FieldScene 30831 11 T0_DL_INN T0_DL_INN 47\n", encoding="utf-8", newline="\n")
    (live.root / "ForkDonorPatch.txt").write_text(forkdonor.merge_row("", 30831, 351), encoding="utf-8", newline="\n")
    x, sx = _deploy(tmp_path, game, bk, 30832, "T0_DL_VIW", 312)
    y, sy = _deploy(tmp_path, game, bk, 30833, "T0_DL_WHL", 350)
    assert sx != sy
    rc = subprocess.run([sys.executable, str(x)], capture_output=True, text=True,
                        env={**os.environ, "FF9_GAME_PATH": str(game)})
    assert rc.returncode == 0, rc.stderr
    dp = live.dictionary_patch.read_text(encoding="utf-8")
    fd = (live.root / "ForkDonorPatch.txt").read_text(encoding="utf-8")
    assert not live.eb_path("us", "EVT_T0_DL_VIW.eb.bytes").exists()
    assert "FieldScene 30832" not in dp, "half-revert: the registration survived its .eb (null-.eb black screen)"
    assert forkdonor.own_row(fd, 30832) is None, "half-revert: the donor row survived the field"
    assert "FieldScene 30831" in dp and "FieldScene 30833" in dp, "the neighbours' registrations are untouched"
    assert forkdonor.own_row(fd, 30831) and forkdonor.own_row(fd, 30833)
