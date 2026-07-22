"""THE CAMERA SOLVE -- apply the decompiled ``FF9SpecialEffectPlugin.dll`` spherical->Cartesian
camera formula to ef227's real baked keyframes (reusing ``ef_camera_decode.py``'s container/Code-
stream parser verbatim), and VALIDATE the result hard against the s47 mesh-probe's measured Bahamut
trajectory (``sfxmeshprobe.log``) before anyone builds Thomas's placement on it.

THE HEADLINE RESULT, up front: **NO-GO.** This script reproduces the confirmed trig math faithfully
and byte-cites every claim below, but two of this session's OWN findings -- one carried in from the
decompile pass that spawned this script, one NEW and confirmed by this pass's own PE-section read --
mean a literal per-frame world-space eye/look-at for ef227's actual shots cannot be recovered, not
even approximately, from static analysis:

  1. **The anchor is not static data -- CONFIRMED this pass, not merely suspected.** Every camera
     keyframe ef227 actually uses selects its anchor via ``lookup_anchor`` (RVA
     ``0x1800148f0``-``0x1800149c4`` in the x64 plugin, re-disassembled this pass with the same
     pefile+capstone toolchain the spawning decompile pass used). For a selector in 21-31 (which is
     EVERY keyframe cam_pos/target_pos code this session observed except one hold at code=0 and one
     outro at code=1 -- see ``THE REAL BYTES`` below), the function does ``lea rdx, [rip+0x20b727]``
     at RVA ``0x14932`` (raw bytes ``48 8d 15 27 b7 20 00``, hand-decoded + cross-checked against
     capstone's own operand read) -- a RIP-relative load whose target resolves to **RVA 0x220060**.
     Reading the PE section table directly (this pass, not inherited): that RVA sits inside ``.data``
     (``VirtualAddress=0x4f000, VirtualSize=0x5d3440`` -- ~6.1 MB) at section-relative offset
     ``0x1d1060`` (~1.9 MB in) -- but ``.data``'s own ``SizeOfRawData`` is only ``0x1a000`` (~104 KB,
     ending exactly where ``.pdata``'s ``PointerToRawData`` begins). **0x1d1060 is nowhere near
     0x1a000** -- this address has ZERO bytes backing it on disk. It is deep inside the PE loader's
     auto-zero-fill tail of ``.data``, i.e. a **runtime-populated scratch buffer**, not a compiled-in
     constant table. The prior decompile pass's own "STATIC_TABLE" label was an unverified assumption
     (it never checked disk-backing); this pass refutes it directly. The likely mechanism, unconfirmed
     but consistent with PLAN.md's own PDB-string finding (``sonoda\\PsxEmulator.cpp``): this is a
     slice of an emulated PS1-RAM scratch region, seeded per-cast by the native ``SFX_Play`` init path
     (``PLAY_MODEL_ON_TARGET_V1``, the outer opcode stream's own 0x80 op, fires at tick 15 and 258 --
     suspiciously exactly where each camera shot activates) from battle-runtime state (caster/target
     positions marshalled in from C#) that this pass did not trace further. Bottom line: **no amount
     of additional static disassembly recovers this value** -- it would need a live memory read during
     an actual cast (e.g. extending the s47 probe to also log this exact scratch address), which is a
     different, bigger task than this one.
  2. **Branch B, not branch A, governs nearly every real keyframe -- confirmed by direct byte tally.**
     Of the 38 total Position records (cam_pos + target_pos) across all 3 of ef227's real camera
     resources, the per-Position ``flags`` byte distribution is ``{128: 32, 0: 4, 192: 2}``. Only
     ``0xC0`` (192) has bit 0x40 set -- the CONFIRMED, fully-resolved "branch A" of ``resolve_position``
     (RVA ``0x1800145a0``). **Both 192-flagged records belong to the SAME single keyframe** (shot 2's
     one-and-only pose, local_frame=1, code=1 -- the near-static outro). Every other keyframe in the
     entire cinematic -- i.e. ALL of shot 0 and shot 1, the two shots that carry the whole flight
     Thomas needs to be placed within -- uses branch B, whose own secondary orientation-offset comes
     from the SAME unrecoverable scratch buffer as finding (1) above. There is no way to apply the
     fully-confirmed formula to the frames that matter.

Given both, this script still computes a best-effort reconstruction (substituting the s47 probe's own
measured Bahamut position as an anchor PROXY -- see ``THE ANCHOR-PROXY ASSUMPTION`` below, exactly the
mission's own suggested fallback) so the disagreement can be MEASURED, not just asserted. The measured
disagreement (this pass's own run, see ``--validate`` output): computed eye-to-target distances land in
a plausible cinematic range (189-2962 units, median ~1009 -- consistent with the mission's own "hundreds
to few thousand units" expectation), BUT the "does the eye sit below/level with the target during a
crane-up shot" check the user's own description predicts comes out **9 below / 14 above / not computed
for a few** out of 24 fully-resolved rows -- i.e. close to a coin flip, not a confirmation. Per this
project's own law (the mission's own instruction, and ``feedback-incremental-verbatim-first``): a
result that doesn't clearly agree with the measured log is reported as disagreeing, not built on.

CONSEQUENCE (this is the actionable part): Thomas's placement stays exactly what ``build_thomas.py``
already ships -- the s47 mesh-probe's OWN measured creature trajectory (``P1_DEST``..``P10_DEST``,
``ENTRANCE_ORIGIN``, ``P11_TAIL_DEST``), unchanged, with the qualitative ``YAW_BROADSIDE=90`` scheme
also unchanged. This script's OWN genuinely confirmed contribution is exactly what FLIGHT v3 already
banked from ``ef_camera_decode.py`` -- the real shot-cut tick boundaries (258, 483) -- and that
contribution is NOT touched or revisited here. See ``build_placement_table()``'s docstring for the
final per-piece table this script actually recommends (a restatement/citation of build_thomas.py's own
constants, not a new computation) and its explicit confidence rating.

THE REAL BYTES (this session, extracted via ``ef_camera_decode.py``'s own ``extract_ef_bytes`` against
the live install's ``resources.assets``, sha256 ``fe590d00...ed167`` -- matches ``ef_camera_decode.py``'s
own recorded read exactly): ef227's 3 camera resources carry ``cam_pos``/``target_pos`` records whose
``code`` byte (masked ``& 0x1F``) is overwhelmingly in the 21-31 "scratch-buffer" selector range --
22, 23, 24 account for all but two records (one bare ``code=0`` movement waypoint in shot 1, confirmed
ZERO-anchor by the disassembly; one ``code=1`` pose in shot 2, also confirmed ZERO-anchor). Every
``target_pos`` record's own ``distance`` byte is **0 in all 11 occurrences** -- a genuine, confirmed
structural fact (not an assumption): a zero distance nullifies ``resolve_position``'s entire trig
product regardless of branch/anchor/scale, so **the target position always equals its anchor exactly**.
This is what licenses the anchor-proxy substitution below (target = anchor = "whatever the camera is
looking at" = plausibly Bahamut himself, the whole point of a creature cinematic's own camera).

THE CONFIRMED FORMULA (branch A, ``flags & 0x40`` set -- RVA ``0x1800145a0``, inherited from the
spawning decompile pass, re-cited here verbatim since this script implements it): given a Position's
raw bytes (pitch, orientation, distance -- roll is read but never consumes into this math, confirmed
dead-for-translation by the spawning pass), and ``K = 4096.8`` (byte-verified: ``struct.pack('<d',
4096.8).hex() == 'cdcccccccc00b040'``, matched at RVA ``0x18004b6c8``)::

    rad_per_unit = 2*pi / K
    pitch_rad    = sign8(pitch)       * rad_per_unit
    orient_rad   = sign8(orientation) * rad_per_unit
    r            = sign8(distance) * DISTANCE_SCALE        # world-unit scale-up, see below

    CA   = round(cos(pitch_rad) * K);  CA_R = (CA * r) >> 12
    SB   = round(sin(orient_rad) * -K); X = (SB * CA_R) >> 12
    CB   = round(cos(orient_rad) * -K); Z = (CB * CA_R) >> 12
    SA   = round(sin(pitch_rad) * K);   Y = (SA * r) >> 12

    world = anchor + (X, Y, Z)

DISTANCE_SCALE (unresolved by disassembly, per the spawning pass's own explicit recommendation to
solve it empirically instead): this script defaults to **63.0** (the mission's own "~63 world-units/
byte" hint) purely because it produces the plausible-magnitude result cited above -- this is a
CALIBRATED GUESS, not a re-derived constant; override with ``--distance-scale`` to test others.
``sign8`` treats each wire byte as a signed 8-bit value (-128..127); whether pitch/orientation ALSO
need a pre-multiply (a ``shl ax,5``/``shl ax,6``-style widening the spawning pass found evidence of
but could not conclusively attribute to any specific field) is a second open scale ambiguity --
``--pitch-scale``/``--orient-scale`` expose it for a future round without a code change.

THE ANCHOR-PROXY ASSUMPTION (this script's own addition, per the mission's explicit instruction to
"parameterize with the bench's known positions... state the assumption"): for any keyframe whose
``anchor_kind`` resolves to ``STATIC_TABLE_UNRECOVERABLE`` (the scratch-buffer case, finding 1 above),
this script substitutes the s47 mesh-probe's own measured Bahamut position (``sfxmeshprobe.log``,
median across the 7 confirmed creature/body keys, PROBE.md's own reconstruction method: X/Y = bounds
center, Z = far corner) at the matching absolute tick, using the SAME recovered-clock formula
``ef_camera_decode.py`` already validated (``abs_tick = fire_tick + local_frame - 1``). This is a
PROXY, not a recovered value -- it assumes the camera's look-at anchor coincides with Bahamut's own
body position, licensed only by the target-distance-always-zero structural fact above, and it is
explicitly why this script's own validation run (below) does not close cleanly: it is testing the
proxy assumption, not the ground truth.

Usage::

    py studies/custom-summons/thomas-swap/ef_camera_solve.py
        [--game <path>] [--effect 227] [--mesh-probe-log <path>]
        [--distance-scale 63.0] [--pitch-scale 1.0] [--orient-scale 1.0]
        [--max-probe-gap 8] [--out-csv <path>]

Never writes extracted stock bytes or raw log content into this repo (the ``ef_camera_decode.py``
provenance convention) -- ``--out-csv`` defaults to a path under the OS temp dir and refuses a
destination under this repo's own tree; the file it writes is 100% DERIVED numeric analysis (computed
offsets/positions), not a copy of any Square-Enix asset.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/thomas-swap -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(KIT))

import ef_camera_decode as camdecode        # noqa: E402  -- reused verbatim, not re-implemented
from ff9mapkit import config                # noqa: E402
import build_thomas as bt                   # noqa: E402  -- READ-ONLY citation of the shipped, measured
                                             # FLIGHT v3 constants; never written back to by this script


class SolveError(RuntimeError):
    pass


# --------------------------------------------------------------------------- confirmed constants
K_ANGLE = 4096.8                             # byte-verified, RVA 0x18004b6c8 (see module docstring)
DEFAULT_DISTANCE_SCALE = 63.0                # CALIBRATED GUESS (mission's own hint), not re-derived
DEFAULT_MAX_PROBE_GAP = 8                    # ticks -- how far a keyframe may be from the nearest
                                              # logged mesh-probe frame before the anchor-proxy is
                                              # declared UNAVAILABLE rather than stretched thin

# The 7 confirmed Bahamut body/creature mesh keys (PROBE.md round 1) -- cited from build_thomas.py's
# own HIDE_KEYS rather than re-declared, so this script can never silently drift from the shipped list.
HIDE_KEYS: "tuple[str, ...]" = bt.HIDE_KEYS


# --------------------------------------------------------------------------- the confirmed trig (branch A)
def sign8(b: int) -> int:
    """Wire byte -> signed 8-bit value (-128..127). See docstring's DISTANCE_SCALE note for why this,
    not a 16-bit interpretation, is this script's default."""
    return b - 256 if b > 127 else b


