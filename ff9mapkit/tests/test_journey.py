"""Tests for the multi-campaign journey ASSEMBLER (journey.py) -- the offline core.

All pure: fixture campaigns are written by hand (minimal valid campaign.toml + member field.tomls), so the
namespace guarantee (global id disjointness across every campaign of every journey), lint, resolution, and
the hub fold-in are exercised with NO game install. The deploy ORCHESTRATION (build each campaign at its
band, wire links, deploy the hub) is the in-game step and is not tested here."""

import tomllib
from pathlib import Path

import pytest

from ff9mapkit import campaign, hub, journey
from ff9mapkit.campaign import CampaignPlan, Member
from ff9mapkit.flags import CHOICE_SCRATCH_FLOOR, FIRST_SAFE_FLAG


def test_shared_text_blocks_flags_cross_campaign_collisions(tmp_path):
    """A dialogue text block (mesID) shipped by >1 campaign dist collides when the folders stack."""
    import types
    def _dist(name, blocks):
        d = tmp_path / name / "FF9_Data" / "embeddedasset" / "text" / "us" / "field"
        d.mkdir(parents=True)
        for b in blocks:
            (d / f"{b}.mes").write_text("x", encoding="utf-8")
        return tmp_path / name
    dists = {"prim": _dist("prim", [2]), "acas": _dist("acas", [2, 3]), "evil": _dist("evil", [4])}
    steps = [types.SimpleNamespace(folder=k, mod_folder=f"FF9CustomMap-{k}") for k in dists]
    # block 2 is shipped by BOTH prim + acas -> collision; 3 (acas-only) + 4 (evil-only) are clear
    assert journey.shared_text_blocks(steps, dists) == [(2, ("FF9CustomMap-acas", "FF9CustomMap-prim"))]
    assert journey.shared_text_blocks(steps, {}) == []                          # no dists -> nothing to compare
    assert journey.shared_text_blocks(steps, {"prim": dists["prim"]}) == []     # single campaign -> no collision


def test_text_block_windows_disjoint_per_campaign():
    """Each campaign gets a disjoint custom text-block window, laid end-to-end (span = member count) -- so no two
    campaigns can land on the same mesID. The cross-campaign text-shadow cure's window assignment."""
    import types
    j = types.SimpleNamespace(campaigns=["a", "b", "c"])
    plans = {"a": (types.SimpleNamespace(members=[0, 1, 2]), None),     # 3 members -> span 3
             "b": (types.SimpleNamespace(members=[0]), None),           # 1 member  -> span 1
             "c": (types.SimpleNamespace(members=[0, 1]), None)}        # 2 members -> span 2
    base = journey.TEXT_BLOCK_BASE
    assert journey._text_block_windows(j, plans) == {"a": base, "b": base + 3, "c": base + 4}


# ---- fixture builders (no game) ---------------------------------------------------------
def _make_campaign(root, folder, *, members, id_base, flags_per_field=64, entry=None,
                   seams=None, edges=None, mod_folder="FF9CustomMap-test", sources=None):
    """Write a minimal but VALID campaign folder: campaign.toml + a parseable field.toml per member.
    ``sources`` (name -> donor real id) sets a member's real_id (default 0) -- needed to exercise a boundary
    door that lands straight in the NEXT campaign (the precise field_remap path)."""
    cdir = root / folder
    cdir.mkdir(parents=True, exist_ok=True)
    sources = sources or {}
    plan = CampaignPlan(name=folder, mod_folder=mod_folder, id_base=id_base, flag_base=FIRST_SAFE_FLAG,
                        flags_per_field=flags_per_field, entry_name=entry or members[0], entry_entrance=0)
    for i, name in enumerate(members):
        mdir = cdir / name
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / f"{name}.field.toml").write_text(
            f'[field]\nid = {id_base + i}\nname = "{name}"\narea = 11\ntext_block = 1073\n',
            encoding="utf-8", newline="\n")
        plan.members.append(Member(real_id=int(sources.get(name, 0)), new_id=id_base + i, name=name,
                                   mode="native", src_area=11, folder="",
                                   toml_rel=f"{name}/{name}.field.toml", needs_export=False))
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


def test_lint_journey_leak_kind_and_exits(tmp_path):
    # ca leaks to 999 via a SCRIPTED warp (-> FORCED) and to 888 via a PORTAL door (-> walk-out); neither is forked
    _make_campaign(tmp_path, "ca", members=["A1", "A2"], id_base=6000, sources={"A1": 100, "A2": 101},
                   seams=[{"frm": "A1", "to_real": 999, "kind": "scripted", "note": ""},
                          {"frm": "A2", "to_real": 888, "kind": "portal", "note": ""}])
    body = ('[[journey]]\nid = "j"\nname = "J"\ncampaigns = ["ca"]\n'
            'entry = { campaign = "ca", field = "A1" }\n')
    _, warns = journey.lint_manifest(journey.load_journeys(_write_manifest(tmp_path, body)))
    assert any("999" in w and "FORCED" in w for w in warns), warns       # scripted leak -> FORCED (softlock)
    assert any("888" in w and "door" in w for w in warns), warns         # portal leak -> walk-out door
    # declaring both as intended boundaries silences them
    m2 = journey.load_journeys(_write_manifest(tmp_path, body + "exits = [999, 888]\n"))
    assert m2.journeys[0].exits == (999, 888)
    _, warns2 = journey.lint_manifest(m2)
    assert not any("999" in w or "888" in w for w in warns2), warns2


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
                         "dst_campaign": "ice_cavern", "dst_field": "IC_ENT", "dst_id": 6100,
                         "dst_entrance": 0}]


