r"""``summons.rescore`` -- THE CONTENT RESCORE: the field map, every refusal, the ledger, the scaffold.

TWO LANES, the suite's game-gated pattern:

  * PURE LOGIC -- always runs. Every unit test SYNTHESISES its own container with the builders below,
    so the Code field map, all sixteen refusals, the same-length splice, the three-sequence trap, the
    dynamic-op disclosure, the self-check and the whole write ledger are exercised on bytes this file
    wrote. No install, no extracted corpus, no stock bytes.
  * INSTALL-GATED -- the byte-identity acceptance. The promoted kit module must rebuild the study's
    cast-proven ef227 container from the study's own shipped spec, byte for byte. Skips cleanly when
    the install, UnityPy, or the study tree is absent.

The field values below are AUTHORED, not copied -- the same literals W1e swept the whole stock corpus
for and found nowhere in it. The builders mirror ``test_summons_camera.py``'s deliberately: each test
file stands alone, because a cross-file test import is one more way for a fresh checkout to collect
nothing and still report green.

    py -m pytest tests/test_summon_rescore.py -q          # from ff9mapkit/
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from ff9mapkit.battle import camera_codec as CC
from ff9mapkit.summons import camera as W
from ff9mapkit.summons import container as C
from ff9mapkit.summons import rescore as R


# ============================================================ the gates
def _game():
    try:
        from ff9mapkit import config
        return config.find_game_path()
    except Exception:
        return None


def _have_unitypy() -> bool:
    try:
        import UnityPy                                          # noqa: F401
        return True
    except Exception:
        return False


#: the study's own shipped ef227 spec -- the byte-identity acceptance reads it from the repo it lives
#: in, and skips when there is none (an installed wheel carries no ``studies/`` tree).
STUDY_SPEC = (Path(__file__).resolve().parents[2] / "studies" / "custom-summons" / "tier-w"
              / "bahamut_rescore.toml")

needs_install = pytest.mark.skipif(_game() is None, reason="no FF9 install resolvable")
needs_unitypy = pytest.mark.skipif(not _have_unitypy(),
                                   reason="UnityPy not importable (the `assets` extra)")
needs_study_spec = pytest.mark.skipif(not STUDY_SPEC.is_file(),
                                      reason="no studies/ tree in this checkout (%s)" % STUDY_SPEC)

#: what the study's cast-proven ef227 rescore produces. Pinned by HASH, not by "it built".
EF227_RESCORED_SHA = "8146eff43a1448e3a2fd3ffe4cdc760f8d93dcdb2696c1c1022cee3ecf13beb8"


# ============================================================ synthetic containers
def code(frame, flags, block=b""):
    return struct.pack("<HH", frame, flags) + block


def camera_block(sequences, selector=b"\x01\x00\x00\x00", anchors=None):
    """A real-grammar SFX camera block: Flags + one u16 offset per present group + the groups."""
    flags = 0
    blocks = []
    for i, seq in enumerate(sequences):
        flags |= (1 << i)
        blocks.append(b"".join(seq) + struct.pack("<H", 0))
    if selector is not None:
        flags |= 0x08
        blocks.append(selector)
    if anchors:
        flags |= sum(1 << (4 + i) for i in range(len(anchors)))
        blocks.append(b"".join(struct.pack("<3h", *a) for a in anchors))
    cur = 2 + 2 * len(blocks)
    table = b""
    for b in blocks:
        table += struct.pack("<H", cur)
        cur += len(b)
    return struct.pack("<H", flags) + table + b"".join(blocks)


def sequence_stream(ops):
    out = bytearray()
    for c, a1, a2 in ops:
        out += bytes((c, a1, a2))
    return bytes(out) + bytes((W.OP_END, 0, 0))


def synth(subfiles, ops, extra_sectors=0, chunks=1):
    """A whole ef###.bytes-shaped container: sector 0 (header + sequence @0x400), then per chunk the
    id-2 archive (directory + sub-files)."""
    per = []
    for ci in range(chunks):
        subs = subfiles[ci] if isinstance(subfiles[0], list) else subfiles
        table, body, cur, offs = bytearray(), bytearray(), 4 * len(subs), []
        for s in subs:
            offs.append(cur)
            body += s
            cur += len(s)
        for o in offs:
            table += struct.pack("<i", o)
        payload = bytes(table) + bytes(body)
        sectors = max(1, (len(payload) + W.SECTOR - 1) // W.SECTOR)
        per.append((sectors, payload.ljust(sectors * W.SECTOR, b"\x00")))

    head = bytearray(struct.pack("<h", chunks))
    for ci, (sectors, _p) in enumerate(per):
        head += struct.pack("<hh", ci, 1)
        head += struct.pack("<bbh", 2, 1 if extra_sectors else 0, sectors)
        if extra_sectors:
            head += struct.pack("<h", extra_sectors)
    blob = bytearray(head.ljust(W.SECTOR, b"\x00"))
    blob[0x400:0x400 + len(sequence_stream(ops))] = sequence_stream(ops)
    for _s, payload in per:
        blob += b"\x00" * (extra_sectors * W.SECTOR)
        blob += payload
    return bytes(blob)


CAMPOS = b"\x2a\x40\x33\x0d\x11\x1f"        # code, flags, pitch, orientation, roll, distance
TGTPOS = b"\x2a\x40\x07\x03\x01\x02"
FOCAL = b"\x07\x03\x2c\x01"                  # duration 7, flags 3, H = 300
FOCAL2 = b"\x07\x03\x90\x01"                 # ...        H = 400
MARKER = b"\x11\x22\x33\x44"

ESTABLISH = code(1, 0x0809, CAMPOS + TGTPOS + FOCAL)
MOVE = code(30, 0x0002, b"\x2a\x40\x30\x0c\x10\x1e" + struct.pack("<HBB", 24, 2, 0))
TAIL = code(60, 0x8000, MARKER)


def one_shot_container(sequences=None, selector=b"\x01\x00\x00\x00"):
    """A container whose sequence plays ONE camera at chunk 0 sub-file 1."""
    blk = camera_block(sequences or [[ESTABLISH, MOVE, TAIL]], selector=selector)
    subs = [b"\xaa" * 32, blk, b"\xbb" * 48]
    ops = [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, 0), (W.OP_WAIT, 0, 20)]
    return synth(subs, ops), blk


def two_shot_container():
    """Two PLAY_CAMERA ops -> shots A (sub-file 1) and B (sub-file 3)."""
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    subs = [b"\xaa" * 32, blk, b"\xbb" * 48, blk, b"\xcc" * 16]
    ops = [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, 0),
           (W.OP_WAIT, 0, 20), (W.OP_PLAY_CAMERA, 3, 0)]
    return synth(subs, ops)


def dynamic_container(sequences=None, selector=b"\x01\x00\x00\x00", with_shot=True):
    """A container that ALSO runs a runtime-chosen (``arg2 = 3``) camera op -- the normal corpus
    shape, and precisely what ef227 (the effect this lane was first proven on) does NOT have."""
    blk = camera_block(sequences or [[ESTABLISH, MOVE, TAIL]], selector=selector)
    subs = [b"\xaa" * 32, blk, b"\xbb" * 48]
    ops = [(W.OP_WAIT, 0, 10)]
    if with_shot:
        ops.append((W.OP_PLAY_CAMERA, 1, W.ARG2_LITERAL))
    ops += [(W.OP_WAIT, 0, 5), (W.OP_PLAY_CAMERA, 0, W.ARG2_TABLE)]
    return synth(subs, ops), blk


def three_track_container(differ=True):
    a = [ESTABLISH, MOVE, TAIL]
    other = ([code(1, 0x0809, CAMPOS[:4] + b"\x77\x55" + TGTPOS + FOCAL), MOVE, TAIL]
             if differ else list(a))
    return one_shot_container(sequences=[a, other, list(other)], selector=b"\x02\x00\x00\x00")


def spec_for(edits, effect=999, expect=None):
    r = {"effect": effect, "label": "t"}
    if expect:
        r["expect_sha256"] = expect
    return {"rescore": r, "edit": edits}


def _build(edits, **kw):
    blob, _ = one_shot_container(**kw)
    return R.build_patched(spec_for(edits), "t", blob=blob)


def _build999(blob=None):
    blob = blob or one_shot_container()[0]
    return R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                           blob=blob)


def _parse(text):
    return tomllib.loads(text)


def _write(tmp_path, text):
    p = tmp_path / "s.toml"
    p.write_text(text, encoding="utf-8")
    return p


# ============================================================ (1) the Code field map
def test_field_offsets_agree_with_the_codec_on_an_exhaustive_flag_sweep():
    """``code_field_offsets`` must walk EXACTLY the layout ``camera_codec.split_code`` slices -- it is
    what tells a splice which four bytes are the focal and not the two after it. Swept over every
    flag word rather than sampled: the two are pinned to agree, so a codec field-order change fails
    HERE instead of writing into the wrong four bytes."""
    payload = bytes(range(1, 65))
    checked = 0
    for flags in range(0x10000):
        if flags & 0x0100:                      # 0x100 has no field in the codec's reader
            continue
        want = CC.split_code(flags, payload)
        got = R.code_field_offsets(flags)
        assert set(got) == set(want), flags
        for name, (off, size) in got.items():
            assert payload[off:off + size] == want[name], (hex(flags), name)
        checked += 1
    assert checked > 30000


# ============================================================ (2) the edit + its refusals
def test_a_pose_and_a_focal_edit_change_exactly_the_named_bytes():
    b = _build([{"shot": "A", "frame": 1, "camera": {"roll": 200}, "focal": {"distance": 96}}])
    assert len(b.patched) == len(b.orig)
    assert len(b.check.changed_offsets) == 3        # roll (1B) + H (2B)
    assert b.check.ok


def test_durations_are_refused():
    """CONSTRAINT 1. A duration is a CLOCK: the camera and the effect's program are two clocks the
    original author kept aligned by construction, and a content rescore moves neither."""
    for section, key in (("focal", "duration"), ("camera_move", "duration")):
        with pytest.raises(R.RescoreError, match="CLOCK"):
            _build([{"shot": "A", "frame": 30 if section == "camera_move" else 1,
                     section: {key: 5}}])


def test_every_refused_key_is_refused_from_the_one_table():
    """All three clock keys, not just the two a synthetic container happens to reach."""
    assert set(R._REFUSED) == {("focal", "duration"), ("camera_move", "duration"),
                               ("target_move", "duration")}


def test_a_field_the_flags_do_not_declare_is_refused():
    """MOVE (frame 30) carries campos + cammove and no focal. Writing a focal there would land in
    whatever follows -- a same-length splice would not catch it, so it is refused up front."""
    with pytest.raises(R.RescoreError, match="no focal sub-block"):
        _build([{"shot": "A", "frame": 30, "focal": {"distance": 96}}])


def test_out_of_range_values_are_refused_per_field_width():
    with pytest.raises(R.RescoreError, match="out of range"):
        _build([{"shot": "A", "frame": 1, "camera": {"roll": 256}}])
    with pytest.raises(R.RescoreError, match="out of range"):
        _build([{"shot": "A", "frame": 1, "focal": {"distance": 65536}}])
    assert _build([{"shot": "A", "frame": 1, "focal": {"distance": 65535}}]).check.ok


def test_unknown_field_names_are_refused():
    with pytest.raises(R.RescoreError, match="unknown pose field"):
        _build([{"shot": "A", "frame": 1, "camera": {"zoom": 3}}])
    with pytest.raises(R.RescoreError, match="unknown focal field"):
        _build([{"shot": "A", "frame": 1, "focal": {"zoom": 3}}])
    with pytest.raises(R.RescoreError, match="unknown movement field"):
        _build([{"shot": "A", "frame": 30, "camera_move": {"zoom": 3}}])


def test_a_section_that_is_not_a_table_is_refused():
    with pytest.raises(R.RescoreError, match="must be a table"):
        _build([{"shot": "A", "frame": 1, "camera": 7}])


def test_an_edit_that_changes_nothing_is_refused():
    with pytest.raises(R.RescoreError, match="changes nothing"):
        _build([{"shot": "A", "frame": 1}])


def test_a_missing_frame_is_refused():
    with pytest.raises(R.RescoreError, match="no `frame`"):
        _build([{"shot": "A", "camera": {"roll": 9}}])
    with pytest.raises(R.RescoreError, match="no keyframe at local frame"):
        _build([{"shot": "A", "frame": 77, "camera": {"roll": 9}}])


def test_an_edit_naming_no_shot_at_all_is_refused():
    with pytest.raises(R.RescoreError, match="must name a shot"):
        _build([{"frame": 1, "camera": {"roll": 9}}])


def test_an_unknown_shot_letter_is_refused():
    with pytest.raises(R.RescoreError, match="no shot 'Z'"):
        _build([{"shot": "Z", "frame": 1, "camera": {"roll": 9}}])


def test_shot_letter_and_chunk_subfile_must_agree():
    """A mismatch means the read-out this spec was written against is not the read-out of the bytes
    in front of us. That is a refusal, not a preference for one of the two addresses."""
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


def test_a_sequence_index_the_block_does_not_declare_is_refused():
    with pytest.raises(R.RescoreError, match="no sequence2"):
        _build([{"shot": "A", "sequence": 2, "frame": 1, "camera": {"roll": 9}}])


def test_an_ambiguous_frame_needs_an_occurrence():
    """Two Codes at the same local frame (a placement plus the move it starts) is a real stock idiom.
    Picking one at random would be a coin-flip."""
    dup = [ESTABLISH, code(1, 0x0002, CAMPOS + struct.pack("<HBB", 24, 2, 0)), TAIL]
    with pytest.raises(R.RescoreError, match="Add `occurrence`|occurrence = 0"):
        _build([{"shot": "A", "frame": 1, "camera": {"roll": 9}}], sequences=[dup])
    assert _build([{"shot": "A", "frame": 1, "occurrence": 1, "camera": {"roll": 9}}],
                  sequences=[dup]).check.ok


def test_an_out_of_range_occurrence_is_refused():
    with pytest.raises(R.RescoreError, match="occurrence 3 out of range"):
        _build([{"shot": "A", "frame": 1, "occurrence": 3, "camera": {"roll": 9}}])


# ============================================================ (3) the same-length splice
def test_rescore_block_refuses_a_length_change():
    """CONSTRAINT 2. A camera sub-file's length is the delta to the NEXT id-2 directory entry and the
    slack is 0-2 bytes corpus-wide, so only a SAME-SIZE splice is legal."""
    blob, _ = one_shot_container()
    shot = W.extract_shots(blob, "t").shots[0]
    shot.camera["sequences"][0].insert(
        1, {"frame": 15, "flags": 0x0002, "block": CAMPOS + struct.pack("<HBB", 4, 0, 0)})
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
    """CONSTRAINT 3. This lane writes no frame word at all -- the strongest way to preserve the
    undecoded 0xE000 marks."""
    marked = [code(0x4001, 0x0809, CAMPOS + TGTPOS + FOCAL), MOVE, TAIL]
    blob, _ = one_shot_container(sequences=[marked])
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    ex = W.extract_shots(b.patched, "t")
    assert ex.shots[0].camera["sequences"][0][0]["frame"] == 0x4001
    assert W.frame_marks(ex.shots[0].camera["sequences"][0][0]["frame"]) == 0x4000


# ============================================================ (4) THE THREE-SEQUENCE TRAP
def test_a_one_track_edit_on_differing_alternates_is_refused():
    blob, _ = three_track_container(differ=True)
    with pytest.raises(R.RescoreError, match="THREE-SEQUENCE TRAP"):
        R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)


def test_all_sequences_fans_the_delta_across_every_track():
    blob, _ = three_track_container(differ=True)
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "all_sequences": True,
                                   "camera": {"roll": 200}}]), "t", blob=blob)
    (letter, v), = b.verdicts
    assert v.n_sequences == 3 and v.alternates_differ and v.safe
    assert len(b.check.changed_offsets) == 3        # one roll byte per track
    assert b.check.ok


def test_byte_identical_alternates_need_no_fan_out():
    blob, _ = three_track_container(differ=False)
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}]), "t",
                        blob=blob)
    (letter, v), = b.verdicts
    assert v.has_alternates and not v.alternates_differ and v.safe


def test_the_alternates_signature_is_taken_before_the_edit_not_after():
    """Taken afterwards it is a lie in the most dangerous direction: editing track 0 of a block whose
    alternates really WERE identical makes them look "genuinely different", and the trap check would
    then wave through exactly the one-track edit it exists to refuse."""
    blob, _ = three_track_container(differ=False)
    shot = W.extract_shots(blob, "t").shots[0]
    before = R.alternates_signature(shot)
    assert before == [True, True, True]
    shot.camera["sequences"][0][0]["block"] = b"\x00" * len(shot.camera["sequences"][0][0]["block"])
    assert R.alternates_signature(shot) == [True, False, False]      # the inverted reading
    assert R.check_alternates(before, [0]).safe                      # the honest one


# ============================================================ (5) the self-check
def test_self_check_sees_the_container_it_was_handed():
    blob, _ = one_shot_container()
    truncated = blob[:-W.SECTOR]
    c = R.self_check(blob, truncated + b"\x00" * W.SECTOR, "t", [])
    assert c.header_ok


def test_block_invariants_hold_on_a_written_block():
    b = _build999()
    assert all(b.check.invariants.values())
    assert b.check.directory_identical
    assert set(b.check.invariants) == {
        "i1_first_offset_is_table_end", "i2_offsets_strictly_increasing",
        "i3_last_group_is_not_a_sequence", "i4_block_is_not_the_last_subfile"}


# ============================================================ (6) drift guard + provenance
def test_drift_guard_refuses_a_changed_install():
    with pytest.raises(R.StockDriftError, match="does not match"):
        R.drift_guard(227, b"not the stock bytes")


def test_drift_guard_allows_an_unregistered_effect_but_returns_its_hash():
    assert R.drift_guard(9999, b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_a_spec_pinned_hash_guards_an_unregistered_effect():
    """On a tool that takes ANY summon, the spec's own ``expect_sha256`` is the normal guard -- so it
    must bite, and the report must not call the build "unguarded"."""
    blob, _ = one_shot_container()
    good = hashlib.sha256(blob).hexdigest()
    b = R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}], expect=good),
                        "t", blob=blob)
    assert b.guard == "the spec's own expect_sha256 -- MATCHES"
    with pytest.raises(R.StockDriftError, match="does not match"):
        R.build_patched(spec_for([{"shot": "A", "frame": 1, "camera": {"roll": 200}}],
                                 expect="00" * 32), "t", blob=blob)


def test_an_unpinned_unregistered_effect_says_it_is_unguarded():
    assert _build999().guard == "none -- UNGUARDED (this spec pins no expect_sha256)"


def test_the_registered_hash_is_a_hash_not_data():
    for k, v in R.EXPECTED_STOCK_SHA.items():
        assert len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def test_staging_refuses_a_git_checkout_by_ancestry_not_by_a_hardcoded_root(tmp_path):
    """The predecessor derived the repo root from ``__file__`` by counting directories up -- only
    ACCIDENTALLY correct after a move and silently wrong in a wheel, i.e. a provenance guard that
    fails OPEN. This one refuses ANY ancestor holding ``.git``, so it catches this repo, a worktree
    and any other clone without knowing where any of them are."""
    (tmp_path / "some-clone" / ".git").mkdir(parents=True)
    with pytest.raises(R.RescoreError, match="under the repo"):
        R._refuse_repo_path(tmp_path / "some-clone" / "studies" / "x")
    # ...and a ``.git`` FILE (which is what a worktree has) counts exactly the same
    (tmp_path / "wt").mkdir()
    (tmp_path / "wt" / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    with pytest.raises(R.RescoreError, match="under the repo"):
        R._refuse_repo_path(tmp_path / "wt" / "out")


def test_staging_refuses_the_checkout_this_test_actually_lives_in():
    """The guard is only worth anything if it bites the real tree, not just a fixture."""
    with pytest.raises(R.RescoreError, match="under the repo"):
        R._refuse_repo_path(Path(__file__).resolve().parent / "scratch-out")


def test_staging_refuses_a_memoria_mod_asset_tree(tmp_path):
    with pytest.raises(R.RescoreError, match="StreamingAssets"):
        R._refuse_repo_path(tmp_path / "FF9CustomMap" / "StreamingAssets" / "Sounds")


def test_staging_refuses_the_install_unless_explicitly_told_otherwise(tmp_path):
    game = tmp_path / "FINAL FANTASY IX"
    (game / "FF9CustomMap").mkdir(parents=True)
    with pytest.raises(R.RescoreError, match="inside the game install"):
        R._refuse_install_path(game / "FF9CustomMap", game)
    b = _build999()
    with pytest.raises(R.RescoreError, match="inside the game install"):
        R.stage(b, game / "FF9CustomMap", tmp_path / "w", game_root=game)
    out = R.stage(b, game / "FF9CustomMap", tmp_path / "w", game_root=game, allow_install=True)
    assert os.path.isfile(out["dest"])


def test_the_install_guard_needs_a_root_to_check_against(tmp_path):
    """``game_root=None`` means "no install is in play" -- a normal offline state, and not a licence
    to skip a check that HAD a root."""
    assert R._refuse_install_path(tmp_path / "x", None) == (tmp_path / "x").resolve()


# ============================================================ (7) staging roots
def test_every_effect_gets_its_own_staging_root(tmp_path):
    """PER EFFECT, not shared. With one root for every effect, building a second summon drops its
    container and its revert script INSIDE the first one's kit."""
    for ef in (0, 211, 227, 251, 999):
        root = R.staging_root(ef, tmp_path)
        assert root == os.path.join(str(tmp_path), "ef%03d" % ef)
        assert R.default_mod_root(ef, tmp_path) == os.path.join(root, "mod")
    assert len({R.staging_root(e, tmp_path) for e in (211, 225, 227, 251)}) == 4


