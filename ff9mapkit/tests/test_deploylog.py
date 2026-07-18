"""The deploy LEDGER (ff9mapkit.deploylog) -- the guard that makes a missing registration explain itself.

The failure mode pinned throughout: on 2026-07-18 field 4003's FieldScene line was gone and nothing on disk
said whether it had been RETIRED or LOST -- the two are the same absent line. These tests pin (a) that the
ledger round-trips, (b) that concurrent appenders don't tear each other's lines ON THIS PLATFORM (with a
deliberately non-atomic negative control that DOES tear, so the positive test isn't vacuous), (c) that
reconcile() separates lost from retired from still-registered, and (d) that the whole thing is never
load-bearing -- an unwritable ledger must not raise.

Every fixture install is built explicitly. Nothing here may fall through to the developer's real install.
"""

import ast
import builtins
import multiprocessing as mp
import os
import pathlib
import re
import time

from ff9mapkit import deploylog


# ---------------------------------------------------------------- fixtures

def _make_install(root, folders=("FF9CustomMap",), registrations=None):
    """A minimal fake FF9 install: a Memoria.ini naming a FolderNames stack, and one mod folder per name
    with its own DictionaryPatch.txt. `registrations` maps folder -> list of DictionaryPatch lines."""
    root.mkdir(parents=True, exist_ok=True)
    quoted = ", ".join(f'"{f}"' for f in folders)
    (root / "Memoria.ini").write_text(f"[Mod]\nFolderNames = {quoted}\n", encoding="utf-8")
    for f in folders:
        d = root / f
        d.mkdir(parents=True, exist_ok=True)
        lines = (registrations or {}).get(f, [])
        (d / "DictionaryPatch.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return root


# ---------------------------------------------------------------- record/read round-trip

def test_record_then_read_round_trips_every_field(tmp_path):
    game = _make_install(tmp_path / "game")
    assert deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap",
                            checkout=r"C:\gd\Dream-World-IX", note="TESTROOM <- my.field.toml") is True
    (e,) = deploylog.read(game)
    assert (e.event, e.field_id, e.mod_folder) == ("deployed", 4003, "FF9CustomMap")
    assert e.checkout == r"C:\gd\Dream-World-IX"
    assert e.note == "TESTROOM <- my.field.toml"
    assert e.when                                        # an ISO timestamp, kept as text
    assert deploylog.ledger_path(game).name == "ff9mapkit-deploys.log"


def test_ledger_sits_in_the_install_root_not_a_mod_folder(tmp_path):
    # deploy_campaign rmtree+copytrees a mod folder; a log kept inside one would be destroyed by the very
    # operation it exists to explain (incident 1).
    game = _make_install(tmp_path / "game")
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    assert deploylog.ledger_path(game).is_file()
    assert not (game / "FF9CustomMap" / "ff9mapkit-deploys.log").exists()


def test_appends_accumulate_and_preserve_order(tmp_path):
    game = _make_install(tmp_path / "game")
    for i in range(5):
        deploylog.record(game, deploylog.DEPLOYED, 4000 + i, "FF9CustomMap", note=f"n{i}")
    entries = deploylog.read(game)
    assert [e.field_id for e in entries] == [4000, 4001, 4002, 4003, 4004]   # append, never truncate


def test_last_events_is_last_writer_wins(tmp_path):
    game = _make_install(tmp_path / "game")
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    deploylog.record(game, deploylog.RETIRED, 4003, "FF9CustomMap")
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap", note="re-deployed")
    assert deploylog.last_events(game)[4003].note == "re-deployed"


def test_tabs_and_newlines_in_a_field_cannot_forge_a_record(tmp_path):
    # a mod folder / note is free text and a Windows path can carry anything; a stray newline would split
    # one event into two records and desync every field after it.
    game = _make_install(tmp_path / "game")
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap",
                     note="line1\nline2\tcol2")
    (e,) = deploylog.read(game)
    assert e.note == "line1 line2 col2"


def test_malformed_lines_are_skipped_not_fatal(tmp_path):
    game = _make_install(tmp_path / "game")
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    with open(deploylog.ledger_path(game), "a", encoding="utf-8") as fh:
        fh.write("garbage\n")
        fh.write("a\tb\tNOT_AN_INT\td\te\tf\n")
    assert [e.field_id for e in deploylog.read(game)] == [4003]


# ---------------------------------------------------------------- never load-bearing

def test_missing_ledger_reads_empty_rather_than_raising(tmp_path):
    game = _make_install(tmp_path / "game")
    assert deploylog.read(game) == []
    assert deploylog.last_events(game) == {}
    assert deploylog.reconcile(game).missing == []


