"""``tools/repair_collided_backups.py`` -- repairing the reverts a same-second deploy already armed.

The deploy fix (``ff9mapkit.deploybackup``) stops NEW stamp collisions; reverts written before it keep backups
that hold the earlier deploy's own registration, and running one deletes the field's ``.eb`` but restores its
``FieldScene`` line (the null-.eb black screen; six story-trace rung-3 forks). Every case here is built in a
throwaway game root + backups dir and runs the REAL generated reverts through ``FF9_GAME_PATH`` -- never the
real install, never the main repo's backups or scroll_out.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

import ff9mapkit
from ff9mapkit import deploylog, forkdonor
from ff9mapkit.config import ModLayout
from ff9mapkit.reverttmpl import build_revert_script

_TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools"
_TOOL = _TOOLS / "repair_collided_backups.py"
if not _TOOL.is_file():
    pytest.skip("repo-only tools/ script not present (installed-package layout)", allow_module_level=True)
_spec = importlib.util.spec_from_file_location("repair_collided_backups", _TOOL)
rcb = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = rcb                  # @dataclass resolves its string annotations through sys.modules
_spec.loader.exec_module(rcb)

KIT = pathlib.Path(ff9mapkit.__file__).resolve().parents[1]
S0, S = "20260925-213948", "20260925-213949"       # the predecessor's stamp, and the one 30832 + 30833 share
NAMES = {30831: "T0_DL_INN", 30832: "T0_DL_VIW", 30833: "T0_DL_WHL"}
DONOR = {30831: 351, 30832: 312, 30833: 350}
BASE = ["FieldScene 30100 11 OLD OLD 30100"]           # a foreign registration that must survive everything


def _fs(fid):
    return f"FieldScene {fid} 11 {NAMES[fid]} {NAMES[fid]} 47"


def _fd_text(*fids):
    txt = ""
    for f in fids:
        txt = forkdonor.merge_row(txt, f, DONOR[f])
    return txt or forkdonor.HEADER + "\n"


def _fork_fragment(fid):
    """deploy_field's REAL ForkDonorPatch revert fragment, evaluated out of the script's AST for this id."""
    tree = ast.parse((_TOOLS / "deploy_field.py").read_text(encoding="utf-8"))
    expr = [n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
            for t in n.targets if isinstance(t, ast.Name) and t.id == "fork_revert_code"
            and not (isinstance(n.value, ast.Constant) and n.value.value == "")][-1]
    return eval(compile(ast.Expression(ast.fix_missing_locations(expr)), "<frag>", "eval"), {"FID": fid})  # noqa: S307


def _world(root, *, journal=None, journal_fids=(30831, 30832, 30833), mints=None):
    """The rung-3 shape: 30831 deployed at S0; 30832 then 30833 deployed in the SAME second, so 30833's snapshots
    (taken after 30832 registered itself) replaced 30832's under stamp S. All three are live.
    ``journal`` = (bytes at S0, bytes at S) adds a wholesale-restored JournalPatch to the reverts of
    ``journal_fids`` (every rung-3 fork shipped one); ``mints`` = {fid: [geo ids]} gives those deploys a minted
    3DModel (registered in the shared snapshot)."""
    game, bk, out = root / "game", root / "bk", root / "scroll_out"
    for d in (bk, out):
        d.mkdir(parents=True)
    live = ModLayout(game / "MF")
    live.root.mkdir(parents=True)
    mints = mints or {}
    geo = [f"3DModel {g} GEO_{g}" for g in sorted({g for gs in mints.values() for g in gs})]
    (bk / f"DictionaryPatch.txt.preDEPLOY.{S0}").write_text("\n".join(BASE) + "\n", encoding="utf-8", newline="\n")
    (bk / f"ForkDonorPatch.txt.preDEPLOY.{S0}").write_text(_fd_text(), encoding="utf-8", newline="\n")
    (bk / f"DictionaryPatch.txt.preDEPLOY.{S}").write_text(
        "\n".join(BASE + [_fs(30831), *geo, _fs(30832)]) + "\n", encoding="utf-8", newline="\n")
    (bk / f"ForkDonorPatch.txt.preDEPLOY.{S}").write_text(_fd_text(30831, 30832), encoding="utf-8", newline="\n")
    live.dictionary_patch.write_text("\n".join(BASE + [_fs(30831), *geo, _fs(30832), _fs(30833)]) + "\n",
                                     encoding="utf-8", newline="\n")
    (live.root / "ForkDonorPatch.txt").write_text(_fd_text(30831, 30832, 30833), encoding="utf-8", newline="\n")
    jp = live.root / "JournalPatch.txt"
    if journal:
        (bk / f"JournalPatch.txt.preDEPLOY.{S0}").write_bytes(journal[0])
        (bk / f"JournalPatch.txt.preDEPLOY.{S}").write_bytes(journal[1])
        jp.write_bytes(journal[1])
    for fid, stamp in ((30831, S0), (30832, S), (30833, S)):
        eb = live.eb_path("us", f"EVT_{NAMES[fid]}.eb.bytes")
        eb.parent.mkdir(parents=True, exist_ok=True)
        eb.write_bytes(b"eb")
        csv = (f'\nshutil.copyfile(BK/f"JournalPatch.txt.preDEPLOY.{{STAMP}}", Path({str(jp)!r}))'
               if journal and fid in journal_fids else "")
        (out / f"revert_deploy_{fid}.py").write_text(build_revert_script(
            kit=KIT, backup_dir=bk, stamp=stamp, mod_folder="MF", fid=fid, name=NAMES[fid], fbg=f"FBG_{NAMES[fid]}",
            text_block=47, repo="r", mint_ids={str(g) for g in mints.get(fid, ())}, csv_revert_code=csv,
            fork_revert_code=_fork_fragment(fid)), encoding="utf-8")
    return game, bk, out, live


def _run(out, game, fid):
    rc = subprocess.run([sys.executable, str(out / f"revert_deploy_{fid}.py")], capture_output=True, text=True,
                        env={**os.environ, "FF9_GAME_PATH": str(game)})
    assert rc.returncode == 0, rc.stderr
    return rc


def _live_state(live):
    return (live.dictionary_patch.read_text(encoding="utf-8"),
            (live.root / "ForkDonorPatch.txt").read_text(encoding="utf-8"))


def _infos(out):
    infos, _ = rcb.scan(out)
    return infos, {i.fid: i for i in infos}


def _repair(out, fid, **kw):
    infos, by = _infos(out)
    plan = rcb.plan_repair(by[fid], infos, **kw)
    rcb.apply_repair(plan)
    return plan


def test_the_scan_flags_the_earlier_deploy_of_a_shared_stamp_and_only_it(tmp_path):
    _game, _bk, out, _live = _world(tmp_path)
    infos, by = _infos(out)
    assert {i.fid for i in infos} == {30831, 30832, 30833}
    assert [p.fid for p in rcb.partners_of(by[30832], infos)] == [30833]
    dp_own, fd_own = rcb.held_own(by[30832])
    assert [l.strip() for l in dp_own] == [_fs(30832)] and [l.strip() for l in fd_own] == ["30832 312"]
    assert rcb.held_own(by[30833]) == ([], []) and rcb.held_own(by[30831]) == ([], [])


def test_as_the_backups_stand_the_revert_half_reverts(tmp_path):
    """The defect, reproduced with the real generated revert: .eb gone, registration + donor row restored."""
    game, _bk, out, live = _world(tmp_path)
    _run(out, game, 30832)
    dp, fd = _live_state(live)
    assert not live.eb_path("us", "EVT_T0_DL_VIW.eb.bytes").exists()
    assert _fs(30832) in dp and forkdonor.own_row(fd, 30832) == "30832 312"


def test_after_the_repair_the_revert_removes_its_own_registration(tmp_path):
    game, bk, out, live = _world(tmp_path)
    plan = _repair(out, 30832)
    assert [(p.name, [l.strip() for l in d]) for p, _n, d, _c in plan.rewrites] == [
        (f"DictionaryPatch.txt.preDEPLOY.{S}", [_fs(30832)]), (f"ForkDonorPatch.txt.preDEPLOY.{S}", ["30832 312"])]
    _run(out, game, 30832)
    dp, fd = _live_state(live)
    assert _fs(30832) not in dp and forkdonor.own_row(fd, 30832) is None
    for keep in (*BASE, _fs(30831), _fs(30833)):
        assert keep in dp
    assert forkdonor.own_row(fd, 30831) and forkdonor.own_row(fd, 30833)


def test_the_repair_leaves_the_partners_revert_exactly_as_it_was(tmp_path):
    """The shared files are the PARTNER's backups too. Its revert consults only its own lines in them, so the
    repair must not change what it does: run 30833's revert in an unrepaired and a repaired copy -- same result."""
    results = []
    for sub, repair in (("before", False), ("after", True)):
        game, _bk, out, live = _world(tmp_path / sub)
        if repair:
            _repair(out, 30832)
        _run(out, game, 30833)
        results.append(_live_state(live))
    assert results[0] == results[1]
    assert _fs(30833) not in results[0][0], "and the partner's own revert still works"


