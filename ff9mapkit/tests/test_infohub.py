"""The Info Hub spine: browse / detail / snippet over the catalogs + archetypes. Pure (no game install)."""
from ff9mapkit import campaign, infohub


def test_browse_finds_each_named_kind():
    for q, kind in {"garnet": "archetype", "lich": "creature",
                    "save_point": "composite", "chest": "prop"}.items():
        hits = infohub.browse(q)
        assert any(e.name == q and e.kind == kind for e in hits), (q, kind, [e.name for e in hits[:6]])


def test_browse_finds_raw_model_item_scene():
    assert any(e.name == "GEO_NPC_F0_BMG" for e in infohub.browse("BMG", kinds=["model"]))
    assert infohub.browse("potion", kinds=["item"])
    assert len(infohub.browse("", kinds=["scene"], limit=5)) == 5


def test_browse_kind_filter_and_limit():
    only = infohub.browse("", kinds=["prop"], limit=10)
    assert len(only) == 10 and all(e.kind == "prop" for e in only)


def test_browse_matches_by_model_name():
    # the black_mage archetype is reachable by its GEO model name, not just its friendly name
    assert any(e.kind == "archetype" and e.name == "black_mage"
               for e in infohub.browse("GEO_NPC_F0_BMG"))


def test_find_exact_and_kind():
    assert infohub.find("garnet", kind="archetype").kind == "archetype"
    assert infohub.find("garnet", kind="prop") is None
    assert infohub.find("nope_not_a_thing") is None


def test_detail_archetype_movement_anims_snippet_aliases():
    d = infohub.detail(infohub.find("garnet", kind="archetype"))
    assert d.model and d.model.startswith("GEO_")
    assert d.movement and set(d.movement) == {"stand", "walk", "run", "left", "right"}
    assert d.anims                                                  # a full gesture list
    assert d.snippet.startswith("[[npc]]") and 'archetype = "garnet"' in d.snippet
    assert "dagger" in d.aliases                                    # same model id as garnet


def test_detail_prop_has_pose_and_prop_snippet():
    d = infohub.detail(infohub.find("chest", kind="prop"))
    assert d.model and d.model.startswith("GEO_ACC_")
    assert any(label == "pose" for label, _ in d.facts)
    assert d.snippet.startswith("[[prop]]") and 'prop = "chest"' in d.snippet


def test_detail_composite_lists_parts():
    d = infohub.detail(infohub.find("save_point", kind="composite"))
    assert len(d.parts) >= 2
    for model_name, pose, dx, dz in d.parts:
        assert isinstance(model_name, str) and isinstance(pose, int)
    assert 'prop = "save_point"' in d.snippet


def test_detail_usage_hook_is_optional():
    e = infohub.find("black_mage", kind="archetype")
    assert infohub.detail(e).locations is None                     # install-free by default
    assert infohub.detail(e, usage_fn=lambda mid: [(401, "Dali/Underground")]).locations \
        == [(401, "Dali/Underground")]


def test_snippet_forms_per_kind():
    assert infohub.snippet(infohub.find("lich")).startswith("[[npc]]")        # creature -> npc block
    item = next(e for e in infohub.browse("potion", kinds=["item"]))
    assert infohub.snippet(item).startswith("give_item = [")
    acc = infohub.find("GEO_ACC_F0_CHS", kind="model")                        # a raw ACC model -> prop block
    if acc:
        assert infohub.snippet(acc).startswith("[[prop]]")
    scene = infohub.browse("", kinds=["scene"], limit=1)[0]                   # a battle scene -> [encounter]
    assert infohub.snippet(scene).startswith("[encounter]")


def test_browse_matches_by_comment_description():
    # the rich comment descriptions are searchable: "box" -> shelf (BBX, "...shelf / box"); "barrel" -> cask
    assert any(e.name == "shelf" for e in infohub.browse("box")), "comment description not searched"
    assert any(e.name == "cask" for e in infohub.browse("barrel"))


def test_browse_finds_model_by_friendly_name():
    # a character's MODEL is reachable by the friendly name folded into its summary, not just the GEO token
    assert any(e.kind == "model" and e.name == "GEO_MAIN_F0_ZDN" for e in infohub.browse("zidane"))


def test_crate_alias_resolves_to_the_storage_prop():
    from ff9mapkit import prop_archetypes as PA
    assert any(e.name == "crate" for e in infohub.browse("crate"))      # the natural word resolves
    assert PA.resolve("crate") == PA.resolve("cask")                    # -> FF9's barrel/cask


def test_preview_field_toml_places_selection(tmp_path):
    art = tmp_path / "art"
    npc = infohub.preview_field_toml([infohub.find("black_mage")], art)
    assert npc and "[[npc]]" in npc and 'archetype = "black_mage"' in npc
    assert "[camera.scroll]" in npc                                     # the scrolling arena scene
    assert (art / "back.png").exists() and (art / "floor.png").exists()  # checkerboard art was written
    prop = infohub.preview_field_toml([infohub.find("chest")], art)
    assert "[[prop]]" in prop and 'prop = "chest"' in prop
    item = next(e for e in infohub.browse("potion", kinds=["item"]))
    assert infohub.preview_field_toml([item], art) is None              # items aren't field objects


def test_browse_limit_none_is_uncapped():
    assert len(infohub.browse("", limit=None)) > 1000        # all ~2000+ entries, no 500-row cap
    assert len(infohub.browse("", limit=10)) == 10           # an explicit cap still applies


