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
