"""fork-report -- preview what a fork of a real field will/won't reproduce (docs/FORK_FIDELITY.md).

The pure analysis (analyze_eb / scenario_gates / format_report / resolve_field_id) is tested OFFLINE against
the shipped ALEX100 .eb fixture + synthetic bytes. The full id->report path + the director/rotating-cast
signals (which need the install's p0data) are gated behind the install, mirroring test_eventscan.
"""
from __future__ import annotations

import struct
from pathlib import Path

import pytest

from ff9mapkit import forkreport as FR

FIX = Path(__file__).parent / "fixtures"
ALEX100 = (FIX / "alex100-us.eb.bytes").read_bytes()


def _game_ready():
    try:
        from ff9mapkit.extract import EventBundle
        EventBundle()
        return True
    except Exception:
        return False


# ---- scenario gate extraction (pure) ----
def test_scenario_gates_finds_comparison_not_write():
    gate = b"\xDC\x00\x7D" + struct.pack("<H", 2500) + b"\x1B"   # SC >= 2500  (0x1B = >=, a comparison)
    write = b"\xDC\x00\x7D" + struct.pack("<H", 9999) + b"\x2C"  # SC = 9999   (0x2C = assign, NOT a gate)
    blob = b"\x00\x01\x02" + gate + b"\x10\x11" + write + b"\xff"
    assert FR.scenario_gates(blob) == [2500]                     # the comparison value; the write is excluded


def test_scenario_gates_empty_when_none():
    assert FR.scenario_gates(b"\x00\x01\x02\x03no gates here") == []


# ---- analyze_eb on the real ALEX100 fixture (offline) ----
def test_analyze_eb_alex100_is_static_roster():
    rep = FR.analyze_eb(ALEX100, field_id=100, fbg_name="fbg_n01_alxt_map016_at_msa_0")
    assert rep.has_script
    assert rep.n_objects == rep.n_props + rep.n_talkable
    assert rep.roster_class == "static-roster"        # no Field()-warp directors, few/no SC gates
    assert rep.directors == []
    assert sum(rep.safety.values()) == rep.n_objects  # every carried object is classified


def test_analyze_eb_alex100_reports_vivi_as_a_non_zidane_player():
    # ALEX100 (Alexandria street, field 100) is played as VIVI -- the player axis reports who you control,
    # that it's a single-PC non-Zidane field, and switches the suggested recipe to --verbatim (the graft
    # path would drop Vivi's wrong-rig clips). Proven faithful in-game (memory project-ff9-non-zidane-donors).
    rep = FR.analyze_eb(ALEX100, field_id=100, fbg_name="fbg_n01_alxt_map016_at_msa_0")
    assert rep.player_models and rep.player_models[0][1] == 8      # GEO_MAIN_F0_VIV
    assert rep.player_models[0][2] == "Vivi"
    assert rep.non_zidane and not rep.multi_pc
    out = FR.format_report(rep)
    assert "Player        : Vivi" in out and "non-Zidane" in out
    # the SUGGESTED-AUTHORING command line uses --verbatim, NOT the graft recipe (which drops Vivi's funcs)
    cmd = next(l for l in out.splitlines() if "ff9mapkit import" in l)
    assert "--verbatim" in cmd and "--graft-player-funcs" not in cmd


def test_player_name_falls_back_to_geo_model_name():
    assert FR.player_name(8) == "Vivi" and FR.player_name(98) == "Zidane"
    assert FR.player_name(None) == "none"
    assert FR.player_name(192) == "Freya"


def test_controlled_player_single_pc_is_the_one_entry():
    # ALEX100 is single-PC (Vivi, entry 19); controlled_player returns it with high confidence.
    from ff9mapkit.eb import EbScript
    eb = EbScript.from_bytes(ALEX100)
    entry, conf = FR.controlled_player(eb)
    assert entry == 19 and conf == "high"


