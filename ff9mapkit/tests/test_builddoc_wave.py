"""Build & Deploy tab, the Build/deploy-safety wave: the one-key reversible loop (no modal by default),
and naming the New-Game casualty a wholesale campaign deploy would wipe.

Headless (offscreen). Drives the real BuildDoc; `run` is a stub that records the argv + kwargs (and never
starts a subprocess), so the deploy-chaining `on_finished` can be fired by hand.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication          # noqa: E402

from ff9mapkit.editor.theme import pick_palette     # noqa: E402
from ff9mapkit.workspace import builddoc as BD      # noqa: E402
from ff9mapkit.workspace.builddoc import BuildDoc   # noqa: E402

_REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _doc(app):
    calls = []
    doc = BuildDoc(pick_palette("dark"), _REPO,
                   run=lambda argv, **kw: calls.append((argv, kw)) or True,
                   problems=lambda *a, **k: None)
    doc._calls = calls
    return doc


# --------------------------------------------------------------------------- item 2: one-key F9 loop
def test_reversible_deploy_skips_the_confirm_by_default(app, tmp_path, monkeypatch):
    """A reversible test-slot deploy must NOT pop the modal by default (F9 = one keystroke); the confirm
    opts back IN via prefs.confirm_reversible_deploys."""
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")     # isolate prefs from the dev's
    doc = _doc(app)
    if not doc.has_tools:
        pytest.skip("no dev deploy tools in this checkout")
    p = tmp_path / "F.field.toml"
    p.write_text('[field]\nid = 4003\nname = "X"\narea = 11\n', encoding="utf-8")
    doc.path.setText(str(p))
    doc.rb_test.setChecked(True)
    confirmed = []
    doc._confirm = lambda *a, **k: confirmed.append(1) or True
    doc._go_field(str(p))
    assert not confirmed, "a reversible test deploy popped the modal on the default (skip) setting"
    assert doc._calls, "the deploy still ran without the modal"
    prefs.set_confirm_reversible_deploys(True)                              # opt the modal back in
    doc._go_field(str(p))
    assert confirmed, "with the pref ON the reversible confirm must fire again"


def test_install_to_game_keeps_its_confirm(app, tmp_path, monkeypatch):
    """The one-key skip is for REVERSIBLE deploys only -- Install-to-game (a real write into the shipping
    folder) keeps its unconditional confirm regardless of the pref."""
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    monkeypatch.setattr(BD.jobs, "snapshot_mod_folder", lambda *a: tmp_path / "revert_install.py")
    doc = _doc(app)
    if not doc.game_mod:
        pytest.skip("no game install detected")
    p = tmp_path / "F.field.toml"
    p.write_text('[field]\nid = 4100\nname = "X"\narea = 11\n', encoding="utf-8")
    doc.path.setText(str(p))
    doc.rb_game.setChecked(True)
    confirmed = []
    doc._confirm = lambda *a, **k: confirmed.append(1) or False              # decline -> nothing deploys
    doc._go_field(str(p))
    assert confirmed, "Install-to-game must always confirm (even with the reversible-skip pref default)"
    assert not doc._calls, "a declined install must not deploy"


# --------------------------------------------------------------------------- item 4: name the casualty
def _campaign_doc(app):
    doc = _doc(app)
    doc.kind = "campaign"
    doc.plan = SimpleNamespace(name="Demo",
                               members=[SimpleNamespace(new_id=4100), SimpleNamespace(new_id=4101)],
                               mod_folder="FF9CustomMap")
    doc.rb_camp_deploy.setChecked(True)
    return doc


def test_campaign_deploy_names_the_casualty_in_the_3button(app, monkeypatch):
    doc = _campaign_doc(app)
    monkeypatch.setattr(doc, "_current_newgame_target_for", lambda name: 6000)     # a live New Game entry
    seen = {}
    monkeypatch.setattr(doc, "_confirm_campaign_deploy",
                        lambda casualty, route: (seen.__setitem__("cas", casualty), "cancel")[1])
    doc._go_campaign("c.toml")
    assert seen["cas"] == 6000, "the 3-button confirm was not shown with the casualty id"
    assert not doc._calls, "Cancel must not deploy"


def test_campaign_deploy_plain_confirm_when_no_casualty(app, monkeypatch):
    doc = _campaign_doc(app)
    monkeypatch.setattr(doc, "_current_newgame_target_for", lambda name: None)     # no live entry to wipe
    used_3button = []
    monkeypatch.setattr(doc, "_confirm_campaign_deploy", lambda *a: used_3button.append(1) or "cancel")
    monkeypatch.setattr(doc, "_confirm", lambda *a: True)                          # accept the plain confirm
    doc._go_campaign("c.toml")
    assert not used_3button, "no casualty -> the plain reversible confirm, not the 3-button"
    assert doc._calls, "the deploy ran"


def test_deploy_and_rewire_chains_the_newgame_rewire(app, monkeypatch):
    doc = _campaign_doc(app)
    monkeypatch.setattr(doc, "_current_newgame_target_for", lambda name: 6000)
    monkeypatch.setattr(doc, "_confirm_campaign_deploy", lambda *a: "rewire")
    doc._go_campaign("c.toml")
    assert len(doc._calls) == 1, "the deploy job started"
    doc._calls[0][1]["on_finished"](0)          # simulate a clean deploy finish -> the chain fires
    assert len(doc._calls) == 2, "'Deploy & re-wire' must chain the New-Game re-wire after the deploy"
    rewire = " ".join(str(x) for x in doc._calls[1][0])
    assert "6000" in rewire and "newgame" in rewire.lower(), "the chained job re-points New Game at the casualty"


def test_rewire_targets_the_campaigns_own_mod_folder(app, monkeypatch):
    """The casualty is READ from the campaign's declared folder (_current_newgame_target_for resolves
    against <install>/<plan.mod_folder>), so the re-wire must WRITE the restored override back into that
    SAME folder -- not the FF9CustomMap the argv builders default to. A campaign whose mod_folder is not
    FF9CustomMap would otherwise get its override wiped in its folder and re-created in the wrong one."""
    doc = _campaign_doc(app)
    doc.plan.mod_folder = "FF9CustomMap-ow"                 # a NON-default folder (the whole point)
    monkeypatch.setattr(doc, "_current_newgame_target_for", lambda name: 6000)
    monkeypatch.setattr(doc, "_confirm_campaign_deploy", lambda *a: "rewire")
    doc._go_campaign("c.toml")
    doc._calls[0][1]["on_finished"](0)                     # clean deploy finish -> the re-wire chains
    rewire = doc._calls[1][0]
    assert "--mod-folder" in rewire, rewire
    assert rewire[rewire.index("--mod-folder") + 1] == "FF9CustomMap-ow", rewire


def test_deploy_anyway_does_not_rewire(app, monkeypatch):
    doc = _campaign_doc(app)
    monkeypatch.setattr(doc, "_current_newgame_target_for", lambda name: 6000)
    monkeypatch.setattr(doc, "_confirm_campaign_deploy", lambda *a: "anyway")
    doc._go_campaign("c.toml")
    assert len(doc._calls) == 1
    doc._calls[0][1]["on_finished"](0)          # a clean finish must NOT chain anything
    assert len(doc._calls) == 1, "'Deploy anyway' leaves New Game unwired -- no chained re-wire"


def test_rewire_does_not_fire_on_a_failed_deploy(app, monkeypatch):
    doc = _campaign_doc(app)
    monkeypatch.setattr(doc, "_current_newgame_target_for", lambda name: 6000)
    monkeypatch.setattr(doc, "_confirm_campaign_deploy", lambda *a: "rewire")
    doc._go_campaign("c.toml")
    doc._calls[0][1]["on_finished"](2)          # a FAILED deploy (code != 0)
    assert len(doc._calls) == 1, "a failed deploy must not chain the re-wire"


# --------------------------------------------------------------------------- item 4: status line + reader
def test_newgame_status_line_reads_the_current_target(app, monkeypatch):
    doc = _doc(app)
    doc.game_mod = Path("X")                                   # force the reader to run offline
    monkeypatch.setattr(BD.jobs, "current_newgame_target", lambda mod: 4100)
    doc._refresh_newgame_status()
    assert "4100" in doc.newgame_status.text()
    monkeypatch.setattr(BD.jobs, "current_newgame_target", lambda mod: None)
    doc._refresh_newgame_status()
    assert "stock opening" in doc.newgame_status.text().lower()


def test_current_newgame_target_for_resolves_against_the_install(app, monkeypatch):
    doc = _doc(app)
    doc.game_mod = Path("C:/game/FF9CustomMap")
    seen = {}
    monkeypatch.setattr(BD.jobs, "current_newgame_target",
                        lambda mod: (seen.__setitem__("mod", mod), 6000)[1])
    assert doc._current_newgame_target_for("FF9CustomMap-ow") == 6000
    assert seen["mod"] == Path("C:/game") / "FF9CustomMap-ow"      # <game>/<folder name>
    doc.game_mod = None
    assert doc._current_newgame_target_for("FF9CustomMap") is None  # no install -> None, never raises
