"""Tests for P2 (campaign.py + the extract.py id_remap retarget).

The pure tests need no game: the retarget is exercised by monkeypatching eventscan.scan_content; id/name
assignment uses the STATIC field table (extract.ID_TO_FBG, baked from Memoria source -- no p0data); TOML
validity is checked with tomllib. A final real-bytes test forks the actual Ice Cavern and is skipped when
the FF9 install / UnityPy is absent."""

import tomllib
from collections import OrderedDict

import pytest

from ff9mapkit import campaign, chain, extract


# ---- retarget logic (monkeypatched scan_content, no game) -------------------------------
def _fake_content(gateways, encounter=None):
    return {"gateways": gateways, "music": None, "encounter": encounter,
            "control_direction": None, "ladders": []}


def test_imported_content_retarget(monkeypatch):
    Z = [[0, 0], [1, 0], [1, 1], [0, 1]]
    gws = [{"to": 301, "entrance": 1, "zone": Z}, {"to": 999, "entrance": 2, "zone": Z}]
    # encounter scene 301 == a field id on purpose: must NOT be retargeted (it's a battle scene)
    monkeypatch.setattr(extract.eventscan, "scan_content",
                        lambda eb: _fake_content(gws, encounter={"scenes": [301, 301, 301, 301], "freq": 40}))

    blocks, _cd, summ = extract._imported_content_toml(b"EVxx", id_remap={301: 6001})
    assert "to = 6001" in blocks                       # in-chain retargeted 301 -> 6001
    assert "# SEAM (out-of-chain): real field 999" in blocks
    assert "\nto = 999" not in blocks                  # 999 only appears commented (# to = 999)
    assert "scene = 301" in blocks                     # battle scene id left ALONE
    assert summ["gateways_retargeted"] == 1 and summ["gateways_seamed"] == 1

    live, _c, s2 = extract._imported_content_toml(b"EVxx", id_remap={301: 6001}, live_seams=True)
    assert "SEAM (live)" in live and "\nto = 999" in live   # live door kept

    plain, _c, s0 = extract._imported_content_toml(b"EVxx")  # id_remap=None -> unchanged behavior
    assert "to = 301" in plain and "to = 999" in plain
    assert s0["gateways_retargeted"] == 0 and s0["gateways_seamed"] == 0


# ---- a synthetic walk over REAL Ice Cavern ids (in the static table; no game) ------------
def _synthetic_result():
    Z = [[0, 0], [1, 0], [1, 1], [0, 1]]
    Z2 = [[5, 5], [6, 5], [6, 6], [5, 6]]

    def node(zone, edges, wm=None):
        return {"zone": zone, "found": True, "edges": edges, "overworld_exits": wm or [],
                "encounter": None, "music": None, "hop": 0}

    nodes = OrderedDict()
    nodes[300] = node("iccv", [{"to": 301, "kind": chain.WALK_IN, "entrance": 0, "zone": Z,
                                "story_conditional": False}], wm=[9000])
    nodes[301] = node("iccv", [
        {"to": 300, "kind": chain.WALK_IN, "entrance": 1, "zone": Z, "story_conditional": False},
        {"to": 302, "kind": chain.WALK_IN, "entrance": 1, "zone": Z2, "story_conditional": True},   # stacked
        {"to": 303, "kind": chain.WALK_IN, "entrance": 1, "zone": Z2, "story_conditional": True}])
    nodes[302] = node("iccv", [{"to": 301, "kind": chain.WALK_IN, "entrance": 2, "zone": Z,
                                "story_conditional": False}])
    nodes[303] = node("iccv", [{"to": 301, "kind": chain.WALK_IN, "entrance": 3, "zone": Z,
                                "story_conditional": False}])
    return chain.GraphResult(
        nodes=nodes, portals=[],
        seams=[{"from": 302, "to": 652, "entrance": 99, "trigger": "cutscene-loop", "to_zone": "kuin"}],
        unforkable=[{"from": 300, "to": 108}], seeds=[300], allowed_zones={"iccv"},
        truncated=False, remaining=0,
        bounds={"max_hops": 20, "max_fields": 25, "zones": ["iccv"], "follow_scripted": False,
                "stop_at_zone_boundary": True})


def test_member_name_rule():
    taken = set()
    assert campaign.member_name("fbg_n05_iccv_map085_ic_ent_0", 0, taken) == "IC_ENT"
    assert campaign.member_name("fbg_n06_vgdl_map097_dl_viw_0", 1, taken) == "DL_VIW"
    # collision -> zone-prefixed
    n1 = campaign.member_name("fbg_n05_iccv_map085_ic_ent_0", 2, taken)
    assert n1 != "IC_ENT" and n1 not in (set() | {"IC_ENT", "DL_VIW"})


def test_member_name_prefix_namespaces_globally():
    # --name-prefix makes the deployed FBG/EVT name globally unique (cross-worktree collision fix). The prefix
    # is normalized (uppercased, trailing _ stripped) and byte-identical to the base when empty.
    assert campaign.member_name("fbg_n06_vgdl_map102_dl_inn_1", 0, set()) == "DL_INN"  # no prefix unchanged
    assert campaign.member_name("fbg_n06_vgdl_map102_dl_inn_1", 0, set(), "DC") == "DC_DL_INN"
    assert campaign.member_name("fbg_n06_vgdl_map102_dl_inn_1", 0, set(), "dc_") == "DC_DL_INN"
    # assign_ids threads the prefix to every member
    _, _, name_of = campaign.assign_ids(_synthetic_result(), id_base=4100, name_prefix="DC")
    assert all(n.startswith("DC_") for n in name_of.values())


def test_assign_ids_contiguous_and_named():
    members_ids, new_id, name_of = campaign.assign_ids(_synthetic_result(), id_base=6000)
    assert members_ids == [300, 301, 302, 303]
    assert new_id == {300: 6000, 301: 6001, 302: 6002, 303: 6003}
    assert all(v >= 4000 for v in new_id.values()) and len(set(new_id.values())) == 4
    assert name_of[300] == "IC_ENT" and name_of[303] == "IC_JMP"


def test_assign_ids_fresh_matches_legacy():
    # prior=None / {} reproduces the original index-based allocation byte-for-byte (no behavior change on a
    # first fork).
    a = campaign.assign_ids(_synthetic_result(), id_base=6000)
    b = campaign.assign_ids(_synthetic_result(), id_base=6000, prior=None)
    c = campaign.assign_ids(_synthetic_result(), id_base=6000, prior={})
    assert a[1] == b[1] == c[1] == {300: 6000, 301: 6001, 302: 6002, 303: 6003}
    assert a[2] == b[2] == c[2]