def test_player_line_swap_friendliness_tag():
    # the Player axis previews whether a field is a good --swap-player target: a CUTSCENE field's player
    # gestures glitch on a swapped rig (ALEX100 = 15), a free-roam field is swap-clean.
    rep = FR.analyze_eb(ALEX100, field_id=100, fbg_name="fbg_n01_alxt_map016_at_msa_0")
    assert rep.swap_gesture_count > 0                         # the Vivi opening has scripted player gestures
    line = next(l for l in FR.format_report(rep).splitlines() if l.strip().startswith("Player"))
    assert "gesture(s) glitch" in line
    # a free-roam field (no scripted player gestures) -> swap-clean
    clean = FR.ForkReport(field_id=10, fbg_name="x")
    clean.player_models = [(1, 98, "Zidane")]
    clean.swap_gesture_count = 0
    cl = next(l for l in FR.format_report(clean).splitlines() if l.strip().startswith("Player"))
    assert "swap-clean" in cl


# ---- the Camera axis: the lens the fork plays through (close/medium/wide) ----
def test_camera_line_buckets_by_fov():
    # FOV buckets the "zoom feel": a narrow FOV = an intimate close room, a wide FOV = an establishing shot.
    close = FR.ForkReport(field_id=1, cam_pitch=38.0, cam_fov=29.5)
    assert FR._camera_line(close).strip() == "Camera        : close (FOV 29.5 deg, pitch 38 deg)".strip()
    med = FR.ForkReport(field_id=2, cam_pitch=30.0, cam_fov=45.0)
    assert "medium" in FR._camera_line(med) and "FOV 45 deg" in FR._camera_line(med)
    wide = FR.ForkReport(field_id=3, cam_pitch=42.0, cam_fov=61.3)
    assert "wide" in FR._camera_line(wide)


def test_camera_line_notes_scrolling_and_multicam():
    rep = FR.ForkReport(field_id=4, cam_pitch=40.0, cam_fov=55.0, cam_scrolling=True, cam_count=3)
    line = FR._camera_line(rep)
    assert "scrolling" in line and "3 cameras" in line


def test_camera_line_omitted_when_not_read():
    # the pure .eb-only path (analyze_eb) never sets cam_pitch -> no Camera line (report stays .eb-faithful)
    rep = FR.analyze_eb(ALEX100, field_id=100, fbg_name="fbg_n01_alxt_map016_at_msa_0")
    assert rep.cam_pitch is None
    assert FR._camera_line(rep) == ""
    assert not any(l.strip().startswith("Camera") for l in FR.format_report(rep).splitlines())


# ---- the Party axis: what a verbatim fork does to your party ----
def test_scan_party_ops_on_alex100_adds_vivi_and_resets():
    # ALEX100 (field 100) is the disc-1 opening: it strips the party and adds Vivi (CharacterOldIndex 1).
    ops = FR.scan_party_ops(ALEX100)
    assert 1 in ops["adds"]                            # adds Vivi
    assert FR.PARTY_NONE not in ops["adds"]            # the NONE sentinel is filtered out
    assert ops["reset"]                                # SetPartyReserve -> rebuilds the recruitable roster


def test_party_char_name_maps_old_index():
    assert FR.party_char_name(1) == "Vivi" and FR.party_char_name(3) == "Steiner"
    assert FR.party_char_name(99) == "#99"             # unknown -> a raw marker, never crashes


def test_analyze_eb_alex100_reports_a_party_line():
    rep = FR.analyze_eb(ALEX100, field_id=100, fbg_name="fbg_n01_alxt_map016_at_msa_0")
    assert "Vivi" in rep.party_adds
    out = FR.format_report(rep)
    line = next(l for l in out.splitlines() if l.strip().startswith("Party"))
    assert "adds" in line and "Vivi" in line


def test_party_line_omitted_when_party_neutral():
    rep = FR.ForkReport(field_id=10, fbg_name="x", roster_class="static-roster")  # no party ops set
    assert FR._party_line(rep) == ""
    assert not any(l.strip().startswith("Party") for l in FR.format_report(rep).splitlines())


def test_analyze_eb_no_script():
    rep = FR.analyze_eb(b"", field_id=1)
    assert not rep.has_script
    assert "nothing to fork" in rep.notes[0]
    # renders without crashing
    assert "field 1" in FR.format_report(rep)


def test_analyze_eb_invalid_magic_is_graceful():
    """Garbage bytes (bad .eb magic) report has_script=False rather than crashing the preview."""
    rep = FR.analyze_eb(b"NOTANEB\x00\x01\x02\x03", field_id=7)
    assert not rep.has_script
    assert "parseable" in rep.notes[0]
    assert "field 7" in FR.format_report(rep)


