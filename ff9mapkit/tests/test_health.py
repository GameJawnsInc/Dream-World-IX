"""The Setup & Health engine: pure, never-raises report rows + the cheap Home-banner summary.
Qt-free (health.py is importable headless); the dialog itself gets one offscreen construction test."""

import os

import pytest

from ff9mapkit import config, health, provision


def test_report_unconfigured_is_bad_but_never_raises(monkeypatch):
    def boom():
        raise config.ConfigError("no install")
    monkeypatch.setattr(config, "find_game_path", boom)
    rows = health.health_report()
    assert health.worst_level(rows) == "bad"
    row = next(r for r in rows if r["label"] == "FF9 install")
    assert row["level"] == "bad" and "Locate game" in row["advice"]
    assert health.quick_issues() == ["FF9 install not configured"]


def test_report_fake_install_flags_missing_pieces(monkeypatch, tmp_path):
    (tmp_path / "StreamingAssets").mkdir()             # a folder that half-looks like FF9
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    rows = health.health_report()
    launcher = next(r for r in rows if r["label"] == "FF9_Launcher.exe")
    sa = next(r for r in rows if r["label"] == "StreamingAssets")
    assert launcher["level"] == "bad" and sa["level"] == "ok"


def test_quick_issues_reports_missing_templates(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    monkeypatch.setattr(provision, "templates_present", lambda: False)
    assert health.quick_issues() == ["base templates not extracted"]
    monkeypatch.setattr(provision, "templates_present", lambda: True)
    assert health.quick_issues() == []


def test_health_flags_scripts_dll_engine_drift(monkeypatch, tmp_path):
    """A live custom battle-formula DLL built against a different engine surfaces as a WARN row (the drift
    detector after a Memoria update); a matching one is a plain OK row naming the engine it was built against."""
    (tmp_path / "StreamingAssets").mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    layout = config.ModLayout(tmp_path / "FF9CustomMap")
    dll = layout.scripts_dll("FF9CustomMap")
    dll.parent.mkdir(parents=True, exist_ok=True)
    dll.write_bytes(b"MZ")

    from ff9mapkit.battle import scriptcompile
    monkeypatch.setattr(scriptcompile, "read_engine_stamp", lambda d: {"engine_file_version": "1.1.1.1"})
    monkeypatch.setattr(scriptcompile, "engine_drift_warning",
                        lambda d, game=None: "built against 1.1.1.1, installed is 1.1.2.2")
    rows = health.health_report(mod_folder="FF9CustomMap")       # explicit: a pinned checkout must not move the probe
    row = next(r for r in rows if r["label"] == "Custom battle formula DLL")
    assert row["level"] == "warn" and "1.1.1.1" in row["advice"]

    monkeypatch.setattr(scriptcompile, "engine_drift_warning", lambda d, game=None: None)
    rows = health.health_report(mod_folder="FF9CustomMap")
    row = next(r for r in rows if r["label"] == "Custom battle formula DLL")
    assert row["level"] == "ok" and "1.1.1.1" in row["value"]


def test_health_no_scripts_dll_row_when_absent(monkeypatch, tmp_path):
    """No custom battle-formula DLL deployed -> no drift row at all (don't clutter installs without one)."""
    (tmp_path / "StreamingAssets").mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    labels = {r["label"] for r in health.health_report(mod_folder="FF9CustomMap")}
    assert "Custom battle formula DLL" not in labels


def _write_engine(tmp_path, blob: bytes):
    """A minimal installed-Memoria fixture whose Assembly-CSharp.dll carries the given marker bytes."""
    game = tmp_path / "FF9"
    for arch in ("x64", "x86"):
        mgd = game / arch / "FF9_Data" / "Managed"
        mgd.mkdir(parents=True)
        (mgd / "Assembly-CSharp.dll").write_bytes(blob)
    (game / "StreamingAssets").mkdir()
    (game / "FF9_Launcher.exe").write_bytes(b"")
    (game / "Memoria.ini").write_text("[Netsync]\nEnabled = 0\n", encoding="utf-8")
    return game


def test_netsync_generation_boundaries(tmp_path):
    """The ONE derivation Setup and the Co-op card share: the generation markers -> booleans + a
    summary + a level. s37 stays the Play-style floor boolean; the level is ok ONLY on the current
    generation, and an older one names the next feature it lacks. Every prefix of the ladder is
    walked, so a no-op that returned a fixed string fails the per-generation asserts."""
    gens = health.NETSYNC_GENERATIONS
    game = _write_engine(tmp_path / "none", b"MZ stock")
    gen = health.netsync_generation(game)
    assert (gen["netsync"], gen["s37"], gen["current"], gen["level"]) == (False, False, False, "warn")
    assert "MISSING" in gen["summary"]
    for n in range(1, len(gens) + 1):
        have = gens[:n]
        game = _write_engine(tmp_path / have[-1][0], b"MZ " + b" ".join(g[1] for g in have))
        gen = health.netsync_generation(game)
        names = {g[0] for g in have}
        assert gen["generation"] == have[-1][0] and have[-1][0] in gen["summary"]
        assert (gen["netsync"], gen["s37"], gen["s40"]) == (True, "s37" in names, "s40" in names)
        if n == len(gens):
            assert gen["current"] and gen["level"] == "ok" and "up to date" in gen["summary"]
        else:
            assert not gen["current"] and gen["level"] == "warn"
            assert gens[n][0] in gen["summary"] and gens[n][2] in gen["summary"]
    # a None install (no game) never raises and reads as no netsync
    assert health.netsync_generation(None)["level"] == "warn"


def test_netsync_markers_are_unique_to_their_patch():
    """Each generation marker must be DECLARED first by its own patch (a type or method an earlier
    patch already declares would date the engine wrong). Declarations, not mentions: s22's debug menu
    was re-captured after netsync and USES NetSyncClient. Reads the patch stack, never the install."""
    import re
    from pathlib import Path
    stack = Path(__file__).resolve().parents[2] / "memoria-patches"
    if not stack.is_dir():
        pytest.skip("memoria-patches/ not beside this checkout")
    texts = {int(m.group(1)): p.read_text(encoding="utf-8", errors="replace")
             for p in stack.glob("s*.patch") if (m := re.match(r"s(\d+)-", p.name))}
    for gen, marker, _what in health.NETSYNC_GENERATIONS:
        name = re.escape(marker.decode())
        decl = re.compile(rf"^\+.*(\b(class|struct)\s+{name}\b"
                          rf"|\b(static|public|private|internal)\b[^=;(]*\b{name}\s*\()", re.M)
        declared = sorted(n for n, t in texts.items() if decl.search(t))
        assert declared and declared[0] == int(gen[1:]), \
            f"{marker!r} first declared by s{declared[0] if declared else '?'}, not {gen}"


def test_health_report_has_co_op_engine_row_from_shared_source(tmp_path, monkeypatch):
    """Setup's report gains the engine-generation triage row, sourced from netsync_generation -- the
    SAME helper the Co-op status card reads. Its value/level must equal the helper's, so the two
    surfaces render one fact (a hardcoded row would drift from the helper and fail this)."""
    game = _write_engine(tmp_path, b"MZ " + b" ".join(g[1] for g in health.NETSYNC_GENERATIONS))
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: game)
    row = next(r for r in health.health_report() if r["label"] == "Co-op engine")
    gen = health.netsync_generation(game)
    assert row["value"] == gen["summary"] and row["level"] == gen["level"] == "ok"