def resolve_offset(pitch: int, orientation: int, distance: int, *,
                    distance_scale: float = DEFAULT_DISTANCE_SCALE,
                    pitch_scale: float = 1.0, orient_scale: float = 1.0,
                    K: float = K_ANGLE) -> "tuple[float, float, float]":
    """The CONFIRMED branch-A formula (RVA 0x1800145a0), applied uniformly to every keyframe this
    script processes regardless of its own ``flags`` byte -- see module docstring finding (2): nearly
    every real ef227 keyframe is actually branch B (the "signing value" case, unresolved secondary
    orientation offset), so this is a DOCUMENTED APPROXIMATION for those rows, not the exact math.
    Uses float division in place of the native ``>> 12`` fixed-point shift (equivalent for validation-
    purposes magnitude/sign checks; the native code's integer truncation differs by at most 1 part in
    4096, irrelevant at the scale these positions operate at)."""
    rad_per_unit = 2.0 * math.pi / K
    pitch_rad = sign8(pitch) * pitch_scale * rad_per_unit
    orient_rad = sign8(orientation) * orient_scale * rad_per_unit
    r = sign8(distance) * distance_scale

    CA = round(math.cos(pitch_rad) * K)
    CA_R = (CA * r) / 4096.0
    SB = round(math.sin(orient_rad) * -K)
    X = (SB * CA_R) / 4096.0
    CB = round(math.cos(orient_rad) * -K)
    Z = (CB * CA_R) / 4096.0
    SA = round(math.sin(pitch_rad) * K)
    Y = (SA * r) / 4096.0
    return (X, Y, Z)


