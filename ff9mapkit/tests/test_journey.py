"""Tests for the multi-campaign journey ASSEMBLER (journey.py) -- the offline core.

All pure: fixture campaigns are written by hand (minimal valid campaign.toml + member field.tomls), so the
namespace guarantee (global id disjointness across every campaign of every journey), lint, resolution, and
the hub fold-in are exercised with NO game install. The deploy ORCHESTRATION (build each campaign at its
band, wire links, deploy the hub) is the in-game step and is not tested here."""

import tomllib

import pytest

from ff9mapkit import campaign, hub, journey
from ff9mapkit.campaign import CampaignPlan, Member
from ff9mapkit.flags import CHOICE_SCRATCH_FLOOR, FIRST_SAFE_FLAG


# ---- fixture builders (no game) ---------------------------------------------------------
def _make_campaign(root, folder, *, members, id_base, flags_per_field=64, entry=None,
                   seams=None, edges=None, mod_folder="FF9CustomMap-test"):
    """Write a minimal but VALID campaign folder: campaign.toml + a parseable field.toml per member."""
    cdir = root / folder
    cdir.mkdir(parents=True, exist_ok=True)
    plan = CampaignPlan(name=folder, mod_folder=mod_folder, id_base=id_base, flag_base=FIRST_SAFE_FLAG,
                        flags_per_field=flags_per_field, entry_name=entry or members[0], entry_entrance=0)
    for i, name in enumerate(members):
        mdir = cdir / name
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / f"{name}.field.toml").write_text(
            f'[field]\nid = {id_base + i}\nname = "{name}"\narea = 11\ntext_block = 1073\n',
            encoding="utf-8", newline="\n")
        plan.members.append(Member(real_id=0, new_id=id_base + i, name=name, mode="native",
                                   src_area=11, folder="", toml_rel=f"{name}/{name}.field.toml",
                                   needs_export=False))
    plan.edges = edges or []
    plan.seams = seams or []
    (cdir / "campaign.toml").write_text(campaign.render_campaign_toml(plan), encoding="utf-8", newline="\n")
    return cdir


def _hub_table():
    return ('[hub]\nname = "WORLD_HUB"\nid = 4500\narea = 21\n'
            'borrow_bg = "GRGR_MAP420_GR_CEN_0"\ncamera = "camera_hub.bgx"\ntext_block = 8\n\n')


def _write_manifest(root, body, *, with_hub=True):
    text = (_hub_table() if with_hub else "") + body
    p = root / "journeys.toml"
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


# ---- loader (structural) ----------------------------------------------------------------
def test_load_bare_and_multi(tmp_path):
    _make_campaign(tmp_path, "evil_forest", members=["EVF_START", "EVF_EXIT"], id_base=6000,
                   seams=[{"frm": "EVF_EXIT", "to_real": "WORLDMAP", "kind": "overworld", "note": "exit"}])
    _make_campaign(tmp_path, "ice_cavern", members=["IC_ENT", "IC_DEEP"], id_base=6100)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "treno"
name = "Treno, City of Nobles"
entry = 4501
set_scenario = 7550

