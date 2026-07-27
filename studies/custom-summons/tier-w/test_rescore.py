r"""Tests for the TIER W rung-2 CONTENT RESCORE.

Runs WITHOUT the game install and WITHOUT the extracted corpus: every unit test synthesises its own
container with ``test_summon_camera``'s builders, so the field map, the refusals, the same-length
splice, the three-sequence trap, the self-check and the ledger/revert are all exercised on bytes
this file wrote.  Install- and corpus-dependent tests skip on absence, as tier-r's and W1's do.

    py -m pytest studies/custom-summons/tier-w/test_rescore.py -q
"""
from __future__ import annotations

import glob
import hashlib
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rescore as R                                             # noqa: E402
import summon_camera as W                                       # noqa: E402
from ff9mapkit.battle import camera_codec as CC                 # noqa: E402
from test_summon_camera import (CAMPOS, ESTABLISH, FOCAL, FOCAL2, MOVE, TAIL,  # noqa: E402
                                TGTPOS, camera_block, code, synth)

CORPUS = W.SCRATCH_CORPUS
have_corpus = bool(glob.glob(os.path.join(CORPUS, "ef*.bytes")))
needs_corpus = pytest.mark.skipif(not have_corpus, reason="no extracted corpus at %s" % CORPUS)

SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bahamut_rescore.toml")


def _has_install() -> bool:
    try:
        from ff9mapkit import config
        return bool(config.find_game_path(None))
    except Exception:
        return False


needs_install = pytest.mark.skipif(not _has_install(), reason="no FF9 install resolvable")


# ============================================================ a one-shot synthetic container
def one_shot_container(sequences=None, selector=b"\x01\x00\x00\x00"):
    """A container whose sequence plays ONE camera at chunk 0 sub-file 1."""
    seqs = sequences or [[ESTABLISH, MOVE, TAIL]]
    blk = camera_block(seqs, selector=selector)
    subs = [b"\xaa" * 32, blk, b"\xbb" * 48]
    ops = [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, 0), (W.OP_WAIT, 0, 20)]
    return synth(subs, ops), blk


def spec_for(edits, effect=999, expect=None):
    r = {"effect": effect, "label": "t"}
    if expect:
        r["expect_sha256"] = expect
    return {"rescore": r, "edit": edits}


# ============================================================ (2) the Code field map
def test_field_offsets_agree_with_the_codec_on_an_exhaustive_flag_sweep():
    """``code_field_offsets`` must walk EXACTLY the layout ``camera_codec._split_code`` slices --
    it is what tells a splice which four bytes are the focal and not the two after it."""
    payload = bytes(range(1, 65))
    checked = 0
    for flags in range(0x10000):
        if flags & 0x0100:                      # 0x100 has no field in the codec's reader
            continue
        want = CC._split_code(flags, payload)
        got = R.code_field_offsets(flags)
        assert set(got) == set(want), flags
        for name, (off, size) in got.items():
            assert payload[off:off + size] == want[name], (hex(flags), name)
        checked += 1
    assert checked > 30000


@needs_corpus
def test_field_offsets_agree_on_every_flag_word_in_the_corpus():
    seen, n = set(), 0
    for p in W.corpus_paths()[:60]:
        with open(p, "rb") as fh:
            blob = fh.read()
        ex = W.extract_shots(blob, os.path.basename(p))
        for s in ex.shots:
            for si in range(len(s.camera["sequences"])):
                for c in s.camera["sequences"][si]:
                    if not c.get("frame"):
                        continue
                    seen.add(c["flags"])
                    want = CC._split_code(c["flags"], c["block"])
                    got = R.code_field_offsets(c["flags"])
                    assert set(got) == set(want)
                    for name, (off, size) in got.items():
                        assert c["block"][off:off + size] == want[name]
                    n += 1
    assert n > 200 and len(seen) > 5


# ============================================================ (3) the edit + its refusals
def _build(edits, **kw):
    blob, _ = one_shot_container(**kw)
    return R.build_patched(spec_for(edits), "t", blob=blob)


def test_a_pose_and_a_focal_edit_change_exactly_the_named_bytes():
    b = _build([{"shot": "A", "frame": 1, "camera": {"roll": 200},
                 "focal": {"distance": 96}}])
    assert len(b.patched) == len(b.orig)
    assert len(b.check.changed_offsets) == 3        # roll (1B) + H (2B)
    assert b.check.ok


def test_durations_are_refused_at_w2():
    for section, key in (("focal", "duration"), ("camera_move", "duration")):
        with pytest.raises(R.RescoreError, match="CLOCK"):
            _build([{"shot": "A", "frame": 30 if section == "camera_move" else 1,
                     section: {key: 5}}])


def test_a_field_the_flags_do_not_declare_is_refused():
    """MOVE (frame 30) carries campos + cammove and no focal.  Writing a focal there would land in
    whatever follows -- a same-length splice would not catch it, so it is refused up front."""
    with pytest.raises(R.RescoreError, match="no focal sub-block"):
        _build([{"shot": "A", "frame": 30, "focal": {"distance": 96}}])


def test_out_of_range_values_are_refused_per_field_width():
    with pytest.raises(R.RescoreError, match="out of range"):
        _build([{"shot": "A", "frame": 1, "camera": {"roll": 256}}])
    with pytest.raises(R.RescoreError, match="out of range"):
        _build([{"shot": "A", "frame": 1, "focal": {"distance": 65536}}])
    b = _build([{"shot": "A", "frame": 1, "focal": {"distance": 65535}}])
    assert b.check.ok


def test_unknown_field_names_are_refused():
    with pytest.raises(R.RescoreError, match="unknown pose field"):
        _build([{"shot": "A", "frame": 1, "camera": {"zoom": 3}}])


def test_an_edit_that_changes_nothing_is_refused():
    with pytest.raises(R.RescoreError, match="changes nothing"):
        _build([{"shot": "A", "frame": 1}])


def test_a_missing_frame_is_refused():
    with pytest.raises(R.RescoreError, match="no `frame`"):
        _build([{"shot": "A", "camera": {"roll": 9}}])
    with pytest.raises(R.RescoreError, match="no keyframe at local frame"):
        _build([{"shot": "A", "frame": 77, "camera": {"roll": 9}}])


def two_shot_container():
    """Two PLAY_CAMERA ops -> shots A (sub-file 1) and B (sub-file 3)."""
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    subs = [b"\xaa" * 32, blk, b"\xbb" * 48, blk, b"\xcc" * 16]
    ops = [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, 0),
           (W.OP_WAIT, 0, 20), (W.OP_PLAY_CAMERA, 3, 0)]
    return synth(subs, ops)


