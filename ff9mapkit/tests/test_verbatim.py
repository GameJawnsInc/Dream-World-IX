"""Verbatim-.eb fork (docs/FORK_FIDELITY.md, the entry-0 carry): ship a real field's WHOLE event script
instead of re-synthesizing, remapping only the Field() destinations."""
from __future__ import annotations

import pytest

from ff9mapkit import data
from ff9mapkit.content import gateway as _gw
from ff9mapkit.content import verbatim as _vb
from ff9mapkit.eb import EbScript


def _fields(eb_bytes):
    s = EbScript.from_bytes(eb_bytes)
    return [i.imm(0) for e in s.entries if not e.empty for f in e.funcs
            for i in s.instrs(f) if i.op == 0x2B]


def test_startup_applies_to_verbatim_eb():
    # REGRESSION (review #1): [startup] presets must reach a verbatim .eb too. build_field ships the verbatim
    # bytes WITHOUT calling build_script, so it must apply _apply_startup itself -- else the documented
    # "pair with [startup] to boot a beat" is a silent no-op and the fork boots at scenario-zero.
    from ff9mapkit import build

    class _P:                          # _apply_startup reads project.raw + project.field (the outpost write)
        def __init__(self, raw):
            self.raw = raw
            self.field = raw.get("field", {})

    blank = data.blank_field_bytes("us")
    assert build._apply_startup(_P({}), blank) == blank        # no [startup] -> byte-identical
    booted = build._apply_startup(_P({"startup": {"scenario": 2600}}), blank)
    assert booted != blank and len(booted) > len(blank)        # the ScenarioCounter preset was injected


def test_on_entry_arms_into_verbatim_bytes():
    # CONVERGENCE with story_flags' [[on_entry]]: like [startup], a field-load hook must fire in a verbatim
    # fork too -- build_field applies the shared _apply_on_entry to the verbatim bytes (the synthesize path's
    # build_script bypasses it). The helper arms a gated, once code entry into Main_Init.
    from ff9mapkit import build
    from ff9mapkit.build import _FlagAlloc
    from ff9mapkit.eb import EbScript

    class _P:
        name = "DV"

        def __init__(self, raw):
            self.raw = raw

    blank = data.blank_field_bytes("us")
    n0 = sum(1 for e in EbScript.from_bytes(blank).entries if not e.empty)
    assert build._apply_on_entry(_P({}), blank, {}, _FlagAlloc(None)) == blank   # no [[on_entry]] -> identical
    # a gated state-advance hook arms as one more code entry (the InitCode-in-Main_Init entry-beat hook)
    armed = build._apply_on_entry(_P({"on_entry": [{"set_scenario": 2600, "requires_scenario": 2000}]}),
                                  blank, {}, _FlagAlloc(None))
    assert armed != blank and len(armed) > len(blank)
    assert sum(1 for e in EbScript.from_bytes(armed).entries if not e.empty) == n0 + 1
    # verbatim drop_messages: a message hook drops the narration (warned) but STILL arms its state-advance
    warns = []
    armed_m = build._apply_on_entry(_P({"on_entry": [{"message": "Hi", "set_scenario": 2600}]}),
                                    blank, {0: 1234}, _FlagAlloc(None), drop_messages=True, warnings=warns)
    assert armed_m != blank and any("dropped" in w for w in warns)


def test_render_retarget_live_table_vs_template():
    # single-field import (no id_remap): the commented-out fill-in template, count 0 (byte-identical golden)
    txt, n = _vb.render_retarget([100, 200], None)
    assert n == 0 and txt == "# retarget = {\n#   100 = 0\n#   200 = 0\n# }\n"
    assert _vb.render_retarget([], None) == ("# retarget = {\n#   (this field has no Field() exits)\n# }\n", 0)
    # id_remap with NO in-chain dest -> still the template (nothing to wire), count 0
    assert _vb.render_retarget([100], {999: 4100})[1] == 0
    # import-chain: a LIVE table for the in-chain dest; the rest noted as live seams
    txt, n = _vb.render_retarget([100, 200], {100: 4100})
    assert n == 1
    assert txt == ("retarget = { 100 = 4100 }\n"
                   "# (the rest are live seams back into the real game -- not in this chain: 200)\n")
    # every dest in-chain -> no live-seam note
    assert _vb.render_retarget([100], {100: 4100}) == ("retarget = { 100 = 4100 }\n", 1)


