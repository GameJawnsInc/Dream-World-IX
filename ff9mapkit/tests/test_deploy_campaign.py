"""Offline tests for campaign deploy. The orchestration now lives in the package (``ff9mapkit.deploy``); the
pure helpers (entry resolution, the dist summary, the revert-script generation) are tested there directly,
while the worktree mod-folder resolution + the dry-run ``main`` are tested via the thin repo shim
(``tools/deploy_campaign.py``). A guarded dry-run smoke test forks + dry-runs a tiny campaign when the FF9
install is present. The actual --apply install + in-game warp are verified by a human (Hard Constraint §2)."""

import ast
import importlib.util
import shutil
from pathlib import Path

import pytest

from ff9mapkit import campaign, deploy

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
    assert deploy.resolve_entry(p, None) == 30100        # manifest entry_field IC_ENT -> its new id
    assert deploy.resolve_entry(p, "IC_STP") == 30101    # by member name
    assert deploy.resolve_entry(p, "30101") == 30101     # by exact id
    assert deploy.resolve_entry(p, "99999") == 99999     # arbitrary id passthrough


def test_expected_dist_summary():
    s = deploy.expected_dist_summary(_plan())
    assert any("2 FieldScene lines" in x and "30100..30101" in x for x in s)
    assert any("1 member scene dir" in x and "IC_ENT" in x for x in s)       # IC_ENT ships a scene dir; IC_STP borrows


def test_render_revert_valid_and_complete(tmp_path):
    live, snap = tmp_path / "FF9CustomMap-ow", tmp_path / "snap"
    warp = tmp_path / "revert_newgame_retarget.py"
    txt = deploy.render_revert_campaign(live, snap, warp, "ICE", "20260609-000000")
    ast.parse(txt)                                                   # must be valid python
    assert "shutil.copytree(snap, live)" in txt and "runpy.run_path" in txt
    no_warp = deploy.render_revert_campaign(live, snap, None, "ICE", "20260609-000000")
    ast.parse(no_warp)
    assert "runpy" not in no_warp                                    # no warp -> no warp-revert step


def test_wires_newgame_via_retarget_not_legacy():
    # New Game must be wired by RETARGETING the field-70 override (the proven, install-robust path), NOT the
    # legacy field-100-hop newgame_warp.py whose injection site doesn't exist on every install. The logic now
    # lives in the package: deploy calls newgame.retarget, which writes revert_newgame_retarget.py.
    dsrc = (REPO / "ff9mapkit" / "ff9mapkit" / "deploy.py").read_text(encoding="utf-8")
    nsrc = (REPO / "ff9mapkit" / "ff9mapkit" / "newgame.py").read_text(encoding="utf-8")
    assert "newgame.retarget(" in dsrc                # deploy wires New Game via the field-70 retarget
    assert "revert_newgame_retarget.py" in nsrc       # ...whose revert chains into revert_campaign.py
    # the legacy field-100-hop revert (distinct from the current retarget revert) is gone from both
    assert "revert_newgame_warp.py" not in dsrc and "revert_newgame_warp.py" not in nsrc