def test_shot_letter_and_chunk_subfile_must_agree():
    blob = two_shot_container()
    with pytest.raises(R.RescoreError, match="spec disagrees with the container"):
        R.build_patched(spec_for([{"shot": "A", "chunk": 0, "subfile": 3, "frame": 1,
                                   "camera": {"roll": 9}}]), "t", blob=blob)
    b = R.build_patched(spec_for([{"shot": "B", "chunk": 0, "subfile": 3, "frame": 1,
                                   "camera": {"roll": 9}}]), "t", blob=blob)
    assert b.check.ok and len(b.check.changed_offsets) == 1


def test_an_unresolvable_chunk_subfile_pair_is_refused():
    with pytest.raises(R.RescoreError, match="no shot at chunk"):
        _build([{"shot": "A", "chunk": 0, "subfile": 2, "frame": 1, "camera": {"roll": 9}}])


def test_an_ambiguous_frame_needs_an_occurrence():
    """Two Codes at the same local frame (a placement plus the move it starts) is a real stock idiom
    -- ef227's shot A does it at f121 and f148.  Picking one at random would be a coin-flip."""
    dup = [ESTABLISH, code(1, 0x0002, CAMPOS + struct.pack("<HBB", 24, 2, 0)), TAIL]
    with pytest.raises(R.RescoreError, match="Add `occurrence`|occurrence = 0"):
        _build([{"shot": "A", "frame": 1, "camera": {"roll": 9}}], sequences=[dup])
    b = _build([{"shot": "A", "frame": 1, "occurrence": 1, "camera": {"roll": 9}}],
               sequences=[dup])
    assert b.check.ok


# ============================================================ (4) the same-length splice
def test_rescore_block_refuses_a_length_change():
    blob, blk = one_shot_container()
    ex = W.extract_shots(blob, "t")
    shot = ex.shots[0]
    shot.camera["sequences"][0].insert(
        1, {"frame": 15, "flags": 0x0002,
            "block": CAMPOS + struct.pack("<HBB", 4, 0, 0)})
    with pytest.raises(R.RescoreError, match="SAME-SIZE splice"):
        R.rescore_block(shot)


def test_splice_container_refuses_a_stale_splice():
    blob, _ = one_shot_container()
    sp = R.Splice(0x900, 0x904, b"\x00\x00\x00\x00", b"\x01\x02\x03\x04")
    bad = R.Splice(0x900, 0x904, b"\xff\xff\xff\xff", b"\x01\x02\x03\x04")
    R.splice_container(blob, [sp])
    with pytest.raises(R.RescoreError, match="no longer matches"):
        R.splice_container(blob, [bad])


def test_the_frame_word_is_never_written():
    """W2 writes no frame word at all -- the strongest way to preserve its undecoded 0xE000 marks."""
    marked = [code(0x4001, 0x0809, CAMPOS + TGTPOS + FOCAL), MOVE, TAIL]
    blob, _ = one_shot_container(sequences=[marked])
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    ex = W.extract_shots(b.patched, "t")
    assert ex.shots[0].camera["sequences"][0][0]["frame"] == 0x4001
    assert W.frame_marks(ex.shots[0].camera["sequences"][0][0]["frame"]) == 0x4000


# ============================================================ (5) THE THREE-SEQUENCE TRAP
def _three_track_container(differ=True):
    a = [ESTABLISH, MOVE, TAIL]
    other = ([code(1, 0x0809, CAMPOS[:4] + b"\x77\x55" + TGTPOS + FOCAL), MOVE, TAIL]
             if differ else list(a))
    return one_shot_container(sequences=[a, other, list(other)], selector=b"\x02\x00\x00\x00")


def test_a_one_track_edit_on_differing_alternates_is_refused():
    blob, _ = _three_track_container(differ=True)
    with pytest.raises(R.RescoreError, match="THREE-SEQUENCE TRAP"):
        R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)


def test_all_sequences_fans_the_delta_across_every_track():
    blob, _ = _three_track_container(differ=True)
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "all_sequences": True,
                                   "camera": {"roll": 200}}]), "t", blob=blob)
    (letter, v), = b.verdicts
    assert v.n_sequences == 3 and v.alternates_differ and v.safe
    assert len(b.check.changed_offsets) == 3        # one roll byte per track
    assert b.check.ok


def test_byte_identical_alternates_need_no_fan_out():
    blob, _ = _three_track_container(differ=False)
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    (letter, v), = b.verdicts
    assert v.has_alternates and not v.alternates_differ and v.safe


# ============================================================ (6) the self-check
def test_self_check_sees_a_broken_container():
    blob, _ = one_shot_container()
    truncated = blob[:-W.SECTOR]
    c = R.self_check(blob, truncated + b"\x00" * W.SECTOR, "t", [])
    assert c.header_ok


def test_block_invariants_hold_on_a_written_block():
    blob, _ = one_shot_container()
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    assert all(b.check.invariants.values())
    assert b.check.directory_identical


# ============================================================ (7) drift guard + provenance
def test_drift_guard_refuses_a_changed_install():
    with pytest.raises(R.StockDriftError, match="does not match"):
        R.drift_guard(227, b"not the stock bytes")


def test_drift_guard_allows_an_unregistered_effect_but_returns_its_hash():
    got = R.drift_guard(9999, b"abc")
    assert got == hashlib.sha256(b"abc").hexdigest()


def test_staging_refuses_the_repo():
    with pytest.raises(R.RescoreError, match="under the repo"):
        R._refuse_repo_path(os.path.join(R._REPO, "studies", "x"))


def test_staging_refuses_the_install_unless_explicitly_told_otherwise(tmp_path):
    game = tmp_path / "FINAL FANTASY IX"
    (game / "FF9CustomMap").mkdir(parents=True)
    with pytest.raises(R.RescoreError, match="inside the game install"):
        R._refuse_install_path(game / "FF9CustomMap", game)
    blob, _ = one_shot_container()
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    with pytest.raises(R.RescoreError, match="inside the game install"):
        R.stage(b, game / "FF9CustomMap", tmp_path / "w", game_root=game)
    out = R.stage(b, game / "FF9CustomMap", tmp_path / "w", game_root=game, allow_install=True)
    assert os.path.isfile(out["dest"])


def test_the_registered_hash_is_a_hash_not_data():
    for k, v in R.EXPECTED_STOCK_SHA.items():
        assert len(v) == 64 and all(c in "0123456789abcdef" for c in v)


