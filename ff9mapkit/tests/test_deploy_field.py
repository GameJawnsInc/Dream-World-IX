"""Offline tests for the single-field deploy verb (``ff9mapkit deploy`` -> ``ff9mapkit.deploy.deploy_field``).

The installed-copy twin of ``tools/deploy_field.py``, which stays repo-only (its sandbox id-forcing,
``.ff9deploy.toml`` resolution and prior-id auto-revert are dev-loop concerns). These run against a FAKE
game dir under tmp_path -- never the real install -- and cover the whole reversible round trip: dry-run
touches nothing, apply installs, the emitted revert script actually restores. The in-game warp is verified
by a human (Hard Constraint §2).
"""

import ast
import runpy
from pathlib import Path

import pytest

from ff9mapkit import deploy
from ff9mapkit.deploy import DeployError


def _field(tmp_path, name="ROOM", fid=4009, donor=None, text_block=1073):
    """A minimal buildable field.toml; `donor` makes it a fork (so ForkDonorPatch rides along)."""
    p = tmp_path / f"{name}.field.toml"
    src = f"source_field = {donor}\n" if donor is not None else ""
    p.write_text(
        f'[field]\nid = {fid}\nname = "{name}"\narea = 11\ntext_block = {text_block}\n{src}\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n',
        encoding="utf-8")
    return p


def _dirs(tmp_path):
    return {"game": tmp_path / "game", "backups_dir": tmp_path / "bk", "reverts_dir": tmp_path / "rev"}


def _deploy(toml, tmp_path, **kw):
    d = _dirs(tmp_path)
    d["game"].mkdir(parents=True, exist_ok=True)
    return deploy.deploy_field(toml, game=d["game"], backups_dir=d["backups_dir"],
                               reverts_dir=d["reverts_dir"], verbose=False, **kw)


def test_default_field_folder_is_dedicated_and_sanitized():
    """Default target is a DEDICATED folder in the FF9CustomMap* family the install already stacks -- a
    folder the field owns has nothing of anyone else's to preserve, which is what makes the wholesale
    install correct without a surgical per-id merge."""
    assert deploy.default_field_folder("ROOM") == "FF9CustomMap-ROOM"
    assert deploy.default_field_folder("my room/../x") == "FF9CustomMap-myroomx"   # no path escape
    assert deploy.default_field_folder("") == "FF9CustomMap-field"


def test_dry_run_touches_nothing(tmp_path):
    rep = _deploy(_field(tmp_path), tmp_path)
    assert rep["rc"] == 0 and rep["ok"] and not rep["applied"]
    assert rep["mod_folder"] == "FF9CustomMap-ROOM" and rep["field_id"] == 4009
    assert not (tmp_path / "game" / "FF9CustomMap-ROOM").exists()
    assert not (tmp_path / "rev").exists() and not (tmp_path / "bk").exists()


