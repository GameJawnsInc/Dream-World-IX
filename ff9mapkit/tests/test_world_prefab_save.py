"""SAVE AS PREFAB (rung P6, studies/overworld-editor/PREFABS.md): a composition in a draft or a recipe frozen into a
catalog entry of your own.

``world-prefab NAME --save --from DRAFT|RECIPE [--steps ...]`` takes one base row (an island or a carried coast) and
the relief on it, writes them RELATIVE to the base's anchor block, composes them with the prefab frame outside the
install to learn the footprint, fingerprints them at a clean site, proves at a second that the composition moves as
one, measures the turns, and appends the entry to the user's catalog (read after the kit's, one namespace). Hermetic
tests cover the rows, the catalog file, every refusal and the World tab's dialog and job; the install-gated one saves
the walked desert peak isle's own rows back and gets the catalog's fingerprint, bit for bit.
"""
from __future__ import annotations

import json

import pytest

from ff9mapkit.world import prefab as PF

from .test_world_forestedit import _game, _mod, _no_real_install  # noqa: F401  (the install guard)
from .test_worldforest import app  # noqa: F401  (the Qt app the GUI tests use)

ISLE = {"table": "island", "center": [672.0, -608.0], "radius": 60.0, "seed": 5.0, "ground": "desert", "step": 1,
        "prefab_frame": True}
PEAK = {"table": "mountain", "center": [664.0, -604.0], "rot": 90.0, "donor": "19,3", "ground": "desert", "step": 2}
FOOT = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 0], [0, 1], [1, -1], [1, 0], [1, 1]]


# ---------------------------------------------------------------- the rows
def test_a_composition_becomes_rows_relative_to_its_base_s_block():
    entry, anchor = PF.entry_from_rows("my-isle", [ISLE, PEAK])
    assert anchor == (10, 9)                                   # the block holding the island's centre
    assert entry["rows"] == [
        {"table": "island", "center": [32.0, 32.0], "radius": 60.0, "seed": 5.0, "ground": "desert"},
        {"table": "mountain", "center": [24.0, 36.0], "rot": 90.0, "donor": "19,3", "ground": "desert"}]
    assert entry["status"] == "candidate" and entry["name"] == "my-isle"
    assert PF.expand(entry, anchor)[0]["center"] == ISLE["center"]          # placed back where it was made


def test_a_composition_across_the_seam_and_a_carried_coast_anchor_by_their_own_block():
    entry, anchor = PF.entry_from_rows("seam", [{**ISLE, "center": [1530.0, -608.0]},
                                                {**PEAK, "center": [6.0, -600.0]}])
    assert anchor == (23, 9) and entry["rows"][1]["center"] == [70.0, 40.0]   # x folded over the seam (6+1536-1472)
    entry, anchor = PF.entry_from_rows("coast", [{"table": "transplant", "cell": [20, 0], "donor": [9, 5],
                                                  "size": [2, 3], "rot": 90}])
    assert anchor == (20, 0) and entry["rows"][0]["cell"] == [0, 0]


@pytest.mark.parametrize("name, rows, why", [
    ("My Isle", [ISLE], "lower-case"),
    ("x", [ISLE], "lower-case"),
    ("ok-name", [PEAK, ISLE], "starts with its base"),
    ("ok-name", [ISLE, ISLE], "cannot ride along"),
    ("ok-name", [ISLE, {"table": "sink", "at": [1, 2]}], "cannot ride along"),
    ("ok-name", [{k: v for k, v in ISLE.items() if k != "seed"}], "center and seed"),
    ("ok-name", [ISLE, {**PEAK, "center": [672.0 + 600.0, -608.0]}], "not part of this landmass"),
])
def test_what_a_prefab_cannot_hold_refuses(name, rows, why):
    with pytest.raises(PF.PrefabRefused, match=why):
        PF.entry_from_rows(name, rows)


def test_an_entry_s_toml_loads_back_through_the_catalog_s_own_reader(tmp_path):
    entry, _a = PF.entry_from_rows("my-isle", [ISLE, PEAK])
    entry.update(fingerprint="f" * 64, fingerprint_cell=[1, 14], footprint=FOOT, turns=[0, 90],
                 note='two\nlines "quoted"', saved="2026-11-08 from draft X")
    cat = tmp_path / "c.toml"
    cat.write_text(PF._USER_HEADER + PF.entry_toml(entry), encoding="utf-8")
    (back,) = PF.load_catalog(cat)
    assert back["rows"] == entry["rows"] and back["turns"] == [0, 90] and back["note"] == 'two lines "quoted"'
    assert back["fingerprint_cell"] == [1, 14] and back["footprint"] == FOOT


