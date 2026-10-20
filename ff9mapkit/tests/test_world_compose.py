"""THE COMPOSED WORLD (audit rec 16): world-fuse's compose tables run existing verbs in the
fixed tier order (base mint -> relief -> nav-stamp), attribute every written file to the
table that produced it in world_manifest.json, and REFUSE to build over manifest-diverged
bytes without allow_overwrite. Plus the Tweak protocol: a malformed tweak fails AT THE CALL
SITE by name, and every shipped tweak class satisfies the contract.

Hermetic: every verb entry point is monkeypatched to record its call (and optionally write
files into a tmp mod tree); config.find_game_path is pinned to tmp."""
from __future__ import annotations

import json

import pytest

from ff9mapkit.world import fuse as FU, transplant as TR


def _pin_game(monkeypatch, tmp_path):
    from ff9mapkit import config
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    return tmp_path / "MOD" / "FF9_Data" / "WorldMap"


def _stub_verbs(monkeypatch, calls, writes=None):
    """Patch every compose entry point to append its (verb, key-args) to ``calls``.
    ``writes[label] = [(relpath, bytes)]`` makes that step write files into the mod tree."""
    from ff9mapkit import config
    from ff9mapkit.world import island as IS, interior as IN, coastnav as CN, rimretile as RR

    def _write(label):
        for (rel, data) in (writes or {}).get(label, ()):
            p = config.find_game_path(None) / "MOD" / "FF9_Data" / "WorldMap" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

    monkeypatch.setattr(IS, "landmass", lambda mf, **k: calls.append(("island", k.get("cell") or k.get("center")))
                        or _write("island") or {"blocks": [], "report": {}})
    monkeypatch.setattr(IN, "read_deployed_blocks", lambda *a, **k: {})
    monkeypatch.setattr(IN, "soup_from_blocks", lambda blocks: [])
    monkeypatch.setattr(IN, "carve_forest", lambda soup, **k: calls.append(("forest", k["donor"]))
                        or {"changed": {}, "center": (0, 0), "report": {}})
    monkeypatch.setattr(IN, "build_hill", lambda soup, **k: calls.append(("hill", k["radius"]))
                        or {"changed": {}, "center": (0, 0), "report": {}})
    monkeypatch.setattr(IN, "carve_mountain", lambda soup, **k: calls.append(("mountain", tuple(k["donor"])))
                        or {"changed": {}, "center": (0, 0), "report": {}})
    monkeypatch.setattr(IN, "census_gate", lambda *a, **k: None)
    monkeypatch.setattr(IN, "deploy_changed", lambda *a, **k: _write("relief") or [])
    monkeypatch.setattr(IN, "deploy_mountain_parts", lambda *a, **k: [])
    monkeypatch.setattr(CN, "stamp", lambda mf, **k: calls.append(("coastnav", k["policy"]))
                        or _write("coastnav") or {"cells": [], "totals": {}, "disc": k["disc"],
                                                  "policy": k["policy"], "backup_dir": None})
    monkeypatch.setattr(RR, "rim_retile", lambda mf, cells, donors, **k: calls.append(("rim_retile", tuple(donors)))
                        or {"before": {}, "after": {}, "written": [], "variants": 0,
                            "passes": 0, "quads": 0})


def test_tiers_run_in_the_fixed_order_not_document_order(monkeypatch, tmp_path):
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls)
    doc = {  # document order deliberately SCRAMBLED: nav first, relief, base last
        "coastnav": [{"policy": "land-anywhere"}],
        "hill": [{"near": [10.0, -10.0], "radius": 12.0}],
        "mountain": [{"near": [10.0, -10.0], "donor": "3-4,7"}],
        "island": [{"cell": [4, 2], "seed": 7}],
        "forest": [{"near": [10.0, -10.0], "donor": [5, 6]}],
    }
    out = FU.compose_layout("MOD", doc, dry_run=True)
    assert [c[0] for c in calls] == ["island", "mountain", "forest", "hill", "coastnav"]
    assert calls[0] == ("island", (4, 2)) and calls[1] == ("mountain", ((3, 7), (4, 7)))
    assert out["clean"] is True and out["dry_run"] is True