def test_assign_ids_stable_reuses_prior_and_appends_above_max():
    # STABLE-ID re-fork: a re-discovered donor keeps its exact prior id+name; a net-new donor appends ABOVE
    # every prior id -- INCLUDING an unseen hand-appended one (6010) the walk doesn't rediscover -- so a stale
    # save can never land on the wrong field.
    prior = {300: (6000, "IC_ENT"), 301: (6001, "IC_STP"), 999: (6010, "OOB_DCK")}
    members_ids, new_id, name_of = campaign.assign_ids(_synthetic_result(), id_base=6000, prior=prior)
    assert members_ids == [300, 301, 302, 303]
    assert new_id[300] == 6000 and new_id[301] == 6001                  # frozen ids
    assert name_of[300] == "IC_ENT" and name_of[301] == "IC_STP"        # prior names reused verbatim
    assert new_id[302] == 6011 and new_id[303] == 6012                  # appended above max prior id (6010)
    assert 6010 not in new_id.values()                                 # never reuses a prior (even unseen) id
    assert len(set(new_id.values())) == 4


def test_assign_ids_reserved_protects_sourceless_prior_id():
    # a source-less prior member (a blank-room/logic member with no real donor) isn't in `prior`, but its id
    # must still be protected from reuse by a net-new donor -- passed via reserved_ids.
    prior = {300: (6000, "IC_ENT")}                 # one real donor frozen
    reserved = {6000, 6001}                          # 6001 = a source-less prior member's id (not in `prior`)
    _, new_id, _ = campaign.assign_ids(_synthetic_result(), id_base=6000, prior=prior, reserved_ids=reserved)
    assert new_id[300] == 6000                       # frozen
    assert 6001 not in new_id.values()               # the reserved source-less id is never re-allocated
    assert sorted(v for k, v in new_id.items() if k != 300) == [6002, 6003, 6004]   # net-new above max reserved


def test_assign_ids_new_name_disambiguates_against_prior():
    # a net-new member whose natural name was already claimed by a prior member must disambiguate (the `taken`
    # set is seeded with every prior name) -- else two members collide on the deployed FBG/EVT token.
    _, _, base = campaign.assign_ids(_synthetic_result(), id_base=6000)
    nat302 = base[302]
    prior = {300: (6000, nat302)}                                       # prior already holds 302's natural name
    _, _, name_of = campaign.assign_ids(_synthetic_result(), id_base=6000, prior=prior)
    assert name_of[300] == nat302
    assert name_of[302] != nat302
    assert len(set(name_of.values())) == 4


def test_collect_edges_and_seams():
    r = _synthetic_result()
    members_ids, new_id, name_of = campaign.assign_ids(r, id_base=6000)
    edges, seams = campaign._collect_edges_seams(r, members_ids, new_id, name_of)
    pairs = {(e["frm"], e["to"]) for e in edges}
    assert ("IC_ENT", "IC_STP") in pairs and ("IC_STP", "IC_TER") in pairs
    # the two stacked same-zone exits are flagged story-conditional
    sc = {(e["frm"], e["to"]) for e in edges if e["story_conditional"]}
    assert sc == {("IC_STP", "IC_TER"), ("IC_STP", "IC_JMP")}
    kinds = {s["kind"] for s in seams}
    assert {"scripted", "overworld", "menu"} <= kinds
    assert any(s["kind"] == "overworld" and s["to_real"] == "WORLDMAP" for s in seams)
    assert any(s["kind"] == "scripted" and s["to_real"] == 652 for s in seams)


def test_render_is_valid_toml():
    r = _synthetic_result()
    members_ids, new_id, name_of = campaign.assign_ids(r, id_base=6000)
    edges, seams = campaign._collect_edges_seams(r, members_ids, new_id, name_of)
    members = [campaign.Member(rid, new_id[rid], name_of[rid], "editable", 5, extract.ID_TO_FBG[rid],
                               f"{name_of[rid]}/{name_of[rid]}.field.toml", True) for rid in members_ids]
    plan = campaign.CampaignPlan(name="ICE", mod_folder="FF9CustomMap-ow", id_base=6000, flag_base=campaign.FIRST_SAFE_FLAG,
                                 flags_per_field=64, entry_name=name_of[members_ids[0]], entry_entrance=0,
                                 members=members, edges=edges, seams=seams)
    d = tomllib.loads(campaign.render_campaign_toml(plan))     # must parse
    assert d["campaign"]["id_base"] == 6000 and d["campaign"]["entry_field"] == "IC_ENT"
    assert [f["id"] for f in d["field"]] == [6000, 6001, 6002, 6003]
    names = {f["name"] for f in d["field"]}
    for e in d["edge"]:                                        # every edge resolves to a member name
        assert e["from"] in names and e["to"] in names
    assert not any(e["to"] in {"300", "301", "302", "303"} for e in d["edge"])   # never a raw real id
    assert {s["kind"] for s in d["seam"]} >= {"scripted", "overworld", "menu"}


# ---- real-bytes: fork the actual Ice Cavern (skip without the game) ----------------------
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_ice_cavern_campaign(tmp_path):
    from ff9mapkit import eventscan
    bundle = extract.EventBundle()

    def zone_fn(fid):
        return chain.zone_label(extract.ID_TO_FBG.get(int(fid)))

    def scan_fn(fid):
        eb = bundle.eb_for_id(fid)
        if eb is None:
            return {"found": False}
        w = eventscan.scan_all_warps(eb)
        edges = [{"to": g["to"], "kind": chain.WALK_IN, "entrance": g["entrance"], "zone": g["zone"],
                  "story_conditional": g["story_conditional"]} for g in w["walk_in"]]
        edges += [{"to": s["to"], "kind": chain.SCRIPTED, "entrance": s["entrance"],
                   "trigger": s["trigger"]} for s in w["scripted"]]
        return {"found": True, "edges": edges, "overworld_exits": w["overworld_exits"],
                "encounter": eventscan.scan_encounter(eb), "music": eventscan.scan_music(eb)}

    result = chain.walk(300, scan_fn, zone_fn,
                        forkable_fn=lambda f: int(f) in extract.ID_TO_FBG, zones=["iccv", "vgdl"])
    plan = campaign.write_campaign(result, tmp_path, id_base=6000, name="ICE_CAVERN",
                                   mod_folder="FF9CustomMap-ow")
    d = tomllib.loads((tmp_path / "campaign.toml").read_text(encoding="utf-8"))

    assert len(d["field"]) == 13
    assert [f["id"] for f in d["field"]] == list(range(6000, 6013))
    assert [f["source"] for f in d["field"]] == list(range(300, 313))
    assert d["campaign"]["entry_field"] == "IC_ENT"
    names = {f["name"] for f in d["field"]}
    for e in d["edge"]:
        assert e["from"] in names and e["to"] in names
    # every member toml's live gateway points at a 6000-band id (the retarget invariant)
    member_ids = {f["id"] for f in d["field"]}
    for f in d["field"]:
        text = (tmp_path / f["toml"]).read_text(encoding="utf-8")
        for line in text.splitlines():
            ls = line.strip()
            if ls.startswith("to =") and not ls.startswith("#"):
                assert int(ls.split("=", 1)[1].strip()) in member_ids
    # IC_WAF (308) has no walk-in gateway -> a scripted seam, not an edge
    assert any(s["kind"] == "scripted" for s in d["seam"])
    # all 13 are area<10 -> NATIVE fork (own atlas+.bgs, no .bgx; seamless, no in-game export needed)
    assert all(f["mode"] == "native" for f in d["field"])
    assert not any(f.get("needs_export") for f in d["field"])   # native ships bundle/mod art -> no stubs