def test_the_default_staging_base_is_local_only_by_construction():
    from ff9mapkit.summons import export
    assert R.STAGING_BASE == export.DEFAULT_OUT_DIR / "rescore"
    assert export.assert_local_only(R.STAGING_BASE)              # refuses repo / mod tree / install


def test_a_legacy_pin_relocates_one_effect_and_only_that_one(tmp_path, monkeypatch):
    """A pin exists only for an effect whose staged revert chain is already DEPLOYED somewhere and
    must not be relocated -- per-installation history, not a property of the tool. So the kit ships
    the map EMPTY and a caller who carries such history re-pins it."""
    assert R.LEGACY_STAGING == {}
    monkeypatch.setattr(R, "LEGACY_STAGING", {227: str(tmp_path / "frozen")})
    assert R.staging_root(227, tmp_path) == str(tmp_path / "frozen")
    assert R.default_mod_root(227, tmp_path) == os.path.join(str(tmp_path / "frozen"), "mod")
    assert R.staging_root(211, tmp_path) == os.path.join(str(tmp_path), "ef211")


def test_stage_with_no_mod_root_lands_under_the_per_effect_root(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "STAGING_BASE", tmp_path / "rescore")
    out = R.stage(_build999())                                   # NO mod_root, NO work_dir
    want_mod = tmp_path / "rescore" / "ef999" / "mod"
    assert os.path.normcase(out["mod_root"]) == os.path.normcase(str(want_mod.resolve()))
    assert (want_mod / "FF9_Data" / "SpecialEffects" / "ef999").exists()
    # the work dir is COUPLED to it -- the revert script is the effect's own, beside its own mod/
    assert os.path.normcase(os.path.dirname(out["revert_script"])) == \
        os.path.normcase(str((tmp_path / "rescore" / "ef999").resolve()))


