"""The lost-on-a-mint catalog: engine behaviors keyed on a field's real fldMapNo/fldLocNo, and which a fork on a
custom id keeps (idgated) -- walkmesh hotfix / narrow-map + narrow-camera letterbox / Chocobo HUD / intro FMV /
ATE achievement / per-actor tweak. Pure baked data (no install), so it's unit-testable and safe on the install-free
fork-report path. The remapped/raw claims are checked against the live patch stack (memoria-patches/) below.
"""
from __future__ import annotations

from ff9mapkit import forkreport as FR
from ff9mapkit import idgated as IG
from ff9mapkit._narrowmap_data import RESTRICTED_CAMS

from ._patchstack import WRAPPED, net_added, touches


def _losses(field):
    """The labels fork-report's verdict counts as lost: every entry whose detail does not say ``reproduced``."""
    return [lbl for lbl, det in IG.lost_on_mint(field) if "reproduced" not in det]


def test_narrow_map_width_baked_and_default():
    assert IG.narrow_map_width(2356) == 350          # Gulug/Room (a narrow field, from MapWidthList)
    assert IG.narrow_map_width(101) == 640           # a wide field
    assert IG.narrow_map_width(4003) == IG.FORK_DEFAULT_WIDTH   # an unlisted custom id -> the stock default
    assert IG.narrow_map_width("2356") == 350        # accepts a numeric string
    assert IG.narrow_map_width(None) == IG.FORK_DEFAULT_WIDTH


def test_letterbox_is_kept_on_a_donor_recorded_fork():
    assert IG.is_letterboxed(2356) is True           # 350 < widescreen
    assert IG.is_letterboxed(101) is False           # 640 >= widescreen
    assert IG.is_letterboxed(4003) is False and IG.is_letterboxed(None) is False
    # s23 + s65 give a fork with a ForkDonorPatch row the donor's exact width ...
    assert IG.loses_letterbox(2356) is False
    # ... an --editable or plain BG-borrow import has no row: s23 falls back to the BG camera's width
    assert IG.loses_letterbox(2356, donor_recorded=False) is True
    assert IG.loses_letterbox(101, donor_recorded=False) is False


def test_restricted_cams_only_where_the_camera_is_narrower_than_the_field():
    assert IG.restricted_cams(1205) == ((1, 384),)   # 416-wide field, camera 1 held to 384
    assert IG.restricted_cams(2217) == ((1, 320), (2, 320))
    assert RESTRICTED_CAMS[63] == ((0, 320),) and IG.restricted_cams(63) == ()        # 320 field: a no-op row
    assert IG.restricted_cams(2363) == ((1, 336),)   # its camera 0 row (384) is the field's own width
    assert IG.restricted_cams(101) == () and IG.restricted_cams(None) == ()


def test_lost_on_mint_aggregates():
    labels = lambda f: [lbl for lbl, _ in IG.lost_on_mint(f)]
    # Gulug 2356: a load-time walkmesh hotfix AND a narrow field
    assert labels(2356) == ["walkmesh hotfix", "narrow-map letterbox"]
    # Chocobo's Forest 2950: narrow + the live dig HUD
    assert "Chocobo dig HUD" in labels(2950)
    # field 70: the intro FMV (not in the width table -> not narrow)
    assert labels(70) == ["intro FMV"]
    # a plain wide field loses nothing
    assert IG.lost_on_mint(101) == []
    assert IG.lost_on_mint(99999) == []
    assert IG.lost_on_mint(None) == []


def test_only_the_unreproduced_behaviours_count_as_lost():
    """The verdict steers to fork-in-place only for what the engine and the kit do not reproduce."""
    assert _losses(2356) == [] and _losses(2950) == []    # letterbox (s23/s65), HUD (s24), 2356's hotfix (kit)
    assert _losses(70) == ["intro FMV"]
    assert _losses(1205) == ["narrow-camera letterbox"]  # the map width carries, camera 1's restriction does not
    assert _losses(956) == ["ATE achievement"]           # the one raw MappingATEID compare
    assert _losses(206) == []
    assert _losses(661) == [] and _losses(1413) == ["actor camera priority"]
    v = FR._verdict_line(FR.ForkReport(field_id=2950, lost_on_mint=IG.lost_on_mint(2950)))
    assert "Loses" not in v
    v = FR._verdict_line(FR.ForkReport(field_id=1205, lost_on_mint=IG.lost_on_mint(1205)))
    assert "Loses narrow-camera letterbox" in v and "narrow-map letterbox" not in v