def test_unknown_table_key_refuses_by_name(monkeypatch, tmp_path):
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls)
    doc = {"island": [{"cell": [4, 2], "radius_units": 24}]}         # typo'd key
    out = FU.compose_layout("MOD", doc, dry_run=True)
    g = next(g for g in out["gates"] if g["gate"] == "island #0")
    assert g["ok"] is False and "radius_units" in g["error"] and "allowed" in g["error"]


def test_manifest_attributes_files_to_the_producing_table(monkeypatch, tmp_path):
    wm = _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls, writes={
        "island": [("Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh", b"ISLAND")],
        "relief": [("Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh", b"HILLED"),
                   ("Disc1/0_1/r2/Block[5][2] Terrain.ff9mesh", b"NEW")],
    })
    doc = {"island": [{"cell": [4, 2]}], "hill": [{"near": [10.0, -10.0]}]}
    out = FU.compose_layout("MOD", doc, dry_run=False)
    assert out["clean"] is True
    man = json.loads((wm / "world_manifest.json").read_text())
    by_table = {e["table"]: e["files"] for e in man["entries"]}
    assert list(by_table["island #0"]) == ["FF9_Data/WorldMap/Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh"]
    assert sorted(by_table["hill #0"]) == [                          # the hill CHANGED one + added one
        "FF9_Data/WorldMap/Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh",
        "FF9_Data/WorldMap/Disc1/0_1/r2/Block[5][2] Terrain.ff9mesh"]


def test_manifest_drift_refuses_and_allow_overwrite_builds(monkeypatch, tmp_path):
    """A manifest-recorded file whose on-disk md5 diverged (a hand edit, a foreign session)
    refuses the whole compose BEFORE any step runs; --allow-overwrite proceeds."""
    wm = _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls)
    rel = "Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh"
    f = wm / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"MINE")
    import hashlib
    (wm / "world_manifest.json").write_text(json.dumps(
        {"entries": [{"table": "island #0", "spec": {},
                      "files": {f"FF9_Data/WorldMap/{rel}": hashlib.md5(b"MINE").hexdigest()}}]}))
    doc = {"island": [{"cell": [4, 2]}]}
    out = FU.compose_layout("MOD", doc, dry_run=False)               # clean baseline: runs
    assert out["clean"] is True and calls
    calls.clear()
    f.write_bytes(b"FOREIGN EDIT")                                   # diverge the recorded file
    out = FU.compose_layout("MOD", doc, dry_run=False)
    assert out["clean"] is False and not calls                       # refused BEFORE any step
    drift = out["gates"][0]
    assert drift["gate"] == "manifest-drift" and drift["n_diverged"] == 1
    out = FU.compose_layout("MOD", doc, dry_run=False, allow_overwrite=True)
    assert out["clean"] is True and calls                            # the explicit override builds


def test_a_real_run_stops_at_the_first_failing_step(monkeypatch, tmp_path):
    """Later tiers read the deploys of earlier ones -- a failed base mint must SKIP the
    relief and nav steps on a real run, and say so per step."""
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls)
    from ff9mapkit.world import island as IS

    def boom(mf, **k):
        raise ValueError("gates refused the mint")
    monkeypatch.setattr(IS, "landmass", boom)
    doc = {"island": [{"cell": [4, 2]}], "coastnav": [{"policy": "land-anywhere"}]}
    out = FU.compose_layout("MOD", doc, dry_run=False)
    assert out["clean"] is False
    labels = {g["gate"]: g for g in out["gates"]}
    assert labels["island #0"]["ok"] is False
    assert "skipped" in labels["coastnav #0"] and ("coastnav", "land-anywhere") not in calls


@pytest.mark.parametrize("skip", [False, True])
def test_the_nav_rows_hand_the_runs_skip_mirror_to_their_verbs(monkeypatch, tmp_path, skip):
    """[[coastnav]] and [[rim_retile]] rewrite Disc1 sea in place, and each verb's own auto-mirror carries the bytes
    to Disc4 -- so the row must pass the run's skip_mirror through. It passed nothing, and the rows never mirrored
    (operators F6); the verb-level byte checks are test_world_coastnav's and test_world_rimretile's."""
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls)
    from ff9mapkit.world import coastnav as CN, rimretile as RR
    seen = {}

    def stamp(mf, **k):
        seen["coastnav"] = k
        return {"cells": [], "totals": {}, "disc": k["disc"], "policy": k["policy"], "backup_dir": None}

    def rim(mf, cells, donors, **k):
        seen["rim_retile"] = k
        return {"before": {}, "after": {}, "written": [], "variants": 0, "passes": 0, "quads": 0}
    monkeypatch.setattr(CN, "stamp", stamp)
    monkeypatch.setattr(RR, "rim_retile", rim)
    doc = {"coastnav": [{"cells": [[20, 1]]}], "rim_retile": [{"cells": [[20, 1]], "donor": [7, 17]}]}
    out = FU.compose_layout("MOD", doc, dry_run=False, skip_mirror=skip)
    assert out["clean"] is True, out["gates"]
    assert {t: k.get("skip_mirror", "not passed") for t, k in seen.items()} == {"coastnav": skip, "rim_retile": skip}
    assert seen["coastnav"]["deploy"] is True and seen["rim_retile"]["apply"] is True


