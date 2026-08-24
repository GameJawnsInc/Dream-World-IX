"""Every read->merge->write into a live per-folder patch file holds the fsutil sidecar lock.

The lost-update class: 18+ concurrent sessions share ONE game install, and two writers interleaving a
read->merge->write window on the same file silently drop whichever lines/blocks the other read past --
atomic_write_text makes each rewrite all-or-nothing but serialises nothing, and the non-clobbering splices
(BattlePatch / TextPatch / ForkDonorPatch) are non-clobbering only against what they READ. The lock itself
is proven by test_fsutil's barrier concurrency test, and test_deploy_field_script pins the DictionaryPatch
rewrite specifically; this file pins the REST of the matrix by AST (the deploy scripts cannot be imported
-- they deploy on import -- and a law in a docstring is a wish):

  * the per-target splice locks in tools/deploy_field.py + tools/deploy_battle.py (BattlePatch, TextPatch,
    ForkDonorPatch, the MusicMetaData merge) and their FileLockTimeout loud-abort handlers,
  * the generated revert fragments' surgical counterparts (revert_splice / revert_row under `_lsc`),
  * the package's direct live-DictionaryPatch writers (models.mint.deploy_mint, models.anim.deploy_new_anim
    -- the `model-anim-new` clip line whose loss WAS the vanished key 60001),
  * the legacy one-off tools that rewrite a live DictionaryPatch (install_tworoom + the scroll spikes).
"""
from __future__ import annotations

import ast
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PKG = pathlib.Path(__file__).resolve().parents[1] / "ff9mapkit"

_FIELD_SRC = (_ROOT / "tools" / "deploy_field.py").read_text(encoding="utf-8")
_BATTLE_SRC = (_ROOT / "tools" / "deploy_battle.py").read_text(encoding="utf-8")


