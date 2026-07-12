"""The baked per-model NPC object-params catalog (_npcparams.NPC_PARAMS) + its wiring into the
from-scratch NPC synthesizer -- so non-moogle NPCs get their REAL animset / head-focus / size / clips,
not just safe defaults."""
from __future__ import annotations

from ff9mapkit import catalog, data
from ff9mapkit._npcparams import NPC_PARAMS
from ff9mapkit.content import npc as N
from ff9mapkit.eb import EbScript


def test_catalog_shape_and_moogle_values():
    assert len(NPC_PARAMS) > 100                              # a real census, not a stub
    for m, p in NPC_PARAMS.items():                           # every entry is complete
        assert set(p) == {"animset", "head_focus", "logical_size", "anims"}
        assert set(p["anims"]) == {"stand", "walk", "run", "left", "right"}
        assert len(p["head_focus"]) == 2 and len(p["logical_size"]) == 3
    # the confirmed moogle set (head-ONLY focus); a human rig differs -- the fidelity the catalog adds
    assert NPC_PARAMS[212]["head_focus"] == (4, 1) and NPC_PARAMS[212]["animset"] == 50
    assert NPC_PARAMS[220]["head_focus"] == (4, 1)
    assert NPC_PARAMS[49]["animset"] != 50                    # a Dali human, not the moogle animset


def test_object_params_prefer_catalog_then_defaults():
    assert N._npc_object_params(212, None) == (50, (4, 1), (14, 14, 22))
    av, hf, ls = N._npc_object_params(49, None)               # a human sources its real values
    assert (av, hf, ls) == (NPC_PARAMS[49]["animset"], NPC_PARAMS[49]["head_focus"], NPC_PARAMS[49]["logical_size"])
    assert N._npc_object_params(212, 77)[0] == 77             # an explicit animset still wins
    assert N._npc_object_params(999999, None) == (50, (0, 65), (14, 14, 22))   # off-catalog -> defaults


def test_npc_anims_real_clips_vs_byname_guard():
    got = catalog.npc_anims(212)                                  # Stiltzkin: an F3-MOG rig
    assert {s: catalog.animation_name(v) for s, v in got.items()} == \
        {s: catalog.animation_name(v) for s, v in NPC_PARAMS[212]["anims"].items()}  # his real F3 clips
    assert got["stand"] == 1152                                   # ANH_NPC_F3_MOG_IDLE, canonical row
    assert got != catalog.npc_anims(212, use_catalog=False)       # by-name would pick the F0 moogle set
    # vivi (GEO_MAIN, off-catalog) is identical either way -- its preset is by-name
    assert catalog.npc_anims("GEO_MAIN_F0_VIV") == catalog.npc_anims("GEO_MAIN_F0_VIV", use_catalog=False)


def test_npc_anims_tmm_resolves_to_its_own_clips():
    """GEO_NPC_F0_TMM (124): the baked modal stand was 706 -- a duplicate-row id of the model's own
    idle 654 (both name ANH_NPC_F0_TMM_IDLE). The duplicate id rendered the NPC unposed/INVISIBLE on a
    synthesized field (the stolen-ember innkeeper, in-game 2026-07-12); the resolve must pin to the
    model's own clip list (what ``ff9mapkit models GEO_NPC_F0_TMM`` prints)."""
    want = {"stand": 654, "walk": 655, "run": 657, "left": 17, "right": 16}
    assert catalog.npc_anims(124) == want
    assert catalog.npc_anims("GEO_NPC_F0_TMM") == want


def test_npc_anims_every_resolved_id_is_an_own_canonical_clip():
    """The own-clip law: every auto-resolved slot id names a clip of the model's OWN (group, token)
    family and is that name's CANONICAL row (the lowest duplicate-row alias -- the id ``ff9mapkit
    models`` lists). Exempt slots: where a rig has NO own form of a movement gesture it keeps the real
    observed donor clip verbatim (the frog rigs FRC/FRF play only FRM clips; MON FFF stands on EFM's
    idle -- their own families have only b/p/cut clips)."""
    slots = ("stand", "walk", "run", "left", "right")
    keep_baked = {(174, s) for s in slots} | {(175, s) for s in slots} | {(530, "stand")}
    for mid in NPC_PARAMS:
        got = catalog.npc_anims(mid)
        assert set(got) == set(slots), mid
        m = catalog.model(mid)
        for slot, aid in got.items():
            if (mid, slot) in keep_baked:
                assert aid == NPC_PARAMS[mid]["anims"][slot], (mid, slot)   # kept verbatim, documented
                continue
            nm = catalog.animation_name(aid)
            grp, _form, tok, _act = catalog._split_anh(nm)
            assert (grp, tok) == (m.group, m.token), (mid, slot, aid, nm)
            assert aid == min(catalog.animation_aliases(aid)), (mid, slot, aid, nm)
            # same-NAME repair only: the canonical id still plays the exact clip the real bake observed
            assert nm == catalog.animation_name(NPC_PARAMS[mid]["anims"][slot]) or \
                aid in catalog.animations_for_model(mid).values(), (mid, slot)


def test_synthesized_human_npc_uses_catalog_params():
    blank = data.blank_field_bytes("us")
    out = N.inject_npc(blank, 100, 200, model=49)            # a human rig, no explicit animset/anims
    eb = EbScript.from_bytes(out)
    e = max(idx for idx in (x.index for x in eb.entries if not x.empty))
    f0 = eb.entry(e).func_by_tag(0)
    model, animset = next(i.args for i in eb.instrs(f0) if i.op == 0x2F)
    hf = list(next(i.args for i in eb.instrs(f0) if i.op == 0x8B))
    assert [model, animset] == [49, NPC_PARAMS[49]["animset"]]
    assert hf == list(NPC_PARAMS[49]["head_focus"])


def _count_stale_sound(ebb):
    eb = EbScript.from_bytes(ebb)
    f0 = eb.entry(N._find_player_entry(eb)).func_by_tag(0)
    return sum(1 for i in eb.instrs(f0) if i.op == 0xC5 and tuple(i.args or ()) == (4616, 912))


def test_neutralize_player_audio_cruft_in_place():
    blank = data.blank_field_bytes("us")
    assert _count_stale_sound(blank) > 0                     # the blank template carries the stale preload
    out = N.neutralize_player_audio_cruft(blank)
    assert len(out) == len(blank)                            # in-place (same length)
    assert EbScript.from_bytes(out).to_bytes() == out        # still valid
    assert _count_stale_sound(out) == 0                      # the 'Music Id 912' spam ops are gone


def test_built_synthesized_field_player_has_no_stale_sound(tmp_path):
    # build_script neutralizes it, so EVERY synthesized field ships a clean player (no per-frame 912 lag)
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n', encoding="utf-8")
    eb = build.build_script(build.FieldProject.load(p), "us", {})
    assert _count_stale_sound(eb) == 0
