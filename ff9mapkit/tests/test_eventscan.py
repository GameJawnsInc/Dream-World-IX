"""Read side of the .eb: extracting gateways / music / encounters / movement from a real field.

Two oracles:
  * a REAL field -- Alexandria/Main Street (field 100, ``alex100-us.eb.bytes``) has three real exits
    (101/107/114) plus the door we injected in Session 12 (-> 4000), field BGM song 9, head-on
    movement, and no encounters. The scanner must recover all of that.
  * ROUND-TRIP against the kit's own injectors -- inject a gateway / encounter into the blank field,
    scan it back, and the values must match (the scanner is the exact inverse of the injectors).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import data, eventscan
from ff9mapkit.content import encounter as _enc
from ff9mapkit.content import gateway as _gw

FIX = Path(__file__).parent / "fixtures"
ALEX100 = (FIX / "alex100-us.eb.bytes").read_bytes()
CLEAN = data.blank_field_bytes("us")


# --- real field (field 100) ---------------------------------------------------------------
def test_scan_gateways_real_field():
    gws = eventscan.scan_gateways(ALEX100)
    by_to = {g["to"]: g for g in gws}
    assert {101, 107, 114, 4000} <= set(by_to)            # 3 real exits + our injected door
    assert by_to[101]["entrance"] == 200                  # the real arrival entrance
    for g in gws:
        assert len(g["zone"]) in (3, 4)                   # normalised to quad corners
        assert all(len(p) == 2 for p in g["zone"])


def test_scan_injected_door_roundtrips_through_real_field():
    # the Session-12 Alexandria door we injected into field 100 -> our custom field 4000
    door = next(g for g in eventscan.scan_gateways(ALEX100) if g["to"] == 4000)
    assert door["entrance"] == 0
    assert door["zone"] == [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400]]


def test_scan_music_real_field():
    assert eventscan.scan_music(ALEX100) == 9             # Vivi's Theme (Disc 1)


def test_scan_control_direction_real_field():
    assert eventscan.scan_control_direction(ALEX100) == 0  # head-on town camera


def test_scan_encounter_none_in_town():
    assert eventscan.scan_encounter(ALEX100) is None       # towns have no random battles


# --- GLOB flag scanners (P5) --------------------------------------------------------------
def test_glob_var_token():
    assert eventscan._glob_var_token(bytes([0xC4, 191]), 0) == (191, 2)          # short GLOB bool
    assert eventscan._glob_var_token(bytes([0xE4, 0x71, 0x20]), 0) == (8305, 3)  # long GLOB bool (LE)
    assert eventscan._glob_var_token(bytes([0xC5, 5]), 0) is None                # MAP bool = transient
    assert eventscan._glob_var_token(bytes([0xE5, 0, 1]), 0) is None             # MAP long = transient
    assert eventscan._glob_var_token(bytes([0x7D, 0, 0]), 0) is None             # not a var token


def test_flag_gate_scanners_roundtrip():
    Z = [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400], [-700, 3400]]   # quad + doubled last vertex
    eb = _gw.inject_gateway(CLEAN, 4000, entrance=0, zone=Z, gate_flag=8305, gate_require_set=True)
    assert eventscan.scan_edge_flag_gates(eb) == [(8305, True)]      # the exact region.flag_gate prologue
    assert (8305, True) in eventscan.scan_required_flags(eb)         # general read form catches it too
    # a gate READS its flag, never WRITES it (the template's own housekeeping writes 184/191 stay separate)
    assert 8305 not in {idx for idx, _op in eventscan.scan_flags_set(eb)}

    eb2 = _gw.inject_gateway(CLEAN, 4000, entrance=0, zone=Z, gate_flag=8305, gate_require_set=False)
    assert eventscan.scan_edge_flag_gates(eb2) == [(8305, False)]    # polarity flips with require_set


def test_scan_content_aggregate():
    c = eventscan.scan_content(ALEX100)
    assert c["music"] == 9 and c["control_direction"] == 0 and c["encounter"] is None
    assert len(c["gateways"]) >= 4


# --- round-trips against the kit's own injectors ------------------------------------------
def test_gateway_roundtrip():
    zone = _gw.quad_zone([(-200, 200), (200, 200), (200, 400), (-200, 400)])
    eb = _gw.inject_gateway(CLEAN, 1234, entrance=42, zone=zone)
    gws = eventscan.scan_gateways(eb)
    assert len(gws) == 1
    g = gws[0]
    assert g["to"] == 1234 and g["entrance"] == 42
    assert g["zone"] == [[-200, 200], [200, 200], [200, 400], [-200, 400]]   # doubled vertex dropped


def test_encounter_roundtrip():
    eb = _enc.inject_encounter(CLEAN, scene=67, freq=200)
    enc = eventscan.scan_encounter(eb)
    assert enc is not None
    assert enc["scenes"] == [67, 67, 67, 67]
    assert enc["freq"] == 200


def test_encounter_distinct_scenes_roundtrip():
    eb = _enc.inject_encounter(CLEAN, scene=67, scenes=(10, 11, 12, 13), freq=128)
    enc = eventscan.scan_encounter(eb)
    assert enc["scenes"] == [10, 11, 12, 13] and enc["freq"] == 128


# --- import emission (the field.toml blocks ff9mapkit import writes) ----------------------
def test_imported_content_toml_is_valid_and_complete(tmp_path):
    import tomllib
    from ff9mapkit import extract
    # objects carry a verbatim entry sidecar, so the emit needs an out_dir (as ladders/jumps do)
    blocks, cd, summary = extract._imported_content_toml(ALEX100, out_dir=tmp_path, name="field")
    assert cd == 0
    assert summary == {"gateways": 4, "encounter": False, "music": 9, "battle_music": None,
                       "control_direction": 0,   # no encounter -> no battle song to auto-detect
                       "ladders": 0, "jumps": 0, "objects": 2,   # Alexandria: the bell + the ticket prop,
                       "player_funcs": 0, "carry_text": 0, "save_moogle": 0,   # carried VERBATIM (hidden NPCs
                       "spawn_flash": 0, "spawn_flash_fixed": 0,   # skipped); no graft/carry/save-moogle/flash here
                       "gateways_retargeted": 0, "gateways_seamed": 0, "story_branch": 0,
                       "gateway_carry": 0, "gateway_gated_seam": 0}   # Alexandria doors are spatial, not story-gated
    # the verbatim entry sidecars are written next to the field.toml
    assert (tmp_path / "field.object0.bin").is_file() and (tmp_path / "field.object1.bin").is_file()
    # embed in a complete borrow field.toml -> it must be valid TOML with the right structures
    toml = ('[field]\nid=4003\nname="T"\narea=2\nborrow_bg="X"\n\n'
            f'[camera]\nborrow="c.bgx"\ncontrol_direction={cd}\n\n[player]\nspawn=[0,0]\n\n{blocks}')
    d = tomllib.loads(toml)
    assert {g["to"] for g in d["gateway"]} == {101, 107, 114, 4000}
    assert all(len(g["zone"]) == 4 for g in d["gateway"])
    assert d["music"]["song"] == 9
    # the imported objects are emitted as [[object]] graft blocks pointing at their sidecars
    assert len(d["object"]) == 2 and {o["bin"] for o in d["object"]} == {"field.object0.bin", "field.object1.bin"}
    assert all("instances" in o and o["donor_player_entry"] == 19 for o in d["object"])


# --- scan_objects: carry a real field's persistent NPCs/props (faithful fork) -------------
def test_scan_objects_roundtrips_an_injected_prop():
    # the scanner is the inverse of the prop injector: inject a prop, scan it back exactly.
    from ff9mapkit.content import prop as _prop
    eb = _prop.inject_prop(CLEAN, 120, -340, model=133, pose=1872, face=5)
    objs = eventscan.scan_objects(eb)
    assert len(objs) == 1
    o = objs[0]
    assert o["kind"] == "prop" and o["model_id"] == 133 and o["pose"] == 1872
    assert (o["x"], o["z"]) == (120, -340) and o["face"] == 5 and o["talkable"] is False


def test_scan_objects_roundtrips_an_injected_npc_as_talkable():
    from ff9mapkit.content import npc as _npc
    eb = _npc.inject_npc(CLEAN, -80, 200, model=220, animset=50)   # a GEO_NPC moogle, talkable (keeps tag-3)
    objs = eventscan.scan_objects(eb)
    assert len(objs) == 1 and objs[0]["kind"] == "npc" and objs[0]["talkable"] is True
    assert (objs[0]["x"], objs[0]["z"]) == (-80, 200) and objs[0]["model_id"] == 220


def test_scan_objects_blank_field_has_none():
    # the bare template's only object is the PLAYER (DefinePlayerCharacter), which is excluded.
    assert eventscan.scan_objects(CLEAN) == []


def test_scan_player_arrivals_blank_is_single_spot():
    # #9 baseline: the blank field reads the entrance var (D8:2) but has ONE arrival -- a single spawn, so a
    # synth fork loses nothing. The signal that a fork loses per-door arrival is distinct > 1, not the read.
    a = eventscan.scan_player_arrivals(CLEAN)
    assert a["reads_entrance"] is True
    assert a["distinct"] == 1 and len(a["arrivals"]) == 1
    x, z, _face = a["arrivals"][0]
    assert isinstance(x, int) and isinstance(z, int)


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scan_player_arrivals_recovers_the_per_entrance_table():
    # #9: a real multi-entrance field positions the player by which door they came through. Alexandria Main
    # Street (field 100) has a 4-block arrival table; the Dali Weapon Shop (354) maps its entrances to 2
    # distinct spots. The scan recovers the per-door (x,z[,face]) placements a SYNTH fork would collapse.
    from ff9mapkit import extract
    a100 = eventscan.scan_player_arrivals(extract.extract_event_script("fbg_n01_alxt_map016_at_msa_0"))
    assert a100["reads_entrance"] and a100["distinct"] >= 3            # several distinct door arrivals
    assert all(isinstance(x, int) and isinstance(z, int) for x, z, _f in a100["arrivals"])
    a354 = eventscan.scan_player_arrivals(extract.extract_event_script("fbg_n06_vgdl_map103_dl_shp_0"))
    assert a354["distinct"] == 2                                       # two distinct shop arrival points


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_flags_stacked_story_branch_doors(tmp_path):
    # #2 (FORK_FIDELITY.md): a real field with a stacked if(flag){Field(A)}else{Field(B)} door (>1 DISTINCT
    # destination at one zone) must be surfaced so the author gates each branch -- else both arm in the fork.
    # Alexandria Castle 3F (ALXC_MAP040) has such a door; ~43 real fields do.
    from ff9mapkit import extract
    eb = extract.extract_event_script("fbg_n02_alxc_map040_ac_h3f_0")
    blocks, _cd, summary = extract._imported_content_toml(eb, name="CONDT", out_dir=tmp_path)
    assert summary["story_branch"] >= 2                 # both branches of the stacked door flagged
    assert "STORY-BRANCH door" in blocks and "# requires_flag =" in blocks


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scan_gateway_entries_classifies_story_gated_doors():
    # #2b (FORK_FIDELITY.md): a story-gated door (a conditional jump 0x02/0x03 on a GLOB save flag opC4/opE4)
    # is to be carried VERBATIM, not re-synthesized -- the kit's declarative rebuild drops the conditional
    # logic. scan_gateway_entries classifies each gateway entry + exposes Field-target offsets for the
    # destination remap. Dali Inn (VGDL_MAP101) entry 16 is story-gated (-> field 350); ~40 real fields are.
    from ff9mapkit import extract
    folder = next(f[0] for f in extract.list_fields() if "VGDL_MAP101" in f[2])
    ge = eventscan.scan_gateway_entries(extract.extract_event_script(folder))
    gated = [x for x in ge if x["story_gated"]]
    assert gated                                            # Dali Inn HAS a story-gated door
    for g in ge:
        # every Field-target offset really points at that destination id (LE) inside the verbatim entry bytes
        for off, fid in g["field_targets"]:
            assert int.from_bytes(g["entry_bytes"][off:off + 2], "little") == fid
        assert g["entry_bytes"][:1] == bytes([1])           # a type-1 region entry (carried whole)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scan_objects_skips_script_hidden_save_machinery():
    # field 122 (the Dali storage room): the visible barrel/boxes carry; the SAVE-POINT machinery
    # (moogle/book/tent, all loaded HIDDEN via SetObjectFlags + shown by the save script) is skipped --
    # carrying it placed an always-deployed tent + a floating moogle (the in-game-reported bug).
    from ff9mapkit import extract
    models = {o["model"] for o in eventscan.scan_objects(
        extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0"))}
    assert "GEO_ACC_F0_CSK" in models                                  # the barrel (shown set-dressing)
    assert not (models & {"GEO_ACC_F0_TNT", "GEO_ACC_F0_MGR", "GEO_NPC_F0_MOG"})   # hidden save machinery


# --- scan_objects_verbatim: the FAITHFUL graft spec (verbatim entry bytes + ref classification) -----
def test_scan_objects_verbatim_blank_has_none():
    assert eventscan.scan_objects_verbatim(CLEAN) == []


def test_scan_objects_verbatim_roundtrips_injected_prop_verbatim():
    # the graft scanner carries the donor entry VERBATIM (not a decode) -- a kit prop references nothing,
    # so it's fully graft-safe, and its carried bytes are byte-identical to the entry in the script.
    from ff9mapkit.content import prop as _prop
    eb = _prop.inject_prop(CLEAN, 120, -340, model=133, pose=1872, face=5)
    specs = eventscan.scan_objects_verbatim(eb)
    assert len(specs) == 1
    s = specs[0]
    assert s["kind"] == "prop" and s["model_id"] == 133 and s["pose"] == 1872
    assert s["instances"] == [{"arg": 0, "x": 120, "z": -340}]
    assert s["graft_safety"] == "clean" and s["carry_tags"] == [0]     # bare prop: Init-only, no refs
    assert s["player_tags_needed"] == [] and s["refs"] == []
    assert s["entry_bytes"] == eventscan._entry_bytes(eb, s["donor_idx"])   # VERBATIM
    assert s["self_positions"] is True and s["needs_d9"] == {}


def test_scan_objects_verbatim_dedups_duplicate_arg_instances():
    # #13(a): InitObject(slot, arg) addresses INSTANCE `arg`, so the same (slot, arg) emitted twice is one
    # instance re-init'd -- the donor's beat director fires just one site per beat, but a synth fork (no
    # director) would emit both and STACK identical copies (forking the Dali shop: DAF, InitObject'd twice
    # at arg 0, rendered as a stacked pair). The scanner collapses duplicate-arg sites; DISTINCT args (a
    # genuine row) are kept. Built from tested primitives: inject one prop, then arm extra InitObjects of it.
    from ff9mapkit.content import object as _object, prop as _prop
    eb = _prop.inject_prop(CLEAN, 120, -340, model=133, pose=1872, face=5)
    slot = eventscan.scan_objects_verbatim(eb)[0]["donor_idx"]

    dup = _object._arm(eb, slot, 0, {})                       # a SECOND InitObject, SAME arg 0 -> would stack
    sd = eventscan.scan_objects_verbatim(dup)
    assert len(sd) == 1 and [i["arg"] for i in sd[0]["instances"]] == [0]   # collapsed 2 -> 1

    dist = _object._arm(eb, slot, 1, {})                      # a DISTINCT arg -> a real second instance
    sx = eventscan.scan_objects_verbatim(dist)
    assert len(sx) == 1 and sorted(i["arg"] for i in sx[0]["instances"]) == [0, 1]   # kept


def test_scan_objects_verbatim_npc_is_talkable_and_clean():
    from ff9mapkit.content import npc as _npc
    eb = _npc.inject_npc(CLEAN, -80, 200, model=220, animset=50)
    specs = eventscan.scan_objects_verbatim(eb)
    assert len(specs) == 1 and specs[0]["kind"] == "npc"               # keeps a tag-3 talk func
    assert specs[0]["graft_safety"] == "clean" and specs[0]["carry_tags"] == [0, 1, 3]
    assert specs[0]["entry_bytes"] == eventscan._entry_bytes(eb, specs[0]["donor_idx"])


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scan_objects_verbatim_field122_cask_is_render_faithful():
    # The bug that started this: the field-122 cask rendered upside-down via the player-clone. The graft
    # carries its REAL entry verbatim. Its interactive tag-2 RunScripts the PLAYER (by entry index 23) at
    # tag 24 -- a tag the blank fork's player (tags 0/1 only) lacks -- so it is init_only: render tags
    # carry, tag 2 drops. Validates the design's key facts (docs/OBJECT_CARRY.md).
    from ff9mapkit import extract
    from ff9mapkit.eb import EbScript
    eb = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    specs = eventscan.scan_objects_verbatim(eb)
    by_slot = {s["donor_idx"]: s for s in specs}

    cask = next(s for s in specs if s["model"] == "GEO_ACC_F0_CSK")
    assert cask["graft_safety"] == "init_only"
    assert cask["instances"][0]["x"] == -250 and cask["instances"][0]["z"] == -571   # measured placement
    assert cask["pose"] == 1904 and cask["self_positions"] is True
    assert 2 not in cask["carry_tags"] and 24 in cask["player_tags_needed"]           # drop the dangling tag
    assert cask["entry_bytes"] == eventscan._entry_bytes(eb, cask["donor_idx"])       # VERBATIM
    pref = next(r for r in cask["refs"] if r["klass"] == "player")
    assert pref["op"] == 0x12 and pref["value"] == 23 and pref["tag"] == 24           # player BY ENTRY INDEX

    # the BBX is an arg-instanced row: ONE entry, three InitObject args, self-contained position.
    bbx = next(s for s in specs if s["model"] == "GEO_ACC_F0_BBX")
    assert bbx["graft_safety"] == "clean" and len(bbx["instances"]) == 3
    assert [i["arg"] for i in bbx["instances"]] == [128, 129, 130]

    # the player-entry-index guard: the controlled player (entry 23) is never carried as an object.
    assert eventscan._player_entry_index(EbScript.from_bytes(eb)) == 23
    assert 23 not in by_slot


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_graft_savepoint_carries_the_moogle_cluster():
    # P1 of the verbatim save-Moogle carry (docs/SAVEPOINT.md): the save cluster is loaded script-HIDDEN, so
    # the scanner skips it by default. graft_savepoint un-skips the RECOGNISED cluster -- the Moogle (model
    # 220) + the hidden book/feather/tent props it RunScripts -- as a unit. The mognet letter (entry 8) is
    # NOT in the cluster (it's mognet, not save). Default builds stay byte-identical (gated).
    from ff9mapkit import extract
    eb = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    assert 5 not in {s["donor_idx"] for s in eventscan.scan_objects_verbatim(eb)}        # hidden -> skipped (gated off)

    sp = eventscan.scan_objects_verbatim(eb, graft_savepoint=True, graft_player_funcs=True, graft_seq_helpers=True)
    by_slot = {s["donor_idx"]: s for s in sp}
    assert {5, 6, 7, 9} <= set(by_slot)                                                  # Moogle + book base/page + tent
    assert 8 not in by_slot                                                              # mognet letter NOT carried
    moogle = by_slot[5]
    assert moogle["model"] == "GEO_NPC_F0_MOG"
    # carried VERBATIM except the P6.1 spawn-Y normalization (Init height -> settled height, so a fork shows no
    # one-shot spawn-then-drop). Everything else is byte-identical to the donor entry.
    from ff9mapkit.eb import EbScript as _Eb
    _verbatim = eventscan._entry_bytes(eb, 5)
    _iy, _sy, _pos, _sz = eventscan.spawn_settle_mismatch(_Eb.from_bytes(eb), 5)
    _expected = bytearray(_verbatim)
    _expected[_pos:_pos + _sz] = int(_sy).to_bytes(_sz, "little")
    assert moogle["entry_bytes"] == bytes(_expected)
    assert sorted(moogle["player_tags_needed"]) == [13, 14, 15]                          # the pose surgery
    # P2: those player funcs each TurnTowardObject the carried Moogle (a sibling) -- now graftable (the
    # player graft remaps the uid to the Moogle's fork slot), so the Moogle is CLEAN and its tag-3 (the save
    # talk) is carried whole, not dropped.
    assert moogle["graft_safety"] == "clean"
    assert 3 in moogle["carry_tags"]
    pf = {p["donor_tag"]: p for p in eventscan.scan_player_funcs(eb, graft_savepoint=True)}
    assert all(pf[t]["safety"] == "clean" and pf[t]["sibling_refs"] == [5] for t in (13, 14, 15))


# --- STARTSEQ-helper closure + the two v1 classification fixes (docs/OBJECT_CARRY.md S2 v1.5) ----------
import struct                                                                          # noqa: E402

from ff9mapkit.eb import EbScript, edit, opcodes                                       # noqa: E402

STARTSEQ = 0x43


def _type1(body=None):
    return bytes([1, 1]) + struct.pack("<HH", 0, 4) + (opcodes.RETURN if body is None else body)


def test_seq_helper_safe_vets_the_body():
    eb = EbScript.from_bytes(edit.append_entry(CLEAN, 10, _type1()))                   # benign type-1
    assert eventscan._seq_helper_safe(eb, 10) is True
    movecam = EbScript.from_bytes(edit.append_entry(CLEAN, 10, _type1(
        opcodes.encode(0x6F, 0, 0, 0, 0, 0, 0) + opcodes.RETURN)))                     # MoveCamera = cutscene
    assert eventscan._seq_helper_safe(movecam, 10) is False
    nested = EbScript.from_bytes(edit.append_entry(CLEAN, 10, _type1(
        opcodes.encode(STARTSEQ, 3) + opcodes.RETURN)))                                # nested STARTSEQ
    assert eventscan._seq_helper_safe(nested, 10) is False
    type0 = EbScript.from_bytes(edit.append_entry(CLEAN, 10, bytes([0, 1]) + struct.pack("<HH", 0, 4)
                                                  + opcodes.RETURN))
    assert eventscan._seq_helper_safe(type0, 10) is False                              # not a type-1 entry


def test_classify_ref_secondary_pc_is_player_not_uncarried():
    # a uid ref to a SECONDARY DefinePlayerCharacter entry must classify as `player` (the multi-PC fix)
    assert eventscan._classify_ref("uid", 8, [5, 8], carried_slots=set(), self_slot=7) == "player"
    assert eventscan._classify_ref("uid", 5, 5, carried_slots=set(), self_slot=7) == "player"   # int form
    assert eventscan._classify_ref("uid", 9, [5, 8], carried_slots={9}, self_slot=7) == "sibling"
    assert eventscan._classify_ref("uid", 9, [5, 8], carried_slots=set(), self_slot=7) == "uncarried"


def test_graft_seq_helpers_flips_a_synthetic_object():
    # an object whose LOOP (a render tag) launches STARTSEQ(<benign type-1 helper>): refused by default
    # (the helper is uncarried), graftable with graft_seq_helpers (the closure carries the helper).
    g = edit.append_entry(CLEAN, 10, _type1())                                         # the helper at slot 10
    init = (opcodes.encode(eventscan.SET_MODEL_OP, 133, 0)
            + opcodes.encode(eventscan.SET_STAND_ANIM_OP, 1872) + opcodes.RETURN)
    loop = opcodes.encode(STARTSEQ, 10) + opcodes.RETURN
    obj = bytes([0, 2]) + struct.pack("<HH", 0, 8) + struct.pack("<HH", 1, 8 + len(init)) + init + loop
    g = edit.append_entry(g, 11, obj)
    g = edit.activate(g, opcodes.init_object(11, 0))
    off = {s["donor_idx"]: s for s in eventscan.scan_objects_verbatim(g)}[11]
    assert off["graft_safety"] == "refuse" and "seqs" not in off                       # closure OFF
    on = {s["donor_idx"]: s for s in eventscan.scan_objects_verbatim(g, graft_seq_helpers=True)}[11]
    assert on["graft_safety"] == "clean" and [h["entry"] for h in on["seqs"]] == [10]  # closure ON
    assert on["seqs"][0]["bytes"] == eventscan._entry_bytes(g, 10)                      # the verbatim helper


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_seq_closure_invariants_across_all_fields():
    # The closure must never carry an unsafe/non-type-1/nested helper, never double-arm, and never make a
    # previously-graftable object WORSE (monotone). Census-grounded over every real field.
    from ff9mapkit.extract import EventBundle, ID_TO_EVT
    bundle = EventBundle()
    rank = {"clean": 2, "init_only": 1, "refuse": 0}
    n_seqs = n_helpers = unrefused = 0
    for fid in sorted(ID_TO_EVT):
        try:
            eb_bytes = bundle.eb_for_id(fid)
        except Exception:
            continue
        if not eb_bytes:
            continue
        eb = EbScript.from_bytes(eb_bytes)
        off = {s["donor_idx"]: s for s in eventscan.scan_objects_verbatim(eb_bytes)}
        on = eventscan.scan_objects_verbatim(eb_bytes, graft_seq_helpers=True)
        donor_idx = {s["donor_idx"] for s in on}
        for s in on:
            assert rank[s["graft_safety"]] >= rank[off[s["donor_idx"]]["graft_safety"]]   # monotone
            if off[s["donor_idx"]]["graft_safety"] == "refuse" and s["graft_safety"] != "refuse":
                unrefused += 1
            for h in (s.get("seqs") or []):
                n_seqs += 1
                ei = h["entry"]
                assert eventscan._seq_helper_safe(eb, ei)                                  # benign + type-1
                assert ei not in donor_idx                                                 # no double-arm
                assert h["bytes"] == eventscan._entry_bytes(eb_bytes, ei)                   # verbatim
        n_helpers += sum(len(s.get("seqs") or []) for s in on)
    assert unrefused >= 40 and n_seqs >= 80                                            # the real win (53 / 109)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_seq_closure_field567_flips_the_v02_prop():
    # field 567 (Lindblum): a GEO_ACC_F0_V02 prop is REFUSED by v1 (its Loop STARTSEQs a benign Seq helper
    # the fork drops); the closure carries the helper, so it grafts. The in-game positive gate.
    from ff9mapkit.extract import EventBundle
    eb = EventBundle().eb_for_id(567)
    off = {s["model"]: s for s in eventscan.scan_objects_verbatim(eb)}
    on = {s["model"]: s for s in eventscan.scan_objects_verbatim(eb, graft_seq_helpers=True)}
    assert off["GEO_ACC_F0_V02"]["graft_safety"] == "refuse"
    assert on["GEO_ACC_F0_V02"]["graft_safety"] == "clean"
    assert [h["entry"] for h in on["GEO_ACC_F0_V02"]["seqs"]]                          # carries its helper


# --- scan_player_funcs: the player-function graft scanner (docs/PLAYER_GRAFT.md) -----------
def _classify_player_body(body, model=98):
    from ff9mapkit.eb import edit
    pe = eventscan._player_entry_index(eventscan.EbScript.from_bytes(CLEAN))
    eb2 = eventscan.EbScript.from_bytes(edit.add_function(CLEAN, pe, 50, bytes(body)))
    f = eb2.entry(pe).func_by_tag(50)
    return eventscan._player_func_safety(eb2, f, model, pe)[0]


def test_player_func_safety_classifies_each_class():
    from ff9mapkit.eb import opcodes
    assert _classify_player_body(opcodes.RETURN) == "clean"                          # bare gesture (only RETURN)
    assert _classify_player_body(opcodes.window_sync(1, 128, 62) + opcodes.RETURN) == "text"
    assert _classify_player_body(opcodes.field(100) + opcodes.RETURN) == "exotic"     # a warp mid-interaction
    assert _classify_player_body(opcodes.run_script_sync(2, 5, 0) + opcodes.RETURN) == "sibling"      # uid 5 = sibling
    assert _classify_player_body(opcodes.run_script_sync(2, 250, 9) + opcodes.RETURN) == "transitive"  # -> player tag
    anim = opcodes.encode(0x33, 200) + opcodes.RETURN                                 # SetStandAnimation(200)
    assert _classify_player_body(anim, model=98) == "clean"                           # Zidane donor -> ok
    assert _classify_player_body(anim, model=520) == "model"                          # non-Zidane -> clips won't match


def test_scan_player_funcs_blank_and_no_objects():
    assert eventscan.scan_player_funcs(CLEAN) == []
    from ff9mapkit.content import prop as _prop
    # a kit prop never RunScripts a player tag -> nothing to graft
    assert eventscan.scan_player_funcs(_prop.inject_prop(CLEAN, 0, 0, model=133, pose=1)) == []


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scan_player_funcs_field122_cask_box_are_clean():
    from ff9mapkit import extract
    eb = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    assert eventscan.resolve_player_entries(eventscan.EbScript.from_bytes(eb)) == [23]
    specs = {s["donor_tag"]: s for s in eventscan.scan_player_funcs(eb)}
    assert set(specs) == {11, 12, 24}                            # the cask (24) + the two boxes (11, 12)
    assert all(s["safety"] == "clean" for s in specs.values())   # all graftable
    assert all(s["runscript_tags"] == [] for s in specs.values())          # depth-0 (no transitive closure)
    assert all(s["donor_player_model"] == 98 for s in specs.values())      # Zidane donor
    assert all(len(s["body"]) > 0 for s in specs.values())
    # the donor player Init loads anim packs the blank fork lacks (the clip-load caveat -- box clips live here)
    packs = {p[-1] for p in specs[11]["donor_init_packs"]}
    assert 907 in packs and 914 in packs


def test_player_graft_flag_off_is_byte_identical():
    # the policy-flip flag defaults OFF -> the object-carry result is unchanged (a kit prop has no player refs)
    from ff9mapkit.content import prop as _prop
    eb = _prop.inject_prop(CLEAN, 10, 20, model=133, pose=1)
    assert eventscan.scan_objects_verbatim(eb) == eventscan.scan_objects_verbatim(eb, graft_player_funcs=True)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_player_graft_policy_flip_makes_cask_whole():
    from ff9mapkit import extract
    eb = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    base = {s["donor_idx"]: s for s in eventscan.scan_objects_verbatim(eb)}
    flip = {s["donor_idx"]: s for s in eventscan.scan_objects_verbatim(eb, graft_player_funcs=True)}
    # the cask's ONLY blocker was the player tag-24 ref -> with the graft it carries WHOLE (interactive tag 2 kept)
    assert base[10]["graft_safety"] == "init_only" and 2 not in base[10]["carry_tags"]
    assert flip[10]["graft_safety"] == "clean" and 2 in flip[10]["carry_tags"]
    # TBX-12 ALSO has a STARTSEQ-to-uncarried (tag 18) -> stays init_only, but now carries its player tag 2
    assert flip[12]["graft_safety"] == "init_only" and 2 in flip[12]["carry_tags"]


def test_content_section_falls_back_to_commented_stub_when_empty():
    from ff9mapkit import extract
    assert extract._content_section("", 5, 7).lstrip().startswith("# [[gateway]]")
    assert extract._content_section("[[gateway]]\nto = 9", 0, 0).startswith("[[gateway]]")


def test_fieldtable_maps_known_fields_to_event_names():
    from ff9mapkit._fieldtable import FBG_TO_EVT
    assert len(FBG_TO_EVT) > 600
    assert FBG_TO_EVT["fbg_n21_grgr_map420_gr_cen_0"][1] == "EVT_GARGAN_GR_CEN_0"
    assert FBG_TO_EVT["fbg_n36_glgv_map792_gv_rm1_0"][1] == "EVT_GULUGU_GV_RM1_0"
