"""Static cover for ``tools/deploy_field.py``'s DictionaryPatch ownership wiring.

The script cannot be imported -- it deploys on import -- so the wiring is checked by AST, the same way
``test_deploylog.py`` checks the embedded revert template. What matters here is not that some predicate
exists but that it is THE LIBRARY'S: the same object decides which live registrations the rewrite strips and
which of those strips deserve a warning, so a hand-rolled copy that drifts from ``dictpatch`` re-opens the
silent-loss hole (see ``dictpatch.owned_predicate``).
"""
import ast
import pathlib

_SRC = (pathlib.Path(__file__).resolve().parents[2] / "tools" / "deploy_field.py").read_text(encoding="utf-8")


def _assignments(name):
    """Every value node assigned to ``name`` at any depth of the script."""
    return [n.value for n in ast.walk(ast.parse(_SRC))
            if isinstance(n, ast.Assign)
            for t in n.targets if isinstance(t, ast.Name) and t.id == name]


def test_dp_owned_is_the_library_predicate_not_a_hand_rolled_one():
    """The regression: ``_dp_owned`` was a local ``def`` whose id clause read ``ln.split()[1:2] == [str(FID)]``
    -- directive-AGNOSTIC. Mint GEO ids start at 6000 and the custom field band is 4000-9899, so deploying a
    field in that overlap claimed another session's ``3DModel <same id>``, dropped it from the rewritten file,
    and (because this predicate is handed to the foreign-drop guard as ``owned=``) suppressed the warning too.
    One ownership rule, from the library, or the two drift apart again."""
    values = _assignments("_dp_owned")
    assert len(values) == 1, "_dp_owned must be bound exactly once, from the library"
    call = values[0]
    assert isinstance(call, ast.Call), "_dp_owned must be built by dictpatch.owned_predicate, not defined here"
    assert isinstance(call.func, ast.Attribute) and call.func.attr == "owned_predicate"
    # every ownership axis the deploy re-emits must be handed over -- a forgotten kwarg silently un-owns a
    # registration class and makes the guard cry wolf on every deploy that emits it.
    # `text_blocks` is the MessageFile axis: a custom mesID is registered BY BLOCK, not by field id, so it
    # cannot be derived from `fid` here -- a derived block equals the id, an explicit one need not.
    assert {kw.arg for kw in call.keywords} == {"fid", "model_ids", "anim_keys",
                                               "status_icon_ids", "charname_keys", "text_blocks"}


def test_no_hand_rolled_field_id_column_test_survives():
    """A belt-and-braces text fence on the exact directive-agnostic construct that caused this: any line
    whose column 2 equals the field id, tested without naming a directive."""
    assert "ln.split()[1:2] == [str(FID)]" not in _SRC
    assert "ln.split()[1:2] != [str(FID)]" not in _SRC       # the pre-guard filter form


def test_foreign_drop_guard_is_still_handed_that_predicate():
    """The guard's precision is the predicate's precision; passing no ``owned`` cries wolf on every deploy,
    passing a different one goes silent. Pin that the call site spends the same object."""
    calls = [n for n in ast.walk(ast.parse(_SRC))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "foreign_registrations_dropped"]
    assert len(calls) == 1
    owned = [kw.value for kw in calls[0].keywords if kw.arg == "owned"]
    assert len(owned) == 1 and isinstance(owned[0], ast.Name) and owned[0].id == "_dp_owned"


def _first_call_line(tree, pred):
    """The earliest source line of a Call node matching ``pred`` (asserts one exists)."""
    lines = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and pred(n)]
    assert lines, "expected call not found in tools/deploy_field.py"
    return min(lines)