def test_backup_files_never_enter_the_manifest(monkeypatch, tmp_path):
    wm = _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls, writes={
        "island": [("Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh", b"A"),
                   ("Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh.bak-20260805", b"OLD"),
                   ("Disc1/0_1/r2/Block[4][2] Sea1.ff9mesh.prerim", b"OLD2")]})
    out = FU.compose_layout("MOD", {"island": [{"cell": [4, 2]}]}, dry_run=False)
    assert out["clean"] is True
    man = json.loads((wm / "world_manifest.json").read_text())
    files = [p for e in man["entries"] for p in e["files"]]
    assert files == ["FF9_Data/WorldMap/Disc1/0_1/r2/Block[4][2] Terrain.ff9mesh"]


# --- the recipe speaks the CLI's shape handles (studies/overworld-editor/PLAN.md, habit 3) ---
#
# A compose row and the CLI verb must hand the carve the SAME arguments: the recipe is the
# editor's document, and "the CLI stays the byte oracle" holds only if a row can say whatever
# the CLI can. Both callers run for real down to the carve; the spy binds what each passed to
# the verb's own signature (defaults applied), so a caller that spells a default out and one
# that leaves it implicit still compare equal, and any handle one side drops does not.

_RELIEF = ("carve_forest", "carve_mountain", "build_hill")


def _spy_relief(monkeypatch):
    import inspect
    from ff9mapkit.world import interior as IN
    seen = []
    monkeypatch.setattr(IN, "read_deployed_blocks",
                        lambda mf, **k: seen.append(("read", mf, k)) or {})
    monkeypatch.setattr(IN, "soup_from_blocks", lambda blocks: "SOUP")
    for name in _RELIEF:
        sig = inspect.signature(getattr(IN, name))

        def spy(soup, _n=name, _sig=sig, **k):
            bound = _sig.bind(soup, **k)
            bound.apply_defaults()
            seen.append((_n, {a: v for a, v in bound.arguments.items() if a != "log"}))
            raise ValueError("spy: recorded")       # stop before either caller's report
        monkeypatch.setattr(IN, name, spy)
    return seen


@pytest.mark.parametrize("argv,table,row", [
    (["world-forest", "--center", "300,-500", "--donor", "3,12", "--spread", "1.25", "--rot", "30"],
     "forest", {"center": [300, -500], "donor": "3,12", "spread": 1.25, "rot": 30}),
    (["world-forest", "--center", "300,-500", "--donor", "19,8", "--rot", "90"],
     "forest", {"center": [300, -500], "donor": [19, 8], "rot": 90}),
    (["world-forest", "--near", "300,-500"],                       # every default, no donor key
     "forest", {"near": [300, -500]}),
    (["world-mountain", "--center", "300,-500", "--donor", "19,3", "--ground", "desert",
      "--rot", "200", "--rock-height", "1.5", "--spread", "1.25"],
     "mountain", {"center": [300, -500], "donor": "19,3", "ground": "desert", "rot": 200,
                  "rock_height": 1.5, "spread": 1.25}),
    (["world-mountain", "--near", "300,-500", "--donor", "10,5-6", "--reach", "128"],
     "mountain", {"near": [300, -500], "donor": "10,5-6", "reach": 128}),
    (["world-mountain", "--near", "300,-500"],                     # --near scans the four turns
     "mountain", {"near": [300, -500]}),
    (["world-hill", "--center", "300,-500", "--height", "3", "--radius", "14"],
     "hill", {"center": [300, -500], "height": 3, "radius": 14}),
])
def test_a_compose_row_carves_what_the_cli_carves(monkeypatch, tmp_path, argv, table, row):
    from ff9mapkit import cli
    _pin_game(monkeypatch, tmp_path)
    seen = _spy_relief(monkeypatch)
    assert cli.main([*argv, "--mod-folder", "MOD", "--dry-run"]) == 2   # the spy's refusal
    via_cli = list(seen)
    seen.clear()
    out = FU.compose_layout("MOD", {table: [row]}, dry_run=True)
    assert out["gates"][-1]["error"] == "spy: recorded"                # reached the carve
    assert len(via_cli) == 2 and seen == via_cli                       # same read, same carve


