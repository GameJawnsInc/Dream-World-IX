"""``summons.seqlint`` -- THE SILENT-SKIP GUARD for hand-authored SFX ``.seq``/``.sfxmodel`` files
(rung-8 kit item K5).

All PURE LOGIC (no install, no stock bytes) except two REGRESSION ANCHORS that lint the study's own
in-game-proven artifacts when the repo checkout has them: rung 6's bare cast and rung 5's sprite. Those
two files are the ground truth for "a sequence the engine actually ran", so a linter that rejects either
is wrong about the grammar, not the file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ff9mapkit.summons import seqlint as SL

_STUDY = Path(__file__).resolve().parents[2] / "studies" / "custom-summons"


def _errs(text, **kw):
    return [str(p) for p in SL.analyze_seq(text, **kw).errors]


def _warns(text, **kw):
    return [str(p) for p in SL.analyze_seq(text, **kw).warnings]


#: the shortest cast that satisfies every whole-file law, for negative tests to perturb.
_MINIMAL = (
    "PlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True\n"
    "SetBackgroundIntensity: Intensity=0 ; Time=12\n"
    "Wait: Time=30\n"
    "SetBackgroundIntensity: Intensity=1 ; Time=12\n"
    "Wait: Time=24\n"
    "EffectPoint: Char=AllTargets ; Type=Effect\n"
    "EffectPoint: Char=Everyone ; Type=Figure\n"
    "PlayAnimation: Char=Caster ; Anim=Idle\n"
)


def test_minimal_sequence_is_clean():
    assert _errs(_MINIMAL) == []


# --------------------------------------------------------------------------- the parser

def test_parse_mirrors_the_engine_parser():
    text = ("// a whole-line comment\n"
            "Wait: Time=12   // trailing comment\r\n"
            "\n"
            "Message: Text=[CastName] ; Priority=1 ; Title=True\n")
    lines = SL.parse_seq(text)
    assert [ln.op for ln in lines] == ["Wait", "Message"]
    assert lines[0].args == {"Time": "12"}                        # comment stripped, value Trim()ed
    assert lines[1].args["Text"] == "[CastName]"
    assert lines[0].lineno == 2                                   # 1-based, comment line counted


def test_parse_records_positional_and_duplicate_args():
    lines = SL.parse_seq("Wait: 12\nWait: Time=1 ; Time=2\n")
    assert lines[0].args == {"#0": "12"}                          # no `=` -> engine maps BY POSITION
    assert lines[1].args == {"Time": "2"} and lines[1].dup_keys == ("Time",)


def test_positional_argument_is_an_error_and_duplicate_is_a_warning():
    assert any("has no `Key=`" in m for m in _errs(_MINIMAL + "Wait: 12\n"))
    assert any("more than once" in m for m in _warns(_MINIMAL + "Wait: Time=1 ; Time=2\n"))


# --------------------------------------------------------------------------- op / arg whitelists

def test_unknown_op_is_an_error_because_the_engine_drops_it_silently():
    msgs = _errs(_MINIMAL + "PlayAnimtion: Char=Caster ; Anim=Idle\n")     # typo
    assert any("unknown operation `PlayAnimtion`" in m and "WITHOUT a log" in m for m in msgs)


def test_engine_op_without_our_arg_table_warns_but_does_not_block():
    text = _MINIMAL + "ChangeSize: Char=Caster ; Size=2\n"
    assert _errs(text) == []
    assert any("no executor-derived argument table" in m for m in _warns(text))


def test_unknown_arg_key_is_an_error():
    msgs = _errs(_MINIMAL + "Wait: Times=12\n")
    assert any("`Wait` has no argument `Times`" in m for m in msgs)


def test_reflect_is_universal_and_accepted_on_every_op():
    assert _errs(_MINIMAL + "Wait: Time=1 ; Reflect=True\n") == []


def test_createvisualeffect_sfxmodel_key_is_accepted_though_absent_from_operationArguments():
    # the rung-5 law: the executor reads `SFXModel` (UnifiedBattleSequencer.cs:397); the engine's own
    # positional table lists SPS/Char/Bone/Offset/Size/Time/Speed/UseSHP/UseSFXModel and NOT SFXModel.
    assert "SFXModel" in SL.OUR_OPS["CreateVisualEffect"]
    assert "SFXModel" not in ("SPS", "Char", "Bone", "Offset")
    assert _errs(_MINIMAL + "CreateVisualEffect: Char=Caster ; "
                            "SFXModel=Data/SpecialEffects/ef091/X.sfxmodel\n") == []


def test_playanimation_hold_is_accepted_though_absent_from_operationArguments():
    assert _errs(_MINIMAL + "PlayAnimation: Char=Caster ; Anim=Idle ; Hold=True\n") == []


# --------------------------------------------------------------------------- refused ops

@pytest.mark.parametrize("line,needle", [
    ("PlayCamera: Camera=3 ; Char=Caster", "HARD NO-OP"),
    ("ShiftWorld: Offset=(0,0,200)", "btlRoot"),
])
def test_playcamera_and_shiftworld_are_refused_with_citations(line, needle):
    msgs = _errs(_MINIMAL + line + "\n")
    assert any(needle in m for m in msgs), msgs


# --------------------------------------------------------------------------- threads

def test_thread_balance():
    ok = _MINIMAL + "StartThread: Condition=1 == 1 ; Sync=False\nWait: Time=1\nEndThread\n"
    assert _errs(ok) == []
    assert any("unclosed" in m for m in _errs(_MINIMAL + "StartThread: Sync=False\nWait: Time=1\n"))
    assert any("no open StartThread" in m for m in _errs(_MINIMAL + "EndThread\n"))


# --------------------------------------------------------------------------- THE PHASE-LOCK RULE

_PLAY = ("PlaySFX: SFX=91 ; Reflect=True ; SkipSequence=True\n"
         "Wait: Time=30\n")


def test_clip_bound_wait_inside_the_playsfx_window_is_refused():
    text = _MINIMAL + _PLAY + "WaitAnimation: Char=Caster\nWaitSFXDone: SFX=91\n"
    assert any("THE PHASE-LOCK RULE" in m for m in _errs(text, private_ef=91))


def test_clip_bound_wait_in_the_release_tail_is_allowed():
    # the proven rung-6 tail: everything after the instance drains has no manifest clock left to slide
    text = (_MINIMAL + _PLAY + "WaitSFXDone: SFX=91\n"
            "PlayAnimation: Char=Caster ; Anim=Idle\n"
            "Turn: Char=Caster ; BaseAngle=Default ; Time=5\nWaitTurn: Char=Caster\n")
    assert _errs(text, private_ef=91) == []


def test_clip_bound_wait_before_playsfx_is_allowed():
    text = "WaitAnimation: Char=Caster\n" + _MINIMAL + _PLAY + "WaitSFXDone: SFX=91\n"
    assert _errs(text, private_ef=91) == []


# --------------------------------------------------------------------------- THE FIGURE-VISIBILITY LAW

def test_effectpoint_under_the_blackout_is_refused():
    text = ("PlayAnimation: Char=Caster ; Anim=MP_CHANT\n"
            "SetBackgroundIntensity: Intensity=0 ; Time=12\n"
            "Wait: Time=30\n"
            "EffectPoint: Char=Everyone ; Type=Figure\n"
            "PlayAnimation: Char=Caster ; Anim=Idle\n")
    assert any("THE FIGURE-VISIBILITY LAW" in m for m in _errs(text))


def test_effectpoint_mid_relight_ramp_is_refused():
    text = ("PlayAnimation: Char=Caster ; Anim=MP_CHANT\n"
            "SetBackgroundIntensity: Intensity=0 ; Time=12\nWait: Time=30\n"
            "SetBackgroundIntensity: Intensity=1 ; Time=18\n"
            "Wait: Time=9\n"                                   # only HALF the ramp has run
            "EffectPoint: Char=Everyone ; Type=Figure\n"
            "PlayAnimation: Char=Caster ; Anim=Idle\n")
    msgs = _errs(text)
    assert any("THE FIGURE-VISIBILITY LAW" in m and "0.5" in m for m in msgs), msgs


def test_effect_type_under_blackout_only_warns():
    # Type=Effect queues figures; it is the later Type=Figure/Both that must be lit.
    text = ("PlayAnimation: Char=Caster ; Anim=MP_CHANT\n"
            "SetBackgroundIntensity: Intensity=0 ; Time=12\nWait: Time=30\n"
            "EffectPoint: Char=AllTargets ; Type=Effect\n"
            "SetBackgroundIntensity: Intensity=1 ; Time=12\nWait: Time=24\n"
            "EffectPoint: Char=Everyone ; Type=Figure\n"
            "PlayAnimation: Char=Caster ; Anim=Idle\n")
    assert _errs(text) == []
    assert any("make sure THAT one is" in m for m in _warns(text))


# --------------------------------------------------------------------------- the other laws

def test_mid_intensity_warns():
    assert any("THE INTENSITY SUBTLETY LAW" in m
               for m in _warns(_MINIMAL + "SetBackgroundIntensity: Intensity=0.5 ; Time=30\n"))


def test_anim_idle_release_law():
    no_idle = _MINIMAL.replace("PlayAnimation: Char=Caster ; Anim=Idle\n",
                               "PlayAnimation: Char=Caster ; Anim=MP_MAGIC\n")
    assert any("THE ANIM=IDLE RELEASE LAW" in m for m in _errs(no_idle))
    assert any("no `PlayAnimation: Char=Caster`" in m for m in _errs("Wait: Time=1\n"))


def test_loadsfx_and_playsfx_carry_their_gotcha_warnings():
    assert any("UseCamera=False" in m for m in _warns(_MINIMAL + "LoadSFX: SFX=91 ; Char=Caster\n"))
    assert any("SkipSequence=True" in m for m in _warns(_MINIMAL + "PlaySFX: SFX=91\n"))


# --------------------------------------------------------------------------- cross-file

def test_sfxmodel_path_must_be_data_rooted_and_staged():
    bad_root = _MINIMAL + "CreateVisualEffect: Char=Everyone ; SFXModel=MistWisps.sfxmodel\n"
    assert any("FULL Data/-rooted path" in m for m in _errs(bad_root))
    unstaged = _MINIMAL + "CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/Nope.sfxmodel\n"
    assert any("is not staged" in m for m in _errs(unstaged, particles=["MistWisps.sfxmodel"]))
    good = _MINIMAL + "CreateVisualEffect: Char=Everyone ; SFXModel=Data/SpecialEffects/ef091/MistWisps.sfxmodel\n"
    assert _errs(good, particles=["MistWisps.sfxmodel"]) == []


def test_createvisualeffect_without_char_is_refused():
    text = _MINIMAL + "CreateVisualEffect: SFXModel=Data/SpecialEffects/ef091/A.sfxmodel\n"
    assert any("renders on NOBODY" in m for m in _errs(text))


def test_inert_keys_on_the_sfxmodel_branch_warn():
    text = _MINIMAL + ("CreateVisualEffect: Char=Everyone ; Size=2 ; "
                       "SFXModel=Data/SpecialEffects/ef091/A.sfxmodel\n")
    assert any("INERT on the SFXModel branch" in m for m in _warns(text))


def test_sfx_id_must_be_the_private_host():
    text = _MINIMAL + "LoadSFX: SFX=227 ; Char=Caster ; UseCamera=False\n"
    assert any("does not target this block's private effect id 91" in m for m in _errs(text, private_ef=91))
    assert _errs(_MINIMAL + "LoadSFX: SFX=91 ; Char=Caster ; UseCamera=False\n", private_ef=91) == []


def test_empty_sequence_is_an_error():
    assert any("no operation lines" in m for m in _errs("// nothing but a comment\n"))


# --------------------------------------------------------------------------- the .sfxmodel side

def test_sfxmodel_bad_json_is_reported_not_raised():
    problems = SL.lint_sfxmodel_text('{"Sprite": [],}')          # trailing comma
    assert problems and "not valid JSON" in problems[0]


def test_sfxmodel_index_and_triangle_checks():
    doc = ('{"Sprite":[{"Vertices":["(0, 0, 0)","(1, 0, 0)","(0, 1, 0)"],'
           '"Indices":["0","1","2","0","1"]}]}')
    problems = SL.lint_sfxmodel_text(doc)
    assert any("not a multiple of 3" in m for m in problems)
    bad = '{"Sprite":[{"Vertices":["(0, 0, 0)"],"Indices":["0","1","2"]}]}'
    assert any("outside Vertices" in m for m in SL.lint_sfxmodel_text(bad))


def test_sfxmodel_unknown_interpolation_is_caught():
    doc = '{"Sprite":[{"Vertices":[],"Indices":[],"Movement":{"InterpolationTypeY":"EaseOut"}}]}'
    assert any("EaseOut" in m and "Constant" in m for m in SL.lint_sfxmodel_text(doc))


def test_sfxmodel_color_interpolation_segment_count():
    doc = ('{"Sprite":[{"Vertices":["(0, 0, 0)"],"Indices":[],'
           '"ColorInterpolation":["SinusOut"],'
           '"ColorAnimation":[{"Frame":"0","VertexColors":["(0,0,0,0.5)"]},'
           '{"Frame":"5","VertexColors":["(1,1,1,0.5)"]},'
           '{"Frame":"9","VertexColors":["(0,0,0,0.5)"]}]}]}')
    assert any("3 segment" in m or "2 segment" in m for m in SL.lint_sfxmodel_text(doc))


def test_sfxmodel_parameter_min_max_type_mismatch_is_the_headline_trap():
    # SFXDataMesh.cs:1389-1403 sorts Min/Max into SEPARATE int/float dicts and drops any unpaired key.
    doc = ('{"Sprite":[{"Vertices":[],"Indices":[],'
           '"Emission":[{"Frame":["0"],"ParameterMin1":"0.35","ParameterMax1":"1"}]}]}')
    problems = SL.lint_sfxmodel_text(doc)
    assert any("would vanish with no log" in m for m in problems), problems
    ok = ('{"Sprite":[{"Vertices":[],"Indices":[],'
          '"Emission":[{"Frame":["0"],"ParameterMin1":"0.35","ParameterMax1":"1.0"}]}]}')
    assert SL.lint_sfxmodel_text(ok) == []


def test_sfxmodel_lone_parameter_bound_is_caught():
    doc = '{"Sprite":[{"Vertices":[],"Indices":[],"Emission":[{"Frame":["0"],"ParameterMin1":"0.3"}]}]}'
    assert any("a Min without its Max" in m for m in SL.lint_sfxmodel_text(doc))


def test_sfxmodel_first_curve_piece_must_carry_an_origin():
    doc = '{"FBX":[{"Path":"GEO_X","Movement":[{"Duration":"10","DestinationY":"100"}]}]}'
    assert any("no Origin*" in m for m in SL.lint_sfxmodel_text(doc))


# --------------------------------------------------------------------------- regression anchors

@pytest.mark.skipif(not (_STUDY / "rung6-bare-sequence" / "bare_player_sequence.seq").is_file(),
                    reason="the rung-6 study artifact is not in this checkout")
def test_the_in_game_proven_rung6_cast_lints_clean():
    """Rung 6's bare cast RAN. If the linter rejects it, the linter is wrong about the grammar."""
    rep = SL.lint_seq_file(_STUDY / "rung6-bare-sequence" / "bare_player_sequence.seq")
    assert rep.errors == [], [str(p) for p in rep.errors]