def test_leftover_boundary_placeholder_is_tolerated(tmp_path):
    # A legacy BOUNDARY_MEMBER placeholder must NOT crash resolve, and is now just an obsolete WARNING -- links
    # auto-wire from the seams, so it's not needed. cb is still reached (via the auto-wired overworld hop).
    _two_campaigns(tmp_path)                                       # ca has an overworld exit; cb forked
    p = _write_manifest(tmp_path, """
[[journey]]
id = "ff9disc1"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[[journey.link]]
from = { campaign = "ca", field = "BOUNDARY_MEMBER" }
to = { campaign = "cb", field = "B1" }
""")
    m = journey.load_journeys(p)
    rj = journey.resolve_journey(m.journeys[0], journey.load_campaign_plans(m))   # must NOT raise
    assert rj.entry_id == 6000
    assert any(l["src_campaign"] == "ca" and l["dst_campaign"] == "cb" for l in rj.links)  # cb auto-wired
    errors, warnings = journey.lint_manifest(m)
    assert not any("BOUNDARY_MEMBER" in e for e in errors)        # no longer an ERROR (obsolete placeholder)
    assert any("placeholder" in w and "auto-wire" in w for w in warnings)
    assert not any("neither a member name nor a field id" in e for e in errors)


def test_campaign_connectivity_from_real_seams(tmp_path):
    # the oracle reads each campaign's REAL .eb seams (not zones/id order): a seam landing in a sibling's donor
    # id -> a cross-campaign edge; one landing nowhere-forked -> external; WORLDMAP -> world map.
    _make_campaign(tmp_path, "ca", members=["A1", "A2"], id_base=6000, sources={"A1": 100, "A2": 101},
                   seams=[{"frm": "A2", "to_real": 200, "kind": "scripted", "note": ""},   # -> cb (real 200)
                          {"frm": "A2", "to_real": 200, "kind": "scripted", "note": ""},   # dup target (dedup display)
                          {"frm": "A1", "to_real": 999, "kind": "scripted", "note": ""}])  # forked by nobody -> external
    _make_campaign(tmp_path, "cb", members=["B1", "B2"], id_base=6100, sources={"B1": 200, "B2": 201},
                   seams=[{"frm": "B1", "to_real": "WORLDMAP", "kind": "overworld", "note": ""}])
    plans = {k: campaign.load_campaign(tmp_path / k / "campaign.toml") for k in ("ca", "cb")}
    conn = journey.campaign_connectivity(["ca", "cb"], plans)
    assert list(conn["ca"]["to"]) == ["cb"] and conn["ca"]["to"]["cb"][0] == ("A2", 200, "scripted")
    assert conn["ca"]["external"] == [("A1", 999, "scripted")]
    assert conn["cb"]["to"] == {} and conn["cb"]["worldmap"] == [("B1", "overworld")]
    assert journey.connection_targets(conn["ca"]) == "cb (via 200 scripted)"   # deduped + warp kind
    # an edge NOT in the wired set is flagged [NOT wired]; the leak id surfaces
    rep = "\n".join(journey.render_connectivity(["ca", "cb"], plans))   # wired empty -> everything flagged
    assert "ca:" in rep and "-> cb (via 200 scripted)" in rep and "[NOT wired]" in rep
    assert "leak(s) to unforked fields (999)" in rep                  # the external 999 surfaces with its id
    # ...and DROPS the tag once that pair IS wired
    rep2 = "\n".join(journey.render_connectivity(["ca", "cb"], plans, wired={("ca", "cb")}))
    assert "-> cb (via 200 scripted)" in rep2 and "[NOT wired]" not in rep2.split("ca:")[1].split("\n")[0]


def test_auto_seam_links_one_per_field_warp(tmp_path):
    # a member warping to SEVERAL fields in a sibling must get ONE link PER field (else the others leak); a
    # Field() to a donor forked by TWO siblings wires ONCE (first sibling -- no conflicting double-remap).
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000, sources={"A1": 100},
                   seams=[{"frm": "A1", "to_real": tr, "kind": "scripted", "note": ""} for tr in (200, 201, 202, 300)])
    _make_campaign(tmp_path, "cb", members=["B1", "B2", "B3"], id_base=6100,
                   sources={"B1": 200, "B2": 201, "B3": 202})
    _make_campaign(tmp_path, "cc", members=["C1"], id_base=6300, sources={"C1": 300})
    plain = {k: campaign.load_campaign(tmp_path / k / "campaign.toml") for k in ("ca", "cb", "cc")}
    links = journey.auto_seam_links(["ca", "cb", "cc"], plain)
    a1 = [l for l in links if l["src_field"] == "A1"]
    # 3 distinct warps into cb (200/201/202) + 1 into cc (300) = 4 links, each a DISTINCT arrival id
    assert len(a1) == 4 and len({l["dst_id"] for l in a1}) == 4
    assert {l["dst_field"] for l in a1 if l["dst_campaign"] == "cb"} == {"B1", "B2", "B3"}
    # exclude_members suppresses the whole member
    assert journey.auto_seam_links(["ca", "cb", "cc"], plain, exclude_members={("ca", "A1")}) == []