def test_format_report_edge_cases_render_ascii():
    # props-only (no talkable NPCs)
    pr = FR.ForkReport(field_id=10, fbg_name="x", roster_class="static-roster")
    pr.n_objects = pr.n_props = 3
    pr.safety = {"clean": 3}
    out = FR.format_report(pr)
    out.encode("ascii")
    assert "no talkable NPCs" in out
    # all-refuse + a gated door, no SC gates
    rf = FR.ForkReport(field_id=11, fbg_name="y", roster_class="story-event")
    rf.n_objects = rf.n_talkable = 2
    rf.safety = {"refuse": 2}
    rf.gated_doors = 1
    rf.directors = [3]
    out2 = FR.format_report(rf)
    out2.encode("ascii")
    assert "2 stub" in out2 and "1 gated door" in out2 and "no ScenarioCounter gates" in out2


# ---- #5 preview: the speaking-NPC (text-carry) axis ----
def test_analyze_eb_reports_speaking_npcs_subset_of_talkable():
    # the TEXT axis: carried NPCs whose tag-3 talk SHOWS dialogue (-> need --carry-text). It's a subset of
    # the talkable NPCs, and each speaking NPC shows >= 1 distinct line. (Fixture-independent invariants.)
    rep = FR.analyze_eb(ALEX100, field_id=100, fbg_name="fbg_n01_alxt_map016_at_msa_0")
    assert 0 <= rep.n_speaking <= rep.n_talkable
    assert rep.n_dialogue_lines >= rep.n_speaking
    out = FR.format_report(rep)
    if rep.n_speaking:
        line = next(l for l in out.splitlines() if l.strip().startswith("Dialogue"))
        assert "carry-text" in line and "#5" in line


def test_format_report_dialogue_line_present_and_absent():
    rep = FR.ForkReport(field_id=12, fbg_name="z", roster_class="static-roster")
    rep.n_objects = rep.n_talkable = rep.n_speaking = 2
    rep.n_dialogue_lines = 5
    rep.safety = {"clean": 2}
    out = FR.format_report(rep)
    out.encode("ascii")                                       # ASCII-safe for cp1252 consoles
    assert "2 NPC(s) speak 5 line(s)" in out and "carry-text" in out and "#5" in out
    # no speaking NPCs -> no Dialogue line at all
    rep.n_speaking = rep.n_dialogue_lines = 0
    assert not any(l.strip().startswith("Dialogue") for l in FR.format_report(rep).splitlines())


# ---- format_report (pure render; must be ASCII-safe for cp1252 consoles) ----
def _sample_report():
    rep = FR.ForkReport(field_id=354, fbg_name="fbg_n06_vgdl_map103_dl_shp_0", event_name="EVT_DALI")
    rep.n_objects, rep.n_talkable, rep.n_props = 5, 4, 1
    rep.directors = [4]
    rep.stacked = [4]
    rep.safety = {"clean": 3, "init_only": 1, "refuse": 1}
    rep.sc_gates = [(2600, (2600, "Dali")), (11090, (10930, "Pandemonium"))]
    rep.suggested_scenario = 2600
    rep.roster_class = "story-event"
    rep.notes = ["content gates on 11 story beats -- this field ROTATES its cast/content"]
    return rep


def test_format_report_ascii_and_content():
    out = FR.format_report(_sample_report())
    out.encode("ascii")                                # ASCII-only (no em-dash / arrows that break cp1252)
    assert "STORY-EVENT" in out
    assert "director" in out
    assert "scenario = 2600" in out and "Dali" in out  # the suggested home beat (earliest gate)
    assert "--graft-player-funcs --carry-text" in out  # the faithful-fork recipe is suggested


def test_format_report_static_roster_verdict():
    rep = FR.ForkReport(field_id=557, fbg_name="lb_tmp", roster_class="static-roster")
    rep.n_objects = rep.n_talkable = 6
    rep.safety = {"clean": 6}
    out = FR.format_report(rep)
    assert "CLEAN static-roster" in out
    assert "6 of 6 NPC(s) keep their interactions" in out