@pytest.mark.skipif(not (_STUDY / "rung7-creature" / "rung7_player_sequence.seq").is_file(),
                    reason="the rung-7 study artifact is not in this checkout")
def test_the_in_game_proven_rung7_cast_lints_clean_except_its_known_phase_lock_debt():
    """Rung 7's creature cast also ran -- but it holds the creature with clip-bound WaitAnimations INSIDE
    the PlaySFX..WaitSFXDone window, which is exactly the debt STORYBOARD section 3 turned into THE
    PHASE-LOCK RULE. So it is expected to fail on that rule and nothing else."""
    rep = SL.lint_seq_file(_STUDY / "rung7-creature" / "rung7_player_sequence.seq", private_ef=84)
    others = [str(p) for p in rep.errors if "PHASE-LOCK" not in str(p)]
    assert others == [], others


@pytest.mark.skipif(not (_STUDY / "rung5-particles" / "rung5_sprite.sfxmodel").is_file(),
                    reason="the rung-5 study artifact is not in this checkout")
def test_the_in_game_proven_rung5_sprite_lints_clean():
    assert SL.lint_sfxmodel_file(_STUDY / "rung5-particles" / "rung5_sprite.sfxmodel") == []


@pytest.mark.skipif(not (_STUDY / "rung8-epic" / "nimbra.seq").is_file(),
                    reason="the rung-8 artifacts are not in this checkout")