def _ice_walk():
    from ff9mapkit import eventscan
    bundle = extract.EventBundle()

    def scan_fn(fid):
        eb = bundle.eb_for_id(fid)
        if eb is None:
            return {"found": False}
        w = eventscan.scan_all_warps(eb)
        edges = [{"to": g["to"], "kind": chain.WALK_IN, "entrance": g["entrance"], "zone": g["zone"],
                  "story_conditional": g["story_conditional"]} for g in w["walk_in"]]
        edges += [{"to": s["to"], "kind": chain.SCRIPTED, "entrance": s["entrance"],
                   "trigger": s["trigger"]} for s in w["scripted"]]
        return {"found": True, "edges": edges, "overworld_exits": w["overworld_exits"],
                "encounter": eventscan.scan_encounter(eb), "music": eventscan.scan_music(eb)}

    return chain.walk(300, scan_fn, lambda fid: chain.zone_label(extract.ID_TO_FBG.get(int(fid))),
                      forkable_fn=lambda f: int(f) in extract.ID_TO_FBG, zones=["iccv", "vgdl"])


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_write_campaign_stable_reuse_append_and_carry(tmp_path):
    # Re-fork on top of an existing campaign: re-discovered donors keep their ids (saves survive), a prior
    # member the walk doesn't re-discover (a hand-appended out-of-band fork) is CARRIED at its id, and net-new
    # donors append ABOVE every prior id. Members are emitted id-sorted (so flag windows stay position-stable).
    result = _ice_walk()
    # VERBATIM (the real fork mode): exercises the edge-synth that crashed on a carried Field() destination.
    plan1 = campaign.write_campaign(result, tmp_path, id_base=6000, name="ICE", mod_folder="FF9CustomMap-ow",
                                    verbatim=True)
    ids1 = {m.real_id: m.new_id for m in plan1.members}

    # A synthetic prior: freeze two real donors at their fork-1 ids + a HAND-APPENDED out-of-band member (real
    # id 506, fork 6500) whose dir exists on disk but the walk never visits (mirrors the cargo-deck 506 fix).
    oob = tmp_path / "OOB_DCK"
    oob.mkdir()
    (oob / "OOB_DCK.field.toml").write_text("[field]\nid = 6500\n", encoding="utf-8")
    blank = tmp_path / "BLANK_RM"          # a SOURCE-LESS prior member (real_id 0) -- must still be protected+carried
    blank.mkdir()
    (blank / "BLANK_RM.field.toml").write_text("[field]\nid = 6499\n", encoding="utf-8")
    # A carried member that a RE-FORKED verbatim member warps to: Ice Cavern 306 has Field(652), and 652 (kuin)
    # is out-of-zone so it's carried -> the edge-synth must resolve name_of[652] (regressions the KeyError where a
    # carried id was in new_id but not name_of).
    kuin = tmp_path / "KUIN_X"
    kuin.mkdir()
    (kuin / "KUIN_X.field.toml").write_text("[field]\nid = 6498\n", encoding="utf-8")
    prior = campaign.CampaignPlan(
        name="ICE", mod_folder="FF9CustomMap-ow", id_base=6000, flag_base=campaign.FIRST_SAFE_FLAG,
        flags_per_field=64, entry_name="IC_ENT", entry_entrance=0,
        members=[campaign.Member(300, ids1[300], "IC_ENT", "native", 0, "", "IC_ENT/IC_ENT.field.toml", False),
                 campaign.Member(301, ids1[301], "IC_STP", "native", 0, "", "IC_STP/IC_STP.field.toml", False),
                 campaign.Member(506, 6500, "OOB_DCK", "native", 0, "", "OOB_DCK/OOB_DCK.field.toml", False),
                 campaign.Member(652, 6498, "KUIN_X", "native", 0, "", "KUIN_X/KUIN_X.field.toml", False),
                 campaign.Member(0, 6499, "BLANK_RM", "editable", 0, "", "BLANK_RM/BLANK_RM.field.toml", False)])

    plan2 = campaign.write_campaign(result, tmp_path, id_base=6000, name="ICE",
                                    mod_folder="FF9CustomMap-ow", verbatim=True, prior_plan=prior)
    ids2 = {m.real_id: m.new_id for m in plan2.members}
    assert ids2[300] == ids1[300] and ids2[301] == ids1[301]    # frozen -> in-fork saves survive
    assert ids2[506] == 6500 and "OOB_DCK" in plan2.carried     # the out-of-band fork carried, not dropped
    assert "BLANK_RM" in plan2.carried                          # the SOURCE-LESS prior member carried too
    assert "KUIN_X" in plan2.carried                            # the warped-to carried member (306->Field(652))
    assert any(e["to"] == "KUIN_X" for e in plan2.edges)        # edge-synth resolved name_of[652] (no KeyError)
    assert plan2.entry_name == "IC_ENT"                         # prior entry preserved
    carried_reals = (506, 652)                                  # carried prior members (+ source-less real_id 0)
    newd = [m for m in plan2.members if m.real_id and m.real_id not in (300, 301, *carried_reals)]
    assert newd and all(m.new_id > 6500 for m in newd)          # net-new donors append above EVERY prior id (incl 6499)
    assert {6498, 6499, 6500}.isdisjoint(m.new_id for m in newd)  # carried/source-less ids reserved, never reused
    assert [m.new_id for m in plan2.members] == sorted(m.new_id for m in plan2.members)   # id-sorted
    assert len({m.new_id for m in plan2.members}) == len(plan2.members)                   # all distinct
    # the carried members are in the written manifest at their frozen ids
    d2 = tomllib.loads((tmp_path / "campaign.toml").read_text(encoding="utf-8"))
    carried = next(f for f in d2["field"] if f["source"] == 506)
    assert carried["id"] == 6500 and carried["name"] == "OOB_DCK"
    assert any(f["name"] == "BLANK_RM" and f["id"] == 6499 for f in d2["field"])