def test_the_original_is_kept_and_a_second_plan_is_empty(tmp_path):
    _game, bk, out, _live = _world(tmp_path)
    shared = bk / f"DictionaryPatch.txt.preDEPLOY.{S}"
    before = shared.read_bytes()
    _repair(out, 30832)
    assert (bk / (shared.name + rcb.ORIG_SUFFIX)).read_bytes() == before
    assert shared.read_bytes() == before.replace((_fs(30832) + "\n").encode(), b"")
    infos, by = _infos(out)
    assert rcb.plan_repair(by[30832], infos).rewrites == []
    assert rcb.plan_repair(by[30833], infos).rewrites == [], "the later deploy's backup never held its own lines"


def test_the_simulation_predicts_both_outcomes_without_writing(tmp_path):
    _game, bk, out, live = _world(tmp_path)
    infos, by = _infos(out)
    info = by[30832]
    plan = rcb.plan_repair(info, infos)
    live_dp = live.dictionary_patch.read_text(encoding="utf-8").splitlines()
    live_fd = (live.root / "ForkDonorPatch.txt").read_text(encoding="utf-8")
    stale = rcb.simulate(info, (bk / f"DictionaryPatch.txt.preDEPLOY.{S}").read_text(encoding="utf-8").splitlines(),
                         (bk / f"ForkDonorPatch.txt.preDEPLOY.{S}").read_text(encoding="utf-8"), live_dp, live_fd)
    new = {p.name: b.decode() for p, b, _d, _c in plan.rewrites}
    fixed = rcb.simulate(info, new[f"DictionaryPatch.txt.preDEPLOY.{S}"].splitlines(),
                         new[f"ForkDonorPatch.txt.preDEPLOY.{S}"], live_dp, live_fd)
    assert stale == ([_fs(30832)], "30832 312") and fixed == ([], None)
    assert not list(bk.glob("*" + rcb.ORIG_SUFFIX)), "planning and simulating must write nothing"