def test_record_into_a_nonexistent_directory_returns_false_and_does_not_raise(tmp_path):
    # the never-load-bearing rule: a deploy must not die because its own diagnostics couldn't be written.
    assert deploylog.record(tmp_path / "no" / "such" / "install",
                            deploylog.DEPLOYED, 4003, "FF9CustomMap") is False


def test_record_over_a_directory_named_like_the_ledger_returns_false(tmp_path):
    # a portable stand-in for a read-only / permission-denied install: the target path can't be opened for
    # writing, and os.open raises OSError -- which record() must swallow.
    game = _make_install(tmp_path / "game")
    deploylog.ledger_path(game).mkdir()
    assert deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap") is False


def test_unreadable_ledger_reads_empty(tmp_path):
    game = _make_install(tmp_path / "game")
    deploylog.ledger_path(game).mkdir()                  # a directory where a file belongs -> OSError on read
    assert deploylog.read(game) == []


# ---------------------------------------------------------------- concurrency (with a negative control)

_N_PROCS = 4
_N_LINES = 20


def _record_worker(path, tag, barrier, n):
    """Drives the REAL deploylog.record() -- not a hand-rolled mirror of it, so the test can't pass while
    the shipped writer differs. `path` is the ledger file; record() derives it from the install root."""
    game = os.path.dirname(str(path))
    for i in range(n):
        barrier.wait()                                    # every process writes at the SAME instant
        assert deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap",
                                checkout=tag, note=str(i)) is True