# ---- campaign context: browse/detail over the members of a campaign ---------------------
def _demo_campaign():
    members = [campaign.Member(300, 6000, "IC_ENT", "borrow", 11, "", "IC_ENT/IC_ENT.field.toml", False),
               campaign.Member(301, 6001, "IC_COR", "editable", 5, "", "IC_COR/IC_COR.field.toml", True)]
    return campaign.CampaignPlan(
        name="ICE", mod_folder="M", id_base=6000, flag_base=8300, flags_per_field=64,
        entry_name="IC_ENT", entry_entrance=0, members=members,
        edges=[{"frm": "IC_ENT", "to": "IC_COR", "entrance": 2, "story_conditional": False}],
        seams=[{"frm": "IC_COR", "to_real": "WORLDMAP", "kind": "overworld", "note": "", "to_member": None}])


def test_browse_no_campaign_context_has_no_field_kind():
    assert not any(e.kind == "field" for e in infohub.browse("", limit=None))   # regression: unchanged


def test_browse_campaign_context_lists_members_first():
    plan = _demo_campaign()
    hits = infohub.browse("", campaign_context=plan, limit=None)
    assert {e.name for e in hits if e.kind == "field"} == {"IC_ENT", "IC_COR"}
    assert hits[0].kind == "field"                                       # members are listed FIRST
    assert any(e.kind == "field" and e.name == "IC_COR"                  # searchable by name
               for e in infohub.browse("IC_COR", campaign_context=plan))
    only = infohub.browse("", kinds=["field"], campaign_context=plan)    # kind filter
    assert {e.name for e in only} == {"IC_ENT", "IC_COR"}


def test_detail_field_resolves_doors_seams_flags():
    plan = _demo_campaign()
    ent = next(e for e in infohub.browse("IC_ENT", kinds=["field"], campaign_context=plan))
    d = infohub.detail(ent, campaign_context=plan)
    assert d.kind == "field"
    assert ("door", "-> IC_COR (entrance 2)") in d.facts
    assert ("role", "campaign entry") in d.facts
    assert infohub.snippet(ent).startswith("# campaign field")
    cor = next(e for e in infohub.browse("IC_COR", kinds=["field"], campaign_context=plan))
    dc = infohub.detail(cor, campaign_context=plan)
    assert any(lbl == "entered_from" for lbl, _ in dc.facts)
    assert any(lbl.startswith("seam:") for lbl, _ in dc.facts)
    assert any(lbl == "needs_export" for lbl, _ in dc.facts)             # IC_COR is artless


def test_detail_field_without_context_is_minimal():
    plan = _demo_campaign()
    ent = next(e for e in infohub.browse("IC_ENT", kinds=["field"], campaign_context=plan))
    d = infohub.detail(ent)                                              # no campaign_context -> graceful
    assert d.kind == "field" and ("id", "6000") in d.facts


# ---- F2: campaign shared story flags as a browsable 'flag' kind --------------------------
def test_browse_flag_kind_via_campaign_context():
    plan = _demo_campaign()
    plan.flags = [{"name": "boss_dead", "index": 8700}]
    hits = infohub.browse("", kinds=["flag"], campaign_context=plan)
    assert {e.name for e in hits} == {"boss_dead"} and hits[0].ident == 8700
    d = infohub.detail(hits[0], campaign_context=plan)
    assert d.kind == "flag" and any(lbl == "index" for lbl, _ in d.facts)
    assert infohub.snippet(hits[0]) == 'requires_flag = "boss_dead"'


def test_flag_kind_absent_without_campaign_context():
    assert not any(e.kind == "flag" for e in infohub.browse("", limit=None))   # regression: unchanged


# --- F3: the FF9 story-flag registry as a reference kind (always available, install-free) ---
def test_storyflag_registry_is_browsable():
    # a scenario milestone is searchable by its beat AND its value; the chest band + safe band are findable
    ice = infohub.browse("ice cavern", kinds=["storyflag"])
    assert any(e.ident == 2500 for e in ice), [e.name for e in ice]
    assert any(e.name == "chest_opened" for e in infohub.browse("chest", kinds=["storyflag"]))
    assert any(e.name == "safe_custom" for e in infohub.browse("safe custom", kinds=["storyflag"]))
    assert any(e.name == "ScenarioCounter" for e in infohub.browse("scenariocounter", kinds=["storyflag"]))


def test_storyflag_detail_and_snippet():
    band = infohub.find("safe_custom", "storyflag")
    d = infohub.detail(band)
    assert d.kind == "storyflag" and any(lbl == "location" for lbl, _ in d.facts)
    assert "[[flag]]" in infohub.snippet(band) and "8512" in infohub.snippet(band)
    scen = next(e for e in infohub.browse("ice cavern", kinds=["storyflag"]) if e.ident == 2500)
    assert "save-edit" in infohub.snippet(scen) and "2500" in infohub.snippet(scen)
    chest = infohub.find("chest_opened", "storyflag")
    assert any("reserved" in str(v).lower() for _, v in infohub.detail(chest).facts)


def test_storyflag_in_default_browse_but_a_distinct_kind():
    assert any(e.kind == "storyflag" for e in infohub.browse("", limit=None))   # in the unified search
    assert "storyflag" in infohub.KINDS and "flag" not in infohub.KINDS         # registry kind != campaign 'flag'