def anchor_kind_for_code(code: int) -> "tuple[str, int | None]":
    """Port of ``lookup_anchor``'s selector dispatch (RVA 0x1800148f0, re-disassembled this pass --
    see module docstring finding (1) for the STATIC_TABLE-is-runtime-scratch refutation). Returns one
    of:
      ("ZERO", None)                        -- selector 0, or any UNHANDLED 1-10/12-20 -> anchor=(0,0,0),
                                                CONFIRMED (both a `je` to a pre-zeroed exit and every
                                                non-selector-11 branch in the 1-20 range fall through to
                                                the same zeroed return).
      ("TRGCPOS_LIVE", None)                -- selector 11 (0xB) -> the live BattleCallback-fed
                                                trgcpos_x/z globals (Y forced 0) -- NOT used by any
                                                keyframe this session observed in ef227, so this script
                                                treats it as UNAVAILABLE (no known live value) if hit.
      ("STATIC_TABLE_UNRECOVERABLE", idx)   -- selector 21-31 (idx = selector-21) -- CONFIRMED this
                                                pass to be a runtime-populated scratch buffer (RVA
                                                0x220060, inside .data's auto-zero-fill tail, ~1.9MB
                                                into a 6.1MB virtual region backed by only ~104KB on
                                                disk) -- NOT recoverable by static disassembly.
    """
    sel = code & 0x1F
    if sel == 0:
        return ("ZERO", None)
    if sel <= 0x14:
        if sel == 0x0B:
            return ("TRGCPOS_LIVE", None)
        return ("ZERO", None)
    return ("STATIC_TABLE_UNRECOVERABLE", sel - 0x15)