def _torn_worker(path, tag, barrier, n):
    """The NEGATIVE CONTROL: seek-to-end then write, with the record split across two writes -- i.e. what
    open(path, 'a') does on Windows through the CRT. Every process resolves the same end offset while the
    others are asleep, so they clobber each other deterministically."""
    fd = os.open(str(path), os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        for i in range(n):
            data = ("2026-07-18T00:00:00\tdeployed\t4003\tFF9CustomMap\t"
                    f"{tag}\t{i}\n").encode("utf-8")
            barrier.wait()
            os.lseek(fd, 0, os.SEEK_END)                  # all N agree on the offset here...
            time.sleep(0.01)                              # ...and then all N write to it
            os.write(fd, data[:8])
            time.sleep(0.01)
            os.write(fd, data[8:])
    finally:
        os.close(fd)


def _run_workers(worker, path, n_procs=_N_PROCS, n_lines=_N_LINES):
    barrier = mp.Barrier(n_procs)
    procs = [mp.Process(target=worker, args=(str(path), f"proc{k}", barrier, n_lines))
             for k in range(n_procs)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
    assert all(p.exitcode == 0 for p in procs), [p.exitcode for p in procs]


def _wellformed(path):
    """(well-formed records, total non-empty lines) in a ledger file."""
    lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    good = [ln for ln in lines if len(ln.split("\t")) == 6 and ln.split("\t")[2] == "4003"]
    return good, lines


def test_concurrent_record_loses_no_line_and_tears_none(tmp_path):
    # The claim is BEHAVIOURAL, not a cited guarantee -- and this test earned its keep: with record()
    # relying on O_APPEND alone it FAILED here (69 of 80 lines survived), because the MSVC CRT implements
    # append as seek-then-write. That is what put the cross-process lock in record(). A barrier makes the
    # collision deterministic rather than hoped-for.
    game = _make_install(tmp_path / "game")
    path = deploylog.ledger_path(game)
    _run_workers(_record_worker, path)
    good, lines = _wellformed(path)
    assert len(lines) == _N_PROCS * _N_LINES, "lines lost or merged"
    assert len(good) == _N_PROCS * _N_LINES, "a record was torn"
    payloads = {(ln.split("\t")[4], ln.split("\t")[5]) for ln in good}
    assert payloads == {(f"proc{k}", str(i)) for k in range(_N_PROCS) for i in range(_N_LINES)}


def test_negative_control_seek_then_write_DOES_corrupt(tmp_path):
    # Without this, the test above proves nothing: it could pass on a harness that never actually
    # interleaves. A non-atomic writer under the same barrier must visibly corrupt the file.
    path = tmp_path / "torn.log"
    path.write_bytes(b"")
    _run_workers(_torn_worker, path)
    good, lines = _wellformed(path)
    assert len(good) < _N_PROCS * _N_LINES, "the negative control did not corrupt -- the positive test is vacuous"


# ---------------------------------------------------------------- reconcile

def test_reconcile_ignores_an_id_that_is_still_registered(tmp_path):
    game = _make_install(tmp_path / "game", folders=("FF9CustomMap", "FF9CustomMap-bb"),
                         registrations={"FF9CustomMap": ["FieldScene 4003 12 TESTROOM TESTROOM 1073"],
                                        "FF9CustomMap-bb": ["FieldScene 30001 12 TEST30001 TEST30001 1073"]})
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    deploylog.record(game, deploylog.DEPLOYED, 30001, "FF9CustomMap-bb")
    rep = deploylog.reconcile(game)
    assert rep.missing == [] and rep.ok
    assert rep.folders == ["FF9CustomMap", "FF9CustomMap-bb"]


def test_reconcile_reports_a_deployed_id_whose_registration_vanished(tmp_path):
    # THE incident: the line is simply gone. The ledger is the only thing that can say who put it there.
    game = _make_install(tmp_path / "game", folders=("FF9CustomMap",),
                         registrations={"FF9CustomMap": ["FieldScene 30001 12 TEST30001 TEST30001 1073"]})
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap",
                     checkout=r"C:\gd\Dream-World-IX\.claude\worktrees\wt-a", note="TESTROOM")
    deploylog.record(game, deploylog.DEPLOYED, 30001, "FF9CustomMap")
    rep = deploylog.reconcile(game)
    assert [e.field_id for e in rep.missing] == [4003]
    lost = rep.missing[0]
    assert lost.checkout.endswith("wt-a")                 # WHICH checkout deployed it
    assert lost.mod_folder == "FF9CustomMap" and lost.when and lost.note == "TESTROOM"
    warn = deploylog.reconcile_warning(rep)
    assert "4003" in warn and "wt-a" in warn and "LOST REGISTRATION" in warn


def test_reconcile_classifies_an_explicitly_retired_id_as_deliberate(tmp_path):
    # The 2026-07-18 hunt in one test: 4003 is absent from DictionaryPatch, but it was RETIRED on purpose.
    # It must NOT read as a loss, and it must still be reportable ("retired at <when> from <checkout>").
    game = _make_install(tmp_path / "game", folders=("FF9CustomMap",), registrations={"FF9CustomMap": []})
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    deploylog.record(game, deploylog.RETIRED, 4003, "FF9CustomMap", note="revert_deploy_4003.py")
    rep = deploylog.reconcile(game)
    assert rep.missing == [] and rep.ok
    assert [e.field_id for e in rep.retired] == [4003]
    assert deploylog.reconcile_warning(rep) is None


def test_reconcile_sees_a_redeploy_after_a_retirement(tmp_path):
    # a deploy RUNS the prior revert as its prelude, so 'retired' then 'deployed' is the ordinary sequence.
    game = _make_install(tmp_path / "game", folders=("FF9CustomMap",), registrations={"FF9CustomMap": []})
    deploylog.record(game, deploylog.RETIRED, 4003, "FF9CustomMap")
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    rep = deploylog.reconcile(game)
    assert [e.field_id for e in rep.missing] == [4003]    # deployed, but nothing registers it -> a loss
    assert rep.retired == []


def test_reconcile_stays_silent_when_the_folder_stack_is_unreadable(tmp_path):
    # no Memoria.ini => we cannot know what is registered; flagging every id ever deployed would be a
    # false alarm on a scale that trains people to ignore the guard.
    game = tmp_path / "game"
    game.mkdir()
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    rep = deploylog.reconcile(game)
    assert rep.missing == [] and rep.folders == []


def test_reconcile_only_counts_folders_in_the_foldernames_stack(tmp_path):
    # a registration in a mod folder Memoria.ini does not load is not loaded by the engine either.
    game = _make_install(tmp_path / "game", folders=("FF9CustomMap",), registrations={"FF9CustomMap": []})
    dead = game / "FF9CustomMap-unlisted"
    dead.mkdir()
    (dead / "DictionaryPatch.txt").write_text("FieldScene 4003 12 TESTROOM TESTROOM 1073\n", encoding="utf-8")
    deploylog.record(game, deploylog.DEPLOYED, 4003, "FF9CustomMap")
    assert [e.field_id for e in deploylog.reconcile(game).missing] == [4003]


# ---------------------------------------------------------------- the generated revert script

def _render_revert_template():
    """Render tools/deploy_field.py's embedded revert template with dummy values.

    Pins the failure mode the ledger wiring could introduce: the generated script imports only a couple of
    ff9mapkit modules, and EVERY ordinary deploy runs the prior revert as its prelude -- so an unresolved
    name in that template does not break one revert, it breaks DEPLOYING. Nothing else in the suite renders
    it, and a syntax/name error there is invisible until a real deploy."""
    src = (pathlib.Path(__file__).resolve().parents[2] / "tools" / "deploy_field.py").read_text(encoding="utf-8")
    body = re.search(r"^revert = f'''(.*?)^'''$", src, re.S | re.M).group(1)
    ns = dict(KIT=r"C:\kit", MOD_FOLDER="FF9CustomMap", STAMP="20260718-013000", BK=r"C:\bk", FID=4003,
              _mint_ids_repr="[]", _mint_anim_keys_repr="[]", _mes_blocks_repr="[]",
              FBG="FBG_N00_TESTROOM", name="TESTROOM",
              text_block=1073, csv_revert_code="", bp_revert_code="", tp_revert_code="",
              fork_revert_code="", _REPO=r"C:\gd\Dream-World-IX")
    return eval("f'''" + body.replace("'''", r"\'\'\'") + "'''", {"__builtins__": {}}, ns)


def test_generated_revert_script_has_no_unresolved_names(tmp_path):
    rendered = _render_revert_template()
    assert "_dlog.record(" in rendered and "import deploylog as _dlog" in rendered
    tree = ast.parse(rendered)                        # syntax
    bound = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, ast.alias):
            bound.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            bound.add(node.name)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    assert used - bound == set(), f"the generated revert would NameError on: {sorted(used - bound)}"


