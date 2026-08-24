"""The M8 FOLDER lock: wholesale installs and field RMWs into one mod folder serialise.

The gap M7 left open: the per-file sidecar locks serialise two read->merge->write pairs on ONE file, but
a WHOLESALE installer (deploy-campaign / deploy-journey / the hub overlay: snapshot -> rmtree -> copytree)
cannot use them -- rmtree would have to delete the very lockfile a concurrent field deploy holds open, and
on Windows an open fd inside the tree makes the rmtree itself fail partway. So a concurrent
``tools/deploy_field.py`` RMW into the same folder could land its LOCKED rewrite between snapshot and
rmtree and be silently destroyed -- invisible to the wiped-regs guard, which compares snapshot-time state.

``fsutil.locked_mod_folder`` closes that: one ``<folder>.ff9lock`` OUTSIDE the folder (beside
``Memoria.ini``), taken by the wholesale paths around snapshot->replace and by the RMW writers around
their WHOLE live-mutation section, folder THEN sidecar. This file proves it three ways, following the
house pattern (test_fsutil + test_patchfile_locks): unit tests of the primitive, a barrier-synchronised
TWO-PROCESS test (a field RMW vs a wholesale replace, plus a deliberately unlocked negative control that
measurably loses the write -- without which the positive test proves nothing), and AST pins that every
enumerated writer actually SPENDS the lock (a law in a docstring is a wish).
"""
from __future__ import annotations

import ast
import multiprocessing as mp
import os
import pathlib
import shutil
import time

import pytest