def test_auto_seam_links_tolerates_orphaned_seam_frm(tmp_path):
    # a seam whose `frm` is NOT a member (a stringified real id from a stale/hand-edited campaign.toml) must NOT
    # KeyError the whole deploy/lint pipeline -- skip it. (review MEDIUM: new_id[a][frm] was a raw subscript.)
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000, sources={"A1": 100},
                   seams=[{"frm": "GHOST", "to_real": 200, "kind": "scripted", "note": ""},     # frm not a member
                          {"frm": "999", "to_real": "WORLDMAP", "kind": "overworld", "note": ""}])
    _make_campaign(tmp_path, "cb", members=["B1"], id_base=6100, sources={"B1": 200})
    plain = {k: campaign.load_campaign(tmp_path / k / "campaign.toml") for k in ("ca", "cb")}
    links = journey.auto_seam_links(["ca", "cb"], plain)             # must NOT raise
    assert all(l["src_field"] in {"A1"} for l in links)             # the GHOST/999 orphan seams are skipped


def test_connectivity_shared_donor_names_all_siblings(tmp_path):
    # a donor real id (300) forked by TWO siblings (cb, cc) -> a seam landing there names BOTH, not last-wins.
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000, sources={"A1": 100},
                   seams=[{"frm": "A1", "to_real": 300, "kind": "scripted", "note": ""}])
    _make_campaign(tmp_path, "cb", members=["B1"], id_base=6100, sources={"B1": 300})   # forks real 300
    _make_campaign(tmp_path, "cc", members=["C1"], id_base=6200, sources={"C1": 300})   # ALSO forks real 300
    plans = {k: campaign.load_campaign(tmp_path / k / "campaign.toml") for k in ("ca", "cb", "cc")}
    conn = journey.campaign_connectivity(["ca", "cb", "cc"], plans)
    assert set(conn["ca"]["to"]) == {"cb", "cc"}                      # both siblings named (not just the last)


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


def test_render_selector_hub_and_journey_row(tmp_path):
    # an empty World Hub (the journey selector): [hub] only, defaults to Mognet Central, loads structurally
    t = journey.render_selector_hub_toml(hub_name="World Hub", hub_id=4600)
    p = tmp_path / "journeys.toml"
    p.write_text(t, encoding="utf-8")
    m = journey.load_journeys(p)
    assert m.hub["id"] == 4600 and m.hub["borrow_field"] == 3100 and m.hub["area"] == 56 and m.journeys == []
    assert m.hub["name"] == "World_Hub", "a spaced hub name is coerced to an EVT/FBG token"
    assert all(ord(c) < 128 for c in t), "the generated, hand-edited file must be ASCII"
    # an empty selector hub ([hub] + no rows) is a WARNING, not a hard error (a valid fill-me-in scaffold)
    eerr, ewarn = journey.lint_manifest(m)
    assert eerr == [] and any("add a journey" in w for w in ewarn), (eerr, ewarn)
    # add two bare rows (selector menu) -> they parse, resolve, and lint clean
    t2 = (t + "\n" + journey.render_journey_row("dali", "Dali", 4100, scenario=2600)
          + "\n" + journey.render_journey_row("treno", "Treno", 4501))
    p.write_text(t2, encoding="utf-8")
    m2 = journey.load_journeys(p)
    assert [(j.id, j.entry.field, j.hub_scenario) for j in m2.journeys] == [("dali", 4100, 2600), ("treno", 4501, None)]
    assert journey.lint_manifest(m2) == ([], [])
    # a CUSTOM borrow_bg has NO live Mognet area/borrow_field -- a 'SET ME' area placeholder warns instead of
    # silently defaulting to 21 (the documented BG-borrow black screen).
    t3 = journey.render_selector_hub_toml(borrow_bg="GRGR_MAP420_GR_CEN_0")
    lines3 = t3.splitlines()
    assert 'borrow_bg = "GRGR_MAP420_GR_CEN_0"' in t3
    assert not any(ln.startswith("area =") for ln in lines3) and "# area = 21" in t3 and "SET ME" in t3
    assert not any(ln.startswith("borrow_field") for ln in lines3)   # no LIVE borrow_field for a custom room


def test_render_journey_row_validates():
    with pytest.raises(journey.JourneyError):
        journey.render_journey_row("bad slug!", "X", 4100)      # slug must be A-Z/0-9/_
    with pytest.raises(journey.JourneyError):
        journey.render_journey_row("ok", "X", "not-an-int")     # entry must be a field id


def test_remove_journey_row(tmp_path):
    t = (journey.render_selector_hub_toml(hub_name="Hub")
         + "\n" + journey.render_journey_row("a", "A", 4100)
         + "\n" + journey.render_journey_row("b", "B", 4200)
         + "\n" + journey.render_journey_row("c", "C", 4300))
    t2 = journey.remove_journey_row(t, "b")                      # remove the MIDDLE row
    p = tmp_path / "j.toml"
    p.write_text(t2, encoding="utf-8")
    assert [j.id for j in journey.load_journeys(p).journeys] == ["a", "c"], "middle gone, rest intact"
    assert all(ord(ch) < 128 for ch in t2)
    with pytest.raises(journey.JourneyError):
        journey.remove_journey_row(t2, "nope")


def test_remove_journey_row_keeps_other_subtables(tmp_path):
    # removing journey 'b' must NOT eat journey 'a's [journey.seed] subtable (block boundary = next [[journey]])
    t = ('[hub]\nname = "H"\nid = 4600\n\n'
         '[[journey]]\nid = "a"\ncampaigns = ["ca"]\nentry = { campaign = "ca", field = "A1" }\n'
         '[journey.seed]\nscenario = 2600\n\n'
         '[[journey]]\nid = "b"\nname = "B"\nentry = 4200\n')
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000)
    p = tmp_path / "journeys.toml"
    p.write_text(journey.remove_journey_row(t, "b"), encoding="utf-8")
    m = journey.load_journeys(p)
    assert [j.id for j in m.journeys] == ["a"] and m.journeys[0].seed.scenario == 2600, "a's seed survived"


