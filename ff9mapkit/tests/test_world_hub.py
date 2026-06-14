"""World Hub scaffold: the choice `warp` action, `[player] model=` (the Moogle PC), and their
composition. Pure tests run against the provenance-clean blank field; the end-to-end example build is
install-gated (it BG-borrows real fields)."""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import catalog, data
from ff9mapkit.content import choice, event, npc, startup
from ff9mapkit.eb import opcodes
from ff9mapkit.eb.model import EbScript

EXAMPLES = Path(__file__).parent.parent / "examples" / "world_hub"


def _game_ready():
    try:
        from ff9mapkit.extract import EventBundle
        EventBundle()
        return True
    except Exception:
        return False


# ---- the warp action (the journey-pick primitive) ----
def test_event_warp_is_transition_sound_plus_field():
    # grounded in real talk-handler warps: RunSoundCode(265,65535) (the whoosh in every real warp) + Field(t)
    assert event.warp(4501) == opcodes.run_sound_code(265, 65535) + opcodes.field(4501)
    # the Field op carries the target as a 2-byte immediate -> the warp encodes the destination id
    assert event.warp(4501).endswith(opcodes.field(4501))


def test_event_set_scenario_reuses_startup_lever():
    assert event.set_scenario(2600) == startup.startup_body([], scenario=2600)


def test_choice_option_warp_is_last_and_after_seed():
    # a journey row: seed the beat (set_scenario) THEN warp (warp must be last -- Field transitions away).
    # The choice-warp FADES OUT first (fade=True) so the destination doesn't load in the clear (static-screen
    # fix), so the warp tail == event.warp(.., fade=True), not the bare warp.
    out = choice.option_body({"text": "Dali", "set_scenario": 2600, "warp": 4501})
    assert out == event.set_scenario(2600) + event.warp(4501, fade=True)
    assert out.endswith(event.warp(4501, fade=True))            # faded warp is the final action
    # warp also sits after the existing vocabulary (set_flag before warp)
    out2 = choice.option_body({"text": "x", "set_flag": [8500, 1], "warp": 4502})
    assert out2 == event.set_flag(8500, 1) + event.warp(4502, fade=True)


def test_choice_option_byte_identical_without_warp():
    # a plain option (no warp/set_scenario) is byte-for-byte what it was before the hub feature
    opt = {"give_item": [232, 1], "gil": 50, "set_flag": [8000, 1]}
    assert choice.option_body(opt, reply_txid=501) == (
        event.message(501) + event.give_item(232, 1) + event.give_gil(50) + event.set_flag(8000, 1))
    assert choice.option_body({"text": "Stay here"}) == b""      # the cancel/no-op row emits nothing


# ---- [player] model= : the Moogle (and any-model) PC on a synthesized field ----
def test_set_player_model_reskins_blank_player_keeping_dpc():
    blank = data.blank_field_bytes("us")
    anims = catalog.npc_anims(220)                               # the moogle's movement clips
    out = npc.set_player_model(blank, 220, anims)
    assert len(out) == len(blank)                                # in-place (same width) -> fpos table intact
    eb = EbScript.from_bytes(out)
    pe = npc._find_player_entry(eb)                              # STILL a player (DefinePlayerCharacter kept)
    f0, _b, loc = npc._func0_locations(eb, eb.entry(pe))
    model = int.from_bytes(out[f0.abs_start + loc["model"]:f0.abs_start + loc["model"] + 2], "little")
    assert model == 220
    # the first movement clip (stand) became the moogle's
    stand = int.from_bytes(out[f0.abs_start + loc["stand"]:f0.abs_start + loc["stand"] + 2], "little")
    assert stand == anims["stand"]


def test_set_player_model_resolves_moogle_anims():
    # the model->animation join gives the moogle its own movement clips (Info Hub catalog)
    anims = catalog.npc_anims(220)
    assert anims and {"stand", "walk", "run", "left", "right"} <= set(anims)


def test_moogle_model_id_is_220():
    # the hub PC model id is stable (GEO_NPC_F0_MOG); resolvable by GEO name + numeric id
    assert catalog.resolve_model("GEO_NPC_F0_MOG") == 220
    assert catalog.resolve_model(220) == 220


# ---- validate: a bad warp / set_scenario is a clear build error ----
def test_validate_rejects_bad_warp_and_scenario(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad.field.toml"
    p.write_text(
        '[field]\nid=4500\nname="H"\nborrow_bg="GRGR_MAP420_GR_CEN_0"\narea=21\ntext_block=1073\n'
        '[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n'
        '[[npc]]\nname="G"\npos=[10,10]\n'
        '[[choice]]\nnpc="G"\nprompt="?"\n'
        '[[choice.options]]\ntext="a"\nwarp="nope"\n'
        '[[choice.options]]\ntext="b"\nset_scenario=99999\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    probs = build.validate(proj)
    assert any("warp" in s and "field id" in s for s in probs)
    assert any("set_scenario" in s for s in probs)


# ---- install-gated: the example builds, with the Moogle PC + the journey warps ----
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_hub_example_builds_with_moogle_pc_and_journey_warps(tmp_path):
    import shutil
    from ff9mapkit import build, extract
    # extract the borrowed camera the example references (gitignored; supplied from the install)
    src = EXAMPLES / "camera_hub.bgx"
    cleanup = False
    if not src.exists():
        t = tmp_path / "cam"
        extract.extract_field("950", t)
        shutil.copyfile(t / "camera.bgx", src)
        cleanup = True
    try:
        proj = build.FieldProject.load(EXAMPLES / "hub.field.toml")
        assert build.validate(proj) == []
        out = tmp_path / "mod"
        build.build_mod([proj], out)
        eb_path = next(p for p in out.rglob("*") if p.name == "EVT_WORLD_HUB.eb.bytes")
        ebb = eb_path.read_bytes()
        eb = EbScript.from_bytes(ebb)
        # the Moogle PC
        pe = npc._find_player_entry(eb)
        f0, _b, loc = npc._func0_locations(eb, eb.entry(pe))
        assert int.from_bytes(ebb[f0.abs_start + loc["model"]:f0.abs_start + loc["model"] + 2], "little") == 220
        # the narrator menu warps to both REAL verbatim destinations (Dali 4100, Treno Pub 4501)
        warps = sorted({i.imm(0) for e in eb.entries if not e.empty and e.func_by_tag(3)
                        for i in eb.instrs(e.func_by_tag(3)) if i.op == 0x2B and i.imm(0) is not None})
        assert warps == [4100, 4501]
    finally:
        if cleanup and src.exists():
            src.unlink()