# ---- P3: load_campaign + build_campaign -------------------------------------------------
def test_load_campaign_round_trips(tmp_path):
    r = _synthetic_result()
    members_ids, new_id, name_of = campaign.assign_ids(r, id_base=6000)
    edges, seams = campaign._collect_edges_seams(r, members_ids, new_id, name_of)
    members = [campaign.Member(rid, new_id[rid], name_of[rid], "editable", 5, extract.ID_TO_FBG[rid],
                               f"{name_of[rid]}/{name_of[rid]}.field.toml", rid == 300) for rid in members_ids]
    plan = campaign.CampaignPlan(name="ICE", mod_folder="FF9CustomMap-ow", id_base=6000, flag_base=campaign.FIRST_SAFE_FLAG,
                                 flags_per_field=64, entry_name="IC_ENT", entry_entrance=0,
                                 members=members, edges=edges, seams=seams)
    p = tmp_path / "campaign.toml"
    p.write_text(campaign.render_campaign_toml(plan), encoding="utf-8")

    loaded = campaign.load_campaign(p)
    assert loaded.name == "ICE" and loaded.mod_folder == "FF9CustomMap-ow"
    assert loaded.id_base == 6000 and loaded.entry_name == "IC_ENT"
    assert [m.new_id for m in loaded.members] == [6000, 6001, 6002, 6003]
    assert [m.name for m in loaded.members] == ["IC_ENT", "IC_STP", "IC_TER", "IC_JMP"]
    assert all(m.mode == "editable" for m in loaded.members)
    assert loaded.members[0].needs_export and not any(m.needs_export for m in loaded.members[1:])
    assert sum(1 for e in loaded.edges if e["story_conditional"]) == 2     # the 307-style stacked pair
    assert seams and all("frm" in s for s in loaded.seams)                 # seams normalized like edges
    g = campaign.campaign_graph(loaded)                                    # graph sees the loaded seams
    assert sum(len(n.seams) for n in g.nodes) == len(loaded.seams)         # (none dropped on the 'from' key)


def _plan_with_ids(ids):
    members = [campaign.Member(0, i, f"F{i}", "borrow", 11, "", f"F{i}/F{i}.field.toml", False) for i in ids]
    return campaign.CampaignPlan(name="X", mod_folder="M", id_base=4000, flag_base=campaign.FIRST_SAFE_FLAG, flags_per_field=64,
                                 entry_name="A", entry_entrance=0, members=members)


def test_validate_ids():
    campaign.validate_ids(_plan_with_ids([6000, 6001, 6002]))            # ok
    for bad in ([6000, 6000], [3999], [40000], []):
        with pytest.raises(campaign.CampaignError):
            campaign.validate_ids(_plan_with_ids(bad))


# ---- P5: campaign lint -------------------------------------------------------------------
def _lint_plan(tmp_path, *, members=None, edges=None, seams=None, entry="A", member_content=None):
    members = members if members is not None else [
        campaign.Member(300, 6000, "A", "borrow", 11, "", "A/A.field.toml", False),
        campaign.Member(301, 6001, "B", "borrow", 11, "", "B/B.field.toml", False)]
    plan = campaign.CampaignPlan(name="C", mod_folder="M", id_base=6000, flag_base=campaign.FIRST_SAFE_FLAG,
                                 flags_per_field=64, entry_name=entry, entry_entrance=0,
                                 members=members, edges=edges or [], seams=seams or [])
    for m in members:                                      # materialize minimal member field.tomls
        d = tmp_path / m.name
        d.mkdir(parents=True, exist_ok=True)
        extra = (member_content or {}).get(m.name, "")
        (d / f"{m.name}.field.toml").write_text(
            f'[field]\nid = {m.new_id}\nname = "{m.name}"\narea = 11\n{extra}', encoding="utf-8")
    return plan


def test_lint_structural_pass(tmp_path):
    plan = _lint_plan(tmp_path, edges=[{"frm": "A", "to": "B", "entrance": 0}])
    errors, warnings = campaign.lint_campaign(plan, tmp_path)
    assert errors == []


def test_lint_dangling_edge_and_entry(tmp_path):
    plan = _lint_plan(tmp_path, edges=[{"frm": "A", "to": "GHOST", "entrance": 0}], entry="NOPE")
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert any("GHOST" in e and "not a campaign member" in e for e in errors)
    assert any("entry_field" in e for e in errors)


def test_lint_bad_seam(tmp_path):
    bad = _lint_plan(tmp_path, seams=[{"frm": "A", "to_real": "FOO", "kind": "scripted"}])
    assert any("to_real" in e for e in campaign.lint_campaign(bad, tmp_path)[0])
    ok = _lint_plan(tmp_path, seams=[{"frm": "A", "to_real": "WORLDMAP", "kind": "overworld"},
                                     {"frm": "B", "to_real": 652, "kind": "scripted"}])
    assert campaign.lint_campaign(ok, tmp_path)[0] == []


def test_lint_duplicate_member_names(tmp_path):
    dup = [campaign.Member(300, 6000, "A", "borrow", 11, "", "A/A.field.toml", False),
           campaign.Member(301, 6001, "A", "borrow", 11, "", "A/A.field.toml", False)]   # same name
    plan = _lint_plan(tmp_path, members=dup)
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert any("duplicate member names" in e and "'A'" in e for e in errors)


def test_lint_missing_member_file(tmp_path):
    plan = _lint_plan(tmp_path)
    (tmp_path / "B" / "B.field.toml").unlink()              # remove one member's toml
    assert any("not found" in e for e in campaign.lint_campaign(plan, tmp_path)[0])


def test_lint_ungated_stacked_door_warns(tmp_path):
    plan = _lint_plan(tmp_path, edges=[
        {"frm": "A", "to": "B", "entrance": 0, "story_conditional": True},
        {"frm": "A", "to": "A", "entrance": 0, "story_conditional": True}])
    _, warnings = campaign.lint_campaign(plan, tmp_path)
    assert any("stacked same-zone" in w for w in warnings)


def test_lint_stacked_door_suppressed_for_verbatim(tmp_path):
    # A --verbatim fork ships the donor's WHOLE .eb, so an if(flag){A}else{B} story-conditional door is
    # carried + resolved by the engine -- there's no authored [[gateway]] to gate, so the (g) warning is a
    # false positive and must be suppressed. (The advice "set requires_flag in its field.toml" only applies
    # to a declarative fork that re-authors gateways from the [[edge]]s.)
    edges = [{"frm": "A", "to": "B", "entrance": 0, "story_conditional": True},
             {"frm": "A", "to": "A", "entrance": 0, "story_conditional": True}]
    plan = _lint_plan(tmp_path, edges=edges)
    plan.verbatim = True
    _, warnings = campaign.lint_campaign(plan, tmp_path)
    assert not any("stacked same-zone" in w for w in warnings)


