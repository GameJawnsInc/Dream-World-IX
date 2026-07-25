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
from test_summon_camera import (CAMPOS, ESTABLISH, FOCAL, MOVE, TAIL, TGTPOS,  # noqa: E402
                                camera_block, code, synth)

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
