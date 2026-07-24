"""``[[summon]] staging = "curves"`` + the AUTHORED-cast lane (rung-8 kit items K1-K4).

Everything here is PURE LOGIC -- no install, no stock bytes, no donor. That is the point of the lane:
an ORIGINAL summon reads nothing from the game, so its whole emit path is testable offline, including
the end-to-end deploy (which the transplant lane can only test install-gated).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ff9mapkit.content import summon as CS
from ff9mapkit.summons import deploy as D

_STUDY = Path(__file__).resolve().parents[2] / "studies" / "custom-summons" / "rung8-epic"


# --------------------------------------------------------------------------- fixtures

_SEQ = (
    "PlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True\n"
    "SetBackgroundIntensity: Intensity=0 ; Time=12\n"
    "LoadSFX: SFX=91 ; Char=Caster ; UseCamera=False\n"
    "WaitSFXLoaded: SFX=91\n"
    "PlaySFX: SFX=91 ; SkipSequence=True\n"
    "Wait: Time=30\n"
    "CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/Puff.sfxmodel\n"
    "SetBackgroundIntensity: Intensity=1 ; Time=12\n"
    "Wait: Time=24\n"
    "EffectPoint: Char=Everyone ; Type=Figure\n"
    "WaitSFXDone: SFX=91\n"
    "PlayAnimation: Char=Caster ; Anim=Idle\n"
)

_SPRITE = json.dumps({
    "MinimalDuration": "0",
    "Sprite": [{
        "Material": {"TextureKind": "0", "Shader": "SFX_ADD_G"},
        "Vertices": ["(10, 0, 0)", "(0, 10, 0)", "(-10, 0, 0)"],
        "Indices": ["0", "1", "2"],
        "Duration": "20",
        "Emission": [{"Frame": ["0"], "Count": "1"}],
    }],
})


def _anim_json(frames: int, fps: float = 30.0) -> str:
    last = (frames - 1) / fps
    return json.dumps({"name": "c", "frameRate": fps, "transform": [{
        "bone": "bone000",
        "localRotation": [{"time": 0.0, "x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                          {"time": last, "x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}]}]})


def _staging(**over) -> dict:
    st = {
        "anchor": "target_average", "start": 0, "end": 90,
        "move": [{"duration": 30, "from": [0, -900, 0], "to": [0, 120, 0],
                  "ease": ["Linear", "SinusOut", "Linear"]},
                 {"duration": 60, "to": [0, 190, 0], "ease": ["Linear", "Sinus", "Linear"]}],
        "turn": [{"duration": 90, "from": [0, 180, 180], "to": [0, 180, 180]}],
        "scale": [{"duration": 90, "from": 0.15, "to": 1.0,
                   "ease": ["SinusOut", "SinusOut", "SinusOut"]}],
        "play": [{"clip": "emerge", "speed": 2}, {"clip": "drift", "speed": 1, "repeat": 2}],
    }
    st.update(over)
    return st


@pytest.fixture
def inputs(tmp_path) -> dict:
    """A complete authored input set on disc (sequence + 2 clips + 1 particle + a model stub)."""
    (tmp_path / "cast.seq").write_text(_SEQ, encoding="utf-8", newline="\n")
    (tmp_path / "Puff.sfxmodel").write_text(_SPRITE, encoding="utf-8", newline="\n")
    (tmp_path / "emerge.anim").write_text(_anim_json(90), encoding="utf-8", newline="\n")
    (tmp_path / "drift.anim").write_text(_anim_json(30), encoding="utf-8", newline="\n")
    (tmp_path / "model.fbx").write_text("; stub fbx referencing tex.png\n", encoding="utf-8", newline="\n")
    (tmp_path / "tex.png").write_bytes(b"\x89PNG\r\n\x1a\nstub")
    return {
        "lane": "overlay", "model": str(tmp_path / "model.fbx"), "id": 6400,
        "name": "GEO_MON_B0_M400", "private_ef": 91,
        "sequence": str(tmp_path / "cast.seq"),
        "manifest": "nimbra_manifest.sfxmodel",
        "clips": [str(tmp_path / "emerge.anim"), str(tmp_path / "drift.anim")],
        "particles": [str(tmp_path / "Puff.sfxmodel")],
        # 90/2 = 45 + 30/1 x2 = 60  ->  105 ticks >= the 90-tick window
        "staging": _staging(),
    }


# --------------------------------------------------------------------------- the staging schema

def test_staging_table_selects_curves_mode_and_the_string_form_still_works():
    assert D._norm_staging({"anchor": "caster"}) == ("curves", {"anchor": "caster"})
    assert D._norm_staging("donor") == ("donor", None)
    assert D._norm_staging("curves") == ("curves", None)
    with pytest.raises(D.SummonDeployError, match="staging must be"):
        D._norm_staging("nope")


def test_curves_string_without_a_table_is_refused_with_the_fix():
    with pytest.raises(D.SummonDeployError, match=r"needs an authored \[summon.staging\] table"):
        D.normalize_spec({"donor": 227, "staging": "curves"})


def test_default_staging_is_donor_and_leaves_the_manifest_at_the_world_origin_stub():
    spec = D.normalize_spec({"donor": 227})
    assert spec["staging"] == "donor" and spec["staging_curves"] is None
    spec.update(id=6400, name="GEO_MON_B0_M400")
    man = D._sfxmodel_manifest(spec, [0])["FBX"][0]
    assert man["End"] == "0" and man["Movement"][0]["DestinationY"] == "0"


def test_curve_durations_must_span_the_window():
    with pytest.raises(D.SummonDeployError, match=r"durations sum to 89 but end - start = 90"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"],
                          "staging": _staging(turn=[{"duration": 89, "from": [0, 0, 0], "to": [0, 0, 0]}])})


def test_bad_ease_name_is_refused_because_the_engine_falls_back_to_constant_silently():
    with pytest.raises(D.SummonDeployError, match="TryParseInterpolateType"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": _staging(
            turn=[{"duration": 90, "from": [0, 0, 0], "to": [0, 0, 0], "ease": ["EaseOut", "L", "L"]}])})


def test_anchor_target_is_refused_with_the_multi_target_null():
    with pytest.raises(D.SummonDeployError, match="NULL target into SetupPositions"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": _staging(anchor="target")})


def test_unknown_anchor_is_refused():
    with pytest.raises(D.SummonDeployError, match="anchor must be one of"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": _staging(anchor="enemy")})


def test_first_curve_piece_must_carry_a_from():
    with pytest.raises(D.SummonDeployError, match="no previous destination to inherit"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"],
                          "staging": _staging(turn=[{"duration": 90, "to": [0, 0, 0]}])})


def test_play_clip_must_name_an_authored_clip():
    with pytest.raises(D.SummonDeployError, match="is not one of the block's authored clips"):
        D.normalize_spec({"donor": 227, "clips": ["emerge.anim"],
                          "staging": _staging(play=[{"clip": "nope"}])})


def test_play_speed_must_be_positive():
    with pytest.raises(D.SummonDeployError, match="speed must be > 0"):
        D.normalize_spec({"donor": 227, "clips": ["emerge.anim", "drift.anim"],
                          "staging": _staging(play=[{"clip": "emerge", "speed": 0}])})


# --------------------------------------------------------------------------- unknown-key hygiene (Finding 4)

def test_unknown_key_in_the_staging_table_is_refused():
    st = _staging()
    st["bogus"] = 1
    with pytest.raises(D.SummonDeployError, match=r"\[summon\.staging\] has unknown key"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": st})


def test_unknown_key_in_a_curve_piece_is_refused():
    st = _staging()
    st["move"][0]["bogus"] = 1
    with pytest.raises(D.SummonDeployError, match=r"\[\[summon\.staging\.move\]\] #0 has unknown key"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": st})


def test_unknown_key_in_a_play_row_is_refused():
    st = _staging()
    st["play"][0]["bogus"] = 1
    with pytest.raises(D.SummonDeployError, match=r"\[\[summon\.staging\.play\]\] #0 has unknown key"):
        D.normalize_spec({"donor": 227, "clips": ["emerge.anim", "drift.anim"], "staging": st})


# --------------------------------------------------------------------------- `end` is required (Finding 5)

def test_omitted_end_disables_the_duration_sum_invariant_so_it_is_refused():
    """Both `start` and `end` silently default to 0, which makes `span = end - start` also 0 -- and the
    duration-sum invariant is gated `if span and total != span`, so a falsy span (the omission default)
    SILENTLY SKIPS the check it exists to run. `end` must be explicit."""
    st = _staging()
    del st["end"]
    with pytest.raises(D.SummonDeployError, match=r"needs an explicit `end`"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": st})


def test_explicit_end_zero_is_accepted_only_the_omission_is_refused():
    """The engine's own auto-derive route (SFXDataMesh.cs:803-808, Start==End) needs `end = 0` to be
    WRITABLE -- the fix must refuse the omission, not the value."""
    st = {"anchor": "target_average", "start": 0, "end": 0,
          "move": [{"duration": 0, "from": [0, 0, 0], "to": [0, 0, 0]}],
          "turn": [{"duration": 0, "from": [0, 0, 0], "to": [0, 0, 0]}]}
    spec = D.normalize_spec({"donor": 227, "staging": st})           # must NOT raise
    assert spec["staging"] == "curves" and spec["staging_curves"]["end"] == 0


# --------------------------------------------------------------------------- clip discrimination (K2)

@pytest.mark.parametrize("clips,expect", [
    ("all", None), ("none", None), ("0 1", None),                 # donor selectors
    ([0, 1], None), (["0", "2"], None),                           # donor INDEX lists
    (["a/emerge.anim"], ["a/emerge.anim"]),                       # authored paths
])
def test_authored_clip_paths_discriminates_by_content_not_a_flag(clips, expect):
    assert D.authored_clip_paths(clips) == expect


def test_a_numeric_clip_stem_pins_its_own_key():
    """An upstream clip author may pin the on-disc key by NAMING the file it: ``0.anim`` -> key 0. The
    kit writes both the file and the manifest entry from clip_key_of, so the two can never disagree."""
    names = D.clip_name_map(["x/0.anim", "x/emerge.anim"])
    assert names["0"] == 0                                        # taken at its word
    assert names["emerge"] == D.AUTHORED_CLIP_KEY_BASE + 1         # positional, unaffected


def test_authored_clip_keys_are_in_the_mint_band_and_map_by_stem():
    names = D.clip_name_map(["x/emerge.anim", "x/drift.anim"])
    assert names["emerge"] == D.AUTHORED_CLIP_KEY_BASE
    assert names["drift"] == D.AUTHORED_CLIP_KEY_BASE + 1
    assert names[str(D.AUTHORED_CLIP_KEY_BASE)] == D.AUTHORED_CLIP_KEY_BASE   # numeric form also accepted
    assert D.AUTHORED_CLIP_KEY_BASE > 14739                                   # clear of every stock key


# --------------------------------------------------------------------------- clip aliasing collisions (Finding 7)

def test_clip_name_map_refuses_two_clips_with_the_same_stem():
    """Two authored clips sharing a file NAME but different (positional) keys: `out[stem] = key` is a
    plain dict assignment, so the second entry would silently REPLACE the first in the name map, and a
    `play.clip = "emerge"` row could then only ever reach the second clip."""
    with pytest.raises(D.SummonDeployError, match="both named 'emerge'"):
        D.clip_name_map(["a/emerge.anim", "b/emerge.anim"])


def test_clip_name_map_refuses_a_numeric_stem_colliding_with_a_minted_key():
    """An explicit pinned key (a numeric stem) landing on the same key an auto-derived stem resolves to:
    both `_stage_authored_clips` and the manifest are keyed by that number, so the second clip's write
    would silently overwrite the first clip's .anim file on disc with no error anywhere."""
    # index0 "60001.anim" pins key 60001; index1's auto-derived key is BASE(60000) + 1 == 60001 too.
    with pytest.raises(D.SummonDeployError, match=r"both resolve to \.anim key 60001"):
        D.clip_name_map(["a/60001.anim", "b/emerge.anim"])