def test_lint_warns_on_duplicate_bare_entry(tmp_path):
    t = (journey.render_selector_hub_toml(hub_name="Hub")
         + "\n" + journey.render_journey_row("a", "A", 4100)
         + "\n" + journey.render_journey_row("b", "B", 4100))   # two rows -> the SAME field (a copy-paste)
    p = tmp_path / "j.toml"
    p.write_text(t, encoding="utf-8")
    errs, warns = journey.lint_manifest(journey.load_journeys(p))
    assert errs == [] and any("both warp to field 4100" in w for w in warns), (errs, warns)


def test_lint_hub_id_collides_with_campaign_member(tmp_path):
    # the [hub] field registers in the SAME global EventDB as the campaigns -> a hub/member id collision is a
    # black screen; the disjointness lint must claim the hub id too (else it passes silently).
    _make_campaign(tmp_path, "ca", members=["A1", "A2"], id_base=6000)
    p = _write_manifest(tmp_path, """
[hub]
name = "H"
id = 6000

[[journey]]
id = "arc"
campaigns = ["ca"]
entry = { campaign = "ca", field = "A1" }
""", with_hub=False)
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("claimed by BOTH" in e and "6000" in e and "hub" in e for e in errors)


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


def test_lint_entry_int_not_a_member_is_an_error(tmp_path):
    # a RAW INT entry that resolves to no member is a hard error (not just a warning): it would flow into
    # plan.entry_field_id and `deploy_journey --newgame entry` would wire an unreachable New-Game target.
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000)
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\ncampaigns = ["ca"]\n'
                                  'entry = { campaign = "ca", field = 99999 }\n')
    errors, _ = journey.lint_manifest(journey.load_journeys(p))
    assert any("entry id 99999 is not a member" in e for e in errors)


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


# ---- the in-game deploy plan (offline brain) --------------------------------------------
def _escape_ice(tmp_path, *, forest_seam_real=652, forest_mod="FF9CustomMap-evf",
                cavern_mod="FF9CustomMap-ic"):
    """A 2-campaign journey whose forest boundary (EVF_EXIT) has a SCRIPTED seam to a real id (retargetable)."""
    _make_campaign(tmp_path, "evil_forest", members=["EVF_START", "EVF_EXIT"], id_base=6000,
                   mod_folder=forest_mod,
                   seams=[{"frm": "EVF_EXIT", "to_real": forest_seam_real, "kind": "scripted",
                           "note": "trigger:escape"}])
    _make_campaign(tmp_path, "ice_cavern", members=["IC_ENT", "IC_DEEP"], id_base=6100, mod_folder=cavern_mod)
    return _write_manifest(tmp_path, """
[[journey]]
id = "treno"
name = "Treno"
entry = 4501

[[journey]]
id = "escape_ice"
name = "Escape to the Ice Cavern"
campaigns = ["evil_forest", "ice_cavern"]
entry = { campaign = "evil_forest", field = "EVF_START" }
[[journey.link]]
from = { campaign = "evil_forest", field = "EVF_EXIT" }
to = { campaign = "ice_cavern", field = "IC_ENT" }
""")


def test_build_deploy_plan(tmp_path):
    p = _escape_ice(tmp_path)
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    assert plan.hub_field_id == 4500
    assert plan.bare_entries == [("treno", "Treno", 4501)]
    assert plan.folder_conflicts == []
    assert plan.entry_field_id is None                      # 2 journeys (bare treno + escape_ice) -> no single opening
    # two campaign steps, distinct folders, disjoint flag windows
    by = {s.folder: s for s in plan.campaign_steps}
    assert by["evil_forest"].mod_folder == "FF9CustomMap-evf" and by["evil_forest"].flag_base == FIRST_SAFE_FLAG
    assert by["ice_cavern"].mod_folder == "FF9CustomMap-ic" and by["ice_cavern"].flag_base == FIRST_SAFE_FLAG + 128
    assert (by["evil_forest"].id_lo, by["evil_forest"].id_hi) == (6000, 6001)
    # the link is retargetable: remap the scripted seam target (652) -> the cavern entry (6100)
    assert len(plan.links) == 1
    lk = plan.links[0]
    assert lk.mode == "field_remap" and lk.retargetable and lk.remap == {652: 6100}
    assert lk.eb_name == "EVT_EVF_EXIT"
    assert lk.src_mod_folder == "FF9CustomMap-evf" and lk.dst_id == 6100


def test_deploy_plan_overworld_seam_worldmap_inject(tmp_path):
    # EVF_EXIT's only seam is overworld (no Field() op) -> the link is auto-wired by worldmap_inject
    # (body-replace the walk-out region with a Field(dst) warp -- the elided world-map leg)
    _make_campaign(tmp_path, "evil_forest", members=["EVF_START", "EVF_EXIT"], id_base=6000, mod_folder="mf-a",
                   seams=[{"frm": "EVF_EXIT", "to_real": "WORLDMAP", "kind": "overworld", "note": "wm"}])
    _make_campaign(tmp_path, "ice_cavern", members=["IC_ENT"], id_base=6100, mod_folder="mf-b")
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["evil_forest", "ice_cavern"]
entry = { campaign = "evil_forest", field = "EVF_START" }
[[journey.link]]
from = { campaign = "evil_forest", field = "EVF_EXIT" }
to = { campaign = "ice_cavern", field = "IC_ENT", entrance = 3 }
""")
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    lk = plan.links[0]
    assert lk.mode == "worldmap_inject" and lk.retargetable and lk.remap == {}
    assert lk.dst_id == 6100 and lk.dst_entrance == 3 and "overworld" in lk.seam_kinds


def test_deploy_plan_no_seam_not_retargetable(tmp_path):
    # a boundary member with NO onward seam at all -> not auto-wirable
    _make_campaign(tmp_path, "ca", members=["A1", "A2"], id_base=6000, mod_folder="mf-a")  # A2 has no seam
    _make_campaign(tmp_path, "cb", members=["B1"], id_base=6100, mod_folder="mf-b")
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[[journey.link]]
from = { campaign = "ca", field = "A2" }
to = { campaign = "cb", field = "B1" }
""")
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    lk = plan.links[0]
    assert lk.mode == "none" and not lk.retargetable and "no onward seam" in lk.note