[[journey]]
id = "escape_ice"
name = "Escape to the Ice Cavern"
campaigns = ["evil_forest", "ice_cavern"]
entry = { campaign = "evil_forest", field = "EVF_START" }
[journey.seed]
scenario = 0
party = ["Zidane", "Vivi"]
[[journey.link]]
from = { campaign = "evil_forest", field = "EVF_EXIT" }
to = { campaign = "ice_cavern", field = "IC_ENT" }
""")
    m = journey.load_journeys(p)
    assert [j.id for j in m.journeys] == ["treno", "escape_ice"]
    treno, ice = m.journeys
    assert treno.is_bare and treno.entry.field == 4501 and treno.set_scenario == 7550
    assert not ice.is_bare and ice.campaigns == ["evil_forest", "ice_cavern"]
    assert ice.entry.campaign == "evil_forest" and ice.entry.field == "EVF_START"
    assert ice.seed.scenario == 0 and ice.seed.party == ["Zidane", "Vivi"]
    assert len(ice.links) == 1 and ice.links[0].src_field == "EVF_EXIT"
    assert ice.links[0].dst.campaign == "ice_cavern" and ice.links[0].dst.field == "IC_ENT"


def test_load_link_seam_alias(tmp_path):
    """The handoff schema's `from = {campaign, seam}` is accepted as an alias for `field`."""
    p = _write_manifest(tmp_path, """
[[journey]]
id = "a"
campaigns = ["c1", "c2"]
entry = { campaign = "c1", field = "ROOT" }
[[journey.link]]
from = { campaign = "c1", seam = "BORDER" }
to = { campaign = "c2", field = "ENTRY" }
""")
    m = journey.load_journeys(p)
    assert m.journeys[0].links[0].src_field == "BORDER"


@pytest.mark.parametrize("body,msg", [
    ('[[journey]]\nname = "x"\nentry = 1\n', "missing required key 'id'"),
    ('[[journey]]\nid = "x"\n', "missing required key 'entry'"),
    ('[[journey]]\nid = "x"\ncampaigns = ["c1"]\nentry = 4501\n', "multi-campaign entry must be"),
    ('[[journey]]\nid = "x"\nentry = { campaign = "c1", field = "A" }\n', "lists no 'campaigns'"),
    ('[[journey]]\nid = "x"\nentry = 4501\n[[journey.link]]\nfrom = { campaign = "c", field = "A" }\n'
     'to = 5\n', "bare single-field journey can't have"),
])
def test_load_structural_errors(tmp_path, body, msg):
    p = _write_manifest(tmp_path, body)
    with pytest.raises(journey.JourneyError, match=msg):
        journey.load_journeys(p)


def test_not_a_manifest(tmp_path):
    p = tmp_path / "x.toml"
    p.write_text("[something]\nelse = 1\n", encoding="utf-8")
    with pytest.raises(journey.JourneyError, match="not a journeys manifest"):
        journey.load_journeys(p)


# ---- resolution -------------------------------------------------------------------------
def test_resolve_multi_campaign(tmp_path):
    _make_campaign(tmp_path, "evil_forest", members=["EVF_START", "EVF_EXIT"], id_base=6000,
                   seams=[{"frm": "EVF_EXIT", "to_real": "WORLDMAP", "kind": "overworld", "note": "exit"}])
    _make_campaign(tmp_path, "ice_cavern", members=["IC_ENT", "IC_DEEP"], id_base=6100, flags_per_field=32)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "escape_ice"
campaigns = ["evil_forest", "ice_cavern"]
entry = { campaign = "evil_forest", field = "EVF_START" }
[[journey.link]]
from = { campaign = "evil_forest", field = "EVF_EXIT" }
to = { campaign = "ice_cavern", field = "IC_ENT" }
""")
    m = journey.load_journeys(p)
    plans = journey.load_campaign_plans(m)
    rj = journey.resolve_journey(m.journeys[0], plans)
    assert rj.entry_id == 6000                                  # EVF_START member id
    assert rj.campaign_ids == {"evil_forest": [6000, 6001], "ice_cavern": [6100, 6101]}
    # flag windows laid end-to-end from FIRST_SAFE_FLAG: forest 2*64, cavern 2*32
    assert rj.flag_windows["evil_forest"] == (FIRST_SAFE_FLAG, FIRST_SAFE_FLAG + 127, 64)
    assert rj.flag_windows["ice_cavern"] == (FIRST_SAFE_FLAG + 128, FIRST_SAFE_FLAG + 191, 32)
    assert rj.links == [{"src_campaign": "evil_forest", "src_field": "EVF_EXIT", "src_id": 6001,
                         "dst_campaign": "ice_cavern", "dst_field": "IC_ENT", "dst_id": 6100}]


def test_resolve_bare(tmp_path):
    p = _write_manifest(tmp_path, '[[journey]]\nid = "treno"\nentry = 4501\nset_scenario = 7550\n')
    m = journey.load_journeys(p)
    rj = journey.resolve_journey(m.journeys[0], {})
    assert rj.entry_id == 4501 and rj.flag_windows == {} and rj.links == []


# ---- lint: the global id-disjointness guarantee (the whole job) -------------------------
def _two_campaigns(tmp_path, base_a=6000, base_b=6100):
    _make_campaign(tmp_path, "ca", members=["A1", "A2"], id_base=base_a,
                   seams=[{"frm": "A2", "to_real": "WORLDMAP", "kind": "overworld", "note": "x"}])
    _make_campaign(tmp_path, "cb", members=["B1", "B2"], id_base=base_b)


def test_lint_clean(tmp_path):
    _two_campaigns(tmp_path)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[[journey.link]]
from = { campaign = "ca", field = "A2" }
to = { campaign = "cb", field = "B1" }
""")
    errors, warnings = journey.lint_manifest(journey.load_journeys(p))
    assert errors == []