def test_the_authored_nimbra_set_is_clean():
    """The round's own deliverable: the cast and all three particle models, zero errors AND zero
    warnings (a warning here would mean a law was worked around rather than obeyed)."""
    base = _STUDY / "rung8-epic"
    particles = ["MistFloor.sfxmodel", "MistWisps.sfxmodel", "RiftFlash.sfxmodel"]
    rep = SL.lint_seq_file(base / "nimbra.seq", private_ef=91, particles=particles)
    assert [str(p) for p in rep.problems] == []
    assert rep.total_ticks == 395                       # STORYBOARD section 3.1's own figure
    for name in particles:
        assert SL.lint_sfxmodel_file(base / name) == [], name


# --------------------------------------------------------------------------- THE TURNING SPLIT

def _fbx(**over) -> str:
    fbx = {"Path": "6400.fbx", "Start": "0", "End": "90",
           "Movement": [{"Duration": "90", "OriginY": "0", "DestinationY": "10"}],
           "Rotation": [{"Duration": "90", "OriginY": "180", "DestinationY": "180"}],
           "Scaling": [{"Duration": "90", "OriginX": "1", "DestinationX": "1"}]}
    fbx.update(over)
    return json.dumps({"FBX": [{k: v for k, v in fbx.items() if v is not None}]})