def test_work_dir_defaults_to_the_resolved_mod_roots_parent_not_a_module_constant(tmp_path):
    """A module-constant default means pointing the mod root at effect B still writes effect B's
    revert script into effect A's kit -- a correct flag was not enough to keep two effects apart."""
    out = R.stage(_build999(), tmp_path / "ef999-kit" / "mod")   # work_dir omitted
    assert os.path.normcase(os.path.dirname(out["revert_script"])) == \
        os.path.normcase(str((tmp_path / "ef999-kit").resolve()))
    assert str(R.STAGING_BASE) not in out["revert_script"]


def test_two_effects_staged_in_one_session_never_share_a_revert_script(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "STAGING_BASE", tmp_path / "w5")
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


# ============================================================ (8) staging + the revert ledger
def test_stage_writes_an_extensionless_override_and_a_revert_that_restores_exactly(tmp_path):
    b = _build999()
    mod = tmp_path / "mod"
    out = R.stage(b, mod, tmp_path)
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    assert dest.exists() and dest.suffix == "" and dest.read_bytes() == b.patched
    before = sorted(p.relative_to(mod).as_posix() for p in mod.rglob("*") if p.is_file())
    assert before == ["FF9_Data/SpecialEffects/ef999"]

    p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert not dest.exists()
    assert not [q for q in mod.rglob("*") if q.is_file()]