def test_worst_level_ordering():
    assert health.worst_level([{"level": "ok"}]) == "ok"
    assert health.worst_level([{"level": "ok"}, {"level": "warn"}]) == "warn"
    assert health.worst_level([{"level": "warn"}, {"level": "bad"}]) == "bad"


def test_setup_dialog_constructs_offscreen(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.setupdialog import SetupHealthDialog
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    dlg = SetupHealthDialog(None, pick_palette("dark"), kit_cwd=tmp_path)
    assert dlg._worst in ("ok", "warn", "bad")         # the report rendered
    dlg.refresh()                                      # re-render is safe (grid rebuild)


def test_setup_dialog_refresh_never_stacks_grids(monkeypatch, tmp_path):
    """The doubled-report regression: refresh() before exec() queues the old grid's deferred delete
    OUTSIDE the dialog's nested event loop, so it must be DETACHED immediately — WITHOUT processing
    any deferred deletes, exactly one grid may be parented to the host."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QWidget
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.setupdialog import SetupHealthDialog
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    dlg = SetupHealthDialog(None, pick_palette("dark"), kit_cwd=tmp_path)
    dlg.refresh()                                      # the _open_setup-before-exec() sequence
    dlg.refresh()
    kids = [c for c in dlg.grid_host.findChildren(QWidget) if c.parent() is dlg.grid_host]
    assert len(kids) == 1, f"stale report grids still parented: {len(kids)}"


def test_health_mod_folder_row_follows_the_documented_folder_order(monkeypatch, tmp_path):
    """The Mod folder row and the custom-DLL probe read the folder `config.resolve_mod_folder` names
    (--mod-folder > $FF9_MOD_FOLDER > .ff9deploy.toml > FF9CustomMap), not a hardcoded FF9CustomMap -- a
    pinned checkout's Setup & Health used to report the shared default folder while every deploy went to
    the pin. An explicit ``mod_folder`` still wins over the env var."""
    (tmp_path / "StreamingAssets").mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    monkeypatch.setenv("FF9_MOD_FOLDER", "Alt")
    layout = config.ModLayout(tmp_path / "Alt")
    dll = layout.scripts_dll("Alt")
    dll.parent.mkdir(parents=True, exist_ok=True)
    dll.write_bytes(b"MZ")
    from ff9mapkit.battle import scriptcompile
    monkeypatch.setattr(scriptcompile, "read_engine_stamp", lambda d: {"engine_file_version": "1.1.1.1"})
    monkeypatch.setattr(scriptcompile, "engine_drift_warning", lambda d, game=None: None)
    rows = health.health_report()
    mod = next(r for r in rows if r["label"] == "Mod folder")
    assert mod["value"].startswith(str(tmp_path / "Alt"))
    assert any(r["label"] == "Custom battle formula DLL" for r in rows)     # the probe looked in Alt/
    rows = health.health_report(mod_folder="FF9CustomMap")                   # explicit beats the env var
    mod = next(r for r in rows if r["label"] == "Mod folder")
    assert mod["value"].startswith(str(tmp_path / "FF9CustomMap"))
    assert not any(r["label"] == "Custom battle formula DLL" for r in rows)


def test_health_report_start_keys_the_pin_walk_and_the_dialog_passes_its_checkout(monkeypatch, tmp_path):
    """With no ``start`` the resolver walks up from the CWD -- right for a CLI verb, wrong for the Workspace,
    which never chdirs: launched from outside the checkout its Setup & Health named the shared default while
    the Build tab deployed into the pin. ``start=`` keys the walk; the dialog passes its kit dir (the walk
    climbs to the checkout root, where the pin and the .git marker sit)."""
    game = tmp_path / "game"
    (game / "StreamingAssets").mkdir(parents=True)
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: game)
    monkeypatch.delenv("FF9_MOD_FOLDER", raising=False)
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "ff9mapkit").mkdir()
    (repo / ".ff9deploy.toml").write_text('mod_folder = "Pinned"\n', encoding="utf-8")
    mod = next(r for r in health.health_report(start=repo / "ff9mapkit") if r["label"] == "Mod folder")
    assert mod["value"].startswith(str(game / "Pinned"))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.setupdialog import SetupHealthDialog
    QApplication.instance() or QApplication([])
    seen = []
    real = health.health_report
    monkeypatch.setattr(health, "health_report", lambda *a, **k: seen.append(k) or real(*a, **k))
    SetupHealthDialog(None, pick_palette("dark"), kit_cwd=repo / "ff9mapkit")
    assert seen and seen[-1].get("start") == str(repo / "ff9mapkit")