def test_build_runs_before_the_prelude_revert():
    """H1 (Lane B, 2026-08): the prelude revert used to run FIRST, so any author error -- a typo'd toml path
    at FieldProject.load, a lint refusal, a BuildError -- aborted with the slot's prior deploy ALREADY torn
    down: the field un-registered and its files deleted over a build that never happened, and a mid-playtest
    ~ Reload/Warp on that id black-screened. The build touches only a private tempdir, so it must come first;
    a failed build then leaves the live install exactly as it was. (build_mod reads nothing live -- verified
    against build.py -- so the reorder has no behavioural cost.)"""
    tree = ast.parse(_SRC)
    load_ln = _first_call_line(tree, lambda n: isinstance(n.func, ast.Attribute) and n.func.attr == "load")
    build_ln = _first_call_line(tree, lambda n: isinstance(n.func, ast.Attribute) and n.func.attr == "build_mod")
    run_ln = _first_call_line(tree, lambda n: isinstance(n.func, ast.Attribute) and n.func.attr == "run"
                              and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess")
    assert load_ln < run_ln and build_ln < run_ln, \
        "the prelude revert must run only after a successful load + build"


def test_prelude_revert_failure_aborts_the_deploy():
    """H3: the prelude's subprocess.run result used to be discarded. A revert that crashed midway (mod folder
    wiped by a campaign deploy, a moved backups/ dir) was silently swallowed; the deploy then continued on a
    half-reverted folder -- a stale CSV/patch line the new build no longer ships survives silently -- and
    finally OVERWROTE revert_deploy_<id>.py, orphaning the backups the old revert pointed at. Pin: the run
    result is bound to a name and its returncode is consulted."""
    tree = ast.parse(_SRC)
    runs = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "run"
            and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == "subprocess"]
    assert len(runs) == 1, "the prelude subprocess.run must be BOUND so its returncode can be checked"
    (target,) = runs[0].targets
    assert isinstance(target, ast.Name)
    assert any(isinstance(n, ast.Attribute) and n.attr == "returncode"
               and isinstance(n.value, ast.Name) and n.value.id == target.id
               for n in ast.walk(tree)), "the prelude's returncode is never checked -- a crashed revert " \
                                         "would be silently deployed over"


def test_splice_reverts_are_surgical_not_snapshot_restores():
    """H2 (Lane B, 2026-08): BattlePatch/TextPatch/ForkDonorPatch deploy as non-clobbering splices, but the
    generated reverts restored the whole pre-deploy SNAPSHOT -- re-clobbering every block/row another deploy
    spliced in between. A redeploy runs its revert as the prelude, so the loss window was the whole gap
    between two deploys of an id: redeploy field 30500 and a co-deployed battle's tuning (or a later fork's
    donor row) silently vanished. The fragments must spend the library's surgical revert instead."""
    assert _SRC.count("_bpm.revert_splice") == 1 and _SRC.count("_itm.revert_splice") == 1, \
        "BattlePatch AND TextPatch revert fragments must spend the library's surgical revert"
    assert "revert_row" in _SRC, "the ForkDonorPatch revert fragment"
    assert "merge_row" in _SRC, "the deploy-side ForkDonorPatch write shares forkdonor's one rule"
    for bad in ('shutil.copyfile(BK/f"BattlePatch.txt.preDEPLOY.{STAMP}", live.battle_patch)',
                'shutil.copyfile(BK/f"TextPatch.txt.preDEPLOY.{STAMP}", live.text_patch)',
                'shutil.copyfile(BK/f"ForkDonorPatch.txt.preDEPLOY.{STAMP}"'):
        assert bad not in _SRC, f"a wholesale snapshot restore is back: {bad}"
    # and the triggers use the exact-marker helper, never a substring -- "ff9mapkit field 300" is a prefix
    # of field 3000's marker, and a false trigger armed a revert for a field that owned no block at all.
    assert 'f"ff9mapkit field {FID}" in' not in _SRC
    assert _SRC.count("has_block") >= 2


def test_live_patch_rewrites_are_atomic():
    """M6: the live DictionaryPatch/BattlePatch/TextPatch rewrites went through Path.write_text -- a
    half-written DictionaryPatch (Ctrl-C, disk-full) unregisters EVERY field in the folder at the next
    launch, and these files carry OTHER sessions' lines. fsutil.atomic_write_text is the house rule for
    load-bearing writes (2026-07 review); pin that this script spends it."""
    for bad in ("live.dictionary_patch.write_text", "live.battle_patch.write_text",
                "live.text_patch.write_text"):
        assert bad not in _SRC, f"non-atomic live rewrite is back: {bad}"
    assert "atomic_write_text" in _SRC