def test_deploy_plan_folder_conflict(tmp_path):
    # two campaigns sharing a mod_folder -> deploy_campaign would wholesale-clobber one
    _make_campaign(tmp_path, "evil_forest", members=["EVF_START"], id_base=6000, mod_folder="shared")
    _make_campaign(tmp_path, "ice_cavern", members=["IC_ENT"], id_base=6100, mod_folder="shared")
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["evil_forest", "ice_cavern"]
entry = { campaign = "evil_forest", field = "EVF_START" }
""")
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    assert plan.folder_conflicts and plan.folder_conflicts[0][0] == "shared"


def test_render_deploy_playbook(tmp_path):
    p = _escape_ice(tmp_path)
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    book = journey.render_deploy_playbook(journey.load_journeys(p), hub_toml="hub.field.toml")
    assert "deploy_campaign.py" in book and "--flag-base 8512" in book and "--flag-base 8640" in book
    assert "--no-warp" in book and "--mod-folder FF9CustomMap-evf" in book
    assert "deploy_journey.py" in book and "--apply-links" in book      # the link step
    assert "Field(652) -> Field(6100)" in book
    # the hub + New-Game override go into a DEDICATED journey folder (not the ambient highest)
    assert f"--id 4500 --mod-folder {plan.hub_folder}" in book          # hub field -> the hub folder
    assert f"wire_newgame_from_stock.py 4500 --mod-folder {plan.hub_folder}" in book   # New Game -> hub
    assert "retarget_newgame_warp.py" not in book                       # the no-op-prone retarget is gone
    assert "FolderNames = " in book and plan.hub_folder in book         # the concrete stack line
    assert "'Treno' [treno] -> field 4501" in book                      # bare journey noted


def test_deploy_plan_hub_folder_is_dedicated(tmp_path):
    p = _escape_ice(tmp_path)
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    assert plan.hub_folder and plan.hub_folder.startswith("FF9CustomMap-")
    assert plan.hub_folder not in {s.mod_folder for s in plan.campaign_steps}   # distinct -> no re-deploy clobber


def test_deploy_plan_hub_folder_avoids_a_campaign_folder_collision(tmp_path):
    # a hub named after a campaign would derive the SAME folder -> the loop must pick a distinct fallback so the
    # hub deploy can't wholesale-clobber that campaign's folder.
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000, mod_folder="FF9CustomMap-arc")
    hub = ('[hub]\nname = "arc"\nid = 4500\narea = 21\nborrow_bg = "GRGR_MAP420_GR_CEN_0"\n'
           'camera = "camera_hub.bgx"\ntext_block = 8\n\n')                  # hub name "arc" -> base FF9CustomMap-arc
    p = _write_manifest(tmp_path, hub + '[[journey]]\nid = "x"\ncampaigns = ["ca"]\n'
                                  'entry = { campaign = "ca", field = "A1" }\n', with_hub=False)
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    assert plan.hub_folder == "FF9CustomMap-arc-hub"                            # base collided -> distinct fallback
    assert plan.hub_folder not in {s.mod_folder for s in plan.campaign_steps}


def test_apply_link_rewrites(tmp_path, monkeypatch):
    from ff9mapkit.content import verbatim
    p = _escape_ice(tmp_path)
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    # fake the deployed boundary .eb (2 langs) under <game>/<mod_folder>
    game = tmp_path / "game"
    ebdir = game / "FF9CustomMap-evf" / "US" / "field"
    ebdir.mkdir(parents=True)
    (ebdir / "EVT_EVF_EXIT.eb.bytes").write_bytes(b"ORIG-US")
    (game / "FF9CustomMap-evf" / "JP" / "field").mkdir(parents=True)
    (game / "FF9CustomMap-evf" / "JP" / "field" / "EVT_EVF_EXIT.eb.bytes").write_bytes(b"ORIG-JP")
    monkeypatch.setattr(verbatim, "remap_fields",
                        lambda data, remap: b"PATCHED" if remap == {652: 6100} else data)
    res = journey.apply_link_rewrites(plan, game, backup_dir=tmp_path / "bk")
    r = res[0]
    assert r["found"] and r["mode"] == "field_remap" and r["langs"] == 2 and r["remap"] == {652: 6100}
    assert (ebdir / "EVT_EVF_EXIT.eb.bytes").read_bytes() == b"PATCHED"
    assert len(r["backups"]) == 2 and all(Path(bk).read_bytes().startswith(b"ORIG") for _, bk in r["backups"])


def test_build_campaign_flag_base_override(tmp_path):
    # the override reaches lint BEFORE build: an unsafe base fails the safe-band check (proves it applied)
    _make_campaign(tmp_path, "ca", members=["A1", "A2"], id_base=6000)
    cpath = tmp_path / "ca" / "campaign.toml"
    with pytest.raises(campaign.CampaignError, match="safe floor|treasure-chest"):
        campaign.build_campaign(cpath, flag_base=8300)        # below FIRST_SAFE_FLAG -> lint error


# ---- world-map leg: the worldmap_inject body-replace (the elided overworld seam) --------
def test_worldmap_warp_body_carries_field_and_entrance():
    # the replacement body (lifted from the proven gateway template's tag-2 warp) embeds Field(dst)+entrance
    body = journey._worldmap_warp_body(6300, entrance=4)
    assert isinstance(body, bytes) and len(body) > 0
    # the gateway template's Field literal (REL_FIELD) + entrance (REL_ENTRANCE) sit inside the tag-2 body
    assert b"\x9c\x18" in body                                # 6300 == 0x189C little-endian (the Field dst)
    assert b"\x04\x00" in body                                # entrance 4 (D8:2 i16)


# ---- [journey.seed] capstone (scenario/party -> entry .eb; inventory/equipment -> global CSV) ----------
def test_seed_to_field_blocks():
    seed = journey.JourneySeed(scenario=2600, party=["Zidane", "Vivi", "Steiner"],
                               raw={"scenario": 2600, "party": ["Zidane", "Vivi", "Steiner"],
                                    "flags": [{"flag": 8512, "value": 1}],
                                    "inventory": [["Potion", 5]],
                                    "equipment": [{"character": "Vivi", "weapon": "Mage Masher"}]})
    b = journey.seed_to_field_blocks(seed)
    assert b["startup"]["scenario"] == 2600
    assert b["startup"]["flags"] == [{"flag": 8512, "value": 1}]
    assert b["party"] == {"add": ["Vivi", "Steiner"]}                 # Zidane dropped (New Game seeds slot 0)
    assert b["start_inventory"] == {"items": [["Potion", 5]]}
    assert b["equipment"] == [{"character": "Vivi", "weapon": "Mage Masher"}]


def test_seed_to_field_blocks_empty():
    assert journey.seed_to_field_blocks(journey.JourneySeed()) == {}
    assert journey.seed_to_field_blocks(None) == {}


def test_apply_seed_blocks_merges():
    raw = {"field": {"id": 6000}, "party": {"add": ["Vivi"]}}
    campaign.apply_seed_blocks(raw, {"startup": {"scenario": 2600}, "party": {"add": ["Vivi", "Steiner"]},
                                     "start_inventory": {"items": [["Potion", 5]]}})
    assert raw["startup"]["scenario"] == 2600
    assert raw["party"]["add"] == ["Vivi", "Steiner"]                 # union, no duplicate
    assert raw["start_inventory"] == {"items": [["Potion", 5]]}


def test_apply_seed_blocks_empty_noop():
    raw = {"field": {"id": 1}}
    campaign.apply_seed_blocks(raw, {})
    assert raw == {"field": {"id": 1}}


def test_build_deploy_plan_seeds_only_entry(tmp_path):
    _two_campaigns(tmp_path)                                          # ca (entry), cb
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[journey.seed]
scenario = 1600
party = ["Zidane", "Vivi"]
[[journey.link]]
from = { campaign = "ca", field = "A2" }
to = { campaign = "cb", field = "B1" }
""")
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    by = {s.folder: s for s in plan.campaign_steps}
    assert by["ca"].seed_blocks["startup"]["scenario"] == 1600
    assert by["ca"].seed_blocks["party"] == {"add": ["Vivi"]}
    assert by["cb"].seed_blocks is None                              # non-entry campaign: no seed
    # single-journey manifest -> the opening entry id is exposed (the --newgame entry target = ca/A1)
    assert plan.entry_field_id is not None and by["ca"].id_lo <= plan.entry_field_id <= by["ca"].id_hi