# ============================================================ (8) staging + revert
def test_stage_writes_an_extensionless_override_and_a_revert_that_restores_exactly(tmp_path):
    blob, _ = one_shot_container()
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    mod = tmp_path / "mod"
    out = R.stage(b, mod, tmp_path)
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    assert dest.exists() and dest.suffix == "" and dest.read_bytes() == b.patched
    before = sorted(p.relative_to(mod).as_posix() for p in mod.rglob("*") if p.is_file())
    assert before == ["FF9_Data/SpecialEffects/ef999"]

    import subprocess
    p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert not dest.exists()
    assert not any(mod.rglob("*")) or not [q for q in mod.rglob("*") if q.is_file()]


def test_revert_restores_a_pre_existing_override_byte_for_byte(tmp_path):
    blob, _ = one_shot_container()
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    mod = tmp_path / "mod"
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    dest.parent.mkdir(parents=True)
    prior = b"an earlier override that must come back untouched"
    dest.write_bytes(prior)
    out = R.stage(b, mod, tmp_path)
    assert dest.read_bytes() == b.patched
    import subprocess
    p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert dest.read_bytes() == prior


def test_revert_is_idempotent(tmp_path):
    blob, _ = one_shot_container()
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    out = R.stage(b, tmp_path / "mod", tmp_path)
    import subprocess
    for _ in range(2):
        p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr


# ------------------------------------------------- (8b) W5: PER-EFFECT staging + a --root revert
#
# B5's defect report: `--mod-root` defaulted to `SCRATCH_ROOT/mod` = ef227's own W2 revert kit, for
# EVERY effect, and `--work-dir` defaulted to `SCRATCH_ROOT` independently -- so even a correct
# `--mod-root` still dropped the new effect's revert script inside ef227's kit.  It happened live
# (an `ef211` + `revert_summon_camera_211.py` landed in `rescore-w2/` and had to be cleaned by
# hand).  These tests pin the fix in both directions: ef227 UNMOVED (its deployed revert chain must
# keep resolving), every other effect isolated.
def _build999(blob=None):
    blob = blob or one_shot_container()[0]
    return R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                           blob=blob)


def test_ef227_keeps_w2s_staging_root_verbatim():
    """The revert-chain compat pin.  ef227's `rescore-w2/` kit is DEPLOYED and CAST-PROVEN; a rung
    that generalises the tool must not relocate it."""
    assert R.staging_root(227) == R.SCRATCH_W2_ROOT
    assert R.SCRATCH_ROOT == R.SCRATCH_W2_ROOT              # the old name still points at ef227's
    assert R.default_mod_root(227) == os.path.join(R.SCRATCH_W2_ROOT, "mod")


def test_every_other_effect_gets_its_own_per_effect_root():
    for ef in (0, 211, 251, 999):
        root = R.staging_root(ef)
        assert root == os.path.join(R.SCRATCH_W5_BASE, "ef%03d" % ef)
        assert root != R.SCRATCH_W2_ROOT
        assert R.default_mod_root(ef) == os.path.join(root, "mod")
    # ...and no two effects can ever share one
    assert len({R.staging_root(e) for e in (211, 225, 227, 251)}) == 4


def test_stage_with_no_mod_root_lands_under_the_per_effect_root(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "SCRATCH_W5_BASE", str(tmp_path / "rescore-w5"))
    b = _build999()
    out = R.stage(b)                                         # NO mod_root, NO work_dir
    want_mod = tmp_path / "rescore-w5" / "ef999" / "mod"
    assert os.path.normcase(out["mod_root"]) == os.path.normcase(str(want_mod.resolve()))
    assert (want_mod / "FF9_Data" / "SpecialEffects" / "ef999").exists()
    # the work dir is COUPLED to it -- the revert script is the effect's own, beside its own mod/
    assert os.path.normcase(os.path.dirname(out["revert_script"])) == \
        os.path.normcase(str((tmp_path / "rescore-w5" / "ef999").resolve()))
    assert "rescore-w2" not in out["revert_script"]


def test_work_dir_defaults_to_the_resolved_mod_roots_parent_not_a_module_constant(tmp_path):
    """The second half of the defect: the old default was ``SCRATCH_ROOT`` regardless of where
    ``--mod-root`` pointed, so a correct mod root still wrote the revert script into ef227's kit."""
    b = _build999()
    out = R.stage(b, tmp_path / "ef999-kit" / "mod")          # work_dir omitted
    assert os.path.normcase(os.path.dirname(out["revert_script"])) == \
        os.path.normcase(str((tmp_path / "ef999-kit").resolve()))
    assert R.SCRATCH_ROOT not in out["revert_script"]
    assert os.path.normcase(str(tmp_path)) in os.path.normcase(out["revert_script"])


def test_two_effects_staged_in_one_session_never_share_a_revert_script(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "SCRATCH_W5_BASE", str(tmp_path / "w5"))
    blob, _ = one_shot_container()
    outs = []
    for ef in (211, 251):
        b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}],
                                     effect=ef), "t", blob=blob)
        outs.append(R.stage(b))
    assert outs[0]["revert_script"] != outs[1]["revert_script"]
    assert outs[0]["mod_root"] != outs[1]["mod_root"]
    for o, ef in zip(outs, (211, 251)):
        assert ("ef%03d" % ef) in o["mod_root"]