# ---------------------------------------------------------------- the user's catalog
def test_the_user_catalog_is_read_after_the_kit_s_in_one_namespace(tmp_path):
    user = PF.user_catalog()
    assert not user.exists() and PF.catalog_paths() == [PF.CATALOG]       # (conftest pins the config dir)
    entry, _a = PF.entry_from_rows("mine", [ISLE])
    entry.update(fingerprint="f" * 64, fingerprint_cell=[1, 14], footprint=FOOT)
    user.parent.mkdir(parents=True, exist_ok=True)
    user.write_text(PF._USER_HEADER + PF.entry_toml(entry), encoding="utf-8")
    names = [p["name"] for p in PF.load_catalog()]
    assert names[-1] == "mine" and "desert-peak-isle" in names and PF.get("mine")["status"] == "candidate"
    # THE USER'S CATALOG NEVER TAKES DOWN THE KIT'S (review P6): each defect costs that entry, named, never raised
    user.write_text(user.read_text(encoding="utf-8") + PF.entry_toml({**entry, "name": "desert-peak-isle"})
                    + PF.entry_toml({**entry, "name": "mine"}) + PF.entry_toml({**entry, "name": "bad",
                                                                              "status": "walked"}), encoding="utf-8")
    cat = PF.load_catalog()
    assert [p["name"] for p in cat].count("desert-peak-isle") == 1 and PF.get("desert-peak-isle")["status"] == \
        "qualified"                                            # the kit's name wins
    assert [p["name"] for p in cat].count("mine") == 1 and "bad" not in [p["name"] for p in cat]
    probs = PF.catalog_problems()
    assert len(probs) == 3 and all("skipped" in w for w in probs) and any("'desert-peak-isle'" in w for w in probs)
    user.write_text("[[prefab]\nbroken", encoding="utf-8")
    assert PF.get("desert-scrub-isle")["status"] == "qualified"                  # the kit's prefabs stand
    assert "not a readable prefab catalog" in PF.catalog_problems()[0]
    user.write_bytes(b"\xef\xbb\xbf" + (PF._USER_HEADER + PF.entry_toml(entry)).encode("utf-8"))   # a BOM
    assert PF.get("mine")["name"] == "mine" and PF.catalog_problems() == []
    with pytest.raises(ValueError, match="unique name"):
        PF._load_one(PF.CATALOG, {"desert-peak-isle"})        # the KIT catalog stays strict


# ---------------------------------------------------------------- save(): every step, stood in
@pytest.fixture
def fake(tmp_path, monkeypatch):
    """Stand-ins for every staging: each stage records where it was staged and returns land keyed by ``land``;
    every site clean but the ones in ``dirty``; each turn passes unless named in ``bad_turns``."""
    st = {"stages": [], "land": {}, "dirty": set(), "bad_turns": {}, "nav": {}}

    def stage(prefab, cell, game=None, keep=False):
        st["stages"].append(tuple(cell))
        return {"fingerprint": st["land"].get(tuple(cell), "f" * 64), "footprint": [tuple(b) for b in FOOT],
                "blocks": PF.footprint_labels({"footprint": FOOT}, cell), "nav": st["nav"].get(tuple(cell), {}),
                "root": None}

    def sites(entry, game=None, first=None, limit=None):
        order = ([tuple(first)] if first else []) + [(1, 14), (1, 16), (2, 2)]
        out = [c for c in dict.fromkeys(order) if c not in st["dirty"]]
        return out[:limit] if limit else out

    def stage_turned(entry, turn, cell, game=None):
        if turn in st["bad_turns"]:
            raise st["bad_turns"][turn]
        return {"root": None, "source": {}, "fingerprint": "t", "blocks": [], "footprint": [], "nav": {}}
    monkeypatch.setattr(PF, "stage", stage)
    monkeypatch.setattr(PF, "clean_sites", sites)
    monkeypatch.setattr(PF, "stage_turned", stage_turned)
    monkeypatch.setattr(PF, "_identity_turned", lambda *a, **k: "ok")
    st["cat"] = tmp_path / "mine.toml"
    return st


