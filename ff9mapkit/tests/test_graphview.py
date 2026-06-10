"""Headless tests for the campaign Map's PURE layout core (ff9mapkit.editor.graphview.compute_layout).

No Tk -- compute_layout is a pure function over a campaign.CampaignGraph, so the placement (BFS levels,
unreachable band, border-clipped edges, seam stubs) is unit-testable without a display. The Canvas
widget itself is exercised by the campaign_editor --smoke."""
from ff9mapkit import campaign
from ff9mapkit.editor import graphview


def _plan(edges, *, members=None, seams=None, entry="A"):
    members = ["A", "B", "C"] if members is None else members
    mems = [campaign.Member(300 + i, 30100 + i, nm, "borrow", 11, "", f"{nm}/{nm}.field.toml", False)
            for i, nm in enumerate(members)]
    return campaign.CampaignPlan(name="T", mod_folder="M", id_base=30100,
                                 flag_base=campaign.FIRST_SAFE_FLAG, flags_per_field=64,
                                 entry_name=entry, entry_entrance=0, members=mems,
                                 edges=edges, seams=seams or [])


def test_layout_levels_top_down_from_entry():
    # a chain A->B->C lays out in increasing-y levels, entry at the top
    g = campaign.campaign_graph(_plan([{"frm": "A", "to": "B", "entrance": 0},
                                       {"frm": "B", "to": "C", "entrance": 0}]))
    lay = graphview.compute_layout(g)
    by = lay.by_name
    assert by["A"].y < by["B"].y < by["C"].y
    assert by["A"].is_entry and by["A"].reachable
    assert lay.width > 0 and lay.height > 0


def test_unreachable_member_goes_below_the_reachable_band():
    # C has no inbound live edge -> unreachable -> placed below the deepest reachable level
    g = campaign.campaign_graph(_plan([{"frm": "A", "to": "B", "entrance": 0}]))
    lay = graphview.compute_layout(g)
    by = lay.by_name
    assert not by["C"].reachable
    assert by["C"].y > by["B"].y, "unreachable member sits below the reachable band"


def test_edges_are_clipped_to_node_borders():
    # an edge endpoint lands ON the rectangle border (not the centre), so the arrow touches the box
    g = campaign.campaign_graph(_plan([{"frm": "A", "to": "B", "entrance": 0}]))
    lay = graphview.compute_layout(g)
    a = lay.by_name["A"]
    e = next(e for e in lay.edges if e.frm == "A" and e.to == "B")
    on_border = (abs(e.y1 - (a.y + a.h)) < 1e-6 or abs(e.y1 - a.y) < 1e-6
                 or abs(e.x1 - a.x) < 1e-6 or abs(e.x1 - (a.x + a.w)) < 1e-6)
    assert on_border, (e.x1, e.y1, a)


def test_gated_edge_flag_carries_through():
    g = campaign.campaign_graph(_plan([{"frm": "A", "to": "B", "entrance": 0, "story_conditional": True}]))
    lay = graphview.compute_layout(g)
    assert lay.edges[0].gated is True


def test_seam_becomes_a_stub_with_label():
    g = campaign.campaign_graph(_plan(
        [{"frm": "A", "to": "B", "entrance": 0}],
        seams=[{"frm": "B", "to_real": "WORLDMAP", "kind": "overworld", "note": "", "to_member": None}]))
    lay = graphview.compute_layout(g)
    assert len(lay.seams) == 1
    s = lay.seams[0]
    assert s.frm == "B" and "WORLDMAP" in s.label and s.x > lay.by_name["B"].x


def test_layout_is_deterministic():
    g = campaign.campaign_graph(_plan([{"frm": "A", "to": "B", "entrance": 0},
                                       {"frm": "A", "to": "C", "entrance": 1}]))
    a = graphview.compute_layout(g)
    b = graphview.compute_layout(g)
    assert [(n.name, n.x, n.y) for n in a.nodes] == [(n.name, n.x, n.y) for n in b.nodes]


def test_empty_campaign_yields_a_small_empty_canvas():
    g = campaign.campaign_graph(_plan([], members=[], entry="A"))
    lay = graphview.compute_layout(g)
    assert lay.nodes == [] and lay.edges == [] and lay.width > 0 and lay.height > 0


def test_clip_returns_a_point_on_the_border():
    # straight down from the centre -> lands on the bottom edge at the centre x
    x, y = graphview._clip(100, 100, 50, 25, 100, 999)
    assert abs(x - 100) < 1e-6 and abs(y - 125) < 1e-6