# ---- field id/name resolution (baked table, offline) ----
def test_resolve_field_id_digit():
    assert FR.resolve_field_id("100") == 100


def test_resolve_field_id_substring():
    assert FR.resolve_field_id("dl_shp") == 354          # the Dali Weapon Shop (unique substring)


def test_resolve_field_id_not_found():
    with pytest.raises(ValueError, match="no field matches"):
        FR.resolve_field_id("zzz_nope_nope")


def test_resolve_field_id_invalid_digit():
    # a bare number that is NOT a real field id must error (not silently read as 'nothing to fork') --
    # and the message warns it's a FIELD id, not a map number (the fork-report vs import token footgun).
    with pytest.raises(ValueError, match="no field with id 99999"):
        FR.resolve_field_id("99999")


def test_resolve_field_id_ambiguous():
    with pytest.raises(ValueError, match="matches"):
        FR.resolve_field_id("alxt")                      # many Alexandria fields, no exact match


# ---- install-gated: the director / rotating-cast signals on real fields ----
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_analyze_dali_shop_is_story_event():
    rep = FR.analyze(354)                                # the real Dali Weapon Shop (rotating cast + a director)
    assert rep.roster_class == "story-event"
    assert rep.directors                                 # >= 1 cutscene-director object
    assert len(rep.sc_gates) >= FR._ROTATING_GATE_COUNT  # gates content across many beats


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_analyze_daguerreo_is_static_roster():
    rep = FR.analyze(2803)                               # Daguerreo 2F -- a clean static-roster field
    assert rep.roster_class == "static-roster"
    assert rep.directors == []
    # the #5 text axis: all 6 carried NPCs speak (36 lines) -> the report tells you to fork with --carry-text
    assert rep.n_speaking == 6 and rep.n_dialogue_lines == 36
    assert "6 NPC(s) speak 36 line(s)" in FR.format_report(rep)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_analyze_populates_camera_axis_from_the_scene():
    # the Camera axis needs the install (it reads the scene .bgs, not the .eb). analyze() must fill it in;
    # Daguerreo 2F is a real, non-scrolling field -> a sane pitch/FOV + a rendered Camera line.
    rep = FR.analyze(2803)
    assert rep.cam_pitch is not None and rep.cam_fov is not None
    assert 0 < rep.cam_fov < 120 and rep.cam_count >= 1
    line = next(l for l in FR.format_report(rep).splitlines() if l.strip().startswith("Camera"))
    assert any(feel in line for feel in ("close", "medium", "wide")) and "pitch" in line


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_analyze_multipc_nonzidane_names_the_controlled_pc():
    # field 2003 (ac_alt) defines Garnet + Eiko (no Zidane). The engine binds control to the LAST
    # DefinePlayerCharacter executed = Eiko (Garnet's is gated, Eiko's is unconditional + spawned later).
    # fork-report must NAME Eiko as the controlled PC, not the first-entry Garnet (the old pents[0] guess).
    rep = FR.analyze(2003)
    assert rep.multi_pc and rep.non_zidane
    assert rep.controlled_name == "Eiko"                 # NOT "Garnet" (entry 7 binds, not the first entry 3)
    out = FR.format_report(rep)
    assert "controls Eiko" in out and "--verbatim" in out


# ---- the Items axis: treasure / gil / shops a verbatim fork reproduces (a plain fork DROPS) ----
from ff9mapkit import data                                                     # noqa: E402
from ff9mapkit.eb import edit, opcodes                                         # noqa: E402

CLEAN = data.blank_field_bytes("us")


def _entry(body):
    """A minimal type-1 entry (one tag-0 function at fpos 4) carrying `body` -- the test-eventscan idiom."""
    return bytes([1, 1]) + struct.pack("<HH", 0, 4) + body


def test_item_label_regular_key_and_card():
    assert FR.item_label(236) == "Potion"
    assert FR.item_label(232) == "Sapphire"              # the gem, not a Potion (the 232 trap)
    assert FR.item_label(0) == "Hammer"
    assert FR.item_label(300) == "key item #44"          # id % 1000 in 256-511 = important/key space
    assert FR.item_label(600) == "card #88"              # id % 1000 in 512-611 = Tetra Master card


