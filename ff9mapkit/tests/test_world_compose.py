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