def test_folder_order(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    assert deploy.folder_order(g) == []                              # no Memoria.ini -> empty
    (g / "Memoria.ini").write_text('[Mod]\nFolderNames = "X", "Y"\n', encoding="utf-8")
    assert deploy.folder_order(g) == ["X", "Y"]                      # highest first


def test_resolve_highest_folder():
    assert deploy.resolve_highest_folder(["A", "B"], None) == "A"    # highest = first FolderNames entry
    assert deploy.resolve_highest_folder([], None) == "FF9CustomMap"  # unreadable stack -> canonical primary
    assert deploy.resolve_highest_folder(["A", "B"], "OVERRIDE") == "OVERRIDE"   # explicit --promote-csv-to wins


def test_render_revert_with_promoted_csvs(tmp_path):
    live, snap = tmp_path / "FF9CustomMap-ow", tmp_path / "snap"
    csvs = [(r"C:\g\FF9CustomMap\StreamingAssets\Data\Items\InitialItems.csv",
             r"C:\repo\backups\InitialItems.csv.pre-ICE.20260612-000000"),     # had a prior -> restore
            (r"C:\g\FF9CustomMap\StreamingAssets\Data\Items\ShopItems.csv", None)]  # newly created -> delete
    txt = deploy.render_revert_campaign(live, snap, None, "ICE", "20260612-000000", csvs)
    ast.parse(txt)                                                   # valid python
    assert "CSV_REVERTS" in txt
    assert "shutil.copyfile(_bkp, _dst)" in txt and "_dst.unlink()" in txt
    assert "Path(_bkp).is_file()" in txt                             # don't crash if a backup CSV vanished
    assert "if snap.is_dir():" in txt                                # never rmtree live without a snapshot
    no_csv = deploy.render_revert_campaign(live, snap, None, "ICE", "20260612-000000")
    ast.parse(no_csv)
    assert "CSV_REVERTS" not in no_csv                               # no promotion -> no CSV block


def test_generated_revert_executes(tmp_path):
    # build a realistic post-deploy state and prove the generated revert restores/deletes/skips correctly
    live, snap = tmp_path / "FF9CustomMap-ow", tmp_path / "snap"
    snap.mkdir()
    (snap / "marker.txt").write_text("snapshot", encoding="utf-8")
    live.mkdir()
    (live / "stale.txt").write_text("stale", encoding="utf-8")       # should be wiped by the snapshot restore
    high = tmp_path / "FF9CustomMap" / "Data"
    high.mkdir(parents=True)
    bkdir = tmp_path / "backups"
    bkdir.mkdir()
    dst1 = high / "InitialItems.csv"; dst1.write_text("NEW", encoding="utf-8")       # 1) prior backed up -> restore
    bk1 = bkdir / "InitialItems.csv.bk"; bk1.write_text("OLD", encoding="utf-8")
    dst2 = high / "ShopItems.csv"; dst2.write_text("CREATED", encoding="utf-8")      # 2) newly created -> remove
    dst3 = high / "DefaultEquipment.csv"; dst3.write_text("KEEP", encoding="utf-8")  # 3) backup vanished -> skip
    bk3 = bkdir / "gone.bk"                                                          #    (never created)
    txt = deploy.render_revert_campaign(live, snap, None, "ICE", "x",
                                        [(str(dst1), str(bk1)), (str(dst2), None), (str(dst3), str(bk3))])
    exec(compile(txt, "<revert>", "exec"), {})
    assert dst1.read_text(encoding="utf-8") == "OLD"                 # restored from backup
    assert not dst2.exists()                                         # newly created -> removed
    assert dst3.read_text(encoding="utf-8") == "KEEP"               # backup missing -> left as-is (no crash)
    assert (live / "marker.txt").exists() and not (live / "stale.txt").exists()   # folder restored from snapshot


def test_generated_revert_skips_when_snapshot_missing(tmp_path):
    live, snap = tmp_path / "live", tmp_path / "nope"               # snapshot does NOT exist
    live.mkdir()
    (live / "keep.txt").write_text("keep", encoding="utf-8")
    txt = deploy.render_revert_campaign(live, snap, None, "ICE", "x")
    exec(compile(txt, "<revert>", "exec"), {})
    assert (live / "keep.txt").exists()                             # snapshot missing -> live left untouched, not nuked


def _minimal_campaign(tmp_path, mod_folder):
    """A prebuilt dist + its sibling manifest (is_dist_dir needs both markers AND the manifest)."""
    camp_dir = tmp_path / "camp"
    dist = camp_dir / "dist"
    dist.mkdir(parents=True)
    (dist / "DictionaryPatch.txt").write_text("FieldScene 4000 11 10 TEST 1073\n", encoding="utf-8")
    (dist / "ModDescription.xml").write_text("<Mod/>", encoding="utf-8")
    (dist / "EVT_B.eb.bytes").write_bytes(b"UNPATCHED")          # what a dist carries, by construction
    fd = camp_dir / "F1"
    fd.mkdir()
    (fd / "F1.field.toml").write_text('[field]\nid = 4000\nname = "F1"\narea = 11\n', encoding="utf-8")
    (camp_dir / "campaign.toml").write_text(
        f'[campaign]\nname = "T"\nmod_folder = "{mod_folder}"\nid_base = 4000\nflag_base = 8712\n'
        'flags_per_field = 64\nentry_field = "F1"\nentry_entrance = 0\n\n'
        '[[field]]\nname = "F1"\nsource = 100\nid = 4000\nmode = "borrow"\ntoml = "F1/F1.field.toml"\n',
        encoding="utf-8")
    return dist


@pytest.mark.parametrize("allow, expect_wiped", [(False, False), (True, True)])
def test_a_wholesale_replace_refuses_to_revert_journey_links(tmp_path, allow, expect_wiped):
    """★ THE FAST LOOP ATE THE SLOW LOOP'S OUTPUT. A journey's cross-campaign doors are an edit to the
    INSTALLED .eb -- no dist can carry them, because the destination is another campaign's id. So a
    single-campaign redeploy (rmtree + copytree of the unpatched dist) reverted them silently. JOURNEYS.md
    warned in prose; prose is not a mechanism."""
    from ff9mapkit import linkreceipt as lr
    from ff9mapkit import stamp
    game = tmp_path / "game"
    mod_folder = "FF9CustomMap-links"
    live_root = game / mod_folder
    live_root.mkdir(parents=True)
    patched = live_root / "EVT_B.eb.bytes"
    patched.write_bytes(b"PATCHED")                              # the journey's door, applied in place
    stamp.write(live_root, stamp.finalize(
        {"stamp_version": 1, "kit_version": "x", "built_utc": "t", "mod_name": mod_folder,
         "context": "journey", "source": None, "members": []}, live_root))
    lr.write_receipt(live_root, lr.build_receipt(live_root, [{
        "eb": "EVT_B", "mode": "field_remap", "dst_id": 6501, "remap": {300: 6501},
        "files": [str(patched)], "found": True}]))

    dist = _minimal_campaign(tmp_path, mod_folder)
    rep = deploy.deploy_campaign(dist, game=game, mod_folder=mod_folder, apply=True,
                                 allow_link_wipe=allow, backups_dir=tmp_path / "b",
                                 reverts_dir=tmp_path / "r", verbose=False)
    if expect_wiped:
        assert rep["applied"] is True
        assert patched.read_bytes() == b"UNPATCHED", "--allow-link-wipe must still install"
    else:
        assert rep["applied"] is False, "the default must REFUSE rather than silently revert the doors"
        assert patched.read_bytes() == b"PATCHED", "nothing may be installed on a refusal"
        assert lr.check(live_root).satisfied, "the links must still be intact after the refusal"


def test_wholesale_replace_failure_restores_snapshot(tmp_path, monkeypatch):
    # a mid-copytree failure installing the dist over live_root must NOT leave a half-installed folder with
    # no revert -- it must restore live_root from the pre-install snapshot and still leave a valid revert script.
    game = tmp_path / "game"
    game.mkdir()
    mod_folder = "FF9CustomMap-test"
    live_root = game / mod_folder
    live_root.mkdir()
    (live_root / "sentinel.txt").write_text("PRIOR", encoding="utf-8")     # pre-existing live content

    # a minimal prebuilt dist (skips build_campaign -- is_dist_dir only needs these two markers)
    camp_dir = tmp_path / "camp"
    dist = camp_dir / "dist"
    dist.mkdir(parents=True)
    (dist / "DictionaryPatch.txt").write_text("FieldScene 4000 11 10 TEST 1073\n", encoding="utf-8")
    (dist / "ModDescription.xml").write_text("<Mod/>", encoding="utf-8")
    field_dir = camp_dir / "F1"
    field_dir.mkdir()
    # A MINIMAL but HONEST member: its [field] id has to AGREE with the manifest's, or lint's
    # manifest/artifact reconciliation refuses the deploy long before the copytree this test is about.
    # (This was an empty file, commented "lint stays silent" -- true, and exactly the blind spot: an
    # empty member cannot register field 4000, so the silence was the bug, not a convenience.)
    (field_dir / "F1.field.toml").write_text('[field]\nid = 4000\nname = "F1"\narea = 11\n',
                                             encoding="utf-8")
    (camp_dir / "campaign.toml").write_text(
        '[campaign]\n'
        'name = "T"\n'
        f'mod_folder = "{mod_folder}"\n'
        'id_base = 4000\n'
        'flag_base = 8712\n'
        'flags_per_field = 64\n'
        'entry_field = "F1"\n'
        'entry_entrance = 0\n\n'
        '[[field]]\n'
        'name = "F1"\n'
        'source = 100\n'
        'id = 4000\n'
        'mode = "borrow"\n'
        'toml = "F1/F1.field.toml"\n', encoding="utf-8")

    real_copytree = shutil.copytree

    def _boom(src, dst, *a, **k):
        if Path(src) == dist:                    # only the risky dist->live_root copy fails
            raise OSError("simulated disk-full mid-copy")
        return real_copytree(src, dst, *a, **k)
    monkeypatch.setattr(deploy.shutil, "copytree", _boom)

    report = deploy.deploy_campaign(dist, game=game, mod_folder=mod_folder, apply=True,
                                    backups_dir=tmp_path / "backups", reverts_dir=tmp_path / "reverts",
                                    verbose=False)

    assert report["applied"] is False                                     # the install never completed
    assert (live_root / "sentinel.txt").is_file()                         # restored from the snapshot...
    assert (live_root / "sentinel.txt").read_text(encoding="utf-8") == "PRIOR"   # ...with the ORIGINAL bytes
    rev = report["revert"]
    assert rev is not None and Path(rev).is_file()                        # a revert script still exists
    ast.parse(Path(rev).read_text(encoding="utf-8"))                      # ...and is valid python


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


def test_regs_wiped_reports_another_sessions_fieldscene(tmp_path):
    """A wholesale campaign install rmtree+copytree's the mod folder, so any registration the built dist does
    not carry is gone. Multiple checkouts deploy into ONE shared folder, so that routinely includes a FIELD
    line belonging to another session -- and an unregistered field id makes the engine load a null .eb, a
    black screen with no error (2026-07-18). Pre-fix this guard inspected only 3DModel/3DModelAnimation."""
    class _Live:                                    # only .dictionary_patch is read; an explicit fixture, no
        dictionary_patch = tmp_path / "DictionaryPatch.txt"    # fall-through to the developer's real install
    dist = tmp_path / "dist"
    dist.mkdir()
    _Live.dictionary_patch.write_text(
        "FieldScene 30100 11 10 IC_ENT 1200\n"       # the campaign's own -- carried by the dist
        "FieldScene 4003 11 10 TESTROOM 1073\n"      # ANOTHER session's field, co-resident in the folder
        "LocationName 4003 Test Room\n"
        "3DModelAnimation 60001 ANH_A\n", encoding="utf-8")
    (dist / "DictionaryPatch.txt").write_text("FieldScene 30100 11 10 IC_ENT 1200\n", encoding="utf-8")
    assert deploy._regs_wiped(_Live, dist) == [
        "FieldScene 4003 11 10 TESTROOM 1073", "LocationName 4003 Test Room", "3DModelAnimation 60001 ANH_A"]


def test_regs_wiped_quiet_when_campaign_rewrites_its_own_field_line(tmp_path):
    """Anti-noise: re-deploying the campaign with an edited field (new scene name / text-block id) must not
    warn -- FieldScene is judged on (directive, id), and id 30100 is still registered."""
    class _Live:
        dictionary_patch = tmp_path / "DictionaryPatch.txt"
    dist = tmp_path / "dist"
    dist.mkdir()
    _Live.dictionary_patch.write_text("FieldScene 30100 11 10 OLDNAME 1200\n", encoding="utf-8")
    (dist / "DictionaryPatch.txt").write_text("FieldScene 30100 11 10 NEWNAME 1288\n", encoding="utf-8")
    assert deploy._regs_wiped(_Live, dist) == []


def test_regs_wiped_reports_a_member_the_campaign_itself_retired(tmp_path):
    """A campaign's own RETIRED member is dropped by the wholesale replace exactly like a foreign line, and
    the guard cannot tell them apart -- that indistinguishability IS incident 2 (a retired registration and a
    lost one are byte-identical: a line that is not there). The earlier docstring claimed the campaign owns
    every id in the dist BY CONSTRUCTION so anything left is foreign by definition; that holds for the ids the
    dist STILL carries, not the ones it USED to. This pins the fact being reported."""
    class _Live:                                    # only .dictionary_patch is read; an explicit fixture, no
        dictionary_patch = tmp_path / "DictionaryPatch.txt"    # fall-through to the developer's real install
    dist = tmp_path / "dist"
    dist.mkdir()
    _Live.dictionary_patch.write_text(
        "FieldScene 30100 11 10 IC_ENT 1200\n"       # still a member
        "FieldScene 30102 11 10 IC_DROPPED 1202\n"   # a member the author removed from campaign.toml
        "LocationName 30100 Ice Cavern\n",           # this build stopped emitting [field] location
        encoding="utf-8")
    (dist / "DictionaryPatch.txt").write_text("FieldScene 30100 11 10 IC_ENT 1200\n", encoding="utf-8")
    assert deploy._regs_wiped(_Live, dist) == ["FieldScene 30102 11 10 IC_DROPPED 1202",
                                               "LocationName 30100 Ice Cavern"]


def test_wiped_regs_warning_does_not_assert_another_session_owns_the_line():
    """THE CRY-WOLF REGRESSION. The predecessor text stated flatly that a dropped `FieldScene` "belongs to
    ANOTHER session's field co-resident in this folder" and said to "re-deploy the owning field" -- printed at
    the author who had just removed that member, prescribing the undoing of their own edit, on the routine
    authoring loop. The guard has no ownership record, so the warning must give both readings and the action
    for each, never pick one."""
    w = deploy._wiped_regs_warning(["FieldScene 30102 11 10 IC_DROPPED 1202"])
    assert "belongs to ANOTHER session" not in w
    assert "re-deploy the owning field" not in w
    assert "a member you removed from this campaign" in w      # reading (a): yours, retired -- nothing to do
    assert "ANOTHER checkout's" in w                            # reading (b): a co-resident session's
    assert "BLACK-SCREENS" in w                                 # ...and (b) still names the real consequence
    assert "FieldScene 30102 11 10 IC_DROPPED 1202" in w        # the line itself, verbatim