# --------------------------------------------------------------------------- s47 mesh-probe reuse
def load_mesh_probe_trajectory(log_path: Path, hide_keys: "tuple[str, ...]" = HIDE_KEYS) -> "dict[int, tuple[float, float, float]]":
    """PROBE.md's own reconstruction method (unchanged, re-cited not reinvented): per frame, median
    across the confirmed creature/body keys of X,Y = bounds CENTER (``cx``,``cy``), Z = the FAR CORNER
    (``cz +/- ez``, whichever has the larger magnitude). Returns {frame: (x,y,z)}. Empty dict (not an
    error) if the log doesn't exist -- callers degrade to reporting every anchor as UNAVAILABLE, which
    is itself a legitimate, honestly-reported outcome for a machine with no probe log yet."""
    if not log_path.is_file():
        return {}
    by_frame: "dict[int, list[tuple[float, float, float]]]" = {}
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("MESH,"):
                continue
            parts = line.rstrip("\n").split(",")
            if len(parts) < 13:
                continue
            frame = int(parts[2])
            key_hex = parts[4]
            if key_hex not in hide_keys:
                continue
            cx, cy, cz, ex, ey, ez = (float(x) for x in parts[7:13])
            z_far = cz + ez if abs(cz + ez) > abs(cz - ez) else cz - ez
            by_frame.setdefault(frame, []).append((cx, cy, z_far))
    return {
        frame: (statistics.median([p[0] for p in pts]),
                 statistics.median([p[1] for p in pts]),
                 statistics.median([p[2] for p in pts]))
        for frame, pts in by_frame.items()
    }