def test_lint_seed_inventory_warns(tmp_path):
    _make_campaign(tmp_path, "ca", members=["A1"], id_base=6000)
    p = _write_manifest(tmp_path, '[[journey]]\nid = "x"\ncampaigns = ["ca"]\n'
                                  'entry = { campaign = "ca", field = "A1" }\n'
                                  '[journey.seed]\ninventory = [["Potion", 5]]\n')
    errors, warnings = journey.lint_manifest(journey.load_journeys(p))
    assert errors == [] and any("MOD-GLOBAL New-Game CSVs" in w for w in warnings)


def test_render_playbook_shows_seed_and_oneshot(tmp_path):
    _two_campaigns(tmp_path)
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
[journey.seed]
scenario = 1600
party = ["Zidane", "Vivi"]
[[journey.link]]
from = { campaign = "ca", field = "A2" }
to = { campaign = "cb", field = "B1" }
""")
    book = journey.render_deploy_playbook(journey.load_journeys(p))
    assert "--apply`" in book                                        # the one-shot is advertised
    assert "SEED (via --apply): scenario=1600" in book               # the entry campaign line notes the seed


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_worldmap_inject_real_field_300(tmp_path):
    # full worldmap_inject on the REAL Ice Cavern entrance (field 300, a pure overworld exit): its walk-out
    # WorldMap region body is replaced with a Field(dst) warp, all langs, and the .eb stays well-formed.
    from ff9mapkit import extract
    from ff9mapkit.eb import EbScript
    eb = extract.EventBundle().eb_for_id(300)
    regions = journey._worldmap_region_funcs(eb)
    assert regions, "field 300 should have a tag-2 WorldMap walk-out region"

    # stage a fake 2-lang deploy of field 300 as the boundary member's EVT, behind an overworld-seam link
    _make_campaign(tmp_path, "forest", members=["EVF_EXIT"], id_base=6000, mod_folder="mf-ow",
                   seams=[{"frm": "EVF_EXIT", "to_real": "WORLDMAP", "kind": "overworld", "note": "wm"}])
    _make_campaign(tmp_path, "cavern", members=["IC_ENT"], id_base=6300, mod_folder="mf-ic")
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["forest", "cavern"]
entry = { campaign = "forest", field = "EVF_EXIT" }
[[journey.link]]
from = { campaign = "forest", field = "EVF_EXIT" }
to = { campaign = "cavern", field = "IC_ENT" }
""")
    plan = journey.build_deploy_plan(journey.load_journeys(p))
    game = tmp_path / "game"
    for lang in ("us", "jp"):
        d = game / "mf-ow" / lang / "field"
        d.mkdir(parents=True)
        (d / "EVT_EVF_EXIT.eb.bytes").write_bytes(eb)
    res = journey.apply_link_rewrites(plan, game, backup_dir=tmp_path / "bk")
    r = res[0]
    assert r["mode"] == "worldmap_inject" and r["found"] and r["langs"] == 2 and r["regions"] >= 1
    # the patched .eb: the walk-out region now warps Field(6300) with NO WorldMap op left in it
    out = (game / "mf-ow" / "us" / "field" / "EVT_EVF_EXIT.eb.bytes").read_bytes()
    s = EbScript.from_bytes(out)
    ei, tag = regions[0]
    f = s.entry(ei).func_by_tag(tag)
    ops = [(i.op, i.imm(0) if i.op in (0x2B, 0xB6) else None) for i in s.instrs(f)]
    assert (0x2B, 6300) in ops and not any(op == 0xB6 for op, _ in ops)
    # every entry still re-parses (entry table fixed up by replace_function_body)
    for e in s.entries:
        if not e.empty:
            for fn in e.funcs:
                list(s.instrs(fn))