from ff9mapkit import fsutil

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PKG = pathlib.Path(__file__).resolve().parents[1] / "ff9mapkit"
_FIELD_SRC = (_ROOT / "tools" / "deploy_field.py").read_text(encoding="utf-8")
_BATTLE_SRC = (_ROOT / "tools" / "deploy_battle.py").read_text(encoding="utf-8")
_DEPLOY_SRC = (_PKG / "deploy.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------- the primitive

def test_lockfile_lives_outside_the_folder_and_the_folder_is_untouched(tmp_path):
    root = tmp_path / "FF9CustomMap"
    root.mkdir()
    (root / "DictionaryPatch.txt").write_text("FieldScene 4003 11 10 T 1073\n", encoding="utf-8")
    with fsutil.locked_mod_folder(root):
        pass
    # BESIDE the folder (the game root, next to Memoria.ini), never inside it -- a wholesale rmtree of the
    # folder must not delete the lock its holder owns, and an fd inside the tree would fail the rmtree.
    assert (tmp_path / "FF9CustomMap.ff9lock").exists()
    assert not (root / "FF9CustomMap.ff9lock").exists()
    assert sorted(p.name for p in root.iterdir()) == ["DictionaryPatch.txt"]


def test_lock_works_when_the_folder_does_not_exist(tmp_path):
    # a generated revert may run after a campaign install wiped the folder; only the PARENT must exist.
    with fsutil.locked_mod_folder(tmp_path / "FF9CustomMap-gone"):
        pass
    assert (tmp_path / "FF9CustomMap-gone.ff9lock").exists()


def test_the_holder_can_rmtree_the_folder_it_guards(tmp_path):
    # THE design point: a wholesale replace holds the lock ACROSS its own snapshot -> rmtree -> copytree.
    root = tmp_path / "FF9CustomMap"
    root.mkdir()
    (root / "DictionaryPatch.txt").write_text("x\n", encoding="utf-8")
    with fsutil.locked_mod_folder(root):
        shutil.rmtree(root)
        assert not root.exists()
        root.mkdir()
    assert (tmp_path / "FF9CustomMap.ff9lock").exists()


def test_a_held_lock_times_out_loudly_and_names_the_lockfile(tmp_path):
    root = tmp_path / "FF9CustomMap"
    with fsutil.locked_mod_folder(root):
        with pytest.raises(fsutil.FileLockTimeout) as ei:
            with fsutil.locked_mod_folder(root, timeout=0.2):
                raise AssertionError("acquired a lock another holder owns")
    assert "FF9CustomMap.ff9lock" in str(ei.value)
    with fsutil.locked_mod_folder(root, timeout=0.2):     # reacquirable once released -- nothing wedged
        pass


def test_no_lock_modules_degrades_to_unlocked_not_fatal(tmp_path, monkeypatch):
    # the M7 exotic-platform contract carries over: neither fcntl nor msvcrt -> a no-op, never a crash.
    monkeypatch.setattr(fsutil, "fcntl", None)
    monkeypatch.setattr(fsutil, "msvcrt", None)
    with fsutil.locked_mod_folder(tmp_path / "FF9CustomMap"):
        pass


def test_folder_deadline_clears_the_slow_normal_case():
    # a folder critical section is a whole-folder copytree x2 (or a deploy incl. a C# recompile), not the
    # sidecar's few ms -- a deadline at or below the sidecar's would false-abort real installs.
    assert fsutil.FOLDER_LOCK_TIMEOUT > fsutil.LOCK_TIMEOUT


# ------------------------------- two processes: a field RMW vs a wholesale replace

_ROUNDS = 8
_SEED = "FieldScene 4003 11 10 FOREIGN 1073"


def _locked_field_rmw(root, barrier, rounds):
    """The deploy_field shape post-M8: the FOLDER lock around the whole live mutation, the sidecar inside
    it (lock order folder THEN sidecar), then the usual locked read->merge->atomic-write."""
    root = pathlib.Path(root)
    dp = root / "DictionaryPatch.txt"
    for i in range(rounds):
        barrier.wait()                                    # both processes enter the window together
        with fsutil.locked_mod_folder(root):
            root.mkdir(exist_ok=True)                     # the bootstrap, mirrored
            with fsutil.locked_sidecar(dp):
                lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
                lines.append(f"FieldScene 30000 11 10 FIELD_{i} 1073")
                fsutil.atomic_write_text(dp, "\n".join(lines) + "\n", newline="\n")


def _locked_wholesale(root, snaps, barrier, rounds):
    """The deploy_campaign shape post-M8: snapshot -> rmtree -> copytree under the FOLDER lock. The dist
    here is the snapshot itself (a re-install), so under correct serialisation NOTHING is ever lost: a
    concurrent field line either predates the snapshot (carried through the replace) or lands after it."""
    root = pathlib.Path(root)
    for i in range(rounds):
        barrier.wait()
        snap = pathlib.Path(snaps) / f"snap{i}"
        with fsutil.locked_mod_folder(root):
            shutil.copytree(root, snap)                   # (3) snapshot
            shutil.rmtree(root)                           # (4) the window a foreign RMW used to vanish into
            shutil.copytree(snap, root)
            dp = root / "DictionaryPatch.txt"
            lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
            lines.append(f"FieldScene 30001 11 10 WHOLESALE_{i} 1073")
            fsutil.atomic_write_text(dp, "\n".join(lines) + "\n", newline="\n")


def _unlocked_field_rmw(root, barrier, rounds):
    """The NEGATIVE CONTROL's field side: the pre-M8 shape -- read, dwell, atomic replace, NO folder lock.
    The dwell parks the write inside the wholesale worker's snapshot->replace window. Windows sharp edges
    are sanded off as in test_fsutil's control (per-round staging name outside the folder; retry loops for
    a target folder that is momentarily deleted mid-replace) so the control isolates the PURE
    snapshot-window loss -- the extra failure modes are all things the folder lock also prevents."""
    root = pathlib.Path(root)
    dp = root / "DictionaryPatch.txt"
    for i in range(rounds):
        barrier.wait()
        while True:
            try:
                lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
                break
            except OSError:                               # the file is mid-replace by the other process
                time.sleep(0.001)
        time.sleep(0.02)                                  # land inside the snapshot->replace window
        lines.append(f"FieldScene 30000 11 10 FIELD_{i} 1073")
        tmp = root.parent / f"stage.{i}.tmp"              # OUTSIDE the folder -- survives the rmtree
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        deadline = time.monotonic() + 60
        while True:
            try:
                os.replace(tmp, dp)
                break
            except OSError:                               # the folder itself is momentarily gone/replaced
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.001)


