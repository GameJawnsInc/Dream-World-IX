"""THE CAMERA DECODE -- parse the LEGACY native ``ef227.bytes`` container (Bahamut's real donor
binary, the thing ``FF9SpecialEffectPlugin.dll`` is fed via ``SFX_Play``) and pull out its BAKED
CAMERA TRACK, in the open, without any DLL disassembly.

Why this exists: the s47 mesh-probe reconstruction (``PROBE.md``, ``build_thomas.py``'s ``THE FLIGHT
v2``) derives Thomas's flight path from the CREATURE's own mesh bounds -- accurate for gross position,
but it also has to *guess* where the camera cuts are (a position discontinuity is a decent proxy for a
cut, but it can't tell a real cut from a fast in-shot reposition). This module reads the REAL camera
track instead, straight out of the same container the native plugin reads.

THE FILE ITSELF -- located, not assumed (per mission): ``ef227`` is NOT a loose file anywhere in the
install (every ``StreamingAssets/Data/SpecialEffects/ef227/`` only holds the MODERN re-implemented
``PlayerSequence.seq``/``Sequence.seq`` text pair -- confirmed by a filesystem sweep this session). The
legacy binary is a Unity ``TextAsset`` packed inside ``x64/FF9_Data/resources.assets`` (590MB), found by
opening it with UnityPy (the kit's own extraction idiom, ``ff9mapkit.extract._unitypy``) and searching
for a ``TextAsset`` named ``"ef227"`` -- confirmed present, path_id 3807, 823,296 bytes, sha256
``fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167`` (this session's read, recorded
here purely as a drift guard a la ``build_thomas.py``'s ``EXPECTED_DONOR_SHA256`` -- the bytes
themselves are NEVER written into this repo, only to a caller-supplied scratch path). The managed
call site that proves this IS the buffer the native plugin renders:
``Global/SFX/SFX.cs:1974-1979`` -- ``String path = $"SpecialEffects/ef{(Int32)effNum:D3}";
Byte[] binAsset = AssetManager.LoadBytes(path, true); ... SFX.SFX_Play((Int32)effNum,
binHandle.AddrOfPinnedObject(), binAsset.Length, ...)`` -- and ``AssetManager.LoadBytes`` bottoms out
in ``Resources.Load<TextAsset>(name)`` (``Global/Asset/AssetManager.cs:658-666,535`` chain), i.e. a
Unity ``Resources`` folder TextAsset, exactly where this script finds it.

THE CONTAINER SPEC (``SFXBinaryFile.cs`` -- CAVEAT per the mission brief: dead code, zero live C#
callers found by grep, never validated before this session -- treated here as a draft, validated
byte-for-byte below):

  - u16 ``chunkCount``, then per chunk: u16 ``chunkIndex``, u16 ``resourceCount``, then per resource:
    u8 ``id``, u8 ``info``, u16 ``size`` (``SFXBinaryFile.cs:37-76``). Resource id ``2`` marks the
    chunk's own "small file" (PSX CD-sector-style sub-archive) region; sizes are in 0x800-byte (2048,
    the literal PSX CD sector size) units -- textbook confirmation this is genuine ported PS1-era data,
    matching PLAN.md's own PDB-string finding (``psx_compatibility.cpp``, ``PsxEmulator.cpp``).
  - **VALIDATED THIS SESSION**: walking that table for the real ``ef227.bytes`` and summing
    ``resourcePosition`` (the running byte cursor) lands EXACTLY on the file's own length
    (823,296 / 0xc9000, to the byte) -- the single strongest possible confirmation the chunk-table
    shape is correct, since nothing forces that equality except a correct parse.
  - Each chunk's small-file region is a second directory table (``SFXBinaryFile.cs:82-118``): the
    first u16 is (`entryCount*4`), interpreted as byte-offsets into the small-file region; the
    directory self-describes its own length. **VALIDATED**: every one of the 82 combined small-file
    entries across both of ef227's 2 chunks decodes to an in-bounds slice with no reader overrun.
  - From byte offset 0x400, a flat opcode stream of 3-byte ``(code, arg1, arg2)`` triples
    (``SFXBinaryFile.cs:120-134``, the ``SequenceCode`` enum) runs until ``END`` (0x00). ``LOAD_CHUNK``
    (0x05) selects the active chunk; ``SETUP_CAMERA``(0x23)/``PLAY_CAMERA``(0x29, arg2==0) each mark a
    ``(chunk, small-file-arg)`` pair as a camera resource. **VALIDATED**: this stream decodes cleanly
    (93 ops, terminates on a real ``END``, zero garbage codes outside the enum's own numeric gaps which
    the commented-out debug dump in the source itself already anticipates as "???" holes) and its
    ``PLAY_SOUND`` (0x2D) ops land on exactly the akao/small-file indices ``ef227``'s own real
    ``Sequence.seq`` text file is already known (README.md/PLAN.md) to reference by similar small
    numbers -- an independent vocabulary match, not just a structural one.

THE CAMERA SUB-FORMAT (``SFXDataCamera.cs`` -- the SAME ``Load(BinaryReader)``/``Sequence.Read`` code
used by BOTH ``LoadFromBSC`` (raw17 battle-scene cameras, the format ``battle/camera_codec.py`` already
round-trips byte-exact for real stock scenes) AND ``LoadFromSFX`` (this container's small-file camera
resources, ``SFXDataCamera.cs:112-128``) -- ONE shared binary Code-stream format, confirmed by direct
reading of the source, not assumed):

  - Outer ``Flags`` (u16) selects up to 3 ``Sequence``s (``HAS_SEQUENCE_0/1/2`` = bits 0/1/2), an
    ``HAS_UNKNOWN`` 4-byte block (bit 3), and an ``HAS_CUSTOM_POSITION`` 3x Int16 block (bits 4-7) --
    NONE of ef227's 3 camera resources use the custom-position bits (confirmed: outer flags == 0x9 ==
    HAS_SEQUENCE_0 | HAS_UNKNOWN on all 3).
  - A ``Sequence`` is a Code stream: u16 ``frame`` (0 = end), u16 ``CodeFlags``, then CONDITIONAL
    sub-blocks gated bit-by-bit: a 6-byte spherical ``Position`` (code/flags/pitch/orientation/roll/
    distance bytes) for the camera and, separately, for a TARGET; a 4-byte ``Movement``
    (duration u16, type u8, unknown u8) for each; a 2-byte ``Signing``; a 4-byte ``Focal``
    (duration u8, flags u8, distance u16); assorted unknown blocks (``SFXDataCamera.cs:211-309``).
  - **THE RECOVERED CLOCK (this session's own finding, not in any prior doc)**: a camera resource's
    own ``frame`` values are LOCAL to that resource, re-based to 1 at the ``PLAY_CAMERA`` op that
    activates it. Absolute tick (the SAME clock the s47 probe's own ``frame`` column and
    ``build_thomas.py``'s piece-boundary frames use -- both ultimately read ``SFX.frameIndex``) =
    ``play_camera_tick + local_frame - 1``. Confirmed independently THREE ways on the real bytes: (1)
    camera A's local frame 71 (a bare "hold" keyframe, code 22, all-zero pitch/orientation/roll/
    distance) maps to absolute tick 84 -- exactly the outer sequence's own
    ``SET_BATTLE_SCENE_TRANSPARENCY(77,0)`` op tick; (2) camera A's final movement (local frame 218,
    duration 24) finishes at local 242 -> absolute 255, landing 3 ticks before the real hard cut to
    camera B at absolute 258 -- i.e. camera A's OWN choreography is authored to land its last move
    right before the cut; (3) camera C (the outro shot) fires at absolute 483, one tick after the
    outer sequence's own pre-outro whiteout (``SET_BG_TRANSPARENCY 255,12`` at 482). Zero fudge
    factor needed on any of the three.

THE GEOMETRIC GAP (confirmed, not assumed): nowhere in the OPEN Assembly-CSharp tree does any code
convert a Position's (pitch, orientation, roll, distance) bytes (nor the paired target Position, nor
the Focal distance) into a Unity world-space eye/look-at. ``SFXDataCamera``'s own consumer engine
(``CameraEngine.SFX_DATA_CAMERA``) is a literal ``// TODO`` that clears state and does nothing
(``SFXDataCamera.cs:550-555``); ``PsxCamera.cs`` only converts an ALREADY-BUILT rotation matrix +
translation to/from Unity's matrix form, never a spherical angle triple. The real per-effect camera
for ``ef227`` is driven by ``CameraEngine.SFX_PLUGIN`` (``SFXDataCamera.cs:544-549``), which calls
STRAIGHT into the closed native plugin (``SFX.UpdateCamera()`` -> ``SFX.SFX_UpdateCamera``, a
``[DllImport]``) every frame -- the geometric application of this exact byte format is inside that
closed DLL (PLAN.md's own "the one genuine native-RE gap" -- correctly scoped there to the creature
mesh codec, but by the identical argument it covers the camera's own spherical-to-matrix step too,
since the ONLY consumer of ``SFXDataCamera.Load()``'s parsed fields that actually drives ``Camera.main``
is that same native call, not any of this managed code).

CONSEQUENCE for placement: this script recovers real, validated SHOT-CUT timing (a strictly better
signal than a position-discontinuity guess) and the raw per-keyframe spherical fields (dumped for the
record), but NOT a literal eye/at world position -- reconstructing that would require disassembling the
DLL, which is out of scope (PLAN.md Route D, "high vs narrow payoff", explicitly not needed for the
custom-summons pillar). "Where Thomas should be" therefore still comes from the s47 mesh-probe's
MEASURED trajectory (``build_thomas.py``'s own ``P1_DEST``..``P10_DEST`` -- real, already-measured
absolute-world positions) -- this script's job is to correct the SHOT WINDOW boundaries those
positions get bucketed into, not to replace them.

Usage::

    py studies/custom-summons/thomas-swap/ef_camera_decode.py
        [--game "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"]
        [--effect 227] [--out-csv <path, default scratch>]

Never writes extracted/decoded stock bytes into this repo -- ``--out-csv`` defaults to a path under
the OS temp dir, and refuses a destination under this repo's own tree.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/thomas-swap -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config  # noqa: E402

# Recorded this session (2026-07-22) purely as a drift guard, the build_thomas.py convention --
# never enforced as fatal (a mismatch just gets printed, since this is a read-only research tool,
# not a deploy script splicing against an exact anchor line).
EXPECTED_EF227_SHA256 = "fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167"
EXPECTED_EF227_SIZE = 823296


class DecodeError(RuntimeError):
    pass


# --------------------------------------------------------------------------- extraction (UnityPy)
def _unitypy():
    from ff9mapkit.extract import _unitypy as _u   # reuse the kit's own lazy import + error message
    return _u()


def extract_ef_bytes(game_path: Path, effect_id: int, arch: str = "x64") -> bytes:
    """Pull ``ef{effect_id:03d}`` (the legacy native binary) out of ``resources.assets`` --
    ``Global/Asset/AssetManager.cs``'s ``Resources.Load<TextAsset>`` target, confirmed present as a
    TextAsset (not any p0data model/scene bundle -- those were already swept, PLAN.md 3.4)."""
    UnityPy = _unitypy()
    path = game_path / arch / "FF9_Data" / "resources.assets"
    if not path.is_file():
        raise DecodeError(f"resources.assets not found: {path}")
    name = f"ef{effect_id:03d}"
    env = UnityPy.load(str(path))
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        if data.m_Name != name:
            continue
        script = data.m_Script
        raw = script.encode("utf-8", "surrogateescape") if isinstance(script, str) else bytes(script)
        return bytes(raw)
    raise DecodeError(f"no TextAsset named {name!r} found in {path}")


# --------------------------------------------------------------------------- SFXBinaryFile.cs port
def _u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


CODE_NAMES = {
    0x00: "END", 0x01: "WAIT", 0x02: "PLAY_CASTER_ANIMATION", 0x05: "LOAD_CHUNK",
    0x0D: "CHANGE_MODEL", 0x23: "SETUP_CAMERA", 0x24: "SHOW_HIDE_CHARACTERS",
    0x25: "EFFECT_POINT", 0x27: "CHANNEL_TOWARD_TARGET", 0x28: "PUT_BACK_IN_SLEEP_MODE",
    0x29: "PLAY_CAMERA", 0x2A: "SET_BATTLE_SCENE_TRANSPARENCY", 0x2B: "WAIT_FOR_ANIMATION",
    0x2D: "PLAY_SOUND", 0x51: "SETUP_DESTINATION", 0x55: "PLAY_MISS_SOUND",
    0x5A: "PLAY_CHARACTER_ANIMATION_LOOPING", 0x5B: "PLAY_CHARACTER_ANIMATION",
    0x62: "FACE_BACK_TO_NORMAL", 0x63: "PLAY_RAW_ANIMATION", 0x64: "PLAY_FREYA_CASTING_ANIM",
    0x69: "MOVE_BEFORE", 0x6F: "MOVE_CASTER",
    0x80: "PLAY_MODEL_ON_TARGET_V1", 0x81: "PLAY_MODEL_ON_TARGET_V2",
    0x82: "PLAY_MODEL_ON_TARGET_V3", 0x83: "PLAY_MODEL_ON_TARGET_V4",
}


def parse_container(b: bytes) -> dict:
    """Port of ``SFXBinaryFile.Load`` (SFXBinaryFile.cs:32-135). Raises DecodeError if the resource
    table doesn't sum to the file's own length -- the load-bearing sanity check this format admits."""
    off = 0
    chunk_count = _u16(b, off); off += 2
    resource_position = 0x800
    chunk_index: list[int] = []
    small_file_full_size: list[int] = []
    small_file_base_offset: list[int] = []
    for i in range(chunk_count):
        ci = _u16(b, off); off += 2
        rc = _u16(b, off); off += 2
        chunk_index.append(ci)
        small_file_full_size.append(0)
        small_file_base_offset.append(0)
        for j in range(rc):
            rid = b[off]; off += 1
            _rinfo = b[off]; off += 1
            rsize = _u16(b, off); off += 2
            if rid == 2:
                small_file_full_size[i] = rsize
                if chunk_index[i] == 0:
                    rsize2 = _u16(b, off); off += 2
                    resource_position += rsize2 * 0x800
                small_file_base_offset[i] = resource_position
                resource_position += small_file_full_size[i] * 0x800
            else:
                resource_position += rsize * 0x800
    if resource_position != len(b):
        raise DecodeError(
            f"container size mismatch: resource table sums to {resource_position:#x}, "
            f"file is {len(b):#x} bytes -- parser drift, refusing to trust the rest of the file"
        )

    small_file_offset: list[list[int]] = [[] for _ in range(chunk_count)]
    small_file_index: list[list[int]] = [[] for _ in range(chunk_count)]
    small_file_raw: list[list[bytes]] = [[] for _ in range(chunk_count)]
    small_file_count = [0] * chunk_count
    external_file_count = [0] * chunk_count
    for i in range(chunk_count):
        if small_file_full_size[i] == 0:
            continue
        p = small_file_base_offset[i]
        first = _u16(b, p); p += 2
        p += 2  # firstFlags -- unused by the directory-length derivation
        small_file_offset[i].append(first)
        small_file_index[i].append(0)
        small_file_count[i] = first // 4
        for j in range(1, small_file_count[i]):
            sf_offset = _u16(b, p); p += 2
            sf_flags = _u16(b, p); p += 2
            if sf_flags == 0xFFFF or small_file_index[i][j - 1] < 0:
                small_file_index[i].append(-1)
                external_file_count[i] += 1
            elif sf_offset == small_file_offset[i][-1]:
                small_file_index[i].append(small_file_index[i][j - 1])
            else:
                small_file_index[i].append(small_file_index[i][j - 1] + 1)
                small_file_offset[i].append(sf_offset)
        small_file_count[i] -= external_file_count[i]
        for j in range(len(small_file_offset[i])):
            if j + 1 < len(small_file_offset[i]):
                sz = small_file_offset[i][j + 1] - small_file_offset[i][j]
            else:
                sz = small_file_full_size[i] * 0x800 - small_file_offset[i][j]
            start = small_file_base_offset[i] + small_file_offset[i][j]
            small_file_raw[i].append(b[start:start + sz])

    # the opcode / SequenceCode stream, from 0x400 -- ALSO recovers the outer-sequence tick timeline
    off = 0x400
    current_chunk = 0
    elapsed = 0
    camera_file_list: list[tuple[int, int]] = []
    timeline: list[tuple[int, str, int, int]] = []
    guard = 0
    while True:
        guard += 1
        if guard > 200_000:
            raise DecodeError("opcode stream never hit END within 200000 ops -- runaway/garbage parse")
        code, a1, a2 = b[off], b[off + 1], b[off + 2]
        off += 3
        if code == 0x01:              # WAIT -- Time=arg2 when arg1==0 (the common case; see docstring)
            elapsed += a2
        if code == 0x05:              # LOAD_CHUNK
            current_chunk = a1
            timeline.append((elapsed, "LOAD_CHUNK", a1, a2))
        elif code == 0x23 and a1 != 0xFF:   # SETUP_CAMERA
            camera_file_list.append((current_chunk, a1))
            timeline.append((elapsed, "SETUP_CAMERA", a1, a2))
        elif code == 0x29 and a2 == 0:      # PLAY_CAMERA
            camera_file_list.append((current_chunk, a1))
            timeline.append((elapsed, "PLAY_CAMERA", a1, a2))
        elif code == 0x2A:            # SET_BATTLE_SCENE_TRANSPARENCY
            timeline.append((elapsed, "SET_BG_TRANSPARENCY", a1, a2))
        elif code == 0x24:            # SHOW_HIDE_CHARACTERS
            timeline.append((elapsed, "SHOW_HIDE_CHARACTERS", a1, a2))
        elif code == 0x25:            # EFFECT_POINT
            timeline.append((elapsed, "EFFECT_POINT", a1, a2))
        if code == 0x00:              # END
            break

    return dict(
        chunk_count=chunk_count, small_file_index=small_file_index, small_file_raw=small_file_raw,
        camera_file_list=camera_file_list, timeline=timeline, total_ticks=elapsed,
    )


# --------------------------------------------------------------------------- SFXDataCamera.cs port
_HAS_SEQ_BITS = (1, 2, 4)
_HAS_UNKNOWN_BIT = 8
_HAS_CUSTOM_POSITION_MASK = 0xF0


def _parse_position(b: bytes, o: int) -> tuple[dict, int]:
    code, flags, pitch, orient, roll, dist = b[o], b[o + 1], b[o + 2], b[o + 3], b[o + 4], b[o + 5]
    return dict(code=code, flags=flags, pitch=pitch, orientation=orient, roll=roll, distance=dist), o + 6


def _parse_movement(b: bytes, o: int) -> tuple[dict, int]:
    dur = _u16(b, o)
    typ, unk = b[o + 2], b[o + 3]
    return dict(duration=dur, type=typ, unknown=unk), o + 4


def parse_sequence_codes(b: bytes, seq_off: int) -> list[dict]:
    """Port of ``SFXDataCamera.Sequence.Read`` (SFXDataCamera.cs:215-309). ``seq_off`` is relative to
    ``b[0]`` (the small-file's own start, i.e. the Load() ``basePos``)."""
    codes: list[dict] = []
    o = seq_off
    guard = 0
    while True:
        guard += 1
        if guard > 10_000:
            raise DecodeError("camera Code stream never hit frame=0 within 10000 entries")
        frame = _u16(b, o); o += 2
        if frame == 0:
            codes.append({"frame": 0})
            return codes
        flags = _u16(b, o); o += 2
        c: dict = {"frame": frame, "flags": flags}
        if flags & 0x03:                       # HAS_CAMERA_POSITION (bit0 | bit1)
            c["cam_pos"], o = _parse_position(b, o)
        if flags & 0x02:                        # HAS_CAMERA_MOVEMENT
            c["cam_move"], o = _parse_movement(b, o)
        if flags & 0x04:                         # HAS_UNKNOWN_1 -- source: reader aborted here
            c["abort"] = "HAS_UNKNOWN_1"
            codes.append(c)
            return codes
        if flags & 0x18:                         # HAS_TARGET_POSITION
            c["target_pos"], o = _parse_position(b, o)
        if flags & 0x10:                          # HAS_TARGET_MOVEMENT
            c["target_move"], o = _parse_movement(b, o)
        if flags & 0x20:                          # HAS_UNKNOWN_2 -- aborts
            c["abort"] = "HAS_UNKNOWN_2"
            codes.append(c)
            return codes
        if flags & 0x40:                          # HAS_SIGNING_VALUE
            c["signing"] = (b[o], b[o + 1]); o += 2
        if flags & 0x200:
            c["unknown3"] = _u16(b, o); o += 2
        if flags & 0x400:
            c["unknown4"] = _u16(b, o); o += 2
        if flags & 0x800:                          # HAS_FOCAL_POINT
            fdur, fflags = b[o], b[o + 1]
            fdist = _u16(b, o + 2)
            c["focal"] = dict(duration=fdur, flags=fflags, distance=fdist)
            o += 4
        if flags & 0x1000:
            c["unknown5"] = struct.unpack_from("<I", b, o)[0]; o += 4
        if flags & 0x4000:                          # HAS_SETTING_CHANGE
            c["variable"] = (b[o], b[o + 1]); o += 2
        if flags & 0x8000:
            c["unknown6"] = struct.unpack_from("<I", b, o)[0]; o += 4
        codes.append(c)


def parse_sfxdatacamera(raw: bytes) -> dict:
    """Port of ``SFXDataCamera.Load`` (SFXDataCamera.cs:28-82)."""
    flags = _u16(raw, 0)
    off_offset = 2
    result: dict = {"flags": flags}
    for bit, name in zip(_HAS_SEQ_BITS, ("sequence0", "sequence1", "sequence2")):
        if flags & bit:
            seq_offset = _u16(raw, off_offset)
            result[name] = parse_sequence_codes(raw, seq_offset)
            off_offset += 2
    if flags & _HAS_UNKNOWN_BIT:
        unk_offset = _u16(raw, off_offset)
        result["unknown"] = list(raw[unk_offset:unk_offset + 4])
        off_offset += 2
    if flags & _HAS_CUSTOM_POSITION_MASK:
        pos_offset = _u16(raw, off_offset)
        result["position"] = list(struct.unpack_from("<3h", raw, pos_offset))
        off_offset += 2
    return result


# --------------------------------------------------------------------------- shot-window recovery
def recover_camera_tracks(container: dict) -> list[dict]:
    """For every ``(chunk, arg)`` the opcode stream names as a camera resource: resolve it through
    ``small_file_index`` (``SFXDataCamera.LoadFromSFX``, SFXDataCamera.cs:112-128), parse it, and find
    the absolute tick it activates at (the matching PLAY_CAMERA/SETUP_CAMERA row in the timeline --
    first occurrence in stream order, matching cameraFileList's own append order 1:1)."""
    play_ticks = [t for (t, name, *_r) in container["timeline"] if name in ("PLAY_CAMERA", "SETUP_CAMERA")]
    tracks = []
    for n, (chunk, arg) in enumerate(container["camera_file_list"]):
        real_idx = container["small_file_index"][chunk][arg]
        fire_tick = play_ticks[n] if n < len(play_ticks) else None
        if real_idx < 0:
            tracks.append(dict(chunk=chunk, arg=arg, external=True, fire_tick=fire_tick))
            continue
        raw = container["small_file_raw"][chunk][real_idx]
        cam = parse_sfxdatacamera(raw)
        tracks.append(dict(chunk=chunk, arg=arg, small_file_index=real_idx, fire_tick=fire_tick,
                            raw_len=len(raw), camera=cam))
    return tracks


def absolute_tick(fire_tick: int, local_frame: int) -> int:
    """THE RECOVERED CLOCK (see module docstring) -- confirmed three independent ways on ef227's real
    bytes, zero fudge factor."""
    return fire_tick + local_frame - 1


# --------------------------------------------------------------------------- reporting / CSV
def _iter_keyframe_rows(tracks: list[dict]):
    for shot_idx, tr in enumerate(tracks):
        if tr.get("external"):
            continue
        cam = tr["camera"]
        for seqname in ("sequence0", "sequence1", "sequence2"):
            for c in cam.get(seqname, []):
                if c.get("frame", 0) == 0:
                    continue
                row = {
                    "shot_index": shot_idx, "chunk": tr["chunk"], "arg": tr["arg"],
                    "sequence": seqname, "local_frame": c["frame"],
                    "abs_tick": absolute_tick(tr["fire_tick"], c["frame"]) if tr["fire_tick"] is not None else "",
                    "flags_hex": f"{c['flags']:#06x}",
                }
                cp = c.get("cam_pos"); tp = c.get("target_pos"); cm = c.get("cam_move")
                tm = c.get("target_move"); fo = c.get("focal")
                if cp:
                    row.update(cam_code=cp["code"], cam_pos_flags=cp["flags"], cam_pitch=cp["pitch"],
                               cam_orientation=cp["orientation"], cam_roll=cp["roll"], cam_distance=cp["distance"])
                if cm:
                    row.update(cam_move_duration=cm["duration"], cam_move_type=cm["type"])
                if tp:
                    row.update(tgt_code=tp["code"], tgt_pos_flags=tp["flags"], tgt_pitch=tp["pitch"],
                               tgt_orientation=tp["orientation"], tgt_roll=tp["roll"], tgt_distance=tp["distance"])
                if tm:
                    row.update(tgt_move_duration=tm["duration"], tgt_move_type=tm["type"])
                if fo:
                    row.update(focal_duration=fo["duration"], focal_flags=fo["flags"], focal_distance=fo["distance"])
                if "abort" in c:
                    row["abort"] = c["abort"]
                yield row


CSV_FIELDS = [
    "shot_index", "chunk", "arg", "sequence", "local_frame", "abs_tick", "flags_hex",
    "cam_code", "cam_pos_flags", "cam_pitch", "cam_orientation", "cam_roll", "cam_distance",
    "cam_move_duration", "cam_move_type",
    "tgt_code", "tgt_pos_flags", "tgt_pitch", "tgt_orientation", "tgt_roll", "tgt_distance",
    "tgt_move_duration", "tgt_move_type",
    "focal_duration", "focal_flags", "focal_distance", "abort",
]


def write_csv(tracks: list[dict], out_path: Path) -> int:
    if REPO in out_path.resolve().parents or out_path.resolve() == REPO:
        raise DecodeError(f"refusing to write decoded stock-derived data under the repo tree: {out_path}")
    rows = list(_iter_keyframe_rows(tracks))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", type=Path, default=None, help="game install path (default: auto-detect)")
    ap.add_argument("--effect", type=int, default=227, help="legacy SpecialEffect id to decode (default 227, Bahamut)")
    ap.add_argument("--arch", default="x64", choices=("x64", "x86"))
    ap.add_argument("--out-csv", type=Path, default=None,
                     help="default: <system temp>/ef_camera_decode/ef<id>_camera.csv")
    args = ap.parse_args()

    game_path = args.game or config.find_game_path()
    out_csv = args.out_csv or Path(tempfile.gettempdir()) / "ef_camera_decode" / f"ef{args.effect:03d}_camera.csv"

    print(f"game install : {game_path}")
    print(f"effect id    : {args.effect}  ({args.arch})")

    try:
        raw = extract_ef_bytes(game_path, args.effect, args.arch)
    except DecodeError as e:
        print(f"REFUSING: {e}", file=sys.stderr)
        return 1

    got_sha = hashlib.sha256(raw).hexdigest()
    print(f"extracted    : {len(raw)} bytes, sha256 {got_sha}")
    if args.effect == 227:
        if got_sha != EXPECTED_EF227_SHA256 or len(raw) != EXPECTED_EF227_SIZE:
            print(f"  NOTE: differs from this session's recorded read ({EXPECTED_EF227_SIZE} bytes, "
                  f"sha256 {EXPECTED_EF227_SHA256}) -- install may have updated; proceeding anyway "
                  "(read-only research tool, not a splice).")
        else:
            print("  matches this session's recorded read exactly.")

    try:
        container = parse_container(raw)
    except DecodeError as e:
        print(f"PARSE FAILED -- container structure did not validate: {e}", file=sys.stderr)
        print("STOPPING per the mission's own instruction: a failed structural validation means the "
              "spec draft doesn't hold for this build; do not trust anything derived below.", file=sys.stderr)
        return 1

    print(f"\nchunk_count={container['chunk_count']}  total_ticks={container['total_ticks']}"
          f"  camera_file_list={container['camera_file_list']}")
    print("\n--- outer sequence timeline (LOAD_CHUNK / camera / bg-fade / effect-point ticks) ---")
    for t in container["timeline"]:
        print(" ", t)

    tracks = recover_camera_tracks(container)
    print(f"\n--- {len(tracks)} camera resource(s) recovered ---")
    for i, tr in enumerate(tracks):
        if tr.get("external"):
            print(f"shot {i}: chunk={tr['chunk']} arg={tr['arg']} -- EXTERNAL FILE (not in this container)")
            continue
        n_codes = sum(len(tr["camera"].get(s, [])) for s in ("sequence0", "sequence1", "sequence2"))
        print(f"shot {i}: chunk={tr['chunk']} arg={tr['arg']} fire_tick={tr['fire_tick']} "
              f"small_file_idx={tr['small_file_index']} raw_len={tr['raw_len']} "
              f"outer_flags={tr['camera']['flags']:#x} keyframe_entries={n_codes}")

    n = write_csv(tracks, out_csv)
    print(f"\nwrote {n} keyframe rows -> {out_csv}")
    print("\nSee this module's own docstring for: the confirmed clock-alignment formula, the "
          "confirmed structural validations, and the confirmed geometric gap (no open-source "
          "spherical-to-worldspace conversion exists for this Position format).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