def test_clip_name_map_accepts_distinct_stems_and_distinct_pinned_keys():
    """Not every numeric-stem-plus-authored-clip combination collides -- only an actual overlap does."""
    names = D.clip_name_map(["a/0.anim", "b/emerge.anim", "c/drift.anim"])
    assert names["0"] == 0 and names["emerge"] == D.AUTHORED_CLIP_KEY_BASE + 1
    assert names["drift"] == D.AUTHORED_CLIP_KEY_BASE + 2


# --------------------------------------------------------------------------- the emitted manifest (K4)

def test_staging_curves_json_anchors_movement_and_leaves_rotation_absolute():
    spec = D.normalize_spec({"donor": 227, "id": 6400, "name": "GEO_MON_B0_M400",
                             "clips": ["a/emerge.anim", "a/drift.anim"], "staging": _staging()})
    out = D.staging_curves_json(spec)
    m0, m1 = out["Movement"]
    assert m0["OriginY"] == "TargetAveragePositionY - 900"
    assert m0["OriginX"] == "TargetAveragePositionX"              # a zero offset emits the bare anchor
    assert m0["DestinationY"] == "TargetAveragePositionY + 120"
    # THE INHERITANCE RULE: a piece with no `from` emits NO Origin* keys, so ParametricMovement.cs:88-105
    # chains by EXPRESSION REFERENCE. Re-emitting them would double-evaluate the NCalc.
    assert not any(k.startswith("Origin") for k in m1)
    assert out["Rotation"][0]["OriginY"] == "180"                 # absolute euler, not anchored
    assert out["Scaling"][0]["OriginX"] == "0.15"                 # a scalar `from` fans out to all axes


