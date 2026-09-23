"""Security + robustness: ff9mapkit.reverttmpl.build_revert_script injects every DATA value as a repr()
literal, so an odd or hostile character in a path / name / mod-folder can never break -- let alone inject
code into -- the generated revert script (which a subsequent deploy RUNS as its prelude, against the live
install). Self-contained; no template cache needed.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from ff9mapkit.reverttmpl import build_revert_script

BENIGN = dict(kit=r"C:\kit", backup_dir=r"C:\bk", stamp="20260724-120000", mod_folder="FF9CustomMap",
              fid=4003, name="TESTROOM", fbg="FBG_N4003_TESTROOM", text_block=4003, repo=r"C:\repo")

# Fields that carry arbitrary path/name text into the generated script -- each must be inert as code.
DATA_FIELDS = ["kit", "backup_dir", "stamp", "mod_folder", "name", "fbg", "repo"]

# Strings that would break a naive quoted/raw interpolation, plus an outright code-injection attempt.
PAYLOADS = [
    'a"b',                                   # a double quote -> would close a "..." literal
    "a'b",                                   # a single quote
    r"C:\end\\",                             # trailing backslashes -> would escape a raw-string's closing quote
    "line1\nimport os\nos.system('calc')",   # a newline + code -> would become top-level statements
    '"); __import__("os").system("calc"); ("',  # the classic break-out-and-run payload
]


def _compiles(src: str) -> None:
    compile(src, "<revert>", "exec")         # raises SyntaxError if the generation produced broken Python


def _node_count(src: str) -> int:
    return sum(1 for _ in ast.walk(ast.parse(src)))


def _string_constants(src: str) -> set[str]:
    return {n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def test_benign_script_is_valid_python_and_names_the_deploy():
    src = build_revert_script(**BENIGN)
    _compiles(src)
    consts = _string_constants(src)
    assert "FF9CustomMap" in consts and "FBG_N4003_TESTROOM" in consts
    assert "find_game_path" in src and "_dlog.record" in src   # the load-bearing skeleton is intact


_BENIGN_NODES = _node_count(build_revert_script(**BENIGN))


@pytest.mark.parametrize("field", DATA_FIELDS)
@pytest.mark.parametrize("payload", PAYLOADS)
def test_hostile_value_is_data_not_code(field, payload):
    """A payload in ANY data field must leave the generated script as valid Python whose AST is structurally
    identical to the benign build -- same node count (so no statement/call was injected) and, specifically, no
    `os` import and no `.system` call anywhere. A payload that became code would add nodes; one that stayed a
    string literal cannot. (The value itself may be embedded in a larger literal -- e.g. name -> EVT_<name> --
    or path-normalized -- backup_dir -> str(Path(...)); it is still inert either way, which is the point.)"""
    src = build_revert_script(**{**BENIGN, field: payload})
    _compiles(src)                                            # never breaks the script
    assert _node_count(src) == _BENIGN_NODES                  # nothing injected -- only a literal's value changed
    tree = ast.parse(src)
    assert "os" not in {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(isinstance(n, ast.Attribute) and n.attr == "system" for n in ast.walk(tree))


def test_passthrough_value_is_carried_verbatim_as_a_string_literal():
    """A field that passes straight through (mod_folder) carries even a quote-bearing value into the script as
    an intact string constant -- proving the value is really embedded (as data), not silently dropped."""
    src = build_revert_script(**{**BENIGN, "mod_folder": 'weird"folder'})
    assert 'weird"folder' in _string_constants(src)


def test_trusted_code_fragments_splice_and_stay_valid():
    """The *_revert_code fragments are spliced verbatim (they dedent out of the LANGS loop). The
    representative fragment here mirrors the REAL surgical BattlePatch fragment ``tools/deploy_field.py``
    generates (multi-line, own imports, a parenthesized continuation) and must keep the script compilable."""
    frag = ('\nfrom ff9mapkit.battle import battlepatch as _bpm'
            '\nfrom ff9mapkit.fsutil import atomic_write_text as _awt, locked_sidecar as _lsc'
            '\n_bpb = BK/f"BattlePatch.txt.preDEPLOY.{STAMP}"'
            '\nwith _lsc(live.battle_patch):'
            '\n    _bpn = _bpm.revert_splice(live.battle_patch.read_text(encoding="utf-8") if live.battle_patch.exists() else "",'
            '\n                             _bpb.read_text(encoding="utf-8") if _bpb.exists() else "", 4003)'
            '\n    if _bpn: _awt(live.battle_patch, _bpn, newline="\\n")'
            '\n    elif live.battle_patch.exists(): live.battle_patch.unlink()')
    src = build_revert_script(**BENIGN, bp_revert_code=frag)
    _compiles(src)
    assert "revert_splice" in src and "BattlePatch.txt.preDEPLOY" in src


def test_revert_tolerates_a_wiped_mod_folder():
    """A campaign deploy wholesale-replaces mod folders, and a field deploy runs this script as its PRELUDE
    with the exit code now checked -- so a revert that crashes over a missing DictionaryPatch would hard-block
    every redeploy of the slot. Pin: a missing live DictionaryPatch reads as empty, and restore targets get
    their parent dirs recreated rather than assuming the deploy-time tree still exists."""
    src = build_revert_script(**BENIGN)
    assert "if live.dictionary_patch.exists() else []" in src
    assert src.count("mkdir(parents=True, exist_ok=True)") >= 2   # the DictionaryPatch write + the .mes restore
    # M6: at revert time the live file is the ONLY copy of foreign lines added since the deploy -- a
    # truncated write loses other sessions' registrations with no backup that contains them.
    assert "atomic_write_text(live.dictionary_patch" in src
    assert "live.dictionary_patch.write_text" not in src


def test_dictionary_revert_holds_the_sidecar_lock():
    """The generated revert does the same read->merge->write a deploy does, into the same shared file --
    and a deploy RUNS it as the prelude, so at any instant some other session's revert may be rewriting a
    folder a deploy is about to. Pin: the read, the surgical merge, and the atomic write all sit inside
    `with locked_sidecar(...)` (the same fsutil lock the deploy scripts hold). A timeout PROPAGATES here on
    purpose: the traceback fails the script, and the prelude's checked exit code turns that into a loud
    deploy abort -- rewriting unlocked could drop a foreign FieldScene line that exists in NO backup."""
    src = build_revert_script(**BENIGN)
    tree = ast.parse(src)
    withs = [n for n in ast.walk(tree) if isinstance(n, ast.With)
             and any(isinstance(i.context_expr, ast.Call) and isinstance(i.context_expr.func, ast.Name)
                     and i.context_expr.func.id == "locked_sidecar" for i in n.items)]
    assert len(withs) == 1, "exactly one locked_sidecar block owns the DictionaryPatch revert"
    w = withs[0]
    calls = {n.func.id for n in ast.walk(w) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    attrs = {n.func.attr for n in ast.walk(w) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "read_text" in attrs and "revert_dictionary_patch" in attrs, "read + merge inside the lock"
    assert "atomic_write_text" in calls, "the write inside the lock"
    # the mkdir must PRECEDE the lock: after a campaign wipe the mod folder may not exist, and the sidecar
    # lockfile needs the folder as much as the write does -- a crash here would hard-block every redeploy.
    assert src.index("mkdir(parents=True, exist_ok=True)") < src.index("with locked_sidecar(")


@pytest.mark.parametrize("payload", PAYLOADS)
@pytest.mark.parametrize("where", ["lang", "digest"])
def test_hostile_mes_fresh_entry_is_data_not_code(where, payload):
    """``mes_fresh`` (lang -> sha256 of a freshly written .mes) is data too: a hostile key or digest must
    stay a string literal in the rendered dict -- same AST shape as a benign one-entry map."""
    benign = build_revert_script(**BENIGN, mes_fresh={"us": "ab" * 32})
    entry = {payload: "ab" * 32} if where == "lang" else {"us": payload}
    src = build_revert_script(**BENIGN, mes_fresh=entry)
    _compiles(src)
    assert _node_count(src) == _node_count(benign)
    assert payload in _string_constants(src)


def _run_revert(tmp_path, *, text_block, backed=(), fresh=None):
    """Render a field revert against a throwaway game root and RUN it the way the deploy prelude does (a
    subprocess). ``FF9_GAME_PATH`` points at the tmp game, which exists, so ``find_game_path`` resolves to it
    and never falls through to auto-detecting the real install. Returns (live layout, a zero-arg runner) so
    the caller can stage the live .mes files first."""
    import os, subprocess, sys
    import ff9mapkit
    from ff9mapkit.config import ModLayout
    game, bk, stamp = tmp_path / "game", tmp_path / "bk", "20260923-120000"
    game.mkdir(); bk.mkdir()
    for L, data in backed:                            # the deploy's pre-existing-copy backups
        (bk / f"{L}-{text_block}.mes.preDEPLOY.{stamp}").write_bytes(data)
    src = build_revert_script(**{**BENIGN, "kit": pathlib.Path(ff9mapkit.__file__).resolve().parents[1],
                                 "backup_dir": bk, "stamp": stamp, "mod_folder": "MF",
                                 "text_block": text_block}, mes_fresh=fresh)
    script = tmp_path / "revert_deploy_4003.py"
    script.write_text(src, encoding="utf-8")
    live = ModLayout(game / "MF")
    return live, lambda: subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                                        env={**os.environ, "FF9_GAME_PATH": str(game)})


def _sha(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def test_revert_deletes_the_mes_it_wrote_fresh_and_nothing_else(tmp_path):
    """The leak: a deploy that wrote ``field/<block>.mes`` where none stood took no backup, so the revert had
    nothing to restore and LEFT the file. On a REAL block (1073 = Black Mage Village) that leftover is live
    content -- FF9TextTool merges every folder's .mes over the base game per txid -- and since every redeploy
    runs the prior revert as its prelude, it outlived even a redeploy that no longer ships the .mes.
    Four languages, four outcomes, one run:
      us -- written fresh, still our bytes           -> DELETED
      uk -- written fresh, a later deploy rewrote it -> KEPT (theirs now), and said so
      fr -- pre-existed, backed up                   -> RESTORED from the backup (unchanged path)
      gr -- never touched by this deploy             -> LEFT ALONE"""
    ours_us, ours_uk, theirs_uk = b"our us text", b"our uk text", b"a later deploy's uk text"
    live, run = _run_revert(tmp_path, text_block=1073, backed=[("fr", b"prior fr text")],
                            fresh={"us": _sha(ours_us), "uk": _sha(ours_uk)})
    for L, data in (("us", ours_us), ("uk", theirs_uk), ("fr", b"this deploy's fr text"), ("gr", b"foreign gr")):
        live.mes_path(L, 1073).parent.mkdir(parents=True, exist_ok=True)
        live.mes_path(L, 1073).write_bytes(data)
    rc = run()
    assert rc.returncode == 0, rc.stderr
    assert not live.mes_path("us", 1073).exists(), "the fresh .mes still holding our bytes must be deleted"
    assert live.mes_path("uk", 1073).read_bytes() == theirs_uk, "a later deploy's text must survive"
    assert "kept" in rc.stdout and str(live.mes_path("uk", 1073)) in rc.stdout, "a skipped delete is not silent"
    assert live.mes_path("fr", 1073).read_bytes() == b"prior fr text", "a backed-up .mes is still restored"
    assert live.mes_path("gr", 1073).read_bytes() == b"foreign gr", "a .mes this deploy never wrote is untouched"


def test_revert_of_a_fresh_mes_tolerates_it_already_being_gone(tmp_path):
    """The per-id and the generic ``revert_deploy.py`` are the same script, and a campaign install can wipe the
    folder -- a fresh-listed .mes that is already absent is nothing to do, not a crash (a crash here fails the
    prelude and hard-blocks every redeploy of the slot)."""
    live, run = _run_revert(tmp_path, text_block=1073, fresh={"us": _sha(b"gone")})
    rc = run()
    assert rc.returncode == 0, rc.stderr
    assert not live.mes_path("us", 1073).exists()


def test_revert_without_mes_fresh_keeps_the_old_behavior(tmp_path):
    """No ``mes_fresh`` (a deploy that wrote no fresh .mes, or an older caller) must delete nothing -- only
    the backup restore runs."""
    live, run = _run_revert(tmp_path, text_block=1073)
    live.mes_path("us", 1073).parent.mkdir(parents=True, exist_ok=True)
    live.mes_path("us", 1073).write_bytes(b"not ours to judge")
    rc = run()
    assert rc.returncode == 0, rc.stderr
    assert live.mes_path("us", 1073).read_bytes() == b"not ours to judge"


def test_int_fields_are_coerced():
    """fid / text_block are forced through int() -- a stringy int works, junk raises (never silently becomes a
    stray identifier in the script)."""
    _compiles(build_revert_script(**{**BENIGN, "fid": "5000", "text_block": "8"}))
    with pytest.raises(ValueError):
        build_revert_script(**{**BENIGN, "fid": "not-an-int"})
