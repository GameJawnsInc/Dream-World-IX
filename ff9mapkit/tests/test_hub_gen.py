"""World-Hub generator: a journeys.toml -> a hub field.toml (the "hardcoded MVP -> generator" step).

All offline -- the generator is pure codegen (no game install). The emitted hub uses [camera] borrow, so
validate() only checks the .bgx EXISTS (build.py:391); the tests touch a dummy one beside the toml. The
generated hub is asserted logically identical to the in-game-proven hand-authored examples/world_hub.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from ff9mapkit import build, hub

EXAMPLES = Path(__file__).parent.parent / "examples" / "world_hub"
JOURNEYS = EXAMPLES / "journeys.toml"


def _game_ready():
    """True if the FF9 install + UnityPy are available (gates the camera-extraction tests)."""
    try:
        from ff9mapkit.extract import EventBundle
        EventBundle()
        return True
    except Exception:
        return False


def _spec(**hub_over):
    """A minimal valid HubSpec (one journey), with per-test [hub] overrides."""
    base = dict(name="WORLD_HUB", id=4500, area=21, borrow_bg="GRGR_MAP420_GR_CEN_0",
                camera="camera_hub.bgx", text_block=8,
                journeys=[hub.Journey("j1", "Journey One", 4501, 2600)])
    base.update(hub_over)
    return hub.HubSpec(**base)


def _emit_and_load(tmp_path, spec):
    """Render spec -> a field.toml in tmp_path (+ a dummy borrow .bgx so validate() passes) -> FieldProject."""
    (tmp_path / spec.camera).write_bytes(b"")            # validate() only checks the borrow file EXISTS
    p = tmp_path / "hub.field.toml"
    p.write_text(hub.render_hub_field_toml(spec), encoding="utf-8", newline="\n")
    return build.FieldProject.load(p), p


# ---- load ----
def test_load_journeys_parses_the_example_registry():
    spec = hub.load_journeys(JOURNEYS)
    assert spec.name == "WORLD_HUB" and spec.id == 4500 and spec.area == 21
    assert spec.borrow_bg == "GRGR_MAP420_GR_CEN_0" and spec.text_block == 8
    assert spec.player_model == 220 and spec.narrator == "Stiltzkin"
    # The example points at REAL verbatim forks already deployed in stacked folders (not stubs):
    # Dali = the DALI_CAPSTONE chain entry (4100, FF9CustomMap-sf) seeded to its "waking up" beat;
    # Treno = a single-field verbatim fork of the Treno Pub (4501, FF9CustomMap-ow). Thin -- {entry,seed}.
    assert [(j.name, j.title, j.entry, j.set_scenario) for j in spec.journeys] == [
        ("dali", "The Village of Dali", 4100, 2600),
        ("treno", "Treno, City of Nobles", 4501, 7550)]


def test_load_missing_hub_table_or_keys_raises(tmp_path):
    cases = [
        ('[[journey]]\nname="x"\nentry=4501\n', "no [hub] table"),
        ('[hub]\nid=4500\n', "missing hub.name"),
        ('[hub]\nname="H"\n', "missing hub.id"),
        ('[hub]\nname="H"\nid=4500\n[[journey]]\nname="x"\n', "journey missing entry"),
        ('[hub]\nname="H"\nid=4500\n[[journey]]\nentry=4501\n', "journey missing name"),
    ]
    for i, (toml, _why) in enumerate(cases):
        p = tmp_path / f"case{i}.toml"
        p.write_text(toml, encoding="utf-8")
        with pytest.raises(hub.HubError):
            hub.load_journeys(p)


def test_journey_title_defaults_to_humanized_name(tmp_path):
    p = tmp_path / "j.toml"
    p.write_text('[hub]\nname="H"\nid=4500\nborrow_bg="X"\n[[journey]]\nname="black_mage_village"\nentry=4501\n',
                 encoding="utf-8")
    spec = hub.load_journeys(p)
    assert spec.journeys[0].title == "Black Mage Village"


# ---- render: the emitted field.toml loads + validates clean ----
def test_render_emits_loadable_validatable_field(tmp_path):
    spec = _spec(journeys=[hub.Journey("a", "Alpha", 4501, 2600), hub.Journey("b", "Beta", 4502)])
    proj, _ = _emit_and_load(tmp_path, spec)
    assert build.validate(proj) == []
    f = proj.raw
    assert f["field"]["id"] == 4500 and f["field"]["borrow_bg"] == "GRGR_MAP420_GR_CEN_0"
    assert f["player"]["model"] == 220
    ch = f["choice"][0]
    assert ch["npc"] == "Stiltzkin"
    # options: one per journey (with warp/seed) + a trailing no-warp stay row; cancel points at it
    opts = ch["options"]
    assert [o.get("warp") for o in opts] == [4501, 4502, None]
    assert opts[0]["set_scenario"] == 2600 and "set_scenario" not in opts[1]
    assert ch["cancel"] == 2 and "warp" not in opts[2]


def test_render_set_scenario_only_when_present(tmp_path):
    spec = _spec(journeys=[hub.Journey("a", "A", 4501, None)])
    proj, _ = _emit_and_load(tmp_path, spec)
    assert "set_scenario" not in proj.raw["choice"][0]["options"][0]


def test_render_player_model_geo_name_is_quoted(tmp_path):
    spec = _spec(player_model="GEO_NPC_F0_MOG", journeys=[hub.Journey("a", "A", 4501)])
    text = hub.render_hub_field_toml(spec)
    assert 'model = "GEO_NPC_F0_MOG"' in text          # a GEO name -> quoted; a raw id -> bare
    assert tomllib.loads(text)["player"]["model"] == "GEO_NPC_F0_MOG"


# ---- equivalence: gen-hub of the example == the hand-authored proven hub ----
def test_generated_hub_matches_handauthored_example(tmp_path):
    out = tmp_path / "gen.field.toml"
    info = hub.generate(JOURNEYS, out_path=out)
    gen = tomllib.loads(out.read_text(encoding="utf-8"))
    ref = tomllib.loads((EXAMPLES / "hub.field.toml").read_text(encoding="utf-8"))
    # the in-game-relevant content is identical (field identity, backdrop, the Moogle PC + narrator, the menu)
    assert gen["field"]["id"] == ref["field"]["id"]
    assert gen["field"]["name"] == ref["field"]["name"]
    assert gen["field"]["borrow_bg"] == ref["field"]["borrow_bg"]
    assert gen["field"]["area"] == ref["field"]["area"]
    assert gen["field"]["text_block"] == ref["field"]["text_block"]
    assert gen["camera"]["borrow"] == ref["camera"]["borrow"]
    assert gen["player"]["model"] == ref["player"]["model"] == 220
    assert gen["player"]["spawn"] == ref["player"]["spawn"]
    assert gen["npc"][0]["name"] == ref["npc"][0]["name"]
    assert gen["npc"][0]["model"] == ref["npc"][0]["model"]
    gc, rc = gen["choice"][0], ref["choice"][0]
    assert gc["prompt"] == rc["prompt"] and gc["cancel"] == rc["cancel"]
    norm = lambda os: [(o.get("text"), o.get("warp"), o.get("set_scenario")) for o in os]
    assert norm(gc["options"]) == norm(rc["options"])
    assert info["journeys"] == 2


# ---- validate ----
def test_validate_clean_spec_has_no_errors():
    errors, _ = hub.validate_hub(_spec())
    assert errors == []


def test_validate_rejects_missing_borrow_dup_names_bad_ids_and_scenario():
    errors, _ = hub.validate_hub(_spec(borrow_bg=""))
    assert any("borrow_bg is required" in e for e in errors)

    errors, _ = hub.validate_hub(_spec(id=70))
    assert any("id 70 out of range" in e for e in errors)

    errors, _ = hub.validate_hub(_spec(area=1))
    assert any("area" in e and ">= 10" in e for e in errors)

    dup = _spec(journeys=[hub.Journey("x", "X", 4501), hub.Journey("x", "Y", 4502)])
    errors, _ = hub.validate_hub(dup)
    assert any("duplicated" in e for e in errors)

    bad_entry = _spec(journeys=[hub.Journey("x", "X", 0)])
    errors, _ = hub.validate_hub(bad_entry)
    assert any("must be a positive field id" in e for e in errors)

    bad_sc = _spec(journeys=[hub.Journey("x", "X", 4501, 99999)])
    errors, _ = hub.validate_hub(bad_sc)
    assert any("set_scenario" in e and "out of range" in e for e in errors)

    no_j = _spec(journeys=[])
    errors, _ = hub.validate_hub(no_j)
    assert any("at least one [[journey]]" in e for e in errors)


def test_validate_warns_text_block_1073_and_paging():
    _, warnings = hub.validate_hub(_spec(text_block=1073))
    assert any("1073" in w and "SHADOWED" in w for w in warnings)

    many = _spec(journeys=[hub.Journey(f"j{i}", f"J{i}", 4501 + i) for i in range(hub.PAGING_SOFT_MAX + 1)])
    _, warnings = hub.validate_hub(many)
    assert any("menu rows" in w for w in warnings)


def test_validate_warns_self_warp():
    _, warnings = hub.validate_hub(_spec(id=4500, journeys=[hub.Journey("x", "X", 4500)]))
    assert any("hub itself" in w for w in warnings)


# ---- generate: writes the file, raises on a bad spec ----
def test_generate_writes_default_path_beside_registry(tmp_path):
    reg = tmp_path / "journeys.toml"
    reg.write_text('[hub]\nname="H"\nid=4500\nborrow_bg="X"\ncamera="c.bgx"\n'
                   '[[journey]]\nname="a"\ntitle="A"\nentry=4501\n', encoding="utf-8")
    info = hub.generate(reg)
    assert info["path"] == tmp_path / "hub.field.toml" and info["path"].is_file()


def test_generate_raises_on_validation_error(tmp_path):
    reg = tmp_path / "j.toml"
    reg.write_text('[hub]\nname="H"\nid=4500\n[[journey]]\nname="a"\nentry=4501\n', encoding="utf-8")  # no borrow_bg
    with pytest.raises(hub.HubError):
        hub.generate(reg)


# ---- CLI ----
def test_cli_gen_hub_emits_field_toml(tmp_path):
    from ff9mapkit.cli import main
    out = tmp_path / "hub.field.toml"
    rc = main(["gen-hub", str(JOURNEYS), "--out", str(out)])
    assert rc == 0 and out.is_file()
    assert tomllib.loads(out.read_text(encoding="utf-8"))["field"]["id"] == 4500


def test_cli_gen_hub_validation_error_returns_2(tmp_path):
    from ff9mapkit.cli import main
    reg = tmp_path / "j.toml"
    reg.write_text('[hub]\nname="H"\nid=70\nborrow_bg="X"\ncamera="c.bgx"\n'
                   '[[journey]]\nname="a"\nentry=4501\n', encoding="utf-8")          # id 70 out of range
    assert main(["gen-hub", str(reg)]) == 2


# ---- the centralized camera cache (--extract-camera / extract-field) ----
def test_borrow_field_parsed_and_not_emitted():
    spec = hub.load_journeys(JOURNEYS)
    assert spec.borrow_field == 950
    assert "borrow_field" not in hub.render_hub_field_toml(spec)   # hub metadata, NOT a field.toml key


def test_validate_rejects_bad_borrow_field():
    errors, _ = hub.validate_hub(_spec(borrow_field=-5))
    assert any("borrow_field" in e for e in errors)
    assert hub.validate_hub(_spec(borrow_field=950))[0] == []      # a valid id is clean


def test_generate_extract_camera_without_borrow_field_raises(tmp_path):
    reg = tmp_path / "j.toml"
    reg.write_text('[hub]\nname="H"\nid=4500\nborrow_bg="X"\ncamera="c.bgx"\n'
                   '[[journey]]\nname="a"\nentry=4501\n', encoding="utf-8")          # no borrow_field
    with pytest.raises(hub.HubError):
        hub.generate(reg, out_path=tmp_path / "o.field.toml", extract_camera=True)


def test_cache_dir_resolution(tmp_path, monkeypatch):
    from ff9mapkit import provision
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    assert provision.cache_dir() == tmp_path
    assert provision.field_cache_dir(950) == tmp_path / "fields" / "950"
    monkeypatch.delenv("FF9MAPKIT_DATA", raising=False)
    assert provision.cache_dir().name == ".ff9mapkit-cache"        # the gitignored kit-root default


def test_relpath_is_forward_slash_repo_relative(tmp_path):
    cam = tmp_path / "cache" / "fields" / "950" / "camera.bgx"
    rp = hub._relpath(cam, tmp_path / "examples" / "world_hub")
    assert rp == "../../cache/fields/950/camera.bgx" and "\\" not in rp


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_extract_camera_populates_cache_and_wires_toml(tmp_path, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path / "cache"))   # cache into tmp, not the real one
    out = tmp_path / "hub.field.toml"
    info = hub.generate(JOURNEYS, out_path=out, extract_camera=True)
    ex = info["extracted"]
    assert ex and ex["camera"].is_file()                           # the camera landed in the cache
    assert ex["camera"].parent == (tmp_path / "cache" / "fields" / "950")
    gen = tomllib.loads(out.read_text(encoding="utf-8"))
    assert gen["camera"]["borrow"].endswith("camera.bgx")          # the emitted toml points at the cache copy
    proj = build.FieldProject.load(out)
    assert build.validate(proj) == []                              # resolves the cached camera -> clean
    # second call reuses the cache (idempotent -- no re-extract)
    assert hub.generate(JOURNEYS, out_path=out, extract_camera=True)["extracted"]["cached"] is True


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_cli_extract_field_caches(tmp_path, monkeypatch):
    from ff9mapkit.cli import main
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path / "cache"))
    assert main(["extract-field", "950"]) == 0
    assert (tmp_path / "cache" / "fields" / "950" / "camera.bgx").is_file()