def test_staging_playlist_expands_repeat_and_omits_speed_1():
    spec = D.normalize_spec({"donor": 227, "id": 6400, "name": "GEO_MON_B0_M400",
                             "clips": ["a/emerge.anim", "a/drift.anim"], "staging": _staging()})
    play = D.staging_curves_json(spec)["Animations"]
    assert [p["Path"] for p in play] == ["Animations/6400/60000", "Animations/6400/60001",
                                         "Animations/6400/60001"]
    assert play[0]["Speed"] == "2" and "Speed" not in play[1]


def test_anchor_world_emits_bare_numbers():
    spec = D.normalize_spec({"donor": 227, "id": 6400, "name": "GEO_MON_B0_M400",
                             "clips": ["a/emerge.anim", "a/drift.anim"],
                             "staging": _staging(anchor="world")})
    assert D.staging_curves_json(spec)["Movement"][0]["OriginY"] == "-900"


# --------------------------------------------------------------------------- playlist coverage

def test_anim_frame_count_is_derived_from_the_key_times(tmp_path):
    p = tmp_path / "c.anim"
    p.write_text(_anim_json(90), encoding="utf-8")
    assert D.anim_frame_count(p) == 90
    p.write_text("not json", encoding="utf-8")
    assert D.anim_frame_count(p) is None