def test_lint_stacked_door_fires_for_degraded_verbatim_member(tmp_path):
    # A verbatim chain whose member DEGRADED to a logic-only stub (needs_export) re-authors DECLARATIVE gateways,
    # so its stacked story-conditional door is genuinely ungated -- the warning must STILL fire even though the
    # plan is verbatim (the per-member fix; whole-plan suppression was a false-negative the review caught).
    mem = [campaign.Member(300, 6000, "A", "native", 11, "", "A/A.field.toml", True),     # needs_export stub
           campaign.Member(301, 6001, "B", "native", 11, "", "B/B.field.toml", False)]
    plan = _lint_plan(tmp_path, members=mem, edges=[
        {"frm": "A", "to": "B", "entrance": 0, "story_conditional": True},
        {"frm": "A", "to": "A", "entrance": 0, "story_conditional": True}])
    plan.verbatim = True
    _, warnings = campaign.lint_campaign(plan, tmp_path)
    assert any("stacked same-zone" in w and "member A" in w for w in warnings), warnings


def test_verbatim_story_conditional_marker_survives_roundtrip(tmp_path):
    # the explicit `story_conditional = true` marker must round-trip even for a VERBATIM plan (which omits the
    # gated_by placeholder), so a re-loaded plan's degraded member still trips the stacked-door warning.
    mem = [campaign.Member(300, 6000, "A", "native", 11, "", "A/A.field.toml", True)]
    plan = campaign.CampaignPlan(name="C", mod_folder="M", id_base=6000, flag_base=campaign.FIRST_SAFE_FLAG,
                                 flags_per_field=64, entry_name="A", entry_entrance=0, members=mem, verbatim=True,
                                 edges=[{"frm": "A", "to": "A", "entrance": 0, "story_conditional": True},
                                        {"frm": "A", "to": "A", "entrance": 1, "story_conditional": True}])
    text = campaign.render_campaign_toml(plan)
    assert "story_conditional = true" in text and "gated_by" not in text   # verbatim: marker yes, gated_by no
    p = tmp_path / "campaign.toml"
    p.write_text(text, encoding="utf-8")
    loaded = campaign.load_campaign(p)
    assert sum(1 for e in loaded.edges if e["story_conditional"]) == 2 and loaded.verbatim is True


def test_campaign_toml_roundtrips_verbatim_flag(tmp_path):
    # the verbatim marker must PERSIST (render -> load) so lint stays verbatim-aware on a re-read campaign.toml.
    plan = campaign.CampaignPlan(name="C", mod_folder="M", id_base=6000, flag_base=campaign.FIRST_SAFE_FLAG,
                                 flags_per_field=64, entry_name="A", entry_entrance=0,
                                 members=[campaign.Member(300, 6000, "A", "native", 11, "", "A/A.field.toml", False)],
                                 verbatim=True)
    text = campaign.render_campaign_toml(plan)
    assert "verbatim        = true" in text
    p = tmp_path / "campaign.toml"
    p.write_text(text, encoding="utf-8")
    assert campaign.load_campaign(p).verbatim is True
    # a non-verbatim plan emits no verbatim line + loads False (back-compat with existing campaign.tomls)
    plan.verbatim = False
    assert "verbatim" not in campaign.render_campaign_toml(plan)


def test_lint_flag_dangling_and_dupwriter(tmp_path):
    # B requires flag 8520 that nobody sets -> dangling; A+B both set 8520 -> covered separately
    dangling = _lint_plan(tmp_path, member_content={
        "B": '[[gateway]]\nto = 6000\nentrance = 0\nzone = [[0,0]]\nrequires_flag = 8520\n'})
    _, w1 = campaign.lint_campaign(dangling, tmp_path)
    assert any("8520" in w and "permanently locked" in w for w in w1)

    dup = _lint_plan(tmp_path, member_content={
        "A": '[[event]]\nname = "x"\nflag = 8520\n', "B": '[[event]]\nname = "y"\nflag = 8520\n'})
    _, w2 = campaign.lint_campaign(dup, tmp_path)
    assert any("8520" in w and "multiple members" in w for w in w2)


def test_lint_empty_forks_have_no_flag_warnings(tmp_path):
    # the import-chain reality: empty rooms -> structural checks pass, zero flag findings
    plan = _lint_plan(tmp_path, edges=[{"frm": "A", "to": "B", "entrance": 0}])
    errors, warnings = campaign.lint_campaign(plan, tmp_path)
    assert errors == [] and not any("flag" in w for w in warnings)


def test_lint_resolves_named_gates(tmp_path):
    # F2: a member gating on a shared flag by NAME is now SEEN by the cross-field check (was skipped).
    # (a) name defined + set by a sibling (its event's once-flag) -> the name-based gate resolves -> clean
    ok = _lint_plan(tmp_path, member_content={
        "A": '[[event]]\nname = "s"\nzone = [[0,0]]\ngil = 1\nflag = "boss_dead"\n',
        "B": '[[gateway]]\nto = 6000\nentrance = 0\nzone = [[0,0]]\nrequires_flag = "boss_dead"\n'})
    ok.flags = [{"name": "boss_dead", "index": 8700}]              # above the 2 member blocks [8512,8639]
    errors, warnings = campaign.lint_campaign(ok, tmp_path)
    assert errors == [] and not any("permanently locked" in w for w in warnings)
    # (b) name defined but nobody SETS it -> dangling warning (name-aware now, not silently skipped)
    dangling = _lint_plan(tmp_path, member_content={
        "B": '[[gateway]]\nto = 6000\nentrance = 0\nzone = [[0,0]]\nrequires_flag = "boss_dead"\n'})
    dangling.flags = [{"name": "boss_dead", "index": 8700}]
    _, w2 = campaign.lint_campaign(dangling, tmp_path)
    assert any("8700" in w and "permanently locked" in w for w in w2)
    # (c) gate on a name defined NOWHERE -> hard error (the build would fail to resolve it too)
    ghost = _lint_plan(tmp_path, member_content={
        "B": '[[gateway]]\nto = 6000\nentrance = 0\nzone = [[0,0]]\nrequires_flag = "ghost_flag"\n'})
    errors3, _ = campaign.lint_campaign(ghost, tmp_path)
    assert any("ghost_flag" in e for e in errors3)


