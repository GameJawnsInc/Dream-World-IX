"""Offline unit tests for the import-chain graph walk (ff9mapkit.chain).

The walk is pure: it takes scan_fn/zone_fn callbacks, so these run with no game install. The
real-bytes integration check (reproducing the Ice Cavern graph) is a manual CLI run, not here,
because committing real .eb fixtures would violate the provenance gate."""

from ff9mapkit import chain


# ---- a tiny synthetic world -------------------------------------------------------------
# zones: 'a' = {1,2,3,4}, 'b' = {10,11}. Edges are bidirectional walk-in unless noted.
GRAPH = {
    1: {"zone": "a", "walk_in": [2], "scripted": [], "wm": []},
    2: {"zone": "a", "walk_in": [1, 3], "scripted": [99], "wm": []},          # 99 = scripted teleport out
    3: {"zone": "a", "walk_in": [2, 4], "scripted": [], "wm": []},
    4: {"zone": "a", "walk_in": [3, 10], "scripted": [], "wm": [9001]},        # 4->10 crosses into zone b
    10: {"zone": "b", "walk_in": [4, 11], "scripted": [], "wm": []},
    11: {"zone": "b", "walk_in": [10], "scripted": [], "wm": [9002]},
    99: {"zone": "x", "walk_in": [], "scripted": [], "wm": []},
}


def _zone_fn(fid):
    return GRAPH.get(fid, {}).get("zone", "?")


def _scan_fn(fid):
    node = GRAPH.get(fid)
    if node is None:
        return {"found": False}
    edges = [{"to": t, "kind": chain.WALK_IN, "entrance": 0, "zone": [[0, 0]],
              "story_conditional": False} for t in node["walk_in"]]
    edges += [{"to": t, "kind": chain.SCRIPTED, "entrance": 7, "trigger": "cutscene-loop"}
              for t in node["scripted"]]
    return {"found": True, "edges": edges, "overworld_exits": node["wm"],
            "encounter": None, "music": None}


def _ids(result):
    return set(result.nodes)


def test_zone_label():
    assert chain.zone_label("fbg_n05_iccv_map085_ic_ent_0") == "iccv"
    assert chain.zone_label("fbg_n06_vgdl_map097_dl_viw_0") == "vgdl"
    assert chain.zone_label(None) == "?"
    assert chain.zone_label("weird") == "weird"


def test_walk_stays_in_seed_zone_by_default():
    # default stop_at_zone_boundary: seed zone 'a' only; the 4->10 edge into 'b' becomes a portal.
    r = chain.walk(1, _scan_fn, _zone_fn)
    assert _ids(r) == {1, 2, 3, 4}
    assert any(p["from"] == 4 and p["to"] == 10 and p["reason"].startswith("zone:") for p in r.portals)
    assert not r.truncated


def test_walk_spans_listed_zones():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"])
    assert _ids(r) == {1, 2, 3, 4, 10, 11}
    # no zone-boundary portal now that both zones are in scope
    assert not any(p["reason"].startswith("zone:") for p in r.portals)


def test_walk_bidirectional_no_infinite_loop():
    # 1<->2<->3 ... all bidirectional; visited-set must terminate.
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"])
    assert _ids(r) == {1, 2, 3, 4, 10, 11}


def test_max_hops_bounds_depth():
    # from 1: hop0=1, hop1=2, hop2={1,3}, hop3=4. max_hops=2 stops before 4.
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"], max_hops=2)
    assert 4 not in _ids(r)
    assert any(p["to"] == 4 and p["reason"] == "max-hops" for p in r.portals)


def test_max_fields_truncates_loudly():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"], max_fields=3)
    assert r.truncated
    assert len(r.nodes) == 3
    assert r.remaining >= 1


def test_scripted_warp_is_a_seam_not_followed():
    r = chain.walk(1, _scan_fn, _zone_fn)
    assert 99 not in _ids(r)                     # scripted target not walked by default
    assert any(s["from"] == 2 and s["to"] == 99 and s["trigger"] == "cutscene-loop" for s in r.seams)


def test_follow_scripted_includes_teleport_targets():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "x"], follow_scripted=True)
    assert 99 in _ids(r)


def test_denylist_blocks_a_field():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"], denylist={10})
    assert 10 not in _ids(r)
    assert 11 not in _ids(r)                     # 11 was only reachable via 10
    assert any(p["to"] == 10 and p["reason"] == "denylist" for p in r.portals)


def test_stop_at_cuts_the_walk():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"], stop_at={4})
    assert 4 not in _ids(r)
    assert 10 not in _ids(r)