def test_a_short_playlist_is_refused_with_the_freeze_explained(inputs, tmp_path):
    inputs["staging"] = _staging(end=200)          # 105 playlist ticks vs a 200-tick window
    inputs["staging"]["move"][1]["duration"] = 170
    inputs["staging"]["turn"][0]["duration"] = 200
    inputs["staging"]["scale"][0]["duration"] = 200
    with pytest.raises(D.SummonDeployError, match="THE ANIMATION-PLAYLIST LAW"):
        D.emit_overlay(inputs, tmp_path / "mod", None)


# --------------------------------------------------------------------------- preflight folding (Finding 6)
# Both checks used to fire at their write site -- the seq lint inside _stage_host_seq (after _stage_model
# had already written the mint) and the coverage check inside _stage_overlay_extras_authored (after BOTH
# the mint and the host .seq were written). Folded into _preflight_inputs, so now nothing lands on disc.

def test_preflight_catches_a_bad_sequence_lint_before_any_write(inputs, tmp_path):
    Path(inputs["sequence"]).write_text(_SEQ + "PlayCamera: Camera=3\n", encoding="utf-8", newline="\n")
    mod = tmp_path / "mod"
    with pytest.raises(D.SummonDeployError, match="does not lint"):
        D.emit_overlay(inputs, mod, None)
    assert not mod.exists()


def test_preflight_catches_a_short_playlist_before_any_write(inputs, tmp_path):
    inputs["staging"] = _staging(end=200)          # 105 playlist ticks vs a 200-tick window
    inputs["staging"]["move"][1]["duration"] = 170
    inputs["staging"]["turn"][0]["duration"] = 200
    inputs["staging"]["scale"][0]["duration"] = 200
    mod = tmp_path / "mod"
    with pytest.raises(D.SummonDeployError, match="THE ANIMATION-PLAYLIST LAW"):
        D.emit_overlay(inputs, mod, None)
    assert not mod.exists()


def test_preflight_alone_catches_both_without_emit(inputs):
    """The checks live in _preflight_inputs itself, callable standalone (no mod_root/ledger needed) --
    the same offline-lint promise `test_the_bench_toml_block_survives_the_real_from_toml_path` relies on."""
    spec = D.normalize_spec(inputs)
    D._preflight_inputs(spec)                      # the clean baseline must NOT raise

    bad_seq = dict(spec)
    Path(bad_seq["sequence"]).write_text(_SEQ + "PlayCamera: Camera=3\n", encoding="utf-8", newline="\n")
    with pytest.raises(D.SummonDeployError, match="does not lint"):
        D._preflight_inputs(bad_seq)


# --------------------------------------------------------------------------- end to end (K1+K2+K3+K4)