def test_remap_fields_patches_destinations():
    # a gateway region warps Field(100); remap_fields retargets it (the verbatim-fork destination remap)
    eb = _gw.inject_gateway(data.blank_field_bytes("us"), 100,
                            zone=_gw.quad_zone([(0, 0), (10, 0), (10, 10), (0, 10)]))
    assert 100 in _fields(eb)
    out = _vb.remap_fields(eb, {100: 4100})
    assert 4100 in _fields(out) and 100 not in _fields(out)
    assert EbScript.from_bytes(out).to_bytes() == out          # still a valid, round-tripping eb
    # ids not in the map stay as live seams; an empty map is a byte-identical no-op
    assert _vb.remap_fields(eb, {999: 4100}) == eb
    assert _vb.remap_fields(eb, {}) == eb


def test_fork_donor_id_reads_native_source_field():
    """deploy_field auto-emits ForkDonorPatch for NATIVE/SYNTH forks too: build._verbatim_donor_id resolves the
    donor from `[field] source_field` (the native import's record), not only `[verbatim_eb] donor`."""
    from ff9mapkit.build import _verbatim_donor_id

    class _P:
        def __init__(self, raw):
            self.raw = raw

    assert _verbatim_donor_id(_P({"field": {"source_field": 351}})) == 351   # native fork
    assert _verbatim_donor_id(_P({"verbatim_eb": {"donor": 1860}})) == 1860  # verbatim fork (unchanged)
    assert _verbatim_donor_id(_P({"field": {"borrow_field": 100}})) == 100   # BG-borrow form
    assert _verbatim_donor_id(_P({"field": {}})) is None                     # a non-fork synth field -> no emit