# ---- refusals: the repair only runs where the evidence settles which lines the deploy itself wrote ----------
def test_no_shared_stamp_is_refused(tmp_path):
    _game, _bk, out, _live = _world(tmp_path)
    (out / "revert_deploy_30833.py").unlink()
    infos, by = _infos(out)
    with pytest.raises(rcb.RepairRefused, match="not a stamp collision"):
        rcb.plan_repair(by[30832], infos)


def test_a_line_the_partner_also_owns_is_refused(tmp_path):
    """Both deploys mint GEO 6000: its `3DModel` line is 30832's to drop AND 30833's to restore -- dropping it
    would change the partner's revert, so the repair refuses."""
    _game, _bk, out, _live = _world(tmp_path, mints={30832: [6000], 30833: [6000]})
    infos, by = _infos(out)
    with pytest.raises(rcb.RepairRefused, match="ALSO owned by 30833"):
        rcb.plan_repair(by[30832], infos)


def test_a_wholesale_backup_that_differs_from_the_predecessor_is_refused(tmp_path):
    """Both deploys restore JournalPatch from the shared stamp, so the file there is the LATER deploy's snapshot
    -- right for the earlier one only if nothing changed it in between, which the predecessor's copy shows."""
    same = rcb.plan_repair(*_pick(_world(tmp_path / "same", journal=(b"J", b"J"))[2], 30832))
    assert any("JournalPatch.txt: byte-identical" in e for e in same.evidence)
    with pytest.raises(rcb.RepairRefused, match="not byte-identical"):
        rcb.plan_repair(*_pick(_world(tmp_path / "diff", journal=(b"J", b"J+30832"))[2], 30832))