def _locked_withs(tree, lock_names=("locked_sidecar",)):
    """[(with_node, target_arg_node)] for every ``with <lock>(target)`` under ``tree`` -- the lock callable
    may be a bare name (``locked_sidecar``, a fragment's ``_lsc`` alias) or an attribute (``fsutil.locked_sidecar``)."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.With):
            for i in n.items:
                c = i.context_expr
                if (isinstance(c, ast.Call) and c.args
                        and ((isinstance(c.func, ast.Name) and c.func.id in lock_names)
                             or (isinstance(c.func, ast.Attribute) and c.func.attr in lock_names))):
                    out.append((n, c.args[0]))
    return out


def _key(expr):
    """A lock target / write target expression's identity: ``live.battle_patch`` -> 'battle_patch',
    ``_fdp`` -> '_fdp'."""
    if isinstance(expr, ast.Attribute):
        return expr.attr
    if isinstance(expr, ast.Name):
        return expr.id
    return None


def _calls(node, *, name=None, attr=None):
    """Call nodes under ``node`` by bare-name (``atomic_write_text``) or attribute (``x.merge_row``)."""
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)
            and ((name is not None and isinstance(n.func, ast.Name) and n.func.id == name)
                 or (attr is not None and isinstance(n.func, ast.Attribute) and n.func.attr == attr))]


def _handler_aborts(tree, w):
    """True iff ``w`` sits inside a Try whose FileLockTimeout handler exits or raises -- the loud abort.
    Proceeding unlocked is the one wrong answer, and an uncaught timeout in a top-level script is a raw
    traceback where a deploy needs a message that says whose lock and what to do."""
    for t in ast.walk(tree):
        if isinstance(t, ast.Try) and any(x is w for x in ast.walk(t)):
            for h in t.handlers:
                if isinstance(h.type, ast.Name) and h.type.id == "FileLockTimeout":
                    if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                           and c.func.attr == "exit" for c in ast.walk(h)) \
                            or any(isinstance(r, ast.Raise) for r in ast.walk(h)):
                        return True
    return False


# ---------------------------------------------------------------- the two deploy scripts

@pytest.mark.parametrize("src, expected_targets", [
    (_FIELD_SRC, {"dictionary_patch", "battle_patch", "text_patch", "_fdp", "_live_manifest"}),
    (_BATTLE_SRC, {"dictionary_patch", "battle_patch"}),
], ids=["deploy_field", "deploy_battle"])
def test_every_patch_rewrite_holds_its_own_target_lock(src, expected_targets):
    """One lock per TARGET FILE: DictionaryPatch writers share DictionaryPatch.txt.lock, the BattlePatch
    splice holds BattlePatch.txt.lock, and so on -- a write under the WRONG file's lock serialises nothing.
    Pin: the expected lock set exists, every atomic_write_text lands inside the lock on its own target,
    and every locked block aborts loudly on FileLockTimeout."""
    tree = ast.parse(src)
    locked = {_key(a): w for w, a in _locked_withs(tree)}
    assert set(locked) == expected_targets, f"lock targets drifted: {sorted(locked)}"
    for wr in _calls(tree, name="atomic_write_text"):
        k = _key(wr.args[0])
        assert k in locked, f"atomic_write_text({k}) has no lock for its target"
        assert any(x is wr for x in ast.walk(locked[k])), \
            f"the {k} rewrite sits OUTSIDE its locked_sidecar block -- the lost-update window is back"
    for k, w in locked.items():
        assert _handler_aborts(tree, w), f"the {k} lock has no FileLockTimeout loud-abort handler"


def test_deploy_field_splice_merges_run_inside_their_locks():
    """The merge must read the text the SAME critical section wrote from -- a merge computed outside the
    lock (even if the write moved inside) still merges a stale read. Pin each splice's merge helper AND its
    has_block trigger read to its own lock block."""
    tree = ast.parse(_FIELD_SRC)
    locked = {_key(a): w for w, a in _locked_withs(tree)}
    for target, merge in (("battle_patch", "merge_battle_patch"), ("text_patch", "merge_text_patch"),
                          ("_fdp", "merge_row")):
        inside = _calls(locked[target], attr=merge)
        assert len(inside) == 1, f"{merge} must run INSIDE the {target} lock"
        assert len(_calls(tree, attr=merge)) == 1, f"a second {merge} call exists outside the {target} lock"
    # the has_block triggers decide WHETHER to splice from the live text -- deciding on a stale read
    # reopens the window, so both sit inside their locks too.
    for target in ("battle_patch", "text_patch"):
        assert _calls(locked[target], attr="has_block"), f"the {target} has_block trigger read left its lock"


def test_deploy_battle_splice_merge_runs_inside_its_lock():
    tree = ast.parse(_BATTLE_SRC)
    locked = {_key(a): w for w, a in _locked_withs(tree)}
    assert len(_calls(locked["battle_patch"], attr="merge_battle_patch")) == 1
    assert len(_calls(tree, attr="merge_battle_patch")) == 1
    assert _calls(locked["battle_patch"], attr="has_block")


# ---------------------------------------------------------------- the generated revert fragments

def _fragment(src, name, env):
    """Evaluate the LAST non-empty assignment to ``name`` in ``src`` (the real fragment expression, as
    test_deploy_field_script's compile test does) with the deploy-time names in ``env`` bound."""
    tree = ast.parse(src)
    exprs = [n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
             for t in n.targets if isinstance(t, ast.Name) and t.id == name]
    real = [e for e in exprs if not (isinstance(e, ast.Constant) and e.value == "")]
    assert real, f"no fragment expression found for {name}"
    code = compile(ast.Expression(ast.fix_missing_locations(real[-1])), "<frag>", "eval")
    return eval(code, dict(env))  # noqa: S307 -- evaluating our own source's literal


@pytest.mark.parametrize("src, name, env, revert_call", [
    (_FIELD_SRC, "bp_revert_code", {"FID": 4003}, "revert_splice"),
    (_FIELD_SRC, "tp_revert_code", {"FID": 4003}, "revert_splice"),
    (_FIELD_SRC, "fork_revert_code", {"FID": 4003}, "revert_row"),
    (_BATTLE_SRC, "bp_revert_code",
     {"BK": pathlib.Path("bk"), "STAMP": "s", "_bp_owner": "b1"}, "revert_splice"),
], ids=["field-bp", "field-tp", "field-fork", "battle-bp"])
def test_generated_revert_fragments_hold_the_lock(src, name, env, revert_call):
    """The fragments run inside generated revert scripts -- which a deploy runs as its PRELUDE, so at any
    instant some session's revert may be rewriting a patch file another session's deploy is mid-splice on.
    Pin: each fragment's surgical revert (the read, the revert_splice/revert_row merge, the _awt write, the
    empty-file unlink) sits inside `with _lsc(<target>)`. A timeout PROPAGATES by design: the traceback
    fails the revert, and the deploy prelude's checked exit code turns that into a loud abort."""
    frag = _fragment(src, name, env)
    tree = ast.parse(frag)
    locked = _locked_withs(tree, lock_names=("_lsc",))
    assert len(locked) == 1, f"{name}: exactly one _lsc lock block"
    w = locked[0][0]
    assert len(_calls(w, attr=revert_call)) == 1, f"{name}: the surgical {revert_call} must run inside the lock"
    awts = _calls(tree, name="_awt")
    assert awts and all(any(x is c for x in ast.walk(w)) for c in awts), \
        f"{name}: the _awt write must sit inside the lock"
    unlinks = _calls(tree, attr="unlink")
    assert all(any(x is c for x in ast.walk(w)) for c in unlinks), \
        f"{name}: the empty-file unlink is a write too -- inside the lock"


# ---------------------------------------------------------------- the package's direct writers

@pytest.mark.parametrize("rel, func, extra_inside", [
    ("models/mint.py", "deploy_mint", ()),
    # the free-key SCAN reads the same registry the write extends -- outside one lock, two concurrent
    # mints allocate the same key, so the allocation must share the critical section.
    ("models/anim.py", "deploy_new_anim", ("_anim_key_registry",)),
], ids=["model-mint", "model-anim-new"])
def test_package_dictionary_writers_hold_the_lock(rel, func, extra_inside):
    """`ff9mapkit model-mint --deploy` and `model-anim-new` write registration lines STRAIGHT into a live
    folder's DictionaryPatch between deploys -- the exact foreign-line class the deploy scripts' guards
    exist to protect (the vanished key 60001 was a model-anim-new line lost to an unlocked window)."""
    tree = ast.parse((_PKG / rel).read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func)
    locked = [(w, a) for w, a in _locked_withs(fn) if _key(a) == "dp"]
    assert len(locked) == 1, f"{func} must hold exactly one locked_sidecar(dp) block"
    w = locked[0][0]
    assert _calls(w, attr="read_text"), f"{func}: the registry read must sit inside the lock"
    writes = _calls(fn, attr="atomic_write_text") + _calls(fn, name="atomic_write_text")
    assert writes and all(any(x is c for x in ast.walk(w)) for c in writes), \
        f"{func}: the DictionaryPatch rewrite must sit inside the lock"
    for helper in extra_inside:
        assert _calls(w, name=helper), f"{func}: {helper} (the free-key scan) must sit inside the lock"


# ---------------------------------------------------------------- the legacy one-off tools

@pytest.mark.parametrize("tool, write_name", [
    ("install_tworoom.py", "atomic_write_bytes"),      # wholesale replace -- locked + atomic, byte-verbatim
    ("deploy_scroll_demo.py", "atomic_write_text"),
    ("deploy_user_scroll.py", "atomic_write_text"),
    ("build_scroll_test.py", "atomic_write_text"),
])
def test_legacy_tools_lock_their_dictionary_rewrite(tool, write_name):
    """The one-off spikes write the SAME live DictionaryPatch the deploy loop owns; an unlocked (or
    non-atomic) rewrite there re-opens the lost-line window for every concurrent session -- and a torn
    plain write_text/copyfile unregisters the whole folder at the next launch."""
    src = (_ROOT / "tools" / tool).read_text(encoding="utf-8")
    tree = ast.parse(src)
    locked = [(w, a) for w, a in _locked_withs(tree) if _key(a) == "dictionary_patch"]
    assert len(locked) == 1, f"{tool}: exactly one locked_sidecar block on the live DictionaryPatch"
    w = locked[0][0]
    writes = [c for c in _calls(tree, name=write_name)
              if _key(c.args[0]) == "dictionary_patch"]
    assert writes and all(any(x is c for x in ast.walk(w)) for c in writes), \
        f"{tool}: the DictionaryPatch rewrite must sit inside the lock"
    assert _handler_aborts(tree, w), f"{tool}: no FileLockTimeout loud-abort handler"
    # the unlocked forms must not come back (the revert-script STRING literals inside these tools still
    # mention the path -- but as constants, which produce no Call nodes, so this stays call-level).
    assert not [c for c in _calls(tree, attr="write_text")
                if isinstance(c.func.value, ast.Attribute) and c.func.value.attr == "dictionary_patch"], \
        f"{tool}: a bare dictionary_patch.write_text is back"
    assert not [c for c in _calls(tree, attr="copyfile")
                if len(c.args) == 2 and _key(c.args[1]) == "dictionary_patch"], \
        f"{tool}: an unlocked copyfile ONTO the live DictionaryPatch is back"