def test_item_label_pool_encoded_ids_match_the_engine():
    # the event AddItem operand is POOL-encoded (id % 1000); these are real ids seen on vanilla fields.
    assert FR.item_label(1010) == "item #1010"           # pool 1, %1000=10 -> extended regular (unnamed)
    assert FR.item_label(31000) == "item #31000"         # field 358's "Received [ITEM=0]!" id (pool 31)
    assert FR.item_label(2610) == "card #98"             # %1000=610 -> a card (field 805)
    assert FR.item_label(3700) == "item #3700 (inert)"   # %1000=700 >= 612 -> engine no-op
    assert FR.item_inert(3700) and not FR.item_inert(2610) and not FR.item_inert(238)


def test_scan_item_ops_excludes_inert_grants():
    # an AddItem whose id is an engine no-op (id % 1000 >= 612) grants nothing -> excluded from gives; a card is kept.
    body = (opcodes.add_item(3700, 1)                    # inert (%1000=700) -> not a grant
            + opcodes.add_item(2610, 1)                  # a card (%1000=610) -> a real grant
            + opcodes.RETURN)
    g = edit.append_entry(CLEAN, 10, _entry(body))
    ops = FR.scan_item_ops(g)
    assert ops["gives"] == [(2610, 1)]                   # 3700 excluded, 2610 kept


def test_scan_item_ops_decodes_and_filters():
    # AddItem grants, gil, and a shop are decoded; NoItem(255) is filtered, RemoveItem is counted not granted,
    # and Menu(4,0) (SAVE) is NOT mistaken for a shop (only Menu(2,id) is).
    body = (opcodes.add_item(236, 1)                     # Potion x1
            + opcodes.add_item(237, 3)                   # Hi-Potion x3
            + opcodes.add_item(255, 1)                   # NoItem -> filtered out
            + opcodes.encode(0x49, 240, 1)               # RemoveItem(Phoenix Down) -> counted, not a give
            + opcodes.add_gil(500) + opcodes.add_gil(250)
            + opcodes.menu(2, 7)                         # opens shop #7
            + opcodes.menu(4, 0)                         # the SAVE menu -> must NOT count as a shop
            + opcodes.RETURN)
    g = edit.append_entry(CLEAN, 10, _entry(body))
    ops = FR.scan_item_ops(g)
    assert ops["gives"] == [(236, 1), (237, 3)]          # sorted by id; NoItem filtered
    assert ops["gil_max"] == 500 and ops["gil_any"] is True   # per-grant max (NOT summed to 750)
    assert ops["shops"] == [7]                           # save menu excluded
    assert ops["removes"] == 1
    assert ops["var_give"] is False


def test_scan_item_ops_flags_computed_item_id():
    # an AddItem whose item id is an EXPRESSION (computed) can't be previewed -> var_give, not a give.
    expr = b"\x7d\x00\x00\x7f"                            # a trivial valid expr operand: B_CONST 0 ; end (0x7F)
    body = opcodes.encode(0x48, expr, 1, arg_flags=0b01) + opcodes.RETURN
    g = edit.append_entry(CLEAN, 10, _entry(body))
    ops = FR.scan_item_ops(g)
    assert ops["var_give"] is True and ops["gives"] == []


def test_scan_item_ops_does_not_sum_across_paths_or_show_overcap_gil():
    # a field runs MUTUALLY-EXCLUSIVE gated paths, so the same chest's grant recurs. The preview must NOT sum:
    # two identical grant sites = ONE Ether (count 1, not 2). And an AddGil literal above the 9,999,999 cap is a
    # scripted sentinel (field 854's ~16.7M), so it is suppressed from gil_max but still flips gil_any.
    one = opcodes.add_item(238, 1) + opcodes.add_gil(16776454)
    g = edit.append_entry(CLEAN, 10, _entry(one + one + opcodes.RETURN))
    ops = FR.scan_item_ops(g)
    assert ops["gives"] == [(238, 1)]                    # distinct item; count NOT summed to 2
    assert ops["gil_max"] == 0 and ops["gil_any"] is True  # over-cap literal -> no amount shown, but flagged