def nearest_probe_point(traj: "dict[int, tuple[float, float, float]]", tick: int,
                          max_gap: int = DEFAULT_MAX_PROBE_GAP) -> "tuple[float, float, float] | None":
    best_gap = None
    best_frame = None
    for frame in traj:
        gap = abs(frame - tick)
        if gap <= max_gap and (best_gap is None or gap < best_gap):
            best_gap, best_frame = gap, frame
    return traj[best_frame] if best_frame is not None else None


# --------------------------------------------------------------------------- per-keyframe solve
def iter_camera_keyframes(tracks: "list[dict]"):
    """Walk ``ef_camera_decode.recover_camera_tracks()``'s own parsed output, yielding one dict per
    keyframe ROW that carries a ``cam_pos`` (the vast majority do). Implements TARGET INHERITANCE:
    a keyframe lacking its own ``target_pos`` carries forward the last explicit one seen in this same
    camera resource (matching how a real animation-curve system would treat "no new target given" --
    this script's own addition, ``ef_camera_decode.py`` itself does no such inheritance)."""
    for shot_index, tr in enumerate(tracks):
        if tr.get("external"):
            continue
        cam = tr["camera"]
        cur_target_code = None
        cur_target_pos = None
        for seqname in ("sequence0", "sequence1", "sequence2"):
            for c in cam.get(seqname, []):
                if c.get("frame", 0) == 0:
                    continue
                if "target_pos" in c:
                    cur_target_code = c["target_pos"]["code"]
                    cur_target_pos = c["target_pos"]
                cp = c.get("cam_pos")
                if not cp:
                    continue
                abs_tick = camdecode.absolute_tick(tr["fire_tick"], c["frame"]) if tr["fire_tick"] is not None else None
                yield dict(shot_index=shot_index, local_frame=c["frame"], abs_tick=abs_tick,
                           cam_pos=cp, target_code=cur_target_code, target_pos=cur_target_pos)


def solve(tracks: "list[dict]", traj: "dict[int, tuple[float, float, float]]", *,
          distance_scale: float = DEFAULT_DISTANCE_SCALE, pitch_scale: float = 1.0,
          orient_scale: float = 1.0, max_gap: int = DEFAULT_MAX_PROBE_GAP) -> "list[dict]":
    rows = []
    for kf in iter_camera_keyframes(tracks):
        cp = kf["cam_pos"]
        abs_tick = kf["abs_tick"]
        cam_akind, cam_idx = anchor_kind_for_code(cp["code"])
        probe_pt = nearest_probe_point(traj, abs_tick, max_gap) if abs_tick is not None else None

        if cam_akind == "ZERO":
            anchor = (0.0, 0.0, 0.0)
            anchor_src = "CONFIRMED_ZERO"
        elif cam_akind == "STATIC_TABLE_UNRECOVERABLE":
            anchor = probe_pt
            anchor_src = "MESH_PROBE_PROXY" if probe_pt is not None else "UNAVAILABLE"
        else:  # TRGCPOS_LIVE -- no live value known statically
            anchor = None
            anchor_src = "UNAVAILABLE"

        offset = resolve_offset(cp["pitch"], cp["orientation"], cp["distance"],
                                 distance_scale=distance_scale, pitch_scale=pitch_scale,
                                 orient_scale=orient_scale)
        eye = tuple(a + o for a, o in zip(anchor, offset)) if anchor is not None else None

        tworld = None
        target_akind = None
        if kf["target_pos"] is not None:
            target_akind, _ = anchor_kind_for_code(kf["target_code"])
            if target_akind == "ZERO":
                tanchor = (0.0, 0.0, 0.0)
            elif target_akind == "STATIC_TABLE_UNRECOVERABLE":
                tanchor = probe_pt
            else:
                tanchor = None
            if tanchor is not None:
                toffset = resolve_offset(kf["target_pos"]["pitch"], kf["target_pos"]["orientation"],
                                          kf["target_pos"]["distance"], distance_scale=distance_scale,
                                          pitch_scale=pitch_scale, orient_scale=orient_scale)
                tworld = tuple(a + o for a, o in zip(tanchor, toffset))

        dist_et = math.dist(eye, tworld) if (eye is not None and tworld is not None) else None
        rows.append(dict(
            shot_index=kf["shot_index"], local_frame=kf["local_frame"], abs_tick=abs_tick,
            code=cp["code"], selector=cp["code"] & 0x1F, anchor_kind=cam_akind,
            flags=cp["flags"], branch="A" if (cp["flags"] & 0x40) else "B",
            pitch=cp["pitch"], orientation=cp["orientation"], distance=cp["distance"],
            probe_pt=probe_pt, anchor_src=anchor_src, offset=offset, eye=eye, target=tworld,
            eye_target_dist=dist_et,
        ))
    return rows