def test_lint_safe_band_default_is_clean(tmp_path):
    # the new default flag_base (FIRST_SAFE_FLAG=8512) is clear of all real-FF9 usage -> no band errors
    plan = _lint_plan(tmp_path, edges=[{"frm": "A", "to": "B", "entrance": 0}])
    assert plan.flag_base == campaign.FIRST_SAFE_FLAG
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert not any(("chest" in e.lower() or "safe floor" in e) for e in errors)


def test_lint_chest_band_collision_errors(tmp_path):
    # the PRE-FIX flag_base=8300 + 64/field collides with real-FF9 chest flags (bits 8376-8511): member A's
    # block dips below the safe floor, member B's intersects the chest band -> save-corruption errors.
    plan = _lint_plan(tmp_path, edges=[{"frm": "A", "to": "B", "entrance": 0}])
    plan.flag_base = 8300
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert any("safe floor" in e for e in errors)                 # A: 8300-8363 < 8512
    assert any("treasure-chest" in e for e in errors)             # B: 8364-8427 hits 8376-8511


def test_lint_explicit_flag_in_chest_band_errors(tmp_path):
    # an explicit story flag inside real-FF9's chest band 8376-8511 -> save corruption, hard error
    plan = _lint_plan(tmp_path, member_content={
        "B": '[[gateway]]\nto = 6000\nentrance = 0\nzone = [[0,0]]\nrequires_flag = 8400\n'})
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert any("8400" in e and "treasure-chest" in e for e in errors)


def test_lint_shared_flag_valid(tmp_path):
    # a shared [[flag]] ABOVE the two member blocks (8512-8639) and inside the band -> clean
    plan = _lint_plan(tmp_path)
    plan.flags = [{"name": "boss_dead", "index": 8700}]
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert not any("flag" in e.lower() for e in errors)


def test_lint_shared_flag_in_chest_band_errors(tmp_path):
    plan = _lint_plan(tmp_path)
    plan.flags = [{"name": "bad", "index": 8400}]            # chest band
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert any("treasure-chest" in e for e in errors)


def test_lint_shared_flag_collides_member_block_errors(tmp_path):
    plan = _lint_plan(tmp_path)                              # members A/B -> auto blocks 8512-8639
    plan.flags = [{"name": "boom", "index": 8520}]          # inside member A's block
    errors, _ = campaign.lint_campaign(plan, tmp_path)
    assert any("per-member auto-flag blocks" in e for e in errors)


def test_campaign_render_roundtrips_shared_flags(tmp_path):
    plan = _lint_plan(tmp_path)
    plan.flags = [{"name": "boss_dead", "index": 8700}]
    f = tmp_path / "campaign.toml"
    f.write_text(campaign.render_campaign_toml(plan), encoding="utf-8")
    assert campaign.load_campaign(f).flags == [{"name": "boss_dead", "index": 8700}]


# ---- P6: mutation / creation API (new_campaign / add_field / remove / rename / set_entry) -----
def test_new_campaign_empty_round_trips(tmp_path):
    plan = campaign.new_campaign("MYGAME", "FF9CustomMap-bb", tmp_path, id_base=30100)
    assert plan.members == [] and plan.entry_name == ""
    assert (tmp_path / "campaign.toml").is_file()
    loaded = campaign.load_campaign(tmp_path / "campaign.toml")        # parses + round-trips
    assert loaded.name == "MYGAME" and loaded.id_base == 30100 and loaded.members == []