def test_scan_item_ops_flags_computed_shop_id():
    # Menu(2, <expr>) is a story-gated shop whose id is picked at runtime -> var_shop (not a concrete shop id).
    expr = b"\x7d\x00\x00\x7f"                            # a trivial valid expr operand
    body = opcodes.encode(0x75, 2, expr, arg_flags=0b10) + opcodes.RETURN  # Menu(menu_id=2, sub_id=<expr>)
    g = edit.append_entry(CLEAN, 10, _entry(body))
    ops = FR.scan_item_ops(g)
    assert ops["var_shop"] is True and ops["shops"] == []


def test_scan_item_ops_alex100_is_well_formed():
    ops = FR.scan_item_ops(ALEX100)
    assert set(ops) == {"gives", "gil_max", "gil_any", "shops", "removes", "var_give", "var_shop"}
    assert isinstance(ops["gives"], list) and isinstance(ops["shops"], list) and isinstance(ops["gil_max"], int)


def test_analyze_eb_items_axis_present_iff_content():
    # the Items line renders exactly when the field grants something (ALEX100 -- whatever it contains).
    rep = FR.analyze_eb(ALEX100, field_id=100, fbg_name="fbg_n01_alxt_map016_at_msa_0")
    out = FR.format_report(rep)
    out.encode("ascii")
    has = bool(rep.item_gives or rep.item_var_give or rep.item_gil_any or rep.item_shops or rep.item_var_shop)
    assert any(l.strip().startswith("Items") for l in out.splitlines()) == has


def test_format_report_items_line_present_and_absent():
    rep = FR.ForkReport(field_id=20, fbg_name="t", roster_class="static-roster")
    rep.n_objects = rep.n_props = 1
    rep.safety = {"clean": 1}
    rep.item_gives = [(236, 1), (237, 3)]
    rep.item_gil_max = 400
    rep.item_gil_any = True
    rep.item_shops = [7]
    out = FR.format_report(rep)
    out.encode("ascii")                                  # ASCII-safe for cp1252 consoles
    line = next(l for l in out.splitlines() if l.strip().startswith("Items"))
    assert "Potion" in line and "x3" in line             # Hi-Potion x3 (count shown only when != 1)
    assert "up to 400 gil" in line and "shop(s) #7" in line
    assert "DROPS them" in line and "ShopItems.csv" in line
    # absent when the field grants nothing
    rep.item_gives, rep.item_gil_max, rep.item_gil_any, rep.item_shops = [], 0, False, []
    assert not any(l.strip().startswith("Items") for l in FR.format_report(rep).splitlines())


def test_format_report_items_line_scripted_gil_when_overcap():
    # gil present but no plausible amount (over-cap / computed) -> "gil (scripted)", not a bogus number.
    rep = FR.ForkReport(field_id=21, fbg_name="u", roster_class="static-roster")
    rep.n_objects = rep.n_talkable = 1
    rep.safety = {"clean": 1}
    rep.item_gil_any = True
    out = FR.format_report(rep)
    out.encode("ascii")
    line = next(l for l in out.splitlines() if l.strip().startswith("Items"))
    assert "gil (scripted)" in line and "up to" not in line


def test_format_report_items_line_for_var_give_or_var_shop_only():
    # the BUG fix: a field whose ONLY item op is computed (var_give / var_shop) must STILL render the Items line
    # (the render guard previously omitted both, silently dropping a real signal the scanner detected).
    rep = FR.ForkReport(field_id=22, fbg_name="v", roster_class="static-roster")
    rep.n_objects = rep.n_talkable = 1
    rep.safety = {"clean": 1}
    rep.item_var_give = True
    out = FR.format_report(rep)
    out.encode("ascii")
    assert any(l.strip().startswith("Items") for l in out.splitlines())
    assert "computed-id item(s)" in out
    # a var_shop-only field renders the story-gated-shop note + the base-CSV caveat
    rep2 = FR.ForkReport(field_id=23, fbg_name="w", roster_class="static-roster")
    rep2.n_objects = rep2.n_talkable = 1
    rep2.safety = {"clean": 1}
    rep2.item_var_shop = True
    line = next(l for l in FR.format_report(rep2).splitlines() if l.strip().startswith("Items"))
    assert "story-gated shop" in line and "ShopItems.csv" in line