@pytest.mark.parametrize("curve", ["Movement", "Rotation", "Scaling"])
def test_turning_on_an_fbx_curve_is_reported_as_the_nre_it_is(curve):
    piece = [{"Duration": "90", "OriginY": "0", "DestinationY": "1",
              "InterpolationTypeY": "Turning1"}]
    problems = SL.lint_sfxmodel_text(_fbx(**{curve: piece}))
    assert len(problems) == 1 and "SPRITE-ONLY" in problems[0] and "843-845" in problems[0]


@pytest.mark.parametrize("curve,expect", [
    ("Movement", "THE MOVEMENT TRAP"),
    ("Rotation", "ROTATION BASELINE"),
])
def test_an_fbx_entry_missing_movement_or_rotation_is_reported(curve, expect):
    """A hand-edited manifest is the only way past the emitter's own gate, so the linter has to hold the
    same line: an absent node is never LoadFromJSON'd (SFXDataMesh.cs:1007-1012)."""
    problems = SL.lint_sfxmodel_text(_fbx(**{curve: None}))
    assert len(problems) == 1 and expect in problems[0]


def test_an_fbx_entry_missing_only_scaling_is_clean():
    """Vector3.one seed (ParametricMovement.cs:26-30 via SFXDataMesh.cs:1252) -- identity, not invisible."""
    assert SL.lint_sfxmodel_text(_fbx(Scaling=None)) == []