def test_deploy_target_resolution_is_loud():
    """M5: a malformed .ff9deploy.toml used to be swallowed (`except Exception: pass`) -- the worktree then
    silently deployed into the SHARED default folder, the exact hazard the pin exists to prevent. Deploy is
    the destructive path, so it must ABORT on a malformed pin. And "always pass --id" was a doc-only mandate
    (feedback-deploy-field-default-sandbox): the silent 4003 default is a shared slot, so defaulting must
    announce itself."""
    assert "refusing to guess a deploy target" in _SRC     # the malformed-pin abort
    assert "except Exception:\n            pass" not in _SRC
    assert "no --id given" in _SRC                          # the defaulted-id warning


def test_generated_revert_fragments_compile_when_spliced():
    """The *_revert_code fragments are Python source built by string concatenation -- a stray quote or a
    bad indent in one yields a revert script that dies at PARSE time, and (H3) a crashed prelude now
    hard-blocks every redeploy of the slot. Evaluate the REAL fragment expressions out of the script's AST
    (with FID bound as in a deploy) and compile the fully spliced revert."""
    tree = ast.parse(_SRC)
    frags = {}
    for name in ("bp_revert_code", "tp_revert_code", "fork_revert_code"):
        exprs = [n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 for t in n.targets if isinstance(t, ast.Name) and t.id == name]
        real = [e for e in exprs if not (isinstance(e, ast.Constant) and e.value == "")]
        assert real, f"no fragment expression found for {name}"
        code = compile(ast.Expression(ast.fix_missing_locations(real[-1])), "<frag>", "eval")
        frags[name] = eval(code, {"FID": 4003})  # noqa: S307 -- evaluating our own source's literal
    from ff9mapkit.reverttmpl import build_revert_script
    src = build_revert_script(kit="k", backup_dir="b", stamp="s", mod_folder="M", fid=4003, name="T",
                              fbg="F", text_block=4003, repo="r",
                              bp_revert_code=frags["bp_revert_code"],
                              tp_revert_code=frags["tp_revert_code"],
                              fork_revert_code=frags["fork_revert_code"])
    compile(src, "<revert>", "exec")


def test_message_file_line_is_carried_into_the_live_dictionary_patch():
    """THE BLACK-SCREEN REGRESSION (2026-07-18). `deploy_field` does not copy the built dist's
    DictionaryPatch -- it REBUILDS the live one from parts (mint lines, charname, status icons, the
    FieldScene line, location lines) and re-appends them. When `text_block` began defaulting to a CUSTOM
    (registered) mesID, the build emitted `MessageFile <block>` into the dist but the live merge had no
    branch for it, so the FieldScene line landed WITHOUT its registration. DataPatchers then failed
    `!FF9DBAll.MesDB.ContainsKey(mesID)` and SKIPPED the whole scene: the field never registered and
    black-screened in game, with nothing but "invalid message file ID" in Memoria.log.

    Pinned as source structure (not behaviour) for the same reason the sibling tests are: nothing else in
    the suite executes this script, and the failure is invisible until a real deploy plus a relaunch."""
    assert "message_file_lines" in _SRC, "deploy_field must read info['message_file_lines']"
    assert "dp += message_file_lines" in _SRC, "…and append them to the live DictionaryPatch"
    # ORDER MATTERS: DataPatchers reads the file top-down, so the registration must precede the FieldScene
    # line that depends on it passing the MesDB gate.
    assert _SRC.index("dp += message_file_lines") < _SRC.index('dp.append(info["dictionary"][0])')
    # and the revert must drop its OWN block (scoped by block, so a co-resident folder's line survives) --
    # that scoping now lives in ff9mapkit.reverttmpl.build_revert_script; assert on its rendered output.
    from ff9mapkit.reverttmpl import build_revert_script
    _rev = build_revert_script(kit="k", backup_dir="b", stamp="s", mod_folder="FF9CustomMap", fid=4003,
                               name="TESTROOM", fbg="FBG", text_block=1073, repo="r", mes_blocks=[1073])
    assert "_MES_BLOCKS" in _rev and "text_blocks=_MES_BLOCKS" in _rev