def test_walkmesh_entry_notes_auto_vs_fork_in_place():
    detail = dict(IG.lost_on_mint(2356))["walkmesh hotfix"]
    assert "auto-reproduced" in detail                # 2356 is load-time -> reproduced
    detail2 = dict(IG.lost_on_mint(2803))["walkmesh hotfix"]
    assert "fork-in-place" in detail2                 # 2803 (Daguerreo) is dynamic -> fork in place


# ---- ATE-achievement (fork-report v2): the field->fldLocNo->trophy chain ---------------------------------------
def test_ate_achievement_carries_with_the_text_block():
    # field 206 (the interactive-ATE hub) -> fldLocNo 40, a location WITH an ATE-seen trophy (MappingATEID)
    assert IG.field_loc_no(206) == 40
    assert IG.has_ate_achievement(206) is True
    assert IG.ate_field_gate(206) == (40, "s65")
    assert "reproduced" in dict(IG.lost_on_mint(206))["ATE achievement"]
    # field 707 (Gizamaluke) -> fldLocNo 51, NOT an ATE-achievement location
    assert IG.field_loc_no(707) == 51
    assert IG.has_ate_achievement(707) is False
    assert not any(lbl == "ATE achievement" for lbl, _ in IG.lost_on_mint(707))
    # 204 sits in loc 4's MappingATEID compare but is loc 40 itself: stock never reaches it, fldLocNo alone decides
    assert IG.field_loc_no(204) == 40 and IG.ate_field_gate(204) is None
    assert "fldLocNo alone" in dict(IG.lost_on_mint(204))["ATE achievement"]


def test_ate_achievement_inner_only_locations():
    # loc 8 / 359 / 525 map nothing but one field's compulsory ATE -- their other fields have no trophy at all
    assert IG.has_ate_achievement(306) and not IG.has_ate_achievement(300)
    assert IG.has_ate_achievement(1353) and not IG.has_ate_achievement(1350)
    assert IG.has_ate_achievement(956) and not IG.has_ate_achievement(950)
    det = dict(IG.lost_on_mint(956))["ATE achievement"]
    assert "raw fldMapNo 956" in det and "reproduced" not in det


def test_ate_achievement_locs_are_within_range():
    # baked from EMinigame.MappingATEID (fldLocNo cases) -- a small fixed set, never the fork default
    assert 40 in IG.ATE_ACHIEVEMENT_LOCS and 943 in IG.ATE_ACHIEVEMENT_LOCS
    assert IG.field_loc_no(None) is None and IG.has_ate_achievement(None) is False
    assert {loc for loc, _ in IG.ATE_FIELD_GATES.values()} <= IG.ATE_ACHIEVEMENT_LOCS


# ---- FieldMapActor.cs per-actor tweak (fork-report v3): camera/geo-attach/shadow axis --------------------------
def test_actor_tweak_lost_on_mint():
    # field 1413 (Fossil Roo/Nest) -> a FUNCTIONAL camera-priority tweak (FieldMapActor.cs:135), still raw
    tweaks = IG.actor_tweaks(1413)
    assert tweaks != () and tweaks[0].severity == "FUNCTIONAL"
    assert IG.actor_tweaks(101) == ()
    assert any(lbl == "actor camera priority" for lbl, _ in IG.lost_on_mint(1413))
    assert not any(lbl.startswith("actor ") for lbl, _ in IG.lost_on_mint(101))
    assert "reproduced by the engine fork-donor remap" in dict(IG.lost_on_mint(3002))["actor geo attach"]