def test_lint_id_collision_across_campaigns(tmp_path):
    _two_campaigns(tmp_path, base_a=6000, base_b=6000)            # both bands start at 6000 -> collide
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[[journey.link]]
from = { campaign = "ca", field = "A2" }
to = { campaign = "cb", field = "B1" }
""")
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("claimed by BOTH" in e and "6000" in e for e in errors)


def test_lint_bare_entry_collides_with_campaign(tmp_path):
    _make_campaign(tmp_path, "ca", members=["A1", "A2"], id_base=6000)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca"]
entry = { campaign = "ca", field = "A1" }

[[journey]]
id = "bare"
entry = 6001
""")
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("claimed by BOTH" in e and "6001" in e for e in errors)


def test_lint_missing_campaign_folder(tmp_path):
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["nope"]
entry = { campaign = "nope", field = "A1" }
""")
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("no campaign.toml" in e for e in errors)


def test_lint_out_of_band_id(tmp_path):
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=3000)   # below the custom floor (real-field band)
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\ncampaigns = ["ca"]\n'
                                  'entry = { campaign = "ca", field = "A1" }\n')
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("out of band" in e and "3000" in e for e in errors)


def test_lint_entry_not_a_member(tmp_path):
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000)
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\ncampaigns = ["ca"]\n'
                                  'entry = { campaign = "ca", field = "GHOST" }\n')
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("entry field 'GHOST' is not a member" in e for e in errors)


def test_lint_link_to_nonmember(tmp_path):
    _two_campaigns(tmp_path)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[[journey.link]]
from = { campaign = "ca", field = "A2" }
to = { campaign = "cb", field = "GHOST" }
""")
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("link target 'GHOST'" in e for e in errors)


def test_lint_link_source_not_boundary_warns(tmp_path):
    # A1 has NO seam (only A2 does) -> using A1 as a link source warns (not a boundary)
    _two_campaigns(tmp_path)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[[journey.link]]
from = { campaign = "ca", field = "A1" }
to = { campaign = "cb", field = "B1" }
""")
    errors, warnings = journey.lint_manifest(journey.load_journeys(p))
    assert errors == []
    assert any("has no out-of-chain seam" in w for w in warnings)


def test_lint_unreachable_campaign_warns(tmp_path):
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000)
    _make_campaign(tmp_path, "cb", members=["B1"], id_base=6100)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
""")                                                              # no link -> cb unreachable
    errors, warnings = journey.lint_manifest(journey.load_journeys(p))
    assert any("unreachable from the entry campaign" in w for w in warnings)


