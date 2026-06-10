"""Offline tests for tools/deploy_campaign.py (P4). The pure helpers (entry/mod-folder resolution, the
dist summary, the revert-script generation) need no game; a guarded dry-run smoke test forks + dry-runs a
tiny campaign when the FF9 install is present. The actual --apply install + in-game warp are verified by a
human (Hard Constraint §2)."""

import ast
import importlib.util
from pathlib import Path

import pytest

from ff9mapkit import campaign

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("deploy_campaign", REPO / "tools" / "deploy_campaign.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _plan():
    members = [
        campaign.Member(300, 30100, "IC_ENT", "editable", 5, "f", "IC_ENT/IC_ENT.field.toml", False),
        campaign.Member(301, 30101, "IC_STP", "borrow", 11, "f", "IC_STP/IC_STP.field.toml", False)]
    return campaign.CampaignPlan(name="ICE", mod_folder="FF9CustomMap-ow", id_base=30100, flag_base=8300,
                                 flags_per_field=64, entry_name="IC_ENT", entry_entrance=0, members=members)


def test_resolve_mod_folder(monkeypatch):
    monkeypatch.delenv("FF9_MOD_FOLDER", raising=False)
    assert dc.resolve_mod_folder("EXPLICIT") == "EXPLICIT"            # CLI flag wins
    monkeypatch.setenv("FF9_MOD_FOLDER", "FROM_ENV")
    assert dc.resolve_mod_folder(None) == "FROM_ENV"                  # env next
    assert dc.resolve_mod_folder("CLI") == "CLI"


def test_resolve_entry():
    p = _plan()
    assert dc.resolve_entry(p, None) == 30100        # manifest entry_field IC_ENT -> its new id
    assert dc.resolve_entry(p, "IC_STP") == 30101    # by member name
    assert dc.resolve_entry(p, "30101") == 30101     # by exact id
    assert dc.resolve_entry(p, "99999") == 99999     # arbitrary id passthrough


def test_expected_dist_summary():
    s = dc.expected_dist_summary(_plan())
    assert any("2 FieldScene lines" in x and "30100..30101" in x for x in s)
    assert any("1 editable member" in x and "IC_ENT" in x for x in s)        # only IC_ENT is editable


def test_render_revert_valid_and_complete(tmp_path):
    live, snap = tmp_path / "FF9CustomMap-ow", tmp_path / "snap"
    warp = tmp_path / "revert_newgame_warp.py"
    txt = dc.render_revert_campaign(live, snap, warp, "ICE", "20260609-000000")
    ast.parse(txt)                                                   # must be valid python
    assert "shutil.copytree(snap, live)" in txt and "runpy.run_path" in txt
    no_warp = dc.render_revert_campaign(live, snap, None, "ICE", "20260609-000000")
    ast.parse(no_warp)
    assert "runpy" not in no_warp                                    # no warp -> no warp-revert step


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_dry_run_smoke(tmp_path):
    from ff9mapkit import chain, eventscan, extract
    bundle = extract.EventBundle()

    def zone_fn(f):
        return chain.zone_label(extract.ID_TO_FBG.get(int(f)))

    def scan_fn(f):
        eb = bundle.eb_for_id(f)
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
    rc = dc.main([str(camp / "campaign.toml")])      # dry-run (no --apply) -> loads, lints, prints, exits
    assert rc == 0