def _save(fake, name="my-isle", rows=(ISLE, PEAK), **kw):
    return PF.save(name, list(rows), catalog=fake["cat"], log=lambda *a: None, **kw)


def test_a_clean_anchor_is_the_fingerprint_site_and_a_second_proves_it(fake):
    rep = _save(fake, source="draft D steps 1,2", note="mine")
    assert fake["stages"] == [(10, 9), (1, 14)]                # its own anchor (clean), then a second site
    assert rep["fingerprint_cell"] == [10, 9] and rep["second_site"] == [1, 14] and rep["turns"] == [0, 90, 180, 270]
    (e,) = PF.load_catalog(fake["cat"])
    assert e["name"] == "my-isle" and e["fingerprint"] == "f" * 64 and e["turns"] == [0, 90, 180, 270]
    assert e["saved"].endswith("from draft D steps 1,2") and e["note"] == "mine" and e["status"] == "candidate"
    _save(fake, name="second-isle")
    assert [p["name"] for p in PF.load_catalog(fake["cat"])] == ["my-isle", "second-isle"]   # appended


def test_an_anchor_beside_stock_land_fingerprints_at_the_first_clean_site(fake):
    fake["dirty"].add((10, 9))
    rep = _save(fake)
    assert fake["stages"] == [(10, 9), (1, 14), (1, 16)] and rep["fingerprint_cell"] == [1, 14]


def test_a_composition_that_does_not_move_as_one_refuses_and_writes_nothing(fake):
    fake["land"][(1, 14)] = "e" * 64
    with pytest.raises(PF.PrefabRefused, match="NOT the same land") as e:
        _save(fake)
    assert e.value.gate == "identity" and not fake["cat"].exists()


def test_unsettled_navigation_at_the_fingerprint_site_refuses(fake):
    fake["nav"][(10, 9)] = {53: 3}
    with pytest.raises(PF.PrefabRefused, match="re-class") as e:
        _save(fake)
    assert e.value.gate == "nav" and not fake["cat"].exists()


def test_a_name_in_any_catalog_refuses_before_anything_is_staged(fake, monkeypatch):
    _save(fake)
    n = len(fake["stages"])
    with pytest.raises(PF.PrefabRefused, match="in the catalog already"):
        _save(fake)
    assert len(fake["stages"]) == n
    with pytest.raises(PF.PrefabRefused, match="in the catalog already"):   # the kit's names count for yours
        PF.save("desert-peak-isle", [ISLE], log=lambda *a: None)


def test_turns_that_fail_stay_closed_and_a_riding_part_closes_them_all(fake):
    fake["bad_turns"][180] = PF.PrefabRefused("not the land turned", gate="identity")
    assert _save(fake)["turns"] == [0, 90, 270]
    fake["bad_turns"] = {90: PF.PrefabRefused("its donor prefab draws Object UNTURNED", gate="turn")}
    rep = _save(fake, name="riding")
    assert rep["turns"] == [0] and "UNTURNED" in rep["turns_note"]
    assert PF.get("riding", fake["cat"])["turns_note"].startswith("turn 90")
    assert _save(fake, name="no-turns", turns=False)["turns"] == [0]


def test_too_few_clean_sites_refuses(fake, monkeypatch):
    monkeypatch.setattr(PF, "clean_sites", lambda *a, **k: [(1, 14)])
    with pytest.raises(PF.PrefabRefused, match="proved at a second") as e:
        _save(fake)
    assert e.value.gate == "window"