def test_lint_seed_scenario_range(tmp_path):
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000)
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\ncampaigns = ["ca"]\n'
                                  'entry = { campaign = "ca", field = "A1" }\n'
                                  '[journey.seed]\nscenario = 99999\n')
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("scenario 99999 out of range" in e for e in errors)


def test_lint_flag_window_overflow(tmp_path):
    # one fat campaign that needs more flags than the safe band holds
    big = (CHOICE_SCRATCH_FLOOR - FIRST_SAFE_FLAG) // 64 + 5      # members * 64 > band
    _make_campaign(tmp_path, "ca", members=[f"R{i}" for i in range(big)], id_base=6000)
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\ncampaigns = ["ca"]\n'
                                  'entry = { campaign = "ca", field = "R0" }\n')
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("past the choice-scratch floor" in e for e in errors)


def test_lint_duplicate_journey_id(tmp_path):
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\nentry = 4501\n'
                                  '[[journey]]\nid = "x"\nentry = 4502\n')
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("is duplicated" in e for e in errors)


def test_lint_no_hub_warns(tmp_path):
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\nentry = 4501\n', with_hub=False)
    errors, warnings = journey.lint_manifest(journey.load_journeys(p))
    assert errors == [] and any("no [hub] table" in w for w in warnings)


# ---- hub fold-in (reuse hub.render) -----------------------------------------------------
def test_hub_spec_and_generate(tmp_path):
    _make_campaign(tmp_path, "evil_forest", members=["EVF_START", "EVF_EXIT"], id_base=6000,
                   seams=[{"frm": "EVF_EXIT", "to_real": "WORLDMAP", "kind": "overworld", "note": "x"}])
    _make_campaign(tmp_path, "ice_cavern", members=["IC_ENT"], id_base=6100)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "treno"
name = "Treno, City of Nobles"
entry = 4501
set_scenario = 7550

[[journey]]
id = "escape_ice"
name = "Escape to the Ice Cavern"
campaigns = ["evil_forest", "ice_cavern"]
entry = { campaign = "evil_forest", field = "EVF_START" }
[journey.seed]
scenario = 1600
[[journey.link]]
from = { campaign = "evil_forest", field = "EVF_EXIT" }
to = { campaign = "ice_cavern", field = "IC_ENT" }
""")
    m = journey.load_journeys(p)
    spec = journey.manifest_to_hub_spec(m)
    assert spec.id == 4500 and len(spec.journeys) == 2
    treno, ice = spec.journeys
    assert treno.entry == 4501 and treno.set_scenario == 7550           # bare row, hub-side seed
    assert ice.entry == 6000 and ice.set_scenario == 1600              # resolved entry id + seed scenario
    assert ice.name == "Escape to the Ice Cavern"

    out = journey.generate_hub(p, out_path=tmp_path / "hub.field.toml")
    toml = (tmp_path / "hub.field.toml").read_text(encoding="utf-8")
    parsed = tomllib.loads(toml)                                       # the emitted hub is valid TOML
    assert parsed["field"]["id"] == 4500
    warps = [o.get("warp") for o in parsed["choice"][0]["options"]]
    assert 4501 in warps and 6000 in warps                            # both journeys warp to their entry id
    assert out["errors"] == []


def test_generate_hub_lint_aborts(tmp_path):
    # a manifest that fails lint (missing campaign) must abort generate_hub, not emit a broken hub
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\ncampaigns = ["gone"]\n'
                                  'entry = { campaign = "gone", field = "A" }\n')
    with pytest.raises(journey.JourneyError, match="lint failed"):
        journey.generate_hub(p, out_path=tmp_path / "hub.field.toml")


def test_render_plan_smoke(tmp_path):
    _two_campaigns(tmp_path)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
name = "The Arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[[journey.link]]
from = { campaign = "ca", field = "A2" }
to = { campaign = "cb", field = "B1" }
""")
    text = journey.render_journey_plan(journey.load_journeys(p))
    assert "The Arc" in text and "ca" in text and "link" in text and "6100" in text