# ---- every remapped/raw claim above, read off the LIVE patch stack (memoria-patches/) -----------------------------
#      Each axis names the engine gates its status rests on, in their WRAPPED form. When a patch wraps (or unwraps)
#      one, the catalog must change with it -- the walkmesh axis went stale exactly this way before it had this check.
_NML = "NarrowMapList.cs"
_LETTERBOX_GATES = [
    (_NML, r"Int32 effId = Memoria\.DataPatchers\.EffectiveFieldId\(mapId\)", 2),   # s23: ConditionalForceNarrow +
    (_NML, r"entry\[0\] == effId", 2),                                              #      MapWidth look up the donor
    # s65: OnWidescreenSupportChanged sizes the field to MapWidth(map) -- the one lower-case `int map` alias
    ("FieldMap.cs", r"int map = Memoria\.DataPatchers\.EffectiveFieldId\(FF9StateSystem\.Common\.FF9\.fldMapNo\);", 1),
]
# EventHUD.CheckUIMiniGameForMobile: the file's only fldMapNo alias, which its 2950-2952 branch reads (s24)
_HUD_GATE = ("EventHUD.cs", r"Int32 fldMapNo = Memoria\.DataPatchers\.EffectiveFieldId\(FF9StateSystem\.Common\.FF9\.fldMapNo\)", 1)


def _detail(field, label):
    return dict(IG.lost_on_mint(field))[label]


def test_letterbox_status_follows_the_patch_stack():
    wrapped = all(net_added(f, pat) >= need for f, pat, need in _LETTERBOX_GATES)
    assert wrapped
    assert ("reproduced" in _detail(2356, "narrow-map letterbox")) == wrapped
    assert IG.loses_letterbox(2356) == (not wrapped)


def test_restricted_cams_are_read_on_the_raw_field_id():
    # PSXCameraAspect.LateUpdate is the only reader; no patch touches the file or rewrites the table or a reader
    raw = not touches("PSXCameraAspect.cs") and net_added(None, r"RestrictedCams") == 0
    assert raw
    assert ("reproduced" not in _detail(1205, "narrow-camera letterbox")) == raw


def test_chocobo_hud_status_follows_the_patch_stack():
    f, pat, need = _HUD_GATE
    wrapped = net_added(f, pat) == need
    assert wrapped
    assert all(("reproduced" in _detail(fid, "Chocobo dig HUD")) == wrapped for fid in IG.CHOCOBO_HUD_FIELDS)


def test_intro_fmv_gates_stay_raw():
    # the field-70 gates LoadFieldMap / BG_init / GetCurrentBgCamera / BGI_DEF / FieldMapActor(Controller) /
    # EventEngine's no-save are all written inline (FF9StateSystem...fldMapNo or this._ff9.fldMapNo); none is wrapped.
    # s65's `map` alias does cover two FieldMap camera sites (CenterCameraOnPlayer, SceneService3DScroll), which
    # don't carry the movie.
    raw = net_added(None, r"EffectiveFieldId\([\w.]*fldMapNo\) == 70\b") == 0
    assert raw
    assert ("reproduced" not in _detail(70, "intro FMV")) == raw


def test_ate_field_gates_follow_the_patch_stack():
    # the location keys stay on fldLocNo (nothing remaps them -- they carry with the text block) ...
    assert net_added("EMinigame.cs", r"fldLocNo") == 0
    # ... and each inner fldMapNo compare is wrapped exactly when the catalog names its patch
    for fid, (_loc, patch) in IG.ATE_FIELD_GATES.items():
        assert (net_added("EMinigame.cs", WRAPPED.format("==", fid)) >= 1) == (patch is not None), fid
    # ETb.ProcessATEDialog re-checks 206 for the Prima Vista crash-site choice -- the same s65 wrap
    assert net_added("ETb.cs", r"fldLocNo == 40 && Memoria\.DataPatchers\." + WRAPPED.format("==", 206)) == 1
    for fid in IG.ATE_FIELD_GATES:
        if IG.has_ate_achievement(fid) and IG.ate_field_gate(fid) is not None:
            assert ("reproduced" in _detail(fid, "ATE achievement")) == (IG.ATE_FIELD_GATES[fid][1] is not None), fid