def test_generated_revert_records_a_retirement_for_its_own_id():
    # the tombstone half of the mechanism: a NEWLY generated revert says "this was on purpose". (The ~30
    # legacy scripts on disk say nothing -- reconcile() is what covers them.)
    rendered = _render_revert_template()
    assert '_dlog.record(_GAME, _dlog.RETIRED, 4003, "FF9CustomMap"' in rendered


def test_battlescene_with_the_same_id_does_not_mask_a_lost_fieldscene(tmp_path):
    """`dictionary_ids_at` indexes FieldScene AND BattleScene, and reconcile used to ask only "is this number
    registered anywhere". `deploystack` documents the real collision: `-ate`'s `FieldScene 30011` against
    `-bb`'s `BattleScene 30011`. With the bare-number test, that battle scene stands in for the field: the
    field's registration is genuinely gone (null .eb -> black screen) and the guard reports all clear -- on
    exactly the failure it exists to catch. A row is satisfied only by a FieldScene."""
    game = tmp_path / "game"
    for folder in ("FF9CustomMap-ate", "FF9CustomMap-bb"):
        (game / folder).mkdir(parents=True)
    (game / "FF9CustomMap-ate" / "DictionaryPatch.txt").write_text("", encoding="utf-8")
    (game / "FF9CustomMap-bb" / "DictionaryPatch.txt").write_text(
        "BattleScene 30011 CAMKEYS BBG_B001\n", encoding="utf-8")
    order = ["FF9CustomMap-ate", "FF9CustomMap-bb"]
    deploylog.record(game, deploylog.DEPLOYED, 30011, "FF9CustomMap-ate", checkout="wt-ate")
    report = deploylog.reconcile(game, folder_names=order)
    assert [e.field_id for e in report.missing] == [30011]
    assert "30011" in deploylog.reconcile_warning(report)
    # ...and a real FieldScene registration in either folder still clears it (no new false alarm)
    (game / "FF9CustomMap-ate" / "DictionaryPatch.txt").write_text(
        "FieldScene 30011 11 10 ATEROOM 1073\n", encoding="utf-8")
    assert deploylog.reconcile(game, folder_names=order).missing == []


def test_registrations_keeps_both_kinds_of_a_colliding_id(tmp_path):
    """The mapping reconcile judges on. An id registered under BOTH directives keeps both entries: collapsing
    to a single last-writer-wins winner would either mask a lost FieldScene (battle scene later in the stack)
    or invent one (battle scene earlier). Within a kind, the last folder wins, matching the engine."""
    game = tmp_path / "game"
    for folder in ("A", "B", "C"):
        (game / folder).mkdir(parents=True)
    (game / "A" / "DictionaryPatch.txt").write_text(
        "FieldScene 4003 11 10 TESTROOM 1073\nFieldScene 30110 11 10 TWINALTAR 1080\n", encoding="utf-8")
    (game / "B" / "DictionaryPatch.txt").write_text(
        "BattleScene 30110 CAMKEYS BBG_B001\n", encoding="utf-8")
    (game / "C" / "DictionaryPatch.txt").write_text(
        "FieldScene 4003 11 10 OVERRIDE 1073\n", encoding="utf-8")
    reg, folders = deploylog.registrations(game, folder_names=["A", "B", "C"])
    assert folders == ["A", "B", "C"]
    assert reg[4003] == {"FieldScene": "C"}                            # later folder wins within the kind
    assert reg[30110] == {"FieldScene": "A", "BattleScene": "B"}       # both kinds survive