def test_overworld_exits_recorded_not_followed():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"])
    assert r.nodes[4]["overworld_exits"] == [9001]
    # 9001 must never be treated as a field id / graph node
    assert 9001 not in _ids(r)


def test_unforkable_target_classified_before_zone():
    # mark field 4 as non-forkable (a shop/menu / no-background id): it must be classified as
    # unforkable (NOT followed, NOT a zone portal), and anything reachable only through it drops out.
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"], forkable_fn=lambda fid: fid != 4)
    assert 4 not in _ids(r)
    assert 10 not in _ids(r) and 11 not in _ids(r)        # only reachable via 4
    assert any(u["to"] == 4 for u in r.unforkable)
    assert not any(p["to"] == 4 for p in r.portals)       # classified as menu/no-bg, not a portal


def test_forkable_default_is_all_forkable():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"])
    assert r.unforkable == []                             # default: everything forkable, behavior unchanged


def test_render_smoke():
    r = chain.walk(1, _scan_fn, _zone_fn, zones=["a", "b"], forkable_fn=lambda fid: fid != 4)
    text = chain.render(r, label_fn=lambda i: f"F{i}")
    assert "ZONE a" in text
    assert "BLAST RADIUS" in text
    assert "MENU / NON-FIELD TARGETS" in text and "F4" in text


# ---- zone coverage (the 'isolated seed' hint) -------------------------------------------
def test_zone_coverage_flags_unreached_fields():
    # seed 1 forks zone 'a' = {1,2,3,4}; pretend the zone ALSO has a field 5 the seed can't door-reach.
    r = chain.walk(1, _scan_fn, _zone_fn)
    members = {"a": {1, 2, 3, 4, 5}, "b": {10, 11}}
    cov = chain.zone_coverage(r, lambda z: members.get(z, set()))
    assert cov["a"] == (4, 5, [5])                      # reached 4 of 5; field 5 unreached
    lines = chain.render_coverage(cov)
    assert any("zone a" in ln and "4 of 5" in ln and "--whole-zone" in ln for ln in lines)


def test_zone_coverage_full_is_silent():
    # a fully-covered zone (e.g. a --whole-zone fork) yields no hint.
    r = chain.walk(1, _scan_fn, _zone_fn)
    cov = chain.zone_coverage(r, lambda z: {1, 2, 3, 4} if z == "a" else set())
    assert cov["a"][0] == cov["a"][1] == 4
    assert chain.render_coverage(cov) == []


def test_whole_zone_multi_seed_forks_disconnected_field():
    # the --whole-zone mechanism = seed EVERY zone field. Field 5 is its own island (no edges); seeding it
    # directly forks it where a walk from 1 never would.
    GRAPH[5] = {"zone": "a", "walk_in": [], "scripted": [], "wm": []}
    try:
        r = chain.walk([1, 5], _scan_fn, _zone_fn)     # seed 1 AND the island 5
        assert {1, 2, 3, 4, 5} <= _ids(r)
        cov = chain.zone_coverage(r, lambda z: {1, 2, 3, 4, 5} if z == "a" else set())
        assert chain.render_coverage(cov) == []        # now fully covered
    finally:
        del GRAPH[5]


# ---- CLI seed resolution: comma-separated multi-seed (one campaign over several zones) ----
def test_resolve_chain_seeds_multi():
    """_resolve_chain_seeds splits comma-separated tokens (id or FBG substring), keeps token order
    (first stays the campaign entry), and de-duplicates -- so `import-chain 50,100 --whole-zone`
    forks several zones as ONE campaign. Uses the baked field table (no game install)."""
    from ff9mapkit.cli import _resolve_chain_seeds
    from ff9mapkit import extract, chain
    assert _resolve_chain_seeds("50") == [50]                      # single id unchanged
    assert _resolve_chain_seeds("50,100") == [50, 100]             # multi ids, order kept
    ta = _resolve_chain_seeds("tshp,alxt")                         # two zones by FBG substring
    zones = {chain.zone_label(extract.ID_TO_FBG[f]) for f in ta}
    assert zones == {"tshp", "alxt"} and len(ta) == len(set(ta))   # both zones, de-duped
    assert chain.zone_label(extract.ID_TO_FBG[ta[0]]) == "tshp"    # first token's zone leads
    assert _resolve_chain_seeds("50, tshp")[0] == 50               # whitespace ok, entry preserved
    import pytest
    with pytest.raises(FileNotFoundError):
        _resolve_chain_seeds("nosuchzone_xyz")