def test_clean_sites_skip_stock_land_and_its_nav_margin(monkeypatch):
    """A footprint block with a prefab of its own is not open ocean; a ring of real blocks is read for stock ground
    within the margin; a ring of open ocean needs no read."""
    from ff9mapkit.world import extract as X
    real = {(5, 5), (8, 2)}
    monkeypatch.setattr(X, "block_parts", lambda disc=1, game=None: {b: frozenset({"terrain"}) for b in real})
    reads = []
    monkeypatch.setattr(PF, "stock_ground", lambda e, c, game=None: reads.append(c) or ({(8, 2): [(1, 2)]}
                                                                                       if c == (10, 3) else {}))
    entry = {"name": "x", "footprint": FOOT}
    got = PF.clean_sites(entry)
    assert (5, 5) not in got and (4, 4) not in got and (6, 6) not in got     # (5,5) in the footprint
    assert (9, 3) not in got                                                  # (8,2) in its footprint
    assert (10, 3) not in got and (10, 3) in reads                           # its ring holds (8,2): read, refused
    assert (11, 3) in got and (11, 3) not in reads                           # its ring is all open ocean: no read
    assert (12, 12) in got and (12, 12) not in reads
    assert PF.clean_sites(entry, first=(12, 12), limit=2)[0] == (12, 12)


# ---------------------------------------------------------------- the CLI
def _draft_with(tmp_path, rows):
    from ff9mapkit.world import draft as D
    game = _game(tmp_path)
    src = _mod(game, "Src", ((0, 0),))
    d = D.ensure_draft(src, game=game, root=tmp_path / "drafts")
    for r in rows:
        D.begin_step(d, [(0, 0)])
        D.commit_step(d, r, r["table"])
    return game, d


def test_the_cli_saves_a_draft_s_chosen_steps_and_a_recipe_s_rows(tmp_path, monkeypatch):
    from ff9mapkit import cli
    from ff9mapkit.world import recipe as RC
    seen = []
    monkeypatch.setattr(PF, "save", lambda name, rows, **kw: seen.append((name, rows, kw)) or {
        "ok": True, "name": name, "footprint": FOOT, "turns": [0]})
    sink = {"table": "sink", "at": [100.0, -100.0]}
    _g, d = _draft_with(tmp_path, [sink, {k: v for k, v in ISLE.items() if k not in ("step", "prefab_frame")},
                                   {k: v for k, v in PEAK.items() if k != "step"}])
    out = tmp_path / "v.json"
    assert cli.main(["world-prefab", "mine", "--save", "--from", str(d), "--steps", "2,3", "--note", "a note",
                     "--report-json", str(out)]) == 0
    name, rows, kw = seen[-1]
    assert name == "mine" and [r["table"] for r in rows] == ["island", "mountain"] and kw["note"] == "a note"
    assert kw["source"] == f"draft {d.name} steps 2,3" and kw["turns"] is True
    assert json.loads(out.read_text(encoding="utf-8"))["name"] == "mine"
    rec = tmp_path / "r.toml"
    rec.write_text(RC.dumps([{k: v for k, v in ISLE.items() if k != "step"}]), encoding="utf-8")
    assert cli.main(["world-prefab", "mine2", "--save", "--from", str(rec), "--no-turns"]) == 0
    assert [r["table"] for r in seen[-1][1]] == ["island"] and seen[-1][2]["turns"] is False
    for bad in (["--steps", "4"], ["--steps", "x"], ["--steps", "2,2"]):
        assert cli.main(["world-prefab", "m", "--save", "--from", str(d), *bad, "--report-json", str(out)]) == 1
        assert json.loads(out.read_text(encoding="utf-8"))["refused"]["gate"] == "rows"
    assert cli.main(["world-prefab", "m", "--save", "--from", str(tmp_path)]) == 1          # not a draft
    assert cli.main(["world-prefab", "m", "--save"]) == 1                                  # no --from


def test_a_save_is_never_a_recipe_row():
    from ff9mapkit.world import recipe as RC
    with pytest.raises(ValueError, match="--save"):
        RC.row_for(["world-prefab", "x", "--cell", "1,1", "--save", "--from", "d"])


# ---------------------------------------------------------------- the World tab
def _steps(rows):
    return [{"row": r, "label": r["table"]} for r in rows]


def test_the_dialog_s_rules():
    from ff9mapkit.workspace import worldprefabsave as S
    steps = _steps([ISLE, PEAK, {"table": "sink"}, {**ISLE, "ground": "snow"}, {"table": "hill", "center": [1, 2]}])
    assert S.default_selection(steps) == [3, 4]                  # the last base and the relief after it
    assert S.default_selection(_steps([{"table": "sink"}])) == []
    assert S.why_not(steps, [0, 1]) == "" and "first ticked" in S.why_not(steps, [1])
    assert "one island" in S.why_not(steps, [0, 3]) and "only forest" in S.why_not(steps, [0, 2])
    assert S.suggest_name(steps, [3, 4], {"snow-isle"}) == "snow-isle-2"
    argv = S.save_argv("G", "D", "mine", [3, 0], note="a\nb", turns=False, report="R")
    assert argv[3:] == ["--game", "G", "world-prefab", "mine", "--save", "--from", "D", "--steps", "1,4", "--note=a b",
                        "--no-turns", "--report-json", "R"]