def test_a_compose_row_refuses_past_a_ceiling_as_the_cli_does(monkeypatch, tmp_path, capsys):
    """The handles pass through unclamped: the verb owns the proven ceiling
    (FOREST_SPREAD_MAX), so the recipe and the CLI refuse with the same words."""
    from ff9mapkit import cli
    from ff9mapkit.world import interior as IN
    _pin_game(monkeypatch, tmp_path)
    monkeypatch.setattr(IN, "read_deployed_blocks", lambda mf, **k: {})
    monkeypatch.setattr(IN, "soup_from_blocks",
                        lambda blocks: {"pos": [], "tris": [], "meta": [], "nrm": []})
    too_wide = IN.FOREST_SPREAD_MAX + 0.1
    assert cli.main(["world-forest", "--mod-folder", "MOD", "--near", "300,-500",
                     "--spread", str(too_wide), "--dry-run"]) == 2
    said = capsys.readouterr().err.strip()
    out = FU.compose_layout("MOD", {"forest": [{"near": [300, -500], "spread": too_wide}]},
                            dry_run=True)
    assert "outside 1.0..1.5" in said and out["gates"][-1]["error"] == said
    out = FU.compose_layout("MOD", {"hill": [{"near": [300, -500], "rot": 30}]}, dry_run=True)
    assert "'rot'" in out["gates"][-1]["error"]                        # a hill has no angle


# --- the Tweak protocol (rec 16, finding 3's cheap half) ---------------------------------

def test_every_shipped_tweak_class_satisfies_the_protocol():
    for cls in (TR.DropTris, TR.EmitTris, TR.SeaBump, TR.RowInsert, TR.RowInsertZ,
                TR.VertexDisplace, TR.TileRetexture, TR.PatchRecover, TR.GroundRetile,
                TR.SpillClip, TR.SpillClipZ):
        missing = [a for a in ("apply", "emit", "gate") if not hasattr(cls, a)]
        assert not missing, (cls.__name__, missing)


def test_a_malformed_tweak_fails_at_the_call_site_by_name(monkeypatch):
    class NotATweak:
        part = "terrain"

        def apply(self, part, poly):
            return poly
        # no emit(), no gate()

    with pytest.raises(TypeError) as e:
        TR._check_tweak([NotATweak()])
    assert "NotATweak" in str(e.value) and "emit" in str(e.value) and "gate" in str(e.value)
    from tests.test_world_transplant import _fake_world, _island_donor  # reuse the harness
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    # match= is load-bearing: without it ANY TypeError from these three entry points (a signature
    # slip, a bad kwarg) reads as "the protocol check fired", which is the one thing being asserted.
    named = r"tweak #0 \(NotATweak\) does not satisfy the Tweak protocol"
    with pytest.raises(TypeError, match=named):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True,
                      tweaks=[NotATweak()])
    with pytest.raises(TypeError, match=named):
        TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(1, 1), dry_run=True,
                             tweaks=[NotATweak()])
    with pytest.raises(TypeError, match=named):
        TR.morph_in_place("MOD", cell=(1, 1), tweaks=[NotATweak()], dry_run=True)


# ---- the [[river]] row (RUNG5.md 5b): world-river's one pipeline, run from a recipe ----------------------------------

def _stub_river(monkeypatch, calls, *, red=()):
    """``river.deploy`` replaced by a recorder returning the shape the runner reads (the pipeline itself is
    test_world_river's)."""
    from types import SimpleNamespace
    from ff9mapkit.world import river as RV

    def deploy(mod_folder, **kw):
        calls.append(("river", kw))
        off = kw["offset"] or (512.0, 128.0)
        return SimpleNamespace(comp=SimpleNamespace(offset=off), cells=[(23, 12), (0, 11), (1, 11)],
                               red=list(red), rep={"files": 132}, written=[] if kw["dry_run"] else ["f"] * 132)
    monkeypatch.setattr(RV, "deploy", deploy)