def test_deploy_plan_overworld_preferred_over_ambiguous_field_seams(tmp_path):
    # A boundary member with an overworld exit AND SEVERAL ambiguous in-zone Field() doors (a shop, a sub-room):
    # the >1 Field() targets are ambiguous (previously -> 'none' -> BOUNDARY_MEMBER in reconcile), so the
    # world-map exit wins -> worldmap_inject. This is the dali/south_gate fix (their overworld exit was shadowed).
    _make_campaign(tmp_path, "za", members=["A1", "A2"], id_base=6000, mod_folder="mf-a",
                   seams=[{"frm": "A2", "to_real": "WORLDMAP", "kind": "overworld", "note": "wm"},
                          {"frm": "A2", "to_real": 998, "kind": "scripted", "note": "a shop door"},
                          {"frm": "A2", "to_real": 999, "kind": "scripted", "note": "a sub-room door"}])
    _make_campaign(tmp_path, "zb", members=["B1"], id_base=6100, mod_folder="mf-b")
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["za", "zb"]
entry = { campaign = "za", field = "A1" }
[[journey.link]]
from = { campaign = "za", field = "A2" }
to = { campaign = "zb", field = "B1" }
""")
    lk = journey.build_deploy_plan(journey.load_journeys(p)).links[0]
    assert lk.mode == "worldmap_inject" and lk.retargetable and lk.remap == {}    # overworld wins over ambiguity
    assert "overworld" in lk.seam_kinds


def test_deploy_plan_overworld_wins_over_a_lone_in_zone_door(tmp_path):
    # south_gate's case: the boundary has an overworld exit AND a SINGLE in-zone Field() door that does NOT lead
    # into the next campaign (B1's real id is 0, the door is 555). The world-map exit is the real cross-zone
    # boundary -> worldmap_inject; the in-zone door must NOT shadow it (the bug a naive len==1-first ordering hit).
    _make_campaign(tmp_path, "za", members=["A1", "A2"], id_base=6000, mod_folder="mf-a",
                   seams=[{"frm": "A2", "to_real": "WORLDMAP", "kind": "overworld", "note": "wm"},
                          {"frm": "A2", "to_real": 555, "kind": "scripted", "note": "an in-zone sub-room"}])
    _make_campaign(tmp_path, "zb", members=["B1"], id_base=6100, mod_folder="mf-b")
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["za", "zb"]
entry = { campaign = "za", field = "A1" }
[[journey.link]]
from = { campaign = "za", field = "A2" }
to = { campaign = "zb", field = "B1" }
""")
    lk = journey.build_deploy_plan(journey.load_journeys(p)).links[0]
    assert lk.mode == "worldmap_inject" and lk.remap == {}        # the in-zone door doesn't shadow the overworld


def test_deploy_plan_field_door_into_next_campaign_is_precise(tmp_path):
    # A boundary with a Field() door whose target IS the next campaign's arrival donor id (700) AND an overworld
    # exit: the door straight into the next campaign is the PRECISE boundary -> field_remap {700: dst}, beating
    # the world-map leg (review finding: a real door to the next arc must not be coarsened to worldmap_inject).
    _make_campaign(tmp_path, "za", members=["A1", "A2"], id_base=6000, mod_folder="mf-a",
                   seams=[{"frm": "A2", "to_real": "WORLDMAP", "kind": "overworld", "note": "wm"},
                          {"frm": "A2", "to_real": 700, "kind": "scripted", "note": "door into the next zone"}])
    _make_campaign(tmp_path, "zb", members=["B1"], id_base=6100, mod_folder="mf-b", sources={"B1": 700})
    p = _write_manifest(tmp_path, """
[[journey]]
id = "arc"
campaigns = ["za", "zb"]
entry = { campaign = "za", field = "A1" }
[[journey.link]]
from = { campaign = "za", field = "A2" }
to = { campaign = "zb", field = "B1" }
""")
    lk = journey.build_deploy_plan(journey.load_journeys(p)).links[0]
    assert lk.mode == "field_remap" and lk.remap == {700: 6100}    # precise door into the next campaign