def test_add_blank_fields_and_edges_offline(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    a = campaign.add_field(plan, tmp_path, name="HUB")                 # blank member (no game)
    b = campaign.add_field(plan, tmp_path, name="NORTH")
    assert (a.new_id, b.new_id) == (30100, 30101)                     # next-free ids, contiguous here
    assert plan.entry_name == "HUB"                                    # first add becomes entry
    assert (tmp_path / "HUB" / "hub.field.toml").is_file()             # pack scaffolded a buildable room
    assert (tmp_path / "HUB" / "art" / "back.png").is_file()
    campaign.add_edge(plan, tmp_path, "HUB", "NORTH", entrance=1)
    # reload + lint the whole thing from disk: structurally valid, both ends real, HUB->NORTH resolves
    loaded = campaign.load_campaign(tmp_path / "campaign.toml")
    assert {m.name for m in loaded.members} == {"HUB", "NORTH"}
    errors, _ = campaign.lint_campaign(loaded, tmp_path)
    assert errors == []
    g = campaign.campaign_graph(loaded)
    assert g.by_name["HUB"].out_edges == [{"to": "NORTH", "entrance": 1, "gated": False}]


def test_add_field_rejects_duplicate_name(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    campaign.add_field(plan, tmp_path, name="HUB")
    with pytest.raises(campaign.CampaignError):
        campaign.add_field(plan, tmp_path, name="HUB")


def test_remove_field_prunes_refs_and_subdir(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    campaign.add_field(plan, tmp_path, name="HUB")
    campaign.add_field(plan, tmp_path, name="NORTH")
    campaign.add_field(plan, tmp_path, name="ATTIC")
    campaign.add_edge(plan, tmp_path, "HUB", "NORTH")
    campaign.add_edge(plan, tmp_path, "NORTH", "ATTIC")
    campaign.remove_field(plan, tmp_path, "NORTH")
    assert {m.name for m in plan.members} == {"HUB", "ATTIC"}
    assert not (tmp_path / "NORTH").exists()                          # subdir gone
    assert plan.edges == []                                            # both edges referenced NORTH -> pruned
    assert campaign.load_campaign(tmp_path / "campaign.toml").edges == []
    # removing the entry re-points it
    campaign.remove_field(plan, tmp_path, "HUB")
    assert plan.entry_name == "ATTIC"


def test_rename_field_moves_subdir_and_rekeys(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    campaign.add_field(plan, tmp_path, name="HUB")
    campaign.add_field(plan, tmp_path, name="NORTH")
    campaign.add_edge(plan, tmp_path, "HUB", "NORTH", entrance=2)
    campaign.set_entry(plan, tmp_path, "HUB")
    campaign.rename_field(plan, tmp_path, "HUB", "LOBBY")
    assert {m.name for m in plan.members} == {"LOBBY", "NORTH"}
    assert (tmp_path / "LOBBY").is_dir() and not (tmp_path / "HUB").exists()
    assert plan.entry_name == "LOBBY"
    e = plan.edges[0]
    assert e["frm"] == "LOBBY" and e["to"] == "NORTH"                  # edge rekeyed
    loaded = campaign.load_campaign(tmp_path / "campaign.toml")        # the renamed member still resolves
    m = next(x for x in loaded.members if x.name == "LOBBY")
    assert (tmp_path / m.toml_rel).is_file()
    assert campaign.lint_campaign(loaded, tmp_path)[0] == []


def test_rename_rejects_collision(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    campaign.add_field(plan, tmp_path, name="HUB")
    campaign.add_field(plan, tmp_path, name="NORTH")
    with pytest.raises(campaign.CampaignError):
        campaign.rename_field(plan, tmp_path, "HUB", "NORTH")


def test_set_entry_validates(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    campaign.add_field(plan, tmp_path, name="HUB")
    with pytest.raises(campaign.CampaignError):
        campaign.set_entry(plan, tmp_path, "GHOST")
    campaign.set_entry(plan, tmp_path, "HUB", entrance=3)
    assert plan.entry_name == "HUB" and plan.entry_entrance == 3


def test_mutation_rejects_path_traversal(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    plan.members.append(campaign.Member(0, 30100, "EVIL", "editable", 11, "", "../EVIL/evil.field.toml", False))
    with pytest.raises(campaign.CampaignError):                      # _safe_member_dir blocks the rmtree
        campaign.remove_field(plan, tmp_path, "EVIL")
    assert any("escapes" in e for e in campaign.lint_campaign(plan, tmp_path)[0])   # lint surfaces it too


def test_member_name_validation_rejects_separators(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)
    for bad in ("../x", "a/b", "a\\b", "  ", "."):
        with pytest.raises(campaign.CampaignError):
            campaign.add_field(plan, tmp_path, name=bad)
    campaign.add_field(plan, tmp_path, name="OK")
    with pytest.raises(campaign.CampaignError):
        campaign.rename_field(plan, tmp_path, "OK", "../escape")


def test_add_remove_shared_flag(tmp_path):
    plan = campaign.new_campaign("MY", "M", tmp_path, id_base=30100)   # flag_base = FIRST_SAFE_FLAG (8512)
    campaign.add_field(plan, tmp_path, name="HUB")
    campaign.add_field(plan, tmp_path, name="NORTH")                   # member blocks span [8512, 8639]
    f = campaign.add_flag(plan, tmp_path, "boss_dead")                 # auto-index just ABOVE the blocks
    assert f["name"] == "boss_dead" and f["index"] == 8640
    assert campaign.lint_campaign(plan, tmp_path)[0] == []             # clear of member blocks + chest band
    loaded = campaign.load_campaign(tmp_path / "campaign.toml")        # round-trips
    assert loaded.flags == [{"name": "boss_dead", "index": 8640}]
    campaign.add_flag(plan, tmp_path, "switch", index=9000)           # explicit safe index
    with pytest.raises(campaign.CampaignError):
        campaign.add_flag(plan, tmp_path, "boss_dead")                # dup name
    with pytest.raises(campaign.CampaignError):
        campaign.add_flag(plan, tmp_path, "again", index=9000)        # dup index
    with pytest.raises(campaign.CampaignError):
        campaign.add_flag(plan, tmp_path, "inchest", index=8400)      # below floor / in chest band
    campaign.remove_flag(plan, tmp_path, "boss_dead")
    assert {x["name"] for x in plan.flags} == {"switch"}
    with pytest.raises(campaign.CampaignError):
        campaign.remove_flag(plan, tmp_path, "nope")


def test_campaign_flag_block_overflow_raises(tmp_path):
    # master's _FlagAlloc packs a member's auto once-events into base+1..base+EVENTS_PER_FIELD; Phase D
    # GUARDS the overflow (raise, not silently alias the choice sub-band -> save corruption).
    from ff9mapkit import build
    evs = "".join(f'[[event]]\nname = "e{i}"\nzone = [[{i},0],[{i+1},0],[{i+1},1],[{i},1]]\ngil = 1\n\n'
                  for i in range(build.EVENTS_PER_FIELD + 1))           # one past the per-member event slots
    p = tmp_path / "z.field.toml"
    p.write_text('[field]\nid = 4003\nname = "Z"\narea = 11\ntext_block = 1073\n\n'
                 '[camera]\npitch = 45\nfov = 42.2\n\n'
                 '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n' + evs, encoding="utf-8")
    proj = build.FieldProject.load(p)
    _m, _t, et, _c, _x, _o, _ = build.collect_text(proj)
    build.build_script(proj, "us", {}, event_txids=et)                 # single-field (no block): builds fine
    proj.flag_base = campaign.FIRST_SAFE_FLAG                          # campaign member: now it overflows
    proj.flags_per_field = 64
    with pytest.raises(build.BuildError):
        build.build_script(proj, "us", {}, event_txids=et)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_add_field_forks_a_real_field(tmp_path):
    # the fork path: add a real field (Ice Cavern entrance 300) by id -- needs the game install
    plan = campaign.new_campaign("ICE", "M", tmp_path, id_base=30100)
    m = campaign.add_field(plan, tmp_path, name="IC_ENT", source=300)
    assert m.real_id == 300 and m.new_id == 30100 and m.mode in ("borrow", "native")
    assert (tmp_path / m.toml_rel).is_file()
    assert campaign.lint_campaign(campaign.load_campaign(tmp_path / "campaign.toml"), tmp_path)[0] == []


def test_resolve_source_id_disambiguates_a_shared_folder():
    # add_field must fork the donor by ID (not the FBG folder), so a field that SHARES its background folder
    # with another (52/3008 -- the same room at different beats) forks ITS OWN .eb, not the folder-key winner
    # (the review's HIGH finding -- the bug write_campaign was fixed for, originally left in add_field). Offline.
    assert campaign._resolve_source_id(3008) == 3008          # an id resolves to itself, not the folder's first id
    assert campaign._resolve_source_id("52") == 52
    with pytest.raises(campaign.CampaignError):               # a SHARED-folder substring matches 52 AND 3008
        campaign._resolve_source_id("tshp_map005_th_met")


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_build_all(tmp_path):
    from ff9mapkit import eventscan
    bundle = extract.EventBundle()

    def zone_fn(fid):
        return chain.zone_label(extract.ID_TO_FBG.get(int(fid)))

    def scan_fn(fid):
        eb = bundle.eb_for_id(fid)
        if eb is None:
            return {"found": False}
        w = eventscan.scan_all_warps(eb)
        edges = [{"to": g["to"], "kind": chain.WALK_IN, "entrance": g["entrance"], "zone": g["zone"],
                  "story_conditional": g["story_conditional"]} for g in w["walk_in"]]
        return {"found": True, "edges": edges, "overworld_exits": w["overworld_exits"],
                "encounter": eventscan.scan_encounter(eb), "music": eventscan.scan_music(eb)}

    result = chain.walk(300, scan_fn, zone_fn, forkable_fn=lambda f: int(f) in extract.ID_TO_FBG,
                        zones=["iccv"], max_fields=2)
    camp = tmp_path / "camp"
    campaign.write_campaign(result, camp, id_base=30100, name="ICE2", mod_folder="FF9CustomMap-ow")
    try:
        info = campaign.build_campaign(camp / "campaign.toml", out=tmp_path / "dist")
    except FileNotFoundError as e:                       # base templates not extracted on this machine
        if "extract-templates" in str(e):
            pytest.skip("base templates not extracted (run ff9mapkit extract-templates)")
        raise

    dist = tmp_path / "dist"
    lines = (dist / "DictionaryPatch.txt").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2 and len(info["dictionary"]) == 2
    toks = [ln.split() for ln in lines]                  # FieldScene <id> <area> <mapid> <name> <textid>
    assert all(t[0] == "FieldScene" for t in toks)
    assert sorted(int(t[1]) for t in toks) == [30100, 30101]            # ids = id_base + i
    assert all(int(t[5]) == 1073 for t in toks)                         # textid = a VALID MesDB base block
    md = (dist / "ModDescription.xml").read_text(encoding="utf-8")
    assert "<InstallationPath>FF9CustomMap-ow</InstallationPath>" in md  # matches Memoria FolderNames
    # fork-fidelity: ForkDonorPatch.txt maps each custom-id fork -> its donor real field id (so the engine's
    # real-fldMapNo-gated behaviors fire on the fork; read by the s24 DataPatchers patch). 300->30100, 301->30101.
    fdp = [ln for ln in (dist / "ForkDonorPatch.txt").read_text(encoding="utf-8").splitlines()
           if ln.strip() and not ln.startswith("#")]
    assert sorted(fdp) == ["30100 300", "30101 301"]


# ---- read-only resolved graph (campaign_graph + render_graph; pure, no game) ------------
def _graph_plan(entry="A"):
    """A 4-member synthetic campaign: A->B->C (B->C gated), a DANGLING edge A->GHOST, C has two onward
    SEAMS (overworld + portal), and D is wholly disconnected (unreachable + dead-end)."""
    members = [campaign.Member(300, 6000, "A", "borrow", 11, "", "A/A.field.toml", False),
               campaign.Member(301, 6001, "B", "editable", 5, "", "B/B.field.toml", True),
               campaign.Member(302, 6002, "C", "borrow", 11, "", "C/C.field.toml", False),
               campaign.Member(303, 6003, "D", "borrow", 11, "", "D/D.field.toml", False)]
    edges = [{"frm": "A", "to": "B", "entrance": 1, "story_conditional": False},
             {"frm": "B", "to": "C", "entrance": 2, "story_conditional": True},
             {"frm": "A", "to": "GHOST", "entrance": 0, "story_conditional": False}]      # not a member
    seams = [{"frm": "C", "to_real": "WORLDMAP", "kind": "overworld", "note": "1 op", "to_member": None},
             {"frm": "C", "to_real": 999, "kind": "portal", "note": "zone xx", "to_member": None},
             {"frm": "GHOST2", "to_real": 42, "kind": "scripted", "note": "stale", "to_member": None}]
    return campaign.CampaignPlan(name="ICE", mod_folder="M", id_base=6000, flag_base=8300,
                                 flags_per_field=64, entry_name=entry, entry_entrance=0,
                                 members=members, edges=edges, seams=seams)


def test_campaign_graph_resolves_edges_seams_reachability():
    g = campaign.campaign_graph(_graph_plan())
    by = g.by_name
    assert [n.name for n in g.nodes] == ["A", "B", "C", "D"]            # member (id) order preserved
    assert by["A"].is_entry and by["A"].out_edges == [{"to": "B", "entrance": 1, "gated": False}]
    assert by["B"].in_edges == [{"frm": "A", "entrance": 1, "gated": False}]
    assert by["B"].out_edges[0]["gated"] is True                       # story_conditional -> gated
    assert by["C"].out_edges == [] and len(by["C"].seams) == 2
    assert by["C"].dead_end is False                                   # has onward seams -> not a dead end
    assert by["D"].dead_end is True and by["D"].reachable is False
    assert g.unreachable == ["D"] and g.dead_ends == ["D"]
    assert all(n.reachable for n in g.nodes if n.name != "D")
    assert len(g.dangling_edges) == 1 and g.dangling_edges[0]["to"] == "GHOST"
    assert by["A"].out_edges == [{"to": "B", "entrance": 1, "gated": False}]  # dangling edge NOT an out-edge
    assert len(g.dangling_seams) == 1 and g.dangling_seams[0]["frm"] == "GHOST2"  # surfaced, not dropped
    assert len(by["C"].seams) == 2                                     # only the two member-rooted seams


def test_campaign_graph_verbatim_relaxes_reachability(tmp_path):
    # A VERBATIM fork ships the donor .eb whole, so its real (story-scripted / gated) connectivity is intact --
    # the static walk-in BFS can't see it, so a disconnected member must NOT read as unreachable (the whole-zone
    # red-X flood). A declarative campaign still flags it (its gateways ARE the edges).
    plan = _graph_plan()                                                # D is walk-in-disconnected
    assert campaign.campaign_graph(plan).unreachable == ["D"]           # declarative -> D unreachable (real)
    plan.verbatim = True
    g = campaign.campaign_graph(plan)
    assert g.unreachable == [] and all(n.reachable for n in g.nodes)    # verbatim -> no false-positive flood
    assert g.by_name["D"].reachable is True


def test_campaign_graph_entry_fallback():
    g = campaign.campaign_graph(_graph_plan(entry="NOPE"))
    assert g.entry_valid is False and g.entry == "A"                   # falls back to the first member
    assert g.by_name["A"].is_entry


def test_campaign_graph_tolerates_bad_entrance():
    plan = _graph_plan()
    plan.edges.append({"frm": "C", "to": "D", "entrance": "oops"})     # hand-edited / malformed entrance
    g = campaign.campaign_graph(plan)                                  # must NOT raise (tolerant contract)
    assert g.by_name["C"].out_edges[0]["entrance"] == 0                # coerced to 0, not a crash


def test_render_graph_text():
    txt = campaign.render_graph(_graph_plan())
    assert "campaign ICE" in txt and "entry: A (entrance 0)" in txt
    assert "-> B (entrance 1)" in txt and "[gated]" in txt
    assert "~> seam[overworld] -> WORLDMAP" in txt
    assert "UNREACHABLE FROM ENTRY: D" in txt
    assert "DANGLING EDGES" in txt and "A->GHOST" in txt
    assert "DANGLING SEAMS" in txt and "GHOST2->42" in txt             # stale seam surfaced, not dropped
    assert "needs-export" in txt                                       # B is an artless editable member
    assert "entry_field not a member" in campaign.render_graph(_graph_plan(entry="NOPE"))