def test_the_revert_script_takes_root_and_undoes_the_same_writes_in_another_folder(tmp_path):
    """``--root`` re-targets every mod-root-relative path the plan recorded.  Proven by staging into
    A, cloning the tree to B, and reverting B: B comes back empty and A is untouched."""
    import shutil
    import subprocess
    b = _build999()
    mod_a = tmp_path / "A" / "mod"
    out = R.stage(b, mod_a, tmp_path / "A")
    dest_a = mod_a / "FF9_Data" / "SpecialEffects" / "ef999"
    assert dest_a.exists()
    mod_b = tmp_path / "B" / "mod"
    shutil.copytree(mod_a, mod_b)
    dest_b = mod_b / "FF9_Data" / "SpecialEffects" / "ef999"

    p = subprocess.run([sys.executable, out["revert_script"], "--root", str(mod_b)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert not dest_b.exists(), "the --root folder was not reverted"
    assert dest_a.exists(), "reverting B must not touch A"
    assert mod_b.exists(), "the mod folder the caller named must never be pruned away"


def test_the_revert_scripts_default_root_is_the_staged_root(tmp_path):
    """Zero-argument behaviour is unchanged -- the baked root is still the default."""
    import subprocess
    b = _build999()
    mod = tmp_path / "mod"
    out = R.stage(b, mod, tmp_path)
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert not dest.exists()


def test_the_revert_scripts_dry_run_writes_nothing(tmp_path):
    import subprocess
    b = _build999()
    mod = tmp_path / "mod"
    out = R.stage(b, mod, tmp_path)
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    before = dest.read_bytes()
    p = subprocess.run([sys.executable, out["revert_script"], "--dry-run"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "would delete" in p.stdout and "nothing written" in p.stdout
    assert dest.read_bytes() == before


def test_the_revert_script_refuses_a_bare_root_and_an_unknown_argument(tmp_path):
    import subprocess
    b = _build999()
    out = R.stage(b, tmp_path / "mod", tmp_path)
    for argv, needle in ((["--root"], "--root needs a directory"),
                         (["--wat"], "unexpected argument")):
        p = subprocess.run([sys.executable, out["revert_script"]] + argv,
                           capture_output=True, text=True)
        assert p.returncode == 2, (argv, p.stdout, p.stderr)
        assert needle in p.stdout


def test_a_ledger_with_no_mod_root_still_emits_a_zero_argument_revert(tmp_path):
    """``retime.stage`` and ``reskin.stage`` both build an ``R._Ledger`` with NO mod root (their
    writes straddle a mod folder AND a staging-only sibling, so a half-rebase would be worse than
    none).  Adding ``--root`` must not have made THAT plan un-runnable: with nothing rebasable, the
    zero-argument run still works on absolute paths, and an explicit ``--root`` REFUSES instead of
    being silently ignored."""
    import subprocess
    lg = R._Ledger(tmp_path / "backups")                     # mod_root omitted, as the siblings do
    loose = tmp_path / "loose" / "ef999"
    lg.write_bytes(loose, b"staged bytes")
    script = lg.write_revert_script(tmp_path, "999")
    assert loose.exists()

    bad = subprocess.run([sys.executable, str(script), "--root", str(tmp_path)],
                         capture_output=True, text=True)
    assert bad.returncode == 2 and "nothing to rebase" in bad.stdout
    assert loose.exists(), "the refused run must not have written anything"

    ok = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert not loose.exists()


def test_the_revert_plan_records_mod_root_relative_paths(tmp_path):
    import ast
    import json
    b = _build999()
    mod = tmp_path / "mod"
    out = R.stage(b, mod, tmp_path)
    text = open(out["revert_script"], "r", encoding="utf-8").read()
    # the template bakes the plan as repr(json_text) -- a Python literal wrapping a JSON document
    literal = text.split("PLAN = json.loads(", 1)[1].split(")\n", 1)[0]
    plan = json.loads(ast.literal_eval(literal))
    assert plan["mod_root"]
    assert [e["rel"] for e in plan["files"]] == ["FF9_Data/SpecialEffects/ef999"]
    # a path OUTSIDE the mod root records rel=None -- never an escaping "../", which a later
    # --root would resolve into a file the caller never named
    lg = R._Ledger(tmp_path / "b2", mod_root=mod)
    lg.write_bytes(tmp_path / "elsewhere" / "x", b"outside")
    assert lg.files[-1]["rel"] is None
    assert lg._rel(mod / "FF9_Data" / "SpecialEffects" / "ef999") == "FF9_Data/SpecialEffects/ef999"
    # every recorded destination really is under the recorded mod root
    for e in plan["files"]:
        assert os.path.normcase(os.path.commonpath([e["dest"], plan["mod_root"]])) == \
            os.path.normcase(plan["mod_root"])


def test_a_modfilelist_is_appended_when_present_and_never_created(tmp_path):
    """If a mod folder HAS a ModFileList.txt, ``TryFindAssetInModOnDisc`` trusts it and never calls
    File.Exists -- an unlisted file is invisible.  But CREATING one would make every other file in
    that folder invisible, so the tool must never do that."""
    blob, _ = one_shot_container()
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    mod = tmp_path / "nolist"
    R.stage(b, mod, tmp_path / "w1")
    assert not (mod / "ModFileList.txt").exists()

    mod2 = tmp_path / "withlist"
    mod2.mkdir()
    (mod2 / "ModFileList.txt").write_text("something/else\n", encoding="utf-8")
    out = R.stage(b, mod2, tmp_path / "w2")
    assert out["modfilelist_updated"] is True
    lines = (mod2 / "ModFileList.txt").read_text(encoding="utf-8").splitlines()
    assert "specialeffects/ef999" in lines and "something/else" in lines
    import subprocess
    subprocess.run([sys.executable, out["revert_script"]], check=True)
    assert (mod2 / "ModFileList.txt").read_text(encoding="utf-8").splitlines() == ["something/else"]


# ============================================================ (9) the real spec, the real install
@needs_install
def test_the_shipped_spec_builds_against_this_install():
    spec = R.load_spec(SPEC)
    b = R.build_patched(spec, SPEC)
    assert len(b.patched) == len(b.orig)
    assert b.check.ok
    # X1: exactly the intended bytes, and every one of them inside the target block
    assert len(b.check.changed_offsets) == 4
    sp, = b.splices
    assert all(sp.lo <= o < sp.hi for o in b.check.changed_offsets)
    assert sp.diff_offsets == [13, 14, 24, 25]


@needs_install
def test_the_shipped_spec_leaves_every_duration_byte_identical():
    spec = R.load_spec(SPEC)
    b = R.build_patched(spec, SPEC)
    before = W.extract_shots(b.orig, "ef227")
    after = W.extract_shots(b.patched, "ef227")
    assert len(before.shots) == len(after.shots)
    n = 0
    for a, c in zip(before.shots, after.shots):
        for si in range(len(a.camera["sequences"])):
            ka = W.keyframes(a.camera, si)
            kc = W.keyframes(c.camera, si)
            assert [k.local_frame for k in ka] == [k.local_frame for k in kc]
            assert [k.marks for k in ka] == [k.marks for k in kc]
            for x, y in zip(ka, kc):
                for which in ("cammove", "tgtmove"):
                    ma, mc = x.movement(which), y.movement(which)
                    assert (ma or {}).get("duration") == (mc or {}).get("duration")
                    n += 1
                fa, fc = x.focal(), y.focal()
                assert (fa or {}).get("duration") == (fc or {}).get("duration")
    assert n > 20


@needs_install
def test_the_shipped_spec_leaves_every_other_subfile_and_the_directory_identical():
    import ef_container as EC
    spec = R.load_spec(SPEC)
    b = R.build_patched(spec, SPEC)
    co = EC.parse_header(b.orig, strict=True)
    cp = EC.parse_header(b.patched, strict=True)
    sp, = b.splices
    checked = 0
    for slot in range(len(co.chunks)):
        a = W.id2_directory(b.orig, co, slot)
        c = W.id2_directory(b.patched, cp, slot)
        if a is None:
            continue
        assert a.entries == c.entries and a.base == c.base and a.size == c.size
        for i in range(len(a.entries)):
            try:
                lo, hi = a.bounds(i)
            except W.SummonCameraError:
                continue
            if lo == sp.lo and hi == sp.hi:
                continue
            assert b.orig[lo:hi] == b.patched[lo:hi], (slot, i)
            checked += 1
    assert checked > 10


@needs_install
def test_the_install_still_matches_the_registered_drift_hash():
    blob, src = R.read_stock_effect(227)
    assert R.drift_guard(227, blob) == R.EXPECTED_STOCK_SHA[227]
    assert "resources.assets" in src


@needs_install
def test_the_target_block_declares_one_sequence_so_the_selector_trap_does_not_apply():
    spec = R.load_spec(SPEC)
    b = R.build_patched(spec, SPEC)
    (letter, v), = b.verdicts
    assert letter == "A"
    assert v.n_sequences == 1 and not v.has_alternates and v.safe


# ============================================================================================
# W5 -- THE GENERALISATION.  Everything below is about effects that are NOT ef227.
# ============================================================================================

# ------------------------------------------------------------ (10) THE DYNAMIC-OP DISCLOSURE
def dynamic_container(sequences=None, selector=b"\x01\x00\x00\x00", with_shot=True):
    """A container that ALSO runs a runtime-chosen (``arg2 = 3``) camera op.

    ef227 has none, which is precisely why W2's offline completeness claim does not generalise:
    324 of 1448 camera-naming ops corpus-wide pick their block from a battle-field-keyed table that
    is not in the container at all.
    """
    seqs = sequences or [[ESTABLISH, MOVE, TAIL]]
    blk = camera_block(seqs, selector=selector)
    subs = [b"\xaa" * 32, blk, b"\xbb" * 48]
    ops = [(W.OP_WAIT, 0, 10)]
    if with_shot:
        ops.append((W.OP_PLAY_CAMERA, 1, W.ARG2_LITERAL))
    ops += [(W.OP_WAIT, 0, 5), (W.OP_PLAY_CAMERA, 0, W.ARG2_TABLE)]
    return synth(subs, ops), blk


def test_dynamic_ops_are_detected_and_never_letter_enumerated():
    blob, _ = dynamic_container()
    ex = W.extract_shots(blob, "t")
    assert len(ex.shots) == 1                        # the dynamic op is NOT a shot
    dyn = R.dynamic_ops(ex)
    assert len(dyn) == 1 and dyn[0].arg2 == W.ARG2_TABLE
    text = "\n".join(R.dynamic_disclosure(7, ex))
    assert "ABSENT from these bytes" in text and "in-game cast" in text


def test_a_dynamic_container_is_refused_without_the_acknowledge_key():
    """THE DISCLOSURE GATE.  An edit addressed by (chunk, sub-file) reaches the physical block no
    matter which op resolves to that index, and the table these ops read is not in the container --
    so the author must state that the reachability is unverifiable offline."""
    blob, _ = dynamic_container()
    with pytest.raises(R.RescoreError, match="THE DYNAMIC-OP DISCLOSURE"):
        R.build_patched(spec_for([{"shot": "A", "frame": 1, "focal": {"distance": 96}}]),
                        "t", blob=blob)


def test_the_gate_fires_before_the_edit_is_even_resolved():
    """A spec whose [[edit]] names no field would be refused anyway -- the disclosure must come
    FIRST, or a half-written spec for a dynamic effect gets the wrong error and the risk is never
    read."""
    blob, _ = dynamic_container()
    with pytest.raises(R.RescoreError, match="THE DYNAMIC-OP DISCLOSURE"):
        R.build_patched(spec_for([{"shot": "A", "frame": 1}]), "t", blob=blob)


def test_the_acknowledge_key_lets_a_dynamic_container_build():
    blob, _ = dynamic_container()
    spec = spec_for([{"shot": "A", "frame": 1, "focal": {"distance": 96}}])
    spec["rescore"]["acknowledge_dynamic_ops"] = True
    b = R.build_patched(spec, "t", blob=blob)
    assert b.check.ok and b.acknowledged and len(b.dynamic) == 1
    assert "ACKNOWLEDGED" in "\n".join(R.describe(b))


def test_a_stale_acknowledgement_is_refused():
    """``= true`` on a container with ZERO dynamic ops is a spec copied off another effect. A safety
    key that was never true here must not be allowed to look satisfied."""
    blob, _ = one_shot_container()
    spec = spec_for([{"shot": "A", "frame": 1, "focal": {"distance": 96}}])
    spec["rescore"]["acknowledge_dynamic_ops"] = True
    with pytest.raises(R.RescoreError, match="runs NO runtime-chosen camera op"):
        R.build_patched(spec, "t", blob=blob)


def test_the_acknowledge_key_must_be_a_literal_boolean():
    """A truthy string must never satisfy a safety gate -- and the check lives in ``build_patched``
    as well as ``load_spec``, because in-memory specs never pass through the file reader."""
    blob, _ = dynamic_container()
    for bad in ("true", "yes", 1):
        spec = spec_for([{"shot": "A", "frame": 1, "focal": {"distance": 96}}])
        spec["rescore"]["acknowledge_dynamic_ops"] = bad
        with pytest.raises(R.RescoreError, match="must be a BOOLEAN"):
            R.build_patched(spec, "t", blob=blob)


def test_a_container_with_no_statically_resolved_shot_cannot_be_scaffolded():
    blob, _ = dynamic_container(with_shot=False)
    ex = W.extract_shots(blob, "t")
    assert not ex.shots and len(R.dynamic_ops(ex)) == 1
    with pytest.raises(R.RescoreError, match="no statically-resolved camera shot"):
        R.choose_target(ex)


# ------------------------------------------------------------ (11) strict spec keys
def _write(tmp_path, text):
    p = tmp_path / "s.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_an_unknown_rescore_key_is_refused(tmp_path):
    """A mistyped ``expect_sha256`` would fail OPEN -- the drift guard would vanish with no error.
    So an unrecognised key is refused rather than ignored."""
    p = _write(tmp_path, '[rescore]\neffect = 999\nexpect_sha_256 = "ab"\n'
                         '[[edit]]\nshot = "A"\nframe = 1\n')
    with pytest.raises(R.RescoreError, match="unknown key.*expect_sha_256"):
        R.load_spec(p)


def test_an_unknown_edit_key_is_refused(tmp_path):
    p = _write(tmp_path, '[rescore]\neffect = 999\n[[edit]]\nshot = "A"\nframe = 1\nzoom = 3\n')
    with pytest.raises(R.RescoreError, match="unknown key.*zoom"):
        R.load_spec(p)


def test_an_unknown_top_level_table_is_refused(tmp_path):
    p = _write(tmp_path, '[rescore]\neffect = 999\n[[edit]]\nshot = "A"\nframe = 1\n[retime]\nx = 1\n')
    with pytest.raises(R.RescoreError, match="unknown key.*retime"):
        R.load_spec(p)


def test_a_non_boolean_acknowledgement_is_refused_by_the_file_reader_too(tmp_path):
    p = _write(tmp_path, '[rescore]\neffect = 999\nacknowledge_dynamic_ops = "true"\n'
                         '[[edit]]\nshot = "A"\nframe = 1\n')
    with pytest.raises(R.RescoreError, match="must be a BOOLEAN"):
        R.load_spec(p)


def test_the_shipped_ef227_spec_still_loads_under_the_strict_key_check():
    """ef227 byte-compat starts here: the legacy spec must keep parsing unchanged."""
    spec = R.load_spec(SPEC)
    assert spec["rescore"]["effect"] == 227
    assert set(spec["rescore"]) <= R._RESCORE_KEYS
    for e in spec["edit"]:
        assert set(e) <= R._EDIT_KEYS


# ------------------------------------------------------------ (12) `init` -- the scaffold
def test_the_scaffold_prefers_the_focal_lever_and_is_an_identity():
    """H first, by law not by convenience (THE EFFECT-OWNED SCENERY LAW: focal distance reframes
    without moving the eye, so it exposes less of the effect's own set than a pose change)."""
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")
    t = sc.target
    assert t.section == "focal" and t.frame == 1 and t.identity
    assert t.values == {"distance": 300}             # FOCAL's own H, read back out of the block
    assert not t.all_sequences and not t.ambiguous
    assert "IDENTITY" in sc.text and "acknowledge_dynamic_ops" not in sc.text


def test_the_generated_identity_spec_rebuilds_the_container_byte_identical(tmp_path):
    """The whole point of an identity scaffold: the resolution path (drift guard, shot address,
    alternates, splice, self-check) is proven BEFORE any judgement about art is involved."""
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")
    p = R.write_scaffold(sc, tmp_path / "ef999_rescore.toml")
    b = R.build_patched(R.load_spec(p), str(p), blob=blob)
    assert b.patched == b.orig
    assert b.check.changed_offsets == [] and b.check.ok


def test_the_scaffold_falls_back_to_the_pose_pair_when_no_shot_carries_a_focal():
    blob, _ = one_shot_container(sequences=[[MOVE, TAIL]])
    sc = R.scaffold(999, blob, "t")
    assert sc.target.section == "camera" and sc.target.frame == 30
    assert set(sc.target.values) == {"orientation", "roll"} and sc.target.identity
    assert "no shot here carries a focal" in sc.text


def test_the_scaffold_emits_all_sequences_when_the_alternates_differ():
    blob, _ = _three_track_container(differ=True)
    sc = R.scaffold(999, blob, "t")
    assert sc.target.all_sequences and "all_sequences = true" in sc.text
    assert sc.shots[0].alternates_differ and sc.shots[0].n_sequences == 3


def test_the_scaffold_refuses_to_claim_an_identity_when_the_tracks_disagree():
    """A value that is an identity on track 0 is a real, unjudged change on a track that holds a
    different one -- so the lever is left COMMENTED rather than pre-filled."""
    a = [ESTABLISH, MOVE, TAIL]
    other = [code(1, 0x0809, CAMPOS + TGTPOS + FOCAL2), MOVE, TAIL]     # same shape, other H
    blob, _ = one_shot_container(sequences=[a, other, list(other)],
                                 selector=b"\x02\x00\x00\x00")
    sc = R.scaffold(999, blob, "t")
    t = sc.target
    assert t.all_sequences and not t.identity
    assert "do not hold the same focal value" in t.why_not
    assert "\n# focal  = {" in sc.text and "\nfocal    = {" not in sc.text
    assert t.per_track[0]["distance"] == 300 and t.per_track[1]["distance"] == 400


def test_the_scaffold_emits_an_occurrence_for_an_ambiguous_frame():
    """Two Codes on one local frame (a placement plus the move it starts) is a stock idiom; the
    scaffold must say which one it aimed at or the build refuses the ambiguity."""
    dup = [code(1, 0x0002, CAMPOS + struct.pack("<HBB", 24, 2, 0)), ESTABLISH, TAIL]
    blob, _ = one_shot_container(sequences=[dup])
    sc = R.scaffold(999, blob, "t")
    assert sc.target.ambiguous and sc.target.occurrence == 1 and sc.target.section == "focal"
    assert "occurrence = 1" in sc.text
    b = R.build_patched(_parse(sc.text), "t", blob=blob)
    assert b.patched == b.orig


def _parse(text):
    import tomllib
    return tomllib.loads(text)


def test_the_scaffold_pre_seeds_the_acknowledge_key_false_when_dynamic_ops_exist():
    blob, _ = dynamic_container()
    sc = R.scaffold(999, blob, "t")
    assert len(sc.dynamic) == 1
    assert "acknowledge_dynamic_ops = false" in sc.text
    assert "DYNAMIC (RUNTIME-CHOSEN) CAMERA OPS: 1" in sc.text
    # and the spec it generates is REFUSED until a human flips it
    spec = _parse(sc.text)
    spec["edit"][0]["focal"] = {"distance": 96}
    with pytest.raises(R.RescoreError, match="THE DYNAMIC-OP DISCLOSURE"):
        R.build_patched(spec, "t", blob=blob)
    spec["rescore"]["acknowledge_dynamic_ops"] = True
    assert R.build_patched(spec, "t", blob=blob).check.ok


def test_every_generated_scaffold_parses_and_survives_the_strict_key_check(tmp_path):
    for name, (blob, _blk) in (("plain", one_shot_container()),
                               ("dynamic", dynamic_container()),
                               ("alternates", _three_track_container(differ=True)),
                               ("pose-only", one_shot_container(sequences=[[MOVE, TAIL]]))):
        sc = R.scaffold(999, blob, "t")
        p = R.write_scaffold(sc, tmp_path / ("%s.toml" % name))
        spec = R.load_spec(p)                       # strict keys, boolean acknowledge, [[edit]] shape
        assert spec["rescore"]["effect"] == 999
        assert spec["rescore"]["expect_sha256"] == hashlib.sha256(blob).hexdigest()


def test_write_scaffold_refuses_to_overwrite_an_authored_spec_without_force(tmp_path):
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")
    p = tmp_path / "ef999_rescore.toml"
    R.write_scaffold(sc, p)
    with pytest.raises(R.RescoreError, match="refuses to overwrite"):
        R.write_scaffold(sc, p)
    R.write_scaffold(sc, p, force=True)             # explicit is fine


def test_the_scaffold_quote_budget_is_enforced_at_the_write_site():
    """A generated spec is an AUTHORED file: it may name the values its own edit writes and nothing
    more.  A decoded stock listing belongs in ``summon_camera.py read``'s stdout."""
    R._quote_check([("a", 1)] * R.SCAFFOLD_QUOTE_BUDGET)
    with pytest.raises(R.RescoreError, match="budget"):
        R._quote_check([("a", 1)] * (R.SCAFFOLD_QUOTE_BUDGET + 1))


def test_a_scaffold_that_would_overrun_the_budget_drops_the_values_instead_of_the_gate():
    """Three disagreeing tracks x a two-field pose pair is 6 quotes -- over budget.  The scaffold
    must degrade to a pointer at `summon_camera.py read`, never breach the ceiling."""
    a = [MOVE, TAIL]
    other = [code(30, 0x0002, b"\x2a\x40\x30\x0c\x11\x1e" + struct.pack("<HBB", 24, 2, 0)), TAIL]
    blob, _ = one_shot_container(sequences=[a, other, list(other)],
                                 selector=b"\x02\x00\x00\x00")
    sc = R.scaffold(999, blob, "t")
    assert sc.target.section == "camera" and not sc.target.identity
    assert len(sc.quoted) <= R.SCAFFOLD_QUOTE_BUDGET
    assert "summon_camera.py read" in sc.text


def test_the_scaffold_reports_the_shot_table_without_dumping_keyframes():
    """Structure (letters, addresses, ticks, counts, frame numbers) is derived metadata; poses and
    H values are stock DATA.  The scaffold carries the first and points at the second."""
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")
    (row,) = sc.shots
    assert (row.letter, row.slot, row.subfile) == ("A", 0, 1)
    assert row.n_keyframes == 3 and row.focal_frames == (1,)
    assert row.frames == ((1, 1), (30, 1), (60, 1))
    assert "pitch=" not in sc.text and "orientation =" not in sc.text
    assert "py summon_camera.py read 999" in sc.text


def test_scaffold_bytes_refuses_a_corpus_copy_that_drifted_from_the_install(monkeypatch):
    """The scaffold writes the hash the BUILD will check, and the build always reads the install.
    A corpus copy that no longer matches would write a guard nothing can ever satisfy."""
    monkeypatch.setattr(W, "_load", lambda ef, root=None: (b"corpus bytes", "ef042"))
    monkeypatch.setattr(R, "read_stock_effect", lambda ef, game=None: (b"install bytes", "res"))
    with pytest.raises(R.StockDriftError, match="does NOT match this install"):
        R.scaffold_bytes(42, from_corpus=True)
    monkeypatch.setattr(R, "read_stock_effect", lambda ef, game=None: (b"corpus bytes", "res"))
    blob, src = R.scaffold_bytes(42, from_corpus=True)
    assert blob == b"corpus bytes" and "sha-identical" in src


def test_scaffold_bytes_falls_back_to_the_corpus_when_no_install_is_resolvable(monkeypatch):
    monkeypatch.setattr(W, "_load", lambda ef, root=None: (b"corpus bytes", "ef042"))

    def boom(ef, game=None):
        raise R.RescoreError("no install")
    monkeypatch.setattr(R, "read_stock_effect", boom)
    blob, src = R.scaffold_bytes(42, from_corpus=True)
    assert blob == b"corpus bytes" and "no install resolvable" in src


# ------------------------------------------------------------ (13) the phase cross-reference
def test_phase_rows_place_r3_phases_on_the_sequence_clock():
    """``merged_timeline``'s own derivation, reused: a phase boundary is the ``0x80+N`` op's own
    tick plus R3's phase start.  A machine whose chunk never ran program 0 contributes NOTHING
    rather than being placed at a guessed origin."""
    class _Case:
        def roles(self):
            return ["draws effect models"]

    class _Ph:
        def __init__(self, state, start, ticks):
            self.state, self.start_tick, self.ticks, self.case = state, start, ticks, _Case()

    class _SM:
        image = "ef999:c0"
        phases = (_Ph(0, 0, 10), _Ph(1, 10, None))

    class _SM_other:
        image = "ef999:c9"                            # a chunk that never ran a program
        phases = (_Ph(0, 0, 10),)

    blob, _ = one_shot_container()
    ex = W.extract_shots(blob, "t")
    rows = R._phase_rows(ex, (_SM(), _SM_other()))
    start = ex.walk.program_starts.get((0, 0))
    assert start is None or [(p.state, p.start, p.end) for p in rows] == \
        [(0, start, start + 9), (1, start + 10, None)]
    assert all(p.image == "ef999:c0" for p in rows)   # c9 contributed nothing


def test_a_shot_with_no_recovered_phase_reports_the_budget_as_unknown():
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")                   # no machines passed
    assert not sc.shots[0].phases
    assert "reframe budget is" in sc.text and "UNKNOWN, not loose" in sc.text


# ------------------------------------------------------------ (14) CLI ergonomics
def test_a_bare_plan_no_longer_silently_defaults_to_bahamut():
    """A tool that scaffolds any effect must not rebuild ef227 when you meant yours -- "nothing
    changed" is the symptom of every misresolution in this rung."""
    with pytest.raises(R.RescoreError, match="no default any more"):
        R.resolve_spec(None, None)


def test_resolve_spec_finds_the_standard_filename_for_an_ef(tmp_path):
    (tmp_path / "ef211_rescore.toml").write_text("x", encoding="utf-8")
    assert R.resolve_spec(None, 211, tmp_path).endswith("ef211_rescore.toml")
    assert R.resolve_spec("given.toml", 211, tmp_path) == "given.toml"


def test_resolve_spec_refuses_an_ef_with_no_spec(tmp_path):
    with pytest.raises(R.RescoreError, match="init --ef 42"):
        R.resolve_spec(None, 42, tmp_path)


def test_the_cli_presents_a_refusal_as_a_refusal_not_a_traceback(capsys):
    """A refusal is a RESULT of this tool. A traceback buries the paragraph the author is meant to
    read -- the disclosure, the drift, the ambiguous frame -- under a stack."""
    assert R.cli(["plan"]) == 2
    assert "REFUSED" in capsys.readouterr().err
    with pytest.raises(R.RescoreError):
        R.main(["plan"])                                # main() still raises, for the gate runner


def test_the_spec_registry_pins_ef227_externally_and_discovers_the_rest(tmp_path):
    """``(toml, expected effect)``: ef227's entry carries an EXTERNAL expectation so a spec that
    changed its own ``effect`` is caught; a discovered sibling has none, and inventing one from a
    filename would be a guess."""
    (tmp_path / "bahamut_rescore.toml").write_text("x", encoding="utf-8")
    (tmp_path / "phoenix_rescore.toml").write_text("x", encoding="utf-8")
    (tmp_path / "notes.toml").write_text("x", encoding="utf-8")
    got = [(os.path.basename(p), e) for p, e in R.discover_specs(tmp_path)]
    assert got == [("bahamut_rescore.toml", 227), ("phoenix_rescore.toml", None)]
    assert ("bahamut_rescore.toml", 227) == \
        (os.path.basename(R.discover_specs()[0][0]), R.discover_specs()[0][1])


# ------------------------------------------------------------ (15) the corpus, the real thing
@needs_corpus
def test_the_scaffold_derives_ef211_phoenix_exactly():
    """W5's second-proof target: one shot, one sequence, 17 keyframes, one focal at f87."""
    blob, _ = W._load(211)
    sc = R.scaffold(211, blob, "ef211", W.recover_machines(blob, "ef211"))
    (row,) = sc.shots
    assert (row.letter, row.slot, row.subfile, row.kind) == ("A", 0, 8, "PLAY_CAMERA")
    assert row.n_sequences == 1 and row.n_keyframes == 17 and row.focal_frames == (87,)
    assert not sc.dynamic
    assert sc.target.section == "focal" and sc.target.frame == 87 and sc.target.identity
    assert row.phases and row.draws_set          # the reframe budget is TIGHT here
    assert "reframe budget: TIGHT" in sc.text


@needs_corpus
def test_the_ef211_scaffold_rebuilds_the_stock_container_byte_identical():
    blob, _ = W._load(211)
    sc = R.scaffold(211, blob, "ef211")
    b = R.build_patched(_parse(sc.text), "ef211", blob=blob)
    assert b.patched == b.orig and b.check.ok
    assert b.guard.startswith("the spec's own expect_sha256")


@needs_corpus
def test_the_scaffold_derives_ef000_with_all_three_traps():
    """ef000 carries every trap ef227 sidesteps at once: 0x23-only addressing, a runtime-chosen op,
    and three genuinely differing alternate takes on every shot."""
    blob, _ = W._load(0)
    sc = R.scaffold(0, blob, "ef000")
    assert len(sc.shots) == 3 and all(r.kind == "SETUP_CAMERA" for r in sc.shots)
    assert all(r.alternates_differ and r.n_sequences == 3 for r in sc.shots)
    assert len(sc.dynamic) == 1 and sc.dynamic[0].arg2 == W.ARG2_TABLE
    assert "acknowledge_dynamic_ops = false" in sc.text
    t = sc.target
    assert t.letter == "B" and t.all_sequences and t.ambiguous and t.occurrence == 1
    assert not t.identity and "do not hold the same focal value" in t.why_not


@needs_corpus
def test_the_dynamic_gate_fires_on_the_real_ef000_and_lifts_with_the_key():
    blob, _ = W._load(0)
    spec = _parse(R.scaffold(0, blob, "ef000").text)
    spec["edit"][0]["focal"] = {"distance": 240}
    with pytest.raises(R.RescoreError, match="THE DYNAMIC-OP DISCLOSURE"):
        R.build_patched(spec, "ef000", blob=blob)
    spec["rescore"]["acknowledge_dynamic_ops"] = True
    b = R.build_patched(spec, "ef000", blob=blob)
    assert b.check.ok and len(b.check.changed_offsets) == 6      # 2 bytes of H x 3 tracks
    (letter, v), = b.verdicts
    assert letter == "B" and v.alternates_differ and v.safe


@needs_corpus
def test_the_scaffold_survives_the_whole_corpus():
    """The generalisation claim, falsifiable: every extracted container either scaffolds or REFUSES
    with a named reason.  No crash, no traceback, no silent success on bytes we cannot address.

    It also measures how far ef227 is from typical: 300 of the 342 scaffoldable containers carry a
    runtime-chosen camera op, so the DISCLOSURE GATE is the normal path and ef227's silence about
    it was the exception.
    """
    ok, refused, seen_dynamic = 0, 0, 0
    for p in W.corpus_paths():
        with open(p, "rb") as fh:
            blob = fh.read()
        ef = int(os.path.basename(p)[2:5])
        try:
            sc = R.scaffold(ef, blob, os.path.basename(p))
        except R.RescoreError as e:
            assert "no lever for a rescore to pull" in str(e), os.path.basename(p)
            refused += 1
            continue
        ok += 1
        seen_dynamic += bool(sc.dynamic)
        assert sc.text.startswith("# TIER W")
        assert _parse(sc.text)["rescore"]["effect"] == ef
        assert (sc.target.identity) == ("THIS IS AN IDENTITY" in sc.text)
        assert bool(sc.dynamic) == ("acknowledge_dynamic_ops = false" in sc.text)
    assert ok + refused == len(W.corpus_paths())
    assert ok > 300 and refused >= 25 and seen_dynamic > 250


@needs_corpus
def test_every_scaffolded_identity_really_rebuilds_its_container_byte_identical():
    """The identity claim is checked, not asserted: an identity scaffold must produce ZERO changed
    bytes over EVERY container it claims one for -- otherwise "run it first to prove the whole path
    resolves" is a lie."""
    n = 0
    for p in W.corpus_paths():
        with open(p, "rb") as fh:
            blob = fh.read()
        ef = int(os.path.basename(p)[2:5])
        try:
            sc = R.scaffold(ef, blob, os.path.basename(p))
        except R.RescoreError:
            continue
        if not sc.target.identity or sc.dynamic:
            continue                                  # a dynamic container needs the ack key first
        b = R.build_patched(_parse(sc.text), "t", blob=blob)
        assert b.patched == b.orig and b.check.ok, os.path.basename(p)
        n += 1
    assert n > 30


@needs_install
def test_the_ef227_spec_still_builds_the_exact_same_container_after_w5():
    """ef227 BYTE-COMPAT, the hard gate: the shipped spec's output is pinned by hash, not by the
    fact that it built."""
    b = R.build_patched(R.load_spec(SPEC), SPEC)
    assert hashlib.sha256(b.patched).hexdigest() == \
        "8146eff43a1448e3a2fd3ffe4cdc760f8d93dcdb2696c1c1022cee3ecf13beb8"
    assert not b.dynamic and not b.acknowledged
    assert b.guard == "the spec's own expect_sha256 -- MATCHES"