def _sprite(emission: dict, interp: str = "Turning1") -> str:
    return json.dumps({"Sprite": [{
        "Vertices": ["(1, 1)"], "Indices": ["0", "0", "0"],
        "Movement": {"InterpolationTypeX": interp},
        "Emission": [dict({"Frame": ["0"], "Count": "1"}, **emission)]}]})


def test_turning_on_a_sprite_movement_needs_an_emission_parameter():
    """The other half of the split. p.param is null unless the emission declared a ParameterMin/Max pair
    (SFXDataMesh.cs:1379, 1386-1388), and the same unguarded TryGetValue then throws."""
    problems = SL.lint_sfxmodel_text(_sprite({}))
    assert len(problems) == 1 and "needs an emission Parameter" in problems[0]


def test_turning_on_a_sprite_movement_WITH_a_parameter_is_clean():
    """The shipped MistFloor/MistWisps shape -- Turning1/Turning2 paired with Parameter0..2. This is why
    the eases read as 'endorsed' and why the FBX refusal cannot simply be a global ban."""
    assert SL.lint_sfxmodel_text(_sprite({"ParameterMin0": "0", "ParameterMax0": "360"})) == []


def test_turning_stays_legal_on_the_colour_scale_dictionary_path():
    """Color/Scale/UV interpolation runs through GetInterpolatedDictionaryValue -> Factor1/Factor2, which
    never touch customParam -- so Turning is unconditionally safe there and must not be flagged."""
    doc = json.dumps({"Sprite": [{
        "Vertices": ["(1, 1)"], "Indices": ["0", "0", "0"],
        "ScaleAnimation": [{"Frame": "0", "Scale": "1"}, {"Frame": "10", "Scale": "2"}],
        "ScaleInterpolation": ["Turning1"],
        "Emission": [{"Frame": ["0"], "Count": "1"}]}]})
    assert SL.lint_sfxmodel_text(doc) == []