def test_the_river_row_runs_in_the_base_tier_before_relief(monkeypatch, tmp_path, capsys):
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls)
    _stub_river(monkeypatch, calls)
    doc = {"forest": [{"near": [49.0, -824.0]}], "river": [{"at": [512, 128], "apron": False, "area": 3}],
           "island": [{"cell": [4, 2]}]}
    out = FU.compose_layout("MOD", doc, dry_run=False)
    assert [c[0] for c in calls] == ["island", "river", "forest"] and out["clean"] is True
    kw = calls[1][1]
    assert (kw["offset"], kw["apron"], kw["area"], kw["dry_run"], kw["skip_mirror"]) == ((512.0, 128.0), False, 3,
                                                                                         False, False)
    assert kw["donor"].name == "cluster-c"                                   # the default donor
    assert "[[river]] cluster-c: at = [512, 128], 3 cells, deployed 132 files" in capsys.readouterr().out
    assert FU.COMPOSE_TIERS[0] == ("placement", "island", "river")


@pytest.mark.parametrize("row, kwargs, error", [
    ({"at": [512, 128], "rot": 90}, {}, "unknown key(s) ['rot']"),
    ({}, {}, "[[river]] needs at = [dx, dz]"),
    ({"at": "auto"}, {}, 'at = "auto" resolves on a dry run only'),
    ({"at": [512, 128], "donor": "cluster-d"}, {}, "is not a river donor"),
    ({"at": [512, 128]}, {"target_disc": 4}, "[[river]] writes disc 1 lod 0_1"),
])
def test_the_river_row_refuses_by_name(monkeypatch, tmp_path, row, kwargs, error):
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_river(monkeypatch, calls)
    out = FU.compose_layout("MOD", {"river": [row]}, dry_run=False, **kwargs)
    g = next(g for g in out["gates"] if g["gate"] == "river #0")
    assert g["ok"] is False and error in g["error"] and calls == []         # refused before the pipeline ran


def test_the_river_row_auto_resolves_on_a_dry_run_and_red_gates_refuse(monkeypatch, tmp_path, capsys):
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_river(monkeypatch, calls)
    out = FU.compose_layout("MOD", {"river": [{"at": "auto"}]}, dry_run=True)
    assert out["clean"] is True and calls[0][1]["offset"] is None and calls[0][1]["dry_run"] is True
    assert "at = [512, 128], 3 cells, would deploy 132 files" in capsys.readouterr().out   # the placement to copy
    _stub_river(monkeypatch, calls, red=[("B1", "B1: the stack already overrides these cells")])
    out = FU.compose_layout("MOD", {"river": [{"at": "512,128"}]}, dry_run=False, allow_overwrite=True)
    g = next(g for g in out["gates"] if g["gate"] == "river #0")
    assert g["ok"] is False and "world-river refused (at = [512, 128], 3 cells) -- B1: the stack" in g["error"]


def test_a_dry_run_names_why_a_relief_row_cannot_read_the_river_island(monkeypatch, tmp_path):
    """A dry run deploys nothing, so a relief row aimed at the island the same recipe's base tier would mint reads the
    folder as it is now and fails: the failure says so, by the base step's name."""
    from ff9mapkit.world import interior as IN
    _pin_game(monkeypatch, tmp_path)
    calls = []
    _stub_verbs(monkeypatch, calls)
    _stub_river(monkeypatch, calls)

    def no_island(soup, **k):
        raise ValueError("the forest footprint needs deployed Terrain overrides -- mint a bigger island first")
    monkeypatch.setattr(IN, "carve_forest", no_island)
    out = FU.compose_layout("MOD", {"river": [{"at": "auto"}], "forest": [{"near": [49.0, -824.0]}]}, dry_run=True)
    g = next(g for g in out["gates"] if g["gate"] == "forest #0")
    assert g["ok"] is False and "mint a bigger island first [dry run: river #0 in this recipe was not deployed" \
        in g["error"]
    out = FU.compose_layout("MOD", {"forest": [{"near": [49.0, -824.0]}]}, dry_run=True)
    assert "[dry run:" not in next(g for g in out["gates"] if g["gate"] == "forest #0")["error"]   # no base, no hint