def test_the_dialog_disables_save_until_the_steps_and_name_are_lawful(app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialogButtonBox
    from ff9mapkit.workspace.worldprefabsave import SavePrefabDialog
    dlg = SavePrefabDialog(_steps([{"table": "sink"}, ISLE, PEAK]), taken={"desert-isle"})
    save = dlg.buttons.button(QDialogButtonBox.StandardButton.Save)
    assert dlg.picked() == [1, 2] and dlg.name_edit.text() == "desert-isle-2" and save.isEnabled()
    assert not (dlg.list.item(0).flags() & Qt.ItemFlag.ItemIsEnabled)          # a sink is not offered
    dlg.name_edit.setText("desert-isle")
    assert not save.isEnabled() and "already" in dlg.why_lbl.text()
    dlg.name_edit.setText("Bad Name")
    assert not save.isEnabled()
    dlg.name_edit.setText("fine-name")
    dlg.list.item(1).setCheckState(Qt.CheckState.Unchecked)
    assert not save.isEnabled() and "first ticked" in dlg.why_lbl.text()
    dlg.list.item(1).setCheckState(Qt.CheckState.Checked)
    assert save.isEnabled() and dlg.result_value() == {"name": "fine-name", "picked": [1, 2], "note": "",
                                                       "turns": True}


def test_the_world_tab_saves_the_draft_as_a_prefab_and_the_card_offers_it(app, monkeypatch, tmp_path):
    from .test_worldforest import Scripted
    from .test_worldmountain import _doc
    from ff9mapkit.world import draft as D
    doc, game = _doc(app, monkeypatch, tmp_path)
    doc.set_view_mode("3d", sync=True)
    assert doc.open_save_prefab() is None and "Nothing to save" in doc._recipe.status_lbl.text()
    d = D.ensure_draft(doc._census.root, game=game, root=tmp_path / "drafts") if doc._census.root.is_dir() else None
    if d is None:
        _mod(game, "FF9CustomMap-world", ((0, 0),))
        d = D.ensure_draft(doc._census.root, game=game, root=tmp_path / "drafts")
    for r in ({k: v for k, v in ISLE.items() if k not in ("step", "prefab_frame")},
              {k: v for k, v in PEAK.items() if k != "step"}):
        D.begin_step(d, [(0, 0)])
        D.commit_step(d, r, r["table"])
    doc._recipe.refresh()
    asked = []
    doc._prefab_save_ask = lambda parent, steps, taken: asked.append((len(steps), "desert-peak-isle" in taken)) or {
        "name": "my-isle", "picked": [0, 1], "note": "", "turns": True}

    def answer(kind, argv):
        entry, _a = PF.entry_from_rows("my-isle", [ISLE, PEAK])
        entry.update(fingerprint="f" * 64, fingerprint_cell=[1, 14], footprint=FOOT, turns=[0, 90])
        PF.user_catalog().parent.mkdir(parents=True, exist_ok=True)
        PF.user_catalog().write_text(PF._USER_HEADER + PF.entry_toml(entry), encoding="utf-8")
        return {"ok": True, "refused": None, "name": "my-isle", "footprint": FOOT, "turns": [0, 90]}
    run = Scripted(answer)
    doc._prefab_save_runner = run
    told = []
    doc._prefab_save_tell = lambda ok, title, text: told.append((ok, title, text))
    doc._prefab_seams = {"ghost_fn": lambda p: __import__("numpy").zeros((0, 3, 3)), "ocean_fn": lambda: set(),
                         "soup_fn": doc._mountain_seams["soup_fn"], "stack_fn": lambda: [], "sync": True}
    doc.tool_actions["prefab"].trigger()
    assert doc._prefab.prefab_box.findData("my-isle") < 0
    argv = doc.open_save_prefab()
    assert asked == [(2, True)] and argv[argv.index("--from") + 1] == str(d) and argv[argv.index("--steps") + 1] == "1,2"
    assert "Saved my-isle as a prefab" in doc._recipe.status_lbl.text() and "turns 0, 90" in doc._recipe.status_lbl.text()
    assert doc._prefab.prefab_box.findData("my-isle") >= 0               # the open card offers it at once
    assert told[-1][:2] == (True, "Saved as a prefab") and "my-isle" in told[-1][2]
    act = doc.tool_actions["save_prefab"]
    assert act.isEnabled() and act.text() == "Save the draft as a prefab…"
    hold = Scripted(lambda k, a: {"ok": False, "refused": {"gate": "identity", "message": "boom"}})
    hold.hold = True                                                     # a save still running
    doc._prefab_save_runner = hold
    doc.open_save_prefab()
    assert not act.isEnabled() and act.text() == "Saving my-isle as a prefab…"
    assert doc.open_save_prefab() is None                               # one save at a time, and the entry says so
    doc._recipe.refresh()                                               # (a refresh overwrites the bar's caption)
    hold.pending()
    assert told[-1][:2] == (False, "Not saved as a prefab") and "boom" in told[-1][2] and act.isEnabled()


# ---------------------------------------------------------------- install-gated: the walked land saves back as itself
def test_the_desert_peak_isle_s_own_rows_save_back_as_its_catalog_fingerprint(tmp_path):
    """The oracle: the walked prefab's rows, placed where it stands live and saved as a new prefab, are the same
    land -- the same rows, the same footprint, the catalog's fingerprint bit for bit -- and every turn passes."""
    from .test_world_prefab import _install
    _install()
    p = PF.get("desert-peak-isle")
    rep = PF.save("peak-again", PF.expand(p, (10, 9)), catalog=tmp_path / "c.toml", log=lambda *a: None)
    assert rep["fingerprint"] == p["fingerprint"] and sorted(map(tuple, rep["footprint"])) == sorted(
        map(tuple, p["footprint"]))
    (e,) = PF.load_catalog(tmp_path / "c.toml")
    assert e["rows"] == p["rows"] and e["turns"] == [0, 90, 180, 270]


def test_a_transplant_base_needs_its_whole_target_rect_open_not_just_its_footprint(monkeypatch):
    """Measured: the comma's rect is 3x2 and its footprint 5 blocks; a site whose sixth (unwritten) block is real sea
    refused the carry. clean_sites holds the whole rect (turned) to open ocean."""
    from ff9mapkit.world import extract as X
    unit = {"name": "u", "footprint": [[0, 0], [1, 0], [1, 1], [2, 0], [2, 1]],
            "rows": [{"table": "transplant", "cell": [0, 0], "donor": [9, 5], "size": [2, 3], "rot": 90}]}
    assert PF.target_rel(unit) == {(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)}
    assert PF.target_rel({**unit, "rows": [{**unit["rows"][0], "rot": 0}]}) >= {(0, 2), (1, 2)}   # 2x3 unturned
    monkeypatch.setattr(X, "block_parts", lambda disc=1, game=None: {(18, 1): frozenset({"sea4"})})
    monkeypatch.setattr(PF, "stock_ground", lambda *a, **k: {})
    got = PF.clean_sites(unit)
    assert (18, 0) not in got and (19, 0) in got                 # (18,1) is the rect's unwritten corner at (18,0)



# ---------------------------------------------------------------- the review of P6
def test_a_name_saved_during_this_save_s_staging_refuses_at_the_append_and_the_write_is_atomic(fake, monkeypatch):
    """Review P6: the name is checked again under the lock at write time (two saves may stage for minutes at once),
    and the file is replaced whole (a temp beside it, then a rename): no temp or lock is left behind."""
    stage = PF.stage

    def racing(prefab, cell, game=None, keep=False):
        if not fake["cat"].exists():                   # another save finishes while this one stages
            e, _a = PF.entry_from_rows("my-isle", [ISLE])
            e.update(fingerprint="e" * 64, fingerprint_cell=[1, 14], footprint=FOOT)
            fake["cat"].write_text(PF._USER_HEADER + PF.entry_toml(e), encoding="utf-8")
        return stage(prefab, cell, game=game, keep=keep)
    monkeypatch.setattr(PF, "stage", racing)
    with pytest.raises(PF.PrefabRefused, match="was saved while") as e:
        _save(fake)
    assert e.value.gate == "catalog" and [p["name"] for p in PF.load_catalog(fake["cat"])] == ["my-isle"]
    _save(fake, name="other-isle")
    assert [p["name"] for p in PF.load_catalog(fake["cat"])] == ["my-isle", "other-isle"]
    assert sorted(x.name for x in fake["cat"].parent.iterdir() if x.name.startswith("mine.toml")) == ["mine.toml"]


def test_a_lock_a_killed_save_left_is_taken_over_and_a_live_one_waits(fake, tmp_path, monkeypatch):
    import os
    import time
    lock = fake["cat"].with_name(fake["cat"].name + ".lock")
    lock.write_text("", encoding="utf-8")
    os.utime(lock, (time.time() - 120, time.time() - 120))
    _save(fake)                                                      # a 2-minute-old lock is a dead save's
    assert not lock.exists()
    lock.write_text("", encoding="utf-8")
    monkeypatch.setattr(time, "sleep", lambda s: None)
    with pytest.raises(PF.PrefabRefused, match="locked by another save"):
        _save(fake, name="second-isle")
    assert [p["name"] for p in PF.load_catalog(fake["cat"])] == ["my-isle"]


def test_the_cli_refuses_a_save_with_no_name_and_composes_steps_in_draft_order(tmp_path, monkeypatch):
    from ff9mapkit import cli
    seen = []
    monkeypatch.setattr(PF, "save", lambda name, rows, **kw: seen.append((rows, kw)) or {
        "ok": True, "name": name, "footprint": FOOT, "turns": [0]})
    _g, d = _draft_with(tmp_path, [{k: v for k, v in ISLE.items() if k not in ("step", "prefab_frame")},
                                   {k: v for k, v in PEAK.items() if k != "step"},
                                   {"table": "hill", "center": [650.0, -590.0]}])
    out = tmp_path / "v.json"
    assert cli.main(["world-prefab", "--save", "--from", str(d), "--report-json", str(out)]) == 1
    assert json.loads(out.read_text(encoding="utf-8"))["refused"]["gate"] == "catalog" and not seen
    assert cli.main(["world-prefab", "x", "--save", "--from", str(d), "--steps", "1,3,2"]) == 0
    assert [r["table"] for r in seen[-1][0]] == ["island", "mountain", "hill"]
    assert seen[-1][1]["source"].endswith("steps 1,2,3")
    assert cli.main(["world-prefab", "y", "--save", "--from", str(d), "--note=-wip draft"]) == 0
    assert seen[-1][1]["note"] == "-wip draft"


def test_the_dialog_s_note_may_start_with_a_dash():
    from ff9mapkit import cli
    from ff9mapkit.workspace import worldprefabsave as S
    argv = S.save_argv("G", "D", "mine", [0], note="-wip")
    assert "--note=-wip" in argv
    a = cli.build_parser().parse_args(argv[3:])
    assert a.note == "-wip"


def test_the_list_names_what_your_catalog_skipped(capsys):
    from ff9mapkit import cli
    user = PF.user_catalog()
    user.parent.mkdir(parents=True, exist_ok=True)
    user.write_text("[[prefab]\nbroken", encoding="utf-8")
    assert cli.main(["world-prefab", "--list"]) == 0
    out = capsys.readouterr()
    assert "desert-peak-isle" in out.out and "SKIPPED from your catalog" in out.err


def test_the_card_s_picker_survives_a_catalog_that_refuses_to_read(app, tmp_path):
    from .test_worldprefab import _card
    cat = tmp_path / "c.toml"
    e, _a = PF.entry_from_rows("my-isle", [ISLE])
    e.update(fingerprint="e" * 64, fingerprint_cell=[1, 14], footprint=FOOT)
    cat.write_text(PF.entry_toml(e), encoding="utf-8")
    tool, *_ = _card(app, tmp_path, cat, lambda k, a: None)
    assert tool.prefab_box.count() == 1
    cat.write_text("[[prefab]\nbroken", encoding="utf-8")
    with pytest.raises(ValueError):
        tool.reload_catalog()
    assert tool.prefab_box.count() == 1 and tool.donor() == "my-isle" and not tool.prefab_box.signalsBlocked()
