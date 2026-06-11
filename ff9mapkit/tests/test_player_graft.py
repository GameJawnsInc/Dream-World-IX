"""Player-function graft -- carry the donor's player funcs onto the fork player (content/player.py).

The graft that lights up the interactive tags the object graft drops to ``init_only``: a carried object's
``RunScript(player, T)`` now resolves because tag T's donor player function is grafted onto the fork player
(at a fresh band tag) and the object's call is remapped. These pin the mechanism offline; the closing proof
that the cask turns to face you on examine is the human playtest (docs/PLAYER_GRAFT.md, P4).
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import data, eventscan
from ff9mapkit.content import object as _object
from ff9mapkit.content import player as _player
from ff9mapkit.eb import EbScript, edit, opcodes

CLEAN = data.blank_field_bytes("us")


# --- the tag allocator: disjoint ladder / jump / object bands ---------------------------------------
def test_player_tag_allocator_bands():
    alloc = _player.PlayerTagAllocator(CLEAN)             # a blank fork player has tags {0, 1}
    assert alloc.take("ladder", 2) == [17, 18]            # byte-identical to the fixed FIRST_CLIMB_TAG today
    assert alloc.take("jump", 1) == [40]                  # FIRST_JUMP_TAG
    assert alloc.take("object", 3) == [64, 65, 66]        # FIRST_OBJECT_PLAYER_TAG


def test_player_tag_allocator_slides_past_overflow():
    alloc = _player.PlayerTagAllocator(CLEAN)
    jumps = alloc.take("jump", 25)                        # 40..64 -- the jump band overflows INTO the object floor
    assert jumps[-1] == 64
    assert alloc.take("object", 2) == [65, 66]            # 64 is taken -> the object band slides past it (no collision)


# --- the tag remaps (site a in object.py, site b here) ---------------------------------------------
def test_remap_entry_refs_player_tag_arg2_discriminator():
    # an object func that RunScripts the player BY ENTRY INDEX (23, tag 24) AND itself (255, tag 30):
    # the PLAYER call's tag is remapped (24 -> 66); the SELF call's tag is left verbatim (its own tag space).
    f0 = opcodes.RETURN
    f2 = bytes([0x12, 0x00, 6, 23, 24]) + bytes([0x12, 0x00, 0, 255, 30]) + opcodes.RETURN
    table = struct.pack("<HH", 0, 4 * 2) + struct.pack("<HH", 2, 4 * 2 + len(f0))
    entry = bytes([0, 2]) + table + f0 + f2
    slot = EbScript.from_bytes(CLEAN).first_free_slot()
    g = edit.append_entry(CLEAN, slot, entry)
    g = _object.remap_entry_refs(g, slot, donor_idx=10, donor_player_entry=23,
                                 donor2new={10: slot}, player_tag_remap={24: 66})
    eb = EbScript.from_bytes(g)
    runs = [[i.imm(k) for k in range(len(i.args))] for i in eb.instrs(eb.entry(slot).func_by_tag(2)) if i.op == 0x12]
    assert runs[0] == [6, 250, 66]                        # player: uid 23 -> 250, tag 24 -> 66
    assert runs[1] == [0, 255, 30]                        # self: untouched
    assert eb.to_bytes() == g                             # same-length patches -> still valid


def test_remap_player_func_siblings():
    # P2 of the save-Moogle carry: a grafted player func that TurnTowardObject(donor sibling 5) -- once the
    # object graft placed that sibling at fork slot 7 -- gets its uid remapped 5 -> 7. A player uid (250) is
    # never in the slot map, so it's untouched. Same-length 1-byte patch.
    body = opcodes.encode(0x51, 5, 16) + opcodes.encode(0x14, 2, 250, 0) + opcodes.RETURN   # TurnToward(5); RunScript(player)
    pe = eventscan._player_entry_index(EbScript.from_bytes(CLEAN))
    g = edit.add_function(CLEAN, pe, 66, body)                       # graft at fork tag 66
    out = _player.remap_player_func_siblings(g, {13: 66}, {5: 7})
    eb = EbScript.from_bytes(out)
    f = eb.entry(pe).func_by_tag(66)
    assert [i.imm(0) for i in eb.instrs(f) if i.op == 0x51] == [7]   # 5 -> 7 (the sibling's fork slot)
    assert [i.imm(1) for i in eb.instrs(f) if i.op == 0x14] == [250] # the player uid is untouched (not in slot_map)
    assert len(out) == len(g) and eb.to_bytes() == out              # same-length, valid


def test_remap_player_func_siblings_noop_without_map():
    pe = eventscan._player_entry_index(EbScript.from_bytes(CLEAN))
    g = edit.add_function(CLEAN, pe, 66, opcodes.encode(0x51, 5, 16) + opcodes.RETURN)
    assert _player.remap_player_func_siblings(g, {13: 66}, {}) == g  # empty slot_map -> byte-identical


def test_remap_player_tag_calls_site_b():
    body = bytes([0x14, 0x00, 2, 250, 11]) + bytes([0x14, 0x00, 2, 5, 11]) + opcodes.RETURN
    out = _player.remap_player_tag_calls(body, {11: 64})
    from ff9mapkit.eb.disasm import iter_code
    runs = [[i.imm(k) for k in range(len(i.args))] for i in iter_code(out, 0, len(out)) if i.op == 0x14]
    assert runs[0] == [2, 250, 64]                        # player call -> tag remapped
    assert runs[1] == [2, 5, 11]                          # a non-player (sibling) call -> untouched
    assert len(out) == len(body)                          # same-length


# --- the anim-pack splice + the graft itself --------------------------------------------------------
def test_ensure_player_anim_packs_splices_and_is_idempotent():
    pack = (16, 25, 4, 907)
    g = _player.ensure_player_anim_packs(CLEAN, [pack])
    eb = EbScript.from_bytes(g)
    pe = eventscan._player_entry_index(eb)
    loaded = [tuple(i.args) for i in eb.instrs(eb.entry(pe).func_by_tag(0)) if i.op == 0x88]
    assert pack in loaded and eb.to_bytes() == g
    assert _player.ensure_player_anim_packs(g, [pack]) == g   # idempotent: the pack is already present


def test_graft_player_funcs_adds_clean_skips_refused():
    pe = eventscan._player_entry_index(EbScript.from_bytes(CLEAN))
    specs = [
        {"donor_tag": 24, "safety": "clean", "body": opcodes.RETURN, "donor_init_packs": []},
        {"donor_tag": 11, "safety": "text", "body": opcodes.window_sync(1, 128, 5) + opcodes.RETURN,
         "donor_init_packs": []},                          # refused -> NOT grafted
    ]
    g = _player.graft_player_funcs(CLEAN, specs, {24: 66, 11: 64})
    eb = EbScript.from_bytes(g)
    tags = {f.tag for f in eb.entry(pe).funcs}
    assert 66 in tags and 64 not in tags                  # only the clean func grafted, at its fork tag
    assert eb.to_bytes() == g


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_full_graft_field122_cask_examine_resolves():
    # the headline: graft field-122's player funcs + objects onto a blank fork so the cask EXAMINE fires.
    from ff9mapkit import extract
    donor = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    specs_obj = eventscan.scan_objects_verbatim(donor, graft_player_funcs=True)
    specs_pf = eventscan.scan_player_funcs(donor)
    clean = [s for s in specs_pf if s["safety"] == "clean"]
    alloc = _player.PlayerTagAllocator(CLEAN)
    tagmap = {int(s["donor_tag"]): ft for s, ft in zip(clean, alloc.take("object", len(clean)))}
    assert tagmap == {11: 64, 12: 65, 24: 66}

    fork = _player.graft_player_funcs(CLEAN, specs_pf, tagmap)
    fork = _object.graft_objects(fork, [dict(s) for s in specs_obj], player_tag_remap=tagmap)
    eb = EbScript.from_bytes(fork)
    assert eb.to_bytes() == fork                          # the grafted fork round-trips byte-exact

    pe = eventscan._player_entry_index(eb)
    assert {64, 65, 66} <= {f.tag for f in eb.entry(pe).funcs}          # the player funcs grafted
    cask = next(s for s in eventscan.scan_objects_verbatim(fork) if s["model"] == "GEO_ACC_F0_CSK")
    assert 2 in [f.tag for f in eb.entry(cask["donor_idx"]).funcs]      # the interactive tag carried whole
    runs = [[i.imm(k) for k in range(len(i.args))]
            for i in eb.instrs(eb.entry(cask["donor_idx"]).func_by_tag(2)) if i.op in (0x10, 0x12, 0x14)]
    assert [6, 250, 66] in runs                           # cask EXAMINE -> player turn func (tag 24 -> fork 66)
    assert [0, 255, 30] in runs                           # the self-call (tag 30) is left verbatim
    # the box gesture clips' anim packs were spliced into the fork player Init
    packs = {tuple(i.args)[-1] for i in eb.instrs(eb.entry(pe).func_by_tag(0)) if i.op == 0x88}
    assert 907 in packs and 914 in packs


# --- P3 wiring: the import emit + build consume + the dangling-tag lint ------------------------------
def test_lint_flags_dangling_carried_player_tag(tmp_path):
    # an [[object]] whose CARRIED func RunScripts a player tag that no [[player_func]] grafts -> flagged
    # (the softlock guard). A DROPPED interactive tag (init_only carry_tags) would NOT flag -- tested via
    # the campaign suite (init_only objects build clean).
    import struct
    from ff9mapkit import build
    from ff9mapkit.eb import opcodes
    proj = tmp_path / "p"
    proj.mkdir()
    body = bytes([0x12, 0x00, 2, 5, 99]) + opcodes.RETURN                 # tag 0: RunScript(player-entry 5, tag 99)
    (proj / "o.object0.bin").write_bytes(bytes([0, 1]) + struct.pack("<HH", 0, 4) + body)
    (proj / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "T"\narea = 11\nborrow_bg = "X"\n\n[camera]\nborrow = "c.bgx"\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[object]]\nbin = "o.object0.bin"\nkind = "prop"\ndonor_idx = 10\ndonor_player_entry = 5\n'
        'instances = [{ arg = 0 }]\n', encoding="utf-8")
    probs = build.validate(build.FieldProject.load(proj / "f.field.toml"))
    assert any("99" in x and "dangle" in x.lower() for x in probs)        # player tag 99 has no [[player_func]]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_graft_player_funcs_builds_working_field122(tmp_path):
    # the full P3 pipeline: import --graft-player-funcs emits [[player_func]] + sidecars; build grafts them
    # onto the fork player + remaps the object's RunScript. (The closing visual proof is the human playtest.)
    from ff9mapkit import build, extract
    from ff9mapkit.config import ModLayout
    meta, toml = extract.write_native_project("fbg_n08_udft_map122_uf_sto_0", tmp_path / "proj",
                                              name="DALI_STO", field_id=30003, graft_player_funcs=True)
    assert meta["imported_content"]["player_funcs"] == 3                  # cask + 2 boxes
    p = build.FieldProject.load(toml)
    assert build.validate(p) == []                                       # lint clean (all 3 tags grafted)
    dist = tmp_path / "dist"
    build.build_mod([p], dist, mod_name="FF9CustomMap")
    data = ModLayout(dist).eb_path("us", "EVT_DALI_STO.eb.bytes").read_bytes()
    eb = EbScript.from_bytes(data)
    assert eb.to_bytes() == data
    pe = eventscan._player_entry_index(eb)
    assert {64, 65, 66} <= {f.tag for f in eb.entry(pe).funcs}            # grafted after the jump band (40-44)
    cask = next(s for s in eventscan.scan_objects_verbatim(data) if s["model"] == "GEO_ACC_F0_CSK")
    runs = [[i.imm(k) for k in range(len(i.args))]
            for i in eb.instrs(eb.entry(cask["donor_idx"]).func_by_tag(2)) if i.op in (0x10, 0x12, 0x14)]
    assert [6, 250, 66] in runs and [0, 255, 30] in runs                 # examine -> fork tag 66; self-call kept