def test_apply_installs_a_complete_mod_folder(tmp_path):
    rep = _deploy(_field(tmp_path, donor=600, text_block=22), tmp_path, apply=True)
    assert rep["rc"] == 0 and rep["applied"] and rep["created_folder"] is True
    live = tmp_path / "game" / "FF9CustomMap-ROOM"
    assert "FieldScene 4009" in (live / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert (live / "ModDescription.xml").read_text(encoding="utf-8").count(
        "<InstallationPath>FF9CustomMap-ROOM</InstallationPath>") == 1
    # the Phase-0 payoff: a FORK installed this way carries its donor map, so the s24-s33 fork gates resolve
    assert [l for l in (live / "ForkDonorPatch.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")] == ["4009 600"]
    assert (live / "StreamingAssets").is_dir()


def test_revert_of_a_created_folder_removes_it(tmp_path):
    """The deploy CREATED the folder, so there is no snapshot to copy back -- the revert must REMOVE it.
    (_render_folder_revert, the campaign one, would leave the install in place and report success.)"""
    rep = _deploy(_field(tmp_path), tmp_path, apply=True)
    live = tmp_path / "game" / "FF9CustomMap-ROOM"
    assert live.is_dir()
    ast.parse(Path(rep["revert"]).read_text(encoding="utf-8"))       # must be valid python
    runpy.run_path(str(rep["revert"]), run_name="__main__")
    assert not live.exists()


def test_revert_of_an_existing_folder_restores_it(tmp_path):
    """Re-deploying over a folder this field already owns snapshots it first; the revert restores that
    snapshot byte-for-byte, including a file the second build does not emit."""
    _deploy(_field(tmp_path), tmp_path, apply=True)
    live = tmp_path / "game" / "FF9CustomMap-ROOM"
    (live / "keepme.txt").write_text("v1", encoding="utf-8")         # something only the FIRST install had
    rep = _deploy(_field(tmp_path), tmp_path, apply=True)
    assert rep["created_folder"] is False
    assert not (live / "keepme.txt").exists()                        # wholesale replace dropped it
    runpy.run_path(str(rep["revert"]), run_name="__main__")
    assert (live / "keepme.txt").read_text(encoding="utf-8") == "v1"  # ...and the revert brought it back


def test_refuses_to_unregister_another_field_in_a_shared_folder(tmp_path):
    """A single-field install OWNS its folder and replaces it wholesale. Pointed at a SHARED folder, that
    silently unregisters the other fields -- their .eb/.mes stay on disk, so nothing looks wrong until the
    engine black-screens on the field whose FieldScene line vanished. Same rule build_mod enforces for
    --out; the surgical merge that would make it safe is Phase 2 (repo script only)."""
    _deploy(_field(tmp_path), tmp_path, apply=True)
    live = tmp_path / "game" / "FF9CustomMap-ROOM"
    dp = live / "DictionaryPatch.txt"
    dp.write_text("FieldScene 30110 11 THEIRS THEIRS 30110\n" + dp.read_text(encoding="utf-8"),
                  encoding="utf-8")
    other = _field(tmp_path, name="OTHER", fid=4010)
    rep = _deploy(other, tmp_path, mod_folder="FF9CustomMap-ROOM", apply=True)
    assert rep["rc"] == 2 and not rep["applied"]
    assert "FieldScene 30110" in dp.read_text(encoding="utf-8")      # aborted BEFORE touching the folder
    # ...and the escape hatch works
    rep2 = _deploy(other, tmp_path, mod_folder="FF9CustomMap-ROOM", apply=True, allow_drop=True)
    assert rep2["applied"] and "FieldScene 4010" in dp.read_text(encoding="utf-8")


def test_lint_errors_abort_before_any_build(tmp_path):
    """A field that fails the offline lint never reaches the game (rc 2, nothing created)."""
    p = tmp_path / "bad.field.toml"
    p.write_text('[field]\nid = 4009\nname = "BAD"\narea = 11\n\n'
                 '[camera]\npitch = 45\nfov = 42.2\n\n'
                 '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
                 '[[npc]]\nname = "Ghost"\npos = [0, 0]\nanim = "NO_SUCH_ANIMATION_XYZ"\n'
                 'model = "NO_SUCH_MODEL_XYZ"\n', encoding="utf-8")
    rep = _deploy(p, tmp_path, apply=True)
    assert rep["rc"] == 2 and not rep["applied"]
    assert not (tmp_path / "game" / "FF9CustomMap-BAD").exists()


def test_unloadable_target_raises_deploy_error(tmp_path):
    with pytest.raises(DeployError):
        _deploy(tmp_path / "nope.field.toml", tmp_path)


def test_render_field_revert_is_valid_python_both_ways(tmp_path):
    created = deploy._render_field_revert(tmp_path / "live", None, "20260726-000000", "ROOM")
    ast.parse(created)
    assert "rmtree" in created and "copytree" not in created         # create case: remove, never restore
    restored = deploy._render_field_revert(tmp_path / "live", tmp_path / "snap", "20260726-000000", "ROOM")
    ast.parse(restored)
    assert "copytree(snap, live)" in restored