# --------------------------------------------------------------------------- validation / reporting
def validate(rows: "list[dict]") -> dict:
    """Quantify agreement against the mesh-probe log per the mission's own go/no-go criteria:
    magnitude sanity (hundreds-few-thousand units) and the "eye below/level with target during a
    crane-up shot" directional check the user's own description predicts."""
    resolved = [r for r in rows if r["eye"] is not None and r["target"] is not None]
    dists = [r["eye_target_dist"] for r in resolved if r["eye_target_dist"] and r["eye_target_dist"] > 0.01]
    below = sum(1 for r in resolved if r["eye"][1] < r["target"][1])
    above = sum(1 for r in resolved if r["eye"][1] > r["target"][1])
    branch_a = sum(1 for r in rows if r["branch"] == "A")
    branch_b = sum(1 for r in rows if r["branch"] == "B")
    unrecoverable = sum(1 for r in rows if r["anchor_kind"] == "STATIC_TABLE_UNRECOVERABLE" and r["anchor_src"] == "UNAVAILABLE")
    proxied = sum(1 for r in rows if r["anchor_src"] == "MESH_PROBE_PROXY")
    zero_anchor = sum(1 for r in rows if r["anchor_kind"] == "ZERO")

    per_shot = {}
    for shot_index in sorted({r["shot_index"] for r in rows}):
        shot_resolved = [r for r in resolved if r["shot_index"] == shot_index]
        if not shot_resolved:
            per_shot[shot_index] = dict(n=0)
            continue
        sd = [r["eye_target_dist"] for r in shot_resolved]
        per_shot[shot_index] = dict(
            n=len(shot_resolved),
            below=sum(1 for r in shot_resolved if r["eye"][1] < r["target"][1]),
            above=sum(1 for r in shot_resolved if r["eye"][1] > r["target"][1]),
            dist_min=min(sd), dist_max=max(sd),
        )

    return dict(
        total_keyframes=len(rows), resolved_both=len(resolved),
        branch_a_count=branch_a, branch_b_count=branch_b,
        zero_anchor_count=zero_anchor, proxied_count=proxied, unrecoverable_count=unrecoverable,
        dist_min=min(dists) if dists else None, dist_max=max(dists) if dists else None,
        dist_median=statistics.median(dists) if dists else None,
        below_count=below, above_count=above, per_shot=per_shot,
    )