def test_a_wholesale_backup_no_partner_restores_is_the_ids_own(tmp_path):
    """30842 (block 47) shared its stamp with 30843 (block 8): the block-47 .mes snapshots there were written by
    30842 alone -- a deploy only writes backups its own revert restores -- so they are genuine, whatever the
    predecessor held."""
    plan = rcb.plan_repair(*_pick(_world(tmp_path, journal=(b"J", b"J+30832"), journal_fids=(30832,))[2], 30832))
    assert plan.rewrites and any("JournalPatch.txt: this deploy's own snapshot" in e for e in plan.evidence)


def _pick(out, fid):
    infos, by = _infos(out)
    return by[fid], infos


def test_a_prelude_revert_right_before_the_deploy_is_refused(tmp_path):
    """A prelude re-add is invisible to every backup; the ledger's `retired` row seconds before the stamp is the
    only witness."""
    _game, _bk, out, _live = _world(tmp_path)
    old = deploylog.Entry("2026-09-25T20:00:00", deploylog.RETIRED, 30832, "MF", "", "")
    assert rcb.plan_repair(*_pick(out, 30832), ledger=[old]).rewrites, "an old retirement is not this deploy's"
    fresh = deploylog.Entry("2026-09-25T21:39:47", deploylog.RETIRED, 30832, "MF", "", "")
    with pytest.raises(rcb.RepairRefused, match="prelude revert"):
        rcb.plan_repair(*_pick(out, 30832), ledger=[old, fresh])


def test_more_than_one_other_deploy_in_the_gap_needs_the_explicit_flag(tmp_path):
    _game, bk, out, _live = _world(tmp_path)
    shared = bk / f"DictionaryPatch.txt.preDEPLOY.{S}"
    shared.write_text(shared.read_text(encoding="utf-8") + "BattleScene 30871 LEDGER_A BBG_B251\n", encoding="utf-8", newline="\n")
    with pytest.raises(rcb.RepairRefused, match="more than one other deploy"):
        rcb.plan_repair(*_pick(out, 30832))
    assert rcb.plan_repair(*_pick(out, 30832), allow_other_deploys=True).rewrites
    shared.write_text(shared.read_text(encoding="utf-8") + "3DModel 6001 GEO_X\n", encoding="utf-8", newline="\n")
    with pytest.raises(rcb.RepairRefused, match="not another deploy's id-keyed"):
        rcb.plan_repair(*_pick(out, 30832), allow_other_deploys=True)


def test_the_cli_scan_and_repair_through_path_seams(tmp_path, capsys):
    game, bk, out, live = _world(tmp_path)
    assert rcb.main(["--scroll-out", str(out), "--game", str(game)]) == 1
    assert "30832  HALF-REVERT" in capsys.readouterr().out
    assert rcb.main(["--plan", "30832", "--scroll-out", str(out), "--game", str(game)]) == 0
    plan_out = capsys.readouterr().out
    assert "revert as the backups stand: leaves ['FieldScene 30832" in plan_out
    assert "revert after the repair: leaves no own registration" in plan_out
    assert not list(bk.glob("*" + rcb.ORIG_SUFFIX))
    assert rcb.main(["--repair", "30832", "--scroll-out", str(out), "--game", str(game)]) == 0
    assert list(bk.glob("*" + rcb.ORIG_SUFFIX))
    assert rcb.main(["--scroll-out", str(out), "--game", str(game)]) == 0, "nothing defective is left"