def test_revert_restores_a_pre_existing_override_byte_for_byte(tmp_path):
    b = _build999()
    mod = tmp_path / "mod"
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    dest.parent.mkdir(parents=True)
    prior = b"an earlier override that must come back untouched"
    dest.write_bytes(prior)
    out = R.stage(b, mod, tmp_path)
    assert dest.read_bytes() == b.patched
    p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert dest.read_bytes() == prior                            # RESTORE, not delete


def test_revert_is_idempotent(tmp_path):
    out = R.stage(_build999(), tmp_path / "mod", tmp_path)
    for _ in range(2):
        p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr


def test_the_revert_script_takes_root_and_undoes_the_same_writes_in_another_folder(tmp_path):
    """``--root`` re-targets every mod-root-relative path the plan recorded. Proven by staging into
    A, cloning the tree to B, and reverting B: B comes back empty and A is untouched."""
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
    mod = tmp_path / "mod"
    out = R.stage(_build999(), mod, tmp_path)
    p = subprocess.run([sys.executable, out["revert_script"]], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert not (mod / "FF9_Data" / "SpecialEffects" / "ef999").exists()


def test_the_revert_scripts_dry_run_writes_nothing(tmp_path):
    mod = tmp_path / "mod"
    out = R.stage(_build999(), mod, tmp_path)
    dest = mod / "FF9_Data" / "SpecialEffects" / "ef999"
    before = dest.read_bytes()
    p = subprocess.run([sys.executable, out["revert_script"], "--dry-run"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "would delete" in p.stdout and "nothing written" in p.stdout
    assert dest.read_bytes() == before


def test_the_revert_script_refuses_a_bare_root_and_an_unknown_argument(tmp_path):
    out = R.stage(_build999(), tmp_path / "mod", tmp_path)
    for argv, needle in ((["--root"], "--root needs a directory"),
                         (["--wat"], "unexpected argument")):
        p = subprocess.run([sys.executable, out["revert_script"]] + argv,
                           capture_output=True, text=True)
        assert p.returncode == 2, (argv, p.stdout, p.stderr)
        assert needle in p.stdout


def test_a_ledger_with_no_mod_root_still_emits_a_zero_argument_revert(tmp_path):
    """A lane whose writes straddle a mod folder AND a staging-only sibling records absolute paths
    only (a HALF-rebased revert would be worse than an un-rebasable one). Adding ``--root`` must not
    have made THAT plan un-runnable -- and an explicit ``--root`` must REFUSE rather than be silently
    ignored, because a caller who believes they re-targeted a revert that in fact did not is worse
    off than one who got an error."""
    lg = R.Ledger(tmp_path / "backups")                          # mod_root omitted
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
    b = _build999()
    mod = tmp_path / "mod"
    out = R.stage(b, mod, tmp_path)
    text = Path(out["revert_script"]).read_text(encoding="utf-8")
    # the template bakes the plan as repr(json_text) -- a Python literal wrapping a JSON document
    literal = text.split("PLAN = json.loads(", 1)[1].split(")\n", 1)[0]
    plan = json.loads(ast.literal_eval(literal))
    assert plan["mod_root"]
    assert [e["rel"] for e in plan["files"]] == ["FF9_Data/SpecialEffects/ef999"]
    for e in plan["files"]:
        assert os.path.normcase(os.path.commonpath([e["dest"], plan["mod_root"]])) == \
            os.path.normcase(plan["mod_root"])


def test_a_path_outside_the_mod_root_records_no_rebase_key(tmp_path):
    """``None``, never an escaping ``../``: a relative path that climbs out of the root would let a
    later ``--root`` resolve into a file the caller never named."""
    mod = tmp_path / "mod"
    lg = R.Ledger(tmp_path / "b2", mod_root=mod)
    lg.write_bytes(tmp_path / "elsewhere" / "x", b"outside")
    assert lg.files[-1]["rel"] is None
    assert lg._rel(mod / "FF9_Data" / "SpecialEffects" / "ef999") == "FF9_Data/SpecialEffects/ef999"


def test_the_ledger_records_delete_for_a_new_file_and_restore_for_an_existing_one(tmp_path):
    """RULES 1 AND 2, at the record level. A newly created file records ``backup = None`` so the
    revert DELETES it; a pre-existing one is backed up first so the revert RESTORES it. Recording the
    two the same way would either resurrect a file that never existed or destroy one that did."""
    mod = tmp_path / "mod"
    (mod / "sub").mkdir(parents=True)
    (mod / "sub" / "old").write_bytes(b"was here first")
    lg = R.Ledger(tmp_path / "backups", mod_root=mod)
    lg.write_bytes(mod / "sub" / "new", b"brand new")
    lg.write_bytes(mod / "sub" / "old", b"overwritten")
    assert [e["backup"] is None for e in lg.files] == [True, False]
    assert Path(lg.files[1]["backup"]).read_bytes() == b"was here first"
    assert [e["rel"] for e in lg.files] == ["sub/new", "sub/old"]

    script = lg.write_revert_script(tmp_path, "t")
    p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert not (mod / "sub" / "new").exists()                    # deleted
    assert (mod / "sub" / "old").read_bytes() == b"was here first"   # restored


def test_the_ledger_is_the_one_implementation_under_both_of_its_names():
    from ff9mapkit.summons import ledger
    assert R.Ledger is ledger.Ledger and ledger._Ledger is ledger.Ledger
    assert issubclass(ledger.LedgerError, RuntimeError)
    assert ledger._REVERT_TEMPLATE is ledger.REVERT_TEMPLATE


# ---- THE MODFILELIST POSTURE
def test_a_modfilelist_is_appended_when_present_and_never_created(tmp_path):
    """If a mod folder HAS a ModFileList.txt, ``TryFindAssetInModOnDisc`` trusts it and never calls
    File.Exists -- an unlisted file is invisible. But CREATING one would make every other file in
    that folder invisible, so the tool must never do that."""
    b = _build999()
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
    subprocess.run([sys.executable, out["revert_script"]], check=True)
    assert (mod2 / "ModFileList.txt").read_text(encoding="utf-8").splitlines() == ["something/else"]


def test_the_deploy_posture_refuses_a_folder_that_carries_a_list(tmp_path):
    """The DEPLOY path refuses rather than half-owning a registry whose format this lane does not
    own, in a folder somebody else's tooling maintains."""
    mod = tmp_path / "withlist"
    mod.mkdir()
    assert R.modfilelist_refusal(mod) is None
    (mod / "ModFileList.txt").write_text("something/else\n", encoding="utf-8")
    why = R.modfilelist_refusal(mod)
    assert why and "REFUSING to deploy" in why and "Nothing changed" in why
    with pytest.raises(R.RescoreError, match="REFUSING to deploy"):
        R.stage(_build999(), mod, tmp_path / "w", refuse_modfilelist=True)
    assert not (mod / "FF9_Data").exists(), "the refusal must come BEFORE any write"


# ---- verify
def test_verify_tells_missing_from_divergent_from_matching(tmp_path):
    """The point is not "did the file get written" but "are the bytes at the override path the bytes
    this spec produces from THIS install today" -- so it re-derives rather than trusting a hash."""
    b = _build999()
    mod = tmp_path / "mod"
    v = R.verify(b, mod)
    assert not v["ok"] and "nothing staged" in v["reason"] and v["sha256"] is None
    R.stage(b, mod, tmp_path)
    v = R.verify(b, mod)
    assert v["ok"] and v["sha256"] == b.sha_out and "matches the rebuild" in v["reason"]
    Path(v["dest"]).write_bytes(b"someone else wrote this")
    v = R.verify(b, mod)
    assert not v["ok"] and "DIVERGES" in v["reason"]


# ============================================================ (9) THE DYNAMIC-OP DISCLOSURE
def test_dynamic_ops_are_detected_and_never_letter_enumerated():
    blob, _ = dynamic_container()
    ex = W.extract_shots(blob, "t")
    assert len(ex.shots) == 1                        # the dynamic op is NOT a shot
    dyn = R.dynamic_ops(ex)
    assert len(dyn) == 1 and dyn[0].arg2 == W.ARG2_TABLE
    text = "\n".join(R.dynamic_disclosure(7, ex))
    assert "ABSENT from these bytes" in text and "in-game cast" in text
    assert R.dynamic_disclosure(7, W.extract_shots(one_shot_container()[0], "t")) == []


def test_a_dynamic_container_is_refused_without_the_acknowledge_key():
    """THE DISCLOSURE GATE. An edit addressed by (chunk, sub-file) reaches the physical block no
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


def test_describe_reports_both_disclosure_states():
    lines = "\n".join(R.describe(_build999()))
    assert "0 runtime-chosen camera ops" in lines
    assert "THE THREE-SEQUENCE CHECK" in lines and "SELF-CHECK" in lines


# ============================================================ (10) strict spec keys
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
    """Including ``[retime]`` -- the retime lane is STUDY-ONLY and a kit spec may not declare it."""
    p = _write(tmp_path, '[rescore]\neffect = 999\n[[edit]]\nshot = "A"\nframe = 1\n[retime]\nx = 1\n')
    with pytest.raises(R.RescoreError, match="unknown key.*retime"):
        R.load_spec(p)


def test_a_non_boolean_acknowledgement_is_refused_by_the_file_reader_too(tmp_path):
    p = _write(tmp_path, '[rescore]\neffect = 999\nacknowledge_dynamic_ops = "true"\n'
                         '[[edit]]\nshot = "A"\nframe = 1\n')
    with pytest.raises(R.RescoreError, match="must be a BOOLEAN"):
        R.load_spec(p)


def test_a_spec_with_no_rescore_table_or_no_edits_is_refused(tmp_path):
    with pytest.raises(R.RescoreError, match="no \\[rescore\\] table"):
        R.load_spec(_write(tmp_path, '[[edit]]\nshot = "A"\n'))
    with pytest.raises(R.RescoreError, match="needs `effect`"):
        R.load_spec(_write(tmp_path, '[rescore]\nlabel = "x"\n[[edit]]\nshot = "A"\n'))
    with pytest.raises(R.RescoreError, match="declares no \\[\\[edit\\]\\]"):
        R.load_spec(_write(tmp_path, '[rescore]\neffect = 999\n'))


# ============================================================ (11) THE SCAFFOLD
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


def test_a_container_with_no_lever_at_all_is_refused_not_scaffolded():
    """A minority of stock containers are of this class -- a camera block whose only Code is the
    trailing marker. There is nothing to reframe; this is a refusal, not a failure."""
    blob, _ = one_shot_container(sequences=[[TAIL]])
    with pytest.raises(R.RescoreError, match="no lever for a rescore to pull"):
        R.scaffold(999, blob, "t")


def test_the_scaffold_emits_all_sequences_when_the_alternates_differ():
    blob, _ = three_track_container(differ=True)
    sc = R.scaffold(999, blob, "t")
    assert sc.target.all_sequences and "all_sequences = true" in sc.text
    assert sc.shots[0].alternates_differ and sc.shots[0].n_sequences == 3


def test_the_scaffold_refuses_to_claim_an_identity_when_the_tracks_disagree():
    """A value that is an identity on track 0 is a real, unjudged change on a track that holds a
    different one -- so the lever is left COMMENTED rather than pre-filled."""
    a = [ESTABLISH, MOVE, TAIL]
    other = [code(1, 0x0809, CAMPOS + TGTPOS + FOCAL2), MOVE, TAIL]     # same shape, other H
    blob, _ = one_shot_container(sequences=[a, other, list(other)], selector=b"\x02\x00\x00\x00")
    sc = R.scaffold(999, blob, "t")
    t = sc.target
    assert t.all_sequences and not t.identity
    assert "do not hold the same focal value" in t.why_not
    assert "\n# focal  = {" in sc.text and "\nfocal    = {" not in sc.text
    assert t.per_track[0]["distance"] == 300 and t.per_track[1]["distance"] == 400


def test_the_scaffold_emits_an_occurrence_for_an_ambiguous_frame():
    dup = [code(1, 0x0002, CAMPOS + struct.pack("<HBB", 24, 2, 0)), ESTABLISH, TAIL]
    blob, _ = one_shot_container(sequences=[dup])
    sc = R.scaffold(999, blob, "t")
    assert sc.target.ambiguous and sc.target.occurrence == 1 and sc.target.section == "focal"
    assert "occurrence = 1" in sc.text
    assert R.build_patched(_parse(sc.text), "t", blob=blob).patched == blob


def test_the_scaffold_pre_seeds_the_acknowledge_key_false_when_dynamic_ops_exist():
    blob, _ = dynamic_container()
    sc = R.scaffold(999, blob, "t")
    assert len(sc.dynamic) == 1
    assert "acknowledge_dynamic_ops = false" in sc.text
    assert "DYNAMIC (RUNTIME-CHOSEN) CAMERA OPS: 1" in sc.text
    # ...and the spec it generates is REFUSED until a human flips it
    spec = _parse(sc.text)
    spec["edit"][0]["focal"] = {"distance": 96}
    with pytest.raises(R.RescoreError, match="THE DYNAMIC-OP DISCLOSURE"):
        R.build_patched(spec, "t", blob=blob)
    spec["rescore"]["acknowledge_dynamic_ops"] = True
    assert R.build_patched(spec, "t", blob=blob).check.ok


def test_every_generated_scaffold_parses_and_survives_the_strict_key_check(tmp_path):
    for name, (blob, _blk) in (("plain", one_shot_container()),
                               ("dynamic", dynamic_container()),
                               ("alternates", three_track_container(differ=True)),
                               ("pose-only", one_shot_container(sequences=[[MOVE, TAIL]]))):
        sc = R.scaffold(999, blob, "t")
        p = R.write_scaffold(sc, tmp_path / ("%s.toml" % name))
        spec = R.load_spec(p)                       # strict keys, boolean acknowledge, [[edit]] shape
        assert spec["rescore"]["effect"] == 999
        assert spec["rescore"]["expect_sha256"] == hashlib.sha256(blob).hexdigest()


def test_write_scaffold_refuses_to_overwrite_an_authored_spec_without_force(tmp_path):
    """Silently replacing an author's finished spec with a generated starting point is the single
    most destructive thing this verb could do."""
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")
    p = tmp_path / "ef999_rescore.toml"
    R.write_scaffold(sc, p)
    with pytest.raises(R.RescoreError, match="refuses to overwrite"):
        R.write_scaffold(sc, p)
    R.write_scaffold(sc, p, force=True)             # explicit is fine


def test_the_scaffold_quote_budget_is_enforced_at_the_write_site():
    """A generated spec is an AUTHORED file: it may name the values its own edit writes and nothing
    more. A decoded stock listing belongs on stdout."""
    R._quote_check([("a", 1)] * R.SCAFFOLD_QUOTE_BUDGET)
    with pytest.raises(R.RescoreError, match="budget"):
        R._quote_check([("a", 1)] * (R.SCAFFOLD_QUOTE_BUDGET + 1))


def test_a_scaffold_that_would_overrun_the_budget_drops_the_values_instead_of_the_gate():
    """Three disagreeing tracks x a two-field pose pair is 6 quotes -- over budget. The scaffold must
    degrade to a pointer at the read verb, never breach the ceiling."""
    a = [MOVE, TAIL]
    other = [code(30, 0x0002, b"\x2a\x40\x30\x0c\x11\x1e" + struct.pack("<HBB", 24, 2, 0)), TAIL]
    blob, _ = one_shot_container(sequences=[a, other, list(other)], selector=b"\x02\x00\x00\x00")
    sc = R.scaffold(999, blob, "t")
    assert sc.target.section == "camera" and not sc.target.identity
    assert len(sc.quoted) <= R.SCAFFOLD_QUOTE_BUDGET
    assert "read the read-out to see them" in sc.text


def test_the_scaffold_reports_the_shot_table_without_dumping_keyframes():
    """Structure (letters, addresses, ticks, counts, frame numbers) is derived metadata; poses and H
    values are stock DATA. The scaffold carries the first and points at the second."""
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")
    (row,) = sc.shots
    assert (row.letter, row.slot, row.subfile) == ("A", 0, 1)
    assert row.n_keyframes == 3 and row.focal_frames == (1,)
    assert row.frames == ((1, 1), (30, 1), (60, 1))
    assert "pitch=" not in sc.text and "orientation =" not in sc.text
    assert "ff9mapkit summon-rescore read --ef 999" in sc.text


def test_scaffold_summary_is_a_screen_not_a_dump():
    blob, _ = one_shot_container()
    lines = R.scaffold_summary(R.scaffold(999, blob, "t"))
    text = "\n".join(lines)
    assert "THE DYNAMIC-OP DISCLOSURE: none" in text
    assert "IDENTITY" in text and "reframe budget UNKNOWN" in text
    assert "pitch=" not in text


# ============================================================ (12) the phase cross-reference
class _Case:
    def roles(self):
        return ["draws effect models"]


class _Ph:
    def __init__(self, state, start, ticks):
        self.state, self.start_tick, self.ticks, self.case = state, start, ticks, _Case()


class _SM:
    image = "ef999:c0"
    phases = (_Ph(0, 0, 10), _Ph(1, 10, None))


class _SMOther:
    image = "ef999:c9"                            # a chunk that never ran a program
    phases = (_Ph(0, 0, 10),)


def test_phase_rows_place_recovered_phases_on_the_sequence_clock():
    """A phase boundary is the ``0x80+N`` op's own tick plus the phase start. A machine whose chunk
    never ran program 0 contributes NOTHING rather than being placed at a guessed origin."""
    blk = camera_block([[ESTABLISH, MOVE, TAIL]])
    blob = synth([b"\xaa" * 32, blk, b"\xbb" * 48],
                 [(W.OP_WAIT, 0, 10), (W.OP_PLAY_CAMERA, 1, 0), (W.OP_RUN_PROGRAM, 0, 0)])
    ex = W.extract_shots(blob, "t")
    start = ex.walk.program_starts[(0, 0)]
    rows = R._phase_rows(ex, (_SM(), _SMOther()))
    assert [(p.state, p.start, p.end) for p in rows] == \
        [(0, start, start + 9), (1, start + 10, None)]
    assert all(p.image == "ef999:c0" for p in rows)   # c9 contributed nothing
    assert rows[0].draws_set


def test_a_shot_with_no_recovered_phase_reports_the_budget_as_unknown():
    """The kit ships no MIPS disassembler, so ``machines`` is empty and the reframe budget is
    reported as UNKNOWN -- an absent judgement, not a favourable one."""
    blob, _ = one_shot_container()
    sc = R.scaffold(999, blob, "t")                   # no machines passed
    assert not sc.shots[0].phases
    assert "reframe budget is then UNKNOWN" in sc.text and "not loose" in sc.text


# ============================================================ (13) ORTHOGONALITY -- the retime lane
def test_the_retime_lane_is_out_of_kit_scope_on_every_surface():
    """SCOPE, stated as a test rather than as a note. The retime lane -- which moves DURATIONS and
    must carry the program's phase constants with it -- stayed in the study. The kit must not
    half-ship it: no module to import, no ``[retime]`` table a spec may declare, and every duration
    key refused BY NAME rather than quietly accepted as an ordinary field."""
    with pytest.raises(ModuleNotFoundError):
        __import__("ff9mapkit.summons.retime")
    assert "retime" not in R._SPEC_KEYS
    assert ("focal", "duration") in R._REFUSED
    assert "duration" not in R.POSE_FIELDS                   # nor by another name on a pose


# ============================================================ (14) INSTALL-GATED ACCEPTANCE
# The promoted module must regenerate the study's CAST-PROVEN artefact byte for byte, from the
# study's own committed spec. Pinned by hash, not by "it built".
@needs_install
@needs_unitypy
@needs_study_spec
def test_the_shipped_ef227_spec_builds_the_cast_proven_container_byte_for_byte():
    b = R.build_patched(R.load_spec(STUDY_SPEC), str(STUDY_SPEC))
    assert hashlib.sha256(b.patched).hexdigest() == EF227_RESCORED_SHA
    assert b.guard == "the spec's own expect_sha256 -- MATCHES"
    assert not b.dynamic and not b.acknowledged
    assert len(b.patched) == len(b.orig)


@needs_install
@needs_unitypy
@needs_study_spec
def test_the_shipped_spec_changes_exactly_four_bytes_all_inside_the_target_block():
    b = R.build_patched(R.load_spec(STUDY_SPEC), str(STUDY_SPEC))
    assert b.check.ok
    assert len(b.check.changed_offsets) == 4
    sp, = b.splices
    assert all(sp.lo <= o < sp.hi for o in b.check.changed_offsets)
    assert sp.diff_offsets == [13, 14, 24, 25]


@needs_install
@needs_unitypy
@needs_study_spec
def test_the_shipped_spec_leaves_every_duration_byte_identical():
    b = R.build_patched(R.load_spec(STUDY_SPEC), str(STUDY_SPEC))
    before = W.extract_shots(b.orig, "ef227")
    after = W.extract_shots(b.patched, "ef227")
    assert len(before.shots) == len(after.shots)
    n = 0
    for a, c in zip(before.shots, after.shots):
        for si in range(len(a.camera["sequences"])):
            ka, kc = W.keyframes(a.camera, si), W.keyframes(c.camera, si)
            assert [k.local_frame for k in ka] == [k.local_frame for k in kc]
            assert [k.marks for k in ka] == [k.marks for k in kc]
            for x, y in zip(ka, kc):
                for which in ("cammove", "tgtmove"):
                    assert (x.movement(which) or {}).get("duration") == \
                           (y.movement(which) or {}).get("duration")
                    n += 1
                assert (x.focal() or {}).get("duration") == (y.focal() or {}).get("duration")
    assert n > 20


@needs_install
@needs_unitypy
@needs_study_spec
def test_the_shipped_spec_leaves_every_other_subfile_and_the_directory_identical():
    b = R.build_patched(R.load_spec(STUDY_SPEC), str(STUDY_SPEC))
    co = C.parse_header(b.orig, strict=True)
    cp = C.parse_header(b.patched, strict=True)
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
@needs_unitypy
def test_the_install_still_matches_the_registered_drift_hash():
    blob, src = R.read_stock_effect(227)
    assert R.drift_guard(227, blob) == R.EXPECTED_STOCK_SHA[227]
    assert "resources.assets" in src


@needs_install
@needs_unitypy
def test_a_stock_effect_this_install_does_not_carry_is_refused_by_name():
    with pytest.raises(R.RescoreError, match="no TextAsset"):
        R.read_stock_effect(998)