def _game_ready():
    try:
        import UnityPy  # noqa: F401,PLC0415
        from ff9mapkit import config  # noqa: PLC0415
        return config.find_game_path(None) is not None
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_verbatim_ships_the_whole_donor_eb(tmp_path):
    # import --verbatim emits a [verbatim_eb] block + sidecar; the build ships the donor's WHOLE .eb
    # (Field-remapped) instead of synthesizing -- so the field runs its real logic (in-game proven on Dali Inn).
    from ff9mapkit import build, extract
    meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    assert meta["imported_content"]["verbatim_eb"]
    body = toml.read_text()
    assert "[verbatim_eb]" in body
    # #43: a verbatim fork ships a ready-to-uncomment [startup] stub (a fork boots at scenario 0; this is where
    # you set the beat). It's commented so the build IGNORES it (the donor .eb runs as-is)...
    assert "# [startup]" in body and "# scenario = 0" in body, "verbatim toml carries a commented [startup] stub"
    assert "startup" not in build.FieldProject.load(toml).raw, "the stub is commented -> not active until uncommented"
    # ...and uncommenting [startup]+scenario is well-formed TOML of the expected shape (the [startup] VALIDATOR
    # itself is covered by test_startup.py).
    import tomllib
    su = tomllib.loads("[startup]\nscenario = 0\nflags = [ { flag = 184, value = 1 } ]\n"
                       "words = [ { byte = 236, value = 0 } ]\n")["startup"]
    assert su["scenario"] == 0 and su["flags"][0]["flag"] == 184 and su["words"][0]["byte"] == 236
    project = build.FieldProject.load(toml)
    donor = extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0")
    assert _vb.verbatim_eb(project) == donor                    # no retarget -> the whole donor .eb, verbatim
    # P2 text: the donor's WHOLE .mes ships too, and the verbatim .eb's index-txids resolve into it (no remap)
    from ff9mapkit import dialogue
    assert meta["imported_content"]["text"]
    us = _vb.verbatim_mes(project, "us")
    assert us == dialogue.extract_field_mes("fbg_n06_vgdl_map101_dl_inn_0", "us")
    shown = {c.txid for c in dialogue.scan_dialogue(EbScript.from_bytes(donor)) if c.txid is not None}
    assert shown and shown <= set(dialogue.parse_mes(us))       # every line the .eb shows resolves in the text
    # with a retarget, that destination is patched in the shipped .eb (the rest stay live seams)
    exits = meta["imported_content"]["field_exits"]
    assert exits                                                # Dali Inn has Field() exits
    project.raw["verbatim_eb"]["retarget"] = {exits[0]: 4100}
    shipped = _vb.verbatim_eb(project)
    assert 4100 in _fields(shipped) and exits[0] not in _fields(shipped)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_native_import_records_donor_for_forkdonorpatch(tmp_path):
    # A NATIVE (non-verbatim) import now records `[field] source_field = <donor real id>`, so deploy_field can
    # auto-emit ForkDonorPatch (name-keyed occlusion/location fidelity) -- no more hand-written `<fork> <donor>`.
    from ff9mapkit import extract
    from ff9mapkit.build import FieldProject, _verbatim_donor_id
    from ff9mapkit.dialogue import _resolve_field_id
    fbg = "fbg_n06_vgdl_map101_dl_inn_0"
    donor = _resolve_field_id(fbg)
    _m, toml = extract.write_native_project(fbg, tmp_path, name="DV")    # native scene, NOT verbatim
    proj = FieldProject.load(toml)
    assert "verbatim_eb" not in proj.raw                                 # it's a native fork
    assert proj.raw["field"].get("source_field") == donor               # donor recorded in [field]
    assert _verbatim_donor_id(proj) == donor                            # -> deploy_field emits ForkDonorPatch


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_logic_edit_end_to_end(tmp_path):
    # REGRESSION: a FULL build of a verbatim fork must run build_field's per-language loop (which reads
    # _verbatim.verbatim_mes) AND apply [[logic_edit]] through compose_verbatim_eb -- the path the GUI panel
    # authors into. Exercises the whole pipe end-to-end (build_mod -> build_field), not just the unit helpers.
    from ff9mapkit import build, extract
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    site = next(((e.index, f.tag, ins.imm(0))
                 for e in donor.entries if not e.empty for f in e.funcs
                 for ins in donor.instrs(f) if ins.op == 0x2B and ins.imm(0) is not None), None)
    assert site, "Dali Inn has a literal Field() exit"
    ent, tag, dest = site
    project = build.FieldProject.load(toml)
    project.raw["logic_edit"] = [{"kind": "field", "entry": ent, "tag": tag, "op": 0x2B,
                                  "old": dest, "new": 6300, "nth": 0}]
    assert build.validate(project) == []                        # the GUI dry-run's offline gate agrees
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")     # must NOT raise (the _verbatim NameError site)
    ebs = list(out.rglob("*.eb.bytes"))
    assert ebs and any(6300 in _fields(p.read_bytes()) for p in ebs), "the [[logic_edit]] field retarget shipped"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_npc_end_to_end(tmp_path):
    # Add a NEW self-contained [[npc]] to a verbatim fork: build must (1) seat the NPC entry BELOW the donor's
    # 9-slot party-character band (so the entry count grows by 1 and the NPC is below the band), (2) ship a
    # _SpeakBTN WindowSync at a high appended txid, and (3) APPEND the NPC's dialogue line to every language's
    # .mes at that txid. This is the [[npc]]-on-verbatim wiring (was in _VERBATIM_IGNORED_BLOCKS).
    from ff9mapkit import build, extract, dialogue
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["npc"] = [{"name": "Guide", "preset": "vivi", "pos": [100, 200],
                           "dialogue": "Welcome to the modded fork!"}]
    assert build.validate(project) == []                        # Check agrees offline (incl. the txid plan)
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")     # must not raise
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    # the NPC seated below the band -> one more entry than the donor, NPC at slot N_donor-9
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE
    win_txids = set()
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 1, "the NPC entry was added below the band"
        assert not s.entry(band_lo).empty and s.entry(band_lo).func_by_tag(3) is not None, "NPC talk at band_lo"
        for e in s.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for i in s.instrs(f):
                    if i.op == 0x1F and i.imm(2) is not None and i.imm(2) >= 1000:
                        win_txids.add(i.imm(2))
    assert win_txids, "the NPC _SpeakBTN WindowSync was injected at an appended txid"
    mes = [p for p in out.rglob("*.mes")]
    assert mes and any("Welcome to the modded fork!" in p.read_text(encoding="utf-8") for p in mes), \
        "the NPC dialogue shipped in the appended .mes"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_opens_shop_end_to_end(tmp_path):
    # A shopkeeper [[npc]] opens_shop ADDED to a verbatim fork: the NPC seated below the band gets a tag-3 talk
    # body that (greets, then) opens the shop -- Menu(2, id) (op 0x75) -- and the custom [[shop]] inventory ships
    # in ShopItems.csv. The verbatim opener wiring (was warned + skipped; now passes speak_body to inject_npc).
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["shop"] = [{"id": 40, "comment": "Test", "sells": ["Potion", "Hi-Potion", "Phoenix Down"]}]
    project.raw["npc"] = [{"name": "Merchant", "preset": "vivi", "pos": [100, 200],
                           "dialogue": "Care to buy?", "opens_shop": 40}]
    assert build.validate(project) == []                         # Check agrees offline
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")     # must not raise
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 1            # merchant seated below the band
        tag3 = s.entry(band_lo).func_by_tag(3)
        assert tag3 is not None, "merchant has a tag-3 talk body"
        menus = [(i.imm(0), i.imm(1)) for i in s.instrs(tag3) if i.op == 0x75]
        assert (2, 40) in menus, f"merchant tag-3 should open shop 40 via Menu(2,40); got {menus}"
        assert any(i.op == 0x1F for i in s.instrs(tag3)), "the dialogue greeting (WindowSync) precedes the shop open"
    csv = list(out.rglob("ShopItems.csv"))
    assert csv and ";40;" in csv[0].read_text(encoding="utf-8"), "the custom shop 40 inventory shipped to ShopItems.csv"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_npc_choice_end_to_end(tmp_path):
    # An NPC dialogue [[choice]] ADDED to a verbatim fork: the below-band NPC's tag-3 talk body opens a menu
    # (a WindowSync prompt + a GetChoose branch) whose rows give an item / gil; the prompt + option rows +
    # replies ship on the appended-.mes channel (a [CHOO] entry). The verbatim choice wiring (was dropped).
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["npc"] = [{"name": "Quizzer", "preset": "vivi", "pos": [100, 200]}]
    project.raw["choice"] = [{"npc": "Quizzer", "prompt": "What'll it be?", "options": [
        {"text": "A Potion", "give_item": ["Potion", 1], "reply": "Here you go!"},
        {"text": "Some gil", "gil": 100, "reply": "Spend it well."},
        {"text": "Nothing"}]}]
    assert build.validate(project) == []                         # Check agrees offline
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")     # must not raise
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 1            # the choice NPC seated below the band
        tag3 = s.entry(band_lo).func_by_tag(3)
        assert tag3 is not None, "the choice NPC has a tag-3 talk body"
        ops = [i.op for i in s.instrs(tag3)]
        assert 0x1F in ops, "the choice prompt WindowSync"
        assert 0x48 in ops, "option 0 gives an item (AddItem)"
        assert 0xCE in ops, "option 1 gives gil (give_gil)"
    mes = [p for p in out.rglob("*.mes")]
    blob = "".join(p.read_text(encoding="utf-8") for p in mes)
    assert "What'll it be?" in blob and "A Potion" in blob and "Here you go!" in blob, "the choice text shipped"
    assert "[CHOO]" in blob, "the [CHOO] menu tag is in the appended choice entry"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_cutscene_conductor_end_to_end(tmp_path):
    # A MULTI-ACTOR [cutscene] conductor ADDED to a verbatim fork: a below-band DIRECTOR code entry drives two
    # additive NPCs (by their below-band uids) + the player (250) via the *Ex opcodes; say lines ship on the
    # appended-.mes channel. (Previously [cutscene] was dropped entirely on a verbatim fork.)
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["npc"] = [{"name": "lefty", "preset": "vivi", "pos": [100, 200], "dialogue": "."},
                          {"name": "righty", "preset": "vivi", "pos": [300, 200], "dialogue": "."}]
    project.raw["cutscene"] = {"once": True, "actor": ["lefty", "righty", "player"], "steps": [
        {"actor": "lefty", "walk": [800, 200]},                  # walk on a verbatim fork (a tag on lefty's below-band entry)
        {"actor": "lefty", "turn": 128},
        {"actor": "lefty", "say": "We exist on a verbatim fork."},
        {"actor": "righty", "anim": "glad"},
        {"actor": "righty", "say": "Driven by one below-band conductor."},
        {"actor": "player", "say": "Neat."}]}
    assert build.validate(project) == []                         # Check agrees offline
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")     # must not raise
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE        # lefty=band_lo, righty=band_lo+1, conductor=band_lo+2
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 3            # 2 NPCs + 1 conductor seated below the band (a walk = a TAG, not an entry)
        cond = s.entry(band_lo + 2).func_by_tag(0)               # the conductor's single director function
        assert cond is not None
        speak_uids = {i.imm(0) for i in s.instrs(cond) if i.op == 0x95}   # WindowSyncEx targets, by uid
        assert band_lo in speak_uids and 250 in speak_uids       # lefty (below-band uid) + the player speak by id
        ops = [i.op for i in s.instrs(cond)]
        assert 0x87 in ops and 0xBD in ops                       # TurnInstantEx + RunAnimationEx (drive actors by id)
        assert 0x2D in ops and 0x2E in ops                       # control lock + release
        # the walk beat: lefty's below-band entry got a walk tag (20), and the conductor RunScriptSyncs into it
        assert s.entry(band_lo).func_by_tag(20) is not None, "walk tag on lefty's below-band entry"
        runscripts = [(i.imm(0), i.imm(1), i.imm(2)) for i in s.instrs(cond) if i.op == 0x14]
        assert (2, band_lo, 20) in runscripts                    # RunScriptSync(level=2, uid=lefty, tag=20)
    blob = "".join(p.read_text(encoding="utf-8") for p in out.rglob("*.mes"))
    assert "We exist on a verbatim fork." in blob and "Neat." in blob    # say lines shipped on the appended channel


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_parallel_walk_end_to_end(tmp_path):
    # Two additive NPCs walk SIMULTANEOUSLY on a verbatim fork (the 2nd beat with_prev): each below-band entry
    # gets a walk tag (20) AND a bare-RETURN join tag (19); the below-band conductor forks BOTH async
    # (RunScriptAsync) then drains BOTH (RunScriptSync into tag 19) -- the engine's async barrier on a fork.
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["npc"] = [{"name": "lefty", "preset": "vivi", "pos": [100, 200], "dialogue": "."},
                          {"name": "righty", "preset": "vivi", "pos": [300, 200], "dialogue": "."}]
    project.raw["cutscene"] = {"once": True, "actor": ["lefty", "righty"], "steps": [
        {"actor": "lefty", "walk": [800, 200]},
        {"actor": "righty", "walk": [600, 400], "with_prev": True}]}   # righty walks together with lefty
    assert build.validate(project) == []
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")          # must not raise
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE             # lefty=band_lo, righty=band_lo+1, conductor=band_lo+2
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 3                 # 2 NPCs + 1 conductor below the band (walks = TAGS)
        for sl in (band_lo, band_lo + 1):                             # both NPC entries got a walk tag AND a join tag
            assert s.entry(sl).func_by_tag(20) is not None and s.entry(sl).func_by_tag(19) is not None
        cond = s.entry(band_lo + 2).func_by_tag(0)
        forks = sorted((i.imm(1), i.imm(2)) for i in s.instrs(cond) if i.op == 0x10)   # RunScriptAsync(level, uid, tag)
        drains = sorted((i.imm(1), i.imm(2)) for i in s.instrs(cond) if i.op == 0x14)  # RunScriptSync(level, uid, tag)
        assert forks == [(band_lo, 20), (band_lo + 1, 20)]           # both walks forked async, by below-band uid
        assert drains == [(band_lo, 19), (band_lo + 1, 19)]          # then both drained via the bare-RETURN join tag


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_player_walk_end_to_end(tmp_path):
    # The PLAYER walks in a conductor on a verbatim fork: the walk tag lands on the DONOR's player entry
    # (DefinePlayerCharacter), NOT a below-band slot, and the conductor RunScriptSyncs into uid 250.
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object, player as _player
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    pe = _player.find_player_entry(donor)
    project = build.FieldProject.load(toml)
    project.raw["npc"] = [{"name": "lefty", "preset": "vivi", "pos": [100, 200], "dialogue": "."}]
    project.raw["cutscene"] = {"once": True, "actor": ["lefty", "player"], "steps": [
        {"actor": "lefty", "say": "Come here."},
        {"actor": "player", "walk": [400, 300]}]}                    # the player walks (a tag on the donor's player entry)
    assert build.validate(project) == []
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")         # must not raise (tag 20 free on the player entry)
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE            # lefty=band_lo, conductor=band_lo+1
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry(pe).func_by_tag(20) is not None              # the walk tag is on the DONOR player entry (index unchanged)
        cond = s.entry(band_lo + 1).func_by_tag(0)
        calls = [(i.imm(0), i.imm(1), i.imm(2)) for i in s.instrs(cond) if i.op == 0x14]
        assert (2, 250, 20) in calls                                # conductor RunScriptSync(2, player=250, 20)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_conductor_exit_warp_end_to_end(tmp_path):
    # A conductor on a verbatim fork with `exit_warp`: the below-band director ENDS with a fade + Field(target)
    # (the warp-back) instead of EnableMove -- the player is warped out after the scene (the same lever the
    # forced-ATE scene uses to return the player). exit_warp sits OUTSIDE the once-gate so it always fires.
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["npc"] = [{"name": "lefty", "preset": "vivi", "pos": [100, 200], "dialogue": "."}]
    project.raw["cutscene"] = {"once": True, "actor": ["lefty"], "exit_warp": 1153,
                               "steps": [{"actor": "lefty", "say": "The scene ends -- and out you go."}]}
    assert build.validate(project) == []
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")         # must not raise
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE            # lefty=band_lo, conductor=band_lo+1
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        cond = s.entry(band_lo + 1).func_by_tag(0)
        ops = [i.op for i in s.instrs(cond)]
        assert 1153 in [i.imm(0) for i in s.instrs(cond) if i.op == 0x2B]   # ends with Field(exit_warp) -- the warp-back
        assert 0x2E not in ops                                      # NO EnableMove (the destination restores control)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_readable_prop_end_to_end(tmp_path):
    # A readable [[prop]] (dialogue=) ADDED to a verbatim fork: the below-band prop object is NON-bare -- it
    # gets a tag-3 WindowSync into the appended-.mes channel, so it reads when examined (vs silent set-dressing).
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["prop"] = [{"prop": "chest", "pos": [100, 200], "dialogue": "A weathered old chest. It won't budge."}]
    assert build.validate(project) == []                         # Check agrees offline
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")     # must not raise
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 1            # a single readable prop seated below the band
        tag3 = s.entry(band_lo).func_by_tag(3)
        assert tag3 is not None, "the readable prop has a tag-3 talk body (NOT bare set-dressing)"
        assert any(i.op == 0x1F for i in s.instrs(tag3)), "the prop's dialogue WindowSync"
    mes = [p for p in out.rglob("*.mes")]
    assert any("A weathered old chest." in p.read_text(encoding="utf-8") for p in mes), "prop dialogue shipped in .mes"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_chest_end_to_end(tmp_path):
    # A real [[chest]] on a verbatim fork: ONE object below the band with a flag-gated pose Init (the two
    # SetStandAnimation open/closed = the savable open-state), a tag-3 open handler (RunAnimation lid 7336 +
    # AddItem 0x48 + window-7 Received), and a "Received [ITEM=0]!" line appended to the .mes.
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["chest"] = [{"pos": [0, 0], "item": "Potion", "count": 1, "flag": 8520}]
    assert build.validate(project) == []
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 1
        e = s.entry(band_lo)
        poses = [i.imm(0) for i in s.instrs(e.func_by_tag(0)) if i.op == 0x33]
        assert 7338 in poses and 7339 in poses, poses              # the open/closed savable pose branch
        assert any(i.op == 0x40 and i.imm(0) == 7336 for i in s.instrs(e.func_by_tag(3))), "lid animation"
        assert any(i.op == 0x48 for i in s.instrs(e.func_by_tag(3))), "AddItem"
    mes = [p for p in out.rglob("*.mes")]
    assert mes and any("Received" in p.read_text(encoding="utf-8") for p in mes), "Received line shipped"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_prop_end_to_end(tmp_path):
    # Add a VISIBLE [[prop]] (a chest model) to a verbatim fork: build must seat the prop object below the
    # band (SetModel 0x2F present, no talk tag-3) and lint clean.
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    from ff9mapkit.content import object as _object
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["prop"] = [{"prop": "chest", "pos": [0, 0]}]
    assert build.validate(project) == []
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    band_lo = donor.entry_count - _object.PARTY_BAND_SIZE
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count == donor.entry_count + 1
        pr = s.entry(band_lo)
        assert not pr.empty and pr.func_by_tag(3) is None and any(
            i.op == 0x2F for f in pr.funcs for i in s.instrs(f)), "bare prop with a SetModel, below the band"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_event_end_to_end(tmp_path):
    # Add a NEW [[event]] chest to a verbatim fork: build must seat the event region(s) BELOW the band, give
    # the item (AddItem 0x48), and APPEND the "found" message to every language's .mes at a high txid.
    from ff9mapkit import build, extract
    from ff9mapkit.eb import EbScript
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    donor = EbScript.from_bytes(extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0"))
    project = build.FieldProject.load(toml)
    project.raw["event"] = [{"zone": [[0, 0], [100, 0], [100, 100], [0, 100]], "give_item": ["Potion", 1],
                             "message": "You found a Potion!", "once": True}]
    assert build.validate(project) == []
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        assert s.entry_count >= donor.entry_count + 2          # >=1 event region + the shared arm entry
        assert any(i.op == 0x48 for e in s.entries if not e.empty for f in e.funcs for i in s.instrs(f)), "AddItem"
    mes = [p for p in out.rglob("*.mes")]
    assert mes and any("You found a Potion!" in p.read_text(encoding="utf-8") for p in mes), "event .mes shipped"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_build_field_verbatim_with_show_line_end_to_end(tmp_path):
    # Phase 4b show_line: a [[logic_add]] that SHOWS a line must (1) build clean, (2) ship a WindowSync into
    # the verbatim .eb at a txid ABOVE the donor text, and (3) APPEND that line to every language's .mes at
    # the same txid -- the give_item "Received..." gap closed via the [[on_entry]]-style .mes channel.
    from ff9mapkit import build, extract, dialogue
    from ff9mapkit.eb import EbScript
    _meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    project = build.FieldProject.load(toml)
    project.raw["logic_add"] = [{"kind": "give_item", "entry": 0, "tag": 0, "item": "Potion",
                                 "message": "SHOW LINE TEST!"}]
    assert build.validate(project) == []                        # Check agrees offline (incl. the txid plan)
    out = tmp_path / "mod"
    build.build_mod([project], out, mod_name="FF9CustomMap")     # must not raise
    # the shipped .eb has a WindowSync (0x1F) to a high (appended) txid, and gives the Potion (0x48)
    ebs = [p for p in out.rglob("*.eb.bytes")]
    assert ebs
    win_txids = set()
    for p in ebs:
        s = EbScript.from_bytes(p.read_bytes())
        for e in s.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for i in s.instrs(f):
                    if i.op == 0x1F and i.imm(2) is not None and i.imm(2) >= 1000:
                        win_txids.add(i.imm(2))
    assert win_txids, "the show_line WindowSync was injected at an appended txid"
    # the appended .mes line is present at that txid in the shipped text
    mes = [p for p in out.rglob("*.mes")]
    assert mes
    hit = False
    for p in mes:
        parsed = dialogue.parse_mes(p.read_text(encoding="utf-8"))
        for t in win_txids:
            if t in parsed and "SHOW LINE TEST!" in parsed[t].text:
                hit = True
    assert hit, "the show_line text shipped in the .mes at the WindowSync's txid"


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_chain_verbatim_wires_a_connected_slice(tmp_path):
    # import-chain --verbatim forks a CONNECTED slice: every member ships its donor's WHOLE .eb (run as-is),
    # with the IN-CHAIN Field() exits retargeted to sibling forks + each member's donor .mes at the donor's
    # OWN registered textid (EVENT_ID_TO_MES -- a valid MesDB key). A 2-field slice: the Dali Inn (FieldScene
    # id 351) -> the Dali Wheel (350, one of its real exits). The inn's Field(350) must point at the wheel's
    # NEW id; the inn's out-of-chain exits stay live seams; both get the donor's registered textid.
    from collections import OrderedDict

    from ff9mapkit import build, campaign
    from ff9mapkit.chain import WALK_IN, GraphResult
    from ff9mapkit._fieldtext import EVENT_ID_TO_MES

    INN, WHEEL = 351, 350                                      # FieldScene ids (ID_TO_FBG keys), not event ids
    nodes = OrderedDict()
    nodes[INN] = {"zone": "vgdl", "found": True, "hop": 0, "overworld_exits": [], "encounter": None,
                  "music": None, "edges": [{"to": WHEEL, "kind": WALK_IN, "entrance": 0,
                                            "zone": [(0, 0), (1, 0), (1, 1), (0, 1)], "story_conditional": False}]}
    nodes[WHEEL] = {"zone": "vgdl", "found": True, "hop": 1, "overworld_exits": [], "encounter": None,
                    "music": None, "edges": []}
    result = GraphResult(nodes=nodes, portals=[], seams=[], unforkable=[], seeds=[INN],
                         allowed_zones={"vgdl"}, truncated=False, remaining=0,
                         bounds={"max_hops": 20, "max_fields": 25, "zones": ["vgdl"],
                                 "follow_scripted": False, "stop_at_zone_boundary": True})

    plan = campaign.write_campaign(result, tmp_path, id_base=6000, name="DALI", mod_folder="FF9CustomMap-ow",
                                   verbatim=True)
    by_real = {m.real_id: m for m in plan.members}
    inn, wheel = by_real[INN], by_real[WHEEL]
    assert inn.new_id == 6000 and wheel.new_id == 6001 and inn.mode == "native"

    # each member is a verbatim fork at its donor's OWN registered textid (a valid MesDB key, so the
    # FieldScene line registers). Same-zone members share it -- and ship IDENTICAL zone text, so no clobber.
    inn_proj = build.FieldProject.load(tmp_path / inn.toml_rel)
    wheel_proj = build.FieldProject.load(tmp_path / wheel.toml_rel)
    assert "verbatim_eb" in inn_proj.raw and "verbatim_eb" in wheel_proj.raw
    assert inn_proj.text_block == EVENT_ID_TO_MES[INN]         # the donor's own registered textid, not 1073
    assert wheel_proj.text_block == EVENT_ID_TO_MES[WHEEL]
    if inn_proj.text_block == wheel_proj.text_block:           # same zone -> the shipped .mes must be identical
        assert (_vb.verbatim_mes(inn_proj, "us") == _vb.verbatim_mes(wheel_proj, "us"))

    # the LIVE retarget: the inn's in-chain exits (Field(350)->wheel, Field(351)->itself) point at the forks;
    # its OUT-of-chain exits stay live seams back into the real game.
    inn_eb = _vb.verbatim_eb(inn_proj)
    rt = inn_proj.raw["verbatim_eb"]["retarget"]              # TOML inline-table keys are strings
    assert {int(k): int(v) for k, v in rt.items()} == {WHEEL: 6001, INN: 6000}
    assert 6001 in _fields(inn_eb) and 6000 in _fields(inn_eb)
    assert WHEEL not in _fields(inn_eb) and INN not in _fields(inn_eb)
    for seam in (352, 450):                                    # out-of-chain exits untouched (warp to live game)
        assert seam in _fields(inn_eb)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_chain_swap_player_swaps_every_member(tmp_path):
    # import-chain --swap-player: every verbatim member's controlled player rig is swapped to the chosen
    # character, so you play as that character across the whole chain; plan.swap_player records it.
    from collections import OrderedDict

    from ff9mapkit import build, campaign, eventscan
    from ff9mapkit.chain import GraphResult

    INN = 351
    nodes = OrderedDict()
    nodes[INN] = {"zone": "vgdl", "found": True, "hop": 0, "overworld_exits": [], "encounter": None,
                  "music": None, "edges": []}
    result = GraphResult(nodes=nodes, portals=[], seams=[], unforkable=[], seeds=[INN],
                         allowed_zones={"vgdl"}, truncated=False, remaining=0,
                         bounds={"max_hops": 20, "max_fields": 25, "zones": ["vgdl"],
                                 "follow_scripted": False, "stop_at_zone_boundary": True})
    plan = campaign.write_campaign(result, tmp_path, id_base=6000, name="DALI", mod_folder="FF9CustomMap-ow",
                                   verbatim=True, swap_player="steiner")
    assert plan.swap_player == "steiner"
    proj = build.FieldProject.load(tmp_path / plan.members[0].toml_rel)
    es = EbScript.from_bytes(_vb.verbatim_eb(proj))
    models = [eventscan._player_model(es, p) for p in eventscan.resolve_player_entries(es)]
    assert 5489 in models                                      # Steiner (model 5489) now among the player entries


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_native_fork_carries_donor_sps_assets(tmp_path):
    # A field's SPS effect bins (.sps) + texture (spt.tcb) load by the RUNNING scene name, so a fork (custom
    # scene name) must ship the donor's under its OWN FBG folder -- else RunSPSCode finds no bin and the effect
    # (fire/smoke/magic) never draws (the forked Ice Cavern lost Vivi's melt-fire until we carried these).
    from ff9mapkit import build, extract
    # Ice Cavern "ic_jmp" (field 303): its melt cutscene loads the fire SPS 2266-2269.
    meta, toml = extract.write_native_project("fbg_n05_iccv_map088_ic_jmp_0", tmp_path / "m", name="ICJ", verbatim=True)
    fire = {"2266.sps.bytes", "2267.sps.bytes", "2268.sps.bytes", "2269.sps.bytes"}
    assert meta["sps"] > 0
    staged = {p.name for p in (tmp_path / "m" / "sps").iterdir()}
    assert "spt.tcb.bytes" in staged and fire <= staged        # the importer stages the donor's SPS sidecar
    out = tmp_path / "mod"
    build.build_mod([build.FieldProject.load(toml)], out)       # ...and the build copies it into the FBG folder
    fbg = next(p for p in out.rglob("FieldMaps/*") if p.is_dir() and "ICJ" in p.name)
    shipped = {p.name for p in fbg.iterdir()}
    assert "spt.tcb.bytes" in shipped and fire <= shipped
