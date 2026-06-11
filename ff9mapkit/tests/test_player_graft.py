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


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_savepoint_carry_trigger_chain_and_flags_intact():
    # P3 of the verbatim save-Moogle carry (docs/SAVEPOINT.md). After the FULL cluster carry of field 122:
    #   (1) the TRIGGER CHAIN survives -- every RunScript ref in the carried cluster resolves to a carried
    #       fork slot / player (250) / self (255) / party (251-254); no ref dangles, whatever the indirect
    #       Moogle trigger (the cask sets a shared MAP var the Moogle's loop polls -- no direct RunScript).
    #   (2) the Moogle is carried VERBATIM (its save + state-machine logic byte-identical to the real game).
    #   (3) the cluster references NO save-persistent (GLOB bool) flag in the kit's CUSTOM band
    #       (>= FIRST_SAFE_FLAG 8512) -- so a forked save point can't corrupt the kit's own story flags. (It
    #       DOES reference the chest band 8376-8511: the Moogle's verbatim mognet/treasure-hunter logic reads
    #       the chest-opened bitfield -- a real-FF9 band the kit reserves anyway, not a collision. Its own
    #       GLOB writes include bits 184/189 = the byte-23 engine menu handshake.)
    from ff9mapkit import extract, flags
    donor = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    specs_obj = eventscan.scan_objects_verbatim(donor, graft_savepoint=True, graft_player_funcs=True,
                                                graft_seq_helpers=True)
    specs_pf = eventscan.scan_player_funcs(donor, graft_savepoint=True)
    clean = [s for s in specs_pf if s["safety"] == "clean"]
    alloc = _player.PlayerTagAllocator(CLEAN)
    tagmap = {int(s["donor_tag"]): ft for s, ft in zip(clean, alloc.take("object", len(clean)))}
    fork = _player.graft_player_funcs(CLEAN, specs_pf, tagmap)
    slot_map = {}
    fork = _object.graft_objects(fork, [dict(s) for s in specs_obj], player_tag_remap=tagmap, out_slot_map=slot_map)
    fork = _player.remap_player_func_siblings(fork, tagmap, slot_map)
    p = EbScript.from_bytes(fork)
    assert p.to_bytes() == fork                                       # the whole carried cluster round-trips
    fork_slots = set(slot_map.values())

    # (1) no dangling RunScript ref anywhere in the carried cluster
    for slot in fork_slots:
        for f in p.entry(slot).funcs:
            for i in p.instrs(f):
                if i.op in (0x10, 0x12, 0x14):
                    uid = i.imm(1)
                    if uid is None:
                        continue
                    assert uid in fork_slots or uid in (250, 255) or 251 <= uid <= 254, \
                        f"dangling RunScript uid {uid} (entry {slot} tag {f.tag})"

    # (2) the Moogle carried verbatim -- its save talk (tag 3) is present
    assert p.entry(slot_map[5]).func_by_tag(3) is not None

    # (3) GLOB-bool writes (0xC4 short / 0xE4 long) stay below the kit's reserved bands
    globs = []
    for slot in fork_slots:
        for f in p.entry(slot).funcs:
            for ins in p.instrs(f):
                if ins.op != 0x05:
                    continue
                raw = p.data[ins.off:ins.off + 8]
                tok = raw[1] if len(raw) > 1 else 0
                if tok in (0xC4, 0xE4):                               # GLOB bool (save-persistent)
                    globs.append((raw[2] | (raw[3] << 8)) if tok == 0xE4 else raw[2])
    assert globs, "expected the verbatim Moogle's GLOB refs to carry through"
    assert all(idx < flags.FIRST_SAFE_FLAG for idx in globs), \
        f"cluster GLOB ref in the kit's CUSTOM band: {sorted(i for i in globs if i >= flags.FIRST_SAFE_FLAG)}"
    assert {184, 189} & set(globs)                                   # the real menu-handshake writes, verbatim
    assert any(flags.CHEST_FLAG_LO <= i <= flags.CHEST_FLAG_HI for i in globs)   # the verbatim treasure-hunter reads


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


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_save_moogle_emits_cluster_and_builds(tmp_path):
    # P4 (docs/SAVEPOINT.md): `import --save-moogle` (graft_savepoint) emits the hidden save-Moogle cluster as
    # [[object]] blocks (the Moogle + book/feather/tent) + its pose surgery (13/14/15) as [[player_func]] +
    # a [[save_moogle]] marker; the build carries them. The closing proof (the pop-out + flourish) is P5 in-game.
    from ff9mapkit import build, extract
    from ff9mapkit.config import ModLayout
    meta, toml = extract.write_native_project("fbg_n08_udft_map122_uf_sto_0", tmp_path / "proj",
                                              name="SAVEMOG", field_id=30003, graft_player_funcs=True,
                                              graft_savepoint=True)
    assert meta["imported_content"]["save_moogle"] == 1                  # the marker fired (field 122 has one)
    p = build.FieldProject.load(toml)
    assert any(sm.get("carried") for sm in p.raw.get("save_moogle", []))  # [[save_moogle]] carried=true emitted
    assert build.validate(p) == []                                       # lint clean (cluster present)
    dist = tmp_path / "dist"
    build.build_mod([p], dist, mod_name="FF9CustomMap")
    data = ModLayout(dist).eb_path("us", "EVT_SAVEMOG.eb.bytes").read_bytes()
    s = EbScript.from_bytes(data)
    assert s.to_bytes() == data                                          # the carried fork round-trips
    models = {i.imm(0) for e in s.entries if not e.empty for f in e.funcs for i in s.instrs(f) if i.op == 0x2F}
    assert {220, 133, 134, 225} <= models                               # Moogle + book base/page + tent carried


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_savepoint_director_extracted_and_grafted():
    # the director graft (docs/SAVEPOINT.md P6): the donor's entry-0 tag-1 puppeteers the carried Moogle via
    # shared MAP vars. Extract it, confirm it's a clean shared-var driver (no entry refs, save-flash stripped),
    # and graft it into the fork's empty entry-0 tag-1.
    from ff9mapkit import data, extract
    from ff9mapkit.content import savepoint as _savepoint
    donor = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    director = eventscan.extract_savepoint_director(donor)
    assert director is not None
    from ff9mapkit.eb.disasm import iter_code
    ops = [i.op for i in iter_code(director, 0, len(director))]
    assert not any(o in (0x10, 0x12, 0x14, 0x43, 0x07, 0x08, 0x09) for o in ops)   # no entry refs (shared-var only)
    assert 0x6B not in ops                                              # SetBackgroundColor (save flash) stripped
    assert any(director[j:j + 3] == b"\xd5\x20\x7d" for j in range(len(director)))  # drives the Moogle state var
    # graft into a blank fork's empty entry-0 tag-1, round-trip
    fork = _savepoint.graft_director(data.blank_field_bytes("us"), director)
    p = EbScript.from_bytes(fork)
    assert p.to_bytes() == fork
    t1 = list(p.instrs(p.entry(0).func_by_tag(1)))
    assert any(i.op == 0x05 and p.data[i.off:i.off + 3] == b"\x05\xd5\x20" for i in t1)   # director now lives there
    # a field with no save Moogle -> no director
    assert eventscan.extract_savepoint_director(data.blank_field_bytes("us")) is None


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_savepoint_spawn_y_normalized():
    # P6.1 (docs/SAVEPOINT.md): the save Moogle's Init height (-362, standing ON the barrel) differs from its
    # settled height (-2, IN the barrel), so a fork shows a one-shot spawn-then-drop (the source field's
    # entrance fade hides it; F6-warp does not). The carry AUTO-FIXES it -- the carried Moogle spawns at rest.
    from ff9mapkit import extract
    donor = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    eb = EbScript.from_bytes(donor)
    moog = next(e.index for e in eb.entries if not e.empty and e.func_by_tag(0)
                and any(i.op == 0x2F and i.imm(0) == 220 for i in eb.instrs(e.func_by_tag(0))))
    mism = eventscan.spawn_settle_mismatch(eb, moog)
    assert mism is not None                                          # the donor HAS the spawn-flash signature
    init_y, settle_y, pos, sz = mism
    assert init_y != settle_y
    # the carried Moogle's entry is normalised: its Init Y now equals the settle Y
    specs = eventscan.scan_objects_verbatim(donor, graft_savepoint=True, graft_player_funcs=True,
                                            graft_seq_helpers=True)
    moogle = next(s for s in specs if s["model"] == "GEO_NPC_F0_MOG")
    assert int.from_bytes(moogle["entry_bytes"][pos:pos + sz], "little") == settle_y
    # the normalised entry still grafts + round-trips byte-exact
    fork = _object.graft_objects(data.blank_field_bytes("us"), [dict(moogle)])
    assert EbScript.from_bytes(fork).to_bytes() == fork
    # the recognised Moogle is auto-fixed (not left as a spawn_flash lint flag)
    assert "spawn_flash" not in moogle


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_graft_gateway_entry_carries_gated_door_verbatim():
    # #2b P2 (FORK_FIDELITY.md): a story-gated door is carried VERBATIM (its conditional state machine kept) +
    # the Field() destinations retargeted, NOT re-synthesized. Dali Inn (VGDL_MAP101) entry 16 is story-gated
    # -> field 350.
    from ff9mapkit import extract
    from ff9mapkit.content import gateway as _gw
    folder = next(f[0] for f in extract.list_fields() if "VGDL_MAP101" in f[2])
    gated = next(x for x in eventscan.scan_gateway_entries(extract.extract_event_script(folder))
                 if x["story_gated"])
    fork = data.blank_field_bytes("us")
    out, slot = _gw.graft_gateway_entry(fork, gated["entry_bytes"], retarget={350: 4100})
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out                                   # a valid eb (round-trips byte-exact)
    fields = [i.imm(0) for f in eb.entry(slot).funcs for i in eb.instrs(f) if i.op == 0x2B]
    assert fields == [4100]                                       # destination retargeted 350 -> 4100
    assert any(i.op == 0x08 and i.imm(0) == slot                  # armed: InitRegion(slot) in Main_Init
               for i in eb.instrs(eb.entry(0).func_by_tag(0)))
    assert any(i.op in (0x02, 0x03)                               # its conditional state machine SURVIVES
               for f in eb.entry(slot).funcs for i in eb.instrs(f))
    # no-retarget -> destinations stay as live seams (the door walks back into the live game)
    out2, slot2 = _gw.graft_gateway_entry(fork, gated["entry_bytes"])
    eb2 = EbScript.from_bytes(out2)
    assert [i.imm(0) for f in eb2.entry(slot2).funcs for i in eb2.instrs(f) if i.op == 0x2B] == [350]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_story_gated_door_carried_verbatim_and_builds(tmp_path):
    # #2b P3 (docs/FORK_FIDELITY.md): the import emits a story-gated door as a [[gateway_carry]] block +
    # .gatewayN.bin sidecar (NOT a declarative [[gateway]]), and the build grafts its conditional state machine
    # verbatim. Dali Inn (VGDL_MAP101) has one (-> field 350). End-to-end: import -> build -> the gate survives.
    from ff9mapkit import build, extract
    from ff9mapkit.config import ModLayout
    folder = next(f[0] for f in extract.list_fields() if "VGDL_MAP101" in f[2])
    meta, toml = extract.write_native_project(folder, tmp_path / "proj", name="DALIINN", field_id=30003)
    assert meta["imported_content"]["gateway_carry"] >= 1                 # a story-gated door was carried
    p = build.FieldProject.load(toml)
    assert any(gc.get("bin") for gc in p.raw.get("gateway_carry", []))    # [[gateway_carry]] emitted
    dist = tmp_path / "dist"
    build.build_mod([p], dist, mod_name="FF9CustomMap")
    data = ModLayout(dist).eb_path("us", "EVT_DALIINN.eb.bytes").read_bytes()
    assert EbScript.from_bytes(data).to_bytes() == data                  # the carried fork round-trips
    # the conditional state machine survived the graft -- the built fork still has a story-gated door entry
    assert any(x["story_gated"] for x in eventscan.scan_gateway_entries(data))