def _unlocked_wholesale(root, snaps, barrier, rounds):
    """The NEGATIVE CONTROL's wholesale side: snapshot, dwell, rmtree, restore -- NO folder lock. Any
    field write that landed after the snapshot is erased by the restore; the retry loops absorb the
    transient OSErrors two unserialised processes inflict on each other."""
    root = pathlib.Path(root)
    for i in range(rounds):
        barrier.wait()
        snap = pathlib.Path(snaps) / f"snap{i}"
        while True:
            try:
                shutil.copytree(root, snap)               # snapshot
                break
            except OSError:                               # a file inside is mid-replace
                shutil.rmtree(snap, ignore_errors=True)
                time.sleep(0.001)
        time.sleep(0.05)                                  # the snapshot->replace window
        while root.exists():
            shutil.rmtree(root, ignore_errors=True)       # rmtree
            if root.exists():
                time.sleep(0.001)
        while True:
            try:
                shutil.copytree(snap, root)               # replace -- erasing anything since the snapshot
                break
            except OSError:
                shutil.rmtree(root, ignore_errors=True)
                time.sleep(0.001)


def _run_pair(field_worker, wholesale_worker, tmp_path):
    root = tmp_path / "FF9CustomMap"
    root.mkdir()
    (root / "DictionaryPatch.txt").write_text(_SEED + "\n", encoding="utf-8")
    snaps = tmp_path / "snaps"
    snaps.mkdir()
    barrier = mp.Barrier(2)
    procs = [mp.Process(target=field_worker, args=(str(root), barrier, _ROUNDS), daemon=True),
             mp.Process(target=wholesale_worker, args=(str(root), str(snaps), barrier, _ROUNDS), daemon=True)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(120)
    try:
        assert all(p.exitcode == 0 for p in procs), [p.exitcode for p in procs]
    finally:
        for p in procs:                                   # a barrier-stuck straggler would outlive join(120)
            if p.is_alive():
                p.terminate()
    return root


def test_a_field_rmw_and_a_wholesale_replace_serialize(tmp_path):
    """The deliverable: with both sides holding the folder lock, EVERY line survives -- the seed, every
    field-RMW line, every wholesale marker -- and none is torn. The field write can no longer land inside
    the snapshot->rmtree window, because that whole window excludes it."""
    root = _run_pair(_locked_field_rmw, _locked_wholesale, tmp_path)
    lines = [ln for ln in (root / "DictionaryPatch.txt").read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    assert _SEED in lines, "the foreign seed line was dropped"
    payloads = {ln.split()[4] for ln in lines if ln != _SEED}
    assert payloads == ({f"FIELD_{i}" for i in range(_ROUNDS)}
                        | {f"WHOLESALE_{i}" for i in range(_ROUNDS)}), \
        f"a write was silently destroyed: {sorted(payloads)}"
    assert all(len(ln.split()) == 6 and ln.startswith("FieldScene ") for ln in lines), "a line was torn"
    assert (tmp_path / "FF9CustomMap.ff9lock").exists()   # the lock lived OUTSIDE and survived every rmtree


def test_negative_control_unlocked_pair_DOES_lose_the_write(tmp_path):
    """Without this, the test above proves nothing -- it could pass on a harness that never interleaves.
    The same pair WITHOUT the folder lock must measurably lose field writes to the snapshot->replace
    window: that IS the pre-M8 deploy loop, and the loss is the silent kind the wiped-regs guard cannot
    see (it compares snapshot-time state, and the write postdates the snapshot)."""
    root = _run_pair(_unlocked_field_rmw, _unlocked_wholesale, tmp_path)
    lines = [ln for ln in (root / "DictionaryPatch.txt").read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    field_lines = {ln.split()[4] for ln in lines if ln.split()[4].startswith("FIELD_")}
    assert len(field_lines) < _ROUNDS, \
        "the negative control lost nothing -- the positive test is vacuous"


# ---------------------------------------------------------------- AST pins: the writers spend the lock

def _enter_context_calls(tree):
    """Every ``<stack>.enter_context(locked_mod_folder(...))`` call node under ``tree``."""
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "enter_context" and n.args and isinstance(n.args[0], ast.Call)
            and isinstance(n.args[0].func, ast.Name) and n.args[0].func.id == "locked_mod_folder"]


def _folder_lock_withs(node):
    """Every ``with <x>.locked_mod_folder(...)`` / ``with locked_mod_folder(...)`` block under ``node``."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.With):
            for i in n.items:
                c = i.context_expr
                if (isinstance(c, ast.Call)
                        and ((isinstance(c.func, ast.Name) and c.func.id == "locked_mod_folder")
                             or (isinstance(c.func, ast.Attribute) and c.func.attr == "locked_mod_folder"))):
                    out.append(n)
    return out


def _call_lines(tree, *, name=None, attr=None):
    return [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
            and ((name is not None and isinstance(n.func, ast.Name) and n.func.id == name)
                 or (attr is not None and isinstance(n.func, ast.Attribute) and n.func.attr == attr))]


@pytest.mark.parametrize("src", [_FIELD_SRC, _BATTLE_SRC], ids=["deploy_field", "deploy_battle"])
def test_deploy_scripts_hold_the_folder_lock_across_the_whole_mutation_section(src):
    """The scripts enter the folder lock ONCE (an ExitStack -- the section is hundreds of lines of flat
    top-level script), BEFORE the first live mutation (the folder bootstrap mkdir), release it AFTER the
    last locked patch-file write, and abort loudly on a FileLockTimeout at acquisition -- proceeding
    unlocked is the one wrong answer. The sidecar locks stay INSIDE the section: folder THEN sidecar."""
    tree = ast.parse(src)
    enters = _enter_context_calls(tree)
    assert len(enters) == 1, "exactly one folder-lock acquisition per deploy script"
    enter_ln = enters[0].lineno
    mkdir_lns = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "mkdir"
                 and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == "root"] or \
                [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "mkdir"
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == "live_root"]
    assert mkdir_lns and enter_ln < min(mkdir_lns), \
        "the folder lock must be held BEFORE the live folder bootstrap (the first mutation)"
    sidecar_lns = _call_lines(tree, name="locked_sidecar")
    assert sidecar_lns and enter_ln < min(sidecar_lns), "folder THEN sidecar -- never the reverse"
    closes = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "close"
              and isinstance(n.func.value, ast.Name) and n.func.value.id == "_folder_lock"]
    assert len(closes) == 1, "exactly one release of the folder lock"
    writes = _call_lines(tree, name="atomic_write_text")
    assert writes and closes[0] > max(writes), \
        "the folder lock must be released only AFTER the last locked patch-file write"
    # the acquisition's FileLockTimeout handler exits loudly (same M7 semantics as the sidecar aborts)
    handled = False
    for t in ast.walk(tree):
        if isinstance(t, ast.Try) and any(x is enters[0] for x in ast.walk(t)):
            for h in t.handlers:
                if isinstance(h.type, ast.Name) and h.type.id == "FileLockTimeout":
                    handled = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                                  and c.func.attr == "exit" for c in ast.walk(h))
    assert handled, "a folder-lock timeout must abort the deploy loudly, never proceed unlocked"


@pytest.mark.parametrize("func, wants_handler", [
    ("deploy_campaign", True),
    ("deploy_field", True),
    ("_install_hub", False),        # its FileLockTimeout PROPAGATES into the journey's loud _abort
    ("_apply_journey_single", True),
], ids=["campaign", "field", "hub-overlay", "journey-single"])
def test_wholesale_paths_hold_the_folder_lock_around_snapshot_and_replace(func, wants_handler):
    """Every wholesale install in ff9mapkit.deploy runs its snapshot AND its rmtree+copytree replace
    inside ONE `with fsutil.locked_mod_folder(...)` block -- a snapshot outside the lock re-opens the
    exact window this lock exists to close (the guard compares snapshot-time state)."""
    tree = ast.parse(_DEPLOY_SRC)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func)
    withs = _folder_lock_withs(fn)
    assert len(withs) == 1, f"{func} must hold exactly one folder-lock block"
    w = withs[0]
    for verb in ("copytree", "rmtree"):
        allc = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == verb]
        assert allc, f"{func}: expected at least one shutil.{verb}"
        assert all(any(x is c for x in ast.walk(w)) for c in allc), \
            f"{func}: a shutil.{verb} escaped the folder lock -- the snapshot->replace window is back"
    if wants_handler:
        handlers = [h for t in ast.walk(fn) if isinstance(t, ast.Try)
                    and any(x is w for x in ast.walk(t))
                    for h in t.handlers if isinstance(h.type, ast.Attribute)
                    and h.type.attr == "FileLockTimeout"]
        assert handlers and all(any(isinstance(r, ast.Return) for r in ast.walk(h)) for h in handlers), \
            f"{func}: a folder-lock timeout must abort loudly (return the failed report), never proceed"


@pytest.mark.parametrize("rel, func", [
    ("models/mint.py", "deploy_mint"),
    ("models/anim.py", "deploy_new_anim"),
], ids=["model-mint", "model-anim-new"])
def test_package_dictionary_writers_take_the_folder_lock_outside_the_sidecar(rel, func):
    """`model-mint --deploy` / `model-anim-new` write a staged tree AND a registration line straight into
    a live folder -- the folder lock spans BOTH (a registered line whose staged file was rmtree'd away is
    as lost as the line itself), with the sidecar nested inside (the lock ORDER law)."""
    tree = ast.parse((_PKG / rel).read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func)
    withs = _folder_lock_withs(fn)
    assert len(withs) == 1, f"{func} must hold exactly one folder-lock block"
    w = withs[0]
    sidecars = [n for n in ast.walk(w) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == "locked_sidecar"]
    assert sidecars, f"{func}: the sidecar lock must nest INSIDE the folder lock (folder THEN sidecar)"
    writes = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr in ("atomic_write_text", "write_text", "write_bytes")]
    assert writes and all(any(x is c for x in ast.walk(w)) for c in writes), \
        f"{func}: a live write escaped the folder lock"


# ---------------------------------------------------------------- the generated reverts

def test_generated_field_revert_takes_the_folder_lock_before_any_mutation():
    """revert_deploy_<id>.py runs as every redeploy's PRELUDE -- the highest-frequency live mutator of
    all. It must hold the folder lock across its whole mutation (folder THEN sidecar; ExitStack so the
    column-0 revert fragments splice unchanged) and release it before the ledger record, which lives
    outside the folder. A timeout PROPAGATES: the traceback fails the revert, and the prelude's checked
    exit code turns that into a loud deploy abort."""
    from ff9mapkit.reverttmpl import build_revert_script
    src = build_revert_script(kit="k", backup_dir="b", stamp="s", mod_folder="M", fid=4003, name="T",
                              fbg="F", text_block=4003, repo="r")
    compile(src, "<revert>", "exec")
    i_enter = src.index("enter_context(locked_mod_folder(live.root))")
    assert i_enter < src.index("with locked_sidecar("), "folder THEN sidecar"
    assert i_enter < src.index("live.dictionary_patch.parent.mkdir"), "lock before the first mutation"
    i_close = src.index("_folder_lock.close()")
    assert src.index("with locked_sidecar(") < i_close < src.index("_dlog.record"), \
        "release after the last live-folder write, before the (outside-the-folder) ledger record"


def test_generated_battle_revert_takes_the_folder_lock_and_still_compiles():
    """revert_battle_<BBG>.py is assembled by string concatenation in tools/deploy_battle.py -- evaluate
    the REAL write_text argument out of the script's AST (with the deploy-time names bound, both with and
    without a spliced BattlePatch fragment) and require: it compiles, the folder lock is entered before
    the CREATED/OVERWRITTEN mutations, and it closes after the fragment splice point."""
    tree = ast.parse(_BATTLE_SRC)
    args = [n.args[0] for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "write_text"
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "revert"]
    assert len(args) == 1, "exactly one revert.write_text in tools/deploy_battle.py"
    code = compile(ast.Expression(ast.fix_missing_locations(args[0])), "<revtext>", "eval")
    frag = ('\nfrom ff9mapkit.battle import battlepatch as _bpm'
            '\nfrom ff9mapkit.fsutil import atomic_write_text as _awt, locked_sidecar as _lsc'
            '\n_bpb = Path(r"bk")'
            '\n_bpl = LIVE/"BattlePatch.txt"'
            '\n_bpl.parent.mkdir(parents=True, exist_ok=True)'
            '\nwith _lsc(_bpl):'
            '\n    _bpn = ""'
            '\n    if _bpn: _awt(_bpl, _bpn, newline="\\n")')
    for bp in ("", frag):
        env = {"KIT": "k", "live_root": pathlib.Path("L"), "bk_dir": pathlib.Path("B"),
               "created": ["a"], "overwritten": ["b"], "bp_revert_code": bp,
               "BBG": "BBG_TEST", "BK": pathlib.Path("bk"), "STAMP": "s"}
        src = eval(code, env)  # noqa: S307 -- evaluating our own source's literal
        compile(src, "<battle-revert>", "exec")
        i_enter = src.index("_fl.enter_context(locked_mod_folder(LIVE))")
        assert i_enter < src.index("for rel in CREATED:"), "lock before the first mutation"
        assert src.index("if b.exists()") < src.index("_fl.close()"), "release after the last mutation"