def build_placement_table() -> "list[dict]":
    """THE PLACEMENT TABLE this script actually recommends, per its own NO-GO verdict above: a
    RESTATEMENT of ``build_thomas.py``'s own already-shipped, already-measured FLIGHT v3 constants
    (P1_DEST..P10_DEST + the reasoned ENTRANCE_ORIGIN/P11_TAIL_DEST extrapolations), with NO
    eye-derived "pull toward camera" adjustment and NO per-shot computed yaw -- both were asked for by
    the mission, and both are withheld here because this module's own validation (see ``validate()``'s
    output) does not clear the bar: the eye/look-at reconstruction it would take to compute either
    disagrees with (or at best is a coin-flip against) the measured mesh-probe log, for the two shots
    (0 and 1) covering essentially the entire flight. Confidence per piece follows build_thomas.py's
    own CAVEAT (a)/(b)/(d) -- restated here, not re-derived."""
    pieces = [
        dict(piece="P1 ENTRANCE", frames="0-82", dest=bt.ENTRANCE_ORIGIN, note="unmeasured Origin -> measured P1_DEST",
             confidence="Origin: REASONED EXTRAPOLATION (zero ground truth); Dest: measured"),
        dict(piece="P2 RISE-TO-FAR", frames="82-144", dest=bt.P2_DEST, confidence="measured, solid"),
        dict(piece="P3 FAR-DIP", frames="144-157", dest=bt.P3_DEST, confidence="measured, solid"),
        dict(piece="P4 FAR-DEEP", frames="157-172", dest=bt.P4_DEST, confidence="measured, n=4 LOW-SAMPLE (PROBE.md)"),
        dict(piece="P5 RETURN-DRIFT", frames="172-179", dest=bt.P5_DEST, confidence="measured, n=28 solid"),
        dict(piece="P6 2ND-APPROACH", frames="179-204", dest=bt.P6_DEST, confidence="measured, solid"),
        dict(piece="P7 CHARGE-DRIFT", frames="204-207", dest=bt.P7_DEST, confidence="measured, n=28 solid"),
        dict(piece="P8 CHARGE-HOLD", frames="207-258", dest=bt.P8_DEST, confidence="measured, solid"),
        dict(piece="CUT1 (real cut)", frames="258-262", dest=bt.P9_DEST, confidence="camera-decode CONFIRMED cut tick; position = snap to P9_DEST"),
        dict(piece="P9 GROUND-REIGN", frames="262-414", dest=bt.P9_DEST, confidence="measured, solid (both damage beats land here)"),
        dict(piece="P10 EXIT-EDGE", frames="414-417", dest=bt.P10_DEST, confidence="measured, n=4 low-sample"),
        dict(piece="P10_HOLD", frames="417-483", dest=bt.P10_DEST, confidence="camera-decode CONFIRMED 2nd cut tick; position held"),
        dict(piece="P11 TAIL", frames="483-580", dest=bt.P11_TAIL_DEST, confidence="UNMEASURED extrapolation (zero ground truth past frame 417)"),
    ]
    for p in pieces:
        p["yaw_deg"] = bt.YAW_BROADSIDE
        p["yaw_source"] = "UNCHANGED from build_thomas.py -- qualitative scheme, NOT camera-eye-derived (see NO-GO)"
        p["eye_pull"] = "NONE APPLIED -- no eye reconstruction cleared validation for this shot"
    return pieces


# --------------------------------------------------------------------------- CLI
CSV_FIELDS = ["shot_index", "local_frame", "abs_tick", "code", "selector", "anchor_kind", "branch",
              "flags", "pitch", "orientation", "distance", "anchor_src", "offset_x", "offset_y",
              "offset_z", "eye_x", "eye_y", "eye_z", "target_x", "target_y", "target_z", "eye_target_dist"]