def test_authored_overlay_emit_writes_the_whole_effect_folder(inputs, tmp_path):
    res = D.emit_overlay(inputs, tmp_path / "mod", None)          # game=None: NOTHING is read from an install
    ef = tmp_path / "mod" / "StreamingAssets" / "Data" / "SpecialEffects" / "ef091"

    # K1 -- the authored cast, copied VERBATIM (no splice, no donor, no drift guard)
    assert res["seq"]["seq_authored"] is True and res["seq"]["seq_diff"] == ""
    assert (ef / "PlayerSequence.seq").read_text(encoding="utf-8") == _SEQ
    # R15: the nested Sequence.seq must never be written
    assert not (ef / "Sequence.seq").exists()

    # K3 -- particles verbatim beside the manifest; K4 -- the manifest carries the authored curves
    assert (ef / "Puff.sfxmodel").read_text(encoding="utf-8") == _SPRITE
    man = json.loads((ef / "nimbra_manifest.sfxmodel").read_text(encoding="utf-8"))["FBX"][0]
    assert man["End"] == "90" and man["Movement"][0]["OriginY"] == "TargetAveragePositionY - 900"

    # the FileList grammar: exactly ONE space, no tab (SFXData.cs:253-254)
    fl = (ef / "FileList.txt").read_bytes()
    assert fl == b"Model nimbra_manifest.sfxmodel\n" and fl.count(b" ") == 1

    # K2 -- clips at anim_disc_path, keyed from the mint band, NO 3DModelAnimation line
    anim = tmp_path / "mod" / "StreamingAssets" / "Assets" / "Resources" / "Animations" / "6400"
    assert (anim / "60000.anim").is_file() and (anim / "60001.anim").is_file()
    assert "3DModelAnimation" not in (tmp_path / "mod" / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert "3DModel 6400 GEO_MON_B0_M400" in (tmp_path / "mod" / "DictionaryPatch.txt").read_text(encoding="utf-8")


def test_authored_emit_refuses_a_sequence_that_would_be_silently_dropped(inputs, tmp_path):
    Path(inputs["sequence"]).write_text(_SEQ + "PlayCamera: Camera=3\n", encoding="utf-8", newline="\n")
    with pytest.raises(D.SummonDeployError, match="does not lint"):
        D.emit_overlay(inputs, tmp_path / "mod", None)


def test_authored_emit_refuses_a_particle_the_sequence_never_names(inputs, tmp_path):
    Path(inputs["sequence"]).write_text(
        _SEQ.replace("Puff.sfxmodel", "Ghost.sfxmodel"), encoding="utf-8", newline="\n")
    with pytest.raises(D.SummonDeployError, match="is not staged"):
        D.emit_overlay(inputs, tmp_path / "mod", None)


def test_authored_emit_refuses_a_broken_particle_json(inputs, tmp_path):
    Path(inputs["particles"][0]).write_text('{"Sprite": [],}', encoding="utf-8", newline="\n")
    with pytest.raises(D.SummonDeployError, match="does not lint"):
        D.emit_overlay(inputs, tmp_path / "mod", None)


def test_missing_authored_inputs_are_named_before_anything_is_written(inputs, tmp_path):
    """The preflight: a missing input must be reported BEFORE the mint and the host .seq land, or a
    half-emitted mod folder is left behind with no revert script (the ledger only writes one at the end).
    The particle keeps its NAME so this tests the missing FILE, not the sequence's cross-reference."""
    cases = {
        "sequence": (str(tmp_path / "gone.seq"), "sequence file not found"),
        "clips": ([str(tmp_path / "gone.anim")], "clip not found"),
        "particles": ([str(tmp_path / "gone" / "Puff.sfxmodel")], "particle .sfxmodel not found"),
    }
    for key, (value, msg) in cases.items():
        bad = dict(inputs)
        bad[key] = value
        if key == "clips":
            bad["staging"] = _staging(play=[])
        mod = tmp_path / f"mod-{key}"
        with pytest.raises(D.SummonDeployError, match=msg):
            D.emit_overlay(bad, mod, None)
        assert not mod.exists(), f"{key}: the emit wrote files before refusing"


def test_the_revert_script_removes_the_whole_effect_folder(inputs, tmp_path):
    res = D.emit_overlay(inputs, tmp_path / "mod", None)
    ef = tmp_path / "mod" / "StreamingAssets" / "Data" / "SpecialEffects" / "ef091"
    assert ef.is_dir()
    out = subprocess.run([sys.executable, res["revert_script"]], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert not ef.exists()


# --------------------------------------------------------------------------- the block-schema layer

def test_donor_becomes_optional_when_a_sequence_is_authored():
    block = {"model": "m.fbx", "sequence": "cast.seq"}
    assert "donor" not in CS.numeric_block(block)
    with pytest.raises(CS.SummonBlockError, match="An ORIGINAL summon has no donor"):
        CS.numeric_block({"model": "m.fbx"})


# --------------------------------------------------------------------------- donor-less normalize (Finding 8)

def test_authored_sequence_leaves_donor_none_not_silently_bahamut():
    """A pure-authored (`sequence=`) block used to fall through to `donor_raw = block.get("donor",
    DEFAULT_DONOR)` -> a silent donor=227 (Bahamut) even though nothing donor-shaped was ever read."""
    spec = D.normalize_spec({"model": "m.fbx", "sequence": "cast.seq", "lane": "overlay"})
    assert spec["donor"] is None


def test_a_plain_transplant_block_without_sequence_still_defaults_the_donor():
    """The regression guard: an ordinary (non-authored) block omitting `donor` must still default to
    DEFAULT_DONOR -- this fix only changes behaviour for a `sequence=`-authored block."""
    spec = D.normalize_spec({"model": "m.fbx"})
    assert spec["donor"] == D.DEFAULT_DONOR


def test_hybrid_lane_with_no_donor_is_refused():
    """A donor-dependent feature: the hybrid lane arms `[SfxHybrid] EffectId = donor`, posing the model on
    the DONOR's live skeleton. An authored block with no donor has no skeleton to pose on -- refuse it
    explicitly instead of writing `EffectId = None` (or, pre-fix, a silent Bahamut) into Memoria.ini."""
    with pytest.raises(D.SummonDeployError, match='lane = "hybrid" needs a `donor`'):
        D.normalize_spec({"model": "m.fbx", "sequence": "cast.seq", "lane": "hybrid"})


def test_decode_donor_clips_refuses_a_none_donor_instead_of_crashing():
    """The other donor-dependent feature: a donor-decode `clips` selector ('all'/index list) with no
    donor used to crash with a bare TypeError (`int(None)`) inside `_local_ef_bytes` -- refuse cleanly."""
    with pytest.raises(D.SummonDeployError, match="cannot decode donor clips"):
        D._decode_donor_clips({"donor": None, "clips": "all"}, None)


def test_authored_block_with_clips_none_and_no_donor_deploys_without_crashing(tmp_path):
    """The counterpart: `clips = "none"` needs no donor at all (nothing to decode), so a donor-less
    authored block using it must deploy cleanly, not trip the donor-dependent code path at all."""
    seq = tmp_path / "cast.seq"
    seq.write_text(_SEQ, encoding="utf-8", newline="\n")
    (tmp_path / "model.fbx").write_text("; stub fbx\n", encoding="utf-8", newline="\n")
    block = {"lane": "overlay", "model": str(tmp_path / "model.fbx"), "id": 6400,
             "name": "GEO_MON_B0_M400", "private_ef": 91, "sequence": str(seq),
             "manifest": "m.sfxmodel", "clips": "none"}
    res = D.emit_overlay(block, tmp_path / "mod", None)
    assert res["spec"]["donor"] is None


def test_the_new_keys_are_known_to_the_schema():
    assert {"sequence", "particles", "manifest"} <= CS.KNOWN_KEYS
    assert CS.validate_block({"model": "m.fbx", "sequence": "c.seq", "nonsense": 1}) != []


def test_validate_block_checks_every_authored_path(tmp_path):
    (tmp_path / "m.fbx").write_text("x", encoding="utf-8")
    # `lane = "overlay"` explicit -- an authored (`sequence=`) block with no `donor` now normalizes
    # `donor = None` (Finding 8), and the default `lane` is "hybrid", which refuses a None donor outright
    # (a donor-dependent feature); this test is about the PATH checks, so pick the lane that actually
    # accepts a donor-less authored block.
    block = {"model": "m.fbx", "sequence": "c.seq", "particles": ["p.sfxmodel"],
             "clips": ["a.anim"], "id": 6400, "name": "GEO_MON_B0_M400", "private_ef": 91,
             "lane": "overlay"}
    problems = CS.validate_block(block, base_dir=tmp_path)
    assert any("`sequence` file not found" in p for p in problems)
    assert any("`particles[0]` file not found" in p for p in problems)
    assert any("`clips[0]` file not found" in p for p in problems)


def test_donor_index_clips_are_not_path_checked(tmp_path):
    (tmp_path / "m.fbx").write_text("x", encoding="utf-8")
    problems = CS.validate_block({"donor": 227, "model": "m.fbx", "clips": "all"}, base_dir=tmp_path)
    assert problems == []


def test_lint_notes_flag_the_private_ef_auto_alloc_trap():
    notes = CS.lint_notes([{"model": "m.fbx", "sequence": "c.seq", "lane": "overlay"}])
    assert any("auto-allocate the FIRST free stock-absent id (18)" in n for n in notes)
    assert not any("auto-allocate" in n for n in
                   CS.lint_notes([{"model": "m.fbx", "sequence": "c.seq", "private_ef": 91}]))


def test_manifest_name_must_be_bare():
    with pytest.raises(D.SummonDeployError, match="BARE file name"):
        D.normalize_spec({"donor": 227, "manifest": "sub/dir/x.sfxmodel"})


# --------------------------------------------------------------------------- the rung-8 block itself

@pytest.mark.skipif(not (_STUDY / "nimbra.summon.toml").is_file(),
                    reason="the rung-8 study artifacts are not in this checkout")
def test_the_rung8_block_normalizes_and_reproduces_the_storyboards_numbers():
    """The round's deliverable block, read as the kit reads it. The three curve totals and the playlist
    tick total are STORYBOARD section 3.2/3.3's own figures, re-derived here from the TOML."""
    import tomllib
    block = tomllib.loads((_STUDY / "nimbra.summon.toml").read_text(encoding="utf-8"))["summon"][0]
    spec = D.normalize_spec(CS.numeric_block(block))
    assert spec["staging"] == "curves" and spec["private_ef"] == 91
    assert spec["sequence"] == "nimbra.seq" and spec["manifest"] == "nimbra_manifest.sfxmodel"
    fbx = D.staging_curves_json(spec)
    assert fbx["Start"] == "0" and fbx["End"] == "330"
    for curve in ("Movement", "Rotation", "Scaling"):
        assert sum(int(p["Duration"]) for p in fbx[curve]) == 330, curve
    assert len(fbx["Animations"]) == 6
    # 45 + 75 + 75 + 30 + 75 + 75 = 375 >= 330: the playlist is never exhausted, so it never freezes
    frames = {"emerge": 90, "drift": 75, "strike": 60}
    ticks = sum(-(-frames[p["clip"]] // p.get("speed", 1)) * p.get("repeat", 1)
                for p in spec["staging_curves"]["play"])
    assert ticks == 375 and ticks >= 330


# --------------------------------------------------------------------------- the INTEGRATION regressions
# Both of these were found by ASSEMBLING the bench (studies/custom-summons/rung8-epic/bench/), not by any
# single lane -- each one is invisible until two pieces of shipped code meet.

def test_normalize_spec_is_idempotent_for_a_curve_table(inputs):
    """THE DOUBLE-NORMALIZE BUG. ``deploy.deploy()`` normalizes the block and then hands the SPEC to
    ``emit_overlay``, which normalizes again -- both docstrings promise idempotency. A curve table broke
    it: pass 1 splits ``staging = <table>`` into ``staging = "curves"`` + a separate ``staging_curves``
    key, so pass 2 saw a bare ``"curves"`` string with no table and raised THE MOVEMENT TRAP refusal.

    It only bit the real ``summon-deploy`` CLI (which goes through ``deploy()``); every study build script
    calls ``emit_overlay`` directly and normalizes exactly once, so the whole lane could be green while
    the actual deploy command refused the same block."""
    once = D.normalize_spec(inputs)
    twice = D.normalize_spec(once)                    # <-- raised SummonDeployError before the fix
    assert twice == once
    assert twice["staging"] == "curves" and twice["staging_curves"] == once["staging_curves"]
    # and a THIRD pass still holds (emit -> _resolve_ids -> ... never re-splits)
    assert D.normalize_spec(twice) == once


def test_curves_string_with_no_table_is_still_refused_after_the_idempotency_fix():
    """The fix adopts an ALREADY-SPLIT ``staging_curves``; it must not weaken the real refusal."""
    with pytest.raises(D.SummonDeployError, match="needs an authored"):
        D.normalize_spec({"lane": "overlay", "id": 6400, "private_ef": 91, "staging": "curves"})


def test_from_toml_rebases_relative_paths_against_the_toml_dir(tmp_path):
    """``summon-deploy --from-toml`` used to take a block's relative paths VERBATIM, so a block that
    ``lint``/``build`` accepted (they resolve against ``base_dir``) died at emit the moment the caller's
    cwd was not the TOML's folder. The bench toml lives in ``bench/`` and reaches into ``../creature/``,
    so it hit this on the very first deploy rehearsal."""
    from ff9mapkit import cli
    block = {"lane": "overlay", "model": "sub/model.fbx", "sequence": "cast.seq",
             "clips": ["a.anim", "b.anim"], "particles": ["p.sfxmodel"], "textures": ["t.png"]}
    out = cli._rebase_summon_paths(block, tmp_path)
    assert out["model"] == str(tmp_path / "sub/model.fbx")
    assert out["sequence"] == str(tmp_path / "cast.seq")
    assert out["clips"] == [str(tmp_path / "a.anim"), str(tmp_path / "b.anim")]
    assert out["particles"] == [str(tmp_path / "p.sfxmodel")]
    assert out["textures"] == [str(tmp_path / "t.png")]
    # an ABSOLUTE path is left alone, and the donor INDEX-selector form of `clips` is never path-mangled
    abs_fbx = str(tmp_path / "abs.fbx")
    keep = cli._rebase_summon_paths({"model": abs_fbx, "clips": "all"}, tmp_path)
    assert keep["model"] == abs_fbx and keep["clips"] == "all"
    assert cli._rebase_summon_paths({"clips": [0, 1]}, tmp_path)["clips"] == [0, 1]


@pytest.mark.skipif(not (_STUDY / "bench" / "rung8.field.toml").is_file(),
                    reason="the rung-8 study artifacts are not in this checkout")
def test_the_bench_toml_block_survives_the_real_from_toml_path(tmp_path):
    """End to end on the round's actual deliverable: read the BENCH field toml exactly as
    ``summon-deploy --from-toml`` does (rebase -> numeric_block -> normalize twice), from a cwd that is
    NOT the toml's folder. Every path must resolve to a real file."""
    import tomllib
    from pathlib import Path as _P

    from ff9mapkit import cli
    src = _STUDY / "bench" / "rung8.field.toml"
    block = tomllib.loads(src.read_text(encoding="utf-8"))["summon"][0]
    block = cli._rebase_summon_paths(block, src.parent)
    spec = D.normalize_spec(D.normalize_spec(CS.numeric_block(block)))
    assert spec["private_ef"] == 91 and spec["id"] == 6400 and spec["staging"] == "curves"
    for p in [spec["model"], spec["sequence"], *spec["particles"], *spec["clips"]]:
        assert _P(p).is_file(), p
    D._preflight_inputs(spec)                          # the emitter's own front-loaded existence check


# --------------------------------------------------------------------------- THE TURNING SPLIT

@pytest.mark.parametrize("ease", ["Turning1", "Turning2"])
@pytest.mark.parametrize("curve", ["move", "turn", "scale"])
def test_turning_eases_are_refused_on_every_fbx_curve(curve, ease):
    """Turning1/Turning2 are the only InterpolateType arms that read ``customParam``, and they read it
    with NO null guard (ParametricMovement.cs:233-237). The FBX render path passes ``null`` on all three
    curves (SFXDataMesh.cs:843-845) => NullReferenceException on every render frame. They are legal in
    the enum, legal on a SPRITE, and fatal here -- so the vocabulary has to be split, not shared."""
    st = _staging(**{curve: [{"duration": 90, "from": [0, 0, 0], "to": [0, 0, 0],
                              "ease": [ease, "Linear", "Linear"]}]})
    with pytest.raises(D.SummonDeployError, match="SPRITE-ONLY"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": st})
    assert ease not in D._FBX_EASES and ease in D._EASES


def test_the_sprite_only_eases_are_still_a_real_enum_member_not_a_typo():
    """The refusal must NOT be the generic typo message -- a Turning ease is a correctly-spelled engine
    value that happens to be fatal on this path, and the error has to say so or the author will 'fix' it
    by re-spelling it."""
    st = _staging(scale=[{"duration": 90, "from": 0.5, "to": 1.0, "ease": ["Turning1"] * 3}])
    with pytest.raises(D.SummonDeployError, match="customParam.TryGetValue"):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": st})


# --------------------------------------------------------------------------- THE OMITTED-CURVE SPLIT

@pytest.mark.parametrize("curve,match", [
    ("move", "THE MOVEMENT TRAP"),
    ("turn", "ROTATION BASELINE"),
])
def test_an_omitted_move_or_turn_curve_is_refused(curve, match):
    """staging_curves_json emits no key for an empty piece list, LoadFBX only LoadFromJSON's a node that
    EXISTS (SFXDataMesh.cs:1007-1012), and GetPosition then returns the ctor seed forever
    (ParametricMovement.cs:226-227). For movement/rotation that seed is Vector3.zero: the world origin,
    and euler (0,0,0) written over the FBX's own orientation every frame."""
    st = {k: v for k, v in _staging().items() if k != curve}
    with pytest.raises(D.SummonDeployError, match=match):
        D.normalize_spec({"donor": 227, "clips": ["a.anim"], "staging": st})


def test_an_omitted_scale_curve_is_ACCEPTED_because_its_seed_is_identity():
    """The counterpart, and the reason the three curves cannot share one rule: ``scaling`` alone is built
    ``new ParametricMovement(true)`` (SFXDataMesh.cs:1252), whose isScaling branch seeds Vector3.one
    (ParametricMovement.cs:26-30). An omitted Scaling is therefore a benign identity scale, NOT an
    invisible creature -- so refusing it would be a false alarm."""
    st = {k: v for k, v in _staging().items() if k != "scale"}
    spec = D.normalize_spec({"donor": 227, "id": 6400, "name": "GEO_MON_B0_M400",
                             "clips": ["a/emerge.anim", "a/drift.anim"], "staging": st})
    out = D.staging_curves_json(spec)
    assert "Scaling" not in out and "Movement" in out and "Rotation" in out