# ---- pre-flight collision sweep (the "remove the superseded folder" report) --------------
def _fake_game(tmp, foldernames, dicts):
    """A throwaway game dir: Memoria.ini with a FolderNames line + a DictionaryPatch.txt per folder. ``dicts``
    maps folder -> [(id, name), ...] (each becomes a FieldScene line)."""
    g = tmp / "game"
    g.mkdir(exist_ok=True)
    fn = ", ".join(f'"{f}"' for f in foldernames)
    (g / "Memoria.ini").write_text(f"[Mod]\nFolderNames = {fn}\n", encoding="utf-8", newline="\n")
    for folder, rows in dicts.items():
        d = g / folder
        d.mkdir(parents=True, exist_ok=True)
        body = "\n".join(f"FieldScene {i} 11 {nm} {nm} 33" for (i, nm) in rows)
        (d / "DictionaryPatch.txt").write_text(body + "\n", encoding="utf-8", newline="\n")
    return g


def _intro_plan(tmp):
    """A 2-campaign journey: ca -> FF9CustomMap-ca (6000..6001), cb -> FF9CustomMap-cb (6100..6101),
    hub 4500 -> FF9CustomMap-world_hub."""
    _make_campaign(tmp, "ca", members=["A1", "A2"], id_base=6000, mod_folder="FF9CustomMap-ca",
                   sources={"A1": 100})
    _make_campaign(tmp, "cb", members=["B1", "B2"], id_base=6100, mod_folder="FF9CustomMap-cb")
    p = _write_manifest(tmp, """
[[journey]]
id = "intro"
name = "Intro"
campaigns = ["ca", "cb"]
entry = { campaign = "ca", field = "A1" }
""")
    return journey.build_deploy_plan(journey.load_journeys(p))


def test_preflight_clean_when_no_foreign_folder(tmp_path):
    plan = _intro_plan(tmp_path)
    g = _fake_game(tmp_path, ["FF9CustomMap-ca", "FF9CustomMap-cb", "FF9CustomMap-world_hub", "MoguriMain"], {})
    col = journey.preflight_collisions(plan, g)
    assert not col.has_blockers
    assert journey.render_collision_report(col) == ""


def test_preflight_flags_foreign_id_collision(tmp_path):
    # a SUPERSEDED foreign folder still in FolderNames registers id 6000 (== ca's entry id) -> a blocker.
    plan = _intro_plan(tmp_path)
    g = _fake_game(tmp_path, ["FF9CustomMap-OLD", "FF9CustomMap-ca", "FF9CustomMap-cb"],
                   {"FF9CustomMap-OLD": [(6000, "OLD_FIELD")]})
    col = journey.preflight_collisions(plan, g)
    assert col.has_blockers
    assert "FF9CustomMap-OLD" in col.external_folders
    assert any(i == 6000 and f == "FF9CustomMap-OLD" for (i, _mf, _nm, f, _ok, _on) in col.external_ids)
    rep = journey.render_collision_report(col)
    assert "FF9CustomMap-OLD" in rep and "remove" in rep.lower()


def test_preflight_flags_foreign_hub_id_collision(tmp_path):
    # the hub's own id (4500) clashing with a foreign folder is a blocker too (the -disc1 vs hub 4600 case).
    plan = _intro_plan(tmp_path)
    g = _fake_game(tmp_path, ["FF9CustomMap-OLDHUB", "FF9CustomMap-ca", "FF9CustomMap-cb"],
                   {"FF9CustomMap-OLDHUB": [(4500, "OLD_HUB")]})
    col = journey.preflight_collisions(plan, g)
    assert col.has_blockers
    assert any(i == 4500 for (i, *_rest) in col.external_ids)


def test_preflight_excludes_this_journeys_own_folders(tmp_path):
    # ca's OWN folder still holds 6100 (cb's sibling band, a prior re-banded deploy): NOT a blocker (it's
    # wholesale-replaced) -- it surfaces only in stale_own, the informational "will be replaced" note.
    plan = _intro_plan(tmp_path)
    g = _fake_game(tmp_path, ["FF9CustomMap-ca", "FF9CustomMap-cb"],
                   {"FF9CustomMap-ca": [(6100, "STALE")]})
    col = journey.preflight_collisions(plan, g)
    assert not col.has_blockers
    assert any(f == "FF9CustomMap-ca" and 6100 in ids for (f, ids) in col.stale_own)
    rep = journey.render_collision_report(col)
    assert "FF9CustomMap-ca" in rep and "replaced" in rep.lower()


def test_preflight_includes_hub_evt_name(tmp_path):
    # the hub ships its own EVT_<token>.eb, so the name axis must sweep it vs foreign folders (review LOW #1).
    plan = _intro_plan(tmp_path)
    ids, eb, _scene = journey._journey_registrations(plan, hub_name="WORLD_HUB")
    assert 4500 in ids                                       # hub id still covered (the ID axis)
    assert eb.get("EVT_WORLD_HUB") == plan.hub_folder        # hub EVT name now on the NAME axis
    # ...and without a hub_name the hub EVT name is simply absent (no crash, no false entry)
    _ids2, eb2, _s2 = journey._journey_registrations(plan)
    assert not any(k.startswith("EVT_WORLD_HUB") for k in eb2)


def test_preflight_degrades_without_memoria_ini(tmp_path):
    # no Memoria.ini -> empty stack -> nothing to collide with (graceful, like the deploystack helpers).
    plan = _intro_plan(tmp_path)
    g = tmp_path / "empty_game"
    g.mkdir()
    col = journey.preflight_collisions(plan, g)
    assert not col.has_blockers and not col.stale_own