def write_csv(rows: "list[dict]", out_path: Path) -> int:
    if REPO in out_path.resolve().parents or out_path.resolve() == REPO:
        raise SolveError(f"refusing to write derived data under the repo tree: {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, restval="")
        w.writeheader()
        for r in rows:
            flat = dict(r)
            for name, tup in (("offset", flat.pop("offset", None)), ("eye", flat.pop("eye", None)),
                               ("target", flat.pop("target", None))):
                if tup is not None:
                    flat[f"{name}_x"], flat[f"{name}_y"], flat[f"{name}_z"] = tup
            flat.pop("probe_pt", None)
            w.writerow(flat)
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", type=Path, default=None)
    ap.add_argument("--effect", type=int, default=227)
    ap.add_argument("--arch", default="x64", choices=("x64", "x86"))
    ap.add_argument("--mesh-probe-log", type=Path, default=None,
                     help="default: <game>/sfxmeshprobe.log")
    ap.add_argument("--distance-scale", type=float, default=DEFAULT_DISTANCE_SCALE)
    ap.add_argument("--pitch-scale", type=float, default=1.0)
    ap.add_argument("--orient-scale", type=float, default=1.0)
    ap.add_argument("--max-probe-gap", type=int, default=DEFAULT_MAX_PROBE_GAP)
    ap.add_argument("--out-csv", type=Path, default=None,
                     help="default: <system temp>/ef_camera_solve/ef<id>_solve.csv")
    args = ap.parse_args()

    game_path = args.game or config.find_game_path()
    log_path = args.mesh_probe_log or (game_path / "sfxmeshprobe.log")
    out_csv = args.out_csv or Path(tempfile.gettempdir()) / "ef_camera_solve" / f"ef{args.effect:03d}_solve.csv"

    print(f"game install    : {game_path}")
    print(f"effect id       : {args.effect} ({args.arch})")
    print(f"mesh-probe log  : {log_path} ({'found' if log_path.is_file() else 'NOT FOUND'})")
    print(f"distance_scale  : {args.distance_scale}  pitch_scale: {args.pitch_scale}  orient_scale: {args.orient_scale}")

    raw = camdecode.extract_ef_bytes(game_path, args.effect, args.arch)
    container = camdecode.parse_container(raw)
    tracks = camdecode.recover_camera_tracks(container)
    traj = load_mesh_probe_trajectory(log_path)
    print(f"\nmesh-probe creature-key frames loaded: {len(traj)}"
          + (f" (range {min(traj)}-{max(traj)})" if traj else " -- NONE (every anchor will read UNAVAILABLE)"))

    rows = solve(tracks, traj, distance_scale=args.distance_scale, pitch_scale=args.pitch_scale,
                 orient_scale=args.orient_scale, max_gap=args.max_probe_gap)
    stats = validate(rows)

    print(f"\n--- VALIDATION (go/no-go inputs) ---")
    print(f"total camera-position keyframes         : {stats['total_keyframes']}")
    print(f"  branch A (confirmed formula)           : {stats['branch_a_count']}")
    print(f"  branch B (unresolved 'signing value')  : {stats['branch_b_count']}")
    print(f"  CONFIRMED_ZERO anchor                  : {stats['zero_anchor_count']}")
    print(f"  MESH_PROBE_PROXY anchor (assumption)   : {stats['proxied_count']}")
    print(f"  UNRECOVERABLE (no nearby probe data)   : {stats['unrecoverable_count']}")
    print(f"rows with both eye+target resolved       : {stats['resolved_both']}")
    if stats["dist_min"] is not None:
        print(f"eye-target distance range               : {stats['dist_min']:.1f} - {stats['dist_max']:.1f}"
              f" (median {stats['dist_median']:.1f}) -- 'cinematically sane' per the mission's own"
              f" hundreds-to-few-thousand-units expectation: {'YES' if stats['dist_max'] < 10000 else 'CHECK'}")
    print(f"eye.Y < target.Y (matches 'low-angle crane-up')  : {stats['below_count']}")
    print(f"eye.Y > target.Y (does NOT match)                : {stats['above_count']}")
    ratio_ok = stats["below_count"] > 1.5 * stats["above_count"] if stats["above_count"] else stats["below_count"] > 0
    print(f"directional check clears a 'clearly confirms' bar: {'YES' if ratio_ok else 'NO -- near coin-flip or worse'}")

    print(f"\n--- per-shot ---")
    for shot_index, s in stats["per_shot"].items():
        if s.get("n", 0) == 0:
            print(f" shot {shot_index}: no fully-resolved rows")
            continue
        print(f" shot {shot_index}: n={s['n']}  below={s['below']} above={s['above']}"
              f"  dist [{s['dist_min']:.1f}, {s['dist_max']:.1f}]")

    verdict_go = stats["branch_a_count"] >= stats["total_keyframes"] and ratio_ok
    print(f"\n=== GO/NO-GO: {'GO' if verdict_go else 'NO-GO'} ===")
    if not verdict_go:
        print("Reasons (see module docstring for full citations):")
        print(f" - only {stats['branch_a_count']}/{stats['total_keyframes']} keyframes use the fully-confirmed")
        print("   branch-A formula; the rest (shots 0+1, the whole flight) use the unresolved branch B.")
        print(f" - the anchor for {stats['proxied_count']} keyframes is a PROXY (Bahamut's own measured")
        print("   position substituted for a runtime scratch-buffer value confirmed NOT statically recoverable")
        print("   this pass -- RVA 0x220060, .data's auto-zero-fill tail, see docstring finding (1)).")
        print(f" - the directional (crane-up) check is {stats['below_count']} below / {stats['above_count']} above")
        print("   -- not a clear confirmation.")
        print("RECOMMENDATION: do not use this reconstruction to place Thomas or compute yaw. Keep")
        print("build_thomas.py's existing measured P1-P11 trajectory + YAW_BROADSIDE unchanged -- see")
        print("build_placement_table() below, which restates (not recomputes) that shipped data.")

    n = write_csv(rows, out_csv)
    print(f"\nwrote {n} per-keyframe rows -> {out_csv}")

    print(f"\n--- placement table (restated from build_thomas.py, NOT recomputed -- see NO-GO above) ---")
    for p in build_placement_table():
        print(f" {p['piece']:20s} frames {p['frames']:8s} dest={p['dest']}  yaw={p['yaw_deg']}"
              f"  [{p['confidence']}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
